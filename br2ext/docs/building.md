# Building AOS

## First build

```sh
make BR2_EXTERNAL=$PWD/br2ext aos_x86_64_defconfig
make
```

The first build takes roughly **2 to 4 hours** on 16 cores, most of it LLVM,
Mesa and gcc (gcc is built twice: once as the cross compiler, once as the
compiler that runs on AOS). Later builds are far quicker because Buildroot
only rebuilds what changed.

You only need `BR2_EXTERNAL=` the first time. Buildroot records the path in
`output/.br2-external.mk`, so plain `make` works afterwards.

## Where the output goes

Everything lands in `output/images/`:

| File | Size | What it is |
|---|---|---|
| `rootfs.iso9660` | ~956 MB | **The AOS image.** Bootable ISO, BIOS and UEFI |
| `bzImage` | ~11 MB | The kernel on its own |
| `rootfs.tar` | ~2.6 GB | The whole filesystem as a tarball |
| `rootfs.ext2` | 4 GB | The filesystem as a disk image |
| `aos-disk.img` | 8 GB | Scratch disk used by `run-qemu.sh install` |

`rootfs.iso9660` is the one you give people. It is compressed with zisofs, so
956 MB on disk expands to about 2.6 GB once installed.

`output/` is not in git — it is entirely rebuildable from `br2ext/`.

## Host requirements

A Linux machine with about 30 GB free and the usual build tools. On Fedora,
Buildroot's own dependency check misses several Perl modules that Fedora ships
separately; without them the build fails partway through:

```sh
sudo dnf install perl-Time-Piece perl-Digest-SHA perl-Pod-Html perl-Test-Simple \
  perl-ExtUtils-CBuilder perl-ExtUtils-Embed perl-Term-ReadLine perl-autodie \
  perl-Thread-Semaphore perl-Memoize perl-Sys-Hostname perl-Compress-Raw-Zlib \
  perl-IO-Compress perl-IO-Zlib perl-Archive-Tar perl-bignum perl-open \
  perl-IPC-SysV perl-Text-Abbrev
```

For testing you also want `qemu-system-x86` and `edk2-ovmf`.

## Two Buildroot behaviours that will bite you

**1. Options you set can vanish silently.** If a symbol's dependencies are not
met, kconfig drops it with no warning at all — the build succeeds and the
feature is simply missing. This has happened four times on this project. After
changing the defconfig, always check the symbol actually took:

```sh
make BR2_EXTERNAL=$PWD/br2ext aos_x86_64_defconfig
grep BR2_PACKAGE_MESA3D_LLVM .config      # expect =y, not "is not set"
```

**2. Changing config does not rebuild a package.** If you enable an option that
changes how an already-built package is configured, Buildroot will not redo it.
Force it:

```sh
make <package>-dirclean && make
```

The failure usually shows up in some *other* package that expected the result,
which makes it confusing. When in doubt about a specific package, dirclean it.

**3. Nothing is ever removed from `output/target`.** A package installs
into the target and Buildroot never uninstalls: change a package so that
it installs fewer files -- an option turned off, a unit no longer built --
and `<package>-dirclean && make` leaves the old files exactly where they
were. The symptom is a thing you turned off still running. Delete the
stale files by hand (`output/build/packages-file-list.txt` says which
package, if any, still claims a file) or build clean; CI always does.

## Adding a package

Most things are already in Buildroot — add the symbol to
`br2ext/configs/aos_x86_64_defconfig`, reload, verify it took, and `make`.

For something Buildroot does not have, write a package under
`br2ext/package/<name>/` following the four in there now, and add a `source`
line to `br2ext/Config.in`. Check the style before building:

```sh
./utils/check-package --br2-external br2ext/package/<name>/*
```

## Working on ade, apm, terminal, notepad or files

Each of those is its own repository, and the OS builds it from a tagged
commit named in `br2ext/package/<name>/<name>.mk` — the way it builds
everything else. That is what makes an image reproducible: two people
building the same commit of this tree get the same binaries, and no build
depends on what happens to be in a working tree on one machine.

While you change one of them, point the OS at your checkout instead. Create
`local.mk` at the repository root (it is ignored by git) with a line per
package:

```make
ADE_OVERRIDE_SRCDIR = /home/jax/Projects/OS/ade
TERMINAL_OVERRIDE_SRCDIR = /home/jax/Projects/Rust/terminal
```

Then `make ade-rebuild` (or `-reconfigure`) picks up the working tree,
uncommitted changes included. This is Buildroot's own mechanism; the manual
calls it `<pkg>_OVERRIDE_SRCDIR`. A package built this way vendors its
crates at build time (`AOS_CARGO_VENDOR` in `external.mk`), which needs the
network once per rebuild.

To ship the change: commit, tag, push, and put the new commit in the `.mk`.
The SDK -- awin and tgn, in the `aos-sdk` repository -- is a git dependency
of every application at a tag, so a change there is tagged first and the
applications move to the new tag in their `Cargo.toml`.
