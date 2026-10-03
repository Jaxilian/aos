#!/usr/bin/env python3
"""Checks against the installed QEMU disk (boot-test.py install, then
apm), where third-party packages can be installed; first written for the
G14's round 9 (the review in AOS-issues.md). The ade, settings and
sysmon binaries from output/target are copied in over ssh and the
session restarted on them, so a working-tree build is tested without an
ISO. Then: the overview driven by the keyboard (Right, Enter starts the
second tile); Firefox and Xwayland installed from the repositories the
disk knows; Firefox maximised and its hamburger menu opened (an xdg
popup with a grab, at the screen's edge); Xwayland's pixman hidden and
the session restarted, so a start fails and is tried again until the
library is back; sysmon's right-click menu on a process row.
Screendumps: r9i-*. R9I_HX/R9I_HY place the hamburger click for another
screen size; R9I_STOP_AT_FF=1 stops after the Firefox dump."""
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import time

BT = "/home/jax/Projects/OS/aos/br2ext/board/aos/boot-test.py"
sys.argv = ["boot-test.py", "disk"]
spec = importlib.util.spec_from_file_location("bt", BT)
bt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bt)

TARGET = "/home/jax/Projects/OS/aos/output/target/usr/bin"
QMP = os.path.join(bt.OUT, "r9i-qmp.sock")
W, H = 1280, 800
ENV = ("WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/1000 HOME=/home/admin "
       "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus")
KEY = os.path.expanduser("~/.ssh/id_ed25519")
SSH = ["-P", str(bt.SSH_PORT), "-i", KEY, "-o", "StrictHostKeyChecking=no",
       "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes"]


class Qmp:
    def __init__(self, path):
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.s.connect(path)
        self.s.settimeout(3)
        self.recv()
        self.cmd("qmp_capabilities")

    def recv(self):
        buf = b""
        while not buf.endswith(b"\n"):
            buf += self.s.recv(65536)
        return buf

    def cmd(self, name, **args):
        self.s.sendall((json.dumps({"execute": name, "arguments": args}) + "\n").encode())
        return self.recv()

    def move(self, x, y):
        ev = [{"type": "abs", "data": {"axis": "x", "value": int(x * 32767 / W)}},
              {"type": "abs", "data": {"axis": "y", "value": int(y * 32767 / H)}}]
        self.cmd("input-send-event", events=ev)
        time.sleep(0.3)

    def button(self, b, x, y):
        self.move(x, y)
        self.cmd("input-send-event", events=[{"type": "btn", "data": {"down": True, "button": b}}])
        time.sleep(0.15)
        self.cmd("input-send-event", events=[{"type": "btn", "data": {"down": False, "button": b}}])
        time.sleep(1.0)


def ink(tag):
    s = bt.shot(tag)
    return s[0] if s else 0.0


def changed(a, b, x0, y0, x1, y1):
    from PIL import Image, ImageChops
    box = (max(0, x0), max(0, y0), min(W, x1), min(H, y1))
    ia = Image.open(os.path.join(bt.OUT, "%s.screen.png" % a)).convert("RGB").crop(box)
    ib = Image.open(os.path.join(bt.OUT, "%s.screen.png" % b)).convert("RGB").crop(box)
    d = ImageChops.difference(ia, ib).convert("L").point(lambda v: 255 if v > 24 else 0)
    n = sum(1 for v in d.getdata() if v)
    return n / float(d.size[0] * d.size[1])


def scp(files, dst):
    for _ in range(8):
        r = subprocess.run(["scp"] + SSH + files + ["root@127.0.0.1:" + dst], capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            return True
        time.sleep(5)
    print("!! scp: %s" % (r.stdout + r.stderr).strip())
    return False


def journal(ser, pat, n=6):
    return ser.run("journalctl -b _COMM=ade-comp --no-pager | grep -E '%s' | tail -%d | cut -c17-200" % (pat, n))


def main():
    for p in (bt.SER, bt.MON, QMP):
        if os.path.exists(p):
            os.unlink(p)
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    cmd = bt.qemu_command()
    cmd += ["-device", "qemu-xhci,id=xhci", "-device", "usb-tablet,bus=xhci.0",
            "-qmp", "unix:%s,server,nowait" % QMP]
    q = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    ok = True
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "r9i.serial.txt"))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! no login prompt")
            return False
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)
        for _ in range(30):
            s = bt.shot("r9i-boot", quiet=True)
            if s and s[0] >= 0.005:
                break
            time.sleep(2)
        # 0. The new binaries in, the session restarted on them. apm and
        #    aos-sandbox too: the app sandbox is theirs. With APM_THIRDPARTY
        #    a local index directory (publish.sh --local), the recipes under
        #    test go in beside them and the guest reads them by file://.
        files = [os.path.join(TARGET, b) for b in ("ade-comp", "ade-shell", "ade-lock", "settings", "sysmon", "apm", "aos-sandbox")]
        if bt.APM_TP_LOCAL:
            files.append(bt.APM_THIRDPARTY.rstrip("/"))
        ser.run("mkdir -p /root/new")
        if not scp(["-r"] + files, "/root/new/"):
            return False
        print("$ install\n%s" % ser.run("ls -la /root/new; for f in /root/new/*; do [ -f $f ] && mv -f $f /usr/bin/; done; systemctl restart ade; sleep 12; "
                                       "journalctl -b _COMM=ade-comp --no-pager | tail -6 | cut -c17-200", timeout=120))
        for _ in range(30):
            s = bt.shot("r9i-desktop", quiet=True)
            if s and s[0] >= 0.005:
                break
            time.sleep(2)
        qmp = Qmp(QMP)
        print("$ xwayland at session start\n%s" % journal(ser, "xwayland|head "))

        # 1. The overview by keyboard: Super, Right, Enter starts the second
        #    tile; the journal names what was launched.
        bt.monitor("sendkey meta_l")
        time.sleep(3)
        ink("r9i-over")
        bt.monitor("sendkey right")
        time.sleep(1)
        ink("r9i-over-right")
        moved = changed("r9i-over", "r9i-over-right", 0, 300, W, H)
        bt.monitor("sendkey ret")
        time.sleep(6)
        launched = ser.run("journalctl -b --no-pager | grep 'ade-shell: launch' | tail -2 | cut -c17-120")
        print("== overview: highlight moved %.2f%%; launched:\n%s" % (moved * 100, launched))
        if moved < 0.001 or "launch" not in launched:
            print("!! the overview did not follow the keys")
            ok = False
        ser.run("pkill -x terminal; pkill -x files; pkill -x notepad; pkill -x images; pkill -x settings; pkill -x sysmon; sleep 1")

        # 1b. Firefox and Xwayland from the repositories the disk already
        #     knows (the apm run leaves the repos and the key, removes the
        #     packages).
        print("$ install firefox, xwayland\n%s" % ser.run(
            "apm repo remove thirdparty >/dev/null 2>&1; apm repo add thirdparty %s --third-party 2>&1 | tail -1; for i in $(seq 30); do getent hosts github.com >/dev/null 2>&1 && break; sleep 1; done; " % ("file:///root/new/" + os.path.basename(bt.APM_THIRDPARTY.rstrip("/")) if bt.APM_TP_LOCAL else bt.APM_THIRDPARTY) +
            "apm update --force --quiet 2>&1 | tail -1; apm --yes --force remove firefox >/dev/null 2>&1; rm -rf /home/admin/.var/app/mozilla.firefox; apm install firefox --quiet 2>&1 | tail -2; apm install xwayland --quiet 2>&1 | tail -2; "
            "ls /opt/apm/bin/ | head; sleep 25; journalctl -b _COMM=ade-comp --no-pager | grep -i xwayland | tail -4 | cut -c17-200", timeout=1500))
        # 2. Firefox maximised, its hamburger button at the top right: the
        #    menu must open on screen (a box left of and below the button
        #    changes), and the journal must show no popup grab warning.
        mapped = ser.run("journalctl -b _COMM=ade-comp --no-pager | grep -c 'toplevel mapped'").strip()
        ser.run("su -s /bin/sh admin -c '%s setsid /opt/apm/bin/firefox file:///etc/os-release >/tmp/ff.log 2>&1 &'" % ENV)
        for _ in range(60):
            time.sleep(3)
            now = ser.run("journalctl -b _COMM=ade-comp --no-pager | grep -c 'toplevel mapped'").strip()
            if now != mapped:
                break
        time.sleep(10)
        bt.monitor("sendkey meta_l-up")
        time.sleep(4)
        ink("r9i-ff")
        print("$ firefox\n%s" % ser.run("pgrep -a firefox | head -2; " + "journalctl -b _COMM=ade-comp --no-pager | grep -E 'mapped|snapped' | tail -3 | cut -c17-160"))
        # The sandbox, when the recipe declares one: the farm entry is a
        # wrapper, Firefox's home is its own, and the real home is not in
        # its mount table.
        print("$ sandbox\n%s" % ser.run("head -3 /opt/apm/bin/firefox | cut -c1-200; grep -c Exec=/usr/bin/aos-sandbox /opt/apm/exports/share/applications/mozilla.firefox.desktop; "
                                        "ls -la /home/admin/.var/app/ 2>&1 | tail -2; p=$(pgrep -f -o firefox/firefox); [ -n \"$p\" ] && grep -c ' /home/admin ' /proc/$p/mountinfo; "
                                        "[ -n \"$p\" ] && grep -E ' /home/admin[ /]' /proc/$p/mountinfo | awk '{print $4, $5}' | head -4; tail -5 /tmp/ff.log"))
        # The person's override (Settings -> Programs writes this line):
        # with "full" the real home is what Firefox mounts at /home/admin,
        # with the declaration it is the private one under .var/app.
        ser.run("pkill -f firefox; sleep 2; su -s /bin/sh admin -c 'mkdir -p /home/admin/.config/aos/sandbox; echo full > /home/admin/.config/aos/sandbox/mozilla.firefox'")
        ser.run("su -s /bin/sh admin -c '%s setsid /opt/apm/bin/firefox file:///etc/os-release >/tmp/ff2.log 2>&1 &'; sleep 12" % ENV)
        over = ser.run("p=$(pgrep -f -o firefox/firefox); echo pid=$p; grep -E ' /home/admin ' /proc/$p/mountinfo | awk '{print $4}' | head -2")
        print("$ override full: home source\n%s" % over)
        ser.run("pkill -f firefox; sleep 2; rm -f /home/admin/.config/aos/sandbox/mozilla.firefox")
        if "/.var/app/" in over or "/home/admin" not in over:
            print("!! the override did not give Firefox the real home: %r" % over)
            ok = False
        ser.run("su -s /bin/sh admin -c '%s setsid /opt/apm/bin/firefox file:///etc/os-release >/tmp/ff.log 2>&1 &'; sleep 12" % ENV)
        back = ser.run("p=$(pgrep -f -o firefox/firefox); grep -E ' /home/admin ' /proc/$p/mountinfo | awk '{print $4}' | head -2")
        print("$ declaration again: home source\n%s" % back)
        if "/.var/app/mozilla.firefox" not in back:
            print("!! without the override Firefox did not get its private home: %r" % back)
            ok = False
        # Maximised again for the hamburger's position below.
        bt.monitor("sendkey meta_l-up")
        time.sleep(4)
        return_early = os.environ.get("R9I_STOP_AT_FF")
        if return_early:
            print("== stopping after the firefox dump for a look")
            ser.send("poweroff\n")
            ser.read_until(b"reboot: Power down", 90)
            return ok
        hx, hy = int(os.environ.get("R9I_HX", W - 22)), int(os.environ.get("R9I_HY", 28 + 78))
        qmp.button("left", hx, hy)
        time.sleep(3)
        ink("r9i-ff-menu")
        menu = changed("r9i-ff", "r9i-ff-menu", W - 400, hy, W, hy + 400)
        print("== hamburger at %d,%d: box changed %.1f%%" % (hx, hy, menu * 100))
        print("$ journal: popup\n%s" % journal(ser, "popup|grab"))
        if menu < 0.05:
            print("!! the hamburger menu did not open")
            ok = False
        # An item in that menu must take the click: "New Window" is the
        # third entry (the G14: the menu opened but no item did anything,
        # 2026-10-03). A new toplevel mapping says it did.
        before = ser.run("journalctl -b _COMM=ade-comp --no-pager | grep -c 'toplevel mapped'").strip().lstrip("# ").strip()
        ix, iy = int(os.environ.get("R9I_IX", W - 160)), int(os.environ.get("R9I_IY", hy + 132))
        qmp.button("left", ix, iy)
        time.sleep(6)
        after = ser.run("journalctl -b _COMM=ade-comp --no-pager | grep -c 'toplevel mapped'").strip().lstrip("# ").strip()
        ink("r9i-ff-newwin")
        print("== menu item at %d,%d: toplevels %s -> %s" % (ix, iy, before, after))
        if before == after:
            print("!! the menu item took no click: no new window")
            ok = False
        bt.monitor("sendkey esc")
        time.sleep(1)
        ser.run("pkill -f firefox; sleep 2")

        # 3. Xwayland that cannot start: its pixman hidden, the session
        #    restarted; the compositor gives it three tries, the library
        #    comes back, and the fourth is ready.
        print("$ xwayland: break\n%s" % ser.run(
            "mkdir -p /root/aside; ls -la /opt/apm/lib/libpixman-1.so*; mv /opt/apm/lib/libpixman-1.so* /root/aside/; ldconfig /opt/apm/lib; systemctl restart ade; sleep 40; "
            "journalctl -b _COMM=ade-comp --no-pager | grep -E 'xwayland' | tail -6 | cut -c17-200", timeout=120))
        print("$ xwayland: mend\n%s" % ser.run(
            "mv /root/aside/libpixman-1.so* /opt/apm/lib/; ldconfig /opt/apm/lib; sleep 20; "
            "journalctl -b _COMM=ade-comp --no-pager | grep -E 'xwayland' | tail -4 | cut -c17-200; ls /tmp/.X11-unix/", timeout=120))
        xw = journal(ser, "xwayland", 12)
        if "starting again" not in xw or "ready on" not in xw.split("starting again")[-1]:
            print("!! xwayland was not started again, or the retry did not come up")
            ok = False
        for _ in range(30):
            s = bt.shot("r9i-desktop2", quiet=True)
            if s and s[0] >= 0.005:
                break
            time.sleep(2)

        # 4. sysmon's process list: a right click on a row opens the menu.
        ser.run("su -s /bin/sh admin -c '%s setsid sysmon --procs >/tmp/sysmon.log 2>&1 &'" % ENV)
        time.sleep(8)
        bt.monitor("sendkey meta_l-up")
        time.sleep(3)
        ink("r9i-sysmon")
        rx, ry = W // 2, 300
        qmp.button("right", rx, ry)
        time.sleep(2)
        ink("r9i-sysmon-menu")
        m = changed("r9i-sysmon", "r9i-sysmon-menu", rx - 20, ry - 20, rx + 260, ry + 120)
        print("== sysmon right-click: box changed %.1f%%" % (m * 100))
        if m < 0.02:
            print("!! no menu on the process row")
            ok = False
        bt.monitor("sendkey esc")
        ser.run("pkill -x sysmon; sleep 1")
        print("$ failed\n%s" % ser.run("systemctl --failed --no-legend"))
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
    print("\n== done, ok: %s" % ok)
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
