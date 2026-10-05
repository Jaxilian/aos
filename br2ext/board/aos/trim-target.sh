#!/bin/sh
#
# trim-target.sh -- what a desktop never loads, taken out of the target
# tree before the image is made (post-build.sh runs this).
#
#   trim-target.sh TARGET_DIR
#
# 1. Intel Wi-Fi firmware. linux-firmware ships every API revision of a
#    family's firmware -- 13 of iwlwifi-ty-a0-gf-a0, 230 MB in all -- and
#    the driver loads one: the highest revision it supports, counting down
#    from its UCODE_API_MAX. Per family the one file the kernel will
#    choose stays; the rest go. The ceilings are the kernel's (7.2.9,
#    drivers/net/wireless/intel/iwlwifi): JF 77, AX210 (so/ty/ma) 89,
#    GF/HR/FM/WH 100; the older chips theirs. The -cNNN files of the
#    newest families are the same idea in another spelling.
# 2. libclc's bitcode (usr/share/clc, 57 MB): OpenCL kernels for a
#    runtime nothing here has. libclang-cpp (66 MB) and diagtool: Mesa
#    needs clang to build, nothing on the target links it.
#
# Each line says what it removed; the image's size is in docs/performance.md.

set -e
T=${1:?target dir}

# --- 1. iwlwifi -------------------------------------------------------------
limit() {
	case "$1" in
		3160|7260|7265) echo 17 ;;
		3168|7265D) echo 29 ;;
		8000C|8265) echo 36 ;;
		9000-*|9260-*) echo 46 ;;
		*-jf-*) echo 77 ;;
		so-*|ty-*|ma-*) echo 89 ;;
		*) echo 100 ;;
	esac
}
FW="$T/lib/firmware/intel/iwlwifi"
if [ -d "$FW" ]; then
	before=$(du -sm "$FW" | cut -f1)
	# Families: the name without its revision suffix.
	ls "$FW" | sed -n 's/^iwlwifi-\(.*\)-c\{0,1\}[0-9]\{1,3\}\.ucode$/\1/p' | sort -u | while read -r fam; do
		max=$(limit "$fam")
		keep=""
		for f in "$FW"/iwlwifi-"$fam"-[0-9]*.ucode "$FW"/iwlwifi-"$fam"-c[0-9]*.ucode; do
			[ -f "$f" ] || continue
			n=$(echo "$f" | sed 's/.*-c\{0,1\}\([0-9]\{1,3\}\)\.ucode$/\1/')
			if [ "$n" -le "$max" ]; then
				case "$keep" in
					"") keep="$f"; kn=$n ;;
					*) if [ "$n" -gt "$kn" ]; then keep="$f"; kn=$n; fi ;;
				esac
			fi
		done
		# The newest families (fm, wh: the G14's own) come only as -cNNN
		# files, above every ceiling above, and the driver that loads
		# them (iwlmld) names no ceiling in a define; it took c106 on the
		# same hardware under Fedora's 7.2.8. The two highest c files
		# stay, so a driver one step behind still finds one.
		cs=$(ls "$FW"/iwlwifi-"$fam"-c[0-9]*.ucode 2>/dev/null | sed 's/.*-c\([0-9]*\)\.ucode$/\1/' | sort -n | tail -2 | tr '\n' ' ')
		[ -n "$keep$cs" ] || continue
		for f in "$FW"/iwlwifi-"$fam"-[0-9]*.ucode "$FW"/iwlwifi-"$fam"-c[0-9]*.ucode; do
			[ -f "$f" ] || continue
			[ "$f" = "$keep" ] && continue
			case "$f" in *-c[0-9]*.ucode)
				n=$(echo "$f" | sed 's/.*-c\([0-9]*\)\.ucode$/\1/')
				case " $cs " in *" $n "*) continue ;; esac ;;
			esac
			rm -f "$f"
		done
		echo "iwlwifi $fam: $(basename "${keep:-none}") c:[$cs]"
	done
	after=$(du -sm "$FW" | cut -f1)
	echo "trim-target: iwlwifi ${before} MB -> ${after} MB"
fi

# --- 2. OpenCL leftovers of the Mesa build ----------------------------------
for p in "$T"/usr/share/clc "$T"/usr/lib/libclang-cpp.so "$T"/usr/lib/libclang-cpp.so.* "$T"/usr/bin/diagtool "$T"/usr/lib/clang; do
	if [ -e "$p" ]; then
		echo "trim-target: ${p#"$T"/} ($(du -sm "$p" | cut -f1) MB)"
		rm -rf "$p"
	fi
done
