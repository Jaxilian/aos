#!/bin/sh
#
# AOS post-build: export the development sysroot into the target.
#
# Buildroot installs only the *runtime* parts of libraries into the target
# filesystem -- libfoo.so.N and nothing else -- because a normal Buildroot
# image is never expected to compile anything. AOS is self-hosting, so the
# target also needs what Buildroot leaves behind in the staging sysroot:
# headers, startup files (crt*.o), static archives, and the unversioned
# .so symlinks and linker scripts that "-lfoo" resolves through.
#
# This runs as a post-build script rather than as a package because it must
# happen after *every* package has populated staging. A package could only
# guarantee ordering against its own declared dependencies.
#
# $1 is TARGET_DIR; STAGING_DIR is exported by Buildroot.

set -e

TARGET_DIR="${1:?post-build.sh: TARGET_DIR not passed}"
: "${STAGING_DIR:?post-build.sh: STAGING_DIR not set}"

# Headers: the C library's, the kernel's UAPI, the C++ standard library's,
# and those of every library AOS ships. A user writing a compositor needs
# EGL/GBM/DRM headers on the machine, not on some other machine.
rsync -a --chmod=u=rwX,go=rX \
	"${STAGING_DIR}/usr/include/" "${TARGET_DIR}/usr/include/"

# Link-time artefacts. Restricted to development file types so we do not
# duplicate the runtime .so.N libraries that are already in the target.
#
# The .so entries are mostly symlinks (libm.so -> libm.so.6) and, for the C
# library, GNU ld linker scripts. Both refer to their targets by absolute
# path, and those paths are correct on the target because the sysroot we are
# copying from is laid out as the target's own root.
for d in lib usr/lib; do
	[ -d "${STAGING_DIR}/${d}" ] || continue
	mkdir -p "${TARGET_DIR}/${d}"
	find "${STAGING_DIR}/${d}" -maxdepth 1 \
		\( -name '*.o' -o -name '*.a' -o -name '*.so' \) \
		-exec cp -a -t "${TARGET_DIR}/${d}/" {} +
done

# pkg-config metadata, so ./configure and build.rs can discover what is here.
if [ -d "${STAGING_DIR}/usr/lib/pkgconfig" ]; then
	mkdir -p "${TARGET_DIR}/usr/lib/pkgconfig"
	cp -a "${STAGING_DIR}/usr/lib/pkgconfig/." \
		"${TARGET_DIR}/usr/lib/pkgconfig/"
	# Staging .pc files carry the host-side sysroot prefix; on the target
	# the sysroot is simply /.
	sed -i "s,${STAGING_DIR},,g" "${TARGET_DIR}"/usr/lib/pkgconfig/*.pc
fi
