"""Micro Step view: pad 31 = fixed length, pad 32 = gate by holding (MIT; RH46, docs/PRUEBA_RH46.md; the feature of CIRCUIT-HACKS'
stepgate, written again for the Rhythm's step pads).

The user (2026-10-26): «Falta portar fixed length y user input length de Tracks en la vista microstep».

The stock of the Rhythm (read in its image, run on the RAM dump):
  * the step pads (1-16) of the track views go to the track's step view (0x2004B3A4 + 0x118 t, vtable 0x080682CC; [view + 0xC] = ST1,
    [view + 0x10] = ST2 of the pattern on the screen; p0 of [view + 0x60] = the second page: pad + 16): slot 0 0x0805CB04 (press) marks the
    step pending, slot 1 0x0805CCF0 (release) toggles it through 0x0805D610(view, step) (0x08054AE0(ST1, step) <> 0 = a hit there: delete,
    else a hit with the step's gate as it is, 6 for an untouched step); a press held 300 ms (its timer, 0x0805CE48) drops the pending
    toggle, so a long press makes no hit;
  * a step's gate = byte step & 3 of parameter 8 + step / 4 of ST2 (micro steps, 6 a step; the Gate view writes 6 .. 96); written there and
    committed (0x0803FD26 / 0x0803FBEC) the store's listener carries it to the pattern;
  * Micro Step = Shift + Gate (the track views' container 0x20048B9C in mode 5, [+ 0x264]); its view per track at 0x2004C258 + 0x4C t
    (vtable 0x08067FBC): slot 0 0x08056F7C gets pads 17-32 as 0..15 and uses 0..5 (the micro steps): pads 31 / 32 do nothing.
Ours (per track, saved with the project: rhrec "stepgate", "SG", a check byte, the gate-by-holding bits, 8 fixed-length bytes: bit 7 on,
bits 0-4 the length 1..16 steps, kept while off):
  * Micro Step pad 32 = the gate by holding on / off; pad 31 = the fixed length: off -> its selector on pads 17-32 (1 .. 16 steps; a length
    picked turns it on), on -> off; one turned on turns the other off.  LEDs: 32 green on, 31 orange on, dim off; the selector green up to
    the length.  The selector closes when Micro Step leaves the screen;
  * a step pad whose press found the step empty and whose release leaves a hit there (the stock's tap; a step held while a sample pad or a key
    makes the hit) gets the fixed length, or the time it was held (micro steps at the project's tempo and the track's sync rate, 1 .. 96);
    with the gate by holding, a press held 300 ms or more on an empty step (no Shift, Clear, Duplicate) makes the hit too, with that gate.
  RAM (rhstate OFF2 "stepgate"): + 0 the selector's track + 1, + 1 the track of the presses + 1, + 4 the steps empty at their press, + 8 the
  steps pressed, + 12 each step's press time (HAL tick, low 16 bits).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b, b_cond, b_w, bl, cmp_imm, cmp_reg, eors_reg, h, ldr_imm, ldrb_imm, ldrb_w, ldrh_imm,  # noqa: E402
                   lsls_imm, lsls_reg, lsrs_imm, lsrs_reg, mov_reg, movs_imm, movt, movw, muls, orrs_reg, pop_list, push_list, raw, str_imm,
                   strb_imm, strh_imm, subs_imm8, subs_reg, bics_reg, tst_reg)
import countin as CI  # noqa: E402
import rhrec  # noqa: E402
import rhstate  # noqa: E402
import sckn as SK  # noqa: E402
import stockplus as SP  # noqa: E402

SV0, SV_SZ, SV_VT = 0x2004B3A4, 0x118, 0x080682CC          # the step views
SV_ST1, SV_ST2, SV_PAGE = 0xC, 0x10, 0x60
HIT, TOGGLE = 0x08054AE0, 0x0805D610
MV0, MV_SZ, MV_VT = 0x2004C258, 0x4C, 0x08067FBC          # the Micro Step views
CONT, O_MODE, MODE_MICRO = SK.CONT, SK.O_MODE, 5
SELTRK = SP.SELTRK
PAD_FIX, PAD_HOLD, NMICRO = 14, 15, 6                      # pads 31 / 32 (the view gets pads 17-32 as 0..15)
PLAYER0, PL_SZ, PL_RATE = 0x200470D4, 0x190, 0x10
TICKS = 0x08068D9C                                          # ticks a step (24 a beat) by sync rate
TEMPO = 0x20012788                                          # p0 = the BPM
GET, WPTR, COMMIT = CI.PARAM_GET, CI.WPTR, CI.COMMIT
HAL_TICK = CI.HAL_TICK
O_HELD, B_CLEAR, B_DUP = 0xA0, 23, 24
HOLD_MS, MS_MAX, GMAX = 300, 60000, 96
COL_ON, COL_DIM, COL_FIX = 0x1E, 0x09, 0x41                 # green, dim, orange
# ui (RH52; docs/INTERFAZ.md, the user, 2026-10-28: «toggles change brightness if they're on-off»): off = the dim of its own colour
UI_DIM_ON, UI_DIM_FIX = 0x1F, 0x42                        # dim green, dim orange
MARK0, MARK1, CHECK = 0x53, 0x47, 0x5A                      # "SG"
BLK, BLK_LEN = rhrec.OFF["stepgate"]
T_HOLD, T_FIX = 3, 4                                        # the tail block: + 3 the gate-by-holding bits, + 4 + t the fixed lengths
O = rhstate.OFF2["stepgate"][0]
R_SEL, R_TRK, R_EMPTY, R_PRESS, R_TIME = 0, 1, 4, 8, 12
assert BLK_LEN >= T_FIX + 8 and rhstate.OFF2["stepgate"][1] >= R_TIME + 64 and O % 4 == 0
INV = SK.INV


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))
def udiv(rd, rn, rm): return h(0xFBB0 | rn) + h(0xF0F0 | rd << 8 | rm)
def ldrh_reg(rt, rn, rm): return h(0x5A00 | rm << 6 | rn << 3 | rt)
def strh_reg(rt, rn, rm): return h(0x5200 | rm << 6 | rn << 3 | rt)
def ldr_reg(rt, rn, rm): return h(0x5800 | rm << 6 | rn << 3 | rt)


def gate_ms(ms, bpm, tps):
    """the model (the tests'): the gate for a press held ms milliseconds, as c_sgms"""
    ms = min(ms, MS_MAX)
    if bpm < 40:
        bpm = 120
    g = (ms * 144 * bpm + tps * 30000) // (tps * 60000)
    return max(1, min(GMAX, g))


def arm_code(base, L, prev, ui=False):
    a = Asm(base)
    E = a.emit
    zc = [0]

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    def bc(target, cond):
        zc[0] += 1
        n = f"_g{zc[0]}"
        E(b_cond, n, INV[cond])
        E(b, target)
        a.label(n)

    # ---- c_sgram() -> r0 = our RAM block, 0 without it; clobbers r1-r3
    a.label("c_sgram")
    E(push_list, [4], lr=True)
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "rm_x", "eq")
    E(movw, 1, O)
    E(adds_reg, 0, 0, 1)
    a.label("rm_x")
    E(pop_list, [4], pc=True)

    # ---- c_sgblk() -> r0 = our block in the record's tail when it is valid, else 0; r1 = the block (0 without a record); clobbers r2, r3
    a.label("c_sgblk")
    E(push_list, [4], lr=True)
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "bk_0", "eq")
    E(movw, 1, BLK)
    E(adds_reg, 0, 0, 1)
    E(mov_reg, 1, 0)
    E(ldrb_imm, 2, 0, 0)
    E(cmp_imm, 2, MARK0)
    E(b_cond, "bk_n", "ne")
    E(ldrb_imm, 2, 0, 1)
    E(cmp_imm, 2, MARK1)
    E(b_cond, "bk_n", "ne")
    E(movs_imm, 2, CHECK)
    E(movs_imm, 3, T_HOLD)
    a.label("bk_l")
    E(raw, h(0x5CC4))                                                     # ldrb r4, [r0, r3]
    E(eors_reg, 2, 4)
    E(adds_imm8, 3, 1)
    E(cmp_imm, 3, T_FIX + 8)
    E(b_cond, "bk_l", "lo")
    E(ldrb_imm, 3, 0, 2)
    E(cmp_reg, 2, 3)
    E(b_cond, "bk_x", "eq")
    a.label("bk_n")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)
    a.label("bk_0")
    E(movs_imm, 1, 0)
    a.label("bk_x")
    E(pop_list, [4], pc=True)

    # ---- c_sgget(r0 = track) -> r0 = its fixed-length byte | the gate by holding << 8 (0 without a valid block); clobbers r1-r3
    a.label("c_sgget")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_sgblk")
    E(cmp_imm, 0, 0)
    E(b_cond, "gg_x", "eq")
    E(ldrb_imm, 1, 0, T_HOLD)
    E(lsrs_reg, 1, 4)
    E(lsls_imm, 1, 1, 31)
    E(lsrs_imm, 1, 1, 23)                                                 # bit 8
    E(adds_reg, 0, 0, 4)
    E(ldrb_imm, 0, 0, T_FIX)
    E(orrs_reg, 0, 1)
    a.label("gg_x")
    E(pop_list, [4], pc=True)

    # ---- c_sgput(r0 = track, r1 = its fixed-length byte | the gate by holding << 8): the block made when missing, the check again; clobbers r0-r3
    a.label("c_sgput")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(bl, "c_sgblk")
    E(cmp_imm, 1, 0)
    E(b_cond, "pt_x", "eq")                                               # no record
    E(mov_reg, 6, 1)
    E(cmp_imm, 0, 0)
    E(b_cond, "pt_v", "ne")
    E(movs_imm, 2, MARK0)                                                 # new: marked, all off
    E(strb_imm, 2, 6, 0)
    E(movs_imm, 2, MARK1)
    E(strb_imm, 2, 6, 1)
    E(movs_imm, 2, 0)
    E(movs_imm, 3, T_HOLD)
    a.label("pt_z")
    E(raw, h(0x54F2))                                                     # strb r2, [r6, r3]
    E(adds_imm8, 3, 1)
    E(cmp_imm, 3, T_FIX + 8)
    E(b_cond, "pt_z", "lo")
    a.label("pt_v")
    E(adds_reg, 0, 6, 4)
    E(strb_imm, 5, 0, T_FIX)                                              # the fixed-length byte
    E(ldrb_imm, 1, 6, T_HOLD)
    E(movs_imm, 2, 1)
    E(lsls_reg, 2, 4)
    E(raw, h(0x4391))                                                     # bics r1, r2
    E(lsrs_imm, 3, 5, 8)
    E(movs_imm, 0, 1)
    E(raw, h(0x4003))                                                     # ands r3, r0: the gate by holding
    E(lsls_reg, 3, 4)
    E(orrs_reg, 1, 3)
    E(strb_imm, 1, 6, T_HOLD)
    E(movs_imm, 2, CHECK)                                                 # the check
    E(movs_imm, 3, T_HOLD)
    a.label("pt_c")
    E(raw, h(0x5CF0))                                                     # ldrb r0, [r6, r3]
    E(eors_reg, 2, 0)
    E(adds_imm8, 3, 1)
    E(cmp_imm, 3, T_FIX + 8)
    E(b_cond, "pt_c", "lo")
    E(strb_imm, 2, 6, 2)
    a.label("pt_x")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_sgstep(r0 = a step view, r1 = its pad) -> r0 = the step (pad + 16 on the second page); clobbers r1-r3
    a.label("c_sgstep")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 1)
    E(ldr_imm, 0, 0, SV_PAGE)
    E(movs_imm, 1, 0)
    E(bl, GET)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "sp_x", "eq")
    E(adds_imm8, 4, 16)
    a.label("sp_x")
    E(movs_imm, 0, 31)
    E(raw, h(0x4020))                                                     # ands r0, r4
    E(pop_list, [4], pc=True)

    # ---- c_sgsvt(r0 = a view, r1 = its first, r2 = its stride, r3 = its vtable) -> r0 = its track, 8 if not one of the eight; clobbers r1-r3
    a.label("c_sgsvt")
    E(push_list, [4], lr=True)
    E(ldr_imm, 4, 0, 0)
    E(cmp_reg, 4, 3)
    E(b_cond, "vt_n", "ne")
    E(subs_reg, 0, 0, 1)
    E(b_cond, "vt_n", "lo")
    E(raw, udiv(3, 0, 2))
    E(muls, 2, 3)
    E(cmp_reg, 0, 2)
    E(b_cond, "vt_n", "ne")
    E(cmp_imm, 3, 8)
    E(b_cond, "vt_n", "hs")
    E(mov_reg, 0, 3)
    E(pop_list, [4], pc=True)
    a.label("vt_n")
    E(movs_imm, 0, 8)
    E(pop_list, [4], pc=True)

    # ---- c_sgms(r0 = track, r1 = ms) -> r0 = the gate (micro steps, 1..96) at the project's tempo and the track's sync rate; clobbers r1-r3
    a.label("c_sgms")
    E(push_list, [4, 5, 6], lr=True)
    imm32(2, MS_MAX)
    E(cmp_reg, 1, 2)
    E(b_cond, "ms_m", "ls")
    E(mov_reg, 1, 2)
    a.label("ms_m")
    E(mov_reg, 4, 1)                                                      # r4 = ms
    E(movw, 1, PL_SZ)
    E(muls, 0, 1)
    imm32(1, PLAYER0)
    E(adds_reg, 0, 0, 1)
    E(ldr_imm, 0, 0, PL_RATE)
    E(movs_imm, 1, 1)
    E(bl, GET)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, 7)
    E(b_cond, "ms_r", "ls")
    E(movs_imm, 0, 7)
    a.label("ms_r")
    E(lsls_imm, 0, 0, 2)
    imm32(1, TICKS)
    E(raw, ldr_reg(5, 1, 0))                                              # r5 = the ticks a step
    imm32(0, TEMPO)
    E(movs_imm, 1, 0)
    E(bl, GET)
    E(ldrb_imm, 1, 0, 0)
    E(cmp_imm, 1, 40)
    E(b_cond, "ms_b", "hs")
    E(movs_imm, 1, 120)
    a.label("ms_b")
    E(movs_imm, 0, 144)
    E(muls, 0, 1)
    E(muls, 0, 4)                                                         # ms x 144 x BPM
    imm32(1, 30000)
    E(muls, 1, 5)
    E(adds_reg, 0, 0, 1)
    imm32(1, 60000)
    E(muls, 1, 5)
    E(raw, udiv(0, 0, 1))
    E(cmp_imm, 0, 0)
    E(b_cond, "ms_1", "ne")
    E(movs_imm, 0, 1)
    a.label("ms_1")
    E(cmp_imm, 0, GMAX)
    E(b_cond, "ms_x", "ls")
    E(movs_imm, 0, GMAX)
    a.label("ms_x")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_sgset(r0 = step view, r1 = step, r2 = gate): the gate in ST2 and its commit (the listener writes the pattern); clobbers r0-r3
    a.label("c_sgset")
    E(push_list, [4, 5, 6], lr=True)
    E(ldr_imm, 4, 0, SV_ST2)
    E(mov_reg, 5, 1)
    E(mov_reg, 6, 2)
    E(mov_reg, 0, 4)
    E(lsrs_imm, 1, 5, 2)
    E(adds_imm8, 1, 8)
    E(bl, WPTR)
    E(movs_imm, 1, 3)
    E(raw, h(0x4029))                                                     # ands r1, r5
    E(raw, h(0x5446))                                                     # strb r6, [r0, r1]
    E(mov_reg, 0, 4)
    E(bl, COMMIT)
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_sghit(r0 = step view, r1 = step) -> r0 = 1 when the step holds a hit; clobbers r1-r3
    a.label("c_sghit")
    E(push_list, [4], lr=True)
    E(ldr_imm, 0, 0, SV_ST1)
    E(bl, HIT)
    E(cmp_imm, 0, 0)
    E(b_cond, "ht_x", "eq")
    E(movs_imm, 0, 1)
    a.label("ht_x")
    E(pop_list, [4], pc=True)

    # ---- c_sgpress (the step views' slot 0: r0 = view, r1 = pad, r2 = velocity): whether the step is empty, and the time, then the stock's
    a.label("c_sgpress")
    E(push_list, [0, 1, 2, 3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    imm32(1, SV0)
    E(movw, 2, SV_SZ)
    imm32(3, SV_VT)
    E(bl, "c_sgsvt")
    E(cmp_imm, 0, 8)
    bc("pr_x", "hs")
    E(mov_reg, 6, 0)                                                      # r6 = the track
    E(bl, "c_sgget")
    E(cmp_imm, 0, 0)
    E(b_cond, "pr_g", "ne")
    bc("pr_x", "eq")
    a.label("pr_g")
    E(lsls_imm, 1, 0, 24)                                                 # the fixed length on (bit 7) or the gate by holding (bit 8)
    E(b_cond, "pr_on", "mi")
    E(lsrs_imm, 1, 0, 8)
    bc("pr_x", "eq")
    a.label("pr_on")
    E(bl, "c_sgram")
    E(cmp_imm, 0, 0)
    bc("pr_x", "eq")
    E(mov_reg, 7, 0)                                                      # r7 = our RAM
    E(ldrb_imm, 0, 7, R_TRK)
    E(subs_imm8, 0, 1)
    E(cmp_reg, 0, 6)
    E(b_cond, "pr_t", "eq")
    E(mov_reg, 0, 6)                                                      # another track: its records forgotten
    E(adds_imm8, 0, 1)
    E(strb_imm, 0, 7, R_TRK)
    E(movs_imm, 0, 0)
    E(str_imm, 0, 7, R_EMPTY)
    E(str_imm, 0, 7, R_PRESS)
    a.label("pr_t")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, "c_sgstep")
    E(mov_reg, 5, 0)                                                      # r5 = the step
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, "c_sghit")
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 5)                                                     # r1 = its bit
    E(ldr_imm, 2, 7, R_EMPTY)
    E(raw, h(0x438A))                                                     # bics r2, r1
    E(cmp_imm, 0, 0)
    E(b_cond, "pr_h", "ne")
    E(orrs_reg, 2, 1)
    a.label("pr_h")
    E(str_imm, 2, 7, R_EMPTY)
    E(ldr_imm, 2, 7, R_PRESS)
    E(orrs_reg, 2, 1)
    E(str_imm, 2, 7, R_PRESS)
    imm32(0, HAL_TICK)
    E(ldr_imm, 0, 0, 0)
    E(lsls_imm, 1, 5, 1)
    E(adds_imm8, 1, R_TIME)
    E(raw, strh_reg(0, 7, 1))
    a.label("pr_x")
    E(raw, popw([0, 1, 2, 3, 4, 5, 6, 7], lr=True))
    E(b_w, prev["press"])

    # ---- c_sgrel (the step views' slot 1: r0 = view, r1 = pad): the stock's, then the gate of the hit it made
    a.label("c_sgrel")
    E(push_list, [0, 1, 3, 4, 5, 6, 7], lr=True)
    E(bl, prev["rel"])
    E(raw, h(0x9C00))                                                     # ldr r4, [sp, #0]: the view
    imm32(1, SV0)
    E(mov_reg, 0, 4)
    E(movw, 2, SV_SZ)
    imm32(3, SV_VT)
    E(bl, "c_sgsvt")
    E(cmp_imm, 0, 8)
    bc("rl_x", "hs")
    E(mov_reg, 6, 0)                                                      # r6 = the track
    E(bl, "c_sgram")
    E(cmp_imm, 0, 0)
    bc("rl_x", "eq")
    E(mov_reg, 7, 0)                                                      # r7 = our RAM
    E(ldrb_imm, 0, 7, R_TRK)
    E(subs_imm8, 0, 1)
    E(cmp_reg, 0, 6)
    bc("rl_x", "ne")
    E(mov_reg, 0, 4)
    E(raw, h(0x9901))                                                     # ldr r1, [sp, #4]: the pad
    E(bl, "c_sgstep")
    E(mov_reg, 5, 0)                                                      # r5 = the step
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 5)
    E(ldr_imm, 2, 7, R_PRESS)
    E(tst_reg, 2, 1)
    bc("rl_x", "eq")                                                      # its press not seen
    E(raw, h(0x438A))                                                     # bics r2, r1
    E(str_imm, 2, 7, R_PRESS)
    E(ldr_imm, 2, 7, R_EMPTY)
    E(tst_reg, 2, 1)
    bc("rl_x", "eq")                                                      # a hit was there
    E(mov_reg, 0, 6)
    E(bl, "c_sgget")
    E(mov_reg, 1, 0)
    E(push_list, [1])
    E(push_list, [1])                                                     # [sp] = the track's setting (twice: the stack kept 8-aligned)
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, "c_sghit")
    E(cmp_imm, 0, 0)
    E(b_cond, "rl_g", "ne")
    E(raw, h(0x9800))                                                     # ldr r0, [sp]: no hit: only the gate by holding makes one
    E(lsrs_imm, 0, 0, 9)
    E(b_cond, "rl_hd", "hs")
    E(b, "rl_p")
    a.label("rl_hd")
    E(bl, "c_sgheld")
    imm32(1, HOLD_MS)
    E(cmp_reg, 0, 1)
    bc("rl_p", "lo")
    imm32(0, CI.CTRL + O_HELD)
    E(ldr_imm, 0, 0, 0)
    imm32(1, 1 << B_CLEAR | 1 << B_DUP)
    E(tst_reg, 0, 1)
    bc("rl_p", "ne")
    E(bl, L["c_cishift"])
    E(cmp_imm, 0, 0)
    bc("rl_p", "ne")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, TOGGLE)
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, "c_sghit")
    E(cmp_imm, 0, 0)
    bc("rl_p", "eq")
    a.label("rl_g")
    E(raw, h(0x9800))                                                     # ldr r0, [sp]: the gate by holding, else the fixed length
    E(lsrs_imm, 1, 0, 9)
    E(b_cond, "rl_t", "hs")
    E(movs_imm, 1, 31)
    E(raw, h(0x4008))                                                     # ands r0, r1
    E(movs_imm, 1, 6)
    E(muls, 0, 1)
    E(cmp_imm, 0, 0)
    bc("rl_p", "eq")
    E(b, "rl_s")
    a.label("rl_t")
    E(bl, "c_sgheld")
    E(mov_reg, 1, 0)
    E(mov_reg, 0, 6)
    E(bl, "c_sgms")
    a.label("rl_s")
    E(mov_reg, 2, 0)
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, "c_sgset")
    a.label("rl_p")
    E(raw, h(0xB002))                                                     # add sp, #8
    a.label("rl_x")
    E(pop_list, [0, 1, 3, 4, 5, 6, 7], pc=True)

    # ---- c_sgheld() (r5 = step, r7 = our RAM) -> r0 = the ms since its press; clobbers r1
    a.label("c_sgheld")
    imm32(0, HAL_TICK)
    E(ldr_imm, 0, 0, 0)
    E(lsls_imm, 1, 5, 1)
    E(adds_imm8, 1, R_TIME)
    E(raw, ldrh_reg(1, 7, 1))
    E(subs_reg, 0, 0, 1)
    E(lsls_imm, 0, 0, 16)
    E(lsrs_imm, 0, 0, 16)
    E(raw, h(0x4770))

    # ---- c_sgmpad (the Micro Step views' slot 0: r0 = view, r1 = pad 0..15 = pads 17-32, r2 = velocity)
    a.label("c_sgmpad")
    E(push_list, [0, 1, 2, 3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)                                                      # r5 = the pad
    imm32(1, MV0)
    E(movs_imm, 2, MV_SZ)
    imm32(3, MV_VT)
    E(bl, "c_sgsvt")
    E(cmp_imm, 0, 8)
    bc("mp_s", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the track
    E(bl, "c_sgram")
    E(cmp_imm, 0, 0)
    bc("mp_s", "eq")
    E(mov_reg, 7, 0)                                                      # r7 = our RAM
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    bc("mp_s", "eq")                                                      # no record: the stock's
    E(mov_reg, 0, 4)
    E(bl, "c_sgget")
    E(mov_reg, 6, 0)                                                      # r6 = the setting
    E(ldrb_imm, 0, 7, R_SEL)
    E(subs_imm8, 0, 1)
    E(cmp_reg, 0, 4)
    E(b_cond, "mp_n", "ne")
    E(adds_imm8, 5, 1)                                                    # the selector: pad k = k + 1 steps, on, the gate by holding off
    E(movs_imm, 1, 0x80)
    E(orrs_reg, 1, 5)
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 7, R_SEL)
    E(b, "mp_w")
    a.label("mp_n")
    E(cmp_imm, 5, PAD_FIX)
    E(b_cond, "mp_h", "ne")
    E(lsls_imm, 0, 6, 24)
    E(b_cond, "mp_o", "pl")
    E(movs_imm, 1, 0x7F)                                                  # on: off (the length kept)
    E(raw, h(0x4031))                                                     # ands r1, r6
    E(b, "mp_w")
    a.label("mp_o")
    E(mov_reg, 0, 4)                                                      # off: the selector (the gate by holding off)
    E(adds_imm8, 0, 1)
    E(strb_imm, 0, 7, R_SEL)
    E(movs_imm, 1, 0x7F)
    E(raw, h(0x4031))                                                     # ands r1, r6
    E(b, "mp_w")
    a.label("mp_h")
    E(cmp_imm, 5, PAD_HOLD)
    bc("mp_s", "ne")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 7, R_SEL)
    E(lsrs_imm, 0, 6, 9)
    E(b_cond, "mp_ho", "hs")
    E(movs_imm, 1, 0x7F)                                                  # off: on, the fixed length off
    E(raw, h(0x4031))                                                     # ands r1, r6
    E(movs_imm, 0, 1)
    E(lsls_imm, 0, 0, 8)
    E(orrs_reg, 1, 0)
    E(b, "mp_w")
    a.label("mp_ho")
    E(movs_imm, 1, 0xFF)                                                  # on: off
    E(raw, h(0x4031))                                                     # ands r1, r6
    a.label("mp_w")
    E(mov_reg, 0, 4)
    E(bl, "c_sgput")
    E(pop_list, [0, 1, 2, 3, 4, 5, 6, 7], pc=True)
    a.label("mp_s")
    E(raw, popw([0, 1, 2, 3, 4, 5, 6, 7], lr=True))
    E(b_w, prev["mpad"])

    # ---- c_sgled (the LED task's calls: ctrl, frame): the chain, then Micro Step's pads 31 / 32 or the selector; the selector closed off it
    a.label("c_sgled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)                                                      # r5 = the frame
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(bl, "c_sgram")
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(mov_reg, 7, 0)                                                      # r7 = our RAM
    E(movs_imm, 4, 8)                                                     # r4 = the track in Micro Step, 8 = none
    imm32(0, CI.CTRL)
    E(ldr_imm, 1, 0, 0x7C)
    imm32(0, CONT)
    E(cmp_reg, 0, 1)
    E(b_cond, "ld_m", "ne")
    E(ldrb_w, 1, 0, O_MODE)
    E(cmp_imm, 1, MODE_MICRO)
    E(b_cond, "ld_m", "ne")
    E(bl, SELTRK)
    E(cmp_imm, 0, 8)
    E(b_cond, "ld_m", "hs")
    E(mov_reg, 4, 0)
    a.label("ld_m")
    E(ldrb_imm, 0, 7, R_SEL)
    E(cmp_imm, 0, 0)
    E(b_cond, "ld_d", "eq")
    E(subs_imm8, 0, 1)
    E(cmp_reg, 0, 4)
    E(b_cond, "ld_d", "eq")
    E(movs_imm, 0, 0)                                                     # its Micro Step not on the screen: closed
    E(strb_imm, 0, 7, R_SEL)
    a.label("ld_d")
    E(cmp_imm, 4, 8)
    bc("ld_x", "hs")
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(mov_reg, 0, 4)
    E(bl, "c_sgget")
    E(mov_reg, 6, 0)                                                      # r6 = the setting
    E(ldrb_imm, 0, 7, R_SEL)
    E(subs_imm8, 0, 1)
    E(cmp_reg, 0, 4)
    E(b_cond, "ld_p", "ne")
    E(movs_imm, 0, 31)                                                    # the selector: green up to the length
    E(raw, h(0x4030))                                                     # ands r0, r6
    E(movs_imm, 2, 0)
    a.label("ld_l")
    E(movs_imm, 1, UI_DIM_ON if ui else COL_DIM)
    E(cmp_reg, 2, 0)
    E(b_cond, "ld_w", "hs")
    E(movs_imm, 1, COL_ON)
    a.label("ld_w")
    E(lsls_imm, 3, 2, 1)
    E(adds_reg, 3, 3, 5)
    E(strh_imm, 1, 3, 32)
    E(adds_imm8, 2, 1)
    E(cmp_imm, 2, 16)
    E(b_cond, "ld_l", "lo")
    E(b, "ld_x")
    a.label("ld_p")
    E(movs_imm, 1, UI_DIM_FIX if ui else COL_DIM)
    E(lsls_imm, 0, 6, 24)
    E(b_cond, "ld_f", "pl")
    E(movs_imm, 1, COL_FIX)
    a.label("ld_f")
    E(strh_imm, 1, 5, 2 * (16 + PAD_FIX))
    E(movs_imm, 1, UI_DIM_ON if ui else COL_DIM)
    E(lsrs_imm, 0, 6, 9)
    E(b_cond, "ld_h", "lo")
    E(movs_imm, 1, COL_ON)
    a.label("ld_h")
    E(strh_imm, 1, 5, 2 * (16 + PAD_HOLD))
    a.label("ld_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr, ui=False):
    """The step views' slots 0 / 1, the Micro Step views' slot 0, the head of the LED calls.  Needs rhstate ram2, rhrec, countin."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]                 # noqa: E731
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    assert "c_rram" in report["rhstate"]["labels"], "stepgate needs rhstate ram2 (RH41)"
    L = dict(c_rram=lab("rhstate", "c_rram"), c_rrt=lab("rhrec", "c_rrt"), c_ciok=lab("countin", "c_ciok"),
             c_cishift=lab("countin", "c_cishift"))
    prev = dict(press=u(SV_VT) & ~1, rel=u(SV_VT + 4) & ~1, mpad=u(MV_VT) & ~1, ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code, labels = arm_code(base_addr, L, prev, ui)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch_word(img, SV_VT, prev["press"] | 1, labels["c_sgpress"] | 1)
    rhbuild.patch_word(img, SV_VT + 4, prev["rel"] | 1, labels["c_sgrel"] | 1)
    rhbuild.patch_word(img, MV_VT, prev["mpad"] | 1, labels["c_sgmpad"] | 1)
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_sgled"]))
    report["stepgate"] = dict(prev={k: hex(v) for k, v in prev.items()}, block=hex(BLK), ram=hex(rhstate.ST2 + O),
                              labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
