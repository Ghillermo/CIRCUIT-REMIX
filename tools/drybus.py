"""The FX sequencer's per-track sends on core 0: a dry bus around the Grid FX (MIT; RD49; the user, 2026-11-11: «dedicated knob sends on the
FX sequencer? Each one sends a track through master FX, all full at start. They set wet/dry level»; docs/DISENO_RH92.md).

Core 0's block (the stock, read in its program): P:$224 mixes the tracks (each sample s_t[i] x its main gains X:$DE + 64 t + 2 i / + 1 into
the shared bus, the samples at Y:$304F0 + 64 t + (y:$FFFFD0 << 5)), $1A11 sums that bus into the master bus X:$4AD8 (32 stereo pairs), the
reverb's return is added (P:$22C-$238); then the Grid FX: Beat Repeat in place on $4AD8 (P:$239 jsr $166B), the copy to $4B18
($23B-$248), the other six on $4B18 (to P:$27A); P:$282 the compressor ($1A26) reads $4B18.
Ours (only with the key X:DKEY = KEYV; each track's dry share f_t at X:FT + t, 0 = all through the Grid FX):
  * DRY1 (P:$239's jsr): D = sum over t of f_t x s_t[i] x its main gains (L, R), into X:DBUF; $4AD8 -= D; then Beat Repeat;
  * DRY2 (P:$282's jsr): $4B18 += D; then the compressor.
With no Grid FX on, the chain passes the bus as it is: what is taken out comes back (but rounding).  Every register the two touch is saved
and put back (X:SAVE), so Beat Repeat and the compressor start as the stock's.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

AT = 0x2898                                             # synth0's tables' old place (OPT xtab: in X now)
HOOK1, OLD1 = 0x239, 0x166B
HOOK2, OLD2 = 0x282, 0x1A26
DBUF, SAVE, FT, DKEY = 0x5120, 0x5160, 0x5180, 0x5188   # core 0 X (after synth0's INCT / ENVT at $5000-$5110; SAVE: 18 words)
KEYV = 0x5D7B95
BUS1, BUS2 = 0x4AD8, 0x4B18
GAINS, SAMPLES = 0xDE, 0x304F0
REGS = ("a0", "a1", "a2", "b0", "b1", "b2", "x0", "x1", "y0", "y1", "r1", "r2", "r3", "r5", "n2", "n3", "n5")


assert SAVE + 1 + len(REGS) <= FT and DBUF + 64 <= SAVE


def looper():
    import rhbuild
    return bool(rhbuild.OPT.get("looper"))


def build():
    """-> the code's words at AT and its labels; the inner loop is a subroutine (the track loop's body calls it); (RD50, OPT looper) DRY2
    also runs tools/looper0.py's body, with r4 / n4 saved too"""
    import core0 as C0
    regs = REGS + (("r4", "n4") if looper() else ())
    assert SAVE + 1 + len(regs) <= FT
    sv = [("label", "dsave"), f"move r0,x:>${SAVE:x}", f"move #>${SAVE + 1:x},r0", "nop"] + [f"move {r},x:(r0)+" for r in regs] + ["rts"]
    rs = [("label", "drest"), f"move #>${SAVE + 1:x},r0", "nop"] + [f"move x:(r0)+,{r}" for r in regs] + [f"move x:>${SAVE:x},r0", "rts"]
    key = [f"move x:>${DKEY:x},a", f"move #>${KEYV:x},x0", "cmp x0,a"]
    # the track's part: r2 = its gains, r3 = its samples, y1 = f; D += s f gL, s f gR
    trk = [("label", "dtrk"), "move r2,r0", "move r3,r5", f"move #>${DBUF:x},r1", "nop",
           "do #$20,${dt_e:x}",
           "move y:(r5)+,x0", "mpy x0,y1,a", "move a,y0",
           "move x:(r0)+,x0", "move x:(r1),a", "mac y0,x0,a", "move a,x:(r1)+",
           "move x:(r0)+,x0", "move x:(r1),a", "mac y0,x0,a", "move a,x:(r1)+",
           ("label", "dt_e"), "rts"]
    d1 = [("label", "dry1"), ("jsr", "dsave"), *key, ("jcc", "ne", "d1_r"),
          f"move #>${DBUF:x},r1", "clr a", "nop", "rep #$40", "move a,x:(r1)+",
          "movep y:<<$ffffd0,b", "asl #5,b,b", f"move #>${SAMPLES:x},a", "add b,a", "move a1,r3",
          f"move #>${GAINS:x},r2", "move #>$40,n2", "move #>$40,n3", f"move #>${FT:x},r1", "nop",
          "do #$8,${d1_te:x}",
          "move x:(r1)+,y1", "move r1,n5", "move y1,a", "tst a", ("jscc", "ne", "dtrk"), "move n5,r1",
          "move (r2)+n2", "move (r3)+n3",
          ("label", "d1_te"),
          f"move #>${BUS1:x},r0", f"move #>${DBUF:x},r1", "nop",
          "do #$40,${d1_se:x}", "move x:(r0),a", "move x:(r1)+,x0", "sub x0,a", "move a,x:(r0)+", ("label", "d1_se"),
          ("label", "d1_r"), ("jsr", "drest"), ("jmp", OLD1)]
    d2 = [("label", "dry2"), ("jsr", "dsave"), *key, ("jcc", "ne", "d2_r"),
          f"move #>${BUS2:x},r0", f"move #>${DBUF:x},r1", "nop",
          "do #$40,${d2_se:x}", "move x:(r0),a", "move x:(r1)+,x0", "add x0,a", "move a,x:(r0)+", ("label", "d2_se"),
          ("label", "d2_r")] + ([("jsr", "loop")] if looper() else []) + [("jsr", "drest"), ("jmp", OLD2)]
    lp = []
    if looper():
        import looper0
        lp = looper0.items()
    import rhbuild
    if rhbuild.OPT.get("xclr"):
        lp += xclr_items()
    w, lab = C0.asm_at(sv + rs + trk + d1 + d2 + lp, AT)
    assert AT + len(w) <= 0x2AAA, hex(AT + len(w))                         # (synth0's old tables' room)
    return w, lab


CLR_AT = 0x1C5C                                         # the stock's start-up clear (in P:$1C4F): r0 = 0, x0 = 0, x1 = $6000, then
CLR_OLD = [0x06C500, 0x001C5F, 0x446000, 0x4C5800]       # do x1,$1C60 / move x0,x:(r0) / move x0,y:(r0)+: X and Y 0..$5FFF to 0


def keep():
    import rhbuild
    """the X words core 0's loader writes before the stock starts (synth0 OPT xtab): [(first, end)]"""
    import synth0 as S
    with rhbuild.options(va=3):
        tb = S.tables()
    return [(S.XA, S.XA + len(tb["F2"]) + len(tb["Q2"])), (S.XB, S.XB + len(tb["INCT"]) + len(tb["ENVT"]))]


def xclr_items():
    """(RD50 on the device: RD49's synth silent; OPT xclr) the stock's start-up clear in place: Y 0..$5FFF, X 0..$5FFF but the tables
    (jsr XCLR in place of its do; x0 = 0, x1 = $6000, r0 = 0 from the stock)"""
    L = [("label", "xclr"), "do x1,${xc_y:x}", "move x0,y:(r0)+", ("label", "xc_y")]
    lo = 0
    for k, (a, e) in enumerate(keep() + [(0x6000, 0x6000)]):
        if a > lo:
            L += [f"move #>${lo:x},r0", f"move #>${a - lo:x},x1", "nop", f"do x1,${{xc_{k}:x}}", "move x0,x:(r0)+", ("label", f"xc_{k}")]
        lo = e
    return L + ["rts"]


def segs():
    """the code at AT and the two hooks (jsr DRY1 / DRY2 in place of the stock's jsr, the old targets checked)"""
    w, lab = build()
    import rhbuild
    out = [(AT, w), (HOOK1, [0x0BF080, lab["dry1"]]), (HOOK2, [0x0BF080, lab["dry2"]])]
    if rhbuild.OPT.get("xclr"):
        out.append((CLR_AT, [0x0BF080, lab["xclr"], 0x000000, 0x000000]))
    return out
