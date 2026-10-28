"""The line input as a track's sound (MIT; RH47, pending #21 of docs/PORTADO.md: «Line in o retornos de efectos como fuente de una pista (con
sidechain y efectos)»).

The stock of the Rhythm (read in core 0's program, tools/rhdsp.py dis 0):
  * the audio interrupt (P:$1C5) puts the two inputs into the Y ring at Y:$FFE; each block P:$19FA (called at P:$209) leaves them, sign
    corrected, interleaved L R in the shared Y:$30710 (64 words; core 1 records from there) and adds them x X:$307B0 into the output block
    (the input monitor);
  * then (P:$224, `jsr $367`, granular0's hook: SPL -> GR -> the mix) each track's 32 samples, which core 1 leaves in Y:$304F0 + 64 t +
    32 (y:$FFFFD0) (doubly buffered), get the track's level, pan, sends, side-chain and mute in the mix.
Ours:
  * core 0 (LI at P:AT, P:$224 -> jsr LI, which goes on to stsplit's SPL): while Y:LKEY = KEY, the line track's 32 samples = (L + R) / 2
    of this block's inputs x a gain: 1 (gate «always»), or its voice's gain x envelope (gate «notes»: Y:$37400 + 16 t, tools/envexp.py,
    the track's own steps open it), ramped across the block (Y:GC); so the input goes through the track's mixer strip: level, pan,
    reverb / delay sends, side-chain, mute, the cue;
  * the ARM: the track menu (RH45: a track button held) pad 5 = the line input on / off on that track (the granular engine leaves it), pad 6
    = its gate (lit = notes, dim = always); saved with the project (rhrec "linein": "L", a check byte, the track + 1, the gate); the LED
    task writes LKEY / LTRK / LGATE into core 0 (all three after a change, else one a frame), only with cthresh READY.
  If the granular engine is on the line track as well, it wins (GR writes the samples after LI).
two=True (RH48; the user, 2026-10-27: «When two input tracks are set, lower number becomes left, higher becomes right. When a single track
is set, both to the same channel»): up to two line tracks.  One: (L + R) / 2, as RH47.  Two: the lower-numbered track gets L, the higher R,
each with its own gate and gain ramp (core 0: slot 0 = LTRK / LGATE / GC, slot 1 = LTRK2 (the track | SLOT2, 0 = none) / LGATE2 / GC2).
The project's block: "L", a check byte (CHECK2: RH47's blocks read as none), then the two line tracks in the order they were set, each the
track + 1 | the gate << 4 (0 = none; the second only with a first).  Pad 5 on a third track: the older one leaves.  Pad 6 = the gate of the
menu's track, only on a line track (dark otherwise).  The LED task sends all five words (the key last) whenever the sorted pair differs from
the last one sent (a pad, a project loaded, the first frame), else one a frame.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, ands_reg, b, b_cond, b_w, bics_reg, bl, cmp_imm, cmp_reg, eors_reg, h, ldr_imm, ldrb_imm, ldrb_w,  # noqa: E402
                   lsls_imm, lsls_reg, lsrs_imm, mov_reg, movs_imm, movt, movw, orrs_reg, pop_list, push_list, raw, str_imm, strb_imm, strh_imm,
                   subs_imm8, tst_reg)
import core0 as C0  # noqa: E402
import countin as CI  # noqa: E402
import cthresh as TH  # noqa: E402
import envexp as EX  # noqa: E402
import granpage as GP  # noqa: E402
import rhrec  # noqa: E402
import rhstate  # noqa: E402

# ---- core 0
AT = 0x2E00                                            # P (granchain, with its stereo part, ends below $2E00)
HOOK = 0x224
Y0 = 0x1520                                            # core 0 Y (granchain has $1500-$1515)
LKEY, LTRK, LGATE, GC, GS = range(Y0, Y0 + 5)
LTRK2, LGATE2, GC2 = range(Y0 + 5, Y0 + 8)             # (two) slot 1
SLOT2 = 8                                              # (two) LTRK2 = the higher line track | SLOT2
SV = Y0 + 8                                            # r0, r1, then m0, m1
KEY = 0x11E1AE
TRK_BUF, INB, ONE = 0x304F0, 0x30710, 0x7FFFFF


# fx (RH54; the user, 2026-10-28: «add a "line in" mode that takes the fx returns (reverb or delay, toggleable), with another mode that
# also gets vca/vcf gated behavior»; the pads: «Pad 15 source, pad 14 gate»): each line slot has a source (LSRC / LSRC2: 0 the inputs, 1 the
# reverb's return, 2 the delay's) and its gate («notes») also puts the track's filter knobs on it (the low-pass, the high-pass, the
# resonance: granchain's state-variable filter, synth0's F2 / Q2 tables) besides the voice's VCA.  The returns: core 0's stock leaves each
# block's delay output in Y:$9C9 and the reverb's in Y:$889 (64 words, L R; tools/rhdsp.py dis 0: P:$597 copies the sends from
# X:$304B0 / X:$30470, P:$99A the delay, P:$11BB the reverb), then sums them into Y:$889 at P:$5C0; FXH (P:$5C0 -> jsr FXH, its
# `move #>$9c9,r6` kept) copies both to RVB / DLY first, so LI (at P:$224, before them) takes the last block's (0.67 ms late).
FXHOOK, FX_RV, FX_DL = 0x5C0, 0x889, 0x9C9
RVB, DLY = 0x1D00, 0x1D40                              # core 0 Y (free: synth0.GE0 is $1C00-$1CFF)
FY = 0x1540                                            # core 0 Y (free: gstereo's ends at $1535)
LSRC, LSRC2, SV2 = FY, FY + 1, FY + 2                  # the sources; r2, r3, r4, then m2, m3, m4 (6 words)
FS0, FS_N = FY + 8, 16                                 # a slot's filter: + 0 L, B (low-pass), + 2 L, B (high-pass), + 4 f low, + 5 f high,
F_LL, F_HL, F_FL, F_FH, F_TFL, F_TFH, F_LON, F_HON, F_QL, F_T = 0, 2, 4, 5, 6, 7, 8, 9, 10, 11   # + 6 / 7 targets, + 8 / 9 on, + 10 q, + 11 track
SRC_IN, SRC_RV, SRC_DL = 0, 1, 2
GSW, FMAG = FS0 + 2 * FS_N, FS0 + 2 * FS_N + 1          # lf_smp's switch (this slot gated); the filters' magic (else their states cleared)
FMAGIC = 0x1F7E4C
PAR, LP_I, HP_I, RES_I, LP_OPEN = 0x307C8, 0xC, 0xB, 0xD, 127


def items(spl, two=False, fx=None):
    if fx is not None:
        return items_fx(spl, fx)
    if two:
        return items2(spl)
    L = []

    def e(*s):
        L.extend(s)
    e(("label", "li"), f"move y:>${LKEY:x},a", f"move #>${KEY:x},x0", "cmp x0,a", ("jcc", "ne", spl))
    for i, k in enumerate((0, 1)):
        e(f"move r{k},y:>${SV + i:x}", ("words", [0x057060 | k, SV + 2 + i]), ("words", [0x05F420 | k, 0xFFFFFF]))
    # the track's buffer, as granular0's GR finds it: Y:$304F0 + 64 t + (y:$FFFFD0 << 5)
    e(f"move y:>${LTRK:x},a", "and #>$7,a", "move a1,x0",
      "movep y:<<$ffffd0,b", "asl #5,b,b", "clr a", "move x0,a1", "asl #6,a,a", f"add #>${TRK_BUF:x},a", "move b1,x1", "add x1,a",
      "move a1,r0")
    # the gain's target: 1, or the voice's gain x envelope; its step over the block
    e(f"move #>${ONE:x},a", f"move y:>${LGATE:x},b", "tst b", ("jcc", "eq", "li_g"),
      "clr a", "move x0,a1", "asl #4,a,a", f"add #>${EX.SHARED:x},a", "move a1,r1", "nop", "move y:(r1),a",
      ("label", "li_g"), f"move y:>${GC:x},b", "sub b,a", "asr #5,a,a", f"move a,y:>${GS:x}")
    # the 32 samples: (L + R) / 2 x the gain
    e(f"move #>${INB:x},r1", "nop", "do #$20,${li_l:x}",
      "move y:(r1)+,a", "asr a", "move y:(r1)+,b", "asr b", "add b,a", "move a,y1",
      f"move y:>${GC:x},b", f"move y:>${GS:x},x1", "add x1,b", f"move b,y:>${GC:x}", "move b,x0",
      "mpy y1,x0,a", "move a,y:(r0)+", ("label", "li_l"))
    for i, k in enumerate((0, 1)):
        e(f"move y:>${SV + i:x},r{k}", ("words", [0x05F060 | k, SV + 2 + i]))
    e(("jmp", spl))
    return L


def items2(spl):
    """(two) slot 0 = LTRK: (L + R) / 2 when LTRK2 = 0, else L; slot 1 = LTRK2 when <> 0: R"""
    L = []

    def e(*s):
        L.extend(s)
    e(("label", "li"), f"move y:>${LKEY:x},a", f"move #>${KEY:x},x0", "cmp x0,a", ("jcc", "ne", spl))
    for i, k in enumerate((0, 1)):
        e(f"move r{k},y:>${SV + i:x}", ("words", [0x057060 | k, SV + 2 + i]), ("words", [0x05F420 | k, 0xFFFFFF]))
    for sl, (wt, wg, gc) in enumerate(((LTRK, LGATE, GC), (LTRK2, LGATE2, GC2))):
        x = f"li{sl}_"
        if sl:
            e(f"move y:>${LTRK2:x},a", "tst a", ("jcc", "eq", "li_r"))
        # the track's buffer, as granular0's GR finds it: Y:$304F0 + 64 t + (y:$FFFFD0 << 5)
        e(f"move y:>${wt:x},a", "and #>$7,a", "move a1,x0",
          "movep y:<<$ffffd0,b", "asl #5,b,b", "clr a", "move x0,a1", "asl #6,a,a", f"add #>${TRK_BUF:x},a", "move b1,x1", "add x1,a",
          "move a1,r0")
        # the gain's target: 1, or the voice's gain x envelope; its step over the block
        e(f"move #>${ONE:x},a", f"move y:>${wg:x},b", "tst b", ("jcc", "eq", x + "g"),
          "clr a", "move x0,a1", "asl #4,a,a", f"add #>${EX.SHARED:x},a", "move a1,r1", "nop", "move y:(r1),a",
          ("label", x + "g"), f"move y:>${gc:x},b", "sub b,a", "asr #5,a,a", f"move a,y:>${GS:x}")
        # the 32 samples x the gain: slot 0 (L + R) / 2 alone, L with a slot 1; slot 1 R
        tail = [f"move y:>${gc:x},b", f"move y:>${GS:x},x1", "add x1,b", f"move b,y:>${gc:x}", "move b,x0",
                "mpy y1,x0,a", "move a,y:(r0)+", ("label", x + "l")]
        e(f"move #>${INB:x},r1")
        if sl == 0:
            e(f"move y:>${LTRK2:x},a", "tst a", ("jcc", "ne", x + "o"),
              "do #$20,${" + x + "l:x}", "move y:(r1)+,a", "asr a", "move y:(r1)+,b", "asr b", "add b,a", "move a,y1", *tail,
              ("jmp", "li1_"), ("label", x + "o"))
            x = "li0o_"
            tail[-1] = ("label", x + "l")
            e("do #$20,${" + x + "l:x}", "move y:(r1)+,a", "move y:(r1)+,b", "move a,y1", *tail)
        else:
            e("nop", "do #$20,${" + x + "l:x}", "move y:(r1)+,b", "move y:(r1)+,a", "move a,y1", *tail)
        if sl == 0:
            e(("label", "li1_"))
    e(("label", "li_r"))
    for i, k in enumerate((0, 1)):
        e(f"move y:>${SV + i:x},r{k}", ("words", [0x05F060 | k, SV + 2 + i]))
    e(("jmp", spl))
    return L


def items_fx(spl, tabs):
    """(fx, with two) items2 with a source per slot and the filter on a gated slot; tabs = synth0's table addresses (F2, Q2)"""
    L = []

    def e(*s):
        L.extend(s)
    e(("label", "li"), f"move y:>${LKEY:x},a", f"move #>${KEY:x},x0", "cmp x0,a", ("jcc", "ne", spl))
    for i, k in enumerate((0, 1)):
        e(f"move r{k},y:>${SV + i:x}", ("words", [0x057060 | k, SV + 2 + i]), ("words", [0x05F420 | k, 0xFFFFFF]))
    for i, k in enumerate((2, 3, 4)):
        e(f"move r{k},y:>${SV2 + i:x}", ("words", [0x057060 | k, SV2 + 3 + i]), ("words", [0x05F420 | k, 0xFFFFFF]))
    e(f"move y:>${FMAG:x},a", f"move #>${FMAGIC:x},x0", "cmp x0,a", ("jcc", "eq", "lf_ok"),           # once: the filters' states
      "clr a", f"move #>${FS0:x},r2", "nop", f"do #${2 * FS_N:x},${{lf_z:x}}", "move a,y:(r2)+", ("label", "lf_z"),
      "move #>$ff,a", f"move a,y:>${FS0 + F_T:x}", f"move a,y:>${FS0 + FS_N + F_T:x}", f"move x0,y:>${FMAG:x}", ("label", "lf_ok"))
    for sl, (wt, wg, gc, ws) in enumerate(((LTRK, LGATE, GC, LSRC), (LTRK2, LGATE2, GC2, LSRC2))):
        x = f"li{sl}_"
        if sl:
            e(f"move y:>${LTRK2:x},a", "tst a", ("jcc", "eq", "li_r"))
        e(f"move #>${FS0 + FS_N * sl:x},r2")
        # the track's buffer, as granular0's GR finds it: Y:$304F0 + 64 t + (y:$FFFFD0 << 5)
        e(f"move y:>${wt:x},a", "and #>$7,a", "move a1,x0",
          "movep y:<<$ffffd0,b", "asl #5,b,b", "clr a", "move x0,a1", "asl #6,a,a", f"add #>${TRK_BUF:x},a", "move b1,x1", "add x1,a",
          "move a1,r0")
        # gated: the filter's words from the track's knobs
        e(f"move y:>${wg:x},b", "tst b", ("jcc", "eq", x + "nf"), ("jsr", "lf_set"), ("label", x + "nf"))
        # the gain's target: 1, or the voice's gain x envelope; its step over the block
        e(f"move #>${ONE:x},a", f"move y:>${wg:x},b", "tst b", ("jcc", "eq", x + "g"),
          "clr a", "move x0,a1", "asl #4,a,a", f"add #>${EX.SHARED:x},a", "move a1,r1", "nop", "move y:(r1),a",
          ("label", x + "g"), f"move y:>${gc:x},b", "sub b,a", "asr #5,a,a", f"move a,y:>${GS:x}")
        # the source
        e(f"move y:>${ws:x},b", f"move #>${INB:x},a", "tst b", ("jcc", "eq", x + "s"), f"move #>${RVB:x},a", f"move #>${SRC_RV:x},x0",
          "cmp x0,b", ("jcc", "eq", x + "s"), f"move #>${DLY:x},a", ("label", x + "s"), "move a1,r1")
        # the 32 samples: slot 0 (L + R) / 2 alone, L with a slot 1; slot 1 R; gated: through the filter; x the gain
        tail = [("jsr", "lf_smp"), f"move y:>${gc:x},b", f"move y:>${GS:x},x1", "add x1,b", f"move b,y:>${gc:x}", "move b,x0",
                "mpy y1,x0,a", "move a,y:(r0)+", ("label", x + "l")]
        e(f"move y:>${wg:x},a", f"move a,y:>${GSW:x}")                    # (lf_smp's switch: this slot gated)
        if sl == 0:
            e(f"move y:>${LTRK2:x},a", "tst a", ("jcc", "ne", x + "o"),
              "do #$20,${" + x + "l:x}", "move y:(r1)+,a", "asr a", "move y:(r1)+,b", "asr b", "add b,a", "move a,y1", *tail,
              ("jmp", "li1_"), ("label", x + "o"))
            x = "li0o_"
            tail[-1] = ("label", x + "l")
            e("do #$20,${" + x + "l:x}", "move y:(r1)+,a", "move y:(r1)+,b", "move a,y1", *tail)
        else:
            e("nop", "do #$20,${" + x + "l:x}", "move y:(r1)+,b", "move y:(r1)+,a", "move a,y1", *tail)
        if sl == 0:
            e(("label", "li1_"))
    e(("label", "li_r"))
    for i, k in enumerate((0, 1)):
        e(f"move y:>${SV + i:x},r{k}", ("words", [0x05F060 | k, SV + 2 + i]))
    for i, k in enumerate((2, 3, 4)):
        e(f"move y:>${SV2 + i:x},r{k}", ("words", [0x05F060 | k, SV2 + 3 + i]))
    e(("jmp", spl))
    # ---- lf_set (r2 = the slot's filter, x0 = its track): the low-pass / high-pass on (index < 127 / > 0), their f smoothed 1/8 a block,
    # the damping; a new track or a filter turned on: its states from zero (granchain's way); keeps x0, r0
    e(("label", "lf_set"), f"move y:(r2+${F_T:x}),a", "cmp x0,a", ("jcc", "eq", "lf_same"),
      f"move x0,y:(r2+${F_T:x})", "clr a", *[f"move a,y:(r2+${o:x})" for o in (F_LL, F_LL + 1, F_HL, F_HL + 1, F_LON, F_HON)],
      ("label", "lf_same"),
      "clr a", "move x0,a1", "asl #5,a,a", f"add #>${PAR:x},a", "move a1,r3", "nop",
      f"move y:(r3+${LP_I:x}),a", "and #>$7f,a", "move a1,a", f"move #>${LP_OPEN:x},x1", "clr b", "cmp x1,a", ("jcc", "ge", "lf_lo"),
      "move #>$1,b", f"add #>${tabs['F2']:x},a", "move a1,r4", "nop", "move p:(r4),x1", f"move x1,y:(r2+${F_TFL:x})",
      f"move y:(r2+${F_LON:x}),a", "tst a", ("jcc", "ne", "lf_lo"),
      f"move x1,y:(r2+${F_FL:x})", "clr a", f"move a,y:(r2+${F_LL:x})", f"move a,y:(r2+${F_LL + 1:x})",
      ("label", "lf_lo"), f"move b,y:(r2+${F_LON:x})",
      f"move y:(r3+${HP_I:x}),a", "and #>$7f,a", "move a1,a", "clr b", "tst a", ("jcc", "eq", "lf_ho"),
      "move #>$1,b", f"add #>${tabs['F2']:x},a", "move a1,r4", "nop", "move p:(r4),x1", f"move x1,y:(r2+${F_TFH:x})",
      f"move y:(r2+${F_HON:x}),a", "tst a", ("jcc", "ne", "lf_ho"),
      f"move x1,y:(r2+${F_FH:x})", "clr a", f"move a,y:(r2+${F_HL:x})", f"move a,y:(r2+${F_HL + 1:x})",
      ("label", "lf_ho"), f"move b,y:(r2+${F_HON:x})")
    for fn, tf in ((F_FL, F_TFL), (F_FH, F_TFH)):                                  # f += (target - f) / 8
        e(f"move y:(r2+${tf:x}),a", f"move y:(r2+${fn:x}),b", "sub b,a", "asr #3,a,a", "add b,a", f"move a,y:(r2+${fn:x})")
    e(f"move y:(r3+${RES_I:x}),a", "and #>$7f,a", "move a1,a", f"add #>${tabs['Q2']:x},a", "move a1,r4", "nop", "move p:(r4),x1",
      f"move x1,y:(r2+${F_QL:x})", "rts")
    # ---- lf_smp (y1 = a sample, r2 = the slot's filter): gated (Y:FY + 7), through its low-pass / high-pass -> y1; keeps r0, r1
    e(("label", "lf_smp"), f"move y:>${GSW:x},a", "tst a", ("jcc", "eq", "ls_x"), "move y1,x1",
      f"move y:(r2+${F_LON:x}),a", "tst a", ("jcc", "eq", "ls_1"),
      f"lua (r2+${F_LL:x}),r4", f"move y:(r2+${F_FL:x}),x0", f"move y:(r2+${F_QL:x}),y0", ("jsr", "lf_svf"), "move y:(r4),x1",
      ("label", "ls_1"),
      f"move y:(r2+${F_HON:x}),a", "tst a", ("jcc", "eq", "ls_2"),
      f"lua (r2+${F_HL:x}),r4", f"move y:(r2+${F_FH:x}),x0", f"move y:(r2+${F_QL:x}),y0", ("jsr", "lf_svf"), "move y1,x1",
      ("label", "ls_2"), "move x1,y1",
      ("label", "ls_x"), "rts")
    # ---- lf_svf: granchain's c_svf (two passes of Chamberlin's filter; in x1, f x0, q / 2 y0, L / B at y:(r4) / y:(r4 + 1) -> L there, H y1)
    e(("label", "lf_svf"), "do #$2,${lf_sv:x}",
      "move y:(r4)+,a", "move y:(r4)-,y1", "mac x0,y1,a", "move a,y:(r4)",
      "move x1,b", "sub a,b", "mac -y1,y0,b", "mac -y1,y0,b",
      "tfr y1,a", "move b,y1", "mac x0,y1,a", "move a,y:(r4+$1)",
      ("label", "lf_sv"), "rts")
    # ---- FXH (P:$5C0 -> jsr FXH): the reverb's and the delay's outputs of this block to RVB / DLY, then the stock's `move #>$9c9,r6`
    e(("label", "fxh"), f"move #>${FX_RV:x},r6", f"move #>${RVB:x},r0", "nop", "do #$40,${fx_1:x}", "move y:(r6)+,a", "move a,y:(r0)+",
      ("label", "fx_1"),
      f"move #>${FX_DL:x},r6", f"move #>${DLY:x},r0", "nop", "do #$40,${fx_2:x}", "move y:(r6)+,a", "move a,y:(r0)+", ("label", "fx_2"),
      f"move #>${FX_DL:x},r6", "rts")
    return L


def code(spl, two=False, fx=None):
    w, labels = C0.asm_at(items(spl, two, fx), AT)
    assert AT + len(w) <= C0.LD, hex(AT + len(w))
    return w, labels


def segs(spl, two=False, fx=None):
    """for granular0's extra, after stsplit's: our code at P:AT and P:$224 -> jsr LI (the loader writes it last); fx (RH54, with two): also
    P:$5C0 -> jsr FXH (its stock words checked by the loader's builder: `move #>$9c9,r6`)"""
    w, labels = code(spl, two, fx)
    hooks = [(FXHOOK, [0x0BF080, labels["fxh"]])] if fx is not None else []
    return [(AT, w), (HOOK, [0x0BF080, labels["li"]])] + hooks


def model(ins, gate_gain, gc0, gate, src=0):
    """the 32 samples LI writes (floats), and the gain after (the tests'); src 0 = (L + R) / 2, 1 = L, 2 = R"""
    target = gate_gain if gate else ONE / (1 << 23)
    gc, step, out = gc0, (target - gc0) / 32, []
    for i in range(32):
        gc += step
        x = (ins[2 * i] / 2 + ins[2 * i + 1] / 2, ins[2 * i], ins[2 * i + 1])[src]
        out.append(x * gc)
    return out, gc


# ---- the ARM
WR16 = TH.WR16
MARK, CHECK = 0x4C, 0x5D                               # "L"
CHECK2 = 0x5E                                          # (two) the block's other format
GATE_BIT = 0x10                                        # (two) in a line track's byte
BLK, BLK_LEN = rhrec.OFF["linein"]
O = rhstate.OFF2["linein"][0]
R_DIRTY, R_ROUND = 0, 1
R_SENT, R_LO, R_HI = 0, 2, 3                           # (two) + 0 sent once, + 2 / + 3 the sorted pair last sent
NW = 5                                                 # (two) the words: LTRK, LGATE, LTRK2, LGATE2, LKEY
O_TH = rhstate.OFF["cthresh"][0] + 1
PAD_LINE, PAD_GATE = 4, 5                              # the menu's pads 5 / 6
PAD_LINE_, PAD_GATE_ = PAD_LINE, PAD_GATE
# ui (RH52; docs/INTERFAZ.md): the track menu's pads 13 / 14 (the row under the pages), in amber: pad 13 bright = a line track, dim = not;
# pad 14 (the gate) bright = with the notes, dim = always, dark when not a line track
UI_PAD_LINE, UI_PAD_GATE = 12, 13
UI_COL, UI_DIM = 0x2B, 0x2C
# fx (RH54, with ui): the menu's pad 15 = the line track's source, in turns: the inputs (amber) -> the reverb's return (cream, the FX
# view's reverb colour) -> the delay's (peach, its delay colour); dark off a line track; the source in bits 5-6 of the track's byte
# (RH48-RH53's bytes: 0 = the inputs); its words LSRC / LSRC2 sent with the others (the key still last)
UI_PAD_SRC, SRC_SHIFT, SRC_MASK = 14, 5, 0x60
SRC_COLS = (UI_COL, 0x29, 0x74)
PAL, PAL_ON, PAL_OFF, PAL_TON, PAL_TOFF = GP.PAL, GP.PAL_ON, GP.PAL_OFF, GP.PAL_TON, GP.PAL_TOFF
PP_ENTRY = GP.PP_ENTRY
M_GRAN, M_SWAL = GP.M_GRAN, GP.M_SWAL


def _liw(a, E):
    # ---- c_liw(r0 = word, r1 = Y address): into core 0; clobbers r0-r3, r12
    a.label("c_liw")
    E(push_list, [4], lr=True)
    E(movw, 2, 0x8000)
    E(orrs_reg, 2, 1)
    E(lsls_imm, 1, 0, 8)
    E(movs_imm, 0, 0)
    E(bl, WR16)
    E(pop_list, [4], pc=True)


def _arm2(a, E, imm32, L, prev, ui=False, fx=False):
    """(two) c_lipad, c_liw, c_liwk, c_liled; ui: the menu's pads 13 / 14 in amber (bright / dim)"""
    PAD_LINE, PAD_GATE = (UI_PAD_LINE, UI_PAD_GATE) if ui else (PAD_LINE_, PAD_GATE_)
    # ---- c_lipad (the controller's pad press, granpage's head after it): the menu open, pads 5 / 6 are ours
    a.label("c_lipad")
    E(cmp_imm, 1, PAD_LINE)
    E(b_cond, "pd_s", "lo")
    E(cmp_imm, 1, UI_PAD_SRC if fx else PAD_GATE)
    E(b_cond, "pd_s", "hi")
    E(push_list, [0, 1, 2, 3, 4, 5, 6], lr=True)
    E(mov_reg, 5, 1)
    E(bl, L["c_gpmopen"])
    E(cmp_imm, 0, 8)
    E(b_cond, "pd_p", "hs")
    E(mov_reg, 4, 0)
    E(adds_imm8, 4, 1)                                                    # r4 = the menu's track + 1
    E(bl, L["c_gpmst"])                                                   # its release swallowed by the menu's
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 5)
    E(ldr_imm, 2, 0, M_SWAL)
    E(orrs_reg, 2, 1)
    E(str_imm, 2, 0, M_SWAL)
    E(mov_reg, 6, 0)                                                      # r6 = the menu state
    E(bl, "c_liget")                                                      # r0 = the first line track's byte, r1 = the second's
    E(movs_imm, 3, 15)
    E(mov_reg, 2, 0)
    E(ands_reg, 2, 3)
    E(ands_reg, 3, 1)
    E(cmp_reg, 2, 4)
    E(b_cond, "pd_a", "eq")
    E(cmp_reg, 3, 4)
    E(b_cond, "pd_b", "eq")
    E(cmp_imm, 5, PAD_GATE)                                               # not a line track: pad 6 nothing
    E(b_cond, "pd_x", "eq")
    if fx:
        E(cmp_imm, 5, UI_PAD_SRC)                                         # (fx) nor pad 15
        E(b_cond, "pd_x", "eq")
    E(cmp_imm, 0, 0)                                                      # pad 5: this track in, the older one out when both taken
    E(b_cond, "pd_n1", "ne")
    E(mov_reg, 0, 4)
    E(b, "pd_ad")
    a.label("pd_n1")
    E(cmp_imm, 1, 0)
    E(b_cond, "pd_n2", "eq")
    E(mov_reg, 0, 1)
    a.label("pd_n2")
    E(mov_reg, 1, 4)
    a.label("pd_ad")
    E(bl, "c_liput")
    if "c_gndrop" in L:                                                   # (RH50, granpage multi) the track's granular slot freed
        E(subs_imm8, 4, 1)
        E(mov_reg, 0, 4)
        E(bl, L["c_gndrop"])
        E(b, "pd_x")
    else:
        E(movs_imm, 0, 3)                                                 # the granular engine leaves the track
        E(bl, L["c_gpbyte"])
        E(cmp_reg, 0, 4)
        E(b_cond, "pd_x", "ne")
        E(movs_imm, 0, 3)
        E(movs_imm, 1, 0)
        E(bl, L["c_gpsetb"])
        E(movs_imm, 0, 0)
        E(strb_imm, 0, 6, M_GRAN)
        E(movs_imm, 0, 1)
        E(bl, L["c_gpdirty"])
        E(b, "pd_x")
    a.label("pd_a")                                                       # the first: pad 6 its gate, pad 5 out (the second moves up)
    if fx:
        E(cmp_imm, 5, UI_PAD_SRC)
        E(b_cond, "pd_na", "ne")
        E(bl, "li_nsrc")                                                  # (fx) pad 15: its next source
        E(b, "pd_w")
        a.label("pd_na")
    E(cmp_imm, 5, PAD_GATE)
    E(b_cond, "pd_ra", "ne")
    E(movs_imm, 2, GATE_BIT)
    E(eors_reg, 0, 2)
    E(b, "pd_w")
    a.label("pd_ra")
    E(mov_reg, 0, 1)
    E(movs_imm, 1, 0)
    E(b, "pd_w")
    a.label("pd_b")                                                       # the second: pad 6 its gate, pad 5 out
    if fx:
        E(cmp_imm, 5, UI_PAD_SRC)
        E(b_cond, "pd_nb", "ne")
        E(push_list, [0])
        E(mov_reg, 0, 1)
        E(bl, "li_nsrc")
        E(mov_reg, 1, 0)
        E(pop_list, [0])
        E(b, "pd_w")
        a.label("pd_nb")
    E(cmp_imm, 5, PAD_GATE)
    E(b_cond, "pd_rb", "ne")
    E(movs_imm, 2, GATE_BIT)
    E(eors_reg, 1, 2)
    E(b, "pd_w")
    a.label("pd_rb")
    E(movs_imm, 1, 0)
    a.label("pd_w")
    E(bl, "c_liput")
    a.label("pd_x")
    E(pop_list, [0, 1, 2, 3, 4, 5, 6], pc=True)
    a.label("pd_p")
    E(raw, GP.popw([0, 1, 2, 3, 4, 5, 6], lr=True))
    a.label("pd_s")
    E(b_w, prev["pad"])

    if fx:
        # li_nsrc(r0 = a line track's byte) -> r0 with its next source (0 -> 1 -> 2 -> 0); clobbers r2, r3
        a.label("li_nsrc")
        E(lsrs_imm, 2, 0, SRC_SHIFT)
        E(movs_imm, 3, 3)
        E(ands_reg, 2, 3)
        E(adds_imm8, 2, 1)
        E(cmp_imm, 2, 3)
        E(b_cond, "ns_w", "lo")
        E(movs_imm, 2, 0)
        a.label("ns_w")
        E(movs_imm, 3, SRC_MASK)
        E(bics_reg, 0, 3)
        E(lsls_imm, 2, 2, SRC_SHIFT)
        E(orrs_reg, 0, 2)
        E(raw, h(0x4770))                                                 # bx lr

    _liw(a, E)

    # ---- c_liwk(r0 = 0..4; r6 = the lower line track's byte, r7 = the higher's, 0 = none): LTRK / LGATE / LTRK2 / LGATE2 / LKEY into
    # core 0; clobbers r0-r3, r12
    a.label("c_liwk")
    E(push_list, [4], lr=True)
    E(cmp_imm, 0, 1)
    E(b_cond, "wk_g0", "eq")
    E(cmp_imm, 0, 2)
    E(b_cond, "wk_t1", "eq")
    E(cmp_imm, 0, 3)
    E(b_cond, "wk_g1", "eq")
    if fx:
        E(cmp_imm, 0, 4)
        E(b_cond, "wk_s0", "eq")
        E(cmp_imm, 0, 5)
        E(b_cond, "wk_s1", "eq")
        E(cmp_imm, 0, 6)
    else:
        E(cmp_imm, 0, 4)
    E(b_cond, "wk_k", "eq")
    E(movs_imm, 0, 15)                                                    # 0: the lower track
    E(ands_reg, 0, 6)
    E(subs_imm8, 0, 1)
    E(movs_imm, 1, 7)
    E(ands_reg, 0, 1)
    E(movw, 1, LTRK)
    E(b, "wk_w")
    a.label("wk_g0")                                                      # 1: its gate
    E(lsrs_imm, 0, 6, 4)
    E(movs_imm, 1, 1)
    E(ands_reg, 0, 1)
    E(movw, 1, LGATE)
    E(b, "wk_w")
    a.label("wk_t1")                                                      # 2: the higher track | SLOT2, 0 = none
    E(movs_imm, 0, 15)
    E(ands_reg, 0, 7)
    E(b_cond, "wk_t1w", "eq")
    E(subs_imm8, 0, 1)
    E(movs_imm, 1, SLOT2)
    E(orrs_reg, 0, 1)
    a.label("wk_t1w")
    E(movw, 1, LTRK2)
    E(b, "wk_w")
    a.label("wk_g1")                                                      # 3: its gate
    E(lsrs_imm, 0, 7, 4)
    E(movs_imm, 1, 1)
    E(ands_reg, 0, 1)
    E(movw, 1, LGATE2)
    E(b, "wk_w")
    if fx:
        a.label("wk_s0")                                                  # (fx) 4 / 5: the sources
        E(lsrs_imm, 0, 6, SRC_SHIFT)
        E(movs_imm, 1, 3)
        E(ands_reg, 0, 1)
        E(movw, 1, LSRC)
        E(b, "wk_w")
        a.label("wk_s1")
        E(lsrs_imm, 0, 7, SRC_SHIFT)
        E(movs_imm, 1, 3)
        E(ands_reg, 0, 1)
        E(movw, 1, LSRC2)
        E(b, "wk_w")
    a.label("wk_k")                                                       # 4: the key
    imm32(0, KEY)
    E(cmp_imm, 6, 0)
    E(b_cond, "wk_kk", "ne")
    E(movs_imm, 0, 0)
    a.label("wk_kk")
    E(movw, 1, LKEY)
    a.label("wk_w")
    E(bl, "c_liw")
    E(pop_list, [4], pc=True)

    # ---- c_liled (the LED task's calls: ctrl, frame): the chain; the DSP words; the menu's pads 5 / 6
    a.label("c_liled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ll_x", "eq")
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ll_x", "eq")
    E(ldrb_w, 1, 0, O_TH)
    E(cmp_imm, 1, TH.READY)
    E(b_cond, "ll_m", "ne")                                               # core 0 not seen up: no words
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ll_m", "eq")
    E(bl, "c_liram")
    E(cmp_imm, 0, 0)
    E(b_cond, "ll_m", "eq")
    E(mov_reg, 4, 0)                                                      # r4 = our RAM
    E(bl, "c_liget")
    E(mov_reg, 6, 0)                                                      # r6 = the lower line track's byte, r7 = the higher's
    E(mov_reg, 7, 1)
    E(cmp_imm, 1, 0)
    E(b_cond, "ll_s", "eq")
    E(movs_imm, 2, 15)
    E(mov_reg, 3, 0)
    E(ands_reg, 3, 2)
    E(ands_reg, 2, 1)
    E(cmp_reg, 3, 2)
    E(b_cond, "ll_s", "lo")
    E(mov_reg, 6, 1)
    E(mov_reg, 7, 0)
    a.label("ll_s")
    E(ldrb_imm, 0, 4, R_SENT)                                             # the pair changed (or never sent): the five now, the key last
    E(cmp_imm, 0, 0)
    E(b_cond, "ll_all", "eq")
    E(ldrb_imm, 0, 4, R_LO)
    E(cmp_reg, 0, 6)
    E(b_cond, "ll_all", "ne")
    E(ldrb_imm, 0, 4, R_HI)
    E(cmp_reg, 0, 7)
    E(b_cond, "ll_one", "eq")
    a.label("ll_all")
    E(movs_imm, 0, 1)
    E(strb_imm, 0, 4, R_SENT)
    E(strb_imm, 6, 4, R_LO)
    E(strb_imm, 7, 4, R_HI)
    nw = NW + 2 if fx else NW
    for k in range(nw):
        E(movs_imm, 0, k)
        E(bl, "c_liwk")
    E(b, "ll_m")
    a.label("ll_one")                                                     # else one a frame
    E(ldrb_imm, 0, 4, R_ROUND)
    E(adds_imm8, 0, 1)
    E(cmp_imm, 0, nw)
    E(b_cond, "ll_rw", "lo")
    E(movs_imm, 0, 0)
    a.label("ll_rw")
    E(strb_imm, 0, 4, R_ROUND)
    E(bl, "c_liwk")
    a.label("ll_m")
    E(bl, L["c_gpmopen"])                                                 # the menu open: pads 5 / 6
    E(cmp_imm, 0, 8)
    E(b_cond, "ll_x", "hs")
    E(adds_imm8, 0, 1)
    E(mov_reg, 4, 0)                                                      # r4 = the menu's track + 1
    E(bl, "c_liget")
    E(movs_imm, 2, 15)
    E(mov_reg, 3, 0)
    E(ands_reg, 3, 2)
    E(cmp_reg, 3, 4)
    E(b_cond, "ll_on", "eq")
    E(mov_reg, 0, 1)
    E(ands_reg, 2, 0)
    E(cmp_reg, 2, 4)
    E(b_cond, "ll_on", "eq")
    if ui:                                                                # not a line track: pad 13 dim, pad 14 dark
        E(movs_imm, 0, UI_DIM)
    else:
        imm32(1, PAL + PAL_TOFF)                                          # not a line track: pad 5 off, pad 6 dark
        E(raw, h(0x8808))                                                 # ldrh r0, [r1]
    E(strh_imm, 0, 5, 2 * PAD_LINE)
    E(movs_imm, 0, 0)
    E(strh_imm, 0, 5, 2 * PAD_GATE)
    if fx:
        E(strh_imm, 0, 5, 2 * UI_PAD_SRC)
    E(b, "ll_x")
    a.label("ll_on")                                                      # r0 = its byte
    E(mov_reg, 7, 0)
    if ui:
        E(movs_imm, 0, UI_COL)
    else:
        imm32(1, PAL + PAL_TON)
        E(raw, h(0x8808))
    E(strh_imm, 0, 5, 2 * PAD_LINE)
    if ui:
        E(movs_imm, 0, UI_DIM)
        E(movs_imm, 2, GATE_BIT)
        E(tst_reg, 7, 2)
        E(b_cond, "ll_g", "eq")
        E(movs_imm, 0, UI_COL)
        a.label("ll_g")
    else:
        imm32(1, PAL + PAL_OFF)
        E(movs_imm, 2, GATE_BIT)
        E(tst_reg, 7, 2)
        E(b_cond, "ll_g", "eq")
        imm32(1, PAL + PAL_ON)
        a.label("ll_g")
        E(raw, h(0x8808))
    E(strh_imm, 0, 5, 2 * PAD_GATE)
    if fx:                                                                # (fx) pad 15: its source's colour
        E(lsrs_imm, 0, 7, SRC_SHIFT)
        E(movs_imm, 1, 3)
        E(ands_reg, 0, 1)
        E(movs_imm, 1, SRC_COLS[0])
        E(cmp_imm, 0, 1)
        E(b_cond, "ll_c1", "ne")
        E(movs_imm, 1, SRC_COLS[1])
        a.label("ll_c1")
        E(cmp_imm, 0, 2)
        E(b_cond, "ll_c2", "ne")
        E(movs_imm, 1, SRC_COLS[2])
        a.label("ll_c2")
        E(strh_imm, 1, 5, 2 * UI_PAD_SRC)
    a.label("ll_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)


def arm_code(base, L, prev, two=False, ui=False, fx=False):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_liblk() -> r0 = our block when valid, else 0; r1 = its place (0 without a record); clobbers r2, r3
    a.label("c_liblk")
    E(push_list, [4], lr=True)
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "lb_0", "eq")
    E(movw, 1, BLK)
    E(adds_reg, 0, 0, 1)
    E(mov_reg, 1, 0)
    E(ldrb_imm, 2, 0, 0)
    E(cmp_imm, 2, MARK)
    E(b_cond, "lb_n", "ne")
    E(ldrb_imm, 2, 0, 2)
    E(ldrb_imm, 3, 0, 3)
    E(eors_reg, 2, 3)
    E(movs_imm, 3, (CHECK2 if two else CHECK) ^ MARK)
    E(eors_reg, 2, 3)
    E(ldrb_imm, 3, 0, 1)
    E(cmp_reg, 2, 3)
    E(b_cond, "lb_x", "eq")
    a.label("lb_n")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)
    a.label("lb_0")
    E(movs_imm, 1, 0)
    a.label("lb_x")
    E(pop_list, [4], pc=True)

    # ---- c_liget() -> r0 = the line track + 1 (0 = none), r1 = the gate; clobbers r2, r3
    a.label("c_liget")
    E(push_list, [4], lr=True)
    E(bl, "c_liblk")
    E(cmp_imm, 0, 0)
    E(b_cond, "lg_0", "eq")
    E(ldrb_imm, 1, 0, 3)
    E(ldrb_imm, 0, 0, 2)
    E(pop_list, [4], pc=True)
    a.label("lg_0")
    E(movs_imm, 1, 0)
    E(pop_list, [4], pc=True)

    # ---- c_liput(r0 = the line track + 1, r1 = the gate): the block made when missing, the check, the DSP words to send; clobbers r0-r3
    a.label("c_liput")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(bl, "c_liblk")
    E(cmp_imm, 1, 0)
    E(b_cond, "lp_x", "eq")
    E(movs_imm, 0, MARK)
    E(strb_imm, 0, 1, 0)
    E(strb_imm, 4, 1, 2)
    E(strb_imm, 5, 1, 3)
    E(eors_reg, 4, 5)
    E(movs_imm, 0, (CHECK2 if two else CHECK) ^ MARK)
    E(eors_reg, 4, 0)
    E(strb_imm, 4, 1, 1)
    if not two:                                                           # (two: the LED task sees the change)
        E(bl, "c_liram")
        E(cmp_imm, 0, 0)
        E(b_cond, "lp_x", "eq")
        E(movs_imm, 1, 1)
        E(strb_imm, 1, 0, R_DIRTY)
    a.label("lp_x")
    E(pop_list, [4, 5], pc=True)

    # ---- c_liram() -> r0 = our RAM, 0 without it; clobbers r1-r3
    a.label("c_liram")
    E(push_list, [4], lr=True)
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "lr_x", "eq")
    E(movw, 1, O)
    E(adds_reg, 0, 0, 1)
    a.label("lr_x")
    E(pop_list, [4], pc=True)
    if two:
        _arm2(a, E, imm32, L, prev, ui, fx)
        return a.assemble()

    # ---- c_lipad (the controller's pad press, granpage's head after it): the menu open, pads 5 / 6 are ours
    a.label("c_lipad")
    E(cmp_imm, 1, PAD_LINE)
    E(b_cond, "pd_s", "lo")
    E(cmp_imm, 1, UI_PAD_SRC if fx else PAD_GATE)
    E(b_cond, "pd_s", "hi")
    E(push_list, [0, 1, 2, 3, 4, 5, 6], lr=True)
    E(mov_reg, 5, 1)
    E(bl, L["c_gpmopen"])
    E(cmp_imm, 0, 8)
    E(b_cond, "pd_p", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the menu's track
    E(bl, L["c_gpmst"])                                                   # its release swallowed by the menu's
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 5)
    E(ldr_imm, 2, 0, M_SWAL)
    E(orrs_reg, 2, 1)
    E(str_imm, 2, 0, M_SWAL)
    E(mov_reg, 6, 0)                                                      # r6 = the menu state
    E(bl, "c_liget")
    E(cmp_imm, 5, PAD_GATE)
    E(b_cond, "pd_l", "ne")
    E(movs_imm, 2, 1)                                                     # pad 6: the gate
    E(eors_reg, 1, 2)
    E(bl, "c_liput")
    E(b, "pd_x")
    a.label("pd_l")                                                       # pad 5: the line input on this track / off
    E(mov_reg, 2, 4)
    E(adds_imm8, 2, 1)
    E(cmp_reg, 0, 2)
    E(b_cond, "pd_off", "eq")
    E(mov_reg, 0, 2)
    E(b, "pd_w")
    a.label("pd_off")
    E(movs_imm, 0, 0)
    a.label("pd_w")
    E(bl, "c_liput")
    E(movs_imm, 0, 3)                                                     # the granular engine leaves the track
    E(bl, L["c_gpbyte"])
    E(raw, h(0x1E40))                                                     # subs r0, r0, #1
    E(cmp_reg, 0, 4)
    E(b_cond, "pd_x", "ne")
    E(movs_imm, 0, 3)
    E(movs_imm, 1, 0)
    E(bl, L["c_gpsetb"])
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 6, M_GRAN)
    E(movs_imm, 0, 1)
    E(bl, L["c_gpdirty"])
    a.label("pd_x")
    E(pop_list, [0, 1, 2, 3, 4, 5, 6], pc=True)
    a.label("pd_p")
    E(raw, GP.popw([0, 1, 2, 3, 4, 5, 6], lr=True))
    a.label("pd_s")
    E(b_w, prev["pad"])

    _liw(a, E)

    # ---- c_liwk(r0 = 0 / 1 / 2; r6 = the track + 1, r7 = the gate): LTRK / LGATE / LKEY into core 0; clobbers r0-r3, r12
    a.label("c_liwk")
    E(push_list, [4], lr=True)
    E(cmp_imm, 0, 1)
    E(b_cond, "wk_g", "eq")
    E(b_cond, "wk_k", "hi")
    E(raw, h(0x1E70))                                                     # subs r0, r6, #1: the track
    E(movs_imm, 1, 7)
    E(raw, h(0x4008))                                                     # ands r0, r1
    E(movw, 1, LTRK)
    E(b, "wk_w")
    a.label("wk_g")
    E(mov_reg, 0, 7)
    E(movw, 1, LGATE)
    E(b, "wk_w")
    a.label("wk_k")
    imm32(0, KEY)
    E(cmp_imm, 6, 0)
    E(b_cond, "wk_kk", "ne")
    E(movs_imm, 0, 0)
    a.label("wk_kk")
    E(movw, 1, LKEY)
    a.label("wk_w")
    E(bl, "c_liw")
    E(pop_list, [4], pc=True)

    # ---- c_liled (the LED task's calls: ctrl, frame): the chain; the DSP words; the menu's pads 5 / 6
    a.label("c_liled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ll_x", "eq")
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ll_x", "eq")
    E(ldrb_w, 1, 0, O_TH)
    E(cmp_imm, 1, TH.READY)
    E(b_cond, "ll_m", "ne")                                               # core 0 not seen up: no words
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ll_m", "eq")
    E(bl, "c_liram")
    E(cmp_imm, 0, 0)
    E(b_cond, "ll_m", "eq")
    E(mov_reg, 4, 0)                                                      # r4 = our RAM
    E(bl, "c_liget")
    E(mov_reg, 6, 0)                                                      # r6 = the track + 1
    E(mov_reg, 7, 1)                                                      # r7 = the gate
    E(ldrb_imm, 0, 4, R_DIRTY)
    E(cmp_imm, 0, 0)
    E(b_cond, "ll_one", "eq")
    E(movs_imm, 0, 0)                                                     # changed: the three now, the key last
    E(strb_imm, 0, 4, R_DIRTY)
    for k in range(3):
        E(movs_imm, 0, k)
        E(bl, "c_liwk")
    E(b, "ll_m")
    a.label("ll_one")                                                     # else one a frame
    E(ldrb_imm, 0, 4, R_ROUND)
    E(adds_imm8, 0, 1)
    E(cmp_imm, 0, 3)
    E(b_cond, "ll_rw", "lo")
    E(movs_imm, 0, 0)
    a.label("ll_rw")
    E(strb_imm, 0, 4, R_ROUND)
    E(bl, "c_liwk")
    a.label("ll_m")
    E(bl, L["c_gpmopen"])                                                 # the menu open: pads 5 / 6
    E(cmp_imm, 0, 8)
    E(b_cond, "ll_x", "hs")
    E(mov_reg, 4, 0)
    E(bl, "c_liget")
    E(mov_reg, 7, 1)
    imm32(1, PAL + PAL_TOFF)
    E(adds_imm8, 4, 1)
    E(cmp_reg, 0, 4)
    E(b_cond, "ll_t", "ne")
    imm32(1, PAL + PAL_TON)
    a.label("ll_t")
    E(raw, h(0x8808))                                                     # ldrh r0, [r1]
    E(strh_imm, 0, 5, 2 * PAD_LINE)
    imm32(1, PAL + PAL_OFF)
    E(cmp_imm, 7, 0)
    E(b_cond, "ll_g", "eq")
    imm32(1, PAL + PAL_ON)
    a.label("ll_g")
    E(raw, h(0x8808))
    E(strh_imm, 0, 5, 2 * PAD_GATE)
    a.label("ll_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr, two=False, ui=False, fx=False):
    """The controller's pad press (in front of granpage v2's head), the head of the LED calls.  core 0's LI goes in through granular0's extra
    (segs, with the same two).  Needs granpage v2, cthresh, rhrec, rhstate ram2."""
    import rhbuild
    BASE = rhbuild.BASE
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    assert "c_gpmopen" in report["granpage"]["labels"], "linein needs granpage v2"
    L = dict(c_rst=lab("rhstate", "c_rst"), c_rram=lab("rhstate", "c_rram"), c_rrt=lab("rhrec", "c_rrt"), c_ciok=lab("countin", "c_ciok"),
             **{k: lab("granpage", k) for k in ("c_gpmopen", "c_gpmst", "c_gpbyte", "c_gpsetb", "c_gpdirty")})
    if report["granpage"].get("multi"):
        assert two, "linein with granpage multi needs two"
        L["c_gndrop"] = lab("granpage", "c_gndrop")
    prev = dict(pad=rhbuild.bw_target(img, PP_ENTRY), ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert prev["pad"] == lab("granpage", "c_gpmpad")
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    assert two or not ui
    assert ui or not fx
    code_, labels = arm_code(base_addr, L, prev, two, ui, fx)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code_
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, PP_ENTRY, f"b.w #{prev['pad']:#x}", b_w(PP_ENTRY, labels["c_lipad"]))
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_liled"]))
    report["linein"] = dict(prev={k: hex(v) for k, v in prev.items()}, **({"ui": True} if ui else {}), **({"fx": True} if fx else {}), labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code_
