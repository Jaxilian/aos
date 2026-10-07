# Alpha roadmap: from a working OS to a product

Written 2026-10-07, at AOS 0.2.8. What it takes for AOS to be something
people and organisations pay for: where it stands, the packages a real
product needs, the business, and the order of work. It assumes a Swedish
company selling first in Sweden and the EU.

## 1. Where AOS stands

**Strong** (five weeks of work, 2 Sept to 7 Oct 2026):

- An image-based OS of the kind organisations want: a read-only core
  checked by dm-verity, A/B slots, an update that boots once and rolls
  back by itself, LUKS2 from the installer. ChromeOS, SteamOS and Fedora
  Silverblue work the same way, and this is the hardest part to get right.
  Tested in QEMU by 28 drivers.
- A release pipeline that answers the questions companies ask: pinned
  sources, a signed SHA256SUMS, a CVE report per release, and a refusal
  to publish a dirty build or one with SSH keys.
- A sandbox for third-party programs, with camera and microphone
  permissions in Software.
- The whole desktop stack is our own and in Rust: compositor, shell,
  toolkit, package manager, store, settings, installer and greeter,
  about 56,000 lines in 12 repos.
- Firefox, VS Code, Discord and Steam run.

**Missing for a Windows or Mac replacement:** one laptop tested (the
G14, the hardest kind); no Secure Boot; no central management; no screen
sharing, printing, VPN or TPM; no screen reader; English and Swedish
only; no firmware updates; several releases a day and no stable channel;
one person behind all of it.

**Verdict.** A replacement for everyone is what Canonical, Red Hat and
Google spend thousands of staff on. A reliable machine for a person who
works in a browser, on one known laptop model, is within a year. Most
office work runs in a browser now (Microsoft 365, Google Workspace,
Teams, the company's own SaaS); for that work AOS's strengths count and
most of its gaps don't. Start there.

## 2. The core packages a real product needs

What the image has today, checked against the defconfig and the kernel
fragment: systemd 258 with repart, logind, homed-capable userdb;
PipeWire and WirePlumber; BlueZ; UPower; polkit; cryptsetup; nftables;
bubblewrap; e2fsprogs and dosfstools; exFAT and NTFS3 in the kernel;
fontconfig and CA certificates. Fonts come from apm's runtime.

Below is what is missing. "BR" means Buildroot already has a package
(a defconfig line); "own" means we write the `.mk` or the code.

### Tier 1: alpha, before anyone pays

| Need | Packages / work | Source |
|---|---|---|
| Secure Boot with our own keys | sign GRUB, the kernel and every module (`CONFIG_MODULE_SIG`, NVIDIA's too); sbsigntools on the build host; keys enrolled at the bench | host tool + release.sh |
| TPM unlock of the disk, recovery key | kernel `CONFIG_TCG_TPM`, `TCG_CRB`, `TCG_TIS` (all off today); tpm2-tss for `systemd-cryptenroll --tpm2-device` | BR + fragment |
| Firmware updates | fwupd, with the LVFS remote | BR |
| Stored logins for browsers, VS Code, Teams | a Secret Service: gnome-keyring or oo7-daemon (Rust), libsecret, unlocked by the login password through PAM | own (libsecret is BR) |
| Video without draining the battery | libva, intel-mediadriver, Mesa's VA drivers; Firefox uses VA-API | BR |
| Fonts that cover every page | Noto (with emoji and CJK) in the image, not only through apm | own |
| Time | systemd-timesyncd, checked on | BR (systemd) |
| Management | `aos-fleet` agent in the image + a server (section 4) | own |
| Kiosk | a session that runs one program full screen and restarts it | own (ade) |
| Stable channel | `channel=` in update.conf, aos-update reads it | own |

### Tier 2: beta, the office worker

| Need | Packages / work | Source |
|---|---|---|
| Screen sharing in Teams, Meet, Zoom | xdg-desktop-portal + a ScreenCast backend in ade (PipeWire stream); the same portal gives the FileChooser by fd | own (not in BR) |
| Printing | CUPS, cups-filters (with qpdf, ghostscript), avahi for IPP Everywhere discovery; a Settings page | BR |
| Scanning | sane-backends + sane-airscan (driverless) | BR + own |
| VPN | kernel `CONFIG_WIREGUARD` (off today), wireguard-tools; OpenVPN for older corporate VPNs; a Settings page | BR + fragment |
| Enterprise Wi-Fi | wpa_supplicant already does 802.1X (PEAP, EAP-TLS); Settings needs the fields and certificates | own (Settings) |
| Docks | bolt (Thunderbolt authorisation); DisplayLink only if customers ask | own |
| Battery and heat | power-profiles-daemon, thermald (Intel) | own + BR |
| USB sticks and phones | exfatprogs, ntfs-3g tools for formatting; libmtp for phones | BR |
| An office suite | LibreOffice or OnlyOffice as an apm package | apm recipe |
| Swedish UI | translations in tgn (gettext or Fluent) and every app | own |
| Smart cards (healthcare SITHS, some e-ID) | pcsc-lite, opensc | BR |

### Tier 3: 1.0, organisations at scale and the public sector

| Need | Packages / work | Source |
|---|---|---|
| Screen reader | at-spi2-core, speech-dispatcher, espeak-ng, Orca; AccessKit in tgn so our apps are readable at all | BR + own |
| Login with the organisation's account | Entra ID (himmelblau) or AD (sssd, krb5, realmd) in the greeter's PAM | own + BR |
| Compliance | audit (auditd), usbguard (USB device policy) | BR |
| Input methods for non-Latin languages | fcitx5 or ibus with a Wayland input-method in ade | own |
| Fingerprint login | fprintd + libfprint | own |
| 2-in-1 laptops | iio-sensor-proxy | own |
| Mobile broadband | ModemManager | BR |
| Multi-GPU output (HDMI on NVIDIA laptops) | smithay's GpuManager in ade | own |

**Not needed:** NetworkManager (networkd + our Settings do it),
firewalld (nftables is there), Flatpak (apm is the one way in), an X
server (XWayland on demand).

Each package added is a QEMU check in a driver, as everything else is.

## 3. The business

### What we sell

1. **AOS laptops**: one refurbished business model with AOS installed,
   our Secure Boot keys enrolled, 2-3 years of warranty.
2. **AOS Managed**, per device per month: the stable channel, central
   management, recovery-key escrow, remote wipe, email support. This is
   the business; hardware pays once, this pays every month.
3. **Setup services**: migration, Wi-Fi and accounts, training; by the day.
4. **The store**, later (section 5).

The OS stays free and open source: it brings developers, and it is the
answer to "what if the company disappears".

### Who buys, in order

1. **Kiosk and single-purpose machines**: receptions, shop terminals,
   library and school lab PCs, signage, call-centre machines that only
   open a browser or a Citrix/AVD web client. An OS that cannot be broken
   and rolls back by itself is the whole point, and they need Tier 1
   only. Competitors: ChromeOS Flex with Chrome Enterprise (about $50 per
   device a year), IGEL, Porteus Kiosk, Windows IoT. Our angle: European,
   no Google account, cheap refurbished hardware.
2. **Small organisations working in the browser**: NGOs, associations,
   consultancies, independent schools. They decide fast and buy on price,
   privacy and "no forced updates in a meeting". Needs Tier 2.
3. **Public sector**, year 2-3: a real European push away from US
   vendors (Denmark's digital ministry and Schleswig-Holstein in
   2024-25), but tenders need Tier 3, references and procurement (LOU)
   frameworks. Run pilots now for the references.

Not worth chasing: consumers (thin margins, a 3-year complaint right,
14-day returns, phone support) and gamers (SteamOS and Bazzite are free).

### Hardware

- One certified model where everything works: an Intel-graphics business
  laptop (ThinkPad T14/T480s/X1 class, Latitude 5000/7000), no NVIDIA,
  Intel Wi-Fi. Every release runs the QEMU drivers plus a hardware
  checklist on it. The G14 stays the torture test, not the product.
- Bought in lots from a refurbisher (Inrego, Foxway, Atea Remarketing),
  grade A, battery health guaranteed.
- Selling our own hardware solves Secure Boot without Microsoft: our keys
  at the bench, signed GRUB and kernel. A Microsoft-signed shim, for "any
  PC", can wait.
- A factory script: wipe, firmware update, BIOS settings (keys, admin
  password, boot order), `aos-install --oobe`, a hardware self-test, the
  serial number into the management server. usb.sh and the drivers are
  most of it.

### Rough numbers (check before buying)

| | per unit |
|---|---|
| Refurbished ThinkPad T14 Gen 2-3, lot price | 2,500-3,500 kr |
| Sale price with AOS, setup, 3-year warranty (B2B, ex VAT) | 5,500-6,500 kr |
| Warranty reserve, shipping, fees, charger, box | ~700 kr |
| Gross margin | ~1,500-2,500 kr |
| AOS Managed, per device per month | 50-90 kr |

40,000 kr a month before tax is about 20 laptops a month, or 500-800
managed devices, or a mix. Track support hours per device per month;
above about 0.25 the price is wrong or the OS is not ready.

### Company and legal

- An aktiebolag, not an enskild firma: hardware means warranty liability.
- B2B first: no consumer complaint and return rights to carry.
- GPL: shipping devices means offering the source of every GPL part.
  `make legal-info` produces the list and the sources; publish them with
  the release and put the written offer in the box.
- The name: "AOS" is crowded (Alpha and Omega Semiconductor and many
  software products). Search PRV and EUIPO before printing a box.
- A licence on every repo we own; a buyer of a fleet asks.
- A GDPR data processing agreement once the management server holds
  device data; host it in the EU.
- Funding to look at: Vinnova, ALMI, NLnet / NGI Zero (accessibility in
  tgn or the portal is the kind of work they fund). Check current calls.

## 4. The order of work

**Stop** glass, animations and transitions beyond what is done. No
customer buys on them.

### Phase A: something to sell (now to about 3 months)

1. Certify one laptop model; buy two units.
2. The stable channel: a release reaches `stable` after a week on `edge`.
3. `aos-fleet` v1: an enrolment token at install or first boot; the
   device reports version, slot, disk, battery, last boot; the server
   sets channel or hold, the allowed packages (an apm repo of the
   organisation's own), Wi-Fi profiles, the kiosk URL; lock and wipe
   (wipe = destroy the LUKS key slots). A web page listing devices.
4. Kiosk mode.
5. TPM2 unlock with the recovery key escrowed to the server.
6. Secure Boot with our keys on the certified model.
7. The rest of Tier 1: fwupd, Secret Service, VA-API, Noto.
8. The factory script.

Then five pilot customers, kiosk first, free or at cost, for a reference
and weekly feedback.

### Phase B: the office worker (3-6 months)

9. Screen sharing (the portal); decides whether Teams and Meet work.
10. Printing, VPN, enterprise Wi-Fi, docks, power profiles.
11. An office suite in the store.
12. The Swedish UI.
13. First paid devices and subscriptions.

### Phase C: grow (6-12 months)

14. Management v2: policies, reports, roles, an admin UI customers run
    themselves.
15. Login with the organisation's identity, or accounts pushed from the
    server first.
16. Accessibility (Tier 3).
17. A second certified model; a signed shim if customers bring hardware.
18. The store with payments.

## 5. The store with purchases

After Phase B: a store earns only when there are buyers, and developers
come after users. Designed now so nothing blocks it later.

Today apm's index is minisign-signed and its artifacts are on GitHub
Releases. A paid package is the same entry plus a `price` and
`licence = "account"`, and its artifact is not public:

```
Software ──buy──▶ payment provider ──webhook──▶ store server (records the entitlement)
apm install ──account token──▶ store server ──signed URL, 5 min──▶ object storage
apm verifies the package against the signed index, as today
```

- **Accounts**: one per person, signed in from Software (OIDC device
  flow); the device keeps a refresh token.
- **Entitlements**: the server signs a licence (ed25519, as minisign)
  naming account, package and versions; apm keeps it, so a bought
  program reinstalls offline.
- **Payments through a merchant of record** (Paddle, Lemon Squeezy): it
  is the seller in law and handles EU VAT, refunds and invoices. Worth
  its 5% for one person.
- **Developers**: upload, a 15% cut, payouts through the merchant.
- **Organisations**: a private catalogue, volume licences assigned to
  devices, an invoice instead of a card. Likely the store's first income.
- **Copy protection**: light. On an open system it stops casual copying
  and nothing more; Steam and itch.io live with that.

## 6. The first month

1. Choose and buy the certified model (two units); run AOS on it and
   file what breaks.
2. Register the AB; check the name at PRV and EUIPO.
3. `aos-fleet` v0: enrolment, the device list, the update channel.
4. Turn on TPM and WireGuard in the kernel fragment; add tpm2-tss and
   fwupd; QEMU checks for each (swtpm gives QEMU a TPM).
5. A one-page website: what it is, for whom, a price, a contact form.
6. Talk to ten possible customers (a reception, a library, a school, two
   NGOs, a shop) before building kiosk mode: what do they run, what does
   it cost, what breaks. Build what three of them ask for.
