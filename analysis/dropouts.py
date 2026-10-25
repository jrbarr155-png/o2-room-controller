import datetime as dt, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
rows=[l.strip().split(",") for l in open("../data/2026-10-23_1138_fill_02.csv") if l.strip() and not l.startswith(("#","time"))]
T=dt.datetime.fromisoformat
ts=np.array([T(r[0]) for r in rows]); a=np.array([float(r[2] or "nan") for r in rows]); b=np.array([float(r[3] or "nan") for r in rows])
base=(ts>=T("2026-10-23T11:42:00"))&(ts<T("2026-10-23T11:56:00"))
rise=((a-np.nanmean(a[base]))+(b-np.nanmean(b[base])))/2
t0=T("2026-10-23T11:56:51"); tm=np.array([(x-t0).total_seconds()/60 for x in ts])
m=(tm>=-10)&(tm<=183)
sm=np.convolve(rise,np.ones(30)/30,mode="same")
V,QL,QM=59.7,0.37,0.010
edges=np.arange(0,180,10); sup=[]
for e in edges:
    w=(tm>=e)&(tm<e+10)
    p=np.polyfit(tm[w],rise[w],1); slope=p[0]; C=np.nanmean(rise[w])
    sup.append(V*slope+QL*C)   # %*m3/min of extra O2 delivered
sup=np.array(sup); norm=sup/np.median(sup[:6])
fig,(ax,bx)=plt.subplots(2,1,figsize=(10,6),sharex=True,gridspec_kw=dict(height_ratios=[1.4,1]))
ax.plot(tm[m],sm[m],color="#1f77b4",lw=1.6); ax.axhline(0,color="#999",lw=0.7,ls=":")
ax.set_ylabel("room O2 rise above\nbaseline (% points)")
ax.set_title("fill_02 (Oct 23, 10 L/min): the room's O2 fell twice while the machine was supposedly on",fontsize=11)
bad=norm<0.4
for e,bd in zip(edges,bad):
    if bd:
        for x in (ax,bx): x.axvspan(e,e+10,color="#d62728",alpha=0.12,lw=0)
cols=["#d62728" if bd else "#1f77b4" for bd in bad]
bx.bar(edges+5,100*norm,width=8.5,color=cols)
bx.axhline(100,color="#999",lw=0.7,ls=":")
bx.set_ylabel("O2 supply, worked backwards\n(% of normal)"); bx.set_xlabel("minutes after the tube was connected")
for x in (ax,bx): x.spines[["top","right"]].set_visible(False)
bx.set_title("supply = V·dC/dt + Q_leak·(C − C_out), each 10-min window, leak rate from the same-day decay",fontsize=9,color="#444",loc="left")
fig.tight_layout(); fig.savefig("18_supply_dropouts.png",dpi=160)
print(np.round(100*norm))
