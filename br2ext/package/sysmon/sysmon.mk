################################################################################
#
# sysmon
#
################################################################################

# A commit, not a tag -- see ade.mk. This one is v0.1.1.
SYSMON_VERSION = 03e5e5b665059a4a4ca53039385d28d66c06365f
SYSMON_SITE = ssh://git@github.com/Jaxilian/sysmon
SYSMON_SITE_METHOD = git
SYSMON_LICENSE = MIT

# For a build from a working tree through SYSMON_OVERRIDE_SRCDIR in
# local.mk; see ade.mk for both lines.
SYSMON_OVERRIDE_SRCDIR_RSYNC_EXCLUSIONS = --exclude=target
ifneq ($(SYSMON_OVERRIDE_SRCDIR),)
SYSMON_PRE_BUILD_HOOKS += AOS_CARGO_VENDOR
endif

# libwayland-client and libxkbcommon are linked; libvulkan is not, because
# ash opens it with dlopen at startup. It still has to be on the image, so
# vulkan-loader is a dependency here even though nothing refers to it at
# link time. host-pkgconf is how the -sys crates find the first two. tgn,
# and awin through it, come from the aos-sdk repository at a tag, named in
# Cargo.toml, and are vendored with the rest of the crates.
SYSMON_DEPENDENCIES = \
	host-pkgconf \
	libxkbcommon \
	vulkan-loader \
	wayland

# Copy the binary out rather than letting pkg-cargo.mk run "cargo install".
# That would compile the whole tree a second time into a target directory of
# its own, which for this dependency graph is minutes of Vulkan and image
# crates rebuilt to produce a file the build step already made.
SYSMON_PROFILE = $(if $(BR2_ENABLE_DEBUG),debug,release)

define SYSMON_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 \
		$(@D)/target/$(RUSTC_TARGET_NAME)/$(SYSMON_PROFILE)/sysmon \
		$(TARGET_DIR)/usr/bin/sysmon
	$(INSTALL) -D -m 0644 $(SYSMON_PKGDIR)/org.aos.Sysmon.desktop \
		$(TARGET_DIR)/usr/share/applications/org.aos.Sysmon.desktop
endef

$(eval $(cargo-package))
