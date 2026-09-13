# Making a USB stick that actually boots

This is the short version, then the long version, then everything that went
wrong the first time so it does not go wrong again. Every rule below is
there because it was broken once.

## The short version

```sh
./usb.sh            # build, pick the stick, install AOS onto it, verify it
```

Run it as yourself. It lists the sticks it can see and picks the only one
(or asks which), asks once for `YES`, asks once for your password, runs
`make`, refuses to go on if the image has no SSH key for root, then boots
the live ISO in QEMU with the stick attached and types the install for you.
Ten minutes, most of it the build and the copy; the guest's transcript is
in `output/images/usb-install.txt`. `./usb.sh --no-build` skips the make,
`./usb.sh --test` boots the finished stick in QEMU afterwards as proof, and
`./usb.sh /dev/sdX` names the stick instead of being asked.

Then: stick into a **USB-A port on the machine itself**, machine fully **off**,
power on, open the **one-time boot menu** (Esc or F8 on ASUS, F12 on most
others), choose the **UEFI** entry for the stick.

That is the whole procedure. It is the only one that has booted on real
hardware here, and it produces a full, writable AOS install on the stick —
which is what you want for a machine you SSH into.

The same by hand, which is what `usb.sh` does for you and what the rest of
this page walks through:

```sh
make                                                  # the image must be current
sudo ./br2ext/board/aos/write-usb.sh                  # lists your stick's device name
sudo ./br2ext/board/aos/write-usb.sh /dev/sdX --install   # X = the letter it printed
```

In the QEMU window that opens: log in as `root`, then

```
aos-install /dev/vda
poweroff
```

(`--install --auto` is the middle ground: the same command, with
`auto-install.py` typing those two lines instead of you.)

**Do not `dd` the ISO to the stick expecting it to boot.** See "Why not the
live ISO" below.

## The long version, with what each step looks like

### 1. Build first

`write-usb.sh` writes `output/images/rootfs.iso9660`. If you changed
anything, run `make` first, or you install the previous image and wonder why
the fix is not there. `post-build.sh` prints one line at the end you should
read every time:

```
post-build.sh: installed 1 SSH key(s) for root
```

If it says `no board/aos/authorized_keys -- SSH will accept no logins`,
you will boot a machine you cannot log into remotely. Fix that before writing
the stick, not after. See [ssh.md](ssh.md).

### 2. Find the stick — and make sure the host actually sees it

```sh
sudo ./br2ext/board/aos/write-usb.sh
```

With no arguments it refuses and lists removable USB disks:

```
Removable USB disks currently attached:
  /dev/sda  29358 MiB   SanDisk 3.2Gen1
```

Rules from experience:

- **`sdX` is a placeholder.** Type the real letter. The script rejects
  `/dev/sdX` — that has been typed literally.
- **If it lists none, the stick is not attached**, whatever the physical
  situation looks like. `Problem opening /dev/sda ... The specified file does
  not exist` from any tool means the same thing. This stick has needed to be
  pulled out and pushed back in before the host would enumerate it, with no
  error anywhere. Re-seat it and run the listing again.
- The script only accepts a **removable, USB, whole disk**. It refuses the
  NVMe and it refuses partitions (`/dev/sda1`). That is deliberate: a typo
  here is your own filesystem.

### 3. Write it

```sh
sudo ./br2ext/board/aos/write-usb.sh /dev/sda --install
```

- It needs `sudo`; writing a block device does. (`run-qemu.sh` must **not**
  be run with sudo. Different tools, different rules.)
- It shows what it is about to erase and asks for `YES` — **capitals**.
  `yes` aborts. That has happened.
- It unmounts anything the desktop auto-mounted from the stick. You do not
  have to.

Then QEMU boots the live ISO with the stick attached as a disk. You will see
GRUB's menu, the kernel log, and:

```
aos login:
```

### 4. Inside the VM: two commands, exactly these

```
root
aos-install /dev/vda
```

- **It is `/dev/vda` inside the VM**, always. The stick is `/dev/sda` on the
  host and `/dev/vda` in the guest; the guest never sees a `/dev/sda`.
  Typing the host command (`/dev/sda --install`) into the guest gives
  `-bash: /dev/sda: No such file or directory`. That has happened too.
- It asks for `YES` again. Capitals.
- What follows, and how long:

  ```
  >>> Wiping old partition tables and signatures from /dev/vda
  >>> Partitioning /dev/vda
  >>> Creating filesystems
  ```
  A `Cannot initialize conversion from codepage 850` message from
  `mkfs.fat` here is harmless — no locale tables on the image; it uses its
  built-in one.
  ```
  >>> Copying system (this takes a while)          ~2 minutes on USB
  >>> Creating swap file
      3924 MiB at /swapfile                        2-3 minutes, no progress shown
  >>> Writing /etc/fstab
  >>> Installing bootloader
  Installing for x86_64-efi platform.
  Installation finished. No error reported.
  Installing for i386-pc platform.
  Installation finished. No error reported.
  >>> Writing grub.cfg
  >>> Unmounting
  AOS installed on /dev/vda. Remove the install media and reboot.
  ```
  The swap step is silent and slow. It has not hung. Kernel lines like
  `clocksource: Watchdog remote CPU 1 read timed out` are QEMU noise.

- **Both "Installation finished" lines must be there.** If the `i386-pc`
  one says `multiple partition labels` or `will not proceed with
  blocklists`, the disk still carried an old identity when it was
  partitioned. The wipe step above exists precisely to prevent that; if you
  see it anyway, the image you are running is older than the wipe. Rebuild.

Then:

```
poweroff
```

QEMU exits on its own. The script re-reads the stick and prints its layout;
what you want to see:

```
NAME    SIZE PARTLABEL PARTTYPENAME     FSTYPE LABEL
sda    28.7G
├─sda1    1M bios_grub BIOS boot
├─sda2  512M ESP       EFI System       vfat   AOS_ESP
└─sda3 28.2G root      Linux filesystem ext4   aos
>>> EFI system partition /dev/sda2 is FAT32    with:
bootx64  efi ...
Done. /dev/sda is ready.
```

If the top line shows `FSTYPE iso9660 LABEL ISOIMAGE` for the whole disk,
that is stale cache from an earlier live-ISO write: `sudo partx -u /dev/sda`
refreshes it. On an image with the wipe step it should not appear at all.

### 5. Boot the machine

In this order, because each has cost a reboot:

1. **Power the machine off completely.** Not a restart. Some firmware only
   enumerates USB at cold boot.
2. **Insert the stick before pressing power**, in a **USB-A port on the
   chassis** — not a hub, dock, or USB-C/Thunderbolt port, which many
   laptops cannot boot from at all.
3. Open the **one-time boot menu** at power-on, not the boot-order page in
   setup. The saved boot order lists configured entries; removable media
   appear in the one-time menu.
4. Pick the entry that names the stick, the **UEFI** one if the firmware
   offers both.
5. At GRUB, the first entry is right. `AOS (safe graphics, no GPU driver)`
   is for when the screen goes black after boot — see below.

Firmware settings that must be right, checked once per machine:

- **Secure Boot off.** The loader is unsigned. Secure Boot usually lists
  the stick and then refuses it, so this is not the "not listed" symptom,
  but it stops the boot all the same.
- **Fast Boot off.** It skips USB enumeration on some boards.

### 6. If the stick is not in the boot menu at all

That happened five times here before it worked. The order to check:

1. Is it the `--install` layout, not a `dd` of the ISO? If it is the ISO,
   stop and use `--install`. See below.
2. Did both bootloaders install (step 4)? If not, rebuild and reinstall.
3. Cold boot, chassis USB-A port, one-time menu (step 5). Try the other
   USB-A port.
4. Prove the stick on the host, without a reboot:

   ```sh
   sudo ./br2ext/board/aos/write-usb.sh /dev/sda --boot
   ```

   This boots the physical stick in QEMU behind the same UEFI firmware a PC
   uses, with the guest's writes diverted to a snapshot so the stick is not
   changed. A login prompt means the stick is good and the machine's
   firmware is the difference; no login prompt means the stick, and the
   serial output on your terminal says what broke. (`--boot --auto` makes
   the same check with no one watching and reports it in the exit status;
   `./usb.sh --test` runs it for you after installing.)

   Not `--test`: that mode writes the live ISO to the stick first and then
   boots it. It is the ISO's check, and on an installed stick it erases the
   install.

## Why not the live ISO

Writing `rootfs.iso9660` to a stick with `dd` is the obvious thing, and it is
what every distribution's instructions say. It boots from a stick under
QEMU's UEFI. **On the ASUS ROG Zephyrus G14 used here (AMI Aptio, BIOS 305)
it has never once appeared in the boot menu**, across every fix that was
tried: a real GPT with the EFI system partition as a partition, a FAT16
ESP instead of the FAT12 Buildroot makes, the backup GPT moved to the end of
the stick, a 128-entry partition table. Same port, same stick, same firmware
settings under which a Fedora live stick boots. The cause was never found.

A `--install` stick is a plain GPT disk with a FAT32 EFI system partition at
the front — the same shape as the Fedora install on this laptop's own NVMe,
which the firmware boots every day. That is why it works where the ISO
does not, and why it is the documented route. The ISO remains right for
optical media and for QEMU. The mechanics of what the ISO needs to be
USB-bootable at all are in [PLATFORM.md](../PLATFORM.md), "USB booting".

## After it boots: the three things that bit on real hardware

None of these show in QEMU. All three are fixed in the image now; the
entries here are so you recognise them if they come back in another form.

**Screen goes black a few seconds after GRUB.** A GPU driver bound, evicted
the firmware framebuffer, and then failed — here because the `xe/` firmware
for the Intel Panther Lake iGPU was not on the image. Reboot, pick
`AOS (safe graphics, no GPU driver)`, log in, and read the previous boot:

```sh
journalctl -b -1 -k --no-pager | grep -iE 'xe|i915|nvidia|drm|firmware'
```

Blind, with no console: the **power button once** is a clean poweroff,
**Ctrl+Alt+Del** a clean reboot. There is **no `sudo` on AOS** — you are
root — so `sudo shutdown now` typed blind does nothing; `poweroff` does.

**Console floods with `PCIe Bus Error: severity=Correctable ... Timeout`
and shutdown seems stuck.** A PCIe device with no driver, not sleeping,
flapping its link tens of thousands of times a second — here the Realtek
card reader before `rtsx_pci` was added. If a new device does this, the
line names it (`device [10ec:525a]`); the fix is its driver, not silencing
the message. The screen entries now run at `loglevel=4`, so warnings go to
the journal and only errors reach the console.

**No network.** A USB-C Ethernet adapter gets DHCP with no setup. Wi-Fi
needs credentials once — the recipe is in [ssh.md](ssh.md). If neither
interface exists at all (`ip link`), it is a missing driver, and it was
here: the Wi-Fi 7 chip needed `iwlmld`, the USB adapter needed the usbnet
drivers, neither of which the kernel had.

## Reinstalling

Running `--install` on a stick that already has AOS is fine and is the
normal way to get a new image onto it. The installer scrubs the disk first:
`wipefs -a`, then the first and last 2 MiB zeroed. That step exists because
a stick that has been a Fedora ISO, then an AOS ISO, then two installs kept
the ISO's volume descriptor at sector 64 through all of it — `parted` and
`mkfs` never touch that sector — until GRUB refused the disk as having two
partition tables and the firmware stopped listing it. Two identities on one
disk; every tool that guesses which one it is looking at can guess wrong.

## The mistakes, in the order they were made

| What happened | The rule |
|---|---|
| ISO `dd`'d to the stick, not bootable: no partition table at all | The ISO is a hybrid now, but use `--install` for real machines |
| Hybrid ISO not listed: FAT12 ESP, backup GPT in the wrong place, 248 GPT entries — all fixed, still not listed | Stop fighting one firmware's ISO handling; a real GPT disk is what it boots |
| `sgdisk: /dev/sda does not exist` | The stick was not attached. Re-seat it; listing first |
| `/dev/sdX is not a block device` | X is a placeholder |
| `Type YES to continue: yes` → `Aborted.` | Capitals |
| `-bash: /dev/sda: No such file or directory` inside the VM | Inside the VM it is `aos-install /dev/vda` |
| Booted, then black screen; `sudo shutdown now` blind did nothing | `xe/` firmware missing; no `sudo` on AOS; power button or Ctrl+Alt+Del |
| Console flooded with correctable PCIe errors | Card reader had no driver; every PCIe device needs one even if unused |
| BIOS loader refused a reinstalled stick; firmware stopped listing it | Stale ISO signature at sector 64; the installer now scrubs first |
| Two fixes rebuilt, stick still had the old image | `make` before `write-usb.sh`, and read post-build's last line — or `./usb.sh`, which does both |
| Unattended install driven through QEMU's stdin on a pty died at GRUB | Drive the guest over a serial socket, as `boot-test.py` and `auto-install.py` do |
