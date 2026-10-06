#!/bin/sh
#
# release.sh -- turn a finished build into what gets published.
#
#   ./br2ext/board/aos/release.sh            -> output/release/
#   ./br2ext/board/aos/release.sh --publish  the same, then uploaded
#   ./br2ext/board/aos/release.sh --publish --iso-to OWNER/REPO
#                                          and the ISO for people to download:
#                                          a GitHub release v<version> there
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
CORE=output/images/core.img
VERITY=output/images/core.verity
[ -f "$ISO" ] || { echo "release.sh: no $ISO; build first" >&2; exit 1; }
[ -f "$CORE" ] && [ -f "$VERITY" ] || { echo "release.sh: no $CORE; build first" >&2; exit 1; }

OSREL=output/target/usr/lib/os-release
VERSION=$(sed -n 's/^VERSION_ID=//p' "$OSREL")
BUILD_ID=$(sed -n 's/^BUILD_ID=//p' "$OSREL")
case "$BUILD_ID" in
	*-dirty|unknown|"") echo "release.sh: BUILD_ID is '$BUILD_ID'; commit, tag, rebuild" >&2; exit 1 ;;
esac
# The version is the tag's only when the tag is on the built commit; a
# commit past it builds with the overlay's placeholder version, and one
# such build went out as "0.1.0" (2026-10-02). Tag HEAD, make, then this.
[ "$BUILD_ID" = "v$VERSION" ] || { echo "release.sh: BUILD_ID '$BUILD_ID' is not the tag of VERSION_ID $VERSION; tag HEAD (git tag -f vX.Y.Z), make, and run this again" >&2; exit 1; }

# A published image carries nobody's key: with one, whoever built it has
# root on every machine that installs it. post-build.sh puts the builder's
# board/aos/authorized_keys on the image and enables sshd for the stick
# rounds; a release is a build made without that file (docs/ssh.md).
if [ -s output/target/root/.ssh/authorized_keys ] || [ -e output/target/usr/lib/systemd/system-preset/60-aos-ssh.preset ]; then
	echo "release.sh: the image carries SSH keys for root; move board/aos/authorized_keys away, make, and run this again" >&2
	exit 1
fi
# The tarball is what aos-update installs: sshd must not be enabled in it.
if [ -e output/target/etc/systemd/system/multi-user.target.wants/sshd.service ]; then
	echo "release.sh: sshd is enabled in the image; see board/aos/rootfs-overlay/usr/lib/systemd/system-preset" >&2
	exit 1
fi

APM=${APM:-$(command -v apm || echo "$BASE/../apm/target/release/apm")}
[ -x "$APM" ] || { echo "release.sh: no apm on the host (APM=/path/to/apm)" >&2; exit 1; }
[ -f "$HOME/.apm/etc/keys/apm.key" ] || { echo "release.sh: no signing key; apm key new" >&2; exit 1; }

OUT=output/release
rm -rf "$OUT"
mkdir -p "$OUT"
NAME="aos-$VERSION-x86_64"
cp "$ISO" "$OUT/$NAME.iso"
xz -T0 -c "$CORE" > "$OUT/$NAME-core.img.xz"
cp "$VERITY" "$OUT/$NAME-core.verity"

make legal-info >/dev/null
tar -C output -czf "$OUT/$NAME-legal-info.tar.gz" legal-info

# Known CVEs against the packages in this configuration, from the NVD feed
# Buildroot's script fetches; what "how a fix reaches you" in SECURITY.md is
# measured against. Minutes, and needs the network.
make pkg-stats >/dev/null
cp output/pkg-stats.html "$OUT/$NAME-pkg-stats.html"
cp output/pkg-stats.json "$OUT/$NAME-pkg-stats.json"

( cd "$OUT" && sha256sum "$NAME.iso" "$NAME-core.img.xz" "$NAME-core.verity" "$NAME-legal-info.tar.gz" "$NAME-pkg-stats.html" "$NAME-pkg-stats.json" > SHA256SUMS )
"$APM" sign "$OUT/SHA256SUMS"

echo "release.sh: $VERSION ($BUILD_ID) in $OUT:"
ls -l "$OUT"
PUBLISH=no
ISO_TO=""
while [ $# -gt 0 ]; do
	case "$1" in
		--publish) PUBLISH=yes ;;
		--iso-to)  ISO_TO="$2"; shift ;;
		*) echo "release.sh: unknown argument $1" >&2; exit 2 ;;
	esac
	shift
done
[ "$PUBLISH" = yes ] || exit 0

TAG=index
REPO=Jaxilian/apm-recipes
for old in $(gh release view "$TAG" -R "$REPO" --json assets -q '.assets[].name' | grep -E '^aos-.*-(root\.tar\.xz|core\.img\.xz|core\.verity)$'); do
	case "$old" in "$NAME-core.img.xz"|"$NAME-core.verity") ;; *) gh release delete-asset "$TAG" "$old" -R "$REPO" -y ;; esac
done
# The upload fails transiently now and then; --clobber makes a retry safe.
n=0
until gh release upload "$TAG" -R "$REPO" --clobber "$OUT/$NAME-core.img.xz" "$OUT/$NAME-core.verity" "$OUT/SHA256SUMS" "$OUT/SHA256SUMS.minisig"; do
	n=$((n + 1)); [ $n -lt 3 ] || exit 1
	echo "upload failed, retrying ($n)" >&2; sleep 5
done
echo "published: https://github.com/$REPO/releases/download/$TAG/SHA256SUMS"
echo "note: the edge cache serves the previous SHA256SUMS for a few minutes" >&2

# The download page: the ISO and what checks it, as release v<version> of a
# public repository of the publisher's choosing. The key goes beside it so
# install.md's minisign step has it; it is the same key every machine
# already trusts.
[ -n "$ISO_TO" ] || exit 0
cp "$HOME/.apm/etc/keys/apm.pub" "$OUT/apm.pub"
# The release notes: what changed since the previous tag, from the commit
# subjects of this tree (one line each, the "aos:" prefix dropped), under
# the standing pointers. Written beside the release too, for the record.
PREV=$(git describe --tags --abbrev=0 "v$VERSION^" 2>/dev/null || true)
{
	echo "AOS $VERSION"
	echo
	if [ -n "$PREV" ]; then
		echo "Since ${PREV#v}:"
		echo
		git log --no-merges --format='%s' "$PREV..v$VERSION" | sed -n 's/^aos: //p' | sed 's/^/- /'
		echo
	fi
	echo "Install guide: docs/install.md. What does not work yet: docs/known-issues.md."
	echo "The CVE report and its triage: docs/security-status.md."
	echo
	echo 'Check the ISO: `minisign -Vm SHA256SUMS -p apm.pub`, then `sha256sum -c --ignore-missing SHA256SUMS`.'
} > "$OUT/NOTES.md"
gh release view "v$VERSION" -R "$ISO_TO" >/dev/null 2>&1 || \
	gh release create "v$VERSION" -R "$ISO_TO" --title "AOS $VERSION" --notes-file "$OUT/NOTES.md"
n=0
until gh release upload "v$VERSION" -R "$ISO_TO" --clobber "$OUT/$NAME.iso" "$OUT/SHA256SUMS" "$OUT/SHA256SUMS.minisig" "$OUT/apm.pub" "$OUT/$NAME-pkg-stats.html"; do
	n=$((n + 1)); [ $n -lt 3 ] || exit 1
	echo "upload failed, retrying ($n)" >&2; sleep 5
done
echo "download page: https://github.com/$ISO_TO/releases/tag/v$VERSION"
