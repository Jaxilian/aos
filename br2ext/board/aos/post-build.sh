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

# gcc's own runtime, and the C++ headers.
#
# aos-gcc builds only the compiler proper ("all-gcc"), deliberately: the
# target libraries were already built once by host-gcc-final, from the same
# gcc source and version, and building them twice risks shipping two subtly
# different copies of the same runtime. The consequence is that the pieces
# gcc links into every binary -- crtbegin.o, crtend.o, libgcc.a -- live in
# the cross toolchain's own directory rather than in the sysroot, so they
# have to be brought over explicitly. Without them the compiler runs fine
# and then fails at the link step with "cannot find crtbegin.o".
: "${HOST_DIR:?post-build.sh: HOST_DIR not set}"

GCC_TRIPLET=x86_64-buildroot-linux-gnu
for gccdir in "${HOST_DIR}/lib/gcc/${GCC_TRIPLET}"/*; do
	[ -d "${gccdir}" ] || continue
	gccver=$(basename "${gccdir}")
	dest="${TARGET_DIR}/usr/lib/gcc/${GCC_TRIPLET}/${gccver}"
	mkdir -p "${dest}"
	find "${gccdir}" -maxdepth 1 \( -name '*.o' -o -name '*.a' \) \
		-exec cp -a -t "${dest}/" {} +
done

# The C++ standard library headers live under the toolchain's own include
# tree, not under the sysroot, so rsync them across as well.
if [ -d "${HOST_DIR}/${GCC_TRIPLET}/include/c++" ]; then
	mkdir -p "${TARGET_DIR}/usr/include/c++"
	rsync -a --chmod=u=rwX,go=rX \
		"${HOST_DIR}/${GCC_TRIPLET}/include/c++/" \
		"${TARGET_DIR}/usr/include/c++/"
fi
