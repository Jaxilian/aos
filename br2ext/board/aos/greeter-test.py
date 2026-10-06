#!/usr/bin/env python3
"""The login screen (INSTALL_MODE=owner boot-test.py install first: the
account OWNER with password LUKS_PASS, no demo account, greetd enabled).

  1. The disk boots to greetd: ade-comp runs as the greeter account with
     ade-greeter, the one account is listed (greeter-screen).
  2. A wrong password: the greeter says so and stays (greeter-wrong).
  3. The right one: greetd starts the owner's session; within half a
     minute ade-comp and ade-shell run as the owner, logind's seat0
     session is the owner's, and the greeter's compositor is gone
     (greeter-desktop).

Screendumps: greeter-*. Serial transcript: greeter.serial.txt."""
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


def main():
    for p in (bt.SER, bt.MON):
        if os.path.exists(p):
            os.unlink(p)
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    q = subprocess.Popen(bt.qemu_command(), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    ok = True
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "greeter.serial.txt"))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! no login prompt")
            return False
        # root's console login is locked on an owned machine; the owner
        # logs in on the serial line and reads the system with sudo.
        ser.send(bt.OWNER + "\n")
        if ser.read_until(b"Password:", 30) is None:
            print("!! no password prompt for %s" % bt.OWNER)
            return False
        ser.send(bt.LUKS_PASS + "\n")
        if ser.read_until(b"$ ", 30) is None:
            print("!! %s could not log in on the console" % bt.OWNER)
            return False
        ser.send("stty -echo cols 200 rows 50\n")
        ser.read_until(b"$ ", 10)
        time.sleep(15)
        sudo = "printf '%%s\\n' '%s' | sudo -S -p '' " % bt.LUKS_PASS
        state = ser.run(sudo + "sh -c 'systemctl is-active greetd ade; ps -o user=,comm= -p $(pgrep -x ade-comp) $(pgrep -x ade-greeter); loginctl list-sessions --no-pager --no-legend'")
        print("$ before\n%s" % state)
        bt.shot("greeter-screen")
        if "greeter" not in state or "ade-greeter" not in state:
            print("!! greetd did not bring up the greeter's compositor with ade-greeter")
            ok = False

        # 2. A wrong password, then the right one, typed on the screen.
        bt.typekeys("wrong-0\n")
        time.sleep(6)
        bt.shot("greeter-wrong")
        still = ser.run("pgrep -a ade-greeter | head -1")
        if "ade-greeter" not in still:
            print("!! the greeter went away on a wrong password")
            ok = False
        bt.typekeys(bt.LUKS_PASS + "\n")
        time.sleep(25)
        after = ser.run(sudo + "sh -c 'ps -o user=,comm= -p $(pgrep -x ade-comp) $(pgrep -x ade-shell) 2>/dev/null; pgrep -a ade-greeter; loginctl list-sessions --no-pager --no-legend; journalctl -b -u greetd --no-pager | tail -4 | cut -c17-140'")
        print("$ after the login\n%s" % after)
        bt.shot("greeter-desktop")
        flat = " ".join(after.split())
        if ("%s ade-comp" % bt.OWNER) not in flat or ("%s ade-shell" % bt.OWNER) not in flat:
            print("!! the owner's session did not start")
            ok = False
        if "ade-greeter" in after:
            print("!! the greeter is still running beside the session")
            ok = False
        ser.send(sudo + "poweroff\n")
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
