# Controller trials — reactive vs feedforward (protocol)

Written Oct 24, 2026, before the first trial.

## Question
When the door opens, does turning the O2 on immediately (feedforward) keep the room
closer to target than waiting for the sensors to see the drop (reactive)?

## Fixed setup (same for every trial)
- 10 L/min, flowmeter not touched. Concentrator outside the room, phone time-lapsing it + flowmeter.
- Valve ports: A (IN) ← flowmeter · B (ROOM) → outlet high on wardrobe · C (VENT) → far from the door.
- Fan low by the wardrobe aimed at the bed. Sensors in the same spots. Thermostat untouched.
- Firmware v2: band control uses a 60-s average (`o2_smooth` column); 30 s minimum between band switches.

## Band (set fresh each day from that day's baseline B = mean o2_avg over the 10-min baseline)
- Low line  L = B + 0.40   (type `L…`)
- High line H = B + 0.50   (type `H…`)
Why: at 10 L/min the room plateaus ~0.7–0.8 above baseline, so B+0.4–0.5 is reachable with
the valve cycling, and the 0.1 band is wider than the averaged noise.

## Each trial
1. Room is cycling in the band (mode `r` or `f`).
2. Wait for the valve to switch to **VENT (high)**. Start a timer.
3. At **+2:00**, type `?` (marker), then **open the barn door fully for 2:00**, then shut it.
   Stand in the doorway the same way each time.
4. Leave everything alone for **30 min** after the door shuts.
5. Switch mode for the next trial (`r` ↔ `f`). Alternate: r, f, r, f, …

Starting every trial at the same point (2 min after the valve turns off) is what makes the
comparison fair: in both modes the valve is OFF when the door opens, so the only difference is
when it turns back on.

## Boost time (feedforward)
First guess B = 180 s. After the first reactive trial, size it from the data:
- O2 lost to the door ≈ V × dip  (V = 59.7 m³, dip in %-points)
- Valve-on supply ≈ 0.59 %·m³/min at 10 L/min (~80 % effective purity, measured)
- Boost ≈ lost / supply − door-open time
Set it with `B<seconds>`. This is the on/off version of the gain derived from the mass balance
in the simulation.

## Measured for each trial (from the log, t = door opening)
- Max dip below L
- Minutes below L
- IAE: integral of |o2_avg − (L+H)/2| over 30 min
- Time until back inside the band

Report the per-trial numbers and the mean of each controller. With a handful of trials this is
an honest small-sample comparison, not a statistical claim.

## Same-day checks
- End the day with a ≥ 1-hour decay (concentrator off, logger running) to measure that day's leak rate.
- Note anything unusual with `?` + a written time (someone home, heat came on, etc.).
