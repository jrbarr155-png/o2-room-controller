"""
controller_sim.py

THE CORE NEW CONTRIBUTION: comparing a REACTIVE (feedback-only) control
strategy against a PREDICTIVE (feedforward + feedback) strategy for
recovering room O2 after a disturbance (e.g. a door opening).

-----------------------------------------------------------------------
THE IDEA
-----------------------------------------------------------------------
A standard consumer enrichment unit almost certainly only reacts AFTER
its O2 sensor detects a drop (feedback control): door opens -> O2 falls
-> sensor notices -> machine ramps up -> O2 recovers. There's an
unavoidable lag between the disturbance and the corrective response.

If the disturbance is at least partially PREDICTABLE (a door/motion
sensor fires the instant the door opens, before the O2 sensor has
detected any drop at all), the machine could respond BEFORE the O2
level actually falls, instead of waiting to react to it. This is
"feedforward control" - a standard concept in controls engineering,
applied here to a specific, testable, real product.

-----------------------------------------------------------------------
WHAT WE'RE ACTUALLY TESTING
-----------------------------------------------------------------------
Two controllers, same physical room/machine model, same disturbance
schedule, compared on:
  - Integrated Absolute Error (IAE): total accumulated deviation from
    target O2 over the whole trial (lower = better)
  - Time spent below a "comfort threshold" just under target
  - Max dip below target after a disturbance
"""

import numpy as np
from scipy import stats

from room_dynamics import (
    NORMAL_O2_FRACTION,
    O2_CONSUMPTION_PER_PERSON_M3_MIN,
)

DT = 0.5  # minutes per simulation step (discrete-time control loop)


def simulate_controlled_room(
    duration_min: float,
    V: float,
    Q_max: float,
    base_leak: float,
    target_C: float,
    disturbance_times: np.ndarray,
    disturbance_leak_boost: np.ndarray,
    disturbance_duration_min: np.ndarray,
    strategy: str,
    C_supply: float = 0.90,
    C_out: float = NORMAL_O2_FRACTION,
    n_people: int = 1,
    Kp: float = 8.0,
    feedforward_lead_min: float = 1.0,
    feedforward_gain: float = None,
):
    if feedforward_gain is None:
        # Derived from the steady-state mass balance, not guessed:
        # extra Q needed per unit of extra leak, to hold C at target_C,
        # given the machine's supply concentration and the target level.
        # (See: Q*(C_supply - C) must offset leak_boost*(C - C_out) at C=target_C)
        feedforward_gain = (target_C - C_out) / (C_supply - target_C)
    """
    Discrete-time simulation of a controlled room, with door-opening-style
    disturbances (temporary leak-rate spikes at known times).

    strategy: "feedback" or "feedforward"
      - "feedback": Q_machine = clip(Kp * (target_C - C), 0, Q_max)
                    (a simple proportional controller reacting only to
                    the CURRENT measured O2 level - standard reactive design)
      - "feedforward": same feedback term, PLUS an anticipatory boost
                    applied feedforward_lead_min BEFORE each known
                    disturbance time, scaled to the disturbance size.
                    (models a door/motion sensor giving early warning)

    Returns dict with time array, C array, Q_machine array, and leak array.
    """
    n_steps = int(duration_min / DT) + 1
    t = np.linspace(0, duration_min, n_steps)
    C = np.zeros(n_steps)
    Q = np.zeros(n_steps)
    leak = np.full(n_steps, base_leak)
    C[0] = target_C  # start already at target (steady operation, then disturbed)

    # Build the time-varying leak rate from scheduled disturbances
    for d_time, d_boost, d_dur in zip(disturbance_times, disturbance_leak_boost, disturbance_duration_min):
        mask = (t >= d_time) & (t < d_time + d_dur)
        leak[mask] += d_boost

    for i in range(1, n_steps):
        error = target_C - C[i - 1]
        Q_fb = np.clip(Kp * error, 0, Q_max)

        Q_ff = 0.0
        if strategy == "feedforward":
            for d_time, d_boost in zip(disturbance_times, disturbance_leak_boost):
                lead_start = d_time - feedforward_lead_min
                if lead_start <= t[i - 1] < d_time:
                    Q_ff = feedforward_gain * d_boost  # anticipatory burst sized to the coming disturbance

        Q[i - 1] = np.clip(Q_fb + Q_ff, 0, Q_max)

        dCdt = (
            Q[i - 1] * (C_supply - C[i - 1])
            - leak[i - 1] * (C[i - 1] - C_out)
            - n_people * O2_CONSUMPTION_PER_PERSON_M3_MIN
        ) / V
        C[i] = C[i - 1] + dCdt * DT

    Q[-1] = Q[-2]
    return {"t": t, "C": C, "Q": Q, "leak": leak}


def performance_metrics(t, C, target_C, comfort_band=0.005):
    """
    IAE (integrated absolute error), time below comfort threshold,
    and max dip below target - the three numbers the comparison hangs on.
    """
    error = target_C - C
    iae = np.trapezoid(np.abs(error), t)
    time_below = np.sum((C < (target_C - comfort_band))) * DT
    max_dip = np.max(error)
    return {"IAE": iae, "time_below_comfort_min": time_below, "max_dip": max_dip}


def run_trial(rng, V, Q_max, base_leak, target_C, duration_min=180, n_disturbances=4):
    """One randomized trial: random door-opening times/severities, same
    disturbance schedule applied to BOTH strategies for a fair comparison."""
    disturbance_times = np.sort(rng.uniform(10, duration_min - 20, size=n_disturbances))
    disturbance_leak_boost = rng.uniform(0.3, 1.2, size=n_disturbances)  # m^3/min extra leak
    disturbance_duration = rng.uniform(0.5, 2.0, size=n_disturbances)    # minutes door stays open

    results = {}
    for strategy in ["feedback", "feedforward"]:
        sim = simulate_controlled_room(
            duration_min, V, Q_max, base_leak, target_C,
            disturbance_times, disturbance_leak_boost, disturbance_duration,
            strategy=strategy,
        )
        results[strategy] = performance_metrics(sim["t"], sim["C"], target_C)
        results[strategy]["sim"] = sim
    return results


if __name__ == "__main__":
    rng = np.random.default_rng(7)
    V, Q_max, base_leak = 40.0, 2.0, 0.4
    target_C = 0.26  # ~matches the sea-level-simulation target from earlier

    N_TRIALS = 200
    iae_feedback, iae_feedforward = [], []

    for _ in range(N_TRIALS):
        r = run_trial(rng, V, Q_max, base_leak, target_C)
        iae_feedback.append(r["feedback"]["IAE"])
        iae_feedforward.append(r["feedforward"]["IAE"])

    iae_feedback = np.array(iae_feedback)
    iae_feedforward = np.array(iae_feedforward)

    pct_improvement = 100 * (iae_feedback - iae_feedforward) / iae_feedback

    t_stat, p_value = stats.ttest_rel(iae_feedback, iae_feedforward)

    print(f"Trials: {N_TRIALS}")
    print(f"Mean IAE - feedback only:      {iae_feedback.mean():.4f}")
    print(f"Mean IAE - feedforward+fb:     {iae_feedforward.mean():.4f}")
    print(f"Mean improvement:              {pct_improvement.mean():.1f}%  "
          f"(std {pct_improvement.std():.1f}%)")
    print(f"Paired t-test:                 t={t_stat:.2f}, p={p_value:.2e}")

    # Also track max-dip and time-below-comfort across the same trials
    rng2 = np.random.default_rng(7)
    dip_fb, dip_ff, below_fb, below_ff = [], [], [], []
    for _ in range(N_TRIALS):
        r = run_trial(rng2, V, Q_max, base_leak, target_C)
        dip_fb.append(r["feedback"]["max_dip"])
        dip_ff.append(r["feedforward"]["max_dip"])
        below_fb.append(r["feedback"]["time_below_comfort_min"])
        below_ff.append(r["feedforward"]["time_below_comfort_min"])

    print(f"\nMean max dip below target - feedback:     {np.mean(dip_fb)*100:.3f} pts O2")
    print(f"Mean max dip below target - feedforward:  {np.mean(dip_ff)*100:.3f} pts O2")
    print(f"Mean minutes below comfort - feedback:    {np.mean(below_fb):.1f} min")
    print(f"Mean minutes below comfort - feedforward: {np.mean(below_ff):.1f} min")

    # Representative single-trial plot
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rng3 = np.random.default_rng(3)
    r_demo = run_trial(rng3, V, Q_max, base_leak, target_C)
    plt.figure(figsize=(9, 5))
    plt.plot(r_demo["feedback"]["sim"]["t"], r_demo["feedback"]["sim"]["C"] * 100,
              label="Feedback only (reactive)", lw=1.8)
    plt.plot(r_demo["feedforward"]["sim"]["t"], r_demo["feedforward"]["sim"]["C"] * 100,
              label="Feedforward + feedback (predictive)", lw=1.8)
    plt.axhline(target_C * 100, color="gray", ls=":", label="Target")
    plt.xlabel("Time (minutes)")
    plt.ylabel("Room O2 (%)")
    plt.title("Reactive vs. predictive control under repeated door-opening disturbances")
    plt.legend()
    plt.tight_layout()
    plt.savefig("controller_comparison.png", dpi=150)
    plt.close()
    print("\nSaved plot: controller_comparison.png")
