#!/usr/bin/env python3
"""A base-OS update on the installed QEMU disk (boot-test.py install first).

A fake release -- this build's core.img named as version 9.9.9, its
SHA256SUMS signed with the local apm key, which the image trusts -- is
served to the guest from the host. Four boots, because QEMU runs with
-no-reboot and a restart is a new QEMU:

  1. on slot a: aos-update writes slot b, grubenv says next=b; poweroff
  2. on slot b: the confirm service makes it the default (slot=b); the
     service is disabled (mask refuses a unit that lives in /etc; the
     wants link is in the overlay, so this holds for both slots) and
     aos-update --rollback arms a; poweroff
  3. on slot a, once: next is cleared, slot is still b; unmask; poweroff
  4. on slot b again: the trial of a was forgotten, as a failed boot's
     would be

Every boot checks the mounts, the account and that no unit failed.
Serial transcripts: update-N.serial.txt beside the disk image."""
import http.server
import importlib.util
import os
import shutil
import socketserver
import subprocess
import sys
import threading
import time

BT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "boot-test.py")
# --usb: the disk as a USB stick, the way the G14 runs it. Its partitions
# are then USB media to udev, which once mounted the idle slot under
# /run/media and stopped the first update on hardware at mkfs.
USB = "--usb" in sys.argv
sys.argv = ["boot-test.py", "disk"]
spec = importlib.util.spec_from_file_location("bt", BT)
bt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bt)
if USB:
    _virtio = bt.qemu_command

    def _usb():
        cmd = _virtio()
        i = cmd.index("virtio-blk-pci,drive=hd0,bootindex=0")
        cmd[i] = "usb-storage,bus=xhci.0,drive=hd0,bootindex=0"
        cmd[i - 1:i - 1] = ["-device", "qemu-xhci,id=xhci"]
        return cmd

    bt.qemu_command = _usb

APM = bt.APM_BIN
RELEASE = os.path.join(bt.OUT, "update-release")
IMG = "aos-9.9.9-x86_64-core.img.xz"
VERITY = "aos-9.9.9-x86_64-core.verity"
PORT = 8765
URL = "http://10.0.2.2:%d" % PORT

# The partition the core was opened from: 3 is slot a, 4 is slot b.
SLOT = "cat /sys/class/block/$(basename $(readlink -f /dev/disk/by-partuuid/$(sed -n 's/.*aos\\.core=PARTUUID=\\([^ ]*\\).*/\\1/p' /proc/cmdline)))/partition"
ENV = "grub-editenv /boot/efi/grub/grubenv list"
FAILED = "systemctl --failed --no-pager"
CHECKS = [
    "cat /proc/cmdline",
    SLOT,
    # Nothing of the OS's own disk may be under /run/media (--usb).
    "findmnt -n -o TARGET,SOURCE | grep run/media || echo 'no media'",
    ENV,
    "grep -E 'VERSION_ID|BUILD_ID' /etc/os-release",
    'for m in / /aos /var /etc /home /opt/apm /boot/efi; do findmnt -n -o TARGET,SOURCE,FSTYPE $m || echo "$m: not mounted"; done',
    "id admin; ls /home; cat /etc/machine-id; hostname",
    FAILED,
    "swapon --show --noheadings",
]


def make_release():
    """A fake release 9.9.9 from this build: the core image compressed the
    way release.sh ships it (xz, fastest preset: this is a test), its
    verity file, and SHA256SUMS signed with the local key."""
    shutil.rmtree(RELEASE, ignore_errors=True)
    os.makedirs(RELEASE)
    core = os.path.join(bt.IMG, "core.img")
    with open(os.path.join(RELEASE, IMG), "wb") as f:
        subprocess.run(["xz", "-0", "-T0", "-c", core], stdout=f, check=True)
    shutil.copy(os.path.join(bt.IMG, "core.verity"), os.path.join(RELEASE, VERITY))
    with open(os.path.join(RELEASE, "SHA256SUMS"), "w") as f:
        subprocess.run(["sha256sum", IMG, VERITY], cwd=RELEASE, stdout=f, check=True)
    subprocess.run([APM, "sign", os.path.join(RELEASE, "SHA256SUMS")], check=True, stdout=subprocess.DEVNULL)


def serve():
    handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=RELEASE, **k)
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def boot(n, steps):
    """One QEMU run on the installed disk: log in, run the checks and the
    steps, power off. Returns {command: output}, or None with no login."""
    for p in (bt.SER, bt.MON):
        if os.path.exists(p):
            os.unlink(p)
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    q = subprocess.Popen(bt.qemu_command(), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    out = {}
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "update-%d.serial.txt" % n))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! boot %d: no login prompt" % n)
            return None
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)
        for c in CHECKS + steps:
            r = ser.run(c, timeout=900)
            out[c] = r
            print("\n$ %s\n%s" % (c, r))
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
    return out


def expect(n, out, slot, env_has, env_not=()):
    """The boot ran from the given partition, grubenv says what it should,
    nothing failed. Returns False and says what is wrong otherwise."""
    ok = True
    # The first line of a command's output carries the prompt's "# ".
    got = out[SLOT].strip().lstrip("# ").strip()
    if got != slot:
        print("!! boot %d: booted partition %s, expected %s" % (n, got, slot))
        ok = False
    env = out[ENV]
    for e in env_has:
        if e not in env.split():
            print("!! boot %d: grubenv lacks %s: %r" % (n, e, env))
            ok = False
    for e in env_not:
        if e in env.split():
            print("!! boot %d: grubenv still has %s: %r" % (n, e, env))
            ok = False
    if "0 loaded" not in out[FAILED]:
        print("!! boot %d: failed units" % n)
        ok = False
    media = out["findmnt -n -o TARGET,SOURCE | grep run/media || echo 'no media'"]
    if "/run/media/aos" in media or "AOS_ESP" in media:
        print("!! boot %d: the OS's own partitions are mounted as media: %r" % (n, media))
        ok = False
    return ok


def main():
    make_release()
    httpd = serve()
    ok = True
    try:
        print("== boot 1: update")
        out = boot(1, ["aos-update --check --url %s" % URL,
                       "aos-update --url %s 2>&1 | tail -5" % URL,
                       ENV])
        if out is None:
            return False
        # Whichever slot the disk is on: A is it, B the other.
        part = out[SLOT].strip().lstrip("# ").strip()
        A, B = (("3", "a"), ("4", "b")) if part != "4" else (("4", "b"), ("3", "a"))
        print("== running slot %s; the update goes to slot %s" % (A[1], B[1]))
        ok &= expect(1, out, A[0], ["slot=" + A[1]])
        # The ENV step ran after the update and replaced the check's entry.
        if ("next=" + B[1]) not in out[ENV].split():
            print("!! boot 1: the update did not arm slot %s: %r" % (B[1], out[ENV]))
            ok = False

        print("\n== boot 2: on the new slot; the confirm service runs; a rollback is armed")
        out = boot(2, ["sleep 35; " + ENV,
                       "systemctl disable aos-update-confirm 2>&1",
                       "aos-update --rollback",
                       "aos-update --rollback; " + ENV])
        if out is None:
            return False
        ok &= expect(2, out, B[0], [], ["next=" + B[1]])
        if ("slot=" + B[1]) not in out["sleep 35; " + ENV].split():
            print("!! boot 2: slot %s was not confirmed: %r" % (B[1], out["sleep 35; " + ENV]))
            ok = False
        if ("next=" + A[1]) not in out["aos-update --rollback; " + ENV].split():
            print("!! boot 2: the rollback did not arm slot %s" % A[1])
            ok = False

        print("\n== boot 3: slot a on trial, confirm disabled")
        out = boot(3, ["sleep 35; " + ENV, "systemctl enable aos-update-confirm 2>&1"])
        if out is None:
            return False
        ok &= expect(3, out, A[0], ["slot=" + B[1]], ["next=" + A[1]])
        if ("slot=" + B[1]) not in out["sleep 35; " + ENV].split():
            print("!! boot 3: a disabled confirm still changed the slot")
            ok = False

        print("\n== boot 4: the trial forgotten, back on slot b")
        out = boot(4, [])
        if out is None:
            return False
        ok &= expect(4, out, B[0], ["slot=" + B[1]], ["next=a", "next=b"])
    finally:
        httpd.shutdown()
    return ok


if __name__ == "__main__":
    ok = main()
    print("\n== done, update test ok:", ok)
    sys.exit(0 if ok else 1)
