################################################################################
#
# aos-store
#
################################################################################

# A commit, not a tag -- see ade.mk. This one is v0.1.5.
AOS_STORE_VERSION = b5f30ff6d227884d2d4785a92a4acd0c4e1f9a58
AOS_STORE_SITE = ssh://git@github.com/Jaxilian/store
AOS_STORE_SITE_METHOD = git
AOS_STORE_LICENSE = MIT

# For a build from a working tree through AOS_STORE_OVERRIDE_SRCDIR in
# local.mk; see ade.mk for both lines.
AOS_STORE_OVERRIDE_SRCDIR_RSYNC_EXCLUSIONS = --exclude=target
ifneq ($(AOS_STORE_OVERRIDE_SRCDIR),)
AOS_STORE_PRE_BUILD_HOOKS += AOS_CARGO_VENDOR
endif

# libwayland-client and libxkbcommon are linked; libvulkan is not, because
# ash opens it with dlopen at startup. It still has to be on the image, so
# vulkan-loader is a dependency here even though nothing refers to it at
# link time. host-pkgconf is how the -sys crates find the first two. tgn,
# and awin through it, come from the aos-sdk repository at a tag, named in
# Cargo.toml, and are vendored with the rest of the crates.
AOS_STORE_DEPENDENCIES = \
	host-pkgconf \
	libxkbcommon \
	vulkan-loader \
	wayland

# Copy the binary out rather than letting pkg-cargo.mk run "cargo install".
# That would compile the whole tree a second time into a target directory of
# its own, which for this dependency graph is minutes of Vulkan and image
# crates rebuilt to produce a file the build step already made.
AOS_STORE_PROFILE = $(if $(BR2_ENABLE_DEBUG),debug,release)

define AOS_STORE_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 \
		$(@D)/target/$(RUSTC_TARGET_NAME)/$(AOS_STORE_PROFILE)/aos-store \
		$(TARGET_DIR)/usr/bin/aos-store
	$(INSTALL) -D -m 0644 $(AOS_STORE_PKGDIR)/org.aos.Store.desktop \
		$(TARGET_DIR)/usr/share/applications/org.aos.Store.desktop
	$(INSTALL) -D -m 0644 $(@D)/res/store.svg \
		$(TARGET_DIR)/usr/share/icons/hicolor/scalable/apps/org.aos.Store.svg
endef

# Ours, not a product of the same name in NVD ("terminal" matched Apple's).
AOS_STORE_CPE_ID_VENDOR = jaxilian

$(eval $(cargo-package))
