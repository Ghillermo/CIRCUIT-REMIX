"""Run the Circuit Rhythm 5706's own DSP programs in emulation (development tool, MIT; CIRCUIT-HACKS' dspemu for the Rhythm).

dsptool (dsp56kEmu's interpreter, ../CIRCUIT-HACKS/ext/bin or $DSPTOOL, see tools/rhdsp.py) runs a script: the core's program from the stock
image (tools/rhdsp.block: core 0 = master, core 1 = the large one; mode 0), placed as the DSP gets it: core 0's block is plain code at P:$0 (the
DSP's own bootstrap); core 1 first gets the fixed 0x40-word loader 0x080662CC, which reads the block from the host port as two header words, then
segments {type 0 / 1 / 2 = P / X / Y, count, address, the words} until a type above 2, then jumps to P:$100 (segments() does the same), the
memory we give it (words, or files dumped from
the device with `tools/rhremote.py dspdump`, RD3), then either a call (jsr from a stub at P:STUB, stopping when it returns) or a run from PC to
STOP; it answers the dumps asked for.  Nothing of the DSP code is copied anywhere: it is read from the user's stock image at run time.

    from rhdspemu import run
    res, ran = run(0, pc=0x1A26, stop=0x1A36, mem=[("y", 0x10A, [1, 0x400000, 0x200000, 1])], dumps=[("x", 0x1BD2, 1)])
    res[("x", 0x1BD2)] -> [word]; ran = "RAN n pc=... ins=... cyc=..."
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import rhdsp

STUB = 0x7000                                    # above both programs
LOADER = 0x080662CC                              # core 1's fixed loader (0x40 words at P:$0)
JSR, JMP = 0x0BF080, 0x0AF080                    # jsr / jmp with an absolute address word


def words_of(path: str | Path):
    d = Path(path).read_bytes()
    return [int.from_bytes(d[i:i + 3], "big") for i in range(0, len(d) - 2, 3)]


def program(core: int, mode: int = 0):
    img = rhdsp.STOCK.read_bytes()
    _, n, load, code = rhdsp.block(img, core, mode)
    return load, code


def segments(core: int, mode: int = 0):
    """-> [(space, address, [words])] as the core holds its program after the upload."""
    load, code = program(core, mode)
    ws = [int.from_bytes(code[i:i + 3], "big") for i in range(0, len(code) - 2, 3)]
    if core == 0:
        return [("p", load, ws)]
    img = rhdsp.STOCK.read_bytes()
    raw = img[LOADER - rhdsp.BASE:]
    n = int.from_bytes(raw[:3], "big")
    loader = [int.from_bytes(raw[6 + 3 * i:9 + 3 * i], "big") for i in range(n)]
    stream = [len(ws), load] + ws                                              # (the block's own two header words)
    out, i = [("p", 0, loader)], 2                                            # the loader's first reads: the two header words
    while i < len(stream):
        t = stream[i]
        if t > 2:
            break
        cnt, addr = stream[i + 1], stream[i + 2]
        out.append(("pxy"[t], addr, stream[i + 3:i + 3 + cnt]))
        i += 3 + cnt
    return out


def run(core, call=None, pc=None, stop=None, mem=(), files=(), dumps=(), maxins=2_000_000, mode=0, regs_code=(), extra=(), segs=None):
    """core 0 / 1; call = a P address to jsr (stops when it returns), or pc / stop; mem = [(space, addr, [words])];
    files = [(space, addr, path)] (3 bytes a word, big-endian: rhremote dspdump); dumps = [(space, addr, n)]; extra = more script lines;
    segs = [(space, addr, [words])] in place of the stock's (a patched program: tools/rhdsp1.py).
    -> ({(space, addr): [words]}, the RAN line)."""
    d = tempfile.mkdtemp()
    try:
        lines = []
        for k, (sp, addr, ws) in enumerate(segs if segs is not None else segments(core, mode)):
            fn = os.path.join(d, f"seg{k}.bin")
            if sp == "p":
                Path(fn).write_bytes(b"".join(w.to_bytes(3, "big") for w in ws))
                lines.append(f"LOADP {fn} {addr:x}")
            else:
                for i in range(0, len(ws), 64):
                    lines.append("%s %x %s" % (sp.upper(), addr + i, " ".join("%06x" % x for x in ws[i:i + 64])))
        for sp, addr, path in files:
            ws = words_of(path)
            for i in range(0, len(ws), 64):
                lines.append("%s %x %s" % (sp.upper(), addr + i, " ".join("%06x" % x for x in ws[i:i + 64])))
        for sp, addr, ws in mem:
            lines.append("%s %x %s" % (sp.upper(), addr, " ".join("%06x" % (x & 0xFFFFFF) for x in ws)))
        if call is not None:
            stub = list(regs_code) + [JSR, call, JMP, STUB + len(regs_code) + 2]
            lines.append("P %x %s" % (STUB, " ".join("%06x" % x for x in stub)))
            lines += [f"PC {STUB:x}", f"STOP {STUB + len(regs_code) + 2:x}"]
        else:
            lines += [f"PC {pc:x}", f"STOP {stop:x}"]
        lines += list(extra) + [f"MAX {maxins}", "RUN"]
        for sp, addr, n in dumps:
            lines.append(f"DUMP{sp.upper()} {addr:x} {n}")
        sc = os.path.join(d, "s.txt")
        Path(sc).write_text("\n".join(lines) + "\n")
        out = subprocess.run([rhdsp.TOOL, "run", sc], capture_output=True, text=True).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    res, ran = {}, None
    for line in out.splitlines():
        if line.startswith("RAN"):
            ran = line
        elif line[:1] in "XYP" and ":" in line:
            k, v = line.split(":", 1)
            sp, a = k.split()
            res[(sp.lower(), int(a, 16))] = [int(x, 16) for x in v.split()]
    return res, ran
