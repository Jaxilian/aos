################################################################################
#
# aos-nvidia
#
################################################################################

AOS_NVIDIA_VERSION = 610.57.04
AOS_NVIDIA_SITE = https://us.download.nvidia.com/XFree86/Linux-x86_64/$(AOS_NVIDIA_VERSION)
AOS_NVIDIA_SOURCE = NVIDIA-Linux-x86_64-$(AOS_NVIDIA_VERSION).run
AOS_NVIDIA_LICENSE = NVIDIA Software License
AOS_NVIDIA_LICENSE_FILES = LICENSE
AOS_NVIDIA_REDISTRIBUTE = NO

# libglvnd owns libGL/libEGL/libGLES and dispatches to a vendor at run time;
# these libraries register themselves as one of those vendors. Without it,
# Mesa and NVIDIA would both try to be libEGL.so.1 and one would lose.
AOS_NVIDIA_DEPENDENCIES = aos-nvidia-open libglvnd wayland

# The .run file is a self-extracting shell archive, not a tarball.
define AOS_NVIDIA_EXTRACT_CMDS
	$(SHELL) $(AOS_NVIDIA_DL_DIR)/$(AOS_NVIDIA_SOURCE) --extract-only --target \
		$(@D)/tmp-extract
	chmod u+w -R $(@D)
	mv $(@D)/tmp-extract/* $(@D)/tmp-extract/.manifest $(@D)
	rm -rf $(@D)/tmp-extract
endef

# EGL, GLES and Vulkan vendor libraries plus the driver core they sit on.
# No libGLX_nvidia and no X11 platform libraries: AOS ships no X server, so
# they would be unloadable.
AOS_NVIDIA_LIBS = \
	libEGL_nvidia.so.$(AOS_NVIDIA_VERSION) \
	libGLESv1_CM_nvidia.so.$(AOS_NVIDIA_VERSION) \
	libGLESv2_nvidia.so.$(AOS_NVIDIA_VERSION) \
	libnvidia-eglcore.so.$(AOS_NVIDIA_VERSION) \
	libnvidia-glcore.so.$(AOS_NVIDIA_VERSION) \
	libnvidia-glsi.so.$(AOS_NVIDIA_VERSION) \
	libnvidia-glvkspirv.so.$(AOS_NVIDIA_VERSION) \
	libnvidia-gpucomp.so.$(AOS_NVIDIA_VERSION) \
	libnvidia-tileiras.so.$(AOS_NVIDIA_VERSION) \
	libnvidia-rtcore.so.$(AOS_NVIDIA_VERSION) \
	libnvidia-allocator.so.$(AOS_NVIDIA_VERSION) \
	libnvidia-wayland-client.so.$(AOS_NVIDIA_VERSION) \
	libnvidia-tls.so.$(AOS_NVIDIA_VERSION) \
	libnvidia-cfg.so.$(AOS_NVIDIA_VERSION) \
	libnvidia-ml.so.$(AOS_NVIDIA_VERSION) \
	libnvidia-sandboxutils.so.$(AOS_NVIDIA_VERSION)

ifeq ($(BR2_PACKAGE_AOS_NVIDIA_CUDA),y)
AOS_NVIDIA_LIBS += \
	libcuda.so.$(AOS_NVIDIA_VERSION) \
	libnvidia-nvvm.so.$(AOS_NVIDIA_VERSION) \
	libnvidia-ptxjitcompiler.so.$(AOS_NVIDIA_VERSION)
endif

ifeq ($(BR2_PACKAGE_AOS_NVIDIA_SMI),y)
AOS_NVIDIA_PROGS += nvidia-smi
endif

# Install one library and the symlinks that make it loadable.
#
# Some of these libraries carry a short SONAME (libEGL_nvidia.so.0) while
# others use the fully versioned filename as their own SONAME. Rather than
# hardcode which is which -- and get it wrong on the next driver release --
# read the SONAME back out of each library, exactly as Buildroot's own
# nvidia-driver package does.
#
# $1: library filename
define AOS_NVIDIA_INSTALL_LIB
	$(INSTALL) -D -m 0644 $(@D)/$(1) $(TARGET_DIR)/usr/lib/$(1)
	libsoname="$$( $(TARGET_READELF) -d "$(@D)/$(1)" \
		|sed -r -e '/.*\(SONAME\).*\[(.*)\]$$/!d; s//\1/;' )"; \
	if [ -n "$${libsoname}" -a "$${libsoname}" != "$(1)" ]; then \
		ln -sf $(1) $(TARGET_DIR)/usr/lib/$${libsoname}; \
	fi
endef

# GSP firmware. The open kernel modules request it as
#   "nvidia/" NV_VERSION_STRING "/" name ".bin"
# (kernel-open/nvidia/nv.c), so the version directory is not optional --
# with the files anywhere else the module loads and the GPU stays dark.
# It ships only here, not in linux-firmware.
AOS_NVIDIA_FIRMWARE = \
	gsp_ga10x.bin \
	gsp_tu10x.bin \
	ucodes_ga10x.bin \
	ucodes_tu10x.bin

# Vendor manifests. libglvnd reads egl_vendor.d to find the EGL driver; the
# Vulkan loader reads icd.d; the EGL external platform modules are what let
# a Wayland compositor or a GBM consumer talk to the NVIDIA driver at all.
define AOS_NVIDIA_INSTALL_MANIFESTS
	$(INSTALL) -D -m 0644 $(@D)/10_nvidia.json \
		$(TARGET_DIR)/usr/share/glvnd/egl_vendor.d/10_nvidia.json
	$(INSTALL) -D -m 0644 $(@D)/nvidia_icd.json \
		$(TARGET_DIR)/usr/share/vulkan/icd.d/nvidia_icd.json
	$(INSTALL) -D -m 0644 $(@D)/nvidia_layers.json \
		$(TARGET_DIR)/usr/share/vulkan/implicit_layer.d/nvidia_layers.json
	$(foreach f,09_nvidia_wayland2.json 10_nvidia_wayland.json 15_nvidia_gbm.json, \
		$(INSTALL) -D -m 0644 $(@D)/$(f) \
			$(TARGET_DIR)/usr/share/egl/egl_external_platform.d/$(f)$(sep))
endef

define AOS_NVIDIA_INSTALL_TARGET_CMDS
	$(foreach lib,$(AOS_NVIDIA_LIBS), \
		$(call AOS_NVIDIA_INSTALL_LIB,$(lib))$(sep))
	$(foreach p,$(AOS_NVIDIA_PROGS), \
		$(INSTALL) -D -m 0755 $(@D)/$(p) $(TARGET_DIR)/usr/bin/$(p)$(sep))
	$(foreach f,$(AOS_NVIDIA_FIRMWARE), \
		$(INSTALL) -D -m 0444 $(@D)/firmware/$(f) \
			$(TARGET_DIR)/lib/firmware/nvidia/$(AOS_NVIDIA_VERSION)/$(f)$(sep))
	$(AOS_NVIDIA_INSTALL_MANIFESTS)
	$(INSTALL) -D -m 0644 $(@D)/LICENSE \
		$(TARGET_DIR)/usr/share/licenses/nvidia/LICENSE
endef

$(eval $(generic-package))
