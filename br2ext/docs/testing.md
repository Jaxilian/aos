# Testing AOS

Most of this runs in QEMU. You do not need a spare machine, and you do not
need root.

Four things QEMU cannot test at all, because it does not emulate them: CPU
microcode application, frequency scaling, a real chipset watchdog, and the
GPU drivers. Those need real hardware — install AOS on a machine and work on
it over SSH, see [ssh.md](ssh.md). The first real-hardware boots found
three gaps of exactly that kind — the `xe` GPU firmware, the `iwlmld` Wi-Fi
driver, and a card reader that floods the bus with correctable PCIe errors
when it has no driver — that every QEMU run had passed over.

```sh
./br2ext/board/aos/run-qemu.sh            # live ISO, UEFI, in a window
./br2ext/board/aos/run-qemu.sh bios       # live ISO, legacy BIOS
./br2ext/board/aos/run-qemu.sh install    # live ISO + a fresh blank 8 GB disk
./br2ext/board/aos/run-qemu.sh disk       # boot what you installed
```

Log in as `root`, no password. Add `serial` as an extra word to run in the
terminal instead of a window.

## Installing to the virtual disk

```sh
./br2ext/board/aos/run-qemu.sh install
```

Then inside the VM:

```sh
aos-install /dev/vda      # type YES when asked; takes a few minutes
poweroff
```

And from the host, `run-qemu.sh disk` to boot the result.

## Checking it actually works

The point of AOS is that it compiles on itself, so that is the test:

```sh
cc --version && rustc --version
echo 'fn main(){println!("hi");}' > /tmp/t.rs && rustc /tmp/t.rs -o /tmp/t && /tmp/t
cargo new /tmp/p && cd /tmp/p && cargo build
```

That last one is the real check — it exercises rustc, cargo, gcc as the
linker, binutils and the glibc development files together.

Graphics and drivers:

```sh
ls /usr/share/glvnd/egl_vendor.d/    # mesa and nvidia both registered
ls /usr/share/vulkan/icd.d/          # intel, amd, llvmpipe, virtio, nvidia
lsmod | grep nvidia
```

Init and networking:

```sh
systemctl --failed                   # expect "0 loaded units listed"
journalctl -b -p err                 # errors from this boot, kernel included
loginctl                             # your login shows as a session with a seat
networkctl                           # the NIC should be "routable"
swapon --show                        # zram0 everywhere; /swapfile too once installed
journalctl -k | grep -i microcode    # the early initrd was found and applied
systemctl status systemd-fsck-root   # ran, on an installed disk
systemctl show -p RuntimeWatchdogUSec  # 30s where a watchdog device exists
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor   # schedutil (no cpufreq in a VM)
systemctl list-timers                # fstrim weekly
```

## Unattended runs

`boot-test.py` boots the image in QEMU with no one watching: it drives the
serial console, runs a list of checks over it, and always ends in a
screendump, because a boot can look perfect on serial while the screen stays
black.

```sh
./br2ext/board/aos/boot-test.py live      # the ISO in an optical drive
./br2ext/board/aos/boot-test.py usb       # the ISO as a USB mass-storage device
./br2ext/board/aos/boot-test.py install   # live ISO + blank disk, runs aos-install
./br2ext/board/aos/boot-test.py disk      # boot what install left behind
./br2ext/board/aos/boot-test.py desktop   # the ade session
./br2ext/board/aos/boot-test.py soak      # the session held and churned; see below
```

It writes `<mode>.serial.txt` and `<mode>.screen.png` next to the images.

For a one-off look inside a booted guest without editing the check lists,
put commands in `BOOT_TEST_EXTRA`, separated by ` ;; `; `desktop` runs them
after its own checks:

```sh
BOOT_TEST_EXTRA="lsmod | grep snd ;; su - admin -c 'XDG_RUNTIME_DIR=/run/user/1000 wpctl status'" \
  ./br2ext/board/aos/boot-test.py desktop
```

`desktop` checks the graphical session rather than the shell — necessary
because `ade.service` takes tty1, so the serial line is the only way in. It
waits for a window to reach the screen (not merely for the compositor to log
that it mapped one: under llvmpipe those are seconds apart), then presses
Super+Return and types into the terminal, both through the QEMU monitor's
`sendkey`. Going in that way is the point — the keystrokes travel the whole
path a real key does, through the emulated PS/2 controller, evdev, libinput,
xkbcommon and the compositor's binding table, none of which anything else
here exercises. It leaves three screendumps: `desktop`, `desktop-spawned`
and `desktop-typed`.

`soak` is the leak test. It holds the desktop for `SOAK_MINUTES` (20 by
default; the nightly job runs 480), and every `SOAK_INTERVAL` seconds (60)
opens a terminal and closes it, opens notepad and closes it, then prints a
row: resident set of ade-comp, ade-shell, pipewire and wireplumber, failed
units, journal errors, uptime, leftover windows. After a three-round
warmup the compositor's memory is the baseline; it fails if that grows by
more than 24 MB *and* 20% by the end, if a unit has failed, if a window
was left behind, or if uptime went backwards (the watchdog fired). A
minute's worth is `SOAK_MINUTES=2 SOAK_INTERVAL=20 boot-test.py soak`.

One thing to know when reading its output: the compositor's own log lines are
not under `journalctl -u ade`. `PAMName=login` hands the process to logind,
which moves it into a session scope, and journald files its output there.
Use `journalctl -b _COMM=ade-comp`.

## Three traps

**Never use `sudo`.** QEMU with KVM does not need root, and running as root
leaves the disk image and firmware files owned by root — after which a normal
run cannot open them. The script refuses to start as root and tells you how to
clean up.

**Use the script, or copy its QEMU flags.** AOS is built for x86-64-v2, and
QEMU's default CPU model predates SSE4.2 — the image panics inside `ld-linux`
before reaching userspace. The script passes `-cpu host` (or `Nehalem`). If
you use GNOME Boxes or virt-manager, set the CPU to host passthrough.

**Serial alone is not proof.** A boot can look perfect on the serial console
while the screen stays black. That exact bug shipped here once: without
`CONFIG_DRM_FBDEV_EMULATION` there is no framebuffer console under UEFI. To
check the screen from a script:

```sh
{ sleep 45; echo "screendump /tmp/s.ppm"; sleep 2; echo quit; } | \
  qemu-system-x86_64 -enable-kvm -m 4G -cpu host \
    -drive if=pflash,format=raw,readonly=on,file=/usr/share/edk2/ovmf/OVMF_CODE.fd \
    -drive if=pflash,format=raw,file=/tmp/vars.fd \
    -cdrom output/images/rootfs.iso9660 \
    -display none -vga std -monitor stdio -no-reboot
```

Then look at `/tmp/s.ppm`. A black screen is a few hundred bytes of solid
colour; a working console is visibly text.
