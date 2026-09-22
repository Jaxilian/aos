#!/bin/sh
#
# runtime-compat32.sh -- the 32-bit userspace bundle for the third-party
# repository, out of the i686 tree (output-compat32, aos_compat32_defconfig).
#
#   ./br2ext/board/aos/runtime-compat32.sh <release> [<out dir>]
#
# One package, runtime/compat32: a 32-bit glibc with its loader, libstdc++
# and libgcc from the same gcc as the image, and zlib. aos-sandbox --lib32
# binds its lib/ as /lib, which is how /lib/ld-linux.so.2 comes to exist
# for a 32-bit ELF. What needs it is Steam's client; what it must never
# be is part of the image.

set -e
BASE=$(cd "$(dirname "$0")/../../.." && pwd)
REL=${1:?release number}
OUT=${2:-$BASE/../apm-thirdparty/index}

BR2_OUTPUT="$BASE/output-compat32" exec "$BASE/br2ext/board/aos/br2apkg.py" \
	glibc gcc-final zlib \
	--name compat32 --org runtime --kind lib \
	--version 2.44.0 --release "$REL" \
	--license "LGPL-2.1-or-later AND GPL-3.0-or-later WITH GCC-exception-3.1 AND Zlib" \
	--summary "32-bit glibc, libstdc++ and zlib for the sandbox: what a 32-bit program needs from a host, and nothing AOS carries" \
	--out "$OUT"
