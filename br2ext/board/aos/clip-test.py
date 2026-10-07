#!/usr/bin/env python3
"""The clipboard from a text field, on the installed QEMU disk (the keyed
build; boot-test.py install first). The report of 2026-10-07: in Files,
F2 then Ctrl+C left the clipboard untouched.

  1. Files (Super+E, at /); Down selects the first row, F2 opens the
     rename prompt with the name marked, Ctrl+C, Escape.
  2. Notepad on an empty file, Ctrl+V, Ctrl+S: the file holds the
     name. (wl-paste is no judge here: ade has no data-control protocol,
     so wl-paste reads through a focus-stealing popup and races; it
     printed nothing while a real paste worked, 2026-10-07.)

Screendumps: clip-*. Serial transcript: clip.serial.txt."""
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


def main():
    for p in (bt.SER, bt.MON):
        if os.path.exists(p):
            os.unlink(p)
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    q = subprocess.Popen(bt.qemu_command(), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    ok = True
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "clip.serial.txt"))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! no login prompt")
            return False
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)
        for _ in range(30):
            s = bt.shot("clip-boot", quiet=True)
            if s and s[0] >= 0.005:
                break
            time.sleep(2)
        # 1. Files (it opens at /: aos is the first row), the row
        #    selected, the rename prompt, Ctrl+C, Escape.
        bt.monitor("sendkey meta_l-e")
        time.sleep(8)
        bt.shot("clip-files")
        bt.monitor("sendkey down")
        time.sleep(1)
        bt.monitor("sendkey f2")
        time.sleep(2)
        bt.shot("clip-rename")
        bt.monitor("sendkey ctrl-c")
        time.sleep(2)
        bt.monitor("sendkey esc")
        time.sleep(1)
        # 2. A real paste: Notepad on an empty file, Ctrl+V, Ctrl+S.
        ser.run("rm -f /tmp/paste.txt; su -s /bin/sh admin -c 'touch /tmp/paste.txt; export %s; setsid notepad /tmp/paste.txt >/tmp/np.log 2>&1 &'" % dt.ENV)
        time.sleep(7)
        bt.monitor("sendkey ctrl-v")
        time.sleep(1.5)
        bt.monitor("sendkey ctrl-s")
        time.sleep(2)
        bt.shot("clip-pasted")
        got = ser.run("cat /tmp/paste.txt; echo")
        print("$ pasted\n%s" % got)
        if "aos" not in got:
            print("!! the paste does not hold the name")
            ok = False
        print("$ files\n%s" % ser.run("pgrep -a files; journalctl -b _COMM=ade-comp --no-pager | grep -i -E 'selection|clip' | tail -5 | cut -c17-160"))
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
    print("\n== done, ok: %s" % ok)
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
