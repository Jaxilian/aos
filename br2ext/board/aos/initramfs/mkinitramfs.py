#!/usr/bin/env python3
"""The initramfs from the target's own binaries: the programs init needs,
every library they load (readelf's NEEDED, followed), the dynamic loader,
and init itself, as a gzip'd newc cpio owned by root.

    mkinitramfs.py TARGET_DIR HOST_DIR OUT.img

Called by post-build.sh. Fails loudly on a missing program: an initramfs
that lacks veritysetup boots nothing."""
import os
import subprocess
import sys

PROGS = [
    "bin/bash", "bin/mount", "bin/umount", "bin/switch_root", "bin/losetup",
    "bin/blkid", "bin/mkdir", "bin/cp", "bin/cat", "bin/ls", "bin/sleep",
    "bin/seq", "bin/chmod", "bin/echo", "bin/sh",
    "sbin/veritysetup", "sbin/cryptsetup", "sbin/e2fsck",
]
LIBDIRS = ["usr/lib"]


def needed(readelf, path):
    out = subprocess.run([readelf, "-d", path], capture_output=True, text=True).stdout
    libs = []
    for line in out.splitlines():
        if "(NEEDED)" in line and "[" in line:
            libs.append(line.split("[")[1].rstrip("]"))
    return libs


def main():
    target, host, out = sys.argv[1], sys.argv[2], sys.argv[3]
    readelf = os.path.join(host, "bin", "llvm-readelf")
    stage = out + ".d"
    subprocess.run(["rm", "-rf", stage], check=True)
    for d in ("usr/bin", "usr/sbin", "usr/lib", "dev", "proc", "sys", "run", "sysroot", "media", "etc"):
        os.makedirs(os.path.join(stage, d), exist_ok=True)
    for link, to in (("bin", "usr/bin"), ("sbin", "usr/sbin"), ("lib", "usr/lib"), ("lib64", "usr/lib"), ("usr/lib64", "lib")):
        os.symlink(to, os.path.join(stage, link))

    copied = set()
    todo = []
    for p in PROGS:
        src = os.path.realpath(os.path.join(target, "usr", p))
        if not os.path.isfile(src):
            sys.exit("mkinitramfs: no %s in the target" % p)
        dst = os.path.join(stage, "usr", p)
        subprocess.run(["cp", "-a", src, dst], check=True)
        todo.append(src)
    while todo:
        src = todo.pop()
        for lib in needed(readelf, src):
            if lib in copied:
                continue
            found = None
            for d in LIBDIRS:
                cand = os.path.join(target, d, lib)
                if os.path.exists(cand):
                    found = cand
                    break
            if not found:
                sys.exit("mkinitramfs: %s needs %s, which the target lacks" % (src, lib))
            copied.add(lib)
            real = os.path.realpath(found)
            dst = os.path.join(stage, "usr/lib", lib)
            subprocess.run(["cp", "-a", real, dst], check=True)
            todo.append(real)
    # The loader, by the name the binaries ask for.
    ld = os.path.join(target, "usr/lib/ld-linux-x86-64.so.2")
    if not os.path.exists(ld):
        sys.exit("mkinitramfs: no dynamic loader in the target")
    subprocess.run(["cp", "-a", os.path.realpath(ld), os.path.join(stage, "usr/lib/ld-linux-x86-64.so.2")], check=True)
    here = os.path.dirname(os.path.abspath(__file__))
    subprocess.run(["cp", os.path.join(here, "init"), os.path.join(stage, "init")], check=True)
    os.chmod(os.path.join(stage, "init"), 0o755)
    with open(out, "wb") as f:
        find = subprocess.Popen(["find", "."], cwd=stage, stdout=subprocess.PIPE)
        sort = subprocess.Popen(["sort"], stdin=find.stdout, stdout=subprocess.PIPE, env={"LC_ALL": "C"})
        cpio = subprocess.Popen(["cpio", "--quiet", "-o", "-H", "newc", "-R", "0:0", "--reproducible"], cwd=stage, stdin=sort.stdout, stdout=subprocess.PIPE)
        gz = subprocess.Popen(["gzip", "-9", "-n"], stdin=cpio.stdout, stdout=f)
        gz.wait()
        for p in (find, sort, cpio):
            p.wait()
    subprocess.run(["rm", "-rf", stage], check=True)
    print("mkinitramfs: %s, %d KB, %d libraries" % (out, os.path.getsize(out) // 1024, len(copied)))


if __name__ == "__main__":
    main()
