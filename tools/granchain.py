"""The stock's VCA and a filter of ours after the granular, on DSP core 0 (MIT; RD30, docs/PRUEBA_RD30.md).  The user, 2026-10-26: «¿Es
posible mantener VCA, VCF y efectos a continuación del granular?» -> «A, cadena propia».

granular0's GR replaces the granular track's 32 samples (core 1's voice: already through the stock's filter, envelope, Stock+ and the
end-of-sample fade) with the grains, so none of that reached the granular.  Ours, from GR's end (granular0 post=AT: after its block and
g_rest, in place of `jmp $367`), on the granular track T, only while the voice's words say so, then the stock's mix:
  * the VCA: the voice's envelope x gain that core 1 leaves in Y:$37400 + 16 T (tools/envexp.py) x its end-of-sample fade Y:$37302 + 2 T
    (the stock's, shared), a block late, ramped across the block;
  * a state-variable filter (Chamberlin's, 2x oversampled), low-pass then high-pass, from the track's own knobs as the ARM leaves them for
    core 1 in shared memory (Y:$307C8 + $20 T: + $B the high-pass index, + $C the low-pass index, + $D the resonance; the index into the
    stock's cutoff curve, core 1's X:$2A4E, 129 words: c doubles every 12, ~262 Hz at 64, ~7.7 kHz at 127); f = 2 sin(asin(c / 2) / 2)
    per pass (the table F2), smoothed 1/8 a block; damping q = 1.86 - 1.8 r / 128 (the table Q2 holds q / 2); the low-pass is skipped
    at 127 (open), the high-pass at 0;
  * the switch: Y:SW = OFFKEY (tools/rhgran.py chain off) = RH43's granular, without the chain; anything else (power-up too) = on.
Core 0's Y from $1500 (free: docs/RECURSOS.md; granular0 uses $1410-$1457, stsplit $1F00..): MAGIC (else state and the shared export
cleared once), the switch, the track seen, the VCA now / its step, the filter's f now (low / high), its states (L, B a filter).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core0 as C0  # noqa: E402
import envexp as EX  # noqa: E402
import granular0 as G  # noqa: E402

AT = 0x2B00                                        # P (stsplit's split ends at $2884)
MIX = 0x367
Y0 = 0x1500
(C_MAG, C_SW, C_T, C_GC, C_GS, C_FL, C_FH, C_LL, C_LB, C_HL, C_HB, C_LON, C_HON, C_QL, C_TFL, C_TFH) = range(Y0, Y0 + 16)
MAGIC, OFFKEY = 0x6C4A1E, 0x0FF0FF
PAR, FADE = 0x307C8, 0x37302
HP_I, LP_I, RES_I = 0xB, 0xC, 0xD
LP_OPEN, HP_OPEN = 127, 0
CURVE_AT, CURVE_N = 0x2A4E, 129                    # core 1's X: the stock's cutoff curve
(C2_LL, C2_LB, C2_HL, C2_HB, C_G0, C_GT) = range(Y0 + 16, Y0 + 22)   # (RH47, stereo) the side's filter states, the VCA at the block's start, its run
# (RH50, multi) one chain per granular slot (granular0 multi): each slot's 20 state words (C_T .. C_GT) at CHY + $20 s, copied into
# Y0 + 2 .. and back around c_blk; c_blk takes the slot's track, buffer and side out from CIN_T / CIN_BUF / CIN_SB; CMAG2 = the slots'
# states made once.  At P:AT_M.
AT_M = 0x3700
AT_E = 0x3B00                                      # (RH54, env) the chain with the envelope: bigger than AT_M's room (gstereo at $3A00); free to $3FDF


def place(multi=False, env=False):
    """where the chain goes (granular0's post jumps there)"""
    return AT_E if env else AT_M if multi else AT
CHY, CH_N, NST = 0x1980, 0x20, 20
CIN_T, CIN_BUF, CIN_SB, CMAG2 = range(Y0 + 22, Y0 + 26)
# (RH54, env; needs multi and synth0 env2) a slot whose envelope block (synth0.GE0 + $40 k: its key, its track = the slot's) is on takes
# the envelope instead of the voice's: the VCA's target = its S_VCA (envelope x velocity), the low-pass index + C_EF x S_ENV (as the
# synth's); CIN_GE = that block (0 = the voice's VCA, as before)
CIN_GE = Y0 + 26


def stock_curve():
    import rhdspemu
    for sp, a, ws in rhdspemu.segments(1):
        if sp == "x" and a <= CURVE_AT and CURVE_AT + CURVE_N <= a + len(ws):
            return [(v - (1 << 24) if v & 0x800000 else v) / (1 << 23) for v in ws[CURVE_AT - a:CURVE_AT - a + CURVE_N]]
    raise SystemExit("core 1's cutoff curve not found")


def frac(x):
    return max(-(1 << 23), min((1 << 23) - 1, round(x * (1 << 23)))) & 0xFFFFFF


def f2_of(c):
    return 2 * math.sin(math.asin(min(c, 1.999) / 2) / 2)


def q_of(r):
    return 1.86 - 1.8 * r / 128


def tables():
    return dict(F2=[frac(f2_of(c)) for c in stock_curve()], Q2=[frac(q_of(r) / 2) for r in range(128)])


def items(tab_at, gr, stereo=False, multi=False, env=False):
    L = []

    def e(*s):
        L.extend(s)

    def yv(a):
        return f"y:>${a:x}"

    # ---- CH: from GR's end (the stock's registers back); the switch, then our block with GR's own save / restore, then the mix
    if multi:                                                                      # (multi) each running slot's chain, its states in and out
        import granular0 as G0
        e(("label", "ch"), f"move {yv(C_SW)},a", f"move #>${OFFKEY:x},x0", "cmp x0,a", ("jcc", "eq", MIX), ("jsr", gr["g_save"]),
          f"move {yv(CMAG2)},a", f"move #>${MAGIC:x},x0", "cmp x0,a", ("jcc", "eq", "c_m2"),
          "clr a", f"move #>${CHY:x},r0", "nop", f"do #${G0.NSLOT * CH_N:x},${{c_z0:x}}", "move a,y:(r0)+", ("label", "c_z0"),
          "move #>$ff,a", *[f"move a1,y:>${CHY + CH_N * k:x}" for k in range(G0.NSLOT)], f"move x0,{yv(CMAG2)}", ("label", "c_m2"))
        for k in range(G0.NSLOT):
            v = G0.slot_y(k) + 0x10
            e(f"move y:>${v + G0.V_ACT:x},a", "tst a", ("jcc", "eq", f"c_n{k}"), f"move y:>${v + G0.V_ON:x},a", "tst a",
              ("jcc", "eq", f"c_n{k}"),
              f"move y:>${v + G0.V_T:x},x0", f"move x0,{yv(CIN_T)}", f"move y:>${v + G0.V_BUF:x},x0", f"move x0,{yv(CIN_BUF)}",
              f"move #>${G0.SBY + 0x20 * k:x},x0", f"move x0,{yv(CIN_SB)}",
              *(_ge_pick(k, v, G0) if env else []),
              f"move #>${CHY + CH_N * k:x},r0", f"move #>${C_T:x},r1", "nop", f"do #${NST:x},${{c_i{k}:x}}", "move y:(r0)+,x0",
              "move x0,y:(r1)+", ("label", f"c_i{k}"),
              ("jsr", "c_blk"),
              f"move #>${C_T:x},r0", f"move #>${CHY + CH_N * k:x},r1", "nop", f"do #${NST:x},${{c_o{k}:x}}", "move y:(r0)+,x0",
              "move x0,y:(r1)+", ("label", f"c_o{k}"),
              ("label", f"c_n{k}"))
        e(("jsr", gr["g_rest"]), ("jmp", MIX))
    else:
        e(("label", "ch"), f"move {yv(C_SW)},a", f"move #>${OFFKEY:x},x0", "cmp x0,a", ("jcc", "eq", MIX),
          ("jsr", gr["g_save"]), ("jsr", "c_blk"), ("jsr", gr["g_rest"]), ("jmp", MIX))
    # ---- c_blk
    e(("label", "c_blk"), f"move {yv(C_MAG)},a", f"move #>${MAGIC:x},x0", "cmp x0,a", ("jcc", "eq", "c_ok"),
      "clr a", f"move #>${Y0 + 2:x},r0", "nop", f"do #${14 + (6 if stereo else 0):x},${{c_z1:x}}", "move a,y:(r0)+", ("label", "c_z1"),
      f"move #>${EX.SHARED:x},r0", "nop", "do #$80,${c_z2:x}", "move a,y:(r0)+", ("label", "c_z2"),
      f"move x0,{yv(C_MAG)}", "move #>$ff,x0", f"move x0,{yv(C_T)}",
      ("label", "c_ok"))
    # the track; a new one: the states from zero
    e(f"move {yv(CIN_T)},a" if multi else f"move x:>${G.VS + G.V_T:x},a", "and #>$7,a", "move a1,a", f"move {yv(C_T)},b", "cmp a,b",
      ("jcc", "eq", "c_same"),
      f"move a1,{yv(C_T)}", "clr b", f"move b,{yv(C_GC)}", f"move b,{yv(C_LL)}", f"move b,{yv(C_LB)}", f"move b,{yv(C_HL)}",
      f"move b,{yv(C_HB)}", *([f"move b,{yv(r)}" for r in (C2_LL, C2_LB, C2_HL, C2_HB)] if stereo else []), ("label", "c_same"))
    # ---- the VCA's target: Y:$37400 + 16 T x Y:$37302 + 2 T; the step over the block
    e("tfr a,b", "asl #4,b,b", f"add #>${EX.SHARED:x},b", "move b1,r2",
      "tfr a,b", "asl #1,b,b", f"add #>${FADE:x},b", "move b1,r3",
      "tfr a,b", "asl #5,b,b", f"add #>${PAR:x},b", "move b1,r1", "nop",
      *(_ge_vca() if env else ["move y:(r2),x0", "move y:(r3),x1", "mpy x1,x0,a"]),
      f"move {yv(C_GC)},b", "sub b,a", "asr #5,a,a", f"move a,{yv(C_GS)}")
    # ---- the filter's words: the low-pass (index < 127), the high-pass (index > 0), their f smoothed 1/8 a block, the damping
    e(f"move y:(r1+${LP_I:x}),a", "and #>$7f,a", "move a1,a", *(_ge_lp() if env else []),
      f"move #>${LP_OPEN:x},x0", "clr b", "cmp x0,a", ("jcc", "ge", "c_lpoff"),
      "move #>$1,b", f"add #>${tab_at['F2']:x},a", "move a1,r4", "nop", "move p:(r4),x0", f"move x0,{yv(C_TFL)}",
      f"move {yv(C_LON)},a", "tst a", ("jcc", "ne", "c_lpon"),                     # turned on: from its target, the state from zero
      f"move x0,{yv(C_FL)}", "clr a", f"move a,{yv(C_LL)}", f"move a,{yv(C_LB)}",
      *([f"move a,{yv(C2_LL)}", f"move a,{yv(C2_LB)}"] if stereo else []),
      ("label", "c_lpon"), ("label", "c_lpoff"), f"move b,{yv(C_LON)}")
    e(f"move y:(r1+${HP_I:x}),a", "and #>$7f,a", "move a1,a", "clr b", "tst a", ("jcc", "eq", "c_hpoff"),
      "move #>$1,b", f"add #>${tab_at['F2']:x},a", "move a1,r4", "nop", "move p:(r4),x0", f"move x0,{yv(C_TFH)}",
      f"move {yv(C_HON)},a", "tst a", ("jcc", "ne", "c_hpon"),
      f"move x0,{yv(C_FH)}", "clr a", f"move a,{yv(C_HL)}", f"move a,{yv(C_HB)}",
      *([f"move a,{yv(C2_HL)}", f"move a,{yv(C2_HB)}"] if stereo else []),
      ("label", "c_hpon"), ("label", "c_hpoff"), f"move b,{yv(C_HON)}")
    for fn, tf in ((C_FL, C_TFL), (C_FH, C_TFH)):                                  # f += (target - f) / 8
        e(f"move {yv(tf)},a", f"move {yv(fn)},b", "sub b,a", "asr #3,a,a", "add b,a", f"move a,{yv(fn)}")
    e(f"move y:(r1+${RES_I:x}),a", "and #>$7f,a", "move a1,a", f"add #>${tab_at['Q2']:x},a", "move a1,r4", "nop", "move p:(r4),x0",
      f"move x0,{yv(C_QL)}")
    # ---- the 32 samples: low-pass, high-pass, VCA
    if stereo:                                                                     # (stereo) the VCA's start, for the side
        e(f"move {yv(C_GC)},a", f"move a,{yv(C_G0)}")
    e(f"move {yv(CIN_BUF)},r0" if multi else f"move x:>${G.VS + G.V_BUF:x},r0", "nop",
      "do #$20,${c_end:x}",
      "move y:(r0),x1",
      f"move {yv(C_LON)},a", "tst a", ("jcc", "eq", "c_s1"),
      f"move #>${C_LL:x},r4", f"move {yv(C_FL)},x0", f"move {yv(C_QL)},y0", ("jsr", "c_svf"), "move y:(r4),x1",
      ("label", "c_s1"),
      f"move {yv(C_HON)},a", "tst a", ("jcc", "eq", "c_s2"),
      f"move #>${C_HL:x},r4", f"move {yv(C_FH)},x0", f"move {yv(C_QL)},y0", ("jsr", "c_svf"), "move y1,x1",
      ("label", "c_s2"),
      f"move {yv(C_GC)},a", f"move {yv(C_GS)},b", "add b,a", f"move a,{yv(C_GC)}", "move a,x0", "mpy x1,x0,a", "move a,y:(r0)+",
      ("label", "c_end"))
    if stereo:                                                                     # (stereo) the side SB: the same filters (its own states), the same VCA
        e(f"move {yv(CIN_SB)},r0" if multi else f"move #>${G.SB:x},r0", f"move {yv(C_G0)},a", f"move a,{yv(C_GT)}",
          "do #$20,${c2_end:x}",
          "move y:(r0),x1",
          f"move {yv(C_LON)},a", "tst a", ("jcc", "eq", "c2_s1"),
          f"move #>${C2_LL:x},r4", f"move {yv(C_FL)},x0", f"move {yv(C_QL)},y0", ("jsr", "c_svf"), "move y:(r4),x1",
          ("label", "c2_s1"),
          f"move {yv(C_HON)},a", "tst a", ("jcc", "eq", "c2_s2"),
          f"move #>${C2_HL:x},r4", f"move {yv(C_FH)},x0", f"move {yv(C_QL)},y0", ("jsr", "c_svf"), "move y1,x1",
          ("label", "c2_s2"),
          f"move {yv(C_GT)},a", f"move {yv(C_GS)},b", "add b,a", f"move a,{yv(C_GT)}", "move a,x0", "mpy x1,x0,a", "move a,y:(r0)+",
          ("label", "c2_end"))
    e("rts")
    # ---- c_svf: two passes of Chamberlin's filter; in x1, f x0, q / 2 y0, the state L, B at y:(r4), y:(r4 + 1) -> L there, H in y1
    e(("label", "c_svf"), "do #$2,${c_sv:x}",
      "move y:(r4)+,a", "move y:(r4)-,y1", "mac x0,y1,a", "move a,y:(r4)",          # L += f B
      "move x1,b", "sub a,b", "mac -y1,y0,b", "mac -y1,y0,b",                        # H = in - L - q B
      "tfr y1,a", "move b,y1", "mac x0,y1,a", "move a,y:(r4+$1)",                     # B += f H
      ("label", "c_sv"), "rts")
    return L


def _ge_pick(k, v, G0):
    """(env) CIN_GE = slot k's envelope block when its key is on and its track is the slot's, else 0"""
    import synth0 as SY
    ge = SY.GE0 + SY.SN * k
    return [f"move y:>${ge + SY.C_KEY:x},a", f"move #>${SY.KEY:x},x0", "cmp x0,a", ("jcc", "ne", f"ge_n{k}"),
            f"move y:>${v + G0.V_T:x},a", "and #>$7,a", "move a1,a", "add #>$1,a", f"move y:>${ge + SY.C_TRK:x},x0", "cmp x0,a",
            ("jcc", "ne", f"ge_n{k}"), f"move #>${ge:x},x0", f"move x0,y:>${CIN_GE:x}", ("jmp", f"ge_y{k}"),
            ("label", f"ge_n{k}"), "clr a", f"move a,y:>${CIN_GE:x}", ("label", f"ge_y{k}")]


def _ge_vca():
    """(env) a = the VCA's target: the envelope block's S_VCA, or the voice's (as before)"""
    import synth0 as SY
    return [f"move y:>${CIN_GE:x},b", "tst b", ("jcc", "eq", "c_vv"), "move b1,r4", "nop", f"move y:(r4+${SY.S_VCA:x}),a", ("jmp", "c_vd"),
            ("label", "c_vv"), "move y:(r2),x0", "move y:(r3),x1", "mpy x1,x0,a", ("label", "c_vd")]


def _ge_lp():
    """(env) a (the low-pass index) + C_EF x S_ENV of the envelope block, from 0"""
    import synth0 as SY
    return [f"move y:>${CIN_GE:x},b", "tst b", ("jcc", "eq", "c_ln"), "move b1,r4", "nop",
            f"move y:(r4+${SY.S_ENV:x}),x0", f"move y:(r4+${SY.C_EF:x}),y0", "mpy y0,x0,b", "asr #16,b,b", "move b1,b", "add b,a",
            "tst a", ("jcc", "ge", "c_ln"), "clr a", ("label", "c_ln")]


def code(gr, stereo=False, multi=False, env=False):
    tb = tables()
    at0 = place(multi, env)
    w0, _ = C0.asm_at(items({k: 0x3F00 for k in tb}, gr, stereo=stereo, multi=multi, env=env), at0)
    at, tab_at = at0 + len(w0), {}
    for k in ("F2", "Q2"):
        tab_at[k] = at
        at += len(tb[k])
    assert multi or not env
    w, labels = C0.asm_at(items(tab_at, gr, stereo=stereo, multi=multi, env=env), at0)
    assert len(w) == len(w0)
    for k in ("F2", "Q2"):
        w += tb[k]
    assert at0 + len(w) <= C0.LD, hex(at0 + len(w))
    return w, labels, tab_at


def segs(gr_labels, stereo=False, multi=False, env=False):
    """for granular0's extra: our code at P:AT (GR's end jumps here: granular0 post=AT); stereo (RH47): the side too; multi (RH50): at
    P:AT_M, a chain per slot"""
    w, labels, _ = code(gr_labels, stereo=stereo, multi=multi, env=env)
    assert labels["ch"] == place(multi, env)
    return [(place(multi, env), w)]
