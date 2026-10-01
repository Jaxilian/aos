#!/usr/bin/env python3
"""The app store on the installed QEMU disk (boot-test.py install first;
the live ISO's apm cache is on its read-only root, so there the store
can only say "no index yet"): the index fetched over the network (`apm
update` as root, the way the Updates page's Check does it through sudo),
then aos-store opened in the demo account's session on the Official,
Third-party and Updates pages and screendumped -- a window with the
packages listed is the catalogue read through apm-core and drawn.

Screendumps: store-*.screen.png; transcript store.serial.txt."""
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
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "store.serial.txt"))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! no login prompt")
            return False
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)
        for _ in range(30):
            s = bt.shot("store-desktop", quiet=True)
            if s and s[0] >= 0.005:
                break
            time.sleep(2)
        print("$ apm update\n%s" % ser.run("for i in $(seq 20); do curl -fsI https://github.com >/dev/null 2>&1 && break; sleep 3; done; apm update 2>&1 | tail -3", timeout=300))
        print("$ apm find .\n%s" % ser.run("apm find a 2>&1 | head -5"))
        if not bt.window_shot(ser, "store-official", "aos-store", "aos-store official"):
            print("!! no window for aos-store")
            ok = False
        if not bt.window_shot(ser, "store-third", "aos-store", "aos-store third-party"):
            print("!! no window for the third-party page")
            ok = False
        if not bt.window_shot(ser, "store-updates", "aos-store", "aos-store updates"):
            print("!! no window for the updates page")
            ok = False
        ser.send("poweroff\n")
        ser.read_until(b"reboot: Power down", 90)
    finally:
        try:
            bt.monitor("quit")
        except OSError:
            pass
        try:
            q.wait(10)
        except subprocess.TimeoutExpired:
            q.kill()
    return ok


if __name__ == "__main__":
    ok = main()
    print("\n== done, store ok:", ok)
    sys.exit(0 if ok else 1)
