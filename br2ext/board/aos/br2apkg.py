#!/usr/bin/env python3
"""Lift one Buildroot package out of the target tree into an apm package.

    br2apkg.py <package>... [--name N] [--org aos] [--kind lib|bin|app]
               [--global] [--version V] [--license L] [--summary S]
               [--depends org/name@track ...] [--wrapper CMD] [--out DIR]

Several packages make one bundle, named by --name: a runtime is one
package with one wrapper, not thirty packages and a graph of edges to
keep by hand. --wrapper CMD generates bin/CMD, which sets the loader path
and the toolkit's data paths to this package's versioned directory and
execs its arguments; an application's launcher then runs
"CMD bin/theapp". Text files under etc/ and *.cache files have /usr
rewritten to that directory too -- the pixbuf loader cache, fonts.conf.

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

Needs: a built output tree (BR2_OUTPUT to name another than output/), and
apm on PATH or in APM.
"""

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
# The output tree to read: the image's by default, or a second one built
# from another configuration (the packages that must never enter the image).
OUTPUT = os.environ.get("BR2_OUTPUT", os.path.join(BASE, "output"))
BUILD = os.path.join(OUTPUT, "build")
TARGET = os.path.join(OUTPUT, "target")
# Development files -- headers, .pc, the unversioned .so links -- are what
# target-finalize strips from a target tree that keeps none; they survive
# in the staging sysroot, which is where they are taken from then.
STAGING = os.path.join(OUTPUT, "staging")
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
    r = subprocess.run(["make", "-s", "--no-print-directory", "O=" + OUTPUT, "%s-show-info" % pkg],
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
    ap.add_argument("packages", nargs="+", metavar="package")
    ap.add_argument("--name", help="the package name; required for a bundle")
    ap.add_argument("--wrapper", metavar="CMD", help="generate bin/CMD setting this package's environment")
    ap.add_argument("--org", default="aos")
    ap.add_argument("--kind", default="lib", choices=["lib", "bin", "app"])
    ap.add_argument("--global", dest="global_", action="store_true",
                    help="sonames join the system loader path")
    ap.add_argument("--version")
    ap.add_argument("--release", type=int, default=1,
                    help="the package release: bump it when the same version is rebuilt")
    ap.add_argument("--license")
    ap.add_argument("--summary")
    ap.add_argument("--depends", action="append", default=[], metavar="org/name@track")
    ap.add_argument("--extra", action="append", default=[], metavar="pkg:./target/path",
                    help="one file of another package, for a bundle that must not carry the rest of it")
    ap.add_argument("--launcher", action="store_true",
                    help="derive [launcher] from the .desktop the package installed")
    ap.add_argument("--out", default=os.getcwd())
    a = ap.parse_args()

    if len(a.packages) > 1 and not (a.name and a.version and a.license):
        sys.exit("br2apkg: a bundle needs --name, --version and --license")
    pkg = a.name or a.packages[0]
    bdir = build_dir(a.packages[0])
    info = show_info(pkg) if not (a.version and a.license) else None
    version = a.version or (info or {}).get("version") or bdir.rsplit("-", 1)[-1]
    license_ = a.license or ",".join((info or {}).get("licenses", "").split(", ")) or "unknown"
    summary = a.summary or "%s, built by Buildroot for AOS" % pkg
    # Buildroot versions are not always semver ("2.1", "1.20.1", "126").
    parts = version.split(".")
    while len(parts) < 3:
        parts.append("0")
    semver = ".".join(parts[:3])

    files = []
    for member in a.packages:
        with open(os.path.join(build_dir(member), ".files-list.txt")) as f:
            files += [line.rstrip("\n").split(",", 1)[1] for line in f if line.startswith(member + ",")]
    # --extra pkg:./path (a glob): single files borrowed from a package that
    # is not a member, for a bundle that must not carry the rest of it --
    # Mesa's GLX vendor library without Mesa.
    for e in a.extra:
        pkg_name, _, pattern = e.partition(":")
        if not pattern.startswith("./"):
            sys.exit("br2apkg: --extra wants pkg:./target/path, got %s" % e)
        with open(os.path.join(build_dir(pkg_name), ".files-list.txt")) as f:
            hits = [line.rstrip("\n").split(",", 1)[1] for line in f
                    if line.startswith(pkg_name + ",") and fnmatch.fnmatch(line.rstrip("\n").split(",", 1)[1], pattern)]
        if not hits:
            sys.exit("br2apkg: --extra %s matched nothing in %s" % (pattern, pkg_name))
        files += hits
    files = sorted(set(files))
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
        if not os.path.lexists(src):
            src = os.path.join(STAGING, tp)
            if not os.path.lexists(src):
                skipped.append(tp)
                continue
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
            elif rel.endswith(".cache") or rel.startswith("etc/"):
                # Loader caches and configuration name /usr paths; they
                # must name this package's own directory instead.
                try:
                    with open(dst) as f:
                        text = f.read()
                except UnicodeDecodeError:
                    text = None
                if text and "/usr/" in text:
                    text = text.replace("/usr/lib/", runtime_prefix + "/lib/").replace("/usr/share/", runtime_prefix + "/share/").replace("/usr/etc/", runtime_prefix + "/etc/")
                    with open(dst, "w") as f:
                        f.write(text)
        if rel.startswith("bin/") and rel.count("/") == 1 and not os.path.isdir(src):
            commands.append(rel[4:])
        m = re.fullmatch(r"lib/(lib[^/]+\.so\.\d+)", rel)
        if m:
            sonames.append(m.group(1))

    if a.wrapper:
        os.makedirs(os.path.join(work, "bin"), exist_ok=True)
        wrapper = os.path.join(work, "bin", a.wrapper)
        with open(wrapper, "w") as f:
            f.write("""#!/bin/sh
# Run a program against the %s runtime: this package's libraries first on
# the loader path, and the toolkit's data where this package put it.
# Generated by br2apkg; the paths are this version's own, so an upgrade
# never changes what a running program already resolved.
P=%s
export PATH="$P/bin:$PATH"
export LD_LIBRARY_PATH="$P/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export XDG_DATA_DIRS="$P/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
export GSETTINGS_SCHEMA_DIR="$P/share/glib-2.0/schemas"
export FONTCONFIG_FILE="$P/etc/fonts/fonts.conf"
export GDK_BACKEND=wayland
for cache in "$P"/lib/gdk-pixbuf-2.0/*/loaders.cache; do
	[ -f "$cache" ] && export GDK_PIXBUF_MODULE_FILE="$cache"
done
export GTK_PATH="$P/lib/gtk-3.0"
export GIO_EXTRA_MODULES="$P/lib/gio/modules"
exec "$@"
""" % (pkg, runtime_prefix))
        os.chmod(wrapper, 0o755)
        # The wrapper is the one command on PATH: a runtime's own tools run
        # through it, since bare they would not find its libraries.
        commands = [a.wrapper]

    # A library bundle exports no commands unless it has a wrapper: its bin/
    # holds the tools its members happened to install, and for a foreign
    # ABI -- compat32's 32-bit gpg-error -- they cannot even run outside
    # the sandbox. They stay in the payload for whoever runs in there.
    if a.kind == "lib" and not a.wrapper:
        commands = []

    # An app's .desktop entry: apm generates its own from [launcher], so the
    # installed file becomes the manifest table and is not shipped.
    launcher = None
    if a.launcher:
        for tp in files:
            if tp.startswith("./usr/share/applications/") and tp.endswith(".desktop"):
                entry = {}
                with open(os.path.join(TARGET, tp)) as f:
                    for line in f:
                        k, _, v = line.strip().partition("=")
                        if _:
                            entry.setdefault(k, v)
                exe = entry.get("Exec", "").split()[0] if entry.get("Exec") else ""
                exe = os.path.basename(exe)
                launcher = {
                    "name": entry.get("Name", pkg),
                    "comment": entry.get("Comment", ""),
                    "exec": "bin/" + exe if exe in commands else exe,
                    "categories": [c for c in entry.get("Categories", "").split(";") if c],
                }
                shutil.rmtree(os.path.join(work, "share", "applications"), ignore_errors=True)
                break
        if launcher is None:
            sys.exit("br2apkg: --launcher, but %s installed no .desktop entry" % pkg)

    deps = []
    for d in a.depends:
        org_name, _, track = d.partition("@")
        org, _, name = org_name.partition("/")
        deps.append((org, name, track or "*"))
        # Fonts come from their own package; fontconfig has to be told.
        fonts_conf = os.path.join(work, "etc", "fonts", "fonts.conf")
        if name == "fonts" and os.path.exists(fonts_conf):
            with open(fonts_conf) as f:
                text = f.read()
            text = text.replace("<dir>%s/share/fonts</dir>" % runtime_prefix,
                                "<dir>/opt/apm/packages/%s/fonts/current/share/fonts</dir>\n\t<dir>%s/share/fonts</dir>" % (org, runtime_prefix), 1)
            with open(fonts_conf, "w") as f:
                f.write(text)

    manifest = [
        "# Generated by br2apkg.py from Buildroot's %s; do not edit." % pkg,
        "manifest_version = 1",
        "",
        "[package]",
        "name         = %s" % toml_str(pkg),
        "organization = %s" % toml_str(a.org),
        "version      = %s" % toml_str(semver),
        "release      = %d" % a.release,
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
    if launcher:
        manifest += ["", "[launcher]",
                     "name       = %s" % toml_str(launcher["name"]),
                     "comment    = %s" % toml_str(launcher["comment"]),
                     "exec       = %s" % toml_str(launcher["exec"]),
                     "categories = [%s]" % ", ".join(toml_str(c) for c in launcher["categories"]),
                     "terminal   = false"]
    if a.global_ and sonames:
        # No ldconfig hook: apm runs "ldconfig <farm>" itself for a global
        # package, and a bare "ldconfig" after it rebuilds the cache from the
        # trusted directories alone -- there is no ld.so.conf on AOS -- and
        # throws the farm out again eleven milliseconds later.
        pass
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
