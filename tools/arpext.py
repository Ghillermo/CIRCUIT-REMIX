"""An external keyboard through the arpeggiator (MIT; RH46, as CIRCUIT-HACKS' arpx of Beta 3.29, issues #13 / #14 of its public repository:
«user wants arpeggiator to work with external midi input» · «should be toggleable … default setting should be like it is now»).

The stock of the Rhythm (read in its image, run on the RAM dump): a note on a track's channel reaches the MIDI-in listener ([[0x20006EEC]],
vtable 0x080665E4: slot 0 note-on 0x0803F5A8, slot 1 note-off 0x0803F660, (this, id, note, velocity); id 0x10 + t a track, 0xFE the drum map of
channel 16; a note-on with velocity 0 goes to slot 1 through the object's vtable), which plays it on the track ([this + 0x24] slot 0 / 1) and
keeps it in a bit set (this + 0x74 + 20 t).  drumarp (RH15 / RH22, notes) arpeggiates the Note view's held keys: its running state (rhstate
"drumarp"), c_dains / c_dadel (the sorted held list), c_daend; the LED task ends it when its view has not been drawn for 200 ms.
Ours, with the toggle on (Advanced Setup pad 22, bit 29 of the device settings' parameter 2, saved by setsave; off at first, as the stock):
  * a note-on of an external keyboard on track t whose playing pattern has the arpeggiator on: the first held note sounds as always (the
    stock's) and is kept as the arpeggio's first; the next ones do not reach the stock: they start the arpeggio of the held notes (drumarp's
    notes mode, its order and resolution); flag 8 of the state's flags marks it as the keyboard's;
  * a note-off: a held note leaves the list (the first one's to the stock); the list empty = the arpeggio ends;
  * the LED task (ahead of drumarp's) keeps the keyboard's arpeggio alive while notes are held (its view need not be on the screen).
  * LEDs: Advanced Setup pad 22 green on, dim off.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, b, b_cond, b_w, bl, cmp_imm, cmp_reg, h, ldr_imm, ldrb_imm, lsls_imm, mov_reg, movs_imm, movt, movw, orrs_reg,  # noqa: E402
                   pop_list, push_list, raw, str_imm, strb_imm, strh_imm, tst_reg)
import countin as CI  # noqa: E402
import drumarp as DA  # noqa: E402
import pgmch as PG  # noqa: E402
import usbmerge as UM  # noqa: E402

LIS_VT = 0x080665E4
BIT = 1 << 29
PAD = 21                                                  # pad 22
F_EXT = 8
S_N, S_TRK, S_FL, S_FIRST, S_K, S_FG, S_FP, S_NEXT, S_SEEN = DA.S_N, DA.S_TRK, DA.S_FL, DA.S_FIRST, DA.S_K, DA.S_FG, DA.S_FP, DA.S_NEXT, DA.S_SEEN
F_NOTES = DA.F_NOTES
SETUP_VT = PG.SETUP_VT
COL_ON, COL_DIM = UM.COL_ON, UM.COL_DIM


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_axtrk(r1 = id) -> r0 = the track when the keyboard's notes go to its arpeggiator now (the toggle, the pattern's arpeggiator on),
    #      else 8; clobbers r1-r3
    a.label("c_axtrk")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 1)
    E(movs_imm, 5, 8)
    E(mov_reg, 0, 4)
    E(raw, h(0x3810))                                                     # subs r0, #0x10
    E(cmp_imm, 0, 8)
    E(b_cond, "xt_x", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the track
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "xt_x", "eq")
    UM.p2bit(E, imm32, BIT)
    E(cmp_imm, 0, 0)
    E(b_cond, "xt_x", "eq")
    E(mov_reg, 0, 4)
    E(bl, L["c_dapat"])
    E(mov_reg, 1, 0)
    E(mov_reg, 0, 4)
    E(bl, L["c_dacfg"])
    E(lsls_imm, 0, 0, 24)
    E(b_cond, "xt_x", "pl")
    E(mov_reg, 5, 4)
    a.label("xt_x")
    E(mov_reg, 0, 5)
    E(pop_list, [4, 5], pc=True)

    # ---- c_axon (the MIDI-in listener's slot 0: this, id, note, velocity)
    a.label("c_axon")
    E(cmp_imm, 3, 0)
    E(b_cond, "c_axoff", "eq")                                            # velocity 0: a note-off
    E(push_list, [0, 1, 2, 3, 4, 5, 6, 7], lr=True)
    E(bl, "c_axtrk")
    E(cmp_imm, 0, 8)
    E(b_cond, "xo_p", "hs")
    E(mov_reg, 7, 0)                                                      # r7 = the track
    E(bl, L["c_dast"])
    E(cmp_imm, 0, 0)
    E(b_cond, "xo_i", "eq")
    E(ldrb_imm, 1, 0, S_TRK)
    E(cmp_reg, 1, 7)
    E(b_cond, "xo_e", "ne")
    E(ldrb_imm, 1, 0, S_FL)
    E(movs_imm, 2, F_NOTES)
    E(tst_reg, 1, 2)
    E(b_cond, "xo_g", "ne")
    E(ldrb_imm, 1, 0, S_N)
    E(cmp_imm, 1, 0)
    E(b_cond, "xo_m", "eq")
    a.label("xo_e")
    E(bl, L["c_daend"])                                                   # another track's, or samples: over
    a.label("xo_i")
    E(mov_reg, 0, 7)
    E(bl, L["c_daini"])
    E(cmp_imm, 0, 0)
    E(b_cond, "xo_p", "eq")
    a.label("xo_m")
    E(movs_imm, 1, F_NOTES)
    E(strb_imm, 1, 0, S_FL)
    a.label("xo_g")
    E(mov_reg, 4, 0)                                                      # r4 = the state
    E(ldrb_imm, 1, 4, S_FL)
    E(movs_imm, 2, F_EXT)
    E(orrs_reg, 1, 2)
    E(strb_imm, 1, 4, S_FL)
    E(ldrb_imm, 6, 4, S_N)
    E(mov_reg, 0, 4)
    E(raw, h(0x9902))                                                     # ldr r1, [sp, #8]: the note
    E(raw, h(0x9A03))                                                     # ldr r2, [sp, #12]: the velocity
    E(bl, L["c_dains"])
    E(cmp_imm, 6, 0)
    E(b_cond, "xo_2", "ne")
    E(raw, h(0x9802))                                                     # ldr r0, [sp, #8]
    E(strb_imm, 0, 4, S_FIRST)                                            # the first: the stock's
    if L.get("c_da1st"):
        E(mov_reg, 0, 4)
        E(bl, L["c_da1st"])
    E(b, "xo_p")
    a.label("xo_2")
    E(ldrb_imm, 0, 4, S_FL)
    E(lsls_imm, 1, 0, 31)
    E(b_cond, "xo_t", "mi")
    E(movs_imm, 1, 1)
    E(orrs_reg, 0, 1)
    E(strb_imm, 0, 4, S_FL)                                               # it starts: the order from its start, the clock now
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 4, S_K)
    E(strb_imm, 0, 4, S_FG)
    E(strb_imm, 0, 4, S_FP)
    imm32(0, CI.HAL_TICK)
    E(ldr_imm, 0, 0, 0)
    E(str_imm, 0, 4, S_NEXT)
    E(str_imm, 0, 4, S_SEEN)
    a.label("xo_t")
    E(pop_list, [0, 1, 2, 3, 4, 5, 6, 7], pc=True)                        # taken
    a.label("xo_p")
    E(raw, popw([0, 1, 2, 3, 4, 5, 6, 7], lr=True))
    a.label("xo_s")
    E(b_w, prev["on"])

    # ---- c_axoff (the MIDI-in listener's slot 1: this, id, note, velocity)
    a.label("c_axoff")
    E(push_list, [0, 1, 2, 3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 0, 1)
    E(raw, h(0x3810))                                                     # subs r0, #0x10
    E(cmp_imm, 0, 8)
    E(b_cond, "xf_p", "hs")
    E(mov_reg, 7, 0)                                                      # r7 = the track
    E(bl, L["c_dast"])
    E(cmp_imm, 0, 0)
    E(b_cond, "xf_p", "eq")
    E(mov_reg, 4, 0)
    E(ldrb_imm, 1, 4, S_TRK)
    E(cmp_reg, 1, 7)
    E(b_cond, "xf_p", "ne")
    E(ldrb_imm, 1, 4, S_FL)
    E(movs_imm, 2, F_EXT)
    E(tst_reg, 1, 2)
    E(b_cond, "xf_p", "eq")
    E(raw, h(0x9D02))                                                     # ldr r5, [sp, #8]: the note
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, L["c_dadel"])
    E(cmp_imm, 0, 0)
    E(b_cond, "xf_p", "eq")                                               # not ours
    E(ldrb_imm, 0, 4, S_FIRST)
    E(cmp_reg, 0, 5)
    E(b_cond, "xf_t", "ne")
    E(movs_imm, 0, 0xFF)
    E(strb_imm, 0, 4, S_FIRST)                                            # the first: its note-off to the stock
    E(raw, h(0x9800))                                                     # ldr r0, [sp]
    E(raw, h(0x9901))                                                     # ldr r1, [sp, #4]
    E(raw, h(0x9A02))                                                     # ldr r2, [sp, #8]
    E(raw, h(0x9B03))                                                     # ldr r3, [sp, #12]
    E(bl, prev["off"])
    a.label("xf_t")
    E(ldrb_imm, 0, 4, S_N)
    E(cmp_imm, 0, 0)
    E(b_cond, "xf_k", "ne")
    E(mov_reg, 0, 4)
    E(bl, L["c_daend"])
    a.label("xf_k")
    E(pop_list, [0, 1, 2, 3, 4, 5, 6, 7], pc=True)
    a.label("xf_p")
    E(raw, popw([0, 1, 2, 3, 4, 5, 6, 7], lr=True))
    E(b_w, prev["off"])

    # ---- c_axpad (the Setup view's slot 0: view, pad, velocity): Advanced Setup pad 22
    a.label("c_axpad")
    E(cmp_imm, 1, PAD)
    E(b_cond, "xp_s", "ne")
    E(push_list, [0, 1, 2, 3, 4, 5], lr=True)
    E(raw, h(0xF890) + h(0x3024))                                         # ldrb.w r3, [r0, #0x24]
    E(cmp_imm, 3, 0)
    E(b_cond, "xp_p", "eq")
    UM.toggle(E, imm32, BIT)
    E(pop_list, [0, 1, 2, 3, 4, 5], pc=True)
    a.label("xp_p")
    E(raw, popw([0, 1, 2, 3, 4, 5], lr=True))
    a.label("xp_s")
    E(b_w, prev["pad"])

    # ---- c_axled (the LED task's calls: ctrl, frame): the keyboard's arpeggio kept alive, the chain, then pad 22 in Advanced Setup
    a.label("c_axled")
    E(push_list, [3, 4, 5, 6], lr=True)
    E(mov_reg, 5, 1)
    E(mov_reg, 6, 0)
    E(bl, L["c_dast"])
    E(cmp_imm, 0, 0)
    E(b_cond, "xl_c", "eq")
    E(ldrb_imm, 1, 0, S_FL)
    E(movs_imm, 2, F_EXT)
    E(tst_reg, 1, 2)
    E(b_cond, "xl_c", "eq")
    E(ldrb_imm, 1, 0, S_N)
    E(cmp_imm, 1, 0)
    E(b_cond, "xl_c", "eq")
    imm32(1, CI.HAL_TICK)
    E(ldr_imm, 1, 1, 0)
    E(str_imm, 1, 0, S_SEEN)
    a.label("xl_c")
    E(mov_reg, 0, 6)
    E(mov_reg, 1, 5)
    E(bl, prev["ledtask"])
    UM.advanced(E, imm32, L, "xl_x")
    UM.p2bit(E, imm32, BIT)
    E(movs_imm, 1, COL_DIM)
    E(cmp_imm, 0, 0)
    E(b_cond, "xl_w", "eq")
    E(movs_imm, 1, COL_ON)
    a.label("xl_w")
    E(strh_imm, 1, 5, 2 * PAD)
    a.label("xl_x")
    E(pop_list, [3, 4, 5, 6], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """The MIDI-in listener's slots 0 / 1, the head of the Setup view's slot 0, the head of the LED calls.  Needs drumarp (notes)."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]                 # noqa: E731
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    dl = report["drumarp"]["labels"]
    assert "c_danpad" in dl, "arpext needs drumarp with notes"
    L = dict(c_ciok=lab("countin", "c_ciok"), c_cinew=lab("countin", "c_cinew"),
             **{k: lab("drumarp", k) for k in ("c_dast", "c_daini", "c_dains", "c_dadel", "c_daend", "c_dapat", "c_dacfg")})
    if "c_da1st" in dl:
        L["c_da1st"] = lab("drumarp", "c_da1st")
    prev = dict(on=u(LIS_VT) & ~1, off=u(LIS_VT + 4) & ~1, pad=u(SETUP_VT) & ~1, ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch_word(img, LIS_VT, prev["on"] | 1, labels["c_axon"] | 1)
    rhbuild.patch_word(img, LIS_VT + 4, prev["off"] | 1, labels["c_axoff"] | 1)
    rhbuild.patch_word(img, SETUP_VT, prev["pad"] | 1, labels["c_axpad"] | 1)
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_axled"]))
    report["arpext"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
