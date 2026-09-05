#!/bin/sh
#
# Rebuild the ISO as a hybrid image, so it boots from a USB stick as well as
# from optical media.
#
# Buildroot's fs/iso9660 produces a dual El Torito image (BIOS + UEFI), which
# is all an optical drive or a VM needs, but it gives the image no partition
# table -- BR2_TARGET_ROOTFS_ISO9660_HYBRID exists only for the isolinux path,
# not the GRUB2 one. Written to a USB stick with dd, such an image offers a
# legacy BIOS nothing to boot, and offers UEFI firmware no EFI system
# partition to find, so nothing happens.
#
# Two extra xorriso flags fix that, and they have to be given when the image
# is created rather than bolted on afterwards:
#
#   -isohybrid-mbr        an MBR, built from GRUB's boot_hybrid.img, so a
#                         legacy BIOS sees a bootable disk;
#   -isohybrid-gpt-basdat a GPT entry covering the embedded FAT image, so UEFI
#                         firmware sees an EFI system partition.
#
# Everything else mirrors the invocation in fs/iso9660/iso9660.mk, so the
# resulting image is identical apart from being bootable from a stick.
#
# $1 is BINARIES_DIR.

set -e

BINARIES_DIR="${1:?post-image.sh: BINARIES_DIR not passed}"
: "${BUILD_DIR:?post-image.sh: BUILD_DIR not set}"
: "${HOST_DIR:?post-image.sh: HOST_DIR not set}"
: "${TARGET_DIR:?post-image.sh: TARGET_DIR not set}"

ISO="${BINARIES_DIR}/rootfs.iso9660"
ISO_TREE="${BUILD_DIR}/buildroot-fs/rootfs.iso9660.tmp"
HYBRID_MBR="${TARGET_DIR}/lib/grub/i386-pc/boot_hybrid.img"

[ -f "${ISO}" ] || exit 0

for f in "${ISO_TREE}/boot/grub/grub-eltorito.img" "${ISO_TREE}/boot/fat.efi" \
         "${HYBRID_MBR}"; do
	if [ ! -f "${f}" ]; then
		echo "post-image.sh: ${f} missing, leaving the ISO non-hybrid"
		exit 0
	fi
done

echo "Rebuilding ISO as a hybrid (USB-bootable) image"

"${HOST_DIR}/bin/xorriso" -as mkisofs \
	-z -J -R \
	-V AOS \
	-isohybrid-mbr "${HYBRID_MBR}" \
	-b boot/grub/grub-eltorito.img \
	-no-emul-boot -boot-load-size 4 -boot-info-table \
	-eltorito-alt-boot \
	-e boot/fat.efi \
	-no-emul-boot -isohybrid-gpt-basdat \
	-o "${ISO}.new" "${ISO_TREE}"

mv -f "${ISO}.new" "${ISO}"
echo "Hybrid ISO: $(du -h "${ISO}" | cut -f1)"
