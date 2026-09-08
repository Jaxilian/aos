# Building an OS on top of AOS: init, compositor, desktop

## Context

AOS itself is finished and verified: it boots on BIOS and UEFI, installs to disk,
and compiles C, C++ and Rust on itself. It is a foundation with nothing above
the line — no init beyond BusyBox, no display server, no applications.

This plan covers the next phase: the three things that turn that foundation into
an operating system you can use.

1. **An init system** you write yourself, in the spirit of systemd but yours.
2. **A Vulkan Wayland compositor**, built on Smithay in Rust.
3. **A desktop environment**: compositor, terminal, launcher, status bar.

### Decisions taken

| | |
|---|---|
| Compositor | Smithay (Rust) for Wayland/DRM plumbing, `ash` for Vulkan |
| DE scope, v1 | Compositor + terminal + launcher + bar |
| Workflow | Cross-compile on Fedora, ship into the image as Buildroot packages |

### What the research found

- **Buildroot's `cargo-package` infrastructure does the hard part.** It vendors
  crates at download time and builds `--offline --locked`.
  [package/eza/eza.mk](package/eza/eza.mk) is a complete Rust package in 8 lines.
  Shipping a Rust compositor is packaging-trivial; writing it is the work.
- **`seatd` is in Buildroot and provides `libseat`**, with `INSTALL_STAGING=YES`
  and a SysV init script that suits BusyBox init. This is the piece that lets a
  compositor take DRM master and open input devices without being root, and it
  is why you do not need logind.
- **`xkeyboard-config` is absent from Buildroot**, and `libxkbcommon` does not
  pull it in. Without that data every keyboard layout fails to resolve inside a
  compositor. AOS must supply it — a data-only custom package.
- **`glslang` and `shaderc` are absent.** Do not add them: use `naga` (pure
  Rust, already in the wgpu ecosystem) to compile shaders, or precompile SPIR-V
  on the host and `include_bytes!` it.
- **`wlroots` 0.20, `weston`, `cage`, `foot`, `wmenu` are all available.** You
  are not using wlroots as your foundation, but `cage` and `weston` are
  invaluable as a *smoke test*: they prove AOS's graphics stack works before you
  debug your own code against it.
- **Software Vulkan is already in the image** (`libvulkan_lvp.so`, lavapipe).
  A Vulkan compositor can be developed and tested in QEMU with no GPU
  passthrough at all.

---

## Phase 0 — Give AOS what a compositor needs

Nothing here is your code; it is the platform gap. Add to
[br2ext/configs/aos_x86_64_defconfig](br2ext/configs/aos_x86_64_defconfig):

```
BR2_PACKAGE_SEATD=y
BR2_PACKAGE_SEATD_DAEMON=y
BR2_PACKAGE_LIBINPUT=y
BR2_PACKAGE_LIBXKBCOMMON=y
BR2_PACKAGE_LIBEVDEV=y
BR2_PACKAGE_MTDEV=y
BR2_PACKAGE_LIBDISPLAY_INFO=y
BR2_PACKAGE_HWDATA=y
BR2_PACKAGE_DEJAVU=y
BR2_PACKAGE_FREETYPE=y
BR2_PACKAGE_FONTCONFIG=y
BR2_PACKAGE_HARFBUZZ=y
BR2_PACKAGE_VULKAN_HEADERS=y
BR2_PACKAGE_VULKAN_TOOLS=y
```

Plus one new package, `br2ext/package/aos-xkeyboard-config/`, following the
pattern of the four existing ones. It is data only — no compilation — installing
XKB layout data to `/usr/share/X11/xkb`. `libxkbcommon` finds it there by
default.

**Verify every symbol landed.** Four times during the AOS build kconfig silently
dropped an option whose dependency was unmet. After loading the defconfig, grep
`.config` for each symbol above. And if a package was already built before you
changed its options, `make <pkg>-dirclean` or the change does nothing.

## Phase 1 — Prove the stack before writing any code

Temporarily enable `BR2_PACKAGE_CAGE=y` (a single-window wlroots compositor) and
`BR2_PACKAGE_FOOT=y`, boot AOS, and run `cage -- foot`.

This is worth doing first and cannot be skipped. If a terminal appears, then
DRM/KMS, GBM, EGL, seatd, libinput and the fonts all work, and every later
failure is in your code. If it does not appear, you are debugging AOS, not your
compositor — much easier to establish now than in three months.

Then check Vulkan specifically with `vulkaninfo --summary`; expect lavapipe in
QEMU and the real driver on hardware.

Remove both packages afterwards, or keep them behind a `BR2_PACKAGE_AOS_DEVTOOLS`
option for future debugging.

## Phase 2 — The init system

Create `aos-init` as a Rust workspace, cross-compiled and packaged at
`br2ext/package/aos-init/` using the `cargo-package` pattern.

Build it in this order, each stage bootable:

1. **PID 1 that does not panic.** Mount `/proc`, `/sys`, `/dev`; reap orphaned
   children; handle `SIGCHLD`; never exit. Getting reaping wrong is the classic
   PID 1 bug — an unreaped zombie accumulates forever.
2. **Service definitions and supervision.** A declarative unit format (TOML fits
   Rust well), start/stop/restart, and restart-on-failure with backoff.
3. **Dependency ordering.** A DAG of units, started in topological order, in
   parallel where the graph allows.
4. **Sockets and readiness.** Socket activation and a readiness protocol, so a
   unit can declare itself up rather than being assumed up after `fork`.
5. **Cut over.** Set `BR2_INIT_NONE` and install your binary as `/sbin/init`.
   Keep BusyBox init installed as `/sbin/init-busybox` and add a GRUB menu entry
   with `init=/sbin/init-busybox` — a rescue path for when your init cannot boot.

Keep the existing AOS init scripts working during 1–4 by running your init under
BusyBox init first, as an ordinary service. Only take PID 1 at step 5.

## Phase 3 — The compositor

`aos-comp`, a Rust binary. Smithay for Wayland and DRM, `ash` for Vulkan,
`naga` for shaders.

Milestones, each independently verifiable:

1. **Open the GPU.** Take a seat via `libseat`, become DRM master, enumerate
   connectors and modes. Success is a log line naming your monitor, nothing on
   screen yet.
2. **Clear the screen to a colour** via Vulkan, page-flipped through DRM. This
   is the milestone that proves the whole Vulkan-on-KMS path.
3. **Accept a Wayland client.** Implement `wl_compositor`, `wl_shm` and
   `xdg_shell`; import a client buffer as a Vulkan texture and composite it.
   `foot` is your test client.
4. **Input.** libinput through your seat: pointer, keyboard with XKB layouts
   (this is where Phase 0's `xkeyboard-config` matters), focus handling.
5. **Real compositing.** Multiple surfaces, damage tracking, alpha, transforms,
   a scene graph.
6. **Multiple outputs**, hotplug, DPMS.

Test in QEMU with lavapipe throughout; move to your RTX 5070 once stage 3 works.
The NVIDIA path is already in the image and needs no extra work.

## Phase 4 — The desktop environment

Three separate binaries talking Wayland to your compositor, not one monolith.

- **Terminal** — the hardest of the three (VTE state machine, font shaping via
  harfbuzz, glyph atlas). Ship `foot` initially; replace it when you want to.
- **Launcher** — the easiest, and a good first client to write: fuzzy-match
  `$PATH`, spawn, exit.
- **Bar** — clock, battery from `/sys/class/power_supply`, network state. Needs
  the `wlr-layer-shell` protocol implemented in your compositor first.

Package each as `br2ext/package/aos-<name>/`.

## Phase 5 — Make it a session

A session unit in your init that starts the compositor on boot, and a compositor
config for autostarting the bar. Then a `BR2_PACKAGE_AOS_DESKTOP` meta-option
that pulls in the whole set, so AOS still builds as a bare foundation without it.

---

## Verification

Each phase ends in something runnable, tested the same way AOS was:

```sh
make BR2_EXTERNAL=$PWD/br2ext aos_x86_64_defconfig
grep BR2_PACKAGE_SEATD .config          # confirm symbols actually took
make
./br2ext/board/aos/run-qemu.sh
```

**Check the screen, not just the serial console.** AOS shipped a black-screen bug
that every serial-based test passed. For anything graphical, screendump the VGA
output and look at it:

```sh
{ sleep 45; echo "screendump /tmp/s.ppm"; sleep 2; echo quit; } | \
  qemu-system-x86_64 ... -display none -vga std -monitor stdio
```

Per phase: Phase 1 succeeds when a terminal renders under `cage`. Phase 2 when
AOS boots to a login with your binary as PID 1 and `ps` shows your supervised
services. Phase 3 at each of the six milestones. Phase 4 when the launcher opens
a terminal. Phase 5 when a cold boot reaches your desktop with no manual steps.

## Risks

1. **Scope.** Any one of these three is a large project; together they are the
   bulk of what a distribution is. Phase 1 is deliberately cheap and proves the
   platform before you commit.
2. **Becoming PID 1.** A broken init means an unbootable machine. The
   `init=/sbin/init-busybox` rescue entry is not optional.
3. **Vulkan on NVIDIA under Wayland** has historically been the rough path
   (explicit sync, buffer import). Develop against lavapipe and Intel first; treat
   the NVIDIA GPU as a later target, not the first one.
4. **Crate vendoring.** Buildroot vendors crates at download time and builds
   offline. A dependency added to `Cargo.toml` will not appear until the package
   is re-downloaded — `make <pkg>-dirclean` after touching dependencies.
5. **Smithay is a moving target.** Pin the version in `Cargo.lock`; Buildroot's
   `--locked` build depends on it.
