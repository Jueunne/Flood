"""P0 pilot compute: per member-year source backtracking + bottleneck crossing.

Network-flow bookkeeping on the Mississippi above the 32.125N gauge.
  source  : C_i = sum_{k=-5..5} R_i(pk + k - tau_i) * 86400   [m3]  (fixed travel time tau_i = dist_i / v)
  bottleneck: ratio = storge / RIVSTOMAX, RIVSTOMAX = rivlen*rivwth_gwdlr*rivhgt;
              first day in [pk-10, pk] on which ratio crosses 1 from below, per cell.
Outputs one npz per member-year: result/2026.10.23/pilot/<member>_<year>.npz  (idempotent).
Usage: python -u p0_10_pilot_compute.py <member> <y0> <y1> [v_mps]
"""
import os, sys, time
import numpy as np
import xarray as xr

MEM = sys.argv[1]; Y0 = int(sys.argv[2]); Y1 = int(sys.argv[3])
V = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
MAP = "/data2/juen/RS12_handoff/map/glb_15min"
OUT = f"/data2/juen/CaMa-output/cesm/{MEM}"
ROF = f"/data1/juen/CaMa-input/CESM2_roff/{MEM}"
RES = "/home/juen0828/RS12_Flood_origin/cc_output/result/2026.10.23"
PIL = f"{RES}/pilot"; os.makedirs(PIL, exist_ok=True)
NX, NY, INPN = 1440, 720, 7
KWIN = 5      # +-days around peak for source window
BWIN = 10     # days before peak for bottleneck search

def rbin(name, dtype, nvar=1):
    a = np.fromfile(f"{MAP}/{name}.bin", dtype=dtype)
    return a.reshape(nvar, NY, NX) if nvar > 1 else a.reshape(NY, NX)
nextx, nexty = rbin("nextxy", "<i4", 2)
uparea = rbin("uparea", "<f4"); rivlen = rbin("rivlen", "<f4"); rivwth = rbin("rivwth_gwdlr", "<f4"); rivhgt = rbin("rivhgt", "<f4")
raw = np.fromfile(f"{MAP}/inpmat_1deg_nc.bin", dtype="<i4").reshape(3 * INPN, NY, NX)
INPX = raw[:INPN]; INPY = raw[INPN:2 * INPN]; INPA = raw[2 * INPN:].view("<f4")

mk = np.load(f"{RES}/mississippi_gauge_mask.npz")
mask = mk["mask"]; giy, gix = int(mk["gauge_iy"]), int(mk["gauge_ix"])
cells = np.flatnonzero(mask.ravel()); nc = len(cells)
gcell = giy * NX + gix
rows = np.flatnonzero(mask.any(1)); cols = np.flatnonzero(mask.any(0))
r0, r1, c0, c1 = rows[0], rows[-1] + 1, cols[0], cols[-1] + 1
sub_idx = (cells // NX - r0) * (c1 - c0) + (cells % NX - c0)     # index into bbox-flattened arrays

# ---- travel distance to gauge (m): process in descending uparea so downstream is done first
down = np.full(NY * NX, -1, np.int64); v = nextx > 0
down[np.flatnonzero(v)] = (nexty[v] - 1) * NX + (nextx[v] - 1)
dist = np.full(NY * NX, np.nan); dist[gcell] = 0.0
order = cells[np.argsort(-uparea.ravel()[cells])]
for c in order:
    if c == gcell: continue
    dist[c] = dist[down[c]] + rivlen.ravel()[c]
dist_c = dist[cells]; assert np.all(np.isfinite(dist_c))
tau = np.rint(dist_c / (V * 86400.0)).astype(int)           # days
rivstomax = (rivlen * rivwth * rivhgt).ravel()[cells].astype(np.float64)
ok_cap = rivstomax > 0

def runoff_cells(year):
    """daily runoff per mask cell [m3/s], CaMa recipe: clip<0, inpmat weights, /1000."""
    ro = np.maximum(xr.open_dataset(f"{ROF}/roff_{year}.nc")["ro"].load().values, 0)
    R = np.zeros((ro.shape[0], nc))
    for k in range(INPN):
        ix = INPX[k].ravel()[cells]; iy = INPY[k].ravel()[cells]; a = INPA[k].ravel()[cells]
        ok = (ix > 0) & (iy > 0) & (a > 0)
        R[:, ok] += ro[:, iy[ok] - 1, ix[ok] - 1] * a[ok][None]
    return R / 1000.0

def rd(var, year, tsel=None):
    da = xr.open_dataset(f"{OUT}/{var}/o_{var}{year}.nc")[var].isel(lat=slice(r0, r1), lon=slice(c0, c1))
    if tsel is not None: da = da.isel(time=tsel)
    return da.load().values

prev_R = None; prev_year = None
for year in range(Y0, Y1 + 1):
    fn = f"{PIL}/{MEM}_{year}.npz"
    if os.path.exists(fn):
        print(f"{MEM} {year} exists, skip", flush=True); continue
    t0 = time.time()
    # --- gauge hydrograph and peak
    Q = rd("outflw", year)[:, giy - r0, gix - c0]
    n = len(Q); pk = int(np.argmax(Q))
    # --- runoff: this year + previous year (for tau reach-back)
    R1 = runoff_cells(year)
    if prev_year == year - 1 and prev_R is not None: R0 = prev_R
    else:
        R0 = runoff_cells(year - 1) if os.path.exists(f"{ROF}/roff_{year-1}.nc") else np.full((365, nc), np.nan)
    Rcat = np.concatenate([R0, R1], 0); off = R0.shape[0]
    # --- source contribution
    C = np.zeros(nc); miss = 0
    for k in range(-KWIN, KWIN + 1):
        t = off + pk + k - tau                      # per-cell source day index
        bad = (t < 0) | (t >= Rcat.shape[0]); miss += bad.sum()
        tt = np.clip(t, 0, Rcat.shape[0] - 1)
        C += np.where(bad, 0.0, Rcat[tt, np.arange(nc)]) * 86400
    kk = np.arange(max(0, pk - KWIN), min(n, pk + KWIN + 1))
    Vwin = Q[kk].sum() * 86400
    # --- bottleneck: ratio in [pk-BWIN-1, pk]
    t_lo = pk - BWIN - 1
    if t_lo >= 0:
        S = rd("storge", year, slice(t_lo, pk + 1))
    else:
        Sp = rd("storge", year - 1, slice(t_lo, None)) if os.path.exists(f"{OUT}/storge/o_storge{year-1}.nc") else np.full((-t_lo,) + (r1 - r0, c1 - c0), np.nan, np.float32)
        S = np.concatenate([Sp, rd("storge", year, slice(0, pk + 1))], 0)
    S = S.reshape(S.shape[0], -1)[:, sub_idx]                 # (nt, nc)
    ratio = np.where(ok_cap[None], S / np.where(ok_cap, rivstomax, 1.0)[None], np.nan)
    above = ratio >= 1.0
    cross = above[1:] & ~above[:-1]                            # day j (1..) crosses from below
    first = np.full(nc, -1, np.int16)
    anyc = cross.any(0)
    first[anyc] = np.argmax(cross[:, anyc], 0)                 # 0 => day pk-BWIN
    exceed_any = above[1:].any(0)
    ratio_pk = ratio[-1].astype(np.float32)
    np.savez_compressed(fn, year=year, n=n, pk=pk, Q=Q.astype(np.float32), C=C.astype(np.float32), Vwin=Vwin,
                        miss=miss, first=first, exceed_any=exceed_any, ratio_pk=ratio_pk, tau=tau.astype(np.int16), V=V)
    print(f"{MEM} {year}: pk day {pk+1} Q={Q[pk]:.0f} m3/s, sumC/Vwin={C.sum()/Vwin:.3f}, cells crossing={anyc.sum()}, "
          f"exceed_any={exceed_any.sum()}, miss={miss}, {time.time()-t0:.0f}s", flush=True)
    prev_R, prev_year = R1, year
print("done", MEM, Y0, Y1, flush=True)
