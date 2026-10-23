"""P0 step 0b: water-balance closure accounting for bifurcation (LPTHOUT).

(a) union of basins connected to Mississippi (basin 6) through bifprm.txt paths;
    budget = sum runoff - sum outflw(all river-mouth cells in union) - dS(union).
(b) sub-basin upstream of a lower-Mississippi cell (~32.4N) above the first
    cross-basin bifurcation; budget with outflw at that cell. Reports number of
    bifurcation paths crossing the sub-basin boundary.
Usage: python -u p0_02_closure_with_bifurcation.py [member] [year]
"""
import os, sys
import numpy as np
import xarray as xr

MEM = sys.argv[1] if len(sys.argv) > 1 else "LE2-1031.002"
YEAR = int(sys.argv[2]) if len(sys.argv) > 2 else 1952
MAP = "/data2/juen/RS12_handoff/map/glb_15min"
OUT = f"/data2/juen/CaMa-output/cesm/{MEM}"
ROF = f"/data1/juen/CaMa-input/CESM2_roff/{MEM}"
RES = "/home/juen0828/RS12_Flood_origin/cc_output/result/2026.10.23"
NX, NY = 1440, 720
lon = -179.875 + 0.25 * np.arange(NX); lat = 89.875 - 0.25 * np.arange(NY)

def rbin(name, dtype, nvar=1):
    a = np.fromfile(f"{MAP}/{name}.bin", dtype=dtype)
    return a.reshape(nvar, NY, NX) if nvar > 1 else a.reshape(NY, NX)

nextxy = rbin("nextxy", "<i4", 2); nextx, nexty = nextxy[0], nextxy[1]
basin = rbin("basin", "<i4"); uparea = rbin("uparea", "<f4"); ctmare = rbin("ctmare", "<f4")

# downstream index + upstream tracer
down = np.full(NY * NX, -1, np.int64); v = nextx > 0
down[np.flatnonzero(v)] = (nexty[v] - 1) * NX + (nextx[v] - 1)
src = np.argsort(down); d_sorted = down[src]
def upstream(cell):
    up = np.zeros(NY * NX, bool); up[cell] = True; front = [cell]
    while front:
        nxt = []
        for f in front:
            lo, hi = np.searchsorted(d_sorted, f, "left"), np.searchsorted(d_sorted, f, "right")
            c = src[lo:hi]; c = c[~up[c]]; up[c] = True; nxt.extend(c.tolist())
        front = nxt
    return up.reshape(NY, NX)

# bifurcation paths: (ix,iy)->(jx,jy) 1-based, basins at last two columns
bif = np.loadtxt(f"{MAP}/bifprm.txt", skiprows=1)
pix, piy, pjx, pjy = bif[:, 0].astype(int) - 1, bif[:, 1].astype(int) - 1, bif[:, 2].astype(int) - 1, bif[:, 3].astype(int) - 1
pb1, pb2 = bif[:, -2].astype(int), bif[:, -1].astype(int)

# ---- (a) connected-basin union
conn = {6}
while True:
    sel = np.isin(pb1, list(conn)) | np.isin(pb2, list(conn))
    new = set(pb1[sel]) | set(pb2[sel])
    if new <= conn: break
    conn |= new
print("basins connected to 6 by bifurcation:", sorted(conn), flush=True)
mask_u = np.isin(basin, list(conn))
mouths_u = mask_u & (nextx == -9)
print(f"union: {mask_u.sum()} cells, {ctmare[mask_u].sum()/1e12:.3f} Mkm2, {mouths_u.sum()} river-mouth cells", flush=True)
for b in sorted(conn):
    mb = basin == b
    print(f"  basin {b}: {mb.sum()} cells, {ctmare[mb].sum()/1e12:.4f} Mkm2, mouths={np.sum(mb & (nextx==-9))}", flush=True)

# ---- (b) sub-basin above the first cross-basin bifurcation
cross = pb1 != pb2
lat_cross_max = lat[piy[cross & ((pb1 == 6) | (pb2 == 6))]].max()
print(f"northernmost cross-basin bifurcation touching basin 6 at lat {lat_cross_max:.3f}", flush=True)
# pick main-stem cell: max uparea among basin-6 cells in latitude band just north of that
band = (basin == 6) & (lat[:, None] > lat_cross_max + 0.3) & (lat[:, None] < lat_cross_max + 1.3)
giy, gix = np.unravel_index(np.argmax(np.where(band, uparea, -1)), uparea.shape)
print(f"gauge cell: lat={lat[giy]:.3f} lon={lon[gix]:.3f} uparea={uparea[giy,gix]/1e12:.3f} Mkm2", flush=True)
mask_s = upstream(giy * NX + gix)
# bifurcation paths crossing the sub-basin boundary (one end in, one end out)
in1 = mask_s[piy, pix]; in2 = mask_s[pjy, pjx]
ncross = np.sum(in1 != in2)
print(f"sub-basin: {mask_s.sum()} cells, {ctmare[mask_s].sum()/1e12:.3f} Mkm2; bifurcation paths crossing its boundary: {ncross}", flush=True)
if ncross:
    k = np.flatnonzero(in1 != in2)
    for q in k[:10]:
        print(f"   path ({lat[piy[q]]:.2f},{lon[pix[q]]:.2f})->({lat[pjy[q]]:.2f},{lon[pjx[q]]:.2f}) basins {pb1[q]},{pb2[q]}", flush=True)

# ---- budgets
def budget(mask, outcells, label):
    rows = np.flatnonzero(mask.any(1)); cols = np.flatnonzero(mask.any(0))
    r0, r1, c0, c1 = rows[0], rows[-1] + 1, cols[0], cols[-1] + 1
    m = mask[r0:r1, c0:c1]; area = ctmare[r0:r1, c0:c1]; oc = outcells[r0:r1, c0:c1]
    rd = lambda var, yr: xr.open_dataset(f"{OUT}/{var}/o_{var}{yr}.nc")[var].isel(lat=slice(r0, r1), lon=slice(c0, c1))
    sto = rd("storge", YEAR).load().values; sto0 = rd("storge", YEAR - 1).isel(time=-1).load().values
    S = np.concatenate([[np.nansum(np.where(m, sto0, 0))], np.nansum(np.where(m[None], sto, 0), axis=(1, 2))])
    dS = np.diff(S)
    of = rd("outflw", YEAR).load().values
    Qout = np.nansum(np.where(oc[None], of, 0), axis=(1, 2))
    ro = xr.open_dataset(f"{ROF}/roff_{YEAR}.nc")["ro"]
    jr = np.arange(r0, r1) // 4; jc = np.arange(c0, c1) // 4
    ro_sub = ro.isel(lat=slice(jr[0], jr[-1] + 1), lon=slice(jc[0], jc[-1] + 1)).load().values
    ro_q = ro_sub[:, jr - jr[0], :][:, :, jc - jc[0]]
    Rin = np.nansum(np.where(m[None], ro_q / 1000.0 * area[None], 0), axis=(1, 2))
    n = min(len(Rin), len(Qout), len(dS)); Rin, Qout, dS = Rin[:n], Qout[:n], dS[:n]
    res = (Rin - Qout) * 86400 - dS; scale = np.mean(Rin) * 86400
    print(f"\n=== {label} ===", flush=True)
    print(f"mean Rin {Rin.mean():.0f}  mean Qout {Qout.mean():.0f}  peak Qout {Qout.max():.0f} (day {np.argmax(Qout)+1}) m3/s", flush=True)
    print(f"daily mean|res|/scale = {np.mean(np.abs(res))/scale:.4f}   bias = {np.mean(res)/scale:+.4f}", flush=True)
    for lag in (-1, 1):
        rr = (np.roll(Rin, lag) - Qout) * 86400 - dS
        print(f"  lag {lag:+d}: mean|res|/scale = {np.mean(np.abs(rr[2:-2]))/scale:.4f}", flush=True)
    tot = (Rin.sum() - Qout.sum()) * 86400 - (S[n] - S[0])
    print(f"annual residual = {tot:.3e} m3 ({tot/(Rin.sum()*86400)*100:+.2f}% of inflow)", flush=True)
    np.savez_compressed(f"{RES}/closure_{label}_{MEM}_{YEAR}.npz", Rin=Rin, Qout=Qout, dS=dS, S=S, res=res)
    return Rin, Qout, dS, res

budget(mask_u, mouths_u, "union_allmouths")
oc = np.zeros_like(mask_s); oc[giy, gix] = True
budget(mask_s, oc, "subbasin_gauge")
np.savez_compressed(f"{RES}/masks_union_subbasin.npz", mask_union=mask_u, mask_sub=mask_s, gauge_iy=giy, gauge_ix=gix, basins=sorted(conn))
