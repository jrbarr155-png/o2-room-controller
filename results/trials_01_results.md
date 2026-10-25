# trials_01 — reactive vs feedforward, first controller trials (Oct 24, 2026)

Raw data `data/2026-10-24_1635_trials_01.csv` · plot `results/2026-10-24_trials_overlay.png`
Protocol (written before trial 1): `predictions/controller_trial_protocol.md`

## Setup
10 L/min · 3-way valve (A in, B room, C vent out a window) · relay + 12 V in the room · firmware v2
(band control on a 60-s average) · band L = 21.46, H = 21.56 (baseline 21.06 + 0.40 / + 0.50)
· feedforward boost 600 s (sized from trial 1) · door opened 5 min after each high-line valve switch, for 2 min.

## Timeline
| Clock | Event |
|---|---|
| 16:35–16:51 | Baseline 21.06 (flat, door shut) |
| 16:51 | Reactive mode on, fill to band |
| ~17:40–18:01 | Concentrator stopped (flow 0) — **its cooling fan had been unplugged** since reassembly; thermal cutoff. Fan plugged in ~18:00, back on 18:01 |
| 18:16:49 | **Trial 1 (reactive)** |
| 19:13:09 | **Trial 2 (feedforward)** |
| 20:00:08 | **Trial 3 (reactive)** — door opened 71 s late |
| 20:50:16 | Trial 4 attempt — **void**: sensor B wires kicked; safety rule forced valve to VENT 20:50:39–20:52:13 |
| 21:20:50 | **Trial 4 (feedforward)** redo |
| 22:00:08 | Concentrator off, valve VENT → 1-h decay |

## Results (t = 0 at door opening; 1-min average)
| | T1 reactive | T2 feedforward | T3 reactive | T4 feedforward |
|---|---|---|---|---|
| Valve on after door | 2.1 min | 0.0 | 1.7 min | 0.0 |
| Dip from own pre-door level | 0.081 | 0.080 | 0.116 | 0.071 |
| Time below low line | 2.9 min | 1.0 | 6.6 | 4.6 |
| Back to pre-door level | 13.4 min | 11.5 | 12.5 | 15.5 |
| IAE vs band center (32 min) | 1.24 | 1.14 | 1.25 | 1.15 |

| Mean | Reactive | Feedforward | Change |
|---|---|---|---|
| Dip | 0.099 | 0.076 | −23 % |
| Time below low line | 4.8 min | 2.8 min | −40 % |
| Back to pre-door level | 12.9 min | 13.5 min | none |
| IAE vs band center | 1.24 | 1.15 | −7 % |

## Interpretation (honest)
- Feedforward had the smaller dip and lower IAE in **both** pairs; IAE was very consistent (1.14/1.15 vs 1.24/1.25).
- Size of the gain matches the prediction made after trial 1: a ~2-min head start × net valve supply ≈ 0.01–0.02
  less dip; measured 0.023.
- It did not recover faster to the pre-door level.
- n = 2 per controller, and trial-to-trial variation (0.081 vs 0.116 for the same controller) is as big as the
  effect. Suggestive, not proven.

## Why the effect is small: actuator authority
The open door lost ≈ 59.7 m³ × 0.08 ≈ 5 %·m³ of O2 in 2 min (≈ 2.4 per min). The valve can add ≈ 0.6 per min.
Even switched on instantly, the concentrator replaces about a quarter of what the door removes, so no
controller can prevent the dip; feedforward can only buy a ~2-min head start. The simulation assumed a
machine ~200× stronger relative to the room, which is why it predicted more.

## Decay (22:00–23:00)
τ ≈ 70 min → leak ≈ 0.85 m³/min (fit with the end level fixed at the day's baseline 21.06; a free fit is not
constrained by a 1-h decay). Leak rates so far: 0.62 (Oct 22), 0.37 (Oct 23), ~0.85 (Oct 24) — the room's
air exchange changes a lot from day to day.

## Next session (write into the protocol before running)
- Open the door **at** the high-line click (not +5 min) and widen the band (L = baseline + 0.30) so reactive waits
  longer — tests whether feedforward helps more when the head start is bigger.
- Logger beeps/speaks at the click, so door timing doesn't depend on phone notifications.
- More pairs (≥ 4 each), tape all sensor wires, same-day decay every session.
