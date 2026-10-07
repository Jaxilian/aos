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

An installed machine moves to a new release by a base-OS update (below).
A machine on 0.1.x cannot update to 0.2.x and is reinstalled once
([layout.md](layout.md)).

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
packet that is not a reply, ICMP, a DHCP answer or SSH; sshd itself runs
only when the person turns remote login on in Settings -> Network (a
developer's image built with an SSH key has it on; `release.sh` refuses
to publish one); systemd-resolved's LLMNR
and mDNS responders are off. There is no LSM policy (AppArmor, SELinux,
Landlock) yet -- a known gap, not a decision. Updates are looked for
daily (`aos-update-check.timer`, which refreshes the signed indexes and
asks whether a new AOS is out) and the desktop says when there are some;
nothing is installed without the person: `apm upgrade`, Software ->
Updates or Settings does that. The CVE report of each release and its
triage are in [security-status.md](security-status.md).

## Secure Boot: unsupported

Nothing AOS ships is signed for UEFI Secure Boot: not GRUB, not the kernel,
not the NVIDIA modules. A machine with Secure Boot on will not boot it.
Turn Secure Boot off in the firmware setup. This is the first line of the
known limitations, and it stays that way until there is a reason to carry
shim, a MOK-enrolled kernel and signed modules -- a business reason, since
the engineering is known and the maintenance is what costs.

## Encryption: every home, always; the whole partition by choice

Decided 2026-10-07 (0.3.0). Every account is a systemd-homed one: its
home is a LUKS2 volume of its own, unlocked by its password at login
and locked when the last session ends, so a stolen laptop is a stolen
laptop and nothing more, with no choice to make at install. A recovery
key is made with the home and shown once at the first boot; a forgotten
password without it is the data gone, by design, and the setup says so.
The owner is therefore made at the machine's first boot, by the
installed system itself, for every kind of install: the installer asks
no account. Machines installed before 0.3 keep their classic account
(reinstall to get an encrypted home).

The installer's "Also encrypt the whole disk" (`aos-install --encrypt`)
puts LUKS2 around the aos partition as well: programs, settings, the
journal, with a passphrase of its own asked on the console at every
start, before the desktop. The swap file exists only there. The cores
stay in the clear: they are the public release images, and verity
covers their integrity ([layout.md](layout.md)).

## Base OS updates

A release's core image (a squashfs with its dm-verity hash tree), named
in a `SHA256SUMS` signed with the apm key, written by `aos-update` into
the idle one of two core slots and checked through its verity; GRUB boots it once and the desktop coming up confirms it, else the
previous slot boots at the next reset, and "AOS (previous version)" in the
boot menu goes back by hand ([upgrading.md](upgrading.md)). Accounts,
`/home`, installed programs and settings live on the aos partition, which
no update touches; the kernel comes with the core, not from apm. Application updates go through `apm upgrade`; both are on the
Software application's Update page. A disk installed before 0.2.0
is reinstalled once, which erases it.
