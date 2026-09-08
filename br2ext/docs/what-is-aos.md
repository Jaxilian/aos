# What is AOS?

**AOS is a foundation for building an operating system, not an operating
system you use.**

It gives you a modern Linux kernel, a C library, drivers for ordinary PC
hardware, a full graphics stack, and a working compiler — and then it stops.
There is no package manager, no desktop, no applications. Those are yours to
write, and AOS is designed so you can write them *on the machine itself*.

Think of it as the layer every distribution has underneath it, packaged on its
own and nothing more.

## What makes it unusual

**It compiles itself.** Most minimal Linux images are built on one machine and
run on another; they contain no compiler. An AOS machine has gcc, g++, Rust
and cargo, plus the headers and link libraries to use them. You can write your
package manager on AOS, for AOS, without a second computer.

**It stops deliberately.** The absence of a package manager and a desktop is
the product, not an unfinished edge. AOS defines a stable base — a fixed ABI,
a documented filesystem layout, working drivers — and leaves every decision
above that line to you.

**It targets real PCs.** Broad hardware coverage: Intel, AMD and NVIDIA
graphics, wired and wireless networking with firmware, USB, NVMe, SATA and
legacy PATA. Roughly any x86-64 machine from 2009 onwards.

## What it includes

| | |
|---|---|
| Kernel | Linux 7.1.13, modular, ~115 driver modules |
| C library | glibc 2.44 |
| Compilers | gcc 15.3.0 (C and C++), Rust 1.96.1 with cargo |
| Init | systemd, all of it — journald, udev, logind, polkit, networkd, resolved, oomd, nspawn |
| Userland | Real GNU tools — coreutils, bash, gawk, sed, grep, tar, findutils, vim |
| Graphics | Mesa 26.1.8, Vulkan, libglvnd, NVIDIA 610.57.04 |
| Networking | systemd-networkd, wpa_supplicant, iw, OpenSSL, curl, CA certificates |
| Keyboard | kbd, with every common console layout |
| Architecture | x86-64-v2 (roughly 2009 and newer) |

Full list with versions: [packages.md](packages.md).

## What it does not include

No package manager. No display server — no X11, no Wayland compositor. No
editor beyond vim, no browser, no language runtimes other than Rust.

## The short answer

> AOS is a minimal Linux foundation for people who want to build their own
> operating system. It is the kernel, glibc, PC drivers, Mesa and NVIDIA
> graphics, and a self-hosting C and Rust toolchain — about 2.6 GB installed.
> It has no package manager, no desktop and no applications, because those are
> what you are expected to write. It boots on most x86-64 PCs from 2009
> onwards and can compile its own software without another machine.
