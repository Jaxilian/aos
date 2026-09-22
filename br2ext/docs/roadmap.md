# Roadmap: from foundation to an operating system

## Where this stands

AOS began as a foundation — kernel, glibc, drivers, a toolchain, and nothing
above. That phase is over. The image now boots into ade, installs software
through apm, and runs a terminal, notepad, files, and Visual Studio Code
from a package repository. The previous roadmap (an init system under
BusyBox, then a compositor) is done or superseded: systemd is the init, ade
is the compositor.

The goal from here is a **consumer Linux distribution with hard standards**.
One desktop. One package format. One native GUI stack. A person installs it,
sets it up, and uses it — for games, for work, for anything — without ever
opening a terminal, the way they use Windows 11 or macOS. The long game is
shipping it on hardware, so that a fixed, predictable platform is worth
developers' time.

This file is the plan for reaching an alpha that an enterprise evaluator can
take seriously. Every item names where it stands today and what done looks
like. Items are ordered within a phase; the phases are ordered too, and
Phase 0 blocks all of the rest.

## The platform contract

These are the standards. They are stated here and in
[../PLATFORM.md](../PLATFORM.md), and they do not soften.

| | |
|---|---|
| Desktop | ade, and only ade. No other desktop environment, no other compositor. |
| Native stack | awin/tgn → Wayland → ade-comp → Mesa (Intel, AMD) or NVIDIA → Linux. This is the SDK, and it is what AOS's own applications are written on. |
| Not enforced | Applications are not required to use awin/tgn. Electron, SDL, Qt and GTK programs run as ordinary Wayland clients. Requiring the native stack would exclude Visual Studio Code, Steam and Discord, and without those the platform does not sell. |
| X11 | XWayland is a compatibility layer, off by default, that the user turns on. It is never a dependency of an official package. |
| Packaging | apm is the only way software enters the machine: signed packages with a `.desktop` entry, installed into apm's store. No tarballs, no `curl \| sh`. |
| Two tiers | **Official** — [apm-recipes](https://github.com/Jaxilian/apm-recipes), tested against each release, recommended. **Third-party** — [apm-thirdparty](https://github.com/Jaxilian/apm-thirdparty), carried for compatibility, at the user's risk, and labelled so wherever it appears. A third-party package may depend on official ones, never the reverse. |
| Users | Never need a console. Install, first-boot setup, settings, updates and the app store are all graphical. The terminal exists for developers. |
| Base | systemd, all of it; glibc; x86-64-v2; merged `/usr`; no initramfs. As in [../PLATFORM.md](../PLATFORM.md), unchanged. |

## Phase 0 — Build and release engineering

Nothing below this phase can be claimed until this phase is done: until the
image builds from tagged sources on a machine that is not the author's, every
other item is a result no one else can reproduce.

1. **Tagged sources for ade, apm, terminal, notepad and files.**
   *Done 2026-09-22.* Each `.mk` names a GitHub repository and a commit;
   Buildroot's download step vendors the crates. awin and tgn, which every
   application used to reach by an absolute path into one machine, are one
   workspace in the `aos-sdk` repository and a git dependency at a tag. A
   developer's working tree goes in through `local.mk`
   ([building.md](building.md)). Outstanding: the repositories exist only
   locally until pushed, and there are no `.hash` files yet -- the commit
   pins the content, the hash would guard the download.
2. **Pin what floats.**
   *Done 2026-09-22*, except the archive. Kernel pinned
   ([upgrading.md](upgrading.md) has the headers trap that comes with it),
   `BR2_REPRODUCIBLE=y`, and [post-build.sh](../board/aos/post-build.sh)
   writes `BUILD_ID` from the commit (`-dirty` when the tree is not clean)
   and `VERSION_ID` from the tag when there is one. `BR2_PER_PACKAGE_DIRECTORIES`
   was left out: it changes the whole build layout for a benefit (parallel
   top-level builds) nothing here needs yet. Outstanding: a `make source`
   archive per tag, and the first clean build under `BR2_REPRODUCIBLE` --
   the current tree was built before the flag.
3. **Continuous integration.**
   Today: the root `.gitlab-ci.yml` is upstream Buildroot's and
   `.github/workflows/` holds only repo-lockdown. Nothing builds AOS on a
   push. [boot-test.py](../board/aos/boot-test.py) does the right test and
   runs only when someone types it.
   Done: a self-hosted runner with KVM builds nightly and on every tag, then
   runs `boot-test.py live`, `install`, `disk` and `desktop`, keeping the
   serial logs and screendumps as artifacts. A red run blocks the tag.
   *Written 2026-09-22*: [ci.sh](../board/aos/ci.sh) is the job and
   `.github/workflows/aos.yml` runs it. Outstanding: a runner registered
   with the label `kvm`.
4. **Release shape.**
   *Half done 2026-09-22*: `aos-install` now asks for the machine's own
   account and installs that; the demo account survives only with `--demo`,
   which the tests pass. Outstanding: the live ISO itself still carries
   `admin` / `123321`, because the desktop session needs a user to belong
   to. That goes when first-boot setup exists (Phase 2, item 2).
5. **Signed releases.**
   Today: [publishing.md](publishing.md) suggests a bare `sha256sum`.
   Done: `SHA256SUMS` signed with the same minisign key every AOS machine
   already trusts for apm, published fingerprint, and the `make legal-info`
   manifest beside the ISO.
   *Written 2026-09-22*: [release.sh](../board/aos/release.sh) does all of
   it with `apm sign`, and refuses a `-dirty` build.
6. **Cadence and support window, in writing.** For instance: a 0.x release
   monthly, each supported until the next. The number matters less than its
   existence.

## Phase 1 — Trust and security

What an evaluator checks before anything else.

1. **A security policy that is AOS's.** Today the root `SECURITY.md` is
   Buildroot's, untouched. Done: reporting address, what happens to a report,
   and an honest statement of what an alpha promises.
2. **apm refuses unknown keys.** *Done 2026-09-22*: an index no trusted
   key verifies is refused (`trust = "required"` is the default), and the
   image ships the official key already trusted with the official
   repository configured, in `rootfs-overlay/opt/apm/etc`. A developer with
   an unsigned index sets `trust = "warn"`. Outstanding: the store showing
   which key signed each package.
3. **A CVE report per release.** Buildroot's `make pkg-stats` against the
   tagged configuration, published with the release, with a paragraph on
   how a fix reaches an installed machine.
4. **Secure Boot: decide.** Today nothing is signed and a machine with
   Secure Boot on cannot boot AOS at all. Either shim plus a MOK-enrolled
   kernel and modules (the NVIDIA modules need signing too), or "unsupported;
   turn it off" at the top of the known limitations. Decide before any
   evaluation, not during one.
5. **Base OS updates.** Today an installed machine is updated by
   reinstalling. Done: a signed, versioned root image in A/B slots and a
   "previous version" entry in the boot menu next to the existing
   safe-graphics one. `systemd-sysupdate` is already in the image and fits
   the no-initramfs, `root=PARTUUID=` layout. Until it lands, a documented
   reinstall that preserves `/home`.
6. **Disk encryption: decide.** Without an initramfs the root cannot be on
   LUKS ([../PLATFORM.md](../PLATFORM.md)). Either a minimal initramfs for
   LUKS, or `/home` only. Evaluators ask.
7. **No telemetry**, written down as a guarantee. It is true today; it
   should be a promise.

## Phase 2 — Everything a user does, without a terminal

In the order a new user meets them.

1. **A graphical installer.** Today [aos-install](../board/aos/rootfs-overlay/usr/bin/aos-install)
   is a shell prompt. Done: disk, keyboard, time zone, account and password,
   progress — on the awin/tgn stack, with `aos-install` kept as the engine
   it drives.
2. **First-boot setup.** Account, Wi-Fi, time zone, and the choice to enable
   the third-party repository. This is what lets the released image carry
   no account at all.
3. **A Settings application.** Display and scale, sound, network and Wi-Fi,
   keyboard layout, power and suspend, users, updates, the XWayland switch,
   the third-party repository switch. systemd-networkd, resolved, localed
   and logind already expose all of it over D-Bus.
4. **The app store.** A graphical front to apm, with Official and Third-party
   clearly separated: search, install, update, remove, and who signed it.
5. **Updates in one place.** Base OS (Phase 1, item 5) and applications on
   one screen, with a restart prompt.
6. **XWayland**, as an optional package ade-comp can host (smithay supports
   it), off by default.
7. **The third-party proof points**, in apm-thirdparty: Visual Studio Code
   (exists), Discord, Firefox, and Steam. Steam needs a 32-bit userspace,
   which is a Buildroot decision with a wide blast radius; plan it as its own
   piece of work. These are release gates, not extras: if they do not run,
   the platform does not sell.
8. **Session basics a consumer expects.** *Sound done 2026-09-22*:
   PipeWire and WirePlumber as session services, a sink on QEMU's HDA card
   checked every desktop boot ([../PLATFORM.md](../PLATFORM.md) has the
   three things that had to be right: modular controller, ACL through
   logind, real-time through the pipewire group). Outstanding for sound:
   Intel SOF and AMD ACP -- kernel options and firmware for the DSPs on
   laptops from 2019 on, which QEMU cannot test -- and Bluetooth audio.
   Then: lock screen (`ade/lock` is a placeholder awaiting
   `ext-session-lock-v1`), screenshot, notifications, clipboard,
   drag-and-drop, Bluetooth, battery and power in the bar. Printing can
   wait.

## Phase 3 — Stability and performance

1. **A soak test in CI.** A desktop session held for 24–48 hours, then
   `systemctl --failed` empty, `journalctl -p err` empty, `ade-comp` memory
   flat, no watchdog reboot. Nothing today would notice a compositor leak.
2. **Suspend, resume and lid-close** on every machine on the hardware list.
   The most common laptop failure, and untested today.
3. **Boot-test the release path.** `boot-test.py` exercises the demo image.
   The `--release` path and, once it exists, the graphical installer need
   the same treatment.
4. **A gaming baseline.** A Vulkan game at native resolution on Intel, AMD
   and NVIDIA, through ade-comp's direct-scanout path, measured against a
   stock distribution. Steam with Proton is the real test. Variable refresh
   and 10-bit output come later.
5. **A crash story.** coredump and journald are configured. *`aos-report`
   added 2026-09-22*: one command, one tarball -- this boot's journal, the
   errors, failed units, the compositor's log, the hardware, what apm has
   installed. Outstanding: a "send diagnostics" button in Settings that
   produces the same file.
6. **Fault isolation.** A shell crash must not end the session (ade's
   design already separates them). A compositor crash must restart the
   session with an explanation, never leave a black screen.

## Phase 4 — Hardware and the evaluation

1. **A hardware compatibility list.** Today one machine, an ASUS G14. Done:
   three to five more — an Intel-graphics laptop, an AMD APU, an NVIDIA
   desktop, and a machine from around 2012 for the x86-64-v2 floor — with
   pass or fail per feature: boot, graphics, Wi-Fi, suspend, audio,
   touchpad.
2. **Reference hardware.** One machine that is *the* AOS machine, where
   everything is made perfect first. That is the hardware story, and the
   machine an evaluator is handed.
3. **One use case the evaluation wins at.** "Runs anything" is the vision;
   the evaluation needs a single thing AOS does better. With what works
   today, that is a developer workstation — Visual Studio Code, gcc and Rust,
   nothing to configure. Gaming becomes the second once Steam runs.
4. **Documentation for someone who is not the author.** An install guide a
   systems administrator can follow, and a known-issues list.

## Verification

Each phase ends the same way AOS has always been tested — see
[testing.md](testing.md): build, boot in QEMU, run `boot-test.py`, and look
at the screen, not just the serial line. Real hardware for what QEMU cannot
emulate. Every item above names a state that can be checked: a `.config`
symbol, a green CI run, a signed file, a screendump, a machine on a list.
