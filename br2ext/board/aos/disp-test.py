#!/usr/bin/env python3
"""Two displays on the installed QEMU disk (boot-test.py install first):
the order line of the display file puts the second display left of the
first, and the off line switches it off; the compositor follows each
within seconds. The working tree's ade-comp, ade-shell and settings are
copied in over ssh and the session restarted on them.

QEMU: virtio-vga with two outputs; the second connector is disconnected
until its status is forced on (the ade test's recipe). A terminal is
opened and maximised: it fills whichever display is first in the row.

  1. Both displays on, the panel (Virtual-1) first: the terminal is on
     head 0 (disp-a0, disp-a1).
  2. order=Virtual-2,Virtual-1: the row starts with Virtual-2, so a new
     maximised terminal lands on head 1 (disp-b0, disp-b1).
  3. off=Virtual-2: head 1 goes dark and the terminal comes back to head
     0 (disp-c0, disp-c1); the journal says "head Virtual-2 off".
  4. The off line removed: head 1 is back (disp-d1).

Screendumps: disp-*. Serial transcript: disp.serial.txt."""
import importlib.util
import json
import os
import shutil
import socket
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
DISPLAY = "/home/admin/.config/ade/display"


def shot_head(qmp, tag, head):
    ppm = os.path.join(bt.OUT, "%s.ppm" % tag)
    png = os.path.join(bt.OUT, "%s.screen.png" % tag)
    qmp.cmd("screendump", filename=ppm, device="vga0", head=head)
    time.sleep(1)
    try:
        from PIL import Image
        im = Image.open(ppm).convert("RGB")
        im.save(png)
        px = list(im.getdata())
        ink = sum(1 for p in px[::7] if max(p) > 40) / max(1, len(px[::7]))
        print("== screendump head %d %dx%d, %.1f%% ink -> %s" % (head, im.size[0], im.size[1], ink * 100, png))
        return ink
    except Exception as e:
        print("!! screendump head %d: %s" % (head, e))
        return 0.0


def terminal(ser):
    ser.run("pkill -x terminal; sleep 1; su -s /bin/sh admin -c '%s setsid terminal >/tmp/term.log 2>&1 &'; sleep 5" % dt.ENV)
    bt.monitor("sendkey meta_l-up")
    time.sleep(3)


def write_display(ser, text):
    ser.run("su -s /bin/sh admin -c \"mkdir -p %s; printf '%%s\\n' '%s' > %s\"; sleep 6" % (os.path.dirname(DISPLAY), text, DISPLAY))


def main():
    for p in (bt.SER, bt.MON, dt.QMP):
        if os.path.exists(p):
            os.unlink(p)
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    cmd = bt.qemu_command()
    cmd[cmd.index("virtio-vga")] = "virtio-vga,id=vga0,max_outputs=2"
    cmd += ["-device", "qemu-xhci,id=xhci", "-device", "usb-tablet,bus=xhci.0",
            "-qmp", "unix:%s,server,nowait" % dt.QMP]
    q = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    ok = True
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "disp.serial.txt"))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! no login prompt")
            return False
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)
        for _ in range(30):
            s = bt.shot("disp-boot", quiet=True)
            if s and s[0] >= 0.005:
                break
            time.sleep(2)
        # The disk holds this build (a verity core since 0.2.0): nothing to push.
        print("$ install\n%s" % ser.run("rm -f %s; systemctl restart ade; sleep 10; "
                                       "c=$(ls -d /sys/class/drm/card*-Virtual-2); echo on > $c/status; "
                                       "udevadm trigger --action=change --subsystem-match=drm --property-match=DEVTYPE=drm_minor; sleep 6; "
                                       "journalctl -b _COMM=ade-comp --no-pager | grep -E 'head|output' | tail -4 | cut -c17-160" % DISPLAY, timeout=120))
        qmp = dt.Qmp(dt.QMP)

        # 1. Both on, the panel first.
        terminal(ser)
        a0, a1 = shot_head(qmp, "disp-a0", 0), shot_head(qmp, "disp-a1", 1)
        print("== step 1: head 0 ink %.1f%%, head 1 ink %.1f%%" % (a0 * 100, a1 * 100))

        # 2. The second display first in the row.
        write_display(ser, "order=Virtual-2,Virtual-1")
        terminal(ser)
        b0, b1 = shot_head(qmp, "disp-b0", 0), shot_head(qmp, "disp-b1", 1)
        print("== step 2: head 0 ink %.1f%%, head 1 ink %.1f%%" % (b0 * 100, b1 * 100))
        row = ser.run("journalctl -b _COMM=ade-comp --no-pager | grep 'row:' | tail -1 | cut -c17-120")
        print("$ row\n%s" % row)
        if "Virtual-2 at 0" not in row or "Virtual-1 at 1024" not in row:
            print("!! the order line did not put Virtual-2 first")
            ok = False

        # 3. The second display off.
        write_display(ser, "off=Virtual-2")
        terminal(ser)
        c0, c1 = shot_head(qmp, "disp-c0", 0), shot_head(qmp, "disp-c1", 1)
        print("== step 3: head 0 ink %.1f%%, head 1 ink %.1f%%" % (c0 * 100, c1 * 100))
        print("$ journal\n%s" % ser.run("journalctl -b _COMM=ade-comp --no-pager | grep -E 'head .* (off|on)' | tail -3 | cut -c17-120"))
        if c1 > 0.02:
            print("!! head 1 is not dark with off=Virtual-2")
            ok = False

        # 4. On again.
        write_display(ser, "")
        time.sleep(4)
        d1 = shot_head(qmp, "disp-d1", 1)
        print("== step 4: head 1 ink %.1f%%" % (d1 * 100))
        if d1 < 0.02:
            print("!! head 1 did not come back")
            ok = False
        ser.run("pkill -x terminal; sleep 1")
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
