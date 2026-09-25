################################################################################
#
# ade
#
################################################################################

# A commit, not a tag: a tag can be moved, and the point of pinning is that
# this file and the sources it names cannot drift apart. This one is v0.1.12.
# Over ssh, because the repositories are private: whoever builds needs a
# key GitHub knows. The applications' Cargo.toml fetch the SDK the same way.
ADE_VERSION = 0d7511993e4010c02dd2fba865ccf01e3d333940
ADE_SITE = ssh://git@github.com/Jaxilian/ade
ADE_SITE_METHOD = git
ADE_LICENSE = MIT

# For a build from a working tree through ADE_OVERRIDE_SRCDIR in local.mk:
# keep the developer's target/ out of the rsync. cargo's host output lands
# in the same x86_64-unknown-linux-gnu directory the cross build writes to,
# so a tree built with the host toolchain would hand Buildroot fresh-looking
# artifacts linked against the host glibc. It also keeps a couple of
# gigabytes out of every rsync. And vendor the crates at build time, since
# an override has no download step to do it in -- see external.mk.
ADE_OVERRIDE_SRCDIR_RSYNC_EXCLUSIONS = --exclude=target
ifneq ($(ADE_OVERRIDE_SRCDIR),)
ADE_PRE_BUILD_HOOKS += AOS_CARGO_VENDOR
endif

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

# The compositor, the shell and the lock screen. All three are workspace
# members; nothing else in the workspace is a binary. The shell's and the
# locker's awin and tgn come from the aos-sdk repository at a tag, named in
# their Cargo.toml, and are vendored with the rest of the crates.
ADE_CARGO_BUILD_OPTS = --package ade-comp --package ade-shell --package ade-lock

# The install step is written out here rather than left to pkg-cargo.mk.
# That one runs "cargo install --path ./", and ./ is a virtual workspace
# manifest, which cargo install refuses. Its --path cannot be pointed at
# comp/ either: a second --path is an error, not an override. Copying the
# binary out of the build tree is what cargo install would have done with
# it in any case.
ADE_PROFILE = $(if $(BR2_ENABLE_DEBUG),debug,release)

define ADE_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 \
		$(@D)/target/$(RUSTC_TARGET_NAME)/$(ADE_PROFILE)/ade-comp \
		$(TARGET_DIR)/usr/bin/ade-comp
	$(INSTALL) -D -m 0755 \
		$(@D)/target/$(RUSTC_TARGET_NAME)/$(ADE_PROFILE)/ade-shell \
		$(TARGET_DIR)/usr/bin/ade-shell
	$(INSTALL) -D -m 0755 \
		$(@D)/target/$(RUSTC_TARGET_NAME)/$(ADE_PROFILE)/ade-lock \
		$(TARGET_DIR)/usr/bin/ade-lock
	$(INSTALL) -D -m 0644 $(@D)/dist/ade-lock.pam \
		$(TARGET_DIR)/etc/pam.d/ade-lock
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
