# slot.sh -- what aos-install and aos-update share about an installed disk.
#
# An installed disk has five partitions: a BIOS boot partition, the ESP,
# two root slots (a = partition 3, b = partition 4) and the data partition
# (5), which holds everything that must outlive a slot: /var, and through
# it /home (var/home), the apm store (var/apm), the upper half of the /etc
# overlay (var/etc) and the swap file. A slot is replaced whole by an
# update; the data partition is never touched by one.
#
# GRUB and its grubenv live on the ESP (/boot/efi/grub), so they belong to
# neither slot. grubenv has two variables: slot, the confirmed slot GRUB
# boots by default, and next, a slot to try exactly once.

GRUBENV=/boot/efi/grub/grubenv

# The partition device for partition N of a disk: /dev/sda3, /dev/nvme0n1p3.
slot_part() {
	case "$1" in
		*[0-9]) echo "${1}p$2" ;;
		*)      echo "$1$2" ;;
	esac
}

# Partition number -> slot letter, and back.
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

# The block device the running root was mounted from, via the kernel
# command line: there is no initramfs, so root= is always PARTUUID=.
slot_root_dev() {
	local pu
	pu=$(sed -n 's/.*root=PARTUUID=\([^ ]*\).*/\1/p' /proc/cmdline)
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

# The whole disk the running root is on: /dev/sda, /dev/nvme0n1.
slot_disk() {
	local dev
	dev=$(slot_root_dev) || return 1
	echo "/dev/$(basename "$(readlink -f "/sys/class/block/$(basename "$dev")/..")")"
}

# The partition device of slot a or b on the running disk.
slot_dev() {
	slot_part "$(slot_disk)" "$(slot_partnum "$1")"
}

# The fstab of a slot, into its lower /etc. The three devices are written
# as UUID= specs by the caller. Why it looks the way it does:
#
#  - "/" is listed, with fsck pass 1. The kernel mounts the root read-only
#    from root=PARTUUID= (it cannot resolve UUID= without an initramfs);
#    systemd-fsck-root then checks it -- which is only possible while it is
#    still read-only -- and systemd-remount-fs makes it writable using this
#    line. Without the line the root would never be checked.
#  - /var and the /etc overlay are mounted by /usr/lib/aos/init before
#    systemd starts, because PID 1 reads /etc (machine-id, hostname, unit
#    drop-ins) before it mounts anything from fstab. The lines are here so
#    systemd knows them as units; it adopts the existing mounts. The
#    wrapper runs fsck on the data partition itself, hence pass 0.
#  - /boot/efi is by UUID. systemd waits for udev to create the by-uuid
#    link before mounting; nofail makes a missing or damaged ESP degrade
#    the boot rather than stop it.
#  - /home and /opt/apm are bind mounts out of /var; systemd orders them
#    after /var by itself. The swap file is pri=10, behind zram at pri=100.
#  - /proc, /sys, /dev and /run are mounted by systemd itself.
slot_write_fstab() {
	local etc="$1" root="$2" data="$3" esp="$4" swap="$5"
	cat > "$etc/fstab" <<FSTAB
# <device>			<mount>		<type>		<options>			<dump>	<pass>
# Written by AOS for this root slot; /usr/lib/aos/slot.sh says why each line
# is here. User changes to this file do not survive an update.
$root		/		ext4		defaults			0	1
$data		/var		ext4		defaults			0	0
$esp		/boot/efi	vfat		defaults,noatime,nofail		0	2
overlay				/etc		overlay		lowerdir=/etc,upperdir=/var/etc/upper,workdir=/var/etc/work	0	0
/var/home			/home		none		bind				0	0
/var/apm			/opt/apm	none		bind				0	0
tmpfs				/tmp		tmpfs		defaults			0	0
$swap
FSTAB
}

# The directories on the data partition a slot expects.
slot_data_dirs() {
	mkdir -p "$1/home" "$1/apm" "$1/etc/upper" "$1/etc/work" "$1/log/journal"
}

# Mount the overlay and the binds over a slot whose /var is already the
# data partition, so that a chroot into it sees the system as it will run.
slot_mount_tree() {
	local t="$1"
	mount -t overlay overlay -o "lowerdir=$t/etc,upperdir=$t/var/etc/upper,workdir=$t/var/etc/work" "$t/etc"
	mount --bind "$t/var/home" "$t/home"
	mount --bind "$t/var/apm" "$t/opt/apm"
}

slot_umount_tree() {
	local t="$1"
	umount "$t/opt/apm" "$t/home" "$t/etc"
}

# GRUB's menu for an installed disk, on the ESP. The slots are partitions
# 3 and 4 of the disk the ESP is on, found from \$root (which grub-install
# pointed at the ESP) rather than by label, so a second AOS disk plugged
# in -- a stick installed with make-usb.sh -- is never mistaken for this
# one. The PARTUUIDs are baked in: they never change for the life of the
# disk.
slot_write_grub_cfg() {
	local file="$1" a_uuid="$2" b_uuid="$3"
	cat > "$file" <<GRUBCFG
serial --unit=0 --speed=115200
terminal_input console serial
terminal_output console serial

set default="0"
set timeout="5"

set a_uuid=$a_uuid
set b_uuid=$b_uuid

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
regexp --set=1:disk '^(hd[0-9]+),' "\$root"
if [ "\$boot" = b ]; then
	set cur=4; set other=3; set cur_uuid=\$b_uuid; set other_uuid=\$a_uuid
else
	set cur=3; set other=4; set cur_uuid=\$a_uuid; set other_uuid=\$b_uuid
fi

# Each entry sets \$root to the slot it boots so the kernel and modules come
# from that slot, then prefers the kernel apm installed into it, when there
# is one: the aos/kernel package copies /boot/bzImage.apm next to the
# image's /boot/bzImage and keeps the kernel before it as bzImage.prev.
#
# "ro": the root is checked by systemd-fsck-root before systemd-remount-fs
# makes it writable from /etc/fstab. init=: mounts /var and the /etc
# overlay before systemd. The initrd is CPU microcode only. rootwait: a
# USB stick enumerates long after the kernel first looks for the root.
#
# loglevel=4 on the entries that own the screen: kernel messages of warning
# severity and below go to the journal only; errors still reach the screen.
# The serial entry keeps the default 7 -- serial is the channel you watch a
# boot on.
menuentry "AOS" {
	set root=\$disk,gpt\$cur
	set kernel=/boot/bzImage
	if [ -f /boot/bzImage.apm ]; then set kernel=/boot/bzImage.apm; fi
	linux \$kernel root=PARTUUID=\$cur_uuid init=/usr/lib/aos/init ro rootwait loglevel=4 console=ttyS0,115200 console=tty1
	initrd /boot/microcode.img
}

# The other slot: what this machine ran before its last update.
menuentry "AOS (previous version)" {
	set root=\$disk,gpt\$other
	set kernel=/boot/bzImage
	if [ -f /boot/bzImage.apm ]; then set kernel=/boot/bzImage.apm; fi
	linux \$kernel root=PARTUUID=\$other_uuid init=/usr/lib/aos/init ro rootwait loglevel=4 console=ttyS0,115200 console=tty1
	initrd /boot/microcode.img
}

menuentry "AOS (previous kernel)" {
	set root=\$disk,gpt\$cur
	set kernel=/boot/bzImage
	if [ -f /boot/bzImage.prev ]; then set kernel=/boot/bzImage.prev; fi
	linux \$kernel root=PARTUUID=\$cur_uuid init=/usr/lib/aos/init ro rootwait loglevel=4 console=ttyS0,115200 console=tty1
	initrd /boot/microcode.img
}

menuentry "AOS (serial console)" {
	set root=\$disk,gpt\$cur
	set kernel=/boot/bzImage
	if [ -f /boot/bzImage.apm ]; then set kernel=/boot/bzImage.apm; fi
	linux \$kernel root=PARTUUID=\$cur_uuid init=/usr/lib/aos/init ro rootwait console=ttyS0,115200
	initrd /boot/microcode.img
}

# nomodeset keeps every DRM driver off the display, so the console stays on
# the firmware framebuffer no matter what the GPU driver does. This is the
# way back in when a graphics driver fails: log in, read journalctl -b -1,
# fix, reboot normally.
menuentry "AOS (safe graphics, no GPU driver)" {
	set root=\$disk,gpt\$cur
	set kernel=/boot/bzImage
	if [ -f /boot/bzImage.apm ]; then set kernel=/boot/bzImage.apm; fi
	linux \$kernel root=PARTUUID=\$cur_uuid init=/usr/lib/aos/init ro rootwait nomodeset loglevel=4 console=ttyS0,115200 console=tty1
	initrd /boot/microcode.img
}

# The kernel the slot was installed with, whatever apm has done since.
menuentry "AOS (image kernel)" {
	set root=\$disk,gpt\$cur
	linux /boot/bzImage root=PARTUUID=\$cur_uuid init=/usr/lib/aos/init ro rootwait loglevel=4 console=ttyS0,115200 console=tty1
	initrd /boot/microcode.img
}
GRUBCFG
}
