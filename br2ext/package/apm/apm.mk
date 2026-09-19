################################################################################
#
# apm
#
################################################################################

APM_VERSION = 0.1.0
APM_SITE = $(call qstrip,$(BR2_PACKAGE_APM_PATH))
APM_SITE_METHOD = local
APM_LICENSE = MIT

# As for ade: the developer's own target/ must not be rsynced in, or a tree
# built with the host toolchain hands Buildroot artifacts linked against the
# host glibc.
APM_OVERRIDE_SRCDIR_RSYNC_EXCLUSIONS = --exclude=target

# curl and tar are runtime dependencies, not link ones: apm shells out to
# both. Listing them here only orders the build; Config.in selects them.
APM_DEPENDENCIES = host-pkgconf

# Vendor the crates into the build directory. Same reason and same shape
# as ade.mk: a local site has no download step, and pkg-cargo.mk builds
# --offline --locked. See the comment there for why the config file is
# rewritten rather than appended to.
define APM_VENDOR
	rm -f $(@D)/.cargo/config.toml
	cd $(@D) && \
	CARGO_HOME=$(BR_CARGO_HOME) \
	$(HOST_DIR)/bin/cargo vendor --locked --versioned-dirs VENDOR \
		>$(@D)/.cargo-vendor-config
	mkdir -p $(@D)/.cargo
	cp -f $(@D)/.cargo-vendor-config $(@D)/.cargo/config.toml
endef
APM_PRE_BUILD_HOOKS += APM_VENDOR

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
