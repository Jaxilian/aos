# The AOS platform contract

AOS is a foundation, not a distribution. It gives you a kernel, a C library,
drivers, a graphics stack and a working toolchain -- and then stops. There is
no package manager, no init beyond BusyBox, no desktop, no applications. Those
are yours to write.

This document is the contract: what is guaranteed to be present, what is
deliberately absent, and what you can rely on when building on top.

## ABI baseline

| | |
|---|---|
| Architecture | x86_64, **x86-64-v2** baseline (SSE4.2 + POPCNT, ~2009 and later) |
| C library | glibc 2.43 |
| C/C++ compiler | gcc 15.3.0 |
| Rust | 1.96.1 (rustc + cargo) |
| Kernel | Linux 7.0.11 |
| binutils | as, ld and friends, on the target |

The v2 baseline is a deliberate trade. It rules out pre-2009 CPUs and buys
better code generation everywhere else. Anything you compile on an AOS machine
targets v2 by default, so it will run on any other AOS machine.

**This matters in a VM.** QEMU's default `qemu64` CPU model predates SSE4.2, so
an AOS image will panic on it with an invalid opcode inside `ld-linux`. Use
`-cpu Nehalem`, `-cpu host` or `-cpu max`.

## Filesystem layout

Standard FHS. Buildroot's skeleton decides whether `/usr` is merged; AOS does
not override it. Programs live in `/usr/bin` and `/usr/sbin`, libraries in
`/usr/lib`, and `/bin`, `/sbin` and `/lib` are symlinks into `/usr` when the
merged layout is active.

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

## What is guaranteed present

**Toolchain.** gcc, g++, cpp, `cc`, binutils (as, ld, ar, nm, objdump,
readelf), make, rustc, cargo, pkgconf, flex.

**GNU userland**, not BusyBox applets: coreutils, bash, gawk, sed, grep,
findutils, diffutils, tar, gzip, xz, zstd, patch, which, less, file.
BusyBox is present, but only as init and as a fallback for applets nothing
else provides. This matters because `./configure` scripts, `build.rs` and
kbuild all depend on GNU behaviour that BusyBox does not reproduce exactly.

**Kernel and drivers.** A modular kernel with broad PC coverage: SATA/AHCI,
NVMe, legacy PATA, USB, HID, ext4/btrfs/xfs/f2fs/exfat/NTFS3/vfat, and wired
and wireless networking for the common Intel, Atheros, Realtek, MediaTek and
Broadcom parts, with firmware.

**Networking.** dhcpcd, iproute2, iw, wpa_supplicant, OpenSSL, a CA bundle
and curl. Enough that whatever fetches your first package can use TLS on
first boot.

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
- **systemd.** Init is BusyBox with `/etc/inittab` and shell scripts in
  `/etc/init.d`. Replacing `/sbin/init` with your own is expected.
- **Applications.** No editor beyond what BusyBox provides, no browser, no
  language runtimes other than Rust.
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
