"""Fig D: per-member tributary share of peak water, past vs future (slope chart) + snow-fed share per year."""
import glob, os, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
RES="/home/juen0828/RS12_Flood_origin/cc_output/result/2026.10.23"
g=np.load(f"{RES}/pilot_group_labels.npy",allow_pickle=True)
groups=["Ohio","other_lower_stem","Arkansas","Upper Mississippi","Missouri"]
names={"Ohio":"Ohio (rain)","other_lower_stem":"lower stem","Arkansas":"Arkansas","Upper Mississippi":"Upper Miss. (snow)","Missouri":"Missouri (snow)"}
files=sorted(glob.glob(f"{RES}/pilot/*.npz")); mems=sorted({os.path.basename(f).rsplit("_",1)[0] for f in files})
def shares(mem,y0,y1):
    C=np.zeros(len(g)); per=[]
    for y in range(y0,y1+1):
        d=np.load(f"{RES}/pilot/{mem}_{y}.npz"); c=d["C"].astype(float); C+=c
        per.append([c[g==k].sum()/c.sum() for k in groups])
    return np.array([C[g==k].sum()/C.sum() for k in groups]), np.array(per)
P=[];F=[];Pyr=[];Fyr=[]
for m in mems:
    a,ay=shares(m,1952,1981); b,by=shares(m,2071,2100); P.append(a);F.append(b);Pyr.append(ay);Fyr.append(by)
P=np.array(P)*100;F=np.array(F)*100;Pyr=np.array(Pyr)*100;Fyr=np.array(Fyr)*100
snow=[groups.index("Upper Mississippi"),groups.index("Missouri")]
sp=P[:,snow].sum(1); sf=F[:,snow].sum(1); syp=Pyr[:,:,snow].sum(2).ravel(); syf=Fyr[:,:,snow].sum(2).ravel()
fig,ax=plt.subplots(1,2,figsize=(11,5.2),gridspec_kw=dict(width_ratios=[1.3,1]))
cols={"Ohio":"#d7301f","Missouri":"#2b8cbe","Upper Mississippi":"#74a9cf","Arkansas":"#999999","other_lower_stem":"#bdbdbd"}
for j,k in enumerate(groups):
    for i in range(len(mems)):
        ax[0].plot([0,1],[P[i,j],F[i,j]],color=cols[k],alpha=.35,lw=1)
    ax[0].plot([0,1],[P[:,j].mean(),F[:,j].mean()],color=cols[k],lw=3,marker="o")
    ax[0].text(1.03,F[:,j].mean()+{"other_lower_stem":-1.6,"Missouri":0.8}.get(k,0),f"{names[k]}  {P[:,j].mean():.0f}→{F[:,j].mean():.0f}%",va="center",color=cols[k],fontsize=10)
ax[0].set_xticks([0,1]);ax[0].set_xticklabels(["1952–1981","2071–2100"]);ax[0].set_xlim(-0.15,1.9)
ax[0].set_ylabel("share of peak-day water at gauge (%)");ax[0].set_title("Where the flood peak water comes from\n(10 CESM2-LE members, thin = member, thick = mean)",fontsize=11)
ax[0].spines[["top","right"]].set_visible(False)
bins=np.arange(0,70,3)
ax[1].hist(syp,bins,alpha=.6,color="#2b8cbe",label=f"1952–1981 (mean {syp.mean():.0f}%)")
ax[1].hist(syf,bins,alpha=.6,color="#d7301f",label=f"2071–2100 (mean {syf.mean():.0f}%)")
ax[1].set_xlabel("snow-fed share (Upper Miss. + Missouri) of peak water, per year (%)");ax[1].set_ylabel("member-years (of 300)")
ax[1].legend(frameon=False);ax[1].set_title("Snow-fed tributaries lose a quarter of their share",fontsize=11)
ax[1].spines[["top","right"]].set_visible(False)
fig.suptitle("Mississippi at 32.1°N: flood size unchanged (+0%), origin moves from snow to rain tributaries",fontsize=12,y=1.0)
fig.tight_layout();fig.savefig(f"{RES}/pilot_figD_slope_snowshare.png",dpi=140,bbox_inches="tight")
print("members",len(mems),"snow share past %.1f±%.1f future %.1f±%.1f"%(sp.mean(),sp.std(),sf.mean(),sf.std()))
print("per-year snow share: past median %.1f, future median %.1f; frac years >40%%: past %.2f future %.2f"%(np.median(syp),np.median(syf),(syp>40).mean(),(syf>40).mean()))
print("frac years snow<20%%: past %.2f future %.2f"%((syp<20).mean(),(syf<20).mean()))
