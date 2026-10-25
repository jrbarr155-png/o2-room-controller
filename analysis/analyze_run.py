"""
analyze_run.py — fit the room model to one logged run and make the plot.

Usage:
    pip install numpy scipy matplotlib
    python analyze_run.py data/2026-10-15_1900_fill_01.csv --kind fill
    python analyze_run.py data/2026-10-16_1000_decay_01.csv --kind decay

THE MODEL (well-mixed room, first-order mass balance):
    V dC/dt = Qm*(Cs - C) - Ql*(C - Cout)
  V    room volume (m^3)            Qm  concentrator flow (m^3/min)
  Cs   concentrator purity (~0.93)  Ql  room air exchange / leak (m^3/min)
  Cout outside air (0.209)

  Solution: C(t) = Css + (C0 - Css) * exp(-t / tau)

  FILL run (unit ON):   tau = V / (Qm + Ql)     Css = (Qm*Cs + Ql*Cout) / (Qm + Ql)
  DECAY run (unit OFF): tau = V / Ql            Css = Cout

THE VALIDATION TEST (this is the real science):
  A fill run lets you estimate the leak rate Ql TWO independent ways —
  once from how FAST the room fills (tau) and once from WHERE it levels off (Css).
  If the well-mixed model is right, the two numbers agree. If they don't, the
  model is missing something, and that disagreement is itself a finding.
  A decay run gives a third, cleaner estimate of Ql with the machine off.
"""
import argparse
import pathlib

import numpy as np
from scipy.optimize import curve_fit
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COUT = 20.9  # % O2 in normal air (the sensor is calibrated to this)


def load(path):
    meta, rows = {}, []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("# ") and "=" in line:
                k, v = line[2:].split("=", 1)
                meta[k] = v
            elif line and not line.startswith("#") and not line.startswith("time_iso"):
                rows.append(line.split(","))
    ms = np.array([float(r[1]) for r in rows])
    t_min = (ms - ms[0]) / 60000.0
    a = np.array([float(r[2]) for r in rows])
    b = np.array([float(r[3]) for r in rows])
    door = np.array([int(r[6]) for r in rows])
    temp = np.array([float(r[4]) for r in rows])
    return meta, t_min, a, b, door, temp


def first_order(t, css, c0, tau):
    return css + (c0 - css) * np.exp(-t / tau)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("--kind", choices=["fill", "decay"], required=True)
    p.add_argument("--start", type=float, default=0, help="ignore data before this minute (e.g. sensor warm-up)")
    p.add_argument("--purity", type=float, default=93.0, help="concentrator output purity, %% (spec ~93)")
    p.add_argument("--baseline-min", type=float, default=None,
                   help="minutes of machine-OFF baseline at the start of the log. Each sensor's own average over "
                        "this window is treated as outside air (cancels per-sensor offsets). Fitting starts after it "
                        "unless --start is later.")
    p.add_argument("--cout", type=float, default=20.9,
                   help="outside/background O2 %% as YOUR sensors read it (use the baseline measured before the run)")
    a = p.parse_args()
    global COUT
    COUT = a.cout

    meta, t, o2a, o2b, door, temp = load(a.csv)
    if a.baseline_min:
        base = (t >= 1.0) & (t < a.baseline_min)          # skip the first minute (sensor power-up dip)
        ba, bb = np.nanmean(o2a[base]), np.nanmean(o2b[base])
        print(f"  baseline (machine off): sensor A = {ba:.2f}%, sensor B = {bb:.2f}%  -> both re-referenced to {COUT}%")
        o2a = o2a - ba + COUT
        o2b = o2b - bb + COUT
        a.start = max(a.start, a.baseline_min)
    keep = t >= a.start
    t, o2a, o2b, door = t[keep] - a.start, o2a[keep], o2b[keep], door[keep]
    c = np.nanmean(np.vstack([o2a, o2b]), axis=0)   # average of the two sensors

    guess = [c[-1], c[0], max(t[-1] / 3, 1)]
    (css, c0, tau), cov = curve_fit(first_order, t, c, p0=guess, maxfev=20000)
    css_err, _, tau_err = np.sqrt(np.diag(cov))
    resid = c - first_order(t, css, c0, tau)

    print(f"\nRun: {meta.get('run')}   ({a.kind})")
    print(f"  tau  = {tau:7.1f} ± {tau_err:.1f} min")
    print(f"  Css  = {css:7.2f} ± {css_err:.2f} %O2")
    print(f"  fit residual RMS = {np.sqrt(np.mean(resid**2)):.3f} %O2")
    print(f"  sensors A vs B mean difference = {np.nanmean(o2a - o2b):+.2f} %O2  (well-mixed check)")

    V = float(meta["volume_m3"]) if meta.get("volume_m3") not in (None, "None") else None
    lpm = float(meta["lpm"]) if meta.get("lpm") not in (None, "None") else None
    if V:
        if a.kind == "decay":
            ql = V / tau
            print(f"  -> leak rate Ql = V/tau = {ql:.3f} m^3/min  ({ql*60/V:.2f} room air changes per hour)")
        elif lpm:
            qm = lpm / 1000.0
            ql_tau = V / tau - qm
            ql_css = qm * (a.purity - css) / (css - COUT) if css > COUT else float("nan")
            print(f"  -> Ql from fill SPEED (tau): {ql_tau:.3f} m^3/min")
            print(f"  -> Ql from fill LEVEL (Css): {ql_css:.3f} m^3/min")
            if np.isfinite(ql_css):
                print(f"  -> agreement: {100*abs(ql_tau-ql_css)/np.mean([ql_tau, ql_css]):.0f}% difference "
                      f"(close agreement supports the well-mixed model)")
    else:
        print("  (add --volume when logging to get leak-rate numbers)")

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(t, o2a, ".", ms=2, alpha=0.4, label="sensor A")
    ax.plot(t, o2b, ".", ms=2, alpha=0.4, label="sensor B")
    ax.plot(t, first_order(t, css, c0, tau), lw=2, label=f"model fit  (tau={tau:.0f} min, Css={css:.2f}%)")
    for i in np.where(np.diff(door) == 1)[0]:
        ax.axvline(t[i + 1], color="gray", alpha=0.3)
    ax.axhline(23.5, color="red", ls=":", label="23.5% safety limit")
    ax.set_xlabel("time (min)")
    ax.set_ylabel("room O2 (%)")
    ax.set_title(f"{meta.get('run')} — {a.kind} run")
    ax.legend()
    fig.tight_layout()
    out = pathlib.Path(a.csv).with_suffix(".png")
    fig.savefig(out, dpi=150)
    print(f"  plot saved: {out}\n")


if __name__ == "__main__":
    main()
