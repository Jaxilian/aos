# Upgrading

## The kernel

The kernel version comes from one line in
`br2ext/configs/aos_x86_64_defconfig`:

```
BR2_LINUX_KERNEL_LATEST_VERSION=y
```

That means "whatever this Buildroot release considers latest" — currently
**7.0.11**. It does not follow new kernels on its own; it moves when Buildroot
itself is upgraded.

To pin a specific version instead, replace that line with:

```
BR2_LINUX_KERNEL_CUSTOM_VERSION=y
BR2_LINUX_KERNEL_CUSTOM_VERSION_VALUE="7.1.12"
```

Then rebuild the kernel and the image:

```sh
make BR2_EXTERNAL=$PWD/br2ext aos_x86_64_defconfig
make linux-dirclean
make
```

Two things to watch. Buildroot's kernel patches and `linux-firmware` are tested
against the version it ships, so a hand-picked kernel is less well tested. And
the NVIDIA modules must support it — 610.57.04 builds against 7.x, but a much
newer kernel may need a newer driver.

## Kernel options

Driver and feature choices live in
`br2ext/board/aos/linux.config.fragment`, applied on top of the mainline
`x86_64_defconfig`. Add a line, then:

```sh
make linux-reconfigure && make
```

Always confirm the option survived — the mainline defconfig or another symbol
can override it:

```sh
grep CONFIG_YOUR_OPTION output/build/linux-*/.config
```

## The NVIDIA driver

Two files, and the version must match in both:

- `br2ext/package/aos-nvidia-open/aos-nvidia-open.mk` — kernel modules
- `br2ext/package/aos-nvidia/aos-nvidia.mk` — userspace and GSP firmware

Change `_VERSION`, update the `.hash` files with the new checksums, then:

```sh
make aos-nvidia-dirclean aos-nvidia-open-dirclean && make
```

The GSP firmware must end up under `/lib/firmware/nvidia/<version>/`. The
kernel module builds that path from its own version string, so a mismatch
means the module loads and the GPU never initialises.

## Rust

`br2ext/package/aos-rust/aos-rust.mk`. Change `AOS_RUST_VERSION`, update
`aos-rust.hash` (upstream publishes a `.sha256` next to each tarball), then
`make aos-rust-dirclean && make`.

## gcc and glibc

These come from Buildroot itself, chosen in the defconfig
(`BR2_GCC_VERSION_15_X=y`). Changing gcc means rebuilding the whole toolchain
and everything above it — effectively a full rebuild. Note that `aos-gcc`
deliberately reuses whatever version Buildroot uses, so the compiler on the
target always matches its own runtime libraries.

## Buildroot itself

The root of this repository is a Buildroot release tree, imported as a single
commit with no upstream history behind it. Everything AOS adds lives under
`br2ext/`, and outside of it the tree is untouched — the diff against the
import commit is one file, `.gitignore`. That makes an upgrade a clean swap:
delete everything except `br2ext/`, and put a newer release in its place.

Buildroot versions are dates, not a running count. `2026.05.1` is the May 2026
release plus its first point update. There is a new release every three months
— `.02`, `.05`, `.08`, `.11` — and point releases on each branch for a while
after. A version that looks old usually just means this tree has not been
touched in a while, not that the project stopped.

Which version you are on:

```sh
grep '^export BR2_VERSION :=' Makefile
```

### One-time: add the upstream remote

`origin` is the AOS repository, so it has nothing to do with Buildroot. There
is nothing to pull from until you add it:

```sh
git remote add buildroot https://gitlab.com/buildroot.org/buildroot.git
git fetch buildroot --tags
```

Then see what is out, ignoring the release candidates:

```sh
git tag -l '20*' | grep -v rc | sort -V | tail
```

Two kinds of upgrade are worth telling apart. Moving along the branch you are
already on — `2026.05.1` to `2026.05.2` — is security and bugfix only: no new
kernel, no new toolchain, and only a few packages rebuild. Moving to a new
quarterly release — `2026.05` to `2026.08` — brings a new kernel, Mesa, LLVM
and usually a new gcc, which means a full rebuild.

### Doing the swap

Commit or stash anything under `br2ext/` first; this deletes files.

```sh
git ls-files -z | grep -zv '^br2ext/' | xargs -0 rm -f
git checkout 2026.08 -- .
git add -A -- . ':!br2ext'
git commit -m "buildroot 2026.08"
```

The delete is the part people skip. `git checkout <tag> -- .` restores every
file that release has, but it will not remove files that release dropped —
without the delete you keep dead packages and stale `.mk` files that the new
`Config.in` no longer mentions.

The `:!br2ext` on `git add` keeps whatever you have in progress under
`br2ext/` out of the Buildroot commit. `.gitignore` comes from upstream — it
ignores `output/`, `dl/` and `.config` like ours did, plus a few more — so
there is nothing of ours to preserve there.

`br2ext/` is the only thing in the tree that is ours. If that ever stops
being true and you patch Buildroot itself, this recipe throws the patch away
without saying so. Keep any such change as a commit you can replay on top,
or better, move it into `br2ext/`.

### Rebuilding afterwards

Reload the defconfig against the new tree and check it survived:

```sh
make BR2_EXTERNAL=$PWD/br2ext aos_x86_64_defconfig
grep BR2_LEGACY .config
```

That grep must come back empty. Options Buildroot renamed select `BR2_LEGACY`,
and `Makefile.legacy` turns that into a hard error on the next `make`, so those
you cannot miss. The kind you *can* miss is the one in
[building.md](building.md): an option whose dependencies stopped being met, or
one deleted with no legacy entry, is dropped in silence. Spot-check the ones
that matter:

```sh
grep -E 'BR2_PACKAGE_MESA3D_LLVM|BR2_PACKAGE_MESA3D_VULKAN|BR2_GCC_VERSION' .config
```

Re-check our own packages against the new package infrastructure too:

```sh
./utils/check-package --br2-external br2ext/package/*/*
```

Then build. A quarterly upgrade nearly always moves gcc or glibc, which
invalidates the toolchain and everything above it, so start from clean:

```sh
make clean
make
```

`make clean` wipes `output/` but leaves `dl/` and `.config` alone, so packages
whose versions did not change are not downloaded again. Expect the same 2 to 4
hours as a first build. Avoid `make distclean` unless you mean it — it also
removes `dl/` and `output/.br2-external.mk`, so you lose the download cache and
have to pass `BR2_EXTERNAL=` again.

A point release within a branch does not need `make clean`. Read that
release's entry in `CHANGES`, dirclean the handful of packages whose versions
moved, and let the rest stand.

### What does not come along

An upgrade only moves what Buildroot ships. The NVIDIA driver and the Rust
toolchain are our packages, pinned in `br2ext/package/`, and stay exactly where
they were — use the sections above to move them. After a kernel bump, confirm
the NVIDIA modules still build against the new kernel; that is the piece most
likely to break.
