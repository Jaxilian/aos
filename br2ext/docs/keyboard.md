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

`systemd-vconsole-setup` reads that file at every boot.

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

**This is the text console only.** The desktop does its own keyboard
handling through libxkbcommon and ignores `/etc/vconsole.conf` entirely;
`loadkeys` run from a terminal window fails ("Couldn't get a file
descriptor referring to the console") because it wants a text console, and
it would not change the desktop anyway. The desktop's layout comes from
XKB's environment variables, which ade reads from `/etc/ade/environment`:

```sh
XKB_DEFAULT_LAYOUT=se
```

Log out and in (or reboot) for it to take. XKB names differ from console
ones: Swedish is `se`, Norwegian `no`, Danish `dk`, Finnish `fi`, German
`de`, French `fr`, UK `gb`; variants go in `XKB_DEFAULT_VARIANT`, e.g.
`dvorak`. Until the Settings application exists, this file is the
setting.

**Serial consoles are unaffected.** Key translation there happens in your
terminal emulator, not in AOS, so the setting does nothing for a login on
`console=ttyS0`.

## Why kbd is installed

`systemd-vconsole-setup` does not load keymaps itself: it runs `loadkeys`,
and the keymap files have to come from somewhere. Without the `kbd` package
the console is stuck on the kernel's built-in US layout with no way to select
another. `kbd` provides `loadkeys` and the keymap files for every common
layout, for a few MB.
