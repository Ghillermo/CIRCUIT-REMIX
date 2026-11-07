"""The pads' velocity curve (MIT; CIRCUIT-HACKS' velcurve of SC48 for the Circuit Rhythm 5706; the user, 2026-11-01: «Curva de velocity»).

  * Advanced Setup (the Setup view with byte + 0x24 set), K1: the curve, -8 .. +8, 2 clicks a step; the centre (0) = the stock's response, the
    default.  Right = more sensitive (soft hits come out louder), left = harder; v + c (t - v) / 8, t = 127 - (127 - v)^2 / 127 (right) or v^2 / 127
    (left); 1 .. 127 kept.  K1's LED: dark at the centre, brighter away from it, in one colour (docs/INTERFAZ.md), through kbright's overlay.
  * the pads: the controller's pad entry (word 0 of its vtable 0x080672E4 -> 0x0803D7FE: ctrl, pad, velocity) goes through c_vcpad first: every pad
    hit of every view takes the curve.  The stock's fixed velocity (Shift + Velocity) is applied later, in the views: untouched.
  * saved with the unit's settings: byte 2 of parameter 3 (the stock's comparer only reads byte 0): 0xA0 | (c + 8); anything else = 0.
RAM: rhstate OFF2 "velcurve": + 0 the knob's accumulator (s8).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b, b_cond, b_w, bl, cmp_imm, h, ldr_imm, ldrb_imm, lsls_imm, lsrs_imm, mov_reg, movs_imm, movt,  # noqa: E402
                   movw, muls, orrs_reg, pop_list, push_list, raw, strb_imm, strh_imm, strh_w_imm, subs_imm8, subs_reg)
import countin as CI  # noqa: E402
import midithru as M  # noqa: E402
import pgmch as PG  # noqa: E402
import rhstate  # noqa: E402
import stockplus as SP  # noqa: E402
import usbmerge as UM  # noqa: E402

CTRL_VT, PAD_ENTRY = 0x080672E4, 0x0803D7FE
SETUP_VT = PG.SETUP_VT
KNOB_SLOT = SETUP_VT + 16
P_UNIT, B_CURVE, TAG = 3, 2, 0xA0
CMAX, CLICKS, KNOB = 8, 2, 0
COL = 0x1E                                                 # green, the Advanced view's toggles
O = rhstate.OFF2["velcurve"][0]
O_KB = rhstate.OFF["kbright"][0]
GET, WPTR, COMMIT = CI.PARAM_GET, CI.WPTR, CI.COMMIT


def curve(v, c):
    """the model of c_vcpad"""
    if v <= 0 or c == 0:
        return v
    t = 127 - (127 - v) * (127 - v) * 258 // 32768 if c > 0 else v * v * 258 // 32768
    r = v + abs(c) * (t - v) // 8 if t >= v else v - (abs(c) * (v - t)) // 8
    return max(1, min(127, r))


def popw(regs, lr=False): return UM.popw(regs, lr)


def arm_code(base, L, prev):
    import rhbuild
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_vcget() -> r0 = the curve, -8 .. 8; clobbers r1-r3
    a.label("c_vcget")
    E(push_list, [4], lr=True)
    imm32(0, M.SETTINGS)
    E(movs_imm, 1, P_UNIT)
    E(bl, GET)
    E(ldrb_imm, 0, 0, B_CURVE)
    E(movs_imm, 1, 0)
    E(mov_reg, 2, 0)
    E(subs_imm8, 2, TAG)
    E(cmp_imm, 2, 2 * CMAX)
    E(b_cond, "vg_0", "hi")
    E(subs_imm8, 2, CMAX)
    E(mov_reg, 1, 2)
    a.label("vg_0")
    E(mov_reg, 0, 1)
    E(pop_list, [4], pc=True)

    # ---- c_vcpad (the pad entry: ctrl, pad, velocity): the curve on the velocity
    a.label("c_vcpad")
    E(push_list, [0, 1, 4, 5, 6], lr=True)
    E(mov_reg, 4, 2)                                                      # r4 = v
    E(cmp_imm, 4, 0)
    E(b_cond, "vp_s", "eq")
    E(bl, "c_vcget")
    E(cmp_imm, 0, 0)
    E(b_cond, "vp_s", "eq")
    E(mov_reg, 5, 0)                                                      # r5 = c
    E(b_cond, "vp_n", "mi")
    E(movs_imm, 0, 127)                                                   # right: t = 127 - (127 - v)^2 x 258 >> 15
    E(subs_reg, 0, 0, 4)
    E(mov_reg, 1, 0)
    E(muls, 0, 1)
    E(movw, 1, 258)
    E(muls, 0, 1)
    E(lsrs_imm, 0, 0, 15)
    E(movs_imm, 1, 127)
    E(subs_reg, 6, 1, 0)                                                  # r6 = t
    E(b, "vp_t")
    a.label("vp_n")
    E(raw, h(0x426D))                                                     # negs r5, r5
    E(mov_reg, 0, 4)
    E(muls, 0, 4)
    E(movw, 1, 258)
    E(muls, 0, 1)
    E(lsrs_imm, 6, 0, 15)
    a.label("vp_t")
    E(subs_reg, 0, 6, 4)                                                  # t - v
    E(b_cond, "vp_d", "mi")
    E(muls, 0, 5)
    E(lsrs_imm, 0, 0, 3)
    E(adds_reg, 4, 4, 0)
    E(b, "vp_c")
    a.label("vp_d")
    E(subs_reg, 0, 4, 6)                                                  # v - t
    E(muls, 0, 5)
    E(lsrs_imm, 0, 0, 3)
    E(subs_reg, 4, 4, 0)
    a.label("vp_c")
    E(cmp_imm, 4, 1)
    E(b_cond, "vp_1", "ge")
    E(movs_imm, 4, 1)
    a.label("vp_1")
    E(cmp_imm, 4, 127)
    E(b_cond, "vp_s", "le")
    E(movs_imm, 4, 127)
    a.label("vp_s")
    E(mov_reg, 2, 4)
    E(raw, popw([0, 1, 4, 5, 6], lr=True))
    E(b_w, prev["pad"])

    # ---- c_vcknob (the Setup view's slot 4: view, knob, delta): Advanced Setup, K1
    a.label("c_vcknob")
    E(cmp_imm, 1, KNOB)
    E(b_cond, "vk_s", "ne")
    E(push_list, [0, 1, 2, 3, 4, 5], lr=True)
    E(raw, h(0xF890) + h(0x3024))                                         # ldrb.w r3, [r0, #0x24]
    E(cmp_imm, 3, 0)
    E(b_cond, "vk_p", "eq")                                               # not Advanced
    E(mov_reg, 5, 2)                                                      # r5 = the turn
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "vk_x", "eq")
    E(movw, 1, O)
    E(adds_reg, 4, 0, 1)                                                  # r4 = our RAM
    E(ldrb_imm, 0, 4, 0)
    E(raw, h(0xB240))                                                     # sxtb r0, r0
    E(adds_reg, 0, 0, 5)
    E(cmp_imm, 0, CLICKS)
    E(b_cond, "vk_u", "ge")
    E(movs_imm, 1, CLICKS)
    E(raw, h(0x4249))                                                     # negs r1, r1
    E(raw, h(0x4288))                                                     # cmp r0, r1
    E(b_cond, "vk_d", "le")
    E(strb_imm, 0, 4, 0)
    E(b, "vk_x")
    a.label("vk_u")
    E(movs_imm, 5, 1)
    E(b, "vk_a")
    a.label("vk_d")
    E(movs_imm, 5, 0)
    E(subs_imm8, 5, 1)
    a.label("vk_a")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 4, 0)
    E(bl, "c_vcget")
    E(adds_reg, 0, 0, 5)
    E(cmp_imm, 0, CMAX)
    E(b_cond, "vk_h", "gt")
    E(movs_imm, 1, 0)
    E(subs_imm8, 1, CMAX)
    E(raw, h(0x4288))                                                     # cmp r0, r1
    E(b_cond, "vk_x", "lt")
    E(mov_reg, 5, 0)
    imm32(0, M.SETTINGS)
    E(movs_imm, 1, P_UNIT)
    E(bl, WPTR)
    E(adds_imm8, 5, TAG + CMAX)
    E(strb_imm, 5, 0, B_CURVE)
    imm32(0, M.SETTINGS)
    E(bl, COMMIT)
    a.label("vk_h")
    a.label("vk_x")
    E(pop_list, [0, 1, 2, 3, 4, 5], pc=True)
    a.label("vk_p")
    E(raw, popw([0, 1, 2, 3, 4, 5], lr=True))
    a.label("vk_s")
    E(b_w, prev["knob"])

    # ---- c_vcled (the LED task's calls: ctrl, frame): the chain; Advanced Setup: K1 from the centre
    a.label("c_vcled")
    E(push_list, [3, 4, 5, 6], lr=True)
    E(mov_reg, 5, 1)
    E(bl, prev["ledtask"])
    UM.advanced(E, imm32, L, "vl_x")
    E(bl, "c_vcget")
    E(raw, h(0x17C1))                                                     # asrs r1, r0, #31
    LL = rhbuild.OPT.get("leftlight")
    if LL:                                                                # (RH78, leftlight) r4 = left (the sign)
        E(lsrs_imm, 4, 1, 31)
        E(lsls_imm, 4, 4, 15)
    E(raw, h(0x4048))                                                     # eors r0, r1
    E(raw, h(0x1A40))                                                     # subs r0, r0, r1: |c|
    E(movs_imm, 1, 127)
    E(muls, 0, 1)
    E(lsrs_imm, 6, 0, 3)                                                  # r6 = the brightness
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "vl_x", "eq")
    E(movw, 1, O_KB)
    E(adds_reg, 0, 0, 1)
    E(ldrb_imm, 1, 0, SP.K_MASK)
    E(movs_imm, 2, 1 << KNOB)
    E(raw, h(0x4311))                                                     # orrs r1, r2
    E(strb_imm, 1, 0, SP.K_MASK)
    E(strb_imm, 6, 0, SP.K_VAL + KNOB)
    E(movs_imm, 1, COL)
    if LL:
        E(orrs_reg, 4, 1)
        E(strh_imm, 4, 0, SP.K_CODE + 2 * KNOB)
    else:
        E(strh_imm, 1, 0, SP.K_CODE + 2 * KNOB)
    E(strh_w_imm, 1, 5, 2 * (SP.LED_KNOB0 + KNOB))
    a.label("vl_x")
    E(pop_list, [3, 4, 5, 6], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """The pad entry's vtable word, the head of the Setup view's slot 4, the head of the LED calls.  Needs kbright, rhstate ram2, usbmerge's
    helpers, setsave with its byte (OPT setp3)."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]                 # noqa: E731
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    assert u(CTRL_VT) == PAD_ENTRY | 1
    L = dict(c_rram=lab("rhstate", "c_rram"), c_rst=lab("rhstate", "c_rst"), c_ciok=lab("countin", "c_ciok"), c_cinew=lab("countin", "c_cinew"))
    prev = dict(pad=PAD_ENTRY, knob=u(KNOB_SLOT) & ~1, ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch_word(img, CTRL_VT, PAD_ENTRY | 1, labels["c_vcpad"] | 1)
    rhbuild.patch_word(img, KNOB_SLOT, prev["knob"] | 1, labels["c_vcknob"] | 1)
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_vcled"]))
    report["velcurve"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
