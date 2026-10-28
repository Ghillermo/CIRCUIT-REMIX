"""The Envelope page of a synth or granular track (MIT; RH54; the user, 2026-10-28: «add start length for envelope controls (percussive env
for one shot.  Unitary sustain: atk/release for gated, atk/sustain for loop), slope for env to amp and dist for env to filt»; «Synth and
granular»; the loop's «Attack + sustain time»; the slope «From the centre»; the knobs «replacing knobs that do nothing, or sharing page
with other new parameters, create new page in case there's no room in existing ones»: a new page).

  * the page: the track menu's pad 5 (synthpage env: a granular or synth track; its bit in the menu's byte + 3), rose (docs/INTERFAZ.md);
    K1 start (the attack: instant .. 2 s), K2 length (by the track's play mode: one-shot = the decay, gated = the release, loop = the time
    it holds; 5 ms .. 8 s), K3 slope (from the centre: right exponential, left rounder), K4 envelope -> low-pass (from the centre);
    K5-K8 nothing (dark); Clear + a knob = its default; the knobs lit with their value (K3 / K4 from the middle), the track's button
    blinking rose; the menu's pad 5 rose (bright on the page, dim available, dark on a sample or line track);
  * the values: a synth slot's start / length / envelope -> filter are its own values 15 (the spare) / 13 (the release's) / 14 (K_EF,
    synthpage's c_syp: its words follow); its slope and a granular slot's four are in the project's block «E» (rhrec.OFF54, the tail
    trkcopy's photo left: trkcopy ram);
  * core 0 (synth0 env2, granchain env): each synth slot's C_ATK, C_DEC, C_HOLD, C_MODE, C_SLP, C_RQ (Y:$1A00 + $40 s + 48..53) and
    each granular slot's envelope block (Y:$1C00 + $40 g: C_TRK, C_EF, the six, C_KEY last; on = a slot in use with its gate knob on;
    granpage env leaves the engine's gate at 0: the envelope gates); the play mode = the track's parameter 1 (0x08046410(0x10 + t, 1):
    0 one-shot, 1 gated, 2 loop); a slot's words all at once after a change (the lowest pending first), else two words a frame in turn,
    all of them after the block changed (a project loaded) or at the first frame; only with cthresh READY.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm3, adds_imm8, adds_reg, b, b_cond, b_w, bics_reg, bl, cmp_imm, cmp_reg, eors_reg, h, ldr_imm, ldr_sp,  # noqa: E402
                   ldrb_imm, ldrb_reg, ldrb_w, ldrh_reg, lsls_imm, lsls_reg, lsrs_imm, lsrs_reg, mov_reg, movs_imm, movt, movw, muls, orrs_reg,
                   pop_list, push_list, raw, str_imm, strb_imm, strb_reg, strh_imm, strh_w_imm, subs_imm8, subs_reg, tst_reg)
import countin as CI  # noqa: E402
import cthresh as TH  # noqa: E402
import granpage as GP  # noqa: E402
import rhrec  # noqa: E402
import rhstate  # noqa: E402
import sckn as SK  # noqa: E402
import stockplus as SP  # noqa: E402
import synth0 as S  # noqa: E402
import synthpage as SY  # noqa: E402

BLK, BLK_LEN = rhrec.OFF54["envelope"]
MARK, CHECK = 0x45, 0x2D                               # "E"
B_SSLP, B_G = 2, 6                                     # + s: a synth slot's slope; + 4 g: a granular slot's start, length, slope, -> filter
NSL, NG = SY.NSL, 4
DEF_G = (0, 40, 64, 64)
DEF = bytes([MARK, 0]) + bytes([64] * NSL) + bytes(DEF_G * NG)
assert len(DEF) == BLK_LEN
M_ENV = SY.M_ENV                                       # the menu's byte + 3: the Envelope pages (bit t)
R_PEND, R_ROUND, R_SUM, R_SENT = 12, 13, 14, 15        # in the menu's state (bytes + 12 .. + 15, free): the slots to send (bits 0-3 synth,
                                                       # 4-7 granular), the round, the block's check last seen, sent once
PAD_ENV = SY.UI_PAD_ENV
COL, DIM = 0x3B, 0x3C                                  # rose
GETTER = 0x08046410
CONT, SLOT_KNOB, SUBVIEW = SK.CONT, SK.SLOT_KNOB, SP.SUBVIEW
K_MASK, K_VAL, K_CODE = SP.K_MASK, SP.K_VAL, SP.K_CODE
LED_TRK0, LED_TRK1, LED_KNOB0 = SP.LED_TRK0, SP.LED_TRK1, SP.LED_KNOB0
O_KB, O_TH = rhstate.OFF["kbright"][0], rhstate.OFF["cthresh"][0] + 1
BPS = 48000 / 32                                       # blocks a second
RQ = S.ONE // 15                                       # the loop's release: 10 ms
NWS, NWG = 6, 9
SW_OFF = (S.C_ATK, S.C_DEC, S.C_HOLD, S.C_MODE, S.C_SLP, S.C_RQ)
GW_OFF = (S.C_TRK, S.C_EF, S.C_ATK, S.C_DEC, S.C_HOLD, S.C_MODE, S.C_SLP, S.C_RQ, S.C_KEY)
NW = NSL * NWS + NG * NWG
# the knobs' defaults by sound (granular, synth): start, length, slope, -> filter
KDEF = {SY.SND_GRAN: DEF_G, SY.SND_SYNTH: (0, SY.LEN_DEF, 64, 64)}
BIPK = (0, 0, 1, 1)


def atk_blocks(v):
    return 1 if v == 0 else max(1, round(BPS * 0.001 * 2000 ** (v / 127)))


def len_blocks(v):
    return max(1, round(BPS * 0.005 * 1600 ** (v / 127)))


def tables():
    atki = [min(S.ONE, S.ONE // atk_blocks(v)) for v in range(128)]
    leni = [min(S.ONE, S.ONE // len_blocks(v)) for v in range(128)]
    lenb = [len_blocks(v) for v in range(128)]
    return atki, leni, lenb


def wmap():
    """word i -> (slot 0..3 synth / 4..7 granular, j)"""
    return [(i // NWS, i % NWS) for i in range(NSL * NWS)] + [(NSL + (i // NWG), i % NWG) for i in range(NG * NWG)]


def model_words(start, length, slope, mode, ef=64, trk1=0, on=False, granular=False):
    """a slot's words as the ARM computes them (the tests'): synth (offset, word) x 6, granular x 9 (the key last)"""
    atki, leni, lenb = tables()
    vals = {S.C_ATK: atki[start], S.C_DEC: leni[length], S.C_HOLD: lenb[length], S.C_MODE: mode,
            S.C_SLP: ((slope - 64) << 17) & 0xFFFFFF, S.C_RQ: RQ}
    if not granular:
        return [(o, vals[o]) for o in SW_OFF]
    vals.update({S.C_TRK: trk1 if on else 0, S.C_EF: ((ef - 64) << 17) & 0xFFFFFF, S.C_KEY: S.KEY if on else 0})
    return [(o, vals[o]) for o in GW_OFF]


def model_block(sslope=(64,) * 4, gvals=(DEF_G,) * 4):
    b = bytearray(DEF)
    b[B_SSLP:B_SSLP + NSL] = bytes(sslope)
    for g, v in enumerate(gvals):
        b[B_G + 4 * g:B_G + 4 * g + 4] = bytes(v)
    x = CHECK ^ MARK
    for c in b[2:]:
        x ^= c
    b[1] = x
    return bytes(b)


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit
    zc = [0]

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    def bc(target, cond):
        zc[0] += 1
        n = f"_e{zc[0]}"
        E(b_cond, n, SP.INV[cond])
        E(b, target)
        a.label(n)

    atki, leni, lenb = tables()
    t_def = base
    E(raw, DEF)
    t_kdef = t_def + BLK_LEN                              # the knobs' defaults: granular x 4, synth x 4
    E(raw, bytes(KDEF[SY.SND_GRAN]) + bytes(KDEF[SY.SND_SYNTH]))
    t_map = t_kdef + 8
    E(raw, bytes(s_ << 4 | j for s_, j in wmap()))
    t_soff = t_map + NW
    E(raw, bytes(SW_OFF) + bytes(GW_OFF))
    t_goff = t_soff + NWS
    pad = (-(t_goff + NWG - base)) % 4
    E(raw, bytes(pad))
    t_atk = t_goff + NWG + pad
    E(raw, b"".join(x.to_bytes(4, "little") for x in atki))
    t_len = t_atk + 512
    E(raw, b"".join(x.to_bytes(4, "little") for x in leni))
    t_lnb = t_len + 512
    E(raw, b"".join(x.to_bytes(2, "little") for x in lenb))

    # ---- c_evsum(r0 = block): its check byte; clobbers r1-r3
    a.label("c_evsum")
    E(movs_imm, 1, CHECK ^ MARK)
    E(movs_imm, 2, 2)
    a.label("es_l")
    E(ldrb_reg, 3, 0, 2)
    E(eors_reg, 1, 3)
    E(adds_imm8, 2, 1)
    E(cmp_imm, 2, BLK_LEN)
    E(b_cond, "es_l", "lo")
    E(strb_imm, 1, 0, 1)
    E(raw, h(0x4770))                                                     # bx lr
    # ---- c_evb() -> r0 = our block (made anew with the defaults when missing or wrong), 0 without a record; clobbers r1-r3
    a.label("c_evb")
    E(push_list, [4, 5], lr=True)
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "eb_x", "eq")
    E(movw, 1, BLK)
    E(adds_reg, 4, 0, 1)
    E(ldrb_imm, 0, 4, 0)
    E(cmp_imm, 0, MARK)
    E(b_cond, "eb_new", "ne")
    E(ldrb_imm, 5, 4, 1)
    E(movs_imm, 1, CHECK ^ MARK)
    E(movs_imm, 2, 2)
    a.label("eb_l")
    E(ldrb_reg, 3, 4, 2)
    E(eors_reg, 1, 3)
    E(adds_imm8, 2, 1)
    E(cmp_imm, 2, BLK_LEN)
    E(b_cond, "eb_l", "lo")
    E(cmp_reg, 1, 5)
    E(b_cond, "eb_ok", "eq")
    a.label("eb_new")
    imm32(1, t_def)
    E(movs_imm, 2, 0)
    a.label("eb_c")
    E(ldrb_reg, 0, 1, 2)
    E(strb_reg, 0, 4, 2)
    E(adds_imm8, 2, 1)
    E(cmp_imm, 2, BLK_LEN)
    E(b_cond, "eb_c", "lo")
    E(mov_reg, 0, 4)
    E(bl, "c_evsum")
    a.label("eb_ok")
    E(mov_reg, 0, 4)
    a.label("eb_x")
    E(pop_list, [4, 5], pc=True)

    # ---- c_evon(r0 = track) -> r0 = 1 on its Envelope page (its bit and a granular or synth sound), else 0; clobbers r1-r3
    a.label("c_evon")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, L["c_gpmst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "eo_0", "eq")
    E(ldrb_imm, 0, 0, M_ENV)
    E(lsrs_reg, 0, 4)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "eo_0", "eq")
    E(mov_reg, 0, 4)
    E(bl, L["c_sysnd"])
    E(cmp_imm, 0, SY.SND_GRAN)
    E(b_cond, "eo_1", "eq")
    E(cmp_imm, 0, SY.SND_SYNTH)
    E(b_cond, "eo_1", "eq")
    a.label("eo_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)
    a.label("eo_1")
    E(movs_imm, 0, 1)
    E(pop_list, [4], pc=True)

    # ---- c_evget(r0 = track, r1 = k 0..3) -> r0 = its value, r1 = its sound (0 = none); clobbers r2, r3
    a.label("c_evget")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(bl, L["c_sysnd"])
    E(mov_reg, 6, 0)
    E(cmp_imm, 6, SY.SND_SYNTH)
    E(b_cond, "eg_g", "ne")
    E(mov_reg, 0, 4)
    E(bl, L["c_syslot"])
    E(cmp_imm, 5, 2)
    E(b_cond, "eg_ss", "eq")
    imm32(1, 0x0E000D0F)                                                  # k 0 / 1 / 3 -> its value 15 / 13 / 14
    E(lsls_imm, 2, 5, 3)
    E(lsrs_reg, 1, 2)
    E(movs_imm, 2, 0xFF)
    E(raw, h(0x4011))                                                     # ands r1, r2
    E(bl, L["c_syv"])
    E(b, "eg_x")
    a.label("eg_ss")
    E(mov_reg, 4, 0)                                                      # the synth slot's slope in our block
    E(bl, "c_evb")
    E(cmp_imm, 0, 0)
    E(b_cond, "eg_d", "eq")
    E(adds_reg, 0, 0, 4)
    E(ldrb_imm, 0, 0, B_SSLP)
    E(b, "eg_x")
    a.label("eg_g")
    E(cmp_imm, 6, SY.SND_GRAN)
    E(b_cond, "eg_n", "ne")
    E(mov_reg, 0, 4)
    E(bl, L["c_gnslot"])
    E(mov_reg, 4, 0)
    E(bl, "c_evb")
    E(cmp_imm, 0, 0)
    E(b_cond, "eg_d", "eq")
    E(lsls_imm, 4, 4, 2)
    E(adds_reg, 0, 0, 4)
    E(adds_reg, 0, 0, 5)
    E(ldrb_imm, 0, 0, B_G)
    E(b, "eg_x")
    a.label("eg_d")
    E(movs_imm, 0, 64)
    E(b, "eg_x")
    a.label("eg_n")
    E(movs_imm, 6, 0)
    E(movs_imm, 0, 0)
    a.label("eg_x")
    E(mov_reg, 1, 6)
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_evset(r0 = track, r1 = k 0..3, r2 = value): stored, its words pending; clobbers r0-r3
    a.label("c_evset")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(mov_reg, 7, 2)
    E(bl, L["c_sysnd"])
    E(mov_reg, 6, 0)
    E(cmp_imm, 6, SY.SND_SYNTH)
    E(b_cond, "et_g", "ne")
    E(mov_reg, 0, 4)
    E(bl, L["c_syslot"])
    E(mov_reg, 4, 0)                                                      # r4 = the synth slot
    E(cmp_imm, 5, 2)
    E(b_cond, "et_ss", "eq")
    imm32(1, 0x0E000D0F)
    E(lsls_imm, 2, 5, 3)
    E(lsrs_reg, 1, 2)
    E(movs_imm, 2, 0xFF)
    E(raw, h(0x4011))                                                     # ands r1, r2
    E(mov_reg, 2, 7)
    E(bl, L["c_syp"])
    E(b, "et_p")
    a.label("et_ss")
    E(bl, "c_evb")
    E(cmp_imm, 0, 0)
    E(b_cond, "et_x", "eq")
    E(adds_reg, 1, 0, 4)
    E(strb_imm, 7, 1, B_SSLP)
    E(bl, "c_evsum")
    a.label("et_p")
    E(movs_imm, 0, 1)
    E(lsls_reg, 0, 4)
    E(bl, "ev_pend")
    E(b, "et_x")
    a.label("et_g")
    E(cmp_imm, 6, SY.SND_GRAN)
    E(b_cond, "et_x", "ne")
    E(mov_reg, 0, 4)
    E(bl, L["c_gnslot"])
    E(mov_reg, 4, 0)                                                      # r4 = the granular slot
    E(bl, "c_evb")
    E(cmp_imm, 0, 0)
    E(b_cond, "et_x", "eq")
    E(lsls_imm, 1, 4, 2)
    E(adds_reg, 1, 1, 0)
    E(adds_reg, 1, 1, 5)
    E(strb_imm, 7, 1, B_G)
    E(bl, "c_evsum")
    E(movs_imm, 0, 0x10)
    E(lsls_reg, 0, 4)
    E(bl, "ev_pend")
    a.label("et_x")
    E(pop_list, [4, 5, 6, 7], pc=True)
    # ev_pend(r0 = bits): the slots' words to send; the block's check as seen (our own change, not a project loaded); clobbers r0-r3
    a.label("ev_pend")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(bl, L["c_gpmst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ep_x", "eq")
    E(mov_reg, 5, 0)
    E(ldrb_imm, 1, 5, R_PEND)
    E(orrs_reg, 1, 4)
    E(strb_imm, 1, 5, R_PEND)
    E(bl, "c_evb")
    E(cmp_imm, 0, 0)
    E(b_cond, "ep_x", "eq")
    E(ldrb_imm, 1, 0, 1)
    E(strb_imm, 1, 5, R_SUM)
    a.label("ep_x")
    E(pop_list, [4, 5], pc=True)

    # ---- c_evword(r0 = i 0..NW-1) -> r0 = its word, r1 = its address ($8000 | core 0's Y); clobbers r2, r3
    a.label("c_evword")
    E(push_list, [4, 5, 6, 7], lr=True)
    imm32(1, t_map)
    E(ldrb_reg, 1, 1, 0)
    E(lsrs_imm, 4, 1, 4)                                                  # r4 = the slot (0-3 synth, 4-7 granular)
    E(movs_imm, 2, 15)
    E(raw, h(0x4011))                                                     # ands r1, r2
    E(mov_reg, 5, 1)                                                      # r5 = j
    E(cmp_imm, 4, NSL)
    bc("ew_g", "hs")
    # a synth slot: start / length its values 15 / 13, the slope our block's, the track its block's
    E(mov_reg, 0, 4)
    E(movs_imm, 1, SY.K_SPARE)
    E(bl, L["c_syv"])
    E(mov_reg, 6, 0)                                                      # r6 = start
    E(mov_reg, 0, 4)
    E(movs_imm, 1, SY.K_REL)
    E(bl, L["c_syv"])
    E(mov_reg, 7, 0)                                                      # r7 = length
    imm32(1, t_soff)
    E(ldrb_reg, 1, 1, 5)
    E(lsls_imm, 0, 4, 6)
    E(adds_reg, 1, 1, 0)
    E(movw, 0, 0x8000 | S.Y0)
    E(adds_reg, 1, 1, 0)
    E(push_list, [1])
    E(cmp_imm, 5, 3)                                                      # j 3: the mode, j 4: the slope
    bc("ew_sm", "eq")
    E(cmp_imm, 5, 4)
    bc("ew_ssl", "eq")
    E(b, "ew_c")
    a.label("ew_sm")
    E(bl, L["c_syb"])
    E(cmp_imm, 0, 0)
    bc("ew_z", "eq")
    E(movs_imm, 1, SY.SL)
    E(muls, 1, 4)
    E(adds_reg, 0, 0, 1)
    E(ldrb_imm, 0, 0, 2)                                                  # the track + 1
    E(b, "ew_mode")
    a.label("ew_ssl")
    E(bl, "c_evb")
    E(cmp_imm, 0, 0)
    bc("ew_z", "eq")
    E(adds_reg, 0, 0, 4)
    E(ldrb_imm, 0, 0, B_SSLP)
    E(b, "ew_slope")
    # a granular slot: its four in our block, the track its block's, on = in use with its gate knob on
    a.label("ew_g")
    E(subs_imm8, 4, NSL)
    imm32(1, t_goff)
    E(ldrb_reg, 1, 1, 5)
    E(lsls_imm, 0, 4, 6)
    E(adds_reg, 1, 1, 0)
    E(movw, 0, 0x8000 | S.GE0)
    E(adds_reg, 1, 1, 0)
    E(push_list, [1])
    E(bl, "c_evb")
    E(cmp_imm, 0, 0)
    bc("ew_z", "eq")
    E(lsls_imm, 1, 4, 2)
    E(adds_reg, 0, 0, 1)
    E(ldrb_imm, 6, 0, B_G)                                                # r6 = start
    E(ldrb_imm, 7, 0, B_G + 1)                                            # r7 = length
    E(cmp_imm, 5, 6)
    bc("ew_gsl", "eq")
    E(cmp_imm, 5, 1)
    bc("ew_gef", "eq")
    E(cmp_imm, 5, 5)
    bc("ew_gm", "eq")
    E(cmp_imm, 5, 0)
    bc("ew_gt", "eq")
    E(cmp_imm, 5, 8)
    bc("ew_gk", "eq")
    # j 2 / 3 / 4 / 7: as a synth's (j - 2)
    E(subs_imm8, 5, 2)
    E(cmp_imm, 5, 5)
    E(b_cond, "ew_c", "ne")
    E(movs_imm, 5, 5)
    E(b, "ew_c")
    a.label("ew_gsl")
    E(ldrb_imm, 0, 0, B_G + 2)
    E(b, "ew_slope")
    a.label("ew_gef")
    E(ldrb_imm, 0, 0, B_G + 3)
    E(b, "ew_slope")
    a.label("ew_gm")
    E(bl, "ew_trk")
    E(b, "ew_mode")
    a.label("ew_gt")
    E(bl, "ew_on")
    E(b, "ew_out")
    a.label("ew_gk")
    E(bl, "ew_on")
    E(cmp_imm, 0, 0)
    E(b_cond, "ew_out", "eq")
    imm32(0, S.KEY)
    E(b, "ew_out")
    # the synth's j (and a granular's 2 / 3 / 4 / 7 as 0 / 1 / 2 / 5): ATK, DEC, HOLD, -, -, RQ
    a.label("ew_c")
    E(cmp_imm, 5, 0)
    E(b_cond, "ew_c1", "ne")
    imm32(0, t_atk)
    E(lsls_imm, 1, 6, 2)
    E(raw, h(0x5840))                                                     # ldr r0, [r0, r1]
    E(b, "ew_out")
    a.label("ew_c1")
    E(cmp_imm, 5, 1)
    E(b_cond, "ew_c2", "ne")
    imm32(0, t_len)
    E(lsls_imm, 1, 7, 2)
    E(raw, h(0x5840))                                                     # ldr r0, [r0, r1]
    E(b, "ew_out")
    a.label("ew_c2")
    E(cmp_imm, 5, 2)
    E(b_cond, "ew_c5", "ne")
    imm32(0, t_lnb)
    E(lsls_imm, 1, 7, 1)
    E(raw, h(0x5A40))                                                     # ldrh r0, [r0, r1]
    E(b, "ew_out")
    a.label("ew_c5")
    imm32(0, RQ)
    E(b, "ew_out")
    a.label("ew_slope")                                                   # r0 = 0..127 -> (v - 64) << 17, 24 bits
    E(subs_imm8, 0, 64)
    E(lsls_imm, 0, 0, 17)
    E(lsls_imm, 0, 0, 8)
    E(lsrs_imm, 0, 0, 8)
    E(b, "ew_out")
    a.label("ew_mode")                                                    # r0 = the track + 1 -> its play mode (0 without), at most 2
    E(cmp_imm, 0, 0)
    E(b_cond, "ew_out", "eq")
    E(subs_imm8, 0, 1)
    E(adds_imm8, 0, 0x10)
    E(movs_imm, 1, 1)
    E(bl, GETTER)
    E(cmp_imm, 0, 2)
    E(b_cond, "ew_out", "ls")
    E(movs_imm, 0, 0)
    E(b, "ew_out")
    a.label("ew_z")
    E(movs_imm, 0, 0)
    a.label("ew_out")
    E(pop_list, [1])
    E(pop_list, [4, 5, 6, 7], pc=True)
    # ew_trk (r4 = the granular slot) -> r0 = its track + 1 (0 = free); ew_on -> r0 = the track + 1 when on (its gate knob on), else 0
    a.label("ew_trk")
    E(push_list, [4], lr=True)
    E(bl, L["c_gnb"])
    E(cmp_imm, 0, 0)
    E(b_cond, "et2_x", "eq")
    E(movs_imm, 1, GP.GN_SLOT)
    E(muls, 1, 4)
    E(adds_reg, 0, 0, 1)
    E(ldrb_imm, 0, 0, 2)
    a.label("et2_x")
    E(pop_list, [4], pc=True)
    a.label("ew_on")
    E(push_list, [4, 5], lr=True)
    E(bl, "ew_trk")
    E(mov_reg, 5, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "eon_x", "eq")
    E(mov_reg, 0, 4)
    E(movs_imm, 1, 11)                                                    # its gate knob (Shift + K8)
    E(bl, L["c_gnv"])
    E(movw, 1, 8192)
    E(cmp_reg, 0, 1)
    E(movs_imm, 0, 0)
    E(b_cond, "eon_x", "lo")
    E(mov_reg, 0, 5)
    a.label("eon_x")
    E(pop_list, [4, 5], pc=True)

    # ---- ev_send(): the words to core 0: a pending slot's all at once (the lowest), else two a frame in turn; all of them at the first
    # frame and when the block's check changed (a project loaded); clobbers r0-r3
    a.label("ev_send")
    E(push_list, [4, 5, 6], lr=True)
    E(bl, L["c_gpmst"])
    E(cmp_imm, 0, 0)
    bc("ev_x", "eq")
    E(mov_reg, 4, 0)                                                      # r4 = the menu's state
    E(bl, "c_evb")
    E(cmp_imm, 0, 0)
    bc("ev_x", "eq")
    E(ldrb_imm, 0, 0, 1)
    E(ldrb_imm, 1, 4, R_SENT)
    E(ldrb_imm, 2, 4, R_SUM)
    E(cmp_imm, 1, 0)
    E(b_cond, "ev_all", "eq")
    E(cmp_reg, 0, 2)
    E(b_cond, "ev_pd", "eq")
    a.label("ev_all")
    E(strb_imm, 0, 4, R_SUM)
    E(movs_imm, 0, 1)
    E(strb_imm, 0, 4, R_SENT)
    E(movs_imm, 0, 0xFF)
    E(strb_imm, 0, 4, R_PEND)
    a.label("ev_pd")
    E(ldrb_imm, 5, 4, R_PEND)
    E(cmp_imm, 5, 0)
    E(b_cond, "ev_rd", "eq")
    E(movs_imm, 6, 0)                                                     # the lowest pending slot
    a.label("ev_fs")
    E(mov_reg, 0, 5)
    E(lsrs_reg, 0, 6)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "ev_go", "ne")
    E(adds_imm8, 6, 1)
    E(b, "ev_fs")
    a.label("ev_go")
    E(movs_imm, 0, 1)
    E(lsls_reg, 0, 6)
    E(bics_reg, 5, 0)
    E(strb_imm, 5, 4, R_PEND)
    E(cmp_imm, 6, NSL)                                                    # its first word and count
    E(b_cond, "ev_gg", "hs")
    E(movs_imm, 5, NWS)
    E(muls, 6, 5)
    E(b, "ev_wa")
    a.label("ev_gg")
    E(subs_imm8, 6, NSL)
    E(movs_imm, 5, NWG)
    E(muls, 6, 5)
    E(adds_imm8, 6, NSL * NWS)
    a.label("ev_wa")
    E(mov_reg, 0, 6)
    E(bl, "ev_w1")
    E(adds_imm8, 6, 1)
    E(subs_imm8, 5, 1)
    E(b_cond, "ev_wa", "ne")
    E(b, "ev_x")
    a.label("ev_rd")
    for _ in range(2):
        E(ldrb_imm, 6, 4, R_ROUND)
        E(cmp_imm, 6, NW)
        E(b_cond, f"ev_r{_}", "lo")
        E(movs_imm, 6, 0)
        a.label(f"ev_r{_}")
        E(mov_reg, 0, 6)
        E(bl, "ev_w1")
        E(adds_imm8, 6, 1)
        E(strb_imm, 6, 4, R_ROUND)
    a.label("ev_x")
    E(pop_list, [4, 5, 6], pc=True)
    # ev_w1(r0 = i): its word written; clobbers r0-r3, r12
    a.label("ev_w1")
    E(push_list, [4], lr=True)
    E(bl, "c_evword")
    E(movs_imm, 2, 0)
    E(bl, L["c_gpw"])
    E(pop_list, [4], pc=True)

    # ---- c_evknob (the container's slot 4, the head of its chain: r0 = container, r1 = knob, r2 = delta)
    a.label("c_evknob")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(cmp_imm, 1, 8)
    bc("kn_p", "hs")
    E(bl, L["c_spview"])
    E(cmp_imm, 0, 8)
    bc("kn_p", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the track
    E(bl, "c_evon")
    E(cmp_imm, 0, 0)
    bc("kn_p", "eq")                                                      # not its Envelope page
    imm32(0, CONT)
    E(bl, SUBVIEW)
    E(cmp_imm, 0, 0)
    bc("kn_p", "eq")                                                      # no knobs in this mode
    E(ldr_sp, 5, 4)                                                       # r5 = k
    E(cmp_imm, 5, 4)
    bc("kn_x", "hs")                                                      # K5-K8: nothing
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, "c_evget")
    E(mov_reg, 6, 0)                                                      # r6 = the value, r1 = the sound
    E(bl, L["c_spheld"])
    E(lsls_imm, 0, 0, 31 - SP.BIT_CLEAR)
    E(b_cond, "kn_t", "pl")
    E(mov_reg, 0, 4)                                                      # Clear + the knob: its default (the sound's)
    E(bl, L["c_sysnd"])
    E(movs_imm, 2, 0)
    E(cmp_imm, 0, SY.SND_SYNTH)
    E(b_cond, "kn_dg", "ne")
    E(movs_imm, 2, 4)
    a.label("kn_dg")
    E(adds_reg, 2, 2, 5)
    imm32(0, t_kdef)
    E(ldrb_reg, 2, 0, 2)
    E(b, "kn_w")
    a.label("kn_t")
    E(ldr_sp, 1, 8)                                                       # the delta, a click a step
    E(adds_reg, 2, 6, 1)
    E(cmp_imm, 2, 0)
    E(b_cond, "kn_h", "ge")
    E(movs_imm, 2, 0)
    a.label("kn_h")
    E(cmp_imm, 2, 127)
    E(b_cond, "kn_w", "le")
    E(movs_imm, 2, 127)
    a.label("kn_w")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, "c_evset")
    a.label("kn_x")
    E(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)
    a.label("kn_p")
    E(raw, GP.popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    E(b_w, prev["knob"])

    # ---- c_evled (the LED task's calls: ctrl, frame): the chain; the words; the menu's pad 5; the Envelope page's LEDs
    a.label("c_evled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)                                                      # r5 = the frame
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("ll_x", "eq")
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    bc("ll_x", "eq")
    E(ldrb_w, 1, 0, O_TH)
    E(cmp_imm, 1, TH.READY)
    E(b_cond, "ll_m", "ne")                                               # core 0 not seen up: no words
    E(bl, "ev_send")
    a.label("ll_m")
    E(bl, L["c_gpmopen"])                                                 # the menu open: pad 5 (and pads 1-4 none chosen on our page)
    E(cmp_imm, 0, 8)
    bc("ll_pg", "hs")
    E(mov_reg, 4, 0)
    E(bl, L["c_sysnd"])
    E(movs_imm, 1, 0)
    E(cmp_imm, 0, SY.SND_GRAN)
    E(b_cond, "lm_a", "eq")
    E(cmp_imm, 0, SY.SND_SYNTH)
    E(b_cond, "lm_w", "ne")
    a.label("lm_a")
    E(mov_reg, 0, 4)
    E(bl, "c_evon")
    E(movs_imm, 1, DIM)
    E(cmp_imm, 0, 0)
    E(b_cond, "lm_w", "eq")
    E(movs_imm, 1, COL)
    for k, (br, dm) in enumerate(((0x01, 0x09), (SP.UI_KNOB, SP.UI_DIM), (GP.UI_KNOB, GP.UI_DIM), (SY.UI_KNOB, SY.UI_DIM))):
        E(raw, h(0x8828 | (k << 6)))                                      # ldrh r0, [r5, #2k]
        E(cmp_imm, 0, br)
        E(b_cond, f"lm_k{k}", "ne")
        E(movs_imm, 0, dm)
        E(strh_imm, 0, 5, 2 * k)
        a.label(f"lm_k{k}")
    a.label("lm_w")
    E(strh_imm, 1, 5, 2 * PAD_ENV)
    a.label("ll_pg")
    E(bl, L["c_spview"])
    E(cmp_imm, 0, 8)
    bc("ll_x", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the track
    E(bl, "c_evon")
    E(cmp_imm, 0, 0)
    bc("ll_x", "eq")
    E(bl, L["c_rst"])
    E(movw, 1, O_KB)
    E(adds_reg, 7, 0, 1)                                                  # r7 = kbright's overlay
    E(movs_imm, 0, 0xFF)
    E(strb_imm, 0, 7, K_MASK)
    for k in range(8):
        if k < 4:
            E(mov_reg, 0, 4)
            E(movs_imm, 1, k)
            E(bl, "c_evget")
            if BIPK[k]:
                E(subs_imm8, 0, 64)                                       # from the middle: |v - 64| x 2
                E(b_cond, f"lq_{k}", "ge")
                E(raw, h(0x4240))                                         # rsbs r0, r0, #0
                a.label(f"lq_{k}")
                E(lsls_imm, 0, 0, 1)
                E(cmp_imm, 0, 127)
                E(b_cond, f"lu_{k}", "le")
                E(movs_imm, 0, 127)
                a.label(f"lu_{k}")
            E(strb_imm, 0, 7, K_VAL + k)
            E(movs_imm, 0, COL)
        else:
            E(movs_imm, 0, 0)
            E(strb_imm, 0, 7, K_VAL + k)
        E(strh_imm, 0, 7, K_CODE + 2 * k)
        E(strh_w_imm, 0, 5, 2 * (LED_KNOB0 + k))
    imm32(0, CI.HAL_TICK)
    E(ldr_imm, 0, 0, 0)
    E(lsls_imm, 0, 0, 23)                                                 # bit 8 of the tick
    bc("ll_x", "pl")
    E(movs_imm, 0, COL)
    E(lsls_imm, 1, 4, 1)
    E(adds_reg, 1, 5, 1)
    E(strh_w_imm, 0, 1, 2 * LED_TRK0)
    E(strh_w_imm, 0, 1, 2 * LED_TRK1)
    a.label("ll_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """The container's knob slot (in front of synthpage's), the head of the LED calls.  Needs synthpage env (its pad 5, c_sysnd), granpage
    multi (env: the engine's gate at 0), synth0 env2 and granchain env on core 0, trkcopy ram (our block in the tail it left)."""
    import rhbuild
    import struct
    BASE = rhbuild.BASE
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]                 # noqa: E731
    assert report["synthpage"].get("env") and report["granpage"].get("env") and report["trkcopy"].get("ram")
    L = dict(c_rst=lab("rhstate", "c_rst"), c_rrt=lab("rhrec", "c_rrt"), c_ciok=lab("countin", "c_ciok"),
             **{k: lab("synthpage", k) for k in ("c_sysnd", "c_syslot", "c_syv", "c_syp", "c_syb")},
             **{k: lab("granpage", k) for k in ("c_gpmst", "c_gpmopen", "c_gpw", "c_gnslot", "c_gnb", "c_gnv")},
             **{k: lab("stockplus", k) for k in ("c_spview", "c_spheld")})
    prev = dict(knob=u(SLOT_KNOB) & ~1, ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert prev["knob"] == lab("synthpage", "c_syknob")
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code_, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code_
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch_word(img, SLOT_KNOB, prev["knob"] | 1, labels["c_evknob"] | 1)
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_evled"]))
    report["envpage"] = dict(prev={k: hex(v) for k, v in prev.items()}, tables=hex(base_addr), block=hex(BLK),
                             labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code_
