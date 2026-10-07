################################################################################
#
# ade-greeter
#
################################################################################

# A commit, not a tag -- see ade.mk.
ADE_GREETER_VERSION = dcec2a08ddd12a12b3ff7e5323d37b18d49f485d
ADE_GREETER_SITE = ssh://git@github.com/Jaxilian/greeter
ADE_GREETER_SITE_METHOD = git
ADE_GREETER_LICENSE = MIT
ADE_GREETER_OVERRIDE_SRCDIR_RSYNC_EXCLUSIONS = --exclude=target
ifneq ($(ADE_GREETER_OVERRIDE_SRCDIR),)
ADE_GREETER_PRE_BUILD_HOOKS += AOS_CARGO_VENDOR
endif
ADE_GREETER_DEPENDENCIES = \
	host-pkgconf \
	libxkbcommon \
	vulkan-loader \
	wayland
ADE_GREETER_PROFILE = $(if $(BR2_ENABLE_DEBUG),debug,release)
define ADE_GREETER_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 \
		$(@D)/target/$(RUSTC_TARGET_NAME)/$(ADE_GREETER_PROFILE)/ade-greeter \
		$(TARGET_DIR)/usr/bin/ade-greeter
endef
ADE_GREETER_CPE_ID_VENDOR = jaxilian

$(eval $(cargo-package))
