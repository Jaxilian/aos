# Publishing AOS

## What to hand out

One file, renamed, with a signed checksum and a licence manifest beside it:

```sh
cp output/images/rootfs.iso9660 aos-0.1.0-x86_64.iso
sha256sum aos-0.1.0-x86_64.iso > SHA256SUMS
minisign -Sm SHA256SUMS -s ~/.apm/etc/keys/apm.key
make legal-info && tar -C output -czf aos-0.1.0-legal-info.tar.gz legal-info
```

Sign with the same key that signs the apm repositories -- the one
`apm key new` made, in minisign format, whose public half is `keys/apm.pub`
in [apm-recipes](https://github.com/Jaxilian/apm-recipes). One key, already
trusted by every AOS machine, and the stock `minisign` tool verifies it.
Publish the public key next to the download, not only in the repository.

The version string lives in
`br2ext/board/aos/rootfs-overlay/usr/lib/os-release`. Bump it there before a
release so the running system reports the same version as the file.

**The live ISO carries the demo account.** `admin` with password
`123321`, and a passwordless root on the live system. Say so when you
publish it. An install does not: `aos-install` asks for the machine's own
account and installs that instead, unless told `--demo`. A live ISO with no
demo account needs the first-boot setup of [roadmap.md](roadmap.md),
Phase 2. See the accounts section of [../PLATFORM.md](../PLATFORM.md).

## How people use it

**In a VM** — works, BIOS and UEFI. Tell them to set the CPU model to host
passthrough; AOS needs x86-64-v2 and most default QEMU CPU models are older.

**On a USB stick** — `sudo ./br2ext/board/aos/write-usb.sh /dev/sdX --install`,
or `./usb.sh` to build and write in one go. This installs AOS onto the stick
as an ordinary system rather than writing the ISO, which is the form every
firmware boots. [usb.md](usb.md) has the procedure and the ways that failed.

**Burned to a DVD** — should work; the ISO is a proper dual El Torito image.

## What to say alongside it

Point at [what-is-aos.md](what-is-aos.md), and be direct about the things
that surprise people: there is one desktop and no way to install another;
third-party software is marked as such and carried at the user's risk; it
needs a 2009-or-newer 64-bit CPU; and Secure Boot must be off.

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

Mesa still covers Intel and AMD, and nouveau covers older NVIDIA cards. The
`make legal-info` report above is the full manifest; ship it with every
release.
