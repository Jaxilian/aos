#!/usr/bin/env python3
"""Post-process the GPT that xorriso put in the live ISO, then verify it.

    iso-gpt.py <rootfs.iso9660> <expected PARTUUID of partition 1>

Two jobs, run by a ROOTFS_ISO9660_POST_GEN hook in br2ext/external.mk:

1. Normalise the partition entry count to 128.

   xorriso sizes the entry array to fill the space in front of the first
   partition: with -partition_offset 16 that is LBAs 2..63, which is 248
   entries. The UEFI spec makes 128 the minimum and every partitioning tool
   writes exactly that, and some firmware -- AMI Aptio is the usual
   suspect -- treats anything else as an invalid table. An invalid table
   means no EFI system partition, which means the stick never appears in
   the boot menu. Only the first three entries are ever used, so cutting
   the array to 128 loses nothing; the header CRC and the array CRC are
   recomputed, for the primary and the backup header both.

2. Confirm partition 1 carries the PARTUUID the boot menu names.

   The menu's root=PARTUUID= is fixed before the image exists, from a
   pinned disk GUID (--gpt_disk_guid) and xorriso's undocumented rule for
   deriving partition GUIDs. If that rule ever changes, this is what turns
   a silently unbootable ISO into a failed build.
"""

import struct
import sys
import uuid
import zlib

SECTOR = 512
HDR_FMT = "<8sIIII QQQQ 16s QIII"
STD_ENTRIES = 128


def read_header(f, lba):
    f.seek(lba * SECTOR)
    raw = f.read(92)
    fields = struct.unpack(HDR_FMT, raw)
    if fields[0] != b"EFI PART":
        sys.exit("iso-gpt: no GPT header at LBA %d" % lba)
    return list(fields)


def write_header(f, lba, fields, entries_blob):
    # fields: sig rev hdrsize hdrcrc reserved mylba altlba first last guid
    #         entlba nent entsize arrcrc
    fields[13] = zlib.crc32(entries_blob) & 0xffffffff
    fields[3] = 0
    raw = struct.pack(HDR_FMT, *fields)
    fields[3] = zlib.crc32(raw) & 0xffffffff
    raw = struct.pack(HDR_FMT, *fields)
    f.seek(lba * SECTOR)
    f.write(raw + b"\x00" * (SECTOR - len(raw)))


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    path, want = sys.argv[1], sys.argv[2].lower()

    with open(path, "r+b") as f:
        prim = read_header(f, 1)
        n_ent, ent_size = prim[11], prim[12]
        if ent_size != 128:
            sys.exit("iso-gpt: unexpected entry size %d" % ent_size)

        f.seek(prim[10] * SECTOR)
        entries = f.read(n_ent * ent_size)
        used = sum(1 for i in range(n_ent)
                   if entries[i * ent_size:(i + 1) * ent_size][:16] != b"\x00" * 16)

        if n_ent != STD_ENTRIES:
            if n_ent < STD_ENTRIES:
                sys.exit("iso-gpt: only %d entries; refusing to grow the array" % n_ent)
            tail = entries[STD_ENTRIES * ent_size:]
            if tail.strip(b"\x00"):
                sys.exit("iso-gpt: entries beyond %d are in use" % STD_ENTRIES)
            keep = entries[:STD_ENTRIES * ent_size]

            # fields: 5 = MyLBA, 6 = AlternateLBA (where the backup header is)
            back_lba = prim[6]
            back = read_header(f, back_lba)
            for hdr, lba in ((prim, 1), (back, back_lba)):
                hdr[11] = STD_ENTRIES
                write_header(f, lba, hdr, keep)
            # The backup's own copy of the array must match what its CRC
            # now says; write the trimmed entries there too.
            f.seek(back[10] * SECTOR)
            f.write(keep)
            print("iso-gpt: partition entries %d -> %d (%d in use), CRCs rewritten"
                  % (n_ent, STD_ENTRIES, used))
            entries = keep
        else:
            print("iso-gpt: %d partition entries, %d in use" % (n_ent, used))

        got = str(uuid.UUID(bytes_le=entries[16:32]))
        if got != want:
            sys.exit("iso-gpt: ISO partition 1 is PARTUUID=%s but the boot menu says %s.\n"
                     "xorriso changed how it derives partition GUIDs; update "
                     "AOS_ISO_ROOT_PARTUUID in br2ext/external.mk." % (got, want))
        print("iso-gpt: ISO root PARTUUID=%s, as the boot menu expects" % got)


if __name__ == "__main__":
    main()
