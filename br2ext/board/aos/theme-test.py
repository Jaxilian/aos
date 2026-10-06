#!/usr/bin/env python3
"""The bar follows the theme file while the shell runs (boot-test.py
install first): Settings says "the desktop follows at once", and the
shell's palette used to be set once at its start. The working tree's
ade-shell is copied in over ssh and the session restarted on it.

  1. effects=chrome (the default): the bar is glass over the blurred
     wallpaper -- few of its pixels are the panel's own grey.
  2. ~/.config/aos/theme says effects=light: within seconds the bar is
     the opaque panel colour (most pixels the one grey), no restart.
  3. effects=chrome again: glass again.

Screendumps: theme-*. Serial transcript: theme.serial.txt."""
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
THEME = "/home/admin/.config/aos/theme"
BAR_H = 28
PANEL = (24, 24, 24)  # tgn's panel grey, 0.094 * 255


def bar_grey(tag):
    """The share of the bar's pixels that are the opaque panel colour."""
    s = bt.shot(tag, quiet=True)
    if s is None:
        return None
    from PIL import Image
    im = Image.open(os.path.join(bt.OUT, "%s.screen.png" % tag)).convert("RGB")
    w = im.size[0]
    px = [im.getpixel((x, y)) for y in range(2, BAR_H - 2) for x in range(0, w, 3)]
    grey = sum(1 for p in px if all(abs(p[i] - PANEL[i]) <= 3 for i in range(3)))
    return grey / max(1, len(px))


def set_theme(ser, text):
    ser.run("su -s /bin/sh admin -c \"mkdir -p %s; printf '%%s\\n' '%s' > %s\"; sleep 6" % (os.path.dirname(THEME), text, THEME))


def main():
    for p in (bt.SER, bt.MON):
        if os.path.exists(p):
            os.unlink(p)
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    q = subprocess.Popen(bt.qemu_command(), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    ok = True
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "theme.serial.txt"))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! no login prompt")
            return False
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)
        for _ in range(30):
            s = bt.shot("theme-boot", quiet=True)
            if s and s[0] >= 0.005:
                break
            time.sleep(2)
        ser.run("mkdir -p /root/new")
        if not dt.scp([os.path.join(TARGET, "ade-shell")], "/root/new/"):
            return False
        print("$ install\n%s" % ser.run("mv -f /root/new/ade-shell /usr/bin/; rm -f %s; systemctl restart ade; sleep 12; cat /etc/aos/theme" % THEME, timeout=60))
        a = bar_grey("theme-a-chrome")
        set_theme(ser, "effects=light")
        b = bar_grey("theme-b-light")
        set_theme(ser, "effects=chrome")
        c = bar_grey("theme-c-chrome")
        print("== bar pixels in the panel grey: chrome %.0f%%, light %.0f%%, chrome again %.0f%%" % (a * 100, b * 100, c * 100))
        if b < 0.5:
            print("!! the bar did not turn opaque under effects=light")
            ok = False
        if a > 0.3 or c > 0.3:
            print("!! the bar is not glass under effects=chrome")
            ok = False
        ser.run("rm -f %s" % THEME)
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
