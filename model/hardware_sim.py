"""
hardware_sim.py — SIMULATION of the real Oct 24 controller trials, using measured
hardware parameters instead of the original idealized ones.

Model (same mass balance as room_dynamics.py):
    V dC/dt = Qm*(Cs - C) - (Ql + Qdoor(t))*(C - Cout) - n_people*0.00025
Solved with a simple Euler step (dt = 2 s, same as the logger).

What is copied from the real system:
  - V = 59.7 m^3, Qm = 10 L/min, effective purity Cs ~ 79 % (measured, not 93 % spec)
  - leak rate Ql from the same-day decay (Oct 24: ~0.85 m^3/min); 0.62 also run
  - on/off valve, band L/H = baseline +0.40/+0.50, decided on a 60-s moving average
  - 30-s minimum between band switches
  - door opened 5 min after the valve switches to VENT at the high line, open 2 min
  - feedforward: valve to ROOM the instant the door opens, held 600 s after it shuts
  - door modeled as an extra leak Qdoor while open, sized from the measured
    open-door loss (~2.4 %*m^3/min at ~0.45 pts above baseline)

Metrics follow trial.py (t = 0 at door opening, 32-min window), except the dip is the
lowest point in the first 5 min so that ordinary band cycling later in the window is
not counted as door dip (it matters only in the stronger-machine what-if).
"""
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

V, QM, CS, COUT = 59.7, 0.010, 79.0, 21.06       # m^3, m^3/min, %, % (Oct 24 baseline)
L, H = COUT + 0.40, COUT + 0.50
DT = 2 / 60                                      # min
SMOOTH_N, MIN_SWITCH = 30, 0.5                   # samples (60 s), min
DOOR_DELAY, DOOR_OPEN, BOOST = 5.0, 2.0, 10.0    # min
QDOOR = 2.4 / 0.45                               # m^3/min extra exchange while open (~5.3)
PEOPLE = 1

def run(mode, ql, qm=QM, qdoor=QDOOR, settle=240, boost=BOOST, noise=0.0, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(0, settle + 160, DT); n = len(t)
    C = np.empty(n); C[0] = L; M = np.empty(n); M[0] = L; valve = np.zeros(n, bool); door = np.zeros(n, bool)
    buf, last_sw, v = [], -1e9, True
    door_t = None; armed = False
    for i in range(1, n):
        ti = t[i]
        # door schedule: arm after settling, open DOOR_DELAY after next high-line switch
        d = door_t is not None and door_t <= ti < door_t + DOOR_OPEN
        door[i] = d
        # controller (acts on 60-s average)
        buf.append(C[i-1] + rng.normal(0, noise)); buf = buf[-SMOOTH_N:]
        avg = np.mean(buf)
        if len(buf) == SMOOTH_N and ti - last_sw >= MIN_SWITCH:
            if avg < L and not v: v, last_sw = True, ti
            elif avg > H and v:
                v, last_sw = False, ti
                if ti > settle and door_t is None: door_t = ti + DOOR_DELAY
        on = v
        if mode == "ff" and door_t is not None and door_t <= ti < door_t + DOOR_OPEN + boost:
            on = True
        valve[i] = on
        q_in = qm if on else 0.0
        q_l = ql + (qdoor if d else 0.0)
        dC = (q_in * (CS - C[i-1]) - q_l * (C[i-1] - COUT) - PEOPLE * 0.00025 * 100) / V
        C[i] = C[i-1] + dC * DT
        M[i] = C[i] + rng.normal(0, noise)
    k0 = np.searchsorted(t, door_t); k1 = np.searchsorted(t, door_t + 32)
    tt, cc = t[k0:k1] - door_t, C[k0:k1]
    mm = np.convolve(M, np.ones(SMOOTH_N)/SMOOTH_N, mode="same")[k0:k1]   # 1-min avg of noisy reading
    pre = C[k0]; mid = (L + H) / 2
    on_idx = np.where(valve[k0:k1])[0]
    return dict(t=tt, C=cc, valve=valve[k0:k1], pre=pre,
                dip=pre - cc[tt < 5].min(),          # door dip: lowest point in first 5 min
                on_after=tt[on_idx[0]] if len(on_idx) else np.nan,
                below=(cc < L).sum() * DT,
                iae=np.abs(cc - mid).sum() * DT,
                iae_meas=np.abs(mm - mid).sum() * DT)

def boost_for(qm, ql=0.85):
    # boost formula from the protocol: O2 lost to the door / valve supply - door-open time
    lost = QDOOR * DOOR_OPEN * 0.45            # %*m^3
    supply = qm * (CS - (COUT + 0.45))         # %*m^3/min
    return max(lost / supply - DOOR_OPEN, 0.0)

def noisy(mode, ql, n=40, sigma=0.03):
    rs = [run(mode, ql, noise=sigma, seed=k) for k in range(n)]
    return {k: np.mean([r[k] for r in rs]) for k in ("dip", "below", "iae_meas", "on_after")}

MEAS = {"r": dict(dip=0.099, below=4.8, iae=1.24, on_after=1.9),
        "f": dict(dip=0.076, below=2.8, iae=1.15, on_after=0.0)}

if __name__ == "__main__":
    out = []
    def line(s): print(s); out.append(s)
    for ql in (0.85, 0.62):
        r, f = run("r", ql), run("ff", ql)
        line(f"\nSIMULATION, Ql = {ql} m^3/min (Cs = {CS} %, Qm = 10 L/min)")
        line(f"{'':22s}{'reactive':>10s}{'feedfwd':>10s}{'change':>9s}")
        for k, lab in [("on_after", "valve on after (min)"), ("dip", "dip (pts)"),
                       ("below", "below L (min)"), ("iae", "IAE (pt*min)")]:
            ch = "" if k == "on_after" else f"{100*(f[k]-r[k])/r[k]:+.0f}%"
            line(f"{lab:22s}{r[k]:10.3f}{f[k]:10.3f}{ch:>9s}")
    line("\nMEASURED (Oct 24, mean of 2 trials each)")
    for k in ("on_after", "dip", "below", "iae"):
        r, f = MEAS["r"][k], MEAS["f"][k]
        ch = "" if k == "on_after" else f"{100*(f-r)/r:+.0f}%"
        line(f"{k:22s}{r:10.3f}{f:10.3f}{ch:>9s}")
    nr, nf = noisy("r", 0.85), noisy("ff", 0.85)
    line("\nSIMULATION WITH SENSOR NOISE (sigma 0.03, 40 runs, Ql = 0.85), IAE computed on the noisy 1-min average like the real analysis")
    line(f"IAE  reactive {nr['iae_meas']:.3f}  feedforward {nf['iae_meas']:.3f}  change {100*(nf['iae_meas']-nr['iae_meas'])/nr['iae_meas']:+.0f}%")
    line(f"below L  reactive {nr['below']:.2f}  feedforward {nf['below']:.2f}")
    line("\nWHAT-IF (simulation, Ql = 0.85): stronger oxygen source, same room, boost resized with the protocol formula")
    line(f"{'flow':>8s}{'boost':>7s}{'dip r':>9s}{'dip ff':>9s}{'dip cut':>9s}{'IAE cut':>9s}")
    what = []
    for mult in (1, 2, 4, 8):
        r, f = run("r", 0.85, qm=QM*mult), run("ff", 0.85, qm=QM*mult, boost=boost_for(QM*mult))
        what.append((mult, r, f))
        line(f"{10*mult:6d} L{boost_for(QM*mult):6.1f}m{r['dip']:9.3f}{f['dip']:9.3f}{100*(r['dip']-f['dip'])/r['dip']:8.0f}%"
             f"{100*(r['iae']-f['iae'])/r['iae']:8.0f}%")
    open(__file__.replace(".py", "_results.txt"), "w").write("\n".join(out) + "\n")

    # ---- figure
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw=dict(width_ratios=[1.5, 1]))
    r, f = run("r", 0.85), run("ff", 0.85)
    a = ax[0]
    a.axvspan(0, DOOR_OPEN, color="#bbbbbb", alpha=0.35, lw=0)
    a.text(1.0, 0.012, "door open", ha="center", fontsize=9, color="#555")
    a.plot(r["t"], r["C"] - r["pre"], color="#d62728", lw=2.2, label="reactive (model)")
    a.plot(f["t"], f["C"] - f["pre"], color="#1f77b4", lw=2.2, label="feedforward (model)")
    a.axhline(-MEAS["r"]["dip"], color="#d62728", ls=":", lw=1.3)
    a.axhline(-MEAS["f"]["dip"], color="#1f77b4", ls=":", lw=1.3)
    a.text(31.5, -MEAS["r"]["dip"] + 0.003, "measured mean dip, reactive", ha="right", fontsize=8, color="#d62728")
    a.text(31.5, -MEAS["f"]["dip"] + 0.004, "measured mean dip, feedforward", ha="right", fontsize=8, color="#1f77b4")
    a.set_xlim(-1, 32); a.set_xlabel("minutes after door opens")
    a.set_ylabel("O2 change from pre-door level (% points)")
    a.set_title("Model prediction (measured room parameters) vs measured dips", fontsize=11)
    a.legend(loc="upper center", frameon=False, fontsize=9)
    a.set_ylim(-0.11, 0.03)
    a.spines[["top", "right"]].set_visible(False)
    b = ax[1]
    flows = [10*m for m, _, _ in what]
    cut = [100*(r_['dip']-f_['dip'])/r_['dip'] for _, r_, f_ in what]
    b.bar([str(x) for x in flows], cut, color=["#1f77b4"] + ["#9ecae1"]*3)
    for i, c in enumerate(cut): b.text(i, c + 1, f"{c:.0f}%", ha="center", fontsize=9)
    b.set_xlabel("concentrator flow (L/min)"); b.set_ylabel("dip reduction from feedforward (%)")
    b.set_title("Model prediction: benefit grows with oxygen supply", fontsize=11)
    b.text(0, -9, "my concentrator", ha="center", fontsize=8, color="#1f77b4")
    b.set_ylim(-12, max(cut) * 1.2); b.axhline(0, color="#999", lw=0.8)
    b.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(__file__.replace(".py", ".png"), dpi=160)
