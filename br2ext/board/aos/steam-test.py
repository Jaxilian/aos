#!/usr/bin/env python3
"""Steam's sandbox declaration on the installed QEMU disk (boot-test.py
install first): the recipe declares [sandbox] home = "full", lib32 =
"runtime/compat32", and apm writes the farm entry that runs it under
aos-sandbox with those flags; Steam itself is not started (it wants an
X server and Valve's download).

The working tree's apm and aos-sandbox are copied in over ssh, and the
third-party index from apm-thirdparty/index (publish.sh --local) beside
them, read by file://. Then: apm installs steam (Valve's package, from
Valve), the farm entry's second line names the declaration, its exec
line carries --lib32, and a shell started through the same aos-sandbox
call sees /lib/ld-linux.so.2 -- the 32-bit loader -- and the person's
own home directory. Serial transcript: steam.serial.txt."""
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
INDEX = os.path.join(bt.BASE, "..", "apm-thirdparty", "index")


def main():
    for p in (bt.SER, bt.MON):
        if os.path.exists(p):
            os.unlink(p)
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    q = subprocess.Popen(bt.qemu_command(), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    ok = True
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "steam.serial.txt"))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! no login prompt")
            return False
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)
        time.sleep(15)
        # The disk holds this build (a verity core since 0.2.0): only the
        # index goes in, under /var/tmp (on the aos partition).
        ser.run("rm -rf %s; mkdir -p %s" % (dt.NEW, dt.NEW))
        if not dt.scp(["-r", INDEX], dt.NEW + "/"):
            return False
        print("$ install steam\n%s" % ser.run(
            "apm repo remove thirdparty >/dev/null 2>&1; apm repo add thirdparty file://%s/index --third-party 2>&1 | tail -1; "
            "for i in $(seq 30); do getent hosts repo.steampowered.com >/dev/null 2>&1 && break; sleep 1; done; "
            "apm update --force --quiet 2>&1 | tail -1; apm --yes --force remove steam >/dev/null 2>&1; "
            "apm --yes --quiet install steam 2>&1 | tail -3" % dt.NEW, timeout=1200))
        entry = ser.run("head -3 /opt/apm/bin/steam | cut -c1-200")
        print("$ the farm entry\n%s" % entry)
        if "[sandbox] full" not in entry or "--lib32 runtime/compat32" not in entry:
            print("!! the farm entry does not carry Steam's declaration")
            ok = False
        # The same aos-sandbox call with a shell in place of Steam.
        call = ser.run("sed -n 's/^exec \\(.*\\) -- .*/\\1/p' /opt/apm/bin/steam").strip().split("\n")[-1].strip().lstrip("# ")  # the prompt comes with the line
        print("$ the call\n%s" % call)
        # Through a script under /tmp: a one-line su -c with nested quotes
        # came back empty over the serial line, and /root is not admin's.
        inside = ser.run("printf '%%s\\n' '#!/bin/sh' \"exec >/tmp/p.out 2>&1\" \"%s -- /bin/sh -c 'ls -la /lib/ld-linux.so.2; ls -ld /home/admin; id -u'\" 'echo rc=$?' > /tmp/p.sh; "
                         "chmod 755 /tmp/p.sh; su -s /bin/sh admin -c '%s /tmp/p.sh'; echo; cat /tmp/p.out" % (call, dt.ENV), timeout=60)
        print("$ inside the sandbox\n%s" % inside)
        if "ld-linux.so.2" not in inside or "admin admin" not in inside or "rc=0" not in inside:
            print("!! the sandbox has no 32-bit loader or no home")
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
