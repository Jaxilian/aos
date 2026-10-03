# The security model

What AOS defends its users against, how, and what is still to build.
This is the page the word "secure" is measured against; the CVE report
of each release is [security-status.md](security-status.md), the
promises are [policies.md](policies.md).

## The values

1. **AOS protects its users' privacy and integrity.** Nothing leaves the
   machine that the person did not send. No telemetry, no accounts, no
   identifiers ([policies.md](policies.md)).
2. **AOS protects its users from threats, outside and inside.** From the
   network, from a stolen laptop, and from a program they installed
   themselves.
3. **AOS provides an easy way to do everything.** Protection that needs a
   terminal, a policy file or a judgment call has failed; the safe way is
   the default and the only one on offer.
4. **AOS strives for "it just works".** A protection that breaks a
   program people need is a protection they will switch off.

The person owns the computer. AOS serves them, not a vendor: there is no
one else to report to, and no way in for anyone they did not let in.

## Who AOS is defending

- **Someone's grandmother**, who installs what a web page tells her to,
  types her password where she is asked, and never opens Settings.
- **A child** who downloads "free RAM", a cracked game, or a Discord
  plugin, and runs it. The program is the attacker.
- **A household**, where one account's documents are not another's.
- **An enterprise**, which asks how the machine is updated, what runs
  on it with what rights, what happens when a laptop is stolen, and
  wants every answer in writing and checkable.

The threats, in the order the defences below address them:

| Threat | What it looks like |
|---|---|
| A malicious program | Installed by the person, runs as them, reads their files, keys and sessions, talks to the network, stays after a restart |
| The network | A port that answers, a service that can be asked to do something, a download that was tampered with on the way |
| A stolen machine | The disk read in another computer; the OS altered and put back |
| A compromised AOS | Our own build machine, signing key or repository, or someone claiming to be it |
| Another account on the same machine | Reading or changing what is not theirs |

Not defended against, and said so: an attacker with physical access and
time (Secure Boot is off, see below), a compromised CPU or firmware,
and the person themselves typing their password into a program they
should not have trusted -- the sandbox limits what that program then
gets.

## What is in place

**Updates and software come signed, or not at all.** apm refuses an
index that no trusted key verifies; the image ships the official key.
`aos-update` writes a release's root tarball into the idle slot only
when `SHA256SUMS` carries that key's signature, and GRUB boots the new
slot once before the desktop confirms it ([upgrading.md](upgrading.md)).
A tampered download, mirror or publisher is a refused download.

**The network is closed.** nftables drops everything inbound that is
not a reply, except DHCP, ICMP and port 22. Nothing listens on 22
unless the person turns remote login on in Settings -> Network, with a
key and never a password; while it is on, the bar shows **SSH open** in
red in the middle of the screen, so a door opened for a reason is not
forgotten. A published image carries nobody's key: `release.sh` refuses
an image with a root key on it ([ssh.md](ssh.md)).

**Programs cannot read each other's memory, or the kernel's.** Yama
limits ptrace to a process's own children; kernel pointers and the
kernel log are root's; BPF and perf counters are root's; the running
kernel cannot be replaced from userspace (`/etc/sysctl.d/10-aos-hardening.conf`).
The kernel builds with the memory-corruption checks Fedora's does and the
security modules a desktop can use without a policy -- Landlock, Yama,
lockdown -- and not SELinux, Smack, TOMOYO or AppArmor, which do
nothing without a policy nobody has written and would imply one.

**Everything is built with the usual hardening**: PIE, full RELRO,
`-fstack-protector-strong` and `_FORTIFY_SOURCE=2`, as Fedora and
Ubuntu do.

**Accounts are separate.** Homes are 0700; the first account is an
administrator and the rest are not; root has no password and no
console login; `sudo` asks for the person's own. The live system's
account has no password either: nothing on the ISO lets anyone in by a
password that every copy shares, and whoever sits at the stick owns the
machine, so its sudo asks for none and there is no lock screen there.

**Third-party programs are labelled**, carried in their own repository
at the person's risk, and never a dependency of anything official.

**A program sees what its package declares, and the store says so.** A
package's manifest carries a `[sandbox]` section -- `home = "private"`
with the directories it may share (`Downloads`), or `home = "full"` for
an editor -- and apm writes the program's command and desktop entry to
run through `aos-sandbox` with exactly those flags: bubblewrap,
unprivileged, the OS read-only, the package and what it depends on, the
session's sockets, and a home of its own under `~/.var/app/<org>.<name>`
that holds nothing of the real one but the shared directories. The
store's details page shows it as "Sees: its own files and Downloads"
before Install, and Settings -> Programs shows every sandboxed program
with what it may see, and lets the person change it: its own files or
the whole home, each of Downloads, Documents, Pictures, Music and
Videos, and the network. The change is a line in
`~/.config/aos/sandbox/<org>.<name>` that aos-sandbox reads over the
package's declaration. Firefox and Discord run that way; Visual Studio
Code sees the whole home, being an editor; Steam runs in the same
sandbox with the whole home and its 32-bit runtime. A package that
declares nothing runs as the person, and the store says "everything,
undeclared".

## What is next, in order

1. **The rest of the sandbox.** The private home and the declared
   directories are in (above); what is still to come: a file dialog the
   desktop draws, so a sandboxed program reaches one chosen file outside
   its home and nothing else (the portal pattern) -- until then a program
   that needs more declares a directory, or the person grants one in
   Settings; Landlock fencing the view a second
   time from inside; a package that cannot be installed without a
   declaration, once every recipe has one; and AOS's own programs in it
   too. The declaration is what answers the child with the download: a
   "free RAM" package that asks for the whole home says so on its page.
2. **Verified root slots.** Each A/B slot is one image, written once and
   never changed, which is what dm-verity is for: a hash tree over the
   slot, its root hash in the signed `SHA256SUMS`, checked by the kernel
   on every read, set up from the kernel command line so no initramfs is
   needed. A root compromise then does not survive a restart, and a
   disk altered in another computer does not boot. It changes the release
   from a tarball extracted into a partition to an image written to one.
3. **`/home` encrypted**, LUKS, unlocked by the account's own password at
   login, as decided in [policies.md](policies.md). A stolen laptop is
   then a stolen laptop and nothing more. The root slots stay in the
   clear: there is nothing private in them, and verity covers their
   integrity.
4. **Secure Boot**, shim, a MOK-enrolled kernel, signed modules
   including NVIDIA's, and lockdown on. This closes the chain from
   firmware to kernel and is the last link verity and LUKS leave open.
   It is known engineering and ongoing maintenance per kernel and per
   driver, and it comes after the three above, which stop more.
5. **An outside measure.** The CIS benchmark for a Linux desktop run
   once against a release and the differences explained here, so the
   claims above are checked by someone else's list.

## How a report reaches us

[../../SECURITY.md](../../SECURITY.md): the address, the window, and
what an alpha promises.
