################################################################################
#
# devmapper-udev
#
################################################################################

# The same tarball as package/lvm2 (shared download), the same configure
# line, plus --enable-udev_sync; see Config.in for why lvm2 itself cannot
# have it. Only the device-mapper half is built and installed (the library,
# dmsetup, the udev rules), over the files lvm2 put in the target. A later
# "make lvm2-reinstall" puts the old library back; run
# "make devmapper-udev-reinstall" after it.
DEVMAPPER_UDEV_VERSION = $(LVM2_VERSION)
DEVMAPPER_UDEV_SOURCE = LVM2.$(DEVMAPPER_UDEV_VERSION).tgz
DEVMAPPER_UDEV_SITE = $(LVM2_SITE)
DEVMAPPER_UDEV_DL_SUBDIR = lvm2
DEVMAPPER_UDEV_LICENSE = GPL-2.0, LGPL-2.1
DEVMAPPER_UDEV_LICENSE_FILES = COPYING COPYING.LIB
DEVMAPPER_UDEV_DEPENDENCIES = host-pkgconf lvm2 udev
DEVMAPPER_UDEV_MAKE = $(MAKE1)
DEVMAPPER_UDEV_MAKE_ENV = $(TARGET_CONFIGURE_OPTS)
DEVMAPPER_UDEV_MAKE_OPTS = device-mapper
DEVMAPPER_UDEV_INSTALL_TARGET_OPTS = DESTDIR=$(TARGET_DIR) install_device-mapper

DEVMAPPER_UDEV_CONF_OPTS = \
	--enable-write_install \
	--enable-pkgconfig \
	--enable-cmdlib \
	--enable-dmeventd \
	--disable-nls \
	--with-symvers=no \
	--disable-readline \
	--disable-selinux \
	--enable-udev_rules \
	--enable-udev_sync

ifeq ($(BR2_TOOLCHAIN_SUPPORTS_PIE),)
DEVMAPPER_UDEV_CONF_ENV += ac_cv_flag_HAVE_PIE=no
endif

$(eval $(autotools-package))
