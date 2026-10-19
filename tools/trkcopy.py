"""A track's parameters and selected sample: Duplicate held + track button A, then track button B = A's copied onto B; Clear + track button = the
track back to how the project was loaded (MIT; for the Circuit Rhythm 5706).  The user (2026-10-19): «Parametros y sample seleccionado por pista:
Restablecer (clear+pista) o duplicar (hold duplicate, pista 1 y luego pista 2)»; the reset = «a como se guardó» (the knobs as RH06: their
defaults, their automation deleted).

The stock of the Rhythm (read in the firmware and on the RAM dump, emulated):
  * a track's parameters = the group 0x10 + t of the setter 0x08031A38(0x20010E10, group, index, value) (store, DSP, MIDI) and the getter
    0x08046410(group, index), indices 0..0x18: 6..13 the eight knobs, 0x10 level, 0x11 pan, 0x12 / 0x13 the reverb / delay sends, 0x14..0x18 the
    side-chain (source, attack, hold, decay, depth);
  * the selected sample = p0 of the store [player + 0x60] (the players 0x200470D4 + 0x190 t; the same store as the sample view's [+ 0x28]):
    a write and its commit select it, the player takes it at its next step;
  * Duplicate + a track button and Clear + a track button only select the track (tests/emu_stock.py); RH06 (clrtrk) puts the knobs back with
    Clear + a track button in the track views.

Ours, the head of the button chain (after the stock's selection, run first):
  * Duplicate held (not Clear): the first track button is the source; each next one gets the source's 25 parameters, its selected sample and
    its side-chain knob values of RH12 (sckn's block in the tail); letting Duplicate go forgets the source;
  * Clear held (not Duplicate) + a track button, with the track views on the screen: after RH06's knobs, the track's other parameters (0..5,
    14..24) and its selected sample as they were when the project was loaded;
  * the photo of each track at the load (and at power-on): the LED task's first frame after «apply the record» (after RH12's values), in the
    record's tail (rhrec "trkcopy": "TS", then 26 bytes a track: the 25 parameters and the sample).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b, b_cond, b_w, bics_reg, bl, cmp_imm, cmp_reg, h, ldr_imm, ldr_sp, ldrb_imm, ldrb_reg,  # noqa: E402
                   lsls_imm, lsls_reg, lsrs_reg, mov_reg, movs_imm, movt, movw, muls, orrs_reg, pop_list, push_list, raw, strb_imm, strb_reg,
                   subs_imm8, tst_reg, ldrb_w, strb_w)
import countin as CI  # noqa: E402
import patchain as PC  # noqa: E402
import rhrec  # noqa: E402
import rhstate  # noqa: E402
import sckn as SK  # noqa: E402

CTRL = CI.CTRL
DP0, DP_SZ, O_SEL = 0x200470D4, 0x190, 0x60
WPTR, COMMIT = 0x0803FD26, 0x0803FBEC
N_PAR, KNOB_LO, KNOB_HI = 0x19, 6, 13
CONT = 0x20048B9C
BIT_CLEAR, BIT_DUP = 23, 24
BLK, BLK_LEN = rhrec.OFF["trkcopy"]
REC = N_PAR + 1                                       # a track's photo: 25 parameters, the sample
O_ST = rhstate.OFF["trkcopy"][0]
S_TAG, S_SRC = 0, 1
TAG = 0xC3
INV = SK.INV
assert BLK_LEN >= 2 + 8 * REC


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
        n = f"_t{zc[0]}"
        E(b_cond, n, INV[cond])
        E(b, target)
        a.label(n)

    # ---- c_tcst() -> r0 = our RAM (0 without it); c_tcblk() -> r0 = the photos in the tail (0 without a record); clobber r1-r3
    a.label("c_tcst")
    E(push_list, [4], lr=True)
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ts_x", "eq")
    E(adds_imm8, 0, O_ST)
    a.label("ts_x")
    E(pop_list, [4], pc=True)
    a.label("c_tcblk")
    E(push_list, [4], lr=True)
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "tb_x", "eq")
    E(movw, 1, BLK)
    E(adds_reg, 0, 0, 1)
    a.label("tb_x")
    E(pop_list, [4], pc=True)

    # ---- c_tcsel(r0 = track) -> r0 = its selected sample's store; clobbers r1
    a.label("c_tcsel")
    E(movw, 1, DP_SZ)
    E(muls, 0, 1)
    imm32(1, DP0)
    E(adds_reg, 0, 0, 1)
    E(ldr_imm, 0, 0, O_SEL)
    E(raw, h(0x4770))

    # ---- c_tcsetsmp(r0 = track, r1 = sample): the track's selection (write and commit, as the sample view); clobbers r0-r3
    a.label("c_tcsetsmp")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 5, 1)
    E(bl, "c_tcsel")
    E(mov_reg, 4, 0)
    E(movs_imm, 1, 0)
    E(bl, WPTR)
    E(strb_imm, 5, 0, 0)
    E(mov_reg, 0, 4)
    E(bl, COMMIT)
    E(pop_list, [4, 5], pc=True)

    # ---- c_tcget(r0 = track, r1 = index) -> r0 = the parameter; c_tcset(r0 = track, r1 = index, r2 = value); clobber r0-r3, r12
    a.label("c_tcget")
    E(push_list, [4], lr=True)
    E(adds_imm8, 0, 0x10)
    E(bl, SK.GETTER)
    E(movs_imm, 1, 0xFF)
    E(raw, h(0x4008))                                                     # ands r0, r1
    E(pop_list, [4], pc=True)
    a.label("c_tcset")
    E(mov_reg, 3, 2)
    E(mov_reg, 2, 1)
    E(mov_reg, 1, 0)
    E(adds_imm8, 1, 0x10)
    imm32(0, SK.SET_OBJ)
    E(b_w, SK.SETTER)

    # ---- c_tccopy(r0 = source, r1 = destination): the 25 parameters, the selected sample, RH12's side-chain values
    a.label("c_tccopy")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(movs_imm, 6, 0)
    a.label("cp_l")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 6)
    E(bl, "c_tcget")
    E(mov_reg, 2, 0)
    E(mov_reg, 0, 5)
    E(mov_reg, 1, 6)
    E(bl, "c_tcset")
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, N_PAR)
    E(b_cond, "cp_l", "lo")
    E(mov_reg, 0, 4)
    E(bl, "c_tcsel")
    E(movs_imm, 1, 0)
    E(bl, L["c_cinew"])
    E(mov_reg, 1, 0)
    E(mov_reg, 0, 5)
    E(bl, "c_tcsetsmp")
    E(bl, L["c_skblk"])                                                   # RH12's block: the destination's bit and values = the source's
    E(cmp_imm, 0, 0)
    bc("cp_x", "eq")
    E(mov_reg, 6, 0)
    E(bl, L["c_skok"])
    E(cmp_imm, 0, 0)
    bc("cp_x", "eq")
    E(ldrb_imm, 0, 6, SK.B_BITS)
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 5)
    E(bics_reg, 0, 1)
    E(ldrb_imm, 2, 6, SK.B_BITS)
    E(lsrs_reg, 2, 4)
    E(lsls_imm, 2, 2, 31)
    E(b_cond, "cp_b", "pl")
    E(orrs_reg, 0, 1)
    a.label("cp_b")
    E(strb_imm, 0, 6, SK.B_BITS)
    E(movs_imm, 3, 0)
    a.label("cp_v")
    E(lsls_imm, 0, 4, 2)
    E(adds_reg, 0, 0, 3)
    E(adds_reg, 0, 0, 6)
    E(ldrb_imm, 1, 0, SK.B_VAL)
    E(lsls_imm, 0, 5, 2)
    E(adds_reg, 0, 0, 3)
    E(adds_reg, 0, 0, 6)
    E(strb_imm, 1, 0, SK.B_VAL)
    E(adds_imm8, 3, 1)
    E(cmp_imm, 3, 4)
    E(b_cond, "cp_v", "lo")
    E(mov_reg, 0, 6)
    E(bl, L["c_skfix"])
    a.label("cp_x")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_tcrestore(r0 = track): its parameters but the knobs and its selected sample, as the photo of the load
    a.label("c_tcrestore")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_tcblk")
    E(cmp_imm, 0, 0)
    bc("rs_x", "eq")
    E(ldrb_imm, 1, 0, 0)
    E(cmp_imm, 1, ord("T"))
    bc("rs_x", "ne")
    E(ldrb_imm, 1, 0, 1)
    E(cmp_imm, 1, ord("S"))
    bc("rs_x", "ne")
    E(adds_imm8, 0, 2)
    E(movs_imm, 1, REC)
    E(muls, 1, 4)
    E(adds_reg, 5, 0, 1)                                                  # r5 = the track's photo
    E(movs_imm, 6, 0)
    a.label("rs_l")
    E(cmp_imm, 6, KNOB_LO)
    E(b_cond, "rs_s", "lo")
    E(cmp_imm, 6, KNOB_HI)
    E(b_cond, "rs_n", "ls")                                               # the knobs: RH06's
    a.label("rs_s")
    E(ldrb_reg, 2, 5, 6)
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 6)
    E(bl, "c_tcset")
    a.label("rs_n")
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, N_PAR)
    E(b_cond, "rs_l", "lo")
    E(ldrb_imm, 1, 5, N_PAR)
    E(mov_reg, 0, 4)
    E(bl, "c_tcsetsmp")
    a.label("rs_x")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_tcphoto(): every track's photo into the tail
    a.label("c_tcphoto")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(bl, "c_tcblk")
    E(cmp_imm, 0, 0)
    bc("ph_x", "eq")
    E(mov_reg, 7, 0)
    E(movs_imm, 1, ord("T"))
    E(strb_imm, 1, 7, 0)
    E(movs_imm, 1, ord("S"))
    E(strb_imm, 1, 7, 1)
    E(adds_imm8, 7, 2)                                                    # r7 = the photos
    E(movs_imm, 4, 0)
    a.label("ph_t")
    E(movs_imm, 5, 0)
    a.label("ph_i")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, "c_tcget")
    E(strb_reg, 0, 7, 5)
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, N_PAR)
    E(b_cond, "ph_i", "lo")
    E(mov_reg, 0, 4)
    E(bl, "c_tcsel")
    E(movs_imm, 1, 0)
    E(bl, L["c_cinew"])
    E(strb_imm, 0, 7, N_PAR)
    E(adds_imm8, 7, REC)
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, 8)
    E(b_cond, "ph_t", "lo")
    a.label("ph_x")
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_tcbtn (the head of the button chain: ctrl, button)
    a.label("c_tcbtn")
    E(cmp_imm, 1, 8)
    E(b_cond, "tb_in", "lo")
    E(b_w, prev["btn"])
    a.label("tb_in")
    E(push_list, [0, 1, 4, 5, 6, 7], lr=True)
    imm32(2, CTRL)
    E(ldr_imm, 7, 2, 0x7C)                                                # r7 = the view on the screen before the press
    E(bl, prev["btn"])                                                    # the stock's first (and RH06's): the track selected
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("tc_x", "eq")
    E(bl, "c_tcst")
    E(cmp_imm, 0, 0)
    bc("tc_x", "eq")
    E(mov_reg, 6, 0)                                                      # r6 = our RAM
    E(ldr_sp, 5, 4)                                                       # r5 = the track
    imm32(0, CTRL)
    E(raw, h(0xF8D0) + h(0x40A0))                                         # ldr.w r4, [r0, #0xa0]: the held buttons
    E(movs_imm, 0, 1)
    E(lsls_imm, 0, 0, BIT_DUP)
    E(tst_reg, 4, 0)
    E(b_cond, "tc_c", "eq")
    E(movs_imm, 0, 1)
    E(lsls_imm, 0, 0, BIT_CLEAR)
    E(tst_reg, 4, 0)
    bc("tc_x", "ne")                                                      # (Clear and Duplicate: nothing)
    E(ldrb_imm, 0, 6, S_SRC)                                              # Duplicate: the source, or a copy
    E(cmp_imm, 0, 0)
    E(b_cond, "tc_cp", "ne")
    E(adds_imm8, 5, 1)
    E(strb_imm, 5, 6, S_SRC)
    E(b, "tc_x")
    a.label("tc_cp")
    E(subs_imm8, 0, 1)
    E(cmp_reg, 0, 5)
    bc("tc_x", "eq")
    E(mov_reg, 1, 5)
    E(bl, "c_tccopy")
    E(b, "tc_x")
    a.label("tc_c")                                                       # Clear, the track views on the screen: the photo
    E(movs_imm, 0, 1)
    E(lsls_imm, 0, 0, BIT_CLEAR)
    E(tst_reg, 4, 0)
    bc("tc_x", "eq")
    imm32(0, CONT)
    E(cmp_reg, 0, 7)
    bc("tc_x", "ne")
    E(mov_reg, 0, 5)
    E(bl, "c_tcrestore")
    a.label("tc_x")
    E(pop_list, [0, 1, 4, 5, 6, 7], pc=True)

    # ---- c_tcload (the end of «apply the record», r0-r3 = the stock's tail call's): a photo to take
    a.label("c_tcload")
    E(raw, pushw([0, 1, 2, 3, 12], lr=True))
    E(bl, "c_tcst")
    E(cmp_imm, 0, 0)
    E(b_cond, "tl_x", "eq")
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 0, S_TAG)
    a.label("tl_x")
    E(raw, popw([0, 1, 2, 3, 12], lr=True))
    E(b_w, prev["load"])

    # ---- c_tcled (the LED task's calls: ctrl, frame): after the chain (RH12's values written again), the photo once; Duplicate let go = no source
    a.label("c_tcled")
    E(push_list, [3, 4, 5, 6], lr=True)
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "td_x", "eq")
    E(bl, "c_tcst")
    E(cmp_imm, 0, 0)
    E(b_cond, "td_x", "eq")
    E(mov_reg, 4, 0)
    imm32(0, CTRL)
    E(raw, h(0xF8D0) + h(0x10A0))                                         # ldr.w r1, [r0, #0xa0]
    E(movs_imm, 0, 1)
    E(lsls_imm, 0, 0, BIT_DUP)
    E(tst_reg, 1, 0)
    E(b_cond, "td_d", "ne")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 4, S_SRC)
    a.label("td_d")
    E(ldrb_imm, 0, 4, S_TAG)
    E(cmp_imm, 0, TAG)
    E(b_cond, "td_x", "eq")
    E(movs_imm, 0, TAG)
    E(strb_imm, 0, 4, S_TAG)
    E(bl, "c_tcphoto")
    a.label("td_x")
    E(pop_list, [3, 4, 5, 6], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; the head of the button chain, the end of «apply the record», the LED task calls."""
    import rhbuild
    BASE = rhbuild.BASE
    lab = lambda sec, n: int(report[sec]["labels"][n], 16)
    L = dict(c_rst=lab("rhstate", "c_rst"), c_rrt=lab("rhrec", "c_rrt"), c_ciok=lab("countin", "c_ciok"), c_cinew=lab("countin", "c_cinew"),
             c_skblk=lab("sckn", "c_skblk"), c_skok=lab("sckn", "c_skok"), c_skfix=lab("sckn", "c_skfix"))
    prev = dict(btn=rhbuild.bw_target(img, CI.BTN_ENTRY), load=rhbuild.bw_target(img, PC.LOAD_TAIL), ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, CI.BTN_ENTRY, f"b.w #{prev['btn']:#x}", b_w(CI.BTN_ENTRY, labels["c_tcbtn"]))
    rhbuild.patch(img, PC.LOAD_TAIL, f"b.w #{prev['load']:#x}", b_w(PC.LOAD_TAIL, labels["c_tcload"]))
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_tcled"]))
    report["trkcopy"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
