"""Shift + a track pad in the Mixer = that track's mute toggled on the next bar (MIT; CIRCUIT-HACKS' qmute of SC43.4, for the Circuit Rhythm 5706).

The stock of the Rhythm (read in the firmware and on the RAM dump, emulated):
  * the Mixer = button 14 -> the view 0x2004E090 (vtable 0x08067918; [ctrl + 0x7C] while it shows); its slot 0 = 0x08050C38(view, pad, velocity):
    pads 0-7 toggle the track's mute (the store [[view + 0x1D8] + [view + 0x1D0] x pad], parameter 0, then the commit 0x0803FBEC); it does not
    look at Shift (Shift + pad = the same toggle); pads 16-31 go to a sub-object; LEDs 0-7 of the frame = pads 0-7;
  * the clock 0x2003C200: [clock + 8] = 0x200126E8, whose byte + 0x20 counts the ticks of the bar, 0..95 (0x08032800: + 1, 96 -> 0; the metronome
    clicks when it is a multiple of 24, 0x080333AA); Play sets it to 0 (emulated), so the bar starts with the transport.

Ours:
  * the Mixer's slot 0 (in front of the stock): Shift + pads 1-8 = that track's bit in a pending mask (again = cancel); the press goes no further;
  * the LED task: stopped, the pending toggles at once; playing, when the bar's tick reaches 95 (one tick early, so the downbeat already plays or
    is already silent; when the task missed 95, at the wrap), each through the stock's own handler (pad, velocity 127);
  * while the Mixer shows, the pending pads blink (dark every other 256 ms).
The mask lives in rhstate (RAM): a toggle pending when another project is loaded during playback applies to it on the next bar.
Every entry checks the controller (countin's c_ciok), the Mixer's vtable and the clock object; otherwise the stock path, untouched.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, b, b_cond, b_w, bl, cmp_imm, cmp_reg, h, ldr_imm, ldr_sp, ldrb_imm, ldrb_w, lsls_imm, lsrs_imm, lsrs_reg,  # noqa: E402
                   mov_reg, movs_imm, movt, movw, pop_list, push_list, raw, strb_imm)
import countin as CI  # noqa: E402
import rhstate  # noqa: E402

CTRL = CI.CTRL
MIX_VIEW, MIX_VT = 0x2004E090, 0x08067918
CLOCK, CLK_OBJ, BAR_TICK = 0x2003C200, 0x200126E8, 0x20
TICKS_BAR = 96
O_M, O_L = rhstate.OFF["qmute"][0], rhstate.OFF["qmute"][0] + 1
HAL_TICK = CI.HAL_TICK
LED_CALLS = CI.LED_CALLS


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_qmmix() -> r0 = 1 when the Mixer view is the dump's; clobbers r1
    a.label("c_qmmix")
    imm32(0, MIX_VIEW)
    E(ldr_imm, 0, 0, 0)
    imm32(1, MIX_VT)
    E(cmp_reg, 0, 1)
    E(movs_imm, 0, 0)
    E(b_cond, "mm_x", "ne")
    E(movs_imm, 0, 1)
    a.label("mm_x")
    E(raw, h(0x4770))

    # ---- c_qmpad (the Mixer view's slot 0: view, pad, velocity): Shift + pads 1-8 = queue / cancel that track's toggle
    a.label("c_qmpad")
    E(cmp_imm, 1, 8)
    E(b_cond, "qp_f", "hs")
    E(push_list, [0, 1, 2, 3, 4], lr=True)
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "qp_p", "eq")
    E(mov_reg, 4, 0)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "qp_p", "eq")
    E(bl, L["c_cishift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "qp_p", "eq")
    E(ldr_sp, 1, 4)                                                       # the pad
    E(movs_imm, 0, 1)
    E(raw, h(0x4088))                                                     # lsls r0, r1
    E(ldrb_imm, 1, 4, O_M)
    E(raw, h(0x4041))                                                     # eors r1, r0
    E(strb_imm, 1, 4, O_M)
    E(pop_list, [0, 1, 2, 3, 4], pc=True)
    a.label("qp_p")
    E(raw, popw([0, 1, 2, 3, 4], lr=True))
    a.label("qp_f")
    E(b_w, prev["pad"])

    # ---- c_qmdo(r0 = our block): the pending toggles through the stock's handler; clobbers r0-r3
    a.label("c_qmdo")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 6, 0)
    E(ldrb_imm, 4, 6, O_M)
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 6, O_M)
    E(bl, "c_qmmix")
    E(cmp_imm, 0, 0)
    E(b_cond, "qd_x", "eq")
    E(movs_imm, 5, 0)
    a.label("qd_l")
    E(mov_reg, 0, 4)
    E(lsrs_reg, 0, 5)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "qd_n", "pl")
    imm32(0, MIX_VIEW)
    E(mov_reg, 1, 5)
    E(movs_imm, 2, 127)
    E(bl, prev["pad"])
    a.label("qd_n")
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, 8)
    E(b_cond, "qd_l", "lo")
    a.label("qd_x")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_qmled (the LED task's calls: r0 = ctrl, r1 = frame): the chain; the bar; the blinking pads
    a.label("c_qmled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)
    E(bl, prev["ledtask"])
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ql_x", "eq")
    E(mov_reg, 4, 0)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ql_x", "eq")
    imm32(0, CI.TRANSPORT)
    E(movs_imm, 1, 0)
    E(bl, L["c_cinew"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ql_p", "ne")
    E(movs_imm, 0, 0xFF)                                                  # stopped: at once
    E(strb_imm, 0, 4, O_L)
    E(b, "ql_do")
    a.label("ql_p")
    imm32(0, CLOCK)
    E(ldr_imm, 0, 0, 8)
    imm32(1, CLK_OBJ)
    E(cmp_reg, 0, 1)
    E(b_cond, "ql_l", "ne")
    E(ldrb_w, 6, 0, BAR_TICK)                                             # r6 = the bar's tick
    E(ldrb_imm, 7, 4, O_L)                                                # r7 = the last one seen
    E(strb_imm, 6, 4, O_L)
    E(cmp_imm, 7, TICKS_BAR - 1)
    E(b_cond, "ql_l", "eq")                                               # done at 95 already
    E(cmp_imm, 6, TICKS_BAR - 1)
    E(b_cond, "ql_do", "eq")
    E(cmp_imm, 7, 0xFF)
    E(b_cond, "ql_l", "eq")                                               # just started
    E(cmp_reg, 6, 7)
    E(b_cond, "ql_l", "hs")
    a.label("ql_do")                                                      # 95 reached, or the bar wrapped
    E(ldrb_imm, 0, 4, O_M)
    E(cmp_imm, 0, 0)
    E(b_cond, "ql_l", "eq")
    E(mov_reg, 0, 4)
    E(bl, "c_qmdo")
    a.label("ql_l")                                                       # the Mixer on the screen: the pending pads blink
    E(ldrb_imm, 6, 4, O_M)
    E(cmp_imm, 6, 0)
    E(b_cond, "ql_x", "eq")
    imm32(0, CTRL)
    E(ldr_imm, 0, 0, 0x7C)
    imm32(1, MIX_VIEW)
    E(cmp_reg, 0, 1)
    E(b_cond, "ql_x", "ne")
    imm32(0, HAL_TICK)
    E(ldr_imm, 0, 0, 0)
    E(lsrs_imm, 0, 0, 8)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "ql_x", "pl")
    E(movs_imm, 7, 0)
    a.label("ql_b")
    E(mov_reg, 0, 6)
    E(lsrs_reg, 0, 7)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "ql_bn", "pl")
    E(lsls_imm, 1, 7, 1)
    E(movs_imm, 0, 0)
    E(raw, h(0x5268))                                                     # strh r0, [r5, r1]
    a.label("ql_bn")
    E(adds_imm8, 7, 1)
    E(cmp_imm, 7, 8)
    E(b_cond, "ql_b", "lo")
    a.label("ql_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; slot 0 of the Mixer's vtable, the two LED task calls."""
    import rhbuild
    BASE = rhbuild.BASE
    lab = lambda sec, n: int(report[sec]["labels"][n], 16)
    L = dict(c_rst=lab("rhstate", "c_rst"), c_ciok=lab("countin", "c_ciok"), c_cishift=lab("countin", "c_cishift"),
             c_cinew=lab("countin", "c_cinew"))
    old = struct.unpack_from("<I", img, MIX_VT - BASE)[0]
    prev = dict(pad=old & ~1, ledtask=rhbuild.bl_target(img, LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in LED_CALLS)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch_word(img, MIX_VT, old, labels["c_qmpad"] | 1)
    for c in LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_qmled"]))
    report["qmute"] = dict(mix_slot0=hex(MIX_VT), led_calls=[hex(c) for c in LED_CALLS],
                           prev={k: hex(v) for k, v in prev.items()},
                           labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
