"""The device settings saved when only our bits of parameter 2 change (MIT; RH46).

The stock (read in the Rhythm's image): the device settings 0x20012478 are saved by their listener (the object 0x2003CD88, vtable 0x08068F6C:
0x08035698) when 0x0803571E finds them changed: it compares parameter 0's byte 0, the bytes 0 of parameters 3..10 and bits 0..19 of parameter 2
(`ubfx #0, #0x14`), and a block of its own; the save is 0x080356D0(obj) (the 11 parameters copied whole, then queued for the storage task).
So bits 20..31 of parameter 2 (ours: pgmch's channels 20..27, usbmerge 28, arpext 29, midithru's Merge / Filter 30 / 31) reach the unit's
memory only when something of the stock changes at the same time.  Ours: the LED task keeps the last bits 20..31 it saw (rhstate OFF2
"setsave": + 0 the bits, + 4 0x5E when known); when they change, with the transport stopped, it calls the stock's save 0x080356D0(obj)
(after checking the object's vtable and its store).  The first frame only takes them (no save).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_reg, h, raw, b_cond, bl, cmp_imm, cmp_reg, ldr_imm, ldrb_imm, lsls_imm, lsrs_imm, mov_reg, movs_imm, movt, movw,  # noqa: E402
                   pop_list, push_list, str_imm, strb_imm)
import countin as CI  # noqa: E402
import midithru as M  # noqa: E402
import rhstate  # noqa: E402

SAVER, SAVER_VT, SAVE = 0x2003CD88, 0x08068F6C, 0x080356D0
O_STORE = 0xB0
SETTINGS = M.SETTINGS
O = rhstate.OFF2["setsave"][0]
KNOWN = 0x5E
GET, TRANSPORT = CI.PARAM_GET, CI.TRANSPORT


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_ssled (the LED task's calls: ctrl, frame): the chain, then the save when bits 20..31 of parameter 2 changed
    a.label("c_ssled")
    E(push_list, [3, 4, 5, 6], lr=True)
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ss_x", "eq")
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ss_x", "eq")
    E(movw, 1, O)
    E(adds_reg, 4, 0, 1)                                                  # r4 = our RAM
    imm32(0, SETTINGS)
    E(movs_imm, 1, 2)
    E(bl, GET)
    E(ldr_imm, 5, 0, 0)
    E(lsrs_imm, 5, 5, 20)
    E(lsls_imm, 5, 5, 20)                                                 # r5 = bits 20..31
    E(ldrb_imm, 0, 4, 4)
    E(cmp_imm, 0, KNOWN)
    E(b_cond, "ss_k", "eq")
    E(movs_imm, 0, KNOWN)                                                 # the first: taken
    E(strb_imm, 0, 4, 4)
    E(str_imm, 5, 4, 0)
    E(pop_list, [3, 4, 5, 6], pc=True)
    a.label("ss_k")
    E(ldr_imm, 0, 4, 0)
    E(cmp_reg, 0, 5)
    E(b_cond, "ss_x", "eq")
    imm32(0, TRANSPORT)
    E(movs_imm, 1, 0)
    E(bl, GET)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "ss_x", "ne")                                               # playing: later
    imm32(6, SAVER)
    E(ldr_imm, 0, 6, 0)
    imm32(1, SAVER_VT)
    E(cmp_reg, 0, 1)
    E(b_cond, "ss_x", "ne")
    E(raw, h(0xF8D0 | 6) + h(0 << 12 | O_STORE))                         # ldr.w r0, [r6, #0xb0]: its store
    imm32(1, SETTINGS)
    E(cmp_reg, 0, 1)
    E(b_cond, "ss_x", "ne")
    E(str_imm, 5, 4, 0)
    E(mov_reg, 0, 6)
    E(bl, SAVE)
    a.label("ss_x")
    E(pop_list, [3, 4, 5, 6], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """The head of the LED calls.  Needs rhstate ram2 and countin."""
    import rhbuild
    BASE = rhbuild.BASE
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    L = dict(c_ciok=lab("countin", "c_ciok"), c_rram=lab("rhstate", "c_rram"))
    prev = dict(ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_ssled"]))
    report["setsave"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
