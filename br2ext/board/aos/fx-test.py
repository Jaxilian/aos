#!/usr/bin/env python3
"""The desktop's effects of 2026-10-06 on the installed QEMU disk
(boot-test.py install first). The working tree's ade-comp and ade-shell
are copied in over ssh and the session restarted on them.

  1. The quick panel (a click on the bar's right end) is glass:
     fx-quick, for the eye.
  2. A Notepad window dragged by its header to the left edge: while the
     button is held a pale ghost covers the left half of the zone
     (fx-ghost brighter than fx-open in the bottom-left strip).
  3. Minimize from the decoration: a screendump taken at once catches
     the window small near the bottom centre (fx-anim differs from
     fx-min-done there).
  4. Print: a toast; a click on it starts Images on the screenshot.

Screendumps: fx-*. Serial transcript: fx.serial.txt."""
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
MIN_X, DOT_Y = 1222, 46
# A new window: 3/5 of the zone, centred (lay.rs); its header is the
# first rows of its geometry.
WIN_X, WIN_Y = 256, 182


def mean(tag, box):
    from PIL import Image
    im = Image.open(os.path.join(bt.OUT, "%s.screen.png" % tag)).convert("L").crop(box)
    px = list(im.getdata())
    return sum(px) / max(1, len(px))


def notepad(ser, maximised):
    ser.run("pkill -x notepad; sleep 1; rm -f /home/admin/Untitled.txt")
    ser.run("su -s /bin/sh admin -c '%s setsid notepad >/tmp/notepad.log 2>&1 &'; sleep 6" % dt.ENV)
    if maximised:
        bt.monitor("sendkey meta_l-up")
        time.sleep(3)


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
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "fx.serial.txt"))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! no login prompt")
            return False
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)
        for _ in range(30):
            s = bt.shot("fx-boot", quiet=True)
            if s and s[0] >= 0.005:
                break
            time.sleep(2)
        # The disk holds this build (a verity core since 0.2.0): nothing to push.
        print("$ install\n%s" % ser.run("rm -rf /home/admin/Pictures/Screenshots; systemctl restart ade; sleep 12; echo restarted", timeout=60))
        qmp = dt.Qmp(dt.QMP)

        # 1. The quick panel.
        qmp.button("left", W - 30, 14)
        time.sleep(2)
        dt.ink("fx-quick")
        bt.monitor("sendkey esc")
        time.sleep(1)

        # 2. The ghost.
        notepad(ser, False)
        dt.ink("fx-open")
        qmp.move(WIN_X + 300, WIN_Y + 16)
        qmp.cmd("input-send-event", events=[{"type": "btn", "data": {"down": True, "button": "left"}}])
        time.sleep(0.3)
        for x in (500, 300, 120, 40, 4):
            qmp.move(x, 60)
        time.sleep(0.5)
        dt.ink("fx-ghost")
        qmp.cmd("input-send-event", events=[{"type": "btn", "data": {"down": False, "button": "left"}}])
        time.sleep(2)
        dt.ink("fx-snapped")
        strip = (0, H - 160, W // 2 - 10, H - 40)
        a, b = mean("fx-open", strip), mean("fx-ghost", strip)
        print("== bottom-left strip brightness: open %.1f, while dragging %.1f" % (a, b))
        if b < a + 6:
            print("!! no ghost over the left half while dragging")
            ok = False
        print("$ journal\n%s" % dt.journal(ser, "snapped", 2))

        # 3. The minimize animation.
        notepad(ser, True)
        dt.ink("fx-max")
        qmp.move(MIN_X, DOT_Y)
        qmp.cmd("input-send-event", events=[{"type": "btn", "data": {"down": True, "button": "left"}}])
        time.sleep(0.05)
        qmp.cmd("input-send-event", events=[{"type": "btn", "data": {"down": False, "button": "left"}}])
        time.sleep(0.06)
        qmp.cmd("screendump", filename=os.path.join(bt.OUT, "fx-anim.screen.ppm"))
        time.sleep(1.5)
        dt.ink("fx-min-done")
        try:
            from PIL import Image
            Image.open(os.path.join(bt.OUT, "fx-anim.screen.ppm")).convert("RGB").save(os.path.join(bt.OUT, "fx-anim.screen.png"))
            dock = dt.changed("fx-anim", "fx-min-done", W // 2 - 220, H - 260, W // 2 + 220, H - 10)
            whole = dt.changed("fx-anim", "fx-max", 0, 40, W, H - 300)
            print("== mid-animation: dock region differs from the end by %.1f%%, the window area from the start by %.1f%%" % (dock * 100, whole * 100))
            if dock < 0.01:
                print("!! nothing small near the dock during the minimize (timing, or no animation)")
                ok = False
        except Exception as e:
            print("!! fx-anim: %s" % e)
            ok = False
        print("$ journal\n%s" % dt.journal(ser, "minimized|restored", 2))

        # 4. The screenshot toast.
        dt.ink("fx-before-shot")
        bt.monitor("sendkey print")
        # The toast holds six seconds (ade v0.1.47); the dump takes two
        # and a half, so the click comes at about four.
        time.sleep(1)
        dt.ink("fx-toast")
        toast = dt.changed("fx-before-shot", "fx-toast", W - 400, 20, W, 140)
        print("== toast region changed %.2f%%" % (toast * 100))
        qmp.button("left", W - 180, 70)
        time.sleep(6)
        after = ser.run("ls /home/admin/Pictures/Screenshots; pgrep -a images; journalctl -b _SYSTEMD_UNIT=ade.service + SYSLOG_IDENTIFIER=ade-session --no-pager | grep -i 'launch' | tail -1 | cut -c17-160")
        print("$ after the click\n%s" % after)
        dt.ink("fx-images")
        if toast < 0.01 or "images " not in after or "Screenshots/" not in after:
            print("!! the screenshot toast did not open the picture in Images")
            ok = False
        ser.run("pkill -x images; pkill -x notepad; sleep 1")
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
