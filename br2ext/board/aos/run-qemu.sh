#!/bin/sh
#
# Boot AOS in QEMU.
#
#   run-qemu.sh              live ISO, UEFI firmware  (default)
#   run-qemu.sh bios         live ISO, legacy BIOS
#   run-qemu.sh disk [file]  boot an installed disk image instead of the ISO
#   run-qemu.sh install      live ISO plus a blank 8G disk, for aos-install
#
# Add "serial" as a second word to run headless on the terminal instead of
# opening a window, e.g.  run-qemu.sh bios serial
#
# The -cpu choice is not cosmetic. AOS is built to an x86-64-v2 baseline, and
# QEMU's default "qemu64" model predates SSE4.2, so the image panics inside
# ld-linux with an invalid opcode before it reaches userspace.

set -e

HERE=$(cd "$(dirname "$0")" && pwd)
BASE=$(cd "$HERE/../../.." && pwd)
IMAGES="$BASE/output/images"
ISO="$IMAGES/rootfs.iso9660"

MODE="${1:-uefi}"
ARG2="${2:-}"

# KVM plus the host CPU model is both fastest and safely above the v2 baseline.
# Without KVM, Nehalem is the oldest model that still satisfies x86-64-v2.
if [ -w /dev/kvm ]; then
	ACCEL="-enable-kvm -cpu host"
else
	ACCEL="-cpu Nehalem"
	echo "note: /dev/kvm not writable, running without KVM (slower)"
fi

OVMF_CODE=/usr/share/edk2/ovmf/OVMF_CODE.fd
OVMF_VARS_SRC=/usr/share/edk2/ovmf/OVMF_VARS.fd
OVMF_VARS="$BASE/output/images/OVMF_VARS.local.fd"

DISPLAY_OPTS=""
[ "$ARG2" = "serial" ] || [ "$MODE" = "serial" ] && DISPLAY_OPTS="-nographic"

uefi_flags() {
	[ -f "$OVMF_VARS" ] || cp "$OVMF_VARS_SRC" "$OVMF_VARS"
	printf -- "-drive if=pflash,format=raw,readonly=on,file=%s -drive if=pflash,format=raw,file=%s" \
		"$OVMF_CODE" "$OVMF_VARS"
}

case "$MODE" in
	bios)
		[ -f "$ISO" ] || { echo "no $ISO -- run make first"; exit 1; }
		# shellcheck disable=SC2086
		exec qemu-system-x86_64 $ACCEL -m 4G -smp 4 \
			-cdrom "$ISO" -boot d $DISPLAY_OPTS
		;;
	uefi|serial)
		[ -f "$ISO" ] || { echo "no $ISO -- run make first"; exit 1; }
		# shellcheck disable=SC2086
		exec qemu-system-x86_64 $ACCEL -m 4G -smp 4 \
			$(uefi_flags) -cdrom "$ISO" $DISPLAY_OPTS
		;;
	disk)
		IMG="${2:-$IMAGES/aos-disk.img}"
		[ -f "$IMG" ] || { echo "no disk image at $IMG"; exit 1; }
		# shellcheck disable=SC2086
		exec qemu-system-x86_64 $ACCEL -m 4G -smp 4 \
			$(uefi_flags) -drive file="$IMG",if=virtio,format=raw $DISPLAY_OPTS
		;;
	install)
		IMG="$IMAGES/aos-disk.img"
		[ -f "$IMG" ] || truncate -s 8G "$IMG"
		echo "Blank disk at $IMG -- log in as root and run: aos-install /dev/vda"
		# shellcheck disable=SC2086
		exec qemu-system-x86_64 $ACCEL -m 4G -smp 4 \
			$(uefi_flags) -cdrom "$ISO" \
			-drive file="$IMG",if=virtio,format=raw $DISPLAY_OPTS
		;;
	*)
		echo "usage: $0 [uefi|bios|disk [image]|install] [serial]"
		exit 1
		;;
esac
