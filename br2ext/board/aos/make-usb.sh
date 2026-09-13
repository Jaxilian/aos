#!/bin/sh
#
# make-usb.sh -- build AOS and install it onto a USB stick, as one command.
#
#   ./usb.sh                  build, pick the stick, install it, verify it
#   ./usb.sh /dev/sdX         the same, onto that stick
#   ./usb.sh --no-build       skip make; install the image already built
#   ./usb.sh --test           afterwards boot the stick in QEMU to prove it
#
# Options combine: "./usb.sh /dev/sda --no-build --test".
#
# Run it as yourself, not under sudo. The build must not run as root, and
# the one step that needs root -- opening the block device -- asks for your
# password once, first thing, and keeps that authorisation alive through the
# build so it does not stop halfway to ask again.
#
# The order is deliberate: the stick is chosen and confirmed before the
# build starts, so a stick that is not plugged in fails in seconds rather
# than after five minutes of compiling. Everything the guest prints during
# the install lands in output/images/usb-install.txt.
#
# What this is not: a way to skip docs/usb.md. Once the stick is written,
# cold boot, chassis USB-A port, one-time boot menu, UEFI entry -- the notes
# there are why each of those words is there.

set -e

HERE=$(cd "$(dirname "$0")" && pwd)
BASE=$(cd "$HERE/../../.." && pwd)
WRITE="$HERE/write-usb.sh"

if [ "$(id -u)" = 0 ]; then
	echo "make-usb.sh: run this as your normal user, not with sudo." >&2
	echo "    It asks for your password itself, for the one step that needs it." >&2
	exit 1
fi

DEV=""
BUILD=yes
TEST=no
for a in "$@"; do
	case "$a" in
		--no-build) BUILD=no ;;
		--test)     TEST=yes ;;
		--help|-h)  sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
		/dev/*)     DEV="$a" ;;
		*)          echo "make-usb.sh: unknown argument '$a'" >&2; exit 1 ;;
	esac
done

# The removable USB whole disks the host can see right now, one per line.
# Same test write-usb.sh applies before it will touch anything.
sticks() {
	for d in /sys/block/sd*; do
		[ -e "$d" ] || continue
		[ "$(cat "$d/removable" 2>/dev/null)" = "1" ] || continue
		readlink -f "$d" | grep -q usb || continue
		echo "/dev/$(basename "$d")"
	done
}

echo ">>> Sticks attached:"
LIST=$(sticks)
if [ -z "$LIST" ]; then
	echo "    none. Plug the stick in -- and if it is in, pull it out and push" >&2
	echo "    it back; this host has needed that before it would list one." >&2
	exit 1
fi
# shellcheck disable=SC2086
lsblk -o NAME,SIZE,TRAN,MODEL,LABEL,MOUNTPOINT $LIST | sed 's/^/    /'
echo

if [ -z "$DEV" ]; then
	N=$(echo "$LIST" | wc -l)
	if [ "$N" = 1 ]; then
		DEV="$LIST"
	else
		i=0
		for d in $LIST; do
			i=$((i + 1))
			echo "  $i) $d"
		done
		printf "Which one? [1-%s] " "$N"
		read -r pick
		DEV=$(echo "$LIST" | sed -n "${pick}p")
		[ -n "$DEV" ] || { echo "Aborted."; exit 1; }
	fi
fi
echo "$LIST" | grep -qx "$DEV" || {
	echo "make-usb.sh: $DEV is not a removable USB disk on this host -- refusing" >&2
	exit 1
}

echo "About to ERASE $DEV and install AOS onto it."
printf "Type YES to continue: "
read -r confirm
[ "$confirm" = "YES" ] || { echo "Aborted."; exit 1; }
echo

# Root, now rather than later. sudo's ticket normally lasts a few minutes,
# less than a build; the loop renews it until this script exits.
echo ">>> Writing $DEV needs root; asking once now so the build is not interrupted."
sudo -v
( while sudo -n -v 2>/dev/null; do sleep 50; done ) &
KEEPALIVE=$!
trap 'kill $KEEPALIVE 2>/dev/null' EXIT

if [ "$BUILD" = yes ]; then
	echo ">>> Building (make in $BASE)"
	cd "$BASE"
	# tee's status is the pipe's, so make's own comes back through a file.
	RC="$BASE/output/.make-usb.rc"
	{ make 2>&1; echo $? > "$RC"; } | tee "$BASE/output/make-usb.log"
	rc=$(cat "$RC"); rm -f "$RC"
	[ "$rc" = 0 ] || { echo "make-usb.sh: make failed ($rc); see output/make-usb.log" >&2; exit 1; }
	echo
fi

ISO="$BASE/output/images/rootfs.iso9660"
[ -f "$ISO" ] || { echo "make-usb.sh: no $ISO -- nothing to install" >&2; exit 1; }
echo ">>> Image: $ISO ($(date -r "$ISO" '+%F %T'))"

# The rule from docs/usb.md: never write a stick that will accept no SSH
# login. post-build.sh says so at the end of the build; this checks the
# result rather than the message.
KEYS="$BASE/output/target/root/.ssh/authorized_keys"
if [ -s "$KEYS" ]; then
	echo ">>> SSH: $(grep -c . "$KEYS") key(s) for root on the image"
else
	echo "make-usb.sh: the image has no SSH keys for root." >&2
	echo "    Add yours to br2ext/board/aos/authorized_keys and build again (docs/ssh.md)." >&2
	exit 1
fi
echo

# The stick was confirmed above; write-usb.sh asks the same question once
# more, and the answer travels down the pipe.
printf 'YES\n' | sudo "$WRITE" "$DEV" --install --auto

if [ "$TEST" = yes ]; then
	echo
	sudo "$WRITE" "$DEV" --boot --auto
fi

cat <<EOF

Next, on the machine you are booting:
  1. power fully off, not restart
  2. stick in a USB-A port on the chassis, before pressing power
  3. one-time boot menu at power-on (Esc/F8 on ASUS, F12 on most others)
  4. the UEFI entry for the stick; first GRUB entry
If the screen goes black after GRUB, reboot into "AOS (safe graphics)".
See br2ext/docs/usb.md for why each of those matters.
EOF
