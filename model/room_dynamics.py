"""
room_dynamics.py

Step 2 of the model: a first-order mass-balance ODE describing how the
room's oxygen percentage changes over time in response to the machine's
enrichment output, room leakage, and occupant consumption.

This is the same mathematical structure as a thermostat heating a room,
a tank filling with fluid, or drug concentration in the bloodstream -
a classic "inflow vs. outflow toward a setpoint" system. 

MODEL
-----
Let C(t) = O2 fraction in the room at time t (e.g. 0.21 = 21%)
Let C_out = O2 fraction of outside air leaking in (~0.2095, normal)
Let C_supply = O2 fraction of the enriched air the machine outputs (near-pure O2,
               or a boosted mixture - configurable)

State equation (well-mixed room assumption):

    V * dC/dt = Q_machine * (C_supply - C)      <- machine adding enriched air
              - Q_leak    * (C - C_out)          <- room leaking to outside
              - N_people  * o2_consumption_rate  <- people breathing O2 out of the air

Where:
    V           = room volume (m^3)
    Q_machine   = machine's air output flow rate (m^3/min)
    Q_leak      = effective leakage/exchange flow rate with outside (m^3/min)
    N_people    = number of occupants
    o2_consumption_rate = O2 consumed per person per minute (m^3/min), a small
                          constant based on human metabolic O2 uptake

This is a linear first-order ODE - given constant inputs, C(t) rises like a
capacitor charging (exponential approach to a steady-state value), with a
time constant tau = V / (Q_machine + Q_leak).

"""

import numpy as np
from scipy.integrate import odeint
from scipy.optimize import curve_fit

# Human O2 consumption: an adult at rest consumes roughly 0.25-0.3 L/min of O2.
# Converting to m^3/min: 0.25 L/min = 0.00025 m^3/min
O2_CONSUMPTION_PER_PERSON_M3_MIN = 0.00025

NORMAL_O2_FRACTION = 0.2095


def room_ode(C, t, V, Q_machine, Q_leak, C_supply, C_out, n_people):
    """Right-hand side of dC/dt for scipy.odeint."""
    dCdt = (
        Q_machine * (C_supply - C)
        - Q_leak * (C - C_out)
        - n_people * O2_CONSUMPTION_PER_PERSON_M3_MIN
    ) / V
    return dCdt


def simulate(
    t_minutes: np.ndarray,
    V: float,
    Q_machine: float,
    Q_leak: float,
    C_supply: float = 0.90,   # machine's enriched-air O2 fraction, e.g. 90% O2 concentrator output
    C_out: float = NORMAL_O2_FRACTION,
    n_people: int = 1,
    C0: float = NORMAL_O2_FRACTION,
) -> np.ndarray:
    """
    Simulate room O2 fraction over time given machine and room parameters.

    Returns array of O2 fraction at each time in t_minutes.
    """
    sol = odeint(
        room_ode, C0, t_minutes,
        args=(V, Q_machine, Q_leak, C_supply, C_out, n_people)
    )
    return sol.flatten()


def steady_state_o2(V, Q_machine, Q_leak, C_supply=0.90, C_out=NORMAL_O2_FRACTION, n_people=1):
    """
    Closed-form steady state (dC/dt = 0), useful for sanity-checking the
    simulation and for quickly answering 'what O2 level does this room
    settle at, given this machine setting?' without integrating.
    """
    return (
        Q_machine * C_supply + Q_leak * C_out
        - n_people * O2_CONSUMPTION_PER_PERSON_M3_MIN
    ) / (Q_machine + Q_leak)


def time_constant_minutes(V, Q_machine, Q_leak):
    """tau = V / (Q_machine + Q_leak); ~63% of the way to steady state at t=tau."""
    return V / (Q_machine + Q_leak)


def fit_parameters(t_minutes, C_observed, V, C_supply=0.90, C_out=NORMAL_O2_FRACTION, n_people=1):
    """
    THE KEY FUNCTION FOR WHEN REAL DATA ARRIVES.

    Given observed time-series data of room O2 fraction (from a real unit or
    a bench test), fit Q_machine and Q_leak so the model reproduces it.

    t_minutes:    array of timestamps (minutes)
    C_observed:   array of measured O2 fractions at those timestamps
    V:            known/measured room volume (m^3)

    Returns: (Q_machine_fit, Q_leak_fit), plus you can feed these back into
    simulate() to check the fit visually, or into steady_state_o2() to
    predict behavior in other room sizes.
    """

    def model_fn(t, Q_machine, Q_leak):
        return simulate(t, V, Q_machine, Q_leak, C_supply, C_out, n_people, C0=C_observed[0])

    # initial guesses - fairly generic starting point for a small machine/room
    p0 = [0.5, 0.3]
    bounds = ([1e-4, 1e-4], [50, 50])  # keep flow rates physically positive/reasonable

    popt, pcov = curve_fit(model_fn, t_minutes, C_observed, p0=p0, bounds=bounds)
    return popt  # [Q_machine_fit, Q_leak_fit]
