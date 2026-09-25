################################################################################
#
# settings
#
################################################################################

# A commit, not a tag -- see ade.mk. This one is v0.1.0.
SETTINGS_VERSION = 0b45fed1a9619b6d791261e904d2f2d261b312fa
SETTINGS_SITE = ssh://git@github.com/Jaxilian/settings
SETTINGS_SITE_METHOD = git
SETTINGS_LICENSE = MIT

# For a build from a working tree through SETTINGS_OVERRIDE_SRCDIR in
# local.mk; see ade.mk for both lines.
SETTINGS_OVERRIDE_SRCDIR_RSYNC_EXCLUSIONS = --exclude=target
ifneq ($(SETTINGS_OVERRIDE_SRCDIR),)
SETTINGS_PRE_BUILD_HOOKS += AOS_CARGO_VENDOR
endif

# libwayland-client and libxkbcommon are linked; libvulkan is not, because
# ash opens it with dlopen at startup. It still has to be on the image, so
# vulkan-loader is a dependency here even though nothing refers to it at
# link time. host-pkgconf is how the -sys crates find the first two. tgn,
# and awin through it, come from the aos-sdk repository at a tag, named in
# Cargo.toml, and are vendored with the rest of the crates.
SETTINGS_DEPENDENCIES = \
	host-pkgconf \
	libxkbcommon \
	vulkan-loader \
	wayland

# Copy the binary out rather than letting pkg-cargo.mk run "cargo install".
# That would compile the whole tree a second time into a target directory of
# its own, which for this dependency graph is minutes of Vulkan and image
# crates rebuilt to produce a file the build step already made.
SETTINGS_PROFILE = $(if $(BR2_ENABLE_DEBUG),debug,release)

define SETTINGS_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 \
		$(@D)/target/$(RUSTC_TARGET_NAME)/$(SETTINGS_PROFILE)/settings \
		$(TARGET_DIR)/usr/bin/settings
	$(INSTALL) -D -m 0644 $(SETTINGS_PKGDIR)/org.aos.Settings.desktop \
		$(TARGET_DIR)/usr/share/applications/org.aos.Settings.desktop
endef

$(eval $(cargo-package))
