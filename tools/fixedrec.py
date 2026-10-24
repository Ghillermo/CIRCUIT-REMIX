"""Fixed Recording at the external MIDI clock's tempo (MIT; Circuit Rhythm 5706).

The stock takes the Fixed Recording length from word 0 of the tempo store, the BPM set on the device; with an external
clock the measured BPM is word 1 (written by the clock tick 0x08032430 about once a beat) and word 0 keeps the old tempo.
The two reads, each `ldr r0, [r4, #0x10]; movs r1, #0; bl GET`:
  * 0x0803CEA0 in 0x0803CE98: target samples 720000 x {8, 16, 32, 64} / BPM and the stop timer 15000 x n / BPM + 50 ms,
    computed once when the sampler's state becomes 3 (recording);
  * 0x08058FE0 in 0x08058F9C: the length in ms, {120000, 240000, 480000, 960000} / BPM.
Both `bl GET` -> `bl c_frbpm`, which returns &word 1 when the store is the clock's tempo store (clock 0x200126E8 with its
vtable), the clock's external-clock store (+0x48) word 0 is set and word 1 is 40..240; otherwise &word 0, as the stock.
Test: tools/emu_fixedrec.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import Asm, b_cond, bl, cmp_imm, cmp_reg, ldr_imm, ldrb_imm, mov_reg, movs_imm, movt, movw, pop_list, push_list, subs_imm8  # noqa: E402

GET = 0x0803FC58
CALLS = (0x0803CEA0, 0x08058FE0)
CLOCK, CLOCK_VT = 0x200126E8, 0x08068EFC
CLK_TEMPO, CLK_EXT = 0x14, 0x48
BPM_MIN, BPM_MAX = 40, 240


def arm_code(base):
    a = Asm(base)

    def imm32(rd, v):
        a.emit(movw, rd, v & 0xFFFF)
        a.emit(movt, rd, v >> 16)

    a.label("c_frbpm")                                  # r0 = store, r1 = 0 -> r0 = &BPM word
    a.emit(push_list, [4, 5, 6], lr=True)
    a.emit(mov_reg, 4, 0)
    imm32(5, CLOCK)
    a.emit(ldr_imm, 2, 5, 0)
    imm32(3, CLOCK_VT)
    a.emit(cmp_reg, 2, 3)
    a.emit(b_cond, "fr_stock", "ne")
    a.emit(ldr_imm, 2, 5, CLK_TEMPO)
    a.emit(cmp_reg, 2, 4)
    a.emit(b_cond, "fr_stock", "ne")
    a.emit(ldr_imm, 0, 5, CLK_EXT)
    a.emit(movs_imm, 1, 0)
    a.emit(bl, GET)
    a.emit(ldrb_imm, 0, 0, 0)
    a.emit(cmp_imm, 0, 0)
    a.emit(b_cond, "fr_stock", "eq")
    a.emit(mov_reg, 0, 4)
    a.emit(movs_imm, 1, 1)
    a.emit(bl, GET)
    a.emit(ldrb_imm, 2, 0, 0)
    a.emit(subs_imm8, 2, BPM_MIN)
    a.emit(cmp_imm, 2, BPM_MAX - BPM_MIN)
    a.emit(b_cond, "fr_stock", "hi")
    a.emit(pop_list, [4, 5, 6], pc=True)
    a.label("fr_stock")
    a.emit(mov_reg, 0, 4)
    a.emit(movs_imm, 1, 0)
    a.emit(bl, GET)
    a.emit(pop_list, [4, 5, 6], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    import rh_fw
    import rhbuild
    BASE = rh_fw.APP_BASE
    code, labels = arm_code(base_addr)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    for site in CALLS:
        rhbuild.patch(img, site, f"bl #{GET:#x}", bl(site, labels["c_frbpm"]))
    report["fixedrec"] = dict(calls=[hex(c) for c in CALLS], labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
