# SSH

The intended way to work on AOS is to install it on a real machine and drive
that machine from your desk. A foundation has no desktop to sit at, and real
hardware is the only place the drivers, the GPU and the CPU microcode are
actually exercised — QEMU cannot test any of them.

## No key by default

Since 2026-10-07 a stick and a release carry no SSH key and no listening
sshd: root has no password, and the person at the keyboard logs in with
their own. An image built without `br2ext/board/aos/authorized_keys` has
sshd installed but *disabled*, and `make-usb.sh` refuses to write a
keyed image to a stick unless `AOS_DEV=1` says it is a development
stick.

The key is for the QEMU drivers that copy files into the guest
(`fx-test.py`, `desk-test.py`, `disp-test.py`, ...): put it there, build,
run them, and remove it before anything leaves the machine. The file is
**deliberately untracked** (`br2ext/.gitignore`), and `release.sh`
refuses an image with a root key or sshd enabled.

```sh
cp ~/.ssh/id_ed25519.pub br2ext/board/aos/authorized_keys   # the drivers
make
rm br2ext/board/aos/authorized_keys; make                   # before a stick
```

On an installed machine the person turns sshd on in Settings -> Network
("Let other computers log in over SSH"), keys only, with their own
`~/.ssh/authorized_keys`; the bar shows **SSH open** in red while it is.

`post-build.sh` says which it did at the end of every build:

```
post-build.sh: installed 1 SSH key(s) for root; sshd enabled
post-build.sh: no board/aos/authorized_keys -- sshd disabled
```

## Getting AOS onto a machine to SSH into

Install it on a USB stick and boot the machine from that — nothing on the
machine's own disk is touched, and the stick is a full, persistent AOS:

```sh
sudo ./br2ext/board/aos/write-usb.sh /dev/sdX --install
```

Log in as root in the QEMU window it opens, run `aos-install /dev/vda`,
then `poweroff`. Boot the target from the stick; it is an ordinary installed
system with its own host keys, so the changed-host-key warning below does
not apply.

## Getting on the network

Every wired interface, including a USB-C Ethernet adapter, gets an address
by DHCP with no configuration -- plug it in and it is up. That is the
reliable path on a laptop.

Wi-Fi needs the network's credentials once. Find the interface name, write
the configuration, start the supplicant; networkd then does DHCP on it:

```sh
ip link                                   # the wireless one is wl...
wpa_passphrase 'MyNetwork' 'the passphrase' \
    > /etc/wpa_supplicant/wpa_supplicant-wlo1.conf
systemctl enable --now wpa_supplicant@wlo1
networkctl status wlo1                    # "routable" once it has an address
```

Use the real interface name in both the file name and the unit instance;
`wlo1` here is one laptop's. The unit is enabled, so it comes back on every
boot.

## If the screen goes black after boot

A GPU driver that binds and then fails leaves nothing owning the display,
and the console with it. The boot menu has an entry for exactly this:
**AOS (safe graphics, no GPU driver)** boots with `nomodeset`, which keeps
every DRM driver off the screen. Log in there, read the failed boot's log --
it is persistent on an installed system -- and fix what it names:

```sh
journalctl -b -1 -p err --no-pager
journalctl -b -1 -k --no-pager | grep -iE 'xe|i915|nvidia|drm|firmware'
```

Blind, with no console at all: the power button once is a clean poweroff
(logind), and Ctrl+Alt+Del a clean reboot. Over SSH you are root, so
`poweroff` typed blind also works. At the keyboard you are the session's
user, not root: `systemctl poweroff` and `reboot` work there without a
password (polkit lets the active seat), and everything else goes through
`sudo` -- see "Accounts" in [usb.md](usb.md).

## Connecting

```sh
ssh root@<address>
```

Find the address from the machine's own console with `ip addr`, or from your
router. Every wired and wireless interface is on DHCP.

## Host keys, and the warning you will see with the live ISO

On an **installed** system host keys live in `/etc/ssh` and persist, so the
machine keeps one identity and `ssh` stays quiet.

The **live ISO** has a read-only `/etc`, so it generates host keys into
`/run/ssh` on every boot and they are different every time. `ssh` will refuse
to connect the second time with a changed-host-key warning. That is expected.
Either drop the stale entry:

```sh
ssh-keygen -R <address>
```

or, for a machine you are booting from the ISO repeatedly, skip the check:

```sh
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@<address>
```

Only for a live ISO on a network you trust — it disables the protection
against someone impersonating the machine.

## What is configured

`/etc/ssh/sshd_config` in the rootfs overlay. Key authentication only,
`PermitRootLogin prohibit-password`, no X11 forwarding, sftp available (so
`scp` and `rsync -e ssh` work). PAM runs the session stack, so an SSH login
becomes a logind session with a seat and an `XDG_RUNTIME_DIR`, exactly like a
console login — which is what a compositor started over SSH needs.

`sshd` restarts on failure. It does not wait for `network-online.target`:
it listens on the wildcard address, and that wait cost every boot a minute
and a half on a laptop with no Wi-Fi configured.

## Copying files in

`sftp-server` is installed, so both of these work with no extra packages:

```sh
scp file root@<address>:/root/
rsync -a --info=progress2 src/ root@<address>:/root/src/
```

There is no `git` in the image. If you want to clone on the machine rather
than copy to it, add `BR2_PACKAGE_GIT=y` to the defconfig and rebuild.
