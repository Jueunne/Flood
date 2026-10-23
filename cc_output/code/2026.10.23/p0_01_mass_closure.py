"""P0 step 0: Mississippi basin mask + CaMa water-balance closure test.

Checks, for one CESM2-LE member and one year, whether
    sum_basin(runoff)*86400 - outflw(mouth)*86400  ==  S(d) - S(d-1)
holds day by day, where S = sum_basin(storge) (snapshot at end of day) and
outflw is the daily mean at the basin outlet. Residual tells us how well the
archived outputs close and whether a bifurcation (LPTHOUT) leak exists.

Usage: python -u p0_01_mass_closure.py [member] [year]
"""
import os
import sys
import numpy as np
import xarray as xr

MEM = sys.argv[1] if len(sys.argv) > 1 else "LE2-1031.002"
YEAR = int(sys.argv[2]) if len(sys.argv) > 2 else 1952

MAP = "/data2/juen/RS12_handoff/map/glb_15min"
OUT = f"/data2/juen/CaMa-output/cesm/{MEM}"
ROF = f"/data1/juen/CaMa-input/CESM2_roff/{MEM}"
RES = "/home/juen0828/RS12_Flood_origin/cc_output/result/2026.10.23"
os.makedirs(RES, exist_ok=True)

NX, NY = 1440, 720
lon = -179.875 + 0.25 * np.arange(NX)
lat = 89.875 - 0.25 * np.arange(NY)          # row 0 = north (GrADS yrev)


def rbin(name, dtype, nvar=1):
    a = np.fromfile(f"{MAP}/{name}.bin", dtype=dtype)
    return a.reshape(nvar, NY, NX) if nvar > 1 else a.reshape(NY, NX)


nextxy = rbin("nextxy", "<i4", 2)
nextx, nexty = nextxy[0], nextxy[1]
basin = rbin("basin", "<i4")
uparea = rbin("uparea", "<f4")               # m2
ctmare = rbin("ctmare", "<f4")               # m2
print("nextx negative codes:", np.unique(nextx[nextx < 0]), flush=True)

# ---- 1. Mississippi outlet = largest uparea river-mouth cell in the delta box
box = (lat[:, None] > 27) & (lat[:, None] < 31) & (lon[None, :] > -92) & (lon[None, :] < -88)
cand = box & (nextx == -9)
iy, ix = np.unravel_index(np.argmax(np.where(cand, uparea, -1)), uparea.shape)
bid = basin[iy, ix]
print(f"outlet: lat={lat[iy]:.3f} lon={lon[ix]:.3f} uparea={uparea[iy,ix]/1e12:.3f} Mkm2 basinID={bid}", flush=True)

mask_b = basin == bid
print(f"basin.bin mask: {mask_b.sum()} cells, ctmare sum={ctmare[mask_b].sum()/1e12:.3f} Mkm2", flush=True)

# ---- cross-check: upstream tracing via nextxy (1-based x,y) from the outlet
down = np.full(NY * NX, -1, dtype=np.int64)
valid = nextx > 0
down[np.flatnonzero(valid)] = (nexty[valid] - 1) * NX + (nextx[valid] - 1)
up = np.zeros(NY * NX, dtype=bool)
up[iy * NX + ix] = True
front = [iy * NX + ix]
src = np.argsort(down)                      # group cells by downstream id
d_sorted = down[src]
while front:
    nxt = []
    for f in front:
        lo = np.searchsorted(d_sorted, f, "left")
        hi = np.searchsorted(d_sorted, f, "right")
        c = src[lo:hi]
        c = c[~up[c]]
        up[c] = True
        nxt.extend(c.tolist())
    front = nxt
mask_t = up.reshape(NY, NX)
print(f"nextxy-traced mask: {mask_t.sum()} cells; equal to basin.bin mask: {np.array_equal(mask_t, mask_b)}; "
      f"traced&!basin={np.sum(mask_t & ~mask_b)}, basin&!traced={np.sum(mask_b & ~mask_t)}", flush=True)
mask = mask_t
np.savez_compressed(f"{RES}/mississippi_mask.npz", mask=mask, outlet_iy=iy, outlet_ix=ix, basin_id=bid,
                    lat=lat, lon=lon)

# bbox for lazy reads
rows = np.flatnonzero(mask.any(1)); cols = np.flatnonzero(mask.any(0))
r0, r1, c0, c1 = rows[0], rows[-1] + 1, cols[0], cols[-1] + 1
m = mask[r0:r1, c0:c1]
area = ctmare[r0:r1, c0:c1]
print(f"bbox rows {r0}:{r1} cols {c0}:{c1}  lat {lat[r0]:.2f}..{lat[r1-1]:.2f} lon {lon[c0]:.2f}..{lon[c1-1]:.2f}", flush=True)

# ---- 2. read outputs (subset)
def rd(var, yr):
    return xr.open_dataset(f"{OUT}/{var}/o_{var}{yr}.nc")[var].isel(lat=slice(r0, r1), lon=slice(c0, c1))

sto = rd("storge", YEAR).load()                       # m3, snapshot at stamp time (00Z next day)
sto_prev = rd("storge", YEAR - 1).isel(time=-1).load()  # storage at 00Z Jan 1 of YEAR
S = np.concatenate([[np.nansum(np.where(m, sto_prev.values, 0))],
                    np.nansum(np.where(m[None], sto.values, 0), axis=(1, 2))])
dS = np.diff(S)                                       # m3 per day
outflw = rd("outflw", YEAR).load()
Qout = outflw.values[:, iy - r0, ix - c0]              # m3/s daily mean at outlet
print(f"days in output: {len(Qout)}; storge stamps {str(sto.time.values[0])[:10]}..{str(sto.time.values[-1])[:10]}", flush=True)

# ---- 3. runoff: 1deg (mm/s) -> 0.25deg cells by containing cell, weight ctmare
ro = xr.open_dataset(f"{ROF}/roff_{YEAR}.nc")["ro"]
rlat, rlon = ro.lat.values, ro.lon.values
assert rlat[0] > rlat[-1] and abs(rlat[0] - 89.5) < 1e-6 and abs(rlon[0] + 179.5) < 1e-6
jr = (np.arange(r0, r1) // 4); jc = (np.arange(c0, c1) // 4)
ro_sub = ro.isel(lat=slice(jr[0], jr[-1] + 1), lon=slice(jc[0], jc[-1] + 1)).load().values  # (t, ny1, nx1)
ro_q = ro_sub[:, jr - jr[0], :][:, :, jc - jc[0]]        # broadcast to 0.25 cells, mm/s
Rin = np.nansum(np.where(m[None], ro_q / 1000.0 * area[None], 0), axis=(1, 2))   # m3/s
print(f"days in runoff: {len(Rin)}", flush=True)
n = min(len(Rin), len(Qout), len(dS))
Rin, Qout, dS = Rin[:n], Qout[:n], dS[:n]

# ---- 4. closure
res = (Rin - Qout) * 86400 - dS                        # m3/day
scale = np.mean(np.abs(Rin)) * 86400
print("\n=== daily closure (lag 0) ===", flush=True)
print(f"mean|res| / mean(Rin*86400) = {np.mean(np.abs(res))/scale:.4f}", flush=True)
print(f"mean res (bias) / mean Rin = {np.mean(res)/scale:+.4f}", flush=True)
for lag in (-1, 1):
    rr = (np.roll(Rin, lag) - Qout) * 86400 - dS
    print(f"lag {lag:+d}: mean|res|/scale = {np.mean(np.abs(rr[2:-2]))/scale:.4f}", flush=True)
print("\n=== annual budget (m3) ===", flush=True)
print(f"sum Rin*86400 = {Rin.sum()*86400:.4e}", flush=True)
print(f"sum Qout*86400= {Qout.sum()*86400:.4e}", flush=True)
print(f"S_end - S_0   = {S[n]-S[0]:.4e}", flush=True)
print(f"residual      = {(Rin.sum()-Qout.sum())*86400-(S[n]-S[0]):.4e}  "
      f"({((Rin.sum()-Qout.sum())*86400-(S[n]-S[0]))/(Rin.sum()*86400)*100:+.2f}% of annual inflow)", flush=True)
print(f"peak Qout {Qout.max():.0f} m3/s on day {np.argmax(Qout)+1}; mean Qout {Qout.mean():.0f} m3/s", flush=True)

np.savez_compressed(f"{RES}/mass_closure_{MEM}_{YEAR}.npz", Rin=Rin, Qout=Qout, dS=dS, S=S, res=res)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, ax = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
d = np.arange(1, n + 1)
ax[0].plot(d, Rin, label="basin runoff in"); ax[0].plot(d, Qout, label="outlet outflw")
ax[0].plot(d, dS / 86400, label="dS/dt"); ax[0].set_ylabel("m$^3$/s"); ax[0].legend()
ax[0].set_title(f"Mississippi water balance, {MEM}, {YEAR}")
ax[1].plot(d, res / scale); ax[1].axhline(0, c="k", lw=.5)
ax[1].set_ylabel("residual / mean inflow"); ax[1].set_xlabel("day of year")
fig.tight_layout(); fig.savefig(f"{RES}/mass_closure_{MEM}_{YEAR}.png", dpi=120)
print("saved", f"{RES}/mass_closure_{MEM}_{YEAR}.png", flush=True)
