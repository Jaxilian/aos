#!/usr/bin/env python3
"""The performance baseline, on the live ISO in QEMU: seconds from QEMU's
start to the serial login prompt and to the first window on screen,
memory at idle (MemAvailable and the session's biggest processes), and
the time each of the terminal, notepad and files takes to put its first
window up. QEMU numbers are QEMU numbers -- llvmpipe, four cores -- so
they are for comparison between releases, not for a laptop. Written to
output/images/perf.json and printed as a table; docs/performance.md
keeps one row per release."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = ["boot-test.py", "desktop"]
spec = importlib.util.spec_from_file_location("bt", os.path.join(HERE, "boot-test.py"))
bt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bt)

ENV = ("WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/1000 HOME=/home/admin "
       "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus")
APPS = ["terminal", "notepad", "files"]


def first_window(ser, app):
    """Seconds from starting `app` to the compositor mapping its window, by
    the guest's own clock: the launch time taken just before, the journal's
    timestamp of the next "toplevel mapped" line after it. A screendump
    costs seconds, so the screen is no clock for this."""
    t0 = ser.run("echo; date +%s.%N").strip().splitlines()[-1].strip()
    ser.run("su -s /bin/sh admin -c '%s setsid %s >/tmp/perf-%s.log 2>&1 &'" % (ENV, app, app))
    for _ in range(60):
        time.sleep(1)
        out = ser.run("echo; journalctl -b _COMM=ade-comp --no-pager -o short-unix --since=@%s 2>/dev/null | grep 'toplevel mapped' | head -1 | cut -d' ' -f1" % t0.split('.')[0])
        line = out.strip().splitlines()[-1].strip()
        try:
            t1 = float(line)
        except ValueError:
            continue
        if t1 >= float(t0):
            return round(t1 - float(t0), 2)
    return None


def main():
    for p in (bt.SER, bt.MON):
        if os.path.exists(p):
            os.unlink(p)
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    r = {"version": None, "boot_to_login_s": None, "boot_to_desktop_s": None, "mem_available_mb": None, "top_rss": [], "first_window_s": {}}
    t_start = time.time()
    q = subprocess.Popen(bt.qemu_command(), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "perf.serial.txt"))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! no login prompt")
            return False
        r["boot_to_login_s"] = round(time.time() - t_start, 1)
        # The desktop: the first ink on the screen.
        while time.time() - t_start < 180:
            s = bt.shot("perf-desktop", quiet=True)
            if s and s[0] >= 0.005:
                r["boot_to_desktop_s"] = round(time.time() - t_start, 1)
                break
            time.sleep(0.5)
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)
        ser.run("true")
        r["version"] = ser.run("echo; sed -n 's/^VERSION_ID=//p' /etc/os-release").strip().splitlines()[-1].strip()
        # Idle, once the session has settled.
        time.sleep(15)
        mem = ser.run("echo; awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo; ps -eo rss,comm --sort=-rss | head -9 | tail -8")
        lines = [l.strip() for l in mem.strip().splitlines() if l.strip() and not l.startswith("#")]
        if lines:
            try:
                r["mem_available_mb"] = int(lines[0])
            except ValueError:
                pass
            for l in lines[1:]:
                parts = l.split(None, 1)
                if len(parts) == 2 and parts[0].isdigit():
                    r["top_rss"].append([parts[1], int(parts[0]) // 1024])
        analyze = ser.run("echo; systemd-analyze; systemd-analyze critical-chain --no-pager 2>&1 | head -14; echo; systemd-analyze blame --no-pager 2>&1 | head -10", timeout=60)
        r["analyze"] = analyze.strip()
        print("$ systemd-analyze; critical-chain; blame\n" + analyze)
        # Each app's first window: the autostarted terminal is closed first.
        ser.run("pkill -x terminal; sleep 2")
        for app in APPS:
            r["first_window_s"][app] = first_window(ser, app)
            ser.run("pkill -x %s; sleep 2" % app)
        ser.send("poweroff\n")
        ser.read_until(b"reboot: Power down", 90)
    finally:
        try:
            bt.monitor("quit")
        except OSError:
            pass
        try:
            q.wait(10)
        except subprocess.TimeoutExpired:
            q.kill()
    iso = os.path.join(bt.IMG, "rootfs.iso9660")
    tar = os.path.join(bt.IMG, "rootfs.tar.xz")
    r["iso_mb"] = os.path.getsize(iso) // (1024 * 1024) if os.path.exists(iso) else None
    r["root_tar_mb"] = os.path.getsize(tar) // (1024 * 1024) if os.path.exists(tar) else None
    with open(os.path.join(bt.OUT, "perf.json"), "w") as f:
        json.dump(r, f, indent=2)
    print("\n== AOS %s in QEMU" % r["version"])
    print("boot to login      %s s" % r["boot_to_login_s"])
    print("boot to desktop    %s s" % r["boot_to_desktop_s"])
    print("memory available   %s MB at idle" % r["mem_available_mb"])
    for name, mb in r["top_rss"]:
        print("  %-18s %4d MB" % (name, mb))
    for app in APPS:
        print("first window %-8s %s s" % (app, r["first_window_s"].get(app)))
    print("ISO %s MB, root tarball %s MB" % (r["iso_mb"], r["root_tar_mb"]))
    return r["boot_to_desktop_s"] is not None


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
