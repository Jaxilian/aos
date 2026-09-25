include $(sort $(wildcard $(BR2_EXTERNAL_AOS_PATH)/package/*/*.mk))

# Vendoring for a Rust package built from a developer's working tree.
#
# pkg-cargo.mk builds --offline --locked and fills the VENDOR directory in
# the download step. A package pointed at a checkout through
# <PKG>_OVERRIDE_SRCDIR in local.mk has no download step, so nothing is
# vendored and the build stops on the first dependency. Each AOS cargo
# package adds this hook in that case and only then; a release build, from
# the git tag, never runs it and never needs the network past download.
#
# The config file is removed and then written, not appended to: a second
# "make <pkg>-rebuild" would otherwise land the [source.crates-io] block in
# it twice and cargo stops on the duplicate key -- in this very hook, since
# cargo reads the config before vendoring, so the build cannot recover.
define AOS_CARGO_VENDOR
	rm -f $(@D)/.cargo/config.toml
	cd $(@D) && \
	CARGO_HOME=$(BR_CARGO_HOME) \
	$(HOST_DIR)/bin/cargo vendor --locked --versioned-dirs VENDOR \
		>$(@D)/.cargo-vendor-config
	mkdir -p $(@D)/.cargo
	cp -f $(@D)/.cargo-vendor-config $(@D)/.cargo/config.toml
endef

# The live ISO stores the tree zisofs-compressed, and GRUB does not read a
# large compressed file back correctly: a compressed /boot/microcode.img
# reaches the kernel truncated and "Initramfs unpacking failed". Buildroot
# hits the same thing with the kernel and solves it by copying bzImage into
# the tree uncompressed after mkzftree has run; do the same for the
# microcode image. Hooks run in list order, so this lands after mkzftree.
define AOS_ISO9660_COPY_MICROCODE
	$(INSTALL) -D -m 0644 $(TARGET_DIR)/boot/microcode.img \
		$(ROOTFS_ISO9660_TMP_TARGET_DIR)/boot/microcode.img
endef
ifeq ($(BR2_TARGET_ROOTFS_ISO9660_TRANSPARENT_COMPRESSION),y)
ROOTFS_ISO9660_PRE_GEN_HOOKS += AOS_ISO9660_COPY_MICROCODE
endif

# Make the ISO bootable from a USB stick as well as from optical media.
#
# Written to a stick with dd, the plain ISO has no partition table at all:
# UEFI firmware finds no EFI system partition and refuses it, and a BIOS has
# no MBR to run. Two additions fix that, and both are what grub-mkrescue
# itself emits:
#
#   -append_partition 2 0xef <esp>  puts the FAT image Buildroot already
#   -appended_part_as_gpt           builds for El Torito into a real GPT
#                                   partition of type EF00, so firmware
#                                   finds /EFI/BOOT/bootx64.efi on it. A
#                                   protective MBR comes with the GPT.
#   --grub2-mbr <boot_hybrid.img>   GRUB's hybrid MBR, for a legacy BIOS
#                                   booting the same stick.
#   -partition_offset 16            gives the ISO partition its own second
#                                   superblock, so it is a mountable iso9660
#                                   filesystem in its own right. Without it
#                                   the partition starts 32 KiB into the
#                                   image, root=PARTUUID= resolves to
#                                   /dev/sda1, and the kernel panics with
#                                   "No filesystem could mount root". The
#                                   whole device stays mountable too, which
#                                   is what optical boot uses.
#
# The ESP is the one the iso9660 rules stage at boot/fat.efi; appending it a
# second time as a partition costs one more megabyte and leaves the El Torito
# entry, and so optical boot, untouched.
#
# The GPT disk GUID is pinned so that the ISO filesystem partition gets a
# PARTUUID known before the image exists -- iso-grub.cfg needs it on the
# kernel command line, and the image is what would carry it. xorriso derives
# partition N's GUID from the disk GUID by XORing byte 9 with N, so
# partition 1 differs only in the fourth group: aa05 -> aa04. That
# derivation is undocumented, so AOS_ISO9660_CHECK_PARTUUID below reads the
# finished image back and fails the build if it ever stops holding.
AOS_ISO_DISK_GUID = aa05aa05-aa05-4a05-aa05-aa05aa05aa05
AOS_ISO_ROOT_PARTUUID = aa05aa05-aa05-4a05-aa04-aa05aa05aa05

ifeq ($(BR2_TARGET_ROOTFS_ISO9660_EFI_BOOTLOADER),y)
ROOTFS_ISO9660_OPTS += \
	-append_partition 2 0xef $(ROOTFS_ISO9660_TMP_TARGET_DIR)/boot/fat.efi \
	-appended_part_as_gpt \
	-partition_offset 16 \
	--gpt_disk_guid $(AOS_ISO_DISK_GUID)

# Runs after ROOTFS_ISO9660_PREPARATION has staged the menu, so the
# placeholder is there to replace.
define AOS_ISO9660_SET_ROOT_PARTUUID
	$(SED) 's/__ROOT_PARTUUID__/$(AOS_ISO_ROOT_PARTUUID)/g' \
		$(ROOTFS_ISO9660_TMP_TARGET_DIR)/boot/grub/grub.cfg
endef
ROOTFS_ISO9660_PRE_GEN_HOOKS += AOS_ISO9660_SET_ROOT_PARTUUID

# After xorriso: cut the GPT entry array to the standard 128 entries (some
# firmware rejects any other count, and rejection means no ESP and no boot
# entry), then read the table back and confirm partition 1 really has the
# PARTUUID the boot menu tells the kernel to look for. See the script.
define AOS_ISO9660_CHECK_PARTUUID
	$(Q)python3 $(BR2_EXTERNAL_AOS_PATH)/board/aos/iso-gpt.py \
		$(BINARIES_DIR)/rootfs.iso9660 $(AOS_ISO_ROOT_PARTUUID)
endef
ROOTFS_ISO9660_POST_GEN_HOOKS += AOS_ISO9660_CHECK_PARTUUID
endif
ifeq ($(BR2_TARGET_ROOTFS_ISO9660_BIOS_BOOTLOADER),y)
ROOTFS_ISO9660_OPTS += \
	--grub2-mbr $(GRUB2_DIR)/build-i386-pc/grub-core/boot_hybrid.img
endif

# A bigger, FAT16 EFI system partition.
#
# Buildroot builds this as a 1 MiB image, and mkfs.vfat picks FAT12 at that
# size. OVMF in QEMU reads FAT12 happily; a lot of real firmware does not --
# it looks for an ESP, finds a filesystem it will not touch, and reports no
# bootable device at all. Every distribution's ISO ships FAT16 here for
# exactly this reason, so match them.
#
# 16 MiB is the smallest round size that mkfs.vfat will make FAT16 with room
# to spare for the ~900 KiB loader. It costs twice that in the image, once
# for the El Torito copy and once for the appended partition.
#
# Overriding the whole define is deliberate: Buildroot hardcodes both the
# size and the FAT type in the dd/mkfs.vfat pair, with no variable to set.
# br2-external .mk files are included after fs/common.mk, so this wins.
define ROOTFS_ISO9660_INSTALL_BOOTLOADER_EFI
	rm -rf $(ROOTFS_ISO9660_EFI_PARTITION_PATH)
	mkdir -p $(dir $(ROOTFS_ISO9660_EFI_PARTITION_PATH))
	dd if=/dev/zero of=$(ROOTFS_ISO9660_EFI_PARTITION_PATH) bs=1M count=16
	$(HOST_DIR)/sbin/mkfs.vfat -F 16 -n AOS_ESP \
		$(ROOTFS_ISO9660_VFAT_OPTS) $(ROOTFS_ISO9660_EFI_PARTITION_PATH)
	$(ROOTFS_ISO9660_FIX_TIME) $(ROOTFS_ISO9660_EFI_PARTITION_CONTENT)/*
	$(HOST_DIR)/bin/mcopy -p -m -i $(ROOTFS_ISO9660_EFI_PARTITION_PATH) -s \
		$(ROOTFS_ISO9660_EFI_PARTITION_CONTENT)/* ::/
	$(ROOTFS_ISO9660_FIX_TIME) $(ROOTFS_ISO9660_EFI_PARTITION_PATH)
endef

# Intel Wi-Fi firmware Buildroot has no option for.
#
# Its IWLWIFI_* options stop at BE200 ("gl"). Three later families are what
# laptops of 2022-2026 actually carry, and each is a chip with no Wi-Fi at
# all without its blobs:
#   ma  AX211 CNVi on 12th/13th-gen Core         ~15 MiB
#   bz  BE201 on Lunar Lake / Arrow Lake         ~47 MiB
#   sc  the CNVi in Core Ultra Series 3          ~21 MiB
# The first real machine AOS booted on had "sc". linux-firmware's file list
# is expanded when its build step runs, so appending here is seen.
LINUX_FIRMWARE_FILES += \
	intel/iwlwifi/iwlwifi-ma-* \
	intel/iwlwifi/iwlwifi-bz-* \
	intel/iwlwifi/iwlwifi-sc-*

# bwrap without the setuid bit. Buildroot sets it "in case the kernel has
# user namespaces disabled for non-root users"; AOS has them on, and a
# setuid sandbox helper is a larger trust boundary than an unprivileged
# one. The permissions table is expanded when it is applied, so the
# package's line can be replaced from here.
ifeq ($(BR2_PACKAGE_BUBBLEWRAP),y)
define BUBBLEWRAP_PERMISSIONS
	/usr/bin/bwrap f 0755 0 0 - - - - -
endef
endif

# libinput without Lua plugins. Buildroot turns them on whenever lua is in
# the image, and liblua is built without libm in its NEEDED: ld.so then
# refuses ade-comp at start ("Relink liblua with libm for IFUNC symbol
# tanh"). Nothing on AOS writes input plugins in Lua anyway. Expanded at
# configure time, so it can be corrected from here.
ifeq ($(BR2_PACKAGE_LIBINPUT),y)
LIBINPUT_CONF_OPTS := $(filter-out -Dlua-plugins=enabled,$(LIBINPUT_CONF_OPTS)) \
	-Dlua-plugins=disabled
endif

# PipeWire and WirePlumber for the session only, never system-wide.
#
# Buildroot builds both with their system-service units, and preset-all
# then enables them: a second PipeWire runs as the "pipewire" user from
# boot, with no session bus and no runtime directory, logs errors every
# boot, and holds the sound card against the session's own instance. On
# AOS sound belongs to the person at the seat; the user units in
# rootfs-overlay/usr/lib/systemd/user are the only ones. <PKG>_CONF_OPTS
# is expanded at configure time, so it can be corrected from here (unlike
# _DEPENDENCIES; see the polkit note below).
ifeq ($(BR2_PACKAGE_PIPEWIRE),y)
PIPEWIRE_CONF_OPTS := $(filter-out -Dsystemd-system-service=enabled,$(PIPEWIRE_CONF_OPTS)) \
	-Dsystemd-system-service=disabled
endif
ifeq ($(BR2_PACKAGE_WIREPLUMBER),y)
WIREPLUMBER_CONF_OPTS := $(filter-out -Dsystemd-system-service=true,$(WIREPLUMBER_CONF_OPTS)) \
	-Dsystemd-system-service=false
endif

# polkit tracking sessions through logind.
#
# Buildroot builds polkit with -Dsession_tracking=ConsoleKit, because its
# systemd recipe depends on polkit (only so that systemd's own rule files
# land in /usr/share/polkit-1/rules.d after polkit has created it) and
# polkit built for logind needs libsystemd -- a cycle, resolved upstream by
# giving polkit no session tracking at all. On a systemd system the cost is
# large and silent: polkitd can attach no session to any request, so
# subject.local and subject.active are always false, and every
# "allow_active=yes" in every policy file -- systemd's power-off, reboot and
# suspend included -- quietly becomes "auth_admin". The person at the
# keyboard is then refused a power-off with "interactive authentication
# required", and no rule under /etc/polkit-1/rules.d can say otherwise,
# because none of them ever sees a local or active subject.
#
# AOS breaks the cycle the other way round: systemd does not wait for
# polkit, and polkit builds after systemd, against libsystemd, with logind
# tracking -- polkit's own default.
#
# How, precisely, because the obvious way does not work. A package's
# <PKG>_DEPENDENCIES is read when its recipe is evaluated, at the include
# of package/*/*.mk, which happens before this file: the configure stamp's
# order-only prerequisites (pkg-generic.mk, "$(2)_TARGET_CONFIGURE): |
# $(2)_FINAL_DEPENDENCIES") are expanded then. Appending to or filtering
# the variable here changes nothing that make will act on. It looked as if
# it did, for as long as the tree was built incrementally and systemd was
# always already there; the first clean build configured polkit first and
# it failed to find libsystemd. <PKG>_CONF_OPTS, by contrast, is expanded
# when the configure command runs, so it can be changed here.
#
# So the systemd side comes from the config: BR2_PACKAGE_SYSTEMD_POLKIT is
# left unset, which is the only way systemd.mk does not add polkit to its
# dependencies, and the -Dpolkit=enabled that option would have set is
# restored here. The polkit side is an explicit rule on the stamp itself,
# which is a prerequisite make has not seen yet.
ifeq ($(BR2_PACKAGE_SYSTEMD_LOGIND)$(BR2_PACKAGE_POLKIT),yy)
SYSTEMD_CONF_OPTS := $(filter-out -Dpolkit=disabled,$(SYSTEMD_CONF_OPTS)) \
	-Dpolkit=enabled
POLKIT_CONF_OPTS := $(filter-out -Dsession_tracking=ConsoleKit,$(POLKIT_CONF_OPTS)) \
	-Dsession_tracking=logind
$(POLKIT_TARGET_CONFIGURE): | systemd
polkit-depends: systemd
endif
