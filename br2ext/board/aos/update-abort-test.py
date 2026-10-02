#!/usr/bin/env python3
"""An update cut off mid-write must never break the machine. Whichever
slot the disk is on (boot-test.py install, update-test.py), three boots:

  1. aos-update starts writing the other slot; QEMU is killed while the
     tarball is still being extracted -- a power-off, the lid, Settings
     closed
  2. the machine boots the same slot as before, grubenv names no next,
     and `aos-update --rollback` refuses the half-written slot; then the
     update runs to completion and arms the other slot
  3. the other slot boots and is confirmed

The disk ends on the other slot, which is where update-test.py wants it
when it started on slot a: run this after it, not before.

Reuses update-test.py's fake 9.9.9 release and its boot driver."""
import importlib.util
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = ["boot-test.py", "disk"]
spec = importlib.util.spec_from_file_location("ut", os.path.join(HERE, "update-test.py"))
ut = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ut)
bt = ut.bt

LOG = "/var/log/aos-update.log"


def boot_and_cut():
    """Start the update, wait for the slot write to begin, kill QEMU.
    Returns the partition number the machine booted from, or None."""
    for p in (bt.SER, bt.MON):
        if os.path.exists(p):
            os.unlink(p)
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    q = subprocess.Popen(bt.qemu_command(), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "update-abort-1.serial.txt"))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! boot 1: no login prompt")
            return False
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50\n")
        ser.read_until(b"# ", 10)
        print("$ " + ut.ENV + "\n" + ser.run(ut.ENV))
        part = ser.run(ut.SLOT).strip().lstrip("# ").strip()
        print("$ booted partition %s" % part)
        ser.run("rm -f %s; (setsid aos-update --url %s >/dev/null 2>&1 &)" % (LOG, ut.URL))
        for _ in range(120):
            time.sleep(2)
            r = ser.run("grep -c 'Writing slot' %s 2>/dev/null; grep -c 'installed in slot' %s 2>/dev/null" % (LOG, LOG))
            lines = [l.strip().lstrip("# ").strip() for l in r.splitlines() if l.strip()]
            if lines and lines[0] not in ("0", ""):
                break
        else:
            print("!! boot 1: the update never reached the slot write")
            return None
        if len(lines) > 1 and lines[1] not in ("0", ""):
            print("!! boot 1: the update finished before it could be cut")
            return None
        # Into the extraction: a few seconds of writing, then the plug.
        time.sleep(6)
        print("== boot 1: slot write under way; killing QEMU now\n$ tail " + LOG + "\n" + ser.run("tail -3 " + LOG))
        try:
            bt.monitor("quit")
        except OSError:
            pass
    finally:
        try:
            q.wait(10)
        except subprocess.TimeoutExpired:
            q.kill()
    return part


def main():
    ut.make_release()
    httpd = ut.serve()
    ok = True
    try:
        print("== boot 1: the update cut mid-write")
        part = boot_and_cut()
        if part not in ("3", "4"):
            print("!! boot 1: booted partition %r" % part)
            return False
        cur, other = (("3", "a"), ("4", "b")) if part == "3" else (("4", "b"), ("3", "a"))
        same_slot, other_slot = cur[1], other[1]
        print("== slot %s is running; slot %s is the half-written one" % (same_slot, other_slot))

        print("\n== boot 2: still slot %s, no next, rollback refused, then the update completes" % same_slot)
        out = ut.boot(2, ["aos-update --rollback 2>&1; echo rollback=$?",
                          "tail -4 " + LOG,
                          "aos-update --url %s 2>&1 | tail -3" % ut.URL,
                          ut.ENV])
        if out is None:
            return False
        got = out[ut.SLOT].strip().lstrip("# ").strip()
        if got != cur[0]:
            print("!! boot 2: booted partition %s, expected %s (slot %s)" % (got, cur[0], same_slot))
            ok = False
        rb = out["aos-update --rollback 2>&1; echo rollback=$?"]
        if "holds no system" not in rb or "rollback=1" not in rb:
            print("!! boot 2: rollback did not refuse the half-written slot: %r" % rb)
            ok = False
        if ("next=" + other_slot) not in out[ut.ENV].split():
            print("!! boot 2: the second update did not arm slot %s: %r" % (other_slot, out[ut.ENV]))
            ok = False
        if "0 loaded" not in out[ut.FAILED]:
            print("!! boot 2: failed units")
            ok = False

        print("\n== boot 3: slot %s boots and is confirmed" % other_slot)
        out = ut.boot(3, ["sleep 35; " + ut.ENV, "ls -la /.aos-slot-ok"])
        if out is None:
            return False
        ok &= ut.expect(3, out, other[0], ["slot=" + other_slot], ["next=" + other_slot])
    finally:
        httpd.shutdown()
    print("\n== done, abort test ok: %s" % ok)
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
