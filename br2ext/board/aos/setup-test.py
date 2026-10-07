#!/usr/bin/env python3
"""The graphical installer, end to end, in QEMU: the live ISO with a blank
32 GB disk, aos-setup started in the demo account's session with every
answer on its command line and --go, screendumps while it installs, then
the disk booted: its first boot makes the owner (the installer makes no
account since 0.3.0), the keyboard and the time zone reached the disk,
the login screen lists jax and the password brings the desktop. Leaves
the disk jax's, not admin's: run `boot-test.py install` afterwards to
give the other tests their demo disk back.

Screendumps: setup-*.screen.png; transcripts setup-N.serial.txt."""
import importlib.util
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DISK_ONLY = "--disk-only" in sys.argv
spec = importlib.util.spec_from_file_location("bt", os.path.join(HERE, "boot-test.py"))
sys.argv = ["boot-test.py", "install"]
bt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bt)

USER, PASS = "jax", "secretpass1"    # typed at the login screen under the se layout: no -
ENV = ("WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/1000 HOME=/home/admin "
       "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus")
OOBE_ENV = ("WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/$(id -u setup) HOME=/var/lib/aos-setup "
            "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u setup)/bus")
LOG = "/tmp/setup.log"


def qemu(mode):
    for p in (bt.SER, bt.MON):
        if os.path.exists(p):
            os.unlink(p)
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    bt.MODE = mode
    cmd = bt.qemu_command()
    if mode == "install":
        # the desktop needs the GPU the disk test gets; install mode has std VGA
        cmd[cmd.index("-vga") + 1] = "virtio"
        cmd[cmd.index("-vga")] = "-device"
        cmd[cmd.index("virtio")] = "virtio-vga"
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def login(ser, user="root", password=None):
    """root on the live ISO; on the installed disk root's console login is
    locked, so the owner logs in and the checks go through sudo."""
    if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
        print("!! no login prompt")
        return False
    ser.send(user + "\n")
    if password is not None:
        if ser.read_until(b"Password:", 30) is None:
            print("!! no password prompt")
            return False
        ser.send(password + "\n")
        if ser.read_until(b"$ ", 30) is None:
            print("!! login as %s refused" % user)
            return False
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"$ ", 10)
        return True
    ser.read_until(b"# ", 30)
    ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
    ser.read_until(b"# ", 10)
    return True


def quit_qemu(q):
    try:
        bt.monitor("quit")
    except OSError:
        pass
    try:
        q.wait(10)
    except subprocess.TimeoutExpired:
        q.kill()


def main():
    ok = True
    if DISK_ONLY:
        return boot2()
    print("== boot 1: the live ISO, the installer with --go")
    q = qemu("install")
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "setup-1.serial.txt"))
        if not login(ser):
            return False
        for _ in range(30):
            s = bt.shot("setup-desktop", quiet=True)
            if s and s[0] >= 0.005:
                break
            time.sleep(2)
        cmd = ("aos-setup --user %s --pass %s --disk /dev/vda --keymap se --zone Europe/Stockholm --go"
               % (USER, PASS))
        ser.run("rm -f %s; su -s /bin/sh admin -c '%s setsid %s >%s 2>&1 &'" % (LOG, ENV, cmd, LOG))
        time.sleep(8)
        bt.shot("setup-started")
        # aos-install's stages reach the log through the app; the copy is
        # the long silent one.
        t_end = time.time() + 900
        done = False
        while time.time() < t_end:
            time.sleep(15)
            tail = ser.run("tail -3 %s" % LOG)
            if "AOS installed on" in tail or "Creating swap" in tail:
                if "AOS installed on" in tail:
                    done = True
                    break
                bt.shot("setup-progress", quiet=True)
        print("\n$ cat %s\n%s" % (LOG, ser.run("cat %s" % LOG)))
        bt.shot("setup-done")
        if not done:
            print("!! the installer did not finish")
            ok = False
        ser.run("pkill -f aos-setup; sleep 1")
        ser.send("poweroff\n")
        ser.read_until(b"reboot: Power down", 90)
    finally:
        quit_qemu(q)
    if not ok:
        return False
    return boot2()


def boot2():
    """The installed disk has no account (0.3.0): its first boot runs the
    setup session, which makes the owner -- aos-setup --first-boot --go,
    as oobe-test.py does -- then the login screen lists jax, the keyboard
    and the time zone the installer was given are on the disk, and the
    password at the login screen brings jax's desktop."""
    ok = True
    print("\n== boot 2: the installed disk, its first boot")
    q = qemu("disk")
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "setup-2.serial.txt"))
        # root's console login is open until the owner exists.
        if not login(ser):
            return False
        up = False
        for _ in range(60):
            if "setup" in ser.run("ps -o user= -C ade-shell"):
                up = True
                break
            time.sleep(2)
        bt.shot("setup-welcome")
        if not up:
            print("!! the first boot did not come up as the setup user")
            print("$ greetd and the console say\n%s" % ser.run(
                "systemctl status greetd --no-pager 2>&1 | head -5; journalctl -b --no-pager | grep -iE 'greetd|session|logind|ade' | tail -20 | cut -c17-200", timeout=60))
            return False
        print("$ first boot\n%s" % ser.run(
            "su -s /bin/sh setup -c '%s aos-setup --first-boot --user %s --pass %s --keymap se --zone Europe/Stockholm --go >/tmp/oobe.log 2>&1 &'; "
            "for i in $(seq 40); do grep -q 'AOS is yours' /tmp/oobe.log 2>/dev/null && break; sleep 1; done; "
            "grep -E '>>>|AOS is yours|aos-firstboot' /tmp/oobe.log | head -8" % (OOBE_ENV, USER, PASS), timeout=120))
        time.sleep(40)
        checks = [
            # the harness drops the first output line; keep it blank
            "echo; id %s; id admin 2>&1 | head -1" % USER,
            "ps -o user= -C ade-greeter",
            "grep XKB /etc/ade/environment; cat /etc/vconsole.conf | grep KEYMAP",
            "readlink /etc/localtime",
            "systemctl --failed --no-pager",
        ]
        out = {}
        for c in checks:
            out[c] = ser.run(c)
            print("\n$ %s\n%s" % (c, out[c]))
        if "uid=1000(%s)" % USER not in out[checks[0]] or "no such user" not in out[checks[0]]:
            print("!! the account is wrong: %r" % out[checks[0]])
            ok = False
        if "greeter" not in out[checks[1]]:
            print("!! the login screen is not up after the first boot")
            ok = False
        if "XKB_DEFAULT_LAYOUT=se" not in out[checks[2]] or "sv-latin1" not in out[checks[2]]:
            print("!! the keyboard layout did not reach the disk")
            ok = False
        if "Europe/Stockholm" not in out[checks[3]]:
            print("!! the time zone did not reach the disk")
            ok = False
        if "0 loaded" not in out[checks[4]]:
            print("!! failed units")
            ok = False
        bt.shot("setup-login")
        bt.typekeys(PASS + "\n")
        time.sleep(25)
        who = " ".join(ser.run("ps -o user=,comm= -C ade-comp,ade-shell").split())
        print("$ after the login: %s" % who)
        s = bt.shot("setup-installed")
        if ("%s ade-shell" % USER) not in who:
            print("!! the owner's session did not start from the login screen")
            ok = False
        if not s or s[0] < 0.005:
            print("!! the installed desktop is black")
            ok = False
        ser.send("poweroff\n")
        ser.read_until(b"reboot: Power down", 90)
    finally:
        quit_qemu(q)
    return ok


if __name__ == "__main__":
    ok = main()
    print("\n== done, installer ok:", ok)
    sys.exit(0 if ok else 1)
