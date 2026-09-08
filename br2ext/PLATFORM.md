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

Standard FHS with a merged `/usr`, as systemd requires. Programs live in
`/usr/bin` and `/usr/sbin`, libraries in `/usr/lib`, and `/bin`, `/sbin` and
`/lib` are symlinks into `/usr`.

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

On an installed system, `/etc/fstab` has **no entry for `/`** — on purpose.
The kernel mounts the root from `root=PARTUUID=` in `/boot/grub/grub.cfg`,
read-write, and with no line to consult `systemd-remount-fs` leaves it alone.
`/boot/efi` is listed by `UUID=` with `nofail`; systemd waits for udev to
create the `/dev/disk/by-uuid` link before mounting it, and entries you add
by UUID work the same way.

On the live ISO the root is read-only and `/var` is a tmpfs, seeded at boot
from `/usr/share/factory/var`. An installed system has a real `/var`; the
drop-in in `/etc/systemd/system/var.mount.d/` keeps the tmpfs off there.

## What is guaranteed present

**Toolchain.** gcc, g++, cpp, `cc`, binutils (as, ld, ar, nm, objdump,
readelf), make, rustc, cargo, pkgconf, flex.

**Init.** systemd: units, journald, udev with hwdb, logind, D-Bus,
systemd-networkd, systemd-resolved, timesyncd and vconsole. Console logins
go through PAM and register a logind session, so anything you start from one
has a seat and an `XDG_RUNTIME_DIR` — which is what a Wayland compositor and
its clients need.

**GNU userland**: coreutils, bash (also `/bin/sh`), gawk, sed, grep,
findutils, diffutils, tar, gzip, bzip2, xz, zstd, patch, which, less, file,
vim; util-linux, procps, psmisc, kmod, kbd, shadow, iputils. There is no
BusyBox. This matters because `./configure` scripts, `build.rs` and kbuild
all depend on GNU behaviour that BusyBox does not reproduce exactly.

**Kernel and drivers.** A modular kernel with broad PC coverage: SATA/AHCI,
NVMe, legacy PATA, USB, HID, ext4/btrfs/xfs/f2fs/exfat/NTFS3/vfat, and wired
and wireless networking for the common Intel, Atheros, Realtek, MediaTek and
Broadcom parts, with firmware.

**Networking.** systemd-networkd and systemd-resolved, with every wired and
wireless interface on DHCP; iproute2, iw, wpa_supplicant, OpenSSL, a CA
bundle and curl. Enough that whatever fetches your first package can use TLS
on first boot.

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

**Not yet supported, and untested.** The ISO boots from optical media and in
VMs (BIOS and UEFI). Written to a USB stick with `dd` it has no partition
table, so a BIOS has nothing to boot and UEFI firmware finds no EFI system
partition. Buildroot's `HYBRID` option only exists for the isolinux path,
not the GRUB2 one this image uses.

Do not "fix" this by regenerating the ISO from a post-image script. Buildroot
builds images inside a fakeroot session so everything is owned by root, and
post-image scripts run outside it: the rebuilt ISO comes out owned by the
build user, `/dev/console` becomes unopenable, and the system boots into a
cascade of permission errors. That was tried and reverted.

The workable approach, when a stick is available to test against, is
`xorriso -indev … -outdev … -boot_image any replay` plus the isohybrid MBR
and GPT options, which rewrites only the boot records and copies the
filesystem image verbatim, preserving ownership. UEFI-from-USB additionally
needs the embedded GRUB config to *search* for its medium rather than assume
`(cd0)`, which `grub-embedded.cfg` already does.

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
