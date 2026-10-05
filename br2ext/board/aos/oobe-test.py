#!/usr/bin/env python3
"""The first boot of an installation made without an account
(INSTALL_MODE=oobe boot-test.py install first): the session belongs to
the locked setup user and shows "Welcome to AOS"; the helper then makes
the owner and the desktop restarts as them.

  1. The disk boots; root's console login still works (nothing else
     could log in yet). The desktop is up as `setup` with aos-setup's
     window (oobe-welcome).
  2. aos-setup --first-boot --user tester --pass secret-1 --go, started
     as the setup user the way the window would: aos-firstboot runs
     through the one sudoers line; the journal shows its stages.
  3. Within half a minute the desktop restarts as tester (oobe-owner);
     /etc/aos/oobe and the sudoers line are gone, root is locked.
  4. tester logs in on the serial console with the password and sudo
     asks for it (an owner, not the live account).

Afterwards the disk is tester's: run boot-test.py install again before
the other disk tests, which log in as the demo account.
Screendumps: oobe-*. Serial transcript: oobe.serial.txt."""
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

USER, PASS = "tester", "secret-1"
ENV = ("WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/$(id -u setup) HOME=/var/lib/aos-setup "
       "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u setup)/bus")


def main():
    for p in (bt.SER, bt.MON):
        if os.path.exists(p):
            os.unlink(p)
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    q = subprocess.Popen(bt.qemu_command(), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    ok = True
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "oobe.serial.txt"))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! no login prompt")
            return False
        ser.send("root\n")
        if ser.read_until(b"# ", 30) is None:
            print("!! root could not log in before the owner exists")
            return False
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)
        for _ in range(30):
            s = bt.shot("oobe-boot", quiet=True)
            if s and s[0] >= 0.005:
                break
            time.sleep(2)
        time.sleep(8)
        state = ser.run("cat /etc/aos/oobe >/dev/null 2>&1 && echo marker; ps -o user= -C ade-shell; pgrep -a aos-setup | head -2; "
                        "cat /etc/sudoers.d/30-aos-oobe; id setup; id admin 2>&1 | head -1")
        print("$ before\n%s" % state)
        bt.shot("oobe-welcome")
        if "setup" not in state or "aos-setup" not in state or "NOPASSWD" not in state:
            print("!! the first boot did not come up as the setup user with the welcome window")
            ok = False

        # 2. The answers given up front, as the window would after Finish.
        print("$ first boot\n%s" % ser.run(
            "su -s /bin/sh setup -c '%s aos-setup --first-boot --user %s --pass %s --go >/tmp/oobe.log 2>&1 &'; "
            "for i in $(seq 40); do grep -q 'AOS is yours' /tmp/oobe.log 2>/dev/null && break; sleep 1; done; "
            "grep -E '>>>|AOS is yours|aos-firstboot' /tmp/oobe.log | head -8" % (ENV, USER, PASS), timeout=120))
        # 3. The desktop restarts as the owner; the setup account goes.
        time.sleep(40)
        after = ser.run("ps -o user= -C ade-shell; test -e /etc/aos/oobe && echo marker || echo no-marker; "
                        "test -e /etc/sudoers.d/30-aos-oobe && echo sudoers || echo no-sudoers; "
                        "id %s | cut -c1-80; id setup 2>&1 | head -1; passwd -S root | cut -d' ' -f1-2; ls /etc/sudoers.d; "
                        "grep User= /etc/systemd/system/ade.service.d/10-aos-user.conf" % USER)
        print("$ after\n%s" % after)
        bt.shot("oobe-owner")
        if USER not in after.split("\n")[0] or "no-marker" not in after or "no-sudoers" not in after:
            print("!! the desktop is not the owner's, or the first boot's road is still open")
            ok = False
        if "root L" not in after and "root LK" not in after:
            print("!! root's console login is not locked")
            ok = False
        ser.send("exit\n")
        time.sleep(2)
        # 4. The owner on the console, and sudo asking for the password.
        if ser.read_until(b"login:", 30) is None:
            print("!! no login prompt after root's logout")
            ok = False
        else:
            ser.send(USER + "\n")
            if ser.read_until(b"Password:", 30) is None:
                print("!! no password prompt for %s" % USER)
                ok = False
            else:
                ser.send(PASS + "\n")
                if ser.read_until(b"$ ", 30) is None:
                    print("!! %s could not log in" % USER)
                    ok = False
                else:
                    ser.send("stty -echo cols 200 rows 50\n")
                    ser.read_until(b"$ ", 10)
                    r = ser.run("ls /etc/sudoers.d; sudo -n true >/dev/null 2>&1; echo asks=$?; printf '%%s\\n' '%s' | sudo -S -p '' id -u" % PASS)
                    print("$ as %s\n%s" % (USER, r))
                    if "asks=1" not in r or r.strip().split("\n")[-1].strip() != "0":
                        print("!! sudo does not ask %s's password, or refuses it" % USER)
                        ok = False
                    ser.send("sudo -n poweroff 2>/dev/null || printf '%s\\n' '" + PASS + "' | sudo -S -p '' poweroff\n")
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
