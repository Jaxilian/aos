# Roadmap: from foundation to an operating system

## Where this stands

AOS began as a foundation — kernel, glibc, drivers, a toolchain, and nothing
above. That phase is over. The image now boots into ade, installs software
through apm, and runs a terminal, notepad, files, and Visual Studio Code
from a package repository. The previous roadmap (an init system under
BusyBox, then a compositor) is done or superseded: systemd is the init, ade
is the compositor.

*As of 0.2.8 (2026-10-07)*: an installed disk holds two read-only cores
(squashfs checked by dm-verity) and an `aos` partition for everything
written, optionally LUKS2-encrypted; an owned machine boots to a login
screen, an unowned one to the first-boot setup; Software installs
programs and the OS update in one place; third-party programs run in a
sandbox with their microphone and camera withheld unless allowed. The
core is 746 MB, the ISO 825 MB, both published (the ISO on
[aos-releases](https://github.com/Jaxilian/aos-releases)). Open, in
rough order: per-user encrypted homes (systemd-homed, waiting for the
owner's yes), the file dialog for sandboxed programs and then AOS's own
apps in the sandbox, output on the second GPU's connectors (the G14's
HDMI), a second test machine, CI's first green run, and Secure Boot,
decided unsupported. Everything has been tested on one laptop, the G14.

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
| Base | systemd, all of it; glibc; x86-64-v2; merged `/usr`; a small initramfs of the image's own binaries that opens the verity core and the aos partition (since 0.2.0; [layout.md](layout.md)). As in [../PLATFORM.md](../PLATFORM.md). |

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
   ([building.md](building.md)). The repositories are on GitHub (private),
   and each package has a `.hash` for its vendored tarball; repinning an
   application means rewriting that line (`make <pkg>-source` fetches
   the tarball to hash).
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
   `.github/workflows/aos.yml` runs it. *Runner registered 2026-10-03*
   (`g14`, label `kvm`, on the build laptop); its runs so far failed on
   the runner's side, not the build's, and it was paused on 2026-10-07.
   Outstanding: a first green run.
4. **Release shape.**
   *Half done 2026-09-22*: `aos-install` now asks for the machine's own
   account and installs that; the demo account survives only with `--demo`,
   which the tests pass. *Done 2026-10-03*: the live ISO's account has no
   password at all (sudo asks for none there, no lock screen, root on the
   serial console only); the desktop session still needs a user to belong
   to, and this one can be nobody's way in. *2026-10-05*: `--oobe` leaves
   the account to the machine's first boot (Phase 2, item 2).
5. **Signed releases.**
   Today: [publishing.md](publishing.md) suggests a bare `sha256sum`.
   Done: `SHA256SUMS` signed with the same minisign key every AOS machine
   already trusts for apm, published fingerprint, and the `make legal-info`
   manifest beside the ISO.
   *Written 2026-09-22*: [release.sh](../board/aos/release.sh) does all of
   it with `apm sign`, and refuses a `-dirty` build.
6. **Cadence and support window, in writing.** *Done 2026-09-28*: a 0.x
   release monthly, each supported until the next --
   [policies.md](policies.md).

## Phase 1 — Trust and security

What an evaluator checks before anything else.

1. **A security policy that is AOS's.** *Done*: the root `SECURITY.md`
   has the reporting address, what happens to a report, the disclosure
   window, and what an alpha promises.
2. **apm refuses unknown keys.** *Done 2026-09-22*: an index no trusted
   key verifies is refused (`trust = "required"` is the default), and the
   image ships the official key already trusted with the official
   repository configured, in `rootfs-overlay/opt/apm/etc`. A developer with
   an unsigned index sets `trust = "warn"`. Outstanding: the store showing
   which key signed each package.
3. **A CVE report per release.** *Done 2026-10-01*: `release.sh` makes
   `pkg-stats` with every release, and [security-status.md](security-status.md)
   triages it -- for 0.1.7, 64 CVEs in 19 packages: seven packages bumped
   (util-linux, libxml2, pcre2, gzip, coreutils, gawk, patch), the
   not-applicable ones ignored in `external.mk` with their reasons, our own
   packages given an explicit CPE vendor, and five open ones with a plan
   (binutils and systemd wait for a toolchain and core update).
4. **Secure Boot: decide.** *Decided 2026-09-28*: unsupported, turn it
   off, first line of the known limitations ([policies.md](policies.md)).
   Shim plus a MOK-enrolled kernel and signed modules (NVIDIA's too) is
   known engineering and ongoing maintenance; it waits for a reason.
5. **Base OS updates.** *Done 2026-10-01*: two root slots and a data
   partition on every installed disk, `aos-update` writing a release's
   signed root tarball into the idle slot, GRUB booting it once and the
   desktop confirming it, "AOS (previous version)" in the menu
   ([upgrading.md](upgrading.md)). Not `systemd-sysupdate`: it was never in
   the image, verifies with gpg, and is built around systemd-boot; what it
   would have saved was the slot switch, which GRUB has to do by hand
   anyway. The release is published next to the apm index
   (`release.sh --publish`). Disks installed before this are reinstalled.
   *Verity cores, 0.2.0 (2026-10-06)*: a release is a core -- a squashfs
   with its dm-verity hash tree, written raw into the slot and read back
   through the verity -- not a tarball; the kernel ships inside it, no
   longer as an apm package, and a small initramfs opens it. What is
   written lives on the `aos` partition ([layout.md](layout.md)). 0.1.x
   disks are reinstalled.
6. **Disk encryption: decide.** *Decided 2026-09-28*: `/home` on LUKS,
   unlocked at login, when it comes; the root stays in the clear and there
   is no initramfs ([policies.md](policies.md)). *Done differently, 0.2.2
   (2026-10-06)*: LUKS2 around the whole `aos` partition (homes,
   programs, settings, logs), `aos-install --encrypt` and the installer's
   "Encrypt the disk", the passphrase asked by the initramfs before the
   desktop; the cores stay in the clear, public and verified.
   Outstanding: per-user homes unlocked at login (systemd-homed through
   greetd's PAM, with a recovery key) -- it changes what a disk holds and
   waits for the owner's yes; and `./usb.sh --encrypt`.
7. **No telemetry**, written down as a guarantee. *Done 2026-09-28*:
   [policies.md](policies.md).
8. **An application sandbox.** *`aos-sandbox` 2026-09-22; declarations
   done 2026-10-02*: a package declares
   what it needs (`[sandbox]` in its manifest), apm writes an
   `aos-sandbox` wrapper for it, a program gets a private home under
   `~/.var/app` unless it declares more, and Software shows what each
   one sees and lets the person change it. *Camera 2026-10-05*
   (`/dev/video*` only with the switch on), *microphone 2026-10-06*
   (0.1.29: PipeWire's capture refused on a second socket the sandbox
   binds over the real one, unless allowed; `mic-test.py`). No prompt
   when a program first asks; the switch is the answer. Outstanding: a
   file dialog the desktop draws, handing a sandboxed program one file
   by descriptor, and then AOS's own applications in the sandbox (they
   run outside it today).

## Phase 2 — Everything a user does, without a terminal

In the order a new user meets them.

1. **A graphical installer.** *Done 2026-10-01 (aos-setup v0.1.0)*:
   "Install AOS" in the live ISO's overview -- keyboard layout, time
   zone, account and password, the disk (the live medium is never
   offered, too-small disks are marked), then `aos-install` run through
   sudo with its stages on a progress bar and a Restart button. The
   engine gained `--password-file`, `--keymap` and `--zone`. On the
   live ISO the app unlocks sudo with the demo account's password
   itself. Tested in QEMU as every other app; the first hardware run is
   the G14's next stick.
2. **First-boot setup.** *Dropped 2026-10-01, then asked for and done
   2026-10-05 (0.1.24)*, so a stick can be handed to someone:
   `aos-install --oobe` (`./usb.sh --oobe`) leaves no account; the first
   boot is a locked `setup` user's session running `aos-setup
   --first-boot` -- keyboard, time zone, account -- whose Finish runs
   `aos-firstboot` through its one sudoers line; that makes the owner,
   locks root, and refuses once an owner exists. `oobe-test.py` in QEMU;
   untested on hardware.
2b. **A login screen.** *Done 0.2.3 (2026-10-06)*: greetd with
   ade-greeter (Jaxilian/greeter) on an owned or first-boot machine --
   the accounts listed, a password, the session started as that account;
   the live medium and a demo install keep the autologin.
   `greeter-test.py` in QEMU, including the lock screen keeping the
   keyboard under an OSD (0.2.8).
3. **A Settings application.** *Done 2026-09-25 (settings v0.1.0)*:
   network and Wi-Fi, sound, display, keyboard layout, power and the lid,
   users, date and time, apm updates, the XWayland switch, the
   third-party repository switch, about with the diagnostics report. It
   drives the tools the image has (iw and aos-wifi, wpctl, timedatectl,
   hostnamectl, the shadow tools, apm) through sudo, and asks for the
   password itself since there is no polkit agent; suspend, restart and
   power off go through the seat's polkit rule. *Display scale and a
   Lock button added 2026-09-25 (settings v0.1.1, ade v0.1.11)*: the
   scale goes to `~/.config/ade/display`, which the compositor rereads
   within seconds. *Display arrangement and per-display on/off done
   2026-10-05 (0.1.25)*: the file's `order=` and `off=` lines, left or
   right of the first display (`disp-test.py`); per-display scale since
   2026-10-02. And
   *idle blanking added 2026-09-28*: `blank=<seconds>` in the same file,
   ten minutes by default; ade switches every head off through its DPMS
   property after that long without input and on again at the next key
   or pointer event, and the Display page offers the times.
4. **The app store.** *Done 2026-10-01 (aos-store v0.1.0)*: "Software"
   in the overview -- Installed, Official and Third-party pages with
   search, Install and Remove, the key every index is checked against,
   and Updates with one button for every package and a new AOS. It
   reads through apm-core as a library (the repositories, the index,
   what is installed, what an upgrade would do -- typed, no text
   parsing, no root) and changes things through `sudo apm`, asking the
   password once like Settings. Not yet, because apm's index does not
   carry them: icons, long descriptions, per-package signers (both
   repositories sign with one key today, so "who signed it" is the
   repository's key); an index format 2 is where they go.
   *Icons, 2026-10-01 (apm v0.1.4, aos-store v0.1.1)*: the signed index
   zip carries a `meta.tsv` beside `index.tsv` -- display name,
   categories, description, and an icon published next to the packages
   with its sha256 -- which older apm never opens, so machines in the
   field keep working. The store shows applications as an icon grid and
   libraries and tools as their own list; hello and hello-c left the
   official repository. Per-package signers are still to come.
5. **Updates in one place.** *Done 2026-10-01*: `apm upgrade` carries the
   OS (apm v0.1.3); Software -> Updates and Settings -> Software are the
   one button, with Restart beside it; `aos-update-check.timer` looks
   daily and the shell says when there is something (ade v0.1.27).
   *Software owns updates, 2026-10-04 (0.1.19)*: Settings' Software page
   is gone; Software's Update page lists every pending package and the OS
   with a line each while they run (`apm --progress`), a failed package
   is skipped and reported, then Restart; the check runs two minutes
   after boot and a click on its toast opens the page
   (`upgrade-ui-test.py`).
6. **XWayland.** *Done 2026-09-23*: `runtime/xwayland` in apm-thirdparty,
   built out of the packages tree by `board/aos/runtime-xwayland.sh`.
   Installing it is the switch: ade-comp starts Xwayland at the next
   session when it finds one on PATH, manages its windows like Wayland
   ones (`comp/src/ade/xw.rs`), and every program started from the session
   inherits DISPLAY; without the package the code is inert. The boot test
   restarts the session after installing it and draws GTK3's demo through
   the X11 backend. What the OS itself had to gain for it: GLX. The GLX
   client library must share the image's libgallium (its DRI3 loader is
   built only with the X11 platform), so it cannot come from a package;
   the image's Mesa now builds GLX, which brings libGL, the X client
   libraries and xkbcomp into the OS. No official software uses them. And
   glamor, Xwayland's GPU path, wants linux-dmabuf version 4 from the
   compositor: ade v0.1.6 offers it, with the render node in its
   feedback. On QEMU Xwayland refuses glamor on llvmpipe and serves
   software GLX; on a GPU it renders through the compositor's device.
   *On demand, done 2026-09-24 (ade v0.1.9)*: XWayland used to start
   only with a session, so a package installed into a running session had
   no DISPLAY until the next login (seen on the G14: Steam installed and
   started in one sitting). Now a session that began without it looks for
   the binary every five seconds and starts it when the package appears;
   a program the shell launches after that, or Steam's wrapper from a
   terminal older than the start, finds the display by its socket in
   `/tmp/.X11-unix`, since neither inherited DISPLAY.
   Round 6, 2026-09-26: Thronefall installed, launched and an entire map
   was played -- on the Intel GPU. The stick that round was written
   through a stale page cache of the previous stick's root, which the
   host still had mounted, and came out with every group descriptor
   checksum wrong; the writer flushes the partition buffers now. The
   NVIDIA device-node service had not reached that image (a package
   whose files change under br2ext/package needs its own `-rebuild`;
   a plain `make` keeps the old install), so `prime-run` found no GPU
   and the game waited without a window. Alt+Tab with Steam's
   Properties open went to Steam's own window under the dialog; ade
   v0.1.15 cycles main windows only and brings a target's dialogs up
   with it. And the launcher read its entries once at start, so Steam
   appeared in it only after a reboot; it rereads them on every show.
   Round 5 on the G14, 2026-09-25 evening, three findings. Alt+Tab onto
   Steam still typed into the old window: an X client takes keys only
   where the X server's input focus is, which only the window manager
   sets, and ade's keyboard focus was a bare wl_surface; ade v0.1.14
   focuses an X11 window as itself (`foc.rs`). Copy never pasted between
   any two programs: the compositor never passed the clipboard along
   with the keyboard (fixed in the same ade), and awin created its data
   device after its surface, so a new window was focused -- and offered
   the clipboard -- before it had anything to receive it (aos-sdk
   v0.4.2; smithay never re-offers, wlroots does). And the game: no
   Vulkan in its container because the Vulkan loader had been built
   before the X11 libraries entered the image and knew no X11 surfaces
   -- Buildroot does not rebuild a package when a dependency it probes
   at configure time appears later; five such packages were rebuilt.
   NVIDIA's device nodes were still missing on the G14: the udev RUN
   never showed why, so a udev-started unit makes them now, and its log
   is in the journal.
   Round 3 on the G14, 2026-09-25: Alt+Tab onto Steam raised it but
   typing stayed with the previous window -- an X client takes input
   only once the window manager has marked the window active, and only
   the map path did; ade v0.1.10 does it on every focus change, and
   Super+Tab is an alias. Same round: the game (Thronefall, Proton
   Experimental) crashed with "d3d11: failed to create factory", no
   usable Vulkan inside the game's runtime container, though Steam's
   own container sees the Intel GPU; pressure-vessel had logged a lock
   error on the runtime's `.ref` first. `aos-report --steam` now bundles
   Steam's, the runtime's and Proton's logs for the next round. And the
   wifi driver worked all along; what was missing was a way to join a
   network: `aos-wifi SSID`; the Settings application's Network page
   runs it now.
   Seen on the G14, 2026-09-24: Steam's window could not be moved or
   resized. Steam draws its own titlebar and asks the window manager for
   the drag (`_NET_WM_MOVERESIZE`); ade answered neither request. ade
   v0.1.8 starts the same grabs an xdg toplevel's get, proven in the
   boot-test harness with gtk3-demo's header bar dragged through QEMU's
   tablet -- which took two findings of its own: the GTK3 runtime's
   wrapper forced `GDK_BACKEND=wayland`, so the boot test's "X11 window"
   had been a Wayland one all along (runtime/gtk3 release 5 only defaults
   it; the check now sets x11 inside the wrapper), and the HMP monitor's
   `mouse_move` never reaches the usb-tablet, only QMP's
   `input-send-event` does (buttons and the PS/2 mouse work either way).
7. **The third-party proof points**, in apm-thirdparty. *Firefox and
   Discord done 2026-09-22*, beside Visual Studio Code: each installs from
   the repository and puts a window on ade in the boot test. The runtime
   they share (`runtime/gtk3`, now built by `board/aos/runtime-gtk3.sh`
   rather than by hand) gained GTK3's X11 backend and libXcursor for
   Firefox. Discord is its own bootstrap: the application lives and
   updates in the account's home, as Discord does everywhere. *Steam done
   2026-09-23*: Valve's launcher package as a recipe (`st/valve.steam`),
   its 64-bit SteamRT3 client selected by `STEAM_FORCE_CLIENT`, running in
   `aos-sandbox` with `runtime/compat32` bound at `/lib` for the one 32-bit
   program left, the bootstrap's updater; the sign-in window draws on ade
   through XWayland with GLX (`steam-after.screen.png` in the boot test).
   Games are the next proof, on hardware: Proton needs the GPU, and the
   compositor's direct-scanout path (Phase 3, item 4). Open, seen on the
   G14 2026-09-24: Steam's install dialog named the library's drive by
   a path under `/run` and Install did nothing. The journal on the stick
   (persistent on an installed system) and Steam's own logs show a
   healthy client, a second library made at `/home/admin/games`, and no
   install ever attempted: the button never reached the content system.
   Steam's client runs in its own container (pressure-vessel), whose
   mount table starts with the host's `/usr` at `/run/host/usr` on every
   distribution -- seen on Fedora too, running the same tool from the
   stick -- so that alone is not it. What differs on AOS: the sandbox's
   root and its `/home` are tmpfs, so no device-backed mount covers the
   home's filesystem as a whole, where a normal distribution has "/".
   Round 6 named it: the entry reads `/run/host/usr`, the first mount
   on the home's disk inside the container -- and the install works
   regardless; only the label is odd. A `/home` of its own would fix
   the label; not worth an installer change for a label. (Also fixed on the way: on a stick-installed system
   the media rule mounted the OS's own root and ESP again under
   `/run/media`; `aos-media` skips the disk `/` lives on.)
   Seen on the G14, 2026-09-26, fixed 2026-09-28: every page in
   Firefox rendered as hex boxes while its own chrome was fine. The
   content processes run in Firefox's sandbox, which reads fonts only
   from directories Firefox names itself (`/usr/share/fonts` and a
   few more) and never learns fontconfig's; AOS keeps the fonts and
   the runtime under `/opt/apm`. Firefox release 2 ships a default
   preference (`security.sandbox.content.read_path_whitelist`) that
   opens the store to them read-only, and the boot test's Firefox
   window now shows a text page rather than the New Tab. These are release
   gates, not extras: if they do not run, the platform does not sell.
   Open: twice the boot test saw a program's first `mkdir` in the home
   fail with "No space left on device" on a disk with 17 GB free, right
   after a large install (Steam once, Discord once); not reproduced by
   hand, not understood, to be caught with `df`, `df -i` and `dmesg` at
   the moment it happens.
8. **Session basics a consumer expects.** *Sound done 2026-09-22*:
   PipeWire and WirePlumber as session services, a sink on QEMU's HDA card
   checked every desktop boot ([../PLATFORM.md](../PLATFORM.md) has the
   three things that had to be right: modular controller, ACL through
   logind, real-time through the pipewire group). *SOF and ACP added 2026-09-28*: the SOF
   driver for every Intel generation from Bay Trail to Nova Lake,
   SoundWire, the generic HDA and SoundWire machine drivers and the I2S
   boards, the Cirrus and TI amplifiers gaming laptops hang beside an HDA
   codec, and AMD's ACP drivers, legacy and SOF; the firmware is the
   `sof-firmware` package (sof-bin, since linux-firmware no longer
   carries it; AMD's SOF firmware is in neither, so AMD runs the legacy
   ACP path). QEMU cannot test any of it; the G14 (Panther Lake) is the
   first check. *Bluetooth 2026-09-30*: the kernel stack and btusb,
   BlueZ with its audio and HID plugins started by udev's
   `bluetooth.target`, PipeWire's BlueZ backend (sbc, opus), a
   Bluetooth page in Settings (settings v0.1.13); UPower beside it for
   the programs that ask D-Bus about the battery. Also untestable in
   QEMU; the G14 checks it.
   Round 10 on the G14, 2026-10-01, the first boot of the A/B layout
   (which worked), six findings, all fixed the same day: no Bluetooth
   adapter -- the G14's BE201 hangs its Bluetooth off PCIe and the
   kernel had only btusb (`CONFIG_BT_INTEL_PCIE`), and Settings froze
   for twelve seconds asking bluetoothctl about a daemon that never
   started (it looks in sysfs first, settings v0.1.15); the SoundWire
   card was found and silent -- no ALSA UCM profiles on the image
   (`alsa-ucm-conf`); the brightness slider changed the NVIDIA GPU's
   own backlight, first in sysfs, not the panel's (the eDP one wins,
   settings v0.1.15, ade v0.1.24; a udev rule and the `video` group let
   the shell write it); the time zone set in Settings never reached the
   bar's clock -- `localtime_r` reads the zone once per process (`tzset`
   first, aos-sdk v0.4.9); every window soft at 200% -- the compositor
   told only the lock screen the output's scale, so each client drew at
   1x and was stretched (ade v0.1.24 sends it to every surface); and the
   quick panel's rounded corners were black because every awin surface
   was opaque (layer surfaces are translucent, aos-sdk v0.4.9; the
   overview and launcher are rounded too).
   *Lock screen done 2026-09-25 (ade v0.1.11)*: `ade-lock` on
   `ext-session-lock-v1`, the password through PAM (`/etc/pam.d/ade-lock`),
   Super+L and the Settings Power page start it, and the compositor
   keeps the session locked and restarts a locker that died. Then:
   *The desktop's chrome, 2026-09-28 (ade v0.1.17)*: the Super tap
   opens an overview -- search, the applications as tiles, the running
   ones as a dock along the bottom that brings a window up or, with
   several of one application, offers them by title; Super+A keeps the
   quick launcher; the bar shows the network, battery and volume beside
   the clock, and a click there opens a quick panel with the session
   buttons, volume and brightness sliders and tiles into Settings. The
   shell asks the compositor for its windows over a control socket.
   *Icons, 2026-09-29 (aos-sdk v0.4.5, ade v0.1.18)*: tgn draws
   pictures -- PNG, JPEG, and SVG rasterised at the asked size -- on a
   frame, and the tiles show each application's icon from its desktop
   entry; the image installs the official applications' SVGs into the
   hicolor theme. *An image viewer the same day*: `images`
   (Jaxilian/images, in the image and in apm as `aos/images`), PNG,
   JPEG and SVG, the folder walked with Left and Right, zoom and pan,
   turns and Set as Wallpaper (ade's wallpaper draws a picture since
   v0.1.19); Files opens a picture with it, and `/etc/xdg/mimeapps.list`
   makes it the system's default for PNG, JPEG and SVG. Fixed on the
   way: tgn uploaded pictures as sRGB onto a UNORM swapchain, so every
   icon and picture was drawn as a dark fade of itself (aos-sdk v0.4.7). Then:
   screenshot, clipboard, drag-and-drop, Bluetooth. Printing can
   wait. Seen on the G14, 2026-09-23: Visual Studio Code died on Open
   Folder -- GTK's file chooser aborts without its GSettings schema, and
   the GTK3 runtime shipped the schema as XML only, since Buildroot
   compiles schemas for the image at finalization and no package lists
   the result; br2apkg compiles them now (runtime/gtk3 release 4), and
   apm treats a newer release of the same version as an upgrade (v0.1.2),
   which it did not before, so the fix could have reached nobody. There is
   no desktop portal: Electron falls back to GTK's dialog, which is fine
   until the portal becomes the way to file pickers and screen sharing.
   Smaller, fixed in the apps 2026-09-28: the terminal rewraps its
   lines when the window changes width (terminal v0.1.5); in Files, a
   right-click on a sidebar entry painted the entry black until the
   menu closed -- the rows under the popup are hidden while it is up
   (files v0.1.5); the desktop keyboard layout had no
   setting -- `/etc/ade/environment` with `XKB_DEFAULT_LAYOUT=se` is
   the way today ([keyboard.md](keyboard.md)); the Settings application's
   Keyboard page writes it since 2026-09-25.

## Phase 3 — Stability and performance

1. **A soak test in CI.** *Done 2026-09-22*: `boot-test.py soak` holds
   the session, opens and closes a terminal and notepad every round, and
   fails on compositor memory growth, a failed unit, a leftover window or a
   watchdog reboot ([testing.md](testing.md)). The nightly workflow runs
   eight hours of it after the build. First run: 147,740 kB flat.
2. **Suspend, resume and lid-close** on every machine on the hardware list.
   The most common laptop failure. Worked through on the G14 in rounds
   13-17 (input after resume, the NVIDIA GPU's memory, the lock before
   sleep); no second machine yet, and QEMU cannot resume from S3.
3. **Boot-test the release path.** *Done*: `boot-test.py` exercises the
   demo image; `INSTALL_MODE=owner|oobe|encrypt` installs the other kinds
   of disk, and `greeter-test.py`, `oobe-test.py`, `luks-test.py` and
   `setup-test.py` (the graphical installer) drive them
   ([testing.md](testing.md)).
4. **A gaming baseline.** A Vulkan game at native resolution on Intel, AMD
   and NVIDIA, through ade-comp's direct-scanout path, measured against a
   stock distribution. Steam with Proton is the real test. Variable refresh
   and 10-bit output come later. *NVIDIA made usable 2026-09-25*, for the
   G14's RTX 5070 Laptop (Blackwell, so the open kernel modules are the
   only choice): the image had the modules and EGL but not the Vulkan
   driver (libGLX_nvidia, which the Vulkan manifest names), not the
   Wayland/GBM/X11 EGL platforms its manifests named, no /dev/nvidia*
   nodes (udev now runs nvidia-modprobe), no nvidia-drm (a softdep on
   nvidia, so machines without the GPU load nothing), and nouveau, which
   won the GPU and left it dark without GSP firmware (blacklisted). The
   sandbox passes the nodes through; `prime-run` offloads a program. Not
   yet proven on the hardware, and no 32-bit NVIDIA libraries yet (32-bit
   GL games under Proton). Open: the G14's HDMI port belongs to the NVIDIA
   GPU, and the compositor drives the connectors of one DRM device only;
   output on a second GPU's connectors (smithay's GpuManager) is big and
   not started.
5. **A crash story.** coredump and journald are configured. *`aos-report`
   added 2026-09-22*: one command, one tarball -- this boot's journal, the
   errors, failed units, the compositor's log, the hardware, what apm has
   installed. The Settings application's About page has a Save Report
   button that runs it (2026-09-25).
6. **Fault isolation.** *Done 2026-10-01 (ade v0.1.25)*: a shell that
   dies is started again by the compositor, after a pause that doubles
   from a second to thirty; a compositor crash is restarted by its unit
   within two seconds, the session comes back locked if it was locked,
   and the next shell shows a toast saying what happened (the unit
   writes `/run/ade/crash`, the compositor passes it on); four crashes
   in two minutes stop the unit and `ade-failed.service` puts a login
   prompt on tty1 under an explanation of what to run. A desktop that
   restarted this boot does not confirm a trial slot. Panics print a
   backtrace to the journal, and `aos-report` carries `coredumpctl`.
   `crash-test.py` kills the shell, the locked compositor and the
   compositor five times, in QEMU.

## Phase 4 — Hardware and the evaluation

1. **A hardware compatibility list.** Today one machine, an ASUS G14. Done:
   three to five more — an Intel-graphics laptop, an AMD APU, an NVIDIA
   desktop, and a machine from around 2012 for the x86-64-v2 floor — with
   pass or fail per feature: boot, graphics, Wi-Fi, suspend, audio,
   touchpad.
2. **Reference hardware.** One machine that is *the* AOS machine, where
   everything is made perfect first. That is the hardware story, and the
   machine an evaluator is handed. A preinstalled machine has no owner
   yet; the first-boot setup (Phase 2, item 2, done 2026-10-05) is what it
   ships with. Never a placeholder account with a known password. A second
   test machine (an Intel or AMD laptop) is postponed until there is one.
3. **One use case the evaluation wins at.** "Runs anything" is the vision;
   the evaluation needs a single thing AOS does better. With what works
   today, that is a developer workstation — Visual Studio Code, gcc and Rust,
   nothing to configure. Gaming becomes the second once Steam runs.
4. **Documentation for someone who is not the author.** *Written
   2026-10-01*: [install.md](install.md) (download, verify, the stick,
   the installer, after) and [known-issues.md](known-issues.md). Still
   owed: a public place to download the ISO from. *Done*: `release.sh
   --iso-to` since 2026-10-01, and this repository (Jaxilian/aos) public
   since 2026-10-03; `release.sh --publish
   --iso-to Jaxilian/aos-releases` puts each release's ISO, `SHA256SUMS`,
   signature and key there ([publishing.md](publishing.md)).

## Verification

Each phase ends the same way AOS has always been tested — see
[testing.md](testing.md): build, boot in QEMU, run `boot-test.py`, and look
at the screen, not just the serial line. Real hardware for what QEMU cannot
emulate. Every item above names a state that can be checked: a `.config`
symbol, a green CI run, a signed file, a screendump, a machine on a list.
