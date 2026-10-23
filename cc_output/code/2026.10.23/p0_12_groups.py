"""Group source contributions by major sub-basin: Ohio, Upper Mississippi, Missouri, Arkansas, other (lower stem)."""
import numpy as np
MAP="/data2/juen/RS12_handoff/map/glb_15min"; RES="/home/juen0828/RS12_Flood_origin/cc_output/result/2026.10.23"
NX,NY=1440,720; lon=-179.875+0.25*np.arange(NX); lat=89.875-0.25*np.arange(NY)
nextx,nexty=np.fromfile(f"{MAP}/nextxy.bin",dtype="<i4").reshape(2,NY,NX); uparea=np.fromfile(f"{MAP}/uparea.bin",dtype="<f4").reshape(NY,NX)
down=np.full(NY*NX,-1,np.int64); v=nextx>0; down[np.flatnonzero(v)]=(nexty[v]-1)*NX+(nextx[v]-1)
S=np.load(f"{RES}/pilot_summary.npz"); cells=S["cells"]; stem=list(S["stem"]); Cp,Cf=S["Cp"],S["Cf"]
stem_idx={c:i for i,c in enumerate(stem)}
def near(la,lo): return min(stem,key=lambda c:(lat[c//NX]-la)**2+(lon[c%NX]-lo)**2)
conf_ohio=near(37.0,-89.1); conf_up=near(38.8,-90.1); conf_ark=near(33.9,-91.1)
print("stem confluence cells:", [(f"{lat[c//NX]:.2f}N",f"{abs(lon[c%NX]):.2f}W",stem_idx[c]) for c in (conf_ark,conf_ohio,conf_up)])
# entry: first stem cell reached; side: the cell just before entering
entry=np.zeros(len(cells),np.int64); side=np.zeros(len(cells),np.int64)
for i,c in enumerate(cells):
    x=c; prev=c
    while x not in stem_idx: prev=x; x=down[x]
    entry[i]=x; side[i]=prev
up_side=uparea.ravel()[side]
grp=np.full(len(cells),"other_lower_stem",dtype=object)
grp[(entry==conf_ohio)&(up_side>3e11)]="Ohio"
grp[(entry==conf_up)&(up_side>3e11)&(up_side<8e11)]="Upper Mississippi"
grp[(entry==conf_ark)&(up_side>3e11)]="Arkansas"
grp[np.array([stem_idx[e]>stem_idx[conf_up] for e in entry])]="Missouri"
grp[np.array([(c in stem_idx) and stem_idx[c]>stem_idx[conf_up] for c in cells])]="Missouri"
load=lambda p: None
import glob,os
def shares(y0,y1):
    out={}
    for f in sorted(glob.glob(f"{RES}/pilot/LE2-*_[0-9]*.npz")):
        y=int(f.split("_")[-1][:4]); 
        if not(y0<=y<=y1): continue
        m=os.path.basename(f).split("_")[0]; d=np.load(f); c=d["C"]/d["C"].sum()
        for g in np.unique(grp): out.setdefault(g,{}).setdefault(m,[]).append(c[grp==g].sum())
    return {g:np.array([np.mean(v) for v in d.values()]) for g,d in out.items()}
P=shares(1952,1981); F=shares(2071,2100)
print(f"{'group':20s} {'past%':>7s} {'future%':>8s} {'diff':>6s}  member-sd  (n members agreeing on sign)")
for g in ["Ohio","Upper Mississippi","Missouri","Arkansas","other_lower_stem"]:
    p,f=100*P[g],100*F[g]; print(f"{g:20s} {p.mean():7.1f} {f.mean():8.1f} {f.mean()-p.mean():+6.1f}  {p.std():.1f}/{f.std():.1f}  ({np.sum(np.sign(f-p)==np.sign(f.mean()-p.mean()))}/10)")
print("cells per group:", {g:int((grp==g).sum()) for g in np.unique(grp)})
np.save(f"{RES}/pilot_group_labels.npy", grp)
# bottleneck frequency by group (major rivers >=100k km2 and >=10k km2)
for tag in ["_up100k",""]:
    B=np.load(f"{RES}/pilot_summary{tag}.npz"); Bp,Bf=B["Bp"],B["Bf"]
    print(f"\nbottleneck share by group (earliest-crossing frequency summed over cells), rivers {'>=100k km2' if tag else '>=10k km2'}:")
    for g in ["Ohio","Upper Mississippi","Missouri","Arkansas","other_lower_stem"]:
        print(f"  {g:20s} past {100*Bp[grp==g].sum():5.1f}%  future {100*Bf[grp==g].sum():5.1f}%")
