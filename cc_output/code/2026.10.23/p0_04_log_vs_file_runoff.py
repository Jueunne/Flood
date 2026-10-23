"""Compare CaMa's own per-step runoff input (log: STONEW-STONXT, km3) with the
file-based global runoff (sum INPA*ro/1000*dt) for the first days of 1952."""
import re, numpy as np, xarray as xr
MEM="LE2-1031.002"; YEAR=1952
MAP="/data2/juen/RS12_handoff/map/glb_15min"
NX,NY,INPN=1440,720,7
raw=np.fromfile(f"{MAP}/inpmat_1deg_nc.bin",dtype="<i4").reshape(3*INPN,NY,NX)
INPX=raw[:INPN]; INPY=raw[INPN:2*INPN]; INPA=raw[2*INPN:].view("<f4")
ro=xr.open_dataset(f"/data1/juen/CaMa-input/CESM2_roff/{MEM}/roff_{YEAR}.nc")["ro"].isel(time=slice(0,10)).load().values
R=np.zeros(ro.shape[0])
for k in range(INPN):
    ix=INPX[k].ravel(); iy=INPY[k].ravel(); a=INPA[k].ravel(); ok=(ix>0)&(iy>0)&(a>0)
    R+=(ro[:,iy[ok]-1,ix[ok]-1]*a[ok][None]).sum(1)
R=R/1000.0*86400/1e9   # km3/day
pat=re.compile(r"^(\d{4}/\d{2}/\d{2})_(\d{2}):(\d{2})\s+(\d+) flx:\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)")
day={}; nstep={}
with open(f"/data2/juen/CaMa-work/cesm2_1deg/{MEM}/log_CaMa-{YEAR}.txt") as f:
    for line in f:
        m=pat.match(line)
        if not m: continue
        d=m.group(1); hh=int(m.group(2)); mm=int(m.group(3))
        # step stamped 24:00 belongs to that day; step at 00:00 next day? keep by date string
        stonxt=float(m.group(6)); stonew=float(m.group(7))
        day[d]=day.get(d,0.0)+(stonew-stonxt); nstep[d]=nstep.get(d,0)+1
        if len(day)>10: break
keys=sorted(day)[:10]
print("date        steps  log_runoff(km3)  file_runoff(km3)  ratio")
for i,d in enumerate(keys):
    print(f"{d}  {nstep[d]:5d}  {day[d]:14.4f}  {R[i]:16.4f}  {day[d]/R[i]:.4f}")
