#!/bin/sh
#
# Boot AOS in QEMU.
#
#   run-qemu.sh              live ISO, UEFI firmware  (default)
#   run-qemu.sh bios         live ISO, legacy BIOS
#   run-qemu.sh disk [file]  boot an installed disk image (default: output/images/aos-disk.img)
#   run-qemu.sh install      live ISO plus a fresh blank 8G disk, for aos-install
#
# Add "serial" as a second word to run headless on the terminal instead of
# opening a window, e.g.  run-qemu.sh bios serial
#
# The -cpu choice is not cosmetic. AOS is built to an x86-64-v2 baseline, and
# QEMU's default "qemu64" model predates SSE4.2, so the image panics inside
# ld-linux with an invalid opcode before it reaches userspace.

set -e

# Never run this under sudo. QEMU with KVM needs no root (the invoking user
# just needs access to /dev/kvm), and running as root creates the install
# disk image and firmware files owned by root -- after which a normal,
# correct run can no longer open them.
if [ "$(id -u)" = 0 ]; then
	echo "Do not run this with sudo/root -- QEMU with KVM does not need it."
	echo "If a previous sudo run left root-owned files, clean them up with:"
	echo "    sudo rm -f output/images/aos-disk.img output/images/OVMF_VARS.*.fd"
	echo "then run again as your normal user."
	exit 1
fi

HERE=$(cd "$(dirname "$0")" && pwd)
BASE=$(cd "$HERE/../../.." && pwd)
IMAGES="$BASE/output/images"
ISO="$IMAGES/rootfs.iso9660"

# Arguments in any order: a mode word, an optional image path (disk mode),
# and "serial". So "disk serial", "disk foo.img serial" and "serial disk"
# all mean the same thing.
MODE=uefi
IMG_ARG=""
SERIAL=no
for a in "$@"; do
	case "$a" in
		serial)                 SERIAL=yes ;;
		bios|uefi|disk|install) MODE="$a" ;;
		*)                      IMG_ARG="$a" ;;
	esac
done

# KVM plus the host CPU model is both fastest and safely above the v2 baseline.
# Without KVM, Nehalem is the oldest model that still satisfies x86-64-v2.
if [ -w /dev/kvm ]; then
	ACCEL="-enable-kvm -cpu host"
else
	ACCEL="-cpu Nehalem"
	echo "note: /dev/kvm not writable, running without KVM (slower)"
fi

DISPLAY_OPTS=""
[ "$SERIAL" = yes ] && DISPLAY_OPTS="-nographic"

# Networking: keep a NIC so networkd inside AOS gets an address, but strip its
# PXE option ROM (romfile=) so the firmware is never offered network boot.
# OVMF's PXE on QEMU's user network gets a DHCP lease and then waits a very
# long time, which looks exactly like "nothing to boot".
NET="-netdev user,id=n0 -device virtio-net-pci,netdev=n0,romfile="

OVMF_CODE=/usr/share/edk2/ovmf/OVMF_CODE.fd
OVMF_VARS_SRC=/usr/share/edk2/ovmf/OVMF_VARS.fd

# A fresh copy of the OVMF variable store on EVERY run. OVMF persists its
# BootOrder in that file; reusing one across runs let a stale order put PXE
# ahead of the ISO and the disk, so every mode dropped into the firmware.
# Nothing in AOS needs firmware variables to survive between runs.
uefi_flags() {
	vars="$IMAGES/OVMF_VARS.run.fd"
	cp -f "$OVMF_VARS_SRC" "$vars"
	rm -f "$IMAGES/OVMF_VARS.local.fd"   # the old, persisted one
	printf -- "-drive if=pflash,format=raw,readonly=on,file=%s -drive if=pflash,format=raw,file=%s" \
		"$OVMF_CODE" "$vars"
}

# Explicit devices with bootindex, instead of -cdrom/-drive shorthands, so
# both OVMF and SeaBIOS boot what we say first regardless of any saved order.
#   $1: bootindex
cdrom_dev() {
	printf -- "-drive if=none,id=cd0,media=cdrom,format=raw,file=%s -device ide-cd,drive=cd0,bootindex=%s" \
		"$ISO" "$1"
}
#   $1: image file   $2: bootindex
disk_dev() {
	printf -- "-drive if=none,id=hd0,format=raw,file=%s -device virtio-blk-pci,drive=hd0,bootindex=%s" \
		"$1" "$2"
}

need_iso() { [ -f "$ISO" ] || { echo "no $ISO -- run make first"; exit 1; }; }

case "$MODE" in
	bios)
		need_iso
		# shellcheck disable=SC2086
		exec qemu-system-x86_64 $ACCEL -m 4G -smp 4 \
			$(cdrom_dev 0) $NET $DISPLAY_OPTS
		;;
	uefi)
		need_iso
		# shellcheck disable=SC2086
		exec qemu-system-x86_64 $ACCEL -m 4G -smp 4 \
			$(uefi_flags) $(cdrom_dev 0) $NET $DISPLAY_OPTS
		;;
	disk)
		IMG="${IMG_ARG:-$IMAGES/aos-disk.img}"
		[ -f "$IMG" ] || { echo "no disk image at $IMG -- run 'install' first"; exit 1; }
		# A disk that was created by 'install' but never actually installed
		# to is 8G of zeros. Booting it just lands in the firmware with no
		# explanation, so check for a GPT header before launching.
		if ! dd if="$IMG" bs=512 skip=1 count=1 2>/dev/null | grep -q "EFI PART"; then
			echo "$IMG has no partition table -- nothing was installed on it."
			echo "Run '$0 install', log in as root, run 'aos-install /dev/vda', then try again."
			exit 1
		fi
		echo "Booting installed disk $IMG"
		# shellcheck disable=SC2086
		exec qemu-system-x86_64 $ACCEL -m 4G -smp 4 \
			$(uefi_flags) $(disk_dev "$IMG" 0) $NET $DISPLAY_OPTS
		;;
	install)
		need_iso
		IMG="$IMAGES/aos-disk.img"
		# Always start from a blank disk. If a previous install is left on
		# it, the firmware would boot that in preference to the ISO.
		if [ -f "$IMG" ]; then
			echo "Discarding previous install at $IMG"
			rm -f "$IMG"
		fi
		truncate -s 8G "$IMG"
		echo "Blank disk at $IMG -- log in as root and run: aos-install /dev/vda"
		# shellcheck disable=SC2086
		exec qemu-system-x86_64 $ACCEL -m 4G -smp 4 \
			$(uefi_flags) $(cdrom_dev 0) $(disk_dev "$IMG" 1) $NET $DISPLAY_OPTS
		;;
	*)
		echo "usage: $0 [uefi|bios|disk [image]|install] [serial]"
		exit 1
		;;
esac
