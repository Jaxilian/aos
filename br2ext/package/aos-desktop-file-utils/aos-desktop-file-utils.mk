################################################################################
#
# aos-desktop-file-utils
#
################################################################################

# Buildroot's own desktop-file-utils package is host-only (it uses the
# tools while assembling an image); this is the same release built for
# the target, under a name of its own since a package cannot be both.
AOS_DESKTOP_FILE_UTILS_VERSION = 0.26
AOS_DESKTOP_FILE_UTILS_SOURCE = desktop-file-utils-$(AOS_DESKTOP_FILE_UTILS_VERSION).tar.xz
AOS_DESKTOP_FILE_UTILS_SITE = https://www.freedesktop.org/software/desktop-file-utils/releases
AOS_DESKTOP_FILE_UTILS_LICENSE = GPL-2.0+
AOS_DESKTOP_FILE_UTILS_LICENSE_FILES = COPYING
AOS_DESKTOP_FILE_UTILS_DEPENDENCIES = host-pkgconf libglib2

$(eval $(meson-package))
