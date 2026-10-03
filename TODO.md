# TODO

Updated 2026-10-03 evening. The newest release is 0.1.18 (kernel 7.2.9). The stick round is in
[TEST.md](TEST.md).

Anything that needs a second machine, a second stick or a permanent
installation is postponed (see the end).

## Next, in priority order

Done since 2026-10-03 morning: the live ISO's account has no password
(0.1.16); release notes come from the commit log; binutils 2.46.1
closed eight CVEs and the systemd one is ignored with its reason
(0.1.17); a performance baseline exists
([br2ext/docs/performance.md](br2ext/docs/performance.md)); the CI
runner is installed on this laptop.

1. ~~**The kernel to 7.2.y.**~~ Done and published 2026-10-03 evening as
   0.1.18: 7.2.9 pinned, NVIDIA open builds against it, the fragment fixed
   for 7.2, all QEMU tests pass. The aos/kernel 7.2.9-3 package is in the
   public index and copies its modules into the slot (release 2 linked
   them into the store, which early boot cannot see). Untested on the
   stick: [TEST.md](TEST.md) step 0.
2. **CI's first real run.** `systemctl --user enable --now aos-runner`,
   then watch the v0.1.17 tag build at
   https://github.com/Jaxilian/aos/actions; fix what differs from a
   desk build. Stop the runner before a local release chain.
3. **Performance, from the baseline:** boot to login is 30 s in QEMU and
   the critical chain says where; the shell and the compositor hold 200
   and 150 MB resident at idle (llvmpipe inflates that; measure on the
   stick); the ISO is 1057 MB and the root tarball 520 MB, and
   `output/target` 2.7 GB: list what a desktop needs none of. Each a
   measured change, with perf-test.py run before and after.
4. **Steam's sandbox declaration.** It already runs in `aos-sandbox`;
   the store still says "everything, undeclared".
5. **Display arrangement** and per-display on/off in Settings → Display.
6. **A file dialog the desktop draws** for sandboxed programs, so they
   reach one chosen file outside their home.
6b. **Programs page as a list** that folds each program open, with a
   search field, as a tgn widget other pages can use.
7. **AOS's own apps in the sandbox**, once the file dialog exists.
8. **dm-verity on the root slots.** The release becomes an image, not a
   tarball: release.sh, aos-update and aos-install change. Testable in
   QEMU.
9. **LUKS-encrypted home**, unlocked at login. QEMU first, then the
   stick, which needs its data partition recreated.

The stick round ([TEST.md](TEST.md)) stays as written for whenever the
laptop is free; sound and Bluetooth wait for the target hardware.

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
