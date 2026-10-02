#!/usr/bin/env python3
"""The security round's checks on the live ISO (docs/security-model.md):
the sysctls applied, the LSM list the kernel came up with, and the bar's
red "SSH open" following port 22. A build made with board/aos/
authorized_keys has sshd enabled, so the bar starts red; sshd is stopped
over serial and the mark must go; then it is enabled again the way
Settings does it, sudo as the demo account, and the mark must be back.

Screendumps: sec-*.screen.png; transcript sec.serial.txt."""
import importlib.util
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = ["boot-test.py", "desktop"]
spec = importlib.util.spec_from_file_location("bt", os.path.join(HERE, "boot-test.py"))
bt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bt)

# The bar is 28 logical px at the top; QEMU's screen is scale 1.
BAR_H = 28


def red_in_bar(raw, w):
    """Pixels in the bar that are unmistakably red."""
    n = 0
    for i in range(0, min(len(raw), w * BAR_H * 3), 3):
        r, g, b = raw[i], raw[i + 1], raw[i + 2]
        if r > 180 and g < 120 and b < 120:
            n += 1
    return n


def bar_shot(tag):
    for _ in range(bt.WINDOW_TIMEOUT // 2):
        s = bt.shot(tag, quiet=True)
        if s and s[0] >= 0.005:
            break
        time.sleep(2)
    if not s:
        print("!! screendump %s failed" % tag)
        return None
    ink, raw = s
    # raw is the whole frame, w*h*3; the width is in the PNG's header.
    import struct
    with open(os.path.join(bt.OUT, "%s.screen.png" % tag), "rb") as f:
        f.seek(16)
        w = struct.unpack(">I", f.read(4))[0]
    red = red_in_bar(raw, w)
    print("== %s: %.1f%% ink, %d red pixels in the bar" % (tag, ink * 100, red))
    return red


def main():
    ok = True
    for p in (bt.SER, bt.MON):
        if os.path.exists(p):
            os.unlink(p)
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    q = subprocess.Popen(bt.qemu_command(), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "sec.serial.txt"))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! no login prompt")
            return False
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)

        print("\n== sysctls")
        # run() drops its first line (the echoed command), hence the echo.
        out = ser.run("echo; sysctl kernel.dmesg_restrict kernel.kptr_restrict kernel.yama.ptrace_scope "
                      "kernel.unprivileged_bpf_disabled kernel.perf_event_paranoid net.ipv4.conf.all.accept_redirects 2>&1")
        print(out)
        want = {"kernel.dmesg_restrict = 1", "kernel.kptr_restrict = 2", "kernel.yama.ptrace_scope = 1",
                "kernel.unprivileged_bpf_disabled = 1", "kernel.perf_event_paranoid = 3",
                "net.ipv4.conf.all.accept_redirects = 0"}
        missing = [w for w in want if w not in out]
        if missing:
            print("!! sysctl not applied: %s" % missing)
            ok = False
        print("\n== systemd-sysctl: %s" % ser.run("systemctl is-active systemd-sysctl; journalctl -u systemd-sysctl --no-pager -b 2>&1 | tail -3"))

        print("\n== LSM")
        # The file has no trailing newline; without the echo the marker
        # lands on its line and run() drops it.
        lsm = ser.run("echo; cat /sys/kernel/security/lsm 2>&1; echo")
        print(lsm)
        for bad in ("selinux", "apparmor", "smack", "tomoyo"):
            if bad in lsm:
                print("!! %s still in the LSM list" % bad)
                ok = False
        for good in ("landlock", "yama", "lockdown"):
            if good not in lsm:
                print("!! %s missing from the LSM list" % good)
                ok = False

        print("\n== sshd on this build: %s" % ser.run("systemctl is-enabled sshd; systemctl is-active sshd"))
        listening = ser.run("grep -c ':0016 00000000:0000 0A' /proc/net/tcp /proc/net/tcp6")
        print("$ listeners on 22: %s" % listening)

        # The bar, with sshd as the build left it.
        red_on = bar_shot("sec-ssh-on")
        print("\n== stop sshd")
        print(ser.run("systemctl stop sshd; sleep 7; grep -c ':0016 00000000:0000 0A' /proc/net/tcp /proc/net/tcp6", timeout=60))
        time.sleep(2)
        red_off = bar_shot("sec-ssh-off")

        print("\n== enable it again the way Settings does: sudo as admin")
        print(ser.run("su -s /bin/sh admin -c \"printf '123321\\n' | sudo -S -v -p '' && sudo -n -- systemctl enable --now sshd; systemctl is-enabled sshd\"; sleep 7", timeout=60))
        time.sleep(2)
        red_again = bar_shot("sec-ssh-again")

        if None in (red_on, red_off, red_again):
            ok = False
        else:
            if not (red_on > 20 and red_off < 5 and red_again > 20):
                print("!! the red mark did not follow sshd: on=%d off=%d again=%d" % (red_on, red_off, red_again))
                ok = False
            else:
                print("\n== the bar's SSH mark follows port 22: on=%d off=%d again=%d" % (red_on, red_off, red_again))

        ser.run("systemctl poweroff", timeout=10)
        for _ in range(30):
            if q.poll() is not None:
                break
            time.sleep(1)
    finally:
        if q.poll() is None:
            q.kill()
    print("\n== done: %s" % ("ok" if ok else "FAILED"))
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
