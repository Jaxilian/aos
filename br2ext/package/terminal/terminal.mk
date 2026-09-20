################################################################################
#
# terminal
#
################################################################################

TERMINAL_VERSION = 0.1.0
# The path symbol exists only while the package is enabled, and Buildroot
# checks a local site for every configuration it parses, on or off; the
# fallback is never used, it only lets a configuration without this
# package -- the packages tree -- parse.
TERMINAL_SITE = $(or $(call qstrip,$(BR2_PACKAGE_TERMINAL_PATH)),/nonexistent)
TERMINAL_SITE_METHOD = local
TERMINAL_LICENSE = MIT, OFL-1.1 (Liberation Mono)
TERMINAL_LICENSE_FILES = res/fonts/liberation-mono.ttf

# Keep the developer's own target/ out of the rsync -- see the same note in
# package/ade/ade.mk. The host and the cross build share the
# x86_64-unknown-linux-gnu output directory, so host artifacts copied in
# here would be picked up as if they were cross-built.
TERMINAL_OVERRIDE_SRCDIR_RSYNC_EXCLUSIONS = --exclude=target

# The same three as notepad, for the same reasons: libwayland-client and
# libxkbcommon are linked, libvulkan is opened with dlopen by ash at startup
# and so has to be on the image without appearing at link time. The pty and
# termios calls come from rustix, which is all syscalls and needs nothing
# here.
TERMINAL_DEPENDENCIES = \
	host-pkgconf \
	libxkbcommon \
	vulkan-loader \
	wayland

# Vendor the crate dependencies into the build directory. pkg-cargo.mk
# passes --offline --locked and fills the vendor directory in its download
# step, which a local site does not have -- so without this the build stops
# on the first dependency. See package/ade/ade.mk for why the config file is
# rewritten rather than appended to.
define TERMINAL_VENDOR
	rm -f $(@D)/.cargo/config.toml
	cd $(@D) && \
	CARGO_HOME=$(BR_CARGO_HOME) \
	$(HOST_DIR)/bin/cargo vendor --locked --versioned-dirs VENDOR \
		>$(@D)/.cargo-vendor-config
	mkdir -p $(@D)/.cargo
	cp -f $(@D)/.cargo-vendor-config $(@D)/.cargo/config.toml
endef
TERMINAL_PRE_BUILD_HOOKS += TERMINAL_VENDOR

# Copy the binary out rather than letting pkg-cargo.mk run "cargo install",
# which would compile the whole tree a second time into a target directory
# of its own to produce a file the build step already made.
TERMINAL_PROFILE = $(if $(BR2_ENABLE_DEBUG),debug,release)

define TERMINAL_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 \
		$(@D)/target/$(RUSTC_TARGET_NAME)/$(TERMINAL_PROFILE)/terminal \
		$(TARGET_DIR)/usr/bin/terminal
	$(INSTALL) -D -m 0644 $(TERMINAL_PKGDIR)/org.aos.Terminal.desktop \
		$(TARGET_DIR)/usr/share/applications/org.aos.Terminal.desktop
endef

$(eval $(cargo-package))
