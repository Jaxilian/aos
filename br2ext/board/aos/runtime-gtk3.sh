#!/bin/sh
#
# runtime-gtk3.sh -- the GTK3 runtime bundle for the third-party repository.
#
#   ./br2ext/board/aos/runtime-gtk3.sh <release> [<out dir>]
#
# One package, runtime/gtk3, out of the packages tree (output-pkgs, built
# from aos_packages_defconfig): GTK3 and everything Electron applications
# and Firefox load at startup. The list below is the bundle; the first
# one was assembled by hand and its list recovered from the payload, so
# this file exists to make the next one a command. Bump <release> when
# the same GTK3 version is rebuilt with more in it.

set -e
BASE=$(cd "$(dirname "$0")/../../.." && pwd)
REL=${1:?release number}
OUT=${2:-$BASE/../apm-thirdparty/index}

BR2_OUTPUT="$BASE/output-pkgs" exec "$BASE/br2ext/board/aos/br2apkg.py" \
	libgtk3 gdk-pixbuf pango cairo pixman harfbuzz libfribidi freetype fontconfig \
	libepoxy at-spi2-core libpng shared-mime-info \
	adwaita-icon-theme hicolor-icon-theme \
	alsa-lib cups sqlite libnss libnspr \
	xcb-proto libxcb xlib_libX11 xlib_libXau xlib_libXdmcp xlib_libXext \
	xlib_libXcomposite xlib_libXdamage xlib_libXfixes xlib_libXi \
	xlib_libXrandr xlib_libXrender xlib_libXtst xlib_libxshmfence \
	xlib_libXcursor \
	--name gtk3 --org runtime --kind lib --wrapper gtk3-run \
	--version 3.24.0 --release "$REL" \
	--license "LGPL-2.1-or-later AND MPL-2.0 AND MIT AND Apache-2.0" \
	--summary "GTK3 and what Electron applications and Firefox load: fontconfig, NSS, ALSA, CUPS, the X client libraries" \
	--depends 'aos/fonts@*' \
	--out "$OUT"
