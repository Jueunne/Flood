"""P0 step 0c: closure with CaMa's own input matrix (inpmat INPX/INPY/INPA).

Rin(cell) = sum_k ro[INPY_k, INPX_k] / DROFUNIT * INPA_k   (exactly what CaMa does)
Budgets: (1) upper-Missouri sub-basin (no bifurcation crossing), (2) basin 6+65 with 2 mouths,
(3) basin 6 only (mouth 1) for reference.
Usage: python -u p0_03_closure_exact_inpmat.py [member] [year]
"""
import sys
import numpy as np
import xarray as xr

MEM = sys.argv[1] if len(sys.argv) > 1 else "LE2-1031.002"
YEAR = int(sys.argv[2]) if len(sys.argv) > 2 else 1952
MAP = "/data2/juen/RS12_handoff/map/glb_15min"
OUT = f"/data2/juen/CaMa-output/cesm/{MEM}"
ROF = f"/data1/juen/CaMa-input/CESM2_roff/{MEM}"
RES = "/home/juen0828/RS12_Flood_origin/cc_output/result/2026.10.23"
NX, NY, INPN, NXIN, NYIN = 1440, 720, 7, 360, 180
lon = -179.875 + 0.25 * np.arange(NX); lat = 89.875 - 0.25 * np.arange(NY)

def rbin(name, dtype, nvar=1):
    a = np.fromfile(f"{MAP}/{name}.bin", dtype=dtype)
    return a.reshape(nvar, NY, NX) if nvar > 1 else a.reshape(NY, NX)
nextx = rbin("nextxy", "<i4", 2)[0]; basin = rbin("basin", "<i4"); ctmare = rbin("ctmare", "<f4")

raw = np.fromfile(f"{MAP}/inpmat_1deg_nc.bin", dtype="<i4").reshape(3 * INPN, NY, NX)
INPX = raw[:INPN]; INPY = raw[INPN:2 * INPN]; INPA = raw[2 * INPN:].view("<f4")
# sanity: level-0 index vs containing 1deg cell for an interior land cell
iy0, ix0 = 200, 300
print(f"cell lat {lat[iy0]:.3f} lon {lon[ix0]:.3f}: INPX0={INPX[0,iy0,ix0]} INPY0={INPY[0,iy0,ix0]} "
      f"(containing 1deg: x={ix0//4+1}, y={iy0//4+1}); INPA sum={INPA[:,iy0,ix0].sum():.4e} ctmare={ctmare[iy0,ix0]:.4e}", flush=True)
land = basin > 0
print(f"global: sum INPA / sum ctmare over land = {INPA[:, land].sum()/ctmare[land].sum():.5f}", flush=True)

mk = np.load(f"{RES}/masks_union_subbasin.npz")
mask_sub, giy, gix = mk["mask_sub"], int(mk["gauge_iy"]), int(mk["gauge_ix"])
mask6 = basin == 6; mask665 = np.isin(basin, [6, 65])

ro = xr.open_dataset(f"{ROF}/roff_{YEAR}.nc")["ro"].load().values   # (t, 180, 360), lat north->south
if len(sys.argv) > 3 and sys.argv[3] == "clip":
    print("NEGATIVE RUNOFF CLIPPED TO 0", flush=True); ro = np.maximum(ro, 0)
assert ro.shape[1:] == (NYIN, NXIN)

def rin_exact(mask):
    cells = np.flatnonzero(mask.ravel())
    R = np.zeros(ro.shape[0])
    for k in range(INPN):
        ix = INPX[k].ravel()[cells]; iy = INPY[k].ravel()[cells]; a = INPA[k].ravel()[cells]
        ok = (ix > 0) & (iy > 0) & (a > 0)
        R += (ro[:, iy[ok] - 1, ix[ok] - 1] * a[ok][None]).sum(1)
    return R / 1000.0    # mm/s -> m/s  (DROFUNIT=1000)

def budget(mask, outcells, label):
    rows = np.flatnonzero(mask.any(1)); cols = np.flatnonzero(mask.any(0))
    r0, r1, c0, c1 = rows[0], rows[-1] + 1, cols[0], cols[-1] + 1
    m = mask[r0:r1, c0:c1]; oc = outcells[r0:r1, c0:c1]
    rd = lambda var, yr: xr.open_dataset(f"{OUT}/{var}/o_{var}{yr}.nc")[var].isel(lat=slice(r0, r1), lon=slice(c0, c1))
    sto = rd("storge", YEAR).load().values; sto0 = rd("storge", YEAR - 1).isel(time=-1).load().values
    S = np.concatenate([[np.nansum(np.where(m, sto0, 0))], np.nansum(np.where(m[None], sto, 0), axis=(1, 2))])
    dS = np.diff(S)
    Qout = np.nansum(np.where(oc[None], rd("outflw", YEAR).load().values, 0), axis=(1, 2))
    Rin = rin_exact(mask)
    n = min(len(Rin), len(Qout), len(dS)); Rin, Qout, dS = Rin[:n], Qout[:n], dS[:n]
    res = (Rin - Qout) * 86400 - dS; scale = Rin.mean() * 86400
    print(f"\n=== {label}: {mask.sum()} cells, {ctmare[mask].sum()/1e12:.3f} Mkm2, {outcells.sum()} outlet cells ===", flush=True)
    print(f"mean Rin {Rin.mean():.0f}  mean Qout {Qout.mean():.0f}  peak Qout {Qout.max():.0f} (day {np.argmax(Qout)+1}) m3/s", flush=True)
    print(f"daily mean|res|/scale = {np.mean(np.abs(res))/scale:.4f}   bias = {np.mean(res)/scale:+.4f}", flush=True)
    tot = (Rin.sum() - Qout.sum()) * 86400 - (S[n] - S[0])
    print(f"annual residual = {tot:.3e} m3 ({tot/(Rin.sum()*86400)*100:+.2f}% of inflow)", flush=True)
    np.savez_compressed(f"{RES}/closure_exact_{label}_{MEM}_{YEAR}.npz", Rin=Rin, Qout=Qout, dS=dS, S=S, res=res)

oc = np.zeros_like(mask_sub); oc[giy, gix] = True
budget(mask_sub, oc, "subbasin_gauge")
budget(mask665, mask665 & (nextx == -9), "basin6_65")
budget(mask6, mask6 & (nextx == -9), "basin6")
