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

The repository root is a plain Buildroot checkout and all our work is under
`br2ext/`, so upgrading is a normal pull. Expect to re-check the defconfig
afterwards: symbols get renamed between releases, and a renamed symbol
disappears silently.
