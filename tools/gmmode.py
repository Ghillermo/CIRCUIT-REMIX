"""General MIDI mode: the tracks' notes out on channel 10 with a GM note each, and the GM notes in on channel 10 choosing the track (MIT; RH46,
CIRCUIT-HACKS' gmdrum of Beta 3.19 for the Rhythm's eight tracks; the user, 2026-10-27: «Cuando el modo GM está activo, las notas externas del
canal GM seleccionan sample en vez de pitch»).

The stock of the Rhythm (read in its image, run on the RAM dump):
  * MIDI out: the transmitter X = 0x200126B0 (vtable 0x08067158: slot 0 note-on, slot 1 note-off, (X, id, note, velocity)); a track is id
    0x10 + t, its channel = [[X + 0xC] + t] (the Setup's channels; 0x08031FAC); a pad or a step of track t sends its note on that channel;
  * MIDI in: the receive method 0x0805AF94(A = [0x20006EEC], message), reached through the thunk 0x08052274 (`mov r0, r2; b.w`); with Note Rx
    (A + 0x1C bit 0) a note on a track's channel goes to the listener [A] (vtable 0x080665E4) as id 0x10 + t at its pitch, and on channel 16
    as id 0xFE: the drum map, notes 36 / 38 / 40 / 41 / 43 / 45 / 47 / 48 = tracks 1..8 at their own note (0x0803F91E);
  * the Setup view (Shift + Save; not Advanced): pad 22 does nothing, its knobs reach slot 4, a stub (0x0805211C).
Ours (the project's: the record's tail, rhrec "gmmode": "GM", a check byte, the flags (bit 0 on), the eight GM notes 35..81; a project without
it = off, notes 36 / 38 / 42 / 46 / 39 / 37 / 45 / 49: kick, snare, closed hat, open hat, clap, side stick, low tom, crash):
  * out: with the mode on, a track's note-on goes out on channel 10 with its GM note (the transmitter's channel byte of that track set to 10
    for the call), and its note-off with the note its note-on had (rhstate OFF2 "gmmode" + t), so nothing is left hanging when the mode or a
    note changes;
  * in: with the mode on (and Note Rx), a note on channel 10 equal to a track's GM note plays that track as the stock's drum map does (id 0xFE
    with the drum map's note of the track); other notes on channel 10 do nothing (the track's pitch is not changed);
  * Setup pad 22 = on / off (its LED green on / dim off); with the mode on, K1..K8 = the GM note of tracks 1..8 (2 clicks a note; each new
    note sounds once on channel 10), their LEDs in the tracks' colours.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b, b_cond, b_w, bl, cmp_imm, cmp_reg, eors_reg, h, ldr_imm, ldrb_imm, ldrb_w, lsls_imm,  # noqa: E402
                   lsrs_imm, mov_reg, movs_imm, movt, movw, pop_list, push_list, raw, strb_imm, strh_imm, subs_imm8, subs_reg)
import countin as CI  # noqa: E402
import pgmch as PG  # noqa: E402
import rhrec  # noqa: E402
import rhstate  # noqa: E402
import usbmerge as UM  # noqa: E402

TX, TX_VT, O_CHT = 0x200126B0, 0x08067158, 0xC
RECV_PTR, RX_THUNK, RX = 0x20006EEC, 0x08052276, 0x0805AF94
O_RXF, RX_NOTE = 0x1C, 0x01
LIS_DRUM = 0xFE
GM_CH = 9                                                 # channel 10
DEF = (36, 38, 42, 46, 39, 37, 45, 49)
DM = (36, 38, 40, 41, 43, 45, 47, 48)                     # the stock's drum map of channel 16
NMIN, NMAX, CLICKS = 35, 81, 2
PAD = 21                                                  # Setup pad 22
SETUP_VT = PG.SETUP_VT
KNOB_SLOT = SETUP_VT + 16
COL_ON, COL_DIM = UM.COL_ON, UM.COL_DIM
# ui (RH52; docs/INTERFAZ.md, the user, 2026-10-28: «toggles change brightness if they're on-off»): off = the dim of its own colour
UI_DIM = 0x1F                                             # dim green
COL_TRK = 0x149                                           # + t: the Mixer's colour of each track
MARK0, MARK1, CHECK = 0x47, 0x4D, 0x6B                    # "GM"
BLK, BLK_LEN = rhrec.OFF["gmmode"]
B_FL, B_NOTES = 3, 4
O = rhstate.OFF2["gmmode"][0]
R_SOUND, R_ACC = 0, 8
assert BLK_LEN >= B_NOTES + 8 and rhstate.OFF2["gmmode"][1] >= R_ACC + 8


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))
def ldrb_reg(rt, rn, rm): return h(0x5C00 | rm << 6 | rn << 3 | rt)
def strb_reg(rt, rn, rm): return h(0x5400 | rm << 6 | rn << 3 | rt)
def ldrsb_reg(rt, rn, rm): return h(0x5600 | rm << 6 | rn << 3 | rt)


def arm_code(base, L, prev, ui=False):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    t_def = base
    E(raw, bytes(DEF) + bytes(DM))

    # ---- c_gmblk() -> r0 = our block in the tail when valid, else 0; r1 = its place (0 without a record); clobbers r2, r3
    a.label("c_gmblk")
    E(push_list, [4], lr=True)
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "gb_0", "eq")
    E(movw, 1, BLK)
    E(adds_reg, 0, 0, 1)
    E(mov_reg, 1, 0)
    E(ldrb_imm, 2, 0, 0)
    E(cmp_imm, 2, MARK0)
    E(b_cond, "gb_n", "ne")
    E(ldrb_imm, 2, 0, 1)
    E(cmp_imm, 2, MARK1)
    E(b_cond, "gb_n", "ne")
    E(movs_imm, 2, CHECK)
    E(movs_imm, 3, B_FL)
    a.label("gb_l")
    E(raw, ldrb_reg(4, 0, 3))
    E(eors_reg, 2, 4)
    E(adds_imm8, 3, 1)
    E(cmp_imm, 3, B_NOTES + 8)
    E(b_cond, "gb_l", "lo")
    E(ldrb_imm, 3, 0, 2)
    E(cmp_reg, 2, 3)
    E(b_cond, "gb_x", "eq")
    a.label("gb_n")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)
    a.label("gb_0")
    E(movs_imm, 1, 0)
    a.label("gb_x")
    E(pop_list, [4], pc=True)

    # ---- c_gmon_() -> r0 = 1 when the mode is on; clobbers r1-r3
    a.label("c_gmis")
    E(push_list, [4], lr=True)
    E(bl, "c_gmblk")
    E(cmp_imm, 0, 0)
    E(b_cond, "gi_x", "eq")
    E(ldrb_imm, 0, 0, B_FL)
    E(movs_imm, 1, 1)
    E(raw, h(0x4008))                                                     # ands r0, r1
    a.label("gi_x")
    E(pop_list, [4], pc=True)

    # ---- c_gmnote(r0 = track) -> r0 = its GM note; clobbers r1-r3
    a.label("c_gmnote")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_gmblk")
    E(cmp_imm, 0, 0)
    E(b_cond, "gn_d", "eq")
    E(adds_reg, 0, 0, 4)
    E(ldrb_imm, 0, 0, B_NOTES)
    E(pop_list, [4], pc=True)
    a.label("gn_d")
    imm32(0, t_def)
    E(raw, ldrb_reg(0, 0, 4))
    E(pop_list, [4], pc=True)

    # ---- c_gmput(r0 = 8 for the flags or a track, r1 = the value): the block made when missing (off, the defaults), the check; clobbers r0-r3
    a.label("c_gmput")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(bl, "c_gmblk")
    E(cmp_imm, 1, 0)
    E(b_cond, "gp_x", "eq")
    E(mov_reg, 6, 1)
    E(cmp_imm, 0, 0)
    E(b_cond, "gp_v", "ne")
    E(movs_imm, 0, MARK0)
    E(strb_imm, 0, 6, 0)
    E(movs_imm, 0, MARK1)
    E(strb_imm, 0, 6, 1)
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 6, B_FL)
    imm32(2, t_def)
    E(movs_imm, 3, 0)
    a.label("gp_d")
    E(raw, ldrb_reg(0, 2, 3))
    E(adds_reg, 1, 6, 3)
    E(strb_imm, 0, 1, B_NOTES)
    E(adds_imm8, 3, 1)
    E(cmp_imm, 3, 8)
    E(b_cond, "gp_d", "lo")
    a.label("gp_v")
    E(cmp_imm, 4, 8)
    E(b_cond, "gp_n", "lo")
    E(strb_imm, 5, 6, B_FL)
    E(b, "gp_c")
    a.label("gp_n")
    E(adds_reg, 0, 6, 4)
    E(strb_imm, 5, 0, B_NOTES)
    a.label("gp_c")
    E(movs_imm, 2, CHECK)
    E(movs_imm, 3, B_FL)
    a.label("gp_l")
    E(raw, ldrb_reg(0, 6, 3))
    E(eors_reg, 2, 0)
    E(adds_imm8, 3, 1)
    E(cmp_imm, 3, B_NOTES + 8)
    E(b_cond, "gp_l", "lo")
    E(strb_imm, 2, 6, 2)
    a.label("gp_x")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_gmram() -> r0 = our RAM, 0 without it; clobbers r1-r3
    a.label("c_gmram")
    E(push_list, [4], lr=True)
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "gr_x", "eq")
    E(movw, 1, O)
    E(adds_reg, 0, 0, 1)
    a.label("gr_x")
    E(pop_list, [4], pc=True)

    # ---- c_gmsend(r0 = slot offset 0 / 4, r1 = track, r2 = note, r3 = velocity): the stock's note-on / note-off of the track on channel 10;
    #      clobbers r0-r3
    a.label("c_gmsend")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(mov_reg, 6, 2)
    E(mov_reg, 7, 3)
    imm32(0, TX)
    E(ldr_imm, 0, 0, O_CHT)
    E(adds_reg, 0, 0, 5)                                                  # its channel byte
    E(ldrb_imm, 1, 0, 0)
    E(push_list, [0, 1])                                                  # (kept)
    E(movs_imm, 1, GM_CH)
    E(strb_imm, 1, 0, 0)
    imm32(0, TX)
    E(mov_reg, 1, 5)
    E(adds_imm8, 1, 0x10)
    E(mov_reg, 2, 6)
    E(mov_reg, 3, 7)
    E(cmp_imm, 4, 0)
    E(b_cond, "gs_f", "ne")
    E(bl, prev["on"])
    E(b, "gs_r")
    a.label("gs_f")
    E(bl, prev["off"])
    a.label("gs_r")
    E(pop_list, [0, 1])
    E(strb_imm, 1, 0, 0)                                                  # the track's channel back
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_gmtxon (the transmitter's slot 0: X, id, note, velocity)
    a.label("c_gmtxon")
    E(push_list, [0, 1, 2, 3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 1)
    E(raw, h(0x3C10))                                                     # subs r4, #0x10
    E(cmp_imm, 4, 8)
    E(b_cond, "to_s", "hs")
    E(bl, "c_gmis")
    E(cmp_imm, 0, 0)
    E(b_cond, "to_s", "eq")
    E(bl, "c_gmram")
    E(cmp_imm, 0, 0)
    E(b_cond, "to_s", "eq")
    E(mov_reg, 5, 0)                                                      # r5 = our RAM
    E(mov_reg, 0, 4)
    E(bl, "c_gmnote")
    E(mov_reg, 2, 0)
    E(raw, strb_reg(2, 5, 4))                                             # sounding
    E(movs_imm, 0, 0)
    E(mov_reg, 1, 4)
    E(raw, h(0x9B03))                                                     # ldr r3, [sp, #12]: the velocity
    E(bl, "c_gmsend")
    E(pop_list, [0, 1, 2, 3, 4, 5, 6, 7], pc=True)
    a.label("to_s")
    E(raw, popw([0, 1, 2, 3, 4, 5, 6, 7], lr=True))
    E(b_w, prev["on"])

    # ---- c_gmtxoff (the transmitter's slot 1: X, id, note, velocity): the note its note-on had
    a.label("c_gmtxoff")
    E(push_list, [0, 1, 2, 3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 1)
    E(raw, h(0x3C10))                                                     # subs r4, #0x10
    E(cmp_imm, 4, 8)
    E(b_cond, "tf_s", "hs")
    E(bl, "c_gmram")
    E(cmp_imm, 0, 0)
    E(b_cond, "tf_s", "eq")
    E(mov_reg, 5, 0)
    E(raw, ldrb_reg(2, 5, 4))
    E(cmp_imm, 2, 0)
    E(b_cond, "tf_s", "eq")
    E(movs_imm, 0, 0)
    E(raw, strb_reg(0, 5, 4))
    E(movs_imm, 0, 4)
    E(mov_reg, 1, 4)
    E(raw, h(0x9B03))                                                     # ldr r3, [sp, #12]
    E(bl, "c_gmsend")
    E(pop_list, [0, 1, 2, 3, 4, 5, 6, 7], pc=True)
    a.label("tf_s")
    E(raw, popw([0, 1, 2, 3, 4, 5, 6, 7], lr=True))
    E(b_w, prev["off"])

    # ---- c_gmrx (in the receive thunk: r0 = A, r1 = the message): channel 10's notes with the mode on
    a.label("c_gmrx")
    E(push_list, [0, 1, 2, 3, 4, 5, 6, 7], lr=True)
    E(ldrb_imm, 4, 1, 0)                                                  # r4 = the status
    E(movs_imm, 2, 0x0F)
    E(raw, h(0x4022))                                                     # ands r2, r4
    E(cmp_imm, 2, GM_CH)
    E(b_cond, "rx_s", "ne")
    E(lsrs_imm, 2, 4, 4)
    E(cmp_imm, 2, 8)
    E(b_cond, "rx_n", "eq")
    E(cmp_imm, 2, 9)
    E(b_cond, "rx_s", "ne")
    a.label("rx_n")
    E(ldrb_imm, 2, 0, O_RXF)
    E(lsls_imm, 2, 2, 31)
    E(b_cond, "rx_s", "pl")                                               # Note Rx off: the stock's
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "rx_s", "eq")
    E(bl, "c_gmis")
    E(cmp_imm, 0, 0)
    E(b_cond, "rx_s", "eq")
    E(raw, h(0x9D01))                                                     # ldr r5, [sp, #4]: the message
    E(ldrb_imm, 6, 5, 1)                                                  # r6 = the note
    E(movs_imm, 7, 0)
    a.label("rx_l")
    E(mov_reg, 0, 7)
    E(bl, "c_gmnote")
    E(cmp_reg, 0, 6)
    E(b_cond, "rx_f", "eq")
    E(adds_imm8, 7, 1)
    E(cmp_imm, 7, 8)
    E(b_cond, "rx_l", "lo")
    E(pop_list, [0, 1, 2, 3, 4, 5, 6, 7], pc=True)                        # not a track's: nothing
    a.label("rx_f")
    E(raw, h(0x9800))                                                     # ldr r0, [sp]: A
    E(ldr_imm, 0, 0, 0)                                                   # the listener
    imm32(2, t_def + 8)
    E(raw, ldrb_reg(2, 2, 7))                                             # the drum map's note of the track
    E(ldrb_imm, 3, 5, 2)                                                  # the velocity
    E(movs_imm, 1, LIS_DRUM)
    E(ldr_imm, 6, 0, 0)
    E(lsrs_imm, 4, 4, 4)
    E(cmp_imm, 4, 9)
    E(b_cond, "rx_on", "eq")
    E(ldr_imm, 6, 6, 4)                                                   # note-off: slot 1
    E(b, "rx_c")
    a.label("rx_on")
    E(ldr_imm, 6, 6, 0)                                                   # note-on: slot 0 (velocity 0 = its note-off)
    a.label("rx_c")
    E(raw, h(0x47B0))                                                     # blx r6
    E(pop_list, [0, 1, 2, 3, 4, 5, 6, 7], pc=True)
    a.label("rx_s")
    E(raw, popw([0, 1, 2, 3, 4, 5, 6, 7], lr=True))
    E(b_w, RX)

    # ---- c_gmpad (the Setup view's slot 0: view, pad, velocity): pad 22 (not Advanced) = on / off
    a.label("c_gmpad")
    E(cmp_imm, 1, PAD)
    E(b_cond, "gd_s", "ne")
    E(push_list, [0, 1, 2, 3, 4, 5], lr=True)
    E(ldrb_w, 3, 0, 0x24)
    E(cmp_imm, 3, 0)
    E(b_cond, "gd_p", "ne")                                               # Advanced: not ours
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "gd_p", "eq")
    E(bl, "c_gmis")
    E(movs_imm, 1, 1)
    E(eors_reg, 1, 0)
    E(movs_imm, 0, 8)
    E(bl, "c_gmput")
    E(pop_list, [0, 1, 2, 3, 4, 5], pc=True)
    a.label("gd_p")
    E(raw, popw([0, 1, 2, 3, 4, 5], lr=True))
    a.label("gd_s")
    E(b_w, prev["pad"])

    # ---- c_gmknob (the Setup view's slot 4: view, knob, delta): with the mode on, the GM note of track k, 2 clicks a note, each new one sounds
    a.label("c_gmknob")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(ldrb_w, 3, 0, 0x24)
    E(cmp_imm, 3, 0)
    E(b_cond, "gk_s", "ne")
    E(cmp_imm, 1, 8)
    E(b_cond, "gk_s", "hs")
    E(mov_reg, 4, 1)                                                      # r4 = the knob = the track
    E(bl, "c_gmis")
    E(cmp_imm, 0, 0)
    E(b_cond, "gk_s", "eq")
    E(bl, "c_gmram")
    E(cmp_imm, 0, 0)
    E(b_cond, "gk_s", "eq")
    E(adds_imm8, 0, R_ACC)
    E(mov_reg, 5, 0)                                                      # r5 = the accumulators
    E(mov_reg, 0, 4)
    E(bl, "c_gmnote")
    E(mov_reg, 6, 0)                                                      # r6 = the note
    E(mov_reg, 7, 6)
    E(raw, ldrsb_reg(1, 5, 4))
    E(raw, h(0x9A02))                                                     # ldr r2, [sp, #8]: the delta
    E(adds_reg, 1, 1, 2)
    a.label("gk_u")
    E(cmp_imm, 1, CLICKS)
    E(b_cond, "gk_d", "lt")
    E(subs_imm8, 1, CLICKS)
    E(cmp_imm, 6, NMAX)
    E(b_cond, "gk_u", "hs")
    E(adds_imm8, 6, 1)
    E(b, "gk_u")
    a.label("gk_d")
    E(movs_imm, 0, 0)
    E(subs_imm8, 0, CLICKS - 1)                                           # r0 = 1 - CLICKS
    E(cmp_reg, 1, 0)
    E(b_cond, "gk_w", "ge")
    E(adds_imm8, 1, CLICKS)
    E(cmp_imm, 6, NMIN)
    E(b_cond, "gk_d", "ls")
    E(subs_imm8, 6, 1)
    E(b, "gk_d")
    a.label("gk_w")
    E(raw, strb_reg(1, 5, 4))
    E(cmp_reg, 6, 7)
    E(b_cond, "gk_x", "eq")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 6)
    E(bl, "c_gmput")
    E(movs_imm, 0, 0)                                                     # the new note, once, on channel 10
    E(mov_reg, 1, 4)
    E(mov_reg, 2, 6)
    E(movs_imm, 3, 100)
    E(bl, "c_gmsend")
    E(movs_imm, 0, 4)
    E(mov_reg, 1, 4)
    E(mov_reg, 2, 6)
    E(movs_imm, 3, 0)
    E(bl, "c_gmsend")
    a.label("gk_x")
    E(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)
    a.label("gk_s")
    E(raw, popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    E(b_w, prev["knob"])

    # ---- c_gmled (the LED task's calls: ctrl, frame): the chain, then in the Setup view (not Advanced) pad 22 and, on, the knobs
    a.label("c_gmled")
    E(push_list, [3, 4, 5, 6], lr=True)
    E(mov_reg, 5, 1)
    E(bl, prev["ledtask"])
    E(bl, L["c_pgsetup"])
    E(cmp_imm, 0, 0)
    E(b_cond, "gl_x", "eq")
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "gl_x", "eq")
    E(bl, "c_gmis")
    E(mov_reg, 6, 0)
    E(movs_imm, 1, UI_DIM if ui else COL_DIM)
    E(cmp_imm, 6, 0)
    E(b_cond, "gl_p", "eq")
    E(movs_imm, 1, COL_ON)
    a.label("gl_p")
    E(strh_imm, 1, 5, 2 * PAD)
    E(cmp_imm, 6, 0)
    E(b_cond, "gl_x", "eq")
    E(movw, 1, COL_TRK)
    E(movs_imm, 2, 0)
    a.label("gl_k")
    E(lsls_imm, 3, 2, 1)
    E(adds_reg, 3, 3, 5)
    E(raw, h(0xF8A3) + h(0x1000 | 2 * 60))                                # strh.w r1, [r3, #120]: knob LED 60 + k
    E(adds_imm8, 1, 1)
    E(adds_imm8, 2, 1)
    E(cmp_imm, 2, 8)
    E(b_cond, "gl_k", "lo")
    a.label("gl_x")
    E(pop_list, [3, 4, 5, 6], pc=True)
    return a.assemble()


def install(img, report, base_addr, ui=False):
    """The transmitter's slots 0 / 1, the receive thunk's branch, the Setup view's slots 0 / 4, the head of the LED calls.  Needs pgmch, rhrec,
    rhstate ram2."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]                 # noqa: E731
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    L = dict(c_ciok=lab("countin", "c_ciok"), c_rrt=lab("rhrec", "c_rrt"), c_rram=lab("rhstate", "c_rram"), c_pgsetup=lab("pgmch", "c_pgsetup"))
    prev = dict(on=u(TX_VT) & ~1, off=u(TX_VT + 4) & ~1, pad=u(SETUP_VT) & ~1, knob=u(KNOB_SLOT) & ~1,
                ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code, labels = arm_code(base_addr, L, prev, ui)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch_word(img, TX_VT, prev["on"] | 1, labels["c_gmtxon"] | 1)
    rhbuild.patch_word(img, TX_VT + 4, prev["off"] | 1, labels["c_gmtxoff"] | 1)
    rhbuild.patch_word(img, SETUP_VT, prev["pad"] | 1, labels["c_gmpad"] | 1)
    rhbuild.patch_word(img, KNOB_SLOT, prev["knob"] | 1, labels["c_gmknob"] | 1)
    rhbuild.patch(img, RX_THUNK, f"b.w #{RX:#x}", b_w(RX_THUNK, labels["c_gmrx"]))
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_gmled"]))
    report["gmmode"] = dict(prev={k: hex(v) for k, v in prev.items()}, block=hex(BLK),
                            labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
