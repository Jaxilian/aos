# What is in the image

Versions are those pinned by Buildroot 2026.08. Regenerate this list from a
finished build with:

```sh
ls output/build | grep -vE '^(host-|buildroot-|\.)' | sed 's/-\([0-9].*\)$/ \1/'
```

Installed size is **2.6 GB**. The ISO is 956 MB because it is compressed.

## Where the size goes

| Part | Size | Note |
|---|---|---|
| Mesa, LLVM, Vulkan | 618 MB | LLVM is most of it; needed by iris, radeonsi, llvmpipe |
| NVIDIA userspace | 338 MB | Proprietary; optional |
| Firmware | 392 MB | Wireless and GPU, selected per vendor |
| gcc | 144 MB | Compiler binaries and internal headers |
| Rust | 149 MB | rustc, cargo, standard library |
| Kernel modules | 122 MB | 115 modules |
| Headers | 128 MB | `/usr/include` — what makes it self-hosting |

## Core

| Package | Version |
|---|---|
| linux | 7.1.13 |
| glibc | 2.44 |
| systemd | 258.7 (init, journald, udev, logind, networkd, resolved) |
| dbus | 1.16.2 |
| linux-pam | 1.7.2 |
| grub2 | 2.14 (BIOS and UEFI) |
| linux-firmware | 20260810 |

## Toolchain — the self-hosting part

| Package | Version | Note |
|---|---|---|
| aos-gcc | 15.3.0 | gcc and g++ that run *on* AOS. Custom package |
| aos-rust | 1.96.1 | rustc and cargo on the target. Custom package |
| binutils | 2.44 | as, ld, ar, nm, objdump |
| make | 4.4.1 | |
| gmp / mpfr / mpc | 6.3.0 / 4.2.2 / 1.4.1 | gcc's arithmetic libraries |
| pkgconf | 2.3.0 | |
| flex | 2.6.4 | |

Buildroot does not support putting a toolchain on the target — `aos-gcc` and
`aos-rust` exist to work around exactly that.

## GNU userland

Real GNU tools, and no BusyBox at all, because `./configure`, cargo's
`build.rs` and kbuild all depend on GNU behaviour BusyBox does not reproduce.

coreutils 9.10 · bash 5.2.37 (also `/bin/sh`) · gawk 5.4.0 · sed 4.10 ·
grep 3.12 · findutils 4.10.0 · diffutils 3.12 · tar 1.35 · gzip 1.14 ·
bzip2 1.0.8 · xz 5.8.3 · zstd 1.5.7 · patch 2.7.6 · less 704 · file 5.47 ·
which · vim 9.2 ·
ncurses 6.6 · readline 8.3 · kmod 34.2 · kbd 2.9.0 (console keymaps) ·
procps-ng 4.0.6 · psmisc 23.7 · util-linux 2.41.5 (mount, su, agetty) ·
shadow 4.18.0 (login, passwd, useradd) · iputils 20250605 (ping) ·
libseccomp 2.6.0

## Graphics

| Package | Version |
|---|---|
| mesa3d | 26.1.8 |
| llvm / clang | 22.1.8 |
| libdrm | 2.4.134 |
| libglvnd | 1.7.0 |
| wayland | 1.24.0 (libwayland only — no compositor) |
| wayland-protocols | 1.48 |
| aos-nvidia / aos-nvidia-open | 610.57.04 |

Gallium drivers: iris, crocus, radeonsi, r600, nouveau, llvmpipe, zink.
Vulkan drivers: Intel, AMD, llvmpipe (lvp), virtio, and NVIDIA from the blob.
There is no X server and no Wayland compositor — you write that.

## Networking and storage

wpa_supplicant 2.12 · iw 6.17 · iproute2 7.1.0 · libnl 3.12.0 ·
openssl 3.6.4 · ca-certificates 20260223 · libcurl 8.22.0 ·
e2fsprogs 1.47.4 · dosfstools 4.2 · parted 3.6 · efibootmgr 18

## The four custom packages

Everything above comes from Buildroot except these, which live in
`br2ext/package/`:

- **aos-gcc** — gcc built "crossed-native": built on your machine, runs on
  AOS, compiles for AOS. Reuses Buildroot's exact gcc source so the compiler
  matches its own runtime libraries.
- **aos-rust** — the official upstream Rust binaries, installed to the target.
  Building rustc from source would need LLVM and a bootstrap compiler.
- **aos-nvidia-open** — NVIDIA's open kernel modules, dual MIT/GPL.
- **aos-nvidia** — NVIDIA userspace and GSP firmware. Proprietary, off by
  default.
