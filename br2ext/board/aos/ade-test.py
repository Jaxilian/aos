#!/usr/bin/env python3
"""Checks of the desktop's behaviour in QEMU (first written for G14 round 8): a popup with a grab (the viewer's right-click
menu) opened, dismissed by a click outside, and clicks still working
after; an item picked from that menu actually runs; the keyboard layout
changed live through /etc/ade/environment; the overview toggled quickly
with its icons intact; a second display plugged in extends the desktop
and a window dragged across the seam lands on it. Screendumps: r8-*."""
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import time

BT = "/home/jax/Projects/OS/aos/br2ext/board/aos/boot-test.py"
sys.argv = ["boot-test.py", "desktop"]
spec = importlib.util.spec_from_file_location("bt", BT)
bt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bt)

PNG = os.path.join(bt.OUT, "r8-test.png")
QMP = os.path.join(bt.OUT, "r8-qmp.sock")
W, H = 1280, 800
ENV = ("WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/1000 HOME=/home/admin "
       "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus")


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


def test_png(path, w=320, h=200):
    """A gradient the viewer can open, written without any library."""
    import struct
    import zlib
    rows = b"".join(b"\x00" + bytes(c for x in range(w) for c in (x * 255 // w, y * 255 // h, 128, 255))
                    for y in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def ink(tag):
    s = bt.shot(tag)
    return s[0] if s else 0.0


def changed(a, b, x, y, r=220):
    """The share of pixels that differ between two screendumps inside a
    box around (x, y): a menu opening or closing there shows as a change
    that the whole-screen ink figure hides."""
    from PIL import Image, ImageChops
    box = (max(0, x - 40), max(0, y - 40), min(W, x + r), min(H, y + r))
    ia = Image.open(os.path.join(bt.OUT, "%s.screen.png" % a)).convert("RGB").crop(box)
    ib = Image.open(os.path.join(bt.OUT, "%s.screen.png" % b)).convert("RGB").crop(box)
    d = ImageChops.difference(ia, ib).convert("L").point(lambda v: 255 if v > 24 else 0)
    n = sum(1 for v in d.getdata() if v)
    return n / float(d.size[0] * d.size[1])


def dump2(qmp, tag, head):
    """Screendump one head of the two-output GPU; the share of ink on it."""
    ppm = os.path.join(bt.OUT, "%s.screen.ppm" % tag)
    png = os.path.join(bt.OUT, "%s.screen.png" % tag)
    qmp.cmd("screendump", filename=ppm, device="vga0", head=head)
    time.sleep(1.5)
    if not os.path.exists(ppm):
        print("!! screendump %s: none" % tag)
        return 0.0
    w, h, n, ink_, _ = bt.png_from_ppm(ppm, png)
    os.unlink(ppm)
    print("\n== screendump head %d %dx%d, ~%d colours, %.1f%% ink -> %s" % (head, w, h, n, ink_ * 100, png))
    return ink_


def scp(src, dst):
    key = os.path.expanduser("~/.ssh/id_ed25519")
    for _ in range(8):
        r = subprocess.run(["scp", "-P", str(bt.SSH_PORT), "-i", key, "-o", "StrictHostKeyChecking=no",
                            "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes",
                            src, "root@127.0.0.1:" + dst], capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            return True
        time.sleep(5)
    return False


def main():
    for p in (bt.SER, bt.MON, QMP):
        if os.path.exists(p):
            os.unlink(p)
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    # Two outputs on the one GPU, the second off until step 4 plugs it
    # in; and a relative mouse beside the tablet, which ade merges into
    # the same pointer, since only relative motion can leave a display.
    cmd = bt.qemu_command()
    cmd[cmd.index("virtio-vga")] = "virtio-vga,id=vga0,max_outputs=2"
    cmd += ["-device", "usb-mouse,bus=xhci.0", "-qmp", "unix:%s,server,nowait" % QMP]
    q = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    ok = True
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "r8.serial.txt"))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! no login prompt")
            return False
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)
        for _ in range(30):
            s = bt.shot("r8-desktop", quiet=True)
            if s and s[0] >= 0.005:
                break
            time.sleep(2)
        base = ink("r8-desktop")
        qmp = Qmp(QMP)
        print("$ fonts and nodes\n%s" % ser.run("ls -l /usr/share/fonts; ls /usr/bin/nvidia-nodes; systemctl status nvidia-devices --no-pager 2>&1 | head -3"))

        # 1. A popup with a grab: the viewer's right-click menu. Clicking
        #    outside it must dismiss it, and the next click must reach the
        #    window (a second menu opens where it lands).
        test_png(PNG)
        scp(PNG, "/tmp/test.png")
        ser.run("mkdir -p /tmp/pics && cp /tmp/test.png /tmp/pics/a.png && chmod -R a+rwX /tmp/pics")
        ser.run("su -s /bin/sh admin -c '%s setsid images /tmp/pics/a.png >/tmp/images.log 2>&1 &'" % ENV)
        time.sleep(8)
        ink("r8-viewer")
        print("$ viewer\n%s" % ser.run("pgrep -a images; head -3 /tmp/images.log"))
        qmp.button("right", W // 2, H // 2)
        time.sleep(2)
        ink("r8-menu")
        menu = changed("r8-viewer", "r8-menu", W // 2, H // 2)
        qmp.button("left", W // 2 - 250, H // 2)
        time.sleep(2)
        ink("r8-menu-gone")
        gone = changed("r8-menu", "r8-menu-gone", W // 2, H // 2)
        qmp.button("right", W // 2 - 200, H // 2 + 60)
        time.sleep(2)
        ink("r8-menu-again")
        again = changed("r8-menu-gone", "r8-menu-again", W // 2 - 200, H // 2 + 60)
        print("== menu opened %.1f%% -> closed %.1f%% -> second opened %.1f%% (box change)" % (menu * 100, gone * 100, again * 100))
        if not (menu > 0.02 and gone > 0.02 and again > 0.02):
            print("!! the popup grab did not dismiss and hand the click on")
            ok = False
        # An item of that second menu, its first row, "Rotate 90 Right": the
        # landscape picture turns to portrait. The menu is drawn on the
        # window's decoration, the click moves the pointer onto it from the
        # content, and a compositor that moved keyboard focus between the
        # two surfaces closed the menu under the click (Set as Wallpaper
        # did nothing on the G14).
        qmp.button("left", W // 2 - 200 + 60, H // 2 + 60 + 17)
        time.sleep(2)
        ink("r8-item")
        turned = changed("r8-menu-gone", "r8-item", W // 2, H // 2 - 60)
        print("== menu item: picture changed %.1f%%" % (turned * 100))
        if turned < 0.02:
            print("!! a right-click menu item did not run")
            ok = False
        bt.monitor("sendkey esc")
        time.sleep(1)
        print("$ journal: grabs\n%s" % ser.run("journalctl -b _COMM=ade-comp --no-pager | grep -iE 'grab|popup' | tail -5 | cut -c17-160; tail -5 /tmp/images.log"))
        ser.run("pkill -x images; sleep 1")

        # 2. The keyboard layout, live: Swedish puts + where US has -.
        bt.monitor("sendkey meta_l-ret")
        time.sleep(5)
        bt.typekeys("echo ")
        bt.monitor("sendkey minus")
        time.sleep(1)
        ink("r8-us")
        # The live ISO's /etc is read-only: a writable copy of /etc/ade
        # bound over it, as an installed system would simply be written.
        print("$ layout -> se\n%s" % ser.run("cp -a /etc/ade /tmp/ade && mount --bind /tmp/ade /etc/ade && sleep 3 && "
            "(grep -q '^XKB_DEFAULT_LAYOUT=' /etc/ade/environment && sed -i 's/^XKB_DEFAULT_LAYOUT=.*/XKB_DEFAULT_LAYOUT=se/' /etc/ade/environment || echo XKB_DEFAULT_LAYOUT=se >> /etc/ade/environment); grep XKB /etc/ade/environment"))
        time.sleep(5)
        bt.monitor("sendkey minus")
        time.sleep(2)
        ink("r8-se")
        print("$ journal: layout\n%s" % ser.run("journalctl -b _COMM=ade-comp --no-pager | grep -i 'keyboard layout' | tail -2 | cut -c17-160"))
        bt.monitor("sendkey ret")
        time.sleep(1)
        typed = ink("r8-typed")

        # 3. The overview toggled fast, five times, then opened: icons stay.
        # Four fast taps (closed again), a pause, then one: open, with icons.
        for _ in range(4):
            bt.monitor("sendkey meta_l")
            time.sleep(0.6)
        time.sleep(3)
        bt.monitor("sendkey meta_l")
        time.sleep(4)
        # The overview's panel covers most of the screen: the ink moves
        # either way when it is up (down, since ade v0.1.24 -- the panel
        # is darker than the wallpaper it now shows through its corners).
        icons = abs(ink("r8-overview") - typed)
        print("== overview drawn: ink moved %.1f%%" % (icons * 100))
        if icons < 0.05:
            print("!! the overview did not open")
            ok = False
        bt.monitor("sendkey esc")
        time.sleep(1)

        # 4. A second display, plugged in while the session runs. QEMU with
        #    no display window reports only the first output connected, so
        #    the connector is forced on and the change announced the way a
        #    cable does. The terminal from step 2 is dragged by its title
        #    to the right, across the seam; it must show on the second
        #    display and be gone from the first.
        print("$ plug\n%s" % ser.run(
            "c=$(ls -d /sys/class/drm/card*-Virtual-2); echo on > $c/status; "
            "udevadm trigger --action=change --subsystem-match=drm --property-match=DEVTYPE=drm_minor; sleep 4; "
            "journalctl -b _COMM=ade-comp --no-pager | grep -E 'head ' | cut -c17-120"))
        empty = dump2(qmp, "r9-second-empty", 1)
        print("== second display: ink %.1f%% with only the shell on it" % (empty * 100))
        if empty < 0.005:
            print("!! no bar on the second display")
            ok = False
        qmp.move(500, 200)
        qmp.cmd("input-send-event", events=[{"type": "btn", "data": {"down": True, "button": "left"}}])
        time.sleep(0.3)
        for _ in range(30):
            qmp.cmd("input-send-event", events=[{"type": "rel", "data": {"axis": "x", "value": 30}}])
            time.sleep(0.05)
        time.sleep(0.5)
        qmp.cmd("input-send-event", events=[{"type": "btn", "data": {"down": False, "button": "left"}}])
        time.sleep(2)
        second = dump2(qmp, "r9-second", 1)
        print("== second display: ink %.1f%% after the drag" % (second * 100))
        if second < 0.1:
            print("!! the window did not reach the second display")
            ok = False

        # 5. Mirror, from the settings file: the second display, smaller
        #    (1024x768 against 1280x800), runs at a scale that fits the
        #    first's whole picture; its dump shows the terminal that step 4
        #    left on the first display, not the plain background.
        print("$ mirror\n%s" % ser.run(
            "mount -t tmpfs -o mode=755,uid=1000,gid=1000 tmpfs /home/admin 2>/dev/null; "
            "su -s /bin/sh admin -c 'mkdir -p ~/.config/ade && echo mirror=yes > ~/.config/ade/display'; sleep 6; "
            "journalctl -b _COMM=ade-comp --no-pager | grep -E 'scale' | tail -2 | cut -c17-120"))
        bt.monitor("sendkey meta_l-ret")
        time.sleep(5)
        first = dump2(qmp, "r9-mirror-0", 0)
        mirror = dump2(qmp, "r9-mirror-1", 1)
        print("== mirror: first %.1f%%, second %.1f%% ink" % (first * 100, mirror * 100))
        if mirror < 0.1 or abs(first - mirror) > 0.25:
            print("!! the mirror does not show the first display's picture")
            ok = False
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
