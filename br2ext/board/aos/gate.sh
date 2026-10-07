#!/bin/sh
#
# gate.sh -- every QEMU driver, in the order the disks need, one verdict
# per driver and one at the end. A release is tagged only after this is
# green (docs/testing.md).
#
#   gate.sh                 make the keyed build, run everything, then
#                           make the keyless one a release and a stick need
#   gate.sh --no-build      the build in output/images as it is
#   gate.sh --keep-keys     no keyless rebuild at the end
#   gate.sh NAME...         only these drivers (desktop, greeter, clip, ...),
#                           with the disk each needs made first
#
# Needs board/aos/authorized_keys: the disk drivers copy files in over ssh.
# Output: output/gate/summary, output/gate/<driver>.log, and the
# screendumps each driver left under output/gate/<driver>/. Hours; run it
# in the background and wait for "GATE" at the end of its output.

set -u
cd "$(dirname "$0")/../../.." || exit 1
T=br2ext/board/aos
G=output/gate
BUILD=yes
KEYLESS=yes
ONLY=
for a in "$@"; do
	case "$a" in
		--no-build)  BUILD=no ;;
		--keep-keys) KEYLESS=no ;;
		--*)         echo "gate.sh: unknown option $a" >&2; exit 2 ;;
		*)           ONLY="$ONLY $a" ;;
	esac
done

[ -s $T/authorized_keys ] || { echo "gate.sh: no $T/authorized_keys; the disk drivers need the keyed build (docs/testing.md)" >&2; exit 2; }
[ -f local.mk ] && echo "gate.sh: local.mk is present; this tests an override, not the pinned tree" >&2

rm -rf $G
mkdir -p $G
touch $G/.mark
FAILED=0

if [ $BUILD = yes ]; then
	echo ">>> keyed build"
	if ! make > $G/make.log 2>&1; then
		echo "FAIL make (see $G/make.log)"
		echo "GATE FAILED"
		exit 1
	fi
fi

# Which drivers to run: all, or the names given.
want() { # name
	[ -z "$ONLY" ] && return 0
	case " $ONLY " in *" $1 "*) return 0 ;; esac
	return 1
}

# A disk the next drivers need. Made once per kind, only when one of
# the drivers after it is wanted (the caller lists them).
DISK=
disk() { # kind, drivers...
	kind=$1; shift
	needed=no
	for d in "$@"; do want "$d" && needed=yes; done
	[ $needed = yes ] || return 1
	[ "$DISK" = "$kind" ] && return 0
	if [ "$kind" = demo ]; then
		run "install" python3 $T/boot-test.py install
	else
		run "install-$kind" env INSTALL_MODE=$kind python3 $T/boot-test.py install
	fi
	DISK=$kind
	return 0
}

run() { # name, command...
	name=$1; shift
	start=$(date +%s)
	printf '>>> %s\n' "$name"
	if "$@" > "$G/$name.log" 2>&1; then r=pass; else r=FAIL; FAILED=$((FAILED + 1)); fi
	took=$(( $(date +%s) - start ))
	printf '%s %s %ss\n' "$r" "$name" "$took" | tee -a $G/summary
	mkdir -p "$G/$name"
	find output/images -maxdepth 1 \( -name '*.png' -o -name '*.serial.txt' -o -name '*.ppm' \) -newer $G/.mark -exec mv -t "$G/$name/" {} + 2>/dev/null
	touch $G/.mark
}

# The live ISO.
want live    && run live    python3 $T/boot-test.py live
want usb     && run usb     python3 $T/boot-test.py usb
want desktop && run desktop python3 $T/boot-test.py desktop
want ade     && run ade     python3 $T/ade-test.py
want sec     && run sec     python3 $T/sec-test.py
want perf    && run perf    python3 $T/perf-test.py
want replug  && run replug  python3 $T/replug-test.py
# The graphical installer: leaves the disk installed for jax.
if want setup; then run setup python3 $T/setup-test.py; DISK=setup; fi

# The other kinds of disk, each with its drivers.
disk owner greeter   && { want greeter && run greeter python3 $T/greeter-test.py; }
disk oobe oobe homed && {
	want oobe && run oobe python3 $T/oobe-test.py
	if want homed; then
		# oobe-test used up the first boot; homed-test needs a fresh one.
		want oobe && run install-oobe-2 env INSTALL_MODE=oobe python3 $T/boot-test.py install
		run homed python3 $T/homed-test.py
	fi
}
disk encrypt luks    && { want luks && run luks python3 $T/luks-test.py; }

# The demo disk: the installed-disk drivers, update-abort after update.
DEMO="disk diskt clip crash desk disp fx mic perm shot steam store theme update update-abort upgrade-ui"
if disk demo $DEMO; then
	want disk         && run disk         python3 $T/boot-test.py disk
	want diskt        && run diskt        python3 $T/disk-test.py
	want clip         && run clip         python3 $T/clip-test.py
	want crash        && run crash        python3 $T/crash-test.py
	want desk         && run desk         python3 $T/desk-test.py
	want disp         && run disp         python3 $T/disp-test.py
	want fx           && run fx           python3 $T/fx-test.py
	want mic          && run mic          python3 $T/mic-test.py
	want perm         && run perm         python3 $T/perm-test.py
	want shot         && run shot         python3 $T/shot-test.py
	want steam        && run steam        python3 $T/steam-test.py
	want store        && run store        python3 $T/store-test.py
	want theme        && run theme        python3 $T/theme-test.py
	want update       && run update       python3 $T/update-test.py
	want update-abort && run update-abort python3 $T/update-abort-test.py
	want upgrade-ui   && run upgrade-ui   python3 $T/upgrade-ui-test.py
	# update-test leaves the disk on a fake 9.9.9: a fresh demo disk for
	# whoever comes next.
	if want update || want update-abort || want upgrade-ui; then run install-again python3 $T/boot-test.py install; fi
fi

if [ $KEYLESS = yes ]; then
	echo ">>> keyless build (a release and a stick carry no key)"
	rm -f $T/authorized_keys
	rm -rf output/target/root/.ssh
	if ! make > $G/make-keyless.log 2>&1; then
		echo "FAIL make-keyless (see $G/make-keyless.log)"
		FAILED=$((FAILED + 1))
	fi
fi

echo
cat $G/summary
if [ $FAILED -eq 0 ]; then echo "GATE OK"; exit 0; fi
echo "GATE FAILED: $FAILED"
exit 1
