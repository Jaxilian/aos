################################################################################
#
# greetd
#
################################################################################

# Upstream, at a release tag; the Cargo workspace builds the daemon and
# agreety (a text greeter, for a serial console). ade-greeter is ours
# (package/ade-greeter) and speaks greetd's socket (greetd-ipc(7)).
GREETD_VERSION = 0.10.3
GREETD_SITE = https://git.sr.ht/~kennylevinsen/greetd
GREETD_SITE_METHOD = git
GREETD_LICENSE = GPL-3.0
GREETD_LICENSE_FILES = LICENSE
GREETD_DEPENDENCIES = host-pkgconf linux-pam
GREETD_CARGO_BUILD_OPTS = -p greetd -p agreety
GREETD_PROFILE = $(if $(BR2_ENABLE_DEBUG),debug,release)

# The daemon, the text greeter, the service (upstream's, without an
# install section: the preset in the overlay enables it where it should
# run), and AOS's configuration and PAM service from the overlay.
define GREETD_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 $(@D)/target/$(RUSTC_TARGET_NAME)/$(GREETD_PROFILE)/greetd \
		$(TARGET_DIR)/usr/bin/greetd
	$(INSTALL) -D -m 0755 $(@D)/target/$(RUSTC_TARGET_NAME)/$(GREETD_PROFILE)/agreety \
		$(TARGET_DIR)/usr/bin/agreety
	$(INSTALL) -D -m 0644 $(@D)/greetd.service \
		$(TARGET_DIR)/usr/lib/systemd/system/greetd.service
endef

$(eval $(cargo-package))
