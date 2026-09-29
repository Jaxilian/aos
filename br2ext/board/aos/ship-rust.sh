#!/bin/sh
#
# ship-rust.sh -- a cargo project as an apm package, numbered so that
# `apm upgrade` (or `apm install ./x.apkg`) takes every build.
#
#   ship-rust.sh <project dir> [--desktop FILE] [--release N] [--out DIR]
#
# Name, version, summary and license come from Cargo.toml. The release is
# the build's Unix time unless given: apm refuses a package whose version
# and release it already has, and a dev loop rebuilds the same version all
# day. The .desktop -- given, or found as br2ext/package/<name>/*.desktop
# when run from the aos tree -- becomes [launcher]; without one the package
# is a plain command. Runs on AOS itself, or on the host as a shortcut
# (host glibc must be no newer than AOS's, and a GUI app's sonames must
# exist there).
#
# Then: sudo apm install ./aos-<name>-*.apkg, or `apm index` the directory
# for a file:// repository.

set -e

BASE=$(cd "$(dirname "$0")/../../.." && pwd)
APM=${APM:-$(command -v apm || echo "$BASE/../apm/target/release/apm")}
ORG=${ORG:-aos}
DESKTOP=""
RELEASE=$(date +%s)
OUT=$PWD
PROJECT=""

while [ $# -gt 0 ]; do
	case $1 in
		--desktop) DESKTOP=$2; shift 2 ;;
		--release) RELEASE=$2; shift 2 ;;
		--out) OUT=$2; shift 2 ;;
		-*) echo "usage: ship-rust.sh <project dir> [--desktop FILE] [--release N] [--out DIR]" >&2; exit 2 ;;
		*) PROJECT=$1; shift ;;
	esac
done
[ -d "$PROJECT" ] || { echo "ship-rust.sh: no project directory '$PROJECT'" >&2; exit 2; }
[ -x "$APM" ] || { echo "ship-rust.sh: no apm (APM=/path/to/apm)" >&2; exit 1; }
cd "$PROJECT"

# [package] is the first table in Cargo.toml; the first match is its name,
# not a [[bin]]'s.
field() { sed -n "s/^$1 *= *\"\(.*\)\".*/\1/p" Cargo.toml | head -1; }
NAME=$(field name)
VERSION=$(field version)
SUMMARY=$(field description)
LICENSE=$(field license)
[ -n "$NAME" ] && [ -n "$VERSION" ] || { echo "ship-rust.sh: no name/version in Cargo.toml" >&2; exit 1; }
[ -n "$DESKTOP" ] || DESKTOP=$(ls "$BASE/br2ext/package/$NAME"/*.desktop 2>/dev/null | head -1)

cargo build --release --bin "$NAME"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/bin"
cp "target/release/$NAME" "$WORK/bin/$NAME"

KIND=bin
LAUNCHER=""
if [ -n "$DESKTOP" ]; then
	KIND=app
	entry() { sed -n "s/^$1=//p" "$DESKTOP" | head -1; }
	CATEGORIES=$(entry Categories | tr ';' '\n' | sed '/^$/d; s/.*/"&"/' | paste -sd, -)
	LAUNCHER="[launcher]
name       = \"$(entry Name)\"
comment    = \"$(entry Comment)\"
exec       = \"bin/$NAME\"
categories = [$CATEGORIES]
"
fi

cat > "$WORK/manifest.toml" <<EOF
# $NAME $VERSION, built by br2ext/board/aos/ship-rust.sh from $(pwd).

manifest_version = 1

[package]
name         = "$NAME"
organization = "$ORG"
version      = "$VERSION"
release      = $RELEASE
kind         = "$KIND"
summary      = "${SUMMARY:-$NAME}"
license      = "${LICENSE:-MIT}"

[provides]
command = ["$NAME"]

[requires]
run = ["glibc"]

$LAUNCHER
EOF

mkdir -p "$OUT"
cd "$OUT"
"$APM" ship "$WORK" --sign
