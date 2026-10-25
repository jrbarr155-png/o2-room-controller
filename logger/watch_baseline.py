"""
watch_baseline.py — tells you when the O2 baseline has gone flat.

Ran it in a SECOND Terminal tab while log_serial.py keeps logging in the first:
    cd ~/Downloads/o2_lab
    python3 watch_baseline.py

It only READS the newest data/*.csv file; it never touches the Arduino.
Every 20 s it looks at the last 10 minutes of the averaged O2 column and checks:
  - drift:  the straight-line trend over those 10 min is under 0.006 %/min
            (about 0.06 points over 10 min — smaller than the fill's starting slope)
  (it also prints the spread of 30-second averages, for information only)
When the drift check passes, it prints STABLE and says "baseline stable" through the speakers.
Ctrl+C to stop.
"""
import glob
import os
import subprocess
import time

WINDOW_MIN = 10.0
MAX_SLOPE = 0.006     # %O2 per minute
CHECK_EVERY_S = 20


def newest_csv():
    files = sorted(glob.glob("data/*.csv"), key=os.path.getmtime)
    return files[-1] if files else None


def read_avg(path):
    t, c = [], []
    with open(path) as f:
        for line in f:
            if line.startswith("#") or line.startswith("time_iso"):
                continue
            p = line.strip().split(",")
            if len(p) < 10:
                continue
            try:
                t.append(float(p[1]) / 60000.0)   # ms -> minutes
                c.append(float(p[9]))             # o2_avg column
            except ValueError:
                pass
    return t, c


def slope(t, c):
    n = len(t)
    mt, mc = sum(t) / n, sum(c) / n
    num = sum((ti - mt) * (ci - mc) for ti, ci in zip(t, c))
    den = sum((ti - mt) ** 2 for ti in t)
    return num / den if den else 0.0


def main():
    path = newest_csv()
    if not path:
        print("No CSV in data/ yet.")
        return
    print(f"Watching {path}  (Ctrl+C to stop)")
    announced = False
    while True:
        t, c = read_avg(path)
        if t and t[-1] - t[0] >= WINDOW_MIN:
            keep = [i for i, ti in enumerate(t) if ti >= t[-1] - WINDOW_MIN]
            tw, cw = [t[i] for i in keep], [c[i] for i in keep]
            s = slope(tw, cw)
            # 30-second block averages
            blocks, cur, start = [], [], tw[0]
            for ti, ci in zip(tw, cw):
                if ti - start >= 0.5:
                    blocks.append(sum(cur) / len(cur)); cur, start = [], ti
                cur.append(ci)
            if cur:
                blocks.append(sum(cur) / len(cur))
            spread = max(blocks) - min(blocks)
            ok = abs(s) < MAX_SLOPE   # spread is shown for info; the sensors wobble ~0.1 even when flat
            now = time.strftime("%H:%M:%S")
            print(f"{now}  last 10 min: mean={sum(cw)/len(cw):.3f}%  drift={s:+.4f} %/min  "
                  f"spread={spread:.3f}  -> {'STABLE' if ok else 'still settling'}")
            if ok and not announced:
                print("\n*** BASELINE STABLE: reconnect the tube, set 5.0 LPM, type ? in the logger tab ***\n")
                try:
                    subprocess.run(["say", "baseline stable"])
                except Exception:
                    print("\a")
                announced = True
            elif not ok:
                announced = False
        else:
            print("Waiting for 10 minutes of data...")
        time.sleep(CHECK_EVERY_S)


if __name__ == "__main__":
    main()
