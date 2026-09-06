# Publishing AOS

## What to hand out

One file:

```
output/images/rootfs.iso9660      ~956 MB
```

Rename it to something meaningful first, and publish a checksum next to it:

```sh
cp output/images/rootfs.iso9660 aos-0.1.0-x86_64.iso
sha256sum aos-0.1.0-x86_64.iso > aos-0.1.0-x86_64.iso.sha256
```

The version string lives in
`br2ext/board/aos/rootfs-overlay/usr/lib/os-release`. Bump it there before a
release so the running system reports the same version as the file.

## How people use it

**In a VM** — works today, BIOS and UEFI. This is the tested path. Tell them
to set the CPU model to host passthrough; AOS needs x86-64-v2 and most
default QEMU CPU models are older.

**Burned to a DVD** — should work; the ISO is a proper dual El Torito image.

**Written to a USB stick — not yet.** `dd` of this ISO produces a stick with
no partition table, so a BIOS has nothing to boot and UEFI finds no EFI system
partition. See the USB section in [../PLATFORM.md](../PLATFORM.md) for why,
and for the approach to fix it. Say so plainly when you publish, rather than
letting people discover it.

## What to say alongside it

Point at [what-is-aos.md](what-is-aos.md), and be direct about the two things
that surprise people: there is no package manager and no desktop, on purpose;
and it needs a 2009-or-newer 64-bit CPU.

## Licensing

Almost everything is open source. The exception is the NVIDIA userspace
driver, which is proprietary. Its kernel modules are dual MIT/GPL and freely
redistributable; the userspace half is under NVIDIA's licence, which permits
redistribution unmodified and with the licence text included. AOS ships that
text at `/usr/share/licenses/nvidia/LICENSE`.

If you would rather publish something with no proprietary code, turn NVIDIA
off and rebuild:

```
# BR2_PACKAGE_AOS_NVIDIA is not set
```

Mesa still covers Intel and AMD, and nouveau covers older NVIDIA cards. To
produce a full licence manifest of everything in the image, run
`make legal-info`; the report lands in `output/legal-info/`.
