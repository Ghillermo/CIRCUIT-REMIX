"""The FX sequencer over the Grid FX (MIT; RH92; the user, 2026-11-11: «Port the FX sequencer from Hacks, with the 16 assigned Grid FX
destinations»; chosen: pick the slot like a sample flip, the effect lasts the step's gate, Octave down + step = random, Octave up + step = repeat
the last effect; two new Grid FX types on the ARM: delay throw and reverb throw / wash; docs/DISENO_RH92.md).

The stock of the Rhythm (read in its image, run on the RAM dump):
  * Grid FX = Shift + Mixer (the Mixer's mode 7): pads 17-32 = 16 slots of the manager MGR (the table at MGR + 0x1D8, 16 x 7 B: the type 0-6,
    then the macros; a type above 6 plays nothing, its on / off reaches the router as id 0); the manager's press / release (mgr, slot) are the
    words PRESS_W / RELEASE_W (0x08039770 / 0x08039848): the macros, then the type's on / off through the parameter router;
  * the seven types are engines of their own: the project group 0x20, index 0xA.. (generic id 0x9F + index): Beat Repeat 0xA9-0xAB, Reverser
    0xAC-0xAD, Gater 0xAE-0xAF, Auto-Filter 0xB0-0xB6, Digitiser 0xB7-0xB9, Phaser 0xBA-0xBE, Vinyl 0xBF-0xC3, the first of each = on;
    two types play together, two slots of one type share it;
  * the Grid FX colours: the halfwords at COLT (types 0-6); a held pad white (0x01); the held slot = the byte HELD (0x10 = none);
  * a track's step: its sample (the step's flip, else the track's selected sample) is set at the step's start (the players' slot 4) before
    its note-on 0x08040778(0x10 + t, note, velocity); the note-off 0x0804083C(0x10 + t, note) at the end of its gate (the player sends one
    before each note-on too); the track's sample = parameter 0 of its group (0x08046410(0x10 + t, 0));
  * the steps' edit store ST1 = [step view + 0xC] (the step view 0x2004B3A4 + 0x118 t; its page p0 of [+ 0x60]): parameter s / 4 the
    velocity, 8 + s / 4 the probability, 16 + s / 4 the micro steps, 24 + s / 4 the flip (byte s & 3); WPTR + COMMIT writes the pattern.

Ours:
  * an FX track: its bit in the byte R + 0x61 of the record (scene 1's + 33, never written by the stock: travels with the project); Sample
    mode's selector, pad 21 (dark until now) = FX on / off (blue 0xDD / dim 0xE0; on also picks the sample engine); another engine pad
    takes it off;
  * its notes never reach the DSP (silent): a note-on turns on the Grid FX slot of its sample (0-15; 16 = one of the slots with a type at
    random; 17 = the track's last one again; more = & 15), the note-off turns it off (only if this track turned it on);
  * its sample view (the track view, mode 0): pads 17-32 = the slots in their type's colour (dark: no type), the track's sample white;
    Octave down (19) / up (20) held + a step pad = that step's flip 16 / 17 (an empty step gets a hit: velocity 100, probability 7, micro
    step 0); the Octave buttons do not page there;
  * two types of ours, 7 = delay throw (peach 0x74), 8 = reverb throw / wash (cream 0x29): on = every track's delay / reverb send to the
    slot's macro 1, and (macro 2 > 0) the delay's feedback / the reverb's decay to macro 2; off = all back; from the Grid FX view too;
  * in the Grid FX view, a slot held + Shift + K1 = its type (0-8; ours with macros 100, 0), in the live table and in the source the stock
    keeps and saves ([MGR + 0xC]: the live one is restored from it on a release); the 16 pads from the table (white held).
RAM: FXR (modmx's old offsets, free with mx64: not with icprobe): + 0 MAGIC, + 4 cur[8] (slot + 1 on), + 12 last[8], + 20 owner[9] (track +
1; 0x80 the Grid FX view), + 30 throws on (bit ty - 7), + 32 saved delay sends [8], + 40 saved reverb sends [8], + 48 / 49 the saved
feedback / decay (0xFF = untouched), + 52 the pads swallowed (bits).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, ands_reg, b, b_cond, b_w, bics_reg, bl, cmp_imm, cmp_reg, h, ldr_imm, ldr_sp, ldrb_imm,  # noqa: E402
                   ldrb_reg, ldrb_w, lsls_imm, lsls_reg, lsrs_imm, lsrs_reg, mov_reg, movs_imm, movt, movw, muls, orrs_reg, pop_list,
                   push_list, raw, str_imm, strb_imm, strb_reg, strb_w, strh_reg, subs_imm8, subs_reg, tst_reg)
import countin as CI  # noqa: E402
import granpage as GP  # noqa: E402
import rhstate  # noqa: E402

FXR = rhstate.ST2 + rhstate.OFF2["modmx"][0] + 296
MAGIC = 0x51535846                                        # "FXSQ"
O_OCT = 31                                               # the Octave button held in an FX track's view (19 / 20; 0 = none)
O_CUR, O_LAST, O_OWN, O_THR, O_BUSY, O_SDL, O_SRV, O_SFB, O_SDC, O_PEND, O_SW, O_SMP, RAM_LEN = 4, 12, 20, 29, 30, 32, 40, 48, 49, 50, 60, 64, 72
O_SENT, O_RR, RAM_LEN_S = 72, 80, 84                   # (sends) the values last sent (8), the round
MGR = 0x200438AC
TBL = MGR + 0x1D8
HELD = 0x20043894
PRESS_W, RELEASE_W = 0x08063A78, 0x08063A7C
PRESS0, RELEASE0 = 0x08039770, 0x08039848
COLT = 0x08062B30
NOTE_ON, NOTE_OFF = 0x08040778, 0x0804083C
BREL = CI.BTN_RELEASE                                    # the button release's entry (already a chain: our head in front)
UNLOCK, UNLOCK_SITES = 0x08030EB8, (0x080467A4, 0x0804681E)          # the note-on / note-off wrappers (0x08046780 / 0x080467AA) release the lock 0x2000A820
OFF_HEAD, OFF_CONT = "push {r2, r3, r4, r5, r6, lr}|and r0, r0, #7", 0x08040842
SETTER, SET_OBJ, GETTER = 0x08031A38, 0x20010E10, 0x08046410
GSET, GSET_OBJ = 0x08038A08, 0x20011998
WPTR, COMMIT, PARAM_GET = CI.WPTR, CI.COMMIT, CI.PARAM_GET
REC_OWNER, REC_FX = 0x2003C0CC, 0x61
HAL = 0x20006F3C
CTRL = CI.CTRL
CONT_MODE = 0x20048B9C + 0x264
MIXER, MIX_MODE, MIX_SLOT_KNOB = 0x2004E090, 0x1CC, 0x08067918 + 0x10
SV0, SV_SZ, SV_ST1, SV_PAGE = 0x2004B3A4, 0x118, 0xC, 0x60
PL0, PL_SZ, PL_SEL, PAT_SZ = 0x200470D4, 0x190, 0x60, 0xA28
SLOT4 = 0x08068D24 + 0x10                        # the players' vtable, slot 4 (0x0804B060 in the stock: the step's sample)
ID_DOWN, ID_UP = 19, 20
P_FX, P_E0, P_E1 = 20, 16, 23                            # Sample mode's pad 21; the engine pads 17-24
COL_FX, COL_FXD, COL_DEL, COL_REV, COL_SEL = 0xDD, 0xE0, 0x74, 0x29, 0x01
COL_FX2, COL_FXD2 = 0xC1, 0xB5                          # (fxbright) the same blues steady: the stock's output stage blinks 0xD2-0xE0 white
T_DEL, T_REV, T_MAX = 7, 8, 8
GRP_PROJ, GRP_TRK, IDX_REV, IDX_DEL, GID_REV, GID_DEL = 0x20, 0x10, 0x12, 0x13, 0x80, 0x88
IDX_FB, IDX_DEC = 5, 1                                   # the delay's feedback, the reverb's decay (group 0x20)
BASEID = (0xA9, 0xAC, 0xAE, 0xB0, 0xB7, 0xBA, 0xBF, 0x00)
NPAR = (3, 2, 2, 7, 3, 5, 5, 0)
NEW_MAC = (100, 0)
INV = dict(eq="ne", ne="eq", lo="hs", hs="lo", hi="ls", ls="hi", ge="lt", lt="ge", gt="le", le="gt", mi="pl", pl="mi")
DATA = 16                                                 # BASEID, NPAR at the code's start
K_LO, K1_TOP = 6, 124                                    # (sends) a track's K1-K8 = its group's 6..13; K1 (the pitch) held in 4..124
ROUTER = 0x20043740                                      # the parameter router: vtable[0](router, 0x10 t + k, value)
SENDS = False                                            # (RD49, OPT sends) see c_fxsnd
HOLD = False                                             # (RD50, OPT fxhold; the user: «when a step in the two top rows is held, it should
O_HLD = 84                                               #  activate and show its effect») + 84 the held step pad + 1, + 85 its track
BRIGHT = False                                           # (RD50, OPT fxbright; the user: «every step must show the selected fx brighter,
                                                         #  just like the keyboard») the FX track's view: dim slots, the one on bright


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def arm_code(base, L, prev, off_head):
    global SENDS, BRIGHT, HOLD
    import rhbuild
    SENDS = bool(rhbuild.OPT.get("sends"))
    BRIGHT = bool(rhbuild.OPT.get("fxbright"))
    HOLD = bool(rhbuild.OPT.get("fxhold"))
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

    E(raw, bytes(BASEID) + bytes(NPAR))

    # ---- c_fxr() -> r0 = our RAM (zeroed when its magic was missing); clobbers r1-r3
    a.label("c_fxr")
    imm32(0, FXR)
    E(ldr_imm, 1, 0, 0)
    imm32(2, MAGIC)
    E(cmp_reg, 1, 2)
    E(b_cond, "fr_x", "eq")
    E(movs_imm, 1, 0)
    E(movs_imm, 3, (RAM_LEN_S if SENDS else RAM_LEN) + (4 if HOLD else 0))
    a.label("fr_z")
    E(subs_imm8, 3, 4)
    E(raw, h(0x50C1))                                                     # str r1, [r0, r3]
    E(b_cond, "fr_z", "ne")
    E(movs_imm, 1, 0xFF)
    E(strb_w, 1, 0, O_SFB)
    E(strb_w, 1, 0, O_SDC)
    E(str_imm, 2, 0, 0)
    a.label("fr_x")
    E(raw, h(0x4770))

    # ---- c_fxrec() -> r0 = the record's FX byte's address (0: no record); clobbers r1
    a.label("c_fxrec")
    imm32(1, REC_OWNER)
    E(ldr_imm, 0, 1, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "fc_x", "eq")
    E(adds_imm8, 0, REC_FX)
    a.label("fc_x")
    E(raw, h(0x4770))

    # ---- c_fxis(r0 = track) -> r0 = 1 when an FX track; clobbers r1-r3
    a.label("c_fxis")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_fxrec")
    E(cmp_imm, 0, 0)
    E(b_cond, "fi_x", "eq")
    E(ldrb_imm, 0, 0, 0)
    E(lsrs_reg, 0, 4)
    E(movs_imm, 1, 1)
    E(ands_reg, 0, 1)
    a.label("fi_x")
    E(pop_list, [4], pc=True)

    # ---- c_fxset(r0 = group, r1 = index, r2 = generic id, r3 = value): the group's and the view's stores; clobbers r0-r3
    a.label("c_fxset")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 2)
    E(mov_reg, 5, 3)
    E(mov_reg, 3, 5)
    E(mov_reg, 2, 1)
    E(mov_reg, 1, 0)
    imm32(0, SET_OBJ)
    E(bl, SETTER)
    imm32(0, GSET_OBJ)
    E(mov_reg, 1, 4)
    E(mov_reg, 2, 5)
    E(bl, GSET)
    E(pop_list, [4, 5], pc=True)

    # ---- c_fxget(r0 = group, r1 = index) -> r0 = the value (0..127); clobbers r1-r3
    a.label("c_fxget")
    E(push_list, [4], lr=True)
    E(bl, GETTER)
    E(movs_imm, 1, 0x7F)
    E(ands_reg, 0, 1)
    E(pop_list, [4], pc=True)

    # ---- c_fxty(r0 = slot) -> r0 = its type, r1 = its row in the table; clobbers r2
    a.label("c_fxty")
    E(lsls_imm, 1, 0, 3)
    E(subs_reg, 1, 1, 0)                                                  # 7 s
    imm32(2, TBL)
    E(adds_reg, 1, 1, 2)
    E(ldrb_imm, 0, 1, 0)
    E(raw, h(0x4770))

    # ---- c_fxthr(r0 = type 7 / 8, r1 = on, r2 = the slot's row): a throw on / off; clobbers r0-r3
    a.label("c_fxthr")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(subs_imm8, 0, T_DEL)
    E(mov_reg, 4, 0)                                                      # r4 = 0 delay, 1 reverb
    E(mov_reg, 5, 1)                                                      # r5 = on
    E(mov_reg, 6, 2)                                                      # r6 = the row
    E(bl, "c_fxr")
    E(mov_reg, 7, 0)                                                      # r7 = our RAM
    E(ldrb_imm, 0, 7, O_THR)
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)                                                     # r1 = the throw's bit
    E(tst_reg, 0, 1)
    E(b_cond, "th_on", "ne")
    E(cmp_imm, 5, 0)
    bc("th_x", "eq")                                                      # off and not on
    E(orrs_reg, 0, 1)
    E(strb_imm, 0, 7, O_THR)
    E(b, "th_go")
    a.label("th_on")
    E(cmp_imm, 5, 0)
    bc("th_x", "ne")                                                      # on already
    E(bics_reg, 0, 1)
    E(strb_imm, 0, 7, O_THR)
    a.label("th_go")
    # each track's send: saved and set (on), or set back (off)
    E(push_list, [4, 6])                                                  # [sp] kind, + 4 the row
    E(movs_imm, 6, 0)                                                     # r6 = the track
    a.label("th_t")
    E(ldr_sp, 0, 0)
    E(lsls_imm, 0, 0, 3)
    E(adds_reg, 4, 7, 0)
    E(adds_reg, 4, 4, 6)                                                  # r4 = our RAM + 8 kind + t (saved at + O_SDL)
    E(ldr_sp, 1, 0)
    E(movs_imm, 0, IDX_DEL)
    E(subs_reg, 0, 0, 1)
    E(mov_reg, 1, 0)                                                      # r1 = the index (delay 0x13, reverb 0x12)
    E(cmp_imm, 5, 0)
    E(b_cond, "th_off", "eq")
    E(push_list, [1])
    E(mov_reg, 0, 6)
    E(adds_imm8, 0, GRP_TRK)
    E(bl, "c_fxget")
    E(strb_w, 0, 4, O_SDL)
    E(pop_list, [1])
    E(ldr_sp, 3, 4)
    E(ldrb_imm, 3, 3, 1)                                                  # the amount = macro 1
    E(b, "th_set")
    a.label("th_off")
    E(ldrb_w, 3, 4, O_SDL)
    a.label("th_set")
    E(mov_reg, 0, 6)
    E(adds_imm8, 0, GRP_TRK)
    E(ldr_sp, 2, 0)
    E(lsls_imm, 2, 2, 3)
    E(raw, h(0x4252))                                                     # rsbs r2, r2 (negs)
    E(adds_imm8, 2, GID_DEL)
    E(adds_reg, 2, 2, 6)                                                  # the generic id: delay 0x88 + t, reverb 0x80 + t
    E(bl, "c_fxset")
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, 8)
    E(b_cond, "th_t", "lo")
    # the tail: the delay's feedback (5) / the reverb's decay (1), the generic id 0x9F + index
    E(pop_list, [4, 6])
    E(movs_imm, 0, IDX_FB)
    E(cmp_imm, 4, 0)
    E(b_cond, "th_i", "eq")
    E(movs_imm, 0, IDX_DEC)
    a.label("th_i")
    E(mov_reg, 1, 0)                                                      # r1 = the index
    E(adds_reg, 4, 7, 4)                                                  # r4 = our RAM + kind (saved at + O_SFB)
    E(cmp_imm, 5, 0)
    E(b_cond, "th_toff", "eq")
    E(ldrb_imm, 3, 6, 2)                                                  # macro 2
    E(cmp_imm, 3, 0)
    bc("th_x", "eq")
    E(push_list, [1, 3])
    E(movs_imm, 0, GRP_PROJ)
    E(bl, "c_fxget")
    E(strb_w, 0, 4, O_SFB)
    E(pop_list, [1, 3])
    E(b, "th_ts")
    a.label("th_toff")
    E(ldrb_w, 3, 4, O_SFB)
    E(cmp_imm, 3, 0xFF)
    bc("th_x", "eq")
    E(movs_imm, 0, 0xFF)
    E(strb_w, 0, 4, O_SFB)
    a.label("th_ts")
    E(movs_imm, 0, GRP_PROJ)
    E(mov_reg, 2, 1)
    E(adds_imm8, 2, 0x9F)
    E(bl, "c_fxset")
    a.label("th_x")
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_fxgfx(r0 = slot, r1 = on): its type on / off (a stock type: the macros first on; ours: the throw); clobbers r0-r3
    a.label("c_fxgfx")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)
    E(bl, "c_fxty")
    E(mov_reg, 6, 1)                                                      # r6 = the row
    E(cmp_imm, 0, T_MAX)
    bc("gx_x", "hi")
    E(cmp_imm, 0, T_DEL)
    E(b_cond, "gx_s", "lo")
    E(mov_reg, 1, 5)
    E(mov_reg, 2, 6)
    E(bl, "c_fxthr")
    E(b, "gx_x")
    a.label("gx_s")
    imm32(1, base)
    E(ldrb_reg, 4, 1, 0)                                                  # r4 = the first id (on)
    E(adds_imm8, 1, 8)
    E(ldrb_reg, 7, 1, 0)                                                  # r7 = the parameters
    E(cmp_imm, 5, 0)
    E(b_cond, "gx_o", "eq")
    a.label("gx_m")                                                       # the macros: k = 1 .. n - 1
    E(subs_imm8, 7, 1)
    E(cmp_imm, 7, 0)
    E(b_cond, "gx_o", "eq")
    E(ldrb_reg, 3, 6, 7)
    E(adds_reg, 2, 4, 7)
    E(mov_reg, 1, 2)
    E(subs_imm8, 1, 0x9F)
    E(movs_imm, 0, GRP_PROJ)
    E(bl, "c_fxset")
    E(b, "gx_m")
    a.label("gx_o")
    E(mov_reg, 3, 5)
    E(mov_reg, 2, 4)
    E(mov_reg, 1, 4)
    E(subs_imm8, 1, 0x9F)
    E(movs_imm, 0, GRP_PROJ)
    E(bl, "c_fxset")
    a.label("gx_x")
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_fxoff1(r0 = track): what it turned on, off; clobbers r0-r3
    a.label("c_fxoff1")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_fxr")
    E(mov_reg, 5, 0)
    E(adds_reg, 1, 5, 4)
    E(ldrb_imm, 0, 1, O_CUR)
    E(cmp_imm, 0, 0)
    E(b_cond, "o1_x", "eq")
    E(movs_imm, 2, 0)
    E(strb_imm, 2, 1, O_CUR)
    E(subs_imm8, 0, 1)
    E(mov_reg, 6, 0)                                                      # r6 = the slot
    E(bl, "c_fxty")
    E(cmp_imm, 0, T_MAX)
    E(b_cond, "o1_x", "hi")
    E(adds_reg, 1, 5, 0)
    E(ldrb_imm, 2, 1, O_OWN)
    E(adds_imm8, 4, 1)
    E(cmp_reg, 2, 4)
    E(b_cond, "o1_x", "ne")                                               # another track (or the view) took it since
    E(movs_imm, 2, 0)
    E(strb_imm, 2, 1, O_OWN)
    E(mov_reg, 0, 6)
    E(movs_imm, 1, 0)
    E(bl, "c_fxgfx")
    a.label("o1_x")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_fxon (0x08040778's head: r0 = code, r1 = note, r2 = velocity): an FX track's note = its slot on, nothing to the DSP
    a.label("c_fxon")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(bl, "c_fxtk")
    E(cmp_imm, 0, 8)
    bc("on_p", "hs")
    E(mov_reg, 4, 0)
    E(bl, "c_fxr")
    E(adds_reg, 0, 0, 4)
    E(movs_imm, 1, 2)
    E(strb_w, 1, 0, O_PEND)                                               # the slot on, after the stock's lock
    E(pop_list, [0, 1, 2])
    E(movs_imm, 0, 0)
    E(pop_list, [4, 5, 6, 7], pc=True)
    a.label("on_p")
    E(raw, popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    E(b_w, prev["note"])

    # ---- c_fxtk(r0 = code) -> r0 = the track when the code is an FX track's (0x10 + t) and the stock is up, else 8; clobbers r1-r3
    a.label("c_fxtk")
    E(push_list, [4], lr=True)
    E(lsrs_imm, 3, 0, 4)
    E(cmp_imm, 3, 1)
    E(b_cond, "tk_8", "ne")
    E(movs_imm, 3, 0xF)
    E(ands_reg, 0, 3)
    E(cmp_imm, 0, 7)
    E(b_cond, "tk_8", "hi")
    E(mov_reg, 4, 0)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "tk_8", "eq")
    E(mov_reg, 0, 4)
    E(bl, "c_fxis")
    E(cmp_imm, 0, 0)
    E(b_cond, "tk_8", "eq")
    E(mov_reg, 0, 4)
    E(pop_list, [4], pc=True)
    a.label("tk_8")
    E(movs_imm, 0, 8)
    E(pop_list, [4], pc=True)

    # ---- c_fxdo(r0 = track): its note-on: the slot of its sample on (after what it had); clobbers r0-r3
    a.label("c_fxdo")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_fxr")
    E(mov_reg, 5, 0)                                                      # r5 = our RAM
    E(adds_reg, 1, 5, 4)
    E(ldrb_w, 6, 1, O_SMP)                                                # r6 = the sample (the step's, or the pad's)
    E(cmp_imm, 6, 17)
    E(b_cond, "on_r", "ne")
    E(adds_reg, 1, 5, 4)                                                  # 17: the last one again
    E(ldrb_imm, 6, 1, O_LAST)
    E(subs_imm8, 6, 1)
    E(b_cond, "on_x", "mi")
    E(b, "on_s")
    a.label("on_r")
    E(cmp_imm, 6, 16)
    E(b_cond, "on_m", "ne")
    # 16: one of the slots with a type at random (a hash of the tick): the count, then the k-th
    E(movs_imm, 7, 0)
    E(movs_imm, 6, 0)
    a.label("on_c")
    E(mov_reg, 0, 6)
    E(bl, "c_fxty")
    E(cmp_imm, 0, T_MAX)
    E(b_cond, "on_c1", "hi")
    E(adds_imm8, 7, 1)
    a.label("on_c1")
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, 16)
    E(b_cond, "on_c", "lo")
    E(cmp_imm, 7, 0)
    bc("on_x", "eq")
    imm32(0, HAL)
    E(ldr_imm, 0, 0, 0)
    imm32(1, 0x9E3779B1)
    E(muls, 0, 1)
    E(lsrs_imm, 0, 0, 24)
    E(muls, 0, 7)
    E(lsrs_imm, 7, 0, 8)                                                  # r7 = k (0 .. count - 1)
    E(movs_imm, 6, 0)
    a.label("on_k")
    E(mov_reg, 0, 6)
    E(bl, "c_fxty")
    E(cmp_imm, 0, T_MAX)
    E(b_cond, "on_k1", "hi")
    E(subs_imm8, 7, 1)
    E(b_cond, "on_s", "mi")
    a.label("on_k1")
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, 16)
    E(b_cond, "on_k", "lo")
    E(b, "on_x")
    a.label("on_m")
    E(movs_imm, 0, 15)
    E(ands_reg, 6, 0)
    a.label("on_s")                                                       # r6 = the slot
    E(mov_reg, 0, 6)
    E(bl, "c_fxty")
    E(cmp_imm, 0, T_MAX)
    bc("on_x", "hi")
    E(mov_reg, 7, 0)                                                      # r7 = its type
    E(mov_reg, 0, 4)
    E(bl, "c_fxoff1")
    E(adds_reg, 1, 5, 4)
    E(adds_imm8, 6, 1)
    E(strb_imm, 6, 1, O_LAST)
    E(strb_imm, 6, 1, O_CUR)
    E(subs_imm8, 6, 1)
    E(adds_reg, 1, 5, 7)
    E(adds_imm8, 4, 1)
    E(strb_imm, 4, 1, O_OWN)
    E(mov_reg, 0, 6)
    E(movs_imm, 1, 1)
    E(bl, "c_fxgfx")
    a.label("on_x")
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_fxsmp(r0 = track, r1 = sample): kept for its next note-on; clobbers r0-r3
    a.label("c_fxsmp")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(bl, "c_fxr")
    E(adds_reg, 0, 0, 4)
    E(strb_w, 5, 0, O_SMP)
    E(pop_list, [4, 5], pc=True)

    # ---- c_fxs4 (the players' slot 4: r0 = player, r1 = pattern, r2 = step): an FX track's step sample (its flip, else the track's), then the chain
    a.label("c_fxs4")
    E(push_list, [0, 1, 2, 4, 5, 6], lr=True)
    imm32(3, PL0)
    E(subs_reg, 4, 0, 3)
    imm32(3, PL_SZ)
    E(raw, h(0xFBB4) + h(0xF4F3))                                         # udiv r4, r4, r3: the track
    E(cmp_imm, 4, 7)
    E(b_cond, "s4_p", "hi")
    E(mov_reg, 0, 4)
    E(bl, "c_fxis")
    E(cmp_imm, 0, 0)
    E(b_cond, "s4_p", "eq")
    E(ldr_sp, 0, 0)
    E(ldr_imm, 5, 0, 0x50)
    E(ldr_sp, 1, 4)
    E(movw, 2, PAT_SZ)
    E(muls, 1, 2)
    E(adds_reg, 5, 5, 1)
    E(ldr_sp, 2, 8)
    E(lsls_imm, 2, 2, 3)
    E(adds_reg, 5, 5, 2)
    E(ldrb_imm, 1, 5, 5)                                                  # the flip
    E(cmp_imm, 1, 0xFF)
    E(b_cond, "s4_s", "ne")
    E(ldr_imm, 0, 0, PL_SEL)
    E(movs_imm, 1, 0)
    E(bl, PARAM_GET)
    E(ldrb_imm, 1, 0, 0)
    a.label("s4_s")
    E(mov_reg, 0, 4)
    E(bl, "c_fxsmp")
    a.label("s4_p")
    E(raw, popw([0, 1, 2, 4, 5, 6], lr=True))
    E(b_w, prev["s4"])

    if SENDS:
        import drybus as DB
        # ---- c_fxsnd(): (sends) the FX track's K1-K8 = how much of each track goes through the Grid FX: the dry shares to core 0's X
        #      (changed ones at once, one more a frame in turn, the key with track 0's); nothing before core 0's mode 0 program; clobbers r0-r3
        a.label("c_fxsnd")
        E(push_list, [4, 5, 6, 7], lr=True)
        E(bl, L["c_rst"])
        E(cmp_imm, 0, 0)
        E(b_cond, "sn_x", "eq")
        E(ldrb_w, 1, 0, L["O_TH"])
        E(cmp_imm, 1, L["READY"])
        E(b_cond, "sn_x", "ne")
        E(bl, "c_fxrec")
        E(movs_imm, 6, 8)                                                 # r6 = the first FX track (8: none)
        E(cmp_imm, 0, 0)
        E(b_cond, "sn_f", "eq")
        E(ldrb_imm, 0, 0, 0)
        E(movs_imm, 6, 0)
        a.label("sn_ft")
        E(cmp_imm, 6, 8)
        E(b_cond, "sn_f", "hs")
        E(mov_reg, 1, 0)
        E(lsrs_reg, 1, 6)
        E(movs_imm, 2, 1)
        E(tst_reg, 1, 2)
        E(b_cond, "sn_f", "ne")
        E(adds_imm8, 6, 1)
        E(b, "sn_ft")
        a.label("sn_f")
        E(bl, "c_fxr")
        E(mov_reg, 7, 0)                                                  # r7 = our RAM
        E(ldrb_w, 5, 7, O_RR)
        E(adds_imm8, 5, 1)
        E(movs_imm, 0, 7)
        E(ands_reg, 5, 0)
        E(strb_w, 5, 7, O_RR)                                             # r5 = this frame's forced one
        E(movs_imm, 4, 0)                                                 # r4 = u
        a.label("sn_u")
        E(movs_imm, 0, 127)                                               # (no FX track, or the FX track itself: all through)
        E(cmp_imm, 6, 8)
        E(b_cond, "sn_v", "hs")
        E(cmp_reg, 4, 6)
        E(b_cond, "sn_v", "eq")
        E(mov_reg, 0, 6)
        E(adds_imm8, 0, GRP_TRK)
        E(mov_reg, 1, 4)
        E(adds_imm8, 1, K_LO)
        E(bl, "c_fxget")
        E(cmp_imm, 4, 0)
        E(b_cond, "sn_v", "ne")
        E(cmp_imm, 0, K1_TOP)                                             # K1 (the pitch) is held in 4..124: 124 = full
        E(b_cond, "sn_v", "lo")
        E(movs_imm, 0, 127)
        a.label("sn_v")
        E(adds_reg, 1, 7, 4)
        E(ldrb_w, 2, 1, O_SENT)
        E(cmp_reg, 2, 0)
        E(b_cond, "sn_w", "ne")
        E(cmp_reg, 4, 5)
        E(b_cond, "sn_n", "ne")
        a.label("sn_w")
        E(strb_w, 0, 1, O_SENT)
        E(movs_imm, 1, 127)
        E(subs_reg, 1, 1, 0)                                              # 127 - v
        imm32(2, 0x10204)
        E(muls, 1, 2)                                                     # the dry share: (127 - v) x $10204 (127 -> 0, 0 -> $7FFFFC)
        E(lsls_imm, 1, 1, 8)
        E(movs_imm, 0, 0)
        imm32(2, DB.FT)
        E(adds_reg, 2, 2, 4)
        E(bl, L["WR16"])
        E(cmp_imm, 4, 0)
        E(b_cond, "sn_n", "ne")
        E(movs_imm, 0, 0)                                                 # with track 0's: the key
        imm32(1, DB.KEYV << 8)
        imm32(2, DB.DKEY)
        E(bl, L["WR16"])
        a.label("sn_n")
        E(adds_imm8, 4, 1)
        E(cmp_imm, 4, 8)
        E(b_cond, "sn_u", "lo")
        a.label("sn_x")
        E(pop_list, [4, 5, 6, 7], pc=True)

        # ---- c_fxfull(r0 = track): (sends) its K1-K8 to full through the parameter router (K1 to 124: its top); clobbers r0-r3
        a.label("c_fxfull")
        E(push_list, [4, 5], lr=True)
        E(lsls_imm, 4, 0, 4)                                              # r4 = 0x10 t
        E(movs_imm, 5, 0)
        a.label("fu_k")
        imm32(0, ROUTER)
        E(ldr_imm, 3, 0, 0)
        E(ldr_imm, 3, 3, 0)
        E(adds_reg, 1, 4, 5)
        E(movs_imm, 2, 127)
        E(cmp_imm, 5, 0)
        E(b_cond, "fu_c", "ne")
        E(movs_imm, 2, K1_TOP)
        a.label("fu_c")
        E(raw, h(0x4798))                                                 # blx r3
        E(adds_imm8, 5, 1)
        E(cmp_imm, 5, 8)
        E(b_cond, "fu_k", "lo")
        E(pop_list, [4, 5], pc=True)

    # ---- c_fxapply(): the tracks' pending note-on / note-off (once at a time); clobbers r0-r3
    a.label("c_fxapply")
    E(push_list, [4, 5, 6], lr=True)
    E(bl, "c_fxr")
    E(mov_reg, 5, 0)
    E(ldrb_imm, 1, 5, O_BUSY)
    E(cmp_imm, 1, 0)
    E(b_cond, "ap_x", "ne")
    E(movs_imm, 1, 1)
    E(strb_imm, 1, 5, O_BUSY)
    E(movs_imm, 4, 0)
    a.label("ap_t")
    E(adds_reg, 1, 5, 4)
    E(ldrb_w, 6, 1, O_PEND)
    E(cmp_imm, 6, 0)
    E(b_cond, "ap_n", "eq")
    E(movs_imm, 0, 0)
    E(strb_w, 0, 1, O_PEND)
    E(mov_reg, 0, 4)
    E(cmp_imm, 6, 2)
    E(b_cond, "ap_on", "eq")
    E(bl, "c_fxoff1")
    E(b, "ap_n")
    a.label("ap_on")
    E(bl, "c_fxdo")
    a.label("ap_n")
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, 8)
    E(b_cond, "ap_t", "lo")
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 5, O_BUSY)
    if SENDS:
        E(bl, "c_fxsnd")                                                  # (sends) a step's automation of the knobs at once
    a.label("ap_x")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_fxunl (the note wrappers' bl to the lock's release, r0 = its guard): released, then what is pending
    a.label("c_fxunl")
    E(push_list, [4], lr=True)
    E(bl, UNLOCK)
    E(bl, "c_fxapply")
    E(pop_list, [4], pc=True)

    # ---- c_fxof (0x0804083C's entry: r0 = code, r1 = note): an FX track's slot off, then the stock's note-off
    a.label("c_fxof")
    E(push_list, [0, 1, 2, 3, 4], lr=True)
    E(bl, "c_fxtk")
    E(cmp_imm, 0, 8)
    E(b_cond, "of_p", "hs")
    E(mov_reg, 4, 0)
    E(bl, "c_fxr")
    E(adds_reg, 0, 0, 4)
    E(movs_imm, 1, 1)
    E(strb_w, 1, 0, O_PEND)                                               # the slot off, after the stock's lock (an on not yet done: dropped)
    a.label("of_p")
    E(pop_list, [0, 1, 2, 3, 4])
    E(raw, h(0xF85D) + h(0xEB04))                                         # ldr lr, [sp], #4
    E(raw, off_head)                                                      # the stock's first two instructions
    E(b_w, OFF_CONT)

    # ---- c_fxgp / c_fxgr (the manager's press / release: r0 = manager, r1 = slot): our types here (the throw), the stock's to the stock;
    #      another type above 6 does nothing
    a.label("c_fxgp")
    E(movs_imm, 3, 1)
    E(b, "gp_c")
    a.label("c_fxgr")
    E(movs_imm, 3, 0)
    a.label("gp_c")
    E(cmp_imm, 1, 15)
    E(b_cond, "gp_s", "hi")
    E(lsls_imm, 2, 1, 3)
    E(subs_reg, 2, 2, 1)
    E(adds_reg, 2, 2, 0)
    E(ldrb_w, 2, 2, 0x1D8)
    E(cmp_imm, 2, 6)
    E(b_cond, "gp_s", "ls")
    E(cmp_imm, 2, T_MAX)
    E(b_cond, "gp_x", "hi")
    E(push_list, [4], lr=True)
    E(mov_reg, 0, 1)
    E(mov_reg, 1, 3)
    E(bl, "c_fxgfx")
    E(pop_list, [4], pc=True)
    a.label("gp_x")
    E(raw, h(0x4770))
    a.label("gp_s")
    E(cmp_imm, 3, 0)
    E(b_cond, "gp_r", "eq")
    E(b_w, PRESS0)
    a.label("gp_r")
    E(b_w, RELEASE0)

    # ---- c_fxview() -> r0 = the track when its sample view (mode 0) is on the screen and it is an FX track, else 8; clobbers r1-r3
    a.label("c_fxview")
    E(push_list, [4], lr=True)
    E(bl, L["c_spview"])
    E(cmp_imm, 0, 8)
    E(b_cond, "fv_8", "hs")
    E(mov_reg, 4, 0)
    imm32(1, CONT_MODE)
    E(ldrb_imm, 1, 1, 0)
    E(cmp_imm, 1, 0)
    E(b_cond, "fv_8", "ne")
    E(bl, "c_fxis")
    E(cmp_imm, 0, 0)
    E(b_cond, "fv_8", "eq")
    E(mov_reg, 0, 4)
    E(pop_list, [4], pc=True)
    a.label("fv_8")
    E(movs_imm, 0, 8)
    E(pop_list, [4], pc=True)

    # ---- c_fxsel() -> r0 = the track while Sample mode's engine selector is open on it, else 8; clobbers r1-r3
    a.label("c_fxsel")
    E(push_list, [4], lr=True)
    E(bl, L["c_estrk"])
    E(cmp_imm, 0, 8)
    E(b_cond, "fs_8", "hs")
    E(mov_reg, 4, 0)
    imm32(1, L["ESR"])
    E(ldr_imm, 2, 1, L["O_MAG"])
    imm32(3, L["MAG"])
    E(cmp_reg, 2, 3)
    E(b_cond, "fs_8", "ne")
    E(ldrb_imm, 2, 1, 0)
    E(cmp_imm, 2, 0)
    E(b_cond, "fs_8", "eq")
    E(mov_reg, 0, 4)
    E(pop_list, [4], pc=True)
    a.label("fs_8")
    E(movs_imm, 0, 8)
    E(pop_list, [4], pc=True)

    # ---- c_fxsw(r0 = pad, r1 = 1 set / 0 test-and-clear) -> r0 = was set; clobbers r1-r3
    a.label("c_fxsw")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(bl, "c_fxr")
    E(ldr_imm, 1, 0, O_SW)
    E(movs_imm, 2, 1)
    E(lsls_reg, 2, 4)
    E(mov_reg, 3, 1)
    E(ands_reg, 3, 2)
    E(cmp_imm, 5, 0)
    E(b_cond, "sw_c", "eq")
    E(orrs_reg, 1, 2)
    E(b, "sw_s")
    a.label("sw_c")
    E(bics_reg, 1, 2)
    a.label("sw_s")
    E(str_imm, 1, 0, O_SW)
    E(mov_reg, 0, 3)
    E(pop_list, [4, 5], pc=True)

    # ---- c_fxpad (the head of the pad press chain: r0 = ctrl, r1 = pad, r2 = velocity)
    a.label("c_fxpad")
    E(cmp_imm, 1, 32)
    bc("pd_p0", "hs")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)                                                      # r5 = the pad
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("pd_p", "eq")
    # Sample mode's selector: pad 21 = FX on / off; another engine pad = FX off
    E(bl, "c_fxsel")
    E(cmp_imm, 0, 8)
    E(b_cond, "pd_v", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the track
    E(cmp_imm, 5, P_E0)
    E(b_cond, "pd_v", "lo")
    E(cmp_imm, 5, P_E1)
    E(b_cond, "pd_v", "hi")
    E(bl, "c_fxrec")
    E(cmp_imm, 0, 0)
    bc("pd_p", "eq")
    E(mov_reg, 6, 0)                                                      # r6 = the FX byte
    E(ldrb_imm, 1, 6, 0)
    E(movs_imm, 2, 1)
    E(lsls_reg, 2, 4)
    E(cmp_imm, 5, P_FX)
    E(b_cond, "pd_e", "eq")
    E(bics_reg, 1, 2)                                                     # another engine: FX off, the pad as before
    E(strb_imm, 1, 6, 0)
    E(b, "pd_p")
    a.label("pd_e")
    E(tst_reg, 1, 2)
    E(b_cond, "pd_eoff", "ne")
    E(orrs_reg, 1, 2)
    E(strb_imm, 1, 6, 0)
    if SENDS:
        E(mov_reg, 0, 4)
        E(bl, "c_fxfull")                                                 # (sends) every track through the Grid FX at first
    E(ldr_sp, 0, 0)                                                       # on: the sample engine too (its pad 17)
    E(movs_imm, 1, P_E0)
    E(movs_imm, 2, 100)
    E(bl, L["c_espad"])
    E(ldr_sp, 0, 0)
    E(movs_imm, 1, P_E0)
    E(bl, L["c_esrel"])
    E(b, "pd_swal")
    a.label("pd_eoff")
    E(bics_reg, 1, 2)
    E(strb_imm, 1, 6, 0)
    E(mov_reg, 0, 4)
    E(bl, "c_fxoff1")
    E(b, "pd_swal")
    # an FX track's sample view: a sample pad = its slot for the note it plays; Octave down / up held + a step pad = its flip 16 / 17
    a.label("pd_v")
    E(bl, "c_fxview")
    E(cmp_imm, 0, 8)
    bc("pd_p", "hs")
    E(cmp_imm, 5, 16)
    E(b_cond, "pd_st", "lo")
    E(mov_reg, 1, 5)
    E(subs_imm8, 1, 16)
    E(bl, "c_fxsmp")
    E(b, "pd_p")
    a.label("pd_st")
    E(mov_reg, 4, 0)
    E(bl, "c_fxr")
    E(ldrb_imm, 7, 0, O_OCT)
    E(subs_imm8, 7, ID_DOWN - 16)                                         # 19 -> 16, 20 -> 17
    E(cmp_imm, 7, 16)
    bc("pd_hl" if HOLD else "pd_p", "lo")
    E(cmp_imm, 7, 17)
    bc("pd_hl" if HOLD else "pd_p", "hi")                                 # r7 = the flip
    imm32(0, SV_SZ)
    E(muls, 0, 4)
    imm32(1, SV0)
    E(adds_reg, 6, 0, 1)                                                  # r6 = the step view
    E(ldr_imm, 0, 6, SV_PAGE)
    E(movs_imm, 1, 0)
    E(bl, PARAM_GET)
    E(ldrb_imm, 0, 0, 0)
    E(movs_imm, 1, 1)
    E(ands_reg, 0, 1)
    E(lsls_imm, 0, 0, 4)
    E(adds_reg, 5, 5, 0)                                                  # r5 = the step
    E(ldr_imm, 6, 6, SV_ST1)                                              # r6 = ST1
    E(mov_reg, 0, 6)
    E(lsrs_imm, 1, 5, 2)
    E(bl, WPTR)
    E(movs_imm, 3, 3)
    E(ands_reg, 3, 5)
    E(ldrb_reg, 1, 0, 3)
    E(cmp_imm, 1, 0)
    E(b_cond, "pd_h", "ne")
    E(movs_imm, 1, 100)                                                   # an empty step: velocity 100, probability 7, micro step 0
    E(strb_reg, 1, 0, 3)
    for par, val in ((8, 7), (16, 1)):
        E(mov_reg, 0, 6)
        E(lsrs_imm, 1, 5, 2)
        E(adds_imm8, 1, par)
        E(bl, WPTR)
        E(movs_imm, 3, 3)
        E(ands_reg, 3, 5)
        E(movs_imm, 1, val)
        E(strb_reg, 1, 0, 3)
    a.label("pd_h")
    E(mov_reg, 0, 6)
    E(lsrs_imm, 1, 5, 2)
    E(adds_imm8, 1, 24)
    E(bl, WPTR)
    E(movs_imm, 3, 3)
    E(ands_reg, 3, 5)
    E(strb_reg, 7, 0, 3)
    E(mov_reg, 0, 6)
    E(bl, COMMIT)
    E(ldr_sp, 5, 4)
    a.label("pd_swal")
    E(mov_reg, 0, 5)
    E(movs_imm, 1, 1)
    E(bl, "c_fxsw")
    E(pop_list, [0, 1, 2])
    E(pop_list, [4, 5, 6, 7], pc=True)
    if HOLD:                                                              # (fxhold) a plain step pad: its slot on until let go, then the stock
        a.label("pd_hl")
        E(mov_reg, 0, 4)
        E(mov_reg, 1, 5)
        E(bl, "c_fxhold")
    a.label("pd_p")
    E(raw, popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    a.label("pd_p0")
    E(b_w, prev["pad"])

    if HOLD:
        # ---- c_fxhold(r0 = track, r1 = step pad 0-15): the step's slot (its flip, else the track's sample) on, the pad kept; clobbers r0-r3
        a.label("c_fxhold")
        E(push_list, [4, 5, 6, 7], lr=True)
        E(mov_reg, 4, 0)
        E(mov_reg, 7, 1)                                                  # r7 = the pad
        imm32(0, SV_SZ)
        E(muls, 0, 4)
        imm32(1, SV0)
        E(adds_reg, 6, 0, 1)                                              # r6 = the step view
        E(ldr_imm, 0, 6, SV_PAGE)
        E(movs_imm, 1, 0)
        E(bl, PARAM_GET)
        E(ldrb_imm, 0, 0, 0)
        E(movs_imm, 1, 1)
        E(ands_reg, 0, 1)
        E(lsls_imm, 0, 0, 4)
        E(adds_reg, 5, 7, 0)                                              # r5 = the step
        E(ldr_imm, 0, 6, SV_ST1)
        E(lsrs_imm, 1, 5, 2)
        E(adds_imm8, 1, 24)
        E(bl, PARAM_GET)
        E(movs_imm, 3, 3)
        E(ands_reg, 3, 5)
        E(ldrb_reg, 1, 0, 3)                                              # its flip
        E(cmp_imm, 1, 0xFF)
        E(b_cond, "hd_s", "ne")
        imm32(0, PL_SZ)
        E(muls, 0, 4)
        imm32(1, PL0)
        E(adds_reg, 0, 0, 1)
        E(ldr_imm, 0, 0, PL_SEL)
        E(movs_imm, 1, 0)
        E(bl, PARAM_GET)
        E(ldrb_imm, 1, 0, 0)                                              # none: the track's sample
        a.label("hd_s")
        E(mov_reg, 0, 4)
        E(bl, "c_fxsmp")
        E(bl, "c_fxr")
        E(adds_imm8, 7, 1)
        E(strb_w, 7, 0, O_HLD)
        E(strb_w, 4, 0, O_HLD + 1)
        E(adds_reg, 0, 0, 4)
        E(movs_imm, 1, 2)
        E(strb_w, 1, 0, O_PEND)                                           # on (the LED frame applies it)
        E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_fxrel (the head of the pad release chain: r0 = ctrl, r1 = pad): a pad we took, swallowed
    a.label("c_fxrel")
    E(cmp_imm, 1, 32)
    bc("rl_p0", "hs")
    E(push_list, [0, 1], lr=True)
    if HOLD:                                                              # (fxhold) the held step let go: its slot off
        E(bl, "c_fxr")
        E(ldr_sp, 1, 4)
        E(adds_imm8, 1, 1)
        E(ldrb_w, 2, 0, O_HLD)
        E(cmp_reg, 2, 1)
        E(b_cond, "rl_h", "ne")
        E(movs_imm, 2, 0)
        E(strb_w, 2, 0, O_HLD)
        E(ldrb_w, 2, 0, O_HLD + 1)
        E(adds_reg, 0, 0, 2)
        E(movs_imm, 2, 1)
        E(strb_w, 2, 0, O_PEND)
        a.label("rl_h")
        E(ldr_sp, 1, 4)
    E(mov_reg, 0, 1)
    E(movs_imm, 1, 0)
    E(bl, "c_fxsw")
    E(cmp_imm, 0, 0)
    E(b_cond, "rl_p", "eq")
    E(pop_list, [0, 1], pc=True)
    a.label("rl_p")
    E(raw, popw([0, 1], lr=True))
    a.label("rl_p0")
    E(b_w, prev["rel"])

    # ---- c_fxbtn (the head of the button chain: r0 = ctrl, r1 = id): Octave down / up in an FX track's sample view do not page
    a.label("c_fxbtn")
    E(cmp_imm, 1, ID_DOWN)
    E(b_cond, "bt_c", "eq")
    E(cmp_imm, 1, ID_UP)
    bc("bt_p0", "ne")
    a.label("bt_c")
    E(push_list, [0, 1, 4], lr=True)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "bt_p", "eq")
    E(bl, "c_fxview")
    E(cmp_imm, 0, 8)
    E(b_cond, "bt_p", "hs")
    E(bl, "c_fxr")
    E(ldr_sp, 1, 4)
    E(strb_imm, 1, 0, O_OCT)                                              # held (ours: the stock never sees it)
    E(pop_list, [0, 1, 4], pc=True)
    a.label("bt_p")
    E(raw, popw([0, 1, 4], lr=True))
    a.label("bt_p0")
    E(b_w, prev["btn"])

    # ---- c_fxbrel (the button release's entry: r0 = ctrl, r1 = id): the Octave flag let go; then the stock's release
    a.label("c_fxbrel")
    E(push_list, [0, 1, 2, 3], lr=True)
    E(subs_imm8, 1, ID_DOWN)
    E(cmp_imm, 1, 1)
    E(b_cond, "br_p", "hi")
    E(bl, "c_fxr")
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 0, O_OCT)
    a.label("br_p")
    E(pop_list, [0, 1, 2, 3])
    E(raw, h(0xF85D) + h(0xEB04))                                         # ldr lr, [sp], #4
    E(b_w, prev["brel"])

    # ---- c_fxmix(r0 = view) -> r0 = 1 when the Mixer is on the screen in its Grid FX mode; clobbers r1-r3
    a.label("c_fxmix")
    E(push_list, [4], lr=True)
    imm32(1, MIXER)
    E(cmp_reg, 0, 1)
    E(b_cond, "mx_0", "ne")
    E(movw, 1, MIX_MODE)
    E(adds_reg, 0, 0, 1)
    E(ldr_imm, 0, 0, 0)
    E(movs_imm, 1, 0)
    E(bl, PARAM_GET)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, 7)
    E(b_cond, "mx_0", "ne")
    E(movs_imm, 0, 1)
    E(pop_list, [4], pc=True)
    a.label("mx_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)

    # ---- c_fxknob (the Mixer's knob slot: r0 = view, r1 = knob, r2 = delta): Grid FX, a slot held + Shift + K1 = its type
    a.label("c_fxknob")
    E(cmp_imm, 1, 0)
    bc("kn_p0", "ne")
    E(push_list, [0, 1, 2, 4, 5], lr=True)
    E(bl, "c_fxmix")
    E(cmp_imm, 0, 0)
    E(b_cond, "kn_p", "eq")
    E(bl, L["c_cishift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "kn_p", "eq")
    imm32(0, HELD)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, 15)
    E(b_cond, "kn_p", "hi")
    E(bl, "c_fxty")
    E(mov_reg, 4, 1)                                                      # r4 = the row
    E(subs_reg, 5, 1, 2)                                                  # r5 = 7 s
    E(ldr_sp, 2, 8)
    E(movs_imm, 3, 1)
    E(cmp_imm, 2, 0)
    E(b_cond, "kn_d", "gt")
    E(b_cond, "kn_x", "eq")
    E(movs_imm, 3, 0)
    E(subs_imm8, 3, 1)
    a.label("kn_d")
    E(cmp_imm, 0, T_MAX)
    E(b_cond, "kn_0", "ls")
    E(movs_imm, 0, 0)
    E(b, "kn_w")
    a.label("kn_0")
    E(adds_reg, 0, 0, 3)
    E(b_cond, "kn_x", "mi")
    E(cmp_imm, 0, T_MAX)
    E(b_cond, "kn_x", "hi")
    a.label("kn_w")
    imm32(1, MGR)
    E(ldr_imm, 1, 1, 0xC)
    E(adds_reg, 1, 1, 5)                                                  # r1 = the source's row
    E(strb_imm, 0, 4, 0)
    E(strb_imm, 0, 1, 0)
    E(cmp_imm, 0, T_DEL)
    E(b_cond, "kn_x", "lo")
    E(movs_imm, 2, NEW_MAC[0])
    E(strb_imm, 2, 4, 1)
    E(strb_imm, 2, 1, 1)
    E(movs_imm, 2, NEW_MAC[1])
    E(strb_imm, 2, 4, 2)
    E(strb_imm, 2, 1, 2)
    a.label("kn_x")
    E(pop_list, [0, 1, 2])
    E(pop_list, [4, 5], pc=True)
    a.label("kn_p")
    E(raw, popw([0, 1, 2, 4, 5], lr=True))
    a.label("kn_p0")
    E(b_w, prev["knob"])

    # ---- c_fxcol(r0 = slot) -> r0 = its colour (0: no type); clobbers r1-r3
    a.label("c_fxcol")
    E(push_list, [4], lr=True)
    E(bl, "c_fxty")
    E(cmp_imm, 0, T_MAX)
    E(b_cond, "cl_0", "hi")
    E(movs_imm, 1, COL_DEL)
    E(cmp_imm, 0, T_DEL)
    E(b_cond, "cl_r", "eq")
    E(movs_imm, 1, COL_REV)
    E(cmp_imm, 0, T_REV)
    E(b_cond, "cl_r", "eq")
    E(lsls_imm, 0, 0, 1)
    imm32(1, COLT)
    E(raw, h(0x5A08))                                                     # ldrh r0, [r1, r0]
    E(pop_list, [4], pc=True)
    a.label("cl_r")
    E(mov_reg, 0, 1)
    E(pop_list, [4], pc=True)
    a.label("cl_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)

    # ---- c_fxled (the LED calls: ctrl, frame): the chain; then the FX track's slots, the selector's pad 21, the Grid FX view's types
    a.label("c_fxled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 6, 1)                                                      # r6 = the frame
    E(mov_reg, 7, 0)                                                      # r7 = ctrl
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(bl, "c_fxapply")
    if SENDS:
        E(bl, "c_fxsnd")
    # the FX track's sample view: the slots, the track's sample white
    E(bl, "c_fxview")
    E(cmp_imm, 0, 8)
    E(b_cond, "ld_s", "hs")
    imm32(1, PL_SZ)
    E(muls, 0, 1)
    imm32(1, PL0)
    E(adds_reg, 0, 0, 1)
    E(ldr_imm, 0, 0, PL_SEL)
    E(movs_imm, 1, 0)
    E(bl, PARAM_GET)
    E(ldrb_imm, 5, 0, 0)
    E(movs_imm, 0, 15)
    E(ands_reg, 5, 0)                                                     # r5 = the track's sample (& 15: its slot)
    if BRIGHT:                                                            # (bright) the slot on now instead, when one is
        E(bl, "c_fxview")
        E(push_list, [0])
        E(bl, "c_fxr")
        E(pop_list, [1])
        E(adds_reg, 0, 0, 1)
        E(ldrb_imm, 0, 0, O_CUR)
        E(cmp_imm, 0, 0)
        E(b_cond, "ld_vs", "eq")
        E(subs_imm8, 0, 1)
        E(mov_reg, 5, 0)
        a.label("ld_vs")
    E(movs_imm, 4, 0)
    a.label("ld_v")
    E(mov_reg, 0, 4)
    E(bl, "c_fxcol")
    if BRIGHT:                                                            # every slot dim in its colour, the one on (or the track's) bright
        E(cmp_imm, 0, 0)
        E(b_cond, "ld_v1", "eq")
        E(cmp_imm, 0, COL_DEL)
        E(b_cond, "ld_vt", "eq")
        E(cmp_imm, 0, COL_REV)
        E(b_cond, "ld_vt", "eq")
        E(cmp_reg, 4, 5)                                                  # the stock's colours are its dim codes, the bright one below
        E(b_cond, "ld_v1", "ne")
        E(subs_imm8, 0, 1)
        E(b, "ld_v1")
        a.label("ld_vt")                                                  # ours (0x74 / 0x29) bright, the dim one above
        E(cmp_reg, 4, 5)
        E(b_cond, "ld_v1", "eq")
        E(adds_imm8, 0, 1)
    else:
        E(cmp_reg, 4, 5)
        E(b_cond, "ld_v1", "ne")
        E(movs_imm, 0, COL_SEL)
    a.label("ld_v1")
    E(mov_reg, 1, 4)
    E(adds_imm8, 1, 16)
    E(lsls_imm, 1, 1, 1)
    E(strh_reg, 0, 6, 1)
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, 16)
    E(b_cond, "ld_v", "lo")
    if SENDS:                                                             # (sends) K1-K8: blue, the send as brightness (kbright's overlay)
        E(bl, "c_fxview")
        E(mov_reg, 5, 0)                                                  # r5 = the track
        E(bl, L["c_rst"])
        E(cmp_imm, 0, 0)
        E(b_cond, "ld_x", "eq")
        E(movw, 1, L["O_KB"])
        E(adds_reg, 4, 0, 1)                                              # r4 = the overlay
        E(ldrb_imm, 0, 4, 0)
        E(cmp_imm, 0, 0)
        E(b_cond, "ld_x", "ne")                                           # a page of ours drew the knobs
        E(movs_imm, 0, 0xFF)
        E(strb_imm, 0, 4, 0)
        E(movs_imm, 6, 0)
        a.label("ld_kn")
        E(mov_reg, 0, 5)
        E(adds_imm8, 0, GRP_TRK)
        E(mov_reg, 1, 6)
        E(adds_imm8, 1, K_LO)
        E(bl, "c_fxget")
        E(cmp_imm, 6, 0)
        E(b_cond, "ld_kv", "ne")
        E(cmp_imm, 0, K1_TOP)
        E(b_cond, "ld_kv", "lo")
        E(movs_imm, 0, 127)
        a.label("ld_kv")
        E(adds_reg, 1, 4, 6)
        E(strb_imm, 0, 1, 1)
        E(lsls_imm, 1, 6, 1)
        E(adds_reg, 1, 1, 4)
        E(movs_imm, 0, COL_FX2 if BRIGHT else COL_FX)
        E(strb_imm, 0, 1, 10)
        E(movs_imm, 0, 0)
        E(strb_imm, 0, 1, 11)
        E(adds_imm8, 6, 1)
        E(cmp_imm, 6, 8)
        E(b_cond, "ld_kn", "lo")
    E(b, "ld_x")
    # Sample mode's selector: pad 21
    a.label("ld_s")
    E(bl, "c_fxsel")
    E(cmp_imm, 0, 8)
    E(b_cond, "ld_g", "hs")
    E(bl, "c_fxis")
    E(movs_imm, 1, COL_FX2 if BRIGHT else COL_FX)
    E(cmp_imm, 0, 0)
    E(b_cond, "ld_s1", "ne")
    E(movs_imm, 1, COL_FXD2 if BRIGHT else COL_FXD)
    a.label("ld_s1")
    E(movs_imm, 0, 2 * P_FX)
    E(strh_reg, 1, 6, 0)
    E(b, "ld_x")
    # the Grid FX view: the 16 pads from the table (a held one white)
    a.label("ld_g")
    E(ldr_imm, 0, 7, 0x7C)
    E(bl, "c_fxmix")
    E(cmp_imm, 0, 0)
    E(b_cond, "ld_x", "eq")
    E(movs_imm, 4, 0)
    a.label("ld_gl")
    E(mov_reg, 1, 4)
    E(adds_imm8, 1, 16)
    E(lsls_imm, 5, 1, 1)
    E(raw, h(0x5B70))                                                     # ldrh r0, [r6, r5]
    E(cmp_imm, 0, COL_SEL)
    E(b_cond, "ld_gn", "eq")
    E(mov_reg, 0, 4)
    if BRIGHT:                                                            # (the user on RD50: latched slots lost their bright state) only
        E(bl, "c_fxty")                                                   # our two types redrawn, bright on / dim off; the stock's as drawn
        E(subs_imm8, 0, T_DEL)
        E(b_cond, "ld_gn", "lo")
        E(cmp_imm, 0, T_REV - T_DEL)
        E(b_cond, "ld_gn", "hi")
        E(push_list, [0])
        E(bl, "c_fxr")
        E(pop_list, [1])                                                  # r1 = 0 delay / 1 reverb
        E(ldrb_imm, 2, 0, O_THR)
        E(lsrs_reg, 2, 1)
        E(movs_imm, 3, 1)
        E(ands_reg, 2, 3)                                                 # r2 = on
        E(movs_imm, 0, COL_DEL)
        E(cmp_imm, 1, 0)
        E(b_cond, "ld_g1", "eq")
        E(movs_imm, 0, COL_REV)
        a.label("ld_g1")
        E(cmp_imm, 2, 0)
        E(b_cond, "ld_g2", "ne")
        E(adds_imm8, 0, 1)
        a.label("ld_g2")
    else:
        E(bl, "c_fxcol")
    E(strh_reg, 0, 6, 5)
    a.label("ld_gn")
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, 16)
    E(b_cond, "ld_gl", "lo")
    a.label("ld_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; the heads: 0x08040778 (note-on), 0x0804083C's entry (note-off), the Grid FX manager's press / release words, the pad
    press / release chains, the button chain, the Mixer's knob slot, the LED calls (outermost).  Needs esel, stockplus, countin; RH91's RAM
    (not with icprobe)."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]          # noqa: E731
    lab = lambda sec, n: int(report[sec]["labels"][n], 16)              # noqa: E731
    import esel as ES
    import modmx as MX
    assert "icprobe" not in report and "c_mxhrf" in report["modmx"]["labels"] and MX.R_OFF == 296
    assert 296 + RAM_LEN_S <= rhstate.OFF2["modmx"][1]
    import cthresh as TH
    L = dict(c_rst=lab("rhstate", "c_rst"), O_TH=rhstate.OFF["cthresh"][0] + 1, READY=TH.READY, WR16=TH.WR16, O_KB=rhstate.OFF["kbright"][0],
             c_ciok=lab("countin", "c_ciok"), c_cishift=lab("countin", "c_cishift"), c_spview=lab("stockplus", "c_spview"),
             c_estrk=lab("esel", "c_estrk"), c_espad=lab("esel", "c_espad"), c_esrel=lab("esel", "c_esrel"), ESR=ES.ESR, O_MAG=ES.O_MAG, MAG=ES.MAG)
    prev = dict(s4=u(SLOT4) & ~1, brel=rhbuild.bw_target(img, BREL), note=rhbuild.bw_target(img, NOTE_ON), pad=rhbuild.bw_target(img, GP.PP_ENTRY), rel=rhbuild.bw_target(img, GP.PR_ENTRY),
                btn=rhbuild.bw_target(img, CI.BTN_ENTRY), knob=u(MIX_SLOT_KNOB) & ~1, ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    assert u(PRESS_W) == PRESS0 | 1 and u(RELEASE_W) == RELEASE0 | 1
    off_head = bytes(img[NOTE_OFF - BASE:NOTE_OFF - BASE + 6])
    code_, labels = arm_code(base_addr, L, prev, off_head)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code_
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, NOTE_ON, f"b.w #{prev['note']:#x}", b_w(NOTE_ON, labels["c_fxon"]))
    rhbuild.patch(img, NOTE_OFF, OFF_HEAD, b_w(NOTE_OFF, labels["c_fxof"]) + h(0xBF00))
    rhbuild.patch(img, BREL, f"b.w #{prev['brel']:#x}", b_w(BREL, labels["c_fxbrel"]))
    rhbuild.patch_word(img, PRESS_W, PRESS0 | 1, labels["c_fxgp"] | 1)
    rhbuild.patch_word(img, RELEASE_W, RELEASE0 | 1, labels["c_fxgr"] | 1)
    rhbuild.patch(img, GP.PP_ENTRY, f"b.w #{prev['pad']:#x}", b_w(GP.PP_ENTRY, labels["c_fxpad"]))
    rhbuild.patch(img, GP.PR_ENTRY, f"b.w #{prev['rel']:#x}", b_w(GP.PR_ENTRY, labels["c_fxrel"]))
    rhbuild.patch(img, CI.BTN_ENTRY, f"b.w #{prev['btn']:#x}", b_w(CI.BTN_ENTRY, labels["c_fxbtn"]))
    rhbuild.patch_word(img, MIX_SLOT_KNOB, prev["knob"] | 1, labels["c_fxknob"] | 1)
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_fxled"]))
    rhbuild.patch_word(img, SLOT4, prev["s4"] | 1, labels["c_fxs4"] | 1)
    for c in UNLOCK_SITES:
        rhbuild.patch(img, c, f"bl #{UNLOCK:#x}", bl(c, labels["c_fxunl"]))
    report["fxseq"] = dict(prev={k: hex(v) for k, v in prev.items()}, ram=hex(FXR),
                           labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code_
