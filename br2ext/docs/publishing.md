# Publishing AOS

## What to hand out

```sh
./br2ext/board/aos/release.sh            # -> output/release/
./br2ext/board/aos/release.sh --publish  # the same, then uploaded for aos-update
./br2ext/board/aos/release.sh --publish --iso-to Jaxilian/aos-releases  # and the download page
```

`release.sh` takes a tagged, clean build and writes `output/release/`: the
ISO renamed `aos-<version>-x86_64.iso`, the core image
`aos-<version>-x86_64-core.img` with its verity parameters
`aos-<version>-x86_64-core.verity` (what `aos-update` writes into a root
slot and checks it by), the legal-info manifest, the CVE report from `make pkg-stats`, and
`SHA256SUMS` over all of them signed with `apm sign` -- the same key that
signs the apm repositories, the one `apm key new` made, whose public half
is `keys/apm.pub` in [apm-recipes](https://github.com/Jaxilian/apm-recipes)
and is trusted by every AOS machine. `--publish` uploads the core image,
its `.verity`, `SHA256SUMS` and `SHA256SUMS.minisig` as assets of the apm
package index's release in apm-recipes (tag `index`), which is the URL in
the image's `/usr/lib/aos/update.conf`; the previous release's core (and
any 0.1.x root tarball) is removed. The core goes up as it is, not
compressed again: it is a zstd squashfs already (746 MB for 0.2.8).
`--iso-to OWNER/REPO` makes the download page: a GitHub release
`v<version>` there with the ISO (825 MB for 0.2.8), `SHA256SUMS`, its
signature, `apm.pub` and the CVE report, and release notes made from the
commit subjects since the previous tag; AOS's is
[Jaxilian/aos-releases](https://github.com/Jaxilian/aos-releases).
The version is the tag's (`v0.2.0` -> `VERSION_ID=0.2.0`), written into
`os-release` by `post-build.sh`; `release.sh` refuses a `-dirty` build, a
build whose `BUILD_ID` is not `v<VERSION_ID>` (the tag must be on the
built commit: tag, then `make`), and one carrying a root SSH key or with
sshd enabled ([ssh.md](ssh.md)). The CVE report is Buildroot's
`pkg-stats`, whose `cve.py` wants two Python modules the host may lack
(`python3 -m pip install --user aiohttp setuptools` -- the second for
`distutils`, gone from Python 3.12); it fetches the NVD feed, minutes.

**The live ISO's account has no password.** `admin` logs in nowhere by
password, its sudo asks for none, and root logs in on the serial console
only (`/etc/securetty`). Say so when you publish it. An install does not: `aos-install` asks for the machine's own
account and installs that instead, with the login screen, unless told
`--demo`; `--oobe` leaves the account to the machine's first boot. See
the accounts section of [../PLATFORM.md](../PLATFORM.md).

## How people use it

**In a VM** — works, BIOS and UEFI. Tell them to set the CPU model to host
passthrough; AOS needs x86-64-v2 and most default QEMU CPU models are older.

**On a USB stick** — `sudo ./br2ext/board/aos/write-usb.sh /dev/sdX --install`,
or `./usb.sh` to build and write in one go (a stick carries no SSH key
and no listening sshd, like a release; [ssh.md](ssh.md)). This installs AOS onto the stick
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
