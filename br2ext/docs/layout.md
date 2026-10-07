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

## Homes

Every account made since 0.3 is a systemd-homed one: its home is a
LUKS2 image, `/home/<name>.home` under `users/`, ext4 inside, sparse on
the disk (discard on and off line), unlocked by the account's password
at login -- pam_systemd_home ahead of pam_unix in greetd's, login's,
sudo's, the lock screen's and system-auth's stacks, with a pam_exec
line before it that caches the typed password: without one cached the
module first asks homed with no password, homed counts that as a
failed attempt and is busy rewriting the record when the real one
follows at once, which is how a greeter or `sudo -S` answers -- and
locked again when the last session ends. The record is in `/var/lib/systemd/home`,
not in `/etc/passwd`; the greeter and Settings list accounts through
the C library (nsswitch: `files systemd`), and aos-update's passwd
merge never sees them. The owner is made at the first boot by
`aos-firstboot` (`homectl create --storage=luks --fs-type=ext4`, the
first free uid from 1000), since homed must be running; the installer
makes no account at all. A **recovery key** (homed's, eight groups of
eight letters) is made with the home and shown once by the first-boot
setup, written nowhere; typed where the password goes, it opens the
home. A classic account (`aos-install --demo`, `--user` for the
drivers, a machine installed before 0.3) keeps working through
pam_unix; its home is a plain directory.

## Encryption

`aos-install --encrypt FILE` (the graphical installer's "Also encrypt
the whole disk", with a passphrase of its own) puts LUKS2 around the
aos partition before the filesystem: programs, settings and logs are
encrypted too, and the homes twice; the cores are not (public images,
verified). The initramfs finds the LUKS header and asks for the
passphrase on the console at every start, before the desktop; five
tries. The ESP and the cores carry nothing of yours. The swap file
(`aos/aos/swapfile`) is made only on an encrypted partition: in the
clear it would hold pages of the encrypted homes; zram is the swap
otherwise.

## The greeter

An owned machine (and one installed for someone else, once its owner
exists) boots to a login screen: greetd runs `/usr/lib/aos/session
--greeter` as the `greeter` account -- the compositor with ade-greeter
as its one program (the repository `greeter`), which lists the accounts,
takes a password and asks greetd over its socket to start
`/usr/lib/aos/session` as that account: the compositor and the shell as
before, with the apm environment, started again after a crash up to
four times in two minutes. The lock screen later in the session is
ade-lock, as it was. The live medium and a demo install keep
ade.service's autologin; `/etc/greetd/config.toml` in the /etc overlay
and the unit's enablement are what aos-install writes for the others,
and aos-firstboot rewrites after the first boot. greetd's PAM service
(`/etc/pam.d/greetd`) is the console's with pam_systemd, so both the
greeter and the session are logind's on seat0.

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
| `aos.offset=`    | where the hash tree starts in the core, in bytes            |
| `aos.live=`      | on the live medium: the device (or `PARTUUID=`) holding `/aos/core.img` |
| `aos.data=`      | `PARTUUID=<uuid>` of the aos partition; absent on the live ISO |

## Images and releases

Buildroot makes `rootfs.squashfs` (zstd) inside its fakeroot; post-image.sh
appends the hash tree (`veritysetup format`) and writes `core.img` with
`core.verity` beside it (`hash=`, `offset=`, `size=`), then assembles the ISO from
`/boot` and that image. A release ships `aos-X-x86_64.iso`,
`aos-X-x86_64-core.img` (a squashfs is compressed already) and
`aos-X-x86_64-core.verity`, named in the
signed SHA256SUMS. aos-update writes the image into the idle slot with dd,
checks it by opening its verity, copies the kernel, microcode and
initramfs out of it onto the ESP, writes `verity.cfg`, and sets `next`.

A 0.1.x installation cannot update into this layout: its updater knows
tarballs and ext4 slots. It is a reinstall (`./usb.sh`), once.
