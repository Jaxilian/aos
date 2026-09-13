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
    ./br2ext/board/aos/boot-test.py desktop   live ISO, but checks the ade
                                              session instead of the shell:
                                              screendumps the autostarted
                                              terminal, presses Super+Return
                                              through the QEMU monitor, and
                                              screendumps again

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
import re
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
# How long the desktop gets to put its first window on the screen. Generous
# because QEMU has no GPU: every pixel here goes through llvmpipe.
WINDOW_TIMEOUT = 60
# Longer again for notepad: it brings up a Vulkan instance and device, and
# in QEMU that is lavapipe doing it in software.
NOTEPAD_TIMEOUT = 60
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

# The desktop session, checked from the serial login -- which is the only way
# in, since ade.service has taken tty1 away from getty. The order is the
# order things have to work in: a logind session on seat0, the DRM and input
# devices that session hands over, the compositor process, then the client.
DESKTOP = [
    "systemctl is-active ade.service; systemctl is-active getty@tty1.service",
    "loginctl list-sessions --no-pager",
    "loginctl show-session "
    "$(loginctl list-sessions --no-pager --no-legend | awk '$3==\"ade\"{print $1}') "
    "-p Id -p User -p Seat -p Active -p State -p TTY -p Type -p Class",
    "ls -l /dev/dri/",
    "ls /dev/input/",
    "localectl status 2>&1 | head -3; echo \"LANG in ade: "
    "$(tr '\\0' '\\n' </proc/$(pgrep -x ade-comp)/environ | grep ^LANG=)\"",
    "pgrep -a ade-comp; pgrep -a terminal",
    "ls -l /usr/bin/ade-comp /usr/bin/terminal /usr/bin/notepad",
    "ls /usr/share/vulkan/icd.d/",
    "for p in $(pgrep -x terminal); do echo \"terminal $p ->\"; pgrep -aP $p; done",
    "journalctl -b _COMM=terminal --no-pager | tail -10",
    # Not "journalctl -u ade": pam_systemd hands the process to logind, which
    # moves it into its own session scope, and from that point journald files
    # everything it prints under that scope instead of the service. The unit
    # log keeps the two systemd lines and loses every line the compositor
    # wrote. Matching on the executable finds it wherever it ended up.
    "journalctl -b _COMM=ade-comp --no-pager | tail -20",
    "ls -l /run/user/$(id -u ade)/wayland-* 2>&1",
    "fc-match monospace 2>&1",
    # The terminal reports TERM=xterm-256color, so clear/tput and every
    # ncurses program running inside it need that entry present -- see the
    # ncurses note in the defconfig for why terminfo is easy to lose.
    "TERM=xterm-256color clear | wc -c; TERM=xterm-256color tput colors; "
    "infocmp -1 xterm-256color | head -2",
    "journalctl -u ade -b --no-pager | tail -5",
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
    px = [raw[i:i + 3] for i in range(0, len(raw), 3 * 97)]
    distinct = len(set(px))
    # "ink": how much of the screen is not the single most common colour.
    # A compositor that came up but mapped nothing paints one flat clear
    # colour and a cursor -- a couple of hundred pixels out of a million --
    # so this separates "a desktop with a window on it" from "a desktop",
    # which distinct colours alone does not.
    bg = max(set(px), key=px.count) if px else b""
    ink = sum(1 for p in px if p != bg) / len(px) if px else 0.0
    return w, h, distinct, ink, raw


# Colour, cursor positioning, and the OSC 3008 shell-integration reports
# bash emits around every prompt. Harmless to read, but they are inside the
# text of every captured command, so anything that parses output -- a number
# of processes, say -- sees them too and gets nonsense.
ANSI = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]|\x1b\[[0-9;:?]*[ -/]*[@-~]")


def unescape(s):
    return ANSI.sub("", s)


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
        lines = unescape(out.decode(errors="replace")).replace("\r", "").split("\n")
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
           "-display", "none", "-no-reboot",
           "-device", "i6300esb", "-action", "watchdog=reset",
           "-chardev", "socket,id=ser0,path=%s,server=on,wait=off" % SER,
           "-serial", "chardev:ser0",
           "-monitor", "unix:%s,server,nowait" % MON]
    # std VGA everywhere except the desktop: it is the harsher case for a
    # text console, being what a machine with no KMS driver falls back to.
    # ade cannot use it, though -- damage-tracked compositing on bochs-drm
    # smears the cursor and eats the background (see run-qemu.sh) -- so the
    # desktop gets virtio-vga, which is also what run-qemu.sh hands you.
    # usb-tablet comes with it so the pointer is absolute; the xHCI
    # controller is needed because "pc" has no USB bus of its own.
    if MODE == "desktop":
        cmd += ["-device", "virtio-vga",
                "-device", "qemu-xhci,id=xhci",
                "-device", "usb-tablet,bus=xhci.0"]
    else:
        cmd += ["-vga", "std"]
    cdrom = ["-drive", "if=none,id=cd0,media=cdrom,format=raw,file=%s" % ISO,
             "-device", "ide-cd,drive=cd0,bootindex=0"]
    if MODE in ("live", "desktop"):
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
    sys.exit("usage: boot-test.py live|usb|install|disk|desktop")


def shot(tag, quiet=False):
    """Screendump the VGA output and report how much is on it."""
    ppm = os.path.join(OUT, "%s.screen.ppm" % tag)
    png = os.path.join(OUT, "%s.screen.png" % tag)
    r = monitor("screendump %s" % ppm)
    time.sleep(1)
    if not os.path.exists(ppm):
        if not quiet:
            print("!! screendump failed: %s" % r.strip())
        return None
    w, h, n, ink, raw = png_from_ppm(ppm, png)
    os.unlink(ppm)
    if not quiet:
        print("\n== screendump %dx%d, ~%d distinct sampled colours, %.1f%% ink -> %s"
              % (w, h, n, ink * 100, png))
    return ink, raw


# QEMU key names for the characters this file needs to type. Anything not
# here would be sent as its own name, which is right for letters and digits
# and wrong for everything else.
# The shifted ones are the reason this table exists at all: "sendkey >" is
# not an error QEMU reports, it is a key that never arrives, so a mistyped
# command runs anyway with a word missing from it.
KEYNAMES = {
    " ": "spc", "-": "minus", ".": "dot", "/": "slash", "\n": "ret",
    ">": "shift-dot", "<": "shift-comma", "_": "shift-minus",
    "=": "equal", "|": "shift-backslash", "~": "shift-grave_accent",
}


def typekeys(text):
    """Type a string into the guest through the monitor, key by key."""
    for c in text:
        if c in KEYNAMES:
            k = KEYNAMES[c]
        elif c.isupper():
            k = "shift-%s" % c.lower()
        else:
            k = c
        monitor("sendkey %s" % k)
        time.sleep(0.3)


def count(ser, prog):
    """How many processes of this name are running in the guest.

    The captured output still carries the shell prompt that preceded it, so
    take the last number in it rather than trying to parse the whole string.
    """
    n = re.findall(r"\d+", ser.run("pgrep -c -x %s" % prog))
    return int(n[-1]) if n else 0


def desktop(ser):
    """Screendump the session, press Super+Return, screendump again.

    The keypress goes in through the QEMU monitor rather than the serial
    line on purpose: it travels the whole path a real key does -- emulated
    PS/2 controller, atkbd, evdev, libinput, xkbcommon, the compositor's
    binding table -- and none of that is exercised by anything else here.

    A pass needs both halves. Ink on the first dump means the autostarted
    terminal was mapped and composited; more windows after the keypress
    means input reached the compositor and its spawn path ran.
    """
    # Wait for something to reach the screen, rather than for the log line
    # that says a window was mapped. Those are not the same moment: mapping
    # happens when the client asks, the first frame when it has actually
    # rendered one, and under llvmpipe that gap is seconds. Polling the
    # screen itself puts a bound on the thing that matters -- how long after
    # boot there is a desktop to look at -- instead of racing it.
    first = None
    for _ in range(WINDOW_TIMEOUT // 2):
        first = shot("desktop", quiet=True)
        if first and first[0] >= 0.005:
            break
        time.sleep(2)
    if first is None:
        print("!! screendump failed")
        return False
    before, raw0 = first
    print("\n== first window on screen -> %s (%.1f%% ink)"
          % (os.path.join(OUT, "desktop.screen.png"), before * 100))

    n0 = count(ser, "terminal")
    print("\n== Super+Return (sendkey meta_l-ret)")
    monitor("sendkey meta_l-ret")
    time.sleep(6)
    n1 = count(ser, "terminal")
    print("\n$ pgrep -c -x terminal: %d before, %d after" % (n0, n1))
    print("\n$ journalctl -b _COMM=ade-comp | tail -10\n%s"
          % ser.run("journalctl -b _COMM=ade-comp --no-pager | tail -10"))

    spawned = shot("desktop-spawned")
    after, raw1 = spawned if spawned else (0.0, b"")

    # Type into the terminal. The shell being alive is not the same as its
    # output reaching the screen: the window can be mapped and composited
    # while the client never draws a glyph. Echoed text is the only thing
    # that proves the whole round trip -- key to libinput, to the focused
    # client, to a buffer, to the scanout.
    print("\n== typing 'echo AOS' into the focused terminal")
    typekeys("echo AOS\n")
    time.sleep(5)
    typed = shot("desktop-typed")
    changed = 0
    if typed and raw1:
        changed = sum(1 for i in range(0, min(len(raw1), len(typed[1])), 3)
                      if raw1[i:i + 3] != typed[1][i:i + 3])
    print("\n== %d pixels changed after typing" % changed)

    # Launch notepad the way a user would, by typing its name at the shell
    # in the focused terminal. It is a second, independent client on the
    # awin + tgn stack -- one the compositor did not spawn itself -- so it
    # covers a client connecting to an already-running session. Under
    # llvmpipe it is slow to appear, hence the wait.
    # stderr goes to a file rather than the terminal so it can be read back
    # here: notepad is a child of the shell inside the terminal, so what it prints
    # reaches the journal, and whatever it says is behind its own window.
    print("\n== launching notepad from the terminal")
    typekeys("notepad 2>/tmp/notepad.err\n")
    npad = 0
    for _ in range(NOTEPAD_TIMEOUT // 3):
        time.sleep(3)
        npad = count(ser, "notepad")
        if npad:
            break
    print("\n$ pgrep -c -x notepad: %d" % npad)
    time.sleep(8)
    shot("desktop-notepad")
    print("\n$ cat /tmp/notepad.err\n%s"
          % ser.run("cat /tmp/notepad.err 2>&1 | tail -20"))
    if not npad:
        print("!! notepad did not start")

    grew = n1 > n0

    print("\n== desktop: %.1f%% ink before, %.1f%% after; terminal %d -> %d"
          % (before * 100, after * 100, n0, n1))
    if before < 0.005:
        print("!! nothing was composited -- the screen is effectively blank")
    if not grew:
        print("!! Super+Return spawned nothing")
    if not changed:
        print("!! typing changed nothing on screen -- the terminal is not live")
    return before >= 0.005 and grew and changed > 0 and npad > 0


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
                if MODE == "desktop":
                    for c in DESKTOP:
                        print("\n$ %s\n%s" % (c, ser.run(c)))
                    ok = desktop(ser)
        # desktop mode takes its own pair of screendumps, before and after
        # the keypress; re-dumping here would overwrite the "before" one.
        if MODE == "desktop":
            if not ok:
                shot("desktop-failed")
        elif MODE != "install" or not ok:
            shot(MODE)
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
