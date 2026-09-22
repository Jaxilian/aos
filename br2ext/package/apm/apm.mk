################################################################################
#
# apm
#
################################################################################

# A commit, not a tag -- see ade.mk. This one is v0.1.0.
APM_VERSION = 66cd84c3fa62fac1592808918a50132abccfd510
APM_SITE = ssh://git@github.com/Jaxilian/apm
APM_SITE_METHOD = git
APM_LICENSE = MIT

# For a build from a working tree through APM_OVERRIDE_SRCDIR in local.mk;
# see ade.mk for both lines.
APM_OVERRIDE_SRCDIR_RSYNC_EXCLUSIONS = --exclude=target
ifneq ($(APM_OVERRIDE_SRCDIR),)
APM_PRE_BUILD_HOOKS += AOS_CARGO_VENDOR
endif

# curl and tar are runtime dependencies, not link ones: apm shells out to
# both. Listing them here only orders the build; Config.in selects them.
APM_DEPENDENCIES = host-pkgconf

# The workspace holds the library and the binary; only the binary ships.
APM_CARGO_BUILD_OPTS = --package apm

# Hand-written install because the workspace root is a virtual manifest,
# which "cargo install --path ./" refuses (see ade.mk).
APM_PROFILE = $(if $(BR2_ENABLE_DEBUG),debug,release)

define APM_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 \
		$(@D)/target/$(RUSTC_TARGET_NAME)/$(APM_PROFILE)/apm \
		$(TARGET_DIR)/usr/bin/apm
endef

$(eval $(cargo-package))
