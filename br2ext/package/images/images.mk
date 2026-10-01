################################################################################
#
# images
#
################################################################################

# A commit, not a tag -- see ade.mk. This one is v0.1.4.
IMAGES_VERSION = a619cd6fb35aadf7b03fd0df3d5988fdff47f816
IMAGES_SITE = ssh://git@github.com/Jaxilian/images
IMAGES_SITE_METHOD = git
IMAGES_LICENSE = MIT

# For a build from a working tree through IMAGES_OVERRIDE_SRCDIR in
# local.mk; see ade.mk for both lines.
IMAGES_OVERRIDE_SRCDIR_RSYNC_EXCLUSIONS = --exclude=target
ifneq ($(IMAGES_OVERRIDE_SRCDIR),)
IMAGES_PRE_BUILD_HOOKS += AOS_CARGO_VENDOR
endif

# libwayland-client and libxkbcommon are linked; libvulkan is not, because
# ash opens it with dlopen at startup. It still has to be on the image, so
# vulkan-loader is a dependency here even though nothing refers to it at
# link time. host-pkgconf is how the -sys crates find the first two. tgn,
# and awin through it, come from the aos-sdk repository at a tag, named in
# Cargo.toml, and are vendored with the rest of the crates.
IMAGES_DEPENDENCIES = \
	host-pkgconf \
	libxkbcommon \
	vulkan-loader \
	wayland

# Copy the binary out rather than letting pkg-cargo.mk run "cargo install".
# That would compile the whole tree a second time into a target directory of
# its own, which for this dependency graph is minutes of Vulkan and image
# crates rebuilt to produce a file the build step already made.
IMAGES_PROFILE = $(if $(BR2_ENABLE_DEBUG),debug,release)

define IMAGES_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 \
		$(@D)/target/$(RUSTC_TARGET_NAME)/$(IMAGES_PROFILE)/images \
		$(TARGET_DIR)/usr/bin/images
	$(INSTALL) -D -m 0644 $(IMAGES_PKGDIR)/org.aos.Images.desktop \
		$(TARGET_DIR)/usr/share/applications/org.aos.Images.desktop
	$(INSTALL) -D -m 0644 $(@D)/res/images.svg \
		$(TARGET_DIR)/usr/share/icons/hicolor/scalable/apps/org.aos.Images.svg
endef

# Ours, not a product of the same name in NVD ("terminal" matched Apple's).
IMAGES_CPE_ID_VENDOR = jaxilian

$(eval $(cargo-package))
