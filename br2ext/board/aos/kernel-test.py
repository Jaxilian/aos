#!/usr/bin/env python3
"""The aos/kernel package on the installed QEMU disk (boot-test.py install
first): its hooks copy the kernel to /boot/bzImage.apm -- a copy, since the
store is on the data partition and GRUB cannot follow a link out of the
root slot -- and GRUB boots that file. Two boots:

  1. the package (kernel-test.py <file.apkg>) copied in over ssh and
     installed; bzImage.apm must be a regular file identical to the
     store's; poweroff
  2. the disk boots again, which GRUB can only do by reading that copy;
     then apm remove drops the copy and the module link

Transcripts: kernel-N.serial.txt beside the disk image."""
import importlib.util
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv, apkg = ["boot-test.py", "disk"], os.path.abspath(sys.argv[1])
spec = importlib.util.spec_from_file_location("ut", os.path.join(HERE, "update-test.py"))
ut = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ut)
bt = ut.bt

KEY = os.path.expanduser("~/.ssh/id_ed25519")
SCP = ["scp", "-P", str(bt.SSH_PORT), "-i", KEY, "-o", "StrictHostKeyChecking=no",
       "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes"]


def main():
    name = os.path.basename(apkg)
    ut.CHECKS[:] = [ut.SLOT, ut.FAILED, "ls -l /boot/ | grep bzImage; ls -l /usr/lib/modules/"]
    return run_with_copy(name)


def run_with_copy(name):
    ok = True
    print("== boot 1: copy the package in, install it")
    for p in (bt.SER, bt.MON):
        if os.path.exists(p):
            os.unlink(p)
    import shutil
    shutil.copy(bt.OVMF_VARS, bt.VARS)
    q = subprocess.Popen(bt.qemu_command(), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        ser = bt.Serial(bt.SER, os.path.join(bt.OUT, "kernel-1.serial.txt"))
        if ser.read_until(b"login:", bt.LOGIN_TIMEOUT) is None:
            print("!! no login prompt")
            return False
        ser.send("root\n")
        ser.read_until(b"# ", 30)
        ser.send("stty -echo cols 200 rows 50; export SYSTEMD_PAGER= PAGER=cat\n")
        ser.read_until(b"# ", 10)
        print(ser.run("for i in $(seq 20); do systemctl is-active sshd >/dev/null && break; sleep 3; done; systemctl is-active sshd", timeout=120))
        r = None
        for _ in range(8):
            r = subprocess.run(SCP + [apkg, "root@127.0.0.1:/root/"], capture_output=True, text=True, timeout=300)
            if r.returncode == 0:
                break
        if r.returncode != 0:
            print("!! scp: %s" % (r.stdout + r.stderr).strip())
            return False
        for c in ["apm install /root/%s --quiet 2>&1 | tail -3" % name,
                  "ls -l /boot/ | grep bzImage",
                  "cmp /boot/bzImage.apm /opt/apm/packages/aos/kernel/current/boot/bzImage && echo same",
                  "ls -l /usr/lib/modules/",
                  ut.FAILED]:
            o = ser.run(c, timeout=600)
            print("\n$ %s\n%s" % (c, o))
            if c.startswith("cmp") and "same" not in o:
                print("!! /boot/bzImage.apm is not the package's kernel")
                ok = False
            if c.startswith("ls -l /boot") and "-> " in o.replace("bzImage.prev", ""):
                print("!! /boot/bzImage.apm is a symlink")
                ok = False
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

    print("\n== boot 2: GRUB boots the copy; then remove the package")
    out = ut.boot(2, ["apm remove kernel --yes --quiet 2>&1 | tail -2",
                      "ls -l /boot/ | grep bzImage; ls -l /usr/lib/modules/"])
    if out is None:
        print("!! the disk did not boot with bzImage.apm in place")
        return False
    if "0 loaded" not in out[ut.FAILED]:
        print("!! failed units")
        ok = False
    after = out["ls -l /boot/ | grep bzImage; ls -l /usr/lib/modules/"]
    if "bzImage.apm" in after:
        print("!! bzImage.apm survived apm remove")
        ok = False
    return ok


if __name__ == "__main__":
    ok = main()
    print("\n== done, kernel package ok:", ok)
    sys.exit(0 if ok else 1)
