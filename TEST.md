# Stick test round

On the G14, booted from the stick. Each step says what to do and what
you should see. Write anything that differs into `~/issues.md`, one line
per item, with its number.

## 0. A new disk layout: reinstall the stick (0.2.0)

0.2.0 changes what a disk holds (docs/layout.md): the two root slots are
now immutable cores checked block by block (dm-verity), the data
partition is called `aos` and shows in Files as "AOS" with `aos/`,
`apm/` and `users/`, and a small initramfs assembles the system before
systemd. The updater of 0.1.x knows nothing of this, so the stick is
rewritten once:
```
./usb.sh --release
```
(or `./usb.sh --oobe` for a stick that asks for its owner at the first
boot.) Your files on the old stick are gone with it; copy out what you
want to keep first.
1. Boot the stick. Expect the desktop as before. Then:
   ```
   grep VERSION_ID /etc/os-release; cat /proc/cmdline
   findmnt / /aos /home /opt/apm /var /etc /boot/efi
   journalctl -b -t aos-init --no-pager
   ```
   Expect `VERSION_ID=0.2.7`.
   `/` is `/dev/mapper/core`, squashfs, read-only; `/aos` is the fifth
   partition, ext4; `/home` and `/opt/apm` come from it; the command
   line carries `aos.core=PARTUUID=... aos.hash=...`.
2. Files: the sidebar says **AOS** (no "Root"); inside it `aos`,
   `apm`, `users`, and your home is `users/<you>`. Nothing else of the
   Unix tree is shown there.
3. `touch /usr/x` as root fails ("Read-only file system"). The core
   cannot be written, by anyone.
4. Software → Update → **Upgrade system** when a newer release is out:
   each line as before, the AOS line downloads the core (about 700 MB),
   writes it, verifies it, and says "boots at the next restart". Restart: the new version; `aos-update --rollback` and a
   restart: the old one again. GRUB's "AOS (previous version)" does
   the same from the menu.
5. The kernel is part of the core now: Software's AOS page no longer
   lists a kernel package, and `uname -r` matches the release notes.

## 0a. The login screen (0.2.3)

A stick installed with an owner (`./usb.sh --release`, or the live
installer with an account) boots to a login screen now instead of
straight into the desktop: the clock, "Who is this?", the account,
a password field. A wrong password says "Wrong password" and stays;
the right one brings the desktop as before, as that account. The lock
screen (Super+L) is unchanged. Suspend and resume return to the lock
screen, not to the login screen. `./usb.sh --oobe` sticks: the first
boot runs the setup as before and then shows the login screen with the
new owner listed.

## 0b. An encrypted install (optional, needs a second stick or a machine to erase)

In the graphical installer (the live ISO's Install AOS), the install
page has **Encrypt the disk**. With it on, the aos partition is LUKS2
and your account's password is its passphrase. The machine then asks
for it at every start, in text, before the desktop: a wrong one is
asked again (five tries); the right one brings the desktop as usual.
`findmnt /aos` says `/dev/mapper/aos`. `./usb.sh` does not do this
yet; the installer does.

## 1. Sleep

Round 15 came back from sleep with the keyboard and touchpad dead;
0.1.22 resumes the input devices with the session.

1. Close the lid, wait 30 s, open it. Expect the lock screen (if you
   removed the live marks in step 0.5), then the desktop, with the
   keyboard and touchpad working and the windows as they were.
2. If anything is off:
   ```
   journalctl -b -u ade --no-pager | grep -i -E "session|input|resume" | tail -10 > ~/sleep.txt
   ```

## 2. The installer sees the NVMe

```
lsblk -d -o NAME,SIZE,MODEL,TRAN
```
Expect the KIOXIA NVMe beside the stick; **Install AOS** from the
launcher must offer it. Do not install.

## 3. Windows: minimize, the dock, the question

1. Open Notepad, type something, press its close dot (the red one).
   Expect the question in the window: Save, Don't Save, Cancel. Cancel
   keeps it open; the close dot again and Don't Save closes it.
2. Open Notepad and Terminal. Press Notepad's minimize dot (the
   leftmost): it leaves the screen. Super: the dock at the bottom shows
   an icon per running program, the name when the pointer rests on one,
   a count when one has several windows. Click Notepad's icon: it is
   back where it was.
3. Super, right-click Terminal's icon: its windows listed with a close
   mark each and "Close all" beneath. The mark closes the window; on a
   program that ignores the request the mark reads "kill" and a second
   press ends it.
4. Open the File menu in Notepad, type, click back into the text, then
   close with the dot: it must close (or ask, with unsaved text).

## 4. Appearance

The theme's default is now glass on the chrome only. In 0.1.25 the
bar stayed solid (it painted its own colour); in 0.1.26 the bar and
the panels took a theme change only at the next login (your issue 3).
1. After the restart into 0.1.27: windows are solid; the bar, the
   quick panel (top right) and the launcher (Super) are translucent
   over the blurred desktop.
2. Settings → Display → Appearance → **Light**: within a few seconds
   the bar is opaque and the desktop unblurred, no restart. **Glass on
   the bar and panels** back: the bar is glass again within seconds.
3. **Glass everywhere**: a Notepad started afterwards is translucent;
   one already open stays solid (a window keeps what it started with,
   as the page says). **Glass on the bar and panels** back: a new
   Notepad is solid.

## 4b. Two displays (the USB-C monitor, which goes through the Intel GPU)

1. Plug it in. Settings → Display lists both, each with an **On**
   switch, and the second with **Right of eDP-1** / **Left of eDP-1**.
2. Left of: the pointer crosses to the monitor at the laptop's left
   edge within seconds. Right of: at the right edge.
3. Switch the monitor **On** off: it goes dark, its windows come back
   to the laptop. On again: it lights up.
4. Mirror still works as before.

## 4c. Boot

The GRUB menu waits 2 seconds now instead of 5; "AOS (previous
version)" is still there if you press a key in time.

## 4d. Wi-Fi after the firmware trim

The image lost 170 MB of Intel Wi-Fi firmware revisions the driver
never loads; the one it loads stayed. After the restart into 0.1.26:
```
journalctl -k --no-pager | grep -i "iwlwifi.*loaded firmware"
```
Expect a "loaded firmware version ... sc-a0-wh-b0-c106.ucode" line and
Wi-Fi connected as before. If Wi-Fi is gone, that line (or its absence)
is what I need.

## 4e. Steam in its declared sandbox

Software → Third-party → Steam: its page shows "Sees: everything in
your home" from the index, and once installed (or upgraded to release
7) a Permissions section. Start Steam: it must come up as before.
Software → Third-party → Discord → Permissions: a **Camera** switch;
leave it off unless you want to try a video call.

## 4f. The morning list (0.1.28)

1. **Fonts after sleep.** Open Notepad and Settings, suspend (lid or
   the quick panel), wake. Every label must still read; the journal
   says what ran:
   ```
   journalctl -b -u nvidia-suspend -u nvidia-resume --no-pager | tail -4
   ```
   Expect both units "Finished". AOS programs now run on the Intel GPU
   (check: `cat /proc/driver/nvidia/gpus/*/information` is untouched by
   opening Notepad; `nvidia-smi` lists no aos process). If text still
   breaks, say which program and whether it was open across the sleep.
2. **Quick panel** (click the bar's right end): glass like the bar,
   its buttons translucent, nothing solid in it.
3. **Snap ghost.** Drag a window by its header toward the left edge
   and hold: a pale wash over the left half shows where it will land;
   release: it snaps there. The same at the right edge and the top
   (the whole zone).
4. **Minimize animation.** Minimize a window from its decoration: it
   shrinks and fades toward the bottom centre in a fifth of a second;
   bring it back from the dock: it grows back. Settings → Display →
   Appearance → **Animations** off: the window just disappears.
5. **Screenshot toast.** Print: the toast; click it within a minute:
   Images opens on the screenshot. Shift+Print the same.
6. **Images Ctrl+C.** In Images, Ctrl+C, then paste into Firefox (a
   chat or an image upload field) or into another program: the picture
   arrives as a PNG. Rotate first: the pasted picture is rotated.
7. **Notepad undo.** Type a few words, Ctrl+Z: the last run of typing
   goes; Ctrl+Shift+Z (or Ctrl+Y): it is back. Paste, Ctrl+Z: the
   paste alone goes. Edit menu: Undo, Redo.

## 4g. The microphone permission (0.1.29)

Third-party programs get the microphone only when their package asks
for it or you switch it on; sound still plays without it. Firefox,
Discord and Steam ask for it (their new releases), VS Code does not.
1. Software → Third-party → Firefox → Update (release 6), then its
   page: "Sees: ... the microphone", and Permissions has a
   **Microphone** switch, on. Open a mic test page (e.g. a search for
   "mic test"): the browser asks, allow, the meter moves.
2. Switch Microphone off, restart Firefox, the same page: the site gets
   no sound (Firefox may say the device cannot be opened). Sound from
   a video still plays. Back on, restart: it works again.
3. `journalctl --no-pager _COMM=wireplumber | grep "microphone is off"`
   lists the refused streams from step 2.
4. A terminal outside any sandbox: `pw-loopback` keeps working
   (Ctrl+C to stop): the desktop itself is untouched.

## 4h. Boot time (0.1.30)

After the restart into 0.1.30:
```
systemd-analyze; systemd-analyze blame | head -8; swapon --show
```
Expect: no systemd-journal-flush.service in the top of blame (it was
4.5 s on your report of 2026-10-05), zram-setup.service not in the top
either, /dev/zram0 in swapon with priority 100, and userspace a few
seconds shorter than the 6.1 s of that report. Then
Settings → About → Save Report once more: the memory list tells me what
Notepad and Settings cost on the Intel GPU now.

## 5. Bluetooth

Settings → Bluetooth → Scan lists named devices only, plus anything
paired. Pair your headphones: "Paired and connected", and they appear
in Settings → Sound.

## 6. A stick for someone else (optional, needs a second stick)

```
./usb.sh --oobe /dev/sdX
```
Boot it: no account on it; the desktop comes up as a locked setup user
with "Welcome to AOS" (keyboard, time zone, account, Finish). Finish
makes the account, restarts the desktop as it, and sudo asks its
password from then on. `id setup` afterwards must say no such user.

## When done

1. Settings → About → **Save Report**. It lands in your home folder.
2. Plug the stick into the Fedora laptop, open the `aos-data` partition
   in Files, and tell me. I read the report, `~/issues.md` and
   `~/sleep.txt` from there.
