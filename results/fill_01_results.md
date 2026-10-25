# fill_01 — first real-hardware validation of the room model

**Run:** Thu Oct 22, 2026, 8:42 pm – 12:01 am · raw data `data/2026-10-22_2042_fill_01.csv`
**Reproduce every number here:**
```
python3 analysis/analyze_fill_decay.py data/2026-10-22_2042_fill_01.csv \
  --baseline-start 20:45:30 --fill-start 20:57:57 --decay-start 23:00:44 \
  --volume 59.7 --lpm 5 --date 2026-10-22
```
Plot: `results/2026-10-22_2042_fill_01_analysis.png` · full printout: `results/2026-10-22_2042_fill_01_analysis.txt`

## Setup
| Item | Value |
|---|---|
| Room | Bedroom, L-shaped, 59.7 m³, sliding barn door shut |
| Source | Restored Respironics Millennium concentrator, **outside** the room in the hallway |
| Flow | 5.0 L/min (inline flowmeter, set once, not touched) |
| O2 outlet | Tube taped high on the wardrobe, aimed into the room |
| Mixing | Vornado circulator, low, by the wardrobe, aimed at the bed |
| Sensors | 2 × DFRobot I2C O2 (A on desk, B on chair by the door), DHT22, door reed switch; 1 reading / 2 s |
| Conditions | 19.7–20.1 °C, thermostat untouched, door shut for the whole fill |

## Timeline
| Clock | Event |
|---|---|
| 20:44:45 | Tube disconnected → **baseline** (room at rest) |
| 20:57:57 | Tube reconnected → **fill starts** |
| 23:00:44 | Concentrator off → **decay starts** |
| 23:31:00 | Door opened ~6 s (going to bed) |
| 00:01 | Logger stopped itself (`sleep 3600; pkill -INT`) |

## Results
| Quantity | Value |
|---|---|
| Baseline (each sensor's own resting reading) | A 20.909 %, B 20.804 % → both re-referenced to 20.9 % |
| Noise of 2-sensor average | ±0.04 (1 sd) |
| Rise reached after 123 min of fill | **+0.23** points |
| Fill time constant τ | **85 ± 5 min** |
| Decay time constant τ | **96 ± 3 min** |
| Starting slope (first 20 min) | 0.0048 %/min (model at 93 % purity: 0.0060) |
| Sensors A vs B, end of fill | within 0.02 → room well mixed |

### The validation: leak rate measured two independent ways
| Method | Leak / air-exchange rate Ql |
|---|---|
| From **fill speed** (machine on): Ql = V/τ − Qm | **0.70 m³/min** (0.70 air changes/h) |
| From **decay speed** (machine off): Ql = V/τ | **0.62 m³/min** (0.62 air changes/h) |
| From fill **plateau height** | 1.2 m³/min — unreliable, see below |

The fill and the decay are different experiments (O2 going in vs. coming out) and they agree within **12 %**. That is the well-mixed mass-balance model holding up on a real room.

## What didn't match, and why (keep this in the write-up)
1. **Plateau-based leak rate is off by ~2×.** The fill was stopped while still rising, so the plateau (21.20 %) is extrapolated, and the formula also needs the machine's true purity. Both are uncertain, so this estimate is the weakest.
2. **The concentrator is weaker than its spec.** The starting slope was 79 % of the model's prediction at 93 % purity. If the flowmeter is right, the 17-year-old unit is delivering about **78 % O2**, not 93 %. (Could also be a slightly optimistic flowmeter; a purity meter would separate the two.)
3. **The fill rose more slowly than the model predicts from its own starting slope.** Using the measured leak rate and 78 % purity, the model expects the room to reach ~+0.32 by 123 min; it reached +0.23. One explanation: some O2 escapes before it mixes. The outlet was near the barn door. Testable by moving the outlet.
4. **A pause from ~25 to 45 min** where the curve went flat before climbing again. Not explained yet; the room may not have been fully mixed early on (sensor A led B by up to 0.19 early, then they converged).

## What it means for the controller test
At 5 L/min this room only reaches about **+0.3 above normal** against ±0.04 noise. A short door opening (the 23:31 one) produced at most a ~0.03 dip, inside the noise. Running reactive vs. feedforward trials at this signal size would likely show "no difference" because of the measurement, not the controller. Next step: a 10 L/min fill (`predictions/fill_02_predictions.md`) to roughly double the signal.
