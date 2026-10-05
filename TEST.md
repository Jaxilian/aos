# Stick test round

On the G14, booted from the stick. Each step says what to do and what
you should see. Write anything that differs into `~/issues.md`, one line
per item, with its number.

## 0. Get onto the newest release

1. Boot the stick. If it does not reach the desktop, hold the power
   button, start it again: it falls back to the old version by itself.
2. Software → Update → **Upgrade system**. Press it **once**: every
   line says what its package is doing (downloading with a percentage,
   installing, done or failed with the reason), the AOS line last. Wait
   for "done; boots at the next restart" and press **Restart** there.
3. Restart. About 20 seconds after the desktop appears, check:
   ```
   grep VERSION_ID /etc/os-release
   ```
   Expect `0.1.21`.
4. Software → Update → **Upgrade system** once more, if lines are
   left: runtime/gtk3 release 7 (libpulse) is one. Each line ends in
   done or failed; note any failed one with its reason.
4b. About two minutes after a boot a toast says what updates wait (if
   any). Click it: Software must open on its Update page.
5. The stick was installed with the demo account, which keeps the live
   system's marks: no lock screen ever, sudo without a password. You
   set a password since, so take them away once (an update does not
   bring them back from 0.1.21 on):
   ```
   sudo rm -f /etc/aos/live /etc/sudoers.d/20-aos-live
   ```
   From then on sudo asks your password, and the lock screen is real.
6. XWayland lost its libraries to the runtime upgrade of the last
   round (an apm bug, fixed in 0.1.21, but the links are gone on this
   stick): Software → AOS → Compatibility → **XWayland** off, then on
   again. After a few seconds `pgrep -a Xwayland` must show it.

## 1. Sound

libpulse was on the stick at the end of the last round (runtime/gtk3
release 7 installed at 08:36); a Firefox started before that could not
have it. So: close every Firefox window, start it again, play a video.
```
wpctl status | sed -n '/Streams/,$p'
grep -c libpulse /proc/$(pgrep -f -o firefox/firefox)/maps
```
Expect a Firefox line under Streams and a count above 0. If the count
is 0, Firefox is not loading the library; if it is above 0 and there is
still no stream, put the last lines of this in `~/issues.md`:
```
journalctl --user -b --no-pager | grep -i -E "pulse|pipewire" | tail -5
```

## 2. Bluetooth

Settings → Bluetooth talks to BlueZ directly now (no bluetoothctl).
1. The page must show the adapter on. Switch it off and on.
2. **Scan** with a device in pairing mode; it appears in the list.
3. Pick it, **Pair**: expect "Paired and connected". Headphones should
   then show up in Settings → Sound. If anything fails, the page's
   message at the bottom is what I need, word for word.

## 3. Suspend and lid

The windows go blank after a resume while Firefox stays fine, and no
error reaches the journal. This narrows it:

1. Open Notepad with some text. Open a terminal and in it:
   ```
   settings 2>&1 | tee ~/settings-after-sleep.txt
   ```
   (the Settings window opens from the terminal; leave both open).
2. Close the lid, wait 30 s, open it. Expect the lock screen (after
   step 0.5), then the desktop.
3. Click into Notepad and into the Settings window; use them. Note what
   each shows. Press **Print** for a screenshot (it lands in
   Pictures/Screenshots).
4. Then:
   ```
   journalctl -b -u ade --no-pager | tail -40 > ~/suspend.txt
   ```
   and close the Settings window, so `~/settings-after-sleep.txt` holds
   whatever it printed.

## 3b. Brightness

The slider writes `/sys/class/backlight/intel_backlight/brightness`,
range 0 to 38400, and 0 went black, so the writes arrive. Whether the
panel follows other values is a kernel question; this answers it:
```
echo 19200 | sudo tee /sys/class/backlight/intel_backlight/brightness
echo 38400 | sudo tee /sys/class/backlight/intel_backlight/brightness
echo 50 | sudo tee /sys/class/backlight/nvidia_0/brightness
```
Say for each line whether the panel changed.

## 4. Software

1. Software → Third-party → Firefox: **Back** is the first row, above
   the title.
2. Software → Update after an upgrade: no "apm said" section; the
   steps' own lines only.
3. The updates toast says what waits, without "Click to open", and
   comes once per session.

## When done

1. Settings → About → **Save Report**. It lands in your home folder.
2. Plug the stick into the Fedora laptop, open the `aos-data` partition
   in Files, and tell me. I read the report, `~/issues.md`,
   `~/suspend.txt`, `~/settings-after-sleep.txt` and the screenshot
   from there.
