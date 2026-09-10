# The AOS platform contract

> Looking for how to build, test, upgrade or publish AOS, or a plain-language
> description of what it is? See [docs/](docs/). This file is the technical
> contract for software built *on* AOS.


AOS is a foundation, not a distribution. It gives you a kernel, a C library,
drivers, a graphics stack and a working toolchain -- and then stops. There is
no package manager, no desktop, no applications. Those are yours to write.

This document is the contract: what is guaranteed to be present, what is
deliberately absent, and what you can rely on when building on top.

## ABI baseline

| | |
|---|---|
| Architecture | x86_64, **x86-64-v2** baseline (SSE4.2 + POPCNT, ~2009 and later) |
| C library | glibc 2.44 |
| C/C++ compiler | gcc 15.3.0 |
| Rust | 1.96.1 (rustc + cargo) |
| Kernel | Linux 7.1.13 |
| Init | systemd 258.7 |
| binutils | as, ld and friends, on the target |

The v2 baseline is a deliberate trade. It rules out pre-2009 CPUs and buys
better code generation everywhere else. Anything you compile on an AOS machine
targets v2 by default, so it will run on any other AOS machine.

**This matters in a VM.** QEMU's default `qemu64` CPU model predates SSE4.2, so
an AOS image will panic on it with an invalid opcode inside `ld-linux`. Use
`-cpu Nehalem`, `-cpu host` or `-cpu max`.

## Filesystem layout

Standard FHS with a merged `/usr` and a merged `bin`, as systemd requires.
Every program lives in `/usr/bin`, libraries in `/usr/lib`; `/bin`, `/sbin`,
`/lib` and `/usr/sbin` are all symlinks. Anything you install belongs in
`/usr/bin` too — a real `/usr/sbin` directory would shadow the symlink.

Two things are worth knowing because they are not typical of an embedded image:

- **`/usr/include` is populated.** Headers for the C library, the kernel UAPI,
  the C++ standard library and every library AOS ships are present on the
  machine, not only in a build host's sysroot.
- **`/usr/lib` carries development artefacts.** Static archives, startup files
  (`crt1.o` and friends) and the unversioned `.so` symlinks that `-lfoo`
  resolves through are all there, alongside the runtime `.so.N` libraries.

Together those are what make the system self-hosting. They are exported from
the staging sysroot by `board/aos/post-build.sh`.

`/etc/os-release` identifies the system as `ID=aos`.

On an installed system the kernel mounts the root **read-only** from
`root=PARTUUID=` in `/boot/grub/grub.cfg`, `systemd-fsck-root` checks it, and
`systemd-remount-fs` makes it writable from its `/etc/fstab` line. That is
how the root gets an fsck without an initramfs; do not change the `ro` on
the kernel command line. `/boot/efi` is listed by `UUID=` with `nofail`;
systemd waits for udev to create the `/dev/disk/by-uuid` link before mounting
it, and entries you add by UUID work the same way.

There is no initramfs. The `initrd` GRUB passes is `/boot/microcode.img`,
CPU microcode only; the kernel applies it and, finding no `/init`, mounts
the root itself. That is also why the root cannot live on LVM, RAID or LUKS.

On the live ISO the root is read-only and `/var` is a tmpfs, seeded at boot
from `/usr/share/factory/var`. An installed system has a real `/var`; the
drop-in in `/etc/systemd/system/var.mount.d/` keeps the tmpfs off there.

**Swap** is two layers. `/dev/zram0` — zstd-compressed swap in RAM, half of
memory up to 8 GB — is active on every system including the live ISO, at
priority 100. An installed system also has `/swapfile` (RAM-sized, up to
8 GB, created by `aos-install`) at priority 10, which is what gives a large
build real headroom. `systemd-oomd` is configured the way Fedora ships it:
it kills on sustained memory pressure in a user session and when swap is
nearly full, before the kernel's own OOM killer has to.

## What is guaranteed present

**Toolchain.** gcc, g++, cpp, `cc`, binutils (as, ld, ar, nm, objdump,
readelf), make, rustc, cargo, pkgconf, flex.

**Init.** systemd, and deliberately all of it: units, journald, udev with
hwdb, logind, polkit, dbus-broker, systemd-networkd, systemd-resolved,
timesyncd, oomd, localed, vconsole, machined and nspawn, sysext, repart,
coredump and binfmt. AOS is not trying to be small; it is trying to be the
base that is hardest to knock over, and one supervisor, one log, one seat
manager, one network stack and one memory-pressure policy is the most widely
tested way to get there. Console logins go through PAM and register a logind
session, so anything you start from one has a seat and an `XDG_RUNTIME_DIR`
— which is what a Wayland compositor and its clients need.

**Self-recovery.** A hardware watchdog (iTCO, WDAT, SP5100, or QEMU's
i6300esb) petted by systemd every 30 s; a panic reboots after 10 s; a hard
lockup is a panic; oomd acts on memory pressure before the kernel's OOM
killer has to. Machine checks, ACPI platform errors and EDAC memory-controller
drivers put hardware faults in the journal by name. CPU microcode is applied
at boot, the frequency governor is `schedutil`, and `fstrim` runs weekly.

**GNU userland**: coreutils, bash (also `/bin/sh`), gawk, sed, grep,
findutils, diffutils, tar, gzip, bzip2, xz, zstd, patch, which, less, file,
vim; util-linux, procps, psmisc, kmod, kbd, shadow, iputils. There is no
BusyBox. This matters because `./configure` scripts, `build.rs` and kbuild
all depend on GNU behaviour that BusyBox does not reproduce exactly.

**Kernel and drivers.** A modular kernel with broad PC coverage: SATA/AHCI,
NVMe, legacy PATA, USB, HID, ext4/btrfs/xfs/f2fs/exfat/NTFS3/vfat, and wired
and wireless networking for the common Intel, Atheros, Realtek, MediaTek and
Broadcom parts, with firmware — including Intel Wi-Fi 6E and Wi-Fi 7
(AX210/AX211, BE200/BE201 and the Core Ultra Series 3 CNVi, which needs the
`iwlmld` driver) and the USB Ethernet adapters laptops actually use (ASIX,
Realtek, Microchip, CDC/RNDIS class). Intel GPUs from Lunar Lake on use the
`xe` driver and its `xe/` firmware; both are present alongside `i915`.
Realtek card readers (PCIe and USB) have their driver even though no card
may ever be inserted: an unbound PCIe reader never sleeps and floods the
machine with correctable PCIe errors.

On the screen the kernel logs at `loglevel=4`: errors and worse are shown,
warnings and below go to the journal. Serial consoles get everything.

**Getting back in.** The boot menu carries an *AOS (safe graphics, no GPU
driver)* entry — `nomodeset` — so a GPU driver that binds and then fails
cannot lock you out: boot that, read `journalctl -b -1`, fix. See
[docs/ssh.md](docs/ssh.md).

**Networking.** systemd-networkd and systemd-resolved, with every wired and
wireless interface on DHCP; iproute2, iw, wpa_supplicant, OpenSSL, a CA
bundle and curl. Enough that whatever fetches your first package can use TLS
on first boot.

**SSH.** An OpenSSH server, key authentication only — root has no password
and password authentication is off. A published image carries no key and so
accepts no login; the builder supplies one in
`board/aos/authorized_keys` before building. See [docs/ssh.md](docs/ssh.md).
An SSH login is a logind session, with a seat and an `XDG_RUNTIME_DIR`.

**Graphics.** libdrm, Mesa (GBM, EGL, OpenGL ES, Vulkan) and libglvnd.
Gallium drivers: iris, crocus, radeonsi, r600, nouveau, llvmpipe, zink.
Vulkan drivers: Intel, AMD, swrast, virtio, plus the Vulkan loader.
libwayland and wayland-protocols are present so writing a compositor does not
begin with adding packages.

Optionally, the NVIDIA open kernel modules and the matching proprietary
userspace (EGL, GLES, Vulkan and GSP firmware). These are off by default;
enable `BR2_PACKAGE_AOS_NVIDIA` to include them.

## What is deliberately absent

- **A package manager.** There is no dependency resolver, no repository and no
  update mechanism. Writing one is the intended first project.
- **A display server.** No X11 and no Wayland compositor. You get DRM/KMS,
  GBM, EGL and Vulkan, and you write the compositor.
- **Applications.** No editor beyond vim, no browser, no language runtimes
  other than Rust.
- **A GUI installer.** `aos-install` is a shell script.

## Building on top

The system compiles for itself. Nothing needs a cross-compiler or a build
host:

```sh
cc hello.c -o hello
cargo build --release
```

`libglvnd` means your compositor links against `libEGL.so.1` and
`libGL.so.1` generically, and the right vendor -- Mesa or NVIDIA -- is
selected per device at run time. Do not link a vendor library directly.

Vulkan ICDs are registered in `/usr/share/vulkan/icd.d/`, EGL vendors in
`/usr/share/glvnd/egl_vendor.d/`, and EGL external platforms in
`/usr/share/egl/egl_external_platform.d/`. Anything you add should follow
the same convention.

## Trying it in QEMU

```sh
./br2ext/board/aos/run-qemu.sh            # live ISO, UEFI, in a window
./br2ext/board/aos/run-qemu.sh bios       # live ISO, legacy BIOS
./br2ext/board/aos/run-qemu.sh install    # live ISO + a fresh blank 8G disk
./br2ext/board/aos/run-qemu.sh disk       # boot the disk you installed to
```

Log in as `root`, no password. Add `serial` as a second word to run in the
terminal instead of a window.

Two things people trip over:

- **Never run it with `sudo`.** QEMU with KVM needs no root; your user only
  needs `/dev/kvm`. A root run leaves the disk image and OVMF variables owned
  by root, after which a normal run cannot open them. The script refuses to
  run as root and prints the cleanup command.
- **Firmware variables are not kept between runs, on purpose.** OVMF saves
  its boot order in its variable store. Reusing one file across runs let a
  stale order put network boot (PXE) ahead of the ISO and the disk, so every
  mode dropped into the firmware and sat on `Start PXE over IPv4`. The
  script now uses a fresh copy of the store each run, pins the boot order
  with `bootindex`, and strips the NIC's PXE ROM. If you drive QEMU by hand,
  do the same.
- **The two boot menu entries differ only in where the login goes.** The
  first puts it on the screen, the second on the serial line. In a window,
  use the first; with `serial`, use the second. Kernel messages go to both
  either way.

## USB booting

**Two ways, and the second is the one that works everywhere.**

*Install AOS onto the stick* with `board/aos/write-usb.sh /dev/sdX
--install`. It boots the live ISO in QEMU with the physical stick attached
as a disk and runs `aos-install` on it, so the stick ends up an ordinary
installed system: GPT, a FAT32 EFI system partition at the front, an ext4
root, GRUB for UEFI and BIOS. That is the same shape as any installed OS,
which is why every firmware boots it, and it is persistent and writable —
what a machine you SSH into to build on needs.

*Write the live ISO* with `dd` (or `write-usb.sh /dev/sdX`). The image is
a hybrid: it boots from a stick under UEFI in QEMU, verified by attaching
the physical stick to OVMF (`--test`). But real firmware is choosier than
OVMF. One ASUS ROG Zephyrus G14 (GU405AP, AMI Aptio, BIOS 305 of June 2026)
never lists the stick at all — same port, same stick, Secure Boot and Fast
Boot off — while it lists a Fedora live stick, and the cause has not been
found. If a machine will not show it, use `--install` rather than fighting
the firmware. Legacy BIOS from the live ISO is untested either way: GRUB's
hybrid MBR code is present, but `-appended_part_as_gpt` leaves a
protective MBR with no active partition, and some BIOSes want one.

```sh
sudo ./br2ext/board/aos/write-usb.sh /dev/sdX          # live ISO, verified
sudo ./br2ext/board/aos/write-usb.sh /dev/sdX --test   # ...and booted in QEMU
sudo ./br2ext/board/aos/write-usb.sh /dev/sdX --install
```

The script refuses anything that is not a removable USB whole disk, reads
the written bytes back and compares them to the image, and moves the backup
GPT to the end of the medium — after `dd` it sits where the image ends,
which the kernel tolerates and some firmware does not.

Four things in `br2ext/external.mk` make the live ISO bootable from a stick
at all:

- `-append_partition 2 0xef … -appended_part_as_gpt` puts the EFI system
  partition Buildroot already builds for El Torito into a real GPT entry, so
  firmware finds `/EFI/BOOT/bootx64.efi` on a stick. `--grub2-mbr` adds
  GRUB's hybrid MBR for a legacy BIOS.
- A **FAT16** EFI system partition, 16 MiB, built by the override of
  `ROOTFS_ISO9660_INSTALL_BOOTLOADER_EFI` in `br2ext/external.mk`. Buildroot
  makes a 1 MiB image, which `mkfs.vfat` formats FAT12. OVMF under QEMU
  reads FAT12 without complaint; real firmware frequently does not, and the
  symptom is that the stick never appears in the boot menu at all. Every
  distribution ships FAT16 here.
- `-partition_offset 16` gives the ISO partition a second superblock of its
  own, making it a mountable `iso9660` filesystem rather than a window 32 KiB
  into one.
- `--gpt_disk_guid` pins the disk GUID so the ISO partition's PARTUUID is
  known before the image exists, since the boot menu has to name it. A
  post-generation hook reads the finished image back and fails the build if
  the two ever disagree.

The boot menu then picks the right `root=` for the medium it finds itself on:
`/dev/sr0` for an optical drive, whose partition table the kernel does not
read, and `root=PARTUUID=` for a stick, where there is no `/dev/sr0` at all.
`rootwait` is on both, because USB enumeration finishes long after the kernel
first looks for the root device.

Do not regenerate the ISO from a post-image script to change any of this.
Buildroot builds images inside a fakeroot session so everything is owned by
root, and post-image scripts run outside it: the rebuilt ISO comes out owned
by the build user, `/dev/console` becomes unopenable, and the system boots
into a cascade of permission errors. That was tried and reverted.

## Rebuilding AOS itself

AOS is a Buildroot `br2-external` tree. Buildroot itself is unmodified.

```sh
make BR2_EXTERNAL=$PWD/br2ext aos_x86_64_defconfig
make
```

Two Buildroot behaviours are worth internalising before you change anything:

1. **kconfig silently drops options whose dependencies are unmet.** A symbol
   you set in the defconfig can simply not appear in `.config`, with no
   warning. After loading a defconfig, grep `.config` to confirm the symbols
   you care about actually took.
2. **Changing the configuration does not rebuild already-built packages.** If
   you enable an option that changes how an existing package is configured,
   `make <pkg>-dirclean` that package or the change will not take effect --
   and the failure usually surfaces in some *other* package that expected the
   result.
