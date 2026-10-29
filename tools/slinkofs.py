"""The stereo link's second track as offsets from the first (MIT; RH57; the user, 2026-10-29: «second track's view retain knob destinations
and store deviations: they become bipolar and they affect how much the parameters add or subtract from the first.  Pad selection by default is
still left index+1, but can now be changed by selecting a different pad»; chosen: the R sample keeps the gap, K1-K8 only, link centres and
unlink bakes; then: «right channel sequencer works too. So right channel plays everything on left plus their own»).  On top of RH49's slink
(tools/slink.py), whose code stays as it is.

The stock of the Rhythm (read in its image, emulated on the RAM dump):
  * a track's parameters = the getter 0x08046410(0x10 + t, i) / the setter 0x08031A38 (tools/trkcopy.py's c_tcget / c_tcset); 6..13 = K1-K8;
    the setter marks the index in [0x20006B68 + 4 t] and the track in a byte that 0x0802A08A goes through, up to 3 tracks a call, with the
    track flusher 0x0803081C(t): a turned knob reaches the DSP through the flusher without a note;
  * the knobs keep their values in a store of the track view's too ([subview + 0xC], p0..p7 = K1-K8): a knob turn writes both through the
    parameter router 0x20043740 (the views' [+ 0x14], a heap object fixed after start-up), vtable[0](router, 0x10 t + k, value); the group's
    setter alone leaves the view's store (and so the knob's LED and its next turn) as it was; K1 (the pitch) is held in 4..124, the rest in
    0..127; K2 / K3 are 14-bit (the group's 7 / 8 the high bits, 14 / 15 the low ones: the offsets on the high bits);
  * the selected sample = p0 of the store [player + 0x60] (trkcopy's c_tcsel / c_tcsetsmp); the sample that sounds = index 0 of the group, which
    the player sets at its steps (a step's own sample, or the selection).

Ours (tracks t / t + 1 linked = slink's applied leaders, bit t):
  * the flusher's bl (in front of slink's c_slp; the sends through cue's head, as slink's): for K1-K8 a leader's value goes to the leader as it
    is and to its follower plus the follower's own value - 64; the follower's own sends of K1-K8 = the leader's value + its own - 64 (both
    clamped to the knob's range); a leader's sample goes to its follower plus the gap (below); the follower's own sample (its own steps') as
    it is; the rest (the follower's other parameters, the pans, the leader's other parameters) as slink;
  * the trigger queue (in front of slink's c_slq): the follower's own notes (its own steps, its pads) pass as the stock's (slink dropped them);
    the leader's still go to both: the follower plays the leader's notes and its own;
  * the gap = the follower's selected sample - the leader's (default + 1): the LED task keeps it per pair (rhstate OFF2 "slinkofs": + 0 the
    pairs known (bit t), + 4 + t the gap + 128, + 12 + t / + 20 + t the selections last seen): the leader's selection changed = the follower's
    follows it (the gap kept, clamped); the follower's changed (a pad picked on it) = the new gap, and its sample sent now; a pair seen for
    the first time (power-on, a project loaded: «apply the record»'s end forgets them all, a pair linked) takes the gap from the selections;
  * the track menu's link pad (pad 9, in front of the pad chain): a pair linked = the follower's K1-K8 to the centre and its selection the
    leader's + 1; a pair unlinked = the follower's K1-K8 baked (the leader's + its own - 64), so its sound does not jump (before the centring,
    as a track that led may follow now);
  * Clear + a knob on the follower's stock page (after the stock's own Clear, which deletes the knob's automation) = the centre;
  * the projects of RH49-RH56: slink's block in the project's tail ("S", check, leaders, 0) gets its last byte = VER (the check byte keeps
    slink's sum, which takes that byte in); a block without it was saved before RH57, when the follower's own knobs and pad did nothing:
    once slink has applied it, each follower's K1-K8 go to the centre and its selection to the leader's + 1 (the sound it had), then the
    block is marked; a link made on RH57 marks it (slink's c_slput writes the byte 0: marked again after it, unless the block was old);
  * the LEDs: on the follower's stock page (no page of ours drew the knobs) K1-K8 steel blue (the link's colour, docs/INTERFAZ.md), the
    brightness = |v - 64| x 2 (dark in the centre), through kbright's overlay.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm3, adds_imm8, adds_reg, b, b_cond, b_w, bics_reg, bl, blx_reg, cmp_imm, cmp_reg, eors_reg, h, ldr_imm, ldr_sp, ldrb_imm, lsls_imm,  # noqa: E402
                   lsls_reg, lsrs_imm, lsrs_reg, mov_reg, movs_imm, movt, movw, orrs_reg, pop_list, push_list, raw, str_sp, strb_imm, strh_imm,
                   strh_w_imm, subs_imm3, subs_imm8, subs_reg, tst_reg)
import countin as CI  # noqa: E402
import granpage as GP  # noqa: E402
import patchain as PC  # noqa: E402
import rhstate  # noqa: E402
import slink as SL  # noqa: E402
import stockplus as SP  # noqa: E402
import trkcopy as TC  # noqa: E402

O, O_LEN = rhstate.OFF2["slinkofs"]                  # in latdiag's room after clkci's (rhstate.SHARED)
R_INIT, R_GAP, R_LASTL, R_LASTR = 0, 4, 12, 20
assert R_LASTR + 8 <= O_LEN
KNOB_LO, KNOB_HI, CENTRE, VMAX = 6, 13, 64, 127
K1_MIN, K1_MAX = 4, 124                               # the stock holds K1 (the pitch) in 4..124
ROUTER = 0x20043740                                   # the parameter router: vtable[0](router, 0x10 t + k, value)
GAP_BIAS = 128
I_SAMPLE = SL.I_SAMPLE
VER = 0x57                                            # the last byte of slink's block: made on RH57 (the follower's knobs as offsets)
PAD_LINK = SL.UI_PAD_LINK
COL = SL.UI_COL                                       # steel blue: the link's colour
O_KB = rhstate.OFF["kbright"][0]
K_MASK, K_VAL, K_CODE = SP.K_MASK, SP.K_VAL, SP.K_CODE
LED_KNOB0 = SP.LED_KNOB0
CONT, SUBVIEW = SP.CONT, SP.SUBVIEW
SLOT_KNOB = GP.SLOT_KNOB
BIT_CLEAR = SP.BIT_CLEAR


def clamp(v, i=0): return max(K1_MIN, min(K1_MAX, v)) if i == KNOB_LO else max(0, min(VMAX, v))


def model_sends(mask, t, i, v, get, gap):
    """[(track, index, value)] the flusher sends for (t, i, v) with these leaders; get(t, i) = the store, gap(t) = pair t's gap (the tests')"""
    if (KNOB_LO <= i <= KNOB_HI or i == I_SAMPLE) and t > 0 and mask >> (t - 1) & 1:
        return [(t, i, clamp(get(t - 1, i) + v - CENTRE, i))] if i != I_SAMPLE else [(t, i, v)]
    if KNOB_LO <= i <= KNOB_HI and mask >> t & 1:
        return [(t, i, v), (t + 1, i, clamp(v + get(t + 1, i) - CENTRE, i))]
    if i == I_SAMPLE and mask >> t & 1:
        return [(t, i, v), (t + 1, i, clamp(v + gap(t)))]
    return SL.model_sends(mask, t, i, v)


def arm_code(base, L, prev, P, Q):
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

    # ---- c_soclampi(r0 = value, r1 = index) -> r0 clamped to the knob's range (signed); c_soclamp(r0): 0..127
    a.label("c_soclampi")
    E(cmp_imm, 1, KNOB_LO)
    E(b_cond, "c_soclamp", "ne")
    E(cmp_imm, 0, K1_MIN)
    E(b_cond, "cl_1h", "ge")
    E(movs_imm, 0, K1_MIN)
    a.label("cl_1h")
    E(cmp_imm, 0, K1_MAX)
    E(b_cond, "cl_x", "le")
    E(movs_imm, 0, K1_MAX)
    E(raw, h(0x4770))
    a.label("c_soclamp")
    E(cmp_imm, 0, 0)
    E(b_cond, "cl_h", "ge")
    E(movs_imm, 0, 0)
    a.label("cl_h")
    E(cmp_imm, 0, VMAX)
    E(b_cond, "cl_x", "le")
    E(movs_imm, 0, VMAX)
    a.label("cl_x")
    E(raw, h(0x4770))

    # ---- c_soram() -> r0 = our RAM, 0 without it; clobbers r1-r3
    a.label("c_soram")
    E(push_list, [4], lr=True)
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "or_x", "eq")
    E(movw, 1, O)
    E(adds_reg, 0, 0, 1)
    a.label("or_x")
    E(pop_list, [4], pc=True)

    # ---- c_soput(r0 = track, r1 = index 6..13, r2 = value): the knob through the parameter router (the view's store and the group, as a
    # turn); clobbers r0-r3, r12
    a.label("c_soput")
    E(push_list, [4], lr=True)
    E(lsls_imm, 0, 0, 4)
    E(adds_reg, 1, 0, 1)
    E(subs_imm8, 1, KNOB_LO)
    imm32(0, ROUTER)
    E(ldr_imm, 3, 0, 0)
    E(ldr_imm, 3, 3, 0)
    E(blx_reg, 3)
    E(pop_list, [4], pc=True)

    # ---- c_sosel(r0 = track) -> r0 = its selected sample; clobbers r1-r3
    a.label("c_sosel")
    E(push_list, [4], lr=True)
    E(bl, L["c_tcsel"])
    E(movs_imm, 1, 0)
    E(bl, L["c_cinew"])
    E(pop_list, [4], pc=True)

    # ---- c_sogap(r0 = leader) -> r0 = the pair's gap (the one kept, or the selections' while not known); clobbers r1-r3
    a.label("c_sogap")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_soram")
    E(cmp_imm, 0, 0)
    E(b_cond, "gp_s", "eq")
    E(ldrb_imm, 1, 0, R_INIT)
    E(lsrs_reg, 1, 4)
    E(lsls_imm, 1, 1, 31)
    E(b_cond, "gp_s", "eq")
    E(adds_reg, 0, 0, 4)
    E(ldrb_imm, 0, 0, R_GAP)
    E(subs_imm8, 0, GAP_BIAS)
    E(pop_list, [4, 5, 6], pc=True)
    a.label("gp_s")
    E(adds_imm3, 0, 4, 1)
    E(bl, "c_sosel")
    E(mov_reg, 5, 0)
    E(mov_reg, 0, 4)
    E(bl, "c_sosel")
    E(subs_reg, 0, 5, 0)
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_soold() -> r0 = 1 when slink's block is valid and made before RH57; clobbers r1-r3
    a.label("c_soold")
    E(push_list, [4], lr=True)
    E(bl, L["c_slblk"])
    E(cmp_imm, 0, 0)
    E(b_cond, "od_0", "eq")
    E(ldrb_imm, 0, 0, 3)
    E(cmp_imm, 0, VER)
    E(b_cond, "od_0", "eq")
    E(movs_imm, 0, 1)
    E(pop_list, [4], pc=True)
    a.label("od_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)

    # ---- c_somark(): slink's block (when valid) marked as RH57's, its check byte with it; clobbers r0-r3
    a.label("c_somark")
    E(push_list, [4], lr=True)
    E(bl, L["c_slblk"])
    E(cmp_imm, 0, 0)
    E(b_cond, "mk_x", "eq")
    E(movs_imm, 1, VER)
    E(strb_imm, 1, 0, 3)
    E(ldrb_imm, 2, 0, 2)
    E(eors_reg, 2, 1)
    E(movs_imm, 1, SL.CHECK ^ SL.MARK)
    E(eors_reg, 2, 1)
    E(strb_imm, 2, 0, 1)
    a.label("mk_x")
    E(pop_list, [4], pc=True)

    # ---- c_sop (the flusher's bl at 0x0803085E, slink's c_slp after it: r0 = t, r1 = index, r2 = value)
    a.label("c_sop")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(mov_reg, 6, 2)
    E(cmp_imm, 5, I_SAMPLE)
    E(b_cond, "op_k", "eq")
    E(cmp_imm, 5, KNOB_LO)
    E(b_cond, "op_s", "lo")
    E(cmp_imm, 5, KNOB_HI)
    E(b_cond, "op_s", "hi")
    a.label("op_k")
    E(bl, L["c_slm"])
    E(mov_reg, 7, 0)                                                      # r7 = the leaders applied
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)                                                     # r1 = bit t
    E(lsrs_imm, 2, 1, 1)
    E(tst_reg, 7, 2)
    E(b_cond, "op_f", "ne")                                               # a follower's own
    E(tst_reg, 7, 1)
    E(b_cond, "op_s", "eq")                                               # not linked: slink's (the stock's)
    E(mov_reg, 0, 4)                                                      # a leader: its own as it is ...
    E(mov_reg, 1, 5)
    E(mov_reg, 2, 6)
    E(bl, P)
    E(cmp_imm, 5, I_SAMPLE)
    E(b_cond, "op_ls", "eq")
    E(adds_imm3, 0, 4, 1)                                                 # ... and the follower's: + its offset
    E(mov_reg, 1, 5)
    E(bl, L["c_tcget"])
    E(adds_reg, 0, 0, 6)
    E(subs_imm8, 0, CENTRE)
    E(b, "op_lw")
    a.label("op_ls")
    E(mov_reg, 0, 4)                                                      # ... the follower's sample: + the gap
    E(bl, "c_sogap")
    E(adds_reg, 0, 0, 6)
    a.label("op_lw")
    E(mov_reg, 1, 5)
    E(bl, "c_soclampi")
    E(mov_reg, 2, 0)
    E(adds_imm3, 0, 4, 1)
    E(mov_reg, 1, 5)
    E(bl, P)
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    a.label("op_f")
    E(cmp_imm, 5, I_SAMPLE)
    E(b_cond, "op_o", "ne")
    E(mov_reg, 0, 4)                                                      # its own sample (its own steps'): as it is
    E(mov_reg, 1, 5)
    E(mov_reg, 2, 6)
    E(bl, P)
    E(b, "op_x")
    a.label("op_o")
    E(subs_imm3, 0, 4, 1)                                                 # a knob: the leader's + its own offset
    E(mov_reg, 1, 5)
    E(bl, L["c_tcget"])
    E(adds_reg, 0, 0, 6)
    E(subs_imm8, 0, CENTRE)
    E(mov_reg, 1, 5)
    E(bl, "c_soclampi")
    E(mov_reg, 2, 0)
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, P)
    a.label("op_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    a.label("op_s")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(mov_reg, 2, 6)
    E(raw, GP.popw([3, 4, 5, 6, 7], lr=True))
    E(b_w, L["c_slp"])

    # ---- c_soq (0x080406A8's head, slink's c_slq after it: r0 = the message): a follower's own note as the stock's (qfull's), the rest slink's
    a.label("c_soq")
    E(push_list, [0, 1, 2, 3, 4], lr=True)
    E(ldr_imm, 1, 0, 0)                                                   # r1 = w0
    E(lsrs_imm, 2, 1, 20)
    E(cmp_imm, 2, 8)
    E(b_cond, "sq_s", "lo")
    E(cmp_imm, 2, 9)
    E(b_cond, "sq_s", "hi")                                               # notes only
    E(movs_imm, 4, 7)
    E(raw, h(0x400C))                                                     # ands r4, r1: t
    E(cmp_imm, 4, 0)
    E(b_cond, "sq_s", "eq")
    E(bl, L["c_slm"])
    E(subs_imm3, 1, 4, 1)
    E(lsrs_reg, 0, 1)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "sq_s", "eq")                                               # not a follower
    E(raw, GP.popw([0, 1, 2, 3, 4], lr=True))
    E(b_w, Q)
    a.label("sq_s")
    E(raw, GP.popw([0, 1, 2, 3, 4], lr=True))
    E(b_w, L["c_slq"])

    # ---- c_sobake(r0 = a follower that no longer follows): its K1-K8 = the leader's + its own - 64
    a.label("c_sobake")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(movs_imm, 5, KNOB_LO)
    a.label("bk_l")
    E(subs_imm3, 0, 4, 1)
    E(mov_reg, 1, 5)
    E(bl, L["c_tcget"])
    E(mov_reg, 6, 0)
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, L["c_tcget"])
    E(adds_reg, 0, 0, 6)
    E(subs_imm8, 0, CENTRE)
    E(mov_reg, 1, 5)
    E(bl, "c_soclampi")
    E(mov_reg, 2, 0)
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, "c_soput")
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, KNOB_HI)
    E(b_cond, "bk_l", "ls")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)

    # ---- c_socentre(r0 = a new follower): its K1-K8 to the centre, its selection the leader's + 1, the pair's gap to learn again
    a.label("c_socentre")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(movs_imm, 5, KNOB_LO)
    a.label("ce_l")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(movs_imm, 2, CENTRE)
    E(bl, "c_soput")
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, KNOB_HI)
    E(b_cond, "ce_l", "ls")
    E(subs_imm3, 0, 4, 1)
    E(bl, "c_sosel")
    E(adds_imm8, 0, 1)
    E(bl, "c_soclamp")
    E(mov_reg, 1, 0)
    E(mov_reg, 0, 4)
    E(bl, L["c_tcsetsmp"])
    E(bl, "c_soram")
    E(cmp_imm, 0, 0)
    E(b_cond, "ce_x", "eq")
    E(subs_imm3, 1, 4, 1)
    E(movs_imm, 2, 1)
    E(lsls_reg, 2, 1)
    E(ldrb_imm, 1, 0, R_INIT)
    E(bics_reg, 1, 2)
    E(strb_imm, 1, 0, R_INIT)
    a.label("ce_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)

    # ---- c_sopad (the controller's pad press, synthpage's head after it: r0 = ctrl, r1 = pad, r2 = velocity): the menu's link pad
    a.label("c_sopad")
    E(cmp_imm, 1, PAD_LINK)
    bc("sd_p", "ne")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(bl, L["c_gpmopen"])
    E(cmp_imm, 0, 8)
    bc("sd_q", "hs")                                                      # the menu closed: not the link pad
    E(bl, "c_soold")
    E(mov_reg, 5, 0)                                                      # r5 = the block made before RH57 (its migration still to come)
    E(bl, L["c_slget"])
    E(mov_reg, 4, 0)                                                      # r4 = the leaders before
    E(ldr_sp, 0, 0)
    E(ldr_sp, 1, 4)
    E(ldr_sp, 2, 8)
    E(bl, prev["pad"])
    E(str_sp, 0, 0)
    E(bl, L["c_slget"])
    E(lsls_imm, 7, 0, 1)                                                  # r7 = the followers after
    E(lsls_imm, 6, 4, 1)                                                  # r6 = the followers before
    E(mov_reg, 0, 6)
    E(bics_reg, 6, 7)                                                     # r6 = no longer following: baked first ...
    E(bics_reg, 7, 0)                                                     # r7 = following now: ... then centred
    for reg, fn, lp in ((6, "c_sobake", "sd_b"), (7, "c_socentre", "sd_c")):
        E(movs_imm, 4, 1)
        a.label(lp)
        E(movs_imm, 0, 1)
        E(lsls_reg, 0, 4)
        E(tst_reg, reg, 0)
        E(b_cond, lp + "n", "eq")
        E(mov_reg, 0, 4)
        E(bl, fn)
        a.label(lp + "n")
        E(adds_imm8, 4, 1)
        E(cmp_imm, 4, 8)
        E(b_cond, lp, "lo")
    E(cmp_imm, 5, 0)
    E(b_cond, "sd_x", "ne")
    E(bl, "c_somark")                                                     # slink wrote the block: ours again
    a.label("sd_x")
    E(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)
    a.label("sd_q")
    E(raw, GP.popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    a.label("sd_p")
    E(b_w, prev["pad"])

    # ---- c_sostock(r0 = track) -> r0 = 1 on its stock page (not Stock+, Granular, Synth or Envelope); clobbers r1-r3
    a.label("c_sostock")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, L["c_spst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ss_g", "eq")
    E(ldrb_imm, 0, 0, 0)
    E(lsrs_reg, 0, 4)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "ss_0", "ne")
    a.label("ss_g")
    for fn in ("c_gpgran", "c_sypage", "c_evon"):
        E(mov_reg, 0, 4)
        E(bl, L[fn])
        E(cmp_imm, 0, 0)
        E(b_cond, "ss_0", "ne")
    E(movs_imm, 0, 1)
    E(pop_list, [4], pc=True)
    a.label("ss_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)

    # ---- c_sofol() -> r0 = the selected track when it follows in the track views (knobs shown), else 0; clobbers r1-r3
    a.label("c_sofol")
    E(push_list, [4], lr=True)
    E(bl, L["c_spview"])
    E(cmp_imm, 0, 8)
    E(b_cond, "sf_0", "hs")
    E(cmp_imm, 0, 0)
    E(b_cond, "sf_0", "eq")
    E(mov_reg, 4, 0)
    E(bl, L["c_slm"])
    E(subs_imm3, 1, 4, 1)
    E(lsrs_reg, 0, 1)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "sf_0", "eq")
    imm32(0, CONT)
    E(bl, SUBVIEW)
    E(cmp_imm, 0, 0)
    E(b_cond, "sf_0", "eq")                                               # no knobs in this mode
    E(mov_reg, 0, 4)
    E(pop_list, [4], pc=True)
    a.label("sf_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)

    # ---- c_soknob (the container's knob slot, spall's head after it: r0 = the container, r1 = k, r2 = the delta): Clear + a follower's knob
    a.label("c_soknob")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(bl, prev["knob"])
    E(str_sp, 0, 0)
    E(ldr_sp, 5, 4)                                                       # r5 = k
    E(cmp_imm, 5, 8)
    E(b_cond, "kn_x", "hs")
    E(bl, L["c_spheld"])
    E(lsls_imm, 0, 0, 31 - BIT_CLEAR)
    E(b_cond, "kn_x", "pl")
    E(bl, "c_sofol")
    E(cmp_imm, 0, 0)
    E(b_cond, "kn_x", "eq")
    E(mov_reg, 4, 0)
    E(bl, "c_sostock")
    E(cmp_imm, 0, 0)
    E(b_cond, "kn_x", "eq")
    E(mov_reg, 0, 4)                                                      # the offset to the centre
    E(adds_imm3, 1, 5, KNOB_LO)
    E(movs_imm, 2, CENTRE)
    E(bl, "c_soput")
    a.label("kn_x")
    E(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)

    # ---- c_soload (the end of «apply the record», r0-r3 = the stock's tail call's): the gaps to learn again
    a.label("c_soload")
    E(raw, TC.pushw([0, 1, 2, 3, 12], lr=True))
    E(bl, "c_soram")
    E(cmp_imm, 0, 0)
    E(b_cond, "sl_x", "eq")
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 0, R_INIT)
    a.label("sl_x")
    E(raw, GP.popw([0, 1, 2, 3, 12], lr=True))
    E(b_w, prev["load"])

    # ---- c_sotrk(r0 = leader, r1 = our RAM): the pair's selections and gap
    a.label("c_sotrk")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 6, 1)
    E(bl, "c_sosel")
    E(mov_reg, 5, 0)                                                      # r5 = the leader's selection
    E(adds_imm3, 0, 4, 1)
    E(bl, "c_sosel")
    E(mov_reg, 7, 0)                                                      # r7 = the follower's
    E(ldrb_imm, 0, 6, R_INIT)
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(tst_reg, 0, 1)
    E(b_cond, "tk_k", "ne")
    E(orrs_reg, 0, 1)                                                     # first seen: the gap from the selections
    E(strb_imm, 0, 6, R_INIT)
    E(adds_reg, 1, 6, 4)
    E(subs_reg, 0, 7, 5)
    E(adds_imm8, 0, GAP_BIAS)
    E(strb_imm, 0, 1, R_GAP)
    E(strb_imm, 5, 1, R_LASTL)
    E(strb_imm, 7, 1, R_LASTR)
    E(b, "tk_s")                                                          # and its sample now (as the gap says)
    a.label("tk_k")
    E(adds_reg, 1, 6, 4)
    E(ldrb_imm, 0, 1, R_LASTL)
    E(cmp_reg, 0, 5)
    E(b_cond, "tk_r", "eq")
    E(strb_imm, 5, 1, R_LASTL)                                            # the leader's changed: the follower's follows (the gap kept)
    E(ldrb_imm, 0, 1, R_GAP)
    E(adds_reg, 0, 0, 5)
    E(subs_imm8, 0, GAP_BIAS)
    E(bl, "c_soclamp")
    E(cmp_reg, 0, 7)
    E(b_cond, "tk_w", "eq")
    E(mov_reg, 7, 0)
    E(mov_reg, 1, 0)
    E(adds_imm3, 0, 4, 1)
    E(bl, L["c_tcsetsmp"])
    a.label("tk_w")
    E(adds_reg, 1, 6, 4)
    E(strb_imm, 7, 1, R_LASTR)
    E(b, "tk_x")
    a.label("tk_r")
    E(ldrb_imm, 0, 1, R_LASTR)
    E(cmp_reg, 0, 7)
    E(b_cond, "tk_x", "eq")
    E(strb_imm, 7, 1, R_LASTR)                                            # the follower's changed: the new gap, its sample now
    E(subs_reg, 0, 7, 5)
    E(adds_imm8, 0, GAP_BIAS)
    E(strb_imm, 0, 1, R_GAP)
    a.label("tk_s")
    E(mov_reg, 0, 4)
    E(movs_imm, 1, I_SAMPLE)
    E(bl, L["c_tcget"])
    E(adds_reg, 0, 0, 7)
    E(subs_reg, 0, 0, 5)
    E(bl, "c_soclamp")
    E(mov_reg, 2, 0)
    E(adds_imm3, 0, 4, 1)
    E(movs_imm, 1, I_SAMPLE)
    E(bl, P)
    a.label("tk_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)

    # ---- c_soled (the LED task's calls: ctrl, frame): the chain; the pairs' gaps; the follower's knobs
    a.label("c_soled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)                                                      # r5 = the frame
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(bl, "c_soram")
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(mov_reg, 6, 0)                                                      # r6 = our RAM
    E(bl, L["c_slm"])
    E(mov_reg, 7, 0)                                                      # r7 = the leaders applied
    E(ldrb_imm, 0, 6, R_INIT)
    E(raw, h(0x4038))                                                     # ands r0, r7: the pairs no longer linked forgotten
    E(strb_imm, 0, 6, R_INIT)
    E(bl, "c_soold")
    E(cmp_imm, 0, 0)
    E(b_cond, "ld_l", "eq")
    E(bl, L["c_slget"])
    E(cmp_reg, 0, 7)
    E(b_cond, "ld_l", "ne")                                               # a block made before RH57, applied by slink: migrated
    E(movs_imm, 4, 0)
    a.label("ld_mg")
    E(mov_reg, 0, 7)
    E(lsrs_reg, 0, 4)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "ld_mn", "eq")
    E(adds_imm3, 0, 4, 1)
    E(bl, "c_socentre")                                                   # the follower's knobs centred, its pad the leader's + 1
    a.label("ld_mn")
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, 7)
    E(b_cond, "ld_mg", "lo")
    E(bl, "c_somark")
    a.label("ld_l")
    E(movs_imm, 4, 0)
    a.label("ld_t")
    E(mov_reg, 0, 7)
    E(lsrs_reg, 0, 4)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "ld_n", "eq")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 6)
    E(bl, "c_sotrk")
    a.label("ld_n")
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, 7)
    E(b_cond, "ld_t", "lo")
    E(bl, "c_sofol")
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(mov_reg, 4, 0)                                                      # r4 = the follower on the screen
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(movw, 1, O_KB)
    E(adds_reg, 7, 0, 1)                                                  # r7 = kbright's overlay
    E(ldrb_imm, 0, 7, K_MASK)
    E(cmp_imm, 0, 0)
    bc("ld_x", "ne")                                                      # a page of ours drew the knobs
    E(movs_imm, 0, 0xFF)
    E(strb_imm, 0, 7, K_MASK)
    E(movs_imm, 6, 0)
    a.label("ld_k")
    E(mov_reg, 0, 4)
    E(adds_imm3, 1, 6, KNOB_LO)
    E(bl, L["c_tcget"])
    E(subs_imm8, 0, CENTRE)                                               # from the centre: |v - 64| x 2
    E(b_cond, "ld_q", "ge")
    E(raw, h(0x4240))                                                     # rsbs r0, r0, #0
    a.label("ld_q")
    E(lsls_imm, 0, 0, 1)
    E(cmp_imm, 0, VMAX)
    E(b_cond, "ld_u", "le")
    E(movs_imm, 0, VMAX)
    a.label("ld_u")
    E(adds_reg, 1, 7, 6)
    E(strb_imm, 0, 1, K_VAL)
    E(lsls_imm, 1, 6, 1)
    E(adds_reg, 1, 1, 7)
    E(movs_imm, 0, COL)
    E(strh_imm, 0, 1, K_CODE)
    E(lsls_imm, 1, 6, 1)
    E(adds_reg, 1, 1, 5)
    E(strh_w_imm, 0, 1, 2 * LED_KNOB0)
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, 8)
    E(b_cond, "ld_k", "lo")
    a.label("ld_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """The flusher's bl and the trigger queue's head (in front of slink's), the controller's pad press (in front of synthpage's), the container's knob slot (in front of
    spall's), the end of «apply the record», the LED calls.  Needs slink ui, trkcopy, stockplus, granpage menu2, synthpage, envpage, kbright,
    rhstate ram2; not latdiag (its RAM room is ours)."""
    import rhbuild
    BASE = rhbuild.BASE
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    u = lambda a: struct.unpack_from("<I", img, a - BASE)[0]                   # noqa: E731
    assert report["slink"].get("ui") and "latdiag" not in report, "slinkofs: needs slink ui; shares latdiag's RAM room (rhstate.SHARED)"
    L = dict(c_rst=lab("rhstate", "c_rst"), c_rram=lab("rhstate", "c_rram"), c_ciok=lab("countin", "c_ciok"), c_cinew=lab("countin", "c_cinew"),
             **{k: lab("slink", k) for k in ("c_slm", "c_slget", "c_slblk", "c_slp", "c_slq")},
             **{k: lab("trkcopy", k) for k in ("c_tcget", "c_tcsel", "c_tcsetsmp")},
             **{k: lab("stockplus", k) for k in ("c_spview", "c_spheld", "c_spst")},
             **{k: lab("granpage", k) for k in ("c_gpmopen", "c_gpgran")}, c_sypage=lab("synthpage", "c_sypage"), c_evon=lab("envpage", "c_evon"))
    prev = dict(param=rhbuild.bl_target(img, SL.FLUSH_CALL), queue=rhbuild.bw_target(img, SL.QWRITE), pad=rhbuild.bw_target(img, GP.PP_ENTRY),
                knob=u(SLOT_KNOB) & ~1,
                load=rhbuild.bw_target(img, PC.LOAD_TAIL), ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert prev["param"] == L["c_slp"] and prev["queue"] == L["c_slq"], "slinkofs: slink's c_slp / c_slq must be the hooks' heads"
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    P = int(report["slink"]["prev"]["param"], 16)                             # the sends: cue's head, as slink's
    Q = int(report["slink"]["prev"]["queue"], 16)                             # a follower's own notes: qfull's head, as an unlinked track's
    code_, labels = arm_code(base_addr, L, prev, P, Q)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code_
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, SL.FLUSH_CALL, f"bl #{prev['param']:#x}", bl(SL.FLUSH_CALL, labels["c_sop"]))
    rhbuild.patch(img, SL.QWRITE, f"b.w #{prev['queue']:#x}", b_w(SL.QWRITE, labels["c_soq"]))
    rhbuild.patch(img, GP.PP_ENTRY, f"b.w #{prev['pad']:#x}", b_w(GP.PP_ENTRY, labels["c_sopad"]))
    rhbuild.patch_word(img, SLOT_KNOB, prev["knob"] | 1, labels["c_soknob"] | 1)
    rhbuild.patch(img, PC.LOAD_TAIL, f"b.w #{prev['load']:#x}", b_w(PC.LOAD_TAIL, labels["c_soload"]))
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_soled"]))
    report["slinkofs"] = dict(prev={k: hex(v) for k, v in prev.items()}, send=hex(P), own=hex(Q),
                              labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code_
