# Testing AOS

Everything runs in QEMU. You do not need a spare machine, and you do not need
root.

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

## One expected message

On the live ISO you will see:

```
mount: /: cannot remount /dev/root read-write, is write-protected
```

That is normal. BusyBox init tries to remount the root read-write, which
cannot work on a read-only ISO. `/var` is made writable separately. It does
not appear on an installed system.
