"""Pattern Settings: Clear + pad 25 = the pattern's dynamics and mutate cleared (MIT; RH46, as CIRCUIT-HACKS' Clear + pad 25 of Beta 1.16).

drumpat's byte of each step (the pattern + 0x108 + step, read only in a project marked "DQ"): bits 0-2 the dynamics, 3-5 the frequency - 1,
6-7 the mutate.  Ours: in Pattern Settings (a view per track, 0x2004C4B8 + 0x60 t, vtable 0x08067EA4, slot 0 = its pads), Clear held + pad 25
clears bits 0-2 and 6-7 of the 32 bytes of the pattern the track shows (its ST1: [[0x2004C7B8 + 0x40 t + 0xC]], [ST1 + 0x18] = the pattern +
0x128); the frequency stays.  The press does not reach the stock (Clear + pad 25 does nothing there) nor drumpat's pad 25 (the probability
view in mode 2).  Nothing in a project not marked.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b_cond, b_w, bl, cmp_imm, h, ldr_imm, movs_imm, movt, movw, muls, pop_list, push_list, raw,  # noqa: E402
                   subs_reg, tst_reg)
import countin as CI  # noqa: E402
import drumpat as DP  # noqa: E402
import playmode as PM  # noqa: E402

PS0, PS_SZ, PS_VT = PM.PS0, PM.PS_SZ, PM.PS_VT
PROB0, PROB_SZ = DP.PROB0, DP.PROB_SZ
PAD = DP.PS_PAD
O_HELD, B_CLEAR = 0xA0, 23
KEEP = 0x38                                               # the frequency's bits
DQ_FROM_LANES = DP.LANES_OFF - DP.DQ_OFF                  # the step bytes = [ST1 + 0x18] - 0x20


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))
def udiv(rd, rn, rm): return h(0xFBB0 | rn) + h(0xF0F0 | rd << 8 | rm)


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_dcpad (Pattern Settings' slot 0: r0 = view, r1 = pad, r2 = velocity)
    a.label("c_dcpad")
    E(cmp_imm, 1, PAD)
    E(b_cond, "dc_f", "ne")
    E(push_list, [0, 1, 2, 3, 4, 5], lr=True)
    imm32(3, CI.CTRL + O_HELD)
    E(ldr_imm, 3, 3, 0)
    imm32(4, 1 << B_CLEAR)
    E(tst_reg, 3, 4)
    E(b_cond, "dc_p", "eq")                                                # Clear not held
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "dc_p", "eq")
    E(raw, h(0x9800))                                                     # ldr r0, [sp]: the view -> its track
    imm32(1, PS0)
    E(subs_reg, 0, 0, 1)
    E(movs_imm, 1, PS_SZ)
    E(raw, udiv(4, 0, 1))
    E(cmp_imm, 4, 8)
    E(b_cond, "dc_p", "hs")
    E(bl, L["c_dqon"])
    E(cmp_imm, 0, 0)
    E(b_cond, "dc_x", "eq")                                               # not marked: nothing to clear
    E(movs_imm, 0, PROB_SZ)
    E(muls, 0, 4)
    imm32(1, PROB0)
    E(adds_reg, 0, 0, 1)
    E(ldr_imm, 0, 0, 0xC)
    E(ldr_imm, 0, 0, 0)                                                   # ST1
    E(ldr_imm, 0, 0, 0x18)
    E(movs_imm, 1, DQ_FROM_LANES)
    E(subs_reg, 0, 0, 1)                                                  # r0 = the step bytes
    E(movs_imm, 1, 0)
    a.label("dc_l")
    E(raw, h(0x5C42))                                                     # ldrb r2, [r0, r1]
    E(movs_imm, 3, KEEP)
    E(raw, h(0x401A))                                                     # ands r2, r3
    E(raw, h(0x5442))                                                     # strb r2, [r0, r1]
    E(adds_imm8, 1, 1)
    E(cmp_imm, 1, 32)
    E(b_cond, "dc_l", "lo")
    a.label("dc_x")
    E(pop_list, [0, 1, 2, 3, 4, 5], pc=True)
    a.label("dc_p")
    E(raw, popw([0, 1, 2, 3, 4, 5], lr=True))
    a.label("dc_f")
    E(b_w, prev["pspad"])
    return a.assemble()


def install(img, report, base_addr):
    """The head of Pattern Settings' slot 0.  Needs drumpat (its mark) and countin."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]                 # noqa: E731
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    L = dict(c_ciok=lab("countin", "c_ciok"), c_dqon=lab("drumpat", "c_dqon"))
    prev = dict(pspad=u(PS_VT) & ~1)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch_word(img, PS_VT, prev["pspad"] | 1, labels["c_dcpad"] | 1)
    report["dqclear"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
