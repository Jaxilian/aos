#!/bin/sh
#
# Write the AOS live ISO to a USB stick, verify it landed, and optionally
# boot the physical stick in QEMU to prove it is bootable before carrying it
# to another machine.
#
#   sudo ./br2ext/board/aos/write-usb.sh /dev/sdX            live ISO: write + verify
#   sudo ./br2ext/board/aos/write-usb.sh /dev/sdX --test     ... and boot it in QEMU
#   sudo ./br2ext/board/aos/write-usb.sh /dev/sdX --verify-only
#   sudo ./br2ext/board/aos/write-usb.sh /dev/sdX --install  INSTALL AOS onto the stick
#
# --install is the one to use for a machine to work on. It boots the live ISO
# in QEMU with the physical stick attached as a disk, and you run
# aos-install on it there, so the stick ends up a complete AOS system: GPT,
# a FAT32 EFI system partition at the front, an ext4 root, GRUB for UEFI and
# BIOS -- the same shape as any installed OS, and the layout every firmware
# knows how to boot. It is persistent and writable, which the live ISO is
# not, and it is what SSH-ing in to build on real hardware wants.
#
# The plain write is the hybrid live ISO. It boots from a stick under UEFI
# in QEMU, and at least one real laptop refuses to list it while happily
# listing a Fedora stick (see PLATFORM.md, "USB booting"); if the target
# machine will not show it, use --install rather than fighting the firmware.
#
# The QEMU step is the one that settles arguments. It attaches the real stick
# as a USB mass-storage device behind the same UEFI firmware a PC uses, so if
# the stick boots there and not on the target machine, the image is fine and
# the difference is the target's firmware -- not something to keep rebuilding
# the ISO over.
#
# Refuses anything that is not a removable USB disk, because the cost of a
# typo here is the host's own filesystem.

set -e

DEV="$1"
MODE="$2"

usage() {
	echo "usage: $0 /dev/sdX [--test|--verify-only|--install]" >&2
	echo >&2
	echo "Removable USB disks currently attached:" >&2
	found=no
	for d in /sys/block/sd*; do
		[ -e "$d" ] || continue
		n=$(basename "$d")
		[ "$(cat "$d/removable" 2>/dev/null)" = "1" ] || continue
		sz=$(( $(cat "$d/size") / 2 / 1024 ))
		echo "  /dev/$n  ${sz} MiB  $(cat "$d/device/model" 2>/dev/null)" >&2
		found=yes
	done
	[ "$found" = yes ] || echo "  (none -- is the stick plugged in?)" >&2
	exit 1
}

[ -n "$DEV" ] || usage
[ -b "$DEV" ] || { echo "$0: $DEV is not a block device" >&2; usage; }

HERE=$(cd "$(dirname "$0")" && pwd)
BASE=$(cd "$HERE/../../.." && pwd)
ISO="$BASE/output/images/rootfs.iso9660"
[ -f "$ISO" ] || { echo "$0: no $ISO -- run make first" >&2; exit 1; }

NAME=$(basename "$DEV")

# Safety. Only a whole disk, only removable, only USB. A partition would
# also be wrong: the image carries its own partition table.
#
# Whole disks appear directly under /sys/block; partitions do not (sda1
# lives at /sys/block/sda/sda1). That distinguishes them correctly for both
# sd* and nvme* names, where a trailing digit would not -- nvme0n1 is a
# whole disk.
[ -e "/sys/block/$NAME" ] || {
	echo "$0: $DEV is not a whole disk -- give the disk, not a partition" >&2
	exit 1
}
[ "$(cat "/sys/block/$NAME/removable")" = "1" ] || {
	echo "$0: $DEV is not removable -- refusing" >&2; exit 1; }
readlink -f "/sys/block/$NAME" | grep -q usb || {
	echo "$0: $DEV is not on the USB bus -- refusing" >&2; exit 1; }

ISO_BYTES=$(stat -c %s "$ISO")
DEV_BYTES=$(( $(cat "/sys/block/$NAME/size") * 512 ))
[ "$DEV_BYTES" -ge "$ISO_BYTES" ] || {
	echo "$0: $DEV holds ${DEV_BYTES} bytes, the image needs ${ISO_BYTES}" >&2; exit 1; }

verify() {
	echo ">>> Verifying the first ${ISO_BYTES} bytes of $DEV"
	want=$(sha256sum "$ISO" | cut -d' ' -f1)
	got=$(head -c "$ISO_BYTES" "$DEV" | sha256sum | cut -d' ' -f1)
	if [ "$want" = "$got" ]; then
		echo "    match: $got"
	else
		echo "    MISMATCH" >&2
		echo "    image:  $want" >&2
		echo "    device: $got" >&2
		exit 1
	fi

	# What the firmware has to recognise: a GPT, and an EFI system
	# partition holding a FAT it will actually read. FAT12 here is what
	# makes a stick invisible in the boot menu on a lot of machines.
	echo ">>> Partition table as firmware sees it"
	partx -u "$DEV" 2>/dev/null || true
	lsblk -o NAME,SIZE,PARTLABEL,PARTTYPENAME,FSTYPE "$DEV" 2>/dev/null || \
		lsblk -o NAME,SIZE,PARTLABEL,FSTYPE "$DEV"
	# Match the EFI System type GUID, not the human name: lsblk -r escapes
	# the space in "EFI System" as \x20, so matching the name never fires.
	esp=$(lsblk -rno NAME,PARTTYPE "$DEV" 2>/dev/null | \
		awk 'tolower($2) == "c12a7328-f81f-11d2-ba4b-00a0c93ec93b" { print "/dev/"$1; exit }')
	if [ -n "$esp" ]; then
		fat=$(dd if="$esp" bs=1 skip=54 count=8 2>/dev/null)
		echo ">>> EFI system partition $esp is $fat"
		case "$fat" in
			FAT16*|FAT32*) echo "    good: firmware should read this" ;;
			FAT12*) echo "    WARNING: FAT12 -- many firmwares ignore it" >&2 ;;
			*)      echo "    WARNING: unrecognised: '$fat'" >&2 ;;
		esac
	else
		echo ">>> WARNING: no EFI System partition found on $DEV" >&2
	fi
}

boot_test() {
	echo ">>> Booting the physical stick in QEMU under UEFI."
	echo "    A login prompt means the stick is bootable and any failure on"
	echo "    the target machine is that machine's firmware, not this image."
	echo "    Ctrl-A X to quit."
	# shellcheck disable=SC2046
	qemu-system-x86_64 -enable-kvm -cpu host -m 2G -smp 2 \
		$(ovmf_args) \
		-drive if=none,id=usb0,format=raw,file="$DEV" \
		-device qemu-xhci,id=xhci \
		-device usb-storage,bus=xhci.0,drive=usb0,bootindex=0 \
		-nographic -no-reboot || true
	rm -f /tmp/aos-ovmf-vars.*.fd
}

ovmf_args() {
	code=/usr/share/edk2/ovmf/OVMF_CODE.fd
	vars_src=/usr/share/edk2/ovmf/OVMF_VARS.fd
	[ -f "$code" ] || { echo "$0: no OVMF at $code" >&2; exit 1; }
	vars=$(mktemp /tmp/aos-ovmf-vars.XXXXXX.fd)
	cp "$vars_src" "$vars"
	printf -- "-drive if=pflash,format=raw,readonly=on,file=%s -drive if=pflash,format=raw,file=%s" \
		"$code" "$vars"
}

install_mode() {
	echo "About to ERASE $DEV and install a full AOS system onto it:"
	lsblk -o NAME,SIZE,TYPE,TRAN,MODEL,LABEL "$DEV"
	echo
	printf "Type YES to continue: "
	read -r confirm
	[ "$confirm" = "YES" ] || { echo "Aborted."; exit 1; }

	echo ">>> Unmounting anything mounted from $DEV"
	for part in $(lsblk -rno NAME "$DEV" | tail -n +2); do
		umount "/dev/$part" 2>/dev/null || true
	done

	# The stick goes in as a virtio disk, so inside the VM it is /dev/vda:
	# a plain disk name that aos-install partitions as vda1, vda2, vda3.
	# cache=none: every write goes straight to the medium, so nothing is
	# left in host page cache if QEMU is killed.
	#
	# 4G of RAM sizes the swap file aos-install creates (it uses the
	# machine's RAM, up to 8G); on a stick, smaller is kinder.
	cat <<EOF
>>> Booting the live ISO in QEMU with $DEV attached as /dev/vda.

    At the "aos login:" prompt, log in as root (no password) and run:

        aos-install /dev/vda
        poweroff

    aos-install asks you to type YES. Expect a few minutes: it copies
    ~2.8 GB and writes a swap file. QEMU exits when the VM powers off.
    Ctrl-A X aborts.

EOF
	# shellcheck disable=SC2046
	qemu-system-x86_64 -enable-kvm -cpu host -m 4G -smp 4 \
		$(ovmf_args) \
		-drive if=none,id=cd0,media=cdrom,format=raw,file="$ISO" \
		-device ide-cd,drive=cd0,bootindex=0 \
		-drive if=none,id=hd0,format=raw,cache=none,file="$DEV" \
		-device virtio-blk-pci,drive=hd0 \
		-nographic -no-reboot || true
	rm -f /tmp/aos-ovmf-vars.*.fd

	echo ">>> Re-reading the partition table"
	sync
	blockdev --rereadpt "$DEV" 2>/dev/null || partx -u "$DEV" 2>/dev/null || true
	sleep 1
	lsblk -o NAME,SIZE,PARTLABEL,PARTTYPENAME,FSTYPE,LABEL "$DEV"
	esp=$(lsblk -rno NAME,PARTTYPE "$DEV" 2>/dev/null | \
		awk 'tolower($2) == "c12a7328-f81f-11d2-ba4b-00a0c93ec93b" { print "/dev/"$1; exit }')
	if [ -n "$esp" ]; then
		fat=$(dd if="$esp" bs=1 skip=82 count=8 2>/dev/null)
		echo ">>> EFI system partition $esp is $fat with:"
		mdir -i "$esp" ::/EFI/BOOT 2>/dev/null | grep -i -E 'efi|cfg' || \
			echo "    (could not list it; is mtools installed?)"
		echo
		echo "Done. Boot the machine from $DEV; it is a complete AOS install."
	else
		echo ">>> No EFI system partition on $DEV -- did aos-install run?" >&2
		exit 1
	fi
}

if [ "$MODE" = "--install" ]; then
	install_mode
	exit 0
fi

if [ "$MODE" = "--verify-only" ]; then
	verify
	exit 0
fi

echo "About to ERASE $DEV:"
lsblk -o NAME,SIZE,TYPE,TRAN,MODEL,LABEL "$DEV"
echo
echo "and write $(basename "$ISO") (${ISO_BYTES} bytes)."
printf "Type YES to continue: "
read -r confirm
[ "$confirm" = "YES" ] || { echo "Aborted."; exit 1; }

echo ">>> Unmounting anything mounted from $DEV"
for part in $(lsblk -rno NAME "$DEV" | tail -n +2); do
	umount "/dev/$part" 2>/dev/null || true
done

echo ">>> Writing"
dd if="$ISO" of="$DEV" bs=4M oflag=direct conv=fsync status=progress
sync
# Drop the page cache so the verify below reads the medium, not memory.
blockdev --flushbufs "$DEV" 2>/dev/null || true
echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true

verify

# Move the backup GPT header to the end of the stick.
#
# The image describes a ~1 GiB disk, so after dd the backup header sits
# where the image ends rather than at the end of the medium. The kernel says
# so out loud -- "Primary header thinks Alt. header is not at the end of the
# disk" -- and shrugs. Some UEFI firmware does not: it treats the GPT as
# invalid, finds no EFI system partition, and never offers the stick as a
# boot device.
#
# Done after the checksum above, because it rewrites the primary header too.
if command -v sgdisk >/dev/null 2>&1; then
	echo ">>> Moving the backup GPT to the end of $DEV"
	sgdisk -e "$DEV" >/dev/null && echo "    done"
	partx -u "$DEV" 2>/dev/null || true
else
	echo ">>> sgdisk not installed; leaving the backup GPT where dd put it." >&2
	echo "    Some firmware rejects that. Install gdisk and re-run with" >&2
	echo "    --verify-only, or run: sgdisk -e $DEV" >&2
fi

[ "$MODE" = "--test" ] && boot_test

echo
echo "Done. $DEV is ready."
