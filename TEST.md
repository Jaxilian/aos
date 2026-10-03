# Stick test round

On the G14, booted from the stick. Each step says what to do and what
you should see. Write anything that differs into `~/issues.md`, one line
per item, with its number.

## 0. Get onto the newest release

1. Boot the stick. If it does not reach the desktop, hold the power
   button, start it again: it falls back to the old version by itself.
2. Settings → Software → **Install**. Press it **once**, then wait for
   "installed in slot …" (a few minutes). Touch nothing else meanwhile.
3. Restart. About 20 seconds after the desktop appears, check:
   ```
   grep VERSION_ID /etc/os-release
   ```
   Expect `0.1.14`.
4. Settings → Software → **Upgrade**, once. This rebuilds Firefox,
   VS Code and Discord into their sandboxes. Wait until it says done.
5. Once only, for the brightness slider:
   ```
   sudo usermod -aG video admin
   ```
   Then log out and in.

## 1. Sound

1. Open Firefox and play any YouTube video.
2. Settings → Sound: try each output, and the volume keys.
3. If silent:
   ```
   wpctl status
   cat /proc/asound/cards
   ```

## 2. Bluetooth

1. Settings → Bluetooth: turn it on, scan, pair something (headphones,
   a mouse).
2. Note what the page says at each step. If nothing shows:
   ```
   bluetoothctl show
   bluetoothctl power on
   bluetoothctl --timeout 10 scan on
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

1. Settings → Software → Compatibility → **XWayland**: switch it on.
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
