# Stick test round

On the G14, booted from the stick. Each step says what to do and what
you should see. Write anything that differs into `~/issues.md`, one line
per item, with its number. Your 0.3.0 report is read (TODO.md says what
came of each item); this round is 0.3.2, which holds 0.3.1's fix and
the answers to that report.

## 0. Upgrade to 0.3.2

No reinstall: the fix is in the core and your encrypted home stays.
1. Software → Update → Upgrade system, restart. `grep VERSION_ID
   /etc/os-release` says 0.3.2. Log in as before.

## 1. The active home keeps its node (the 0.3.0 refusals)

On 0.3.0 every password check against your unlocked home was refused
by homed five times before the classic check let you through (the
"Too many unsuccessful login attempts" line, the frozen Settings).
1. After the login, in a terminal: `ls -l /dev/mapper/home-jax` is a
   symlink to `../dm-N`. `journalctl -b --no-pager | grep -c
   'incompletely set up'` says 0.
2. Ctrl+Alt+F2, log in as jax, then `sudo true` at once: it takes the
   password with no "Too many unsuccessful login attempts" line.
3. Super+L, type the password: the desktop is back within a second.
4. Settings → Accounts → Set the password: a wrong current one says
   "Wrong current password" at once, and Settings stays; the right one
   with a new password says done, and the next login (log out, log
   in) takes the new one. Set it back the same way.
5. Settings → Accounts: `test` from the 0.3.0 round is still listed;
   Remove it; `ls /home` no longer shows `test.home`.
6. Twenty minutes logged in, then `journalctl -b --no-pager | grep -c
   'currently being used'` says 0.

## 2. The USB-C display

The compositor never drew a display that arrived after the start: the
first frame of a head is what starts its drawing, and a hot-plugged
head got none. Only the G14 can show the fix.
1. Plug the monitor in: bar and wallpaper within seconds. Unplug it:
   the windows come back to the laptop. Plug it in again: bar and
   wallpaper again.
2. Settings → Display → Mirror: the monitor shows the laptop's picture;
   Mirror off: its own bar and wallpaper again.
3. Still black: `journalctl -b -t ade-session --no-pager | tail -40 >
   ~/display.txt`.

## 3. Small things from your report

1. Super, type a few letters, Ctrl+A: the query turns the accent
   colour; Backspace empties it; type again, Ctrl+A, a letter: only
   that letter.
2. Software: Install three things in a row (Blender, Krita, Inkscape):
   the first says Working..., the other two Queued, and each follows
   when the one before is done; the notice says "Queued: ...".
3. The recovery key page (5.1) comes only at a first boot. Skip it, or
   if you reinstall anyway (`./usb.sh --no-build --release /dev/sdX`):
   the key is on two lines, whole, and Copy puts it on the clipboard
   (paste it into the name field to see). Then 0.3.0's 5.5: at the
   login screen the key typed as the password opens your home.

## 4. The window controls are the compositor's

The three lights at the top right of every window are drawn by the
compositor now, the way Windows owns the caption buttons; an AOS
program keeps its own strip with its menus to the left of them.
1. Notepad: its strip looks as before (File, Edit left, the lights
   right). The red light asks about unsaved text; the yellow one
   maximizes and again restores; the green one minimizes and the dock
   brings it back. Drag the strip: the window moves.
2. Software → Blender (or Spotify): the window has a strip above it
   with its title at the left and the lights at the right; drag it
   moves, a double click on it maximizes, the red light closes. Same
   for Krita and Inkscape.
3. Firefox and Chrome keep their own frames and buttons, with nothing
   of ours over them.
4. Steam: its own frame, as before; a dialog it opens (Settings) gets
   our strip if it has none of its own.

## 5. Still from 0.3.0, not done

1. Suspend (close the lid), open it, log in; Notepad saves into your
   home. Neither 0.3.0 boot had a suspend in the journal.

## When done

1. Settings → About → **Save Report**. It lands in your home folder.
2. Plug the stick into the Fedora laptop, `sudo setfacl -m u:jax:rx
   /run/media/jax/jax/jax`, and tell me.
