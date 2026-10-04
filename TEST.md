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
   Expect `0.1.18`.
4. Software → Update → **Upgrade system** once more, if lines are
   left: this rebuilds Firefox, VS Code and Discord into their sandboxes.
   Each line ends in done or failed; note any failed one with its reason.
4b. About two minutes after a boot a toast says what updates wait (if
   any). Click it: Software must open on its Update page.
5. Once only, for the brightness slider:
   ```
   sudo usermod -aG video admin
   ```
   Then log out and in.

## 1. Sound

The speaker PCM exists on this laptop but no "Speaker" output shows up;
the host Fedora on the same machine has one. These lines say why:

1. ```
   amixer -c 1 info | grep -i components
   alsaucm -c sof-soundwire -i _verb HiFi list _devices
   ```
   Put the output in `~/issues.md`. (The report collects it too now.)
2. Open Firefox and play any YouTube video. If silent, while it plays:
   ```
   wpctl status | sed -n '/Streams/,$p'
   ```
   A Firefox line there means Firefox reaches PipeWire from its sandbox.
3. Settings → Sound: an output that is not plugged in (Headphones, an
   HDMI port with no display) cannot be chosen; that is PipeWire's rule,
   not a bug.

## 2. Bluetooth

1. Settings → Bluetooth: turn it on, scan, pair something (headphones,
   a mouse).
2. Note what the page says at each step. If nothing shows, this trace
   of the client's attempt is what I need (put it in `~/issues.md`):
   ```
   bluetoothctl --timeout 5 show; echo rc=$?
   busctl --no-pager status org.bluez | head -5
   timeout 8 busctl --no-pager monitor org.bluez > /tmp/bt.txt & sleep 1; bluetoothctl --timeout 3 show; sleep 6; head -40 /tmp/bt.txt
   ```

## 3. Suspend and lid

1. Close the lid, wait 30 seconds, open it. Expect the lock screen and
   then your desktop as you left it.
2. Then from a terminal:
   ```
   systemctl suspend
   ```
   Press the power button to wake it.

## 4. XWayland

1. Software → AOS → Compatibility → **XWayland**: switch it on.
2. After a few seconds:
   ```
   pgrep -a Xwayland
   ```
   Expect a line with `Xwayland`.

## 5. Firefox in its sandbox

1. Open Firefox. Expect no "Welcome / Terms of Use" screen, and a fresh
   profile (your old bookmarks stay in `~/.mozilla`; that is expected).
2. Open any website. Text must be letters, not boxes.
3. Download a file. Expect it in `~/Downloads`.
4. In Firefox, File → Open File: the dialog shows Firefox's own home,
   with only `Downloads` from yours. Its files live here:
   ```
   ls ~/.var/app/
   ```
   Expect `mozilla.firefox`.

## 5b. Firefox menus

1. Hamburger menu → **New Window**: a second window must open.
2. Right-click an image → **Save Image As…**: a file dialog must open.

## 6. Settings → Programs

1. Settings → **Programs**. Expect Firefox and Discord as "its own
   files and Downloads", and VS Code as "everything in your home".
2. Give Firefox **Pictures**, restart Firefox, and check that a file
   dialog inside it now reaches `~/Pictures`. Then switch it back.

## 7. Remote login and the red mark

1. The bar should show nothing in the middle.
2. Settings → Network → **Let other computers log in over SSH**: on.
   Expect a red **SSH open** in the middle of the bar within 5 seconds.
3. Switch it off. The red mark disappears.

## 8. Crash recovery

```
pkill -ABRT -x ade-shell
```
The bar disappears and comes back within a few seconds.

## 9. Glass and the two displays

1. With the monitor plugged in: Settings → Display → **Scale**. Set
   125% for eDP-1 and Automatic for DP-1. Both follow within seconds.
2. Settings → Display → Appearance → **Light**, then **Glass** again.

## When done

1. Settings → About → **Save Report**. It lands in your home folder.
2. Plug the stick into the Fedora laptop, open the `aos-data` partition
   in Files, and tell me. I read the report, `~/issues.md` and
   `/var/log/aos-update.log` from there.
