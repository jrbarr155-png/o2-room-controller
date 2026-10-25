"""
log_serial.py — record the Arduino's CSV output to a file on laptop.

Usage:
    pip install pyserial
    python log_serial.py                       # lists serial ports
    python log_serial.py --port COM3 --run fill_01 --volume 32 --lpm 10
    python log_serial.py --port /dev/cu.usbmodem1101 --run ff_01 --cmd "L21.45;H21.55;f"

--cmd sends commands to the Arduino as soon as it has booted (opening the port
resets the Arduino, which always starts in vent mode). While logging can
also type a command (v, p, r, f, c, x, ?, L21.5 ...) and press Enter; it is sent
to the Arduino and the Arduino's reply is saved in the file.

Every run gets its own file in ./data/, named with the date and run name.
The first lines of the file record the run settings (room volume, flow, notes)
so the analysis script never has to guess. Press Ctrl+C to stop.

Close the Arduino IDE's Serial Monitor first — only one program can use the port.
"""
import argparse
import datetime as dt
import pathlib
import sys
import threading
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("Install pyserial first:  pip install pyserial")

ALARM_PCT = 23.0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", help="e.g. COM3 (Windows) or /dev/cu.usbmodem1101 (Mac)")
    p.add_argument("--run", default="test", help="short run name, e.g. fill_01, decay_01, door_03")
    p.add_argument("--volume", type=float, help="room volume in m^3 (length x width x height)")
    p.add_argument("--lpm", type=float, help="concentrator flowmeter setting, litres per minute")
    p.add_argument("--note", default="", help="anything worth remembering about this run")
    p.add_argument("--cmd", default="", help='commands to send after boot, separated by ";", e.g. "L21.45;H21.55;f"')
    a = p.parse_args()

    if not a.port:
        print("Serial ports found:")
        for port in list_ports.comports():
            print(f"  {port.device:25s} {port.description}")
        print("\nRe-run with --port <one of the above>.")
        return

    out_dir = pathlib.Path("data")
    out_dir.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    path = out_dir / f"{stamp}_{a.run}.csv"

    with serial.Serial(a.port, 115200, timeout=5) as ser, open(path, "w", newline="") as f:
        f.write(f"# run={a.run}\n# started={dt.datetime.now().isoformat(timespec='seconds')}\n")
        f.write(f"# volume_m3={a.volume}\n# lpm={a.lpm}\n# note={a.note}\n# cmd={a.cmd}\n")

        def send(cmd):
            cmd = cmd.strip()
            if cmd:
                ser.write((cmd + "\n").encode())
                print(f">>> sent: {cmd}")

        def keyboard():
            for typed in sys.stdin:
                send(typed)

        threading.Thread(target=keyboard, daemon=True).start()
        header_written = False
        print(f"Logging to {path}   (Ctrl+C to stop)")
        try:
            while True:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                if line.startswith("#"):
                    print(line)
                    f.write(line + "\n")
                    continue
                if line.startswith("ms,"):
                    if not header_written:
                        f.write("time_iso," + line + "\n")
                        header_written = True
                        time.sleep(0.2)
                        for c in a.cmd.split(";"):
                            send(c)
                    continue
                now = dt.datetime.now().isoformat(timespec="seconds")
                f.write(f"{now},{line}\n")
                f.flush()
                parts = line.split(",")
                if len(parts) >= 8:
                    ms, o2a, o2b, t, h, door, dp, alarm = parts[:8]
                    flag = "   <<< O2 ALARM: turn the unit OFF, open the door >>>" if alarm == "1" else ""
                    extra = ""
                    if len(parts) >= 12:
                        avg, valve, mode, why = parts[8:12]
                        extra = f"  avg={avg}%  valve={'ROOM' if valve == '1' else 'vent'}  mode={mode} ({why})"
                        if len(parts) >= 13:
                            extra += f"  1min={parts[12]}%"
                    print(f"{now}  O2 A={o2a:>6}%  B={o2b:>6}%  {t}C  {h}%RH  "
                          f"door={'OPEN ' if door == '1' else 'shut '}{extra}{flag}")
        except KeyboardInterrupt:
            print(f"\nStopped. Data saved to {path}")


if __name__ == "__main__":
    main()
