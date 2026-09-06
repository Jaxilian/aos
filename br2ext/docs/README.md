# AOS documentation

Short guides for working on AOS. Start here.

- [what-is-aos.md](what-is-aos.md) — what AOS is, and what it includes
- [packages.md](packages.md) — everything in the image, with versions
- [building.md](building.md) — how to build it
- [upgrading.md](upgrading.md) — how to move to a newer kernel or package
- [keyboard.md](keyboard.md) — changing the console keyboard layout
- [testing.md](testing.md) — how to run and test it
- [publishing.md](publishing.md) — how to hand the image to someone else

The platform contract — what AOS guarantees to software built on top of it —
is one level up in [../PLATFORM.md](../PLATFORM.md).

## Why this folder is here and not at the repository root

The root of this repository is an unmodified Buildroot checkout, and Buildroot
already has its own `docs/` (its manual). Everything specific to AOS lives
under `br2ext/`, so that `git pull` on Buildroot never conflicts with our work.
