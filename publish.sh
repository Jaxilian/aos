#!/bin/sh
# Publish both apm repositories: the official one (apm-recipes) and the
# third-party one (apm-thirdparty), each through its own publish.sh.
# Run as yourself, not sudo: the signing key and the gh login are yours.
#
#   ./publish.sh            build, sign and upload both indexes
#   ./publish.sh --local    build and sign only; nothing is uploaded
#
# The sibling checkouts are expected beside this one (../apm-recipes,
# ../apm-thirdparty). apm is the release build in ../apm unless APM says
# otherwise; build it with `cargo build --release` there first.

set -e
[ "$(id -u)" != 0 ] || { echo "publish.sh: run this as yourself, not with sudo" >&2; exit 1; }

OS=$(cd "$(dirname "$0")/.." && pwd)
APM=${APM:-$OS/apm/target/release/apm}
[ -x "$APM" ] || { echo "publish.sh: no apm at $APM (cargo build --release in $OS/apm)" >&2; exit 1; }
export APM

for repo in apm-recipes apm-thirdparty; do
	echo ">>> $repo"
	"$OS/$repo/publish.sh" "$@"
	echo
done
case "$1" in
	--local) echo "Built and signed locally; nothing uploaded." ;;
	*)       echo "Published: apm-recipes and apm-thirdparty." ;;
esac
