"""Sample mode: two more pads that fit the sample to the pattern, by the stretch instead of the pitch (MIT; RH44, docs/PRUEBA_RH44.md).

The user (2026-10-26): «En sample mode, hay dos opciones de repitch para ajustar al patrón (tempo); añade debajo otras dos que ajusten, pero
usando timestretch».

The stock (read in the Rhythm's image, run on the RAM dump):
  * Sample mode's pads 1 / 2 (subview slot 0 0x08057DA8, one subview per track at 0x2004D36C + 0x64 t) send event 0 / 1 to the track's fit
    object (vtable 0x0806847C, one per track at 0x200469CC + 0xB4 t; [subview + 0x18] -> its node, [node] -> it), whose handler
    0x0803BE70 sets the track's pitch to 64 + round(60 log2(L / T)) (the pitch in fifths of a semitone), clamped to 0..127, through
    [fit + 0x14] (a proxy store; vtable[0](proxy, [fit + 0x18] = 16 t, value)); L = the sample's whole length (0x0804A4E4(n): core 0's
    sample table, X:$30001 + 4 n), T = 0x0803C14C(fit, c) = 4 / 8 / 16 / 32 / 64 / 128 sixteenths at the BPM, in samples at 48 kHz
    (c = 0..5); n = p0 of [fit + 0xC], present = bit n of [fit + 0x24];
  * the two options (p0 / p1 of the store [fit + 0x2C] = [subview + 0x1C]; 6 = none) come from 0x0803C034, run when the sample, the tempo
    or the clock's source changes: p0 = the target just longer than the sample (the pitch goes down), p1 = the one just shorter (up), each
    within a ratio 2.0116 and not within 0.58 % (already that long); p2 = the one last applied, 6 again at any change (0x0803C1D4);
  * their LEDs (slot 8, 0x08057E94): 0x08062AB0 + 2 code, code 0x228 none, 0x227 there, 0x226 applied.  Pads 9 / 10, below, do nothing.
Ours:
  * pads 9 / 10 (below 1 / 2): the same two targets, the shortest T >= L (slower: K7 below the middle) and the longest T < L (faster),
    each while the speed L / T is within K7's range (0.25x .. 4x); a press sets the track's K7 (Stock+'s stretch, tools/stockplus.py) to
    the value whose speed (its own table, searched) is nearest L / T, the pitch to the middle (64: the sample's own tone; the stretch
    plays the sample at speed x the pitch's rate) through the stock's proxy, and the stock's «applied» to none (0x0803C1D4);
  * K7 is kept in the project with bit 14 set (stockplus fitflag): with it the stretch is on even within a click of the middle (a loop
    1 % off the tempo); turning K7 clears it (the value is stored again without it);
  * pads 1 / 2: when the stock has that option, the track's stretch goes off (K7 to the middle) before the stock's own fit, so that its
    pitch alone sets the length;
  * their LEDs, written into the frame by the LED task while Sample mode is on the screen, in the stock's three codes of pads 1 / 2:
    applied = K7's effective value is the option's and the pitch is 64;
  * the options of each track are kept in our RAM (OFF2 "stfit": + 0 the tracks whose options are known, + 4 + 4 t the pad 9 / pad 10
    option: K7's value | 0x8000, 0 = none); the stock's 0x0803C034 (its entry: `push {r3-r7, lr}; mov r4, r0` -> c_sfinv) forgets them all,
    the LED task works out the shown track's again (one read of the sample's length), only while core 0 / 1 hold the mode 0 program
    (cthresh READY), as the press does.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b, b_cond, b_w, bl, cbz, cmp_imm, cmp_reg, h, ldr_imm, ldrb_imm, ldrb_w, ldrh_imm, lsls_imm,  # noqa: E402
                   lsls_reg, lsrs_imm, lsrs_reg, mov_reg, movs_imm, movt, movw, muls, orrs_reg, pop_list, push_list, raw, strb_imm, strh_imm,
                   strh_w_imm, subs_imm8, subs_reg)
import countin as CI  # noqa: E402
import cthresh as TH  # noqa: E402
import granpage as GP  # noqa: E402
import rhstate  # noqa: E402
import sckn as SK  # noqa: E402
import stockplus as SP  # noqa: E402

O = rhstate.OFF2["stfit"][0]
BLOCK = rhstate.ST2 + O
S_VALID, S_OPT = 0, 4                                     # + 4 + 4 t: pad 9's option, pad 10's (halfwords: K7's value | AVAIL, 0 = none)
AVAIL, FLAG = 0x8000, 0x4000
O_TH = rhstate.OFF["cthresh"][0] + 1
FIT_VT = 0x0806847C
GET = 0x0803FC58                                          # (store, parameter) -> its pointer
TARGET, SLEN, UNAPPLY = 0x0803C14C, 0x0804A4E4, 0x0803C1D4
RECOMP, RECOMP_HEAD, RECOMP_CONT = 0x0803C034, "push {r3, r4, r5, r6, r7, lr}|mov r4, r0", 0x0803C038
F_SAMPLE, F_PROXY, F_PID, F_PRESENT, F_TRACK = 0x0C, 0x14, 0x18, 0x24, 0x30
SUB0, SUB_STRIDE, SUB_NODE, SUB_OPTS = 0x2004D36C, 0x64, 0x18, 0x1C
FIT0, FIT_STRIDE = 0x200469CC, 0xB4
PAD9, PAD10 = 8, 9
NONE_OPT = 6
CODE_APPLIED, CODE_AVAIL, CODE_NONE = 0x226, 0x227, 0x228
PAL = GP.PAL
NC = 6                                                    # the stock's targets: 4 << c sixteenths, c = 0..5
PITCH_MID = 64
VMAX = 16383
K7, X7, DEAD = SP.K7, SP.X7, SP.DEAD
CONT, SELTRK, O_MODE, MODE_SMP = SK.CONT, SP.SELTRK, SK.O_MODE, GP.MODE_SMP
assert O % 4 == 0 and rhstate.OFF2["stfit"][1] >= S_OPT + 4 * 8


def udiv(rd, rn, rm): return h(0xFBB0 | rn) + h(0xF0F0 | rd << 8 | rm)
def mls(rd, rn, rm, ra): return h(0xFB00 | rn) + h(ra << 12 | rd << 8 | 0x10 | rm)          # rd = ra - rn x rm
def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


# ---- the model (the tests'): what the ARM works out
def word(L, T):
    """the speed L / T as the stretch's word (speed / 4, Q23), as c_sfdiv: three integer divisions"""
    q0, r = divmod(L << 8, T)
    q1, r = divmod(r << 8, T)
    q2 = (r << 5) // T
    return q0 << 13 | q1 << 5 | q2


def spint(v):
    tab = SP.speed_table()
    i, f = v >> 7, v & 127
    return tab[i] + ((tab[i + 1] - tab[i]) * f >> 7)


def vfind(w):
    """K7's value whose speed is nearest the word w, as c_sfv: the largest v with spint(v) <= w, or v + 1 if nearer"""
    lo, hi = 0, VMAX
    while lo < hi:
        mid = (lo + hi + 1) >> 1
        if spint(mid) <= w:
            lo = mid
        else:
            hi = mid - 1
    if lo < VMAX and spint(lo + 1) - w < w - spint(lo):
        lo += 1
    return lo


def options(L, targets):
    """(pad 9's option, pad 10's) for a sample of L samples and the stock's six targets: K7's value | AVAIL, or 0"""
    if not L or L >= 1 << 24:
        return 0, 0
    o9 = o10 = 0
    decided = False
    for T in targets:
        if not T:
            continue
        if T >= L:
            if not decided:
                decided = True
                if T <= 4 * L:
                    o9 = vfind(word(L, T)) | AVAIL
        elif L <= 4 * T:
            o10 = vfind(word(L, T)) | AVAIL
    return o9, o10


def k7_stored(v):
    """what a press leaves in the project for the option's value v (K7 stored XOR 8192; bit 14 = on even near the middle)"""
    return (v ^ X7) if v == X7 else (v ^ X7) | FLAG


def arm_code(base, L, prev, t_spd):
    a = Asm(base)
    E = a.emit
    zc = [0]

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    def bc(target, cond):
        zc[0] += 1
        n = f"_f{zc[0]}"
        E(b_cond, n, SP.INV[cond])
        E(b, target)
        a.label(n)

    # ---- c_sfst() -> r0 = our block (OFF2), 0 without our RAM; clobbers r1-r3
    a.label("c_sfst")
    E(push_list, [4], lr=True)
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "st_x", "eq")
    E(movw, 1, O)
    E(adds_reg, 0, 0, 1)
    a.label("st_x")
    E(pop_list, [4], pc=True)

    # ---- c_sfok() -> r0 = our block when our RAM is set up and core 0 / 1 hold the mode 0 program (cthresh READY), else 0; clobbers r1-r3
    a.label("c_sfok")
    E(push_list, [4], lr=True)
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ok_0", "eq")
    E(ldrb_w, 1, 0, O_TH)
    E(cmp_imm, 1, TH.READY)
    E(b_cond, "ok_0", "ne")
    E(bl, "c_sfst")
    E(pop_list, [4], pc=True)
    a.label("ok_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)

    # ---- c_sffit(r0 = a Sample mode subview) -> r0 = its track's fit object, 0 if not one; clobbers r1, r2
    a.label("c_sffit")
    E(ldr_imm, 0, 0, SUB_NODE)
    E(ldr_imm, 0, 0, 0)
    imm32(1, FIT_VT)
    E(ldr_imm, 2, 0, 0)
    E(cmp_reg, 2, 1)
    E(b_cond, "ff_x", "eq")
    E(movs_imm, 0, 0)
    a.label("ff_x")
    E(raw, h(0x4770))

    # ---- c_sfdiv(r0 = L, r1 = T) -> r0 = L x 2^21 / T (L <= 4 T, L < 2^24); clobbers r2, r3
    a.label("c_sfdiv")
    E(lsls_imm, 2, 0, 8)
    E(raw, udiv(3, 2, 1))
    E(raw, mls(2, 3, 1, 2))
    E(lsls_imm, 0, 3, 13)
    E(lsls_imm, 2, 2, 8)
    E(raw, udiv(3, 2, 1))
    E(raw, mls(2, 3, 1, 2))
    E(lsls_imm, 3, 3, 5)
    E(orrs_reg, 0, 3)
    E(lsls_imm, 2, 2, 5)
    E(raw, udiv(3, 2, 1))
    E(orrs_reg, 0, 3)
    E(raw, h(0x4770))

    # ---- c_sfv(r0 = the word) -> r0 = K7's value with the nearest speed (stockplus's table, as its c_spint reads it); clobbers r1-r3
    a.label("c_sfv")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)                                                      # r4 = the word
    E(movs_imm, 5, 0)                                                     # r5 = lo
    E(movw, 6, VMAX)                                                      # r6 = hi
    a.label("sv_l")
    E(cmp_reg, 5, 6)
    E(b_cond, "sv_d", "hs")
    E(adds_reg, 7, 5, 6)
    E(adds_imm8, 7, 1)
    E(lsrs_imm, 7, 7, 1)                                                  # r7 = mid
    imm32(0, t_spd)
    E(mov_reg, 1, 7)
    E(bl, L["c_spint"])
    E(cmp_reg, 0, 4)
    E(b_cond, "sv_hi", "hi")
    E(mov_reg, 5, 7)
    E(b, "sv_l")
    a.label("sv_hi")
    E(subs_imm8, 7, 1)
    E(mov_reg, 6, 7)
    E(b, "sv_l")
    a.label("sv_d")
    E(movw, 0, VMAX)
    E(cmp_reg, 5, 0)
    E(b_cond, "sv_x", "hs")
    imm32(0, t_spd)
    E(mov_reg, 1, 5)
    E(bl, L["c_spint"])
    E(subs_reg, 6, 4, 0)                                                  # r6 = w - spint(v)
    imm32(0, t_spd)
    E(mov_reg, 1, 5)
    E(adds_imm8, 1, 1)
    E(bl, L["c_spint"])
    E(subs_reg, 0, 0, 4)                                                  # spint(v + 1) - w
    E(cmp_reg, 0, 6)
    E(b_cond, "sv_x", "hs")
    E(adds_imm8, 5, 1)
    a.label("sv_x")
    E(mov_reg, 0, 5)
    E(pop_list, [3, 4, 5, 6, 7], pc=True)

    # ---- c_sfopt(r0 = fit) -> r0 = pad 9's option, r1 = pad 10's (K7's value | AVAIL, or 0); clobbers r2, r3
    a.label("c_sfopt")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)                                                      # r4 = the fit object
    E(ldr_imm, 0, 4, F_SAMPLE)
    E(movs_imm, 1, 0)
    E(bl, GET)
    E(ldrb_imm, 6, 0, 0)                                                  # r6 = n
    E(ldr_imm, 0, 4, F_PRESENT)
    E(lsrs_imm, 1, 6, 5)
    E(bl, GET)
    E(ldr_imm, 0, 0, 0)
    E(movs_imm, 1, 31)
    E(raw, h(0x4000 | 6 << 3 | 1))                                        # ands r1, r6
    E(lsrs_reg, 0, 1)
    E(lsls_imm, 0, 0, 31)
    bc("so_none", "eq")                                                   # no sample there
    E(mov_reg, 0, 6)
    E(bl, SLEN)
    E(mov_reg, 5, 0)                                                      # r5 = L
    E(cmp_imm, 5, 0)
    bc("so_none", "eq")
    E(lsrs_imm, 0, 5, 24)
    bc("so_none", "ne")
    E(movs_imm, 7, 0)                                                     # r7 = pad 10's option << 16 | pad 9's (bit 14: pad 9's decided)
    E(movs_imm, 6, 0)                                                     # r6 = c
    a.label("so_l")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 6)
    E(bl, TARGET)                                                         # r0 = T
    E(cmp_imm, 0, 0)
    E(b_cond, "so_n", "eq")
    E(cmp_reg, 0, 5)
    E(b_cond, "so_sh", "lo")
    E(lsls_imm, 1, 7, 16)                                                 # T >= L: pad 9 takes the first
    E(lsrs_imm, 1, 1, 30)
    E(b_cond, "so_n", "ne")
    E(movw, 1, FLAG)
    E(orrs_reg, 7, 1)                                                     # decided
    E(lsls_imm, 1, 5, 2)
    E(cmp_reg, 0, 1)
    E(b_cond, "so_n", "hi")                                               # slower than 0.25x: none
    E(mov_reg, 1, 0)
    E(mov_reg, 0, 5)
    E(bl, "c_sfdiv")
    E(bl, "c_sfv")
    E(movw, 1, AVAIL)
    E(orrs_reg, 0, 1)
    E(lsrs_imm, 7, 7, 16)
    E(lsls_imm, 7, 7, 16)
    E(orrs_reg, 7, 0)
    E(b, "so_n")
    a.label("so_sh")                                                      # T < L: pad 10 takes the last within 4x
    E(lsls_imm, 1, 0, 2)
    E(cmp_reg, 5, 1)
    E(b_cond, "so_n", "hi")
    E(mov_reg, 1, 0)
    E(mov_reg, 0, 5)
    E(bl, "c_sfdiv")
    E(bl, "c_sfv")
    E(movw, 1, AVAIL)
    E(orrs_reg, 0, 1)
    E(lsls_imm, 0, 0, 16)
    E(lsls_imm, 7, 7, 16)
    E(lsrs_imm, 7, 7, 16)
    E(orrs_reg, 7, 0)
    a.label("so_n")
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, NC)
    E(b_cond, "so_l", "lo")
    E(lsls_imm, 0, 7, 16)
    E(lsrs_imm, 0, 0, 16)
    E(lsls_imm, 1, 0, 16)
    E(b_cond, "so_9", "mi")
    E(movs_imm, 0, 0)                                                     # (only decided: none)
    a.label("so_9")
    E(lsrs_imm, 1, 7, 16)
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    a.label("so_none")
    E(movs_imm, 0, 0)
    E(movs_imm, 1, 0)
    E(pop_list, [3, 4, 5, 6, 7], pc=True)

    # ---- c_sfeff(r0 = track) -> r0 = K7's effective value (8192 when the stretch is off: within DEAD of the middle without bit 14)
    a.label("c_sfeff")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(movs_imm, 1, K7)
    E(bl, L["c_spval"])
    E(mov_reg, 5, 0)
    E(mov_reg, 0, 4)
    E(movs_imm, 1, K7)
    E(bl, L["c_spval_a"])
    E(lsls_imm, 0, 0, 17)
    E(b_cond, "ef_x", "mi")
    E(movw, 1, X7)
    E(subs_reg, 0, 5, 1)
    E(b_cond, "ef_p", "ge")
    E(raw, h(0x4240))                                                     # rsbs r0, r0, #0
    a.label("ef_p")
    E(cmp_imm, 0, DEAD)
    E(b_cond, "ef_x", "ge")
    E(mov_reg, 5, 1)
    a.label("ef_x")
    E(mov_reg, 0, 5)
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_sfoff(r0 = track): the stretch off (K7 to the middle) unless it already is; clobbers r0-r3
    a.label("c_sfoff")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(movs_imm, 1, K7)
    E(bl, L["c_spval_a"])
    E(cmp_imm, 0, 0)                                                      # stored 0 = the middle, no flag
    E(b_cond, "of_x", "eq")
    E(mov_reg, 0, 4)
    E(movs_imm, 1, K7)
    E(movw, 2, X7)
    E(bl, L["c_spput"])
    E(mov_reg, 0, 4)
    E(bl, L["c_spdirty"])
    a.label("of_x")
    E(pop_list, [4], pc=True)

    # ---- c_sfapply(r0 = fit, r1 = the option): K7, the pitch to the middle, the stock's «applied» to none; clobbers r0-r3
    a.label("c_sfapply")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(lsls_imm, 5, 1, 18)
    E(lsrs_imm, 5, 5, 18)                                                 # r5 = v
    E(ldrh_imm, 6, 4, F_PID)
    E(lsrs_imm, 6, 6, 4)                                                  # r6 = the track
    E(movw, 2, X7)
    E(cmp_reg, 5, 2)
    E(b_cond, "ap_m", "eq")
    E(movw, 2, FLAG)
    E(orrs_reg, 2, 5)
    a.label("ap_m")
    E(mov_reg, 0, 6)
    E(movs_imm, 1, K7)
    E(bl, L["c_spput"])
    E(mov_reg, 0, 6)
    E(bl, L["c_spdirty"])
    E(ldr_imm, 0, 4, F_PROXY)                                             # the stock's own call: proxy vtable[0](proxy, 16 t, 64)
    E(ldrh_imm, 1, 4, F_PID)
    E(movs_imm, 2, PITCH_MID)
    E(ldr_imm, 3, 0, 0)
    E(ldr_imm, 3, 3, 0)
    E(raw, h(0x4798))                                                     # blx r3
    E(mov_reg, 0, 4)
    E(bl, UNAPPLY)
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_sfpad (Sample mode's slot 0: r0 = subview, r1 = pad, r2 = velocity)
    a.label("c_sfpad")
    E(cmp_imm, 1, 2)
    E(b_cond, "pd_o", "hs")
    E(push_list, [0, 1, 2, 3, 4], lr=True)                                # pads 1 / 2: the stock's option there -> our stretch off first
    E(ldr_imm, 0, 0, SUB_OPTS)
    E(bl, GET)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, NONE_OPT)
    E(b_cond, "pd_s", "eq")
    E(raw, h(0x9800))                                                     # ldr r0, [sp, #0]: the subview
    E(bl, "c_sffit")
    E(cbz, "pd_s", 0)
    E(ldrh_imm, 0, 0, F_PID)
    E(lsrs_imm, 0, 0, 4)
    E(cmp_imm, 0, 8)
    E(b_cond, "pd_s", "hs")
    E(bl, "c_sfoff")
    a.label("pd_s")
    E(raw, popw([0, 1, 2, 3, 4], lr=True))
    E(b_w, prev["pad"])
    a.label("pd_o")
    E(cmp_imm, 1, PAD9)
    E(b_cond, "pd_9", "eq")
    E(cmp_imm, 1, PAD10)
    E(b_cond, "pd_9", "eq")
    E(b_w, prev["pad"])
    a.label("pd_9")                                                       # pads 9 / 10: ours
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 5, 1)
    E(bl, "c_sffit")
    E(cbz, "pd_x", 0)
    E(mov_reg, 4, 0)                                                      # r4 = the fit object
    E(ldrh_imm, 6, 4, F_PID)
    E(lsrs_imm, 6, 6, 4)                                                  # r6 = the track
    E(cmp_imm, 6, 8)
    E(b_cond, "pd_x", "hs")
    E(bl, "c_sfok")
    E(cbz, "pd_x", 0)
    E(mov_reg, 0, 4)
    E(bl, "c_sfopt")
    E(push_list, [0, 1])
    E(bl, "c_sfst")                                                       # (the options of the track kept)
    E(pop_list, [2, 3])
    E(lsls_imm, 1, 6, 2)
    E(adds_reg, 1, 0, 1)
    E(strh_imm, 2, 1, S_OPT)
    E(strh_imm, 3, 1, S_OPT + 2)
    E(ldrb_imm, 1, 0, S_VALID)
    E(push_list, [2, 3])
    E(movs_imm, 2, 1)
    E(lsls_reg, 2, 6)
    E(orrs_reg, 1, 2)
    E(strb_imm, 1, 0, S_VALID)
    E(pop_list, [0, 1])
    E(cmp_imm, 5, PAD9)
    E(b_cond, "pd_a", "ne")
    E(mov_reg, 1, 0)
    a.label("pd_a")
    E(lsls_imm, 2, 1, 16)
    E(b_cond, "pd_x", "pl")                                               # none: nothing (as the stock's pads)
    E(mov_reg, 0, 4)
    E(bl, "c_sfapply")
    a.label("pd_x")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_sfinv (the stock's 0x0803C034, its first two instructions): our options forgotten, then the stock's
    #      (no call into rhstate: the stock runs it at power-up too, while it still allocates; our block cleared or not set up yet = nothing known)
    a.label("c_sfinv")
    E(push_list, [0, 1, 2, 3, 4], lr=True)
    imm32(2, rhstate.ST2)
    E(ldr_imm, 1, 2, 0)
    imm32(3, rhstate.MAGIC2)
    E(cmp_reg, 1, 3)
    E(b_cond, "iv_x", "ne")
    imm32(2, BLOCK)
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 2, S_VALID)
    a.label("iv_x")
    E(raw, popw([0, 1, 2, 3, 4], lr=True))
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(b_w, RECOMP_CONT)

    # ---- c_sfled (the LED task's calls: ctrl, frame): the chain, then pads 9 / 10 while Sample mode is on the screen
    a.label("c_sfled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)                                                      # r5 = the frame
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("le_x", "eq")
    E(bl, "c_sfok")
    E(cmp_imm, 0, 0)
    bc("le_x", "eq")
    E(mov_reg, 6, 0)                                                      # r6 = our block
    imm32(0, CI.CTRL)
    E(ldr_imm, 1, 0, 0x7C)
    imm32(0, CONT)
    E(cmp_reg, 0, 1)
    bc("le_x", "ne")
    E(ldrb_w, 1, 0, O_MODE)
    E(cmp_imm, 1, MODE_SMP)
    bc("le_x", "ne")
    E(bl, SELTRK)
    E(cmp_imm, 0, 8)
    bc("le_x", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the track
    E(movs_imm, 1, SUB_STRIDE)
    E(muls, 1, 0)
    imm32(0, SUB0)
    E(adds_reg, 0, 0, 1)
    E(bl, "c_sffit")
    E(cmp_imm, 0, 0)
    bc("le_x", "eq")
    E(mov_reg, 7, 0)                                                      # r7 = its fit object
    E(ldrb_imm, 0, 6, S_VALID)
    E(lsrs_reg, 0, 4)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "le_k", "mi")
    E(mov_reg, 0, 7)                                                      # not known: worked out now
    E(bl, "c_sfopt")
    E(lsls_imm, 2, 4, 2)
    E(adds_reg, 2, 2, 6)
    E(strh_imm, 0, 2, S_OPT)
    E(strh_imm, 1, 2, S_OPT + 2)
    E(ldrb_imm, 0, 6, S_VALID)
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(orrs_reg, 0, 1)
    E(strb_imm, 0, 6, S_VALID)
    a.label("le_k")
    E(ldr_imm, 0, 7, F_TRACK)                                             # the pitch (the track's parameter 0)
    E(movs_imm, 1, 0)
    E(bl, GET)
    E(ldrb_imm, 7, 0, 0)
    E(mov_reg, 0, 4)
    E(bl, "c_sfeff")
    E(cmp_imm, 7, PITCH_MID)
    E(b_cond, "le_p", "eq")
    E(movw, 0, 0xFFFF)                                                    # pitch moved: nothing applied
    a.label("le_p")
    E(mov_reg, 7, 0)                                                      # r7 = the effective K7 (0xFFFF: none)
    for k, pad in enumerate((PAD9, PAD10)):
        E(lsls_imm, 2, 4, 2)
        E(adds_reg, 2, 2, 6)
        E(ldrh_imm, 0, 2, S_OPT + 2 * k)
        imm32(3, PAL + 2 * CODE_NONE)
        E(lsls_imm, 1, 0, 16)
        E(b_cond, f"le_d{k}", "pl")
        imm32(3, PAL + 2 * CODE_AVAIL)
        E(lsls_imm, 0, 0, 18)
        E(lsrs_imm, 0, 0, 18)
        E(cmp_reg, 0, 7)
        E(b_cond, f"le_d{k}", "ne")
        imm32(3, PAL + 2 * CODE_APPLIED)
        a.label(f"le_d{k}")
        E(ldrh_imm, 0, 3, 0)
        E(strh_imm, 0, 5, 2 * pad)
    a.label("le_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """Ahead of granpage (Sample mode's slot 0), ahead of the LED calls' chain, and at the entry of the stock's 0x0803C034.  Needs stockplus v2 with fitflag
    (K7 on with bit 14) and rhstate ram2."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]                 # noqa: E731
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    for need in ("stockplus", "granpage", "cthresh"):
        assert need in report, f"stfit needs {need}"
    assert report["stockplus"].get("v2") and report["stockplus"].get("fitflag"), "stfit needs stockplus v2 with fitflag"
    assert "c_rram" in report["rhstate"]["labels"], "stfit needs rhstate ram2 (RH41)"
    t_spd = int(report["stockplus"]["t_spd"], 16)
    assert [u(t_spd + 4 * i) for i in range(129)] == SP.speed_table(), "stockplus's speed table not where its report says"
    L = dict(c_rst=lab("rhstate", "c_rst"), c_rram=lab("rhstate", "c_rram"), c_ciok=lab("countin", "c_ciok"),
             **{k: lab("stockplus", k) for k in ("c_spval", "c_spval_a", "c_spput", "c_spdirty", "c_spint")})
    prev = dict(pad=u(GP.SMP_VT) & ~1, ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert prev["pad"] == lab("granpage", "c_gpxpad")                          # (the LED calls: the last module's head, stereorec's in RH44)
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code, labels = arm_code(base_addr, L, prev, t_spd)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch_word(img, GP.SMP_VT, prev["pad"] | 1, labels["c_sfpad"] | 1)
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_sfled"]))
    rhbuild.patch(img, RECOMP, RECOMP_HEAD, b_w(RECOMP, labels["c_sfinv"]))
    report["stfit"] = dict(prev={k: hex(v) for k, v in prev.items()}, block=hex(BLOCK), t_spd=hex(t_spd),
                           labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
