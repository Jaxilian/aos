# TODO

Updated 2026-10-03. The newest release is 0.1.14. The stick round is in
[TEST.md](TEST.md).

Anything that needs a second machine, a second stick or a permanent
installation is postponed (see the end).

## Next, in priority order

1. **The live ISO's demo account.** Replace `admin` / `123321` and the
   passwordless root with a random password only the installer uses.
   The first thing a reviewer flags.
2. **The stick round** ([TEST.md](TEST.md)): sound, Bluetooth, suspend
   and lid, XWayland, Firefox in its sandbox, Settings → Programs, the
   red SSH mark, crash recovery, two displays.
3. **Release notes** on the download page, generated from the commit
   messages of each release. The release body is empty today.
4. **Open CVEs**: binutils and systemd, through the toolchain and core
   bump, a clean rebuild and the QEMU suite
   ([br2ext/docs/security-status.md](br2ext/docs/security-status.md)).
5. **CI runner**: register a self-hosted GitHub runner with the label
   `kvm` on the Fedora laptop. `.github/workflows/aos.yml` and
   `br2ext/board/aos/ci.sh` are ready.
6. **Steam's sandbox declaration.** It already runs in `aos-sandbox`;
   the store still says "everything, undeclared".
7. **Display arrangement** and per-display on/off in Settings → Display.
8. **A file dialog the desktop draws** for sandboxed programs, so they
   reach one chosen file outside their home.
9. **AOS's own apps in the sandbox** (Files, Notepad, Images, Terminal),
   once the file dialog exists.
10. **dm-verity on the root slots.** The release becomes an image, not a
    tarball: release.sh, aos-update and aos-install change. Testable in
    QEMU.
11. **LUKS-encrypted home**, unlocked at login. QEMU first, then the
    stick, which needs its data partition recreated.

## Postponed: needs hardware

- A second test machine (Intel or AMD laptop): boot, graphics, Wi-Fi,
  sound, suspend, touchpad.
- The ISO written with dd to a stick, and whether the firmware boots it.
- The graphical installer end to end on a disk that can be erased.

## After stable, decided

- Secure Boot (unsupported; turn it off). See
  [br2ext/docs/policies.md](br2ext/docs/policies.md).
- Drag and drop between programs; glass showing other windows.
- btrfs and snapshots for `aos-data`.

## Done (for the record)

- Releases: pinned sources, signed SHA256SUMS, a public download page
  with the CVE report; release.sh refuses a dirty build, a build that is
  not its tag, and an image with an SSH key or with sshd enabled.
- Updates: A/B root slots with confirm and rollback; one update at a
  time; a log in `/var/log/aos-update.log`; safe to interrupt at any
  point (`update-abort-test.py`).
- Security: the model and values in
  [br2ext/docs/security-model.md](br2ext/docs/security-model.md); a
  closed firewall; sshd off unless switched on, with a red bar mark;
  kernel and sysctl hardening; signed package indexes; the app sandbox
  with private homes, declarations shown in the store and changeable in
  Settings → Programs; Firefox without telemetry.
- The desktop: installer, Settings, app store, crash-safe session,
  screenshots, per-display scale, glass.
