#!/bin/sh
#
# release.sh -- turn a finished build into what gets published.
#
#   ./br2ext/board/aos/release.sh            -> output/release/
#
# Refuses a build whose BUILD_ID says -dirty: a release is a commit, and
# one with uncommitted changes in it cannot be rebuilt by anyone. The
# version is the one the image itself reports, which post-build.sh took
# from the tag; see docs/publishing.md for what to do with the result.

set -e

BASE=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$BASE"

ISO=output/images/rootfs.iso9660
[ -f "$ISO" ] || { echo "release.sh: no $ISO; build first" >&2; exit 1; }

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

make legal-info >/dev/null
tar -C output -czf "$OUT/$NAME-legal-info.tar.gz" legal-info

# Known CVEs against the packages in this configuration, from the NVD feed
# Buildroot's script fetches; what "how a fix reaches you" in SECURITY.md is
# measured against. Minutes, and needs the network.
make pkg-stats >/dev/null
cp output/pkg-stats.html "$OUT/$NAME-pkg-stats.html"
cp output/pkg-stats.json "$OUT/$NAME-pkg-stats.json"

( cd "$OUT" && sha256sum "$NAME.iso" "$NAME-legal-info.tar.gz" "$NAME-pkg-stats.html" "$NAME-pkg-stats.json" > SHA256SUMS )
"$APM" sign "$OUT/SHA256SUMS"

echo "release.sh: $VERSION ($BUILD_ID) in $OUT:"
ls -l "$OUT"
