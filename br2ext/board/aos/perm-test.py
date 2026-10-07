#!/usr/bin/env python3
"""Software's package page with its Permissions section, and the
"installed; restart to finish" state, on the installed QEMU disk
(boot-test.py install first; Firefox installed there by disk-test.py).

The working tree's aos-store, settings and ade-shell are copied in over
ssh and the session restarted. Then: aos-store on Third-party, maximised,
the first tile clicked (Firefox) and the page screendumped -- the
Permissions rows must be there (perm-firefox); the updates file written
as aos-update leaves it after a write, and Update and AOS screendumped
(perm-update, perm-aos) -- Restart, not Upgrade system. Settings opened
on About for its Open Software button (perm-settings).

Screendumps: perm-*. Serial transcript: perm.serial.txt beside the disk.
PERM_TX/PERM_TY place the tile click for another screen size."""
import importlib.util
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = ["boot-test.py", "disk"]
spec = importlib.util.spec_from_file_location("bt", os.path.join(HERE, "boot-test.py"))
bt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bt)
spec = importlib.util.spec_from_file_location("dt", os.path.join(HERE, "disk-test.py"))
dt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dt)

TARGET = os.path.join(bt.BASE, "output", "target", "usr", "bin")
W, H = dt.W, dt.H


def open_store(ser, page, tag):
    ser.run("pkill -x aos-store; pkill -x settings; sleep 1")
    ser.run("su -s /bin/sh admin -c '%s setsid %s >/tmp/%s.log 2>&1 &'; sleep 7" % (dt.ENV, page, tag))
    bt.monitor("sendkey meta_l-up")
    time.sleep(4)
    dt.ink(tag)


def main():
    for p in (bt.SER, bt.MON, dt.QMP):
        if os.path.exists(p):
            os.unlink(p)
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    cmd = bt.qemu_command()
    cmd += ["-device", "qemu-xhci,id=xhci", "-device", "usb-tablet,bus=xhci.0",
            "-qmp", "unix:%s,server,nowait" % dt.QMP]
    q = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    ok = True
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "perm.serial.txt"))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! no login prompt")
            return False
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)
        for _ in range(30):
            s = bt.shot("perm-boot", quiet=True)
            if s and s[0] >= 0.005:
                break
            time.sleep(2)
        # The disk holds this build (a verity core since 0.2.0): nothing to push.
        print("$ install\n%s" % ser.run("systemctl restart ade; sleep 12; "
                                       "journalctl -b _COMM=ade-shell --no-pager | tail -3 | cut -c17-200; apm list | grep -c firefox", timeout=120))
        for _ in range(30):
            s = bt.shot("perm-desktop", quiet=True)
            if s and s[0] >= 0.005:
                break
            time.sleep(2)
        qmp = dt.Qmp(dt.QMP)

        open_store(ser, "aos-store third-party", "perm-third")
        tx, ty = int(os.environ.get("PERM_TX", 291)), int(os.environ.get("PERM_TY", 336))
        qmp.button("left", tx, ty)
        time.sleep(4)
        dt.ink("perm-firefox")
        if dt.changed("perm-third", "perm-firefox", 200, 60, W, H - 40) < 0.01:
            print("!! the tile click did not open a package page")
            ok = False

        # The state aos-update leaves behind after writing the idle slot.
        ser.run("mkdir -p /var/lib/aos; printf '1\\nAOS 9.9.9 is installed; restart to finish\\n' > /var/lib/aos/updates; chmod 644 /var/lib/aos/updates")
        open_store(ser, "aos-store update", "perm-update")
        open_store(ser, "aos-store aos", "perm-aos")
        open_store(ser, "settings about", "perm-settings")
        ser.run("rm -f /var/lib/aos/updates; pkill -x settings")
        ser.send("poweroff\n")
        ser.read_until(b"reboot: Power down", 90)
    finally:
        try:
            bt.monitor("quit")
        except OSError:
            pass
        try:
            q.wait(15)
        except subprocess.TimeoutExpired:
            q.kill()
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
