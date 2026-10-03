# Performance

One row per release, measured the same way every time, so a change is a
number and not an impression. `br2ext/board/aos/perf-test.py` boots the
live ISO in QEMU (four cores, 4 GB, llvmpipe for the GPU) and writes
`output/images/perf.json`; the boot figures come from systemd's own clock
inside the guest, a program's first window from the compositor's journal
("toplevel mapped") against the launch time, memory from `/proc`.

QEMU numbers are QEMU numbers: good for comparing releases, not for a
laptop. The G14's `aos-report` carries the same boot chain
(`analyze-chain`, `analyze-blame`) and the biggest processes
(`memory-top`) for the hardware side.

## Baseline

| Release | Boot (kernel + userspace) | Critical chain ends | Terminal, notepad, files first window | Memory at idle | ISO | Root tarball |
|---|---|---|---|---|---|---|
| 0.1.17 | 0.91 s + 2.16 s = 3.07 s | polkit.service @1.58 s | 0.13 s, 0.12 s, 0.12 s | 3473 MB free of 4 GB; ade-shell 196 MB, ade-comp 152 MB, wireplumber 19 MB | 1057 MB | 520 MB |

From QEMU's start to the login prompt is 29 s and to the first frame on
screen 38 s, but that is the firmware, the 5 s GRUB menu, loading the
kernel from an emulated CD, and llvmpipe's first frame; the OS itself is
the 3 s. The slowest units at boot: zram-setup 1.06 s, systemd-resolved
1.03 s, the CD device 0.83 s, systemd-networkd 0.76 s, polkit 0.46 s,
nftables 0.37 s.

## What the baseline says to do

- **zram-setup and resolved** are a third of userspace boot between
  them; neither should be on the critical chain of the desktop.
- **The shell at 196 MB and the compositor at 152 MB** are mostly
  lavapipe and llvmpipe buffers in QEMU; the number that matters is the
  G14's, from `memory-top` in its report, before anything is done about
  it.
- **1057 MB of ISO and 2.7 GB of `output/target`** hold things a desktop
  never runs; `docs/packages.md` lists them. Smaller images update
  faster: 520 MB per release over Wi-Fi is what a person waits for.
- **First windows at 0.12 s** are where they should be; keep the test
  so a regression shows.
