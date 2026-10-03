# AOS documentation

Short guides for working on AOS. Start here.

For someone using AOS rather than building it:

- [install.md](install.md) — from the download to a working desktop
- [known-issues.md](known-issues.md) — what does not work yet, and what to do about it
- [security-status.md](security-status.md) — the CVE report of the release, triaged
- [security-model.md](security-model.md) — what AOS defends against, how, and what is still to build

For working on AOS:

- [what-is-aos.md](what-is-aos.md) — what AOS is: one desktop, one package manager, one stack
- [packages.md](packages.md) — everything in the image, with versions
- [building.md](building.md) — how to build it
- [upgrading.md](upgrading.md) — how to move to a newer kernel or package
- [keyboard.md](keyboard.md) — changing the console keyboard layout
- [testing.md](testing.md) — how to run and test it
- [performance.md](performance.md) — the baseline per release, and what it says to do
- [usb.md](usb.md) — making a USB stick that actually boots (`./usb.sh` does it all), and every way that failed
- [ssh.md](ssh.md) — remote access, and the key you must add before building
- [roadmap.md](roadmap.md) — the platform contract, and the plan to an alpha: release engineering, trust, the no-terminal user path, stability, hardware
- [publishing.md](publishing.md) — how to hand the image to someone else
- [policies.md](policies.md) — what AOS promises and has decided: cadence, no telemetry, Secure Boot, encryption, updates

The platform contract — what AOS guarantees to software built on top of it —
is one level up in [../PLATFORM.md](../PLATFORM.md).

## Why this folder is here and not at the repository root

The root of this repository is an unmodified Buildroot checkout, and Buildroot
already has its own `docs/` (its manual). Everything specific to AOS lives
under `br2ext/`, so that `git pull` on Buildroot never conflicts with our work.
