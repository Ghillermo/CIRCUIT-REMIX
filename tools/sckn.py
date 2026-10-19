"""Knobs for the side-chain and the master compressor in the Sidechain view (MIT; CIRCUIT-HACKS' sckn of SC40.1 and the compressor knobs of
fxsess (SC40.9), for the Circuit Rhythm 5706).  The user (2026-10-19): «¿Existen los valores de sidechain en memoria? si es así, generar knobs y
guardarlos como en Tracks»; the master compressor's NRPNs (the Rhythm's MIDI reference): 1:22 on / off, 1:23 attack, 1:24 release, 1:25 envelope
follow, 1:26 soft clip.

The stock of the Rhythm (read in the firmware and on the RAM dump, emulated):
  * the Sidechain view = Shift + FX: the track views' container 0x20048B9C (vtable 0x080678DC) with [+ 0x264] = 8; the container's knob slot
    (4, 0x0804D826) hands knobs to the subview of 0x0804DB78, which is none in that mode (the knobs do nothing, their LEDs are dark); the pads
    reach slot 0 of the Sidechain object 0x20048E90 (vtable 0x08067F14, 0x0805574A): pads 0-7 the source
    ([+ 0x2C], the object 0x20049048), 16-31 the presets of two tracks a page (t = p0 of [+ 0x30] x 2 + row); a preset pad tells the source
    object its track (0x0805BFD2: [[+ 0x2C] + 0x14] = t): «the chosen track» of the view;
  * a track's side-chain = parameters of the group 0x10 + t: 0x14 the source, 0x15..0x18 attack, hold, decay, depth (0..127); a preset is a number
    per track (the stores [0x20042354 + 0x10 + 4 t]) whose listener (0x08036DF4) writes the four values of the table 0x20003774 through the setter
    0x08031A38(0x20010E10, group, index, value) (the store, the DSP, MIDI out); the getter 0x08046410(group, index) -> value;
    the project keeps the preset number (seen on the unit: docs/PORTADO.md), not the four values;
  * the master group 0x21 (0x08030D12 sends it to the DSP): 2 the compressor on / off, 3 attack, 4 release, 6 soft clip (the second switch of the
    Tracks' notes), 7 the output gain; 5 (envelope follow) is never sent to the DSP: no knob for it.

Ours:
  * K1..K4 = attack, hold, decay, depth of the chosen track's side-chain; K6 = soft clip (right on, left off); K7 / K8 = the compressor's attack /
    release; K5 nothing; all through the stock's setter; LEDs: K1-K4 in the track's colour (the Mixer's knob colours 0x149 + t), K6 white when on
    (dim when off), K7 / K8 white;
  * the values travel with the project in the record's tail (rhrec "sckn"): "SK", a sum, the tracks whose four values are ours (bit t), 8 x 4
    values, the compressor's flag and its three values; a preset pad gives the track back to the stock's preset (its bit cleared);
  * after a load (the end of «apply the record», 0x080379AE, in front of patchain's) the LED task writes them again once (rhstate "sckn").
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b, b_cond, b_w, bl, cmp_imm, cmp_reg, eors_reg, h, ldr_imm, ldrb_imm, ldrb_reg, lsls_imm,  # noqa: E402
                   lsls_reg, lsrs_reg, mov_reg, movs_imm, movt, movw, orrs_reg, pop_list, push_list, raw, strb_imm, strb_reg, strh_imm,
                   subs_imm8, bics_reg, ldrb_w, strb_w, strh_w_imm)
import countin as CI  # noqa: E402
import patchain as PC  # noqa: E402
import rhrec  # noqa: E402
import rhstate  # noqa: E402

CTRL = CI.CTRL
SC_OBJ, SC_VT = 0x20048E90, 0x08067F14
CONT_VT = 0x080678DC
SLOT_PAD, SLOT_KNOB = SC_VT, CONT_VT + 0x10
O_SRC, SRC_TRACK = 0x2C, 0x14
CONT, O_MODE, MODE_SC = 0x20048B9C, 0x264, 8
SETTER, SET_OBJ, GETTER = 0x08031A38, 0x20010E10, 0x08046410
GRP_TRACK, IDX_SC0 = 0x10, 0x15
GRP_MASTER, COMP_IDX = 0x21, (6, 3, 4)          # K6 soft clip, K7 attack, K8 release
LOAD_TAIL = PC.LOAD_TAIL
LED_CALLS = CI.LED_CALLS
LED_KNOB0 = 60
COL_TRACK0, COL_WHITE, COL_DIM = 0x149, 0x151, 0x09
TAG = 0xC5
BLK, BLK_LEN = rhrec.OFF["sckn"]
B_SUM, B_BITS, B_VAL, B_COMP, B_CVAL = 2, 3, 4, 36, 37
SUM_XOR = 0x5A
INV = dict(eq="ne", ne="eq", lo="hs", hs="lo", hi="ls", ls="hi", ge="lt", lt="ge", gt="le", le="gt", mi="pl", pl="mi")
assert BLK_LEN == 40
BRIGHT = False                                  # RH22 (install(bright=True)): the knobs' values as brightness through kbright's overlay


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))
def pushw(regs, lr=False): return h(0xE92D) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit
    zc = [0]

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    def bc(target, cond):
        zc[0] += 1
        n = f"_s{zc[0]}"
        E(b_cond, n, INV[cond])
        E(b, target)
        a.label(n)

    t_cidx = base
    E(raw, bytes(COMP_IDX) + b"\0")

    # ---- c_skblk() -> r0 = our block in the record's tail, 0 without a record; clobbers r1-r3
    a.label("c_skblk")
    E(push_list, [4], lr=True)
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "kb_x", "eq")
    E(adds_imm8, 0, BLK)
    a.label("kb_x")
    E(pop_list, [4], pc=True)

    # ---- c_sksum(r0 = block) -> r0 = the sum of bytes 3..39; clobbers r1, r2
    a.label("c_sksum")
    E(movs_imm, 1, B_BITS)
    E(movs_imm, 2, SUM_XOR)
    a.label("ks_l")
    E(ldrb_reg, 3, 0, 1)
    E(adds_reg, 2, 2, 3)
    E(adds_imm8, 1, 1)
    E(cmp_imm, 1, BLK_LEN)
    E(b_cond, "ks_l", "lo")
    E(movs_imm, 0, 0xFF)
    E(raw, h(0x4010))                                                     # ands r0, r2
    E(raw, h(0x4770))

    # ---- c_skok(r0 = block) -> r0 = 1 when it holds our values (the mark and the sum); clobbers r1-r3
    a.label("c_skok")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(ldrb_imm, 1, 4, 0)
    E(cmp_imm, 1, ord("S"))
    E(b_cond, "ko_0", "ne")
    E(ldrb_imm, 1, 4, 1)
    E(cmp_imm, 1, ord("K"))
    E(b_cond, "ko_0", "ne")
    E(bl, "c_sksum")
    E(ldrb_imm, 1, 4, B_SUM)
    E(cmp_reg, 0, 1)
    E(b_cond, "ko_0", "ne")
    E(movs_imm, 0, 1)
    E(pop_list, [4], pc=True)
    a.label("ko_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)

    # ---- c_skfix(r0 = block): its sum; clobbers r1-r3
    a.label("c_skfix")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_sksum")
    E(strb_imm, 0, 4, B_SUM)
    E(pop_list, [4], pc=True)

    # ---- c_skget(r0 = group, r1 = index) -> r0 = the value (0..127); clobbers r1-r3
    a.label("c_skget")
    E(push_list, [4], lr=True)
    E(bl, GETTER)
    E(movs_imm, 1, 0x7F)
    E(raw, h(0x4008))                                                     # ands r0, r1
    E(pop_list, [4], pc=True)

    # ---- c_skset(r1 = group, r2 = index, r3 = value): the stock's setter (store, DSP, MIDI); clobbers r0-r3, r12
    a.label("c_skset")
    imm32(0, SET_OBJ)
    E(b_w, SETTER)

    # ---- c_skknob (the container's slot 4: view, knob, delta): in the Sidechain view ours, else the stock's
    a.label("c_skknob")
    imm32(3, O_MODE)
    E(raw, h(0x5CC3))                                                     # ldrb r3, [r0, r3]
    E(cmp_imm, 3, MODE_SC)
    E(b_cond, "kk_in", "eq")
    E(b_w, prev["knob"])
    a.label("kk_in")
    imm32(0, SC_OBJ)
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(mov_reg, 6, 2)
    E(cmp_imm, 5, 8)
    bc("kk_f", "hs")
    E(cmp_imm, 5, 4)
    bc("kk_f", "eq")
    E(cmp_imm, 6, 0)
    bc("kk_f", "eq")
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("kk_f", "eq")
    E(bl, "c_skblk")
    E(cmp_imm, 0, 0)
    bc("kk_f", "eq")
    E(mov_reg, 7, 0)                                                      # r7 = the block
    E(bl, "c_skok")
    E(cmp_imm, 0, 0)
    E(b_cond, "kk_ok", "ne")
    E(movs_imm, 0, 0)                                                     # a new block
    E(movs_imm, 1, 0)
    a.label("kk_z")
    E(strb_reg, 0, 7, 1)
    E(adds_imm8, 1, 1)
    E(cmp_imm, 1, BLK_LEN)
    E(b_cond, "kk_z", "lo")
    E(movs_imm, 0, ord("S"))
    E(strb_imm, 0, 7, 0)
    E(movs_imm, 0, ord("K"))
    E(strb_imm, 0, 7, 1)
    a.label("kk_ok")
    E(cmp_imm, 5, 4)
    bc("kk_c", "hi")
    # K1..K4: the chosen track's side-chain
    E(ldr_imm, 0, 4, O_SRC)
    E(ldrb_imm, 4, 0, SRC_TRACK)                                          # r4 = the track (obj no longer needed)
    E(cmp_imm, 4, 8)
    bc("kk_f0", "hs")
    E(ldrb_imm, 0, 7, B_BITS)
    E(lsrs_reg, 0, 4)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "kk_have", "ne")
    E(movs_imm, 0, 0)                                                     # first turn on this track: its four values as they are now
    a.label("kk_cp")
    E(push_list, [0])
    E(mov_reg, 1, 0)
    E(adds_imm8, 1, IDX_SC0)
    E(mov_reg, 0, 4)
    E(adds_imm8, 0, GRP_TRACK)
    E(bl, "c_skget")
    E(pop_list, [1])
    E(lsls_imm, 2, 4, 2)
    E(adds_reg, 2, 2, 1)
    E(adds_reg, 2, 2, 7)
    E(strb_imm, 0, 2, B_VAL)
    E(adds_imm8, 1, 1)
    E(mov_reg, 0, 1)
    E(cmp_imm, 0, 4)
    E(b_cond, "kk_cp", "lo")
    E(ldrb_imm, 0, 7, B_BITS)
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(orrs_reg, 0, 1)
    E(strb_imm, 0, 7, B_BITS)
    a.label("kk_have")
    E(lsls_imm, 0, 4, 2)
    E(adds_reg, 0, 0, 5)
    E(adds_reg, 0, 0, 7)
    E(adds_imm8, 0, B_VAL)
    E(ldrb_imm, 1, 0, 0)
    E(adds_reg, 1, 1, 6)                                                  # the value + the turn, 0..127
    E(cmp_imm, 1, 0)
    E(b_cond, "kk_lo", "ge")
    E(movs_imm, 1, 0)
    a.label("kk_lo")
    E(cmp_imm, 1, 0x7F)
    E(b_cond, "kk_hi", "le")
    E(movs_imm, 1, 0x7F)
    a.label("kk_hi")
    E(strb_imm, 1, 0, 0)
    E(mov_reg, 3, 1)
    E(mov_reg, 2, 5)
    E(adds_imm8, 2, IDX_SC0)
    E(mov_reg, 1, 4)
    E(adds_imm8, 1, GRP_TRACK)
    E(bl, "c_skset")
    E(b, "kk_done")
    # K6..K8: the master compressor
    a.label("kk_c")
    E(ldrb_w, 0, 7, B_COMP)
    E(cmp_imm, 0, 0)
    E(b_cond, "kk_ch", "ne")
    E(movs_imm, 4, 0)                                                     # first turn: its three values as they are now
    a.label("kk_ccp")
    imm32(1, t_cidx)
    E(ldrb_reg, 1, 1, 4)
    E(movs_imm, 0, GRP_MASTER)
    E(bl, "c_skget")
    E(adds_reg, 1, 7, 4)
    E(strb_w, 0, 1, B_CVAL)
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, 3)
    E(b_cond, "kk_ccp", "lo")
    E(movs_imm, 0, 1)
    E(strb_w, 0, 7, B_COMP)
    a.label("kk_ch")
    E(subs_imm8, 5, 5)                                                    # r5 = 0 soft clip, 1 attack, 2 release
    E(adds_reg, 0, 7, 5)
    E(adds_imm8, 0, B_CVAL)
    E(cmp_imm, 5, 0)
    E(b_cond, "kk_cv", "ne")
    E(movs_imm, 1, 0)                                                     # soft clip: right on, left off
    E(cmp_imm, 6, 0)
    E(b_cond, "kk_cw", "le")
    E(movs_imm, 1, 1)
    E(b, "kk_cw")
    a.label("kk_cv")
    E(ldrb_imm, 1, 0, 0)
    E(adds_reg, 1, 1, 6)
    E(cmp_imm, 1, 0)
    E(b_cond, "kk_clo", "ge")
    E(movs_imm, 1, 0)
    a.label("kk_clo")
    E(cmp_imm, 1, 0x7F)
    E(b_cond, "kk_cw", "le")
    E(movs_imm, 1, 0x7F)
    a.label("kk_cw")
    E(strb_imm, 1, 0, 0)
    E(mov_reg, 3, 1)
    imm32(1, t_cidx)
    E(ldrb_reg, 2, 1, 5)
    E(movs_imm, 1, GRP_MASTER)
    E(bl, "c_skset")
    a.label("kk_done")
    E(mov_reg, 0, 7)
    E(bl, "c_skfix")
    E(pop_list, [4, 5, 6, 7], pc=True)
    a.label("kk_f0")                                                      # no chosen track: nothing (a new block keeps a right sum)
    E(mov_reg, 0, 7)
    E(bl, "c_skfix")
    E(pop_list, [4, 5, 6, 7], pc=True)
    a.label("kk_f")                                                       # (the stock has nothing for them here)
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_skpad (the Sidechain object's slot 0: obj, pad, velocity): the stock's; a preset pad gives the track back to its preset
    a.label("c_skpad")
    E(push_list, [0, 1, 4], lr=True)
    E(bl, prev["pad"])
    E(pop_list, [0, 1])
    E(cmp_imm, 1, 16)
    E(b_cond, "kp_x", "lo")
    E(cmp_imm, 1, 32)
    E(b_cond, "kp_x", "hs")
    E(ldr_imm, 0, 0, O_SRC)
    E(ldrb_imm, 4, 0, SRC_TRACK)
    E(cmp_imm, 4, 8)
    E(b_cond, "kp_x", "hs")
    E(bl, "c_skblk")
    E(cmp_imm, 0, 0)
    E(b_cond, "kp_x", "eq")
    E(push_list, [0])
    E(bl, "c_skok")
    E(cmp_imm, 0, 0)
    E(pop_list, [0])
    E(b_cond, "kp_x", "eq")
    E(ldrb_imm, 2, 0, B_BITS)
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(bics_reg, 2, 1)
    E(strb_imm, 2, 0, B_BITS)
    E(bl, "c_skfix")
    a.label("kp_x")
    E(pop_list, [4], pc=True)

    # ---- c_skload (the end of «apply the record», r0-r3 = the stock's tail call's): ours to write again
    a.label("c_skload")
    E(raw, pushw([0, 1, 2, 3, 12], lr=True))
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "kl_x", "eq")
    E(movs_imm, 1, 0)
    imm32(2, rhstate.OFF["sckn"][0])
    E(raw, h(0x5481))                                                     # strb r1, [r0, r2]
    a.label("kl_x")
    E(raw, popw([0, 1, 2, 3, 12], lr=True))
    E(b_w, prev["load"])

    # ---- c_skapply(): the project's values written again (block in r7); clobbers r0-r6
    a.label("c_skapply")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(bl, "c_skblk")
    E(cmp_imm, 0, 0)
    bc("ka_x", "eq")
    E(mov_reg, 7, 0)
    E(bl, "c_skok")
    E(cmp_imm, 0, 0)
    bc("ka_x", "eq")
    E(movs_imm, 4, 0)                                                     # r4 = the track
    a.label("ka_t")
    E(ldrb_imm, 0, 7, B_BITS)
    E(lsrs_reg, 0, 4)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "ka_nt", "eq")
    E(movs_imm, 5, 0)
    a.label("ka_k")
    E(lsls_imm, 0, 4, 2)
    E(adds_reg, 0, 0, 5)
    E(adds_reg, 0, 0, 7)
    E(ldrb_imm, 3, 0, B_VAL)
    E(mov_reg, 2, 5)
    E(adds_imm8, 2, IDX_SC0)
    E(mov_reg, 1, 4)
    E(adds_imm8, 1, GRP_TRACK)
    E(bl, "c_skset")
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, 4)
    E(b_cond, "ka_k", "lo")
    a.label("ka_nt")
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, 8)
    E(b_cond, "ka_t", "lo")
    E(ldrb_w, 0, 7, B_COMP)
    E(cmp_imm, 0, 0)
    E(b_cond, "ka_x", "eq")
    E(movs_imm, 5, 0)
    a.label("ka_c")
    E(adds_reg, 0, 7, 5)
    E(ldrb_w, 3, 0, B_CVAL)
    imm32(1, t_cidx)
    E(ldrb_reg, 2, 1, 5)
    E(movs_imm, 1, GRP_MASTER)
    E(bl, "c_skset")
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, 3)
    E(b_cond, "ka_c", "lo")
    a.label("ka_x")
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_skled (the LED task's calls: ctrl, frame): after a load, the values once; in the Sidechain view, the knob LEDs
    a.label("c_skled")
    E(raw, pushw([4, 5, 6, 7, 8], lr=True))
    E(mov_reg, 5, 1)
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("kd_x", "eq")
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    bc("kd_x", "eq")
    E(mov_reg, 6, 0)
    E(adds_imm8, 6, rhstate.OFF["sckn"][0])                               # r6 = our byte
    E(ldrb_imm, 0, 6, 0)
    E(cmp_imm, 0, TAG)
    E(b_cond, "kd_v", "eq")
    E(movs_imm, 0, TAG)
    E(strb_imm, 0, 6, 0)
    E(bl, "c_skapply")
    a.label("kd_v")
    imm32(0, CTRL)
    E(ldr_imm, 1, 0, 0x7C)
    imm32(0, CONT)
    E(cmp_reg, 0, 1)
    bc("kd_x", "ne")
    imm32(1, O_MODE)
    E(raw, h(0x5C41))                                                     # ldrb r1, [r0, r1]
    E(cmp_imm, 1, MODE_SC)
    bc("kd_x", "ne")
    imm32(0, SC_OBJ)
    E(ldr_imm, 0, 0, O_SRC)
    E(ldrb_imm, 4, 0, SRC_TRACK)
    E(cmp_imm, 4, 8)
    bc("kd_x", "hs")
    imm32(0, COL_TRACK0)
    E(adds_reg, 0, 0, 4)
    for k in range(4):
        E(strh_w_imm, 0, 5, 2 * (LED_KNOB0 + k))
    E(movs_imm, 0, 0)
    E(strh_w_imm, 0, 5, 2 * (LED_KNOB0 + 4))
    E(movs_imm, 0, GRP_MASTER)
    E(movs_imm, 1, COMP_IDX[0])
    E(bl, "c_skget")
    imm32(1, COL_WHITE)
    E(cmp_imm, 0, 0)
    E(b_cond, "kd_sc", "ne")
    E(movs_imm, 1, COL_DIM)
    a.label("kd_sc")
    E(strh_w_imm, 1, 5, 2 * (LED_KNOB0 + 5))
    imm32(1, COL_WHITE)
    E(strh_w_imm, 1, 5, 2 * (LED_KNOB0 + 6))
    E(strh_w_imm, 1, 5, 2 * (LED_KNOB0 + 7))
    if BRIGHT:                                                            # kbright: K1-K4 the track's side-chain values, K7 / K8 the compressor's
        E(mov_reg, 7, 6)
        E(adds_imm8, 7, rhstate.OFF["kbright"][0] - rhstate.OFF["sckn"][0])
        E(movs_imm, 0, 0xCF)
        E(strb_imm, 0, 7, 0)
        for k in range(4):
            E(movs_imm, 0, GRP_TRACK)
            E(adds_reg, 0, 0, 4)
            E(movs_imm, 1, IDX_SC0 + k)
            E(bl, "c_skget")
            E(strb_imm, 0, 7, 1 + k)
            imm32(0, COL_TRACK0)
            E(adds_reg, 0, 0, 4)
            E(strh_imm, 0, 7, 10 + 2 * k)
        for k, idx in ((6, COMP_IDX[1]), (7, COMP_IDX[2])):
            E(movs_imm, 0, GRP_MASTER)
            E(movs_imm, 1, idx)
            E(bl, "c_skget")
            E(strb_imm, 0, 7, 1 + k)
            imm32(0, COL_WHITE)
            E(strh_imm, 0, 7, 10 + 2 * k)
    a.label("kd_x")
    E(raw, popw([4, 5, 6, 7, 8], lr=True))
    E(raw, h(0x4770))
    return a.assemble()


def install(img, report, base_addr, bright=False):
    """Append the code; slot 0 of the Sidechain object's vtable, slot 4 of the container's, the end of «apply the record» (in front of patchain's), the LED task calls."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]
    lab = lambda sec, n: int(report[sec]["labels"][n], 16)
    L = dict(c_rst=lab("rhstate", "c_rst"), c_rrt=lab("rhrec", "c_rrt"), c_ciok=lab("countin", "c_ciok"))
    global BRIGHT
    BRIGHT = bright
    prev = dict(pad=u(SLOT_PAD) & ~1, knob=u(SLOT_KNOB) & ~1, load=rhbuild.bw_target(img, LOAD_TAIL),
                ledtask=rhbuild.bl_target(img, LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in LED_CALLS)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch_word(img, SLOT_PAD, prev["pad"] | 1, labels["c_skpad"] | 1)
    rhbuild.patch_word(img, SLOT_KNOB, prev["knob"] | 1, labels["c_skknob"] | 1)
    rhbuild.patch(img, LOAD_TAIL, f"b.w #{prev['load']:#x}", b_w(LOAD_TAIL, labels["c_skload"]))
    for c in LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_skled"]))
    report["sckn"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
