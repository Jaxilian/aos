#!/usr/bin/env python3
"""Boot AOS in QEMU unattended, run checks over the serial console, and
screendump the VGA output.

    ./br2ext/board/aos/boot-test.py live      the ISO in an optical drive
    ./br2ext/board/aos/boot-test.py usb       the ISO as a USB mass-storage
                                              device, which is what a stick
                                              written with dd looks like
    ./br2ext/board/aos/boot-test.py install   live ISO + a blank 16G disk,
                                              then runs aos-install on it
    ./br2ext/board/aos/boot-test.py disk      boot what install left behind

Same QEMU arrangement as run-qemu.sh -- UEFI, -cpu host, no PXE ROM, a fresh
OVMF variable store each run -- plus a virtual watchdog and a forward from
host port 2222 to the guest's sshd, so SSH is exercised for real.

Why this exists rather than a shell one-liner: a boot can look perfect on the
serial console while the screen stays black, and that bug has shipped here
once already. Every run ends in a screendump and reports how many distinct
colours it found, so a blank screen is visible in the output.

Writes <mode>.serial.txt and <mode>.screen.png next to the images.
"""

import os
import shutil
import signal
import socket
import struct
import subprocess
import sys
import time
import zlib

MODE = sys.argv[1] if len(sys.argv) > 1 else "live"
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
IMG = os.path.join(BASE, "output", "images")
OUT = IMG
ISO = os.path.join(IMG, "rootfs.iso9660")
DISK = os.path.join(IMG, "aos-disk.img")
OVMF_CODE = "/usr/share/edk2/ovmf/OVMF_CODE.fd"
OVMF_VARS = "/usr/share/edk2/ovmf/OVMF_VARS.fd"
VARS = os.path.join(OUT, "OVMF_VARS.test.fd")
SER = os.path.join(OUT, "boot-test-serial.sock")
MON = os.path.join(OUT, "boot-test-monitor.sock")
LOGIN_TIMEOUT = 180
SSH_PORT = 2222

CHECKS = [
    "systemctl is-system-running",
    "systemctl --failed --no-pager",
    "journalctl -b -p err --no-pager | tail -30",
    "systemd-analyze",
    'for m in / /var /tmp /boot/efi; do findmnt -n -o TARGET,SOURCE,FSTYPE,OPTIONS $m || echo "$m: not mounted"; done',
    "swapon --show; zramctl",
    "journalctl -k --no-pager | grep -i -E 'microcode|initramfs' | head -4",
    "systemctl status systemd-fsck-root --no-pager 2>&1 | grep -E 'Active|fsck'",
    "systemctl show --no-pager -p RuntimeWatchdogUSec; ls /dev/watchdog0 2>&1",
    "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>&1; sysctl -n kernel.panic",
    "loginctl list-sessions --no-pager | tail -3",
    "cc --version | head -1; rustc --version; uname -r",
]

INSTALL = [
    "lsblk -o NAME,SIZE,TYPE /dev/vda",
    "printf 'YES\\n' | aos-install /dev/vda 2>&1 | tail -20",
]


def png_from_ppm(ppm, png):
    """QEMU screendumps are P6 PPM; write a PNG without pulling in a library."""
    with open(ppm, "rb") as f:
        data = f.read()
    parts = data.split(b"\n", 3)
    w, h = map(int, parts[1].split())
    raw = parts[3]
    rows = b"".join(b"\x00" + raw[y * w * 3:(y + 1) * w * 3] for y in range(h))

    def chunk(tag, body):
        c = struct.pack(">I", len(body)) + tag + body
        return c + struct.pack(">I", zlib.crc32(tag + body) & 0xffffffff)

    out = b"\x89PNG\r\n\x1a\n"
    out += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    out += chunk(b"IDAT", zlib.compress(rows, 6))
    out += chunk(b"IEND", b"")
    with open(png, "wb") as f:
        f.write(out)
    # a blank console is one flat colour; sample rather than scan it all
    distinct = len(set(raw[i:i + 3] for i in range(0, len(raw), 3 * 97)))
    return w, h, distinct


class Serial:
    def __init__(self, path, log):
        self.log = open(log, "wb")
        self.s = None
        for _ in range(50):
            try:
                self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.s.connect(path)
                break
            except OSError:
                time.sleep(0.2)
        self.s.settimeout(1.0)
        self.buf = b""

    def read_until(self, needle, timeout):
        end = time.time() + timeout
        while time.time() < end:
            try:
                d = self.s.recv(4096)
                if d:
                    self.log.write(d)
                    self.log.flush()
                    self.buf += d
                else:
                    time.sleep(0.1)
            except socket.timeout:
                pass
            if needle in self.buf:
                i = self.buf.index(needle) + len(needle)
                out, self.buf = self.buf[:i], self.buf[i:]
                return out
        return None

    def send(self, s):
        self.s.sendall(s.encode())

    def run(self, cmd, timeout=60):
        marker = "__DONE_%d__" % int(time.time() * 1000)
        self.send(cmd + "; echo " + marker + "\n")
        out = self.read_until(marker.encode(), timeout)
        if out is None:
            return "!! TIMEOUT waiting for: " + cmd
        lines = out.decode(errors="replace").replace("\r", "").split("\n")
        return "\n".join(l for l in lines[1:] if marker not in l).strip()


def monitor(cmd):
    m = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    m.connect(MON)
    m.settimeout(2)
    try:
        m.recv(4096)
    except socket.timeout:
        pass
    m.sendall((cmd + "\n").encode())
    time.sleep(1.5)
    try:
        return m.recv(4096).decode(errors="replace")
    except socket.timeout:
        return ""
    finally:
        m.close()


def ssh_check():
    key = os.path.expanduser("~/.ssh/id_ed25519")
    if not os.path.exists(key):
        return "(no ~/.ssh/id_ed25519 on this host, skipping)"
    r = subprocess.run(
        ["ssh", "-p", str(SSH_PORT), "-i", key,
         "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
         "-o", "ConnectTimeout=15", "-o", "BatchMode=yes", "root@127.0.0.1",
         "echo SSH-OK; systemctl is-system-running; loginctl list-sessions --no-pager | tail -2"],
        capture_output=True, text=True, timeout=60)
    return (r.stdout + r.stderr).strip()[:600]


def qemu_command():
    cmd = ["qemu-system-x86_64", "-enable-kvm", "-cpu", "host", "-m", "4G", "-smp", "4",
           "-drive", "if=pflash,format=raw,readonly=on,file=%s" % OVMF_CODE,
           "-drive", "if=pflash,format=raw,file=%s" % VARS,
           "-netdev", "user,id=n0,hostfwd=tcp:127.0.0.1:%d-:22" % SSH_PORT,
           "-device", "virtio-net-pci,netdev=n0,romfile=",
           "-display", "none", "-vga", "std", "-no-reboot",
           "-device", "i6300esb", "-action", "watchdog=reset",
           "-chardev", "socket,id=ser0,path=%s,server=on,wait=off" % SER,
           "-serial", "chardev:ser0",
           "-monitor", "unix:%s,server,nowait" % MON]
    cdrom = ["-drive", "if=none,id=cd0,media=cdrom,format=raw,file=%s" % ISO,
             "-device", "ide-cd,drive=cd0,bootindex=0"]
    if MODE == "live":
        return cmd + cdrom
    if MODE == "usb":
        # what a dd'd stick looks like: no El Torito, so firmware must find
        # the EFI system partition in the GPT by itself
        return cmd + ["-drive", "if=none,id=usb0,format=raw,file=%s" % ISO,
                      "-device", "qemu-xhci,id=xhci",
                      "-device", "usb-storage,bus=xhci.0,drive=usb0,bootindex=0"]
    if MODE == "install":
        if os.path.exists(DISK):
            os.unlink(DISK)
        with open(DISK, "wb") as f:
            f.truncate(16 * 1024 ** 3)
        return cmd + cdrom + ["-drive", "if=none,id=hd0,format=raw,file=%s" % DISK,
                              "-device", "virtio-blk-pci,drive=hd0,bootindex=1"]
    if MODE == "disk":
        return cmd + ["-drive", "if=none,id=hd0,format=raw,file=%s" % DISK,
                      "-device", "virtio-blk-pci,drive=hd0,bootindex=0"]
    sys.exit("usage: boot-test.py live|usb|install|disk")


def main():
    if os.geteuid() == 0:
        sys.exit("do not run this as root; QEMU with KVM does not need it")
    # let an outer `timeout` (SIGTERM) still run the cleanup below
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(143))
    for p in (SER, MON):
        if os.path.exists(p):
            os.unlink(p)
    shutil.copy(OVMF_VARS, VARS)

    q = subprocess.Popen(qemu_command(), stdout=subprocess.DEVNULL,
                         stderr=subprocess.STDOUT)
    ok = False
    try:
        ser = Serial(SER, os.path.join(OUT, "%s.serial.txt" % MODE))
        t0 = time.time()
        if ser.read_until(b"login:", LOGIN_TIMEOUT) is None:
            print("!! no login prompt on serial within %ds" % LOGIN_TIMEOUT)
        else:
            print("== login prompt after %.0fs" % (time.time() - t0))
            ser.send("root\n")
            if ser.read_until(b"# ", 30) is None:
                print("!! no shell prompt after login")
            else:
                ok = True
                ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
                ser.read_until(b"# ", 10)
                for c in CHECKS:
                    print("\n$ %s\n%s" % (c, ser.run(c)))
                if MODE in ("live", "usb"):
                    print("\n$ (from the host) ssh -p %d root@127.0.0.1\n%s"
                          % (SSH_PORT, ssh_check()))
                if MODE == "install":
                    for c in INSTALL:
                        print("\n$ %s\n%s" % (c, ser.run(c, timeout=900)))
                    ser.send("poweroff\n")
                    ser.read_until(b"reboot: Power down", 90)
        if MODE != "install" or not ok:
            ppm = os.path.join(OUT, "%s.screen.ppm" % MODE)
            png = os.path.join(OUT, "%s.screen.png" % MODE)
            r = monitor("screendump %s" % ppm)
            time.sleep(1)
            if os.path.exists(ppm):
                w, h, n = png_from_ppm(ppm, png)
                os.unlink(ppm)
                print("\n== screendump %dx%d, ~%d distinct sampled colours -> %s"
                      % (w, h, n, png))
            else:
                print("!! screendump failed: %s" % r.strip())
    finally:
        try:
            monitor("quit")
        except OSError:
            pass
        try:
            q.wait(10)
        except subprocess.TimeoutExpired:
            q.kill()
    print("\n== done, login ok:", ok)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
