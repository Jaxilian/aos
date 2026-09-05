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

# The driver builds in two halves. src/nvidia and src/nvidia-modeset are the
# OS-agnostic core, compiled by NVIDIA's own build system into two .o_binary
# blobs; kernel-open is the kbuild glue that links against them. Running kbuild
# alone fails with "No rule to make target nv-kernel.o_binary", so the core has
# to be built first, here. The kernel-module infrastructure's hooks then do the
# kbuild half and the modules_install.
#
# HOST_CC is passed explicitly because NVIDIA's utils.mk defaults it to $(CC),
# which would point host-side build tools at the cross compiler.
AOS_NVIDIA_OPEN_CORE_OBJS = \
	kernel-open/nvidia/nv-kernel.o_binary \
	kernel-open/nvidia-modeset/nv-modeset-kernel.o_binary

define AOS_NVIDIA_OPEN_BUILD_CMDS
	$(TARGET_MAKE_ENV) $(MAKE) -C $(@D) \
		CC="$(TARGET_CC)" \
		LD="$(TARGET_LD)" \
		AR="$(TARGET_AR)" \
		OBJCOPY="$(TARGET_OBJCOPY)" \
		HOST_CC="$(HOSTCC)" \
		ARCH=x86_64 \
		$(AOS_NVIDIA_OPEN_CORE_OBJS)
endef

AOS_NVIDIA_OPEN_INSTALL_TARGET_CMDS =

$(eval $(kernel-module))
$(eval $(generic-package))
