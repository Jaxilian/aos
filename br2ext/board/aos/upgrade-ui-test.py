#!/usr/bin/env python3
"""The update pipeline as a person meets it, on the installed QEMU disk
(boot-test.py install first): the check two minutes after boot, the toast,
a click on it opening Software's Update page, Upgrade system with a line
per package, and the OS written to the idle slot with a percentage.

The working tree's binaries (ade-comp, ade-shell, settings, aos-store,
apm) and the overlay's aos-update, aos-update-check and timer are copied
in over ssh and the session restarted on them, so this tests a build
without an ISO. A fake release 9.9.9 -- this build's core.img, its
SHA256SUMS signed with the local apm key -- is served from the host, and
update.conf in the guest is pointed at it. The package part uses the
public index over the network: whatever the disk has that is older.

  1. aos-update-check as root: /var/lib/aos/updates gains "AOS 9.9.9 is
     available"; within ten seconds the shell shows the toast.
  2. A click on the toast: an aos-store process with "update" appears.
  3. The window maximised (Super+Up) and screendumped: upd-store.
  4. With UPD_BX/UPD_BY set (the Upgrade system button's place, read off
     that dump): the click, the password typed into the modal bar, a
     dump every few seconds while apm runs
     (upd-run-N), the final page, the update log and grubenv.

Screendumps: upd-*. Serial transcript: upd.serial.txt beside the disk.
"""
import http.server
import importlib.util
import os
import shutil
import socketserver
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = ["boot-test.py", "disk"]
spec = importlib.util.spec_from_file_location("bt", os.path.join(HERE, "boot-test.py"))
bt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bt)
spec = importlib.util.spec_from_file_location("dt", os.path.join(HERE, "disk-test.py"))
dt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dt)

TARGET = os.path.join(bt.BASE, "output", "target")
OVERLAY = os.path.join(HERE, "rootfs-overlay")
RELEASE = os.path.join(bt.OUT, "update-release")
IMG = "aos-9.9.9-x86_64-core.img"
VERITY = "aos-9.9.9-x86_64-core.verity"
PORT = 8765
URL = "http://10.0.2.2:%d" % PORT
W, H = dt.W, dt.H
# sudo asks the store for the account's password; the test sets one and
# types it into the modal bar, key by key through QEMU's monitor.
PASS = "aostest"


def make_release():
    """A fake release 9.9.9 from this build: the core image as release.sh
    ships it, its verity file, and SHA256SUMS signed with the local key."""
    shutil.rmtree(RELEASE, ignore_errors=True)
    os.makedirs(RELEASE)
    os.link(os.path.join(bt.IMG, "core.img"), os.path.join(RELEASE, IMG))
    shutil.copy(os.path.join(bt.IMG, "core.verity"), os.path.join(RELEASE, VERITY))
    with open(os.path.join(RELEASE, "SHA256SUMS"), "w") as f:
        subprocess.run(["sha256sum", IMG, VERITY], cwd=RELEASE, stdout=f, check=True)
    subprocess.run([bt.APM_BIN, "sign", os.path.join(RELEASE, "SHA256SUMS")], check=True, stdout=subprocess.DEVNULL)


def serve():
    handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=RELEASE, **k)
    socketserver.TCPServer.allow_reuse_address = True    # the port a minute after the last driver's
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def main():
    make_release()
    httpd = serve()
    for p in (bt.SER, bt.MON, dt.QMP):
        if os.path.exists(p):
            os.unlink(p)
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    cmd = bt.qemu_command()
    cmd += ["-device", "qemu-xhci,id=xhci", "-device", "usb-tablet,bus=xhci.0",
            "-qmp", "unix:%s,server,nowait" % dt.QMP]
    q = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    ok = True
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "upd.serial.txt"))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! no login prompt")
            return False
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)
        for _ in range(30):
            s = bt.shot("upd-boot", quiet=True)
            if s and s[0] >= 0.005:
                break
            time.sleep(2)
        # 0. The new binaries and scripts in; the timer unit too, so the
        #    guest's systemd knows the two-minute check; the session
        #    restarted on the new shell.
        # The disk holds this build (a verity core since 0.2.0): nothing to
        # push. The update URL through /etc/aos/update.conf, which
        # aos-update reads over the core's (the /etc overlay is writable).
        print("$ install\n%s" % ser.run(
            "systemctl list-timers aos-update-check.timer --no-pager | head -3; "
            "mkdir -p /etc/aos; echo URL=%s > /etc/aos/update.conf; cat /etc/aos/update.conf; grep VERSION_ID /etc/os-release; "
            "echo admin:%s | chpasswd; rm -f /var/lib/aos/updates; systemctl restart ade; sleep 12; journalctl -b _SYSTEMD_UNIT=ade.service + SYSLOG_IDENTIFIER=ade-session --no-pager | tail -3 | cut -c17-200" % (URL, PASS), timeout=120))
        for _ in range(30):
            s = bt.shot("upd-desktop", quiet=True)
            if s and s[0] >= 0.005:
                break
            time.sleep(2)
        qmp = dt.Qmp(dt.QMP)

        # 1. The check, as the timer runs it, and the toast it brings.
        print("$ aos-update-check\n%s" % ser.run("for i in $(seq 30); do getent hosts github.com >/dev/null 2>&1 && break; sleep 1; done; "
                                                "time /usr/libexec/aos-update-check 2>&1 | tail -8; echo ---; cat /var/lib/aos/updates", timeout=600))
        # The shell looks at the file every ten seconds and the toast holds
        # six (ade v0.1.47); a screendump takes two and a half, too slow to
        # see the toast and then click it in time. So a click on the
        # toast's place every second until Software is up: a click on the
        # wallpaper does nothing, and only the toast's action starts
        # "aos-store update".
        store = ""
        for _ in range(25):
            qmp.button("left", W - 180, 70)
            time.sleep(1)
            store = ser.run("pgrep -a aos-store")
            if "aos-store" in store:
                break
        time.sleep(6)
        dt.ink("upd-clicked")
        store = ser.run("pgrep -a aos-store; journalctl -b _SYSTEMD_UNIT=ade.service + SYSLOG_IDENTIFIER=ade-session --no-pager | grep -i 'launch' | tail -2 | cut -c17-160")
        print("$ after the click\n%s" % store)
        if "aos-store update" not in store:
            print("!! the toast click did not open Software's Update page")
            ok = False
            ser.run("su -s /bin/sh admin -c '%s setsid aos-store update >/tmp/store.log 2>&1 &'; sleep 8" % dt.ENV)
        # 3. Maximised, so the button's place is a function of the screen.
        bt.monitor("sendkey meta_l-up")
        time.sleep(4)
        dt.ink("upd-store")

        bx, by = os.environ.get("UPD_BX"), os.environ.get("UPD_BY")
        if not (bx and by):
            print("== set UPD_BX/UPD_BY from upd-store.screen.png for the Upgrade system click")
        else:
            # 4. Upgrade system; the page while it runs, and what is left.
            qmp.button("left", int(bx), int(by))
            time.sleep(3)
            dt.ink("upd-unlock")
            for c in PASS:
                bt.monitor("sendkey %s" % c)
                time.sleep(0.2)
            bt.monitor("sendkey ret")
            time.sleep(4)
            dt.ink("upd-run-0")
            n = 0
            t_end = time.time() + 1500
            while time.time() < t_end:
                time.sleep(6)
                n += 1
                dt.ink("upd-run-%d" % n)
                if "apm" not in ser.run("pgrep -x apm || echo none"):
                    break
            time.sleep(6)
            dt.ink("upd-done")
            print("$ afterwards\n%s" % ser.run("tail -12 /var/log/aos-update.log | cut -c1-160; grub-editenv /boot/efi/grub/grubenv list; "
                                               "apm list 2>&1 | head; pgrep -a aos-store"))
            log = ser.run("grep -c '::os 9.9.9 downloading' /var/log/aos-update.log; grep '::os 9.9.9 done' /var/log/aos-update.log")
            print("$ progress lines in the log\n%s" % log)
            if "::os 9.9.9 done" not in log:
                print("!! the OS update did not report done")
                ok = False
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
        httpd.shutdown()
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
