import datetime as dt, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
rows=[l.strip().split(",") for l in open("../data/2026-10-24_1635_trials_01.csv") if l.strip() and not l.startswith(("#","time"))]
T=dt.datetime.fromisoformat
t0=T("2026-10-24T20:47:00"); t1=T("2026-10-24T20:56:00")
R=[r for r in rows if t0<=T(r[0])<=t1]
t=np.array([(T(r[0])-t0).total_seconds()/60 for r in R])
a=np.array([float(r[2]) if r[2] not in("","nan") else np.nan for r in R]); b=np.array([float(r[3]) if r[3] not in("","nan") else np.nan for r in R])
v=np.array([int(r[10]) for r in R]); reason=[r[12] for r in R]
sens=np.array([x=="sensor" for x in reason])
print(set(reason), np.nanmin(b), np.nanmax(b))
fig,(ax,bx)=plt.subplots(2,1,figsize=(10,5.2),sharex=True,gridspec_kw=dict(height_ratios=[3,1]))
ax.plot(t,a,color="#1f77b4",lw=1.4,label="sensor A")
bad=b<15
bb=b.copy(); bb[bad]=np.nan
ax.plot(t,bb,color="#ff7f0e",lw=1.4,label="sensor B")
ax.set_ylim(21.0,21.9)
if bad.any():
    ax.plot(t[bad],np.full(bad.sum(),21.02),"v",color="#ff7f0e",ms=3)
    ax.text(t[bad][0],21.05,"B reads ~0% (loose wire)",fontsize=8,color="#ff7f0e")
if sens.any():
    s0,s1=t[sens][0],t[sens][-1]
    for x in (ax,bx): x.axvspan(s0,s1,color="#d62728",alpha=0.12,lw=0)
    ax.text((s0+s1)/2,ax.get_ylim()[1],"sensor fault → valve forced to VENT\n(%.0f s)"%((s1-s0)*60),ha="center",va="top",fontsize=9,color="#d62728")
ax.set_ylabel("O2 reading (%)"); ax.legend(frameon=False,loc="lower left"); ax.spines[["top","right"]].set_visible(False)
ax.set_title("Kicked sensor B's wires during trial 4 (Oct 24, 20:50) — the safety rule caught it",fontsize=11)
bx.step(t,v,where="post",color="k"); bx.set_yticks([0,1]); bx.set_yticklabels(["VENT","ROOM"]); bx.set_xlabel("minutes after 20:47"); bx.spines[["top","right"]].set_visible(False)
fig.tight_layout(); fig.savefig("21_safety_kicked_wire.png",dpi=160)
