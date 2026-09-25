#!/bin/sh
#
# ci.sh -- the unattended run: build the image, then boot it every way
# boot-test.py knows. What the nightly job and every tag run, on a machine
# with KVM. Exit status is the verdict; the evidence is in output/images:
# <mode>.log, <mode>.serial.txt and <mode>.screen.png per mode.
#
# Run it by hand the same way CI does:  ./br2ext/board/aos/ci.sh
# One mode only:                        ./br2ext/board/aos/ci.sh desktop

set -e

BASE=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$BASE"

if [ "$(id -u)" = 0 ]; then
	echo "ci.sh: run as a normal user; the build must not run as root" >&2
	exit 1
fi

make BR2_EXTERNAL="$BASE/br2ext" aos_x86_64_defconfig >/dev/null

# kconfig drops a symbol whose dependencies are unmet without a word, and
# the failure then shows up hours later in some other package. Check the
# ones a release stands on before spending the hours.
for sym in BR2_TOOLCHAIN_BUILDROOT_GLIBC BR2_REPRODUCIBLE BR2_LINUX_KERNEL_CUSTOM_VERSION \
	BR2_PACKAGE_ADE BR2_PACKAGE_APM BR2_PACKAGE_TERMINAL \
	BR2_PACKAGE_NOTEPAD BR2_PACKAGE_FILES BR2_PACKAGE_SYSMON BR2_PACKAGE_SETTINGS BR2_PACKAGE_AOS_GCC; do
	grep -q "^${sym}=y" .config || { echo "ci.sh: ${sym} did not take" >&2; exit 1; }
done

make

# install leaves the disk that disk boots; keep that order. "soak" is not
# in the default list: it holds the desktop for SOAK_MINUTES (boot-test.py,
# default 20) and is the nightly job's second step, with hours.
MODES=${1:-"live usb install disk desktop"}
rc=0
for mode in $MODES; do
	echo "== boot-test $mode"
	t=1800
	[ "$mode" = soak ] && t=$(( ${SOAK_MINUTES:-20} * 60 + 1800 ))
	if timeout "$t" ./br2ext/board/aos/boot-test.py "$mode" > "output/images/$mode.log" 2>&1; then
		echo "   ok"
	else
		echo "   FAILED (output/images/$mode.log)"
		rc=1
	fi
done
exit $rc
