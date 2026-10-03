#!/bin/sh
# aos-check.sh -- run on any Linux machine: will AOS run on it?
#
#   sh aos-check.sh            prints a verdict per item, and writes
#                              ~/aos-check-<host>-<date>.txt with the
#                              details (send that file along with a bug)
#
# Needs nothing but a shell and /proc, /sys; uses lspci, lsusb and lsblk
# when they are there. No root: a few lines say "(needs root)" instead.
# What it checks is what AOS stands on (br2ext/docs/install.md and
# known-issues.md): an x86-64-v2 CPU, UEFI or BIOS with Secure Boot off,
# a GPU Mesa or NVIDIA's open modules drive, and whether this machine's
# own Linux drives its Wi-Fi, Bluetooth, sound and input -- if it does,
# AOS's kernel most likely does too.

OUT="$HOME/aos-check-$(hostname 2>/dev/null || echo host)-$(date +%Y%m%d-%H%M).txt"
ok=0; check=0; no=0

verdict() {   # verdict OK|CHECK|NO "item" "why"
	case "$1" in OK) ok=$((ok+1));; CHECK) check=$((check+1));; NO) no=$((no+1));; esac
	printf '%-5s %-14s %s\n' "$1" "$2" "$3"
	printf '%-5s %-14s %s\n' "$1" "$2" "$3" >> "$OUT"
}
section() { printf '\n== %s\n' "$1" >> "$OUT"; }
detail() { "$@" >> "$OUT" 2>&1 || true; }
have() { command -v "$1" >/dev/null 2>&1; }

: > "$OUT"
{
	echo "aos-check $(date '+%F %T') on $(hostname 2>/dev/null)"
	echo "host kernel: $(uname -r), $(grep PRETTY_NAME /etc/os-release 2>/dev/null | cut -d= -f2)"
	echo
	echo "== verdicts"
} >> "$OUT"

echo "AOS compatibility check -- details in $OUT"
echo

# --- CPU: x86-64-v2 (2009 or newer), the floor AOS is built for --------------
flags=$(grep -m1 '^flags' /proc/cpuinfo | cut -d: -f2)
model=$(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | sed 's/^ *//')
missing=""
for f in cx16 lahf_lm popcnt sse4_1 sse4_2 ssse3; do
	case " $flags " in *" $f "*) ;; *) missing="$missing $f";; esac
done
if [ "$(uname -m)" != x86_64 ]; then
	verdict NO cpu "$(uname -m): AOS is x86-64 only"
elif [ -n "$missing" ]; then
	verdict NO cpu "$model lacks$missing (x86-64-v2 is the floor)"
else
	v3=yes; for f in avx avx2 bmi1 bmi2 fma movbe; do case " $flags " in *" $f "*) ;; *) v3=no;; esac; done
	verdict OK cpu "$model ($(nproc 2>/dev/null || echo ?) threads, x86-64-v2$([ $v3 = yes ] && echo ', v3 too'))"
fi

# --- Memory and storage -------------------------------------------------------
mem=$(awk '/MemTotal/{printf "%d", $2/1024}' /proc/meminfo)
if [ "$mem" -lt 3500 ]; then verdict CHECK memory "${mem} MB: AOS wants 4 GB; it runs, swap carries the rest"
else verdict OK memory "${mem} MB"; fi
if have lsblk; then
	disks=$(lsblk -dn -o NAME,SIZE,TYPE,TRAN 2>/dev/null | awk '$3=="disk"{printf "%s %s %s; ", $1, $2, $4}')
	big=$(lsblk -dnb -o SIZE,TYPE 2>/dev/null | awk '$2=="disk" && $1>=16*1024*1024*1024{c++} END{print c+0}')
	if [ "$big" -ge 1 ]; then verdict OK disk "$disks(an install needs 16 GB)"
	else verdict CHECK disk "${disks:-none found}: an install needs a 16 GB disk"; fi
fi

# --- Firmware: UEFI or BIOS both boot; Secure Boot must be off ----------------
if [ -d /sys/firmware/efi ]; then
	sb=$(for f in /sys/firmware/efi/efivars/SecureBoot-*; do [ -f "$f" ] && od -An -tu1 -j4 -N1 "$f" 2>/dev/null; done | tr -d ' ')
	case "$sb" in
		1) verdict NO firmware "UEFI with Secure Boot ON: turn it off in the firmware setup; AOS signs nothing for it" ;;
		0) verdict OK firmware "UEFI, Secure Boot off" ;;
		*) verdict CHECK firmware "UEFI; Secure Boot state unreadable (needs root?) -- it must be off" ;;
	esac
else
	verdict OK firmware "BIOS (legacy boot); the ISO boots that way too"
fi
[ -d /sys/class/tpm/tpm0 ] && verdict OK tpm "present (not used yet; disk encryption will)" || verdict OK tpm "none (not needed)"

# --- GPU: Mesa for Intel and AMD; NVIDIA RTX 20 series and newer --------------
gpu_seen=0
if have lspci; then
	lspci -nn 2>/dev/null | grep -Ei 'VGA|3D controller|Display controller' | while IFS= read -r line; do
		id=$(echo "$line" | grep -oE '\[[0-9a-f]{4}:[0-9a-f]{4}\]' | tail -1 | tr -d '[]')
		vendor=${id%%:*}; dev=${id##*:}
		name=$(echo "$line" | sed 's/^[^ ]* //; s/ \[[0-9a-f:]*\].*//')
		case "$vendor" in
			8086) verdict OK gpu "Intel: $name (Mesa)" ;;
			1002) verdict OK gpu "AMD: $name (Mesa)" ;;
			10de)
				if [ "$((0x$dev))" -ge "$((0x1e00))" ]; then verdict OK gpu "NVIDIA: $name (RTX 20 or newer: the open modules)"
				else verdict NO gpu "NVIDIA: $name is older than the RTX 20 series; AOS has no driver for it (a second, Intel or AMD GPU would do)"; fi ;;
			*) verdict CHECK gpu "$name [$id]: not Intel, AMD or NVIDIA" ;;
		esac
	done
	[ "$(lspci -nn 2>/dev/null | grep -Eic 'VGA|3D controller|Display controller')" -eq 0 ] && verdict CHECK gpu "lspci lists no display controller"
else
	for c in /sys/class/drm/card[0-9]; do
		[ -e "$c/device/vendor" ] || continue
		v=$(cat "$c/device/vendor"); d=$(cat "$c/device/device")
		case "$v" in 0x8086) verdict OK gpu "Intel $d (Mesa)";; 0x1002) verdict OK gpu "AMD $d (Mesa)";;
			0x10de) [ "$((d))" -ge "$((0x1e00))" ] && verdict OK gpu "NVIDIA $d (open modules)" || verdict NO gpu "NVIDIA $d: older than RTX 20";;
			*) verdict CHECK gpu "$v:$d";; esac
	done
fi
# Displays connected now, and the panel's size: AOS scales from it.
for c in /sys/class/drm/card*-*; do
	[ -f "$c/status" ] || continue
	st=$(cat "$c/status"); [ "$st" = connected ] || continue
	mode=$(head -1 "$c/modes" 2>/dev/null)
	verdict OK display "$(basename "$c" | sed 's/^card[0-9]*-//') $mode"
done

# --- Network, Bluetooth, sound, input: what the host's Linux drives -----------
drv() {   # the driver the host uses for a PCI device line from lspci -k
	echo "$1" | sed -n 's/.*Kernel driver in use: //p'
}
if have lspci; then
	lspci -k 2>/dev/null | awk '/^[0-9a-f]/{dev=$0} /Kernel driver in use/{print dev " ;; " $0}' | while IFS= read -r pair; do
		dev=${pair%% ;; *}; d=$(echo "$pair" | sed 's/.*Kernel driver in use: //')
		case "$dev" in
			*"Network controller"*|*"Ethernet controller"*)
				verdict OK network "$(echo "$dev" | sed 's/^[^ ]* //') -- $d" ;;
			*"Audio device"*|*"Multimedia audio"*)
				verdict OK sound "$(echo "$dev" | sed 's/^[^ ]* //') -- $d" ;;
		esac
	done
	lspci -k 2>/dev/null | awk '/^[0-9a-f]/{dev=$0; drv=0} /Kernel driver in use/{drv=1} /^$/{if(dev && !drv && (dev ~ /Network|Ethernet|Audio|Multimedia/)) print dev; dev=""}' | while IFS= read -r dev; do
		[ -n "$dev" ] && verdict CHECK driver "no driver on this Linux for: $(echo "$dev" | sed 's/^[^ ]* //')"
	done
fi
if [ -d /sys/class/bluetooth ] && [ -n "$(ls /sys/class/bluetooth 2>/dev/null)" ]; then
	bt=$(ls /sys/class/bluetooth | head -1)
	btdrv=$(basename "$(readlink -f /sys/class/bluetooth/$bt/device/driver 2>/dev/null)" 2>/dev/null)
	verdict OK bluetooth "$bt -- ${btdrv:-?} (the Bluetooth page is still being worked on in AOS)"
else
	verdict CHECK bluetooth "no adapter seen by this Linux"
fi
if [ -f /proc/asound/cards ] && grep -q '^ *[0-9]' /proc/asound/cards; then
	cards=$(grep '^ *[0-9]' /proc/asound/cards | sed 's/^ *[0-9]* *\[[^]]*\]: *//' | tr '\n' ';')
	case "$cards" in *soundwire*|*sof*) verdict CHECK sound "$cards-- a SoundWire/SOF card: AOS has the firmware; speakers depend on the kernel's codec match" ;;
		*) verdict OK sound "$cards" ;; esac
else
	verdict CHECK sound "no sound card seen by this Linux"
fi
tp=$(grep -iE '^N: Name=.*(touchpad|trackpad|synaptics|elan|glidepoint)' /proc/bus/input/devices 2>/dev/null | head -1 | cut -d= -f2-)
[ -n "$tp" ] && verdict OK touchpad "$tp (libinput)" || verdict OK input "no touchpad seen (a desktop, or a mouse)"
for b in /sys/class/power_supply/BAT*; do [ -d "$b" ] && verdict OK battery "$(basename "$b") $(cat "$b/capacity" 2>/dev/null)% (suspend and lid are tested on one laptop so far)"; done
if have lsusb; then
	wifi_usb=$(lsusb 2>/dev/null | grep -iE 'wireless|wlan|802.11|bluetooth' | head -3 | sed 's/^Bus [0-9]* Device [0-9]*: ID //')
	[ -n "$wifi_usb" ] && verdict CHECK usb-radio "USB radio(s): $wifi_usb -- firmware for these is checked per chip"
fi

# --- Details for a bug report -------------------------------------------------
section "cpu";      detail sh -c "grep -m1 'model name' /proc/cpuinfo; grep -m1 '^flags' /proc/cpuinfo | tr ' ' '\n' | grep -E '^(sse4_2|popcnt|avx2?|cx16|lahf_lm|ssse3|bmi[12]|fma|movbe)$' | tr '\n' ' '; echo"
section "memory";   detail head -3 /proc/meminfo
section "firmware"; detail sh -c "ls /sys/firmware/efi >/dev/null 2>&1 && echo UEFI || echo BIOS; cat /sys/class/dmi/id/sys_vendor /sys/class/dmi/id/product_name /sys/class/dmi/id/bios_version 2>/dev/null"
section "pci";      detail sh -c "lspci -nnk 2>/dev/null || ls /sys/bus/pci/devices"
section "usb";      detail sh -c "lsusb 2>/dev/null || ls /sys/bus/usb/devices"
section "drm";      detail sh -c 'for c in /sys/class/drm/card*-*; do echo "$c $(cat $c/status 2>/dev/null) $(head -1 $c/modes 2>/dev/null)"; done'
section "sound";    detail sh -c "cat /proc/asound/cards; ls /proc/asound 2>/dev/null"
section "input";    detail grep -E '^N: Name=' /proc/bus/input/devices
section "block";    detail sh -c "lsblk -o NAME,SIZE,TYPE,FSTYPE,TRAN,MODEL 2>/dev/null"
section "modules";  detail sh -c "lsmod 2>/dev/null | awk 'NR>1{print \$1}' | tr '\n' ' '; echo"
section "firmware files the host loaded"; detail sh -c "dmesg 2>/dev/null | grep -iE 'firmware|microcode' | head -20 || echo '(needs root)'"

echo
echo "$ok ok, $check to check, $no no.  Details: $OUT"
[ "$no" -eq 0 ] && echo "Nothing here stops AOS from running on this machine." || echo "A NO above stops AOS; see br2ext/docs/known-issues.md."
