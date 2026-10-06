# slot.sh -- what aos-install and aos-update share about an installed disk.
#
# An installed disk has five partitions (docs/layout.md): a BIOS boot
# partition, the ESP, two root slots (a = partition 3, b = partition 4)
# that each hold a core -- a squashfs with its dm-verity hash tree, raw --
# and the aos partition (5), the OS a person sees: aos/ (etc and var),
# apm/ (the store), users/ (the homes). A slot is replaced whole by an
# update; the aos partition is never touched by one.
#
# GRUB, grubenv and per slot the kernel, microcode, initramfs and the
# verity parameters (aos/a, aos/b) live on the ESP, so they belong to
# neither slot. grubenv has two variables: slot, the confirmed slot GRUB
# boots by default, and next, a slot to try exactly once.

GRUBENV=/boot/efi/grub/grubenv
ESPAOS=/boot/efi/aos

# The partition device for partition N of a disk: /dev/sda3, /dev/nvme0n1p3.
slot_part() {
	case "$1" in
		*[0-9]) echo "${1}p$2" ;;
		*)      echo "$1$2" ;;
	esac
}

slot_of_partnum() {
	case "$1" in
		3) echo a ;;
		4) echo b ;;
		*) return 1 ;;
	esac
}

slot_partnum() {
	case "$1" in
		a) echo 3 ;;
		b) echo 4 ;;
		*) return 1 ;;
	esac
}

# The block device of the running core, from the kernel command line the
# initramfs read: aos.core=PARTUUID=<uuid>.
slot_root_dev() {
	local pu
	pu=$(sed -n 's/.*aos\.core=PARTUUID=\([^ ]*\).*/\1/p' /proc/cmdline)
	[ -n "$pu" ] || return 1
	readlink -f "/dev/disk/by-partuuid/$pu"
}

# The slot this system booted from: a or b.
slot_current() {
	local dev n
	dev=$(slot_root_dev) || return 1
	n=$(cat "/sys/class/block/$(basename "$dev")/partition")
	slot_of_partnum "$n"
}

slot_other() {
	case "$(slot_current)" in
		a) echo b ;;
		b) echo a ;;
		*) return 1 ;;
	esac
}

# The whole disk the running core is on: /dev/sda, /dev/nvme0n1.
slot_disk() {
	local dev
	dev=$(slot_root_dev) || return 1
	echo "/dev/$(basename "$(readlink -f "/sys/class/block/$(basename "$dev")/..")")"
}

# The partition device of slot a or b on the running disk.
slot_dev() {
	slot_part "$(slot_disk)" "$(slot_partnum "$1")"
}

# The directories a core expects on the aos partition, mounted at $1.
slot_data_dirs() {
	mkdir -p "$1/aos/etc/upper" "$1/aos/etc/work" "$1/aos/var/log/journal" "$1/aos/var/tmp" "$1/apm" "$1/users"
	chmod 1777 "$1/aos/var/tmp"
}

# hash= and offset= of a core.verity file, into VHASH and VOFFSET.
slot_read_verity() {
	VHASH=$(sed -n 's/^hash=//p' "$1")
	VOFFSET=$(sed -n 's/^offset=//p' "$1")
	[ -n "$VHASH" ] && [ -n "$VOFFSET" ]
}

# Writes a core image into a slot's partition and reads it back through
# its verity: a block that does not match its hash is an I/O error, so a
# read of the whole device proves the write.
#   slot_write_core DEV IMAGE VERITYFILE   (IMAGE may be .xz)
slot_write_core() {
	local dev="$1" img="$2" vf="$3"
	slot_read_verity "$vf" || { echo "slot: $vf is not a verity file" >&2; return 1; }
	case "$img" in
		*.xz) xz -dc "$img" | dd of="$dev" bs=4M conv=fsync status=none ;;
		*)    dd if="$img" of="$dev" bs=4M conv=fsync status=none ;;
	esac
	veritysetup open "$dev" aos-check "$dev" "$VHASH" --hash-offset="$VOFFSET" || return 1
	local ok=0
	dd if=/dev/mapper/aos-check of=/dev/null bs=4M status=none || ok=1
	veritysetup close aos-check
	[ "$ok" = 0 ] || { echo "slot: the core on $dev does not read back whole" >&2; return 1; }
}

# Opens a slot's core read-only at a mount point, as the initramfs does.
#   slot_mount_core DEV HASH OFFSET MNT NAME
slot_mount_core() {
	veritysetup open "$1" "$5" "$1" "$2" --hash-offset="$3" || return 1
	mkdir -p "$4"
	mount -t squashfs -o ro "/dev/mapper/$5" "$4" || { veritysetup close "$5"; return 1; }
}

slot_umount_core() {
	umount "$1"
	veritysetup close "$2"
}

# The tree a program sees, assembled over a mounted core whose aos
# partition is mounted at $1/aos: the overlay on /etc, the binds. What
# the initramfs does at boot, for a chroot into an installed system.
slot_mount_tree() {
	local t="$1"
	mount -t overlay overlay -o "lowerdir=$t/etc,upperdir=$t/aos/aos/etc/upper,workdir=$t/aos/aos/etc/work" "$t/etc"
	mount --bind "$t/aos/aos/var" "$t/var"
	mount --bind "$t/aos/apm" "$t/opt/apm"
	mount --bind "$t/aos/users" "$t/home"
}

slot_umount_tree() {
	local t="$1"
	umount "$t/home" "$t/opt/apm" "$t/var" "$t/etc"
}

# The ESP's share of a slot, from its mounted core: kernel, microcode,
# initramfs, os-release, and last the verity parameters, whose presence
# says the slot is complete.
#   slot_stage_esp SLOT COREMNT HASH OFFSET [ESPDIR]
slot_stage_esp() {
	local slot="$1" m="$2" hash="$3" offset="$4" d="${5:-$ESPAOS}/$1"
	rm -rf "$d"
	mkdir -p "$d"
	cp "$m/boot/bzImage" "$d/bzImage"
	cp "$m/boot/microcode.img" "$d/microcode.img"
	cp "$m/boot/initramfs.img" "$d/initramfs.img"
	cp "$m/usr/lib/os-release" "$d/os-release"
	printf 'set verity_hash=%s\nset verity_offset=%s\n' "$hash" "$offset" > "$d/verity.cfg"
	sync
}

# VERSION_ID of the core staged for a slot, by its ESP copy of os-release;
# empty when the slot is not complete.
slot_version() {
	local d="${2:-$ESPAOS}/$1"
	[ -f "$d/verity.cfg" ] && sed -n 's/^VERSION_ID=//p' "$d/os-release"
}

# GRUB's menu for an installed disk, on the ESP, where everything it loads
# is: \$root is the ESP (grub-install pointed the core there). The three
# PARTUUIDs are baked in: they never change for the life of the disk.
#   slot_write_grub_cfg FILE A_UUID B_UUID DATA_UUID
slot_write_grub_cfg() {
	local file="$1" a_uuid="$2" b_uuid="$3" data_uuid="$4"
	cat > "$file" <<GRUBCFG
serial --unit=0 --speed=115200
terminal_input console serial
terminal_output console serial

set default="0"
set timeout="2"

set a_uuid=$a_uuid
set b_uuid=$b_uuid
set data_uuid=$data_uuid

# slot: the confirmed slot. next: a slot to boot exactly once -- cleared
# here, before the kernel runs, so a boot that never reaches the desktop
# goes back to the confirmed slot at the next reset; aos-update --confirm,
# run by a service once the desktop is up, makes it the confirmed slot.
load_env slot next
if [ -z "\$slot" ]; then set slot=a; fi
set boot=\$slot
if [ -n "\$next" ]; then
	set boot=\$next
	set next=
	save_env next
fi
if [ "\$boot" = b ]; then
	set other=a; set cur_uuid=\$b_uuid; set other_uuid=\$a_uuid
else
	set other=b; set cur_uuid=\$a_uuid; set other_uuid=\$b_uuid
fi
# The core's verity root hash and hash offset, written by whatever put
# the core in its slot. A slot without them is not offered.
source /aos/\$boot/verity.cfg
set args="aos.core=PARTUUID=\$cur_uuid aos.hash=\$verity_hash aos.offset=\$verity_offset aos.data=PARTUUID=\$data_uuid rootwait"

# loglevel=4 on the entries that own the screen: kernel messages of warning
# severity and below go to the journal only; errors still reach the screen.
menuentry "AOS" {
	linux /aos/\$boot/bzImage \$args loglevel=4 console=ttyS0,115200 console=tty1
	initrd /aos/\$boot/microcode.img /aos/\$boot/initramfs.img
}

# The other slot: what this machine ran before its last update.
menuentry "AOS (previous version)" {
	if [ -f /aos/\$other/verity.cfg ]; then
		source /aos/\$other/verity.cfg
		linux /aos/\$other/bzImage aos.core=PARTUUID=\$other_uuid aos.hash=\$verity_hash aos.offset=\$verity_offset aos.data=PARTUUID=\$data_uuid rootwait loglevel=4 console=ttyS0,115200 console=tty1
		initrd /aos/\$other/microcode.img /aos/\$other/initramfs.img
	else
		echo "slot \$other holds no system"
		sleep 3
	fi
}

menuentry "AOS (serial console)" {
	linux /aos/\$boot/bzImage \$args console=ttyS0,115200
	initrd /aos/\$boot/microcode.img /aos/\$boot/initramfs.img
}

# nomodeset keeps every DRM driver off the display, so the console stays on
# the firmware framebuffer no matter what the GPU driver does. This is the
# way back in when a graphics driver fails: log in, read journalctl -b -1,
# fix, reboot normally.
menuentry "AOS (safe graphics, no GPU driver)" {
	linux /aos/\$boot/bzImage \$args nomodeset loglevel=4 console=ttyS0,115200 console=tty1
	initrd /aos/\$boot/microcode.img /aos/\$boot/initramfs.img
}
GRUBCFG
}
