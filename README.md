# O2 Room Controller

Firmware, logger, model and analysis for my MIT Maker Portfolio project: a restored medical oxygen
concentrator plus an Arduino controller that regulates the oxygen level in a 59.7 m³ room, comparing
on/off (reactive) control against door-triggered feedforward control.

**Safety note:** the room never went more than about 0.8 percentage points above normal. The firmware
forces the valve to vent if either sensor reaches 23.0 % or the sensors fault, and the valve is wired
fail-safe (unpowered = vent). Please don't build an oxygen-enrichment system without the same precautions.

## What's here
| Folder | Contents |
|---|---|
| `firmware/` | `o2_valve_controller.ino`: the controller (logging, reactive and feedforward modes, safety rules). The v0 file is the earlier logging-only version. |
| `logger/` | `log_serial.py` records the Arduino's output to CSV and sends commands; `watch_baseline.py` announces when the resting O2 is stable. |
| `model/` | Room mass-balance model (`room_dynamics.py`), controller simulation (`controller_sim.py`), and `hardware_sim.py` / `prediction_vs_trials.py`, which rerun the model with measured parameters. Results from these are **simulation**. |
| `analysis/` | Fill/decay fitting (`analyze_fill_decay.py`), the supply-dropout analysis, the safety-event plot, and diagram scripts. |
| `data/` | Raw logger CSVs, unedited: bench test, fill_01 (5 L/min), fill_02 (10 L/min), trials_01 (four door trials + decay), and the Oct 25 feedforward demo takes. |
| `results/`, `predictions/` | Write-ups and plots; predictions were written before each run. |

## Model
V·dC/dt = Qm(Cs − C) − Ql(C − Cout), with V = room volume, C = room O2, Qm = concentrator flow,
Cs = supply purity, Ql = leak rate, Cout = outside O2. Solution: C(t) = C∞ + (C0 − C∞)e^(−t/τ),
τ = V/(Qm + Ql). Ql is found from the decay (τ = V/Ql) and checked against the fill; Cs from the
starting slope of a fill.

## Running it
- Firmware: Arduino Uno; libraries DFRobot_OxygenSensor and Adafruit DHT.
- Logger: `pip install pyserial`, then
  `python3 log_serial.py --port /dev/cu.usbmodemXXXX --run fill_01 --volume 59.7 --lpm 10 --cmd "r"`
- Analysis/model: `pip install numpy scipy matplotlib`; run scripts from their own folder.

## Credits
Hardware restoration, wiring, plumbing, installation and all experiments are my own work. I used
Claude (an Anthropic AI assistant) as a tutor to help write most of the code in this repository from
my descriptions of what each part needed to do; I uploaded, ran and debugged it on the real hardware.
Libraries: DFRobot_OxygenSensor, Adafruit DHT, pyserial, NumPy, SciPy, Matplotlib.
