# Stick test round

On the G14, booted from the stick. Each step says what to do and what
you should see. Write anything that differs into `~/issues.md`, one line
per item, with its number. Everything from the round of 0.2.7 that you
marked as working is done and not repeated here.

## 0. Reinstall the stick (0.2.8)

Your stick's passwd carries the live `admin` account beside yours (the
0.2.7 updater put it back after the upgrade, see TODO.md), and the
0.2.7 updater would do it once more. So this once:
```
./usb.sh --no-build --release /dev/sdX
```
From 0.2.8 on, Software → Update → Upgrade system keeps the accounts
right; the next round upgrades.
1. Boot: the login screen lists your account only. `grep -c '^admin:'
   /etc/passwd` says 0.
2. `grep VERSION_ID /etc/os-release` says 0.2.8.

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
9. Not fixed in 0.2.8: Files' F2 then Ctrl+C still leaves the
   clipboard empty (reproduced in QEMU; Files needs moving onto the
   current SDK widgets, see TODO.md). No need to test it.

## When done

1. Settings → About → **Save Report**. It lands in your home folder.
2. Plug the stick into the Fedora laptop and tell me; I read the
   report, `~/issues.md` and `~/lock.txt` from there.
