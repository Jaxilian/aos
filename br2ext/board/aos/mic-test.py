#!/usr/bin/env python3
"""The microphone permission on the installed QEMU disk (boot-test.py
install first; QEMU's hda-duplex codec gives a capture source). The
working tree's aos-sandbox and the PipeWire and WirePlumber files are
copied in over ssh and the session's sound restarted on them.

  1. The sockets: pipewire-0-nomic beside pipewire-0, pulse/native-nomic
     beside pulse/native.
  2. pw-loopback on the nomic socket: its capture half is refused --
     WirePlumber logs "microphone is off" for its input node; on
     pipewire-0 the same loopback's input node gets links.
  3. Through aos-sandbox without --microphone: refused; with it: links.

Serial transcript: mic.serial.txt."""
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

OVERLAY = os.path.join(bt.BASE, "br2ext", "board", "aos", "rootfs-overlay")
FILES = [
    "usr/bin/aos-sandbox",
    "usr/share/pipewire/pipewire.conf.d/10-aos-nomic.conf",
    "usr/share/pipewire/pipewire-pulse.conf.d/10-aos-nomic.conf",
    "usr/share/wireplumber/wireplumber.conf.d/20-aos-nomic.conf",
    "usr/share/wireplumber/scripts/linking/find-nomic-target.lua",
]
# Exported, so every command of the shell sees the session, not only the
# first one an assignment prefix would reach.
AS_ADMIN = "su -s /bin/sh admin -c 'export %s; %%s'" % dt.ENV


def last(out):
    """The last line of a serial run, without the prompt it carries."""
    return out.strip().split("\n")[-1].strip().lstrip("# ").strip()


def loop(ser, remote, name):
    """Runs pw-loopback for 4 s as admin on `remote` and says whether its
    capture node was refused ("refused"), linked ("linked") or neither."""
    env = "PIPEWIRE_REMOTE=%s " % remote if remote else ""
    cmd = ("%spw-loopback -n %s >/tmp/loop.log 2>&1 & "
           "for i in 1 2 3 4 5 6 7 8; do sleep 1; n=$(pw-link -l 2>/dev/null | grep -c \"input.%s\"); [ \"$n\" != 0 ] && break; done; "
           "pkill -x pw-loopback >/dev/null 2>&1; echo $n" % (env, name, name))
    out = ser.run(AS_ADMIN % cmd.replace("'", "'\\''"), timeout=30)
    j = ser.run("journalctl --no-pager _COMM=wireplumber | grep -c 'microphone is off.*input.%s'" % name)
    links = last(out)
    refused = last(j)
    print("   %s: links %s, refusals logged %s" % (name, links, refused))
    if refused.isdigit() and int(refused) > 0:
        return "refused"
    if links.isdigit() and int(links) > 0:
        return "linked"
    return "neither"


def main():
    for p in (bt.SER, bt.MON):
        if os.path.exists(p):
            os.unlink(p)
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    q = subprocess.Popen(bt.qemu_command(), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    ok = True
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "mic.serial.txt"))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! no login prompt")
            return False
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)
        time.sleep(15)
        # The disk holds this build (a verity core since 0.2.0): the
        # overlay's files are in it; nothing to push.
        print("$ install\n%s" % ser.run(
            "systemctl --user -M admin@ restart pipewire.socket pipewire pipewire-pulse.socket pipewire-pulse wireplumber 2>&1 | tail -2; sleep 5; "
            "ls /run/user/1000/ | grep -E 'pipewire-0'; ls /run/user/1000/pulse; "
            "journalctl --no-pager _COMM=wireplumber | grep -iE 'nomic|error|fail' | tail -4 | cut -c17-180", timeout=120))
        socks = ser.run("test -S /run/user/1000/pipewire-0-nomic && echo pw-nomic; test -S /run/user/1000/pulse/native-nomic && echo pulse-nomic")
        if "pw-nomic" not in socks or "pulse-nomic" not in socks:
            print("!! the nomic sockets are missing")
            ok = False

        print("$ loopbacks")
        a = loop(ser, "pipewire-0-nomic", "aos-nomic-loop")
        b = loop(ser, None, "aos-plain-loop")
        print("== nomic socket: %s; plain socket: %s" % (a, b))
        if a != "refused" or b != "linked":
            print("!! the nomic socket did not refuse capture, or the plain one did not link it")
            ok = False

        print("$ through the sandbox")
        for name, flag in (("aos-sb-nomic", ""), ("aos-sb-mic", "--microphone ")):
            cmd = ("/usr/bin/aos-sandbox --app test/loop --home full %s-- sh -c 'pw-loopback -n %s >/tmp/loop.log 2>&1 & "
                   "for i in 1 2 3 4 5 6 7 8; do sleep 1; n=$(pw-link -l 2>/dev/null | grep -c input.%s); [ \"$n\" != 0 ] && break; done; pkill -x pw-loopback >/dev/null 2>&1; echo $n'"
                   % (flag, name, name))
            out = ser.run(AS_ADMIN % cmd.replace("'", "'\\''"), timeout=40)
            j = ser.run("journalctl --no-pager _COMM=wireplumber | grep -c 'microphone is off.*input.%s'" % name)
            links = last(out)
            refused = last(j)
            print("   %s: links %s, refusals logged %s" % (name, links, refused))
            if flag == "" and (not refused.isdigit() or int(refused) == 0):
                print("!! the sandbox without --microphone could record")
                ok = False
            if flag != "" and (not links.isdigit() or int(links) == 0):
                print("!! the sandbox with --microphone could not record")
                ok = False
        print("$ wireplumber log\n%s" % ser.run("journalctl --no-pager _COMM=wireplumber | grep -i 'microphone' | tail -4 | cut -c17-200"))
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
