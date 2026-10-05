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
   Expect `0.1.22`.
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

The keyboard and touchpad died after a resume because the compositor
never re-opened the input devices logind had revoked; 0.1.22 does.

1. Close the lid, wait 30 s, open it. Expect the lock screen (if you
   removed the live marks in step 0.5), then the desktop, with the
   keyboard and touchpad working and the windows as they were.
2. Then `systemctl suspend` from a terminal, power button to wake.
   Same expectations.
3. If anything is off:
   ```
   journalctl -b -u ade --no-pager | grep -i -E "session|input|resume" | tail -10 > ~/sleep.txt
   ```

## 2. The installer sees the NVMe

The G14's drive sits behind Intel VMD; the kernel has the driver now.
```
lsblk -d -o NAME,SIZE,MODEL,TRAN
```
Expect the KIOXIA NVMe beside the stick. Then open **Install AOS**
from the launcher: the drive must be offered. Do not install.

## 3. Bluetooth

1. Settings → Bluetooth → Scan: only devices with a name are listed
   now (the nameless addresses were noise), plus anything paired.
2. Pair your headphones; expect "Paired and connected" and the
   headphones in Settings → Sound.

## 4. Software

After step 0's restart, Software → AOS and → Update must not say
"installed and boots at the next restart" for the running release.

## When done

1. Settings → About → **Save Report**. It lands in your home folder.
2. Plug the stick into the Fedora laptop, open the `aos-data` partition
   in Files, and tell me. I read the report, `~/issues.md` and
   `~/sleep.txt` from there.
