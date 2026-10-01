# TODO -- needs hardware or a person

Everything here has been built and tested in QEMU only, or needs a
machine Claude cannot reach. Written 2026-10-01; the stick is on 0.1.3,
the latest release is 0.1.6.

## On the G14 (next stick round)

1. **Update the stick**: Settings -> Software -> Install (or
   `sudo apm upgrade`). It should go 0.1.3 -> latest without the
   `umount` workaround.
2. **Sound** (parked): play something, try each output in Settings ->
   Sound. Then Settings -> About -> Save Report and
   `cp /tmp/aos-report-*.tar.gz ~/` -- the report now has WirePlumber's
   view, the mixer and the UCM profile.
3. **Bluetooth** (parked): Settings -> Bluetooth, power on, scan. Same
   report covers it (hci0, rfkill, bluetoothctl as the user).
4. **The installer**: Super -> Install AOS. Walk the pages; only press
   Install with a spare disk to erase. Check the stick itself is not
   offered.
5. **Crash recovery**: `pkill -ABRT -x ade-shell` (bar comes back),
   `sudo pkill -ABRT -x ade-comp` while locked (comes back locked, toast).
6. **The app store**: Super -> Software. Install and remove something
   small (aos/images).
7. **Suspend / lid close** -- never tested on hardware.
8. **Brightness slider** in the quick panel (the `video` group: the
   stick's admin predates it; `sudo usermod -aG video admin`, log in again).
9. **Glass**: the desktop should look frosted behind the terminal and
   the panels. Settings -> Display -> Appearance -> Light should make
   everything opaque within seconds (the compositor) and for apps
   started after. Watch the GPU: if the glass makes the desktop sluggish
   on the Intel GPU, say so -- light is the fallback, and the default
   could flip.
10. Still owed from before: Firefox fonts, NVIDIA under a game, the
   clock after a time-zone change, crisp windows at 200%.

## Infrastructure

- **CI runner**: register a self-hosted GitHub runner with the label
  `kvm` on a machine with /dev/kvm; `.github/workflows/aos.yml` and
  `br2ext/board/aos/ci.sh` are ready.
- **More test machines**: an Intel laptop, an AMD APU, an NVIDIA
  desktop, a ~2012 machine (the x86-64-v2 floor). Per machine: boot,
  graphics, Wi-Fi, suspend, audio, touchpad.

## Decisions waiting

- btrfs for `aos-data` (snapshots) -- ext4 until a feature needs it.
- First-boot setup for preinstalled hardware (roadmap Phase 4, item 2).
