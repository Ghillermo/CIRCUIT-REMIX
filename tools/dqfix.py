"""drumpat's step bytes follow the stock's step paste and Mutate (MIT; the open points of RH09 / RH11 in docs/PORTADO.md, for the Circuit Rhythm 5706).

The stock of the Rhythm (read in the firmware and on the RAM dump, emulated):
  * the track views' step editor object (obj): [obj + 4] = the track's patterns (0xA28 each), the store [obj + 0x28] = the pattern (p0) and the
    step (p1) being edited, [obj + 0x64] = the copy buffer (+ 2 the source pattern, + 3 the source step);
  * Duplicate + step A + step B: 0x08047820(obj, the step's data, its lanes) pastes A onto B (its only call: 0x0803684C): the 12 lanes and the
    edit stores (their commits write the pattern);
  * Mutate (Shift + Duplicate): 0x08047E88(obj) (its only call: 0x0803656C) moves whole steps (their 8 bytes unchanged) to other places of the
    pattern in [obj + 0x28] p0, within its first / last steps.
Ours (drumpat's bytes at the pattern + 0x108 + step):
  * the paste: the source's byte onto the destination;
  * Mutate: the pattern's 32 steps and bytes kept before, then each step takes the byte of the first old step with the same 8 bytes not yet taken.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, add_sp_imm, adds_imm8, adds_reg, b, b_cond, bl, cmp_imm, cmp_reg, h, ldr_imm, ldr_sp, ldrb_imm, ldrb_reg, lsls_imm,  # noqa: E402
                   lsls_reg, mov_reg, movs_imm, movt, movw, muls, orrs_reg, pop_list, push_list, raw, str_sp, strb_reg, sub_sp_imm, tst_reg)
import countin as CI  # noqa: E402
import drumpat as DQ  # noqa: E402

PASTE, PASTE_CALL = 0x08047820, 0x0803684C
MUTATE, MUTATE_CALL = 0x08047E88, 0x0803656C
O_PATS, O_EDIT, O_BUF = 4, 0x28, 0x64
PAT_SZ, DQ_OFF = DQ.PAT_SZ, DQ.DQ_OFF


def pushw(regs, lr=False): return h(0xE92D) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))
def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def arm_code(base, L):
    a = Asm(base)
    E = a.emit

    # ---- c_dfpat(r0 = obj, r1 = pattern) -> r0 = that pattern's drumpat bytes (pattern + 0x108); clobbers r1, r2
    a.label("c_dfpat")
    E(ldr_imm, 0, 0, O_PATS)
    E(movw, 2, PAT_SZ)
    E(muls, 1, 2)
    E(adds_reg, 0, 0, 1)
    E(movw, 1, DQ_OFF)
    E(adds_reg, 0, 0, 1)
    E(raw, h(0x4770))

    # ---- c_dfpaste (in place of the paste's call: obj, data, lanes): the stock's paste, then the source's byte onto the destination
    a.label("c_dfpaste")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(ldr_imm, 1, 0, O_BUF)
    E(ldrb_imm, 4, 1, 2)                                                  # r4 = the source pattern
    E(ldrb_imm, 5, 1, 3)                                                  # r5 = the source step
    E(ldr_imm, 0, 0, O_EDIT)
    E(movs_imm, 1, 0)
    E(bl, L["c_cinew"])
    E(mov_reg, 6, 0)                                                      # r6 = the destination pattern
    E(ldr_sp, 0, 0)
    E(ldr_imm, 0, 0, O_EDIT)
    E(movs_imm, 1, 1)
    E(bl, L["c_cinew"])
    E(mov_reg, 7, 0)                                                      # r7 = the destination step
    E(ldr_sp, 0, 0)
    E(ldr_sp, 1, 4)
    E(ldr_sp, 2, 8)
    E(bl, PASTE)
    E(cmp_imm, 4, 8)
    E(b_cond, "dp_x", "hs")
    E(cmp_imm, 5, 32)
    E(b_cond, "dp_x", "hs")
    E(cmp_imm, 6, 8)
    E(b_cond, "dp_x", "hs")
    E(cmp_imm, 7, 32)
    E(b_cond, "dp_x", "hs")
    E(ldr_sp, 0, 0)
    E(mov_reg, 1, 4)
    E(bl, "c_dfpat")
    E(ldrb_reg, 4, 0, 5)                                                  # r4 = the source's byte
    E(ldr_sp, 0, 0)
    E(mov_reg, 1, 6)
    E(bl, "c_dfpat")
    E(strb_reg, 4, 0, 7)
    a.label("dp_x")
    E(raw, h(0xB003))                                                     # add sp, #12
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_dfmut (in place of Mutate's call: obj): the steps and bytes kept, Mutate, each step's byte found again by its 8 bytes
    # frame: [sp] the obj, [sp + 4] the pattern, [sp + 8] the taken mask, [sp + 12 ..] the 32 old steps (256 B), then their 32 bytes
    OLD, OLDB, FR = 12, 12 + 256, 12 + 256 + 32
    a.label("c_dfmut")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(sub_sp_imm, FR)
    E(str_sp, 0, 0)
    E(ldr_imm, 0, 0, O_EDIT)
    E(movs_imm, 1, 0)
    E(bl, L["c_cinew"])
    E(str_sp, 0, 4)
    E(cmp_imm, 0, 8)
    E(b_cond, "dm_s", "lo")
    E(ldr_sp, 0, 0)
    E(bl, MUTATE)
    E(b, "dm_x")
    a.label("dm_s")
    E(ldr_sp, 0, 0)
    E(ldr_sp, 1, 4)
    E(bl, "c_dfpat")
    E(mov_reg, 4, 0)                                                      # r4 = the bytes
    E(movw, 1, DQ_OFF)
    E(raw, h(0x1A65))                                                     # subs r5, r4, r1: r5 = the steps
    E(movs_imm, 6, 0)
    a.label("dm_c1")                                                      # keep the 256 bytes of the steps
    E(ldrb_reg, 0, 5, 6)
    E(raw, h(0xA800 | 3 << 8 | OLD // 4))                                 # add r3, sp, #OLD
    E(strb_reg, 0, 3, 6)
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, 255)
    E(b_cond, "dm_c1", "ls")
    E(movs_imm, 6, 0)
    a.label("dm_c2")                                                      # and their 32 bytes
    E(ldrb_reg, 0, 4, 6)
    E(raw, h(0xA800 | 3 << 8 | OLDB // 4))                                # add r3, sp, #OLDB
    E(strb_reg, 0, 3, 6)
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, 32)
    E(b_cond, "dm_c2", "lo")
    E(ldr_sp, 0, 0)
    E(bl, MUTATE)
    E(movs_imm, 0, 0)
    E(str_sp, 0, 8)                                                       # nothing taken
    E(movs_imm, 6, 0)                                                     # r6 = the step
    a.label("dm_s1")
    E(lsls_imm, 0, 6, 3)
    E(adds_reg, 0, 0, 5)
    E(ldr_imm, 1, 0, 0)
    E(ldr_imm, 2, 0, 4)                                                   # r1, r2 = its 8 bytes
    E(movs_imm, 7, 0)                                                     # r7 = an old step
    a.label("dm_o")
    E(ldr_sp, 0, 8)
    E(raw, h(0x40C0 | 7 << 3 | 0))                                        # lsrs r0, r7
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "dm_on", "mi")                                              # taken
    E(raw, h(0xA800 | 3 << 8 | OLD // 4))                                 # add r3, sp, #OLD
    E(lsls_imm, 0, 7, 3)
    E(adds_reg, 3, 3, 0)
    E(ldr_imm, 0, 3, 0)
    E(cmp_reg, 0, 1)
    E(b_cond, "dm_on", "ne")
    E(ldr_imm, 0, 3, 4)
    E(cmp_reg, 0, 2)
    E(b_cond, "dm_on", "ne")
    E(ldr_sp, 0, 8)                                                       # found: taken, its byte
    E(movs_imm, 3, 1)
    E(lsls_reg, 3, 7)
    E(orrs_reg, 0, 3)
    E(str_sp, 0, 8)
    E(raw, h(0xA800 | 3 << 8 | OLDB // 4))                                # add r3, sp, #OLDB
    E(ldrb_reg, 0, 3, 7)
    E(b, "dm_w")
    a.label("dm_on")
    E(adds_imm8, 7, 1)
    E(cmp_imm, 7, 32)
    E(b_cond, "dm_o", "lo")
    E(movs_imm, 0, 0)                                                     # (none: no byte)
    a.label("dm_w")
    E(strb_reg, 0, 4, 6)
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, 32)
    E(b_cond, "dm_s1", "lo")
    a.label("dm_x")
    E(add_sp_imm, FR)
    E(pop_list, [4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; the paste's call, Mutate's call."""
    import rhbuild
    BASE = rhbuild.BASE
    L = dict(c_cinew=int(report["countin"]["labels"]["c_cinew"], 16))
    code, labels = arm_code(base_addr, L)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, PASTE_CALL, f"bl #{PASTE:#x}", bl(PASTE_CALL, labels["c_dfpaste"]))
    rhbuild.patch(img, MUTATE_CALL, f"bl #{MUTATE:#x}", bl(MUTATE_CALL, labels["c_dfmut"]))
    report["dqfix"] = dict(labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
