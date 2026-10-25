# fill_02 predictions — written BEFORE the run

**Written:** Fri Oct 23, 2026, ~11:05 am, before any 10 L/min data exists.
**Plan:** same room, same setup as fill_01 (fan, sensor spots, outlet, door), flowmeter at **10 L/min** instead of 5. Unit label appears to say M10 (10 L/min model) — confirm the float holds at 10 with no alarm before starting.

## Where the predictions come from
- Room model: V dC/dt = Qm(Cs − C) − Ql(C − Cout)
- Measured in fill_01: leak rate Ql ≈ 0.62–0.70 m³/min, fill τ = 85 min, starting slope 0.0048 %/min at 5 L/min, rise of +0.23 after 123 min.
- Doubling Qm doubles the O2 going in. Ql is ~60× bigger than Qm, so τ = V/(Qm + Ql) barely changes.

## Predictions
| What | fill_01 measured (5 L/min) | **fill_02 predicted (10 L/min)** |
|---|---|---|
| Starting slope, first 20 min | 0.0048 %/min | **≈ 0.0096 %/min (2×)** |
| Time constant τ | 85 min | **≈ 85–95 min (about the same)** |
| Rise above baseline after 120 min | +0.23 | **≈ +0.46 (2×)** |
| Plateau rise | ~+0.3 | **≈ +0.6** |

## How to read the result
- **Slope and rise come out ~2×, τ unchanged:** the model scales correctly with flow — a strong validation.
- **Rise is clearly less than 2× (say 1.3–1.6×):** the machine's purity drops at 10 L/min (PSA can't keep up). That is a finding about the concentrator, and the starting slope gives the new effective purity.
- **τ changes a lot:** something about the room changed between runs (weather, HVAC, door seal) — check notes.

Safety: predicted peak ≈ 21.5 %, far below the 23.0 % alarm.
