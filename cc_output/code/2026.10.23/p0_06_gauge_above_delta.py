"""Closure at a main-stem gauge above the first delta bifurcation (~32N), plus figure."""
import numpy as np, xarray as xr, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
MEM="LE2-1031.002"; YEAR=1952
MAP="/data2/juen/RS12_handoff/map/glb_15min"
OUT=f"/data2/juen/CaMa-output/cesm/{MEM}"; RES="/home/juen0828/RS12_Flood_origin/cc_output/result/2026.10.23"
NX,NY,INPN=1440,720,7; lon=-179.875+0.25*np.arange(NX); lat=89.875-0.25*np.arange(NY)
nxy=np.fromfile(f"{MAP}/nextxy.bin",dtype="<i4").reshape(2,NY,NX); nextx,nexty=nxy
basin=np.fromfile(f"{MAP}/basin.bin",dtype="<i4").reshape(NY,NX); ctmare=np.fromfile(f"{MAP}/ctmare.bin",dtype="<f4").reshape(NY,NX)
uparea=np.fromfile(f"{MAP}/uparea.bin",dtype="<f4").reshape(NY,NX)
raw=np.fromfile(f"{MAP}/inpmat_1deg_nc.bin",dtype="<i4").reshape(3*INPN,NY,NX); INPX=raw[:INPN]; INPY=raw[INPN:2*INPN]; INPA=raw[2*INPN:].view("<f4")
down=np.full(NY*NX,-1,np.int64); v=nextx>0; down[np.flatnonzero(v)]=(nexty[v]-1)*NX+(nextx[v]-1)
src=np.argsort(down); ds_=down[src]
def upstream(cell):
    up=np.zeros(NY*NX,bool); up[cell]=True; front=[cell]
    while front:
        nxt=[]
        for f in front:
            lo,hi=np.searchsorted(ds_,f,"left"),np.searchsorted(ds_,f,"right"); c=src[lo:hi]; c=c[~up[c]]; up[c]=True; nxt.extend(c.tolist())
        front=nxt
    return up.reshape(NY,NX)
bif=np.loadtxt(f"{MAP}/bifprm.txt",skiprows=1); pix,piy,pjx,pjy=[bif[:,k].astype(int)-1 for k in range(4)]
for lo_,hi_ in [(31.9,32.6)]:   # 32.125N gauge, 99.6% of basin 6 (3 floodplain bifurcation paths cross but carry ~0)
    band=(basin==6)&(lat[:,None]>lo_)&(lat[:,None]<hi_)
    giy,gix=np.unravel_index(np.argmax(np.where(band,uparea,-1)),uparea.shape)
    m=upstream(giy*NX+gix); ncross=np.sum(m[piy,pix]!=m[pjy,pjx])
    print(f"gauge lat={lat[giy]:.3f} lon={lon[gix]:.3f} uparea={uparea[giy,gix]/1e12:.3f} Mkm2 ({uparea[giy,gix]/uparea[basin==6].max()*100:.1f}% of basin 6), cells={m.sum()}, bifurcation crossings={ncross}",flush=True)
    if ncross==0: break
rows=np.flatnonzero(m.any(1)); cols=np.flatnonzero(m.any(0)); r0,r1,c0,c1=rows[0],rows[-1]+1,cols[0],cols[-1]+1
rd=lambda var,yr: xr.open_dataset(f"{OUT}/{var}/o_{var}{yr}.nc")[var].isel(lat=slice(r0,r1),lon=slice(c0,c1))
ms=m[r0:r1,c0:c1]; sto=rd("storge",YEAR).load().values; sto0=rd("storge",YEAR-1).isel(time=-1).load().values
S=np.concatenate([[np.nansum(np.where(ms,sto0,0))],np.nansum(np.where(ms[None],sto,0),axis=(1,2))]); dS=np.diff(S)
Qout=rd("outflw",YEAR).load().values[:,giy-r0,gix-c0]
ro=np.maximum(xr.open_dataset(f"/data1/juen/CaMa-input/CESM2_roff/{MEM}/roff_{YEAR}.nc")["ro"].load().values,0)
cells=np.flatnonzero(m.ravel()); Rin=np.zeros(ro.shape[0])
for k in range(INPN):
    ix=INPX[k].ravel()[cells]; iy=INPY[k].ravel()[cells]; a=INPA[k].ravel()[cells]; ok=(ix>0)&(iy>0)&(a>0)
    Rin+=(ro[:,iy[ok]-1,ix[ok]-1]*a[ok][None]).sum(1)
Rin/=1000.0; n=len(Qout); res=(Rin-Qout)*86400-dS; scale=Rin.mean()*86400
print(f"mean Rin {Rin.mean():.0f} mean Qout {Qout.mean():.0f} peak Qout {Qout.max():.0f} m3/s (day {np.argmax(Qout)+1}); daily mean|res|/scale={np.mean(np.abs(res))/scale:.2e}; annual resid={((Rin.sum()-Qout.sum())*86400-(S[n]-S[0]))/(Rin.sum()*86400)*100:+.4f}%",flush=True)
np.savez_compressed(f"{RES}/mississippi_gauge_mask.npz",mask=m,gauge_iy=giy,gauge_ix=gix,lat=lat,lon=lon)
d=np.arange(1,n+1); fig,ax=plt.subplots(2,1,figsize=(10,6),sharex=True)
ax[0].plot(d,Rin,label="basin runoff in (clipped, inpmat)"); ax[0].plot(d,Qout,label=f"outflw at gauge {lat[giy]:.2f}N {abs(lon[gix]):.2f}W"); ax[0].plot(d,dS/86400,label="dS/dt (storge)")
ax[0].set_ylabel("m$^3$/s"); ax[0].legend(); ax[0].set_title(f"Mississippi above delta bifurcation, {MEM}, {YEAR}: water balance closes")
ax[1].plot(d,res/scale,c="k"); ax[1].set_ylabel("residual / mean inflow"); ax[1].set_xlabel("day of year"); ax[1].set_ylim(-0.01,0.01)
fig.tight_layout(); fig.savefig(f"{RES}/mass_closure_gauge_{MEM}_{YEAR}.png",dpi=120); print("saved fig",flush=True)
