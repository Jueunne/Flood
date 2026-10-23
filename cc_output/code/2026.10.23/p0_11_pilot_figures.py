"""P0 pilot aggregation + figures (Mississippi, 10 members, 1952-81 vs 2071-2100).

Fig A  source map: mean fractional contribution per cell (past / future / diff), centroid + shift km
Fig B  bottleneck map: frequency a cell is among the earliest capacity-crossing river cells (past / future / diff)
Fig C  summary: tributary shares past vs future, gauge annual-max change, centroid shifts
Usage: python -u p0_11_pilot_figures.py [UPAREA_MIN_KM2=10000]
"""
import glob, os, sys
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, TwoSlopeNorm

UPMIN = float(sys.argv[1]) if len(sys.argv) > 1 else 10000.0   # km2, river cells considered for bottleneck
TAG = "" if UPMIN == 10000.0 else f"_up{int(UPMIN/1000)}k"
MAP = "/data2/juen/RS12_handoff/map/glb_15min"
RES = "/home/juen0828/RS12_Flood_origin/cc_output/result/2026.10.23"; PIL = f"{RES}/pilot"
NX, NY = 1440, 720
lon = -179.875 + 0.25 * np.arange(NX); lat = 89.875 - 0.25 * np.arange(NY)
nextx, nexty = np.fromfile(f"{MAP}/nextxy.bin", dtype="<i4").reshape(2, NY, NX)
uparea = np.fromfile(f"{MAP}/uparea.bin", dtype="<f4").reshape(NY, NX); ctmare = np.fromfile(f"{MAP}/ctmare.bin", dtype="<f4").reshape(NY, NX)
mk = np.load(f"{RES}/mississippi_gauge_mask.npz"); mask = mk["mask"]; giy, gix = int(mk["gauge_iy"]), int(mk["gauge_ix"])
cells = np.flatnonzero(mask.ravel()); nc = len(cells)
cy, cx = cells // NX, cells % NX; clat, clon = lat[cy], lon[cx]
up_km2 = uparea.ravel()[cells] / 1e6
river = up_km2 >= UPMIN

# ---- tributary labelling: main stem = path of max-uparea upstream from gauge; tributary = subtree joining main stem
down = np.full(NY * NX, -1, np.int64); v = nextx > 0; down[np.flatnonzero(v)] = (nexty[v] - 1) * NX + (nextx[v] - 1)
gcell = giy * NX + gix
up_of = {}
for c in cells:
    d = down[c]
    if d >= 0 and mask.ravel()[d]: up_of.setdefault(d, []).append(c)
stem = [gcell]
while True:
    ups = up_of.get(stem[-1], [])
    if not ups: break
    stem.append(max(ups, key=lambda c: uparea.ravel()[c]))
stem_set = set(stem)
# each main-stem cell: side tributaries entering it (not the stem continuation)
trib_root = {}
for s in stem:
    for u in up_of.get(s, []):
        if u not in stem_set: trib_root[u] = s
# label each cell by the tributary root it drains through (or 'stem' if on stem / direct)
label = np.full(nc, -1, np.int64); root_of_cell = {}
idx = {c: i for i, c in enumerate(cells)}
for i, c in enumerate(cells):
    x = c; path = []
    while x not in stem_set and x not in root_of_cell:
        path.append(x); x = down[x]
    r = x if x in stem_set else root_of_cell[x]
    if x in stem_set: r = path[-1] if path else -1          # last cell before stem = tributary root
    for p in path: root_of_cell[p] = r
    label[i] = r
roots, counts = np.unique(label[label >= 0], return_counts=True)
root_up = np.array([uparea.ravel()[r] for r in roots]) / 1e6
top = roots[np.argsort(-root_up)[:6]]
known = {"Ohio": (37.0, -89.1), "Missouri": (38.8, -90.1), "Upper Mississippi": (38.8, -90.1), "Arkansas": (33.9, -91.1), "White": (34.0, -91.1), "Illinois": (38.9, -90.4)}
def name_root(r):
    la, lo = lat[r // NX], lon[r % NX]; j = down[r]; jla, jlo = lat[j // NX], lon[j % NX]
    return f"trib@({jla:.1f}N,{abs(jlo):.1f}W) {uparea.ravel()[r]/1e12:.2f}Mkm2"

# ---- load per member-year results
def load(period):
    y0, y1 = period
    files = sorted(glob.glob(f"{PIL}/LE2-*_[0-9]*.npz"))
    C, F, E, Qmax, pk, ratio, mem = [], [], [], [], [], [], []
    for f in files:
        y = int(f.split("_")[-1][:4])
        if not (y0 <= y <= y1): continue
        d = np.load(f)
        C.append(d["C"] / d["C"].sum()); F.append(d["first"]); E.append(d["exceed_any"]); Qmax.append(d["Q"][d["pk"]]); pk.append(d["pk"]); ratio.append(d["Vwin"] and d["C"].sum() / d["Vwin"])
        mem.append(os.path.basename(f).split("_")[0])
    return dict(C=np.array(C), F=np.array(F), E=np.array(E), Qmax=np.array(Qmax), pk=np.array(pk), ratio=np.array(ratio), mem=np.array(mem))
P = load((1952, 1981)); Fu = load((2071, 2100))
print(f"loaded past {len(P['C'])} / future {len(Fu['C'])} member-years; main-stem cells {len(stem)}; river cells (>= {UPMIN:.0f} km2) {river.sum()}", flush=True)
print(f"fixed-tau closure sumC/Vwin: past {P['ratio'].mean():.3f}+-{P['ratio'].std():.3f}, future {Fu['ratio'].mean():.3f}+-{Fu['ratio'].std():.3f}", flush=True)

def centroid(w):
    w = w / w.sum(); return (w * clat).sum(), (w * clon).sum()
def km(a, b):
    R = 6371.0; p1, p2 = np.radians(a[0]), np.radians(b[0]); dl = np.radians(b[1] - a[1])
    return R * np.arccos(np.clip(np.sin(p1) * np.sin(p2) + np.cos(p1) * np.cos(p2) * np.cos(dl), -1, 1))

# ---- source
Cp, Cf = P["C"].mean(0), Fu["C"].mean(0)
cp, cf = centroid(Cp), centroid(Cf)
# per-member centroid for spread
def member_centroids(D):
    out = []
    for m in np.unique(D["mem"]):
        out.append(centroid(D["C"][D["mem"] == m].mean(0)))
    return np.array(out)
mcp, mcf = member_centroids(P), member_centroids(Fu)
src_shift = km(cp, cf)
print(f"SOURCE centroid past ({cp[0]:.2f}N,{abs(cp[1]):.2f}W) -> future ({cf[0]:.2f}N,{abs(cf[1]):.2f}W): shift {src_shift:.0f} km "
      f"(member spread past lat sd {mcp[:,0].std():.2f}, lon sd {mcp[:,1].std():.2f})", flush=True)
# tributary shares
print("tributary shares (% of peak-window water), past -> future:", flush=True)
trib_rows = []
for r in top:
    sel = label == r
    sp, sf = 100 * Cp[sel].sum(), 100 * Cf[sel].sum()
    sp_m = np.array([100 * P["C"][P["mem"] == m].mean(0)[sel].sum() for m in np.unique(P["mem"])])
    sf_m = np.array([100 * Fu["C"][Fu["mem"] == m].mean(0)[sel].sum() for m in np.unique(Fu["mem"])])
    trib_rows.append((name_root(r), sp, sf, sp_m.std(), sf_m.std()))
    print(f"  {name_root(r):42s} {sp:5.1f}% -> {sf:5.1f}%  (member sd {sp_m.std():.1f}/{sf_m.std():.1f})", flush=True)
sel = label < 0; print(f"  {'main stem + direct':42s} {100*Cp[sel].sum():5.1f}% -> {100*Cf[sel].sum():5.1f}%", flush=True)

# ---- bottleneck: among river cells, earliest crossing day per member-year; cells crossing on that day (ties) get credit
def bottleneck_freq(D):
    freq = np.zeros(nc); nyr = 0
    for F in D["F"]:
        f = F.astype(float); f[~river | (F < 0)] = np.nan
        if np.all(np.isnan(f)): continue
        d0 = np.nanmin(f); hit = (f == d0); freq[hit] += 1.0 / hit.sum(); nyr += 1
    return freq / max(nyr, 1), nyr
Bp, nyp = bottleneck_freq(P); Bf, nyf = bottleneck_freq(Fu)
bp, bf = centroid(Bp + 1e-12), centroid(Bf + 1e-12); bn_shift = km(bp, bf)
print(f"BOTTLENECK (earliest crossing among river cells) years with a crossing: past {nyp}/{len(P['F'])}, future {nyf}/{len(Fu['F'])}", flush=True)
print(f"BOTTLENECK centroid past ({bp[0]:.2f}N,{abs(bp[1]):.2f}W) -> future ({bf[0]:.2f}N,{abs(bf[1]):.2f}W): shift {bn_shift:.0f} km", flush=True)
# exceedance-anywhere-in-window frequency (softer)
Ep, Ef = P["E"].mean(0), Fu["E"].mean(0)
# top bottleneck cells
for nm, B in (("past", Bp), ("future", Bf)):
    o = np.argsort(-B)[:5]
    print(f"  top {nm}: " + "; ".join(f"({clat[i]:.2f}N,{abs(clon[i]):.2f}W) {100*B[i]:.1f}% up={up_km2[i]/1e3:.0f}k km2" for i in o), flush=True)

# ---- magnitude
dQ = 100 * (Fu["Qmax"].mean() / P["Qmax"].mean() - 1)
print(f"GAUGE annual-max Q: past {P['Qmax'].mean():.0f} -> future {Fu['Qmax'].mean():.0f} m3/s ({dQ:+.1f}%); peak day-of-year past {P['pk'].mean()+1:.0f} -> future {Fu['pk'].mean()+1:.0f}", flush=True)

# ---- maps
def grid(vals):
    g = np.full((NY, NX), np.nan); g.ravel()[cells] = vals; return g[cy.min():cy.max()+1, cx.min():cx.max()+1]
ext = [lon[cx.min()] - 0.125, lon[cx.max()] + 0.125, lat[cy.max()] - 0.125, lat[cy.min()] + 0.125]
def panel3(A, B, title, fname, cmap="viridis", log=True, unit="", pts=None):
    fig, ax = plt.subplots(1, 3, figsize=(16, 5))
    vmax = np.nanpercentile(np.concatenate([A, B]), 99.5); vmin = max(np.nanmin(np.concatenate([A, B])[np.concatenate([A, B]) > 0]), vmax * 1e-3)
    norm = LogNorm(vmin, vmax) if log else None
    for k, (V_, nm) in enumerate(((A, "past 1952-81"), (B, "future 2071-2100"))):
        im = ax[k].imshow(grid(V_), extent=ext, cmap=cmap, norm=norm, vmin=None if log else 0, vmax=None if log else vmax, interpolation="nearest")
        ax[k].set_title(nm); plt.colorbar(im, ax=ax[k], shrink=0.8, label=unit)
    D = B - A; lim = np.nanpercentile(np.abs(D), 99.5)
    im = ax[2].imshow(grid(D), extent=ext, cmap="RdBu_r", norm=TwoSlopeNorm(0, -lim, lim), interpolation="nearest"); ax[2].set_title("future - past"); plt.colorbar(im, ax=ax[2], shrink=0.8, label=unit)
    if pts:
        for k in range(3):
            ax[k].plot(pts[0][1], pts[0][0], "o", mfc="none", mec="k", ms=10, mew=2, label="centroid past")
            ax[k].plot(pts[1][1], pts[1][0], "s", mfc="none", mec="r", ms=10, mew=2, label="centroid future")
            ax[k].plot(lon[gix], lat[giy], "k^", ms=8, label="gauge 32.1N")
        ax[0].legend(loc="lower left", fontsize=8)
    for a in ax: a.set_xlabel("lon"); a.set_ylabel("lat")
    fig.suptitle(title); fig.tight_layout(); fig.savefig(fname, dpi=130); plt.close(fig); print("saved", fname, flush=True)

panel3(Cp, Cf, f"Source of gauge peak water (fraction of peak-window volume per cell), 10 members; centroid shift {src_shift:.0f} km",
       f"{RES}/pilot_figA_source_map{TAG}.png", unit="fraction", pts=(cp, cf))
panel3(Bp, Bf, f"Bottleneck: frequency of being the earliest capacity-crossing river cell (>= {UPMIN:.0f} km2) in the 10 d before the peak; centroid shift {bn_shift:.0f} km",
       f"{RES}/pilot_figB_bottleneck_map{TAG}.png", cmap="magma", unit="fraction of years", pts=(bp, bf))
panel3(Ep, Ef, "Softer view: fraction of years a cell exceeds channel capacity at any time in the 10 d before the peak (all cells)",
       f"{RES}/pilot_figB2_exceed_any_map{TAG}.png", cmap="magma", log=False, unit="fraction of years")

# ---- summary fig
fig, ax = plt.subplots(1, 3, figsize=(16, 4.5))
names = [r[0].split(" ")[0] for r in trib_rows]; x = np.arange(len(trib_rows))
ax[0].bar(x - 0.2, [r[1] for r in trib_rows], 0.4, yerr=[r[3] for r in trib_rows], label="past", color="#888"); ax[0].bar(x + 0.2, [r[2] for r in trib_rows], 0.4, yerr=[r[4] for r in trib_rows], label="future", color="#F3722C")
ax[0].set_xticks(x); ax[0].set_xticklabels(names, rotation=30, ha="right", fontsize=8); ax[0].set_ylabel("% of peak-window water"); ax[0].legend(); ax[0].set_title("Tributary share of gauge peak water")
ax[1].hist(P["Qmax"] / 1e3, bins=20, alpha=.6, label=f"past mean {P['Qmax'].mean()/1e3:.1f}k"); ax[1].hist(Fu["Qmax"] / 1e3, bins=20, alpha=.6, label=f"future mean {Fu['Qmax'].mean()/1e3:.1f}k")
ax[1].set_xlabel("annual max Q at gauge (10^3 m3/s)"); ax[1].legend(); ax[1].set_title(f"Magnitude change {dQ:+.1f}%")
ax[2].scatter(mcp[:, 1], mcp[:, 0], c="k", label="source centroid, per member (past)"); ax[2].scatter(mcf[:, 1], mcf[:, 0], c="r", marker="s", label="future")
ax[2].plot([cp[1], cf[1]], [cp[0], cf[0]], "k-", lw=2); ax[2].plot(bp[1], bp[0], "ko", mfc="none", ms=12, mew=2, label="bottleneck centroid past"); ax[2].plot(bf[1], bf[0], "rs", mfc="none", ms=12, mew=2, label="bottleneck future")
ax[2].set_xlabel("lon"); ax[2].set_ylabel("lat"); ax[2].legend(fontsize=7); ax[2].set_title(f"Shifts: source {src_shift:.0f} km, bottleneck {bn_shift:.0f} km")
fig.tight_layout(); fig.savefig(f"{RES}/pilot_figC_summary{TAG}.png", dpi=130); print("saved figC", flush=True)
np.savez_compressed(f"{RES}/pilot_summary{TAG}.npz", Cp=Cp, Cf=Cf, Bp=Bp, Bf=Bf, Ep=Ep, Ef=Ef, cells=cells, label=label, stem=np.array(stem),
                    src_shift=src_shift, bn_shift=bn_shift, dQ=dQ, Qmax_p=P["Qmax"], Qmax_f=Fu["Qmax"], pk_p=P["pk"], pk_f=Fu["pk"])
