################################################################################
#
# notepad
#
################################################################################

# A commit, not a tag -- see ade.mk. This one is v0.1.3.
NOTEPAD_VERSION = ffffd6ed6a369967313160eb9c60cd3ab239a23c
NOTEPAD_SITE = ssh://git@github.com/Jaxilian/notepad
NOTEPAD_SITE_METHOD = git
NOTEPAD_LICENSE = MIT

# For a build from a working tree through NOTEPAD_OVERRIDE_SRCDIR in
# local.mk; see ade.mk for both lines.
NOTEPAD_OVERRIDE_SRCDIR_RSYNC_EXCLUSIONS = --exclude=target
ifneq ($(NOTEPAD_OVERRIDE_SRCDIR),)
NOTEPAD_PRE_BUILD_HOOKS += AOS_CARGO_VENDOR
endif

# libwayland-client and libxkbcommon are linked; libvulkan is not, because
# ash opens it with dlopen at startup. It still has to be on the image, so
# vulkan-loader is a dependency here even though nothing refers to it at
# link time. host-pkgconf is how the -sys crates find the first two. tgn,
# and awin through it, come from the aos-sdk repository at a tag, named in
# Cargo.toml, and are vendored with the rest of the crates.
NOTEPAD_DEPENDENCIES = \
	host-pkgconf \
	libxkbcommon \
	vulkan-loader \
	wayland

# Copy the binary out rather than letting pkg-cargo.mk run "cargo install".
# That would compile the whole tree a second time into a target directory of
# its own, which for this dependency graph is minutes of Vulkan and image
# crates rebuilt to produce a file the build step already made.
NOTEPAD_PROFILE = $(if $(BR2_ENABLE_DEBUG),debug,release)

define NOTEPAD_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 \
		$(@D)/target/$(RUSTC_TARGET_NAME)/$(NOTEPAD_PROFILE)/notepad \
		$(TARGET_DIR)/usr/bin/notepad
	$(INSTALL) -D -m 0644 $(NOTEPAD_PKGDIR)/org.aos.Notepad.desktop \
		$(TARGET_DIR)/usr/share/applications/org.aos.Notepad.desktop
endef

$(eval $(cargo-package))
