################################################################################
#
# rust-target
#
################################################################################

AOS_RUST_VERSION = 1.96.1
AOS_RUST_SITE = https://static.rust-lang.org/dist
AOS_RUST_SOURCE = rust-$(AOS_RUST_VERSION)-x86_64-unknown-linux-gnu.tar.xz
AOS_RUST_LICENSE = Apache-2.0 or MIT
AOS_RUST_LICENSE_FILES = COPYRIGHT LICENSE-APACHE LICENSE-MIT

# The Rust toolchain is useless on the target without something to link
# with; aos-gcc provides cc, and pulls in binutils for ld.
AOS_RUST_DEPENDENCIES = aos-gcc

# This is the upstream prebuilt x86_64-unknown-linux-gnu distribution, so
# there is nothing to configure or build -- only to install. Those binaries
# are built against a generic x86-64 baseline and glibc 2.17, so they run
# on our x86-64-v2 / glibc 2.43 target.
AOS_RUST_COMPONENTS = rustc rust-std-x86_64-unknown-linux-gnu cargo

ifeq ($(BR2_PACKAGE_AOS_RUST_RUSTFMT),y)
AOS_RUST_COMPONENTS += rustfmt-preview
endif

ifeq ($(BR2_PACKAGE_AOS_RUST_CLIPPY),y)
AOS_RUST_COMPONENTS += clippy-preview
endif

# rust-docs is deliberately excluded: it is several hundred MB of HTML that
# nothing on a foundation image can render.
#
# --disable-ldconfig matters. install.sh would otherwise run the *host's*
# ldconfig, which would be pointless here and would touch the host system.
# Note also that install.sh treats --prefix as relative to --destdir but
# --sysconfdir as an absolute path, hence the asymmetry below.
define AOS_RUST_INSTALL_TARGET_CMDS
	cd $(@D) && ./install.sh \
		--destdir=$(TARGET_DIR) \
		--prefix=/usr \
		--sysconfdir=$(TARGET_DIR)/etc \
		--components=$(subst $(space),$(comma),$(AOS_RUST_COMPONENTS)) \
		--disable-ldconfig
endef

# install.sh leaves its uninstall bookkeeping behind; a foundation image has
# no package manager to use it, and the manifests reference host paths.
define AOS_RUST_CLEANUP_MANIFESTS
	rm -rf $(TARGET_DIR)/usr/lib/rustlib/uninstall.sh \
		$(TARGET_DIR)/usr/lib/rustlib/install.log \
		$(TARGET_DIR)/usr/lib/rustlib/components \
		$(TARGET_DIR)/usr/lib/rustlib/rust-installer-version
	rm -f $(TARGET_DIR)/usr/lib/rustlib/manifest-*
	rm -rf $(TARGET_DIR)/usr/share/doc/rust
endef
AOS_RUST_POST_INSTALL_TARGET_HOOKS += AOS_RUST_CLEANUP_MANIFESTS

$(eval $(generic-package))
