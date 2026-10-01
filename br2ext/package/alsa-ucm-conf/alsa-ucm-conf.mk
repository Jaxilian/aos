################################################################################
#
# alsa-ucm-conf
#
################################################################################

# Data only: the ucm2 tree alsa-lib's UCM reads, and the legacy ucm one.
# The version follows alsa-lib's (1.2.16 here); a newer profile set on an
# older library is fine, the format is versioned inside the files.
ALSA_UCM_CONF_VERSION = 1.2.16.1
ALSA_UCM_CONF_SITE = $(call github,alsa-project,alsa-ucm-conf,v$(ALSA_UCM_CONF_VERSION))
ALSA_UCM_CONF_LICENSE = BSD-3-Clause
ALSA_UCM_CONF_LICENSE_FILES = LICENSE
ALSA_UCM_CONF_DEPENDENCIES = alsa-lib

define ALSA_UCM_CONF_INSTALL_TARGET_CMDS
	mkdir -p $(TARGET_DIR)/usr/share/alsa
	cp -a $(@D)/ucm $(@D)/ucm2 $(TARGET_DIR)/usr/share/alsa/
endef

ALSA_UCM_CONF_CPE_ID_VENDOR = alsa-project

$(eval $(generic-package))
