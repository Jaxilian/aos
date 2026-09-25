################################################################################
#
# terminal
#
################################################################################

# A commit, not a tag -- see ade.mk. This one is v0.1.2.
TERMINAL_VERSION = ed677c26778f5a2da1f41e8c5bf2a0c4f1384c21
TERMINAL_SITE = ssh://git@github.com/Jaxilian/terminal
TERMINAL_SITE_METHOD = git
TERMINAL_LICENSE = MIT, OFL-1.1 (Liberation Mono)
TERMINAL_LICENSE_FILES = res/fonts/liberation-mono.ttf

# For a build from a working tree through TERMINAL_OVERRIDE_SRCDIR in
# local.mk; see ade.mk for both lines.
TERMINAL_OVERRIDE_SRCDIR_RSYNC_EXCLUSIONS = --exclude=target
ifneq ($(TERMINAL_OVERRIDE_SRCDIR),)
TERMINAL_PRE_BUILD_HOOKS += AOS_CARGO_VENDOR
endif

# libwayland-client and libxkbcommon are linked; libvulkan is not, because
# ash opens it with dlopen at startup. It still has to be on the image, so
# vulkan-loader is a dependency here even though nothing refers to it at
# link time. host-pkgconf is how the -sys crates find the first two. tgn,
# and awin through it, come from the aos-sdk repository at a tag, named in
# Cargo.toml, and are vendored with the rest of the crates.
TERMINAL_DEPENDENCIES = \
	host-pkgconf \
	libxkbcommon \
	vulkan-loader \
	wayland

# Copy the binary out rather than letting pkg-cargo.mk run "cargo install".
# That would compile the whole tree a second time into a target directory of
# its own, which for this dependency graph is minutes of Vulkan and image
# crates rebuilt to produce a file the build step already made.
TERMINAL_PROFILE = $(if $(BR2_ENABLE_DEBUG),debug,release)

define TERMINAL_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 \
		$(@D)/target/$(RUSTC_TARGET_NAME)/$(TERMINAL_PROFILE)/terminal \
		$(TARGET_DIR)/usr/bin/terminal
	$(INSTALL) -D -m 0644 $(TERMINAL_PKGDIR)/org.aos.Terminal.desktop \
		$(TARGET_DIR)/usr/share/applications/org.aos.Terminal.desktop
endef

$(eval $(cargo-package))
