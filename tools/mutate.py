"""The pattern mutate (MIT; RH86): mefisme's Pattern Mutate of Rhythm Plus (https://github.com/mefisme/rhythm-plus, MIT; credit mefisme),
our own code on its findings, as the user decided (docs/DISENO_RH86.md, 2026-11-10).

What it does:
  * Shift + Duplicate in the Patterns view or the Mixer (a short press): a new seed; every selected track plays a list of patterns drawn
    from its chain, from its next pattern end, looping.  Held 333 ms in the Patterns view = the settings page (Duplicate closes it).
  * The list of a track = gen(seed, track, settings, its chain now): nothing is stored but the seed, the settings and the tracks that
    play a list; the list is made again at each pattern end (a chain changed while it plays gives a new list from the same seed).  The
    settings: Length 1-8; Length type: as the chain / exact / at random 1 .. Length; Amount: all / most / some / a little (the slots of
    the chain that change: (c k + 2) / 4 of them, k = 3, 2, 1); Repeats on / off (off: no slot like its neighbours where a new pick can
    avoid it, 16 picks); Keep slot 1 off / on (on: slot 1 = the chain's first).
  * A tap on a pattern pad of a track (Patterns view, without Clear / Duplicate held) ends its list; Clear + Duplicate, in any view, ends
    every list; the chain mode of patchain on (Shift + 20) ends them too (its rules take every track); a track that mutates leaves its
    rules (patchain's running bit of the track).
  * Each scene keeps the seed, the settings and the tracks with a list (the scene save, its copy); a scene that starts puts them back
    (a scene saved without them: no lists), so the same lists come back, the chains being the scene's.  The project keeps the same.
  * The settings page (the Patterns view's 32 pads, one colour: the chosen value bright, the others dim): column 1 Length 1-4, column 2
    Length 5-8, column 3 Length type (3 rows), column 4 Amount (4 rows), column 5 Repeats (on, off), column 6 Keep slot 1 (off, on); the
    track buttons = the tracks a mutate takes (bright) or not (dim).  Record, Play, Clear and Shift keep it open, any other button
    closes it and does its job; leaving the Patterns view closes it.
  * Closed, in the Patterns view: the pads of the patterns outside a track's list are dark (the one playing keeps the stock's colour).
Where (the Rhythm, read in the emulator):
  * the choice of the next pattern: patchain's c_pcnext (OPT mutate) calls a stub after its rules (c_pcmt) that this module turns into
    a b.w c_mtnext(track, choice, the advance's frame, look-ahead): [frame + 2] the chain's last (r8 its first, the new scene's at a scene
    start), [frame + 0x18] forced (a play start), [frame + 0x44] a scene starts, [frame + 0x48] which;
  * the scene records: R + 0x40 + 40 s, a track's first / last at + 4 t / + 4 t + 1, the scene's flag at + 32 (0 = empty, the stock's
    clear zeroes only these), + 33 .. 39 never written by the stock: ours at + 34 .. 39;
  * the project's: 8 bytes of patchain's part of the tail it never writes (+ 48 .. 55); the running state in its running part (zeroed for
    each loaded project): + 96 + t the slot played + 1, + 104 the last scene seen + 1, + 105 the page / gesture flags, + 108 the press tick.
The block (the project's at patchain + 48, a scene's at its record + 32, the same shape from + 2): + 0 'M' (a scene: the stock's flag),
+ 1 (the project) the tracks a mutate does not take, + 2 the seed (u16), + 4 the settings (u16, bits 9-15 = MARK_HI), + 6 the tracks with
a list, + 7 the check byte (the sum of + 2 .. + 6, XOR 0x5A).  Settings: bits 0-2 Length - 1 XOR 3 (zero = 4), 3-4 the type, 5-6 Amount,
7 Repeats off, 8 Keep slot 1.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b, b_cond, b_w, bics_reg, bl, cmp_imm, cmp_reg, eors_reg, h, ldr_imm, ldr_sp,  # noqa: E402
                   ldrb_imm, ldrb_reg, ldrb_w, ldrh_imm, lsls_imm, lsls_reg, lsrs_imm, lsrs_reg, mov_reg, movs_imm, movt, movw, muls,
                   orrs_reg, pop_list, push_list, raw, str_imm, str_sp, strb_imm, strb_reg, strb_w, strh_imm, strh_reg, subs_imm8, subs_reg,
                   tst_reg)
import countin as CI  # noqa: E402
import patchain as PC  # noqa: E402
import rhrec  # noqa: E402

ENG, PARAM_GET = 0x2003C380, 0x0803FC58
CTRL, PV, MIXV = CI.CTRL, PC.PV, PC.MIXV
PV_VT = PC.PV_VT
TRACKFN, PATFN = PC.TRACKFN, PC.PATFN
HAL_TICK, TRANSPORT = CI.HAL_TICK, CI.TRANSPORT
ID_REC, ID_PLAY, ID_UP, ID_CLEAR, ID_DUP, ID_SHIFT = 16, CI.ID_PLAY, 20, 23, 24, 27
LED_TRK0 = 32
HOLD_MS = 333                                             # the stock's hold
COL, DIM = 0xA3, 0xA4                                     # the page: orange-red, its dim (steady codes, unused elsewhere)
A_LCG, C_LCG, K_TRK = 1664525, 1013904223, 0x9E3779B1
CHECK_X, MARK, MARK_HI = 0x5A, ord("M"), 0xB4
NOREP_TRIES = 16
B_LIVE = 48                                               # the project's block in patchain's part of the tail
O_POS, O_LASTSC, O_UI, O_T0 = 96, 104, 105, 108           # patchain's running part (+ 64 .. + 127)
UI_PAGE, UI_PEND, UI_MIX = 1, 2, 4
S_LIVE = PC.SCR + PC.S_LIVE
SC_BASE = 0x29110 - 0x40 - 32                             # the tail -> scene 0's record + 32
# the page's columns: (shift, mask, xor, rows | base << 4)
COLS = ((0, 7, 3, 4), (0, 7, 3, 4 | 4 << 4), (3, 3, 0, 3), (5, 3, 0, 4), (7, 1, 0, 2), (8, 1, 0, 2))
# (RH89, OPT amt8) Amount in two columns: all, then 7 .. 1 slots that change; Repeats / Keep slot 1 one column on
COLS8 = ((0, 7, 3, 4), (0, 7, 3, 4 | 4 << 4), (3, 3, 0, 3), (5, 7, 0, 4), (5, 7, 0, 4 | 4 << 4), (8, 1, 0, 2), (9, 1, 0, 2))
CPSID, CPSIE, BX_LR = h(0xB672), h(0xB662), h(0x4770)
INV = PC.INV


def mvns(rd, rm): return h(0x43C0 | rm << 3 | rd)


def amt8():
    """(RH89, OPT amt8; the user, 2026-11-10: «make mutate column 4 two columns with more values» -> «Exact slot counts»): Amount = 3 bits
    (5-7): 0 every slot, 1 .. 7 = 7 .. 1 slots of the chain change; Repeats off bit 8, Keep slot 1 bit 9 (the mark's bits 10-15)"""
    import rhbuild
    return bool(rhbuild.OPT.get("amt8"))


def cols():
    return COLS8 if amt8() else COLS


def mtend():
    """(RH88, OPT mtend; the user, 2026-11-10: «do mutated patterns change to the next scene when over?» -> «Yes, build RH88») the end of a
    mutating track's chain = its list's last slot (a scene of several waits for the whole list), patchain's c_pcend asks c_mtme"""
    import rhbuild
    return bool(rhbuild.OPT.get("mtend"))
def add_sp_imm(rd, imm): return h(0xA800 | rd << 8 | imm // 4)


# ---------------------------------------------------------------- the model (c_mtgen does the same, word for word)
def gen(seed, st, t, first, last):
    """the list of track t: seed (u16), st the settings (9 bits), the chain first .. last"""
    M = 0xFFFFFFFF
    if first > last:
        first, last = last, first
    clen = last - first + 1
    s = [((seed & 0xFFFF) * 0x10001 + (t * K_TRK & M)) & M]

    def rnd():
        s[0] = (s[0] * A_LCG + C_LCG) & M
        return s[0] >> 16
    A8 = amt8()
    L = ((st & 7) ^ 3) + 1
    typ = st >> 3 & 3
    amt = st >> 5 & (7 if A8 else 3)
    norep = st >> (8 if A8 else 7) & 1
    keep1 = st >> (9 if A8 else 8) & 1
    n = clen if typ == 0 else L if typ == 1 else 1 + (rnd() * L >> 16)
    keep = 1 if keep1 and n >= 2 else 0
    chg = 0xFF
    if amt:
        k = 4 - amt
        c = min(n, clen) - keep
        m = 8 - amt if A8 else (c * k + 2) >> 2 or 1
        if m < c:
            chg = 0
            while m:
                i = rnd() * c >> 16
                if not chg >> i & 1:
                    chg |= 1 << i
                    m -= 1
            chg <<= keep

    def fixed(j):
        if j == 0 and keep:
            return first
        if j < clen and not chg >> j & 1:
            return first + j
        return 0xFF
    out = []
    for i in range(n):
        v = fixed(i)
        if v == 0xFF:
            tries = NOREP_TRIES
            while True:
                v = first + (rnd() * clen >> 16)
                if not norep or tries == 0:
                    break
                tries -= 1
                if i > 0 and v == out[i - 1]:
                    continue
                if i + 1 < n:
                    if fixed(i + 1) == v:
                        continue
                elif i > 0 and v == out[0]:
                    continue
                break
        out.append(v)
    return out


def settings(length=4, typ=0, amount=0, repeats=True, keep1=False):
    if amt8():                                                            # (RH89) amount: 0 all, 1 .. 7 = 7 .. 1 slots
        return ((length - 1) ^ 3) | typ << 3 | amount << 5 | (0 if repeats else 1) << 8 | (1 if keep1 else 0) << 9
    return ((length - 1) ^ 3) | typ << 3 | amount << 5 | (0 if repeats else 1) << 7 | (1 if keep1 else 0) << 8


def check(blk):
    """the check byte of a block (+ 2 .. + 6)"""
    return (sum(blk[2:7]) ^ CHECK_X) & 0xFF


# ---------------------------------------------------------------- the code
def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit
    zc = [0]

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        if v >> 16:
            E(movt, rd, (v >> 16) & 0xFFFF)

    def bc(target, cond):
        zc[0] += 1
        n = f"_m{zc[0]}"
        E(b_cond, n, INV[cond])
        E(b, target)
        a.label(n)

    A8 = amt8()
    CO = cols()
    t_cols = base
    E(raw, b"".join(bytes(c_) for c_ in CO))

    # ---- c_mtrnd(r4 = the state) -> r0 = the next 16 random bits; clobbers r1
    a.label("c_mtrnd")
    imm32(1, A_LCG)
    E(muls, 4, 1)
    imm32(1, C_LCG)
    E(adds_reg, 4, 4, 1)
    E(lsrs_imm, 0, 4, 16)
    E(raw, BX_LR)

    # ---- the fixed slot j (r0) of c_mtgen's list -> r0 = its pattern or 0xFF; [sp + 4] chg, [sp + 8] keep (c_mtgen's stack); clobbers r1
    a.label("mg_fix")
    E(cmp_imm, 0, 0)
    E(b_cond, "mf_1", "ne")
    E(ldr_sp, 1, 8)
    E(cmp_imm, 1, 0)
    E(b_cond, "mf_1", "eq")
    E(mov_reg, 0, 6)
    E(raw, BX_LR)
    a.label("mf_1")
    E(cmp_reg, 0, 7)
    E(b_cond, "mf_n", "hs")
    E(ldr_sp, 1, 4)
    E(lsrs_reg, 1, 0)
    E(lsls_imm, 1, 1, 31)
    E(b_cond, "mf_n", "mi")
    E(adds_reg, 0, 0, 6)
    E(raw, BX_LR)
    a.label("mf_n")
    E(movs_imm, 0, 0xFF)
    E(raw, BX_LR)

    # ---- c_mtgen(r0 = track, r1 = first | last << 8, r2 = seed | settings << 16, r3 = the list, 8 B) -> r0 = its length; clobbers r1-r3, r12
    #      the stack: + 0 n, + 4 chg, + 8 keep, + 12 the settings, then Repeats off
    a.label("c_mtgen")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(raw, h(0xB084))                                                     # sub sp, #16
    E(mov_reg, 5, 3)
    E(lsrs_imm, 3, 2, 16)
    E(str_sp, 3, 12)
    E(lsls_imm, 2, 2, 16)
    E(lsrs_imm, 3, 2, 16)
    E(orrs_reg, 2, 3)                                                     # seed x 0x10001
    imm32(3, K_TRK)
    E(muls, 3, 0)
    E(adds_reg, 4, 2, 3)                                                  # r4 = the state
    E(lsrs_imm, 7, 1, 8)
    E(lsls_imm, 6, 1, 24)
    E(lsrs_imm, 6, 6, 24)
    E(cmp_reg, 6, 7)
    E(b_cond, "mg_o", "ls")
    E(mov_reg, 3, 6)
    E(mov_reg, 6, 7)
    E(mov_reg, 7, 3)
    a.label("mg_o")
    E(subs_reg, 7, 7, 6)
    E(adds_imm8, 7, 1)                                                    # r6 = first, r7 = the chain's length
    E(ldr_sp, 3, 12)
    E(lsls_imm, 0, 3, 29)
    E(lsrs_imm, 0, 0, 29)
    E(movs_imm, 1, 3)
    E(eors_reg, 0, 1)
    E(adds_imm8, 0, 1)                                                    # r0 = Length
    E(lsls_imm, 1, 3, 27)
    E(lsrs_imm, 1, 1, 30)                                                 # the type
    E(mov_reg, 2, 7)
    E(cmp_imm, 1, 0)
    E(b_cond, "mg_n", "eq")
    E(mov_reg, 2, 0)
    E(cmp_imm, 1, 1)
    E(b_cond, "mg_n", "eq")
    E(bl, "c_mtrnd")
    E(muls, 0, 2)
    E(lsrs_imm, 0, 0, 16)
    E(adds_imm8, 0, 1)
    E(mov_reg, 2, 0)
    a.label("mg_n")
    E(str_sp, 2, 0)                                                       # n
    E(movs_imm, 0, 0)
    E(ldr_sp, 3, 12)
    E(lsrs_imm, 1, 3, 10 if A8 else 9)                                    # the carry = Keep slot 1
    E(b_cond, "mg_k", "cc")
    E(cmp_imm, 2, 2)
    E(b_cond, "mg_k", "lo")
    E(movs_imm, 0, 1)
    a.label("mg_k")
    E(str_sp, 0, 8)                                                       # keep
    E(movs_imm, 1, 0xFF)
    E(str_sp, 1, 4)
    E(lsls_imm, 1, 3, 24 if A8 else 25)
    E(lsrs_imm, 1, 1, 29 if A8 else 30)                                   # Amount
    E(cmp_imm, 1, 0)
    E(b_cond, "mg_g", "eq")
    E(movs_imm, 0, 8 if A8 else 4)
    E(subs_reg, 1, 0, 1)                                                  # k (amt8: m, the slots that change)
    E(mov_reg, 0, 2)
    E(cmp_reg, 0, 7)
    E(b_cond, "mg_c", "ls")
    E(mov_reg, 0, 7)
    a.label("mg_c")
    E(ldr_sp, 3, 8)
    E(subs_reg, 0, 0, 3)                                                  # r0 = c
    if not A8:
        E(muls, 1, 0)
        E(adds_imm8, 1, 2)
        E(lsrs_imm, 1, 1, 2)
        E(b_cond, "mg_m", "ne")
        E(movs_imm, 1, 1)
    a.label("mg_m")
    E(cmp_reg, 1, 0)
    E(b_cond, "mg_g", "hs")                                               # every slot changes
    E(mov_reg, 2, 0)
    E(mov_reg, 3, 1)
    E(movs_imm, 0, 0)
    E(str_sp, 0, 4)
    a.label("mg_l")
    E(bl, "c_mtrnd")
    E(muls, 0, 2)
    E(lsrs_imm, 0, 0, 16)
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 0)
    E(ldr_sp, 0, 4)
    E(tst_reg, 0, 1)
    E(b_cond, "mg_l", "ne")
    E(orrs_reg, 0, 1)
    E(str_sp, 0, 4)
    E(subs_imm8, 3, 1)
    E(b_cond, "mg_l", "ne")
    E(ldr_sp, 1, 8)
    E(lsls_reg, 0, 1)
    E(str_sp, 0, 4)
    a.label("mg_g")
    E(ldr_sp, 3, 12)
    E(lsls_imm, 3, 3, 23 if A8 else 24)
    E(lsrs_imm, 3, 3, 31)
    E(str_sp, 3, 12)                                                      # Repeats off
    E(movs_imm, 3, 0)
    a.label("mg_lp")
    E(ldr_sp, 0, 0)
    E(cmp_reg, 3, 0)
    bc("mg_x", "hs")
    E(mov_reg, 0, 3)
    E(bl, "mg_fix")
    E(cmp_imm, 0, 0xFF)
    E(b_cond, "mg_st", "ne")
    E(movs_imm, 2, NOREP_TRIES)
    a.label("mg_p")
    E(bl, "c_mtrnd")
    E(muls, 0, 7)
    E(lsrs_imm, 0, 0, 16)
    E(adds_reg, 0, 0, 6)
    E(ldr_sp, 1, 12)
    E(cmp_imm, 1, 0)
    E(b_cond, "mg_st", "eq")
    E(cmp_imm, 2, 0)
    E(b_cond, "mg_st", "eq")
    E(subs_imm8, 2, 1)
    E(cmp_imm, 3, 0)
    E(b_cond, "mg_q", "eq")
    E(subs_imm8, 3, 1)
    E(ldrb_reg, 1, 5, 3)
    E(adds_imm8, 3, 1)
    E(cmp_reg, 0, 1)
    E(b_cond, "mg_p", "eq")
    a.label("mg_q")
    E(mov_reg, 12, 0)
    E(mov_reg, 0, 3)
    E(adds_imm8, 0, 1)
    E(ldr_sp, 1, 0)
    E(cmp_reg, 0, 1)
    E(b_cond, "mg_w", "hs")
    E(bl, "mg_fix")
    E(mov_reg, 1, 12)
    E(cmp_reg, 0, 1)
    E(b_cond, "mg_p", "eq")
    E(b, "mg_ok")
    a.label("mg_w")
    E(cmp_imm, 3, 0)
    E(b_cond, "mg_ok", "eq")
    E(ldrb_imm, 0, 5, 0)
    E(mov_reg, 1, 12)
    E(cmp_reg, 0, 1)
    E(b_cond, "mg_p", "eq")
    a.label("mg_ok")
    E(mov_reg, 0, 12)
    a.label("mg_st")
    E(strb_reg, 0, 5, 3)
    E(adds_imm8, 3, 1)
    E(b, "mg_lp")
    a.label("mg_x")
    E(ldr_sp, 0, 0)
    E(raw, h(0xB004))                                                     # add sp, #16
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_mtss(r0 = a block) -> r0 = seed | settings << 16; clobbers r1
    a.label("c_mtss")
    E(ldrh_imm, 1, 0, 2)
    E(ldrh_imm, 0, 0, 4)
    E(lsls_imm, 0, 0, 22 if A8 else 23)
    E(lsrs_imm, 0, 0, 6 if A8 else 7)
    E(orrs_reg, 0, 1)
    E(raw, BX_LR)

    # ---- c_mtck(r0 = a block) -> r0 = its check byte; clobbers r1-r3
    a.label("c_mtck")
    E(movs_imm, 1, 2)
    E(movs_imm, 2, 0)
    a.label("ck_l")
    E(ldrb_reg, 3, 0, 1)
    E(adds_reg, 2, 2, 3)
    E(adds_imm8, 1, 1)
    E(cmp_imm, 1, 7)
    E(b_cond, "ck_l", "lo")
    E(movs_imm, 0, CHECK_X)
    E(eors_reg, 0, 2)
    E(lsls_imm, 0, 0, 24)
    E(lsrs_imm, 0, 0, 24)
    E(raw, BX_LR)

    # ---- c_mtsum(r0 = a block): its check byte written; clobbers r1-r3
    a.label("c_mtsum")
    E(push_list, [0], lr=True)
    E(bl, "c_mtck")
    E(pop_list, [1])
    E(strb_imm, 0, 1, 7)
    E(mov_reg, 0, 1)
    E(pop_list, [], pc=True)

    # ---- c_mtg() -> r0 = the project's block (an empty one made when it is not ours), 0 without the record; clobbers r1-r3
    a.label("c_mtg")
    E(push_list, [4], lr=True)
    E(bl, L["c_pcst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "gg_x", "eq")
    E(adds_imm8, 0, B_LIVE)
    E(mov_reg, 4, 0)
    E(ldrb_imm, 1, 4, 0)
    E(cmp_imm, 1, MARK)
    E(b_cond, "gg_f", "ne")
    E(bl, "c_mtck")
    E(ldrb_imm, 1, 4, 7)
    E(cmp_reg, 0, 1)
    E(b_cond, "gg_ok", "eq")
    a.label("gg_f")
    E(movs_imm, 0, 0)
    E(str_imm, 0, 4, 0)
    E(str_imm, 0, 4, 4)
    E(movs_imm, 0, MARK)
    E(strb_imm, 0, 4, 0)
    E(movs_imm, 0, MARK_HI)
    E(strb_imm, 0, 4, 5)
    E(mov_reg, 0, 4)
    E(bl, "c_mtsum")
    a.label("gg_ok")
    E(mov_reg, 0, 4)
    a.label("gg_x")
    E(pop_list, [4], pc=True)

    # ---- c_mtsc(r0 = scene) -> r0 = its record + 32 (0 past 16 or without the record); c_mtscv: 0 too when not a scene of ours; clobbers r1-r3
    a.label("c_mtsc")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(cmp_imm, 4, 16)
    E(b_cond, "sc_0", "hs")
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "sc_0", "eq")
    imm32(1, SC_BASE)
    E(subs_reg, 0, 0, 1)
    E(movs_imm, 1, 40)
    E(muls, 1, 4)
    E(adds_reg, 0, 0, 1)
    E(pop_list, [4], pc=True)
    a.label("sc_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)

    a.label("c_mtscv")
    E(push_list, [4], lr=True)
    E(bl, "c_mtsc")
    E(mov_reg, 4, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "sv_0", "eq")
    E(ldrb_imm, 1, 4, 0)
    E(cmp_imm, 1, 0)
    E(b_cond, "sv_0", "eq")                                               # an empty scene
    E(ldrb_imm, 1, 4, 5)
    E(lsrs_imm, 1, 1, 2 if A8 else 1)
    E(cmp_imm, 1, MARK_HI >> (2 if A8 else 1))
    E(b_cond, "sv_0", "ne")
    E(bl, "c_mtck")
    E(ldrb_imm, 1, 4, 7)
    E(cmp_reg, 0, 1)
    E(b_cond, "sv_0", "ne")
    E(mov_reg, 0, 4)
    E(pop_list, [4], pc=True)
    a.label("sv_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)

    # ---- c_mtcp(r0 = from, r1 = to): + 2 .. + 7 of a block; clobbers r2, r3
    a.label("c_mtcp")
    E(movs_imm, 2, 2)
    a.label("cp_l")
    E(ldrb_reg, 3, 0, 2)
    E(strb_reg, 3, 1, 2)
    E(adds_imm8, 2, 1)
    E(cmp_imm, 2, 8)
    E(b_cond, "cp_l", "lo")
    E(raw, BX_LR)

    # ---- c_mtload(r0 = scene): the scene's into the project's (a scene without ours: no lists); clobbers r0-r3
    a.label("c_mtload")
    E(push_list, [4], lr=True)
    E(bl, "c_mtscv")
    E(mov_reg, 4, 0)
    E(bl, "c_mtg")
    E(cmp_imm, 0, 0)
    E(b_cond, "ld_x", "eq")
    E(raw, CPSID)
    E(cmp_imm, 4, 0)
    E(b_cond, "ld_i", "eq")
    E(mov_reg, 1, 0)
    E(mov_reg, 0, 4)
    E(bl, "c_mtcp")
    E(b, "ld_e")
    a.label("ld_i")
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 0, 6)
    E(bl, "c_mtsum")
    a.label("ld_e")
    E(raw, CPSIE)
    a.label("ld_x")
    E(pop_list, [4], pc=True)

    # ---- c_mtoff(r0 = tracks): their lists end; clobbers r0-r3
    a.label("c_mtoff")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_mtg")
    E(cmp_imm, 0, 0)
    E(b_cond, "of_x", "eq")
    E(raw, CPSID)
    E(ldrb_imm, 1, 0, 6)
    E(bics_reg, 1, 4)
    E(strb_imm, 1, 0, 6)
    E(bl, "c_mtsum")
    E(raw, CPSIE)
    a.label("of_x")
    E(pop_list, [4], pc=True)

    # ---- c_mtdo(): the mutate: a new seed, the tracks it takes play their lists from their next pattern end, out of the rules
    a.label("c_mtdo")
    E(push_list, [4], lr=True)
    E(bl, "c_mtg")
    E(cmp_imm, 0, 0)
    E(b_cond, "do_x", "eq")
    E(mov_reg, 4, 0)
    E(raw, CPSID)
    E(ldrh_imm, 0, 4, 2)
    imm32(1, HAL_TICK)
    E(ldr_imm, 1, 1, 0)
    E(eors_reg, 0, 1)
    imm32(1, A_LCG)
    E(muls, 0, 1)
    imm32(1, C_LCG)
    E(adds_reg, 0, 0, 1)
    E(lsrs_imm, 0, 0, 16)
    E(strh_imm, 0, 4, 2)
    E(ldrb_imm, 0, 4, 1)
    E(raw, mvns(0, 0))
    E(strb_imm, 0, 4, 6)
    E(mov_reg, 0, 4)
    E(bl, "c_mtsum")
    E(mov_reg, 0, 4)
    E(subs_imm8, 0, B_LIVE)                                               # patchain's part
    E(movs_imm, 1, 0)
    E(str_imm, 1, 0, O_POS)
    E(str_imm, 1, 0, O_POS + 4)
    E(raw, ldrb_w(1, 0, S_LIVE))
    E(ldrb_imm, 2, 4, 6)
    E(bics_reg, 1, 2)
    E(raw, strb_w(1, 0, S_LIVE))
    E(raw, CPSIE)
    a.label("do_x")
    E(pop_list, [4], pc=True)

    # ---- c_mtnext(r0 = track, r1 = the choice, r2 = the advance's frame, r3 = look-ahead) -> r0 = the next pattern (the stub in c_pcnext)
    #      the stack: + 0 the list, + 8 the block, + 12 restart
    a.label("c_mtnext")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(raw, h(0xB084))                                                     # sub sp, #16
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(mov_reg, 6, 2)
    E(mov_reg, 7, 3)
    E(cmp_imm, 4, 8)
    bc("nx_r", "hs")
    E(movs_imm, 0, 0)
    E(str_sp, 0, 12)
    E(raw, ldrb_w(0, 6, 0x44))
    E(cmp_imm, 0, 0)
    E(b_cond, "nx_n", "eq")
    E(movs_imm, 0, 1)
    E(str_sp, 0, 12)                                                      # a scene starts: slot 1 of its list
    E(ldr_imm, 0, 6, 0x48)
    E(cmp_imm, 7, 0)
    E(b_cond, "nx_pk", "ne")
    E(bl, "c_mtload")
    E(b, "nx_n")
    a.label("nx_pk")                                                      # the look-ahead only peeks
    E(bl, "c_mtscv")
    E(cmp_imm, 0, 0)
    bc("nx_r", "eq")
    E(b, "nx_b")
    a.label("nx_n")
    E(raw, ldrb_w(0, 6, 0x18))
    E(cmp_imm, 0, 0)
    E(b_cond, "nx_g", "eq")
    E(movs_imm, 0, 1)
    E(str_sp, 0, 12)                                                      # forced (a play start): slot 1
    a.label("nx_g")
    E(bl, "c_mtg")
    E(cmp_imm, 0, 0)
    bc("nx_r", "eq")
    a.label("nx_b")
    E(str_sp, 0, 8)
    E(ldrb_imm, 1, 0, 6)
    E(lsrs_reg, 1, 4)
    E(lsls_imm, 1, 1, 31)
    bc("nx_r", "pl")                                                      # no list
    E(bl, "c_mtss")
    E(mov_reg, 2, 0)
    E(mov_reg, 1, 8)
    E(ldrb_imm, 3, 6, 2)
    E(lsls_imm, 3, 3, 8)
    E(orrs_reg, 1, 3)
    E(mov_reg, 0, 4)
    E(mov_reg, 3, 13)
    E(bl, "c_mtgen")
    E(mov_reg, 5, 0)                                                      # r5 = n
    E(bl, L["c_pcst"])
    E(movs_imm, 2, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "nx_a", "eq")
    E(adds_reg, 1, 0, 4)
    E(adds_imm8, 1, O_POS)                                                # r1 = the track's slot + 1
    E(ldr_sp, 3, 12)
    E(cmp_imm, 3, 0)
    E(b_cond, "nx_s", "ne")
    E(ldrb_imm, 2, 1, 0)
    E(cmp_reg, 2, 5)
    E(b_cond, "nx_s0", "lo")
    a.label("nx_s")
    E(movs_imm, 2, 0)
    a.label("nx_s0")
    E(cmp_imm, 7, 0)
    E(b_cond, "nx_a", "ne")                                               # the look-ahead: nothing changed
    E(adds_imm8, 2, 1)
    E(strb_imm, 2, 1, 0)
    E(subs_imm8, 2, 1)
    E(raw, ldrb_w(3, 0, S_LIVE))                                          # out of the rules
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(bics_reg, 3, 1)
    E(raw, strb_w(3, 0, S_LIVE))
    a.label("nx_a")
    E(mov_reg, 0, 13)
    E(ldrb_reg, 0, 0, 2)
    E(b, "nx_e")
    a.label("nx_r")
    E(mov_reg, 0, 5)
    a.label("nx_e")
    E(raw, h(0xB004))                                                     # add sp, #16
    E(pop_list, [4, 5, 6, 7], pc=True)

    if mtend():
        # ---- c_mtme(r0 = track, r1 = its pattern ending) (patchain's c_pcme): 0 = no list, 1 = the list's last slot (the end), 2 = not the end
        a.label("c_mtme")
        E(push_list, [4, 5, 6], lr=True)
        E(raw, h(0xB082))                                                 # sub sp, #8
        E(mov_reg, 4, 0)
        E(bl, "c_mtg")
        E(cmp_imm, 0, 0)
        E(b_cond, "me_0", "eq")
        E(mov_reg, 6, 0)
        E(ldrb_imm, 1, 0, 6)
        E(lsrs_reg, 1, 4)
        E(lsls_imm, 1, 1, 31)
        E(b_cond, "me_0", "pl")
        E(bl, L["c_pcst"])
        E(cmp_imm, 0, 0)
        E(b_cond, "me_0", "eq")
        E(adds_reg, 0, 0, 4)
        E(raw, ldrb_w(5, 0, O_POS))                                       # r5 = the slot playing + 1
        E(cmp_imm, 5, 0)
        E(b_cond, "me_0", "eq")
        imm32(0, ENG + 0x9C)
        E(ldr_imm, 0, 0, 0)
        E(mov_reg, 1, 4)
        E(bl, PARAM_GET)
        E(ldrb_imm, 1, 0, 0)
        E(ldrb_imm, 0, 0, 1)
        E(lsls_imm, 0, 0, 8)
        E(orrs_reg, 1, 0)
        E(push_list, [1])
        E(mov_reg, 0, 6)
        E(bl, "c_mtss")
        E(mov_reg, 2, 0)
        E(pop_list, [1])
        E(mov_reg, 0, 4)
        E(mov_reg, 3, 13)
        E(bl, "c_mtgen")
        E(movs_imm, 1, 2)
        E(cmp_reg, 5, 0)
        E(b_cond, "me_r", "ne")
        E(movs_imm, 1, 1)
        a.label("me_r")
        E(mov_reg, 0, 1)
        E(b, "me_x")
        a.label("me_0")
        E(movs_imm, 0, 0)
        a.label("me_x")
        E(raw, h(0xB002))                                                 # add sp, #8
        E(pop_list, [4, 5, 6], pc=True)

    # ---- c_mtssave / c_mtscopy (the scene save's and copy's first writes, ahead of patchain's): ours into the scene
    a.label("c_mtssave")
    E(push_list, [0, 1, 2, 3, 4], lr=True)
    E(mov_reg, 0, 1)
    E(bl, "c_mtsc")
    E(mov_reg, 4, 0)
    E(bl, "c_mtg")
    E(cmp_imm, 0, 0)
    E(b_cond, "ss_x", "eq")
    E(cmp_imm, 4, 0)
    E(b_cond, "ss_x", "eq")
    E(mov_reg, 1, 4)
    E(bl, "c_mtcp")
    a.label("ss_x")
    E(raw, h(0xE8BD) + h(0x401F))                                         # pop.w {r0-r4, lr}
    E(b_w, prev["ssave"])

    a.label("c_mtscopy")
    E(push_list, [0, 1, 2, 3, 4], lr=True)
    E(ldrb_imm, 0, 7, 1)
    E(bl, "c_mtsc")
    E(mov_reg, 4, 0)
    E(ldr_sp, 0, 4)
    E(bl, "c_mtsc")
    E(mov_reg, 1, 0)
    E(cmp_imm, 1, 0)
    E(b_cond, "sy_x", "eq")
    E(cmp_imm, 4, 0)
    E(b_cond, "sy_x", "eq")
    E(mov_reg, 0, 4)
    E(bl, "c_mtcp")
    a.label("sy_x")
    E(raw, h(0xE8BD) + h(0x401F))
    E(b_w, prev["scopy"])

    # ---- c_mtpp (the Patterns view's pad press, ahead of patchain's): the page takes the pads; a pattern pad ends its track's list
    a.label("c_mtpp")
    E(push_list, [0, 1, 2, 3, 4], lr=True)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "pp_p", "eq")
    E(bl, L["c_pcst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "pp_p", "eq")
    E(raw, ldrb_w(1, 0, O_UI))
    E(lsls_imm, 1, 1, 31)
    E(b_cond, "pp_pg", "mi")
    E(ldr_sp, 0, 0)                                                       # closed: not with Clear / Duplicate held
    E(ldr_imm, 0, 0, PC.O_HELD_PV)
    E(movs_imm, 1, 0)
    E(bl, PARAM_GET)
    E(ldrb_imm, 0, 0, 0)
    E(lsls_imm, 0, 0, 30)
    E(b_cond, "pp_p", "ne")
    E(ldr_sp, 0, 4)
    E(bl, TRACKFN)
    E(cmp_imm, 0, 8)
    E(b_cond, "pp_p", "hs")
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 0)
    E(mov_reg, 0, 1)
    E(bl, "c_mtoff")
    a.label("pp_p")
    E(raw, h(0xE8BD) + h(0x401F))
    E(b_w, prev["pad"])
    a.label("pp_pg")                                                      # the page: the pad sets its column's value
    E(ldr_sp, 4, 4)
    E(lsrs_imm, 1, 4, 3)
    E(lsls_imm, 0, 4, 29)
    E(lsrs_imm, 0, 0, 29)
    E(cmp_imm, 0, len(CO))
    E(b_cond, "pp_s", "hs")
    imm32(4, t_cols)
    E(lsls_imm, 0, 0, 2)
    E(adds_reg, 4, 4, 0)                                                  # r4 = the column
    E(ldrb_imm, 2, 4, 3)
    E(lsls_imm, 3, 2, 28)
    E(lsrs_imm, 3, 3, 28)
    E(cmp_reg, 1, 3)
    E(b_cond, "pp_s", "hs")
    E(lsrs_imm, 2, 2, 4)
    E(adds_reg, 1, 1, 2)
    E(ldrb_imm, 2, 4, 2)
    E(eors_reg, 1, 2)
    E(push_list, [1])
    E(bl, "c_mtg")
    E(pop_list, [1])
    E(cmp_imm, 0, 0)
    E(b_cond, "pp_s", "eq")
    E(raw, CPSID)
    E(ldrh_imm, 2, 0, 4)
    E(ldrb_imm, 3, 4, 0)
    E(lsls_reg, 1, 3)
    E(ldrb_imm, 4, 4, 1)
    E(lsls_reg, 4, 3)
    E(bics_reg, 2, 4)
    E(orrs_reg, 2, 1)
    E(strh_imm, 2, 0, 4)
    E(bl, "c_mtsum")
    E(raw, CPSIE)
    a.label("pp_s")
    E(pop_list, [0, 1, 2, 3, 4], pc=True)

    # ---- c_mtpr (the Patterns view's pad release): the page swallows it
    a.label("c_mtpr")
    E(push_list, [0, 1, 2, 3, 4], lr=True)
    E(bl, L["c_pcst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "pr_p", "eq")
    E(raw, ldrb_w(1, 0, O_UI))
    E(lsls_imm, 1, 1, 31)
    E(b_cond, "pr_s", "mi")
    a.label("pr_p")
    E(raw, h(0xE8BD) + h(0x401F))
    E(b_w, prev["rel"])
    a.label("pr_s")
    E(pop_list, [0, 1, 2, 3, 4], pc=True)

    # ---- c_mtbtn (the head of the button chain: ctrl, id)
    a.label("c_mtbtn")
    E(push_list, [0, 1, 4, 5], lr=True)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("bt_p", "eq")
    E(bl, L["c_pcst"])
    E(cmp_imm, 0, 0)
    bc("bt_p", "eq")
    E(mov_reg, 5, 0)
    E(ldr_sp, 4, 4)
    E(raw, ldrb_w(0, 5, O_UI))
    E(lsls_imm, 1, 0, 31)
    E(b_cond, "bt_c", "pl")
    E(cmp_imm, 4, 8)                                                      # the page: a track button = taken or not
    E(b_cond, "bt_k", "hs")
    E(bl, "c_mtg")
    E(cmp_imm, 0, 0)
    E(b_cond, "bt_sw", "eq")
    E(ldrb_imm, 1, 0, 1)
    E(movs_imm, 2, 1)
    E(lsls_reg, 2, 4)
    E(eors_reg, 1, 2)
    E(strb_imm, 1, 0, 1)
    a.label("bt_sw")
    E(pop_list, [0, 1, 4, 5], pc=True)
    a.label("bt_k")
    for k in (ID_REC, ID_PLAY, ID_CLEAR, ID_SHIFT):
        E(cmp_imm, 4, k)
        E(b_cond, "bt_p", "eq")
    E(movs_imm, 1, UI_PAGE)                                               # any other button closes it (Duplicate too) and does its job
    E(bics_reg, 0, 1)
    E(raw, strb_w(0, 5, O_UI))
    E(b, "bt_p")
    a.label("bt_c")
    E(cmp_imm, 4, ID_DUP)
    E(b_cond, "bt_20", "ne")
    imm32(1, CTRL + 0xA0)
    E(ldr_imm, 1, 1, 0)
    E(lsrs_imm, 2, 1, ID_CLEAR + 1)                                       # the carry = Clear held
    E(b_cond, "bt_ns", "cc")
    E(movs_imm, 0, 0xFF)                                                  # Clear + Duplicate: every list ends
    E(bl, "c_mtoff")
    E(b, "bt_p")
    a.label("bt_ns")
    E(bl, L["c_cishift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "bt_p", "eq")
    imm32(1, CTRL)
    E(ldr_imm, 1, 1, 0x7C)
    E(movs_imm, 2, UI_PEND)
    imm32(0, PV)
    E(cmp_reg, 1, 0)
    E(b_cond, "bt_pe", "eq")
    E(movs_imm, 2, UI_PEND | UI_MIX)
    imm32(0, MIXV)
    E(cmp_reg, 1, 0)
    E(b_cond, "bt_p", "ne")
    a.label("bt_pe")                                                      # Shift + Duplicate: pending until it is let go or held
    E(raw, ldrb_w(0, 5, O_UI))
    E(movs_imm, 1, UI_PEND | UI_MIX)
    E(bics_reg, 0, 1)
    E(orrs_reg, 0, 2)
    E(raw, strb_w(0, 5, O_UI))
    imm32(1, HAL_TICK)
    E(ldr_imm, 1, 1, 0)
    E(str_imm, 1, 5, O_T0)
    E(b, "bt_p")
    a.label("bt_20")                                                      # Shift + 20 in the Patterns view: the rules take every track
    E(cmp_imm, 4, ID_UP)
    E(b_cond, "bt_p", "ne")
    E(bl, L["c_cishift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "bt_p", "eq")
    imm32(1, CTRL)
    E(ldr_imm, 1, 1, 0x7C)
    imm32(0, PV)
    E(cmp_reg, 1, 0)
    E(b_cond, "bt_p", "ne")
    E(movs_imm, 0, 0xFF)
    E(bl, "c_mtoff")
    a.label("bt_p")
    E(raw, h(0xE8BD) + h(0x4033))                                         # pop.w {r0, r1, r4, r5, lr}
    E(b_w, prev["btn"])

    # ---- c_mtled (the LED task, ahead of the others: ctrl, frame): the gesture, a scene picked while stopped, the page, the overlay
    a.label("c_mtled")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("le_x", "eq")
    E(bl, L["c_pcst"])
    E(cmp_imm, 0, 0)
    bc("le_x", "eq")
    E(mov_reg, 6, 0)
    E(raw, ldrb_w(0, 6, O_UI))
    E(lsls_imm, 1, 0, 30)
    E(b_cond, "le_np", "pl")                                              # nothing pending
    imm32(1, CTRL + 0xA0)
    E(ldr_imm, 1, 1, 0)
    E(lsrs_imm, 1, 1, ID_DUP + 1)
    E(b_cond, "le_h", "cs")
    E(movs_imm, 1, UI_PEND | UI_MIX)                                      # let go: the mutate
    E(bics_reg, 0, 1)
    E(raw, strb_w(0, 6, O_UI))
    E(bl, "c_mtdo")
    E(b, "le_np")
    a.label("le_h")
    E(lsls_imm, 1, 0, 29)
    E(b_cond, "le_np", "mi")                                              # (the Mixer: no page)
    imm32(1, HAL_TICK)
    E(ldr_imm, 1, 1, 0)
    E(ldr_imm, 2, 6, O_T0)
    E(subs_reg, 1, 1, 2)
    E(movw, 2, HOLD_MS)
    E(cmp_reg, 1, 2)
    E(b_cond, "le_np", "lo")
    E(movs_imm, 1, UI_PEND)                                               # held: the page
    E(bics_reg, 0, 1)
    E(movs_imm, 1, UI_PAGE)
    E(orrs_reg, 0, 1)
    E(raw, strb_w(0, 6, O_UI))
    a.label("le_np")
    imm32(0, ENG + 0x2C)                                                  # a scene picked while stopped: its mutate
    E(ldr_imm, 0, 0, 0)
    E(movs_imm, 1, 0)
    E(bl, PARAM_GET)
    E(ldrb_imm, 4, 0, 0)
    E(adds_imm8, 4, 1)
    E(raw, ldrb_w(7, 6, O_LASTSC))
    E(cmp_reg, 7, 4)
    E(b_cond, "le_v", "eq")
    E(raw, strb_w(4, 6, O_LASTSC))
    E(cmp_imm, 7, 0)
    E(b_cond, "le_v", "eq")
    imm32(0, TRANSPORT)
    E(movs_imm, 1, 0)
    E(bl, PARAM_GET)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "le_v", "ne")
    E(subs_imm8, 4, 1)
    E(mov_reg, 0, 4)
    E(bl, "c_mtload")
    a.label("le_v")
    imm32(0, CTRL)
    E(ldr_imm, 0, 0, 0x7C)
    imm32(1, PV)
    E(cmp_reg, 0, 1)
    E(b_cond, "le_pv", "eq")
    E(raw, ldrb_w(0, 6, O_UI))                                            # away from the Patterns view: the page closed
    E(movs_imm, 1, UI_PAGE)
    E(bics_reg, 0, 1)
    E(raw, strb_w(0, 6, O_UI))
    E(b, "le_x")
    a.label("le_pv")
    E(bl, "c_mtg")
    E(cmp_imm, 0, 0)
    bc("le_x", "eq")
    E(mov_reg, 4, 0)                                                      # r4 = the block
    E(raw, ldrb_w(0, 6, O_UI))
    E(lsls_imm, 0, 0, 31)
    bc("le_ov", "pl")
    # the page: r6 = the pad, r7 = the settings
    E(ldrh_imm, 7, 4, 4)
    E(movs_imm, 6, 0)
    a.label("lp_l")
    E(movs_imm, 2, 0)                                                     # r2 = the colour
    E(lsls_imm, 0, 6, 29)
    E(lsrs_imm, 0, 0, 29)
    E(cmp_imm, 0, len(CO))
    E(b_cond, "lp_w", "hs")
    imm32(1, t_cols)
    E(lsls_imm, 0, 0, 2)
    E(adds_reg, 1, 1, 0)                                                  # r1 = the column
    E(ldrb_imm, 3, 1, 3)
    E(lsls_imm, 0, 3, 28)
    E(lsrs_imm, 0, 0, 28)
    E(lsrs_imm, 2, 6, 3)                                                  # the row
    E(cmp_reg, 2, 0)
    E(movs_imm, 2, 0)
    E(b_cond, "lp_w", "hs")
    E(lsrs_imm, 3, 3, 4)
    E(lsrs_imm, 0, 6, 3)
    E(adds_reg, 3, 3, 0)                                                  # the pad's value
    E(ldrb_imm, 0, 1, 2)
    E(eors_reg, 3, 0)
    E(ldrb_imm, 0, 1, 0)
    E(mov_reg, 2, 7)
    E(lsrs_reg, 2, 0)
    E(ldrb_imm, 0, 1, 1)
    E(raw, h(0x4002))                                                     # ands r2, r0
    E(movs_imm, 0, COL)
    E(cmp_reg, 2, 3)
    E(b_cond, "lp_c", "eq")
    E(movs_imm, 0, DIM)
    a.label("lp_c")
    E(mov_reg, 2, 0)
    a.label("lp_w")
    E(lsls_imm, 0, 6, 1)
    E(strh_reg, 2, 5, 0)
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, 32)
    E(b_cond, "lp_l", "lo")
    E(ldrb_imm, 7, 4, 1)                                                  # the track buttons: taken bright
    E(movs_imm, 6, 0)
    a.label("lp_t")
    E(movs_imm, 2, COL)
    E(mov_reg, 0, 7)
    E(lsrs_reg, 0, 6)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "lp_tb", "pl")
    E(movs_imm, 2, DIM)
    a.label("lp_tb")
    E(lsls_imm, 0, 6, 1)
    E(adds_imm8, 0, 2 * LED_TRK0)
    E(strh_reg, 2, 5, 0)
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, 8)
    E(b_cond, "lp_t", "lo")
    E(b, "le_x")
    # the overlay: [sp + 0 .. 7] the masks, [sp + 8 .. 15] a list
    a.label("le_ov")
    E(ldrb_imm, 0, 4, 6)
    E(cmp_imm, 0, 0)
    bc("le_x", "eq")
    E(raw, h(0xB084))                                                     # sub sp, #16
    E(movs_imm, 6, 0)
    a.label("ov_t")
    E(mov_reg, 0, 13)
    E(movs_imm, 1, 0)
    E(strb_reg, 1, 0, 6)
    E(ldrb_imm, 0, 4, 6)
    E(lsrs_reg, 0, 6)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "ov_n", "pl")
    imm32(0, ENG + 0x9C)
    E(ldr_imm, 0, 0, 0)
    E(mov_reg, 1, 6)
    E(bl, PARAM_GET)
    E(ldrb_imm, 1, 0, 0)
    E(ldrb_imm, 0, 0, 1)
    E(lsls_imm, 0, 0, 8)
    E(orrs_reg, 1, 0)
    E(mov_reg, 0, 4)
    E(push_list, [1])
    E(bl, "c_mtss")
    E(mov_reg, 2, 0)
    E(pop_list, [1])
    E(mov_reg, 0, 6)
    E(raw, add_sp_imm(3, 8))
    E(bl, "c_mtgen")
    E(mov_reg, 1, 0)                                                      # the list's patterns -> the mask
    E(movs_imm, 7, 0)
    a.label("ov_m")
    E(subs_imm8, 1, 1)
    E(b_cond, "ov_s", "mi")
    E(raw, add_sp_imm(2, 8))
    E(ldrb_reg, 2, 2, 1)
    E(movs_imm, 3, 1)
    E(lsls_reg, 3, 2)
    E(orrs_reg, 7, 3)
    E(b, "ov_m")
    a.label("ov_s")
    E(mov_reg, 0, 13)
    E(strb_reg, 7, 0, 6)
    a.label("ov_n")
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, 8)
    E(b_cond, "ov_t", "lo")
    E(movs_imm, 6, 0)                                                     # the pads
    a.label("ov_p")
    E(mov_reg, 0, 6)
    E(bl, TRACKFN)
    E(cmp_imm, 0, 8)
    E(b_cond, "ov_q", "hs")
    E(mov_reg, 7, 0)                                                      # r7 = the track
    E(ldrb_imm, 1, 4, 6)
    E(lsrs_reg, 1, 7)
    E(lsls_imm, 1, 1, 31)
    E(b_cond, "ov_q", "pl")
    imm32(0, PV)
    E(mov_reg, 1, 6)
    E(bl, PATFN)
    E(cmp_imm, 0, 8)
    E(b_cond, "ov_q", "hs")
    E(mov_reg, 1, 13)
    E(ldrb_reg, 1, 1, 7)
    E(lsrs_reg, 1, 0)
    E(lsls_imm, 1, 1, 31)
    E(b_cond, "ov_q", "mi")                                               # in the list
    E(push_list, [0])
    imm32(0, ENG + 0x30)
    E(lsls_imm, 1, 7, 2)
    E(adds_reg, 0, 0, 1)
    E(ldr_imm, 0, 0, 0)
    E(movs_imm, 1, 0)
    E(bl, PARAM_GET)
    E(ldrb_imm, 1, 0, 0)
    E(pop_list, [0])
    E(cmp_reg, 0, 1)
    E(b_cond, "ov_q", "eq")                                               # the one playing: the stock's
    E(lsls_imm, 0, 6, 1)
    E(movs_imm, 1, 0)
    E(strh_reg, 1, 5, 0)
    a.label("ov_q")
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, 32)
    E(b_cond, "ov_p", "lo")
    E(raw, h(0xB004))                                                     # add sp, #16
    a.label("le_x")
    E(pop_list, [4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """After patchain (OPT mutate: its stub), and after every other head of the Patterns view's pads, the button chain and the LED calls."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]                 # noqa: E731
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    assert rhbuild.OPT.get("mutate") and "c_pcmt" in report["patchain"]["labels"]
    L = dict(c_rrt=lab("rhrec", "c_rrt"), c_ciok=lab("countin", "c_ciok"), c_cishift=lab("countin", "c_cishift"),
             c_pcst=lab("patchain", "c_pcst"))
    prev = dict(pad=u(PV_VT) & ~1, rel=u(PV_VT + 4) & ~1, btn=rhbuild.bw_target(img, CI.BTN_ENTRY),
                ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]), ssave=rhbuild.bl_target(img, PC.SC_SAVE),
                scopy=rhbuild.bl_target(img, PC.SC_COPY))
    assert prev["ssave"] == lab("patchain", "c_pcssave") and prev["scopy"] == lab("patchain", "c_pcscopy")
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code_, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code_
    while len(img) % 4:
        img += bytes([0xFF])
    stub = lab("patchain", "c_pcmt")
    rhbuild.patch(img, stub, "mov r0, r1|bx lr", b_w(stub, labels["c_mtnext"]))
    if mtend():
        st = lab("patchain", "c_pcme")
        rhbuild.patch(img, st, "movs r0, #0|bx lr", b_w(st, labels["c_mtme"]))
    rhbuild.patch_word(img, PV_VT, prev["pad"] | 1, labels["c_mtpp"] | 1)
    rhbuild.patch_word(img, PV_VT + 4, prev["rel"] | 1, labels["c_mtpr"] | 1)
    rhbuild.patch(img, CI.BTN_ENTRY, f"b.w #{prev['btn']:#x}", b_w(CI.BTN_ENTRY, labels["c_mtbtn"]))
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_mtled"]))
    rhbuild.patch(img, PC.SC_SAVE, f"bl #{prev['ssave']:#x}", bl(PC.SC_SAVE, labels["c_mtssave"]))
    rhbuild.patch(img, PC.SC_COPY, f"bl #{prev['scopy']:#x}", bl(PC.SC_COPY, labels["c_mtscopy"]))
    report["mutate"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")},
                            base=hex(base_addr))
    return labels, code_
