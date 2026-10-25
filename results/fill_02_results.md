# fill_02 — 10 L/min fill + decay (Oct 23, 2026)

Raw data `data/2026-10-23_1138_fill_02.csv` · plot `results/2026-10-23_1138_fill_02_analysis.png`
Predictions written beforehand: `predictions/fill_02_predictions.md`

## Timeline
| Clock | Event |
|---|---|
| 11:38 | Logger started on the new laptop (sensors re-warming after the USB move) |
| 11:42–11:56 | Baseline, tube disconnected (A 20.985 %, B 20.835 %) |
| 11:56:51 | Tube connected, 10 L/min → **fill** |
| 15:00:02 | Concentrator off → **decay** |
| 17:27 | Still logging (2.5 h of decay) |
Door shut the whole time (0 openings). Room warmed 18.4 → 20.6 °C over the day.

## Prediction check
| What | Predicted | Measured | Verdict |
|---|---|---|---|
| Starting slope (0–20 min) | ≈ 0.0096 %/min (2× fill_01) | **0.0114 %/min (2.4×)** | ✅ roughly 2×, a bit above |
| Rise after 30 min | 2× fill_01 | **+0.25 vs +0.12 (2.1×)** | ✅ |
| Rise after 120 min | ≈ +0.46 | **+0.69** | ❌ higher (but the room was less leaky today — see below) |
| Time constant | ≈ 85–95 min | fill: not a clean exponential; decay: **161 min** | ❌ room much tighter than on Oct 22 |

## Findings
1. **The decay is the cleanest curve so far.** τ = 161 ± 1 min → leak rate **0.37 m³/min** (0.37 air changes/h). Fitted with the end level left free, it decays toward **20.908 %** — the measured baseline was 20.9. The room returned to exactly where it started after 5½ hours, so the sensors did not drift with the 2 °C temperature rise.
2. **The room's leak rate changes day to day:** 0.62 m³/min on Oct 22 night, 0.37 on Oct 23 afternoon. Likely wind/outdoor temperature/heating. This is why the plateau beat the prediction: the prediction used Oct 22's leak rate.
3. **The concentrator stopped delivering O2 twice during the fill** (~60–80 min and ~130–140 min). In both windows the room O2 *fell* while the machine was supposed to be adding oxygen — impossible with a steady supply. Working backwards through the mass balance (supply = V·dC/dt + leak × rise) gives the supply in each 10-min window: normally ~75–115 % of its starting value, but **~0–30 % in those two windows**. Leading hypothesis: the compressor overheating and hitting its thermal cutoff (149 °F) at 10 L/min with worn fans, then restarting after cooling. Untested.
4. **When it runs, the machine delivers ~80 % O2** (supply estimate with today's leak rate), matching fill_01's ~78 %. Two runs, two flows, same effective purity.

## What it means
- Signal at 10 L/min: ~+0.7 to +0.8 above normal vs ±0.04 noise — about 2.5× better than at 5 L/min. Better for door trials.
- But an O2 source that drops out on its own would wreck a controller comparison (it looks exactly like a disturbance). Before controller trials: find out whether/why the concentrator stops (watch/listen for the compressor stopping, feel the box, note the flowmeter float at those times).
- Always measure the leak rate on the same day as a trial (a decay at the end), since it isn't constant.
