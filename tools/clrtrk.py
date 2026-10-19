"""Clear + a track button = that track's eight knobs back to their defaults and their automation of the pattern deleted (MIT; CIRCUIT-HACKS' clrtrk
of SC43.4 with use_autoclr of SC43.7, «Clear + drum: back to init knob settings», «clear+drum# to clear all automations and back to init»,
for the Circuit Rhythm 5706).

The stock of the Rhythm (emulated on the RAM dump):
  * the held buttons = the word [ctrl + 0xA0], bit = button id (Clear 23; 24 also sets a bit of the held store with Clear: Duplicate's place);
    Clear + a track button only selects the track (the same RAM as the plain button);
  * a knob = 0x0803DDE0(ctrl, knob, delta); in the track views (the container 0x20048B9C on the screen) it moves the selected track's knob;
    with Clear held a sustained turn (40 events, by count: the emulated clock never moves) to the right puts the knob back to its default, to the
    left deletes the knob's automation lane (lane k of the selected track's pattern, + 0x128 + 192 k) and leaves the value.
Ours, the head of the button chain: Clear held (not 24) + track button 1-8 with the track views on the screen: the stock first (it selects the
track), then for each of the 8 knobs 48 events to the left and 48 to the right through the controller's knob entry; nothing else changes.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, b_cond, b_w, bl, cmp_imm, cmp_reg, ldr_imm, ldr_sp, lsls_imm, mov_reg, movs_imm, movt, movw,  # noqa: E402
                   pop_list, push_list, raw, h, subs_imm8)
import countin as CI  # noqa: E402
import quant as Q  # noqa: E402

CTRL = CI.CTRL
KNOB = 0x0803DDE0
O_HELD = 0xA0
BIT_CLEAR, BIT_DUP = 23, 24
CONT, CONT_VT = Q.CONT, Q.CONT_VT
EVENTS = 48


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_ctok(r0 = ctrl, r1 = id) -> r0 = 1 for ours; clobbers r1-r3
    a.label("c_ctok")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(cmp_imm, 1, 8)
    E(b_cond, "ok_0", "hs")
    E(mov_reg, 0, 4)
    E(adds_imm8, 0, O_HELD)
    E(ldr_imm, 0, 0, 0)                                                   # the held buttons
    E(lsls_imm, 1, 0, 31 - BIT_CLEAR)
    E(b_cond, "ok_0", "pl")                                               # Clear not held
    E(lsls_imm, 1, 0, 31 - BIT_DUP)
    E(b_cond, "ok_0", "mi")
    E(ldr_imm, 0, 4, 0x7C)
    imm32(1, CONT)
    E(cmp_reg, 0, 1)
    E(b_cond, "ok_0", "ne")                                               # not the track views
    E(ldr_imm, 0, 0, 0)
    imm32(1, CONT_VT)
    E(cmp_reg, 0, 1)
    E(b_cond, "ok_0", "ne")
    E(bl, L["c_ciok"])
    E(pop_list, [4], pc=True)
    a.label("ok_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)

    # ---- c_ctbtn (the head of the button chain: r0 = ctrl, r1 = id)
    a.label("c_ctbtn")
    E(push_list, [0, 1, 2, 3, 4, 5, 6], lr=True)                          # 8 words
    E(bl, "c_ctok")
    E(cmp_imm, 0, 0)
    E(b_cond, "cb_f", "eq")
    E(ldr_sp, 0, 0)
    E(ldr_sp, 1, 4)
    E(bl, prev["btn"])                                                    # the stock: the track selected
    E(movs_imm, 4, 0)                                                     # r4 = the knob
    a.label("cb_k")
    for sign, lab in ((-1, "cb_l"), (1, "cb_r")):
        E(movs_imm, 5, EVENTS)
        a.label(lab)
        imm32(0, CTRL)
        E(mov_reg, 1, 4)
        if sign < 0:
            E(movs_imm, 2, 0)
            E(subs_imm8, 2, 1)                                            # -1
        else:
            E(movs_imm, 2, 1)
        E(bl, KNOB)
        E(subs_imm8, 5, 1)
        E(b_cond, lab, "ne")
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, 8)
    E(b_cond, "cb_k", "lo")
    E(pop_list, [0, 1, 2, 3, 4, 5, 6], pc=True)
    a.label("cb_f")
    E(raw, popw([0, 1, 2, 3, 4, 5, 6], lr=True))
    E(b_w, prev["btn"])
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; the head of the button chain."""
    import rhbuild
    BASE = rhbuild.BASE
    L = dict(c_ciok=int(report["countin"]["labels"]["c_ciok"], 16))
    prev = dict(btn=rhbuild.bw_target(img, CI.BTN_ENTRY))
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, CI.BTN_ENTRY, f"b.w #{prev['btn']:#x}", b_w(CI.BTN_ENTRY, labels["c_ctbtn"]))
    report["clrtrk"] = dict(btn_entry=hex(CI.BTN_ENTRY), prev={k: hex(v) for k, v in prev.items()},
                            labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
