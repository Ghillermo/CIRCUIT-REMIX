"""The probability view's painter kept inside its 16 pads (MIT; RH104; CIRCUIT-HACKS' paintguard of Beta 5.65, rewritten for the Circuit Rhythm
5706; the user, 2026-11-19: «keep porting Hacks fixes and features»).

The stock of the Rhythm (read in its image): the probability view's listener 0x0805761E(view) (slot 8 of its vtable 0x08067E6C, the word
0x08067E8C; drumpat's rowfix sits in front of it and calls it) repaints row 3 for the selected step (p1 of [[view + 0xC] + 0xC]) when it has a
hit (0x08054AE0): it lights pad k while k <= the step's probability byte (the byte step & 3 of p(8 + step / 4) of the steps' store [[view +
0xC]]; valid 0..7) into the view's 16 LEDs [[view + 4]], without a bound.  A byte of 16 or more writes past those 16 halfwords into what follows
(on the Tracks it was the next view's head, and the next commit that called it hung the unit: Hacks' Alpha 7).  Nothing of ours writes that
byte; the guard is for whatever does.
Ours: the painter's first instruction (`push.w {r4-r8, lr}`) -> c_pgg: the same byte read; above 15 the listener returns without painting,
else the stock's push and on.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import Asm, adds_imm8, b_cond, b_w, bl, cmp_imm, h, ldr_imm, ldrb_imm, lsls_imm, lsrs_imm, mov_reg, movs_imm, pop_list, push_list, raw  # noqa: E402
import countin as CI  # noqa: E402

PAINTER, BODY = 0x0805761E, 0x08057622
MAXB = 15                                                     # the 16 LEDs: k = 0..byte
GET = CI.PARAM_GET


def arm_code(base):
    a = Asm(base)
    E = a.emit
    # ---- c_pgg (in place of the painter's push: r0 = the view): the selected step's probability byte; > 15: back, nothing painted
    a.label("c_pgg")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(ldr_imm, 0, 4, 0xC)
    E(ldr_imm, 0, 0, 0xC)
    E(movs_imm, 1, 1)
    E(bl, GET)
    E(ldrb_imm, 5, 0, 0)                                      # r5 = the selected step
    E(ldr_imm, 0, 4, 0xC)
    E(ldr_imm, 0, 0, 0)                                       # the steps' store
    E(lsrs_imm, 1, 5, 2)
    E(adds_imm8, 1, 8)
    E(bl, GET)
    E(ldr_imm, 0, 0, 0)
    E(lsls_imm, 1, 5, 30)
    E(lsrs_imm, 1, 1, 27)                                     # (step & 3) x 8
    E(raw, h(0x40C8))                                         # lsrs r0, r1
    E(raw, h(0xB2C0))                                         # uxtb r0, r0
    E(cmp_imm, 0, MAXB)
    E(b_cond, "pg_x", "hi")
    E(mov_reg, 0, 4)
    E(raw, h(0xE8BD) + h(0x4070))                             # pop.w {r4, r5, r6, lr}
    E(raw, h(0xE92D) + h(0x41F0))                             # push.w {r4, r5, r6, r7, r8, lr}: the stock's first
    E(b_w, BODY)
    a.label("pg_x")
    E(pop_list, [4, 5, 6], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; the painter's first instruction."""
    import rhbuild
    BASE = rhbuild.BASE
    code, labels = arm_code(base_addr)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, PAINTER, "push.w {r4, r5, r6, r7, r8, lr}", b_w(PAINTER, labels["c_pgg"]))
    report["paintguard"] = dict(labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
