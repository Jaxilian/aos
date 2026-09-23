#!/bin/sh
#
# runtime-xwayland.sh -- XWayland for the third-party repository, out of
# the packages tree (output-pkgs, aos_packages_defconfig).
#
#   ./br2ext/board/aos/runtime-xwayland.sh <release> [<out dir>]
#
# One package, runtime/xwayland: the Xwayland server. Installing it puts Xwayland on PATH, and that
# is the whole switch: ade-comp starts it at the next session when it
# finds it there, and X11 programs -- Steam's client -- get a DISPLAY.
# --global: the compositor runs the binary bare, through no wrapper, so
# its libraries must be on the system loader path -- apm's lib farm,
# through ldconfig. Every library it links that the image does not carry
# is in here: pixman, epoxy, freetype and the X font libraries. libGL, the
# X client libraries and xkbcomp are the image's (GLX is in the OS for
# exactly this). The GTK3 runtime has some of the same ones; a copy each,
# since that one is not global and this one must be.

set -e
BASE=$(cd "$(dirname "$0")/../../.." && pwd)
REL=${1:?release number}
OUT=${2:-$BASE/../apm-thirdparty/index}

BR2_OUTPUT="$BASE/output-pkgs" exec "$BASE/br2ext/board/aos/br2apkg.py" \
	xwayland xlib_libxcvt xlib_libXfont2 xlib_libxkbfile xlib_libfontenc \
	pixman libepoxy libmd freetype libpng xlib_libxshmfence \
	--name xwayland --org runtime --kind bin --global \
	--version 24.1.0 --release "$REL" \
	--license "MIT" \
	--summary "XWayland: an X server for the programs that still need one, started by the compositor when this is installed" \
	--out "$OUT"
