"""A latched chord per track that follows every note (MIT; RH75, the user, 2026-11-05: «custom scale now lives on shift+note during note expand
view. Shift any note pad is now latch. Playing or sequencing a new note after the latch transposes the whole latch, making a moving chord»,
«Arpeggios also play the latched notes»; chosen: a new note retriggers the chord at it, any track (a mono one plays the root only), Shift + a
latched pad takes it out and Clear clears, the root = the lowest latched note).

The stock of the Rhythm (read in its image, run on the RAM dump):
  * the track views' container 0x20048B9C: mode 1 = the Note view (pads 17-32 the keyboard, 1-16 the steps), Note again = mode 7, the expanded
    Note view (the 32 pads a keyboard); both reach the track's Note view slot 0 (0x08067248: view, pad, velocity) and play
    [[view + 0x4C] + 8 + 0x0805DFEA(view, pad)] (0 = no note);
  * every note to the DSP goes through 0x08040778(code, note, velocity) (the pads, the sequencer, the arpeggios, MIDI; code 0x10 + t a track;
    a note from 0x6F up does nothing): its entry is modmx's / trigflash's b.w (RH64 / RH60); a poly synth track (fmpage's c_plis, RH72) gives each note-on its
    own voice (core 0's PQW; the player's note-off before it releases them all);
  * Clear + Note = Note in the stock (tests/emu_stock.py); Shift + a key pad = the plain pad.

Ours (RAM only, lost at power-off; RAM_ = the free SRAM over the stock's heap, under dspz's state: not with resmap / bootrec):
  * the latch of a track: up to 6 notes, sorted (the root = the lowest); Shift + a key pad in either Note view = that pad's note in / out (the
    pad does not play); Clear + Note in a Note view = the selected track's latch emptied (the view stays);
  * Shift + Note in the expanded Note view = cscale's editor on / off (its flag here; off when that view leaves the screen);
  * the moving chord: a note-on of a track whose latch has two notes or more, on a poly track, with no arpeggio of notes running on it = the
    chord at that note: note + (latched - root) for the next 3 latched notes (4 voices), sent first, then the note itself (the stock's; the
    track's current note stays the played one); a mono track plays the note only (the root);
  * the arpeggio (drumarp's notes mode): a key held on a latched track puts the chord at that key in the arpeggio's list (6 at most), its
    release takes them out: the arpeggio runs over the chord (a single key already arpeggiates with drumarp single);
  * LEDs: in the Note views of the selected track (not the editor), the pads whose note is latched ice blue 0x1A (#b1f0ff; no other use).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, ands_reg, b, b_cond, b_w, bl, cmp_imm, cmp_reg, eors_reg, h, ldr_imm, ldr_sp, ldrb_imm,  # noqa: E402
                   lsls_imm, mov_reg, movs_imm, movt, movw, muls, pop_list, push_list, raw, str_sp, strb_imm, strh_reg, sub_sp_imm,
                   add_sp_imm, subs_imm8, subs_reg, tst_reg)
import countin as CI  # noqa: E402

RAM = 0x2004EB00                                          # (over the stock's heap pointer 0x2004EA98, under dspz's 0x2004EC00)
MAGIC = 0x4843544C                                        # "LTCH"
O_ED, O_TRK, T_SZ = 4, 8, 8                               # the editor's flag; the tracks' latches: count, 6 notes, a spare byte
RAM_LEN = O_TRK + 8 * T_SZ
MAXN, VOICES = 6, 4
COL = 0x1A
NOTE_DSP, MAX_NOTE = 0x08040778, 0x6F
BTN_NOTE, CLEAR_BIT = 9, 1 << 23
CTRL = CI.CTRL
CONT, O_MODE, MODE_NOTE, MODE_EXP = 0x20048B9C, 0x264, 1, 7
NV0, NV_SZ, NV_VT = 0x2004A604, 0x1B4, 0x08067248
S_N, S_TRK, S_FL, F_NOTES = 0, 2, 19, 2                   # drumarp's running state
INV = dict(eq="ne", ne="eq", lo="hs", hs="lo", hi="ls", ls="hi", ge="lt", lt="ge", gt="le", le="gt", mi="pl", pl="mi")
assert RAM + RAM_LEN <= 0x2004EC00


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit
    zc = [0]

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    def bc(target, cond):
        zc[0] += 1
        n = f"_c{zc[0]}"
        E(b_cond, n, INV[cond])
        E(b, target)
        a.label(n)

    # ---- c_lxram() -> r0 = our RAM, zeroed when its magic was missing; clobbers r1-r3
    a.label("c_lxram")
    imm32(0, RAM)
    E(ldr_imm, 1, 0, 0)
    imm32(2, MAGIC)
    E(cmp_reg, 1, 2)
    E(b_cond, "rm_x", "eq")
    E(movs_imm, 1, 0)
    E(movs_imm, 3, RAM_LEN)
    a.label("rm_z")
    E(subs_imm8, 3, 4)
    E(raw, h(0x50C1))                                                     # str r1, [r0, r3]
    E(b_cond, "rm_z", "ne")
    E(raw, h(0x6002))                                                     # str r2, [r0]
    a.label("rm_x")
    E(raw, h(0x4770))

    # ---- c_lxent(r0 = track) -> r0 = its latch (count, notes); clobbers r1-r3
    a.label("c_lxent")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_lxram")
    E(lsls_imm, 1, 4, 3)
    E(adds_reg, 0, 0, 1)
    E(adds_imm8, 0, O_TRK)
    E(pop_list, [4], pc=True)

    # ---- c_lxtog(r0 = track, r1 = note): the note in / out of the track's sorted latch (6 at most); clobbers r0-r3
    a.label("c_lxtog")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 5, 1)
    E(bl, "c_lxent")
    E(mov_reg, 4, 0)
    E(ldrb_imm, 6, 4, 0)
    E(movs_imm, 2, 0)
    a.label("tg_s")
    E(cmp_reg, 2, 6)
    E(b_cond, "tg_n", "hs")
    E(adds_reg, 3, 4, 2)
    E(ldrb_imm, 3, 3, 1)
    E(cmp_reg, 3, 5)
    E(b_cond, "tg_r", "eq")
    E(adds_imm8, 2, 1)
    E(b, "tg_s")
    a.label("tg_r")                                                       # there: out (the next ones down)
    E(mov_reg, 3, 2)
    E(adds_imm8, 3, 1)
    E(cmp_reg, 3, 6)
    E(b_cond, "tg_d", "hs")
    E(adds_reg, 0, 4, 3)
    E(ldrb_imm, 1, 0, 1)
    E(strb_imm, 1, 0, 0)                                                  # L[i] = L[i + 1]
    E(mov_reg, 2, 3)
    E(b, "tg_r")
    a.label("tg_d")
    E(subs_imm8, 6, 1)
    E(strb_imm, 6, 4, 0)
    E(b, "tg_x")
    a.label("tg_n")                                                       # not there: in, sorted (6 at most)
    E(cmp_imm, 6, MAXN)
    E(b_cond, "tg_x", "hs")
    E(mov_reg, 2, 6)
    a.label("tg_i")
    E(cmp_imm, 2, 0)
    E(b_cond, "tg_p", "eq")
    E(adds_reg, 0, 4, 2)
    E(ldrb_imm, 1, 0, 0)                                                  # L[i - 1]
    E(cmp_reg, 1, 5)
    E(b_cond, "tg_p", "ls")
    E(strb_imm, 1, 0, 1)                                                  # L[i] = L[i - 1]
    E(subs_imm8, 2, 1)
    E(b, "tg_i")
    a.label("tg_p")
    E(adds_reg, 0, 4, 2)
    E(strb_imm, 5, 0, 1)
    E(adds_imm8, 6, 1)
    E(strb_imm, 6, 4, 0)
    a.label("tg_x")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_lxview() -> r0 = the container's mode when it is on the screen in a Note view (1 / 7), else 0; clobbers r1-r3
    a.label("c_lxview")
    imm32(0, CTRL)
    E(ldr_imm, 1, 0, 0x7C)
    imm32(0, CONT)
    E(cmp_reg, 0, 1)
    E(b_cond, "vw_0", "ne")
    imm32(1, O_MODE)
    E(raw, h(0x5C40))                                                     # ldrb r0, [r0, r1]
    E(cmp_imm, 0, MODE_NOTE)
    E(b_cond, "vw_x", "eq")
    E(cmp_imm, 0, MODE_EXP)
    E(b_cond, "vw_x", "eq")
    a.label("vw_0")
    E(movs_imm, 0, 0)
    a.label("vw_x")
    E(raw, h(0x4770))

    # ---- c_lxexp(r0 = code) -> r0 = the track's latch when this note-on becomes its chord (a track, two notes or more, poly, no arpeggio of
    #      notes running on it), else 0; clobbers r1-r3
    a.label("c_lxexp")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(movs_imm, 1, 0xF8)
    E(ands_reg, 1, 0)
    E(cmp_imm, 1, 0x10)
    bc("ex_n", "ne")
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("ex_n", "eq")
    E(movs_imm, 0, 7)
    E(ands_reg, 4, 0)                                                     # r4 = the track
    E(mov_reg, 0, 4)
    E(bl, "c_lxent")
    E(mov_reg, 5, 0)
    E(ldrb_imm, 0, 5, 0)
    E(cmp_imm, 0, 2)
    bc("ex_n", "lo")
    E(mov_reg, 0, 4)
    E(bl, L["c_plis"])
    E(cmp_imm, 0, 0)
    bc("ex_n", "eq")
    E(bl, L["c_dast"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ex_y", "eq")
    E(ldrb_imm, 1, 0, S_N)
    E(cmp_imm, 1, 0)
    E(b_cond, "ex_y", "eq")
    E(ldrb_imm, 1, 0, S_TRK)
    E(cmp_reg, 1, 4)
    E(b_cond, "ex_y", "ne")
    E(ldrb_imm, 1, 0, S_FL)
    E(movs_imm, 2, F_NOTES)
    E(tst_reg, 1, 2)
    E(b_cond, "ex_n", "ne")                                               # the arpeggio plays the chord itself
    a.label("ex_y")
    E(mov_reg, 0, 5)
    E(pop_list, [4, 5], pc=True)
    a.label("ex_n")
    E(movs_imm, 0, 0)
    E(pop_list, [4, 5], pc=True)

    # ---- c_lxon (0x08040778's entry: code, note, velocity): the chord's other notes first, then the note (the previous head: trigflash's)
    a.label("c_lxon")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(sub_sp_imm, 8)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(mov_reg, 6, 2)
    E(cmp_imm, 5, MAX_NOTE)
    bc("on_p", "hs")
    E(bl, "c_lxexp")
    E(cmp_imm, 0, 0)
    bc("on_p", "eq")
    E(mov_reg, 7, 0)                                                      # r7 = the latch
    E(movs_imm, 0, 1)
    E(str_sp, 0, 0)
    a.label("on_l")
    E(ldr_sp, 0, 0)
    E(ldrb_imm, 1, 7, 0)
    E(cmp_imm, 1, VOICES)
    E(b_cond, "on_k", "ls")
    E(movs_imm, 1, VOICES)
    a.label("on_k")
    E(cmp_reg, 0, 1)
    E(b_cond, "on_p", "hs")
    E(adds_reg, 1, 7, 0)
    E(ldrb_imm, 1, 1, 1)
    E(ldrb_imm, 2, 7, 1)
    E(subs_reg, 1, 1, 2)
    E(adds_reg, 1, 1, 5)                                                  # note + (latched - root)
    E(cmp_imm, 1, MAX_NOTE)
    E(b_cond, "on_n", "hs")
    E(cmp_imm, 1, 0)
    E(b_cond, "on_n", "eq")
    E(mov_reg, 0, 4)
    E(mov_reg, 2, 6)
    E(bl, prev["note"])
    a.label("on_n")
    E(ldr_sp, 0, 0)
    E(adds_imm8, 0, 1)
    E(str_sp, 0, 0)
    E(b, "on_l")
    a.label("on_p")
    E(add_sp_imm, 8)
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(mov_reg, 2, 6)
    E(raw, popw([4, 5, 6, 7], lr=True))
    E(b_w, prev["note"])

    # ---- c_lxains(r0 = state, r1 = note, r2 = velocity) / c_lxadel(r0 = state, r1 = note) -> r0 = 1 when one was there: drumarp's c_dains /
    #      c_dadel for the chord at that note (a latched track), else for the note
    for nm, tgt in (("c_lxains", "c_dains"), ("c_lxadel", "c_dadel")):
        p = nm[-3:]
        a.label(nm)
        E(push_list, [4, 5, 6, 7], lr=True)
        E(sub_sp_imm, 8)
        E(mov_reg, 4, 0)
        E(mov_reg, 5, 1)
        E(mov_reg, 6, 2)
        E(ldrb_imm, 0, 4, S_TRK)
        E(cmp_imm, 0, 7)
        bc(f"{p}_1", "hi")
        E(bl, "c_lxent")
        E(mov_reg, 7, 0)
        E(ldrb_imm, 0, 7, 0)
        E(cmp_imm, 0, 2)
        bc(f"{p}_1", "lo")
        E(movs_imm, 0, 0)
        E(str_sp, 0, 0)                                                   # [sp] = i
        E(str_sp, 0, 4)                                                   # [sp + 4] = any was there
        a.label(f"{p}_l")
        E(ldr_sp, 0, 0)
        E(ldrb_imm, 1, 7, 0)
        E(cmp_reg, 0, 1)
        E(b_cond, f"{p}_d", "hs")
        E(adds_reg, 1, 7, 0)
        E(ldrb_imm, 1, 1, 1)
        E(ldrb_imm, 2, 7, 1)
        E(subs_reg, 1, 1, 2)
        E(adds_reg, 1, 1, 5)
        E(cmp_imm, 1, MAX_NOTE)
        E(b_cond, f"{p}_n", "hs")
        E(cmp_imm, 1, 0)
        E(b_cond, f"{p}_n", "eq")
        E(mov_reg, 0, 4)
        E(mov_reg, 2, 6)
        E(bl, L[tgt])
        E(ldr_sp, 1, 4)
        E(raw, h(0x4301))                                                 # orrs r1, r0
        E(str_sp, 1, 4)
        a.label(f"{p}_n")
        E(ldr_sp, 0, 0)
        E(adds_imm8, 0, 1)
        E(str_sp, 0, 0)
        E(b, f"{p}_l")
        a.label(f"{p}_d")
        E(ldr_sp, 0, 4)
        E(add_sp_imm, 8)
        E(pop_list, [4, 5, 6, 7], pc=True)
        a.label(f"{p}_1")
        E(add_sp_imm, 8)
        E(mov_reg, 0, 4)
        E(mov_reg, 1, 5)
        E(mov_reg, 2, 6)
        E(raw, popw([4, 5, 6, 7], lr=True))
        E(b_w, L[tgt])

    # ---- c_lxpad (the Note views' slot 0: view, pad, velocity): Shift + a key pad = its note in / out of the latch (not played)
    a.label("c_lxpad")
    E(cmp_imm, 1, 32)
    bc("pd_f", "hs")
    E(push_list, [0, 1, 2, 4], lr=True)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("pd_p", "eq")
    E(bl, L["c_cishift"])
    E(cmp_imm, 0, 0)
    bc("pd_p", "eq")
    E(bl, L["c_csnote"])                                                  # the scale editor takes its pads
    E(cmp_imm, 0, 0)
    bc("pd_p", "ne")
    E(ldr_sp, 0, 0)
    E(bl, L["c_datrkn"])
    E(cmp_imm, 0, 7)
    bc("pd_p", "hi")
    E(mov_reg, 4, 0)
    E(ldr_sp, 0, 0)
    E(ldr_sp, 1, 4)
    E(bl, L["c_danote"])
    E(cmp_imm, 0, 0)
    bc("pd_p", "eq")
    E(mov_reg, 1, 0)
    E(mov_reg, 0, 4)
    E(bl, "c_lxtog")
    E(add_sp_imm, 12)
    E(pop_list, [4], pc=True)
    a.label("pd_p")
    E(raw, popw([0, 1, 2, 4], lr=True))
    a.label("pd_f")
    E(b_w, prev["npad"])

    # ---- c_lxbtn (the head of the button chain: r0 = ctrl, r1 = id): in a Note view, Clear + Note = the latch emptied; Shift + Note in the
    #      expanded one = the scale editor on / off; Note = the editor off
    a.label("c_lxbtn")
    E(cmp_imm, 1, BTN_NOTE)
    bc("bt_f", "ne")
    E(push_list, [0, 1, 4], lr=True)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("bt_p", "eq")
    E(bl, "c_lxview")
    E(cmp_imm, 0, 0)
    bc("bt_p", "eq")
    E(mov_reg, 4, 0)                                                      # r4 = the mode
    E(ldr_sp, 0, 0)
    E(raw, h(0xF8D0) + h(0x10A0))                                         # ldr.w r1, [r0, #0xa0]: the held buttons
    imm32(2, CLEAR_BIT)
    E(tst_reg, 1, 2)
    E(b_cond, "bt_s", "eq")
    E(bl, L["c_cssel"])
    E(cmp_imm, 0, 7)
    bc("bt_p", "hi")
    E(bl, "c_lxent")
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 0, 0)
    E(b, "bt_t")
    a.label("bt_s")
    E(bl, L["c_cishift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "bt_o", "eq")
    E(cmp_imm, 4, MODE_EXP)
    bc("bt_p", "ne")
    E(bl, "c_lxram")
    E(ldrb_imm, 1, 0, O_ED)
    E(movs_imm, 2, 1)
    E(eors_reg, 1, 2)
    E(strb_imm, 1, 0, O_ED)
    a.label("bt_t")
    E(add_sp_imm, 8)
    E(pop_list, [4], pc=True)
    a.label("bt_o")
    E(bl, "c_lxram")
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 0, O_ED)
    a.label("bt_p")
    E(raw, popw([0, 1, 4], lr=True))
    a.label("bt_f")
    E(b_w, prev["btn"])

    # ---- c_lxled (the LED calls: ctrl, frame): the chain; the editor's flag off outside the expanded Note view; the latched pads ice blue
    a.label("c_lxled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 6, 1)                                                      # r6 = the frame
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(bl, "c_lxview")
    E(mov_reg, 5, 0)                                                      # r5 = the mode (0: no Note view)
    E(bl, "c_lxram")
    E(mov_reg, 7, 0)
    E(cmp_imm, 5, MODE_EXP)
    E(b_cond, "ld_e", "eq")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 7, O_ED)
    E(cmp_imm, 5, 0)
    bc("ld_x", "eq")
    E(b, "ld_g")
    a.label("ld_e")
    E(ldrb_imm, 0, 7, O_ED)
    E(cmp_imm, 0, 0)
    bc("ld_x", "ne")                                                      # the editor's picture (cscale)
    a.label("ld_g")
    E(bl, L["c_cssel"])
    E(cmp_imm, 0, 7)
    bc("ld_x", "hi")
    E(mov_reg, 4, 0)
    E(lsls_imm, 0, 4, 3)
    E(adds_reg, 7, 7, 0)
    E(adds_imm8, 7, O_TRK)                                                # r7 = the latch
    E(ldrb_imm, 0, 7, 0)
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(movw, 0, NV_SZ)
    E(muls, 0, 4)
    imm32(1, NV0)
    E(adds_reg, 4, 0, 1)                                                  # r4 = the track's Note view
    E(movs_imm, 0, 0)
    E(cmp_imm, 5, MODE_EXP)
    E(b_cond, "ld_0", "eq")
    E(movs_imm, 0, 16)                                                    # the Note view: pads 17-32
    a.label("ld_0")
    E(mov_reg, 5, 0)                                                      # r5 = the pad
    a.label("ld_l")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, L["c_danote"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ld_n", "eq")
    E(ldrb_imm, 2, 7, 0)
    a.label("ld_s")
    E(cmp_imm, 2, 0)
    E(b_cond, "ld_n", "eq")
    E(adds_reg, 3, 7, 2)
    E(ldrb_imm, 3, 3, 0)                                                  # L[k - 1]
    E(cmp_reg, 3, 0)
    E(b_cond, "ld_h", "eq")
    E(subs_imm8, 2, 1)
    E(b, "ld_s")
    a.label("ld_h")
    E(lsls_imm, 1, 5, 1)
    E(movs_imm, 2, COL)
    E(strh_reg, 2, 6, 1)
    a.label("ld_n")
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, 32)
    E(b_cond, "ld_l", "lo")
    a.label("ld_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def bl_sites(img, start, end, target):
    """The bl instructions in [start, end) that call target"""
    import rhbuild
    out = []
    for x in range(start, end - 2, 2):
        hw1, hw2 = struct.unpack_from("<HH", img, x - rhbuild.BASE)
        if (hw1 & 0xF800) == 0xF000 and (hw2 & 0xD000) == 0xD000 and rhbuild.bl_target(img, x) == target:
            out.append(x)
    return out


def install(img, report, base_addr):
    """Append the code; 0x08040778's entry, the Note views' slot 0, the head of the button chain, the LED calls (outermost), and drumarp's
    c_dains / c_dadel calls in its Note view pad / release slots.  Needs cscale (OPT latch), drumarp (notes), fmpage (poly), trigflash."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]          # noqa: E731
    lab = lambda sec, n: int(report[sec]["labels"][n], 16)              # noqa: E731
    L = dict(c_ciok=lab("countin", "c_ciok"), c_cishift=lab("countin", "c_cishift"), c_cssel=lab("cscale", "c_cssel"),
             c_csnote=lab("cscale", "c_csnote"), c_datrkn=lab("drumarp", "c_datrkn"), c_danote=lab("drumarp", "c_danote"),
             c_dast=lab("drumarp", "c_dast"), c_dains=lab("drumarp", "c_dains"), c_dadel=lab("drumarp", "c_dadel"),
             c_plis=lab("fmpage", "c_plis"))
    prev = dict(note=rhbuild.bw_target(img, NOTE_DSP), npad=u(NV_VT) & ~1, btn=rhbuild.bw_target(img, CI.BTN_ENTRY),
                ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert prev["note"] in (lab("modmx", "c_mxnote"), lab("trigflash", "c_tfon"))       # a head that keeps LR and chains on (callable)
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    dl = sorted(int(v, 16) for v in report["drumarp"]["labels"].values())
    npad, nrel = lab("drumarp", "c_danpad"), lab("drumarp", "c_danrel")
    after = lambda x: min(v for v in dl if v > x)                       # noqa: E731
    ins = bl_sites(img, npad, after(npad), L["c_dains"])
    dels = bl_sites(img, nrel, after(nrel), L["c_dadel"])
    assert len(ins) == 1 and len(dels) == 1, (ins, dels)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, NOTE_DSP, f"b.w #{prev['note']:#x}", b_w(NOTE_DSP, labels["c_lxon"]))
    rhbuild.patch_word(img, NV_VT, prev["npad"] | 1, labels["c_lxpad"] | 1)
    rhbuild.patch(img, CI.BTN_ENTRY, f"b.w #{prev['btn']:#x}", b_w(CI.BTN_ENTRY, labels["c_lxbtn"]))
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_lxled"]))
    rhbuild.patch(img, ins[0], f"bl #{L['c_dains']:#x}", bl(ins[0], labels["c_lxains"]))
    rhbuild.patch(img, dels[0], f"bl #{L['c_dadel']:#x}", bl(dels[0], labels["c_lxadel"]))
    report["latch"] = dict(prev={k: hex(v) for k, v in prev.items()}, sites=dict(ins=hex(ins[0]), dels=hex(dels[0])),
                           labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
