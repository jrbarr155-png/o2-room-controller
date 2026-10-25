"""
analyze_fill_decay.py — full analysis of a fill run that ends with a decay, in ONE log file.

This is the script that produced the fill_01 results (Oct 22, 2026). It is kept so every
number in results/fill_01_results.md can be re-created from the raw CSV.

Usage (from ~/Downloads/o2_lab):
    python3 analysis/analyze_fill_decay.py data/2026-10-22_2042_fill_01.csv \
        --baseline-start 20:45:30 --fill-start 20:57:57 --decay-start 23:00:44 \
        --volume 59.7 --lpm 5 --date 2026-10-22

Times are the clock times of the three markers (from the "?" settings lines / notes):
    baseline-start : tube disconnected, room at rest
    fill-start     : tube reconnected, O2 flowing into the room
    decay-start    : concentrator switched off

METHOD
  1. Baseline: each sensor's mean over the baseline window is taken as "outside air" and the
     sensor is re-referenced so that window reads 20.9 %. This cancels each sensor's own offset
     (they read 20.80 and 20.91 at rest — a 0.1 offset is a third of the whole signal).
  2. Room O2 = average of the two corrected sensors.
  3. Fill:  C(t) = Css + (C0 - Css) * exp(-t / tau)      (Css, tau, C0 all fitted)
            Ql from fill SPEED:  Ql = V / tau - Qm
            Ql from fill LEVEL:  Ql = Qm * (Cs - Css) / (Css - Cout)   (needs purity Cs)
  4. Decay: C(t) = Cout + (C0 - Cout) * exp(-t / tau_d)  (tau_d, C0 fitted; Cout fixed by baseline)
            Ql from decay:       Ql = V / tau_d
  5. Starting slope (first 20 min, straight line) vs the model's prediction Qm*(Cs-Cout)/V.
     The ratio gives the concentrator's EFFECTIVE purity: Cs_eff = Cout + slope*V/Qm.
"""
import argparse
import datetime as dt
import pathlib

import numpy as np
from scipy.optimize import curve_fit
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COUT = 20.9
SPEC_PURITY = 93.0


def load(path):
    rows = [l.strip().split(",") for l in open(path)
            if l.strip() and not l.startswith("#") and not l.startswith("time_iso")]
    ts = np.array([dt.datetime.fromisoformat(r[0]) for r in rows])
    a = np.array([float(r[2]) for r in rows])
    b = np.array([float(r[3]) for r in rows])
    temp = np.array([float(r[4]) for r in rows])
    door = np.array([int(r[6]) for r in rows])
    return ts, a, b, temp, door


def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("--date", required=True, help="YYYY-MM-DD of the baseline/fill start")
    p.add_argument("--baseline-start", required=True)
    p.add_argument("--fill-start", required=True)
    p.add_argument("--decay-start", default=None)
    p.add_argument("--volume", type=float, required=True)
    p.add_argument("--lpm", type=float, required=True)
    p.add_argument("--purity", type=float, default=SPEC_PURITY)
    a = p.parse_args()

    def at(hms):
        t = dt.datetime.fromisoformat(f"{a.date}T{hms}")
        return t

    ts, A, B, temp, door = load(a.csv)
    b0, f0 = at(a.baseline_start), at(a.fill_start)
    d0 = at(a.decay_start) if a.decay_start else None
    if d0 and d0 < f0:
        d0 += dt.timedelta(days=1)

    V, qm, cs = a.volume, a.lpm / 1000.0, a.purity
    base = (ts >= b0) & (ts < f0)
    ba, bb = A[base].mean(), B[base].mean()
    Ar, Br = A - ba + COUT, B - bb + COUT
    C = (Ar + Br) / 2
    tmin = np.array([(x - f0).total_seconds() / 60 for x in ts])

    out = []
    say = lambda s: (print(s), out.append(s))
    say(f"Run: {pathlib.Path(a.csv).name}")
    say(f"Volume {V} m^3, flow {a.lpm} L/min, assumed purity {cs}%")
    say(f"Baseline {a.baseline_start}-{a.fill_start}: sensor A {ba:.3f}%, sensor B {bb:.3f}% "
        f"(n={base.sum()}), noise (sd of 2-sensor avg) {C[base].std():.3f}")

    fill = (ts >= f0) & ((ts < d0) if d0 else True)
    tf, cf = tmin[fill], C[fill]
    fo = lambda t, css, tau, c0: css + (c0 - css) * np.exp(-t / tau)
    pf, cvf = curve_fit(fo, tf, cf, p0=[21.2, 80, 20.9], maxfev=20000)
    sf = np.sqrt(np.diag(cvf))
    css, tau, c0 = pf
    rms = np.sqrt(np.mean((cf - fo(tf, *pf)) ** 2))
    ql_tau = V / tau - qm
    ql_css = qm * (cs - css) / (css - COUT)
    say(f"FILL ({tf[-1]:.0f} min, door-open samples: {door[fill].sum()}, "
        f"temp {temp[fill].min():.1f}-{temp[fill].max():.1f} C)")
    say(f"  tau = {tau:.1f} ± {sf[1]:.1f} min   Css = {css:.3f} ± {sf[0]:.3f}%   C0 = {c0:.3f}%   "
        f"residual RMS {rms:.3f}")
    say(f"  rise above baseline at end of fill: {fo(tf[-1], *pf) - COUT:.3f}  (fitted plateau rise {css - COUT:.3f})")
    say(f"  Ql from fill speed (tau): {ql_tau:.3f} m^3/min  ({ql_tau * 60 / V:.2f} air changes/h)")
    say(f"  Ql from fill level (Css): {ql_css:.3f} m^3/min  ({ql_css * 60 / V:.2f} air changes/h)  "
        f"[depends on purity and on the extrapolated plateau]")
    m = tf < 20
    slope = np.polyfit(tf[m], cf[m], 1)[0]
    pred = qm * (cs - COUT) / V
    cs_eff = COUT + slope * V / qm
    say(f"  starting slope (0-20 min): {slope:.4f} %/min vs model {pred:.4f} %/min at {cs}% purity "
        f"-> ratio {slope / pred:.2f}, effective purity ~{cs_eff:.0f}%")
    lastAB = np.mean((Ar - Br)[fill][tf > tf[-1] - 30])
    say(f"  sensor A - sensor B, last 30 min of fill: {lastAB:+.3f} (well-mixed check)")

    pd = None
    if d0:
        dec = ts >= d0
        td0 = (d0 - f0).total_seconds() / 60
        td, cd = tmin[dec], C[dec]
        de = lambda t, taud, c0d: COUT + (c0d - COUT) * np.exp(-(t - td0) / taud)
        pd, cvd = curve_fit(de, td, cd, p0=[90, 21.15], maxfev=20000)
        sd = np.sqrt(np.diag(cvd))
        ql_dec = V / pd[0]
        say(f"DECAY ({td[-1] - td0:.0f} min, door-open samples: {door[dec].sum()})")
        say(f"  tau = {pd[0]:.1f} ± {sd[0]:.1f} min  ->  Ql = V/tau = {ql_dec:.3f} m^3/min "
            f"({ql_dec * 60 / V:.2f} air changes/h)")
        say(f"  fill-speed vs decay Ql agreement: "
            f"{100 * abs(ql_tau - ql_dec) / np.mean([ql_tau, ql_dec]):.0f}% difference")

    opens = [ts[i] for i in range(1, len(ts)) if door[i] == 1 and door[i - 1] == 0]
    say("Door openings logged: " + ", ".join(x.strftime("%H:%M:%S") for x in opens))

    # ---- plot ----
    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    k = tmin > (b0 - f0).total_seconds() / 60 + 2
    ax.plot(tmin[k], Ar[k], ".", ms=1.4, alpha=.22, color="#4C78A8", label="sensor A (desk)")
    ax.plot(tmin[k], Br[k], ".", ms=1.4, alpha=.22, color="#F58518", label="sensor B (chair, by door)")
    w = 60
    roll = np.convolve(C, np.ones(w) / w, mode="same")
    ax.plot(tmin[k][w:-w], roll[k][w:-w], color="black", lw=1.1, label="2-sensor average (2-min smoothed)")
    tt = np.linspace(0, tf[-1], 300)
    ax.plot(tt, fo(tt, *pf), color="#E45756", lw=2.4, label=f"fill fit: τ = {tau:.0f} min")
    if pd is not None:
        tt2 = np.linspace(td0, tmin[-1], 200)
        ax.plot(tt2, COUT + (pd[1] - COUT) * np.exp(-(tt2 - td0) / pd[0]), color="#54A24B", lw=2.4,
                label=f"decay fit: τ = {pd[0]:.0f} min")
        ax.axvline(td0, color="gray", ls="--", lw=1)
        ax.text(td0 + 0.8, 20.72, "concentrator off", fontsize=9, color="gray")
    ax.axvline(0, color="gray", ls="--", lw=1)
    ax.text(0.8, 20.72, "O2 into room", fontsize=9, color="gray")
    for x in opens:
        xm = (x - f0).total_seconds() / 60
        if xm > 0:
            ax.axvline(xm, color="#B279A2", lw=1)
            ax.text(xm + 0.8, 21.3, "door opened", fontsize=8.5, color="#B279A2")
    ax.axhline(COUT, color="gray", lw=.8, ls=":")
    ax.set_xlabel("minutes since O2 started flowing into the room")
    ax.set_ylabel("room O2 (%), baseline-corrected to 20.9")
    ax.set_title(f"{pathlib.Path(a.csv).stem} — {V} m³ room, {a.lpm:g} L/min concentrator, door shut")
    ax.set_ylim(20.7, max(21.35, float(np.nanmax(roll[k][w:-w])) + 0.1))
    ax.legend(loc="upper left", fontsize=8.5, framealpha=.9)
    fig.tight_layout()
    png = pathlib.Path(a.csv).with_name(pathlib.Path(a.csv).stem + "_analysis.png")
    fig.savefig(png, dpi=160)
    txt = png.with_suffix(".txt")
    txt.write_text("\n".join(out) + "\n")
    print(f"saved {png} and {txt}")


if __name__ == "__main__":
    main()
