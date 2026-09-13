#!/usr/bin/env python3
"""Drive the guest that write-usb.sh starts, so nobody has to type at it.

    auto-install.py install <serial socket> <monitor socket> <log>
    auto-install.py boot    <serial socket> <monitor socket> <log>

install: wait for the live ISO's login prompt, log in as root, run
aos-install /dev/vda with its own YES piped in, and power the guest off once
it reports success. This is what "write-usb.sh --install --auto" runs.

boot: wait for a login prompt, then quit QEMU. That is the whole check
"write-usb.sh --boot --auto" makes of a stick: the firmware found it, GRUB
loaded, the kernel found the root, systemd reached a getty.

The guest is read through the serial console, on a unix socket QEMU serves,
the same way boot-test.py does it. Nothing here touches a terminal, which
matters: driving QEMU through its own stdin from a pty is exactly the
arrangement that died at GRUB the first time this was tried.

Everything the guest prints goes to the log byte for byte, and to stdout
with the escape sequences stripped so that GRUB's menu redraws do not
scribble over the terminal. The exit status is the answer: 0 is done.
"""

import re
import socket
import sys
import time

MODE, SER, MON, LOG = sys.argv[1:5]

LOGIN_TIMEOUT = 300
# A slow stick: ~2.8 GB copied, then a swap file written with no output at
# all. An hour is far more than either needs and still short of "hung".
INSTALL_TIMEOUT = 3600
# Say something after this many seconds of silence, so the long quiet
# stretches read as progress rather than as a hang.
QUIET_NOTE = 30

# Colour, cursor movement and the OSC reports bash prints around prompts.
# Same expression as boot-test.py; the log keeps the raw bytes.
ANSI = re.compile(rb"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]|\x1b\[[0-9;:?]*[ -/]*[@-~]")


def say(msg):
    print("\n>>> auto-install: %s" % msg, flush=True)


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
        if self.s is None:
            sys.exit("auto-install: QEMU never opened %s" % path)
        self.s.settimeout(1.0)
        self.buf = b""
        self.line = b""

    def echo(self, data):
        """Print complete lines, stripped of escapes; hold the partial one."""
        self.line += data
        while b"\n" in self.line:
            l, self.line = self.line.split(b"\n", 1)
            l = ANSI.sub(b"", l).replace(b"\r", b"").rstrip()
            if l:
                print("    " + l.decode(errors="replace"), flush=True)

    def flush_line(self):
        l = ANSI.sub(b"", self.line).replace(b"\r", b"").strip()
        if l:
            print("    " + l.decode(errors="replace"), flush=True)
        self.line = b""

    def wait_for(self, pattern, timeout):
        """Read until the regex matches; return the match, or None on timeout."""
        pat = re.compile(pattern)
        end = time.time() + timeout
        last = time.time()
        while time.time() < end:
            try:
                d = self.s.recv(4096)
            except socket.timeout:
                d = b""
            if d:
                self.log.write(d)
                self.log.flush()
                self.buf += d
                self.echo(d)
                last = time.time()
            elif d == b"" and time.time() - last > QUIET_NOTE:
                print("    ... guest busy, %ds without output" % (time.time() - last),
                      flush=True)
                last = time.time()
            m = pat.search(self.buf)
            if m:
                self.buf = self.buf[m.end():]
                self.flush_line()
                return m
            # keep only what a pattern could still start in
            if len(self.buf) > 65536:
                self.buf = self.buf[-8192:]
        return None

    def send(self, s):
        self.s.sendall(s.encode())


def monitor(cmd):
    m = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        m.connect(MON)
        m.settimeout(2)
        try:
            m.recv(4096)
        except socket.timeout:
            pass
        m.sendall((cmd + "\n").encode())
        time.sleep(0.5)
    except OSError:
        pass
    finally:
        m.close()


def login(ser):
    say("waiting for the guest's login prompt")
    if ser.wait_for(rb"login: ?$", LOGIN_TIMEOUT) is None:
        say("no login prompt within %ds" % LOGIN_TIMEOUT)
        return False
    time.sleep(1)
    ser.send("root\n")
    if ser.wait_for(rb"# $", 60) is None:
        say("no shell prompt after logging in")
        return False
    return True


def install(ser):
    if not login(ser):
        return 1
    say("running aos-install /dev/vda -- several minutes, two of them silent")
    # The exit status comes back on its own line so a failure inside
    # aos-install (set -e) is seen as such and not as a hang. The echoed
    # command line shows "$?" unexpanded, so it cannot match the digits.
    ser.send("printf 'YES\\n' | aos-install /dev/vda; echo AOS-INSTALL-EXIT=$?\n")
    m = ser.wait_for(rb"AOS-INSTALL-EXIT=(\d+)", INSTALL_TIMEOUT)
    if m is None:
        say("aos-install did not finish within %ds; quitting QEMU" % INSTALL_TIMEOUT)
        monitor("quit")
        return 1
    rc = int(m.group(1))
    if rc != 0:
        say("aos-install exited %d -- the stick is NOT usable; see %s" % (rc, LOG))
        monitor("quit")
        return 1
    say("install finished; powering the guest off")
    ser.send("poweroff\n")
    if ser.wait_for(rb"reboot: Power down", 120) is None:
        say("guest did not power down; quitting QEMU")
        monitor("quit")
    return 0


def boot(ser):
    if ser.wait_for(rb"login: ?$", LOGIN_TIMEOUT) is None:
        say("no login prompt within %ds -- the stick did not boot" % LOGIN_TIMEOUT)
        monitor("quit")
        return 1
    say("login prompt reached: the stick boots")
    monitor("quit")
    return 0


def main():
    ser = Serial(SER, LOG)
    if MODE == "install":
        rc = install(ser)
    elif MODE == "boot":
        rc = boot(ser)
    else:
        sys.exit("usage: auto-install.py install|boot <serial> <monitor> <log>")
    ser.log.close()
    sys.exit(rc)


if __name__ == "__main__":
    main()
