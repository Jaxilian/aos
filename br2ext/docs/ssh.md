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
