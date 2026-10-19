"""Our knobs' values as brightness (MIT; for the Circuit Rhythm 5706).  The user (2026-10-19): «fx shift knobs dont show value with brightness»,
«same brightness issue with sidechain and comp».

The stock of the Rhythm (read in the firmware, emulated): the LED task writes colour codes into the frame (69 halfwords); the output stage
0x0803E8E6(ctrl, out, frame) (called at 0x0803E802; not in the Tracks, whose frame halfwords carry a brightness byte) turns them into RGB words:
  * colour = the RAM table 0x20003974 (B, G, R words) at the code;
  * only for the knob LEDs (60-68) and codes >= 0xE9: a brightness from the table 0x20003794 (2 bytes a code: an index into the stores at
    [ctrl + 0x1F4], a parameter): the eight knobs of the eight tracks, the Mixer's sends and levels and a few more; the bipolar ones as |v - 64|;
    then 0x08052122(&rgb, b): each channel x (0x1CC b + 0x1A00) >> 16 (b = 0..127: ~10 % .. 100 %), b / 2 when bit 10 of p2 of [ctrl + 0x88]
    is set (the stock's dimmed LEDs);
  * so a code of ours is shown at full brightness, and the stock's value codes show the stock's parameters: no code reaches the side-chain,
    the compressor or the reverb / delay parameters.

Ours: an overlay in our RAM (rhstate "kbright": [0] the knobs to take (bit k), [1..8] their values 0..127, [10..25] their colour codes) that
a module's LED code fills for the frame it draws (sckn, fxkeys with bright=True); this module empties it before the LED task builds a frame
(the outermost of the LED task calls) and, after the stock's output stage, puts those knobs' colour scaled by their value, as the stock does.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b_cond, b_w, bl, cmp_imm, h, ldr_imm, ldrb_imm, lsls_imm, lsrs_imm, mov_reg, movs_imm, movt,  # noqa: E402
                   movw, pop_list, push_list, raw, str_imm, strb_imm, tst_reg, sub_sp_imm, add_sp_imm, ldr_sp, str_sp)
import countin as CI  # noqa: E402
import rhstate  # noqa: E402

OUT_CALL, OUT_STAGE = 0x0803E802, 0x0803E8E6
SCALE = 0x08052122
COLOURS = 0x20003974
PARAM_GET = CI.PARAM_GET
O_DIM, P_DIM, BIT_DIM = 0x88, 2, 10
LED_KNOB0 = 60
O_KB = rhstate.OFF["kbright"][0]
K_MASK, K_VAL, K_CODE = 0, 1, 10


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_kbblk() -> r0 = the overlay, 0 without our RAM; clobbers r1-r3
    a.label("c_kbblk")
    E(push_list, [4], lr=True)
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "kb_x", "eq")
    E(adds_imm8, 0, O_KB)
    a.label("kb_x")
    E(pop_list, [4], pc=True)

    # ---- c_kbled (the LED task's calls: ctrl, frame): the overlay emptied for the frame about to be built, then the chain
    a.label("c_kbled")
    E(push_list, [0, 1, 2, 3, 4], lr=True)
    E(bl, "c_kbblk")
    E(cmp_imm, 0, 0)
    E(b_cond, "kl_c", "eq")
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 0, K_MASK)
    a.label("kl_c")
    E(raw, popw([0, 1, 2, 3, 4], lr=True))
    E(b_w, prev["ledtask"])

    # ---- c_kbout (in place of the stock's call of its output stage: ctrl, out, frame): the stage, then the overlay's knobs
    a.label("c_kbout")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(sub_sp_imm, 8)
    E(mov_reg, 4, 0)                                                       # r4 = ctrl
    E(mov_reg, 5, 1)                                                       # r5 = the RGB words out
    E(bl, OUT_STAGE)
    E(bl, "c_kbblk")
    E(cmp_imm, 0, 0)
    E(b_cond, "ko_x", "eq")
    E(mov_reg, 6, 0)                                                       # r6 = the overlay
    E(ldrb_imm, 0, 6, K_MASK)
    E(cmp_imm, 0, 0)
    E(b_cond, "ko_x", "eq")
    E(mov_reg, 0, 4)                                                       # the stock's dimmed LEDs: bit 10 of p2 of [ctrl + 0x88]
    E(adds_imm8, 0, O_DIM)
    E(ldr_imm, 0, 0, 0)
    E(movs_imm, 1, P_DIM)
    E(bl, PARAM_GET)
    E(ldr_imm, 0, 0, 0)
    E(lsrs_imm, 0, 0, BIT_DIM)
    E(movs_imm, 1, 1)
    E(raw, h(0x4008))                                                      # ands r0, r1
    E(str_sp, 0, 4)                                                        # [sp + 4] = dimmed
    E(movs_imm, 7, 0)
    a.label("ko_k")
    E(ldrb_imm, 0, 6, K_MASK)
    E(movs_imm, 1, 1)
    E(raw, h(0x40B9))                                                      # lsls r1, r7
    E(tst_reg, 0, 1)
    E(b_cond, "ko_n", "eq")
    E(lsls_imm, 0, 7, 1)
    E(adds_reg, 0, 0, 6)
    E(raw, h(0x8940))                                                      # ldrh r0, [r0, #10]: the colour code
    imm32(1, COLOURS)
    E(lsls_imm, 0, 0, 2)
    E(raw, h(0x5808))                                                      # ldr r0, [r1, r0]
    E(str_sp, 0, 0)                                                        # [sp] = its RGB
    E(adds_reg, 0, 6, 7)
    E(ldrb_imm, 1, 0, K_VAL)                                               # r1 = the value
    E(ldr_sp, 0, 4)
    E(cmp_imm, 0, 0)
    E(b_cond, "ko_d", "eq")
    E(lsrs_imm, 1, 1, 1)
    a.label("ko_d")
    E(mov_reg, 0, 13)
    E(bl, SCALE)
    E(ldr_sp, 0, 0)
    E(adds_imm8, 7, LED_KNOB0)
    E(lsls_imm, 1, 7, 2)
    E(raw, h(0x5068))                                                      # str r0, [r5, r1]
    E(movs_imm, 0, LED_KNOB0)
    E(raw, h(0x1A3F))                                                      # subs r7, r7, r0
    a.label("ko_n")
    E(adds_imm8, 7, 1)
    E(cmp_imm, 7, 8)
    E(b_cond, "ko_k", "lo")
    a.label("ko_x")
    E(add_sp_imm, 8)
    E(pop_list, [4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; the call of the output stage, the two LED task calls (outermost)."""
    import rhbuild
    BASE = rhbuild.BASE
    L = dict(c_rst=int(report["rhstate"]["labels"]["c_rst"], 16))
    prev = dict(ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, OUT_CALL, f"bl #{OUT_STAGE:#x}", bl(OUT_CALL, labels["c_kbout"]))
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_kbled"]))
    report["kbright"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
