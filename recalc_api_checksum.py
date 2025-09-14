#!/usr/bin/env python3
"""
recalc_acpi_checksum.py
Usage:
  recalc_acpi_checksum.py <input.aml> [<output.aml>]

If output omitted the input file is patched in-place.
This sets the 1-byte ACPI checksum (offset 9) so that sum(all bytes) % 256 == 0.
"""
import sys, os

def compute_checksum(data: bytes) -> int:
    if len(data) < 10:
        raise ValueError("file too small (<10 bytes)")
    s = sum(data[:9]) + sum(data[10:])
    s &= 0xFF
    return (-s) & 0xFF

def write_patched(data: bytes, outpath: str, checksum: int):
    b = bytearray(data)
    b[9] = checksum
    with open(outpath, "wb") as f:
        f.write(b)

def verify_mod256(path: str) -> int:
    d = open(path, "rb").read()
    return sum(d) & 0xFF

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    infile = sys.argv[1]
    outfile = sys.argv[2] if len(sys.argv) > 2 else infile

    data = open(infile, "rb").read()
    chk = compute_checksum(data)

    # write either in-place or to new file
    write_patched(data, outfile, chk)

    print(f"Computed checksum: 0x{chk:02X}")
    v = verify_mod256(outfile)
    print(f"Verification: sum(all bytes) % 256 = {v}  (should be 0)")
    if v != 0:
        sys.exit(2)

