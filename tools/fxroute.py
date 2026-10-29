"""The FX returns into a line track leave the master, and that track's send back into the same FX is limited (MIT; RH58; the user,
2026-10-29: «when an fx is routed to an input, it shouldnt be routed to master anymore. also limit feedback (but not crossfeed) as we did on
Hacks»; Hacks' rule: «los envíos de esas tiras tienen tope a la mitad y van a media velocidad, para que la realimentación no se dispare»).

Core 0 (RH54's linein fx: FXH at P:$5C0 copies the reverb's output Y:$889 and the delay's Y:$9C9, 64 words L R, to RVB / DLY for LI; then
the stock's loop at P:$5C6 sums the delay's into Y:$889 (x:$77E's shift), which goes on to the master): FXH's end jumps to FXZ (linein
`excl`), which clears the stock's block of a return that a line slot takes as its source (LSRC / LSRC2 = 1 the reverb, 2 the delay; slot 1
only with LTRK2 <> 0; nothing while Y:LKEY <> KEY) and leaves r6 = $9C9 as the stock's words did.  The effects' own states are elsewhere: their
next blocks are the same (tests/emu_rh58.py).  FXZ is in P:$2D40, free in RH57 (granchain's part ends at $2D20, LI starts at $2E00).

The ARM: the flusher's bl (in front of slinkofs's c_sop): a line track's send to the effect it takes its source from (index $12 the reverb's
with source 1, $13 the delay's with source 2) reaches the DSP halved: the knob's whole turn = half the send, a click half a step (the feedback
capped and slowed); its send to the other effect (the crossfeed) as it is.  The LED task: when the line tracks or their sources change (a pad,
a project loaded), those tracks' two sends are marked and flushed again (rhstate OFF2 "fxroute": + 0 / + 1 the line bytes last seen, + 2 seen).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b_cond, b_w, bl, cmp_imm, cmp_reg, h, ldr_imm, ldrb_imm, ldrb_w, lsls_imm, lsrs_imm, lsrs_reg, mov_reg,  # noqa: E402
                   movs_imm, movt, movw, orrs_reg, pop_list, push_list, raw, str_imm, strb_imm, subs_imm3)
import core0 as C0  # noqa: E402
import countin as CI  # noqa: E402
import cthresh as TH  # noqa: E402
import granpage as GP  # noqa: E402
import linein as LI  # noqa: E402
import rhstate  # noqa: E402
import slink as SL  # noqa: E402
import stockplus as SP  # noqa: E402

FXZ_AT = 0x2D40
I_RV, I_DL = 0x12, 0x13
O, O_LEN = rhstate.OFF2["fxroute"]
R_B0, R_B1, R_SEEN = 0, 1, 2
O_TH = rhstate.OFF["cthresh"][0] + 1


def items():
    L = []

    def e(*s):
        L.extend(s)

    def zero(n):
        """b = a slot's source: its return's block cleared"""
        e(f"move #>${LI.SRC_RV:x},x0", "cmp x0,b", ("jcc", "ne", n + "d"), f"move #>${LI.FX_RV:x},r6", ("jmp", n + "z"),
          ("label", n + "d"), f"move #>${LI.SRC_DL:x},x0", "cmp x0,b", ("jcc", "ne", n + "n"), f"move #>${LI.FX_DL:x},r6",
          ("label", n + "z"), "clr a", "do #$40,${" + n + "l:x}", "move a,y:(r6)+", ("label", n + "l"), ("label", n + "n"))
    e(("label", "fxz"), f"move y:>${LI.LKEY:x},a", f"move #>${LI.KEY:x},x0", "cmp x0,a", ("jcc", "ne", "fz_x"),
      f"move y:>${LI.LSRC:x},b")
    zero("z0")
    e(f"move y:>${LI.LTRK2:x},a", "tst a", ("jcc", "eq", "fz_x"), f"move y:>${LI.LSRC2:x},b")
    zero("z1")
    e(("label", "fz_x"), f"move #>${LI.FX_DL:x},r6", "rts")
    return L


def code():
    w, labels = C0.asm_at(items(), FXZ_AT)
    assert FXZ_AT + len(w) <= LI.AT, hex(FXZ_AT + len(w))
    return w, labels


def segs():
    """for granular0's extra: FXZ (linein's FXH jumps there with `excl`)"""
    return [(FXZ_AT, code()[0])]


def model_send(i, v, src):
    """the send the DSP gets for (index, value) on a line track with this source (0 inputs, 1 reverb, 2 delay; None = not a line track)"""
    return v >> 1 if (i == I_RV and src == LI.SRC_RV) or (i == I_DL and src == LI.SRC_DL) else v


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_frram() -> r0 = our RAM (0 without it); clobbers r1-r3
    a.label("c_frram")
    E(push_list, [4], lr=True)
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "fr_x", "eq")
    E(movw, 1, O)
    E(adds_reg, 0, 0, 1)
    a.label("fr_x")
    E(pop_list, [4], pc=True)

    # ---- c_frp (the flusher's bl at 0x0803085E, slinkofs's c_sop after it: r0 = t, r1 = index, r2 = value)
    a.label("c_frp")
    E(cmp_imm, 1, I_RV)
    E(b_cond, "fp_s", "eq")
    E(cmp_imm, 1, I_DL)
    E(b_cond, "fp_p", "ne")
    a.label("fp_s")
    E(push_list, [0, 1, 2, 4], lr=True)
    E(mov_reg, 4, 1)
    E(bl, L["c_smline"])                                                  # its line byte (0 = not a line track)
    E(cmp_imm, 0, 0)
    E(b_cond, "fp_q", "eq")
    E(lsrs_imm, 0, 0, LI.SRC_SHIFT)
    E(movs_imm, 1, 3)
    E(raw, h(0x4008))                                                     # ands r0, r1: its source
    E(movs_imm, 1, LI.SRC_RV)
    E(cmp_imm, 4, I_RV)
    E(b_cond, "fp_c", "eq")
    E(movs_imm, 1, LI.SRC_DL)
    a.label("fp_c")
    E(cmp_reg, 0, 1)
    E(b_cond, "fp_q", "ne")                                               # the other effect's (the crossfeed): as it is
    E(raw, GP.popw([0, 1, 2, 4], lr=True))
    E(lsrs_imm, 2, 2, 1)                                                  # the feedback: halved
    E(b_w, prev["param"])
    a.label("fp_q")
    E(raw, GP.popw([0, 1, 2, 4], lr=True))
    a.label("fp_p")
    E(b_w, prev["param"])

    # ---- c_frbit(r0 = a line byte, r7 = a track mask) -> r7 with its track (none: as it was); clobbers r0-r2
    a.label("c_frbit")
    E(movs_imm, 1, 15)
    E(raw, h(0x4008))                                                     # ands r0, r1
    E(cmp_imm, 0, 0)
    E(b_cond, "fb_x", "eq")
    E(subs_imm3, 0, 0, 1)
    E(movs_imm, 1, 1)
    E(raw, h(0x4081))                                                     # lsls r1, r0
    E(orrs_reg, 7, 1)
    a.label("fb_x")
    E(raw, h(0x4770))

    # ---- c_frflush(r0 = track): its two sends marked and flushed
    a.label("c_frflush")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    imm32(1, SL.DIRTY)
    E(lsls_imm, 2, 4, 2)
    E(adds_reg, 1, 1, 2)
    E(ldr_imm, 2, 1, 0)
    E(movs_imm, 3, 3)
    E(lsls_imm, 3, 3, I_RV)
    E(orrs_reg, 2, 3)
    E(str_imm, 2, 1, 0)
    E(mov_reg, 0, 4)
    E(bl, SL.FLUSH)
    E(pop_list, [4], pc=True)

    # ---- c_frled (the LED task's calls: ctrl, frame): the chain; the line tracks or their sources changed: their sends again
    a.label("c_frled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "fl_x", "eq")
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "fl_x", "eq")
    E(ldrb_w, 1, 0, O_TH)
    E(cmp_imm, 1, TH.READY)
    E(b_cond, "fl_x", "ne")                                               # core 0 not seen up
    E(bl, "c_frram")
    E(cmp_imm, 0, 0)
    E(b_cond, "fl_x", "eq")
    E(mov_reg, 4, 0)                                                      # r4 = our RAM
    E(bl, L["c_liget"])
    E(mov_reg, 5, 0)                                                      # r5 / r6 = the line bytes now
    E(mov_reg, 6, 1)
    E(ldrb_imm, 0, 4, R_SEEN)
    E(cmp_imm, 0, 0)
    E(b_cond, "fl_c", "eq")
    E(ldrb_imm, 0, 4, R_B0)
    E(cmp_reg, 0, 5)
    E(b_cond, "fl_c", "ne")
    E(ldrb_imm, 0, 4, R_B1)
    E(cmp_reg, 0, 6)
    E(b_cond, "fl_x", "eq")
    a.label("fl_c")
    E(movs_imm, 7, 0)                                                     # r7 = the tracks before and after, each once
    for reg, off in ((None, R_B0), (None, R_B1), (5, None), (6, None)):
        if reg is None:
            E(ldrb_imm, 0, 4, off)
        else:
            E(mov_reg, 0, reg)
        E(bl, "c_frbit")
    E(strb_imm, 5, 4, R_B0)
    E(strb_imm, 6, 4, R_B1)
    E(movs_imm, 0, 1)
    E(strb_imm, 0, 4, R_SEEN)
    E(movs_imm, 5, 0)
    a.label("fl_t")
    E(mov_reg, 0, 7)
    E(lsrs_reg, 0, 5)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "fl_n", "eq")
    E(mov_reg, 0, 5)
    E(bl, "c_frflush")
    a.label("fl_n")
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, 8)
    E(b_cond, "fl_t", "lo")
    a.label("fl_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """The flusher's bl (in front of slinkofs's), the LED calls.  Needs linein two fx excl (FXH -> FXZ) and FXZ on core 0 (segs()),
    smodes (c_smline), cthresh, rhstate ram2; not latdiag."""
    import rhbuild
    BASE = rhbuild.BASE
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    assert "latdiag" not in report and report["linein"].get("excl") == hex(FXZ_AT), "fxroute: needs linein excl and FXZ"
    L = dict(c_rram=lab("rhstate", "c_rram"), c_rst=lab("rhstate", "c_rst"), c_ciok=lab("countin", "c_ciok"),
             c_smline=lab("smodes", "c_smline"), c_liget=lab("linein", "c_liget"))
    prev = dict(param=rhbuild.bl_target(img, SL.FLUSH_CALL), ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert prev["param"] == lab("slinkofs", "c_sop")
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code_, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code_
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, SL.FLUSH_CALL, f"bl #{prev['param']:#x}", bl(SL.FLUSH_CALL, labels["c_frp"]))
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_frled"]))
    report["fxroute"] = dict(prev={k: hex(v) for k, v in prev.items()}, fxz=hex(FXZ_AT),
                             labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code_
