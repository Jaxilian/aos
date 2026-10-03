#!/bin/sh
#
# kernel-apkg.sh -- the kernel Buildroot just built, as an apm package, so
# a kernel update is `apm upgrade kernel` and a reboot rather than an ISO.
#
#   ./br2ext/board/aos/kernel-apkg.sh [--release N] [--out DIR]
#
# The payload is boot/bzImage and the whole lib/modules/<ver> of the target
# tree: depmod's files and the NVIDIA modules in updates/ come along, so the
# package must be made from the same tree as the image whose NVIDIA
# userspace it will run under. Not through br2apkg.py, which has no rule
# for ./boot and would leave depmod's output behind.
#
# The hooks copy both into the root slot: /usr/lib/modules/<ver> for the
# module loader (marked with a .apm file) and /boot/bzImage.apm for GRUB,
# with the kernel that was there before moved to /boot/bzImage.prev.
# Copies, not links into the store: the store is on the data partition,
# which GRUB cannot read and which is not mounted yet when the firewall,
# zram and udev's coldplug load their modules (release 2 linked the
# modules, and a kernel newer than the image booted with no firewall).
# The grub.cfg aos-install writes boots .apm when it exists and
# offers .prev as "previous kernel"; the image's own /boot/bzImage is never
# touched and is the last fallback. A new kernel takes effect at the next
# reboot. Removing the package drops what points into it.
#
# ponytail: no `apm gc` yet, so every kernel keeps ~170M in the store until
# `apm remove kernel`, which drops all versions at once; the slot holds a
# second ~160M copy of the modules while the package is installed.
#
# Needs: a built output tree (BR2_OUTPUT to name another than output/),
# apm on the host (APM=/path/to/apm) and its signing key.

set -e

BASE=$(cd "$(dirname "$0")/../../.." && pwd)
OUTPUT=${BR2_OUTPUT:-$BASE/output}
TARGET=$OUTPUT/target
APM=${APM:-$BASE/../apm/target/release/apm}
RELEASE=1
OUT=$BASE/../apm-recipes/index

while [ $# -gt 0 ]; do
	case $1 in
		--release) RELEASE=$2; shift 2 ;;
		--out) OUT=$2; shift 2 ;;
		*) echo "usage: kernel-apkg.sh [--release N] [--out DIR]" >&2; exit 2 ;;
	esac
done

[ -x "$APM" ] || { echo "kernel-apkg.sh: no apm at $APM" >&2; exit 1; }
[ -f "$TARGET/boot/bzImage" ] || { echo "kernel-apkg.sh: no $TARGET/boot/bzImage; build first" >&2; exit 1; }
set -- "$TARGET"/usr/lib/modules/*
[ $# -eq 1 ] && [ -d "$1" ] || { echo "kernel-apkg.sh: expected exactly one $TARGET/usr/lib/modules/<ver>, found: $*" >&2; exit 1; }
MODULES=$1
VER=$(basename "$MODULES")
# The package version is semver; a kernel without a patch level ("7.2") gets one.
case $VER in
	*.*.*) PKGVER=$VER ;;
	*) PKGVER=$VER.0 ;;
esac

WORK=$(mktemp -d "$OUTPUT/kernel-apkg.XXXXXX")
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/boot" "$WORK/lib/modules"
cp "$TARGET/boot/bzImage" "$WORK/boot/bzImage"
cp -a "$MODULES" "$WORK/lib/modules/"

cat > "$WORK/manifest.toml" <<EOF
# The AOS kernel $VER and its modules, lifted from the Buildroot target
# tree by br2ext/board/aos/kernel-apkg.sh. Takes effect at the next reboot.

manifest_version = 1

[package]
name         = "kernel"
organization = "aos"
version      = "$PKGVER"
release      = $RELEASE
kind         = "bin"
summary      = "the Linux kernel $VER and its modules; boots after a reboot"
license      = "GPL-2.0-only"
homepage     = "https://www.kernel.org/"
requires_scope = "system"

[requires]
run = []

[hooks]
# Copies into the root slot, not links into the store: the store is on the
# data partition, which GRUB cannot read and which is not mounted when the
# firewall, zram and udev load their modules at boot. A real
# /usr/lib/modules/<ver> without our .apm mark is the image's own copy of
# this same version and is left alone. The copies stay with the slot -- an
# OS update boots the release's kernel until the package is installed again.
post_install = '''
for m in "\$APM_PREFIX"/lib/modules/*; do
	dir=/usr/lib/modules/\$(basename "\$m")
	if [ -d "\$dir" ] && [ ! -L "\$dir" ] && [ ! -f "\$dir/.apm" ]; then
		echo "kernel: \$dir is the image's own; not replaced"
	else
		rm -rf "\$dir"
		cp -a "\$m" "\$dir"
		: > "\$dir/.apm"
	fi
done
if [ -f /boot/bzImage.apm ] && ! cmp -s /boot/bzImage.apm "\$APM_PREFIX/boot/bzImage"; then
	mv -f /boot/bzImage.apm /boot/bzImage.prev
fi
cp -f "\$APM_PREFIX/boot/bzImage" /boot/bzImage.apm
echo "kernel $VER boots at the next reboot; the previous kernel stays in the GRUB menu"
'''
pre_remove = '''
for m in "\$APM_PREFIX"/lib/modules/*; do
	dir=/usr/lib/modules/\$(basename "\$m")
	if [ -L "\$dir" ]; then
		rm -f "\$dir"
	elif [ -f "\$dir/.apm" ]; then
		rm -rf "\$dir"
	fi
done
for b in /boot/bzImage.apm /boot/bzImage.prev; do
	if cmp -s "\$b" "\$APM_PREFIX/boot/bzImage"; then
		rm -f "\$b"
	fi
done
'''
EOF

mkdir -p "$OUT"
cd "$OUT"
"$APM" ship "$WORK" --sign
