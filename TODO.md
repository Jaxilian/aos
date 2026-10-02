# TODO -- needs hardware or a person

Everything here has been built and tested in QEMU only, or needs a
machine Claude cannot reach. Written 2026-10-02; the stick is on 0.1.9,
the next release is 0.1.10 (per-display scale, GPU names, the store's
icons and its own icon, the terminal's right-click Copy, the report in
the home directory).

## On the G14 (next stick round)

1. **Update the stick**: `sudo aos-update` in a terminal, restart. The
   stick's Settings button should work too now (0.1.9 has apm v0.1.6).
2. **XWayland**: Settings -> Software -> Compatibility, toggle on. The
   two attempts in the stick's journal were on the old version (the flag
   bug); none was made on 0.1.9. If it still fails, note what the page
   says, and try `sudo apm --yes --quiet install runtime/xwayland`.
3. **Bluetooth** (parked): Settings -> Bluetooth. The adapter is up in
   the 0.1.9 journal (btintel_pcie, firmware loaded, rfkill clear,
   bluetoothd running) and no power-on or scan was ever sent, so say
   what the page shows. `bluetoothctl show` in a terminal, as the user,
   tells whether Settings can see the controller at all.
4. **Sound**: play something, try each output in Settings -> Sound.
5. **The installer**: Super -> Install AOS. Walk the pages; only press
   Install with a spare disk to erase. Check the stick itself is not
   offered.
6. **Crash recovery**: `pkill -ABRT -x ade-shell` (bar comes back),
   `sudo pkill -ABRT -x ade-comp` while locked (comes back locked, toast).
7. **Suspend / lid close** -- never tested on hardware.
8. **The ISO from the boot menu**: write the ISO to a second stick with
   dd (docs/install.md) and see whether the G14's boot menu lists it.
9. **Scale with two displays**: Settings -> Display now has a Scale
   section per display. Pick 125% for eDP-1 and Automatic for the
   monitor; both should follow within seconds.
10. Still owed from before: Firefox fonts, NVIDIA under a game, the
   clock after a time-zone change, crisp windows at 200%.

When done: Settings -> About -> Save Report (it lands in the home
directory now), notes in ~/issues.md, mount the stick here.

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
