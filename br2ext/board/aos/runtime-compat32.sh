#!/bin/sh
#
# runtime-compat32.sh -- the 32-bit userspace bundle for the third-party
# repository, out of the i686 tree (output-compat32, aos_compat32_defconfig).
#
#   ./br2ext/board/aos/runtime-compat32.sh <release> [<out dir>]
#
# One package, runtime/compat32: everything that tree builds -- a 32-bit
# glibc with its loader, libstdc++ and libgcc, zlib, and Mesa with GLX on
# libglvnd with the X libraries GLX is made of. aos-sandbox --lib32 binds
# its lib/ as /lib, which is how /lib/ld-linux.so.2 and a 32-bit libGL
# come to exist for a 32-bit ELF. What needs it is Steam's client; what
# it must never be is part of the image. The member list is the tree's
# own: every package that installed something into its target.

set -e
BASE=$(cd "$(dirname "$0")/../../.." && pwd)
REL=${1:?release number}
OUT=${2:-$BASE/../apm-thirdparty/index}
TREE="$BASE/output-compat32"

# Only packages with a versioned build directory: the skeleton and the
# init scripts install files too, and are not packages br2apkg can read.
MEMBERS=""
for m in $(cut -d, -f1 "$TREE/build/packages-file-list.txt" | sort -u); do
	# eudev is here for libudev alone (an --extra below): its tools would
	# have bin/udevadm pointing at ../sbin/udevadm, and both land in bin/.
	case "$m" in linux-headers|skeleton*|toolchain*|host-*|ifupdown-scripts|eudev|kmod|util-linux|util-linux-libs) continue ;; esac
	ls -d "$TREE/build/$m"-[0-9]* >/dev/null 2>&1 && MEMBERS="$MEMBERS $m"
done
echo "members:$MEMBERS"

# shellcheck disable=SC2086
BR2_OUTPUT="$TREE" exec "$BASE/br2ext/board/aos/br2apkg.py" \
	$MEMBERS \
	--extra 'eudev:./lib/libudev.so*' \
	--name compat32 --org runtime --kind lib \
	--version 2.44.0 --release "$REL" \
	--license "LGPL-2.1-or-later AND GPL-3.0-or-later WITH GCC-exception-3.1 AND MIT AND Zlib" \
	--summary "32-bit glibc, libstdc++, zlib and a GLX Mesa for the sandbox: what a 32-bit program needs from a host, and nothing AOS carries" \
	--out "$OUT"
