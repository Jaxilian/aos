################################################################################
#
# notepad
#
################################################################################

NOTEPAD_VERSION = 0.1.0
NOTEPAD_SITE = $(call qstrip,$(BR2_PACKAGE_NOTEPAD_PATH))
NOTEPAD_SITE_METHOD = local
NOTEPAD_LICENSE = MIT

# Keep the developer's own target/ out of the rsync -- see the same note in
# package/ade/ade.mk. The host and the cross build share the
# x86_64-unknown-linux-gnu output directory, so host artifacts copied in
# here would be picked up as if they were cross-built.
NOTEPAD_OVERRIDE_SRCDIR_RSYNC_EXCLUSIONS = --exclude=target

# libwayland-client and libxkbcommon are linked; libvulkan is not, because
# ash opens it with dlopen at startup. It still has to be on the image, so
# vulkan-loader is a dependency here even though nothing refers to it at
# link time. host-pkgconf is how the -sys crates find the first two.
NOTEPAD_DEPENDENCIES = \
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
# cargo reads them from the absolute paths in notepad's Cargo.toml, which is
# outside this directory entirely. Their own registry dependencies are in
# notepad's dependency graph, so they do get vendored here.
define NOTEPAD_VENDOR
	rm -f $(@D)/.cargo/config.toml
	cd $(@D) && \
	CARGO_HOME=$(BR_CARGO_HOME) \
	$(HOST_DIR)/bin/cargo vendor --locked --versioned-dirs VENDOR \
		>$(@D)/.cargo-vendor-config
	mkdir -p $(@D)/.cargo
	cp -f $(@D)/.cargo-vendor-config $(@D)/.cargo/config.toml
endef
NOTEPAD_PRE_BUILD_HOOKS += NOTEPAD_VENDOR

# Copy the binary out rather than letting pkg-cargo.mk run "cargo install".
# That would compile the whole tree a second time into a target directory of
# its own, which for this dependency graph is minutes of Vulkan and image
# crates rebuilt to produce a file the build step already made.
NOTEPAD_PROFILE = $(if $(BR2_ENABLE_DEBUG),debug,release)

define NOTEPAD_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 \
		$(@D)/target/$(RUSTC_TARGET_NAME)/$(NOTEPAD_PROFILE)/notepad \
		$(TARGET_DIR)/usr/bin/notepad
endef

$(eval $(cargo-package))
