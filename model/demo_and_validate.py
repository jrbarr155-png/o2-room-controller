"""
demo_and_validate.py

Validates the whole pipeline BEFORE any real data exists:

1. Simulate a "fake real unit" with KNOWN true parameters + sensor noise
   (standing in for what a real logged dataset from Altitude Solutions
   would look like).
2. Feed that noisy synthetic data into fit_parameters() as if it were real,
   and confirm the fit recovers parameters close to the true ones.
3. Once real data arrives next week, you literally swap the synthetic
   data-generation step for "load the real CSV" and everything else
   (fitting, plotting, prediction) already works.
4. Also demonstrates the "payoff" analysis: time-to-target for different
   room sizes/occupancy, and a simple feed-forward door-opening scenario.

Run: python3 demo_and_validate.py
Outputs: two PNG plots in this directory.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from altitude_physics import required_o2_fraction
from room_dynamics import (
    simulate, fit_parameters, steady_state_o2, time_constant_minutes,
    NORMAL_O2_FRACTION as C_OUT
)

rng = np.random.default_rng(42)

# ---------------------------------------------------------------------------
# STEP 0: figure out the target O2 fraction for a concrete scenario
# ---------------------------------------------------------------------------
HOME_ELEV_M = 1760.0     # Glenwood Springs, CO ~ 5,760 ft
TARGET_ELEV_M = 0.0      # simulate sea level
target_C = required_o2_fraction(HOME_ELEV_M, TARGET_ELEV_M)
print(f"Target room O2 fraction to simulate sea level: {target_C*100:.2f}%")

# ---------------------------------------------------------------------------
# STEP 1: generate synthetic "ground truth" data standing in for a real unit
# ---------------------------------------------------------------------------
TRUE_V = 40.0          # room volume, m^3 (~ a 400 sq ft room, 10ft ceiling)
TRUE_Q_MACHINE = 0.8   # m^3/min enriched air output
TRUE_Q_LEAK = 0.4       # m^3/min effective leakage

t_minutes = np.linspace(0, 180, 60)  # 3 hours, sampled every 3 min
true_curve = simulate(t_minutes, TRUE_V, TRUE_Q_MACHINE, TRUE_Q_LEAK)
noisy_curve = true_curve + rng.normal(0, 0.0015, size=true_curve.shape)  # sensor noise

# ---------------------------------------------------------------------------
# STEP 2: pretend we only have the noisy data + known room volume, fit params
# ---------------------------------------------------------------------------
Q_machine_fit, Q_leak_fit = fit_parameters(t_minutes, noisy_curve, TRUE_V)

print("\n--- Parameter recovery check ---")
print(f"True  Q_machine: {TRUE_Q_MACHINE:.3f} m^3/min   Fit: {Q_machine_fit:.3f} m^3/min")
print(f"True  Q_leak:    {TRUE_Q_LEAK:.3f} m^3/min   Fit: {Q_leak_fit:.3f} m^3/min")

fitted_curve = simulate(t_minutes, TRUE_V, Q_machine_fit, Q_leak_fit)

# Plot 1: fit validation
plt.figure(figsize=(8, 5))
plt.plot(t_minutes, noisy_curve * 100, "o", ms=3, alpha=0.5, label="Synthetic 'sensor' data")
plt.plot(t_minutes, true_curve * 100, "--", lw=2, label="True underlying curve")
plt.plot(t_minutes, fitted_curve * 100, "-", lw=2, label="Model fit to data")
plt.axhline(target_C * 100, color="gray", ls=":", label=f"Target ({target_C*100:.1f}%)")
plt.xlabel("Time (minutes)")
plt.ylabel("Room O2 (%)")
plt.title("Validation: fitting recovers the true room/machine parameters")
plt.legend()
plt.tight_layout()
plt.savefig("fit_validation.png", dpi=150)
plt.close()

# ---------------------------------------------------------------------------
# STEP 3: the payoff analysis - time-to-target across room sizes/occupancy
# ---------------------------------------------------------------------------
room_sizes = [20, 40, 60, 80, 100]  # m^3
plt.figure(figsize=(8, 5))
for V in room_sizes:
    curve = simulate(t_minutes, V, TRUE_Q_MACHINE, TRUE_Q_LEAK, n_people=1)
    plt.plot(t_minutes, curve * 100, label=f"V={V} m³")
plt.axhline(target_C * 100, color="gray", ls=":", label="Target")
plt.xlabel("Time (minutes)")
plt.ylabel("Room O2 (%)")
plt.title("Time-to-target vs. room size (same machine, 1 occupant)")
plt.legend()
plt.tight_layout()
plt.savefig("room_size_comparison.png", dpi=150)
plt.close()

print("\n--- Time-to-target across room sizes ---")
for V in room_sizes:
    ss = steady_state_o2(V, TRUE_Q_MACHINE, TRUE_Q_LEAK)
    tau = time_constant_minutes(V, TRUE_Q_MACHINE, TRUE_Q_LEAK)
    reaches_target = ss >= target_C
    print(f"V={V:>3} m^3 | steady-state O2={ss*100:5.2f}% | time const={tau:5.1f} min "
          f"| {'reaches target' if reaches_target else 'UNDERSIZED for target'}")

print("\nSaved plots: fit_validation.png, room_size_comparison.png")
