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
   Expect `0.1.23`.
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

## 4. Bluetooth

Settings → Bluetooth → Scan lists named devices only, plus anything
paired. Pair your headphones: "Paired and connected", and they appear
in Settings → Sound.

## When done

1. Settings → About → **Save Report**. It lands in your home folder.
2. Plug the stick into the Fedora laptop, open the `aos-data` partition
   in Files, and tell me. I read the report, `~/issues.md` and
   `~/sleep.txt` from there.
