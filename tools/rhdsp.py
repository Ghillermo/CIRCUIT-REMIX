"""The Circuit Rhythm 5706's DSP programs (development tool, MIT): extract them from the stock image and disassemble them with dsptool.

The ARM uploads them with 0x08031110(mode) -> 0x080310B0(block, core) (the Tracks' 0x08029260 / 0x08029200), from the pointer table
0x08031658 = [core 0 mode 0, core 0 mode 1, core 1 mode 0, core 1 mode 1] (+ a fixed 0x40-word block 0x080662CC for core 1 first); each
block is Motorola's bootstrap format: word count, load address, the words (24 bits, big-endian).  In the Rhythm core 0 holds the master
section (compressor P:$1A26, its inputs Y:$10A..$10D) with 0x1FED words, core 1 the large program (0x376B words).

    python tools/rhdsp.py list
    python tools/rhdsp.py dis CORE [MODE] -o FILE.asm      (CORE 0 / 1, MODE 0 / 1; dsptool from ../CIRCUIT-HACKS/ext/bin or $DSPTOOL;
                                                            core 1: its segments as its loader places them, tools/rhdspemu.segments)
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STOCK = ROOT / "stock" / "circuitrhythm-firmware-5706-STOCK.bin"
BASE, TABLE = 0x08010000, 0x08031658
TOOL = os.environ.get("DSPTOOL") or str(ROOT.parent / "CIRCUIT-HACKS" / "ext" / "bin" / ("dsptool.exe" if os.name == "nt" else "dsptool"))


def block(img, core, mode=0):
    a = int.from_bytes(img[TABLE - BASE + 4 * (2 * core + mode):][:4], "little")
    o = a - BASE
    n, load = int.from_bytes(img[o:o + 3], "big"), int.from_bytes(img[o + 3:o + 6], "big")
    return a, n, load, img[o + 6:o + 6 + 3 * n]


if __name__ == "__main__":
    img = STOCK.read_bytes()
    if sys.argv[1] == "list":
        for c in (0, 1):
            for m in (0, 1):
                a, n, load, _ = block(img, c, m)
                print(f"core {c} mode {m}: {a:#010x}, {n:#x} words at P:${load:X}")
    else:
        c = int(sys.argv[2]); m = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] != "-o" else 0
        out = Path(sys.argv[sys.argv.index("-o") + 1]) if "-o" in sys.argv else None
        import rhdspemu                                                   # core 1: its P segments, as its loader places them
        asm = ""
        with tempfile.TemporaryDirectory() as td:
            for k, (sp, addr, ws) in enumerate(rhdspemu.segments(c, m)):
                if sp != "p" or (c == 1 and k == 0):
                    asm += f"; {sp.upper()}:${addr:X} {len(ws)} words\n" if sp != "p" else ""
                    continue
                pb = Path(td) / f"p{k}.bin"
                pb.write_bytes(b"".join(w.to_bytes(3, "big") for w in ws))
                asm += f"; P:${addr:X} {len(ws)} words\n" + subprocess.run([TOOL, "dis", str(pb), f"{addr:x}"], capture_output=True, text=True).stdout
        (out.write_text(asm) if out else print(asm))
