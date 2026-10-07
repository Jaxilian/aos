# How to work on AOS

The working method for Claude sessions in this tree, distilled from the
rounds of September and October 2026. CLAUDE.md imports this file. Keep it
true: when a step here turns out wrong, fix this file in the same commit.

## 1. Where things are

This directory is an unmodified Buildroot checkout. Everything AOS lives
under `br2ext/` (a BR2_EXTERNAL tree), so pulling Buildroot never conflicts.

| Path | What |
|---|---|
| `br2ext/configs/aos_x86_64_defconfig` | the image: packages, kernel, rootfs format |
| `br2ext/board/aos/linux.config.fragment` | kernel options on top of x86_64_defconfig |
| `br2ext/board/aos/rootfs-overlay/` | every AOS file in the image: aos-install, aos-update, slot.sh, units, PAM, greetd, PipeWire config |
| `br2ext/board/aos/initramfs/` | the initramfs: opens the verity core, mounts the aos partition |
| `br2ext/board/aos/post-build.sh`, `post-image.sh` | target fixups, initramfs, core.img + ISO assembly |
| `br2ext/board/aos/*-test.py` | QEMU drivers (section 4) |
| `br2ext/board/aos/release.sh` | publish a release |
| `br2ext/package/<pkg>/` | AOS packages, pinned by git commit + `.hash` |
| `br2ext/docs/` | design docs; `layout.md` is the disk and boot design |
| `TODO.md` | state of the work, newest first, and open decisions |
| `TEST.md` | the hardware round the user runs on the stick |

The apps live in their own repositories and are pinned here by commit:

| Repo (local path) | Package |
|---|---|
| `../ade` (compositor, shell, lock; branch master) | ade |
| `../apm` (package manager) | apm |
| `../store` (Software) | aos-store |
| `../settings` | settings |
| `../setup` (graphical installer, first boot) | aos-setup |
| `../greeter` (login screen) | ade-greeter |
| `../images`, `../sysmon` | images, sysmon |
| `~/Projects/Rust/notepad`, `files`, `terminal` | notepad, files, terminal |
| `~/Projects/Rust/aos-sdk` (awin + tgn; tagged vX.Y.Z) | used by every app above |
| `../apm-recipes`, `../apm-thirdparty` | package indexes (`publish.sh`) |

`../aos-sdk` is NOT the SDK; `~/Projects/Rust/aos-sdk` is.

Rust in every repo follows the user's global style (C-like: modules and
free functions, plain pub structs, `/* */` comments, explicit `match`).

## 2. Start of a session

1. Read `TODO.md` top to bottom and the top of `TEST.md`: what was
   released last, what is untested, what decisions are open.
2. `git status` here and in any app repo you will touch. Uncommitted work
   may be a previous session's that waits for the user's hardware check;
   do not commit or discard it without reading TODO.md and memory first.
3. `cat local.mk`: a dev override left behind changes what `make` builds.
4. If the user mentions the stick, it is the ASUS G14 test machine, which
   is also this build host. Hardware questions can be answered from the
   host (`lspci`, `lsusb`, `/sys`) as well as from the stick's journal.

## 3. Building

```sh
make                               # the whole image, incremental
make <pkg>-rebuild                 # one package after a source change
make <pkg>-reconfigure             # after changing its config options (util-linux, kernel)
make linux-reconfigure             # after editing linux.config.fragment
make aos_x86_64_defconfig          # after editing the defconfig; then make
```

Outputs in `output/images/`: `core.img` + `core.verity` (the root core),
`rootfs.iso9660` (the live ISO), `bzImage`.

**Dev loop for an app repo:** put `<PKG>_OVERRIDE_SRCDIR = /path/to/repo`
in `local.mk`, then `make <pkg>-rebuild && make`. Remove local.mk before
any release build.

Traps that cost hours before:
- A file deleted from `rootfs-overlay` stays in `output/target`; `rm` it
  there by hand before `make`.
- A package option added without a prompt default hangs a background
  `make` at a kconfig question: run `make olddefconfig` first.
- New programs in util-linux (or any autotools package) need
  `-reconfigure`, not `-rebuild`.
- `BR2_TARGET_ROOTFS_SQUASHFS_COMP_OPTS` has no prompt; squashfs arguments
  go in `external.mk` (`ROOTFS_SQUASHFS_ARGS +=`).
- The core is read-only: mount points the initramfs needs must exist in
  the target (post-build.sh `mkdir -p`).
- The initramfs has only the tools `initramfs/mkinitramfs.py` lists. No
  sed, awk, readlink: a silently empty variable is the symptom.

## 4. Testing in QEMU

Every change is checked in QEMU before it reaches the user. The drivers
boot the build, log in over serial, run commands and screendump the VGA
output. Always look at the screendump, not only serial: serial-only
checks have hidden a black screen.

```sh
python3 br2ext/board/aos/boot-test.py live      # the ISO
python3 br2ext/board/aos/boot-test.py desktop   # the ISO, the session end to end
python3 br2ext/board/aos/boot-test.py install   # ISO + blank disk, aos-install --demo
python3 br2ext/board/aos/boot-test.py disk      # boot what install left
python3 br2ext/board/aos/boot-test.py usb       # the ISO as a USB stick
```

`INSTALL_MODE=oobe|owner|encrypt` before `install` makes the other kinds
of disk; `oobe-test.py`, `greeter-test.py`, `luks-test.py` then drive
them. Run a plain `install` afterwards: the other drivers log in as the
demo account. Feature drivers (`update-test.py`, `fx-test.py`,
`mic-test.py`, `theme-test.py`, `desk-test.py`, ...) need an installed
disk and a **keyed** build, since they scp files in: copy your public
key to `br2ext/board/aos/authorized_keys`, `make`, run them, then
remove the key and `make` again. Since 2026-10-07 no stick and no
release carries a key (docs/ssh.md); the tree has none by default.

Writing a new driver: copy the shape of an existing one (import
boot-test.py and disk-test.py as modules, `bt.Serial`, `ser.run`,
`bt.shot`, `dt.Qmp` for mouse input via QMP, `bt.typekeys` for keys).
Traps:
- `ser.run()` output carries the shell prompt on its first line; strip
  `"# "` before using a line as a command.
- In `su -c 'ENV cmd; cmd2'` the env prefix reaches cmd only: write
  `export ENV;`.
- `pkill -f PATTERN` kills your own shell when the pattern is in your
  command line; kill by pid. `pkill -x qemu-system-x86_64` never matches
  (comm is 15 chars).
- QEMU runs with `-no-reboot`: a reboot ends the VM; boot twice instead.
- A greetd session's output goes to the VT: read it with `cat /dev/vcs1`.
- Real sticks can be booted in QEMU after the user runs
  `sudo setfacl -m u:jax:rw /dev/sdX` (until replug).

Rust: `cargo check`, `cargo test` in the app repo before any commit.

## 5. App repos and the SDK

1. Change, `cargo test`, commit, push (`git push origin HEAD`; ade's
   branch is master).
2. An SDK change: commit in aos-sdk, tag the next `vX.Y.Z`, push the tag,
   then bump the tag in every app's Cargo.toml (ade has three crates:
   comp, shell, lock) and `cargo update -p tgn -p awin`. Commit the
   Cargo.lock with the bump, or Buildroot's vendoring fails with "failed
   to load lockfile".
3. Repin in this tree: set `<PKG>_VERSION` to the commit in
   `br2ext/package/<pkg>/<pkg>.mk`, `make <pkg>-source || true` (it leaves
   the tarball despite the missing hash), write the `.hash` from
   `dl/<pkg>/<pkg>-<commit>-git4-cargo6.tar.gz`, `make <pkg>-dirclean`.

## 6. Releasing

The user asks "commit, push and publish", or a round ends with fixes. A
release is a tag on HEAD built from a clean tree without SSH keys (the
tree has none unless you added one for the drivers):

1. Write the chain as a script in `~/Projects/OS/chains/` (never only in
   /tmp: the scratchpad has been wiped mid-session) and check `wc -l`
   before running it. The last ones there are the template.
2. The chain, in order: repin changed packages and write hashes; `rm -f
   local.mk`; `rm -f br2ext/board/aos/authorized_keys` (a driver round
   may have left one); update
   TODO.md and TEST.md (expected version); `git add -A`; commit with a
   message that says what changed and why; `git tag vX.Y.Z` (tag before
   `make`: post-build reads `git describe`); dirclean repinned packages;
   `make`; the QEMU checks (desktop, install, disk at least; plus the
   drivers for what changed, and the owner/oobe paths when the session or
   installer changed); `release.sh --publish --iso-to Jaxilian/aos-releases`;
   publish package indexes if recipes changed; `git push origin main
   --tags`. The build left behind is what `./usb.sh --no-build` writes:
   keyless, sshd off.
3. Run it in the background and poll its log; if a check fails, stop,
   fix, `git tag -f`, rerun.
   The auto-mode classifier refuses to write a script that names
   `release.sh --publish` or `git push` (a public surface), so since
   0.3.0 the chain ends after the tag and its checks, and the user
   runs the publish and the push as two commands (docs/publishing.md).
   Do not try to get the same outcome another way.
4. release.sh refuses a dirty build, a BUILD_ID that is not the tag, and
   an image with root SSH keys or sshd enabled. Those refusals are right.
5. A tag push starts CI on the self-hosted runner on this laptop. The
   user paused it on 2026-10-07 (`systemctl --user disable --now
   aos-runner`); do not turn it back on unless asked.

## 7. The hardware round

Claude cannot sudo here and cannot write sticks. The user runs:

```sh
./usb.sh --no-build --release /dev/sdX   # an owned machine: login screen, sudo with a password
./usb.sh --no-build /dev/sdX             # the demo account, autologin
./usb.sh --no-build --oobe /dev/sdX      # asks for its owner at the first boot
```

usb.sh refuses an image with a root SSH key (`AOS_DEV=1` overrides,
for a development stick only).

After a round the user plugs the stick in. Its aos partition mounts at
`/run/media/jax/aos`; read the journal with
`journalctl -D /run/media/jax/aos/aos/var/log/journal -b 0` and the /etc
overlay under `aos/etc/upper` (`c--------- 0,0` entries there are
overlay whiteouts: deletions, not files). A second mount of slot a's
squashfs (e.g. `/run/media/jax/disk`) is read-only and needs nothing.
`issues.md` and reports are in `users/<name>/`.

Explain each finding from the journal before fixing it. A symptom that
only shows on the G14 often does not show in QEMU (unit ordering races,
two AOS disks attached, the NVIDIA GPU): reproduce it in QEMU first when
possible, and add the check to a driver so it stays fixed.

## 8. Writing it down

- `TODO.md`: a section per round at the top (what was done, what is
  open, why), the release line in the header.
- `TEST.md`: what the user should check on the stick, numbered, each step
  with what to do and what to expect. Only what changed; the user said a
  long TEST.md is fine, unchanged steps are not.
- `br2ext/docs/`: the design, when it changes (layout.md, upgrading.md,
  security-model.md, performance.md).
- Memory (`~/.claude/projects/-home-jax-Projects-OS-aos/memory/`): one note
  per round with the traps hit and the facts a later session needs.
- Commit messages: `aos X.Y.Z: <what a person notices>`, then a paragraph
  on the cause and the fix. End with the Co-Authored-By line the session
  is given.

## 9. Decisions that are the user's

Settled: systemd owns the core and stability comes first (no minimalism
or own-init pitches); verity cores + the aos partition (docs/layout.md);
the kernel ships with the OS, not apm; LUKS on the aos partition from the
installer; greetd + ade-greeter; per-user homes through systemd-homed;
the file dialog is ours, by fd passing, for AOS apps first.

Ask before: changing what a disk holds or how it boots, dropping a
feature the user asked for, publishing anything new to a public repo,
enabling the CI runner.
