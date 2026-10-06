# Publishing AOS

## What to hand out

```sh
./br2ext/board/aos/release.sh            # -> output/release/
./br2ext/board/aos/release.sh --publish  # the same, then uploaded for aos-update
```

`release.sh` takes a tagged, clean build and writes `output/release/`: the
ISO renamed `aos-<version>-x86_64.iso`, the core image
`aos-<version>-x86_64-core.img` with its verity parameters
`aos-<version>-x86_64-core.verity` (what `aos-update` writes into a root
slot and checks it by), the legal-info manifest, the CVE report from `make pkg-stats`, and
`SHA256SUMS` over all of them signed with `apm sign` -- the same key that
signs the apm repositories, the one `apm key new` made, whose public half
is `keys/apm.pub` in [apm-recipes](https://github.com/Jaxilian/apm-recipes)
and is trusted by every AOS machine. `--publish` uploads the tarball,
`SHA256SUMS` and `SHA256SUMS.minisig` as assets of the apm package index's
release in apm-recipes (tag `index`), which is the URL in the image's
`/usr/lib/aos/update.conf`; the previous release's tarball is removed. The
ISO is handed out by hand. The version is the tag's (`v0.2.0` ->
`VERSION_ID=0.2.0`), written into `os-release` by `post-build.sh`;
`release.sh` refuses a `-dirty` build, and one carrying a root SSH key
([ssh.md](ssh.md)). The CVE report is Buildroot's
`pkg-stats`, whose `cve.py` wants two Python modules the host may lack
(`python3 -m pip install --user aiohttp setuptools` -- the second for
`distutils`, gone from Python 3.12); it fetches the NVD feed, minutes.

**The live ISO's account has no password.** `admin` logs in nowhere by
password, its sudo asks for none, and root logs in on the serial console
only (`/etc/securetty`). Say so when you publish it. An install does not: `aos-install` asks for the machine's own
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
