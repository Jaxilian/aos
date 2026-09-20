#!/usr/bin/env python3
"""Lift one Buildroot package out of the target tree into an apm package.

    br2apkg.py <package> [--org aos] [--kind lib|bin|app] [--global]
               [--version V] [--license L] [--summary S]
               [--depends org/name@track ...] [--out DIR]

Buildroot records what each package installed into the target as
output/build/<pkg>-<ver>/.files-list.txt, one "<pkg>,./path" line per file.
This copies exactly those files into a payload laid out for the store --
./usr/lib/x -> lib/x, ./etc/x -> etc/x -- writes a manifest.toml beside
them, and hands the directory to `apm ship`. The result is a prebuilt .apkg
of a package Buildroot cross-compiled with the AOS toolchain, which is the
only way to get the graphics and input stack, or GTK3, into apm: the
client cannot build those itself.

Development files ship too (headers, .pc files, the unversioned .so
links): AOS is self-hosting, and a library a program on the machine links
against has to be linkable there. pkg-config files have their prefix
rewritten from /usr to the package's versioned store path.

Metadata comes from `make <pkg>-show-info` unless given on the command
line; that runs make, so it must not overlap a running build. The
dependency list is not derived from Buildroot's -- those are build-order
edges, most of them to things the foundation carries -- and is given
explicitly, as apm packages.

Needs: a built output/ tree, and apm on PATH or in APM.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
BUILD = os.path.join(BASE, "output", "build")
TARGET = os.path.join(BASE, "output", "target")
APM = os.environ.get("APM", os.path.join(BASE, "..", "apm", "target", "release", "apm"))

# Where a target path lands in the payload. Order matters: first match wins.
LAYOUT = [
    ("./usr/", ""),
    ("./lib/", "lib/"),
    ("./bin/", "bin/"),
    ("./sbin/", "bin/"),
    ("./etc/", "etc/"),
    ("./opt/", "opt/"),
]
SKIP = ("./usr/share/doc/", "./usr/share/man/", "./usr/share/info/", "./usr/share/locale/",
        "./usr/lib/systemd/system/multi-user.target.wants/")


def build_dir(pkg):
    dirs = sorted(d for d in os.listdir(BUILD) if re.fullmatch(re.escape(pkg) + r"-[0-9][^/]*", d))
    if not dirs:
        sys.exit("br2apkg: no output/build/%s-<version>; is it built?" % pkg)
    return os.path.join(BUILD, dirs[-1])


def show_info(pkg):
    """`make <pkg>-show-info` as a dict, or None if make is busy elsewhere."""
    if subprocess.run(["pgrep", "-x", "make"], capture_output=True).returncode == 0:
        return None
    r = subprocess.run(["make", "-s", "--no-print-directory", "%s-show-info" % pkg],
                       cwd=BASE, capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return json.loads(r.stdout).get(pkg)


def payload_path(target_path):
    for prefix, dest in LAYOUT:
        if target_path.startswith(prefix):
            return dest + target_path[len(prefix):]
    return None


def toml_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("package")
    ap.add_argument("--org", default="aos")
    ap.add_argument("--kind", default="lib", choices=["lib", "bin", "app"])
    ap.add_argument("--global", dest="global_", action="store_true",
                    help="sonames join the system loader path")
    ap.add_argument("--version")
    ap.add_argument("--license")
    ap.add_argument("--summary")
    ap.add_argument("--depends", action="append", default=[], metavar="org/name@track")
    ap.add_argument("--out", default=os.getcwd())
    a = ap.parse_args()

    pkg = a.package
    bdir = build_dir(pkg)
    info = show_info(pkg) if not (a.version and a.license) else None
    version = a.version or (info or {}).get("version") or bdir.rsplit("-", 1)[-1]
    license_ = a.license or ",".join((info or {}).get("licenses", "").split(", ")) or "unknown"
    summary = a.summary or "%s, built by Buildroot for AOS" % pkg
    # Buildroot versions are not always semver ("2.1", "1.20.1", "126").
    parts = version.split(".")
    while len(parts) < 3:
        parts.append("0")
    semver = ".".join(parts[:3])

    with open(os.path.join(bdir, ".files-list.txt")) as f:
        files = [line.rstrip("\n").split(",", 1)[1] for line in f if line.startswith(pkg + ",")]
    if not files:
        sys.exit("br2apkg: %s installed nothing to the target" % pkg)

    work = os.path.join(a.out, "%s-%s.payload" % (pkg, version))
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    commands, sonames, skipped = [], [], []
    runtime_prefix = "/opt/apm/packages/%s/%s/%s" % (a.org, pkg, semver)

    for tp in sorted(files):
        if tp.startswith(SKIP):
            skipped.append(tp)
            continue
        rel = payload_path(tp)
        if rel is None:
            skipped.append(tp)
            continue
        src = os.path.join(TARGET, tp)
        dst = os.path.join(work, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.islink(src):
            link = os.readlink(src)
            if link.startswith("/"):
                # Absolute links into /usr are wrong in the store; make them
                # relative to where the target will live.
                tgt = payload_path("." + link)
                link = os.path.relpath(os.path.join(work, tgt), os.path.dirname(dst)) if tgt else link
            os.symlink(link, dst)
        elif os.path.isdir(src):
            os.makedirs(dst, exist_ok=True)
        else:
            shutil.copy2(src, dst)
            if rel.endswith(".pc"):
                with open(dst) as f:
                    text = f.read()
                text = re.sub(r"^prefix=.*$", "prefix=" + runtime_prefix, text, flags=re.M)
                with open(dst, "w") as f:
                    f.write(text)
        if rel.startswith("bin/") and rel.count("/") == 1 and not os.path.isdir(src):
            commands.append(rel[4:])
        m = re.fullmatch(r"lib/(lib[^/]+\.so\.\d+)", rel)
        if m:
            sonames.append(m.group(1))

    deps = []
    for d in a.depends:
        org_name, _, track = d.partition("@")
        org, _, name = org_name.partition("/")
        deps.append((org, name, track or "*"))

    manifest = [
        "# Generated by br2apkg.py from Buildroot's %s; do not edit." % pkg,
        "manifest_version = 1",
        "",
        "[package]",
        "name         = %s" % toml_str(pkg),
        "organization = %s" % toml_str(a.org),
        "version      = %s" % toml_str(semver),
        "release      = 1",
        "kind         = %s" % toml_str(a.kind),
        "summary      = %s" % toml_str(summary),
        "license      = %s" % toml_str(license_),
        "",
        "[provides]",
        "command = [%s]" % ", ".join(toml_str(c) for c in sorted(commands)),
        "soname  = [%s]" % ", ".join(toml_str(s) for s in sorted(set(sonames))),
        "global  = %s" % ("true" if a.global_ else "false"),
        "",
        "[requires]",
        "run = []",
    ]
    for org, name, track in deps:
        manifest += ["", "[[dependencies]]", "name         = %s" % toml_str(name),
                     "organization = %s" % toml_str(org), "track        = %s" % toml_str(track)]
    if a.global_ and sonames:
        manifest += ["", "[hooks]", 'post_install = "ldconfig"', 'post_remove  = "ldconfig"']
    with open(os.path.join(work, "manifest.toml"), "w") as f:
        f.write("\n".join(manifest) + "\n")

    r = subprocess.run([APM, "ship", work], cwd=a.out, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("br2apkg: apm ship failed:\n" + r.stderr)
    print(r.stdout.strip())
    print("  files     %d copied, %d skipped (docs, man, locale, out-of-layout)" % (len(files) - len(skipped), len(skipped)))
    if not info and not (a.version and a.license):
        print("  metadata  guessed from the build directory; pass --version/--license or run when make is idle", file=sys.stderr)
    shutil.rmtree(work)


if __name__ == "__main__":
    main()
