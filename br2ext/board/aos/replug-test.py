#!/usr/bin/env python3
"""A second display plugged in, unplugged and plugged back in, on the
live ISO (the keyed build). The G14's USB-C monitor came back black on
0.2.7 (2026-10-07). The connector of the two-output virtio GPU is forced
on and off and the change announced like a cable's.

  1. Plugged in: the shell's bar and wallpaper on head 1 (replug-a).
  2. Unplugged and back: the same again (replug-b), and the journals of
     the compositor and the shell for the eye.

Screendumps: replug-*. Serial transcript: replug.serial.txt."""
import importlib.util
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("at", os.path.join(HERE, "ade-test.py"))
at = importlib.util.module_from_spec(spec)
spec.loader.exec_module(at)
bt = at.bt

TRIGGER = "udevadm trigger --action=change --subsystem-match=drm --property-match=DEVTYPE=drm_minor"


def main():
    for p in (bt.SER, bt.MON, at.QMP):
        if os.path.exists(p):
            os.unlink(p)
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    cmd = bt.qemu_command()
    cmd[cmd.index("virtio-vga")] = "virtio-vga,id=vga0,max_outputs=2"
    cmd += ["-device", "usb-mouse,bus=xhci.0", "-qmp", "unix:%s,server,nowait" % at.QMP]
    q = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    ok = True
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "replug.serial.txt"))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! no login prompt")
            return False
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)
        for _ in range(30):
            s = bt.shot("replug-boot", quiet=True)
            if s and s[0] >= 0.005:
                break
            time.sleep(2)
        qmp = at.Qmp(at.QMP)
        print("$ plug\n%s" % ser.run("c=$(ls -d /sys/class/drm/card*-Virtual-2); echo on > $c/status; %s; sleep 8; "
                                     "journalctl -b _COMM=ade-comp --no-pager | grep -E 'head ' | cut -c17-120" % TRIGGER, timeout=60))
        a = at.dump2(qmp, "replug-a", 1)
        print("== head 1 plugged: ink %.1f%%" % (a * 100))
        if a < 0.005:
            print("!! no bar on the second display")
            ok = False
        print("$ unplug\n%s" % ser.run("c=$(ls -d /sys/class/drm/card*-Virtual-2); echo off > $c/status; %s; sleep 6; "
                                       "journalctl -b _COMM=ade-comp --no-pager | tail -6 | cut -c17-160" % TRIGGER, timeout=60))
        print("$ replug\n%s" % ser.run("c=$(ls -d /sys/class/drm/card*-Virtual-2); echo on > $c/status; %s; sleep 12; "
                                       "journalctl -b _COMM=ade-comp --no-pager | tail -12 | cut -c17-160; "
                                       "echo --shell; journalctl -b _COMM=ade-shell --no-pager | tail -8 | cut -c17-160; "
                                       "echo --outputs; cat /sys/class/drm/card*-Virtual-2/status" % TRIGGER, timeout=60))
        b = at.dump2(qmp, "replug-b", 1)
        print("== head 1 after the replug: ink %.1f%%" % (b * 100))
        if b < 0.005:
            print("!! no bar on the second display after it came back")
            ok = False
        bt.shot("replug-head0")
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
    print("\n== done, ok: %s" % ok)
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
