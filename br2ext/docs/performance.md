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
| 0.1.29 (keyed build: sshd on) | 1.18 s + 4.08 s = 5.26 s | sshd.service @3.11 s | 0.23 s, 0.21 s, 0.21 s | 3471 MB; ade-shell 197 MB, ade-comp 153 MB | 955 MB | 491 MB |
| 0.1.30 (keyed) | 1.17 s + 3.34 s = 4.51 s | polkit.service @2.28 s | 0.15 s, 0.18 s, 0.14 s | the same | 955 MB | 491 MB |

0.1.29 against 0.1.17: the ISO lost 100 MB and the tarball 30 MB to the
firmware and OpenCL trim; userspace boot grew by 1.9 s, of which
zram-setup 1.74 s (it was 1.06 s), resolved 1.6 s, networkd 1.2 s and
sshd 0.97 s (a keyed test build only). QEMU's start to the login prompt
went from 29 s to 19 s with GRUB's menu at 2 s.

0.1.30: zram out of the boot's critical chain and the journal persistent
from the first line (below) take 0.75 s off userspace in QEMU and, by
the G14's report, about 4 s off the desktop's start on a USB stick.

## The G14 (0.1.19, report of 2026-10-05, booted from the USB stick)

Firmware 12.8 s, GRUB 1.9 s, kernel 3.0 s, userspace 6.1 s. Of the
userspace: systemd-journal-flush 4.46 s (copying the runtime journal to
the stick, inside sysinit.target: the desktop waited for it), the two
partitions 2.0 s each (USB enumeration), zram-setup 1.46 s (on the way
to swap.target, which sysinit wants), udevd 1.0 s, nvidia-devices 0.95 s.
Memory: settings 168 MB, aos-store 164 MB, notepad 153 MB, ade-shell
140 MB, ade-comp 117 MB, journald 52 MB -- with every program on the
NVIDIA GPU, which 0.1.28 ended; the next report says what the Intel
GPU's numbers are.

Done in 0.1.30: `Storage=persistent` in journald.conf.d (there is no
runtime journal to flush: /var is mounted before systemd by our init),
and zram as a oneshot after ade.service instead of a swap unit under
swap.target. Next: resolved takes 1.4 s on the live ISO (95 ms on an
installed disk), nvidia-devices 0.95 s on the G14 could start after the
desktop, and the memory of a tgn program on the Intel GPU is to be
measured before anything is done about it. What QEMU says about that
memory (smaps of 0.1.30): Notepad's 92 MB resident is 42 MB of libLLVM
and 7 MB of lavapipe (the software Vulkan driver), 21 MB of its own heap,
10 MB shared; the shell's 192 MB is 95 MB of the driver's buffer
allocations (memfd) and 45 MB of libLLVM. A real driver has neither, so
the G14's numbers with every program on the Intel GPU (0.1.28) are the
ones to act on; the font atlas is 4 MB (2048 squared, one byte per
pixel) and is not where the memory goes.

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
