#!/usr/bin/env python3
"""Screenshots, on the installed QEMU disk (boot-test.py install first):
the working tree's ade-comp and ade-shell copied in over ssh and the
session restarted on them (as disk-test.py does), a terminal opened, then
Print (the display) and Shift+Print (the focused window) sent through
QEMU's monitor. Two PNGs must appear in ~/Pictures/Screenshots, the first
the display's size, the second smaller; both are copied back beside the
disk image as shot-display.png and shot-window.png to be looked at."""
import importlib.util
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = ["boot-test.py", "disk"]
spec = importlib.util.spec_from_file_location("ut", os.path.join(HERE, "update-test.py"))
ut = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ut)
bt = ut.bt

TARGET = os.path.join(bt.BASE, "output", "target", "usr", "bin")
KEY = os.path.expanduser("~/.ssh/id_ed25519")
SSH = ["-P", str(bt.SSH_PORT), "-i", KEY, "-o", "StrictHostKeyChecking=no",
       "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes"]
ENV = ("WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/1000 HOME=/home/admin "
       "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus")
DIR = "/home/admin/Pictures/Screenshots"


def scp(args):
    for _ in range(8):
        r = subprocess.run(["scp"] + SSH + args, capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            return True
        time.sleep(5)
    print("!! scp: %s" % (r.stdout + r.stderr).strip())
    return False


def main():
    ok = True
    for p in (bt.SER, bt.MON):
        if os.path.exists(p):
            os.unlink(p)
    import shutil
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    q = subprocess.Popen(bt.qemu_command(), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "shot.serial.txt"))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! no login prompt")
            return False
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)
        print(ser.run("for i in $(seq 20); do systemctl is-active sshd >/dev/null && break; sleep 3; done; mkdir -p /root/new", timeout=120))
        if not scp([os.path.join(TARGET, b) for b in ("ade-comp", "ade-shell")] + ["root@127.0.0.1:/root/new/"]):
            return False
        print(ser.run("mv -f /root/new/* /usr/bin/; rm -rf %s; systemctl restart ade; sleep 15; echo restarted" % DIR, timeout=120))
        ser.run("su -s /bin/sh admin -c '%s setsid terminal >/tmp/t.log 2>&1 &'; sleep 10" % ENV, timeout=60)
        bt.monitor("sendkey print")
        time.sleep(6)
        bt.monitor("sendkey shift-print")
        time.sleep(6)
        out = ser.run("ls -l %s; journalctl -b _COMM=ade-comp --no-pager | grep -i screenshot | tail -3" % DIR)
        print("\n$ ls %s\n%s" % (DIR, out))
        files = [l.split()[-1] for l in out.splitlines() if l.strip().endswith(".png")]
        if len(out.splitlines()) < 2 or out.count(".png") < 2:
            print("!! expected two screenshots")
            ok = False
        else:
            names = ser.run("ls %s | head -2" % DIR).replace("# ", "").splitlines()
            for local, name in zip(("shot-display.png", "shot-window.png"), names):
                scp(["root@127.0.0.1:%s/%s" % (DIR, name.strip().replace(" ", "\\ ")), os.path.join(bt.OUT, local)])
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
    return ok


if __name__ == "__main__":
    ok = main()
    print("\n== done, screenshots ok:", ok)
    sys.exit(0 if ok else 1)
