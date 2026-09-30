# Policies: what AOS promises, and what it has decided

Short statements an evaluator asks for. Each one is a decision, written
down so it is not re-argued; the roadmap items they close are named.

## Releases and support

A 0.x release monthly, tagged, with the ISO, its signed `SHA256SUMS` and
the legal-info manifest published together
([publishing.md](publishing.md)). Each release is supported until the
next one: fixes go into the next monthly release, not into the old one.
There are no point releases before 1.0 unless a fix cannot wait a month,
in which case the release is simply cut early. A release is not made from
a `-dirty` tree ([release.sh](../board/aos/release.sh) refuses).

Until base-OS updates exist (roadmap Phase 1, item 5), moving an installed
machine to a new release is a reinstall that keeps `/home`
([usb.md](usb.md), "Reinstalling").

## Security reporting

[SECURITY.md](../../SECURITY.md) at the repository root: the address, what
happens to a report, the 90-day disclosure window, and what is AOS's to
fix versus upstream's.

## No telemetry

AOS sends nothing anywhere on its own. No usage reports, no crash reports,
no update pings beyond the package index fetch that `apm update` makes
when you or the Settings application ask for one, and no identifier that
would let a server tell one machine from another. The diagnostics bundle
that `aos-report` writes stays on the machine until a person copies it
somewhere. This is true of the image today and it is a promise for every
release: a change that broke it would be a bug, and it would be reverted.

Third-party software does what it does; Firefox, Discord, Steam and Visual
Studio Code have their own telemetry and their own settings for it. That is
part of what "third-party" means on AOS.

## Network: closed by default

An AOS machine answers nothing it was not asked. The firewall
(`/etc/nftables.conf`, loaded before the network) drops every inbound
packet that is not a reply, ICMP, a DHCP answer or SSH; sshd itself is
enabled only in an image built with an SSH key; systemd-resolved's LLMNR
and mDNS responders are off. There is no LSM policy (AppArmor, SELinux,
Landlock) yet, and no automatic update timer: `apm upgrade` is run by a
person or by the Settings application. Both are known gaps, not decisions.

## Secure Boot: unsupported

Nothing AOS ships is signed for UEFI Secure Boot: not GRUB, not the kernel,
not the NVIDIA modules. A machine with Secure Boot on will not boot it.
Turn Secure Boot off in the firmware setup. This is the first line of the
known limitations, and it stays that way until there is a reason to carry
shim, a MOK-enrolled kernel and signed modules -- a business reason, since
the engineering is known and the maintenance is what costs.

## Disk encryption: not yet, and `/home` first when it comes

AOS boots with no initramfs ([../PLATFORM.md](../PLATFORM.md)), so the
root filesystem cannot be on LUKS: there is nothing to unlock it before
the kernel mounts it. When encryption comes it will be `/home` on LUKS,
unlocked at login by the password, with the root left in the clear; that
needs no initramfs and protects what is personal. Full-disk encryption
would need a minimal initramfs and is not planned. Until then: an AOS
machine's disk is readable by anyone who has the disk.

## Base OS updates

Today: reinstall, keeping `/home`. Planned: a signed, versioned root image
in A/B slots with a "previous version" boot entry (roadmap Phase 1, item
5). Application updates already go through `apm upgrade` and the Settings
application's Software page.
