################################################################################
#
# files
#
################################################################################

# A commit, not a tag -- see ade.mk. This one is v0.1.1.
FILES_VERSION = 3dde89061f45fa393ab20edec19eecb0382fc091
FILES_SITE = ssh://git@github.com/Jaxilian/files
FILES_SITE_METHOD = git
FILES_LICENSE = MIT

# For a build from a working tree through FILES_OVERRIDE_SRCDIR in
# local.mk; see ade.mk for both lines.
FILES_OVERRIDE_SRCDIR_RSYNC_EXCLUSIONS = --exclude=target
ifneq ($(FILES_OVERRIDE_SRCDIR),)
FILES_PRE_BUILD_HOOKS += AOS_CARGO_VENDOR
endif

# libwayland-client and libxkbcommon are linked; libvulkan is not, because
# ash opens it with dlopen at startup. It still has to be on the image, so
# vulkan-loader is a dependency here even though nothing refers to it at
# link time. host-pkgconf is how the -sys crates find the first two. awin
# and tgn come from the aos-sdk repository at a tag, named in Cargo.toml,
# and are vendored with the rest of the crates.
FILES_DEPENDENCIES = \
	host-pkgconf \
	libxkbcommon \
	vulkan-loader \
	wayland

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
