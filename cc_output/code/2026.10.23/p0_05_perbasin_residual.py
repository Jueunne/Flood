"""Per-basin budget residual (clipped runoff, exact inpmat) for every basin connected
to basin 6 by bifurcation. residual>0 = net export via bifurcation, <0 = net import."""
import numpy as np, xarray as xr
MEM="LE2-1031.002"; YEAR=1952
MAP="/data2/juen/RS12_handoff/map/glb_15min"
OUT=f"/data2/juen/CaMa-output/cesm/{MEM}"; RES="/home/juen0828/RS12_Flood_origin/cc_output/result/2026.10.23"
NX,NY,INPN=1440,720,7
nextx=np.fromfile(f"{MAP}/nextxy.bin",dtype="<i4").reshape(2,NY,NX)[0]
basin=np.fromfile(f"{MAP}/basin.bin",dtype="<i4").reshape(NY,NX); ctmare=np.fromfile(f"{MAP}/ctmare.bin",dtype="<f4").reshape(NY,NX)
raw=np.fromfile(f"{MAP}/inpmat_1deg_nc.bin",dtype="<i4").reshape(3*INPN,NY,NX); INPX=raw[:INPN]; INPY=raw[INPN:2*INPN]; INPA=raw[2*INPN:].view("<f4")
ro=np.maximum(xr.open_dataset(f"/data1/juen/CaMa-input/CESM2_roff/{MEM}/roff_{YEAR}.nc")["ro"].load().values,0)
basins=[int(b) for b in np.load(f"{RES}/masks_union_subbasin.npz")["basins"]]
mask_u=np.isin(basin,basins); rows=np.flatnonzero(mask_u.any(1)); cols=np.flatnonzero(mask_u.any(0))
r0,r1,c0,c1=rows[0],rows[-1]+1,cols[0],cols[-1]+1
rd=lambda var,yr: xr.open_dataset(f"{OUT}/{var}/o_{var}{yr}.nc")[var].isel(lat=slice(r0,r1),lon=slice(c0,c1)).load().values
sto=rd("storge",YEAR); sto0=xr.open_dataset(f"{OUT}/storge/o_storge{YEAR-1}.nc")["storge"].isel(time=-1,lat=slice(r0,r1),lon=slice(c0,c1)).load().values
of=rd("outflw",YEAR); bsub=basin[r0:r1,c0:c1]; nxsub=nextx[r0:r1,c0:c1]
# annual runoff per cell (m3) via inpmat
Rcell=np.zeros(NY*NX)
for k in range(INPN):
    ix=INPX[k].ravel(); iy=INPY[k].ravel(); a=INPA[k].ravel(); ok=(ix>0)&(iy>0)&(a>0)&mask_u.ravel()
    Rcell[ok]+=(ro[:,iy[ok]-1,ix[ok]-1].sum(0)*a[ok])
Rcell=(Rcell/1000.0*86400).reshape(NY,NX)[r0:r1,c0:c1]
print(f"{'basin':>6} {'Mkm2':>7} {'Rin km3':>9} {'Qout km3':>9} {'dS km3':>8} {'resid km3':>10} {'resid/Rin':>9}  mouth(lat,lon)")
tot=np.zeros(4); lat=89.875-0.25*np.arange(NY); lon=-179.875+0.25*np.arange(NX)
for b in basins:
    m=bsub==b; mo=m&(nxsub==-9)
    Rin=Rcell[m].sum(); Q=np.nansum(np.where(mo[None],of,0))*86400; dS=np.nansum(np.where(m,sto[-1],0))-np.nansum(np.where(m,sto0,0))
    res=Rin-Q-dS; tot+=[Rin,Q,dS,res]
    yy,xx=np.nonzero(mo); pos=f"({lat[r0+yy[0]]:.2f},{lon[c0+xx[0]]:.2f})" if len(yy) else "inland"
    print(f"{b:6d} {ctmare[basin==b].sum()/1e12:7.4f} {Rin/1e9:9.2f} {Q/1e9:9.2f} {dS/1e9:8.2f} {res/1e9:10.2f} {res/Rin if Rin>0 else np.nan:9.3f}  {pos}")
print(f"{'TOTAL':>6} {'':7} {tot[0]/1e9:9.2f} {tot[1]/1e9:9.2f} {tot[2]/1e9:8.2f} {tot[3]/1e9:10.2f} {tot[3]/tot[0]:9.3f}")
