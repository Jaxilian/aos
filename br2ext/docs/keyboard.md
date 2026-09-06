# Keyboard layout

AOS ships the **US** layout by default, because it has to ship something.
Changing it is one line.

## Change it for good

Edit `/etc/vconsole.conf` on the running system:

```sh
KEYMAP=sv-latin1
```

Reboot, or apply it straight away without one:

```sh
loadkeys sv-latin1
```

`/etc/init.d/S20keymap` reads that file at every boot.

## Finding your layout

```sh
ls /usr/share/keymaps/i386/*/
```

| Layout | Name |
|---|---|
| Swedish | `sv-latin1` |
| Norwegian | `no-latin1` |
| Danish | `dk-latin1` |
| Finnish | `fi` |
| German | `de-latin1` |
| French | `fr` |
| Spanish | `es` |
| UK | `uk` |
| Dvorak / Colemak | `dvorak` / `colemak` |

## Building an image that defaults to your layout

Edit the shipped file rather than the running one, then rebuild:

```
br2ext/board/aos/rootfs-overlay/etc/vconsole.conf
```

## Two things worth knowing

**This is the text console only.** A Wayland compositor does its own keyboard
handling through libxkbcommon and ignores `/etc/vconsole.conf` entirely. If
you write one, note that AOS does not currently ship libxkbcommon or the XKB
keyboard data — Buildroot has `libxkbcommon` but not `xkeyboard-config`, so
you will need to supply the layout data yourself.

**Serial consoles are unaffected.** Key translation there happens in your
terminal emulator, not in AOS, so `S20keymap` does nothing when you boot with
`console=ttyS0`.

## Why kbd is installed

BusyBox has a `loadkmap` applet, and it is on the image, but it reads only a
pre-compiled binary keymap and BusyBox ships no keymap data at all. Without
the `kbd` package the console is stuck on the kernel's built-in US layout with
no way to select another. `kbd` provides real `loadkeys` and the keymap files
for every common layout, for a few MB.
