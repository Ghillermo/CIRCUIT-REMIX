"""Stock+ for every sound: the Stock+ page of a granular or synth track (MIT; RH55; the user, 2026-10-28: «Stock+ for every sound»; «Start
RH55: Stock+ for every sound (LFO, pitch envelope, waveshaping, FX for granular and synth on core 0)»; K7 on them: «Waveshaper + its type»;
K8 on the synth: «FM amount»; the stock's distortion knob on them too).

The page itself is stockplus's (the track menu's pad 2: synthpage spall offers it on a granular or synth track; its knobs, values, LEDs and
blocks as on a sample track).  Ours, on a granular or synth track (synthpage's c_sysnd):
  * K7 = the waveshaper's amount, Shift + K7 = its type (four zones: soft, hard, fold, bitcrush), Clear + K7 = both off / soft; 128 a click;
    in the project's block «W» (rhrec.OFF54 "waveshape": a check byte, 8 tracks x (amount, type) halfwords); Clear + a track's button and
    Duplicate + A, B (stockplus's) take them along;
  * K7's LED in the type's colour (gold, red-orange, teal, lime), as bright as the amount (at least K7_MIN) or fully with Shift held
    (as K6's filter type);
  * the DSP: stockplus's push of a track (c_spdsp, from its LED task's round) goes through c_s0dsp: a sample track as before, its core 0
    block off (its key 0); a granular or synth track's core 1 words neutral (no pitch modulation, ring, filter type, follow, stretch,
    bitcrush or scan: its voice is not heard) and its words to core 0 (tools/sp0.py's block Y:$1D80 + $20 t: the same words, the
    waveshaper's, the key last); the synced K3 / K8 phases (c_k3sync / c_k8sync's writes) mirrored to core 0 for those tracks.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b, b_cond, b_w, bl, cmp_imm, cmp_reg, eors_reg, h, ldr_sp, ldrb_imm, ldrb_reg, ldrh_imm,  # noqa: E402
                   lsls_imm, lsls_reg, lsrs_imm, lsrs_reg, mov_reg, movs_imm, movt, movw, muls, pop_list, push_list, raw, strb_imm,
                   strb_reg, strh_imm, strh_w_imm, subs_imm8, subs_reg)
import countin as CI  # noqa: E402
import granpage as GP  # noqa: E402
import pitchmod as PM  # noqa: E402
import rhrec  # noqa: E402
import rhstate  # noqa: E402
import sckn as SK  # noqa: E402
import sp0 as S0  # noqa: E402
import stockplus as SP  # noqa: E402
import synthpage as SY  # noqa: E402

BLK, BLK_LEN = rhrec.OFF54["waveshape"]
MARK, CHECK = ord("W"), 0x5A
NT = 8
K7 = SP.K7
WS_COLS = (0x77, 0x8C, 0x4B, 0x7A)                     # soft gold, hard red-orange, fold teal, bitcrush lime (docs/INTERFAZ.md)
K7_MIN = SP.K6_MIN
FULL, STEP = SP.FULL, SP.STEP
CONT, SLOT_KNOB, SUBVIEW = SK.CONT, SK.SLOT_KNOB, SP.SUBVIEW
K_VAL, K_CODE = SP.K_VAL, SP.K_CODE
LED_KNOB0 = SP.LED_KNOB0
O_KB = rhstate.OFF["kbright"][0]
G_ONE = 0x080000                                       # the waveshaper's gain x 1 (voicefx's: the input x 16 g)
assert BLK_LEN == 2 + 4 * NT


def gain_table():
    """the waveshaper's gain over the amount (129 points): x 1 .. x 16, exponential"""
    return [min(S0.ONE, round(2 ** (4 * i / 128) * G_ONE)) for i in range(129)]


def ws_words(amount, typ):
    """(C_WT, C_WG, C_WM) of the waveshaper's knob values"""
    if amount == 0:
        return 0, 0, 0
    t = 1 + (typ * 4 >> 14)
    if t == 4:
        x = amount * 14 >> 14
        return 4, G_ONE, (0xFFFFFF << (8 + x)) & 0xFFFFFF
    tab = gain_table()
    i, f = amount >> 7, amount & 127
    return t, tab[i] + ((tab[i + 1] - tab[i]) * f >> 7), 0


def neutral_addrs():
    """the core 1 words c_s0dsp writes 0 to for a granular or synth track (+ t)"""
    import stretch as STR
    import voicefilt as F
    import voicefx as V
    vy, yb = V.Y_BASE + 0x300, PM.Y_BASE + 0x300
    return (yb + PM.OFF_A, yb + PM.OFF_R, yb + PM.OFF_L, vy + V.RAM, F.KTYPE, vy + V.FMODE, F.FOLLOW, STR.STRETCH, vy + V.DTYPE, F.SCANR,
            F.SCAND)


def model_words(v, amount=0, typ=0, bpm=120):
    """{core 0 Y address: word} c_s0dsp writes for a granular or synth track t = 0 with stockplus's 12 values v (K7 as its value): the
    tests' (stockplus k3sync / k8sync / ui)"""
    def interp(tab, x):
        i, f = x >> 7, x & 127
        return tab[i] + ((tab[i + 1] - tab[i]) * f >> 7)
    b = S0.blk(0)
    out = {b + S0.C_A: ((v[0] - 8192) * SP.A_SCALE) & 0xFFFFFF, b + S0.C_D: interp(SP.decay_table(), v[1]),
           b + S0.C_R: SP.k3_rate(v[2], bpm, ui=True) & 0xFFFFFF, b + S0.C_L: v[3] * SP.L_SCALE, b + S0.C_RAM: v[4] << 9,
           b + S0.C_RST: interp(SP.ring_table(), v[8]), b + S0.C_KT: v[5] * 3 >> 14, b + S0.C_FOL: v[9] << 9,
           b + S0.C_SCR: SP.k8_rate(v[7], bpm, ui=True) & 0xFFFFFF, b + S0.C_SCD: v[11] << 9, b + S0.C_KEY: S0.SPKEY}
    if out[b + S0.C_R] == 0:
        out[b + S0.C_PH] = SP.K3_MIDPH
    wt, wg, wm = ws_words(amount, typ)                         # (the gain only when on; the mask only for the bitcrush)
    out[b + S0.C_WT] = wt
    if wt:
        out[b + S0.C_WG] = wg
    if wt == 4:
        out[b + S0.C_WM] = wm
    return out


def model_block(vals=None):
    """the block for {track: (amount, type)}"""
    blk = bytearray(BLK_LEN)
    blk[0] = MARK
    for t, (am, ty) in (vals or {}).items():
        struct.pack_into("<HH", blk, 2 + 4 * t, am, ty)
    x = CHECK
    for c in blk[2:]:
        x ^= c
    blk[1] = x
    return bytes(blk)


def arm_code(base, L, prev, tabs):
    a = Asm(base)
    E = a.emit
    zc = [0]

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    def bc(target, cond):
        zc[0] += 1
        n = f"_w{zc[0]}"
        E(b_cond, n, SP.INV[cond])
        E(b, target)
        a.label(n)

    t_gain = base
    E(raw, b"".join(x.to_bytes(4, "little") for x in gain_table()))
    t_cols = t_gain + 4 * 129
    E(raw, b"".join(x.to_bytes(2, "little") for x in WS_COLS))
    t_neut = t_cols + 2 * len(WS_COLS)
    E(raw, b"".join(x.to_bytes(2, "little") for x in neutral_addrs()))
    t_end = t_neut + 2 * len(neutral_addrs())
    if t_end % 4:
        E(raw, bytes(4 - t_end % 4))

    # ---- c_wsb() -> r0 = our block (made anew when missing or wrong: every track off / soft), 0 without a record; clobbers r1-r3
    a.label("c_wsb")
    E(push_list, [4, 5], lr=True)
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "wb_x", "eq")
    E(movw, 1, BLK)
    E(adds_reg, 4, 0, 1)
    E(ldrb_imm, 0, 4, 0)
    E(cmp_imm, 0, MARK)
    E(b_cond, "wb_new", "ne")
    E(bl, "ws_sum")
    E(ldrb_imm, 1, 4, 1)
    E(cmp_reg, 0, 1)
    E(b_cond, "wb_ok", "eq")
    a.label("wb_new")
    E(movs_imm, 0, MARK)
    E(strb_imm, 0, 4, 0)
    E(movs_imm, 0, 0)
    E(movs_imm, 1, 2)
    a.label("wb_z")
    E(strb_reg, 0, 4, 1)
    E(adds_imm8, 1, 1)
    E(cmp_imm, 1, BLK_LEN)
    E(b_cond, "wb_z", "lo")
    E(bl, "ws_sum")
    E(strb_imm, 0, 4, 1)
    a.label("wb_ok")
    E(mov_reg, 0, 4)
    a.label("wb_x")
    E(pop_list, [4, 5], pc=True)
    # ws_sum (r4 = the block) -> r0 = its check byte; clobbers r1, r2
    a.label("ws_sum")
    E(movs_imm, 0, CHECK)
    E(movs_imm, 1, 2)
    a.label("wsum_l")
    E(ldrb_reg, 2, 4, 1)
    E(eors_reg, 0, 2)
    E(adds_imm8, 1, 1)
    E(cmp_imm, 1, BLK_LEN)
    E(b_cond, "wsum_l", "lo")
    E(raw, h(0x4770))                                                     # bx lr

    # ---- c_wsget(r0 = track, r1 = 0 the amount / 1 the type) -> r0 = its value (0 without a record); clobbers r1-r3
    a.label("c_wsget")
    E(push_list, [4, 5], lr=True)
    E(lsls_imm, 4, 0, 2)
    E(lsls_imm, 1, 1, 1)
    E(adds_reg, 4, 4, 1)                                                  # r4 = 4 t + 2 k
    E(bl, "c_wsb")
    E(cmp_imm, 0, 0)
    E(b_cond, "wg_x", "eq")
    E(adds_reg, 0, 0, 4)
    E(ldrh_imm, 0, 0, 2)
    a.label("wg_x")
    E(pop_list, [4, 5], pc=True)

    # ---- c_wsset(r0 = track, r1 = k, r2 = value): stored, the check byte, the track's Stock+ words to push; clobbers r0-r3
    a.label("c_wsset")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 6, 0)
    E(lsls_imm, 5, 0, 2)
    E(lsls_imm, 1, 1, 1)
    E(adds_reg, 5, 5, 1)
    E(mov_reg, 4, 2)
    E(bl, "c_wsb")
    E(cmp_imm, 0, 0)
    E(b_cond, "ws_x", "eq")
    E(adds_reg, 1, 0, 5)
    E(strh_imm, 4, 1, 2)
    E(mov_reg, 4, 0)
    E(bl, "ws_sum")
    E(strb_imm, 0, 4, 1)
    E(mov_reg, 0, 6)
    E(bl, L["c_spdirty"])
    a.label("ws_x")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_s0snd(r0 = track) -> r0 = 1 for a granular or synth track, else 0; clobbers r1-r3
    a.label("c_s0snd")
    E(push_list, [4], lr=True)
    E(bl, L["c_sysnd"])
    E(cmp_imm, 0, SY.SND_GRAN)
    E(b_cond, "sn_1", "eq")
    E(cmp_imm, 0, SY.SND_SYNTH)
    E(b_cond, "sn_1", "eq")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)
    a.label("sn_1")
    E(movs_imm, 0, 1)
    E(pop_list, [4], pc=True)

    # ---- c_s0on(r0 = track) -> r0 = 1 on its Stock+ page with a granular or synth sound; clobbers r1-r3
    a.label("c_s0on")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, L["c_spst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "so_0", "eq")
    E(ldrb_imm, 0, 0, 0)
    E(lsrs_reg, 0, 4)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "so_0", "eq")
    E(mov_reg, 0, 4)
    E(bl, "c_s0snd")
    E(pop_list, [4], pc=True)
    a.label("so_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)

    # ---- s0w(r0 = word, r1 = the offset in the track r4's core 0 block): written; clobbers r0-r3, r12
    a.label("s0w")
    E(push_list, [4], lr=True)
    E(lsls_imm, 2, 4, 5)
    E(adds_reg, 1, 1, 2)
    E(movw, 2, 0x8000 | S0.Y0)
    E(adds_reg, 1, 1, 2)
    E(movs_imm, 2, 0)
    E(bl, L["c_gpw"])
    E(pop_list, [4], pc=True)

    # ---- c_s0dsp(r0 = track): stockplus's push of a track (its LED task's round calls this in place of c_spdsp)
    a.label("c_s0dsp")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_s0snd")
    E(cmp_imm, 0, 0)
    bc("sd_g", "ne")
    E(mov_reg, 0, 4)                                                      # a sample (or line) track: core 1's words, core 0's block off
    E(bl, L["c_spdsp"])
    E(movs_imm, 0, 0)
    E(movs_imm, 1, S0.C_KEY)
    E(bl, "s0w")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    a.label("sd_g")
    E(movs_imm, 5, 0)                                                     # core 1: its words neutral
    a.label("sd_n")
    imm32(0, t_neut)
    E(lsls_imm, 1, 5, 1)
    E(adds_reg, 0, 0, 1)
    E(ldrh_imm, 1, 0, 0)
    E(adds_reg, 1, 1, 4)
    E(movs_imm, 0, 0)
    E(bl, L["c_spw"])
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, len(neutral_addrs()))
    E(b_cond, "sd_n", "lo")

    def val(k):
        E(mov_reg, 0, 4)
        E(movs_imm, 1, k)
        E(bl, L["c_spval"])

    def put(off):
        E(movs_imm, 1, off)
        E(bl, "s0w")

    def tab(k, t, off):
        val(k)
        E(mov_reg, 1, 0)
        imm32(0, t)
        E(bl, L["c_spint"])
        put(off)
    E(movs_imm, 0, 0)                                                     # core 0: the key off while its words change
    put(S0.C_KEY)
    val(0)                                                                # K1: the pitch envelope's amount
    E(movw, 1, 8192)
    E(subs_reg, 0, 0, 1)
    E(movs_imm, 1, SP.A_SCALE)
    E(muls, 0, 1)
    put(S0.C_A)
    tab(1, tabs["dec"], S0.C_D)                                           # K2: its decay
    E(mov_reg, 0, 4)                                                      # K3: the LFO's rate (free / at the tempo / off: the phase at the centre)
    E(bl, L["c_k3r"])
    E(mov_reg, 5, 0)
    put(S0.C_R)
    E(cmp_imm, 5, 0)
    E(b_cond, "sd_k3", "ne")
    imm32(0, SP.K3_MIDPH)
    put(S0.C_PH)
    a.label("sd_k3")
    val(3)                                                                # K4: its depth
    E(movs_imm, 1, SP.L_SCALE)
    E(muls, 0, 1)
    put(S0.C_L)
    val(4)                                                                # K5: the ring's amount
    E(lsls_imm, 0, 0, 9)
    put(S0.C_RAM)
    tab(8, tabs["ring"], S0.C_RST)                                        # Shift + K5: its frequency
    val(5)                                                                # Shift + K6: the filter type
    E(movs_imm, 1, 3)
    E(muls, 0, 1)
    E(lsrs_imm, 0, 0, 14)
    put(S0.C_KT)
    val(9)                                                                # K6: the follow
    E(lsls_imm, 0, 0, 9)
    put(S0.C_FOL)
    E(mov_reg, 0, 4)                                                      # K7: the waveshaper (amount 0 = off)
    E(movs_imm, 1, 0)
    E(bl, "c_wsget")
    E(mov_reg, 6, 0)                                                      # r6 = the amount
    E(mov_reg, 0, 4)
    E(movs_imm, 1, 1)
    E(bl, "c_wsget")
    E(lsrs_imm, 7, 0, 12)                                                 # r7 = the type 0..3
    E(cmp_imm, 6, 0)
    E(b_cond, "sd_w0", "ne")
    E(movs_imm, 0, 0)
    put(S0.C_WT)
    E(b, "sd_k8")
    a.label("sd_w0")
    E(cmp_imm, 7, 3)
    E(b_cond, "sd_wg", "ne")
    E(movs_imm, 0, 14)                                                    # bitcrush: 16 - x bits, x = amount x 14 >> 14
    E(muls, 0, 6)
    E(lsrs_imm, 0, 0, 14)
    E(adds_imm8, 0, 8)
    E(mov_reg, 5, 0)
    imm32(0, 0xFFFFFF)
    E(lsls_reg, 0, 5)
    put(S0.C_WM)
    imm32(0, G_ONE)
    put(S0.C_WG)
    E(b, "sd_wt")
    a.label("sd_wg")
    E(mov_reg, 1, 6)                                                      # the others: the gain x 1 .. x 16
    imm32(0, t_gain)
    E(bl, L["c_spint"])
    put(S0.C_WG)
    a.label("sd_wt")
    E(adds_imm8, 7, 1)
    E(mov_reg, 0, 7)
    put(S0.C_WT)
    a.label("sd_k8")
    E(mov_reg, 0, 4)                                                      # K8: the scan's rate (free / at the tempo / still)
    E(bl, L["c_k8r"])
    put(S0.C_SCR)
    val(11)                                                               # Shift + K8: its depth
    E(lsls_imm, 0, 0, 9)
    put(S0.C_SCD)
    imm32(0, S0.SPKEY)                                                    # the key last
    put(S0.C_KEY)
    E(pop_list, [3, 4, 5, 6, 7], pc=True)

    # ---- c_s0w(r0 = word, r1 = core 1's Y address): c_spw's calls in c_k3sync / c_k8sync; the synced phases mirrored to core 0 for a
    # granular or synth track
    a.label("c_s0w")
    E(push_list, [3, 4, 5, 6], lr=True)
    E(mov_reg, 5, 0)
    E(mov_reg, 6, 1)
    E(bl, L["c_spw"])
    import voicefilt as F
    for base_, off, lab in ((tabs["ph"], S0.C_PH, "sw_p"), (F.SCANPH, S0.C_SPH, "sw_s")):
        E(movw, 0, base_)
        E(subs_reg, 4, 6, 0)
        E(cmp_imm, 4, NT)
        E(b_cond, f"{lab}n", "hs")
        E(mov_reg, 0, 4)
        E(bl, "c_s0snd")
        E(cmp_imm, 0, 0)
        E(b_cond, "sw_x", "eq")
        E(mov_reg, 0, 5)
        put(off)
        E(b, "sw_x")
        a.label(f"{lab}n")
    a.label("sw_x")
    E(pop_list, [3, 4, 5, 6], pc=True)

    # ---- c_s0reset(r0 = track): stockplus's defaults (Clear + the track's button), then ours
    a.label("c_s0reset")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, L["c_spreset"])
    for k in (0, 1):
        E(mov_reg, 0, 4)
        E(movs_imm, 1, k)
        E(movs_imm, 2, 0)
        E(bl, "c_wsset")
    E(pop_list, [4], pc=True)

    # ---- c_s0copy(r0 = track B; r7 = track A, c_spbtn's): Duplicate + A, B: ours copied too, then stockplus's c_spdirty
    a.label("c_s0copy")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 0)
    for k in (0, 1):
        E(mov_reg, 0, 7)
        E(movs_imm, 1, k)
        E(bl, "c_wsget")
        E(mov_reg, 2, 0)
        E(mov_reg, 0, 4)
        E(movs_imm, 1, k)
        E(bl, "c_wsset")
    E(mov_reg, 0, 4)
    E(bl, L["c_spdirty"])
    E(pop_list, [4, 5], pc=True)

    # ---- c_s0knob (the container's slot 4, the head of its chain: r0 = container, r1 = knob, r2 = delta): K7 of a granular or synth
    # track's Stock+ page = the waveshaper (Shift: its type); Clear + K7: both back (off, soft)
    a.label("c_s0knob")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(cmp_imm, 1, K7)
    bc("kn_p", "ne")
    E(bl, L["c_spview"])
    E(cmp_imm, 0, NT)
    bc("kn_p", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the track
    E(bl, "c_s0on")
    E(cmp_imm, 0, 0)
    bc("kn_p", "eq")
    imm32(0, CONT)
    E(bl, SUBVIEW)
    E(cmp_imm, 0, 0)
    bc("kn_p", "eq")                                                      # no knobs in this mode
    E(bl, L["c_spheld"])
    E(lsls_imm, 0, 0, 31 - SP.BIT_CLEAR)
    E(b_cond, "kn_t", "pl")
    for k in (0, 1):
        E(mov_reg, 0, 4)
        E(movs_imm, 1, k)
        E(movs_imm, 2, 0)
        E(bl, "c_wsset")
    E(b, "kn_x")
    a.label("kn_t")
    E(bl, L["c_spshift"])
    E(movs_imm, 5, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "kn_k", "eq")
    E(movs_imm, 5, 1)                                                     # r5 = 0 the amount, 1 the type
    a.label("kn_k")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, "c_wsget")
    E(ldr_sp, 1, 8)                                                       # the delta
    E(movs_imm, 2, STEP)
    E(muls, 1, 2)
    E(adds_reg, 2, 0, 1)
    E(cmp_imm, 2, 0)
    E(b_cond, "kn_h", "ge")
    E(movs_imm, 2, 0)
    a.label("kn_h")
    E(movw, 0, FULL)
    E(cmp_reg, 2, 0)
    E(b_cond, "kn_w", "le")
    E(mov_reg, 2, 0)
    a.label("kn_w")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, "c_wsset")
    a.label("kn_x")
    E(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)
    a.label("kn_p")
    E(raw, GP.popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    E(b_w, prev["knob"])

    # ---- c_s0led (the LED task's calls: ctrl, frame): the chain; K7's LED on a granular or synth track's Stock+ page
    a.label("c_s0led")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)                                                      # r5 = the frame
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(bl, L["c_spview"])
    E(cmp_imm, 0, NT)
    bc("ld_x", "hs")
    E(mov_reg, 4, 0)
    E(bl, "c_s0on")
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(movw, 1, O_KB)
    E(adds_reg, 7, 0, 1)                                                  # r7 = kbright's overlay
    E(mov_reg, 0, 4)
    E(movs_imm, 1, 1)
    E(bl, "c_wsget")
    E(lsrs_imm, 0, 0, 12)                                                 # the type 0..3: its colour
    E(lsls_imm, 0, 0, 1)
    imm32(1, t_cols)
    E(adds_reg, 1, 1, 0)
    E(ldrh_imm, 0, 1, 0)
    E(strh_imm, 0, 7, K_CODE + 2 * K7)
    E(strh_w_imm, 0, 5, 2 * (LED_KNOB0 + K7))
    E(bl, L["c_spshift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ld_a", "eq")
    E(movs_imm, 0, 127)                                                   # Shift: full (the type shown)
    E(b, "ld_w")
    a.label("ld_a")
    E(mov_reg, 0, 4)
    E(movs_imm, 1, 0)
    E(bl, "c_wsget")
    E(lsrs_imm, 0, 0, 7)
    E(cmp_imm, 0, K7_MIN)
    E(b_cond, "ld_w", "ge")
    E(movs_imm, 0, K7_MIN)
    a.label("ld_w")
    E(strb_imm, 0, 7, K_VAL + K7)
    a.label("ld_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def _bls(img, lo, hi, target):
    """the addresses of every `bl target` in [lo, hi)"""
    import rhbuild
    out = []
    for x in range(lo, hi, 2):
        h1, h2 = struct.unpack_from("<HH", img, x - rhbuild.BASE)
        if h1 & 0xF800 == 0xF000 and h2 & 0xD000 == 0xD000 and rhbuild.bl_target(img, x) == target:
            out.append(x)
    return out


def install(img, report, base_addr):
    """The container's knob slot (in front of envpage's), the head of the LED calls; stockplus's push (c_spled's bl c_spdsp), its synced
    phases (c_k3sync / c_k8sync's bl c_spw), its Clear + a track's button (c_spbtn's bl c_spreset) and Duplicate (c_spbtn's copy's bl
    c_spdirty) through ours.  Needs stockplus (v2, k3sync, k8sync, ui), synthpage spall (the menu's pad 2), envpage, sp0 on core 0."""
    import rhbuild
    BASE = rhbuild.BASE
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]                 # noqa: E731
    rs = report["stockplus"]
    assert rs.get("v2") and rs.get("k3sync") and rs.get("k8sync") and rs.get("ui") and report["synthpage"].get("spall")
    assert "envpage" in report and report["granular0"].get("sp")
    spl = {k: lab("stockplus", k) for k in ("c_spst", "c_spview", "c_spheld", "c_spshift", "c_spval", "c_spint", "c_spw", "c_spdsp",
                                           "c_spdirty", "c_spreset", "c_k3r", "c_k8r", "c_k3sync", "c_k8sync", "c_spgrain", "c_spled",
                                           "c_spbtn", "c_spknob")}
    L = dict(c_rst=lab("rhstate", "c_rst"), c_rrt=lab("rhrec", "c_rrt"), c_ciok=lab("countin", "c_ciok"), c_sysnd=lab("synthpage", "c_sysnd"),
             c_gpw=lab("granpage", "c_gpw"), **spl)
    tb = int(rs["tables"], 16)                                                 # stockplus's tables (v2: decay, rate, defaults, ring, speed, scan)
    tabs = dict(dec=tb, ring=tb + 8 * 129 + 2 * SP.NPAR, ph=PM.Y_BASE + 0x300 + PM.OFF_PH)
    assert tabs["ring"] + 4 * 129 == int(rs["t_spd"], 16), "stockplus's tables moved"
    prev = dict(knob=u(SLOT_KNOB) & ~1, ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert prev["knob"] == lab("envpage", "c_evknob")
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code_, labels = arm_code(base_addr, L, prev, tabs)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code_
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch_word(img, SLOT_KNOB, prev["knob"] | 1, labels["c_s0knob"] | 1)
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_s0led"]))
    sites = dict(
        dsp=_bls(img, spl["c_spled"], spl["c_spled"] + 0x200, spl["c_spdsp"]),
        k8=_bls(img, spl["c_k8sync"], spl["c_k3r"], spl["c_spw"]),
        k3=_bls(img, spl["c_k3sync"], spl["c_spgrain"], spl["c_spw"]),
        reset=_bls(img, spl["c_spbtn"], spl["c_spknob"], spl["c_spreset"]),
        copy=_bls(img, spl["c_spbtn"], spl["c_spknob"], spl["c_spdirty"]))
    assert all(len(v) == 1 for k, v in sites.items() if k not in ("k3", "k8")) and sites["k3"] and sites["k8"], sites
    for k, new in (("dsp", "c_s0dsp"), ("k8", "c_s0w"), ("k3", "c_s0w"), ("reset", "c_s0reset"), ("copy", "c_s0copy")):
        old = {"dsp": "c_spdsp", "k8": "c_spw", "k3": "c_spw", "reset": "c_spreset", "copy": "c_spdirty"}[k]
        for x in sites[k]:
            rhbuild.patch(img, x, f"bl #{spl[old]:#x}", bl(x, labels[new]))
    report["spall"] = dict(prev={k: hex(v) for k, v in prev.items()}, tables=hex(base_addr), block=hex(BLK),
                           sites={k: [hex(x) for x in v] for k, v in sites.items()},
                           labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code_
