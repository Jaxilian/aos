# Testing AOS

Most of this runs in QEMU. You do not need a spare machine, and you do not
need root.

Four things QEMU cannot test at all, because it does not emulate them: CPU
microcode application, frequency scaling, a real chipset watchdog, and the
GPU drivers. Those need real hardware — install AOS on a machine and work on
it over SSH, see [ssh.md](ssh.md). The first real-hardware boots found
three gaps of exactly that kind — the `xe` GPU firmware, the `iwlmld` Wi-Fi
driver, and a card reader that floods the bus with correctable PCIe errors
when it has no driver — that every QEMU run had passed over.

```sh
./br2ext/board/aos/run-qemu.sh            # live ISO, UEFI, in a window
./br2ext/board/aos/run-qemu.sh bios       # live ISO, legacy BIOS
./br2ext/board/aos/run-qemu.sh install    # live ISO + a fresh blank 32 GB disk
./br2ext/board/aos/run-qemu.sh disk       # boot what you installed
```

The live ISO and a demo install start the desktop as `admin`; on the
serial console log in as `root`, no password (root logs in nowhere else).
Add `serial` as an extra word to run in the terminal instead of a window.

## Installing to the virtual disk

```sh
./br2ext/board/aos/run-qemu.sh install
```

Then inside the VM:

```sh
aos-install --demo /dev/vda   # type YES when asked; takes a few minutes
                              # without --demo the first boot asks for the owner
poweroff
```

or, on the desktop, Super and "Install AOS": the graphical installer
(aos-setup), which runs the same `aos-install`.

And from the host, `run-qemu.sh disk` to boot the result.

## Checking it actually works

The point of AOS is that it compiles on itself, so that is the test:

```sh
cc --version && rustc --version
echo 'fn main(){println!("hi");}' > /tmp/t.rs && rustc /tmp/t.rs -o /tmp/t && /tmp/t
cargo new /tmp/p && cd /tmp/p && cargo build
```

That last one is the real check — it exercises rustc, cargo, gcc as the
linker, binutils and the glibc development files together.

Graphics and drivers:

```sh
ls /usr/share/glvnd/egl_vendor.d/    # mesa and nvidia both registered
ls /usr/share/vulkan/icd.d/          # intel, amd, llvmpipe, virtio, nvidia
lsmod | grep nvidia
```

Init and networking:

```sh
systemctl --failed                   # expect "0 loaded units listed"
journalctl -b -p err                 # errors from this boot, kernel included
loginctl                             # your login shows as a session with a seat
networkctl                           # the NIC should be "routable"
swapon --show                        # zram0 everywhere; /aos/aos/swapfile too once installed
journalctl -k | grep -i microcode    # the early initrd was found and applied
journalctl -b | grep e2fsck         # the initramfs checks the aos partition; the core is verity, not fsck'd
systemctl show -p RuntimeWatchdogUSec  # 30s where a watchdog device exists
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor   # schedutil (no cpufreq in a VM)
systemctl list-timers                # fstrim weekly
```

## Unattended runs

`boot-test.py` boots the image in QEMU with no one watching: it drives the
serial console, runs a list of checks over it, and always ends in a
screendump, because a boot can look perfect on serial while the screen stays
black.

```sh
./br2ext/board/aos/boot-test.py live      # the ISO in an optical drive
./br2ext/board/aos/boot-test.py usb       # the ISO as a USB mass-storage device
./br2ext/board/aos/boot-test.py install   # live ISO + blank 32 GB disk, runs aos-install
./br2ext/board/aos/boot-test.py disk      # boot what install left behind
./br2ext/board/aos/boot-test.py desktop   # the ade session
./br2ext/board/aos/boot-test.py soak      # the session held and churned; see below
```

It writes `<mode>.serial.txt` and `<mode>.screen.png` next to the images.

Two more scripts drive the session itself through QEMU's monitor and QMP
(clicks, keys, box-diffed screendumps): `ade-test.py` on the live ISO
(popup grabs, the live keyboard layout, a second display), and
`disk-test.py` on the installed disk, where it copies the working-tree
`ade-comp`, `ade-shell`, `settings` and `sysmon` from `output/target` in
over ssh first -- a compositor change tested without an ISO -- and
installs Firefox and Xwayland from the repositories the disk knows.
Every test on the installed disk wants the keyed build in `output/images`
(`board/aos/authorized_keys` present at `make`): `update-test.py` writes
the build's core into the disk's slots, and a keyless one takes
sshd and root's key off the disk, after which nothing can be copied in.
`update-abort-test.py` kills QEMU while `aos-update` is writing the idle
slot, then checks the machine boots its slot as before, `--rollback`
refuses the half-written one, and a second update completes; run it
after `update-test.py`, whose last boot leaves the disk where this one
expects it. `update-test.py`, also on the installed disk, is a base-OS update
([upgrading.md](upgrading.md)): the build's own `core.img` served from
the host as a fake release 9.9.9, signed with the local apm key, then four
boots -- the update into slot b, its confirmation, a rollback armed, the
trial of slot a forgotten -- with the mounts, the account and failed units
checked on each; with `--usb` the disk is a USB stick, as on the G14,
where udev once mounted the idle slot as media and stopped the update
at mkfs. Transcripts: `update-N.serial.txt`. `setup-test.py` is
the graphical installer end to end: the live ISO with a blank disk,
`aos-setup` started in the session with every answer on its command
line and `--go`, screendumps while it installs, then the disk booted and
the account, the session's user, the keyboard layout and the time zone
checked. It leaves the disk installed for `jax`; `boot-test.py install`
gives the other tests their demo disk back. `crash-test.py` kills the
shell (it comes back, the pause doubles), the compositor while the
session is locked (it comes back locked, the toast says so) and the
compositor five times in a row (the unit stops, tty1 gets a login
prompt under an explanation, `systemctl restart ade` recovers).
`store-test.py` fetches the index on the installed disk and screendumps
the store's pages. `upgrade-ui-test.py` is the update pipeline as a
person meets it, on the installed disk with the working tree's binaries
copied in: `aos-update-check` run as the two-minute timer would, the
shell's toast, a click on it opening Software's Update page, and -- with
`UPD_BX`/`UPD_BY` naming the Upgrade system button's place on the
maximised window's screendump -- the upgrade itself against a fake
release served from the host, with a screendump every few seconds while
apm runs and the `::os` progress lines checked in the update log. `shot-test.py` copies the working tree's compositor
and shell onto the installed disk, presses Print and Shift+Print through
QEMU's monitor, and copies the two PNGs back to look at. `sec-test.py`
is the security round on the live ISO: the sysctls applied, the kernel's
LSM list, and the bar's red "SSH open" following port 22 (stopped over
serial, then enabled again with sudo as the demo account, the way
Settings does it).

For a one-off look inside a booted guest without editing the check lists,
put commands in `BOOT_TEST_EXTRA`, separated by ` ;; `; every mode runs
them after the standing checks:

```sh
BOOT_TEST_EXTRA="lsmod | grep snd ;; su - admin -c 'XDG_RUNTIME_DIR=/run/user/1000 wpctl status'" \
  ./br2ext/board/aos/boot-test.py desktop
```

`desktop` checks the graphical session rather than the shell — necessary
because `ade.service` takes tty1, so the serial line is the only way in. It
waits for a window to reach the screen (not merely for the compositor to log
that it mapped one: under llvmpipe those are seconds apart), then presses
Super+Return and types into the terminal, both through the QEMU monitor's
`sendkey`. Going in that way is the point — the keystrokes travel the whole
path a real key does, through the emulated PS/2 controller, evdev, libinput,
xkbcommon and the compositor's binding table, none of which anything else
here exercises. It leaves three screendumps: `desktop`, `desktop-spawned`
and `desktop-typed`.

`soak` is the leak test. It holds the desktop for `SOAK_MINUTES` (20 by
default; the nightly job runs 480), and every `SOAK_INTERVAL` seconds (60)
opens a terminal and closes it, opens notepad and closes it, then prints a
row: resident set of ade-comp, ade-shell, pipewire and wireplumber, failed
units, journal errors, uptime, leftover windows. After a three-round
warmup the compositor's memory is the baseline; it fails if that grows by
more than 24 MB *and* 20% by the end, if a unit has failed, if a window
was left behind, or if uptime went backwards (the watchdog fired). A
minute's worth is `SOAK_MINUTES=2 SOAK_INTERVAL=20 boot-test.py soak`.

One thing to know when reading its output: the compositor's own log lines are
not under `journalctl -u ade`. `PAMName=login` hands the process to logind,
which moves it into a session scope, and journald files its output there.
Use `journalctl -b _COMM=ade-comp`. On an owned machine (greetd) the
session script sends everything the session prints through
`systemd-cat`: `journalctl -b -t ade-session` (the greeter's own
compositor: `-t ade-greeter`).

## The gate: every driver in one run

`br2ext/board/aos/gate.sh` runs every driver above in the order the
disks need -- the live ISO's, then an owner, an OOBE and an encrypted
disk with theirs, then the demo disk with the rest -- and prints one
`pass`/`FAIL` line per driver and `GATE OK` or `GATE FAILED` at the end.
It makes the keyed build first (`board/aos/authorized_keys` must be
there) and the keyless one last, which is what a release and a stick
need; `--no-build` and `--keep-keys` skip those, and driver names
(`gate.sh greeter clip`) run a subset with the disk each needs. Logs
and the screendumps every driver left are under `output/gate/`. It
takes hours: run it in the background. A release is tagged only after
the gate is green (section 6 of WORKFLOW.md).

## Every script, one line each

`INSTALL_MODE=owner|oobe|encrypt` before `boot-test.py install` makes the
other kinds of disk; run a plain `install` afterwards, since the disk
drivers log in as the demo account. "Disk" below means the installed
QEMU disk of the keyed build.

| Script | What it drives |
|---|---|
| `boot-test.py` | live, usb, install, disk, desktop, soak (and probe, apm): boot, serial checks, screendump |
| `ade-test.py` | live ISO: popup grabs, a menu item that runs, the live keyboard layout, the overview, a second display |
| `clip-test.py` | disk: Files' rename field, F2 then Ctrl+C, must reach the clipboard (fails today: Files' old prompt) |
| `crash-test.py` | disk: shell killed, compositor killed while locked, compositor killed five times |
| `desk-test.py` | disk: Notepad's unsaved-text dialog, minimize and restore from the dock, the dock's right-click menu |
| `disk-test.py` | disk: the working tree's binaries copied in; overview keys, Firefox and Xwayland from the index, popups, sysmon's menu |
| `disp-test.py` | disk: two displays, the order= and off= lines followed by the compositor |
| `fx-test.py` | disk: quick panel glass, the snap ghost, the minimize animation, the screenshot toast opening Images |
| `greeter-test.py` | `INSTALL_MODE=owner`: the login screen, a wrong and a right password, Super+L with an OSD while unlocking, the session's journal, the compositor killed while locked and five times |
| `homed-test.py` | `INSTALL_MODE=oobe`: the first boot makes the owner's encrypted home, the recovery key printed for the driver; console, sudo, login screen, lock all open with the password; a second boot opens with the recovery key |
| `luks-test.py` | `INSTALL_MODE=encrypt`: the initramfs's passphrase prompt on serial, wrong then right |
| `mic-test.py` | disk: the nomic PipeWire sockets refuse capture; aos-sandbox with and without `--microphone` |
| `oobe-test.py` | `INSTALL_MODE=oobe`: the setup user's welcome, aos-firstboot making the owner, the login screen after |
| `perf-test.py` | live ISO: seconds to login and first window, memory at idle, app start times (output/images/perf.json) |
| `perm-test.py` | disk: Software's Permissions on a package page, the "restart to finish" state, Settings' Open Software |
| `replug-test.py` | live ISO: a second display unplugged and plugged back gets its bar and wallpaper again (QEMU leaves the head blank; for the journal) |
| `sec-test.py` | live ISO: sysctls, the LSM list, the bar's red "SSH open" following port 22 |
| `setup-test.py` | live ISO + blank disk: the graphical installer end to end; leaves the disk installed for `jax` |
| `shot-test.py` | disk: Print and Shift+Print, the two PNGs copied back |
| `steam-test.py` | disk: Steam's sandbox declaration, the farm entry and the 32-bit loader inside the sandbox |
| `store-test.py` | disk: the index fetched, Software's pages screendumped |
| `theme-test.py` | disk: the bar follows the theme file's effects= line without a restart |
| `update-test.py` | disk: a fake 9.9.9 core written into slot b, confirmed, rolled back, a forgotten trial (`--usb` for a stick) |
| `update-abort-test.py` | disk: QEMU killed mid-write; the old slot boots, `--rollback` refuses, a second update completes |
| `upgrade-ui-test.py` | disk: the update check, the toast, Software's Update page, Upgrade system against a fake release |
| `auto-install.py` | not a test: types the install for `write-usb.sh --install --auto`, and `--boot --auto`'s login check |
| `iso-gpt.py` | not a test: trims and checks the live ISO's GPT after xorriso (a build hook) |
| `br2apkg.py` | not a test: lifts Buildroot packages out of the target into an apm package (the runtimes) |

## Three traps

**Never use `sudo`.** QEMU with KVM does not need root, and running as root
leaves the disk image and firmware files owned by root — after which a normal
run cannot open them. The script refuses to start as root and tells you how to
clean up.

**Use the script, or copy its QEMU flags.** AOS is built for x86-64-v2, and
QEMU's default CPU model predates SSE4.2 — the image panics inside `ld-linux`
before reaching userspace. The script passes `-cpu host` (or `Nehalem`). If
you use GNOME Boxes or virt-manager, set the CPU to host passthrough.

**Serial alone is not proof.** A boot can look perfect on the serial console
while the screen stays black. That exact bug shipped here once: without
`CONFIG_DRM_FBDEV_EMULATION` there is no framebuffer console under UEFI. To
check the screen from a script:

```sh
{ sleep 45; echo "screendump /tmp/s.ppm"; sleep 2; echo quit; } | \
  qemu-system-x86_64 -enable-kvm -m 4G -cpu host \
    -drive if=pflash,format=raw,readonly=on,file=/usr/share/edk2/ovmf/OVMF_CODE.fd \
    -drive if=pflash,format=raw,file=/tmp/vars.fd \
    -cdrom output/images/rootfs.iso9660 \
    -display none -vga std -monitor stdio -no-reboot
```

Then look at `/tmp/s.ppm`. A black screen is a few hundred bytes of solid
colour; a working console is visibly text.
