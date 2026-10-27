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
from thumb import (Asm, adds_imm8, adds_reg, ands_reg, b, b_cond, b_w, bl, cmp_imm, cmp_reg, eors_reg, h, ldr_imm, ldrb_imm, ldrb_w,  # noqa: E402
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


def items(spl, two=False):
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


def code(spl, two=False):
    w, labels = C0.asm_at(items(spl, two), AT)
    assert AT + len(w) <= C0.LD, hex(AT + len(w))
    return w, labels


def segs(spl, two=False):
    """for granular0's extra, after stsplit's: our code at P:AT and P:$224 -> jsr LI (the loader writes it last)"""
    w, labels = code(spl, two)
    return [(AT, w), (HOOK, [0x0BF080, labels["li"]])]


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


def _arm2(a, E, imm32, L, prev):
    """(two) c_lipad, c_liw, c_liwk, c_liled"""
    # ---- c_lipad (the controller's pad press, granpage's head after it): the menu open, pads 5 / 6 are ours
    a.label("c_lipad")
    E(cmp_imm, 1, PAD_LINE)
    E(b_cond, "pd_s", "lo")
    E(cmp_imm, 1, PAD_GATE)
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
    for k in range(NW):
        E(movs_imm, 0, k)
        E(bl, "c_liwk")
    E(b, "ll_m")
    a.label("ll_one")                                                     # else one a frame
    E(ldrb_imm, 0, 4, R_ROUND)
    E(adds_imm8, 0, 1)
    E(cmp_imm, 0, NW)
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
    imm32(1, PAL + PAL_TOFF)                                              # not a line track: pad 5 off, pad 6 dark
    E(raw, h(0x8808))                                                     # ldrh r0, [r1]
    E(strh_imm, 0, 5, 2 * PAD_LINE)
    E(movs_imm, 0, 0)
    E(strh_imm, 0, 5, 2 * PAD_GATE)
    E(b, "ll_x")
    a.label("ll_on")                                                      # r0 = its byte
    E(mov_reg, 7, 0)
    imm32(1, PAL + PAL_TON)
    E(raw, h(0x8808))
    E(strh_imm, 0, 5, 2 * PAD_LINE)
    imm32(1, PAL + PAL_OFF)
    E(movs_imm, 2, GATE_BIT)
    E(tst_reg, 7, 2)
    E(b_cond, "ll_g", "eq")
    imm32(1, PAL + PAL_ON)
    a.label("ll_g")
    E(raw, h(0x8808))
    E(strh_imm, 0, 5, 2 * PAD_GATE)
    a.label("ll_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)


def arm_code(base, L, prev, two=False):
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
        _arm2(a, E, imm32, L, prev)
        return a.assemble()

    # ---- c_lipad (the controller's pad press, granpage's head after it): the menu open, pads 5 / 6 are ours
    a.label("c_lipad")
    E(cmp_imm, 1, PAD_LINE)
    E(b_cond, "pd_s", "lo")
    E(cmp_imm, 1, PAD_GATE)
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


def install(img, report, base_addr, two=False):
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
    code_, labels = arm_code(base_addr, L, prev, two)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code_
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, PP_ENTRY, f"b.w #{prev['pad']:#x}", b_w(PP_ENTRY, labels["c_lipad"]))
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_liled"]))
    report["linein"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code_
