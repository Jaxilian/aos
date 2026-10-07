#!/usr/bin/env python3
"""The owner's encrypted home (INSTALL_MODE=oobe boot-test.py install
first): the first boot makes a systemd-homed account, and every door
into it -- the login screen, the console, sudo, the lock screen, the
recovery key -- opens with its password and nothing else.

  1. The first boot's setup session runs aos-setup --first-boot --go for
     tester; the helper prints the recovery key for the driver, finishes
     by itself, and greetd shows the login screen (homed-greeter).
     /home/tester.home is a LUKS2 image (homectl: Storage luks).
  2. tester logs in on the serial console with the password (login's
     PAM reaches homed), sudo asks for it and gets it; the home is
     mounted, a file written into it.
  3. The login screen: a wrong password refused, the right one brings
     the desktop (homed-desktop); Super+L and the password unlock it.
  4. Power off, boot again: the recovery key typed at the login screen
     opens the home (homed-recovered); the file is there; the key is
     nowhere on the disk.

Afterwards the disk is tester's: run boot-test.py install again before
the demo-disk drivers. Screendumps: homed-*. Transcript: homed.serial.txt."""
import importlib.util
import os
import re
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
SETUP_ENV = ("WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/$(id -u setup) HOME=/var/lib/aos-setup "
             "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u setup)/bus")
KEY_RE = re.compile(r"[cbdefghijklnrtuv]{8}(?:-[cbdefghijklnrtuv]{8}){7}")


def boot(name):
    for p in (bt.SER, bt.MON):
        if os.path.exists(p):
            os.unlink(p)
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    q = subprocess.Popen(bt.qemu_command(), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "homed%s.serial.txt" % name))
    if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
        print("!! no login prompt")
        return None, q
    return ser, q


def stop(ser, q, sudo=""):
    try:
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


def first_boot():
    """1-3: the owner made, every door checked. Returns the recovery key."""
    ser, q = boot("")
    if ser is None:
        q.kill()
        return None
    ok = True
    key = None
    sudo = ""
    try:
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)
        up = False
        for _ in range(60):
            if "setup" in ser.run("ps -o user= -C ade-shell"):
                up = True
                break
            time.sleep(2)
        if not up:
            print("!! no setup session came up")
            return None
        time.sleep(5)
        # 1. The first boot, driven; the key comes back on the log.
        out = ser.run(
            "su -s /bin/sh setup -c '%s aos-setup --first-boot --user %s --pass %s --go >/tmp/oobe.log 2>&1 &'; "
            "for i in $(seq 90); do grep -q 'AOS is yours' /tmp/oobe.log 2>/dev/null && break; sleep 1; done; "
            "grep -E '>>>|AOS is yours|Recovery key|aos-firstboot' /tmp/oobe.log | head -12" % (SETUP_ENV, USER, PASS), timeout=200)
        print("$ first boot\n%s" % out)
        m = KEY_RE.search(out)
        if m is None:
            print("!! no recovery key on the setup log")
            return None
        key = m.group(0)
        time.sleep(30)
        # The image is a GPT with the LUKS volume inside, so cryptsetup
        # isLuks on the file says no; homectl knows what it holds.
        state = ser.run("ps -o user= -C ade-greeter; ls -la /home/; "
                        "homectl inspect %s 2>&1 | grep -E 'Storage|State|LUKS UUID|Members' | tr -s ' '; "
                        "test -e /etc/aos/oobe && echo marker || echo no-marker; id %s" % (USER, USER), timeout=60)
        print("$ after the first boot\n%s" % state)
        bt.shot("homed-greeter")
        if "greeter" not in state or "Storage: luks" not in state or "LUKS UUID" not in state or "no-marker" not in state:
            print("!! the owner is not a homed account on a LUKS image behind the login screen")
            ok = False
        if "wheel" not in state:
            print("!! the owner is not in wheel")
            ok = False
        # The key must not be on the disk: not in the journal, not in /etc.
        leak = ser.run("journalctl -b --no-pager | grep -c '%s'; grep -rl '%s' /etc /var/lib/systemd /var/log 2>/dev/null | head -3" % (key[:17], key[:17]))
        print("$ key on the disk: %r" % leak)
        if not leak.replace("# ", "").strip().startswith("0") or "/" in leak.replace("# ", "").strip()[1:]:
            print("!! the recovery key was written somewhere")
            ok = False
        # 2. The console: tester with the password, then sudo.
        ser.send("exit\n")
        time.sleep(2)
        if ser.read_until(b"login:", 30) is None:
            print("!! no login prompt after root's logout")
            return None
        ser.send(USER + "\n")
        if ser.read_until(b"Password:", 30) is None:
            print("!! no password prompt for %s" % USER)
            return None
        ser.send(PASS + "\n")
        if ser.read_until(b"$ ", 60) is None:
            print("!! %s could not log in on the console with the password" % USER)
            return None
        ser.send("stty -echo cols 200 rows 50\n")
        ser.read_until(b"$ ", 10)
        sudo = "printf '%%s\\n' '%s' | sudo -S -p '' " % PASS
        home = ser.run("echo HOME:$HOME; findmnt -n -o SOURCE,FSTYPE /home/%s; echo kept > ~/kept.txt && echo WROTE; "
                       "%s id -u" % (USER, sudo), timeout=60)
        print("$ the console\n%s" % home)
        if "WROTE" not in home or "ext4" not in home or not home.replace("$ ", "").strip().endswith("0"):
            print("!! the home is not mounted and writable, or sudo refused the password")
            ok = False
        # 3. The login screen: wrong, right, lock, unlock.
        bt.typekeys("wrong-0\n")
        time.sleep(6)
        still = ser.run("pgrep -a ade-greeter | head -1")
        if "ade-greeter" not in still:
            print("!! the greeter went away on a wrong password")
            ok = False
        bt.typekeys(PASS + "\n")
        time.sleep(25)
        who = " ".join(ser.run("ps -o user=,comm= -C ade-comp,ade-shell").split())
        print("$ after the login: %s" % who)
        bt.shot("homed-desktop")
        if ("%s ade-shell" % USER) not in who:
            print("!! the owner's session did not start from the login screen")
            ok = False
        bt.monitor("sendkey meta_l-l")
        time.sleep(6)
        bt.typekeys(PASS + "\n")
        time.sleep(6)
        lock = ser.run("pgrep -c -x ade-lock")
        if not lock.replace("$ ", "").strip().startswith("0"):
            print("!! the lock screen did not open with the password")
            ok = False
    finally:
        stop(ser, q, sudo)
    return key if ok else None


def recovery(key):
    """4. The recovery key at the login screen, after a fresh boot."""
    ser, q = boot("-2")
    if ser is None:
        q.kill()
        return False
    ok = True
    sudo = ""
    try:
        time.sleep(20)
        bt.typekeys(key + "\n")
        time.sleep(30)
        bt.shot("homed-recovered")
        ser.send(USER + "\n")
        ser.read_until(b"Password:", 30)
        ser.send(PASS + "\n")
        if ser.read_until(b"$ ", 60) is None:
            print("!! the console login failed on the second boot")
            return False
        ser.send("stty -echo cols 200 rows 50\n")
        ser.read_until(b"$ ", 10)
        sudo = "printf '%%s\\n' '%s' | sudo -S -p '' " % PASS
        who = ser.run("ps -o user=,comm= -C ade-comp,ade-shell | tr -s ' '; cat ~/kept.txt")
        print("$ after the recovery key\n%s" % who)
        if ("%s ade-shell" % USER) not in " ".join(who.split()) or "kept" not in who:
            print("!! the recovery key did not open the home, or the file is gone")
            ok = False
    finally:
        stop(ser, q, sudo)
    return ok


def main():
    key = first_boot()
    if key is None:
        print("\n== done, homed ok: False")
        return False
    ok = recovery(key)
    print("\n== done, homed ok: %s" % ok)
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
