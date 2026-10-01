#!/bin/sh
#
# release.sh -- turn a finished build into what gets published.
#
#   ./br2ext/board/aos/release.sh            -> output/release/
#   ./br2ext/board/aos/release.sh --publish  the same, then uploaded
#
# Refuses a build whose BUILD_ID says -dirty: a release is a commit, and
# one with uncommitted changes in it cannot be rebuilt by anyone. The
# version is the one the image itself reports, which post-build.sh took
# from the tag; see docs/publishing.md for what to do with the result.
#
# --publish uploads what aos-update on an installed machine fetches -- the
# root tarball, SHA256SUMS and its signature -- as assets of the apm
# package index's release in apm-recipes (the fixed tag `index`, the URL
# in rootfs-overlay/usr/lib/aos/update.conf). The previous release's
# tarball is removed; the ISO is not uploaded, it is handed out by hand.

set -e

BASE=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$BASE"

ISO=output/images/rootfs.iso9660
ROOT=output/images/rootfs.tar.xz
[ -f "$ISO" ] || { echo "release.sh: no $ISO; build first" >&2; exit 1; }
[ -f "$ROOT" ] || { echo "release.sh: no $ROOT; build first" >&2; exit 1; }

OSREL=output/target/usr/lib/os-release
VERSION=$(sed -n 's/^VERSION_ID=//p' "$OSREL")
BUILD_ID=$(sed -n 's/^BUILD_ID=//p' "$OSREL")
case "$BUILD_ID" in
	*-dirty|unknown|"") echo "release.sh: BUILD_ID is '$BUILD_ID'; commit, tag, rebuild" >&2; exit 1 ;;
esac

APM=${APM:-$(command -v apm || echo "$BASE/../apm/target/release/apm")}
[ -x "$APM" ] || { echo "release.sh: no apm on the host (APM=/path/to/apm)" >&2; exit 1; }
[ -f "$HOME/.apm/etc/keys/apm.key" ] || { echo "release.sh: no signing key; apm key new" >&2; exit 1; }

OUT=output/release
rm -rf "$OUT"
mkdir -p "$OUT"
NAME="aos-$VERSION-x86_64"
cp "$ISO" "$OUT/$NAME.iso"
cp "$ROOT" "$OUT/$NAME-root.tar.xz"

make legal-info >/dev/null
tar -C output -czf "$OUT/$NAME-legal-info.tar.gz" legal-info

# Known CVEs against the packages in this configuration, from the NVD feed
# Buildroot's script fetches; what "how a fix reaches you" in SECURITY.md is
# measured against. Minutes, and needs the network.
make pkg-stats >/dev/null
cp output/pkg-stats.html "$OUT/$NAME-pkg-stats.html"
cp output/pkg-stats.json "$OUT/$NAME-pkg-stats.json"

( cd "$OUT" && sha256sum "$NAME.iso" "$NAME-root.tar.xz" "$NAME-legal-info.tar.gz" "$NAME-pkg-stats.html" "$NAME-pkg-stats.json" > SHA256SUMS )
"$APM" sign "$OUT/SHA256SUMS"

echo "release.sh: $VERSION ($BUILD_ID) in $OUT:"
ls -l "$OUT"
[ "$1" = --publish ] || exit 0

TAG=index
REPO=Jaxilian/apm-recipes
for old in $(gh release view "$TAG" -R "$REPO" --json assets -q '.assets[].name' | grep '^aos-.*-root\.tar\.xz$'); do
	[ "$old" = "$NAME-root.tar.xz" ] || gh release delete-asset "$TAG" "$old" -R "$REPO" -y
done
# The upload fails transiently now and then; --clobber makes a retry safe.
n=0
until gh release upload "$TAG" -R "$REPO" --clobber "$OUT/$NAME-root.tar.xz" "$OUT/SHA256SUMS" "$OUT/SHA256SUMS.minisig"; do
	n=$((n + 1)); [ $n -lt 3 ] || exit 1
	echo "upload failed, retrying ($n)" >&2; sleep 5
done
echo "published: https://github.com/$REPO/releases/download/$TAG/SHA256SUMS"
echo "note: the edge cache serves the previous SHA256SUMS for a few minutes" >&2
