# What is in the image

Versions are those pinned by Buildroot 2026.08. Regenerate this list from a
finished build with:

```sh
ls output/build | grep -vE '^(host-|buildroot-|\.)' | sed 's/-\([0-9].*\)$/ \1/'
```

Installed size is **2.4 GB**. The core (`core.img`, squashfs) is 746 MB and
the ISO 825 MB because they are compressed.

## Where the size goes

| Part | Size | Note |
|---|---|---|
| Mesa, LLVM, Vulkan | 697 MB | LLVM is most of it; needed by iris, radeonsi, llvmpipe |
| NVIDIA userspace | 340 MB | Proprietary; optional |
| Firmware | 491 MB | Wireless, audio and GPU, selected per vendor; NVIDIA's GSP firmware is 109 MB of it |
| gcc | 143 MB | Compiler binaries and internal headers |
| Kernel modules | 147 MB | 426 modules |
| Headers | 127 MB | `/usr/include` — what makes it self-hosting |

Rust is not in the image: it is the apm package `aos/rust`.

## Core

| Package | Version |
|---|---|
| linux | 7.2.9 |
| glibc | 2.44 |
| systemd | 258.7 (init, journald, udev, logind, networkd, resolved, oomd, machined, sysext, repart) |
| dbus-broker | 37 |
| polkit | 126 |
| linux-pam | 1.7.2 |
| cryptsetup | 2.8.7 (veritysetup for the cores, LUKS2 for the aos partition) |
| bubblewrap | 0.11.2 (under `aos-sandbox`) |
| sudo | 1.9.17p2 |
| grub2 | 2.14 (BIOS and UEFI) |
| linux-firmware | 20260810 |
| sof-firmware | 2026.09.1 (sof-bin: the Intel audio DSP firmware and topologies, 57 MB; a custom package) |
| linux-firmware, Cirrus | `cs42l43.bin` and `cirrus/` (codec firmware, amplifier tunings by machine; 7 MB), added by `external.mk` since Buildroot has no option: without them a SoundWire codec never probes and the machine has no sound card |

## Toolchain — the self-hosting part

| Package | Version | Note |
|---|---|---|
| aos-gcc | 15.3.0 | gcc and g++ that run *on* AOS. Custom package |
| rust | 1.96.1 | rustc and cargo, as the apm package `aos/rust`, not in the image since 2026-09-20 |
| binutils | 2.46.1 | as, ld, ar, nm, objdump |
| make | 4.4.1 | |
| gmp / mpfr / mpc | 6.3.0 / 4.2.2 / 1.4.1 | gcc's arithmetic libraries |
| pkgconf | 2.3.0 | |
| flex | 2.6.4 | |

Buildroot does not support putting a toolchain on the target — `aos-gcc`
exists to work around exactly that (and `aos-rust` did, until Rust moved to
apm).

## GNU userland

Real GNU tools, and no BusyBox at all, because `./configure`, cargo's
`build.rs` and kbuild all depend on GNU behaviour BusyBox does not reproduce.

coreutils 9.12 · bash 5.2.37 (also `/bin/sh`) · gawk 5.4.1 · sed 4.10 ·
grep 3.12 · findutils 4.10.0 · diffutils 3.12 · tar 1.35 · gzip 1.15 ·
bzip2 1.0.8 · xz 5.8.3 · zstd 1.5.7 · patch 2.8 · less 704 · file 5.47 ·
which · vim 9.2 ·
ncurses 6.6 · readline 8.3 · kmod 34.2 · kbd 2.9.0 (console keymaps) ·
procps-ng 4.0.6 · psmisc 23.7 · util-linux 2.42.4 (mount, su, agetty) ·
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
| libX11, libxcb and the X client libraries | for GLX, the X11 compatibility layer's; no X server |

Gallium drivers: iris, crocus, radeonsi, r600, nouveau, llvmpipe, zink.
Vulkan drivers: Intel, AMD, llvmpipe (lvp), virtio, and NVIDIA from the blob.
There is no X server. The Wayland compositor is ade, below.

## Desktop

| Package | Version |
|---|---|
| ade | v0.1.47, 4654b89 (the compositor, shell and lock screen) |
| ade-greeter | fa02ac8, untagged (the login screen) |
| greetd | 0.10.3 (the login daemon ade-greeter runs under) |
| aos-setup | v0.1.4-5-g88e7a54 (the installer and the first-boot setup) |
| aos-store | v0.2.7, dae6ffc (Software: apps and OS updates) |
| settings | v0.1.26, 45bd7da |
| files | v0.1.8-3-g0d1178c |
| images | v0.1.8-2-ge088064 (the image viewer) |
| notepad | v0.1.7-1-g9337211 |
| terminal | v0.1.8-2-ga39a93a |
| sysmon | v0.1.5-2-g35bf52f |
| apm | v0.1.12 |
| libinput | 1.31.3 |
| libxkbcommon | 1.9.2 |
| seatd | 0.9.1 (libseat only; it talks to logind) |
| xkeyboard-config | 2.38 (keymap data; xkbcomp for XWayland) |

The AOS programs are the commits pinned in `br2ext/package/<pkg>/<pkg>.mk`,
shown as `git describe --tags`; where the repository's tags stop short of
the release named in its commit message (ade, store, settings), that name
and the commit. All of them build on aos-sdk v0.4.16 (awin and tgn).

## Sound

| Package | Version | Note |
|---|---|---|
| pipewire | 1.6.6 | the sound server, as user services of the session; pipewire-pulse built in |
| wireplumber | 0.5.14 | PipeWire's session manager; lua 5.4 is its scripting language |
| alsa-lib | 1.2.16.1 | and the ALSA plugin that routes ALSA programs into PipeWire |
| alsa-ucm-conf | 1.2.16.1 | the UCM2 profiles; a SoundWire card stays silent without its own (a custom package) |
| acl | 2.4.0 | what lets systemd install `70-uaccess.rules`, so the seat's user can open the card |
| bluez5_utils | 5.86 | bluetoothd (started by udev's `bluetooth.target` when an adapter appears, the adapter powered on by `/etc/bluetooth/main.conf`), bluetoothctl for Settings, the audio and HID plugins |
| sbc, opus | | the Bluetooth audio codecs; sbc is what makes PipeWire build its BlueZ backend |
| upower | 0.99.19 | battery, lid and power source over D-Bus for the programs that ask (Firefox, Electron, GTK); D-Bus activated |

Versions are the ones Buildroot 2026.08 pins; check `output/build`.

`ade.service` takes tty1 as the `ade` user, so `getty@tty1` does not run
there. Two UTF-8 locales are generated (`BR2_GENERATE_LOCALE`: en_US and
sv_SE) and the first selected in `/etc/locale.conf`: the terminal decodes
UTF-8 itself, but everything running inside it goes through the C
library's idea of the charset, and Steam's container refuses a LANG the
host has not compiled.

No official program needs a font file or fontconfig: every one that draws
text is an awin + tgn one and compiles in the face it needs — tgn its own,
the terminal Liberation Mono, because a grid cannot use a proportional
face. fontconfig is on the image all the same (`fc-list`, `/etc/fonts`,
naming `/usr/share/fonts`, where the fonts package puts DejaVu and
Liberation), with shared-mime-info and desktop-file-utils: third-party
programs assume all three exist, and Firefox reports an error for each
`update-*-database` it cannot run.

## Networking and storage

wpa_supplicant 2.12 · iw 6.17 · iproute2 7.1.0 · libnl 3.12.0 ·
openssl 3.6.4 · ca-certificates 20260223 · libcurl 8.22.0 · nftables 1.1.4 ·
openssh 10.5p1 · e2fsprogs 1.47.4 · dosfstools 4.2 · parted 3.6 · efibootmgr 18

## The custom packages

Everything above comes from Buildroot except these, which live in
`br2ext/package/`:

- **aos-gcc** — gcc built "crossed-native": built on your machine, runs on
  AOS, compiles for AOS. Reuses Buildroot's exact gcc source so the compiler
  matches its own runtime libraries.
- **aos-rust** — the official upstream Rust binaries, installed to the
  target. Not selected since Rust moved to apm; kept for a build that wants
  it in the image.
- **aos-nvidia-open** — NVIDIA's open kernel modules, dual MIT/GPL.
- **aos-nvidia** — NVIDIA userspace and GSP firmware. Proprietary; off by
  default in Buildroot terms, selected by the AOS defconfig.
- **ade**, **ade-greeter**, **aos-setup**, **aos-store**, **settings**,
  **files**, **images**, **notepad**, **terminal**, **sysmon**, **apm** —
  the AOS programs above, each fetched from its own GitHub repository at a
  pinned commit, its cargo dependencies vendored with a `.hash`. A working
  tree is built instead through `<PKG>_OVERRIDE_SRCDIR` in `local.mk`.
  ade selects terminal, because Super+Return spawning nothing would leave
  the session with no way to reach a shell.
- **greetd** — the login daemon, which Buildroot does not have.
- **sof-firmware** — the Intel audio DSP firmware and topologies (sof-bin).
- **alsa-ucm-conf** — the ALSA UCM2 profiles, which Buildroot does not have.
- **aos-desktop-file-utils** — update-desktop-database and
  desktop-file-validate on the target; Buildroot builds them for the host
  only, and third-party programs expect them.
- **libnsl** — the NIS client library glibc dropped; Steam's `steamui.so`
  still links it.
