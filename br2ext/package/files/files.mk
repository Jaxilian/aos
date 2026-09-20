################################################################################
#
# files
#
################################################################################

FILES_VERSION = 0.1.0
# The path symbol exists only while the package is enabled, and Buildroot
# checks a local site for every configuration it parses, on or off; the
# fallback is never used, it only lets a configuration without this
# package -- the packages tree -- parse.
FILES_SITE = $(or $(call qstrip,$(BR2_PACKAGE_FILES_PATH)),/nonexistent)
# Kconfig only writes the path once the package is on, and Buildroot parses
# every .mk regardless, so a tree with files switched off must still make.
ifeq ($(FILES_SITE),)
FILES_SITE = $(BR2_EXTERNAL_AOS_PATH)/../../../Rust/files
endif
FILES_SITE_METHOD = local
FILES_LICENSE = MIT

# Keep the developer's own target/ out of the rsync -- see the same note in
# package/ade/ade.mk. The host and the cross build share the
# x86_64-unknown-linux-gnu output directory, so host artifacts copied in
# here would be picked up as if they were cross-built.
FILES_OVERRIDE_SRCDIR_RSYNC_EXCLUSIONS = --exclude=target

# libwayland-client and libxkbcommon are linked; libvulkan is not, because
# ash opens it with dlopen at startup. It still has to be on the image, so
# vulkan-loader is a dependency here even though nothing refers to it at
# link time. host-pkgconf is how the -sys crates find the first two.
FILES_DEPENDENCIES = \
	host-pkgconf \
	libxkbcommon \
	vulkan-loader \
	wayland

# Vendor the crate dependencies into the build directory. pkg-cargo.mk
# passes --offline --locked and fills the vendor directory in its download
# step, which a local site does not have -- so without this the build stops
# on the first dependency. See package/ade/ade.mk for why the config file is
# rewritten rather than appended to.
#
# The awin and tgn path dependencies are not vendored and do not need to be:
# cargo reads them from the absolute paths in files' Cargo.toml, which is
# outside this directory entirely. Their own registry dependencies are in
# files' dependency graph, so they do get vendored here.
define FILES_VENDOR
	rm -f $(@D)/.cargo/config.toml
	cd $(@D) && \
	CARGO_HOME=$(BR_CARGO_HOME) \
	$(HOST_DIR)/bin/cargo vendor --locked --versioned-dirs VENDOR \
		>$(@D)/.cargo-vendor-config
	mkdir -p $(@D)/.cargo
	cp -f $(@D)/.cargo-vendor-config $(@D)/.cargo/config.toml
endef
FILES_PRE_BUILD_HOOKS += FILES_VENDOR

# Copy the binary out rather than letting pkg-cargo.mk run "cargo install".
# That would compile the whole tree a second time into a target directory of
# its own, which for this dependency graph is minutes of Vulkan and image
# crates rebuilt to produce a file the build step already made.
FILES_PROFILE = $(if $(BR2_ENABLE_DEBUG),debug,release)

define FILES_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 \
		$(@D)/target/$(RUSTC_TARGET_NAME)/$(FILES_PROFILE)/files \
		$(TARGET_DIR)/usr/bin/files
	$(INSTALL) -D -m 0644 $(FILES_PKGDIR)/org.aos.Files.desktop \
		$(TARGET_DIR)/usr/share/applications/org.aos.Files.desktop
endef

$(eval $(cargo-package))
