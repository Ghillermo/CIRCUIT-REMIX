"""The Clear LED blinks red while one of our features is off because the firmware is not as expected (MIT; Circuit Rhythm 5706).

A new head of the LED task's chain (the two calls countin takes): after the rest of the chain has drawn the frame, each check of the build
runs; if one fails, the Clear LED is red for 250 ms, then dark for 250 ms.  Checks, each only when its feature is in the build:
  * the RAM block (rhstate's c_rst returns 0): playfix and countin off;
  * countin's c_ciok (the controller and the metronome's owner): countin off;
  * the clock and its vtable (fixedrec's guard): fixedrec off.
Install it after every feature it checks.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from thumb import Asm, b_cond, bl, cmp_imm, cmp_reg, h, ldr_imm, lsls_imm, lsrs_imm, mov_reg, movs_imm, movt, movw, pop_list, push_list, raw  # noqa: E402
import countin  # noqa: E402
import fixedrec  # noqa: E402

LED_CALLS = countin.LED_CALLS
HAL_TICK = countin.HAL_TICK
LED_CLEAR, RED = countin.LED_CLEAR, countin.COL_REC
HALF = 8                                                  # 2^8 ms = 256 ms on, 256 ms off


def arm_code(base, prev, checks):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, v >> 16)

    a.label("c_erled")                                    # r0 = ctrl, r1 = frame
    E(push_list, [3, 4, 5], lr=True)
    E(mov_reg, 5, 1)
    E(bl, prev)
    for kind, addr in checks:
        if kind == "call":                                # r0 = 0 means off
            E(bl, addr)
            E(cmp_imm, 0, 0)
            E(b_cond, "er_on", "eq")
        else:                                             # [addr] must hold the vtable
            imm32(0, addr[0])
            E(ldr_imm, 0, 0, 0)
            imm32(1, addr[1])
            E(cmp_reg, 0, 1)
            E(b_cond, "er_on", "ne")
    E(pop_list, [3, 4, 5], pc=True)
    a.label("er_on")
    imm32(0, HAL_TICK)
    E(ldr_imm, 0, 0, 0)
    E(movs_imm, 1, 0)                                     # before the shifts: movs sets the flags too
    E(lsrs_imm, 0, 0, HALF)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "er_w", "ne")
    E(movs_imm, 1, RED)
    a.label("er_w")
    E(movs_imm, 0, 2 * LED_CLEAR)
    E(raw, h(0x5229))                                     # strh r1, [r5, r0]
    E(pop_list, [3, 4, 5], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    import rh_fw
    import rhbuild
    checks = []
    if "rhstate" in report:
        checks.append(("call", int(report["rhstate"]["labels"]["c_rst"], 16)))
    if "countin" in report:
        checks.append(("call", int(report["countin"]["labels"]["c_ciok"], 16)))
    if "fixedrec" in report:
        checks.append(("vt", (fixedrec.CLOCK, fixedrec.CLOCK_VT)))
    prev = rhbuild.bl_target(img, LED_CALLS[0])
    assert all(rhbuild.bl_target(img, c) == prev for c in LED_CALLS)
    code, labels = arm_code(base_addr, prev, checks)
    img += bytes([0xFF]) * (base_addr - rh_fw.APP_BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    for c in LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev:#x}", bl(c, labels["c_erled"]))
    report["errled"] = dict(prev=hex(prev), checks=[k for k, _ in checks], labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
