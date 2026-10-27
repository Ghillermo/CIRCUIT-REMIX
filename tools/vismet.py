"""A visual metronome: the Clear LED flashes on each click that cannot be heard (MIT; Circuit Rhythm 5706).

The click's level is knob K5 of the Tempo / Swing view, master parameter 9 (the getter 0x08046410(0x21, 9), 0..127), which the stock
reads on each click (0x08030D72).  At level 0, each count-in click, and each beat while playing with the metronome or the count-in on,
keeps its HAL tick in our RAM block, and the LED task lights Clear in the mode's colour (countin's: green metronome, magenta count-in
only, cyan both) for 100 ms.  Red (no metronome, no count-in) never flashes.  While Shift or Clear is held the stock's and countin's Clear LED is left alone.
  * c_vmbeat, at the entry of the stock's beat check 0x080333AA(obj) (called on the clock's pulses; [[obj + 8] + 0x20] = the pulse,
    a beat every 24; [obj + 0xC] p3 = the metronome): it runs in the clock's task, so it only uses a block that is already set up.
  * c_vmclick, at countin's click: the same, then clicks.
  * c_vmled, a new head of the LED task's chain.
RAM: our block's slot "vismet": the last silent beat or click (HAL tick, 0 = none).
Install after countin and before errled, so the error blink wins.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from thumb import (Asm, b, b_cond, b_w, bl, cmp_imm, cmp_reg, h, ldr_imm, ldrb_imm, ldrb_w, mov_reg, movs_imm, movt, movw, muls, pop_list,  # noqa: E402
                   push_list, raw, str_imm, subs_reg, tst_reg)
import countin as C  # noqa: E402
import rhstate  # noqa: E402

LIMIT = getattr(rhstate, "OUR_LIMIT", rhstate.ST)        # the heap limit once our block is set up (Circuit Remix: its second block)

BEAT_FN, BEAT_EXPECT, BEAT_OLD = 0x080333AA, "push {r3, r4, r5, lr}|mov r4, r0", bytes.fromhex("38b50446")
GET, GETTER = 0x0803FC58, 0x08046410
GRP_MASTER, IDX_CLICK = 0x21, 9
FLASH_MS = 100
HELD, CLEAR_BIT = 0xA0, 1 << C.ID_CLEAR            # [ctrl + 0xA0]: the buttons held, bit = button id
PULSES = 24


def find_click(img, report):
    """countin's `bl CLICK` (the count's click)."""
    import capstone
    import rh_fw
    lo = int(report["countin"]["base"], 16)
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    hits = [i.address for i in md.disasm(bytes(img[lo - rh_fw.APP_BASE:lo - rh_fw.APP_BASE + 0x400]), lo)
            if i.mnemonic == "bl" and i.op_str == f"#{C.CLICK:#x}"]
    assert len(hits) == 1, hits
    return hits[0]


def arm_code(base, prev_led, L):
    slot = rhstate.OFF["vismet"][0]
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, v >> 16)

    def block(rd, s1, s2, out):                           # rd = our block, or branch to out when it is not set up
        imm32(rd, rhstate.ST)
        imm32(s1, rhstate.HEAP_LIMIT_PTR)
        E(ldr_imm, s1, s1, 0)
        if LIMIT == rhstate.ST:
            E(cmp_reg, s1, rd)
        else:
            imm32(s2, LIMIT)
            E(cmp_reg, s1, s2)
        E(b_cond, out, "ne")
        E(ldr_imm, s1, rd, 0)
        imm32(s2, rhstate.MAGIC)
        E(cmp_reg, s1, s2)
        E(b_cond, out, "ne")

    def ldw(rt, rn, off):                                 # LDR, or LDR.W Rt, [Rn, #imm12] past the narrow form's 124
        E(ldr_imm, rt, rn, off) if off < 128 else E(raw, h(0xF8D0 | rn) + h(rt << 12 | off))

    def stw(rt, rn, off):
        E(str_imm, rt, rn, off) if off < 128 else E(raw, h(0xF8C0 | rn) + h(rt << 12 | off))

    def silent_tick(blk, tag, out):                       # click level 0: [blk + slot] = the HAL tick (never 0); clobbers r0-r3
        E(movs_imm, 0, GRP_MASTER)
        E(movs_imm, 1, IDX_CLICK)
        E(bl, GETTER)
        E(cmp_imm, 0, 0)
        E(b_cond, out, "ne")
        imm32(0, C.HAL_TICK)
        E(ldr_imm, 0, 0, 0)
        E(cmp_imm, 0, 0)
        E(b_cond, tag, "ne")
        E(movs_imm, 0, 1)
        a.label(tag)
        stw(0, blk, slot)

    # ---- the stock's beat check, unchanged
    a.label("c_vmbeat_stock")
    E(raw, BEAT_OLD)
    E(b_w, BEAT_FN + 4)

    # ---- c_vmbeat(r0 = obj): a beat with the metronome or the count-in on and the click at 0 -> its time
    a.label("c_vmbeat")
    E(push_list, [0, 1, 2, 3, 4, 5, 6], lr=True)          # 8 words: the stack stays 8-byte aligned
    E(mov_reg, 5, 0)
    block(4, 1, 2, "vb_x")
    E(ldr_imm, 1, 5, 8)
    E(ldrb_w, 1, 1, 0x20)                                 # the pulse
    E(movs_imm, 2, PULSES)
    E(raw, C.udiv(3, 1, 2))
    E(muls, 3, 2)
    E(subs_reg, 1, 1, 3)
    E(b_cond, "vb_x", "ne")                               # not a beat
    E(ldr_imm, 0, 5, 0xC)
    E(movs_imm, 1, 3)
    E(bl, GET)
    E(ldrb_imm, 0, 0, 0)
    E(movs_imm, 1, 1)
    E(raw, h(0x4008))                                     # ands r0, r1
    E(b_cond, "vb_on", "ne")
    E(ldrb_imm, 0, 4, C.O_FLAG)
    E(cmp_imm, 0, C.CI_ON)
    E(b_cond, "vb_x", "ne")                               # neither the metronome nor the count-in
    a.label("vb_on")
    silent_tick(4, "vb_t", "vb_x")
    a.label("vb_x")
    E(raw, C.popw([0, 1, 2, 3, 4, 5, 6], lr=True))
    E(b, "c_vmbeat_stock")

    # ---- c_vmclick: countin's click (r0-r2 its arguments, kept)
    a.label("c_vmclick")
    E(push_list, [0, 1, 2, 4, 5], lr=True)
    block(4, 1, 2, "vc_go")
    silent_tick(4, "vc_t", "vc_go")
    a.label("vc_go")
    E(raw, C.popw([0, 1, 2, 4, 5], lr=True))
    E(b_w, C.CLICK)

    # ---- c_vmled (r0 = ctrl, r1 = frame): Shift and Clear up, a silent beat or click within 100 ms -> Clear in the mode's colour
    a.label("c_vmled")
    E(push_list, [3, 4, 5], lr=True)
    E(mov_reg, 5, 1)
    E(bl, prev_led)
    block(4, 1, 2, "vl_x")
    E(bl, L["c_cishift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "vl_x", "ne")
    imm32(0, C.CTRL + HELD)
    E(ldr_imm, 0, 0, 0)
    imm32(1, CLEAR_BIT)
    E(tst_reg, 0, 1)
    E(b_cond, "vl_x", "ne")                               # Clear held
    ldw(1, 4, slot)
    E(cmp_imm, 1, 0)
    E(b_cond, "vl_x", "eq")
    imm32(0, C.HAL_TICK)
    E(ldr_imm, 0, 0, 0)
    E(subs_reg, 0, 0, 1)
    E(cmp_imm, 0, FLASH_MS)
    E(b_cond, "vl_x", "hs")
    E(mov_reg, 0, 4)
    E(bl, L["c_cistate"])                                 # 0..3
    for m in (1, 2, 3):
        E(movs_imm, 1, C.COLS[m])
        E(cmp_imm, 0, m)
        E(b_cond, "vl_w", "eq")
    E(b, "vl_x")                                          # red: no flash
    a.label("vl_w")
    E(movs_imm, 0, 2 * C.LED_CLEAR)
    E(raw, h(0x5229))                                     # strh r1, [r5, r0]
    a.label("vl_x")
    E(pop_list, [3, 4, 5], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    import rh_fw
    import rhbuild
    BASE = rh_fw.APP_BASE
    prev_led = rhbuild.bl_target(img, C.LED_CALLS[0])
    assert all(rhbuild.bl_target(img, c) == prev_led for c in C.LED_CALLS)
    assert bytes(img[BEAT_FN - BASE:BEAT_FN - BASE + 4]) == BEAT_OLD
    L = {k: int(v, 16) for k, v in report["countin"]["labels"].items()}
    count_click = find_click(img, report)
    code, labels = arm_code(base_addr, prev_led, L)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, BEAT_FN, BEAT_EXPECT, b_w(BEAT_FN, labels["c_vmbeat"]))
    rhbuild.patch(img, count_click, f"bl #{C.CLICK:#x}", bl(count_click, labels["c_vmclick"]))
    for c in C.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev_led:#x}", bl(c, labels["c_vmled"]))
    report["vismet"] = dict(slot=hex(rhstate.ST + rhstate.OFF["vismet"][0]), count_click=hex(count_click), prev_led=hex(prev_led),
                            labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
