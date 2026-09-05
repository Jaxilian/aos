################################################################################
#
# aos-gcc
#
################################################################################

# A "crossed native" gcc. Three machines matter to a gcc build:
#
#   build  = x86_64-pc-linux-gnu        the machine running this build
#   host   = x86_64-buildroot-linux-gnu the machine the compiler will RUN on
#   target = x86_64-buildroot-linux-gnu the machine it generates code FOR
#
# Buildroot's own host-gcc-final sets build == host != target, giving a cross
# compiler that runs here. We set build != host == target, giving a compiler
# that runs on the AOS machine and compiles for it. Buildroot's autotools
# infrastructure already passes --build and --host correctly for a target
# package; we only add --target.

# Share the cross-compiler's exact version, site and tarball. GCC_VERSION,
# GCC_SITE and GCC_SOURCE come from package/gcc/gcc.mk, which Buildroot always
# includes. Sharing is not cosmetic: the target already carries libgcc_s and
# libstdc++ produced by host-gcc-final from this same source, and a compiler
# whose version disagrees with its own runtime libraries is a real bug.
AOS_GCC_VERSION = $(GCC_VERSION)
AOS_GCC_SITE = $(GCC_SITE)
AOS_GCC_SOURCE = $(GCC_SOURCE)

# Download into dl/gcc/ so the tarball is fetched once and shared with
# Buildroot's gcc package rather than downloaded a second time.
AOS_GCC_DL_SUBDIR = gcc

AOS_GCC_LICENSE = GPL-3.0+, LGPL-3.0+, GCC-exception-3.1
AOS_GCC_LICENSE_FILES = COPYING3 COPYING.RUNTIME COPYING3.LIB

# gmp, mpfr and mpc are gcc's arithmetic dependencies and must be the *target*
# builds, since the compiler linking against them will run on the target.
# binutils supplies the as and ld that the installed gcc driver will invoke.
AOS_GCC_DEPENDENCIES = binutils gmp mpfr mpc

# Buildroot stores gcc patches under package/gcc/<version>/ because its own
# gcc packages are named gcc-initial and gcc-final rather than gcc. They are
# not picked up automatically for a package by another name, so apply them
# explicitly -- the cross compiler and this one must be built from identical
# sources.
define AOS_GCC_APPLY_GCC_PATCHES
	if test -d package/gcc/$(GCC_VERSION); then \
		$(APPLY_PATCHES) $(@D) package/gcc/$(GCC_VERSION) \*.patch || exit 1; \
	fi
endef
AOS_GCC_POST_PATCH_HOOKS += AOS_GCC_APPLY_GCC_PATCHES

# gcc must be configured and built outside its source tree.
AOS_GCC_SUBDIR = build

define AOS_GCC_CONFIGURE_SYMLINK
	mkdir -p $(@D)/build
	ln -sf ../configure $(@D)/build/configure
endef
AOS_GCC_POST_PATCH_HOOKS += AOS_GCC_CONFIGURE_SYMLINK

# Even when producing a compiler that runs elsewhere, gcc's build generates
# and then *executes* tools (genattrtab, gengtype, ...) on the build machine,
# so it needs a build-machine compiler as well as the cross one.
# MAKEINFO=missing suppresses the documentation build.
AOS_GCC_CONF_ENV = \
	MAKEINFO=missing \
	CC_FOR_BUILD="$(HOSTCC)" \
	CXX_FOR_BUILD="$(HOSTCXX)"

# --with-sysroot=/ versus --with-build-sysroot=$(STAGING_DIR) is the crux of
# the whole package. At build time the headers and libraries to compile
# against live in the staging sysroot on this machine; at run time, on the
# target, that same sysroot *is* the root filesystem. So the compiler is built
# against staging but records "/" as the place to look when it runs.
AOS_GCC_CONF_OPTS = \
	--target=$(GNU_TARGET_NAME) \
	--disable-bootstrap \
	--enable-languages=c,c++ \
	--with-sysroot=/ \
	--with-build-sysroot=$(STAGING_DIR) \
	--with-native-system-header-dir=/usr/include \
	--with-build-time-tools=$(HOST_DIR)/$(GNU_TARGET_NAME)/bin \
	--disable-multilib \
	--disable-libssp \
	--disable-nls \
	--enable-__cxa_atexit \
	--enable-threads \
	--enable-tls \
	--enable-lto \
	--enable-plugins \
	--with-gnu-ld \
	--without-zstd \
	--with-gmp=$(STAGING_DIR)/usr \
	--with-mpfr=$(STAGING_DIR)/usr \
	--with-mpc=$(STAGING_DIR)/usr \
	--with-pkgversion="AOS $(GCC_VERSION)" \
	--with-bugurl="https://gitlab.com/buildroot.org/buildroot/-/issues"

# Default the on-target compiler to the same ISA baseline as the rest of the
# system, so that code built on an AOS machine runs on every AOS machine.
ifneq ($(GCC_TARGET_ARCH),)
AOS_GCC_CONF_OPTS += --with-arch=$(GCC_TARGET_ARCH)
endif

ifeq ($(BR2_GCC_ENABLE_GRAPHITE),y)
AOS_GCC_DEPENDENCIES += isl
AOS_GCC_CONF_OPTS += --with-isl=$(STAGING_DIR)/usr
else
AOS_GCC_CONF_OPTS += --without-isl --without-cloog
endif

# Build and install the compiler proper only -- driver, cc1, cc1plus, lto1,
# collect2, the LTO plugin and gcc's own internal headers (stddef.h, stdarg.h
# and friends).
#
# A full "make" would additionally build libgcc, libstdc++ and the C++
# headers for the target. Those are already in the image: host-gcc-final built
# them from this same source, and post-build.sh copies the headers and link
# artefacts out of the staging sysroot. Building them again would be slow,
# and would risk shipping two subtly different copies of the same runtime.
define AOS_GCC_BUILD_CMDS
	$(TARGET_MAKE_ENV) $(MAKE) -C $(@D) all-gcc
endef

define AOS_GCC_INSTALL_TARGET_CMDS
	$(TARGET_MAKE_ENV) $(MAKE) -C $(@D) DESTDIR=$(TARGET_DIR) install-gcc
endef

# Nearly everything that looks for a C compiler looks for "cc" first --
# ./configure scripts, kbuild, and cargo's linker invocation among them.
define AOS_GCC_CC_SYMLINK
	ln -sf gcc $(TARGET_DIR)/usr/bin/cc
endef
AOS_GCC_POST_INSTALL_TARGET_HOOKS += AOS_GCC_CC_SYMLINK

$(eval $(autotools-package))
