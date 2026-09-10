# SSH

The intended way to work on AOS is to install it on a real machine and drive
that machine from your desk. A foundation has no desktop to sit at, and real
hardware is the only place the drivers, the GPU and the CPU microcode are
actually exercised — QEMU cannot test any of them.

## Before you build: add your key

**AOS accepts no SSH login until you do this.** Root has no password, and
sshd refuses password authentication anyway, so a key is the only way in.

```sh
cp ~/.ssh/id_ed25519.pub br2ext/board/aos/authorized_keys
make
```

The file may hold several keys, one per line, and `#` comments are stripped.
It is **deliberately untracked** — see `br2ext/.gitignore`. An image you
publish must not carry anyone's key, or whoever built it has root on every
machine that installs it. If you have no key yet, `ssh-keygen -t ed25519`.

`post-build.sh` says which it did at the end of every build:

```
post-build.sh: installed 1 SSH key(s) for root
post-build.sh: no board/aos/authorized_keys -- SSH will accept no logins
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
(logind), and Ctrl+Alt+Del a clean reboot. There is no `sudo` on AOS; you
are root, so `poweroff` typed blind also works.

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

`sshd` waits for `network-online.target` and restarts on failure.

## Copying files in

`sftp-server` is installed, so both of these work with no extra packages:

```sh
scp file root@<address>:/root/
rsync -a --info=progress2 src/ root@<address>:/root/src/
```

There is no `git` in the image. If you want to clone on the machine rather
than copy to it, add `BR2_PACKAGE_GIT=y` to the defconfig and rebuild.
