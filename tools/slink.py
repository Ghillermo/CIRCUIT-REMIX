"""Stereo link: a track and the next one play as one stereo sound (MIT; RH49; the user, 2026-10-27: «both» (the stereo link and the synth
design), «Any track + the next»).  The other half of RH43's stereo Sample Rec, which saves L in slot A and R in slot A + 1.

The stock of the Rhythm (read in its image; tools/cue.py, tools/qfull.py):
  * a track's sound parameters reach the DSP only through the track flusher 0x0803081C(t), which sends each index marked in
    [0x20006B68 + 4 t] (bits 0..24) with 0x0804070E(t, index, value) (the bl at 0x0803085E, cue's in front); index 0 = the sample (0..127:
    sending it also sends a note-off for the track), 0x10 the level, 0x11 the pan (0..127, 64 = the centre), 0x12 / 0x13 the sends;
  * a note: 0x08040778(code, note, velocity) runs the flusher first, then a note-off when a voice still sounds, then the note-on; each message
    goes to core 1's trigger queue through 0x080406A8(message) (qfull's head in front): {w0, w1}, w0 = $80 / $90 << 16 | t << 16 | velocity << 8
    | t, the pair at X:$30410 + 2 i (i = the ARM's write index [0x20006F38]), then the new index into X:$307B5, each with 0x08031228; core 1
    takes every message waiting at each block (RH42's qdrain), so a message is seen when the index is written.
Ours (track t leads, t + 1 follows; the project's block rhrec "slink": "S", a check byte, the leaders (bit t, t = 0..6), 0):
  * the flusher's sends: a leader's go to the leader and to its follower, the sample + 1 (the R of a stereo recording; 127 stays) and the pan
    hard left (leader) / hard right (follower); a follower's own sends are dropped (its sound is the leader's while linked);
  * the queue: a follower's own messages are dropped; a leader's message is written twice, the follower's copy (the track fields t + 1) first
    at the write slot, then the leader's through qfull and the stock, whose one index write shows both at once: the two voices start in the
    same block (written apart, core 1 would start them a block = 32 samples apart about half the time); room for two is waited for first,
    with qfull's state (at most 3 ms);
  * the track menu (a track button held, RH45): pad 7 = link this track with the next (lit), on the follower = unlink (lit in the other
    colour), on a leader = unlink; track 8 alone: dark;
  * the LED task (rhstate OFF2 "slink": + 0 the leaders applied, + 1 applied once): when the block's leaders differ from those applied, the
    applied ones change and every track whose role changed (but a new follower) gets all its 25 parameters marked and the flusher run.
Not linked (each voice of core 1 has its own): the free-running pitch LFO and the free-running start scan (Stock+ K3 / K8: at the tempo they
run from the same tick); WSOLA (the stretch) aligns each side on its own.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm3, adds_imm8, adds_reg, b, b_cond, b_w, bics_reg, bl, cmp_imm, cmp_reg, eors_reg, h, ldr_imm, ldrb_imm,  # noqa: E402
                   ldrb_w, lsls_imm, lsls_reg, lsrs_imm, mov_reg, movs_imm, movt, movw, orrs_reg, pop_list, push_list, raw, str_imm, strb_imm,
                   strh_imm, subs_imm3, subs_reg, tst_reg)
import countin as CI  # noqa: E402
import cthresh as TH  # noqa: E402
import granpage as GP  # noqa: E402
import rhrec  # noqa: E402
import rhstate  # noqa: E402

QWRITE, QIDX, QBASE, QWIDX, QREAD = 0x080406A8, 0x20006F38, 0x30410, 0x307B5, 0x307B6
DSP_WRITE, DSP_READ = 0x08031228, 0x080314D6
FLUSH_CALL, PARAM_SEND, FLUSH, DIRTY = 0x0803085E, 0x0804070E, 0x0803081C, 0x20006B68
NOTE_ON = 0x08040778
NPAR = 25
ALL = (1 << NPAR) - 1
I_SAMPLE, I_PAN = 0, 0x11
PAN_L, PAN_R, SMAX = 0, 127, 127
TFIELD = 0x070007                                     # the track's two fields of w0
MARK, CHECK = 0x53, 0x6C                              # "S"
BLK, BLK_LEN = rhrec.OFF["slink"]
O = rhstate.OFF2["slink"][0]
R_MASK, R_SEEN = 0, 1
OQ = rhstate.OFF2["qfull"][0]
O_TH = rhstate.OFF["cthresh"][0] + 1
PAD_LINK = 6                                          # the menu's pad 7
# ui (RH52; docs/INTERFAZ.md): the menu's pad 9 (the row under the pages, under stock), steel blue: bright = linked (either track of the
# pair), dim = not, dark on track 8 alone
UI_PAD_LINK, UI_COL, UI_DIM = 8, 0x16, 0x17
PAL, PAL_ON, PAL_TON, PAL_TOFF = GP.PAL, GP.PAL_ON, GP.PAL_TON, GP.PAL_TOFF
PP_ENTRY, M_SWAL = GP.PP_ENTRY, GP.M_SWAL
WAIT_MS = 3


def model_sends(mask, t, i, v):
    """[(track, index, value)] the stock's flusher sends for (t, i, v) with these leaders (the tests')"""
    if t > 0 and mask >> (t - 1) & 1:
        return []
    if not mask >> t & 1:
        return [(t, i, v)]
    vl = PAN_L if i == I_PAN else v
    vf = PAN_R if i == I_PAN else (min(v + 1, SMAX) if i == I_SAMPLE else v)
    return [(t, i, vl), (t + 1, i, vf)]


def sane(m):
    """the leaders as the hooks take them: tracks 1-7, none that follows another"""
    m &= 0x7F
    return m & ~(m << 1) & 0xFF


def arm_code(base, L, prev, ui=False):
    pad = UI_PAD_LINK if ui else PAD_LINK
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_slram() -> r0 = our RAM, 0 without it; clobbers r1-r3
    a.label("c_slram")
    E(push_list, [4], lr=True)
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "sr_x", "eq")
    E(movw, 1, O)
    E(adds_reg, 0, 0, 1)
    a.label("sr_x")
    E(pop_list, [4], pc=True)

    # ---- c_slm() -> r0 = the leaders applied (0 without our RAM); clobbers r1-r3
    a.label("c_slm")
    E(push_list, [4], lr=True)
    E(bl, "c_slram")
    E(cmp_imm, 0, 0)
    E(b_cond, "sm_x", "eq")
    E(ldrb_imm, 0, 0, R_MASK)
    a.label("sm_x")
    E(pop_list, [4], pc=True)

    # ---- c_slblk() -> r0 = our block when valid, else 0; r1 = its place (0 without a record); clobbers r2, r3
    a.label("c_slblk")
    E(push_list, [4], lr=True)
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "sb_0", "eq")
    E(movw, 1, BLK)
    E(adds_reg, 0, 0, 1)
    E(mov_reg, 1, 0)
    E(ldrb_imm, 2, 0, 0)
    E(cmp_imm, 2, MARK)
    E(b_cond, "sb_n", "ne")
    E(ldrb_imm, 2, 0, 2)
    E(ldrb_imm, 3, 0, 3)
    E(eors_reg, 2, 3)
    E(movs_imm, 3, CHECK ^ MARK)
    E(eors_reg, 2, 3)
    E(ldrb_imm, 3, 0, 1)
    E(cmp_reg, 2, 3)
    E(b_cond, "sb_x", "eq")
    a.label("sb_n")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)
    a.label("sb_0")
    E(movs_imm, 1, 0)
    a.label("sb_x")
    E(pop_list, [4], pc=True)

    # ---- c_slget() -> r0 = the block's leaders, sane (0 without the block); clobbers r1-r3
    a.label("c_slget")
    E(push_list, [4], lr=True)
    E(bl, "c_slblk")
    E(cmp_imm, 0, 0)
    E(b_cond, "sg_x", "eq")
    E(ldrb_imm, 0, 0, 2)
    E(movs_imm, 1, 0x7F)
    E(raw, h(0x4008))                                                     # ands r0, r1
    E(lsls_imm, 1, 0, 1)
    E(bics_reg, 0, 1)
    a.label("sg_x")
    E(pop_list, [4], pc=True)

    # ---- c_slput(r0 = the leaders): the block (made when missing); clobbers r0-r3
    a.label("c_slput")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_slblk")
    E(cmp_imm, 1, 0)
    E(b_cond, "sp_x", "eq")
    E(movs_imm, 0, MARK)
    E(strb_imm, 0, 1, 0)
    E(strb_imm, 4, 1, 2)
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 1, 3)
    E(movs_imm, 0, CHECK ^ MARK)
    E(eors_reg, 4, 0)
    E(strb_imm, 4, 1, 1)
    a.label("sp_x")
    E(pop_list, [4], pc=True)

    # ---- c_slp (the flusher's bl at 0x0803085E: r0 = t, r1 = index, r2 = value)
    a.label("c_slp")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(mov_reg, 6, 2)
    E(bl, "c_slm")
    E(mov_reg, 7, 0)
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)                                                     # r1 = bit t
    E(lsrs_imm, 2, 1, 1)
    E(tst_reg, 7, 2)
    E(b_cond, "pp_x", "ne")                                               # a follower's own: dropped
    E(tst_reg, 7, 1)
    E(b_cond, "pp_pass", "eq")
    E(mov_reg, 2, 6)                                                      # a leader: its own (the pan hard left) ...
    E(cmp_imm, 5, I_PAN)
    E(b_cond, "pp_l", "ne")
    E(movs_imm, 2, PAN_L)
    a.label("pp_l")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, prev["param"])
    E(mov_reg, 2, 6)                                                      # ... and the follower's (the pan hard right, the next sample)
    E(cmp_imm, 5, I_PAN)
    E(b_cond, "pp_s", "ne")
    E(movs_imm, 2, PAN_R)
    E(b, "pp_f")
    a.label("pp_s")
    E(cmp_imm, 5, I_SAMPLE)
    E(b_cond, "pp_f", "ne")
    E(cmp_imm, 2, SMAX)
    E(b_cond, "pp_f", "hs")
    E(adds_imm8, 2, 1)
    a.label("pp_f")
    E(adds_imm3, 0, 4, 1)
    E(mov_reg, 1, 5)
    E(bl, prev["param"])
    E(b, "pp_x")
    a.label("pp_pass")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(mov_reg, 2, 6)
    E(bl, prev["param"])
    a.label("pp_x")
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_slroom(): room in the queue for two messages (qfull's way: its last read index, read again only when needed; at most 3 ms)
    a.label("c_slroom")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ro_x", "eq")
    E(movw, 1, OQ)
    E(adds_reg, 4, 0, 1)                                                  # r4 = qfull's state
    imm32(0, QIDX)
    E(ldr_imm, 5, 0, 0)
    E(movs_imm, 0, 15)
    E(raw, h(0x4005))                                                     # ands r5, r0: the write index
    E(ldrb_imm, 6, 4, 0)
    E(lsrs_imm, 0, 6, 7)
    E(b_cond, "ro_r", "eq")                                               # never read: read now
    E(subs_reg, 0, 5, 6)
    E(movs_imm, 1, 15)
    E(raw, h(0x4008))                                                     # ands r0, r1: the messages since the last read index
    E(cmp_imm, 0, 14)
    E(b_cond, "ro_x", "lo")
    a.label("ro_r")
    imm32(7, CI.HAL_TICK)
    E(ldr_imm, 7, 7, 0)
    a.label("ro_l")
    E(movs_imm, 0, 0)
    imm32(1, QREAD)
    E(bl, DSP_READ)
    E(lsrs_imm, 0, 0, 8)
    E(movs_imm, 1, 15)
    E(raw, h(0x4008))                                                     # ands r0, r1: the read index
    E(movs_imm, 1, 0x80)
    E(raw, h(0x4301))                                                     # orrs r1, r0
    E(strb_imm, 1, 4, 0)
    E(subs_reg, 1, 5, 0)
    E(movs_imm, 2, 15)
    E(raw, h(0x4011))                                                     # ands r1, r2: pending
    E(cmp_imm, 1, 14)
    E(b_cond, "ro_x", "lo")
    imm32(0, CI.HAL_TICK)
    E(ldr_imm, 0, 0, 0)
    E(subs_reg, 0, 0, 7)
    E(cmp_imm, 0, WAIT_MS)
    E(b_cond, "ro_l", "lo")
    a.label("ro_x")
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_slq (0x080406A8's head, qfull's after it: r0 = the message)
    a.label("c_slq")
    E(push_list, [0, 1, 2, 3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(ldr_imm, 5, 4, 0)                                                   # r5 = w0
    E(lsrs_imm, 0, 5, 20)
    E(cmp_imm, 0, 8)
    E(b_cond, "q_p", "lo")
    E(cmp_imm, 0, 9)
    E(b_cond, "q_p", "hi")                                                # notes only
    E(bl, "c_slm")
    E(mov_reg, 7, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "q_p", "eq")
    E(movs_imm, 6, 7)
    E(raw, h(0x402E))                                                     # ands r6, r5: t
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 6)
    E(lsrs_imm, 2, 1, 1)
    E(tst_reg, 7, 2)
    E(b_cond, "q_l", "eq")
    E(pop_list, [0, 1, 2, 3, 4, 5, 6, 7], pc=True)                        # a follower's own: dropped
    a.label("q_l")
    E(tst_reg, 7, 1)
    E(b_cond, "q_p", "eq")
    E(bl, "c_slroom")                                                     # a leader's: room for two
    imm32(0, TFIELD)
    E(bics_reg, 5, 0)
    E(adds_imm8, 6, 1)
    E(lsls_imm, 0, 6, 16)
    E(orrs_reg, 0, 6)
    E(orrs_reg, 5, 0)                                                     # r5 = the follower's w0
    imm32(0, QIDX)
    E(ldr_imm, 6, 0, 0)
    E(movs_imm, 1, 15)
    E(raw, h(0x400E))                                                     # ands r6, r1: the write slot
    imm32(7, QBASE)
    E(lsls_imm, 0, 6, 1)
    E(adds_reg, 7, 7, 0)
    E(movs_imm, 0, 0)
    E(lsls_imm, 1, 5, 8)
    E(mov_reg, 2, 7)
    E(bl, DSP_WRITE)
    E(ldr_imm, 1, 4, 4)
    E(lsls_imm, 1, 1, 8)
    E(adds_imm3, 2, 7, 1)
    E(movs_imm, 0, 0)
    E(bl, DSP_WRITE)
    E(adds_imm8, 6, 1)                                                    # the ARM's write index past it (not core 1's: the leader's write shows both)
    E(movs_imm, 1, 15)
    E(raw, h(0x400E))                                                     # ands r6, r1
    imm32(0, QIDX)
    E(str_imm, 6, 0, 0)
    E(mov_reg, 0, 4)
    E(bl, prev["queue"])
    E(pop_list, [0, 1, 2, 3, 4, 5, 6, 7], pc=True)
    a.label("q_p")
    E(raw, GP.popw([0, 1, 2, 3, 4, 5, 6, 7], lr=True))
    E(b_w, prev["queue"])

    # ---- c_slpad (the controller's pad press, linein's head after it): the menu open, pad 7 is ours
    a.label("c_slpad")
    E(cmp_imm, 1, pad)
    E(b_cond, "pd_s", "ne")
    E(push_list, [0, 1, 2, 3, 4, 5, 6], lr=True)
    E(bl, L["c_gpmopen"])
    E(cmp_imm, 0, 8)
    E(b_cond, "pd_p", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the menu's track
    E(bl, L["c_gpmst"])                                                   # its release swallowed by the menu's
    if pad < 8:
        E(movs_imm, 1, 1 << pad)
    else:
        E(movs_imm, 1, 1)
        E(lsls_imm, 1, 1, pad)
    E(ldr_imm, 2, 0, M_SWAL)
    E(orrs_reg, 2, 1)
    E(str_imm, 2, 0, M_SWAL)
    E(bl, "c_slget")
    E(movs_imm, 2, 1)
    E(lsls_reg, 2, 4)                                                     # r2 = bit t
    E(lsrs_imm, 3, 2, 1)
    E(tst_reg, 0, 3)
    E(b_cond, "pd_nf", "eq")
    E(bics_reg, 0, 3)                                                     # a follower: the pair unlinked
    E(b, "pd_w")
    a.label("pd_nf")
    E(tst_reg, 0, 2)
    E(b_cond, "pd_on", "eq")
    E(bics_reg, 0, 2)                                                     # a leader: unlinked
    E(b, "pd_w")
    a.label("pd_on")
    E(cmp_imm, 4, 7)
    E(b_cond, "pd_x", "eq")                                               # track 8: nothing
    E(orrs_reg, 0, 2)                                                     # t leads, t + 1 follows (and leads no more)
    E(lsls_imm, 2, 2, 1)
    E(bics_reg, 0, 2)
    a.label("pd_w")
    E(bl, "c_slput")
    a.label("pd_x")
    E(pop_list, [0, 1, 2, 3, 4, 5, 6], pc=True)
    a.label("pd_p")
    E(raw, GP.popw([0, 1, 2, 3, 4, 5, 6], lr=True))
    a.label("pd_s")
    E(b_w, prev["pad"])

    # ---- c_slled (the LED task's calls: ctrl, frame): the chain; the leaders applied; the menu's pad 7
    a.label("c_slled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ll_x", "eq")
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ll_x", "eq")
    E(ldrb_w, 1, 0, O_TH)
    E(cmp_imm, 1, TH.READY)
    E(b_cond, "ll_m", "ne")                                               # core 0 / 1 not seen up: nothing applied
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ll_m", "eq")
    E(bl, "c_slram")
    E(cmp_imm, 0, 0)
    E(b_cond, "ll_m", "eq")
    E(mov_reg, 4, 0)                                                      # r4 = our RAM
    E(bl, "c_slget")
    E(mov_reg, 6, 0)                                                      # r6 = the block's leaders
    E(ldrb_imm, 7, 4, R_MASK)                                             # r7 = those applied
    E(ldrb_imm, 0, 4, R_SEEN)
    E(cmp_imm, 0, 0)
    E(b_cond, "ll_ap", "eq")
    E(cmp_reg, 6, 7)
    E(b_cond, "ll_m", "eq")
    a.label("ll_ap")
    E(movs_imm, 0, 1)
    E(strb_imm, 0, 4, R_SEEN)
    E(strb_imm, 6, 4, R_MASK)
    E(eors_reg, 7, 6)                                                     # the tracks whose role changed: (old ^ new) | (old ^ new) << 1 ...
    E(lsls_imm, 0, 7, 1)
    E(orrs_reg, 7, 0)
    E(lsls_imm, 0, 6, 1)
    E(bics_reg, 7, 0)                                                     # ... but the new followers (their leader sends theirs)
    E(movs_imm, 4, 0)
    a.label("ll_t")
    E(movs_imm, 0, 1)
    E(lsls_reg, 0, 4)
    E(tst_reg, 7, 0)
    E(b_cond, "ll_n", "eq")
    imm32(1, DIRTY)                                                       # all its parameters marked, the flusher run
    E(lsls_imm, 2, 4, 2)
    E(adds_reg, 1, 1, 2)
    imm32(0, ALL)
    E(str_imm, 0, 1, 0)
    E(mov_reg, 0, 4)
    E(bl, FLUSH)
    a.label("ll_n")
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, 8)
    E(b_cond, "ll_t", "lo")
    a.label("ll_m")
    E(bl, L["c_gpmopen"])                                                 # the menu open: pad 7
    E(cmp_imm, 0, 8)
    E(b_cond, "ll_x", "hs")
    E(mov_reg, 4, 0)
    E(bl, "c_slget")
    E(movs_imm, 2, 1)
    E(lsls_reg, 2, 4)
    if ui:                                                                # (ui) linked either way: bright; not: dim
        E(lsrs_imm, 3, 2, 1)
        E(orrs_reg, 3, 2)
        E(mov_reg, 1, 0)
        E(movs_imm, 0, UI_COL)
        E(tst_reg, 1, 3)
        E(b_cond, "ll_w", "ne")
        E(movs_imm, 0, UI_DIM)
        E(cmp_imm, 4, 7)
        E(b_cond, "ll_w", "ne")
        E(movs_imm, 0, 0)                                                 # track 8 alone: dark
    else:
        imm32(1, PAL + PAL_TOFF)
        E(lsrs_imm, 3, 2, 1)
        E(tst_reg, 0, 3)
        E(b_cond, "ll_nf", "eq")
        imm32(1, PAL + PAL_ON)                                            # a follower
        E(b, "ll_c")
        a.label("ll_nf")
        E(tst_reg, 0, 2)
        E(b_cond, "ll_nl", "eq")
        imm32(1, PAL + PAL_TON)                                           # a leader
        E(b, "ll_c")
        a.label("ll_nl")
        E(cmp_imm, 4, 7)
        E(b_cond, "ll_c", "ne")
        E(movs_imm, 0, 0)                                                 # track 8 alone: dark
        E(b, "ll_w")
        a.label("ll_c")
        E(raw, h(0x8808))                                                 # ldrh r0, [r1]
    a.label("ll_w")
    E(strh_imm, 0, 5, 2 * pad)
    a.label("ll_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr, ui=False):
    """The flusher's bl (in front of cue's), the queue's head (in front of qfull's), the controller's pad press (in front of linein's), the
    head of the LED calls.  Needs granpage v2, linein, cue, qfull, cthresh, rhrec, rhstate ram2."""
    import rhbuild
    BASE = rhbuild.BASE
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    assert "c_gpmopen" in report["granpage"]["labels"] and "linein" in report and "qfull" in report and "cue" in report
    L = dict(c_rst=lab("rhstate", "c_rst"), c_rram=lab("rhstate", "c_rram"), c_rrt=lab("rhrec", "c_rrt"), c_ciok=lab("countin", "c_ciok"),
             **{k: lab("granpage", k) for k in ("c_gpmopen", "c_gpmst")})
    prev = dict(param=rhbuild.bl_target(img, FLUSH_CALL), queue=rhbuild.bw_target(img, QWRITE), pad=rhbuild.bw_target(img, PP_ENTRY),
                ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert prev["param"] == lab("cue", "c_cuparam") and prev["queue"] == lab("qfull", "c_qfw") and prev["pad"] == lab("linein", "c_lipad")
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code_, labels = arm_code(base_addr, L, prev, ui)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code_
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, FLUSH_CALL, f"bl #{prev['param']:#x}", bl(FLUSH_CALL, labels["c_slp"]))
    rhbuild.patch(img, QWRITE, f"b.w #{prev['queue']:#x}", b_w(QWRITE, labels["c_slq"]))
    rhbuild.patch(img, PP_ENTRY, f"b.w #{prev['pad']:#x}", b_w(PP_ENTRY, labels["c_slpad"]))
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_slled"]))
    report["slink"] = dict(prev={k: hex(v) for k, v in prev.items()}, **({"ui": True} if ui else {}), labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code_
