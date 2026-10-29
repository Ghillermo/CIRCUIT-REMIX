"""Velocity view: Shift + a step pad = that step lets go of the automation (MIT; RH46, CIRCUIT-HACKS' autorel of Beta 3.12 for the Rhythm's
tracks; the Tracks' request: «En velocity view, shift+pad hace que deje de aplicarse automatización (posición de knob + init en lugar de
posición + valor previo de automatización)»).

The stock of the Rhythm (read in its image, run on the RAM dump):
  * the automation plays from the players (0x200470D4 + 0x190 t, vtable 0x08068D24): 0x08055324(player, pattern, step, micro step), called once
    a micro step (0x080552AC, its only caller); for each lane k < [player + 0x3C] (12: the knobs K1-K8, then the reverb send, the delay send,
    the level, the pan; the lane's id = halfword k of [player + 0x40]: 0x10 t + k, 0x80 / 0x88 / 0x91 / 0x99 + t) with its bit in p0 of
    [player + 0x30] and not in p0 of [player + 0x34] (the lanes a knob turned by hand suspends), the step's value (or the held one,
    [player + 0x48] + 2 k) is applied when it is not the last applied ([player + 0x4C] + 2 k; 0xFFFF none) through [player + 0x2C]'s
    slot 0 (obj, id, value): the track's parameter (group 0x10 + t, index 6..13 / 0x12 / 0x13 / 0x10 / 0x11; read with 0x08046410(group,
    index)) takes the value and keeps it: nothing remembers the knob's position;
  * the Velocity view = the track views' container in mode 2; Shift + a step pad there = the step pad alone (checked in emulation).
Ours:
  * the mark: bit 0 of byte 7 of the step (zero in every step of the stock; the stock's edits never write it; it moves with the step);
    Velocity view, Shift + a step pad (+ 16 on the second page) toggles it on the pattern on the screen; that press and its release do not
    reach the stock; with Shift held there the step pads are yellow, the marked ones red;
  * playing (the head of 0x08055324, c_arplay): a track whose playing pattern has no marked step plays as the stock's (checked once a step);
    otherwise, at micro step 0 of each step, the parameter of every lane not yet taken by its automation is kept (its base); after the
    stock's run a lane whose last applied value is set is taken (its base frozen), one suspended by a knob or without automation is given
    back; at a marked step no lane plays, and each taken lane gets its base back through the stock's own slot 0, its held and last applied
    values cleared (the next value applies again).
RAM: rhstate OFF2 "autorel": + 0 the swallowed step pads (bit), + 4 + 16 t: the taken lanes (u16), the pattern has marks, this step is
marked, the 12 bases.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b, b_cond, b_w, bl, cmp_imm, cmp_reg, h, ldr_imm, ldrb_imm, ldrb_w, ldrh_imm, lsls_imm,  # noqa: E402
                   lsls_reg, lsrs_imm, lsrs_reg, mov_reg, movs_imm, movt, movw, muls, orrs_reg, pop_list, push_list, raw, str_imm, strb_imm,
                   strh_imm, subs_reg, tst_reg)
import countin as CI  # noqa: E402
import rhrec  # noqa: E402
import rhstate  # noqa: E402
import sckn as SK  # noqa: E402
import stepgate as SG  # noqa: E402

PLAY, PLAY_HEAD, PLAY_CONT = 0x08055324, "push.w {r3, r4, r5, r6, r7, r8, sb, sl, fp, lr}", 0x08055328
DP0, DP_SZ, DP_VT = 0x200470D4, 0x190, 0x08068D24
P_PARAM, P_MASK, P_TOUCH, P_COUNT, P_IDS, P_HELD, P_LAST = 0x2C, 0x30, 0x34, 0x3C, 0x40, 0x48, 0x4C
GROUP_GET = 0x08046410
IDX = (6, 7, 8, 9, 10, 11, 12, 13, 0x12, 0x13, 0x10, 0x11)                # each lane's index in the track's group
NLANE = len(IDX)
PAT0, TRK_SZ, PAT_SZ = 0x2E4, 0x5140, 0xA28
MARK_OFF, MARK = 7, 0x01
CONT, O_MODE, MODE_VEL = SK.CONT, SK.O_MODE, 2
SV0, SV_SZ, SV_VT, SV_ST1, SV_PAGE = SG.SV0, SG.SV_SZ, SG.SV_VT, SG.SV_ST1, SG.SV_PAGE
LANES_OFF = 0x128
COL_AV, COL_MARK = 0x2F, 0x55                                            # yellow, red (Tracks 0x2D / 0x53)
# ui (RH52; docs/INTERFAZ.md): the marks in one colour, bright = marked, dim = not (was yellow / red)
UI_AV = 0x54                                              # dim red
# keep (RH53; the user, 2026-10-28: «Make pads with automation release red, regular pads keep their previous state from velocity view»):
# with Shift only the marked steps are drawn (red); the others keep the Velocity view's own colours
GET = CI.PARAM_GET
O = rhstate.OFF2["autorel"][0]
R_SW, R_TRK, T_SZ = 0, 4, 16
T_FLAGS, T_HAS, T_CUR, T_BASE = 0, 2, 3, 4
assert rhstate.OFF2["autorel"][1] >= R_TRK + 8 * T_SZ and T_BASE + NLANE <= T_SZ


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))
def pushw(regs, lr=False): return h(0xE92D) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))
def udiv(rd, rn, rm): return h(0xFBB0 | rn) + h(0xF0F0 | rd << 8 | rm)
def ldrb_reg(rt, rn, rm): return h(0x5C00 | rm << 6 | rn << 3 | rt)
def strb_reg(rt, rn, rm): return h(0x5400 | rm << 6 | rn << 3 | rt)
def ldrh_reg(rt, rn, rm): return h(0x5A00 | rm << 6 | rn << 3 | rt)
def strh_reg(rt, rn, rm): return h(0x5200 | rm << 6 | rn << 3 | rt)


def arm_code(base, L, prev, ui=False, keep=False, init=False):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    E(raw, bytes(IDX) + bytes(16 - NLANE))
    t_idx = base

    # ---- c_arram() -> r0 = our RAM, 0 without it; clobbers r1-r3
    a.label("c_arram")
    E(push_list, [4], lr=True)
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "rm_x", "eq")
    E(movw, 1, O)
    E(adds_reg, 0, 0, 1)
    a.label("rm_x")
    E(pop_list, [4], pc=True)

    # ---- c_arpat(r0 = track, r1 = pattern) -> r0 = the pattern's base, 0 without a record; clobbers r1-r3
    a.label("c_arpat")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "pa_x", "eq")
    imm32(1, rhrec.TAIL - PAT0)
    E(subs_reg, 0, 0, 1)                                                  # R + 0x2E4
    imm32(1, TRK_SZ)
    E(muls, 1, 4)
    E(adds_reg, 0, 0, 1)
    E(movw, 1, PAT_SZ)
    E(muls, 1, 5)
    E(adds_reg, 0, 0, 1)
    a.label("pa_x")
    E(pop_list, [4, 5], pc=True)

    # ---- c_arstock (0x08055324 as a subroutine)
    a.label("c_arstock")
    E(raw, pushw([3, 4, 5, 6, 7, 8, 9, 10, 11], lr=True))
    E(b_w, PLAY_CONT)

    # ---- c_arplay (0x08055324's head: r0 = player, r1 = pattern, r2 = step, r3 = micro step)
    a.label("c_arplay")
    E(push_list, [0, 1, 2, 3, 4, 5, 6, 7], lr=True)
    E(ldr_imm, 4, 0, 0)
    imm32(5, DP_VT)
    E(cmp_reg, 4, 5)
    E(b_cond, "ap_s", "ne")
    imm32(5, DP0)
    E(subs_reg, 4, 0, 5)
    E(b_cond, "ap_s", "lo")
    E(movw, 5, DP_SZ)
    E(raw, udiv(6, 4, 5))
    E(muls, 5, 6)
    E(cmp_reg, 4, 5)
    E(b_cond, "ap_s", "ne")
    E(cmp_imm, 6, 8)
    E(b_cond, "ap_s", "hs")
    E(cmp_imm, 1, 8)
    E(b_cond, "ap_s", "hs")
    E(cmp_imm, 2, 32)
    E(b_cond, "ap_s", "hs")                                               # r6 = the track
    E(bl, "c_arram")
    E(cmp_imm, 0, 0)
    E(b_cond, "ap_s", "eq")
    E(movs_imm, 1, T_SZ)
    E(muls, 1, 6)
    E(adds_reg, 0, 0, 1)
    E(adds_imm8, 0, R_TRK)
    E(mov_reg, 7, 0)                                                      # r7 = the track's part
    E(raw, h(0x9803))                                                     # ldr r0, [sp, #12]: the micro step
    E(cmp_imm, 0, 0)
    E(b_cond, "ap_k", "ne")
    E(mov_reg, 0, 6)                                                      # micro step 0: the pattern's marks, this step's
    E(raw, h(0x9901))                                                     # ldr r1, [sp, #4]: the pattern
    E(bl, "c_arpat")
    E(cmp_imm, 0, 0)
    E(b_cond, "ap_s", "eq")
    E(movs_imm, 1, 0)                                                     # r1 = any marked
    E(movs_imm, 2, 0)
    a.label("ap_m")
    E(lsls_imm, 3, 2, 3)
    E(adds_reg, 3, 3, 0)
    E(ldrb_imm, 3, 3, MARK_OFF)
    E(movs_imm, 4, MARK)
    E(raw, h(0x4023))                                                     # ands r3, r4
    E(orrs_reg, 1, 3)
    E(adds_imm8, 2, 1)
    E(cmp_imm, 2, 32)
    E(b_cond, "ap_m", "lo")
    E(strb_imm, 1, 7, T_HAS)
    E(raw, h(0x9A02))                                                     # ldr r2, [sp, #8]: the step
    E(lsls_imm, 2, 2, 3)
    E(adds_reg, 2, 2, 0)
    E(ldrb_imm, 2, 2, MARK_OFF)
    E(movs_imm, 4, MARK)
    E(raw, h(0x4022))                                                     # ands r2, r4
    E(strb_imm, 2, 7, T_CUR)
    a.label("ap_k")
    E(ldrb_imm, 0, 7, T_HAS)
    E(cmp_imm, 0, 0)
    E(b_cond, "ap_s", "eq")                                               # no mark in the pattern: the stock's
    E(raw, h(0x9C00))                                                     # ldr r4, [sp]: the player
    E(ldrb_imm, 0, 7, T_CUR)
    E(cmp_imm, 0, 0)
    E(b_cond, "ap_n", "eq")
    E(raw, h(0x9803))                                                     # a marked step: no lane plays; at its micro step 0 the bases back
    E(cmp_imm, 0, 0)
    E(b_cond, "ap_x", "ne")
    E(bl, "c_arrelease")
    E(b, "ap_x")
    a.label("ap_n")
    E(raw, h(0x9803))
    E(cmp_imm, 0, 0)
    E(b_cond, "ap_r", "ne")
    E(bl, "c_arbase")                                                     # micro step 0: the free lanes' bases
    a.label("ap_r")
    E(raw, h(0x9800))
    E(raw, h(0x9901))
    E(raw, h(0x9A02))
    E(raw, h(0x9B03))
    E(bl, "c_arstock")
    E(bl, "c_artake")
    a.label("ap_x")
    E(pop_list, [0, 1, 2, 3, 4, 5, 6, 7], pc=True)
    a.label("ap_s")
    E(raw, popw([0, 1, 2, 3, 4, 5, 6, 7], lr=True))
    E(raw, pushw([3, 4, 5, 6, 7, 8, 9, 10, 11], lr=True))
    E(b_w, PLAY_CONT)

    # ---- c_arbase() (r4 = player, r6 = track, r7 = its part): every lane not taken: its parameter now as its base; clobbers r0-r3, r5
    a.label("c_arbase")
    E(push_list, [4], lr=True)
    E(movs_imm, 5, 0)
    a.label("ab_l")
    E(ldrh_imm, 0, 7, T_FLAGS)
    E(lsrs_reg, 0, 5)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "ab_n", "mi")
    imm32(1, t_idx)
    E(raw, ldrb_reg(1, 1, 5))
    E(mov_reg, 0, 6)
    E(adds_imm8, 0, 0x10)
    E(bl, GROUP_GET)
    E(adds_reg, 1, 7, 5)
    E(strb_imm, 0, 1, T_BASE)
    a.label("ab_n")
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, NLANE)
    E(b_cond, "ab_l", "lo")
    E(pop_list, [4], pc=True)

    # ---- c_artake() (r4 = player, r7 = its part): a lane with a last applied value is taken; suspended or without automation: given back;
    #      clobbers r0-r3, r5
    a.label("c_artake")
    E(push_list, [4, 6], lr=True)
    E(ldr_imm, 0, 4, P_TOUCH)
    E(movs_imm, 1, 0)
    E(bl, GET)
    E(ldr_imm, 6, 0, 0)                                                   # r6 = the suspended lanes
    E(ldr_imm, 0, 4, P_MASK)
    E(movs_imm, 1, 0)
    E(bl, GET)
    E(ldr_imm, 0, 0, 0)
    E(raw, h(0x43C0))                                                     # mvns r0, r0: the lanes without automation
    E(orrs_reg, 6, 0)                                                     # r6 = the lanes to give back
    E(ldrh_imm, 2, 7, T_FLAGS)
    E(ldr_imm, 3, 4, P_LAST)
    E(movs_imm, 5, 0)
    a.label("at_l")
    E(lsls_imm, 0, 5, 1)
    E(raw, ldrh_reg(0, 3, 0))
    E(movw, 1, 0xFFFF)
    E(cmp_reg, 0, 1)
    E(b_cond, "at_g", "eq")
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 5)
    E(orrs_reg, 2, 1)
    a.label("at_g")
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, NLANE)
    E(b_cond, "at_l", "lo")
    E(raw, h(0x43B2))                                                     # bics r2, r6
    E(strh_imm, 2, 7, T_FLAGS)
    E(pop_list, [4, 6], pc=True)

    # ---- c_arrelease() (r4 = player, r7 = its part): every taken lane's base back through the stock's slot, its values cleared; clobbers r0-r3, r5
    a.label("c_arrelease")
    E(push_list, [4, 6], lr=True)
    E(movs_imm, 5, 0)
    a.label("ar_l")
    E(ldrh_imm, 0, 7, T_FLAGS)
    E(lsrs_reg, 0, 5)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "ar_c", "pl")
    E(ldr_imm, 0, 4, P_IDS)
    E(lsls_imm, 1, 5, 1)
    E(raw, ldrh_reg(1, 0, 1))                                             # the lane's id
    E(adds_reg, 2, 7, 5)
    E(ldrb_imm, 2, 2, T_BASE)
    if init:                                                              # (init, RH58) Project init: trkcopy's photo (as loaded / saved) when valid
        E(push_list, [0, 1, 2])
        E(bl, L["c_rram"])
        E(cmp_imm, 0, 0)
        E(b_cond, "ai_b", "eq")
        E(movw, 1, rhstate.OFF2["trkphoto"][0])
        E(adds_reg, 0, 0, 1)
        E(ldrb_imm, 1, 0, 0)
        E(cmp_imm, 1, ord("T"))
        E(b_cond, "ai_b", "ne")
        E(ldrb_imm, 1, 0, 1)
        E(cmp_imm, 1, ord("S"))
        E(b_cond, "ai_b", "ne")
        E(adds_imm8, 0, 2)
        E(movs_imm, 1, 26)
        E(muls, 1, 6)
        E(adds_reg, 0, 0, 1)                                              # the track's photo (r6 = the track, c_arplay's)
        imm32(1, t_idx)
        E(raw, ldrb_reg(1, 1, 5))
        E(raw, ldrb_reg(0, 0, 1))                                         # its parameter of this lane
        E(raw, h(0x9002))                                                 # str r0, [sp, #8]: in place of the base
        a.label("ai_b")
        E(pop_list, [0, 1, 2])
    E(ldr_imm, 0, 4, P_PARAM)
    E(ldr_imm, 3, 0, 0)
    E(ldr_imm, 3, 3, 0)
    E(raw, h(0x4798))                                                     # blx r3
    a.label("ar_c")
    E(movw, 0, 0xFFFF)
    E(lsls_imm, 1, 5, 1)
    E(ldr_imm, 2, 4, P_HELD)
    E(raw, strh_reg(0, 2, 1))
    E(ldr_imm, 2, 4, P_LAST)
    E(raw, strh_reg(0, 2, 1))
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, NLANE)
    E(b_cond, "ar_l", "lo")
    E(movs_imm, 0, 0)
    E(strh_imm, 0, 7, T_FLAGS)
    E(pop_list, [4, 6], pc=True)

    # ---- c_arvel() -> r0 = 1 when the Velocity view is on the screen and Shift held; clobbers r1-r3
    a.label("c_arvel")
    E(push_list, [4], lr=True)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "av_x", "eq")
    imm32(0, CI.CTRL)
    E(ldr_imm, 1, 0, 0x7C)
    imm32(0, CONT)
    E(cmp_reg, 0, 1)
    E(b_cond, "av_0", "ne")
    E(ldrb_w, 1, 0, O_MODE)
    E(cmp_imm, 1, MODE_VEL)
    E(b_cond, "av_0", "ne")
    E(bl, L["c_cishift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "av_x", "eq")
    E(movs_imm, 0, 1)
    E(pop_list, [4], pc=True)
    a.label("av_0")
    E(movs_imm, 0, 0)
    a.label("av_x")
    E(pop_list, [4], pc=True)

    # ---- c_arsteps(r0 = step view) -> r0 = the step bytes of its pattern on the screen (its ST1's pattern); clobbers r1
    a.label("c_arsteps")
    E(ldr_imm, 0, 0, SV_ST1)
    E(ldr_imm, 0, 0, 0x18)
    E(movw, 1, LANES_OFF)
    E(subs_reg, 0, 0, 1)
    E(raw, h(0x4770))

    # ---- c_arpress (the step views' slot 0: view, pad, velocity): Velocity view with Shift: the step's mark
    a.label("c_arpress")
    E(cmp_imm, 1, 16)
    E(b_cond, "pr_s", "hs")
    E(push_list, [0, 1, 2, 3, 4, 5], lr=True)
    imm32(1, SV0)
    E(movw, 2, SV_SZ)
    imm32(3, SV_VT)
    E(bl, L["c_sgsvt"])
    E(cmp_imm, 0, 8)
    E(b_cond, "pr_p", "hs")
    E(bl, "c_arvel")
    E(cmp_imm, 0, 0)
    E(b_cond, "pr_p", "eq")
    E(bl, "c_arram")
    E(cmp_imm, 0, 0)
    E(b_cond, "pr_p", "eq")
    E(mov_reg, 5, 0)                                                      # r5 = our RAM
    E(raw, h(0x9800))                                                     # ldr r0, [sp]: the view
    E(raw, h(0x9901))                                                     # ldr r1, [sp, #4]: the pad
    E(bl, L["c_sgstep"])
    E(mov_reg, 4, 0)                                                      # r4 = the step
    E(raw, h(0x9800))
    E(bl, "c_arsteps")
    E(lsls_imm, 1, 4, 3)
    E(adds_reg, 0, 0, 1)
    E(ldrb_imm, 1, 0, MARK_OFF)
    E(movs_imm, 2, MARK)
    E(raw, h(0x4051))                                                     # eors r1, r2
    E(strb_imm, 1, 0, MARK_OFF)
    E(ldr_imm, 0, 5, R_SW)                                                # its release swallowed
    E(movs_imm, 1, 1)
    E(raw, h(0x9A01))                                                     # ldr r2, [sp, #4]
    E(lsls_reg, 1, 2)
    E(orrs_reg, 0, 1)
    E(str_imm, 0, 5, R_SW)
    E(pop_list, [0, 1, 2, 3, 4, 5], pc=True)
    a.label("pr_p")
    E(raw, popw([0, 1, 2, 3, 4, 5], lr=True))
    a.label("pr_s")
    E(b_w, prev["press"])

    # ---- c_arrel (the step views' slot 1: view, pad): a press we took: its release too
    a.label("c_arrel")
    E(cmp_imm, 1, 16)
    E(b_cond, "rl_s", "hs")
    E(push_list, [0, 1, 2, 3, 4, 5], lr=True)
    E(bl, "c_arram")
    E(cmp_imm, 0, 0)
    E(b_cond, "rl_p", "eq")
    E(ldr_imm, 2, 0, R_SW)
    E(movs_imm, 3, 1)
    E(raw, h(0x9901))                                                     # ldr r1, [sp, #4]
    E(lsls_reg, 3, 1)
    E(tst_reg, 2, 3)
    E(b_cond, "rl_p", "eq")
    E(raw, h(0x439A))                                                     # bics r2, r3
    E(str_imm, 2, 0, R_SW)
    E(pop_list, [0, 1, 2, 3, 4, 5], pc=True)
    a.label("rl_p")
    E(raw, popw([0, 1, 2, 3, 4, 5], lr=True))
    a.label("rl_s")
    E(b_w, prev["rel"])

    # ---- c_arled (the LED task's calls: ctrl, frame): the chain, then the step pads in the Velocity view with Shift
    a.label("c_arled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)
    E(bl, prev["ledtask"])
    E(bl, "c_arvel")
    E(cmp_imm, 0, 0)
    E(b_cond, "ld_x", "eq")
    imm32(0, CONT)
    E(bl, SG.SELTRK)
    E(cmp_imm, 0, 8)
    E(b_cond, "ld_x", "hs")
    E(movw, 1, SV_SZ)
    E(muls, 0, 1)
    imm32(1, SV0)
    E(adds_reg, 6, 0, 1)                                                  # r6 = its step view
    E(ldr_imm, 0, 6, SV_PAGE)
    E(movs_imm, 1, 0)
    E(bl, GET)
    E(ldrb_imm, 4, 0, 0)
    E(cmp_imm, 4, 0)
    E(b_cond, "ld_p", "eq")
    E(movs_imm, 4, 16)
    a.label("ld_p")                                                       # r4 = the page's first step
    E(mov_reg, 0, 6)
    E(bl, "c_arsteps")
    E(mov_reg, 7, 0)
    E(movs_imm, 3, 0)
    a.label("ld_l")
    E(adds_reg, 0, 3, 4)
    E(lsls_imm, 0, 0, 3)
    E(adds_reg, 0, 0, 7)
    E(ldrb_imm, 0, 0, MARK_OFF)
    if keep:                                                              # (keep) only a marked step drawn
        E(lsls_imm, 0, 0, 31)
        E(b_cond, "ld_n", "pl")
        E(movs_imm, 1, COL_MARK)
    else:
        E(movs_imm, 1, UI_AV if ui else COL_AV)
        E(lsls_imm, 0, 0, 31)
        E(b_cond, "ld_w", "pl")
        E(movs_imm, 1, COL_MARK)
        a.label("ld_w")
    E(lsls_imm, 0, 3, 1)
    E(raw, strh_reg(1, 5, 0))
    if keep:
        a.label("ld_n")
    E(adds_imm8, 3, 1)
    E(cmp_imm, 3, 16)
    E(b_cond, "ld_l", "lo")
    a.label("ld_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr, ui=False, keep=False, init=False):
    """The head of 0x08055324, the step views' slots 0 / 1 (stepgate's in front), the head of the LED calls.  Needs stepgate, rhrec, rhstate ram2."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]                 # noqa: E731
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    L = dict(c_rram=lab("rhstate", "c_rram"), c_rrt=lab("rhrec", "c_rrt"), c_ciok=lab("countin", "c_ciok"),
             c_cishift=lab("countin", "c_cishift"), c_sgsvt=lab("stepgate", "c_sgsvt"), c_sgstep=lab("stepgate", "c_sgstep"))
    prev = dict(press=u(SV_VT) & ~1, rel=u(SV_VT + 4) & ~1, ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert prev["press"] == lab("stepgate", "c_sgpress") and prev["rel"] == lab("stepgate", "c_sgrel")
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    assert not init or report["trkcopy"].get("ram"), "autorel init: needs trkcopy's photo in RAM"
    code, labels = arm_code(base_addr, L, prev, ui, keep, init)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, PLAY, PLAY_HEAD, b_w(PLAY, labels["c_arplay"]))
    rhbuild.patch_word(img, SV_VT, prev["press"] | 1, labels["c_arpress"] | 1)
    rhbuild.patch_word(img, SV_VT + 4, prev["rel"] | 1, labels["c_arrel"] | 1)
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_arled"]))
    report["autorel"] = dict(prev={k: hex(v) for k, v in prev.items()}, **({"keep": True} if keep else {}), **({"init": True} if init else {}), labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
