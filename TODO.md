# TODO

Updated 2026-10-06 morning. The newest release is 0.1.27 (0.1.23: the
desktop round; 0.1.24: the first-boot setup; 0.1.25: glass on the
chrome, two displays; 0.1.26: the trim, Steam's sandbox, Camera, the
bar's glass; 0.1.27: the shell follows the theme at once). The stick
round is in [TEST.md](TEST.md).

## Morning (2026-10-06): the stick on 0.1.26, three issues

1. Steam "no X11 display" and 2. VS Code without a window: the same
   cause, XWayland on that stick still has no libpixman link (the apm
   bug of round 14; the links never came back). TEST.md 0.6 has the
   toggle. Nothing to fix in the OS; a fresh install never sees it.
3. "Glass theme isn't applied, probably need to reboot": the shell
   read the theme once at its start, so Settings' promise ("the
   desktop follows at once") held for the compositor's blur only.
   Fixed in ade v0.1.44 (the shell polls the files, sdk v0.4.14);
   theme-test.py drives it in QEMU. Released as 0.1.27.

Anything that needs a second machine, a second stick or a permanent
installation is postponed (see the end).

## Done 2026-10-04: Software owns updates (features.md on the stick)

- Settings' Software page is gone; About has an "Open Software" button.
- Software: Official marks the image's own applications installed (no
  Install on what is there); an AOS page (version, build, kernel, the
  system packages, the third-party and XWayland switches); Updates became
  Update: every pending package under Official / Third-party / AOS with
  old -> new, one "Upgrade system" button, and while it runs a line per
  package -- downloading with a percentage, building, installing, done,
  failed with the reason -- the OS line last, then Restart. A package's
  details page has Upgrade for that one package.
- apm v0.1.9: `--progress` (`::pkg`, `::dl`, `::os` lines); a failed
  package is skipped and reported, the rest and the OS update still run,
  exit 1 with the count. aos-update `--progress`, and a release already
  waiting in the idle slot is not written twice.
- The check runs two minutes after boot (then daily), rewrites
  /var/lib/aos/updates every time; the shell toasts once per boot when
  the file is new since boot, and a click on the toast opens
  `aos-store update` (ade v0.1.34).
- Test: `upgrade-ui-test.py` (docs/testing.md).

## Night round (2026-10-05, more of the list)

Done for 0.1.26: the image trimmed of what a desktop never loads
(board/aos/trim-target.sh from post-build: Intel Wi-Fi firmware
revisions the driver cannot pick, 230 -> ~60 MB; libclc's OpenCL
bitcode, libclang-cpp and diagtool, ~125 MB); Steam declares its
sandbox (apm v0.1.11 `lib32 =` in [sandbox], recipe release 7) so
Software shows what it sees and its Permissions; the Camera permission
(`camera =`, ";cam", aos-sandbox --camera binds /dev/video*), a switch
on a program's page (store v0.2.5); the bar paints the theme's panel
instead of its own opaque colour, so it is glass under chrome (ade
v0.1.43; in 0.1.25 it was the one solid thing). steam-test.py checks
the farm entry and the 32-bit loader inside the sandbox in QEMU.

## Evening round (2026-10-05, for the big validation)

Done for 0.1.25: the theme's third setting, `effects=chrome` -- glass on
the bar and panels, windows solid -- as the default (aos-sdk v0.4.13;
every application re-pinned, since an older SDK reads it as full
glass); Settings → Display arranges two displays (left or right of the
first, each on or off) through the file's order= and off= lines, which
the compositor follows (ade v0.1.40, settings v0.1.26); GRUB's menu
waits 2 s instead of 5 on an installed disk. disp-test.py drives the
two-display part in QEMU.

## Desktop round (2026-10-05 midday, asked after round 15)

Done for 0.1.23: windows minimize from the decoration and come back
from the overview's dock (ade v0.1.38); the dock is icons (initials
without one, the name on hover, a count), with a right-click menu
listing the windows with close marks and "Close all", a program that
ignores the request ended on the second press; a question dialog in
the window itself (tgn ui::dialog, aos-sdk v0.4.12) -- the Notepad
close that "couldn't" was the old external dialog needing zenity, which
the image lacks, so the guard failed silently (notepad v0.1.6).
desk-test.py drives the three in QEMU.

## Round 15 (stick on 0.1.21, 2026-10-05, free testing): what came back

Works: Bluetooth (adapter, scan, a long list), sound in Firefox, Steam
installed. Found: after a resume every input was dead -- logind had
revoked the devices during the pause, and the compositor re-activated
DRM only; it suspends and resumes libinput with the session now (ade
v0.1.37). The installer offered no disk because the kernel never saw
the NVMe: it sits behind Intel VMD (PCI domain 10000) and CONFIG_VMD
was off (fixed in the fragment). Software said "installed; restart to
finish" of the running release (the store now ignores the file for the
running version, v0.2.3). The Bluetooth list showed dozens of nameless
addresses (hidden unless paired, settings v0.1.25).
Asked: an account made at first boot instead of the demo account, so a
stick can be handed to someone -- the first-boot setup of roadmap
Phase 2; now item 2 below.

## Round 14 (stick on 0.1.20, 2026-10-05 morning): what came back

Works: the upgrade and restart, the Permissions section, the restart
state, Open Software. Found: XWayland lost libpixman -- apm's unexpose
unlinked every soname a package names, so the gtk3 upgrade took the X
runtime's shared links (fixed: only the package's own entries go, apm
v0.1.10; the stick needs XWayland off/on once). Firefox still silent,
but libpulse was there -- Firefox was older than the runtime; the next
round restarts it. Bluetooth: the bus answered with the adapter powered,
so Settings talks to BlueZ over zbus now (v0.1.24; scan and read proven
on the host). Resume: windows blank after a redraw, Firefox fine, no
error logged; TEST.md 3 runs Settings from a terminal across a sleep.
Brightness: 0 went black, other values did nothing; TEST.md 3b writes
the sysfs values by hand. The user's four extras done: toast text,
once per session, no "apm said", Back first. Also found: the update
tarball carries /etc/aos/live and sudoers.d/20-aos-live (the live
account's leave), and aos-update wrote them into every slot -- an
installed machine got passwordless sudo and no lock back with its
first update. Fixed: aos-update drops them unless the running system
has them. The stick is a demo install and has them by design, which is
why no lock screen ever showed; TEST.md 0.5 removes them once.

## Round 13 (stick on 0.1.19, 2026-10-04 afternoon): what came back

Works: boot, Upgrade system, restart into 0.1.19, XWayland, Firefox
(menus, downloads, dialogs), Programs, SSH mark, crash recovery.
Fixed for 0.1.20: Settings → Programs became the Permissions section
on each package's page in Software; a release already written into the
idle slot shows as "installed; restart to finish" (Restart, not Upgrade
again); the screen locks before sleep (logind's PrepareForSleep);
libpulse in runtime/gtk3 release 7, which is why Firefox was silent
(pipewire-pulse listened, nothing could speak to it).
Open, in priority order:

1. ~~**Resume.**~~ The input death is explained and fixed (round 15,
   libinput never resumed); whether the blank windows of rounds 13-14
   were the same thing (a window that cannot be clicked looks dead) is
   what round 16 tells.
2. ~~**Bluetooth: a client that talks to BlueZ.**~~ Done 2026-10-05
   (settings v0.1.24, zbus); pairing without an agent, so a keyboard
   that wants a passkey typed is still out. Untested on the stick.
3. **Brightness slider on the G14**: untested after the group change;
   TEST.md step 3b.
4. **The HDMI port is the NVIDIA GPU's**: the compositor renders on one
   DRM device (the Intel one) and never sees the other's connectors.
   Multi-GPU output: scan the second device's connectors and copy
   frames across (smithay's GpuManager). Big.
5. ~~**Glass only on the chrome**~~: done 2026-10-05 evening
   (effects=chrome, the default).
6. **Camera** done 2026-10-05 night (withheld unless the switch is on).
   **Microphone** still needs the PipeWire socket withheld or
   restricted, which also carries the sound output; PipeWire's access
   module is the road.

## Next, in priority order

Done since 2026-10-03 morning: the live ISO's account has no password
(0.1.16); release notes come from the commit log; binutils 2.46.1
closed eight CVEs and the systemd one is ignored with its reason
(0.1.17); a performance baseline exists
([br2ext/docs/performance.md](br2ext/docs/performance.md)); the CI
runner is installed on this laptop.

1. ~~**The kernel to 7.2.y.**~~ Done and published 2026-10-03 evening as
   0.1.18: 7.2.9 pinned, NVIDIA open builds against it, the fragment fixed
   for 7.2, all QEMU tests pass. The aos/kernel 7.2.9-3 package is in the
   public index and copies its modules into the slot (release 2 linked
   them into the store, which early boot cannot see). Untested on the
   stick: [TEST.md](TEST.md) step 0.
1b. ~~**Release 0.1.19 with the above.**~~ Done 2026-10-04 12:45: tags
   apm v0.1.9, store v0.2.0, settings v0.1.22, ade v0.1.34 pushed and
   pinned; ISO on aos-releases, tarball on the index, the three system
   apps published. Untested on the stick: TEST.md step 0.
1c. ~~**First-boot setup.**~~ Done 2026-10-05: `aos-install --oobe`
   (`./usb.sh --oobe`) leaves no account; a locked `setup` user's
   session runs `aos-setup --first-boot` (keyboard, time zone,
   account, Finish), which runs `/usr/libexec/aos-firstboot` through
   its one sudoers line: the owner is made, the session rewritten,
   the desktop restarted as them, the road closed. oobe-test.py in
   QEMU. Untested on hardware.
2. **CI's first real run.** `systemctl --user enable --now aos-runner`,
   then watch the v0.1.17 tag build at
   https://github.com/Jaxilian/aos/actions; fix what differs from a
   desk build. Stop the runner before a local release chain.
3. **Performance, from the baseline:** boot to login is 30 s in QEMU and
   the critical chain says where; the shell and the compositor hold 200
   and 150 MB resident at idle (llvmpipe inflates that; measure on the
   stick); the ISO is 1057 MB and the root tarball 520 MB, and
   `output/target` 2.7 GB: list what a desktop needs none of. Each a
   measured change, with perf-test.py run before and after.
4. ~~**Steam's sandbox declaration.**~~ Done 2026-10-05 night (apm
   `lib32 =`, recipe release 7); Steam itself untested since.
5. ~~**Display arrangement** and per-display on/off in Settings → Display.~~
   Done 2026-10-05 evening (order= and off= lines; left/right of the
   first display; QEMU-tested, hardware untested).
6. **A file dialog the desktop draws** for sandboxed programs, so they
   reach one chosen file outside their home.
6b. ~~**Programs page as a list.**~~ Gone: each program's permissions
   are on its own page in Software (2026-10-04).
7. **AOS's own apps in the sandbox**, once the file dialog exists.
8. **dm-verity on the root slots.** The release becomes an image, not a
   tarball: release.sh, aos-update and aos-install change. Testable in
   QEMU.
9. **LUKS-encrypted home**, unlocked at login. QEMU first, then the
   stick, which needs its data partition recreated.

The stick round ([TEST.md](TEST.md)) stays as written for whenever the
laptop is free; sound and Bluetooth wait for the target hardware.

## Postponed: needs hardware

- A second test machine (Intel or AMD laptop): boot, graphics, Wi-Fi,
  sound, suspend, touchpad.
- The ISO written with dd to a stick, and whether the firmware boots it.
- The graphical installer end to end on a disk that can be erased.

## After stable, decided

- Secure Boot (unsupported; turn it off). See
  [br2ext/docs/policies.md](br2ext/docs/policies.md).
- Drag and drop between programs; glass showing other windows.
- btrfs and snapshots for `aos-data`.

## Done (for the record)

- Releases: pinned sources, signed SHA256SUMS, a public download page
  with the CVE report; release.sh refuses a dirty build, a build that is
  not its tag, and an image with an SSH key or with sshd enabled.
- Updates: A/B root slots with confirm and rollback; one update at a
  time; a log in `/var/log/aos-update.log`; safe to interrupt at any
  point (`update-abort-test.py`).
- Security: the model and values in
  [br2ext/docs/security-model.md](br2ext/docs/security-model.md); a
  closed firewall; sshd off unless switched on, with a red bar mark;
  kernel and sysctl hardening; signed package indexes; the app sandbox
  with private homes, declarations shown in the store and changeable in
  Settings → Programs; Firefox without telemetry.
- The desktop: installer, Settings, app store, crash-safe session,
  screenshots, per-display scale, glass.
