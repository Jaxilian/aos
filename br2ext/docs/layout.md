# The cores and the aos partition

Decided 2026-10-06. What a disk holds, what boots it, and what a person
sees. Supersedes the slot description in `usr/lib/aos/slot.sh` for 0.1.x.

## Partitions

| # | Label  | What                                                       |
|---|--------|------------------------------------------------------------|
| 1 | --     | BIOS boot (GRUB's core for a legacy BIOS)                   |
| 2 | AOS_ESP| The EFI system partition: GRUB, grubenv, and per slot the kernel, microcode, initramfs and the verity parameters (`/aos/a`, `/aos/b`) |
| 3 | aos-a  | Core A: a squashfs image with its dm-verity hash tree appended. Raw, no filesystem of its own. |
| 4 | aos-b  | Core B, the same                                            |
| 5 | aos    | The OS a person sees: ext4 (LUKS2 around it when the installer was asked to encrypt). |

A core is immutable: every block the kernel reads from it is checked
against the hash tree, whose root hash GRUB passes on the command line
from the ESP's `verity.cfg`. A core that was tampered with, or written
half way, does not mount; GRUB's `next` then falls back to the confirmed
slot at the following boot, as before. Nothing writes into a core, so
the kernel is no longer an apm package: a kernel update is an OS update.

## The aos partition

```
aos/
  aos/        what the OS writes: etc/ (the overlay over the core's /etc)
              and var/ (the whole /var), and the swap file
  apm/        the package store: /opt/apm
  users/      the homes: /home
```

The initramfs mounts the partition at /aos and binds from it: `/aos/aos/var`
on /var, an overlay of `/aos/aos/etc/{upper,work}` on /etc, `/aos/apm` on
/opt/apm, `/aos/users` on /home. /tmp and /run are tmpfs. The Unix tree
is still there for every program that needs it; Files shows /aos as "AOS"
with those three folders, and a person's own files are under users/.

On the live ISO /aos is a tmpfs with the same three directories: the live
home is writable now, and the installer copies the core, not a tree.

## Boot

```
firmware -> GRUB (ESP) -> bzImage + microcode + initramfs (ESP, per slot)
         -> initramfs: veritysetup open the core, mount it, fsck and mount
            aos (LUKS open first when encrypted), bind the tree, switch_root
         -> systemd
```

The initramfs is built by post-build.sh from the target's own binaries
(`board/aos/initramfs/`): bash, util-linux, veritysetup, cryptsetup,
e2fsck, and nothing else. The command line it reads:

| Parameter        | Meaning                                                    |
|------------------|------------------------------------------------------------|
| `aos.core=`      | `PARTUUID=<uuid>` of the slot, or `live` (the medium's `/aos/core.img` through a loop device) |
| `aos.hash=`      | the verity root hash of that core                           |
| `aos.data=`      | `PARTUUID=<uuid>` of the aos partition; absent on the live ISO |

## Images and releases

Buildroot makes `rootfs.squashfs` (zstd) inside its fakeroot; post-image.sh
appends the hash tree (`veritysetup format`) and writes `core.img` with
`core.verity` beside it (`blocks=`, `hash=`), then assembles the ISO from
`/boot` and that image. A release ships `aos-X-x86_64.iso`,
`aos-X-x86_64-core.img.xz` and `aos-X-x86_64-core.verity`, named in the
signed SHA256SUMS. aos-update writes the image into the idle slot with dd,
checks it by opening its verity, copies the kernel, microcode and
initramfs out of it onto the ESP, writes `verity.cfg`, and sets `next`.

A 0.1.x installation cannot update into this layout: its updater knows
tarballs and ext4 slots. It is a reinstall (`./usb.sh`), once.
