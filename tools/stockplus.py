"""Stock+ knob page of a track: pitch envelope and pitch LFO on K1-K4 (MIT; the first part of the Stock+ sampler mode, for the Circuit Rhythm
5706).  The user (2026-10-21): «the new sample version has all stock rythm functions, plus some 8 functions on shift»; «in stock, shift+knob is
fine control»; «Use the page toggle: press the track's button again to flip to the Stock+ knob page; Shift stays fine control».

The stock of the Rhythm (emulated on the RAM dump, $TMP checks of 2026-10-21):
  * a track button (ids 0-7) in the track views re-selects the track and its view mode (0x0804D662 / 0x0804D6B6) every time: pressed again it
    changes nothing (the bytes that seem to move are the double copies of the stores; the LEDs stay);
  * a knob: 0x0803DDE0(ctrl, knob, delta) -> slot 4 of the active view; the container's (0x20048B9C, vtable 0x080678DC) hands it to the subview
    of 0x0804DB78 (none in the Sidechain mode, [+ 0x264] = 8); the knob's value is a halfword 0..16383 (the parameter = value >> 7): a turn
    moves it by 128 a click, by 4 with Shift (fine control);
  * the selected track = 0x0805800E(container); Shift = p0 of [ctrl + 0xC]; the held buttons = [ctrl + 0xA0] (Clear 23, Duplicate 24);
  * the track buttons' LEDs: 32 + t and 40 + t of the frame (0x4B the selected one, 0x09 the others); the knob LEDs 60-67; 0x01 white;
    0x151 = white for the knob LEDs.
Ours:
  * the second press of the selected track's button (track views on the screen, not the Sidechain mode, no Shift / Clear / Duplicate held)
    flips that track's knob page: stock / Stock+ (rhstate "stockplus" + 0, bit t; until power-off); the stock's press is run as well;
  * on the Stock+ page the container's knob slot (head of the chain) takes the knobs: K1 pitch envelope amount (centre = none, +- 24 semitones),
    K2 its decay (5 ms .. 4 s, to 10 %), K3 LFO rate (0.05 .. 30 Hz), K4 LFO depth (0 .. 24 semitones); 128 a click, 4 with Shift; Clear held +
    a knob = its default; K5-K8 nothing yet (dark);
  * the values (14 bits, as the stock's knobs) travel with the project in the record's tail (rhrec "stockplus": "SP", a check byte, 8 tracks x
    8 halfwords; a project without it = the defaults: no modulation); Clear + a track button (track views) = that track's defaults; Duplicate +
    track A, then track B = A's values copied to B (as trkcopy does with the stock's parameters); without our block both write nothing (every
    track already has the defaults);
  * the LED task (after the chain): on the Stock+ page K1-K4 white with their value as brightness (kbright's overlay; K1 |v - 64| x 2), K5-K8
    dark, the track's button blinking white (256 ms); and the DSP: each frame one track in turn plus every track a knob changed, its four words
    into core 1 (tools/pitchmod.py: Y:$1320 / $1328 / $1330 / $1338 + t) with 0x08031200(1, word << 8, $8000 | address) (the RD4 command that
    worked on the device, RD6), only while core 0 / 1 hold the mode 0 program (cthresh's state READY: an upload of mode 0 seen); the round
    writes again what a lost write or an upload (core 1 clears Y:$400..$13FF at its start) undid.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, ldr_sp, adds_imm8, adds_reg, b, b_cond, b_w, bl, cmp_imm, cmp_reg, eors_reg, h, ldr_imm, ldrb_imm, ldrb_reg, ldrh_imm,  # noqa: E402
                   lsls_imm, lsls_reg, lsrs_imm, lsrs_reg, mov_reg, movs_imm, movt, movw, muls, orrs_reg, pop_list, push_list, raw, strb_imm,
                   strh_imm, subs_imm8, subs_reg, tst_reg, ldrb_w, strb_w, strh_w_imm, bics_reg)
import countin as CI  # noqa: E402
import cthresh as TH  # noqa: E402
import pitchmod as PM  # noqa: E402
import rhrec  # noqa: E402
import rhstate  # noqa: E402
import sckn as SK  # noqa: E402

CTRL = CI.CTRL
CONT, CONT_VT, O_MODE, MODE_SC = SK.CONT, SK.CONT_VT, SK.O_MODE, SK.MODE_SC
SLOT_KNOB = SK.SLOT_KNOB
SELTRK, SUBVIEW = 0x0805800E, 0x0804DB78
O_HELD, BIT_CLEAR, BIT_DUP = 0xA0, 23, 24
WR16 = TH.WR16
HAL_TICK = CI.HAL_TICK
LED_TRK0, LED_TRK1, LED_KNOB0 = 32, 40, 60
COL_BLINK, COL_KNOB = 0x01, 0x151
BLK, BLK_LEN = rhrec.OFF["stockplus"]
O_ST, ST_LEN = rhstate.OFF["stockplus"]               # + 0 the tracks on the Stock+ page, + 1 the tracks to push, + 2 the round, + 3 Duplicate's source + 1
O_KB, O_TH = rhstate.OFF["kbright"][0], rhstate.OFF["cthresh"][0] + 1
K_MASK, K_VAL, K_CODE = 0, 1, 10
MARK0, MARK1, CHECK = ord("S"), ord("P"), 0xA5
NPAR, NTRK = 8, 8
FULL, STEP, FINE = 16383, 128, 4
DEF = (8192, 8192, 8192, 0, 0, 0, 0, 0)               # K1 none, K2 / K3 the middle, K4 no depth; K5-K8 for later
UPD = 1500 / 8                                        # the voices' pitch updates a second (RD6 on the device: 1 500 blocks / s, one voice a block)
A_SCALE, L_SCALE = 192, 96                            # (v - 8192) x 192: +- 24 semitones ($180000); v x 96: 24 semitones at the top
T_MIN, T_MAX = 0.005, 4.0
HZ_MIN, HZ_MAX = 0.05, 30.0
INV = SK.INV
assert BLK_LEN == 4 + 2 * NPAR * NTRK and ST_LEN == 4 and 0 < O_ST - O_TH < 256 and 0 < O_ST - O_KB < 256


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def decay_table():
    out = []
    for i in range(129):
        n = max(T_MIN * (T_MAX / T_MIN) ** (i / 128) * UPD, 1.0)
        out.append(min(round(0.1 ** (1 / n) * (1 << 23)), 0x7FFFFF))
    return out


def rate_table():
    return [round(HZ_MIN * (HZ_MAX / HZ_MIN) ** (i / 128) / UPD * (1 << 24)) for i in range(129)]


def words(v):
    """the four core 1 words of a track's values (as c_spdsp computes them): for the tests"""
    def interp(t, x):
        i, f = x >> 7, x & 127
        return t[i] + ((t[i + 1] - t[i]) * f >> 7)
    return [((v[0] - 8192) * A_SCALE) & 0xFFFFFF, interp(decay_table(), v[1]), interp(rate_table(), v[2]), v[3] * L_SCALE]


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit
    zc = [0]

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    def bc(target, cond):
        zc[0] += 1
        n = f"_p{zc[0]}"
        E(b_cond, n, INV[cond])
        E(b, target)
        a.label(n)

    t_dec = base
    E(raw, b"".join(w.to_bytes(4, "little") for w in decay_table()))
    t_rate = base + 4 * 129
    E(raw, b"".join(w.to_bytes(4, "little") for w in rate_table()))
    t_def = base + 8 * 129
    E(raw, b"".join(v.to_bytes(2, "little") for v in DEF))

    # ---- c_spst() -> r0 = our state (rhstate), 0 without our RAM; clobbers r1-r3
    a.label("c_spst")
    E(push_list, [4], lr=True)
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ss_x", "eq")
    E(adds_imm8, 0, O_ST)
    a.label("ss_x")
    E(pop_list, [4], pc=True)

    # ---- c_spblk() -> r0 = our block in the record's tail, 0 without the record; clobbers r1-r3
    a.label("c_spblk")
    E(push_list, [4], lr=True)
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "sb_x", "eq")
    E(movw, 1, BLK)
    E(adds_reg, 0, 0, 1)
    a.label("sb_x")
    E(pop_list, [4], pc=True)

    # ---- c_spsum(r0 = block) -> r0 = the check byte of its values; clobbers r1-r3
    a.label("c_spsum")
    E(adds_imm8, 0, 4)
    E(movs_imm, 1, 2 * NPAR * NTRK)
    E(movs_imm, 2, CHECK)
    a.label("su_l")
    E(ldrb_imm, 3, 0, 0)
    E(eors_reg, 2, 3)
    E(adds_imm8, 0, 1)
    E(subs_imm8, 1, 1)
    E(b_cond, "su_l", "ne")
    E(mov_reg, 0, 2)
    E(raw, h(0x4770))                                                     # bx lr

    # ---- c_spok(r0 = block) -> r0 = 1 when it holds our values; clobbers r1-r3
    a.label("c_spok")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(ldrb_imm, 1, 4, 0)
    E(cmp_imm, 1, MARK0)
    E(b_cond, "ok_0", "ne")
    E(ldrb_imm, 1, 4, 1)
    E(cmp_imm, 1, MARK1)
    E(b_cond, "ok_0", "ne")
    E(bl, "c_spsum")
    E(ldrb_imm, 1, 4, 2)
    E(cmp_reg, 0, 1)
    E(b_cond, "ok_0", "ne")
    E(movs_imm, 0, 1)
    E(pop_list, [4], pc=True)
    a.label("ok_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)

    # ---- c_spval(r0 = track, r1 = knob) -> r0 = its value (the default without our block); clobbers r1-r3
    a.label("c_spval")
    E(push_list, [4, 5, 6], lr=True)
    E(lsls_imm, 4, 0, 3)
    E(adds_reg, 4, 4, 1)
    E(lsls_imm, 4, 4, 1)                                                  # r4 = 2 (8 t + k)
    E(lsls_imm, 6, 1, 1)                                                  # r6 = 2 k
    E(bl, "c_spblk")
    E(cmp_imm, 0, 0)
    E(b_cond, "sv_d", "eq")
    E(mov_reg, 5, 0)
    E(bl, "c_spok")
    E(cmp_imm, 0, 0)
    E(b_cond, "sv_d", "eq")
    E(adds_reg, 5, 5, 4)
    E(ldrh_imm, 0, 5, 4)
    E(pop_list, [4, 5, 6], pc=True)
    a.label("sv_d")
    imm32(0, t_def)
    E(adds_reg, 0, 0, 6)
    E(ldrh_imm, 0, 0, 0)
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_spput(r0 = track, r1 = knob, r2 = value): into our block (made with the defaults if missing), its check byte; clobbers r0-r3
    a.label("c_spput")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(lsls_imm, 4, 0, 3)
    E(adds_reg, 4, 4, 1)
    E(lsls_imm, 4, 4, 1)                                                  # r4 = 2 (8 t + k)
    E(mov_reg, 6, 2)
    E(bl, "c_spblk")
    E(cmp_imm, 0, 0)
    E(b_cond, "sp_x", "eq")
    E(mov_reg, 5, 0)
    E(bl, "c_spok")
    E(cmp_imm, 0, 0)
    E(b_cond, "sp_w", "ne")
    E(movs_imm, 0, MARK0)                                                 # a new block: every track's defaults
    E(strb_imm, 0, 5, 0)
    E(movs_imm, 0, MARK1)
    E(strb_imm, 0, 5, 1)
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 5, 3)
    E(movs_imm, 7, 0)
    a.label("sp_i")
    imm32(0, t_def)
    E(movs_imm, 1, 2 * NPAR - 1)
    E(raw, h(0x4039))                                                     # ands r1, r7: (2 i) mod 16 = 2 k
    E(adds_reg, 0, 0, 1)
    E(ldrh_imm, 0, 0, 0)
    E(adds_reg, 1, 5, 7)
    E(strh_imm, 0, 1, 4)
    E(adds_imm8, 7, 2)
    E(cmp_imm, 7, 2 * NPAR * NTRK)
    E(b_cond, "sp_i", "lo")
    a.label("sp_w")
    E(adds_reg, 1, 5, 4)
    E(strh_imm, 6, 1, 4)
    E(mov_reg, 0, 5)
    E(bl, "c_spsum")
    E(strb_imm, 0, 5, 2)
    a.label("sp_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)

    # ---- c_spdirty(r0 = track): to push; clobbers r0-r3
    a.label("c_spdirty")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_spst")
    E(cmp_imm, 0, 0)
    E(b_cond, "sd_x", "eq")
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(ldrb_imm, 2, 0, 1)
    E(orrs_reg, 2, 1)
    E(strb_imm, 2, 0, 1)
    a.label("sd_x")
    E(pop_list, [4], pc=True)

    # ---- c_spreset(r0 = track): its defaults; clobbers r0-r3
    a.label("c_spreset")
    E(push_list, [3, 4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_spvalid")
    E(cmp_imm, 0, 0)
    E(b_cond, "sr_x", "eq")                                               # no block: already the defaults (nothing written)
    E(movs_imm, 5, 0)
    a.label("sr_l")
    imm32(2, t_def)
    E(lsls_imm, 1, 5, 1)
    E(adds_reg, 2, 2, 1)
    E(ldrh_imm, 2, 2, 0)
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, "c_spput")
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, NPAR)
    E(b_cond, "sr_l", "lo")
    E(mov_reg, 0, 4)
    E(bl, "c_spdirty")
    a.label("sr_x")
    E(pop_list, [3, 4, 5], pc=True)

    # ---- c_spvalid() -> r0 = 1 when the project holds our block; clobbers r1-r3
    a.label("c_spvalid")
    E(push_list, [4], lr=True)
    E(bl, "c_spblk")
    E(cmp_imm, 0, 0)
    E(b_cond, "vl_x", "eq")
    E(bl, "c_spok")
    a.label("vl_x")
    E(pop_list, [4], pc=True)

    # ---- c_spview() -> r0 = the selected track when the track views (not the Sidechain mode) are on the screen, else 8; clobbers r1-r3
    a.label("c_spview")
    E(push_list, [4], lr=True)
    imm32(0, CTRL)
    E(ldr_imm, 1, 0, 0x7C)
    imm32(0, CONT)
    E(cmp_reg, 0, 1)
    E(b_cond, "vw_n", "ne")
    E(ldr_imm, 1, 0, 0)
    imm32(2, CONT_VT)
    E(cmp_reg, 1, 2)
    E(b_cond, "vw_n", "ne")
    E(ldrb_w, 1, 0, O_MODE)
    E(cmp_imm, 1, MODE_SC)
    E(b_cond, "vw_n", "eq")
    E(bl, SELTRK)
    E(cmp_imm, 0, NTRK)
    E(b_cond, "vw_x", "lo")
    a.label("vw_n")
    E(movs_imm, 0, NTRK)
    a.label("vw_x")
    E(pop_list, [4], pc=True)

    # ---- c_spheld() -> r0 = the held buttons; clobbers r1
    a.label("c_spheld")
    imm32(1, CTRL + O_HELD)
    E(ldr_imm, 0, 1, 0)
    E(raw, h(0x4770))

    # ---- c_spshift() -> r0 = Shift held; clobbers r1-r3
    a.label("c_spshift")
    E(push_list, [4], lr=True)
    imm32(0, CTRL)
    E(ldr_imm, 0, 0, 0xC)
    E(movs_imm, 1, 0)
    E(bl, CI.PARAM_GET)
    E(ldrb_imm, 0, 0, 0)
    E(pop_list, [4], pc=True)

    # ---- c_spbtn (the head of the button chain: r0 = ctrl, r1 = id)
    a.label("c_spbtn")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)                          # 8 words
    E(cmp_imm, 1, NTRK)
    bc("bt_p", "hs")
    E(mov_reg, 4, 1)                                                      # r4 = the track of the button
    E(bl, "c_spst")
    E(cmp_imm, 0, 0)
    bc("bt_p", "eq")
    E(mov_reg, 5, 0)                                                      # r5 = our state
    E(bl, "c_spheld")
    E(mov_reg, 6, 0)                                                      # r6 = the held buttons
    E(lsls_imm, 0, 6, 31 - BIT_DUP)
    E(b_cond, "bt_nd", "pl")
    E(lsls_imm, 0, 6, 31 - BIT_CLEAR)
    bc("bt_p", "mi")                                                      # Clear and Duplicate: nothing of ours
    E(ldrb_imm, 7, 5, 3)                                                  # Duplicate: the source + 1
    E(cmp_imm, 7, 0)
    E(b_cond, "bt_cp", "ne")
    E(adds_imm8, 4, 1)
    E(strb_imm, 4, 5, 3)                                                  # the first button = the source
    E(b, "bt_p")
    a.label("bt_cp")
    E(subs_imm8, 7, 1)
    E(cmp_reg, 7, 4)
    bc("bt_p", "eq")
    E(bl, "c_spvalid")
    E(cmp_imm, 0, 0)
    bc("bt_p", "eq")                                                      # no block: every track has the defaults
    E(movs_imm, 6, 0)                                                     # r6 = the knob
    a.label("bt_cl")
    E(mov_reg, 0, 7)
    E(mov_reg, 1, 6)
    E(bl, "c_spval")
    E(mov_reg, 2, 0)
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 6)
    E(bl, "c_spput")
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, NPAR)
    E(b_cond, "bt_cl", "lo")
    E(mov_reg, 0, 4)
    E(bl, "c_spdirty")
    E(b, "bt_p")
    a.label("bt_nd")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 5, 3)                                                  # no Duplicate: no source
    E(lsls_imm, 0, 6, 31 - BIT_CLEAR)
    E(b_cond, "bt_nc", "pl")
    E(bl, "c_spview")                                                     # Clear + the button, track views on the screen: the defaults
    E(cmp_imm, 0, NTRK)
    bc("bt_p", "hs")
    E(mov_reg, 0, 4)
    E(bl, "c_spreset")
    E(b, "bt_p")
    a.label("bt_nc")
    E(bl, "c_spshift")
    E(cmp_imm, 0, 0)
    bc("bt_p", "ne")
    E(bl, "c_spview")
    E(cmp_reg, 0, 4)
    bc("bt_p", "ne")                                                      # not the selected track (or not the track views)
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(ldrb_imm, 0, 5, 0)
    E(eors_reg, 0, 1)
    E(strb_imm, 0, 5, 0)                                                  # the page flipped
    a.label("bt_p")
    E(raw, popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    E(b_w, prev["btn"])

    # ---- c_spknob (the container's slot 4, the head of its chain: r0 = container, r1 = knob, r2 = delta)
    a.label("c_spknob")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(cmp_imm, 1, NPAR)
    bc("kn_p", "hs")
    E(bl, "c_spview")
    E(cmp_imm, 0, NTRK)
    bc("kn_p", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the track
    E(bl, "c_spst")
    E(cmp_imm, 0, 0)
    bc("kn_p", "eq")
    E(ldrb_imm, 0, 0, 0)
    E(lsrs_reg, 0, 4)
    E(lsls_imm, 0, 0, 31)
    bc("kn_p", "eq")                                                      # the stock page
    imm32(0, CONT)
    E(bl, SUBVIEW)
    E(cmp_imm, 0, 0)
    bc("kn_p", "eq")                                                      # no knobs in this mode
    E(ldr_sp, 5, 4)                                                       # r5 = the knob
    E(cmp_imm, 5, 4)
    bc("kn_x", "hs")                                                      # K5-K8: nothing yet
    E(bl, "c_spheld")
    E(lsls_imm, 0, 0, 31 - BIT_CLEAR)
    E(b_cond, "kn_t", "pl")
    imm32(0, t_def)                                                       # Clear + the knob: its default
    E(lsls_imm, 1, 5, 1)
    E(adds_reg, 0, 0, 1)
    E(ldrh_imm, 6, 0, 0)
    E(b, "kn_w")
    a.label("kn_t")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, "c_spval")
    E(mov_reg, 6, 0)                                                      # r6 = the value
    E(bl, "c_spshift")
    E(movs_imm, 7, STEP)
    E(cmp_imm, 0, 0)
    E(b_cond, "kn_s", "eq")
    E(movs_imm, 7, FINE)
    a.label("kn_s")
    E(ldr_sp, 0, 8)                                                       # the delta
    E(muls, 7, 0)
    E(adds_reg, 6, 6, 7)
    E(cmp_imm, 6, 0)
    E(b_cond, "kn_h", "ge")
    E(movs_imm, 6, 0)
    a.label("kn_h")
    E(movw, 0, FULL)
    E(cmp_reg, 6, 0)
    E(b_cond, "kn_w", "le")
    E(mov_reg, 6, 0)
    a.label("kn_w")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(mov_reg, 2, 6)
    E(bl, "c_spput")
    E(mov_reg, 0, 4)
    E(bl, "c_spdirty")
    a.label("kn_x")
    E(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)
    a.label("kn_p")
    E(raw, popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    E(b_w, prev["knob"])

    # ---- c_spint(r0 = table, r1 = value) -> r0 = the table at value / 128, interpolated; clobbers r1-r3
    a.label("c_spint")
    E(lsrs_imm, 2, 1, 7)
    E(lsls_imm, 2, 2, 2)
    E(adds_reg, 0, 0, 2)
    E(ldr_imm, 2, 0, 0)
    E(ldr_imm, 3, 0, 4)
    E(subs_reg, 3, 3, 2)
    E(lsls_imm, 1, 1, 25)
    E(lsrs_imm, 1, 1, 25)
    E(muls, 3, 1)
    E(lsrs_imm, 3, 3, 7)
    E(adds_reg, 0, 2, 3)
    E(raw, h(0x4770))

    # ---- c_spw(r0 = word, r1 = Y address of core 1): 0x08031200(1, word << 8, $8000 | address); clobbers r0-r3, r12
    a.label("c_spw")
    E(push_list, [4], lr=True)
    E(lsls_imm, 0, 0, 8)
    E(mov_reg, 2, 1)
    E(movw, 1, 0x8000)
    E(orrs_reg, 2, 1)
    E(mov_reg, 1, 0)
    E(movs_imm, 0, 1)
    E(bl, WR16)
    E(pop_list, [4], pc=True)

    # ---- c_spdsp(r0 = track): its four words into core 1; clobbers r0-r3, r12
    a.label("c_spdsp")
    E(push_list, [3, 4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(movs_imm, 1, 0)
    E(bl, "c_spval")
    E(movw, 1, 8192)
    E(subs_reg, 0, 0, 1)
    E(movs_imm, 1, A_SCALE)
    E(muls, 0, 1)
    E(movw, 1, PM.Y_BASE + PM.OFF_A)
    E(adds_reg, 1, 1, 4)
    E(bl, "c_spw")
    for k, tab, off in ((1, t_dec, PM.OFF_D), (2, t_rate, PM.OFF_R)):
        E(mov_reg, 0, 4)
        E(movs_imm, 1, k)
        E(bl, "c_spval")
        E(mov_reg, 1, 0)
        imm32(0, tab)
        E(bl, "c_spint")
        E(movw, 1, PM.Y_BASE + off)
        E(adds_reg, 1, 1, 4)
        E(bl, "c_spw")
    E(mov_reg, 0, 4)
    E(movs_imm, 1, 3)
    E(bl, "c_spval")
    E(movs_imm, 1, L_SCALE)
    E(muls, 0, 1)
    E(movw, 1, PM.Y_BASE + PM.OFF_L)
    E(adds_reg, 1, 1, 4)
    E(bl, "c_spw")
    E(pop_list, [3, 4, 5], pc=True)

    # ---- c_spled (the LED task's calls: ctrl, frame): the chain, then the DSP's round and the Stock+ page's LEDs
    a.label("c_spled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)                                                      # r5 = the frame
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(bl, "c_spst")
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(mov_reg, 6, 0)                                                      # r6 = our state
    E(bl, "c_spheld")
    E(lsls_imm, 0, 0, 31 - BIT_DUP)
    E(b_cond, "ld_h", "mi")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 6, 3)                                                  # Duplicate let go: no source
    a.label("ld_h")
    E(mov_reg, 0, 6)
    E(subs_imm8, 0, O_ST - O_TH)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, TH.READY)
    E(b_cond, "ld_v", "ne")                                               # not the mode 0 program: no DSP writes
    E(ldrb_imm, 7, 6, 2)
    E(adds_imm8, 7, 1)
    E(movs_imm, 0, NTRK - 1)
    E(raw, h(0x4007))                                                     # ands r7, r0
    E(strb_imm, 7, 6, 2)                                                  # the round's track
    E(movs_imm, 0, 1)
    E(lsls_reg, 0, 7)
    E(ldrb_imm, 7, 6, 1)
    E(orrs_reg, 7, 0)                                                     # r7 = the tracks to push
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 6, 1)
    E(movs_imm, 4, 0)
    a.label("ld_d")
    E(mov_reg, 0, 7)
    E(lsrs_reg, 0, 4)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "ld_dn", "eq")
    E(mov_reg, 0, 4)
    E(bl, "c_spdsp")
    a.label("ld_dn")
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, NTRK)
    E(b_cond, "ld_d", "lo")
    a.label("ld_v")
    E(bl, "c_spview")
    E(cmp_imm, 0, NTRK)
    bc("ld_x", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the track
    E(ldrb_imm, 0, 6, 0)
    E(lsrs_reg, 0, 4)
    E(lsls_imm, 0, 0, 31)
    bc("ld_x", "eq")                                                      # the stock page
    E(mov_reg, 7, 6)
    E(subs_imm8, 7, O_ST - O_KB)                                          # r7 = kbright's overlay
    E(movs_imm, 0, 0x0F)
    E(strb_imm, 0, 7, K_MASK)
    for k in range(4):
        E(mov_reg, 0, 4)
        E(movs_imm, 1, k)
        E(bl, "c_spval")
        E(lsrs_imm, 0, 0, 7)                                              # 0..127
        if k == 0:
            E(subs_imm8, 0, 64)
            E(b_cond, f"lk_p{k}", "ge")
            E(raw, h(0x4240))                                             # rsbs r0, r0, #0
            a.label(f"lk_p{k}")
            E(lsls_imm, 0, 0, 1)
            E(cmp_imm, 0, 127)
            E(b_cond, f"lk_c{k}", "le")
            E(movs_imm, 0, 127)
            a.label(f"lk_c{k}")
        E(strb_imm, 0, 7, K_VAL + k)
        imm32(0, COL_KNOB)
        E(strh_imm, 0, 7, K_CODE + 2 * k)
        E(strh_w_imm, 0, 5, 2 * (LED_KNOB0 + k))
    E(movs_imm, 0, 0)
    for k in range(4, 8):
        E(strh_w_imm, 0, 5, 2 * (LED_KNOB0 + k))
    imm32(0, HAL_TICK)
    E(ldr_imm, 0, 0, 0)
    E(lsls_imm, 0, 0, 23)                                                 # bit 8 of the tick
    E(b_cond, "ld_x", "pl")
    E(movs_imm, 0, COL_BLINK)
    E(lsls_imm, 1, 4, 1)
    E(adds_reg, 1, 5, 1)
    E(strh_w_imm, 0, 1, 2 * LED_TRK0)
    E(strh_w_imm, 0, 1, 2 * LED_TRK1)
    a.label("ld_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; the head of the button chain, the head of the container's knob slot, the LED task calls (outermost).  pitchmod's
    core 1 code (tools/pitchmod.py, without dspload) must be in the build too."""
    import struct
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]
    lab = lambda m, k: int(report[m]["labels"][k], 16)
    for need in ("kbright", "cthresh", "pitchmod"):
        assert need in report, f"stockplus needs {need}"
    L = dict(c_rst=lab("rhstate", "c_rst"), c_rrt=lab("rhrec", "c_rrt"), c_ciok=lab("countin", "c_ciok"))
    prev = dict(btn=rhbuild.bw_target(img, CI.BTN_ENTRY), knob=u(SLOT_KNOB) & ~1, ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, CI.BTN_ENTRY, f"b.w #{prev['btn']:#x}", b_w(CI.BTN_ENTRY, labels["c_spbtn"]))
    rhbuild.patch_word(img, SLOT_KNOB, prev["knob"] | 1, labels["c_spknob"] | 1)
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_spled"]))
    report["stockplus"] = dict(prev={k: hex(v) for k, v in prev.items()}, tables=hex(base_addr),
                               labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
