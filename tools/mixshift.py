"""In the Mixer, on the levels page, Shift + a knob turned right = that track's level to 100, turned left = 0 (MIT; CIRCUIT-HACKS' mixshift of
SC38, «shift+derecha en un knob establece el canal a 100. Shift+izquierda lo pone a 0», for the Circuit Rhythm 5706).

The stock of the Rhythm (read in the firmware and on the RAM dump, emulated):
  * a knob = 0x0803DDE0(ctrl, knob, delta) -> slot 4 of the active view; the Mixer's (0x2004E090, vtable 0x08067918) = 0x08050D2E -> its knob
    object at + 0x80 (0x0805A296): 0x0805F504(+ 0x80) = a special mode (then its own knobs), else the knob page at + 0xF0;
  * knobs 0-7 move the track's level (the store 0x20012098, parameter t; +5 = +5) or, on the pan page, its pan; the page = p0 of the store at
    view + 0x68 (0 levels, 1 pans: button 19 / 20 in the Mixer); Shift does not change anything (Shift + knob = the plain knob);
  * Clear held = bit 0 of p0 of [view + 0x34] (the held buttons; Clear + knob is the stock's own reset, left alone).
Ours: slot 4 of the Mixer's vtable (in front of the stock): Shift + knob 1-8 on the levels page, not in the special mode and without Clear = a turn of
(target - level) through the stock's handler (its clamp, write, sound and automation recording); already there = nothing.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, b, b_cond, b_w, bl, cmp_imm, ldr_imm, ldrb_imm, lsls_imm, mov_reg, movs_imm, movt, movw, pop_list, push_list,  # noqa: E402
                   raw, h, subs_reg, adds_imm8)
import countin as CI  # noqa: E402
import qmute as QM  # noqa: E402

MIX_VT, MIX_VIEW = QM.MIX_VT, QM.MIX_VIEW
SLOT_KNOB = MIX_VT + 0x10
LEVELS = 0x20012098
O_PAGE, O_HELD, O_KNOBS = 0x68, 0x34, 0x80
SPECIAL = 0x0805F504
LEVEL_UP, LEVEL_DOWN = 100, 0


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_mxsh (the Mixer's slot 4: view, knob, delta)
    a.label("c_mxsh")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(mov_reg, 6, 2)
    E(cmp_imm, 5, 8)
    E(b_cond, "mx_f", "hs")
    E(cmp_imm, 6, 0)
    E(b_cond, "mx_f", "eq")
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "mx_f", "eq")
    E(bl, L["c_cishift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "mx_f", "eq")
    E(mov_reg, 0, 4)
    E(adds_imm8, 0, O_PAGE)
    E(movs_imm, 1, 0)
    E(bl, L["c_cinew"])
    E(cmp_imm, 0, 0)
    E(b_cond, "mx_f", "ne")                                               # the pan page
    E(mov_reg, 0, 4)
    E(adds_imm8, 0, O_KNOBS)
    E(bl, SPECIAL)
    E(cmp_imm, 0, 0)
    E(b_cond, "mx_f", "ne")                                               # the special mode's knobs
    E(ldr_imm, 0, 4, O_HELD)
    E(movs_imm, 1, 0)
    E(bl, L["c_cinew"])
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "mx_f", "mi")                                               # Clear held: the stock's Clear
    E(movs_imm, 7, LEVEL_DOWN)
    E(cmp_imm, 6, 0)
    E(b_cond, "mx_t", "lt")
    E(movs_imm, 7, LEVEL_UP)
    a.label("mx_t")
    imm32(0, LEVELS)
    E(mov_reg, 1, 5)
    E(bl, L["c_cinew"])
    E(subs_reg, 6, 7, 0)                                                  # the turn that lands on the target
    E(b_cond, "mx_f", "ne")
    E(pop_list, [4, 5, 6, 7], pc=True)                                    # already there: nothing
    a.label("mx_f")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(mov_reg, 2, 6)
    E(raw, popw([4, 5, 6, 7], lr=True))
    E(b_w, prev)
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; slot 4 of the Mixer's vtable -> c_mxsh."""
    import rhbuild
    BASE = rhbuild.BASE
    lab = lambda sec, n: int(report[sec]["labels"][n], 16)
    L = dict(c_ciok=lab("countin", "c_ciok"), c_cishift=lab("countin", "c_cishift"), c_cinew=lab("countin", "c_cinew"))
    old = struct.unpack_from("<I", img, SLOT_KNOB - BASE)[0]
    code, labels = arm_code(base_addr, L, old & ~1)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch_word(img, SLOT_KNOB, old, labels["c_mxsh"] | 1)
    report["mixshift"] = dict(mix_slot4=hex(SLOT_KNOB), prev=hex(old & ~1), labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
