################################################################################
#
# libnsl
#
################################################################################

LIBNSL_VERSION = 2.0.1
LIBNSL_SOURCE = libnsl-$(LIBNSL_VERSION).tar.xz
LIBNSL_SITE = https://github.com/thkukuk/libnsl/releases/download/v$(LIBNSL_VERSION)
LIBNSL_LICENSE = LGPL-2.1+
LIBNSL_LICENSE_FILES = COPYING
LIBNSL_INSTALL_STAGING = YES
LIBNSL_DEPENDENCIES = host-pkgconf libtirpc

$(eval $(autotools-package))
