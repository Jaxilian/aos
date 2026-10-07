#!/bin/sh
#
# runtime-python.sh -- the Python runtime bundle for the third-party repository.
#
#   ./br2ext/board/aos/runtime-python.sh <release> [<out dir>]
#
# One package, runtime/python, out of the packages tree (output-pkgs,
# aos_packages_defconfig): Python 3 with the GObject bindings and the
# modules Lutris imports, and the typelibs of GLib, GTK3, Pango,
# GdkPixbuf, ATK and HarfBuzz that the bindings load. The libraries those
# typelibs name are the system's (GLib) and runtime/gtk3's (the rest), so
# a program runs it as
#
#   PY=/opt/apm/packages/runtime/python/current
#   PATH=$PY/bin:$PATH LD_LIBRARY_PATH=$PY/lib GI_TYPELIB_PATH=$PY/lib/girepository-1.0 \
#       gtk3-run $PY/bin/python3 program.py
#
# No wrapper of its own: a generated one sets the toolkit's paths
# (fonts.conf, GSettings schemas, GTK modules) to this package, where
# they are not, over gtk3-run's. Python finds its own library from the
# binary's place, so it needs no PYTHONHOME.
#
# The pure-Python packages need a second step. Buildroot's file lists
# name the .py files they installed, but the target is byte-compiled
# (BR2_PACKAGE_PYTHON3_PYC_ONLY) so only .pyc remain there, and unlike
# the standard library they are not in staging either: br2apkg finds
# nothing to copy and ships their dist-info alone. So the package is
# opened again and site-packages taken from the target as it is.

set -e
BASE=$(cd "$(dirname "$0")/../../.." && pwd)
REL=${1:?release number}
OUT=${2:-$BASE/../apm-thirdparty/index}
TL=./usr/lib/girepository-1.0/*.typelib
APM=${APM:-apm}
VERSION=3.14.7

BR2_OUTPUT="$BASE/output-pkgs" "$BASE/br2ext/board/aos/br2apkg.py" \
	python3 gobject-introspection python-gobject python-pycairo dbus-python \
	python-pyyaml libyaml python-lxml libxslt \
	python-requests python-urllib3 python-idna python-charset-normalizer python-certifi \
	python-pillow python-setproctitle python-distro python-evdev \
	--extra "libglib2:$TL" --extra "libgtk3:$TL" --extra "pango:$TL" \
	--extra "gdk-pixbuf:$TL" --extra "at-spi2-core:$TL" --extra "harfbuzz:$TL" \
	--name python --org runtime --kind lib \
	--version "$VERSION" --release "$REL" \
	--license "PSF-2.0 AND LGPL-2.1-or-later AND MIT AND Apache-2.0 AND BSD-3-Clause" \
	--summary "Python 3 with the GObject bindings, and the modules Lutris uses: requests, yaml, lxml, Pillow, dbus" \
	--depends 'runtime/gtk3@*' \
	--out "$OUT"

APKG="$OUT/runtime-python-$VERSION-$REL.x86_64.apkg"
PAYLOAD=$(mktemp -d)
unzip -q "$APKG" -d "$PAYLOAD"
cp -a "$BASE/output-pkgs/target/usr/lib/python3.14/site-packages/." "$PAYLOAD/lib/python3.14/site-packages/"
rm -f "$APKG"
(cd "$OUT" && "$APM" ship "$PAYLOAD")
rm -rf "${PAYLOAD:?}"
