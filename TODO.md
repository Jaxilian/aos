# TODO

Updated 2026-10-07 evening. The newest release is 0.2.9 (the session
in the journal, the lock across a crash; the alpha plan below),
published, untested on the stick: [TEST.md](TEST.md). 0.2.8 was never
on the stick either; its round is in TEST.md too.
0.2.0-0.2.7 brought the verity cores, the aos partition, LUKS and the
login screen; a machine on 0.1.x reinstalls once.

## The stable alpha (decided 2026-10-07 afternoon; 0.3.0)

Robustness and security first, no new features. The plan, in order:

1. ~~**Housekeeping**~~: local.mk gone, the docs on 0.2.8 committed.
2. ~~**Diagnosability**~~ (0.2.9, done): an owned machine's session logs nothing
   -- greetd hands it the VT, so every line of the compositor, the
   shell and the apps was drawn on a hidden console; the lockup of the
   morning left an empty journal. The session script now runs under
   `systemd-cat -t ade-session` (`-t ade-greeter` for the greeter), its
   crash lines go to the account's runtime directory and the compositor
   reads them there (ADE_RUNTIME_DIR, ade v0.1.49). Found on the way:
   /run/ade existed only as ade.service's RuntimeDirectory, so on an
   owned machine the lock mark was never written and a compositor that
   crashed while locked came back **unlocked**; fixed by the same
   change. The session's crash window counts from the first crash (it
   counted from the login, and a window ending mid-series restarted the
   count). greetd failing five times gets the tty1 explanation
   (OnFailure=ade-failed.service); Save Report carries the session
   journal, greetd's, the left-over crash lines and tty1's last screen.
   greeter-test.py steps 4-6 cover it; aos-update-confirm also refuses
   a slot where logind, D-Bus or homed failed.
3. **The open bugs**: Files' rename Ctrl+C is on tgn's field widget
   already and works in QEMU (clip-test.py passes with a real paste;
   the morning's "reproduction" was wl-paste, which races without a
   data-control protocol). A WAYLAND_DEBUG trace shows the data source
   made and the compositor's selection event back. TEST.md 3.9 asks
   where it failed on the G14 (Notepad, terminal, Firefox; launcher or
   terminal). issues.md 3.4 is unclear: asked in TEST.md 4.4.
4. ~~**The gate**~~ (`board/aos/gate.sh`, written, not yet run whole):
   every driver in one run, one verdict each; 0.3.0 is tagged only
   after it is green. kernel-test.py is gone (0.1.x only).
5. **systemd-homed**: a LUKS home per account, unlocked by the password
   at login, a recovery key shown once; **every install's owner is
   made at the first boot** (homectl needs a running homed, so the
   installer's account page goes and `--oobe` is what an owned install
   is; `--demo` keeps the classic account for the drivers). The
   swapfile only on a LUKS aos partition. The half-done PAM/preset/
   defconfig lines are parked in ~/Projects/OS/chains/homed-wip.patch
   (shipped by mistake in a dev build, they are a "faulty module" in
   every PAM stack without homed). About a week.
6. **0.3.0**: TODO/TEST/docs, the gate, the stick round. Another
   session asked (2026-10-07 afternoon) to repin apm to v0.1.13
   (b41da28: .deb and AppImage sources, for the Chrome/Spotify/Krita/
   Inkscape recipes) as part of it; the repin was not done here -- it
   is a commit from outside this session, so it is yours to confirm:
   WORKFLOW.md section 5.3.

Decided out for the alpha: transitions, Notepad Ctrl+F and the last
document, the refresh rate, a glassier panel, HDMI multi-GPU, the file
dialog and own apps in the sandbox, Secure Boot, CI, an update channel
(edge/stable: later), committing CLAUDE.md/WORKFLOW.md/alpha-roadmap.md.

## Open now, in priority order

1. **The stick round on 0.2.8** (TEST.md): reinstall, the lock screen
   with the OSD, two displays, the small things.
2. **Encrypted homes (systemd-homed)**: waits for your yes (0.2.8
   section below); changes what a disk holds; about a week.
3. **Files' rename prompt onto the current tgn widgets** (F2 then
   Ctrl+C copies nothing).
4. **The file dialog by fd passing**, then AOS's own apps in the
   sandbox (settled in WORKFLOW.md section 9).
5. **HDMI on the G14** is the NVIDIA GPU's port: multi-GPU output in
   the compositor (smithay's GpuManager). Big.
6. **A second test machine** (any Intel or AMD laptop): nothing but the
   G14 has run AOS.
7. **CI's first real run**: paused since 2026-10-07; only on your word.
8. Wishes: snap and open/close transitions, Notepad Ctrl+F and the
   last document, refresh rate in Settings, a glassier quick panel
   (say the alpha).

Anything that needs a second machine, a second stick or a permanent
installation is postponed (see the end).

## 0.2.8: the stick round on 0.2.7 (2026-10-07)

Your report of 10:08, issues.md and the journal of the morning's boot.

**The softlock.** The journal (boot 0, 10:14): lid closed, s2idle,
lid opened nine seconds later with a short power-key press (logind
ignored it: the suspend was still finishing), then nothing from the
session until your tty login at 10:15:07. Two faults:
1. The screen can be turned to 0% -- the quick panel's slider and the
   keys went to 0 -- which is a black screen on a machine that is
   fine. Both stop at 5% now (shell osd.rs BRIGHT_MIN).
2. The lock screen took one character and then nothing. Every layer
   surface that unmaps makes the compositor refocus the top window
   (hnd.rs, for popups and panels), and that included the brightness
   OSD you pressed to see the screen again: 1.5 s after it showed, the
   keyboard left the locker for whatever window was under it. The
   earlier lock tests never had an OSD up. win::focus now gives the
   keyboard to the lock surface whatever asked while the session is
   locked (a toast arriving during the lock had the same hole).
   greeter-test.py step 3 does Super+L, a volume key, the password.
Not changed: Ctrl+Alt+F2 and the tty login worked as the way out, as
they should.

**The admin account after an upgrade** (0a): aos-update appends to
the machine's passwd every name the new core's passwd has that the
machine's lacks, so new system users arrive -- and so did the live
medium's `admin`, which aos-install had deleted, with uid 1000 beside
yours; the greeter lists uid 1000 and up. The merge skips admin on an
owned machine and removes a line an earlier update left. Your stick
has that line now: TEST.md says to reinstall, since the 0.2.7 updater
would put it back once more.

**Files says Root** (0.2): the commit that adds the AOS place
(files 0d1178c) was never pinned here; 0.2.8 pins it.

**Two displays** (4b.3, 4b.4): awin bound the wl_outputs once, at
connect; a monitor plugged back in is a new global with the old name,
so the shell's bar and wallpaper for it were made on the stale proxy
and never showed -- black, no panel. aos-sdk v0.4.16 follows outputs
after the connect; the shell drops a gone display's pair and makes a
fresh one (ade v0.1.47). The compositor's journal confirms the fresh
bar and wallpaper map on the returning head. QEMU cannot show the
result: on virtio-gpu a re-plugged head stays blank whatever is drawn
(its scanout after a hotplug), so ade-test.py step 4b and replug-test.py
only report it. A flip watchdog tried for this never fired and was
reverted. Mirror went black for the same reason; both need the G14.

**Also in 0.2.8**: the quick panel closes on a second click of the
status area (it hid on losing the keyboard and the click reopened
it); Ctrl+A in the launcher's search; the screenshot toast stays 6 s;
Images says "Picture copied"; Software lists a run's steps only on
the page of the program being installed (store v0.2.7); "Light" is
"Lightweight" (settings v0.1.26); "Install AOS" is listed on the live
medium and before the first owner only (X-AOS-Live=true in its desktop
entry; the shell reads it).

**Not a bug: "Inbound SSH" open** (own 5). That stick is a build of
yours: make-usb.sh refuses to write a stick without your SSH key, so
every stick from this tree has sshd on and the red bar says so. The
published ISO is built without keys and ships sshd disabled
(release.sh refuses otherwise); an install from it has no SSH.

**Still open from the report**:
- Files: F2 then Ctrl+C does not put the name on the clipboard (own
  1). Reproduced in QEMU (clip-test.py fails). A Wayland trace shows
  Files receives Ctrl and C but never creates a data source or sets a
  selection, so it is in Files, not the compositor. The SDK's field
  copy is present and unchanged since v0.4.15, and Images' copy works;
  Files' key and modal code was last written for aos-sdk v0.4.1
  (files 113124a) and predates the current tgn widgets. Fix: move
  Files' rename prompt onto the current tgn field/prompt widgets
  rather than patch the old path. Not in 0.2.8.
- Quick panel glass (4.1, 4f.2): in QEMU and on your screenshot the
  panel sits over a dark wallpaper and a dark window, and 62% dark
  grey over blurred dark green reads as solid. The blur is drawn under
  it (the same code as the bar). If you want it visibly glassy, the
  panel's alpha goes down; say so.
- Wishes: transitions on the snap ghost, window open/close (4f.3,
  4f.4); Notepad Ctrl+F and reopening the last document (own 4, 9);
  the display's refresh rate in Settings (own 8).
- **Encrypted homes by default** (0b). What you describe is
  systemd-homed: each account a LUKS volume under users/, unlocked by
  the account's password at login (pam_systemd_home in greetd's PAM),
  made by the first-boot setup and the installer, no passphrase before
  the desktop. The risk you name is real: a forgotten password is the
  data gone. homed has a recovery key (a long phrase shown once at
  setup, to be written down); that is the usual answer. This is the
  next big item and changes what a disk holds, so it waits for your
  yes; a week of work.

## 0.2.7: installing from an installed stick onto a second one

Four faults, each only visible with two AOS disks attached. The
installer only knew the live ISO's core; it now copies the running
slot's when there is no live medium. Its release step unmounted
anything from /dev/mapper, the running root included; it now unmounts
the target's own devices, by device, until none is left. The media rule
mounted the running stick's own partitions under /run/media, its
root-disk check predating the verity root; it follows slaves/ now. And
the initramfs mounted /boot/efi by LABEL=AOS_ESP, which with two AOS
disks was the other one's -- the "wipefs: Device or resource busy" on
the G14, and where an update would have written its kernel; it is
partition 2 of the core's disk now. Old partitions' signatures are
wiped before the disk's, and the disk wipe retries, then prints the
mounts and holders. Reproduced and verified with the real sticks in
QEMU, then on the G14.

## 0.2.6: the installer hides the disk it runs from

The root is a device-mapper device now, so the installer app's walk
from "/" to a disk found nothing and the live stick was offered as a
target. It now excludes the disks under /run/aos/live and the slot and
aos partitions the command line names (setup 88e7a54); aos-install
refuses them too.

## 0.2.5: the installer releases the target disk first

A stick with an earlier AOS on it is mounted by the live system's
removable-media rule the moment it is plugged in, and mkfs refused
"/dev/sdb5 is apparently in use" (the G14, 2026-10-06). aos-install
now unmounts, swapoffs and closes whatever is held on the disk before
wiping it.

## 0.2.4: the stick's first boot of 0.2.3 hit a crash guard

aos-update-confirm.service had Requires=ade.service, which pulled the
disabled autologin service in beside greetd; the two conflict, the
autologin won on the G14 and died four times without its account.
The unit now follows whichever desktop service is up; the installer
writes greetd's links itself instead of running systemctl in the
chroot; greeter-test.py fails when ade.service ran.

## The cores and the aos partition (2026-10-06 afternoon, agreed; 0.2.0)

Done in QEMU: squashfs cores with a dm-verity hash tree in the slots,
opened by a 13 MB initramfs of the target's own binaries; the `aos`
partition at /aos with aos/ (etc overlay, var, the swap file), apm/,
users/; the ISO is /boot plus the core (zstd-19, 1 MiB blocks: core
709 MB, ISO 784 MB; xz would be 667/742 and read back slower); aos-install writes the
core from the live medium and verifies it; aos-update fetches
core.img.xz + core.verity, writes, verifies, stages the ESP, sets
next; release.sh ships those; Files shows "AOS"; the setup app knows
the live medium by its core. The live home is writable now (a tmpfs
aos partition). The kernel is no longer an apm package. docs/layout.md.
Open: the kernel packages still in the apm index (remove at release);
docs/upgrading, publishing, usb, security-model to rewrite; the G14
round (TEST.md 0: a reinstall).
Done in 0.2.2: LUKS2 around the aos partition -- `aos-install
--encrypt FILE`, the graphical installer's "Encrypt the disk" (the
account's password is the passphrase), the initramfs's prompt with
five tries; luks-test.py drives it in QEMU on GRUB's serial entry
(the prompt is on /dev/console, which the normal entries make tty1).
Not yet: `./usb.sh --encrypt`.

Done for 0.2.3 (in QEMU, pending): the login screen. greetd
(br2ext/package/greetd, upstream 0.10.3) runs `/usr/lib/aos/session
--greeter` as the greeter account -- ade-comp with ade-greeter, a tgn
app in its own repo (Jaxilian/greeter) that lists the accounts, takes
a password and asks greetd over its socket to start
`/usr/lib/aos/session` as that account: the compositor and the shell
as today, restarted on a crash up to four times, with the apm
environment. An owned machine (aos-install --user) and an OOBE one get
greetd (the OOBE first boot is greetd's initial session as the setup
account; aos-firstboot drops it and restarts greetd); the live medium
and a demo install keep ade.service's autologin, so every existing
QEMU driver stays as it is. greeter-test.py: INSTALL_MODE=owner, a
wrong password, the right one, the owner's session. Next: systemd-homed
for per-user LUKS homes through pam_systemd_home in /etc/pam.d/greetd.

## Decisions of 2026-10-06, settled

dm-verity cores (done, 0.2.0; the kernel is part of the core, not an
apm package), LUKS on the aos partition from the installer (done,
0.2.2), and the file dialog by fd passing for AOS apps first (open,
item 4 above). The earlier questions are in git history.

## Afternoon (2026-10-06): the performance round, for 0.1.30

Done: the journal persistent from the first line (no 4.5 s flush inside
sysinit on a USB stick) and zram started after the desktop instead of
under swap.target (1.3 to 1.7 s off the chain); measured in QEMU before
and after in docs/performance.md, with the G14's own numbers from your
report of 2026-10-05. Left there: resolved's 1.4 s on the live ISO,
nvidia-devices before the desktop on the G14, and tgn programs' memory,
to be read from your next report (TEST.md 4h).

## Afternoon (2026-10-06): the microphone permission, for 0.1.29

Done: a program in the sandbox has no microphone unless its package
declares `microphone = true` ([sandbox], ";mic", --microphone; apm
v0.1.12) or Software's Permissions switch it on (store v0.2.6). How:
PipeWire listens on a second socket, pipewire-0-nomic, and
pipewire-pulse on pulse/native-nomic, whose clients are tagged access
"nomic" (pipewire.conf.d and pipewire-pulse.conf.d); WirePlumber gives
them a sandboxed client's permissions and a linking hook of ours
(scripts/linking/find-nomic-target.lua) refuses every capture stream
with an error to the client and a warning in the journal. aos-sandbox
binds the nomic sockets over the real ones unless --microphone. Sound
plays either way. Firefox r6, Discord r4 and Steam r8 declare it.
mic-test.py drives it in QEMU (pw-loopback refused on the nomic
socket and in the sandbox, linked on the plain one and with the flag).
Not done: a prompt when a program first asks (PipeWire has no portal
here); the switch is the answer. The desktop's own programs are
outside the sandbox and keep the microphone.

## Morning list (2026-10-06, "to keep you at work while I am gone")

Done for 0.1.28:
1. Quick panel glass: it painted Color::Background with opaque
   controls; now the theme's panel, and the SDK's glass palette has
   translucent controls and borders (sdk v0.4.15).
2. Screenshot toast clickable: the compositor sends the path after
   "s1"/"s2", the shell's toast runs `images <path>` on a click.
3. Images Ctrl+C: the picture as shown, rotated, as image/png on the
   clipboard (awin win_clipboard_set_data: one mime with its bytes).
4. Fonts after suspend, two bugs: (a) every AOS program ran on the
   discrete GPU -- awin's VkConf defaulted to Balanced, only the shell
   asked for Low -- now Low (the integrated GPU) by default; (b) the
   NVIDIA driver drops video memory over a sleep unless told to keep it:
   NVreg_PreserveVideoMemoryAllocations=1 + TemporaryFilePath=/var/tmp
   in nvidia.conf, nvidia-suspend/resume/hibernate units (ours, NVIDIA's
   call /usr/bin/logger which the image lacks) and nvidia-sleep.sh. And
   tgn's Gui counts suspends (CLOCK_BOOTTIME against CLOCK_MONOTONIC)
   and re-uploads its atlas, labels and pictures after one, so a
   program on the discrete GPU survives even without the driver's help.
   Hardware only: TEST.md 4f.1.
5. Snap ghost: a pale wash (premultiplied solid element, under the
   windows) over the slot a release would fill, from the move grab.
6. Minimize animation: the window's surface tree rescaled and faded
   toward the bottom centre of its display in 220 ms, and back on a
   restore (comp anim.rs); `animations=off` in the theme file turns it
   off, Settings → Appearance has the switch. No open/close fades.
7. Notepad undo/redo: whole-text snapshots, typing runs coalesced
   within 0.8 s; Ctrl+Z, Ctrl+Shift+Z, Ctrl+Y, the Edit menu.
fx-test.py drives 1, 2, 5 and 6 in QEMU (the ghost's brightness, a
mid-animation frame, the toast click starting Images).

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

## Next, as of 2026-10-03 (superseded by "Open now" at the top)

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
8. ~~**dm-verity on the root slots.**~~ Done in 0.2.0.
9. ~~**LUKS**~~ on the aos partition, done in 0.2.2; per-user homes
   (homed) is item 2 at the top.

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
