#!/bin/sh
#
# make-usb.sh -- build AOS and install it onto a USB stick, as one command.
#
#   ./usb.sh                  build, pick the stick, install it, verify it
#   ./usb.sh /dev/sdX         the same, onto that stick
#   ./usb.sh --no-build       skip make; install the image already built
#   ./usb.sh --test           afterwards boot the stick in QEMU to prove it
#   ./usb.sh --release        a machine of your own: asks for a user name and
#                             password, and the install creates that account
#                             instead of the demo one (admin / 123321) and
#                             locks root's console login. Nothing else differs.
#   ./usb.sh --seed=DIR       afterwards copy DIR's contents into that
#                             account's home on the stick (test notes)
#
# Options combine: "./usb.sh /dev/sda --no-build --release --test".
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
RELEASE=no
ACCOUNT=""
SEED=""
for a in "$@"; do
	case "$a" in
		--no-build) BUILD=no ;;
		--test)     TEST=yes ;;
		--release)  RELEASE=yes ;;
		--seed=*)   SEED=$(realpath "${a#--seed=}") ;;
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

# The release account: asked for here, on the host, before anything slow
# happens. The password never leaves this shell in the clear -- it is
# hashed with sha512-crypt and only the hash travels, through a file only
# this user can read, into the guest with its echo turned off.
cleanup() {
	[ -z "$ACCOUNT" ] || rm -f "$ACCOUNT"
	kill "${KEEPALIVE:-}" 2>/dev/null
}
trap cleanup EXIT
if [ "$RELEASE" = yes ]; then
	echo ">>> Release install: your own account replaces the demo one."
	printf "User name: "
	read -r NEWUSER
	echo "$NEWUSER" | grep -qE '^[a-z_][a-z0-9_-]{0,31}$' || {
		echo "make-usb.sh: '$NEWUSER' is not a usable user name (lowercase, digits, - _)" >&2
		exit 1
	}
	[ "$NEWUSER" != root ] || { echo "make-usb.sh: not root" >&2; exit 1; }
	stty -echo
	printf "Password: "; read -r PW1; echo
	printf "Again:    "; read -r PW2; echo
	stty echo
	[ "$PW1" = "$PW2" ] || { echo "make-usb.sh: passwords differ" >&2; exit 1; }
	[ -n "$PW1" ] || { echo "make-usb.sh: empty password" >&2; exit 1; }
	HASH=$(printf '%s' "$PW1" | openssl passwd -6 -stdin)
	unset PW1 PW2
	ACCOUNT=$(mktemp "${XDG_RUNTIME_DIR:-/tmp}/aos-account.XXXXXX")
	chmod 600 "$ACCOUNT"
	printf '%s\n%s\n' "$NEWUSER" "$HASH" > "$ACCOUNT"
	unset HASH
	echo
fi

# Root, now rather than later. sudo's ticket normally lasts a few minutes,
# less than a build; the loop renews it until this script exits.
echo ">>> Writing $DEV needs root; asking once now so the build is not interrupted."
sudo -v
( while sudo -n -v 2>/dev/null; do sleep 50; done ) &
KEEPALIVE=$!

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
# shellcheck disable=SC2086
printf 'YES\n' | sudo "$WRITE" "$DEV" --install --auto ${ACCOUNT:+--account "$ACCOUNT"}

# --seed=DIR: DIR's contents into the account's home on the installed
# stick -- notes and scripts for the next test round. After the install,
# on the host: the root partition by its label, the account by name, the
# owner by the uid the stick's own passwd gives it.
if [ -n "$SEED" ]; then
	echo ">>> Seeding the home from $SEED"
	who=${NEWUSER:-admin}
	part=$(lsblk -lnpo PATH,LABEL "$DEV" | awk '$2 == "aos" { print $1; exit }')
	[ -n "$part" ] || { echo "make-usb.sh: no partition labelled aos on $DEV; not seeded" >&2; exit 1; }
	mnt=$(mktemp -d)
	sudo mount "$part" "$mnt"
	uid=$(awk -F: -v u="$who" '$1 == u { print $3 ":" $4 }' "$mnt/etc/passwd")
	if [ -n "$uid" ] && [ -d "$mnt/home/$who" ]; then
		sudo cp -r "$SEED"/. "$mnt/home/$who/"
		sudo chown -R "$uid" "$mnt/home/$who"
		echo "    $(ls "$SEED" | tr '\n' ' ')-> /home/$who"
	else
		echo "make-usb.sh: no account $who on the stick; not seeded" >&2
	fi
	sudo umount "$mnt"
	rmdir "$mnt"
fi

if [ "$TEST" = yes ]; then
	echo
	sudo "$WRITE" "$DEV" --boot --auto
fi

cat <<EOF

$([ "$RELEASE" = yes ] && echo "Log in as $NEWUSER; the demo account is gone and root's console login is locked." \
                         || echo "The demo account is admin, password 123321; sudo asks for it.")

Next, on the machine you are booting:
  1. power fully off, not restart
  2. stick in a USB-A port on the chassis, before pressing power
  3. one-time boot menu at power-on (Esc/F8 on ASUS, F12 on most others)
  4. the UEFI entry for the stick; first GRUB entry
If the screen goes black after GRUB, reboot into "AOS (safe graphics)".
See br2ext/docs/usb.md for why each of those matters.
EOF
