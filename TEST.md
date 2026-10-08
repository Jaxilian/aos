# Stick test round

On the G14, booted from the stick. Each step says what to do and what
you should see. Write anything that differs into `~/tests.md`, one line
per item, with its number. Your 0.3.0 round is done; its report is
still to be read here (section 3).

## 0. Upgrade to 0.3.1

No reinstall: the fix is in the core and your encrypted home stays.
1. Software → Update → Upgrade system, restart. `grep VERSION_ID
   /etc/os-release` says 0.3.1. Log in as before.

## 1. The active home keeps its node (the 0.3.0 refusals)

On 0.3.0 every password check against your unlocked home was refused
by homed five times before the classic check let you through (the
"Too many unsuccessful login attempts" line, a stalled lock screen, a
password change that failed). All from one cause: the home's
`/dev/mapper` node vanished right after the login.
1. After the login, in a terminal: `ls -l /dev/mapper/home-jax` is a
   symlink to `../dm-N`. `journalctl -b --no-pager | grep -c
   'incompletely set up'` says 0.
2. Ctrl+Alt+F2, log in as jax, then `sudo true` at once: it takes the
   password with no "Too many unsuccessful login attempts" line.
   `journalctl -b -t sudo | tail -3` shows `pam_systemd_home(sudo:auth):
   Home for user jax successfully acquired`.
3. Super+L, type the password: the desktop is back within a second.
4. Settings → Accounts → Set the password: the current one, then a new
   one; it says done, and the next login (log out, log in) takes the
   new one. Set it back the same way.
5. Settings → Accounts: if `test` from the 0.3.0 round is still listed,
   Remove it; `ls /home` no longer shows `test.home`.
6. Leave the machine logged in for twenty minutes, then `journalctl -b
   --no-pager | grep -c 'currently being used'` says 0 (homed's
   rebalance every seven minutes used to fail).

## 2. Still from 0.3.0, not done or not readable here

1. Suspend (close the lid), open it, log in; Notepad saves into your
   home. Neither 0.3.0 boot had a suspend in the journal.
2. Two displays (0.2.8 round, section 2 then): plug the USB-C monitor
   in, out, in: bar and wallpaper each time.

## 3. When done

1. Settings → About → **Save Report**. It lands in your home folder.
2. Plug the stick into the Fedora laptop; your home is mounted as uid
   1000 mode 0700 there, which Claude (uid 1001, no sudo) cannot read.
   Either `sudo setfacl -m u:jax:rx /run/media/jax/jax/jax` and
   `sudo setfacl -m u:jax:r /run/media/jax/jax/jax/{tests.md,issues.md,lock.txt}`,
   or copy them and the report archive into `~/` here, and tell me.
