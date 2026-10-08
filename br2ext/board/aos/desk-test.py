#!/usr/bin/env python3
"""The desktop's new pieces on the installed QEMU disk (boot-test.py
install first): Notepad's in-window question when closed with unsaved
text, a window minimized from its decoration and brought back from the
overview's dock, and the dock's right-click menu with its close marks.

The working tree's ade-comp, ade-shell and notepad are copied in over
ssh and the session restarted on them. Clicks go through QMP on a
1280x800 screen; a maximised window's decoration dots sit at y 46,
minimize at x 1222 and close at x 1266.

  1. notepad, maximised, "abc" typed, the close dot: the dialog must be
     on screen (desk-dialog). With DESK_DX/DESK_DY (the "Don't Save"
     button, read off that dump) it is clicked and the window must go.
  2. notepad again, the minimize dot: the window must leave the screen
     (desk-min); Super, then a right click on the first dock icon: the
     menu (desk-menu); a click on its first row: the window is back
     (desk-back).

Screendumps: desk-*. Serial transcript: desk.serial.txt."""
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
MIN_X, CLOSE_X, DOT_Y = 1222, 1266, 46


def notepad(ser):
    ser.run("pkill -x notepad; sleep 1; rm -f /home/admin/Untitled.txt")
    ser.run("su -s /bin/sh admin -c '%s setsid notepad >/tmp/notepad.log 2>&1 &'; sleep 6" % dt.ENV)
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
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "desk.serial.txt"))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! no login prompt")
            return False
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)
        for _ in range(30):
            s = bt.shot("desk-boot", quiet=True)
            if s and s[0] >= 0.005:
                break
            time.sleep(2)
        # The disk holds this build (a verity core since 0.2.0): nothing to push.
        print("$ install\n%s" % ser.run("systemctl restart ade; sleep 12; "
                                       "journalctl -b _COMM=ade-comp --no-pager | tail -2 | cut -c17-160", timeout=120))
        for _ in range(30):
            s = bt.shot("desk-desktop", quiet=True)
            if s and s[0] >= 0.005:
                break
            time.sleep(2)
        qmp = dt.Qmp(dt.QMP)

        # 1. Unsaved text, then the close dot: the question.
        notepad(ser)
        for k in "abc":
            bt.monitor("sendkey %s" % k)
            time.sleep(0.2)
        time.sleep(1)
        dt.ink("desk-typed")
        # The lights are the compositor's (ade v0.1.58, aos-sdk v0.4.18),
        # laid over the right end of Notepad's own strip at the top of
        # the zone; the strip's menus (File) are at its left, and the
        # content below the lights has no light of its own.
        shot = bt.shot("desk-header", quiet=True)
        if shot is not None:
            raw = shot[1]
            def px(x, y):
                i = (y * 1280 + x) * 3
                return raw[i], raw[i + 1], raw[i + 2]
            light = px(CLOSE_X, DOT_Y)
            below = px(CLOSE_X, DOT_Y + 36)
            title = any(px(x, DOT_Y)[0] > 150 for x in range(12, 90))
            print("== header: close light %r, below it %r, menu drawn %s" % (light, below, title))
            if not (light[0] > 180 and light[1] < 140) or below[0] > 120 or not title:
                print("!! the compositor's header is not where the lights and the title should be")
                ok = False
        qmp.button("left", CLOSE_X, DOT_Y)
        time.sleep(3)
        dt.ink("desk-dialog")
        alive = ser.run("pgrep -x notepad >/dev/null && echo alive || echo gone").strip()
        print("== after the close dot: notepad %s" % alive)
        if "alive" not in alive:
            print("!! notepad closed without asking")
            ok = False
        dx, dy = os.environ.get("DESK_DX"), os.environ.get("DESK_DY")
        if dx and dy:
            qmp.button("left", int(dx), int(dy))
            time.sleep(3)
            gone = ser.run("pgrep -x notepad >/dev/null && echo alive || echo gone").strip()
            print("== after Don't Save: notepad %s" % gone)
            if "gone" not in gone:
                print("!! Don't Save did not close the window")
                ok = False
        else:
            print("== set DESK_DX/DESK_DY from desk-dialog.screen.png for the Don't Save click")
            ser.run("pkill -x notepad; sleep 1")

        # 2. Minimize, and back through the dock's menu.
        notepad(ser)
        dt.ink("desk-open")
        qmp.button("left", MIN_X, DOT_Y)
        time.sleep(3)
        dt.ink("desk-min")
        print("$ journal\n%s" % ser.run("journalctl -b _COMM=ade-comp --no-pager | grep -E 'minimized|restored' | tail -3 | cut -c17-120"))
        if dt.changed("desk-open", "desk-min", 200, 60, W - 200, H - 60) < 0.05:
            print("!! the window did not leave the screen")
            ok = False
        bt.monitor("sendkey meta_l")
        time.sleep(3)
        dt.ink("desk-over")
        # The dock: centred at the bottom of the overview panel.
        dock_y = H - 20 - 24
        qmp.button("right", W // 2, dock_y)
        time.sleep(2)
        dt.ink("desk-menu")
        if dt.changed("desk-over", "desk-menu", W // 2 - 200, dock_y - 200, W // 2 + 200, dock_y) < 0.005:
            print("!! no menu on the right click")
            ok = False
        # The first row of the menu: the popup's rows sit above the dock,
        # the window rows first and "Close all" last; row 0 is two rows
        # up from the dock (the menu dump of 2026-10-05 had it at y 668).
        qmp.button("left", W // 2 - 60, dock_y - 12 - 30 - 15 - 30)
        time.sleep(3)
        dt.ink("desk-back")
        print("$ journal\n%s" % ser.run("journalctl -b _COMM=ade-comp --no-pager | grep -E 'minimized|restored' | tail -3 | cut -c17-120"))
        if dt.changed("desk-min", "desk-back", 200, 60, W - 200, H - 60) < 0.05:
            print("!! the window did not come back")
            ok = False
        ser.run("pkill -x notepad; sleep 1")
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
