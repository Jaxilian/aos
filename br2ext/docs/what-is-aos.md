# What is AOS?

**AOS is a Linux distribution with one desktop, one package manager and one
way to do things.**

It is built for people who want a computer that works — for games, for work,
for anything — without ever opening a terminal. There is one desktop
environment, ade, and no other. There is one package manager, apm, and
software arrives no other way. Applications written for AOS use one native
GUI stack; applications written for other systems run as well, clearly marked
as third-party, at the user's own risk.

The base underneath is deliberately unadventurous: a modern Linux kernel,
glibc, systemd in full, drivers for ordinary PC hardware, Mesa and the NVIDIA
driver. It compiles its own software — gcc is on the machine, and Rust is one
`apm install` away — so the platform can be developed on the platform.

## What makes it unusual

**One of everything.** Most distributions offer several desktops, several
package formats, and several ways to configure the same thing. AOS offers
one. That is what makes "install it and it works" possible, and what makes
it worth a developer's time: an application that runs on one AOS machine
runs on every AOS machine.

**Two tiers of software, and the line is visible.** Official packages are
built and tested for each release and are what AOS recommends. Third-party
packages — Electron applications, GTK programs, Steam — are carried so the
things people expect to run, run. They are labelled as third-party
everywhere they appear, and may break with an update. That is the deal.

**It targets real PCs.** Intel, AMD and NVIDIA graphics, wired and wireless
networking with firmware, USB, NVMe, SATA and legacy PATA. Roughly any
x86-64 machine from 2009 onwards.

**It is honest about what a compatibility layer is.** XWayland is available
and off by default; the user turns it on when a third-party program needs
it. No official package depends on it.

## What it includes

| | |
|---|---|
| Kernel | Linux 7.1.13, modular, ~115 driver modules |
| C library | glibc 2.44 |
| Init | systemd 258.7, all of it — journald, udev, logind, polkit, networkd, resolved, oomd, nspawn |
| Desktop | ade: a Wayland compositor on smithay, and a shell on the awin/tgn Vulkan stack |
| Package manager | apm, with an official repository and a third-party one |
| Applications | terminal, notepad, files, sysmon, settings; Visual Studio Code and more from the third-party repository |
| Compilers | gcc 15.3.0 (C and C++) on the image; Rust 1.96.1 with cargo through apm |
| Userland | Real GNU tools — coreutils, bash, gawk, sed, grep, tar, findutils, vim |
| Graphics | Mesa 26.1.8, Vulkan, libglvnd, NVIDIA 610.57.04 |
| Sound | PipeWire 1.6 and WirePlumber, per session; ALSA and PulseAudio programs route into it |
| Networking | systemd-networkd, wpa_supplicant, iw, OpenSSL, curl, CA certificates |
| Architecture | x86-64-v2 (roughly 2009 and newer) |

Full list with versions: [packages.md](packages.md). Where it is going:
[roadmap.md](roadmap.md).

## What it does not include

No second desktop, and no way to install one. No X11 server — XWayland is
the compatibility layer, off by default. No graphical installer, settings
application, app store or base-OS updater yet; those are the next phase of
work and are what [roadmap.md](roadmap.md) is about.

## The short answer

> AOS is a Linux distribution with exactly one desktop, one package manager
> and one native GUI stack, aimed at people who want a computer that works
> without a terminal. Its own applications are built on that stack;
> software written for other systems runs too, marked as third-party and at
> the user's risk. Underneath is systemd, glibc, Mesa and NVIDIA graphics,
> and a compiler, on any x86-64 PC from 2009 onwards.
