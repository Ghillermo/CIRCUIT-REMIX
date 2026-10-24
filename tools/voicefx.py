"""Ring mod, filter modes and drive per track in the Circuit Rhythm 5706's DSP core 1, the voices (MIT; the K5-K8 part of the Stock+ sampler
mode: the user's «filter modes, ring mod + LFO, distortion types»).

The stock (core 1's program, tools/rhdsp.py dis 1; docs/PORTADO.md «Núcleo 1 = las voces»): the voices run one after the other ($234 ..
$6CD, r0 = $44 + $10 v, Y:$1405 = v = the track); each is rendered by $1E5 into X:$2A02.. (x:$1 = 32 samples, mono), filtered by $511, then
P:$240 jsr $25C (the sample's end: it does not touch the buffer), $244 (the level ramp) and $6AB (the mix).
Ours (after pitchmod's words, tools/rhdsp1.py): P:$240 jsr $25C -> jsr FX: on X:$2A02.. of voice v, in this order, each stage skipped when off
(all off = the stock's sound, nothing run but the three tests), then jmp $25C:
  * ring mod: gain = 1 - m + m * s(phase), s = 2t - t|t| of a triangle t (close to a sine), phase += step a sample;
  * filter: a Chamberlin state-variable filter (low += f band; high = in - low - q band; band += f high), modes 1 low-pass, 2 band-pass,
    3 high-pass, 4 notch (low + high); mode 5 = a comb (y = x + fb y[n - D], D = 1..255 samples, a buffer of 256 per voice in Y:$800 + $100 v);
  * drive (the gain g x 16 first: g = $080000 = x 1): type 1 soft (3u - u^3) / 2, 2 hard (the clip of the DSP's moves), 3 fold (a triangle of
    the input: period 4), 4 bitcrush (the word ANDed with a mask).
Core 1's Y, track t at + t (written by the ARM, rhremote dspw 1 Y:...; zero at power-on: P:$151 clears Y:$400..$13FF):
  Y:$1340 ring phase (ours)  Y:$1348 ring step (a cycle = $1000000)    Y:$1350 ring amount m (0 = off .. $7FFFFF)
  Y:$1358 filter mode 0-5    Y:$1360 f (SVF; comb: D, an integer)       Y:$1368 q / 2 (SVF damping; comb: fb, signed)
  Y:$1370 SVF low (ours)     Y:$1378 SVF band (ours)                    Y:$1380 drive type 0-4
  Y:$1388 drive gain g       Y:$1390 bitcrush mask                      Y:$1398 comb write index (ours)
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rhdsp  # noqa: E402
import rhdsppatch as DP  # noqa: E402

Y_BASE = 0x1340
RPH, RST, RAM, FMODE, FF, FQ, FL, FB, DTYPE, DG, DMASK, CW = (8 * k for k in range(12))
Y_COMB = 0x800
P_HOOK, P_END = 0x240, 0x25C
OLD_HOOK = 0x0D025C                                     # jsr $25c (short)
JSR_SHORT = 0x0D0000
BUF = 0x2A02
ONE = 0x7FFFFF


def assemble(items, at):
    """items: asm lines, ("label", name), ("jcc", cond, name), ("jmp", name), ("do", name) = do x:$1 until name, ("doa", "do n7", name) -> words (two passes)"""
    def size(it):
        if isinstance(it, str):
            return len(DP.asm([it]))
        return {"label": 0, "jcc": 2, "jmp": 2, "do": 2, "doa": 2, "jsr": 2, "words": len(it[1]) if it[0] == "words" else 0}[it[0]]
    addr, labels = at, {}
    for it in items:
        if isinstance(it, tuple) and it[0] == "label":
            labels[it[1]] = addr
        addr += size(it)
    out = []
    for it in items:
        if isinstance(it, str):
            out += DP.asm([it])
        elif it[0] == "jcc":
            out += DP.jcc(it[1], labels[it[2]])
        elif it[0] == "jmp":
            out += DP.jmp(labels[it[1]] if isinstance(it[1], str) else it[1])
        elif it[0] == "do":
            out += [0x060100, labels[it[1]] - 1]                       # do x:$1,LA (LA = the loop's last word; dsptool's asm has no form)
        elif it[0] == "doa":                                            # ("doa", "do n7" / "do #$20", name): dsptool's own do forms
            w = DP.asm([f"{it[1]},${labels[it[2]]:x}"])
            assert len(w) == 2 and w[1] == labels[it[2]] - 1, (it, w)
            out += w
        elif it[0] == "jsr":
            out += DP.jsr(labels[it[1]] if isinstance(it[1], str) else it[1])
        elif it[0] == "words":
            out += list(it[1])
    return out, labels


SHIFT_COMB = 0x1800                                     # (shift != 0) the comb's buffers out of the voices' sample rings Y:$400..$13FF


def items(shift=0, pre=None, lite=False):
    """shift: our Y words moved up (RD8 on: $300); pre: a routine called first (voicefilt's POST); lite (RD10 on): only what the Stock+
    page uses - the ring, the comb (mode 5) and the bitcrush (drive type 4): no SVF modes, no soft / hard / fold"""
    L = []
    E = L.append
    ybase, ycomb = Y_BASE + shift, (SHIFT_COMB if shift else Y_COMB)

    def y(off):
        return f"y:(r1+${off:x})"
    E(("label", "fx"))
    if pre is not None:
        E(("jsr", pre))
    for s in ("move y:>$1405,n1", f"move #>${ybase:x},r1", "lua (r1)+n1,r1"):
        E(s)

    # ---- ring mod
    E(f"move {y(RAM)},a"); E("tst a"); E(("jcc", "eq", "filt"))
    E(f"move {y(RPH)},b"); E(f"move {y(RST)},x0"); E(f"move {y(RAM)},y1"); E(f"move #>${BUF:x},r2")
    E(("do", "r_end"))
    for s in ("add x0,b", "move b1,y0", "move y0,b", "tfr b,a", "abs a", "asl a", f"sub #>${ONE:x},a", "move a,x1",
              "abs a", "move a,y0", "mpy -x1,y0,a", "add x1,a", "add x1,a", "move a,x1", "mpy y1,x1,a", "sub y1,a",
              f"add #>${ONE:x},a", "move a,x1", "move x:(r2),y0", "mpy x1,y0,a", "move a,x:(r2)+"):
        E(s)
    E(("label", "r_end"))
    E(f"move b1,{y(RPH)}")

    # ---- filter
    E(("label", "filt"))
    E(f"move {y(FMODE)},a"); E("tst a"); E(("jcc", "eq", "drive"))
    E("cmp #>$5,a"); E(("jcc", "eq", "comb"))
    for m in (() if lite else (1, 2, 3, 4)):
        E(f"cmp #>${m:x},a"); E(("jcc", "eq", f"fv{m}"))
    E(("jmp", "drive"))
    outs = {1: ["move x1,x:(r2)+"], 2: ["move b,x:(r2)+"], 3: ["move y0,x:(r2)+"], 4: ["add x1,a", "move a,x:(r2)+"]}
    for m in (() if lite else (1, 2, 3, 4)):
        E(("label", f"fv{m}"))
        for s_ in (f"move {y(FF)},x0", f"move {y(FQ)},y1", f"move {y(FL)},a", f"move {y(FB)},b", f"move #>${BUF:x},r2"):
            E(s_)
        E(("do", f"f{m}_end"))
        for s_ in ("move b,y0", "mac y0,x0,a", "move a,x1", "move x:(r2),a", "sub x1,a", "mac -y1,y0,a", "mac -y1,y0,a",
                   "move a,y0", "mac y0,x0,b", *outs[m], "move x1,a"):
            E(s_)
        E(("label", f"f{m}_end"))
        E(("jmp", "f_out"))
    E(("label", "f_out"))
    E(f"move a,{y(FL)}"); E(f"move b,{y(FB)}")
    E(("jmp", "drive"))

    E(("label", "comb"))
    for s in ("move n1,a", "asl #8,a,a", f"add #>${ycomb:x},a", "move a1,r3", f"move {y(FF)},x0", f"move {y(FQ)},x1",
              f"move {y(CW)},n2", f"move #>${BUF:x},r2"):
        E(s)
    E(("do", "c_end"))
    for s in ("move n2,a", "sub x0,a", "and #>$ff,a", "move a1,n3", "move y:(r3+n3),y0", "move x:(r2),a", "mac x1,y0,a",
              "move a,x:(r2)+", "move n2,n3", "move a,y:(r3+n3)", "move n2,a", "add #>$1,a", "and #>$ff,a", "move a1,n2"):
        E(s)
    E(("label", "c_end"))
    E(f"move n2,{y(CW)}")

    # ---- drive
    E(("label", "drive"))
    E(f"move {y(DTYPE)},a"); E("tst a"); E(("jcc", "eq", "done"))
    E(f"move {y(DG)},x0"); E(f"move {y(DMASK)},y1"); E(f"move #>${BUF:x},r2")
    bodies = {
        1: ["move x:(r2),y0", "mpy y0,x0,a", "asl #4,a,a", "move a,x1", "move a,y0", "mpy x1,y0,a", "move a,y0", "mpy -x1,y0,a",
            "add x1,a", "add x1,a", "add x1,a", "asr a", "move a,x:(r2)+"],
        2: ["move x:(r2),y0", "mpy y0,x0,a", "asl #4,a,a", "move a,x:(r2)+"],
        3: ["move x:(r2),y0", "mpy y0,x0,a", "asl #3,a,a", "add #>$400000,a", "move a1,y0", "move y0,a", "abs a", "asl a",
            f"sub #>${ONE:x},a", "move a,x:(r2)+"],
        4: ["move x:(r2),y0", "mpy y0,x0,a", "asl #4,a,a", "move a,x1", "move x1,a", "and y1,a", "move a,x:(r2)+"],
    }
    for t in ((4,) if lite else (1, 2, 3, 4)):
        E(("label", f"dt{t}"))
        E(f"cmp #>${t:x},a"); E(("jcc", "ne", f"dt{t + 1}" if t < 4 else "done"))
        E(("do", f"d{t}_end"))
        for s in bodies[t]:
            E(s)
        E(("label", f"d{t}_end"))
        E(("jmp", "done"))
    E(("label", "done"))
    E(("jmp", P_END))
    return L


def code(at, shift=0, pre=None, lite=False):
    """-> (words for P:at.., FX's address)"""
    words, labels = assemble(items(shift, pre, lite), at)
    return words, labels["fx"]


def check(words, at):
    """every word as dsptool disassembles it: no mpysu (an invalid multiply pair that dsptool's asm turns into mpysu).  Without dsptool (the
    public tree builds from tools/rhdsp_asm_cache.json) nothing to check: the build's SHA-256 against its manifest proves the words."""
    if not Path(rhdsp.TOOL).exists():
        return ""
    d = tempfile.mkdtemp()
    f = os.path.join(d, "fx.bin")
    Path(f).write_bytes(b"".join(w.to_bytes(3, "big") for w in words))
    out = subprocess.run([rhdsp.TOOL, "dis", f, f"{at:x}"], capture_output=True, text=True).stdout
    bad = [ln for ln in out.splitlines() if "mpysu" in ln or "macsu" in ln or " dc " in ln]
    assert not bad, bad
    return out
