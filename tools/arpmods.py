"""The arpeggio's modifiers (MIT; RH63, CIRCUIT-HACKS' arp.use_mods of SC48.3 for the Rhythm's drumarp; the user, 2026-11-01: «Modificadores del
arpegio»).  drumarp calls this with OPT armods.

  * 8 bits per track and pattern, the high nibbles of pattern + 0x105 / + 0x106 (the low nibbles are patchain's B + 1 and C + 1, + 0x104 its n,
    + 0x107 porder's order, + 0x108.. drumpat's: no free byte is left there; the stock's Duplicate copies them while playing, RH65 stopped too):
    bits 0-1 the octave spread, 2-3 the octave's position, 4-5 the groove, 6-7 the reset;
  * Pattern Settings, Shift held, the pattern's arpeggiator on: pads 1-4 the spread (none, +1, +1 / -1, +2 / -1), pads 5-8 when the octave moves (after
    an iteration, every note, every 3, every 4), pads 9-12 the groove (none, note / dotted note, swing, every note twice), pads 13-16 the reset
    (none, after 1 / 3 / 5 notes of the second iteration); the chosen one of each group bright, the others dim; with the arpeggiator off, the stock's;
  * every hit of an arpeggio goes through c_amo instead of c_arord: the reset (an iteration, then N notes of the next, then from the start), the repeat
    of "twice", then the octave on what comes out (the spread follows the order: the down order high to low); the note moved by its octave
    (folded into 0..127); on a sample arpeggio the hit's note moves, the sample stays;
  * the groove's factor of a hit decides the time to the next one, in sixths of an arpeggio step: playing, an accumulator on the micro steps (with
    no groove, the grid as before); stopped, the ms the same.
RAM: rhstate OFF2 "arpmods" (one arpeggio runs at a time).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (adds_imm8, adds_reg, ands_reg, b, b_cond, bics_reg, bl, cmp_imm, cmp_reg, eors_reg, h, ldr_imm, ldr_sp, ldrb_imm, ldrb_reg,  # noqa: E402
                   lsls_imm, lsls_reg, lsrs_imm, mov_reg, movs_imm, movw, muls, orrs_reg, pop_list, push_list, raw, str_imm, strb_imm, strb_reg, strh_reg,
                   subs_imm8, subs_reg)
import rhstate  # noqa: E402

PAT0, TRK_SZ, PAT_SZ = 0x2E4, 0x5140, 0xA28
MOD_OFF = 0x105
EXT = rhstate.ST2 + rhstate.OFF2["arpmods"][0]
X_P, X_FL, X_RC, X_OI, X_OC, X_LP, X_G, X_OCT, X_ACC = 0, 1, 2, 3, 4, 5, 6, 7, 8   # the place in the iteration, flags (bit 0 a repeat next, 1 the groove's
#   phase, 2 the first iteration done, 4 an iteration ended: the octave moves on), the notes after it, the octave's index and count, the last place,
#   the groove's factor of the hit (sixths; 0 = 6), its octave (s8 semitones), the accumulator (u32)
OCT_UP = ((0,), (0, 1), (-1, 0, 1), (-1, 0, 1, 2))         # the octaves of the four spreads, low to high (the down order: high to low)
OCT_T = (0, 1, 3, 4)                                       # the octave's position: after an iteration, every note, every 3, every 4
GROOVE = ((6, 6), (6, 9), (8, 4), (6, 6))                  # none, note / dotted note, swing, every note twice (the steps' sixths)
RESET_N = (0, 1, 3, 5)
MCOL = (0x6D, 0x73, 0x6B, 0x6C, 0x33, 0x34, 0x47, 0x48)    # (bright, dim) a group: spread sand, position salmon, groove light green, reset violet


def tables():
    t = bytes(((x & 0xFF) for r in OCT_UP for x in (r + (0,) * 4)[:4]))
    return t + bytes(OCT_T) + bytes(x for g in GROOVE for x in g) + bytes(RESET_N) + bytes(MCOL)


T_OCT, T_POS, T_GG, T_RN, T_COL = 0, 16, 20, 28, 32


def model(n, order, mods, count, M_DOWN=1, arord=None):
    """the model of c_amo: [(place, octave in semitones, factor)]; arord(k) = the order's place of the k-th call (up by default)"""
    spread, pos, groove, reset = mods & 3, mods >> 2 & 3, mods >> 4 & 3, mods >> 6 & 3
    arord = arord or (lambda k: k % n)
    L = n
    k, p, fl, rc, oi, oc, lp, out = 0, 0, 0, 0, 0, 0, 0, []
    for _ in range(count):
        if mods == 0:
            place = arord(k)
            k += 1
            out.append((place, 0, 6))
            continue
        go = True
        if fl & 1:
            fl &= ~1
            place = lp
            go = lp >= n
        if go:
            place = arord(k)
            k += 1
            lp = place
            if pos == 0 and fl & 0x10:
                fl &= ~0x10
                oi = oi + 1 if oi + 1 < spread + 1 else 0
            N = RESET_N[reset]
            done = False
            if fl & 4 and not N:
                fl &= ~4
            if fl & 4:
                rc += 1
                if rc < N:
                    done = True
                else:
                    k, p, rc = 0, 0, 0
                    fl = (fl & ~4) | 0x10
                    done = True
            if not done:
                p += 1
                if p >= L:
                    p, rc = 0, 0
                    fl |= 4 if N else 0x10
            if groove == 3:
                fl |= 1
        ln = spread + 1
        if oi >= ln:
            oi = 0
        i = ln - oi - 1 if order == M_DOWN else oi
        octv = OCT_UP[spread][i] * 12
        if pos:
            oc += 1
            if oc >= OCT_T[pos]:
                oi = oi + 1 if oi + 1 < ln else 0
                oc = 0
        g = GROOVE[groove][fl >> 1 & 1]
        fl ^= 2
        out.append((place, octv, g))
    return out


def emit(a, E, L, imm32, bc, t_am, S_N, S_K, S_FG, S_FP, S_TRK, M_DOWN, M_PP, M_FRAC, udiv):
    # ---- c_amptr(r0 = track, r1 = pattern) -> r0 = the two bytes of the modifiers (0 without a record); clobbers r1-r3
    a.label("c_amptr")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ap_x", "eq")
    imm32(1, L["tail"] - PAT0 - MOD_OFF)
    E(subs_reg, 0, 0, 1)
    imm32(1, TRK_SZ)
    E(muls, 1, 4)
    E(adds_reg, 0, 0, 1)
    E(movw, 1, PAT_SZ)
    E(muls, 1, 5)
    E(adds_reg, 0, 0, 1)
    a.label("ap_x")
    E(pop_list, [4, 5], pc=True)

    # ---- c_ammo(r0 = track) -> r0 = the modifiers of the pattern it plays; clobbers r1-r3
    a.label("c_ammo")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_dapat")
    E(mov_reg, 1, 0)
    E(mov_reg, 0, 4)
    E(bl, "c_amptr")
    E(cmp_imm, 0, 0)
    E(b_cond, "am_x", "eq")
    E(ldrb_imm, 1, 0, 0)
    E(lsrs_imm, 1, 1, 4)
    E(ldrb_imm, 0, 0, 1)
    E(lsrs_imm, 0, 0, 4)
    E(lsls_imm, 0, 0, 4)
    E(orrs_reg, 0, 1)
    a.label("am_x")
    E(pop_list, [4], pc=True)

    # ---- c_amlen(r0 = n, r1 = the order) -> r0 = the hits of an iteration; clobbers r1
    a.label("c_amlen")
    E(cmp_imm, 1, M_PP)
    E(b_cond, "ln_1", "ne")
    E(cmp_imm, 0, 1)
    E(b_cond, "ln_x", "ls")
    E(lsls_imm, 0, 0, 1)
    E(subs_imm8, 0, 2)
    E(raw, h(0x4770))
    a.label("ln_1")
    E(cmp_imm, 1, M_FRAC)
    E(b_cond, "ln_x", "ne")
    E(mov_reg, 1, 0)
    E(adds_imm8, 1, 1)
    E(muls, 0, 1)
    E(lsrs_imm, 0, 0, 1)
    a.label("ln_x")
    E(raw, h(0x4770))

    # ---- c_amG() -> r0 = the groove's factor of the last hit (sixths); clobbers r1
    a.label("c_amG")
    imm32(1, EXT)
    E(ldrb_imm, 0, 1, X_G)
    E(cmp_imm, 0, 0)
    E(b_cond, "gg_x", "ne")
    E(movs_imm, 0, 6)
    a.label("gg_x")
    E(raw, h(0x4770))

    # ---- c_amz(): the running state from the start; clobbers r0, r1
    a.label("c_amz")
    imm32(1, EXT)
    E(movs_imm, 0, 0)
    for o in (0, 4, 8):
        E(str_imm, 0, 1, o)
    E(raw, h(0x4770))

    # ---- c_amoct(r1 = a note) -> r1 = the note moved by the hit's octave, folded into 0..127; keeps r0, r2, r3
    a.label("c_amoct")
    E(push_list, [0, 2], lr=True)
    imm32(0, EXT)
    E(ldrb_imm, 2, 0, X_OCT)
    E(raw, h(0xB252))                                                     # sxtb r2, r2
    E(adds_reg, 1, 1, 2)
    a.label("ao_l")
    E(cmp_imm, 1, 0)
    E(b_cond, "ao_h", "ge")
    E(adds_imm8, 1, 12)
    E(b, "ao_l")
    a.label("ao_h")
    E(cmp_imm, 1, 127)
    E(b_cond, "ao_x", "le")
    E(subs_imm8, 1, 12)
    E(b, "ao_h")
    a.label("ao_x")
    E(pop_list, [0, 2], pc=True)

    # ---- c_amo(r0 = state, r1 = the order) -> r0 = the place of the next hit, through the modifiers (as c_arord with none).  r4 state, r5 order,
    #      r6 place, r7 the modifiers
    a.label("c_amo")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(ldrb_imm, 0, 4, S_TRK)
    E(bl, "c_ammo")
    E(mov_reg, 7, 0)
    E(cmp_imm, 7, 0)
    E(b_cond, "mo_on", "ne")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, "c_arord")
    E(mov_reg, 6, 0)
    imm32(3, EXT)
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 3, X_OCT)
    E(movs_imm, 0, 6)
    E(strb_imm, 0, 3, X_G)
    E(mov_reg, 0, 6)
    E(pop_list, [4, 5, 6, 7], pc=True)
    a.label("mo_on")
    imm32(3, EXT)
    E(ldrb_imm, 0, 3, X_FL)
    E(lsls_imm, 1, 0, 31)
    E(b_cond, "mo_fr", "pl")                                              # a repeat ("twice")
    E(movs_imm, 1, 1)
    E(bics_reg, 0, 1)
    E(strb_imm, 0, 3, X_FL)
    E(ldrb_imm, 6, 3, X_LP)
    E(ldrb_imm, 1, 4, S_N)
    E(cmp_reg, 6, 1)
    bc("mo_oc", "lo")
    a.label("mo_fr")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, "c_arord")
    E(mov_reg, 6, 0)
    imm32(3, EXT)
    E(strb_imm, 6, 3, X_LP)
    E(lsrs_imm, 0, 7, 2)                                                  # after an iteration: the octave moves on before this hit
    E(movs_imm, 1, 3)
    E(ands_reg, 0, 1)
    E(cmp_imm, 0, 0)
    E(b_cond, "mo_ac", "ne")
    E(ldrb_imm, 0, 3, X_FL)
    E(lsls_imm, 1, 0, 27)
    E(b_cond, "mo_ac", "pl")
    E(movs_imm, 1, 0x10)
    E(bics_reg, 0, 1)
    E(strb_imm, 0, 3, X_FL)
    E(bl, "mo_inc")
    a.label("mo_ac")                                                      # the iteration and the reset
    E(ldrb_imm, 0, 4, S_N)
    E(mov_reg, 1, 5)
    E(bl, "c_amlen")
    E(mov_reg, 12, 0)                                                     # ip = the iteration's length
    E(lsrs_imm, 0, 7, 6)
    imm32(1, t_am + T_RN)
    E(ldrb_reg, 2, 1, 0)                                                  # r2 = N
    imm32(3, EXT)
    E(ldrb_imm, 0, 3, X_FL)
    E(lsls_imm, 1, 0, 29)
    E(b_cond, "mo_it", "pl")
    E(cmp_imm, 2, 0)
    E(b_cond, "mo_fd", "ne")
    E(movs_imm, 1, 4)                                                     # (the reset turned off meanwhile)
    E(bics_reg, 0, 1)
    E(b, "mo_it")
    a.label("mo_fd")
    E(ldrb_imm, 1, 3, X_RC)                                               # after the first iteration: the hits
    E(adds_imm8, 1, 1)
    E(strb_imm, 1, 3, X_RC)
    E(cmp_reg, 1, 2)
    E(b_cond, "mo_rp", "lo")
    E(movs_imm, 1, 0)                                                     # the reset: from the start
    E(strb_imm, 1, 4, S_K)
    E(strb_imm, 1, 4, S_FG)
    E(strb_imm, 1, 4, S_FP)
    E(strb_imm, 1, 3, X_P)
    E(strb_imm, 1, 3, X_RC)
    E(movs_imm, 1, 4)
    E(bics_reg, 0, 1)
    E(movs_imm, 1, 0x10)
    E(orrs_reg, 0, 1)
    E(b, "mo_fw")
    a.label("mo_it")
    E(ldrb_imm, 1, 3, X_P)
    E(adds_imm8, 1, 1)
    E(raw, h(0x4561))                                                     # cmp r1, ip
    E(b_cond, "mo_pw", "lo")
    E(movs_imm, 1, 0)                                                     # the iteration ends
    E(strb_imm, 1, 3, X_RC)
    E(cmp_imm, 2, 0)
    E(b_cond, "mo_nr", "eq")
    E(movs_imm, 2, 4)
    E(orrs_reg, 0, 2)
    E(b, "mo_pw")
    a.label("mo_nr")
    E(movs_imm, 2, 0x10)
    E(orrs_reg, 0, 2)
    a.label("mo_pw")
    E(strb_imm, 1, 3, X_P)
    a.label("mo_fw")
    E(strb_imm, 0, 3, X_FL)
    a.label("mo_rp")
    E(lsrs_imm, 1, 7, 4)
    E(movs_imm, 2, 3)
    E(ands_reg, 1, 2)
    E(cmp_imm, 1, 3)
    E(b_cond, "mo_oc", "ne")                                              # "twice": a repeat next
    E(ldrb_imm, 0, 3, X_FL)
    E(movs_imm, 1, 1)
    E(orrs_reg, 0, 1)
    E(strb_imm, 0, 3, X_FL)
    a.label("mo_oc")                                                      # the octave of this hit
    imm32(3, EXT)
    E(movs_imm, 0, 3)
    E(ands_reg, 0, 7)
    E(lsls_imm, 2, 0, 2)
    E(adds_imm8, 0, 1)                                                    # r0 = the spread's length, r2 = 4 x the spread
    E(ldrb_imm, 1, 3, X_OI)
    E(cmp_reg, 1, 0)
    E(b_cond, "mo_o1", "lo")
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 3, X_OI)
    a.label("mo_o1")
    E(cmp_imm, 5, M_DOWN)
    E(b_cond, "mo_o2", "ne")
    E(subs_reg, 1, 0, 1)
    E(subs_imm8, 1, 1)
    a.label("mo_o2")
    E(adds_reg, 1, 1, 2)
    imm32(2, t_am + T_OCT)
    E(ldrb_reg, 1, 2, 1)
    E(raw, h(0xB249))                                                     # sxtb r1, r1
    E(movs_imm, 2, 12)
    E(muls, 1, 2)
    E(strb_imm, 1, 3, X_OCT)
    E(lsrs_imm, 1, 7, 2)
    E(movs_imm, 2, 3)
    E(ands_reg, 1, 2)
    E(cmp_imm, 1, 0)
    E(b_cond, "mo_gr", "eq")                                              # every 1 / 3 / 4 hits
    imm32(2, t_am + T_POS)
    E(ldrb_reg, 2, 2, 1)
    E(ldrb_imm, 1, 3, X_OC)
    E(adds_imm8, 1, 1)
    E(cmp_reg, 1, 2)
    E(b_cond, "mo_cw", "lo")
    E(bl, "mo_inc")
    E(movs_imm, 1, 0)
    a.label("mo_cw")
    E(strb_imm, 1, 3, X_OC)
    a.label("mo_gr")                                                      # the groove's factor of this hit, the phase on
    E(lsrs_imm, 1, 7, 4)
    E(movs_imm, 2, 3)
    E(ands_reg, 1, 2)
    E(lsls_imm, 1, 1, 1)
    E(ldrb_imm, 0, 3, X_FL)
    E(lsls_imm, 2, 0, 30)
    E(lsrs_imm, 2, 2, 31)
    E(adds_reg, 1, 1, 2)
    imm32(2, t_am + T_GG)
    E(ldrb_reg, 1, 2, 1)
    E(strb_imm, 1, 3, X_G)
    E(movs_imm, 1, 2)
    E(eors_reg, 0, 1)
    E(strb_imm, 0, 3, X_FL)
    E(mov_reg, 0, 6)
    E(pop_list, [4, 5, 6, 7], pc=True)
    # (mo_inc: the octave's index + 1, wrapping at the spread's length; r7 = the modifiers; r3 = EXT afterwards; clobbers r0, r1)
    a.label("mo_inc")
    E(movs_imm, 0, 3)
    E(ands_reg, 0, 7)
    E(adds_imm8, 0, 1)
    imm32(3, EXT)
    E(ldrb_imm, 1, 3, X_OI)
    E(adds_imm8, 1, 1)
    E(cmp_reg, 1, 0)
    E(b_cond, "mi_w", "lo")
    E(movs_imm, 1, 0)
    a.label("mi_w")
    E(strb_imm, 1, 3, X_OI)
    E(raw, h(0x4770))

    # ---- c_amdue(r0 = the arpeggio's ticks, r1 = the track's ticks a step, r5 = the track) -> r0 kept; r1 = 0 the grid decides, 1 due, 2 not yet
    a.label("c_amdue")
    E(push_list, [0, 1, 4], lr=True)
    E(mov_reg, 0, 5)
    E(bl, "c_ammo")
    E(lsrs_imm, 0, 0, 4)
    E(movs_imm, 1, 3)
    E(ands_reg, 0, 1)
    E(subs_imm8, 0, 1)
    E(cmp_imm, 0, 2)
    E(pop_list, [0, 1, 4])
    E(pop_list, [2])
    E(mov_reg, 14, 2)
    E(mov_reg, 2, 1)
    E(movs_imm, 1, 0)
    E(b_cond, "du_x", "hs")                                               # groove 0 / 3 give 0xFFFFFFFF / 2
    imm32(3, EXT)
    E(ldr_imm, 1, 3, X_ACC)
    E(cmp_imm, 1, 0)                                                      # (0 = the first hit: now)
    E(b_cond, "du_d", "eq")
    E(subs_reg, 1, 1, 2)
    E(b_cond, "du_d", "le")
    E(str_imm, 1, 3, X_ACC)
    E(movs_imm, 1, 2)
    E(raw, h(0x4770))
    a.label("du_d")
    E(str_imm, 1, 3, X_ACC)
    E(movs_imm, 1, 1)
    a.label("du_x")
    E(raw, h(0x4770))

    # ---- c_amrun(r0 = the arpeggio's ticks): after a hit, the accumulator + its gap; clobbers r0-r3
    a.label("c_amrun")
    E(mov_reg, 2, 0)
    imm32(3, EXT)
    E(ldrb_imm, 0, 3, X_G)
    E(cmp_imm, 0, 0)
    E(b_cond, "ar_w", "ne")
    E(movs_imm, 0, 6)
    a.label("ar_w")
    E(muls, 0, 2)
    E(ldr_imm, 1, 3, X_ACC)
    E(adds_reg, 1, 1, 0)
    E(str_imm, 1, 3, X_ACC)
    E(raw, h(0x4770))

    # ---- c_ampspad (Pattern Settings' slot 0: view, pad, velocity): Shift, the arpeggiator on: pads 1-16 = a group's option
    a.label("c_ampspad")
    E(cmp_imm, 1, 16)
    bc("mp_s", "hs")
    E(push_list, [0, 1, 2, 4, 5, 6], lr=True)
    E(mov_reg, 6, 1)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("mp_p", "eq")
    E(bl, L["c_cishift"])
    E(cmp_imm, 0, 0)
    bc("mp_p", "eq")
    E(ldr_sp, 0, 0)
    E(bl, L["c_pmtrk"])
    E(cmp_imm, 0, 7)
    bc("mp_p", "hi")
    E(mov_reg, 4, 0)
    E(bl, "c_dapat")
    E(mov_reg, 5, 0)
    E(mov_reg, 1, 5)
    E(mov_reg, 0, 4)
    E(bl, "c_dacfg")
    E(lsls_imm, 0, 0, 24)
    bc("mp_p", "pl")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, "c_amptr")
    E(cmp_imm, 0, 0)
    bc("mp_p", "eq")
    E(mov_reg, 4, 0)
    E(lsrs_imm, 1, 6, 2)
    E(lsls_imm, 1, 1, 1)                                                  # r1 = the group's shift
    E(movs_imm, 2, 3)
    E(ands_reg, 6, 2)
    E(lsls_reg, 2, 1)
    E(lsls_reg, 6, 1)
    E(ldrb_imm, 3, 4, 0)
    E(lsrs_imm, 3, 3, 4)
    E(ldrb_imm, 0, 4, 1)
    E(lsrs_imm, 0, 0, 4)
    E(lsls_imm, 0, 0, 4)
    E(orrs_reg, 0, 3)
    E(bics_reg, 0, 2)
    E(orrs_reg, 0, 6)
    E(ldrb_imm, 3, 4, 0)
    E(lsls_imm, 3, 3, 28)
    E(lsrs_imm, 3, 3, 28)
    E(lsls_imm, 1, 0, 28)
    E(lsrs_imm, 1, 1, 24)
    E(orrs_reg, 3, 1)
    E(strb_imm, 3, 4, 0)
    E(ldrb_imm, 3, 4, 1)
    E(lsls_imm, 3, 3, 28)
    E(lsrs_imm, 3, 3, 28)
    E(lsrs_imm, 0, 0, 4)
    E(lsls_imm, 0, 0, 4)
    E(orrs_reg, 3, 0)
    E(strb_imm, 3, 4, 1)
    E(pop_list, [0, 1, 2, 4, 5, 6], pc=True)
    a.label("mp_p")
    E(raw, h(0xE8BD) + h(sum(1 << r for r in [0, 1, 2, 4, 5, 6]) | 1 << 14))
    a.label("mp_s")
    E(b, "c_dapspad")

    # ---- c_amled(r0 = track, r1 = the LED buffer): pads 1-16 with the arpeggiator on; clobbers r0-r3
    a.label("c_amled")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 7, 1)
    E(bl, "c_ammo")
    E(mov_reg, 6, 0)                                                      # r6 = the modifiers
    imm32(5, t_am + T_COL)
    E(movs_imm, 4, 0)                                                     # r4 = the pad
    a.label("ml_l")
    E(lsrs_imm, 1, 4, 2)
    E(lsls_imm, 2, 1, 1)
    E(mov_reg, 0, 6)
    E(raw, h(0x40D0))                                                     # lsrs r0, r2
    E(movs_imm, 3, 3)
    E(ands_reg, 0, 3)
    E(ands_reg, 3, 4)
    E(cmp_reg, 0, 3)                                                      # the group's option?
    E(ldrb_reg, 1, 5, 2)                                                  # bright
    E(b_cond, "ml_w", "eq")
    E(adds_imm8, 2, 1)
    E(ldrb_reg, 1, 5, 2)                                                  # dim
    a.label("ml_w")
    E(lsls_imm, 0, 4, 1)
    E(strh_reg, 1, 7, 0)
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, 16)
    E(b_cond, "ml_l", "lo")
    E(pop_list, [4, 5, 6, 7], pc=True)
