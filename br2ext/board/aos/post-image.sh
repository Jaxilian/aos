#!/bin/sh
#
# post-image.sh -- the core and the ISO, from what Buildroot made.
#
#   $1  BINARIES_DIR (output/images); TARGET_DIR, HOST_DIR, BR2_EXTERNAL_AOS_PATH set
#
# 1. core.img: rootfs.squashfs padded to 4 KiB, its dm-verity hash tree
#    appended (veritysetup format, superblock at the offset); core.verity
#    says the root hash, the offset and the data size. The same file goes
#    into a slot (aos-update, aos-install) and onto the ISO.
# 2. rootfs.iso9660: the hybrid BIOS+UEFI live ISO: /boot (kernel,
#    microcode, initramfs, GRUB) and /aos/core.img, nothing else. The
#    xorriso options are the ones external.mk used for the tree ISO (see
#    the comments there: GPT with a pinned disk GUID, the ESP appended as
#    partition 2, GRUB's hybrid MBR); iso-gpt.py then trims the GPT.
#
# Runs outside Buildroot's fakeroot: nothing here reads the target tree's
# ownership, which is why it builds from images and not from the tree.

set -e
IMG="${1:?post-image.sh: BINARIES_DIR not passed}"
: "${TARGET_DIR:?}" "${HOST_DIR:?}" "${BR2_EXTERNAL_AOS_PATH:?}"
BOARD="$BR2_EXTERNAL_AOS_PATH/board/aos"
SQ="$IMG/rootfs.squashfs"
[ -f "$SQ" ] || { echo "post-image.sh: no $SQ" >&2; exit 1; }

# --- 1. the core -----------------------------------------------------------
CORE="$IMG/core.img"
cp "$SQ" "$CORE"
size=$(stat -c %s "$CORE")
pad=$(( (4096 - size % 4096) % 4096 ))
[ "$pad" -eq 0 ] || truncate -s $(( size + pad )) "$CORE"
size=$(( size + pad ))
"$HOST_DIR/sbin/veritysetup" format --hash-offset="$size" "$CORE" "$CORE" > "$IMG/core.verity.log"
hash=$(sed -n 's/^Root hash:[[:space:]]*//p' "$IMG/core.verity.log")
[ -n "$hash" ] || { echo "post-image.sh: veritysetup gave no root hash" >&2; exit 1; }
printf 'hash=%s\noffset=%s\nsize=%s\n' "$hash" "$size" "$(stat -c %s "$CORE")" > "$IMG/core.verity"
echo "post-image.sh: core.img $(( $(stat -c %s "$CORE") / 1048576 )) MB, root hash $hash"

# --- 2. the ISO ------------------------------------------------------------
ISO="$IMG/rootfs.iso9660"
T="$IMG/iso.tmp"
rm -rf "$T"
mkdir -p "$T/boot/grub" "$T/aos"
cp "$IMG/bzImage" "$T/boot/bzImage"
cp "$TARGET_DIR/boot/microcode.img" "$T/boot/microcode.img"
cp "$TARGET_DIR/boot/initramfs.img" "$T/boot/initramfs.img"
ln "$CORE" "$T/aos/core.img" 2>/dev/null || cp "$CORE" "$T/aos/core.img"
cp "$IMG/core.verity" "$T/aos/core.verity"
cp "$IMG/grub-eltorito.img" "$T/boot/grub/grub-eltorito.img"
DISK_GUID=aa05aa05-aa05-4a05-aa05-aa05aa05aa05
ROOT_PARTUUID=aa05aa05-aa05-4a05-aa04-aa05aa05aa05
sed -e "s/__ROOT_PARTUUID__/$ROOT_PARTUUID/g" -e "s/__HASH__/$hash/g" -e "s/__OFFSET__/$size/g" \
	"$BOARD/iso-grub.cfg" > "$T/boot/grub/grub.cfg"
# The ESP: FAT16, 16 MiB (FAT12 is refused by a lot of firmware).
dd if=/dev/zero of="$T/boot/fat.efi" bs=1M count=16 status=none
"$HOST_DIR/sbin/mkfs.vfat" -F 16 -n AOS_ESP "$T/boot/fat.efi" > /dev/null
"$HOST_DIR/bin/mcopy" -p -m -i "$T/boot/fat.efi" -s "$IMG"/efi-part/* ::/
HYBRID=$(ls -d "$IMG"/../build/grub2-*/build-i386-pc/grub-core/boot_hybrid.img | head -1)
"$HOST_DIR/bin/xorriso" -as mkisofs \
	-R -J -r \
	-b boot/grub/grub-eltorito.img -no-emul-boot -boot-load-size 4 -boot-info-table \
	-eltorito-alt-boot -e boot/fat.efi -no-emul-boot \
	-append_partition 2 0xef "$T/boot/fat.efi" -appended_part_as_gpt \
	-partition_offset 16 --gpt_disk_guid "$DISK_GUID" \
	--grub2-mbr "$HYBRID" \
	-V AOS_LIVE -o "$ISO" "$T" 2> "$IMG/iso.log" || { tail -20 "$IMG/iso.log" >&2; exit 1; }
python3 "$BOARD/iso-gpt.py" "$ISO" "$ROOT_PARTUUID"
rm -rf "$T"
echo "post-image.sh: $(basename "$ISO") $(( $(stat -c %s "$ISO") / 1048576 )) MB"
