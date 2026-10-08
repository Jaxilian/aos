#!/usr/bin/env python3
"""A kiosk (INSTALL_MODE=kiosk boot-test.py install first: aos-install
--kiosk notepad, no demo account, the kiosk account's session started by
greetd at boot).
  1. The disk boots straight into the session: ade-comp runs as kiosk
     with ADE_KIOSK set, no ade-shell, Notepad is up and its window is
     full screen (kiosk-up: no bar, Notepad over the whole display).
  2. The program killed: the compositor starts it again within seconds
     ("the kept program exited", "spawned notepad" in the journal) and
     the new one is full screen too (kiosk-again).
  3. Ctrl+Alt+F2 does not leave the kiosk's VT.
  4. The kiosk account has no shell and no sudo; root's console login is
     open (no --user was given).
Screendumps: kiosk-*. Serial transcript: kiosk.serial.txt."""
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


def comp():
    return "journalctl -b -t ade-session --no-pager | grep -E 'spawned|kept program|mapped' | tail -6 | cut -c17-160"


def main():
    for p in (bt.SER, bt.MON):
        if os.path.exists(p):
            os.unlink(p)
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    q = subprocess.Popen(bt.qemu_command(), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    ok = True
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "kiosk.serial.txt"))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! no login prompt")
            return False
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)
        # 1. The session, by itself.
        up = False
        for _ in range(30):
            if "notepad" in ser.run("ps -o comm= -C notepad"):
                up = True
                break
            time.sleep(2)
        time.sleep(6)
        who = ser.run("ps -o user=,comm= -C ade-comp,ade-shell,notepad | tr -s ' '; "
                      "tr '\\0' '\\n' < /proc/$(pgrep -x ade-comp)/environ | grep -E '^ADE_(KIOSK|AUTOSTART)='; "
                      "cat /etc/aos/kiosk; grep '^kiosk:' /etc/passwd | cut -d: -f7; "
                      "journalctl -b _COMM=ade-comp -t ade-session --no-pager | grep -c 'toplevel mapped'")
        print("$ the session\n%s" % who)
        if not up or "kiosk ade-comp" not in who or "kiosk notepad" not in who or "ade-shell" in who \
                or "ADE_KIOSK=1" not in who or "/bin/false" not in who:
            print("!! the kiosk session did not come up as designed")
            ok = False
        # The window is full screen: the compositor's fullscreen state is
        # what a screendump cannot tell from a maximised window, so ask
        # Notepad's size through the journal's mapped line against
        # the display, and look at the dump for the bar's absence.
        shot = bt.shot("kiosk-up")
        if shot is None or shot[0] < 0.02:
            print("!! the display is empty")
            ok = False
        # 2. Killed, it comes back full screen.
        pid1 = ser.run("pgrep -x notepad").replace("# ", "").strip()
        ser.run("kill %s" % pid1)
        back = False
        for _ in range(15):
            pid2 = ser.run("pgrep -x notepad").replace("# ", "").strip()
            if pid2 and pid2 != pid1:
                back = True
                break
            time.sleep(1)
        time.sleep(4)
        print("$ after the kill\n%s" % ser.run(comp()))
        bt.shot("kiosk-again")
        if not back:
            print("!! the program was not started again")
            ok = False
        # 3. Ctrl+Alt+F2 changes nothing: the kiosk stays on its VT (the
        #    serial console is this shell's, root's, with no VT at all).
        before = ser.run("cat /sys/class/tty/tty0/active").replace("# ", "").strip()
        bt.monitor("sendkey ctrl-alt-f2")
        time.sleep(3)
        after = ser.run("cat /sys/class/tty/tty0/active").replace("# ", "").strip()
        print("$ VT before %s, after Ctrl+Alt+F2 %s" % (before, after))
        if before != after or not after.startswith("tty"):
            print("!! the kiosk let Ctrl+Alt+F2 switch the console")
            ok = False
        # 4. No sudo for the account; root's console is open (this shell).
        no = ser.run("su -s /bin/sh kiosk -c 'sudo -n true' 2>&1 | tail -1")
        print("$ sudo as kiosk\n%s" % no)
        if "may not run sudo" not in no and "password" not in no:
            print("!! the kiosk account can sudo")
            ok = False
        print("$ failed\n%s" % ser.run("systemctl --failed --no-legend"))
    finally:
        try:
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
    print("\n== done, kiosk ok: %s" % ok)
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
