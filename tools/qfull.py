"""The trigger queue to core 1 never overrun (MIT; RH46; a fault of the stock found with RD24, docs/PORTADO.md «Arranque de la reproducción»).

The stock (read in the Rhythm's image; tools/latdiag.py, tools/qdrain.py): every note-on / note-off of a track goes to core 1 through a queue of
16 pairs in the DSP's shared memory (0x30410 + 2 i): 0x080406A8(message) writes the pair at the ARM's own write index (0x20006F38) and then the
new index (0x307B5), each with 0x08031228(0, value << 8, address); core 1 takes them from its read index (0x307B6), all of them in each block
since RH42 (qdrain).  The ARM never looks at the read index: 16 messages before a block (8 tracks' note-off and note-on on the same step) make
the write index equal to the read index, so core 1 sees an empty queue and every one of them is lost.
Ours, at the head of 0x080406A8 (`push {r4, r5, r6, lr}; ldr r5, [pc, #0x214]` -> c_qfw): with core 1's program up (cthresh READY), when the
queue may be full (15 messages since the read index we last read: rhstate OFF2 "qfull", 0x80 | it), the read index is read
(0x080314D6(0, 0x307B6), under the stock's lock) until there is room, at most 3 ms (a block is 0.67 ms), then the stock's write as always.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b, b_cond, b_w, bl, cmp_imm, cmp_reg, h, ldr_imm, ldrb_imm, ldrb_w, lsrs_imm, mov_reg,  # noqa: E402
                   movs_imm, movt, movw, pop_list, push_list, raw, strb_imm, subs_reg)
import countin as CI  # noqa: E402
import cthresh as TH  # noqa: E402
import rhstate  # noqa: E402

QWRITE, QWRITE_HEAD, QWRITE_CONT = 0x080406A8, "push {r4, r5, r6, lr}|ldr r5, [pc, #0x214]", 0x080406AC
QIDX, QREAD = 0x20006F38, 0x307B6
DSP_READ = 0x080314D6
O = rhstate.OFF2["qfull"][0]
O_TH = rhstate.OFF["cthresh"][0] + 1
WAIT_MS = 3


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def arm_code(base, L):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_qfw (0x080406A8's head: r0 = the message): room in the queue first, then the stock's write
    a.label("c_qfw")
    E(push_list, [0, 1, 2, 3, 4, 5, 6, 7], lr=True)
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "qf_x", "eq")
    E(ldrb_w, 1, 0, O_TH)
    E(cmp_imm, 1, TH.READY)
    E(b_cond, "qf_x", "ne")                                               # core 1's program not seen up: the stock's
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "qf_x", "eq")
    E(movw, 1, O)
    E(adds_reg, 4, 0, 1)                                                  # r4 = our RAM
    imm32(0, QIDX)
    E(ldr_imm, 5, 0, 0)
    E(movs_imm, 0, 15)
    E(raw, h(0x4005))                                                     # ands r5, r0: r5 = the write index
    E(ldrb_imm, 6, 4, 0)
    E(lsrs_imm, 0, 6, 7)
    E(b_cond, "qf_r", "eq")                                               # never read: read now
    E(subs_reg, 0, 5, 6)
    E(movs_imm, 1, 15)
    E(raw, h(0x4008))                                                     # ands r0, r1: the messages since the last read index
    E(cmp_imm, 0, 15)
    E(b_cond, "qf_x", "ne")
    a.label("qf_r")
    imm32(7, CI.HAL_TICK)
    E(ldr_imm, 7, 7, 0)                                                   # r7 = the start
    a.label("qf_l")
    E(movs_imm, 0, 0)
    imm32(1, QREAD)
    E(bl, DSP_READ)
    E(lsrs_imm, 0, 0, 8)
    E(movs_imm, 1, 15)
    E(raw, h(0x4008))                                                     # ands r0, r1: the read index
    E(movs_imm, 1, 0x80)
    E(raw, h(0x4301))                                                     # orrs r1, r0
    E(strb_imm, 1, 4, 0)
    E(mov_reg, 1, 5)
    E(adds_imm8, 1, 1)
    E(movs_imm, 2, 15)
    E(raw, h(0x4011))                                                     # ands r1, r2: the index after this write
    E(cmp_reg, 1, 0)
    E(b_cond, "qf_x", "ne")                                               # room
    imm32(0, CI.HAL_TICK)
    E(ldr_imm, 0, 0, 0)
    E(subs_reg, 0, 0, 7)
    E(cmp_imm, 0, WAIT_MS)
    E(b_cond, "qf_l", "lo")
    a.label("qf_x")
    E(raw, popw([0, 1, 2, 3, 4, 5, 6, 7], lr=True))
    E(push_list, [4, 5, 6], lr=True)                                      # the stock's first two instructions
    imm32(5, QIDX)
    E(b_w, QWRITE_CONT)
    return a.assemble()


def install(img, report, base_addr):
    """The head of 0x080406A8.  Needs rhstate ram2 and cthresh."""
    import rhbuild
    BASE = rhbuild.BASE
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    assert "cthresh" in report and "c_rram" in report["rhstate"]["labels"]
    L = dict(c_rst=lab("rhstate", "c_rst"), c_rram=lab("rhstate", "c_rram"))
    code, labels = arm_code(base_addr, L)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, QWRITE, QWRITE_HEAD, b_w(QWRITE, labels["c_qfw"]))
    report["qfull"] = dict(labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
