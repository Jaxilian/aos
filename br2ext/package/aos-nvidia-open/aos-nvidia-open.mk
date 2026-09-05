################################################################################
#
# aos-nvidia-open
#
################################################################################

AOS_NVIDIA_OPEN_VERSION = 610.57.04
AOS_NVIDIA_OPEN_SITE = \
	$(call github,NVIDIA,open-gpu-kernel-modules,$(AOS_NVIDIA_OPEN_VERSION))
AOS_NVIDIA_OPEN_LICENSE = MIT or GPL-2.0
AOS_NVIDIA_OPEN_LICENSE_FILES = COPYING

# The module sources live in kernel-open/; the rest of the tree is the
# firmware-facing driver core that gets compiled into them.
AOS_NVIDIA_OPEN_MODULE_SUBDIRS = kernel-open

# kernel-open/Kbuild documents that its parent makefile must supply these.
# Buildroot invokes kbuild directly via "make -C $(LINUX_DIR) M=<dir>", so
# there is no NVIDIA parent makefile to define them and we pass them here.
AOS_NVIDIA_OPEN_MODULE_MAKE_OPTS = \
	NV_KERNEL_SOURCES=$(LINUX_DIR) \
	NV_KERNEL_OUTPUT=$(LINUX_DIR) \
	NV_KERNEL_MODULES="nvidia nvidia-uvm nvidia-drm nvidia-modeset" \
	ARCH=x86_64

# nvidia-drm is the piece that matters for a display server: it exposes the
# GPU through DRM/KMS so a compositor can drive it. It only registers as a
# modesetting driver when this is set, so ship the modprobe option rather
# than leaving every user to discover it.
define AOS_NVIDIA_OPEN_INSTALL_MODPROBE_CONF
	$(INSTALL) -D -m 0644 $(AOS_NVIDIA_OPEN_PKGDIR)/nvidia.conf \
		$(TARGET_DIR)/etc/modprobe.d/nvidia.conf
endef
AOS_NVIDIA_OPEN_POST_INSTALL_TARGET_HOOKS += AOS_NVIDIA_OPEN_INSTALL_MODPROBE_CONF

# The kernel modules are built by the kernel-module infrastructure's hooks;
# there is nothing to build or install by the generic infrastructure itself.
AOS_NVIDIA_OPEN_BUILD_CMDS =
AOS_NVIDIA_OPEN_INSTALL_TARGET_CMDS =

$(eval $(kernel-module))
$(eval $(generic-package))
