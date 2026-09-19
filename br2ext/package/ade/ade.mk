################################################################################
#
# ade
#
################################################################################

ADE_VERSION = 0.1.0
ADE_SITE = $(call qstrip,$(BR2_PACKAGE_ADE_PATH))
ADE_SITE_METHOD = local
ADE_LICENSE = MIT

# Do not drag the developer's own target/ directory into the build. A local
# site is rsynced verbatim, and cargo's host output lands in the same
# x86_64-unknown-linux-gnu directory the cross build writes to -- so a tree
# that has been built with the host toolchain would hand Buildroot fresh-
# looking artifacts linked against the host glibc. Excluding it also keeps
# a couple of gigabytes out of every rsync.
ADE_OVERRIDE_SRCDIR_RSYNC_EXCLUSIONS = --exclude=target

# libseat comes from seatd, libgbm and libEGL from mesa3d. host-pkgconf is
# what the -sys crates use to find all of them. vulkan-loader is for the
# shell: awin's ash dlopens libvulkan at runtime, so it is a runtime rather
# than a link dependency, but it must be on the image or every shell surface
# fails at startup.
ADE_DEPENDENCIES = \
	host-pkgconf \
	libdrm \
	libinput \
	libxkbcommon \
	mesa3d \
	seatd \
	udev \
	vulkan-loader \
	wayland \
	wayland-protocols

# Vendor the crate dependencies into the build directory.
#
# pkg-cargo.mk passes --offline --locked to every cargo invocation, and
# fills the vendor directory in its download step. A local site has no
# download step, so nothing is vendored and an offline build fails on the
# first dependency. Doing it here, against the sources Buildroot has already
# copied into $(@D), gets the same result.
#
# The config file is removed first and then written, not appended to.
# Appending looks harmless until the second build: "make ade-rebuild" runs
# this hook again, the [source.crates-io] block lands in the file twice, and
# cargo stops with "duplicate key" -- and it stops in this very hook, since
# cargo reads the config before vendoring, so the build cannot recover on
# its own once that has happened. Nothing else writes this file: Buildroot
# would have, in the download step a local site does not have, which is why
# the hook exists at all.
#
# This needs network access once per build. It is the cost of tracking a
# working tree instead of a tagged release; a git ADE_SITE would let
# Buildroot's own vendoring handle it and would build fully offline.
define ADE_VENDOR
	rm -f $(@D)/.cargo/config.toml
	cd $(@D) && \
	CARGO_HOME=$(BR_CARGO_HOME) \
	$(HOST_DIR)/bin/cargo vendor --locked --versioned-dirs VENDOR \
		>$(@D)/.cargo-vendor-config
	mkdir -p $(@D)/.cargo
	cp -f $(@D)/.cargo-vendor-config $(@D)/.cargo/config.toml
endef
ADE_PRE_BUILD_HOOKS += ADE_VENDOR

# The compositor and the shell. Both are workspace members; nothing else in
# the workspace is a binary.
#
# ade-shell depends on awin and tgn by absolute path into the developer's
# Rust/ tree, which cargo vendor does not vendor, so this only builds on a
# host where those checkouts exist. Same situation as every awin app.
ADE_CARGO_BUILD_OPTS = --package ade-comp --package ade-shell

# ...which is also why the install step is written out here rather than left
# to pkg-cargo.mk. That one runs "cargo install --path ./", and ./ is a
# virtual workspace manifest, which cargo install refuses. Its --path cannot
# be pointed at comp/ either: a second --path is an error, not an override.
# Copying the binary out of the build tree is what cargo install would have
# done with it in any case.
ADE_PROFILE = $(if $(BR2_ENABLE_DEBUG),debug,release)

define ADE_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 \
		$(@D)/target/$(RUSTC_TARGET_NAME)/$(ADE_PROFILE)/ade-comp \
		$(TARGET_DIR)/usr/bin/ade-comp
	$(INSTALL) -D -m 0755 \
		$(@D)/target/$(RUSTC_TARGET_NAME)/$(ADE_PROFILE)/ade-shell \
		$(TARGET_DIR)/usr/bin/ade-shell
endef

define ADE_INSTALL_INIT_SYSTEMD
	$(INSTALL) -D -m 0644 $(@D)/dist/ade.service \
		$(TARGET_DIR)/usr/lib/systemd/system/ade.service
	$(INSTALL) -D -m 0644 $(@D)/dist/ade.environment \
		$(TARGET_DIR)/etc/ade/environment
	$(INSTALL) -d $(TARGET_DIR)/usr/lib/systemd/system/multi-user.target.wants
	ln -sf ../ade.service \
		$(TARGET_DIR)/usr/lib/systemd/system/multi-user.target.wants/ade.service
endef

$(eval $(cargo-package))
