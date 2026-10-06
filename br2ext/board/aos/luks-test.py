#!/usr/bin/env python3
"""An encrypted aos partition (INSTALL_MODE=encrypt boot-test.py install
first: the demo account on LUKS2, passphrase LUKS_PASS). The disk is booted
on GRUB's serial-console entry, so the initramfs's passphrase prompt is
on the serial line: a wrong passphrase first (cryptsetup asks again),
then the right one; the system comes up with /aos on /dev/mapper/aos. Serial transcript: luks.serial.txt."""
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


def unlock(ser, passes):
    """Picks GRUB's "AOS (serial console)" entry (the third; the menu
    waits 2 s), on which the console is the serial line, so cryptsetup's
    prompt comes here and the answer can go back the same way; then
    answers each of `passes` (a wrong one first, say). Returns the serial
    output up to the login prompt, or None."""
    if ser.read_until(b"AOS (serial console)", 120) is None:
        print("!! no GRUB menu on the serial line")
        return None
    ser.send("\x1b[B\x1b[B\r")
    for p in passes:
        if ser.read_until(b"Enter passphrase", 120) is None:
            print("!! no passphrase prompt on the serial console")
            return None
        time.sleep(1)
        ser.send(p + "\n")
    return ser.read_until(b"login:", bt.LOGIN_TIMEOUT)


def main():
    for p in (bt.SER, bt.MON):
        if os.path.exists(p):
            os.unlink(p)
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    q = subprocess.Popen(bt.qemu_command(), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    ok = True
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "luks.serial.txt"))
        if unlock(ser, ["wrong-0", bt.LUKS_PASS]) is None:
            print("!! no login prompt after the passphrase")
            return False
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)
        time.sleep(10)
        out = ser.run("findmnt -n -o TARGET,SOURCE,FSTYPE /aos /home; cryptsetup status aos | head -4; journalctl -b -t aos-init --no-pager | cut -c17-120; systemctl --failed --no-pager | tail -2; swapon --show --noheadings")
        print("$ state\n%s" % out)
        if "/dev/mapper/aos" not in out or "is active" not in out:
            print("!! /aos is not the opened LUKS device")
            ok = False
        if "0 loaded units" not in out:
            print("!! failed units")
            ok = False
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
