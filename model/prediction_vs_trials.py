"""
prediction_vs_trials.py — the room model's prediction (thick lines, from hardware_sim.py,
built only from parameters measured in the fills, decay and flowmeter) drawn over the
four real Oct 24 door trials (thin lines, straight from the logger CSV).
Right panel: model what-if for stronger oxygen sources (cannot be tested with my hardware).
"""
import sys, datetime as dt, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import hardware_sim as h

CSV = sys.argv[1] if len(sys.argv) > 1 else "../data/2026-10-24_1635_trials_01.csv"
TRIALS = [("Trial 1", "r", "2026-10-24T18:16:50"), ("Trial 2", "f", "2026-10-24T19:13:11"),
          ("Trial 3", "r", "2026-10-24T20:00:10"), ("Trial 4", "f", "2026-10-24T21:20:52")]
RED, BLUE = "#d62728", "#1f77b4"

rows = [l.strip().split(",") for l in open(CSV)
        if l.strip() and not l.startswith("#") and not l.startswith("time")]
ts = np.array([dt.datetime.fromisoformat(r[0]) for r in rows])
o2 = np.array([float(r[9]) for r in rows])                      # o2_avg (A+B)/2
o2_1min = np.convolve(o2, np.ones(30) / 30, mode="same")         # 1-min average (2-s samples)

fig, ax = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw=dict(width_ratios=[1.6, 1]))
a = ax[0]
a.axvspan(0, h.DOOR_OPEN, color="#bbbbbb", alpha=0.35, lw=0)
a.text(1.0, -0.13, "door\nopen", ha="center", fontsize=9, color="#555")
for name, mode, t0 in TRIALS:
    t = np.array([(x - dt.datetime.fromisoformat(t0)).total_seconds() / 60 for x in ts])
    pre = o2[(t >= -5) & (t < 0)].mean()
    w = (t >= -3) & (t <= 32)
    a.plot(t[w], o2_1min[w] - pre, color=RED if mode == "r" else BLUE, lw=0.9, alpha=0.45)
r, f = h.run("r", 0.85), h.run("ff", 0.85)
a.plot(r["t"], r["C"] - r["pre"], color=RED, lw=3, label="reactive — model prediction")
a.plot(f["t"], f["C"] - f["pre"], color=BLUE, lw=3, label="feedforward — model prediction")
a.plot([], [], color=RED, lw=0.9, alpha=0.6, label="reactive — measured (trials 1, 3)")
a.plot([], [], color=BLUE, lw=0.9, alpha=0.6, label="feedforward — measured (trials 2, 4)")
a.axhline(0, color="#999", lw=0.6, ls=":")
a.set_xlim(-3, 32); a.set_ylim(-0.14, 0.17)
a.set_xlabel("minutes after the door opened")
a.set_ylabel("room O2 change from pre-door level (% points)")
a.set_title("Model prediction vs the four real door trials (Oct 24, 10 L/min)", fontsize=11)
a.legend(loc="upper right", frameon=False, fontsize=8.5, ncol=2)
a.spines[["top", "right"]].set_visible(False)

b = ax[1]
mults = (1, 2, 4, 8); cut = []
for m in mults:
    rr = h.run("r", 0.85, qm=h.QM * m); ff = h.run("ff", 0.85, qm=h.QM * m, boost=h.boost_for(h.QM * m))
    cut.append(100 * (rr["dip"] - ff["dip"]) / rr["dip"])
b.bar([str(10 * m) for m in mults], cut, color=[BLUE] + ["#9ecae1"] * 3)
for i, c in enumerate(cut): b.text(i, c + 1.5, f"{c:.0f}%", ha="center", fontsize=9)
b.text(0, -9, "my concentrator", ha="center", fontsize=8, color=BLUE)
b.set_ylim(-12, 120); b.axhline(0, color="#999", lw=0.8)
b.set_xlabel("concentrator flow (L/min)"); b.set_ylabel("dip reduction from feedforward (%)")
b.set_title("Model prediction: benefit grows with oxygen supply", fontsize=11)
b.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig("prediction_vs_trials.png", dpi=160)
