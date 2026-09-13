#!/bin/sh
# Build AOS and install it onto a USB stick. Run as yourself, not sudo.
#
#   ./usb.sh                 build, pick the stick, install, verify
#   ./usb.sh /dev/sdX        onto that stick
#   ./usb.sh --no-build      skip make
#   ./usb.sh --test          then boot the stick in QEMU to prove it
#   ./usb.sh --release       your own account instead of the demo one
#
# This file is only a front door: the repository root is an unmodified
# Buildroot checkout, and everything AOS lives under br2ext/ so that pulling
# Buildroot never conflicts with it. The pipeline is br2ext/board/aos/make-usb.sh.
exec "$(dirname "$0")/br2ext/board/aos/make-usb.sh" "$@"
