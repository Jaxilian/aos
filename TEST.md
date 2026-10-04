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
   Expect `0.1.20`.
4. Software → Update → **Upgrade system** once more, if lines are
   left: runtime/gtk3 release 7 (libpulse) is one. Each line ends in
   done or failed; note any failed one with its reason.
4b. About two minutes after a boot a toast says what updates wait (if
   any). Click it: Software must open on its Update page.
5. Once only, for the brightness slider:
   ```
   sudo usermod -aG video admin
   ```
   Then log out and in.

## 1. Sound

Firefox and Discord play through PulseAudio's API, and 0.1.19 had no
libpulse at all; runtime/gtk3 release 7 carries it. So first:
Software → Update → **Upgrade system** (or `sudo apm upgrade`), which
rebuilds Firefox on the new runtime, then start Firefox again.

1. Play any YouTube video. While it plays:
   ```
   wpctl status | sed -n '/Streams/,$p'
   ```
   Expect a Firefox line under Streams, and sound from the chosen output.
2. If still silent, from the terminal:
   ```
   ls /opt/apm/packages/runtime/gtk3/current/lib/ | grep pulse
   journalctl --user -b | grep -i -E "pulse|pipewire" | tail -5
   ```
3. The speaker: the card's components say `spk:cs35l56+cs42l43-spk`,
   the same as Fedora on this machine. This lists what UCM offers:
   ```
   alsaucm -c sof-soundwire list _verbs
   alsaucm -c sof-soundwire set _verb HiFi list _devices
   ```
   Put both outputs in `~/issues.md`.

## 2. Bluetooth

The journal of your last round shows the adapter working (hci0 with its
firmware loaded, bluetoothd managing it); what prints nothing is the
bluetoothctl client. Put the output of these in `~/issues.md`:
```
busctl --no-pager tree org.bluez
busctl --no-pager --json=short call org.bluez / org.freedesktop.DBus.ObjectManager GetManagedObjects | cut -c1-600
bluetoothctl show | cat; echo rc=$?
```
Settings → Bluetooth stays as it was; a client that talks to BlueZ
directly is the next step and these lines tell me the shape of the data.

## 3. Suspend and lid

Last round: the windows' contents vanished after the first resume and
the machine froze after the second; no lock screen. The shell now locks
the screen when the machine is about to sleep.

1. Open Notepad with some text and a terminal. Then, before closing
   the lid, so the journal survives a freeze:
   ```
   sudo journalctl --flush; sync
   ```
2. Close the lid, wait 30 seconds, open it. Expect the lock screen,
   then your desktop with the windows' contents intact. Note which of
   the three you got.
3. If it came back, at once:
   ```
   journalctl -b --no-pager | grep -i -E "resume|vulkan|device lost|awin|ade:" | tail -30 > ~/suspend.txt
   ```
   If it froze, after the reboot:
   ```
   journalctl -b -1 --no-pager | tail -150 > ~/suspend.txt
   ```
4. Only if 2 went well: `systemctl suspend` from a terminal, power
   button to wake, same expectations.

## 3b. Brightness

The slider writes the panel's backlight as your user, which needs the
`video` group and the udev rule's permissions. Put the output in
`~/issues.md`:
```
id | tr ' ' '\n' | grep -c video
ls -l /sys/class/backlight/*/brightness
for b in /sys/class/backlight/*; do echo "$b -> $(readlink $b/device)"; done
```
Then the quick panel's slider: expect the panel to follow. If not,
```
journalctl -b --no-pager _COMM=ade-shell | grep -i bright | tail -3
```

## 4. Software: the system applications and the permissions

1. Software → Official: Files, Images, Notepad, Terminal, Settings,
   Software, System Monitor, every one marked **Installed**.
2. Software → Third-party → Firefox. Expect, below the details, a
   **Permissions** section: "Its own files" chosen, the folders with
   Downloads on, Network on.
3. Give it **Pictures**, start Firefox, File → Open File: the dialog
   reaches `~/Pictures`. Switch Pictures off again.
4. Settings has no Programs page any more; About's **Open Software**
   button opens Software on Update.

## 5. Firefox in its sandbox

1. Open Firefox. Expect no "Welcome / Terms of Use" screen.
2. Open any website. Text must be letters, not boxes.
3. Download a file. Expect it in `~/Downloads`.

## 6. Update, after the upgrade

1. Right after step 0's upgrade, before the restart: Software → Update
   must say "AOS 0.1.20 is installed and boots at the next restart"
   with a **Restart** button, and no second Upgrade system for the OS.
2. Software → AOS says the same at the top.

## 7. Crash recovery

```
pkill -ABRT -x ade-shell
```
The bar disappears and comes back within a few seconds.

## 8. The HDMI port

On this laptop the HDMI port is wired to the NVIDIA GPU, and the
desktop renders on the Intel one only, so an HDMI monitor stays black
for now; the USB-C port goes through the Intel GPU and works. Nothing
to test; it is on the list.

## When done

1. Settings → About → **Save Report**. It lands in your home folder.
2. Plug the stick into the Fedora laptop, open the `aos-data` partition
   in Files, and tell me. I read the report, `~/issues.md`,
   `~/suspend.txt` and `/var/log/aos-update.log` from there.
