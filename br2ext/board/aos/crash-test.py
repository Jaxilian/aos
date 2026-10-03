#!/usr/bin/env python3
"""The session's crash safety, on the installed QEMU disk (boot-test.py
install first). Three things, one boot each where a restart is involved:

  1. the shell killed: the compositor starts it again and the bar is back
     within seconds; killed again at once, the pause doubles
  2. the compositor killed while locked: systemd restarts the unit, the
     session comes back locked (a lock surface, not the desktop), and
     once unlocked the shell shows the crash toast; the trial-slot
     confirm would have refused (NRestarts is 1)
  3. the compositor killed five times quickly: the unit fails, tty1 gets
     a login prompt under an explanation, and `systemctl restart ade`
     brings the desktop back

Transcripts: update-N.serial.txt (the boots share update-test's driver)."""
import importlib.util
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = ["boot-test.py", "disk"]
spec = importlib.util.spec_from_file_location("ut", os.path.join(HERE, "update-test.py"))
ut = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ut)
bt = ut.bt

ENV = ("WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/1000 HOME=/home/admin "
       "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus")


# Kill a process and wait until it is gone: an aborted Vulkan process
# spends seconds being core-dumped, and nothing has seen it exit before.
# SIGABRT, what a Rust panic raises in the release build; a SIGSEGV sent
# from outside is swallowed once by Rust's stack-overflow handler.
def gone(name, sig="ABRT", limit=90):
    return ("p=$(pgrep -x %s | head -1); pkill -%s -x %s; for i in $(seq %d); do kill -0 $p 2>/dev/null || break; sleep 1; done; "
            % (name, sig, name, limit))


def main():
    ut.CHECKS[:] = ["systemctl show -p NRestarts --value ade.service", "cat /run/ade/crash 2>&1"]
    ok = True

    print("== the shell killed, twice; then the compositor, locked")
    steps = [
        "pgrep -fa ade-shell | head -1",
        gone("ade-shell") + "sleep 3; pgrep -c -x ade-shell; journalctl -b _COMM=ade-comp --no-pager | grep -E 'shell exited|starting the shell' | tail -2",
        gone("ade-shell") + "sleep 4; pgrep -c -x ade-shell; journalctl -b _COMM=ade-comp --no-pager | grep 'starting the shell' | tail -1",
        "su -s /bin/sh admin -c '%s ade-lock >/dev/null 2>&1 &'; sleep 4; journalctl -b _COMM=ade-comp --no-pager | grep -c 'session locked'; ls /run/ade/" % ENV,
        gone("ade-comp") + "sleep 12; systemctl show -p NRestarts --value ade.service; cat /run/ade/crash; ls /run/ade/; journalctl -b _COMM=ade-comp --no-pager | grep -E 'was locked|previous session|lock surface on' | tail -3",
    ]
    out = ut.boot(1, steps)
    if out is None:
        return False
    one = out[steps[1]]
    if "starting the shell again in 1s" not in one or not one.replace("# ", "").startswith("1"):
        print("!! the shell was not restarted after the first kill: %r" % one)
        ok = False
    two = out[steps[2]]
    if "starting the shell again in 2s" not in two or not two.replace("# ", "").startswith("1"):
        print("!! the pause did not double, or the shell is not back: %r" % two)
        ok = False
    four = out[steps[4]]
    if not four.replace("# ", "").startswith("1"):
        print("!! the unit did not restart once: %r" % four)
        ok = False
    if ("core-dump" not in four and "signal" not in four) or "was locked" not in four or "previous session" not in four or "lock surface on" not in four:
        print("!! the restarted session is not locked, or did not learn of the crash: %r" % four)
        ok = False
    return ok and loop_boot()


def loop_boot():
    """A crash loop: the unit fails, tty1 explains. SIGKILL, so no core
    dump: five deaths must fit inside the unit's two-minute window."""
    print("\n== the compositor killed five times")
    steps = [
        "for i in 1 2 3 4 5; do " + gone("ade-comp", "KILL", 30) + "sleep 3; done; sleep 12; echo; systemctl is-active ade.service; systemctl is-active getty@tty1.service; cat /run/issue.d/ade.issue 2>&1 | head -3",
        "systemctl reset-failed ade.service; systemctl restart ade.service; sleep 8; systemctl is-active ade.service; systemctl is-active getty@tty1.service; pgrep -c -x ade-shell",
    ]
    ut.CHECKS[:] = []
    out = ut.boot(2, steps)
    if out is None:
        return False
    ok = True
    one = out[steps[0]].replace("# ", "").strip()
    if not one.startswith("failed") or "active" not in one or "crashed" not in one:
        print("!! the crash loop did not end on the explained prompt: %r" % one)
        ok = False
    two = out[steps[1]].replace("# ", "")
    if not two.startswith("active\ninactive"):
        print("!! restart ade did not bring the desktop back: %r" % two)
        ok = False
    return ok


if __name__ == "__main__":
    ok = main()
    print("\n== done, crash safety ok:", ok)
    sys.exit(0 if ok else 1)
