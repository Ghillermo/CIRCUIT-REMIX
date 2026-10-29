"""The track's modes on Sample mode's free pads; the track menu keeps the pages (MIT; RH58; the user, 2026-10-29: «put all modes in the free
pads from Sample mode view, keep pages on track's double tap/hold view»; the layout chosen: «Sound row + line below»).

Sample mode (the container's mode 9, Samples twice) on the screen, the selected track t, Shift not held:
  * pads 5-8 = the track's sound, one of them lit (docs/INTERFAZ.md: a selection in one row, each in its page's colour, the others dim):
    5 sample (white / grey), 6 granular (lilac), 7 synth (mint), 8 line in (amber); a pad = that sound (the lit one does nothing; 5 turns the
    granular, the synth or the line in off);
  * pads 15 / 16 under line in (its modifiers, only on a line track, dark elsewhere): 15 its source (the inputs dim amber, the reverb's
    return cream, the delay's peach), 16 its gate (amber / dim);
  * pad 14 = the stereo link with the next track (steel blue bright linked either way / dim; dark on track 8 alone).
In the stock these pads do nothing in Sample mode (tests/emu_rh58.py: pads 3-8, 11-18, 20-21 and 30 change nothing; 29 does).

Each pad plays the menu's own pad for track t (granular 11, synth 12, line in 13, gate 14, source 15, link 9): the menu's state (rhstate
OFF2 "menu": its track, flags, press, the pads taken) is set to «sticky, track t» around the press and the release through the pad chains,
then put back as it was (but the Granular / Envelope page bits, which the action may change); so the exclusions, the project's blocks and
the DSP words are the modules' own.  The track menu (open: granpage's c_gpmopen() = its track) no longer shows those pads: dark, and a press
there does nothing (swallowed with its release).
Ours: rhstate OFF2 "smodes": + 0 the pads swallowed (bit p, their release swallowed too), + 4 the menu's state kept around a press.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b, b_cond, b_w, bics_reg, bl, cmp_imm, cmp_reg, h, ldr_imm, ldrb_imm, lsls_imm, lsls_reg,  # noqa: E402
                   lsrs_imm, lsrs_reg, mov_reg, movs_imm, movt, movw, orrs_reg, pop_list, push_list, raw, str_imm, strb_imm, strh_imm, tst_reg)
import countin as CI  # noqa: E402
import granpage as GP  # noqa: E402
import linein as LI  # noqa: E402
import rhstate  # noqa: E402
import slink as SL  # noqa: E402
import stockplus as SP  # noqa: E402
import synthpage as SY  # noqa: E402

O, O_LEN = rhstate.OFF2["smodes"]
R_SWAL, R_MENU = 0, 4
MODE_SMP = GP.MODE_SMP
CONT = SP.CONT
O_MODE = 0x264
# Sample mode's pads (0-based) -> the menu's pad they play
P_SAMPLE, P_GRAN, P_SYNTH, P_LINE, P_LINK, P_SRC, P_GATE = 4, 5, 6, 7, 13, 14, 15
M_GRAN_, M_SYNTH_, M_LINE_, M_LINK_, M_GATE_, M_SRC_ = 10, 11, 12, SL.UI_PAD_LINK, LI.UI_PAD_GATE, LI.UI_PAD_SRC
assert (M_GRAN_, M_SYNTH_, M_LINE_) == (GP.UI_PAD_ENG, SY.UI_PAD_ON, LI.UI_PAD_LINE)
HIDE = (M_LINK_, M_GRAN_, M_SYNTH_, M_LINE_, M_GATE_, M_SRC_)       # the menu's pads moved here
OURS = (P_SAMPLE, P_GRAN, P_SYNTH, P_LINE, P_LINK, P_SRC, P_GATE)
SND = (SY.SND_SAMPLE, SY.SND_GRAN, SY.SND_SYNTH, SY.SND_LINE)
SND_MENU = {SY.SND_GRAN: M_GRAN_, SY.SND_SYNTH: M_SYNTH_, SY.SND_LINE: M_LINE_}
COLS = ((0x01, 0x09), (GP.UI_KNOB, GP.UI_DIM), (SY.UI_KNOB, SY.UI_DIM), (LI.UI_COL, LI.UI_DIM))   # (lit, dim) per sound
SRC_COLS = (LI.UI_DIM,) + tuple(LI.SRC_COLS[1:])                    # the inputs dim (RH56's srcdim), the returns as the FX view's
GATE_COLS = (LI.UI_COL, LI.UI_DIM)
LINK_COLS = (SL.UI_COL, SL.UI_DIM)
MN_O = GP.MN_O
M_GRAN, M_TRK, M_FLAGS, M_SWAL, M_ENV = GP.M_GRAN, GP.M_TRK, GP.M_FLAGS, GP.M_SWAL, 3
F_STICKY = GP.F_STICKY
GATE_BIT, SRC_SHIFT = 4, LI.SRC_SHIFT


def model_leds(sound, linked, line_byte, track):
    """{pad: code} Sample mode's mode pads for a track (the tests'): sound = SND_*, linked = in a pair, line_byte = its line byte (or None)"""
    out = {P_SAMPLE + k: COLS[k][0 if sound == SND[k] else 1] for k in range(4)}
    out[P_LINK] = LINK_COLS[0] if linked else (LINK_COLS[1] if track < 7 else 0)
    if sound == SY.SND_LINE and line_byte is not None:
        out[P_SRC] = SRC_COLS[(line_byte >> SRC_SHIFT) & 3]
        out[P_GATE] = GATE_COLS[0 if line_byte >> GATE_BIT & 1 else 1]
    else:
        out[P_SRC] = out[P_GATE] = 0
    return out


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit
    zc = [0]

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    def bc(target, cond):
        zc[0] += 1
        n = f"_e{zc[0]}"
        E(b_cond, n, SP.INV[cond])
        E(b, target)
        a.label(n)

    # ---- c_smram() -> r0 = our RAM (0 without it); clobbers r1-r3
    a.label("c_smram")
    E(push_list, [4], lr=True)
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "sr_x", "eq")
    E(movw, 1, O)
    E(adds_reg, 0, 0, 1)
    a.label("sr_x")
    E(pop_list, [4], pc=True)

    # ---- c_smview() -> r0 = the selected track while Sample mode is on the screen, else 8; clobbers r1-r3
    a.label("c_smview")
    E(push_list, [4], lr=True)
    E(bl, L["c_spview"])
    E(cmp_imm, 0, 8)
    E(b_cond, "sv_x", "hs")
    imm32(1, CONT + O_MODE)
    E(ldrb_imm, 1, 1, 0)
    E(cmp_imm, 1, MODE_SMP)
    E(b_cond, "sv_x", "eq")
    E(movs_imm, 0, 8)
    a.label("sv_x")
    E(pop_list, [4], pc=True)

    # ---- c_smline(r0 = track) -> r0 = its line byte (track + 1 | gate << 4 | source << 5), 0 when not a line track; clobbers r1-r3
    a.label("c_smline")
    E(push_list, [4], lr=True)
    E(adds_imm8, 0, 1)
    E(mov_reg, 4, 0)
    E(bl, L["c_liget"])
    E(movs_imm, 2, 15)
    E(mov_reg, 3, 0)
    E(raw, h(0x4013))                                                     # ands r3, r2
    E(cmp_reg, 3, 4)
    E(b_cond, "sl_x", "eq")
    E(mov_reg, 0, 1)
    E(mov_reg, 3, 1)
    E(raw, h(0x4013))                                                     # ands r3, r2
    E(cmp_reg, 3, 4)
    E(b_cond, "sl_x", "eq")
    E(movs_imm, 0, 0)
    a.label("sl_x")
    E(pop_list, [4], pc=True)

    # ---- c_smplay(r0 = ctrl, r1 = the menu's pad, r2 = track): the menu's pad pressed and let go for this track, the menu's state as it was
    a.label("c_smplay")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 0)                                                      # r5 = ctrl
    E(mov_reg, 6, 1)                                                      # r6 = the pad
    E(mov_reg, 7, 2)                                                      # r7 = the track
    E(bl, L["c_gpmst"])
    E(cmp_imm, 0, 0)
    bc("pl_x", "eq")
    E(mov_reg, 4, 0)                                                      # r4 = the menu's state
    E(bl, "c_smram")
    E(cmp_imm, 0, 0)
    bc("pl_x", "eq")
    E(mov_reg, 3, 0)
    for k in range(4):                                                    # kept: its 16 bytes
        E(ldr_imm, 1, 4, 4 * k)
        E(str_imm, 1, 3, R_MENU + 4 * k)
    E(adds_imm8, 7, 1)
    E(strb_imm, 7, 4, M_TRK)                                              # sticky, this track's
    E(movs_imm, 1, F_STICKY)
    E(strb_imm, 1, 4, M_FLAGS)
    E(movs_imm, 1, 0)
    E(str_imm, 1, 4, M_SWAL)
    E(mov_reg, 0, 5)
    E(mov_reg, 1, 6)
    E(movs_imm, 2, 100)
    E(bl, prev["pad"])
    E(mov_reg, 0, 5)
    E(mov_reg, 1, 6)
    E(bl, prev["rel"])
    E(bl, "c_smram")                                                      # put back, but the page bits (Granular, Envelope)
    E(ldrb_imm, 1, 4, M_GRAN)
    E(ldrb_imm, 2, 4, M_ENV)
    for k in range(4):
        E(ldr_imm, 3, 0, R_MENU + 4 * k)
        E(str_imm, 3, 4, 4 * k)
    E(strb_imm, 1, 4, M_GRAN)
    E(strb_imm, 2, 4, M_ENV)
    a.label("pl_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)

    # ---- c_smswal(r0 = pad): its release to swallow; clobbers r0-r3
    a.label("c_smswal")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_smram")
    E(cmp_imm, 0, 0)
    E(b_cond, "sw_x", "eq")
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(ldr_imm, 2, 0, R_SWAL)
    E(orrs_reg, 2, 1)
    E(str_imm, 2, 0, R_SWAL)
    a.label("sw_x")
    E(pop_list, [4], pc=True)

    # ---- c_smpad (the controller's pad press, slinkofs's head after it: r0 = ctrl, r1 = pad, r2 = velocity)
    a.label("c_smpad")
    E(cmp_imm, 1, 32)
    bc("sp_p", "hs")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)                                                      # r5 = the pad
    E(bl, L["c_gpmopen"])
    E(cmp_imm, 0, 8)
    E(b_cond, "sp_s", "hs")
    for p in HIDE:                                                        # the menu open: its pads moved to Sample mode, swallowed
        E(cmp_imm, 5, p)
        E(b_cond, "sp_w", "eq")
    E(b, "sp_q")
    a.label("sp_s")
    E(bl, "c_smview")
    E(cmp_imm, 0, 8)
    bc("sp_q", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the track
    E(bl, L["c_spshift"])
    E(cmp_imm, 0, 0)
    bc("sp_q", "ne")
    E(mov_reg, 0, 4)
    E(bl, L["c_sysnd"])
    E(mov_reg, 6, 0)                                                      # r6 = its sound
    E(cmp_imm, 5, P_SAMPLE)
    E(b_cond, "sp_1", "ne")
    for snd, mp in SND_MENU.items():                                      # 5: the one on, off
        E(movs_imm, 1, mp)
        E(cmp_imm, 6, snd)
        E(b_cond, "sp_go", "eq")
    E(b, "sp_w")
    a.label("sp_1")
    for pad, snd, mp in ((P_GRAN, SY.SND_GRAN, M_GRAN_), (P_SYNTH, SY.SND_SYNTH, M_SYNTH_), (P_LINE, SY.SND_LINE, M_LINE_)):
        E(cmp_imm, 5, pad)
        E(b_cond, f"sp_n{pad}", "ne")
        E(movs_imm, 1, mp)
        E(cmp_imm, 6, snd)
        E(b_cond, "sp_go", "ne")                                          # that sound, unless it is on
        E(b, "sp_w")
        a.label(f"sp_n{pad}")
    E(cmp_imm, 5, P_LINK)
    E(b_cond, "sp_2", "ne")
    E(movs_imm, 1, M_LINK_)
    E(b, "sp_go")
    a.label("sp_2")
    for pad, mp in ((P_SRC, M_SRC_), (P_GATE, M_GATE_)):
        E(cmp_imm, 5, pad)
        E(b_cond, f"sp_m{pad}", "ne")
        E(movs_imm, 1, mp)
        E(cmp_imm, 6, SY.SND_LINE)
        E(b_cond, "sp_go", "eq")                                          # the line in's: only on a line track
        E(b, "sp_w")
        a.label(f"sp_m{pad}")
    E(b, "sp_q")                                                          # not ours: the stock's
    a.label("sp_go")
    E(raw, h(0x9800))                                                     # ldr r0, [sp, #0]: ctrl
    E(mov_reg, 2, 4)
    E(bl, "c_smplay")
    a.label("sp_w")
    E(mov_reg, 0, 5)
    E(bl, "c_smswal")
    E(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)
    a.label("sp_q")
    E(raw, GP.popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    a.label("sp_p")
    E(b_w, prev["pad"])

    # ---- c_smrel (the controller's pad release, the head: r0 = ctrl, r1 = pad): one we swallowed, swallowed
    a.label("c_smrel")
    E(cmp_imm, 1, 32)
    bc("sr_p", "hs")
    E(push_list, [0, 1, 2, 3, 4], lr=True)
    E(mov_reg, 4, 1)
    E(bl, "c_smram")
    E(cmp_imm, 0, 0)
    E(b_cond, "sr_q", "eq")
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(ldr_imm, 2, 0, R_SWAL)
    E(tst_reg, 2, 1)
    E(b_cond, "sr_q", "eq")
    E(bics_reg, 2, 1)
    E(str_imm, 2, 0, R_SWAL)
    E(pop_list, [0, 1, 2, 3, 4], pc=True)
    a.label("sr_q")
    E(raw, GP.popw([0, 1, 2, 3, 4], lr=True))
    a.label("sr_p")
    E(b_w, prev["rel"])

    # ---- c_smled (the LED task's calls: ctrl, frame): the chain; the menu without the moved pads; Sample mode's mode pads
    a.label("c_smled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)                                                      # r5 = the frame
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(bl, L["c_gpmopen"])
    E(cmp_imm, 0, 8)
    E(b_cond, "ld_s", "hs")
    E(movs_imm, 0, 0)                                                     # the menu: the moved pads dark
    for p in HIDE:
        E(strh_imm, 0, 5, 2 * p)
    E(b, "ld_x")
    a.label("ld_s")
    E(bl, "c_smview")
    E(cmp_imm, 0, 8)
    bc("ld_x", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the track
    E(bl, L["c_sysnd"])
    E(mov_reg, 6, 0)                                                      # r6 = its sound
    for k, (lit, dim) in enumerate(COLS):
        E(movs_imm, 1, dim)
        E(cmp_imm, 6, SND[k])
        E(b_cond, f"ld_c{k}", "ne")
        E(movs_imm, 1, lit)
        a.label(f"ld_c{k}")
        E(strh_imm, 1, 5, 2 * (P_SAMPLE + k))
    E(bl, L["c_slget"])                                                   # the link: t leads, or t - 1 leads
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(lsls_imm, 2, 0, 1)
    E(orrs_reg, 0, 2)
    E(movs_imm, 2, LINK_COLS[0])
    E(tst_reg, 0, 1)
    E(b_cond, "ld_k", "ne")
    E(movs_imm, 2, LINK_COLS[1])
    E(cmp_imm, 4, 7)
    E(b_cond, "ld_k", "ne")
    E(movs_imm, 2, 0)                                                     # track 8 alone: dark
    a.label("ld_k")
    E(strh_imm, 2, 5, 2 * P_LINK)
    E(movs_imm, 1, 0)
    E(movs_imm, 2, 0)
    E(cmp_imm, 6, SY.SND_LINE)
    E(b_cond, "ld_w", "ne")
    E(mov_reg, 0, 4)
    E(bl, "c_smline")
    E(mov_reg, 7, 0)                                                      # r7 = its line byte
    E(lsrs_imm, 3, 7, SRC_SHIFT)
    E(movs_imm, 1, 3)
    E(raw, h(0x400B))                                                     # ands r3, r1: the source
    E(movs_imm, 1, SRC_COLS[0])
    for k in (1, 2):
        E(cmp_imm, 3, k)
        E(b_cond, f"ld_s{k}", "ne")
        E(movs_imm, 1, SRC_COLS[k])
        a.label(f"ld_s{k}")
    E(movs_imm, 2, GATE_COLS[1])
    E(lsrs_imm, 3, 7, GATE_BIT + 1)
    E(b_cond, "ld_w", "cc")
    E(movs_imm, 2, GATE_COLS[0])
    a.label("ld_w")
    E(strh_imm, 1, 5, 2 * P_SRC)
    E(strh_imm, 2, 5, 2 * P_GATE)
    a.label("ld_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """The controller's pad press (in front of slinkofs's) and release (in front of the menu's), the LED calls.  Needs granpage menu2,
    synthpage menu2 (c_sysnd), linein two fx, slink ui, stockplus, rhstate ram2; not latdiag (its RAM room is ours)."""
    import rhbuild
    BASE = rhbuild.BASE
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    assert "latdiag" not in report and report["granpage"].get("menu2") and report["slink"].get("ui"), "smodes: needs menu2 / ui, not latdiag"
    L = dict(c_rram=lab("rhstate", "c_rram"), c_ciok=lab("countin", "c_ciok"), c_spview=lab("stockplus", "c_spview"),
             c_spshift=lab("stockplus", "c_spshift"), c_gpmopen=lab("granpage", "c_gpmopen"), c_gpmst=lab("granpage", "c_gpmst"),
             c_sysnd=lab("synthpage", "c_sysnd"), c_slget=lab("slink", "c_slget"), c_liget=lab("linein", "c_liget"))
    prev = dict(pad=rhbuild.bw_target(img, GP.PP_ENTRY), rel=rhbuild.bw_target(img, GP.PR_ENTRY),
                ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code_, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code_
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, GP.PP_ENTRY, f"b.w #{prev['pad']:#x}", b_w(GP.PP_ENTRY, labels["c_smpad"]))
    rhbuild.patch(img, GP.PR_ENTRY, f"b.w #{prev['rel']:#x}", b_w(GP.PR_ENTRY, labels["c_smrel"]))
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_smled"]))
    report["smodes"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code_
