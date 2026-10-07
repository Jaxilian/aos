#!/usr/bin/env python3
"""The login screen (INSTALL_MODE=owner boot-test.py install first: the
account OWNER with password LUKS_PASS, no demo account, greetd enabled).

  1. The disk boots to greetd: ade-comp runs as the greeter account with
     ade-greeter, the one account is listed (greeter-screen).
  2. A wrong password: the greeter says so and stays (greeter-wrong).
     The right one: greetd starts the owner's session; within half a
     minute ade-comp and ade-shell run as the owner, logind's seat0
     session is the owner's, and the greeter's compositor is gone
     (greeter-desktop).
  3. Super+L locks; a volume key's OSD comes and goes while the password
     is typed; the right one unlocks (greeter-locked, greeter-unlocked).
  4. The session's output is in the journal (-t ade-session, -t
     ade-greeter): greetd gives a session the VT, and the script sends
     it to the journal instead.
  5. The compositor killed while locked: the session script starts it
     again and it comes back locked, with the crash in the journal
     (greeter-relocked); the password unlocks.
  6. Killed four more times: the script gives up, the greeter is back,
     the crash lines wait under /run/aos/session (greeter-again); the
     next login finds them and the shell's toast says so
     (greeter-crash-toast).

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
        # The autologin service must not have been pulled in beside greetd:
        # the two conflict, and on the G14 it won the race and crashed.
        ade = ser.run(sudo + "systemctl is-active ade.service; systemctl show -p NRestarts --value ade.service").strip().split("\n")[-2:]
        print("$ ade.service: %s" % " ".join(x.strip().lstrip("# ") for x in ade))
        if "inactive" not in " ".join(ade):
            print("!! ade.service ran on an owned machine (the greeter's conflict)")
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

        # 3. The lock screen, with a layer coming and going while it is
        #    up: Super+L, then a volume key (the shell's OSD shows for
        #    1.5 s and unmaps), then the password. The unmap used to
        #    refocus the top window, and the locker got nothing after
        #    its first character (the G14, 2026-10-07).
        bt.monitor("sendkey meta_l-l")
        time.sleep(6)
        bt.shot("greeter-locked")
        locked = ser.run("pgrep -a ade-lock | head -1")
        if "ade-lock" not in locked:
            print("!! Super+L did not start the locker")
            ok = False
        bt.monitor("sendkey volumeup")
        time.sleep(1)
        bt.typekeys(bt.LUKS_PASS[:1])
        time.sleep(3)
        bt.typekeys(bt.LUKS_PASS[1:] + "\n")
        time.sleep(6)
        bt.shot("greeter-unlocked")
        still = ser.run("pgrep -a ade-lock | head -1; journalctl -b _COMM=ade-comp --no-pager | grep -E 'lock' | tail -3 | cut -c17-120")
        print("$ after the unlock\n%s" % still)
        if "ade-lock" in still:
            print("!! the locker is still up: the password did not reach it")
            ok = False

        # 4. What the session said is in the journal, not on the VT.
        logs = ser.run(sudo + "sh -c 'journalctl -b -t ade-session --no-pager | wc -l; journalctl -b -t ade-greeter --no-pager | wc -l; journalctl -b -t ade-session --no-pager | tail -3 | cut -c17-140'")
        print("$ session journal\n%s" % logs)
        counts = [l.strip().lstrip("#$ ") for l in logs.split("\n") if l.strip().lstrip("#$ ").isdigit()]
        if len(counts) < 2 or counts[0] == "0" or counts[1] == "0":
            print("!! the session's or the greeter's output is not in the journal: %r" % counts)
            ok = False

        # 5. The compositor killed while locked: back, and locked. The
        #    owner's compositor only (-u): the greeter's has its own.
        bt.monitor("sendkey meta_l-l")
        time.sleep(5)
        killed = ser.run(sudo + "sh -c 'pkill -KILL -x -u %s ade-comp; sleep 14; echo LOCK:$(pgrep -c -x ade-lock); ps -o user=,comm= -p $(pgrep -x ade-comp); journalctl -b -t ade-session --no-pager | grep -E \"was locked|previous session|giving up\" | tail -3 | cut -c17-160'" % bt.OWNER, timeout=40)
        print("$ killed while locked\n%s" % killed)
        bt.shot("greeter-relocked")
        if "LOCK:1" not in killed or "was locked" not in killed or "previous session" not in killed:
            print("!! the compositor did not come back locked after the kill")
            ok = False
        bt.typekeys(bt.LUKS_PASS + "\n")
        time.sleep(6)
        still = ser.run("pgrep -a ade-lock | head -1")
        if "ade-lock" in still:
            print("!! the locker is still up after the restart: the password did not reach it")
            ok = False

        # 6. Four more kills within the two minutes, each once the
        #    compositor is back: the script gives up and greetd shows the
        #    greeter; the lines wait for the next login, which toasts them.
        gone = ser.run(sudo + "sh -c 'for i in 1 2 3 4; do for t in $(seq 20); do pgrep -x -u %s ade-comp >/dev/null && break; sleep 1; done; sleep 2; pkill -KILL -x -u %s ade-comp; done; sleep 10; echo GREETER:$(pgrep -c -x ade-greeter); echo OWNERCOMP:$(pgrep -c -x -u %s ade-comp); echo LEFT:$(wc -l < /run/aos/session/%s); journalctl -b -t ade-session --no-pager | grep -c \"giving up\"'" % ((bt.OWNER,) * 4), timeout=150)
        print("$ given up\n%s" % gone)
        bt.shot("greeter-again")
        if "GREETER:1" not in gone or "OWNERCOMP:0" not in gone or "LEFT:5" not in gone:
            print("!! the session did not end on the greeter with its five crash lines kept")
            ok = False
        bt.typekeys(bt.LUKS_PASS + "\n")
        time.sleep(25)
        again = ser.run(sudo + "sh -c 'echo SHELL:$(pgrep -c -x -u %s ade-shell); echo LEFT:$(ls /run/aos/session/ | grep -c ^%s$); echo TOLD:$(journalctl -b -t ade-session --no-pager | sed -n \"/giving up/,\\$p\" | grep -c \"previous session\")'" % (bt.OWNER, bt.OWNER))
        print("$ logged in again\n%s" % again)
        bt.shot("greeter-crash-toast")
        if "SHELL:1" not in again or "LEFT:0" not in again or "TOLD:1" not in again:
            print("!! the next login did not take the crash lines and start the owner's session")
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
