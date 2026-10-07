# Stick test round

On the G14, booted from the stick. Each step says what to do and what
you should see. Write anything that differs into `~/issues.md`, one line
per item, with its number. Everything from the round of 0.2.7 that you
marked as working is done and not repeated here.

## 0. Reinstall the stick (0.3.0)

0.3.0 changes what a disk holds (every account a systemd-homed one,
made at the first boot), and your stick's passwd still carries the
live `admin` account beside yours (the 0.2.7 updater put it back after
the upgrade, see TODO.md). So this once, reinstall:
```
./usb.sh --no-build --release /dev/sdX     # no account on it: the first boot asks
```
Section 5 is that first boot. Everything else below is 0.2.8's round
plus section 4 (0.2.9).
1. After section 5's first boot: the login screen lists your account
   only. `grep -c '^admin:' /etc/passwd` says 0.
2. `grep VERSION_ID /etc/os-release` says 0.3.0.

## 1. The lock screen and the brightness (the softlock)

1. Super+L. Press the brightness-down key once (the OSD shows at the
   bottom), wait three seconds, type your password, Enter. Expect the
   desktop. Again with the volume key. Again with a toast: start
   `notify-send hi` in a terminal, Super+L at once, wait for the toast
   to go, type the password.
2. Quick panel → Screen slider all the way left: it stops at 5% and
   the screen stays readable. The brightness-down key held: the same.
3. The round that locked you out: brightness-down held to the floor,
   close the lid, wait, open it, press brightness-up, type the
   password. Expect the desktop with the windows as they were.
4. If the lock screen ever stops taking input again: Ctrl+Alt+F2,
   log in, `journalctl -b _COMM=ade-comp --no-pager | tail -30 >
   ~/lock.txt`, `pgrep -a ade-lock >> ~/lock.txt`, and tell me.

## 2. Two displays (USB-C monitor)

QEMU cannot show this one (its virtual GPU blanks a re-plugged head
regardless), so the G14 is the only check.
1. Plug it in: bar and wallpaper on it within seconds. Unplug it: the
   windows come back to the laptop. Plug it in again: bar and
   wallpaper again, not a black screen.
2. Settings → Display → Mirror: the monitor shows the laptop's picture.
3. If it is still black after the replug: `journalctl -b _COMM=ade-comp
   _COMM=ade-shell --no-pager | tail -30 > ~/display.txt`.

## 3. Small things

1. Files' sidebar says **AOS** (not Root), with aos, apm, users.
2. Super: no "Install AOS" in the launcher on the installed stick.
   (On the live ISO it is still there.)
3. Settings → Display → Appearance: the opaque option is called
   **Lightweight**.
4. Click the bar's right end: the quick panel opens; click it again:
   it closes.
5. Super, type a few letters, Ctrl+A, Backspace: the search is empty.
   Type again, Ctrl+A, type a letter: only that letter.
6. Print: the toast goes by itself after about 6 s; a click within
   that time still opens Images.
7. Images, Ctrl+C: the status line says "Picture copied".
8. Software: install something big (Steam), open another program's
   page while it runs: no steps of Steam's install under its rows;
   Steam's own page shows them.
9. Files' F2 then Ctrl+C: in QEMU it works (clip-test.py: the name
   pastes into Notepad), so where it failed for you matters. Files,
   a row, F2, Ctrl+C, Escape; then Ctrl+V in Notepad, in the
   terminal, and in Firefox's address bar. Say which of the three got
   the name, and whether Files was started from the launcher or from
   a terminal.

## 4. The session is in the journal, the lock survives a crash (0.2.9)

Your stick's session printed its lines on a hidden console until now,
which is why the morning's lockup left nothing to read. From 0.2.9 an
owned machine's session is logged like the demo's was.
1. After a login: `journalctl -b -t ade-session | tail` shows the
   compositor's lines (layers mapped, the shell started); `journalctl
   -b -t ade-greeter | tail` the login screen's.
2. Super+L, then from a tty (Ctrl+Alt+F2, log in): `pkill -KILL -x
   ade-comp`; back on Ctrl+Alt+F1 within seconds the desktop is back
   **locked**, the password unlocks it, and a toast says the desktop
   restarted after a crash. (Before 0.2.9 it came back unlocked.)
3. Settings → About → Save Report: the archive has `session-journal`,
   `greetd`, `session-left` and `tty1`.
4. issues.md 3.4 said "I opened notepad, wrote some, clicked File and
   then back on text. The File menu closed and then the red button."
   What did you expect, and what happened after the red button? One
   line, so it can be fixed.

## 5. Encrypted homes (0.3.0): the first boot

Every account is a systemd-homed account with a LUKS2 home of its own,
made at the first boot. The reinstall of section 0 left no account on
the stick; this is what happens next.
1. First boot: the welcome asks keyboard, time zone, then your name and
   password; Finish; a page shows a **recovery key** (eight groups of
   eight letters). Write it down. Continue: the login screen lists you.
2. Log in. `ls /home` shows `jax.home` (the LUKS image) and `jax`;
   `findmnt /home/jax` says ext4 on a dm device; `homectl inspect jax`
   says Storage luks, State active. `cryptsetup isLuks /home/jax.home
   && echo yes`.
3. `sudo true` asks your password and takes it. Super+L and the
   password unlock. Ctrl+Alt+F2: log in as jax with the password (the
   console reaches homed too), then `sudo true` at once: it should take
   the password; if it says "Too many unsuccessful login attempts"
   first, note it (QEMU shows that line when sudo follows the login
   within a second; it still succeeds).
4. Log out (Ctrl+Alt+F2 and `loginctl terminate-user jax` from a root
   shell is the hard way; the quick panel's Log out if it has one):
   `homectl inspect jax` on a tty says State inactive: the home is
   locked while you are out.
5. Reboot, and at the login screen type the **recovery key** where the
   password goes: your desktop, your files.
6. Settings → Accounts: your account is listed. Set the password: it
   asks the current one (wrong → refused; right → works, and the next
   login takes the new one). Add an account (standard): it appears in
   the login screen, logs in, has its own `/home/<name>.home`. Remove it.
7. Suspend and resume, then a program that writes to your home (Notepad
   save): fine.
8. `swapon --show`: zram only (no swap file on an unencrypted partition).
9. Software → Update → Upgrade system to the next release, restart: you
   log in as before; the home is still encrypted (step 2).
10. If the first boot ever fails: Ctrl+Alt+F2, log in as root (no
    password until the owner exists), `journalctl -b -t ade-session
    --no-pager | tail -40 > /root/firstboot.txt`, and tell me.

## When done

1. Settings → About → **Save Report**. It lands in your home folder.
2. Plug the stick into the Fedora laptop and tell me; I read the
   report, `~/issues.md` and `~/lock.txt` from there.
