"""A custom scale per track for the Note view (MIT; CIRCUIT-HACKS' cscale of SC42.2, for the Circuit Rhythm 5706).  The user (2026-10-19):
«incluye escala personalizada»; the editor = Shift held in the Note view; the keyboard = the scale's rows (each row an iteration, as the
Tracks'); one scale per track, saved with the project.

The stock of the Rhythm (read in the firmware and on the RAM dump, emulated):
  * each track's Note view (0x2004A604 + 0x1B4 t, vtable 0x08067248) plays [[view + 0x4C] + 8 + i], i = pad + 8 x [keyboard + 0x19C] x
    (5 - the octave, p0 of [view + 0x48]) (0x0805DFEA); the keyboard objects 0x200497C4 + 0x1C8 t (vtable 0x080696F4): + 8 index -> note (16
    rows of 8, 0 = none), + 0x88 note -> its first index (0xFF none), + 0x114 links between two pads of the same note (0xFF none), + 0x19C the
    rows a step of ▲ / ▼; it listens to the store [keyboard + 0x198] (0x20011120): its parameter 12 = the Slice mode, 13 the slices; a change
    rebuilds it (0x08055F8C: cleared by 0x08055E58, then the slices 0x08055F0A or the chromatic piano 0x08055E8C: rows of black keys over white
    keys, two rows an octave, the bottom-left pad of the default octave (3) = note 0x48);
  * in the Note view Shift + pad = the plain pad (tests/emu_stock.py): the editor takes it.

Ours:
  * the scale of a track: a set of intervals 1..24 over the root (0x48, a C); the highest = the period P (the root of the next iteration), the
    others the degrees (7 at most with the root); none = the stock's piano; in the record's tail (rhrec "cscale": "CS", a sum, 3 bytes a track);
  * the keyboard (when the track is not in Slice mode): one iteration a row (its n degrees and the period note; a row a step of ▲ / ▼), or with
    n <= 4 two a row (one in each half, without the period note); the bottom-left pad of the default octave = the root 0x48, as the stock's;
    the period note linked with the next row's root;
  * the editor: Shift held in the Note view: the pads are two octaves of a piano from the root (rows 3 / 1 black keys, 4 / 2 white ones:
    intervals 0..12 below, 12..24 above); a key toggles its interval (7 at most); LEDs: root white, degrees green, the period blue, the free
    keys dim; on Shift's release the keyboard is rebuilt;
  * the LED task rebuilds a keyboard whose scale is not the project's (after an edit, a load, a new project): one a frame (rhstate "cscale").
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, ands_reg, b, b_cond, b_w, bics_reg, bl, cmp_imm, cmp_reg, eors_reg, h, ldr_imm, ldr_sp,  # noqa: E402
                   ldrb_imm, ldrb_reg, ldrb_w, lsls_imm, lsls_reg, lsrs_imm, lsrs_reg, mov_reg, movs_imm, movt, movw, muls, orrs_reg, pop_list,
                   push_list, raw, str_imm, str_sp, strb_imm, strb_reg, strb_w, strh_reg, sub_sp_imm, add_sp_imm, subs_imm8, subs_reg, tst_reg)
import countin as CI  # noqa: E402
import rhrec  # noqa: E402
import rhstate  # noqa: E402

CTRL = CI.CTRL
NV0, NV_SZ, NV_VT = 0x2004A604, 0x1B4, 0x08067248
KB0, KB_SZ = 0x200497C4, 0x1C8
BUILD_CALL, CHROMATIC, REBUILD = 0x08055FAC, 0x08055E8C, 0x08055F8C
CONT, CONT_VT, O_MODE, MODE_NOTE, O_SEL = 0x20048B9C, 0x080678DC, 0x264, 1, 0x25C   # the track views' container: mode 1 = the Note view
NV_IDX = 0x0805DFEA                                        # (view, pad) -> the keyboard index (pad + 8 x rows x (5 - octave))
O_ROWS, O_TAB, O_REV, O_LINK = 0x19C, 8, 0x88, 0x114
ROOT = 0x48
BLK, BLK_LEN = rhrec.OFF["cscale"]
O_ST, ST_LEN = rhstate.OFF["cscale"]
MAX_KEYS = 7
# the editor's pads: the interval of each pad (0xFF = none); rows 1 / 2 the upper octave (black / white), 3 / 4 the lower one
KEYS = bytes([0xFF, 13, 15, 0xFF, 18, 20, 22, 0xFF,
              12, 14, 16, 17, 19, 21, 23, 24,
              0xFF, 1, 3, 0xFF, 6, 8, 10, 0xFF,
              0, 2, 4, 5, 7, 9, 11, 12])
COL_ROOT, COL_DEG, COL_PER, COL_FREE = 0x01, 0x1E, 0x12, 0x09
INV = dict(eq="ne", ne="eq", lo="hs", hs="lo", hi="ls", ls="hi", ge="lt", lt="ge", gt="le", le="gt", mi="pl", pl="mi")
assert BLK_LEN >= 27 and ST_LEN >= 32


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))
def pushw(regs, lr=False): return h(0xE92D) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit
    zc = [0]
    RET = h(0x4770)

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    def bc(target, cond):
        zc[0] += 1
        n = f"_c{zc[0]}"
        E(b_cond, n, INV[cond])
        E(b, target)
        a.label(n)

    t_keys = base
    E(raw, KEYS)

    # ---- c_csraw() -> r0 = our block's place in the tail (0 without a record); c_csblk() -> r0 = it when valid, else 0; clobber r1-r3
    a.label("c_csraw")
    E(push_list, [4], lr=True)
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "cr_x", "eq")
    imm32(1, BLK)
    E(adds_reg, 0, 0, 1)
    a.label("cr_x")
    E(pop_list, [4], pc=True)
    a.label("c_cssum")                                                    # (r0 = block) -> r1 = the sum of bytes 3..26; clobbers r2, r3
    E(movs_imm, 1, 0x5A)
    E(movs_imm, 3, 3)
    a.label("cs_l")
    E(ldrb_reg, 2, 0, 3)
    E(adds_reg, 1, 1, 2)
    E(adds_imm8, 3, 1)
    E(cmp_imm, 3, 27)
    E(b_cond, "cs_l", "lo")
    E(movs_imm, 2, 0xFF)
    E(ands_reg, 1, 2)
    E(raw, RET)
    a.label("c_csblk")
    E(push_list, [4], lr=True)
    E(bl, "c_csraw")
    E(cmp_imm, 0, 0)
    E(b_cond, "cb_x", "eq")
    E(mov_reg, 4, 0)
    E(ldrb_imm, 0, 4, 0)
    E(cmp_imm, 0, ord("C"))
    E(b_cond, "cb_0", "ne")
    E(ldrb_imm, 0, 4, 1)
    E(cmp_imm, 0, ord("S"))
    E(b_cond, "cb_0", "ne")
    E(mov_reg, 0, 4)
    E(bl, "c_cssum")
    E(ldrb_imm, 2, 4, 2)
    E(cmp_reg, 1, 2)
    E(b_cond, "cb_0", "ne")
    E(mov_reg, 0, 4)
    E(pop_list, [4], pc=True)
    a.label("cb_0")
    E(movs_imm, 0, 0)
    a.label("cb_x")
    E(pop_list, [4], pc=True)

    # ---- c_cskeys(r0 = track) -> r0 = its scale (bits 1..24 = the intervals; 0 = none); clobbers r1-r3
    a.label("c_cskeys")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_csblk")
    E(cmp_imm, 0, 0)
    E(b_cond, "ck_x", "eq")
    E(lsls_imm, 1, 4, 1)
    E(adds_reg, 1, 1, 4)                                                  # 3 t
    E(adds_reg, 0, 0, 1)
    E(ldrb_imm, 1, 0, 3)
    E(ldrb_imm, 2, 0, 4)
    E(lsls_imm, 2, 2, 8)
    E(orrs_reg, 1, 2)
    E(ldrb_imm, 2, 0, 5)
    E(lsls_imm, 2, 2, 16)
    E(orrs_reg, 1, 2)
    E(mov_reg, 0, 1)
    imm32(1, 0x1FFFFFE)
    E(ands_reg, 0, 1)
    a.label("ck_x")
    E(pop_list, [4], pc=True)

    # ---- c_csput(r0 = track, r1 = scale): into the block (made when missing); clobbers r0-r3
    a.label("c_csput")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(bl, "c_csblk")
    E(cmp_imm, 0, 0)
    E(b_cond, "cp_w", "ne")
    E(bl, "c_csraw")
    E(cmp_imm, 0, 0)
    E(b_cond, "cp_x", "eq")
    E(movs_imm, 1, ord("C"))
    E(strb_imm, 1, 0, 0)
    E(movs_imm, 1, ord("S"))
    E(strb_imm, 1, 0, 1)
    E(movs_imm, 1, 0)
    E(movs_imm, 2, 27)
    a.label("cp_z")
    E(subs_imm8, 2, 1)
    E(strb_reg, 1, 0, 2)
    E(cmp_imm, 2, 3)
    E(b_cond, "cp_z", "hi")
    a.label("cp_w")
    E(mov_reg, 6, 0)
    E(lsls_imm, 1, 4, 1)
    E(adds_reg, 1, 1, 4)
    E(adds_reg, 0, 0, 1)
    E(strb_imm, 5, 0, 3)
    E(lsrs_imm, 1, 5, 8)
    E(strb_imm, 1, 0, 4)
    E(lsrs_imm, 1, 5, 16)
    E(strb_imm, 1, 0, 5)
    E(mov_reg, 0, 6)
    E(bl, "c_cssum")
    E(strb_imm, 1, 6, 2)
    a.label("cp_x")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_cstrk(r0 = a view) -> r0 = its track when it is a Note view, else 0xFF; c_cskb(r0 = keyboard) -> r0 = its track or 0xFF; clobber r1-r3
    a.label("c_cstrk")
    E(ldr_imm, 1, 0, 0)
    imm32(2, NV_VT)
    E(cmp_reg, 1, 2)
    E(b_cond, "ct_n", "ne")
    imm32(1, NV0)
    E(movw, 2, NV_SZ)
    E(b, "ct_f")
    a.label("c_cskb")
    imm32(1, KB0)
    E(movw, 2, KB_SZ)
    a.label("ct_f")
    E(movs_imm, 3, 0)
    a.label("ct_l")
    E(cmp_reg, 0, 1)
    E(b_cond, "ct_y", "eq")
    E(adds_reg, 1, 1, 2)
    E(adds_imm8, 3, 1)
    E(cmp_imm, 3, 8)
    E(b_cond, "ct_l", "lo")
    a.label("ct_n")
    E(movs_imm, 0, 0xFF)
    E(raw, RET)
    a.label("ct_y")
    E(mov_reg, 0, 3)
    E(raw, RET)

    # ---- c_csplace(r0 = keyboard, r1 = index, r2 = note (signed)): a pad of the scale's keyboard (notes 1..127 only); clobbers r3
    a.label("c_csplace")
    E(cmp_imm, 2, 1)
    E(b_cond, "pl_x", "lt")
    E(cmp_imm, 2, 127)
    E(b_cond, "pl_x", "gt")
    E(cmp_imm, 1, 128)
    E(b_cond, "pl_x", "hs")
    E(adds_reg, 3, 0, 1)
    E(strb_imm, 2, 3, O_TAB)
    E(adds_reg, 3, 0, 2)
    E(ldrb_w, 3, 3, O_REV)
    E(cmp_imm, 3, 0xFF)
    E(b_cond, "pl_x", "ne")
    E(adds_reg, 3, 0, 2)
    E(strb_w, 1, 3, O_REV)
    a.label("pl_x")
    E(raw, RET)

    # ---- c_csbuild (the keyboard's chromatic builder, 0x08055E8C(keyboard), called after its tables are cleared): a track with a scale = ours
    # frame: [sp] the degrees (8 B: the root, then the intervals), [sp + 8] n (the degrees without the period), [sp + 12] the period
    a.label("c_csbuild")
    E(raw, pushw([4, 5, 6, 7, 8], lr=True))
    E(sub_sp_imm, 16)
    E(mov_reg, 4, 0)                                                      # r4 = the keyboard
    E(bl, "c_cskb")
    E(cmp_imm, 0, 7)
    bc("cv_c", "hi")
    E(bl, "c_cskeys")
    E(cmp_imm, 0, 0)
    bc("cv_c", "eq")
    E(mov_reg, 8, 0)                                                      # r8 = the scale
    E(movs_imm, 0, 0)
    E(str_sp, 0, 0)
    E(str_sp, 0, 4)                                                       # degrees[0] = 0 (the root)
    E(movs_imm, 6, 1)                                                     # r6 = how many (with the root)
    E(movs_imm, 5, 1)                                                     # r5 = the interval
    E(movs_imm, 7, 0)                                                     # r7 = the period (the highest)
    a.label("cv_d")
    E(mov_reg, 0, 8)
    E(lsrs_reg, 0, 5)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "cv_dn", "pl")
    E(mov_reg, 7, 5)
    E(cmp_imm, 6, 8)
    E(b_cond, "cv_dn", "hs")
    E(raw, h(0xA800))                                                     # add r0, sp, #0
    E(strb_reg, 5, 0, 6)
    E(adds_imm8, 6, 1)
    a.label("cv_dn")
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, 25)
    E(b_cond, "cv_d", "lo")
    E(subs_imm8, 6, 1)                                                    # the period is not a degree
    E(str_sp, 6, 8)
    E(str_sp, 7, 12)
    E(movs_imm, 0, 1)
    E(strb_w, 0, 4, O_ROWS)                                               # one row a step of the arrows
    E(movs_imm, 5, 0)                                                     # r5 = the row
    a.label("cv_r")
    E(ldr_sp, 0, 8)
    E(cmp_imm, 0, 4)
    bc("cv_one", "hi")
    E(movs_imm, 6, 0)                                                     # n <= 4: two iterations a row (r6 = the half)
    a.label("cv_h")
    E(movs_imm, 0, 5)
    E(subs_reg, 0, 0, 5)
    E(lsls_imm, 0, 0, 1)
    E(adds_reg, 0, 0, 6)                                                  # the iteration: 2 (5 - row) + half
    E(ldr_sp, 1, 12)
    E(muls, 0, 1)
    E(adds_imm8, 0, ROOT)
    E(mov_reg, 7, 0)                                                      # r7 = its root
    E(movs_imm, 3, 0)
    a.label("cv_hc")
    E(push_list, [3])
    E(raw, h(0xA801))                                                     # add r0, sp, #4: the degrees
    E(ldrb_reg, 2, 0, 3)
    E(adds_reg, 2, 2, 7)
    E(lsls_imm, 1, 5, 3)
    E(lsls_imm, 0, 6, 2)
    E(adds_reg, 1, 1, 0)
    E(adds_reg, 1, 1, 3)
    E(mov_reg, 0, 4)
    E(bl, "c_csplace")
    E(pop_list, [3])
    E(adds_imm8, 3, 1)
    E(ldr_sp, 0, 8)
    E(cmp_reg, 3, 0)
    E(b_cond, "cv_hc", "lo")
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, 2)
    E(b_cond, "cv_h", "lo")
    E(b, "cv_nr")
    a.label("cv_one")                                                     # one iteration a row (r6 = the column), and its period note
    E(movs_imm, 0, 5)
    E(subs_reg, 0, 0, 5)
    E(ldr_sp, 1, 12)
    E(muls, 0, 1)
    E(adds_imm8, 0, ROOT)
    E(mov_reg, 7, 0)
    E(movs_imm, 6, 0)
    a.label("cv_oc")
    E(raw, h(0xA800))                                                     # add r0, sp, #0
    E(ldrb_reg, 2, 0, 6)
    E(adds_reg, 2, 2, 7)
    E(lsls_imm, 1, 5, 3)
    E(adds_reg, 1, 1, 6)
    E(mov_reg, 0, 4)
    E(bl, "c_csplace")
    E(adds_imm8, 6, 1)
    E(ldr_sp, 0, 8)
    E(cmp_reg, 6, 0)
    E(b_cond, "cv_oc", "lo")
    E(ldr_sp, 2, 12)
    E(adds_reg, 2, 2, 7)                                                  # the period note
    E(lsls_imm, 1, 5, 3)
    E(adds_reg, 1, 1, 6)
    E(mov_reg, 0, 4)
    E(bl, "c_csplace")
    E(cmp_imm, 5, 0)
    E(b_cond, "cv_nr", "eq")
    E(lsls_imm, 1, 5, 3)
    E(adds_reg, 1, 1, 6)                                                  # r1 = the period's pad
    E(lsls_imm, 2, 5, 3)
    E(subs_imm8, 2, 8)                                                    # r2 = the root of the row above (the same note)
    E(movw, 3, O_LINK)
    E(adds_reg, 3, 3, 4)
    E(strb_reg, 2, 3, 1)
    E(strb_reg, 1, 3, 2)
    a.label("cv_nr")
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, 16)
    bc("cv_r", "lo")
    E(add_sp_imm, 16)
    E(raw, popw([4, 5, 6, 7, 8], lr=True))
    E(raw, RET)
    a.label("cv_c")
    E(mov_reg, 0, 4)
    E(add_sp_imm, 16)
    E(raw, popw([4, 5, 6, 7, 8], lr=True))
    E(b_w, CHROMATIC)

    # ---- c_csedit(r0 = view) -> r0 = its track when the editor is on (a Note view, Shift held, the controller the dump's), else 0xFF
    a.label("c_csedit")
    E(push_list, [4], lr=True)
    E(bl, "c_cstrk")
    E(mov_reg, 4, 0)
    E(cmp_imm, 4, 7)
    E(b_cond, "ce_n", "hi")
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ce_n", "eq")
    E(bl, L["c_cishift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ce_n", "eq")
    E(mov_reg, 0, 4)
    E(pop_list, [4], pc=True)
    a.label("ce_n")
    E(movs_imm, 0, 0xFF)
    E(pop_list, [4], pc=True)

    # ---- c_cstoggle(r0 = track, r1 = pad 0..31): the editor's key of that pad toggled (the root fixed, 7 keys at most); clobbers r0-r3
    a.label("c_cstoggle")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)                                                      # r4 = the track
    imm32(0, t_keys)
    E(ldrb_reg, 5, 0, 1)                                                  # r5 = the pad's interval
    E(cmp_imm, 5, 0)
    E(b_cond, "cd_x", "eq")                                               # the root: always there
    E(cmp_imm, 5, 24)
    E(b_cond, "cd_x", "hi")                                               # no key
    E(mov_reg, 0, 4)
    E(bl, "c_cskeys")
    E(mov_reg, 6, 0)                                                      # r6 = the scale
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 5)
    E(tst_reg, 6, 1)
    E(b_cond, "cd_t", "ne")
    E(movs_imm, 2, 0)                                                     # a key more: 7 at most
    E(mov_reg, 3, 6)
    a.label("cd_n")
    E(cmp_imm, 3, 0)
    E(b_cond, "cd_c", "eq")
    E(mov_reg, 0, 3)
    E(subs_imm8, 0, 1)
    E(ands_reg, 3, 0)                                                     # (clears the lowest bit)
    E(adds_imm8, 2, 1)
    E(b, "cd_n")
    a.label("cd_c")
    E(cmp_imm, 2, MAX_KEYS)
    E(b_cond, "cd_x", "hs")
    a.label("cd_t")
    E(eors_reg, 6, 1)
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 6)
    E(bl, "c_csput")
    a.label("cd_x")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_cssel() -> r0 = the selected track (the track views' container: p0 of [+ 0x25C]); clobbers r1-r3
    a.label("c_cssel")
    imm32(0, CONT)
    imm32(1, O_SEL)
    E(raw, h(0x5840))                                                     # ldr r0, [r0, r1]
    E(movs_imm, 1, 0)
    E(b_w, L["c_cinew"])

    # ---- c_csnote() -> r0 = 1 when the Note view is on screen with Shift held (the editor), else 0; clobbers r1-r3
    a.label("c_csnote")
    E(push_list, [4], lr=True)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "cn_x", "eq")
    imm32(0, CTRL)
    E(ldr_imm, 1, 0, 0x7C)
    imm32(0, CONT)
    E(cmp_reg, 0, 1)
    E(b_cond, "cn_0", "ne")
    imm32(1, O_MODE)
    E(raw, h(0x5C41))                                                     # ldrb r1, [r0, r1]
    E(cmp_imm, 1, MODE_NOTE)
    E(b_cond, "cn_0", "ne")
    E(bl, L["c_cishift"])
    E(pop_list, [4], pc=True)
    a.label("cn_0")
    E(movs_imm, 0, 0)
    a.label("cn_x")
    E(pop_list, [4], pc=True)

    # ---- c_cspad (the Note views' slot 0: view, pad 16..31, velocity): Shift held = the editor
    a.label("c_cspad")
    E(cmp_imm, 1, 32)
    bc("cd_f", "hs")
    E(push_list, [0, 1, 2, 4], lr=True)
    E(bl, "c_csedit")
    E(cmp_imm, 0, 7)
    bc("cd_p", "hi")
    E(ldr_sp, 1, 4)
    E(bl, "c_cstoggle")
    E(pop_list, [0, 1, 2, 4], pc=True)
    a.label("cd_p")
    E(raw, popw([0, 1, 2, 4], lr=True))
    a.label("cd_f")
    E(b_w, prev["npad"])

    # ---- c_cscpad (the container's slot 0: container, pad, velocity): in the Note view with Shift, pads 1-16 = the editor's upper octave
    #      (the container never marks them pressed: their release is not passed on)
    a.label("c_cscpad")
    E(cmp_imm, 1, 16)
    bc("cc_f", "hs")
    E(push_list, [0, 1, 2, 4], lr=True)
    E(bl, "c_csnote")
    E(cmp_imm, 0, 0)
    bc("cc_p", "eq")
    E(bl, "c_cssel")
    E(cmp_imm, 0, 7)
    bc("cc_p", "hi")
    E(ldr_sp, 1, 4)
    E(bl, "c_cstoggle")
    E(pop_list, [0, 1, 2, 4], pc=True)
    a.label("cc_p")
    E(raw, popw([0, 1, 2, 4], lr=True))
    a.label("cc_f")
    E(b_w, prev["cpad"])

    # ---- c_csledtask (the LED task's calls: ctrl, frame): the editor drawn over the frame (the Note view, Shift held); else a keyboard
    #      whose scale is not the project's rebuilt, one a frame
    a.label("c_csledtask")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 6, 1)                                                      # r6 = the frame
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("cq_x", "eq")
    E(bl, L["c_cishift"])
    E(cmp_imm, 0, 0)
    bc("cq_s", "eq")
    E(bl, "c_csnote")                                                     # Shift held: the editor?
    E(cmp_imm, 0, 0)
    bc("cq_x", "eq")
    E(bl, "c_cssel")
    E(cmp_imm, 0, 7)
    bc("cq_x", "hi")
    E(bl, "c_cskeys")
    E(mov_reg, 5, 0)                                                      # r5 = the scale
    E(movs_imm, 7, 0)                                                     # r7 = the period (the highest key)
    E(movs_imm, 1, 24)
    a.label("cl_p")
    E(mov_reg, 0, 5)
    E(lsrs_reg, 0, 1)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "cl_pf", "mi")
    E(subs_imm8, 1, 1)
    E(b_cond, "cl_p", "ne")
    E(b, "cl_pd")
    a.label("cl_pf")
    E(mov_reg, 7, 1)
    a.label("cl_pd")
    E(movs_imm, 3, 0)                                                     # r3 = the pad
    a.label("cl_l")
    imm32(0, t_keys)
    E(ldrb_reg, 0, 0, 3)
    E(movs_imm, 2, 0)
    E(cmp_imm, 0, 24)
    E(b_cond, "cl_w", "hi")
    E(movs_imm, 2, COL_ROOT)
    E(cmp_imm, 0, 0)
    E(b_cond, "cl_w", "eq")
    E(movs_imm, 2, COL_FREE)
    E(mov_reg, 1, 5)
    E(lsrs_reg, 1, 0)
    E(lsls_imm, 1, 1, 31)
    E(b_cond, "cl_w", "pl")
    E(movs_imm, 2, COL_DEG)
    E(cmp_reg, 0, 7)
    E(b_cond, "cl_w", "ne")
    E(movs_imm, 2, COL_PER)
    a.label("cl_w")
    E(lsls_imm, 0, 3, 1)
    E(strh_reg, 2, 6, 0)
    E(adds_imm8, 3, 1)
    E(cmp_imm, 3, 32)
    E(b_cond, "cl_l", "lo")
    E(b, "cq_x")
    a.label("cq_s")                                                       # not editing: the keyboards
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    bc("cq_x", "eq")
    E(adds_imm8, 0, O_ST)
    E(mov_reg, 5, 0)                                                      # r5 = what each keyboard holds (4 B a track)
    E(movs_imm, 4, 0)
    a.label("cq_t")
    E(mov_reg, 0, 4)
    E(bl, "c_cskeys")
    E(lsls_imm, 1, 4, 2)
    E(adds_reg, 1, 1, 5)
    E(ldr_imm, 2, 1, 0)
    E(cmp_reg, 0, 2)
    E(b_cond, "cq_rb", "ne")
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, 8)
    E(b_cond, "cq_t", "lo")
    E(b, "cq_x")
    a.label("cq_rb")
    E(str_imm, 0, 1, 0)
    E(movw, 0, KB_SZ)
    E(muls, 0, 4)
    imm32(1, KB0)
    E(adds_reg, 0, 0, 1)
    E(bl, REBUILD)
    a.label("cq_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; the keyboards' chromatic builder call, the Note views' slot 0, the container's slot 0, the LED task calls."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]
    lab = lambda sec, n: int(report[sec]["labels"][n], 16)
    L = dict(c_rst=lab("rhstate", "c_rst"), c_rrt=lab("rhrec", "c_rrt"), c_ciok=lab("countin", "c_ciok"), c_cishift=lab("countin", "c_cishift"),
             c_cinew=lab("countin", "c_cinew"))
    prev = dict(npad=u(NV_VT) & ~1, cpad=u(CONT_VT) & ~1, ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, BUILD_CALL, f"bl #{CHROMATIC:#x}", bl(BUILD_CALL, labels["c_csbuild"]))
    rhbuild.patch_word(img, NV_VT, prev["npad"] | 1, labels["c_cspad"] | 1)
    rhbuild.patch_word(img, CONT_VT, prev["cpad"] | 1, labels["c_cscpad"] | 1)
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_csledtask"]))
    report["cscale"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
