# Model

The room is treated as one well-mixed box. Oxygen mass balance:

    V·dC/dt = Qm·(Cs − C) − Ql·(C − Cout)

V room volume (59.7 m³, tape-measured) · C room O2 · Qm concentrator flow (flowmeter) ·
Cs supply purity · Ql leak / air-exchange rate · Cout normal O2 (same-day baseline).
Solution: C(t) = C∞ + (C0 − C∞)·e^(−t/τ), τ = V/(Qm + Ql). Machine off: τ = V/Ql.
Cs and Ql can't be measured directly; they come from the starting slope of a fill and from the decay.

| File | What it does |
|---|---|
| `room_dynamics.py` | The ODE, closed-form steady state, and a fitting helper. |
| `controller_sim.py` | First simulation (written before any hardware): reactive vs feedforward with an idealized proportional controller. Where the derived feedforward gain came from. Its absolute numbers used assumed parameters. |
| `hardware_sim.py` | The model rerun with **measured** parameters (Cs ≈ 79 %, Ql from the same-day decay) and the real on/off controller: 60-s average, 30-s switch limit, boost, door timing. Includes the "stronger machine" what-if. |
| `prediction_vs_trials.py` | Overlays `hardware_sim.py`'s prediction on the four real door trials (`../data/2026-10-24_1635_trials_01.csv`). |

All outputs of this folder are **simulation**; measured results are in `../results/`.
