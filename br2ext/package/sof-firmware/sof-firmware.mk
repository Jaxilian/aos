################################################################################
#
# sof-firmware
#
################################################################################

# linux-firmware stopped carrying Intel's SOF firmware; the SOF project
# publishes it as sof-bin. The tarball holds every generation side by
# side, laid out as /lib/firmware/intel expects it: sof/ and sof-tplg/
# for the IPC3 parts (Apollo Lake to Raptor Lake), sof-ipc4/,
# sof-ipc4-lib/, sof-ipc4-tplg/ and sof-ace-tplg/ for Meteor Lake on.
# The kernel picks the directory by the platform, so all of them ship;
# it is 17 MB compressed. The tools (sof-ctl, sof-logger) are for DSP
# developers and are not installed.
SOF_FIRMWARE_VERSION = 2026.09.1
SOF_FIRMWARE_SOURCE = sof-bin-$(SOF_FIRMWARE_VERSION).tar.gz
SOF_FIRMWARE_SITE = https://github.com/thesofproject/sof-bin/releases/download/v$(SOF_FIRMWARE_VERSION)
SOF_FIRMWARE_LICENSE = BSD-3-Clause (topologies, community firmware), LICENCE.Intel (signed firmware), Notice.NXP
SOF_FIRMWARE_LICENSE_FILES = LICENCE.Intel LICENCE.NXP Notice.NXP README.md
SOF_FIRMWARE_REDISTRIBUTE = NO

SOF_FIRMWARE_DIRS = sof sof-tplg sof-ipc4 sof-ipc4-lib sof-ipc4-tplg sof-ace-tplg

define SOF_FIRMWARE_INSTALL_TARGET_CMDS
	mkdir -p $(TARGET_DIR)/lib/firmware/intel
	$(foreach d,$(SOF_FIRMWARE_DIRS), \
		cp -a $(@D)/$(d) $(TARGET_DIR)/lib/firmware/intel/$(sep))
endef

SOF_FIRMWARE_CPE_ID_VENDOR = thesofproject

$(eval $(generic-package))
