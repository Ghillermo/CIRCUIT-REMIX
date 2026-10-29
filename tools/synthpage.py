"""The Synth page of a track: tools/synth0.py's engine on DSP core 0 played from the device (MIT; RH51; the user, 2026-10-27: «Start the synth:
RD31 first (core 1's voice with an empty sample slot, the engine in dsptool), then RH51»; the design in docs/PORTADO.md «Diseño del sinte»).

  * the track menu (a track button held, RH45): pad 8 = the synth on the track and its Synth page (a slot first: none of the 4 free =
    nothing; the track's granular and line input leave it); on a synth track not on its page = the page; on the page = the synth off
    (the stock page); pads 1-3 (the pages) leave our page; pads 3 / 4 / 5 (granular, its engine, the line input) take the synth off the
    track first (one of the three a track); pad 8's LED: chosen (on its page), on (another page), off;
  * the page's knobs (the container's knob slot, ahead of granpage's; 7-bit values, STEP a click; Shift = the second layer of all eight;
    Clear + a knob = its default):
        K1 OSC 1's wave (saw / pulse / triangle / sine)   K2 OSC 2's wave        K3 OSC 2's pitch, +-24 semitones   K4 its fine tune, +-50 cents
        K5 the mix OSC 1 .. OSC 2   K6 SUB   K7 FM   K8 the pulse's width (50 % .. 2 %)
        Shift: K1 noise   K2 sync (right half)   K3 glide (5 ms .. 2 s)   K4 the octave (-3 .. +3)   K5 velocity -> FM   K6 release
        (2 ms .. 4 s)   K7 the envelope -> the low-pass (from the middle)   K8 (nothing)
    the track's own knobs on the stock page: its pitch, its envelope knob, the filters, level, pan, sends (synth0 reads them);
  * saved with the project: rhrec "synth" ("Y", a check byte, 4 slots x 17 B: the track + 1 (0 = free), the 16 values); a block that is
    missing or wrong is made anew (no synth);
  * the LED task: with core 0 / 1 up (cthresh READY), a changed slot's 16 words to core 0 (Y:synth0.Y0 + $40 s + i, the track and the key
    last), one slot a frame, else two words a frame in turn (a lost write mended); all four after a project's block changed; on the Synth
    page K1-K8 in the reverb's colour, the value as brightness (the middle dark for the bipolar ones), the track's button blinking peach;
  * the note-off: the stock sends none for a one-shot track (0x0804083C: `ldrb r1, [r6, #1]; cbz r1` = the play mode, 0 = one-shot); a synth
    track gets it whatever its mode (the envelope's release).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm3, ands_reg, adds_imm8, adds_reg, b, b_cond, b_w, bics_reg, bl, cmp_imm, cmp_reg, eors_reg, h, ldr_imm, ldr_sp,  # noqa: E402
                   ldrb_imm, ldrb_reg, ldrb_w, ldrh_imm, lsls_imm, lsls_reg, lsrs_imm, lsrs_reg, mov_reg, movs_imm, movt, movw, muls, orrs_reg, pop_list,
                   push_list, raw, str_imm, strb_imm, strb_reg, strh_imm, strh_w_imm, subs_imm8, subs_reg, tst_reg)
import countin as CI  # noqa: E402
import cthresh as TH  # noqa: E402
import granpage as GP  # noqa: E402
import rhrec  # noqa: E402
import rhstate  # noqa: E402
import sckn as SK  # noqa: E402
import stockplus as SP  # noqa: E402
import synth0 as S  # noqa: E402

BLK, BLK_LEN = rhrec.OFF["synth"]
O = rhstate.OFF2["synth"][0]
R_PEND, R_ROUND, R_SENT, R_SUM, R_PAGE = 0, 1, 2, 3, 4
MARK, CHECK = 0x59, 0x3A                               # "Y"
NSL, NV = S.NSLOT, 16
SL = 1 + NV                                            # a slot's bytes in the block: the track + 1, the values
assert BLK_LEN == 2 + NSL * SL
PAD_SYN = 7                                            # the menu's pad 8
PAD_GRAN, PAD_GEN, PAD_LINE = 2, 3, 4                  # the menu's pads 3 / 4 / 5 (granular page, its engine, the line input)
PAL, PAL_ON, PAL_OFF, PAL_TON, PAL_TOFF = GP.PAL, GP.PAL_ON, GP.PAL_OFF, GP.PAL_TON, GP.PAL_TOFF
COL_KNOB, COL_BLINK = 0x141, 0x74                      # the reverb's colour (stockplus K6 comb), peach (fxkeys ▲)
# ui (RH52; docs/INTERFAZ.md, the user, 2026-10-28): the menu as granular's: pad 4 = the Synth page (the synth put on the track first if it
# has none), pad 12 = the synth on / off (the row under the pages, under it); pads 3 / 11 / 13 (granular page, granular on, line input)
# take the synth off first; the page in its own colour (mint: the knobs, the track's button blinking, pads 4 / 12: bright = shown / on,
# dim = not); K1 / K2 (the waves, modes) in the wave's colour (saw red, pulse yellow, triangle green, sine white) at full brightness;
# Shift + K2 (sync, on / off) as a toggle (dim / full)
UI_PAD_PAGE, UI_PAD_ON, UI_PAD_GEN, UI_PAD_LINE = 3, 11, GP.UI_PAD_ENG, 12
# and (the user, 2026-10-28: «quick tap on page opens sticky page, hold opens page until let go», as the stock's view buttons): a page pad
# (1-4) of the menu let go within PAGE_HOLD ms keeps its page; held longer, the track's pages go back to what they were at its press (the
# sound it put on the track stays); the press in rhstate «pagehold», its release ahead of granpage's (the controller's pad release)
PH_O = rhstate.OFF2["pagehold"][0]
PAGE_HOLD = 500
# menu2 (RH53; the user, 2026-10-28: «granular page is still selectable on synth mode (shouldnt)», «Stock+ for every sound»): the page pads
# only offer the track's own sound's pages (a sample: stock, Stock+; granular: stock, Granular; synth: stock, Synth; the line input: stock;
# Stock+ for the other sounds when it works on them), the others dark and doing nothing; the sound changes only with pads 11-13: switched on,
# its page (granular / synth; the line input: stock), off: stock; the sticky menu (granpage menu2) closes when a menu pad is let go
SND_SAMPLE, SND_GRAN, SND_SYNTH, SND_LINE = 0, 1, 2, 3
PAGE_SND = (None, SND_SAMPLE, SND_GRAN, SND_SYNTH)     # the page pads 1-4: the sound each needs (None = any)
# env (RH54; tools/envpage.py has the page): the menu's pad 5 = the Envelope page, for a granular or synth track (its bit t in the menu's
# byte + 3, M_ENV); a page pad 1-4, a sound switched (pads 11-13) or the Synth page set takes it off; held, as the others (pagehold's bit 3);
# py_sound also as c_sysnd for envpage; the synth's length (the release's value) 64 by default (~200 ms: one-shot is percussive now)
UI_PAD_ENV, M_ENV = 4, 3
# spall (RH55; tools/spall.py, «Stock+ for every sound»): the Stock+ page (pad 2) for a granular or synth track too (not for the line input)
LEN_DEF = 64
UI_KNOB, UI_BLINK, UI_DIM = 0x4F, 0x4F, 0x50
UI_WAVES = (0x55, 0x2F, 0x1E, 0x01)
T_DIM = GP.T_DIM
CONT, SLOT_KNOB, SUBVIEW = SK.CONT, SK.SLOT_KNOB, SP.SUBVIEW
K_MASK, K_VAL, K_CODE = SP.K_MASK, SP.K_VAL, SP.K_CODE
LED_TRK0, LED_TRK1, LED_KNOB0 = SP.LED_TRK0, SP.LED_TRK1, SP.LED_KNOB0
O_KB, O_TH = rhstate.OFF["kbright"][0], rhstate.OFF["cthresh"][0] + 1
NOFF_AT, NOFF_HEAD, NOFF_SKIP = 0x08040852, "ldrb r1, [r6, #1]|cbz r1, #0x8040872", 0x08040872
# the values: k = 0..7 the knobs, 8..15 Shift + the knobs
K_W1, K_W2, K_P2, K_FINE, K_MIX, K_SUB, K_FM, K_PW, K_NOISE, K_SYNC, K_GLIDE, K_OCT, K_VFM, K_REL, K_EF, K_SPARE = range(16)
REL_DEF = round(127 * math.log(4) / math.log(2000))    # 8 ms
DEF = (16, 16, 83, 64, 64, 0, 0, 0, 0, 16, 0, 64, 0, REL_DEF, 64, 0)
STEP = (4, 4, 1, 1, 1, 1, 1, 1, 1, 8, 1, 8, 1, 1, 1, 1)
BIP = (0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0)
BIP_UI = (3, 3) + BIP[2:9] + (2,) + BIP[10:]                # (ui) 3 = a wave (its colour), 2 = a toggle
ORDER = (S.C_SHP, S.C_P2, S.C_OCT, S.C_G1, S.C_G2, S.C_GS, S.C_GN, S.C_FM, S.C_K, S.C_GLD, S.C_VFM, S.C_REL, S.C_EF, S.C_SP, S.C_TRK, S.C_KEY)
G_LEVEL, G_HALF, G_ONE, G_PW = 46236, 33026, 66052, 63410   # 0.7 / 127, 0.5 / 127, 1 / 127, 0.96 / 127 (x 2^23)


def glide_t():
    return [S.ONE] + [S.frac(1 - math.exp(-1 / (5 * 400 ** ((v - 1) / 126) * 1.5))) for v in range(1, 128)]


def rel_t():
    return [S.frac(2 ** (-1 / (2 * 2000 ** (v / 127) * 1.5))) for v in range(128)]


def model_words(vals, trk1):
    """the 16 control words of a slot (the track + 1, 0 = free; its 16 values) as the ARM computes them (the tests')"""
    v = vals
    c = [0] * 16
    c[S.C_TRK] = trk1
    c[S.C_SHP] = (v[K_W1] >> 5) | (v[K_W2] >> 5) << 2 | (S.SHP_SYNC if v[K_SYNC] >= 64 else 0)
    c[S.C_P2] = ((((3 * v[K_P2] + 4) >> 3) - 24) << 16) + ((v[K_FINE] - 64) << 9)
    c[S.C_OCT] = (((v[K_OCT] * 7) >> 7) - 3) * 0xC0000
    c[S.C_G1], c[S.C_G2] = (127 - v[K_MIX]) * G_LEVEL, v[K_MIX] * G_LEVEL
    c[S.C_GS], c[S.C_GN] = v[K_SUB] * G_HALF, v[K_NOISE] * G_HALF
    c[S.C_FM], c[S.C_VFM] = v[K_FM] * G_ONE, v[K_VFM] * G_ONE
    c[S.C_K] = S.ONE - v[K_PW] * G_PW
    c[S.C_GLD], c[S.C_REL] = glide_t()[v[K_GLIDE]], rel_t()[v[K_REL]]
    c[S.C_EF] = (v[K_EF] - 64) * 131072
    c[S.C_KEY] = S.KEY if trk1 else 0
    return [x & 0xFFFFFF for x in c]


def model_block(slots):
    """the project's block for [(track + 1, [16 values])] (the tests')"""
    blk = bytearray(BLK_LEN)
    blk[0] = MARK
    for s, (t1, vals) in enumerate(slots):
        blk[2 + SL * s] = t1
        blk[3 + SL * s:3 + SL * s + NV] = bytes(vals)
    x = CHECK ^ MARK
    for c in blk[2:]:
        x ^= c
    blk[1] = x
    return bytes(blk)


def _pad_ui(a, E, bc, L, prev, menu2=False, env=False, spall=False):
    """(ui) c_sypad: pad 4 the Synth page (the synth put on the track first), pad 12 the synth on / off; pads 1-3 leave our page; pads 3 / 11 /
    13 (granular page, granular on, the line input) take the synth off the track first, then theirs; a page pad's press remembered (pagehold),
    c_syrel: held past PAGE_HOLD, the track's pages back at its release"""
    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    a.label("c_sypad")
    E(cmp_imm, 1, UI_PAD_LINE)
    bc("pd_s", "hi")
    E(push_list, [0, 1, 2, 3, 4, 5, 6], lr=True)
    E(mov_reg, 5, 1)
    E(bl, L["c_gpmopen"])
    E(cmp_imm, 0, 8)
    bc("pd_p", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the menu's track
    E(cmp_imm, 5, UI_PAD_ENV if env else UI_PAD_PAGE)
    E(b_cond, "pd_ns", "hi")
    if menu2:                                                             # (menu2) a page of another sound: nothing (swallowed)
        E(cmp_imm, 5, 0)
        E(b_cond, "pd_ok", "eq")
        E(bl, "py_sound")
        if env:                                                           # (env) pad 5: a granular or synth track
            E(cmp_imm, 5, UI_PAD_ENV)
            E(b_cond, "pd_ne", "ne")
            E(cmp_imm, 0, SND_GRAN)
            E(b_cond, "pd_ok", "eq")
            E(cmp_imm, 0, SND_SYNTH)
            E(b_cond, "pd_ok", "eq")
            E(b, "pd_no")
            a.label("pd_ne")
        if spall:                                                         # (spall) pad 2: Stock+ for a granular or synth track too
            E(cmp_imm, 5, 1)
            E(b_cond, "pd_ns2", "ne")
            E(cmp_imm, 0, SND_GRAN)
            E(b_cond, "pd_ok", "eq")
            E(cmp_imm, 0, SND_SYNTH)
            E(b_cond, "pd_ok", "eq")
            a.label("pd_ns2")
        E(adds_imm8, 0, 1)
        E(cmp_reg, 0, 5)
        E(b_cond, "pd_ok", "eq")
        a.label("pd_no")
        E(bl, "py_sw")
        E(b, "pd_x")
        a.label("pd_ok")
    E(bl, "py_snap")                                                      # a page pad: the pages as they are, its press
    if env:                                                               # (env) pad 5: the Envelope page, the others off
        E(cmp_imm, 5, UI_PAD_ENV)
        E(b_cond, "pd_ev", "ne")
        E(bl, "py_sw")
        E(mov_reg, 0, 4)
        E(movs_imm, 1, 0)
        E(bl, "c_sysetpg")
        E(bl, L["c_spst"])
        E(cmp_imm, 0, 0)
        E(b_cond, "pv_g", "eq")
        E(movs_imm, 1, 1)
        E(lsls_reg, 1, 4)
        E(ldrb_imm, 2, 0, 0)
        E(bics_reg, 2, 1)
        E(strb_imm, 2, 0, 0)
        a.label("pv_g")
        E(bl, L["c_gpmst"])
        E(cmp_imm, 0, 0)
        E(b_cond, "pd_x", "eq")
        E(movs_imm, 1, 1)
        E(lsls_reg, 1, 4)
        E(ldrb_imm, 2, 0, GP.M_GRAN)
        E(bics_reg, 2, 1)
        E(strb_imm, 2, 0, GP.M_GRAN)
        E(ldrb_imm, 2, 0, M_ENV)
        E(orrs_reg, 2, 1)
        E(strb_imm, 2, 0, M_ENV)
        E(b, "pd_x")
        a.label("pd_ev")
        E(bl, "py_envoff")                                                # pads 1-4: the Envelope page off
    a.label("pd_ns")
    E(cmp_imm, 5, UI_PAD_PAGE)
    bc("pd_page", "eq")
    E(cmp_imm, 5, UI_PAD_ON)
    bc("pd_tog", "eq")
    E(cmp_imm, 5, PAD_GRAN)
    E(b_cond, "pd_pg", "hi")
    E(mov_reg, 0, 4)                                                      # pads 1-3: our page off
    E(movs_imm, 1, 0)
    E(bl, "c_sysetpg")
    a.label("pd_pg")
    if not menu2:
        E(cmp_imm, 5, PAD_GRAN)
        E(b_cond, "pd_dr", "eq")
    E(cmp_imm, 5, UI_PAD_GEN)
    E(b_cond, "pd_dr", "eq")
    E(cmp_imm, 5, UI_PAD_LINE)
    E(b_cond, "pd_p", "ne")
    a.label("pd_dr")
    E(mov_reg, 0, 4)                                                      # the synth off the track, then theirs
    E(bl, "c_sydrop")
    if env:
        E(bl, "py_envoff")
    if menu2:                                                             # (menu2) and Stock+'s page off (the sound changes)
        E(bl, L["c_spst"])
        E(cmp_imm, 0, 0)
        E(b_cond, "pd_p", "eq")
        E(movs_imm, 1, 1)
        E(lsls_reg, 1, 4)
        E(ldrb_imm, 2, 0, 0)
        E(bics_reg, 2, 1)
        E(strb_imm, 2, 0, 0)
    a.label("pd_p")
    E(raw, GP.popw([0, 1, 2, 3, 4, 5, 6], lr=True))
    a.label("pd_s")
    E(b_w, prev["pad"])
    # ours: the release swallowed by the menu's
    a.label("pd_page")
    E(bl, "py_sw")
    E(mov_reg, 0, 4)
    E(bl, "c_syslot")
    E(cmp_imm, 0, NSL)
    E(b_cond, "pd_pgon", "lo")
    E(bl, "py_new")
    E(cmp_imm, 0, NSL)
    E(b_cond, "pd_x", "hs")                                               # none free: nothing
    a.label("pd_pgon")
    if env:
        E(bl, "py_envoff")
    E(mov_reg, 0, 4)                                                      # the Synth page: Stock+'s and Granular's off
    E(movs_imm, 1, 1)
    E(bl, "c_sysetpg")
    E(bl, L["c_spst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "pd_g", "eq")
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(ldrb_imm, 2, 0, 0)
    E(bics_reg, 2, 1)
    E(strb_imm, 2, 0, 0)
    a.label("pd_g")
    E(bl, L["c_gpmst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "pd_x", "eq")
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(ldrb_imm, 2, 0, GP.M_GRAN)
    E(bics_reg, 2, 1)
    E(strb_imm, 2, 0, GP.M_GRAN)
    a.label("pd_x")
    E(pop_list, [0, 1, 2, 3, 4, 5, 6], pc=True)
    a.label("pd_tog")
    E(bl, "py_sw")
    if env:
        E(bl, "py_envoff")
    E(mov_reg, 0, 4)
    E(bl, "c_syslot")
    E(cmp_imm, 0, NSL)
    E(b_cond, "pd_ton", "hs")
    E(mov_reg, 0, 4)                                                      # on: off (its page with it)
    E(bl, "c_sydrop")
    E(b, "pd_x")
    a.label("pd_ton")
    E(bl, "py_new")                                                       # off: on, the page as it was
    if menu2:                                                             # (menu2) on: its Synth page
        E(cmp_imm, 0, NSL)
        bc("pd_pgon", "lo")
    E(b, "pd_x")
    if env:
        # py_envoff (r4 = track): its Envelope page off; clobbers r0-r3
        a.label("py_envoff")
        E(push_list, [4], lr=True)
        E(bl, L["c_gpmst"])
        E(cmp_imm, 0, 0)
        E(b_cond, "eo_x", "eq")
        E(movs_imm, 1, 1)
        E(lsls_reg, 1, 4)
        E(ldrb_imm, 2, 0, M_ENV)
        E(bics_reg, 2, 1)
        E(strb_imm, 2, 0, M_ENV)
        a.label("eo_x")
        E(pop_list, [4], pc=True)
        # c_sysnd(r0 = track) -> r0 = its sound (py_sound for the other modules); clobbers r1-r3
        a.label("c_sysnd")
        E(push_list, [4], lr=True)
        E(mov_reg, 4, 0)
        E(bl, "py_sound")
        E(pop_list, [4], pc=True)
    if menu2:
        # py_sound (r4 = track) -> r0 = its sound: SND_SAMPLE, SND_GRAN, SND_SYNTH, SND_LINE; clobbers r1-r3
        a.label("py_sound")
        E(push_list, [4], lr=True)
        E(mov_reg, 0, 4)
        E(bl, "c_syslot")
        E(cmp_imm, 0, NSL)
        E(b_cond, "so_n", "hs")
        E(movs_imm, 0, SND_SYNTH)
        E(pop_list, [4], pc=True)
        a.label("so_n")
        E(mov_reg, 0, 4)
        E(bl, L["c_gnslot"])
        E(cmp_imm, 0, NSL)
        E(b_cond, "so_g", "hs")
        E(movs_imm, 0, SND_GRAN)
        E(pop_list, [4], pc=True)
        a.label("so_g")
        E(bl, L["c_liget"])                                               # r0 / r1: the two line tracks + 1 (low nibbles)
        E(adds_imm8, 4, 1)
        E(movs_imm, 2, 15)
        E(ands_reg, 0, 2)
        E(cmp_reg, 0, 4)
        E(b_cond, "so_l", "eq")
        E(ands_reg, 1, 2)
        E(cmp_reg, 1, 4)
        E(b_cond, "so_l", "eq")
        E(movs_imm, 0, SND_SAMPLE)
        E(pop_list, [4], pc=True)
        a.label("so_l")
        E(movs_imm, 0, SND_LINE)
        E(pop_list, [4], pc=True)

    # py_snap (r4 = track, r5 = page pad): pagehold = the pad + 1, the track, its pages (bit 0 Stock+, 1 Granular, 2 Synth), the HAL tick
    a.label("py_snap")
    E(push_list, [4, 5, 6], lr=True)
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "sn_x", "eq")
    E(movw, 1, PH_O)
    E(adds_reg, 6, 0, 1)                                                  # r6 = pagehold
    E(adds_imm8, 5, 1)
    E(strb_imm, 5, 6, 0)
    E(strb_imm, 4, 6, 1)
    E(movs_imm, 5, 0)
    for n, (get, off) in enumerate(((L["c_spst"], 0), (L["c_gpmst"], GP.M_GRAN), ("c_syram", R_PAGE))
                                   + (((L["c_gpmst"], M_ENV),) if env else ())):
        E(bl, get)
        E(cmp_imm, 0, 0)
        E(b_cond, f"sn_{n}", "eq")
        E(ldrb_imm, 0, 0, off)
        E(lsrs_reg, 0, 4)
        E(lsls_imm, 0, 0, 31)
        E(b_cond, f"sn_{n}", "eq")
        E(adds_imm8, 5, 1 << n)
        a.label(f"sn_{n}")
    E(strb_imm, 5, 6, 2)
    imm32(0, CI.HAL_TICK)
    E(ldr_imm, 0, 0, 0)
    E(str_imm, 0, 6, 4)
    a.label("sn_x")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_syrel (the controller's pad release, ahead of granpage's: r0 = ctrl, r1 = pad): the held page pad let go after PAGE_HOLD ms =
    # the track's pages back as they were
    a.label("c_syrel")
    E(push_list, [0, 1, 2, 3, 4, 5, 6], lr=True)
    E(mov_reg, 4, 1)
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    bc("rl_p", "eq")
    E(movw, 1, PH_O)
    E(adds_reg, 5, 0, 1)                                                  # r5 = pagehold
    E(ldrb_imm, 0, 5, 0)
    E(subs_imm8, 0, 1)
    E(cmp_reg, 0, 4)
    bc("rl_p", "ne")                                                      # not the page pad held
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 5, 0)
    imm32(0, CI.HAL_TICK)
    E(ldr_imm, 0, 0, 0)
    E(ldr_imm, 1, 5, 4)
    E(subs_reg, 0, 0, 1)
    E(movw, 1, PAGE_HOLD)
    E(cmp_reg, 0, 1)
    bc("rl_p", "lo")                                                      # a tap: the page stays
    E(ldrb_imm, 6, 5, 1)                                                  # r6 = its track
    for n, (get, off) in enumerate(((L["c_spst"], 0), (L["c_gpmst"], GP.M_GRAN), ("c_syram", R_PAGE))
                                   + (((L["c_gpmst"], M_ENV),) if env else ())):
        E(bl, get)
        E(cmp_imm, 0, 0)
        E(b_cond, f"rs_{n}", "eq")
        E(movs_imm, 1, 1)
        E(lsls_reg, 1, 6)
        E(ldrb_imm, 2, 0, off)
        E(bics_reg, 2, 1)
        E(ldrb_imm, 3, 5, 2)
        E(lsls_imm, 3, 3, 31 - n)
        E(b_cond, f"rw_{n}", "pl")
        E(orrs_reg, 2, 1)
        a.label(f"rw_{n}")
        E(strb_imm, 2, 0, off)
        a.label(f"rs_{n}")
    a.label("rl_p")
    if menu2:                                                             # (menu2) a menu pad let go: the sticky menu closes
        E(bl, L["c_gpmst"])
        E(cmp_imm, 0, 0)
        E(b_cond, "rl_q", "eq")
        E(ldrb_imm, 1, 0, GP.M_FLAGS)
        E(lsls_imm, 2, 1, 31 - 3)
        E(b_cond, "rl_q", "pl")
        E(ldr_imm, 2, 0, GP.M_SWAL)
        E(lsrs_reg, 2, 4)
        E(lsls_imm, 2, 2, 31)
        E(b_cond, "rl_q", "eq")
        E(movs_imm, 2, GP.F_STICKY | GP.F_CAND | GP.F_SHOWN)
        E(bics_reg, 1, 2)
        E(strb_imm, 1, 0, GP.M_FLAGS)
        E(movs_imm, 1, 0)
        E(strb_imm, 1, 0, GP.M_TRK)
        a.label("rl_q")
    E(raw, GP.popw([0, 1, 2, 3, 4, 5, 6], lr=True))
    E(b_w, prev["rel"])

    # py_sw (r4 = track, r5 = pad): the pad's release swallowed; clobbers r0-r3
    a.label("py_sw")
    E(push_list, [4], lr=True)
    E(bl, L["c_gpmst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "sw_x", "eq")
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 5)
    E(ldr_imm, 2, 0, GP.M_SWAL)
    E(orrs_reg, 2, 1)
    E(str_imm, 2, 0, GP.M_SWAL)
    a.label("sw_x")
    E(pop_list, [4], pc=True)
    # py_new (r4 = track) -> r0 = its new slot (NSL: none free); the granular and the line input leave the track; clobbers r0-r3
    a.label("py_new")
    E(push_list, [5], lr=True)
    E(mov_reg, 0, 4)
    E(bl, "c_syassign")
    E(mov_reg, 5, 0)
    E(cmp_imm, 0, NSL)
    E(b_cond, "nw_x", "hs")
    E(mov_reg, 0, 4)
    E(bl, L["c_gndrop"])
    E(mov_reg, 0, 4)
    E(bl, "c_sylidrop")
    a.label("nw_x")
    E(mov_reg, 0, 5)
    E(pop_list, [5], pc=True)


def arm_code(base, L, prev, ui=False, menu2=False, env=False, spall=False, noblink=False):
    a = Asm(base)
    E = a.emit
    zc = [0]

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    def bc(target, cond):
        zc[0] += 1
        n = f"_g{zc[0]}"
        E(b_cond, n, SP.INV[cond])
        E(b, target)
        a.label(n)

    t_def = base
    dft = DEF[:K_REL] + (LEN_DEF,) + DEF[K_REL + 1:] if env else DEF
    E(raw, bytes(dft) + bytes(STEP) + bytes(BIP_UI if ui else BIP) + bytes(ORDER))
    t_step, t_bip, t_order = t_def + 16, t_def + 32, t_def + 48
    t_gld = t_def + 64
    E(raw, b"".join(x.to_bytes(4, "little") for x in glide_t()))
    t_rel = t_gld + 512
    E(raw, b"".join(x.to_bytes(4, "little") for x in rel_t()))
    t_wave = t_rel + 512
    if ui:
        E(raw, b"".join(x.to_bytes(2, "little") for x in UI_WAVES))

    # ---- c_syram() -> r0 = our RAM (OFF2), 0 without it; clobbers r1-r3
    a.label("c_syram")
    E(push_list, [4], lr=True)
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "yr_x", "eq")
    E(movw, 1, O)
    E(adds_reg, 0, 0, 1)
    a.label("yr_x")
    E(pop_list, [4], pc=True)

    # ---- c_sysum(r0 = the block) -> r0 = its check byte (written); clobbers r1-r3
    a.label("c_sysum")
    E(movs_imm, 1, CHECK ^ MARK)
    E(movs_imm, 2, 2)
    a.label("ys_l")
    E(ldrb_reg, 3, 0, 2)
    E(eors_reg, 1, 3)
    E(adds_imm8, 2, 1)
    E(cmp_imm, 2, BLK_LEN)
    E(b_cond, "ys_l", "lo")
    E(strb_imm, 1, 0, 1)
    E(mov_reg, 0, 1)
    E(raw, h(0x4770))                                                     # bx lr

    # ---- c_syb() -> r0 = our block (made anew when missing or wrong), 0 without a record; clobbers r1-r3
    a.label("c_syb")
    E(push_list, [4, 5], lr=True)
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "yb_x", "eq")
    E(movw, 1, BLK)
    E(adds_reg, 4, 0, 1)
    E(ldrb_imm, 0, 4, 0)
    E(cmp_imm, 0, MARK)
    E(b_cond, "yb_new", "ne")
    E(ldrb_imm, 5, 4, 1)
    E(movs_imm, 1, CHECK ^ MARK)
    E(movs_imm, 2, 2)
    a.label("yb_l")
    E(ldrb_reg, 3, 4, 2)
    E(eors_reg, 1, 3)
    E(adds_imm8, 2, 1)
    E(cmp_imm, 2, BLK_LEN)
    E(b_cond, "yb_l", "lo")
    E(cmp_reg, 1, 5)
    E(b_cond, "yb_ok", "eq")
    a.label("yb_new")
    E(movs_imm, 0, 0)
    E(movs_imm, 2, 0)
    a.label("yb_z")
    E(strb_reg, 0, 4, 2)
    E(adds_imm8, 2, 1)
    E(cmp_imm, 2, BLK_LEN)
    E(b_cond, "yb_z", "lo")
    E(movs_imm, 0, MARK)
    E(strb_imm, 0, 4, 0)
    E(mov_reg, 0, 4)
    E(bl, "c_sysum")
    a.label("yb_ok")
    E(mov_reg, 0, 4)
    a.label("yb_x")
    E(pop_list, [4, 5], pc=True)

    # ---- c_syslot(r0 = track) -> r0 = its slot, NSL without one; clobbers r1-r3
    a.label("c_syslot")
    E(push_list, [4], lr=True)
    E(adds_imm3, 4, 0, 1)
    E(bl, "c_syb")
    E(cmp_imm, 0, 0)
    E(b_cond, "yl_n", "eq")
    E(movs_imm, 1, 0)
    E(adds_imm8, 0, 2)
    a.label("yl_l")
    E(ldrb_imm, 2, 0, 0)
    E(cmp_reg, 2, 4)
    E(b_cond, "yl_y", "eq")
    E(adds_imm8, 0, SL)
    E(adds_imm8, 1, 1)
    E(cmp_imm, 1, NSL)
    E(b_cond, "yl_l", "lo")
    a.label("yl_n")
    E(movs_imm, 0, NSL)
    E(pop_list, [4], pc=True)
    a.label("yl_y")
    E(mov_reg, 0, 1)
    E(pop_list, [4], pc=True)

    # ---- c_syv(r0 = slot, r1 = k) -> its value (the default without the block); clobbers r1-r3
    a.label("c_syv")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(bl, "c_syb")
    E(cmp_imm, 0, 0)
    E(b_cond, "yv_d", "eq")
    E(movs_imm, 1, SL)
    E(muls, 1, 4)
    E(adds_reg, 0, 0, 1)
    E(adds_reg, 0, 0, 5)
    E(ldrb_imm, 0, 0, 3)
    E(pop_list, [4, 5], pc=True)
    a.label("yv_d")
    imm32(0, t_def)
    E(ldrb_reg, 0, 0, 5)
    E(pop_list, [4, 5], pc=True)

    # ---- c_sypend(r0 = slot): its words to send (R_PEND); the block's check seen (our own change); clobbers r0-r3
    a.label("c_sypend")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_syram")
    E(cmp_imm, 0, 0)
    E(b_cond, "yp_x", "eq")
    E(mov_reg, 3, 0)
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(ldrb_imm, 2, 3, R_PEND)
    E(orrs_reg, 2, 1)
    E(strb_imm, 2, 3, R_PEND)
    E(bl, "c_syb")
    E(cmp_imm, 0, 0)
    E(b_cond, "yp_x", "eq")
    E(ldrb_imm, 0, 0, 1)
    E(push_list, [0])
    E(bl, "c_syram")
    E(pop_list, [1])
    E(strb_imm, 1, 0, R_SUM)
    a.label("yp_x")
    E(pop_list, [4], pc=True)

    # ---- c_syp(r0 = slot, r1 = k, r2 = value): into the block, its check, the slot to send; clobbers r0-r3
    a.label("c_syp")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(mov_reg, 6, 2)
    E(bl, "c_syb")
    E(cmp_imm, 0, 0)
    E(b_cond, "yq_x", "eq")
    E(movs_imm, 1, SL)
    E(muls, 1, 4)
    E(adds_reg, 1, 0, 1)
    E(adds_reg, 1, 1, 5)
    E(strb_imm, 6, 1, 3)
    E(bl, "c_sysum")
    E(mov_reg, 0, 4)
    E(bl, "c_sypend")
    a.label("yq_x")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_syassign(r0 = track) -> r0 = its slot (a free one with the defaults), NSL when none is free; clobbers r1-r3
    a.label("c_syassign")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_syslot")
    E(cmp_imm, 0, NSL)
    E(b_cond, "ya_x", "lo")
    E(bl, "c_syb")
    E(cmp_imm, 0, 0)
    E(b_cond, "ya_n", "eq")
    E(mov_reg, 5, 0)
    E(movs_imm, 6, 0)
    E(adds_imm8, 0, 2)
    a.label("ya_l")
    E(ldrb_imm, 1, 0, 0)
    E(cmp_imm, 1, 0)
    E(b_cond, "ya_g", "eq")
    E(adds_imm8, 0, SL)
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, NSL)
    E(b_cond, "ya_l", "lo")
    a.label("ya_n")
    E(movs_imm, 0, NSL)
    E(pop_list, [4, 5, 6], pc=True)
    a.label("ya_g")
    E(adds_imm3, 1, 4, 1)
    E(strb_imm, 1, 0, 0)                                                  # the track + 1, the defaults
    imm32(1, t_def)
    E(movs_imm, 2, 0)
    a.label("ya_d")
    E(ldrb_reg, 3, 1, 2)
    E(adds_reg, 4, 0, 2)
    E(strb_imm, 3, 4, 1)
    E(adds_imm8, 2, 1)
    E(cmp_imm, 2, NV)
    E(b_cond, "ya_d", "lo")
    E(mov_reg, 0, 5)
    E(bl, "c_sysum")
    E(mov_reg, 0, 6)
    E(bl, "c_sypend")
    E(mov_reg, 0, 6)
    a.label("ya_x")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_sypage(r0 = track) -> r0 = 1 on its Synth page (the page bit and a slot), else 0; c_sysetpg(r0 = track, r1 = 0 / 1): the
    # page bit; clobber r1-r3
    a.label("c_sypage")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_syram")
    E(cmp_imm, 0, 0)
    E(b_cond, "yg_0", "eq")
    E(ldrb_imm, 0, 0, R_PAGE)
    E(lsrs_reg, 0, 4)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "yg_0", "eq")
    E(mov_reg, 0, 4)
    E(bl, "c_syslot")
    E(cmp_imm, 0, NSL)
    E(b_cond, "yg_0", "hs")
    E(movs_imm, 0, 1)
    E(pop_list, [4], pc=True)
    a.label("yg_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)
    a.label("c_sysetpg")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(bl, "c_syram")
    E(cmp_imm, 0, 0)
    E(b_cond, "yx_x", "eq")
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(ldrb_imm, 2, 0, R_PAGE)
    E(bics_reg, 2, 1)
    E(cmp_imm, 5, 0)
    E(b_cond, "yx_w", "eq")
    E(orrs_reg, 2, 1)
    a.label("yx_w")
    E(strb_imm, 2, 0, R_PAGE)
    a.label("yx_x")
    E(pop_list, [4, 5], pc=True)

    # ---- c_sydrop(r0 = track): its slot freed (its words to send), its Synth page off; clobbers r0-r3
    a.label("c_sydrop")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_syslot")
    E(cmp_imm, 0, NSL)
    E(b_cond, "yd_p", "hs")
    E(mov_reg, 5, 0)
    E(bl, "c_syb")
    E(movs_imm, 2, SL)
    E(muls, 2, 5)
    E(adds_reg, 2, 0, 2)
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 2, 2)
    E(bl, "c_sysum")
    E(mov_reg, 0, 5)
    E(bl, "c_sypend")
    a.label("yd_p")
    E(mov_reg, 0, 4)
    E(movs_imm, 1, 0)
    E(bl, "c_sysetpg")
    E(pop_list, [4, 5], pc=True)

    # ---- c_sylidrop(r0 = track): the line input off the track (linein's two line tracks); clobbers r0-r3
    a.label("c_sylidrop")
    E(push_list, [4], lr=True)
    E(adds_imm3, 4, 0, 1)
    E(bl, L["c_liget"])
    E(movs_imm, 3, 15)
    E(mov_reg, 2, 0)
    E(ands_reg, 2, 3)
    E(cmp_reg, 2, 4)
    E(b_cond, "yi_a", "eq")
    E(mov_reg, 2, 1)
    E(ands_reg, 2, 3)
    E(cmp_reg, 2, 4)
    E(b_cond, "yi_x", "ne")
    E(movs_imm, 1, 0)                                                     # the second out
    E(b, "yi_w")
    a.label("yi_a")
    E(mov_reg, 0, 1)                                                      # the first out (the second moves up)
    E(movs_imm, 1, 0)
    a.label("yi_w")
    E(bl, L["c_liput"])
    a.label("yi_x")
    E(pop_list, [4], pc=True)

    # ---- c_syword(r0 = slot, r1 = i) -> r0 = its control word i (tools/synth0.py C_*: synthpage.model_words); clobbers r1-r3
    a.label("c_syword")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)

    def val(k, rd=0):
        E(mov_reg, 0, 4)
        E(movs_imm, 1, k)
        E(bl, "c_syv")
        if rd != 0:
            E(mov_reg, rd, 0)

    def case(i, nxt):
        E(cmp_imm, 5, i)
        E(b_cond, nxt, "ne")

    case(S.C_TRK, "w1")
    E(bl, "c_syb")
    E(cmp_imm, 0, 0)
    bc("w_x", "eq")
    E(movs_imm, 1, SL)
    E(muls, 1, 4)
    E(adds_reg, 0, 0, 1)
    E(ldrb_imm, 0, 0, 2)
    E(b, "w_x")
    a.label("w1")
    case(S.C_KEY, "w2")
    E(bl, "c_syb")
    E(cmp_imm, 0, 0)
    bc("w_x", "eq")
    E(movs_imm, 1, SL)
    E(muls, 1, 4)
    E(adds_reg, 0, 0, 1)
    E(ldrb_imm, 0, 0, 2)
    E(cmp_imm, 0, 0)
    bc("w_x", "eq")
    imm32(0, S.KEY)
    E(b, "w_x")
    a.label("w2")
    case(S.C_SHP, "w3")
    val(K_W1, 6)
    E(lsrs_imm, 6, 6, 5)
    val(K_W2)
    E(lsrs_imm, 0, 0, 5)
    E(lsls_imm, 0, 0, 2)
    E(orrs_reg, 6, 0)
    val(K_SYNC)
    E(cmp_imm, 0, 64)
    E(b_cond, "w2s", "lo")
    E(movs_imm, 0, S.SHP_SYNC)
    E(orrs_reg, 6, 0)
    a.label("w2s")
    E(mov_reg, 0, 6)
    E(b, "w_x")
    a.label("w3")
    case(S.C_P2, "w4")
    val(K_P2, 6)                                                          # ((3 v + 4) >> 3) - 24 semitones
    E(movs_imm, 0, 3)
    E(muls, 6, 0)
    E(adds_imm8, 6, 4)
    E(lsrs_imm, 6, 6, 3)
    E(subs_imm8, 6, 24)
    E(lsls_imm, 6, 6, 16)
    val(K_FINE)                                                           # + (v - 64) << 9
    E(subs_imm8, 0, 64)
    E(lsls_imm, 0, 0, 9)
    E(adds_reg, 0, 0, 6)
    E(b, "w_x")
    a.label("w4")
    case(S.C_OCT, "w5")
    val(K_OCT)                                                            # ((v x 7) >> 7) - 3 octaves
    E(movs_imm, 1, 7)
    E(muls, 0, 1)
    E(lsrs_imm, 0, 0, 7)
    E(subs_imm8, 0, 3)
    imm32(1, 0xC0000)
    E(muls, 0, 1)
    E(b, "w_x")
    a.label("w5")
    for i, k, mul, inv in ((S.C_G1, K_MIX, G_LEVEL, True), (S.C_G2, K_MIX, G_LEVEL, False), (S.C_GS, K_SUB, G_HALF, False),
                           (S.C_GN, K_NOISE, G_HALF, False), (S.C_FM, K_FM, G_ONE, False), (S.C_VFM, K_VFM, G_ONE, False)):
        nx = f"wm{i}"
        case(i, nx)
        val(k)
        if inv:
            E(movs_imm, 1, 127)
            E(subs_reg, 0, 1, 0)
        imm32(1, mul)
        E(muls, 0, 1)
        E(b, "w_x")
        a.label(nx)
    case(S.C_K, "w6")
    val(K_PW)
    imm32(1, G_PW)
    E(muls, 0, 1)
    imm32(1, S.ONE)
    E(subs_reg, 0, 1, 0)
    E(b, "w_x")
    a.label("w6")
    for i, k, t in ((S.C_GLD, K_GLIDE, t_gld), (S.C_REL, K_REL, t_rel)):
        nx = f"wt{i}"
        case(i, nx)
        val(k)
        imm32(1, t)
        E(lsls_imm, 0, 0, 2)
        E(adds_reg, 0, 0, 1)
        E(ldr_imm, 0, 0, 0)
        E(b, "w_x")
        a.label(nx)
    case(S.C_EF, "w7")
    val(K_EF)                                                             # (v - 64) << 17
    E(subs_imm8, 0, 64)
    E(lsls_imm, 0, 0, 17)
    E(b, "w_x")
    a.label("w7")
    E(movs_imm, 0, 0)                                                     # C_SP
    a.label("w_x")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_sywr(r0 = slot, r1 = i): its word i to core 0's Y:synth0.Y0 + $40 slot + i; clobbers r0-r3, r12
    a.label("c_sywr")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(bl, "c_syword")
    E(lsls_imm, 1, 4, 6)
    E(adds_reg, 1, 1, 5)
    E(movw, 2, 0x8000 | S.Y0)
    E(adds_reg, 1, 1, 2)
    E(movs_imm, 2, 0)
    E(bl, L["c_gpw"])
    E(pop_list, [4, 5], pc=True)

    if ui:
        _pad_ui(a, E, bc, L, prev, menu2, env, spall)
    else:
        # ---- c_sypad (the controller's pad press, slink's head after it: r0 = ctrl, r1 = pad, r2 = velocity): the menu open, pad 8 is ours;
        # pads 1-3 leave our page; pads 3-5 take the synth off the track first
        a.label("c_sypad")
        E(cmp_imm, 1, PAD_SYN)
        bc("pd_s", "hi")
        E(push_list, [0, 1, 2, 3, 4, 5, 6], lr=True)
        E(mov_reg, 5, 1)
        E(bl, L["c_gpmopen"])
        E(cmp_imm, 0, 8)
        bc("pd_p", "hs")
        E(mov_reg, 4, 0)                                                      # r4 = the menu's track
        E(cmp_imm, 5, PAD_SYN)
        E(b_cond, "pd_ours", "eq")
        E(cmp_imm, 5, PAD_GRAN)
        E(b_cond, "pd_pg", "hi")
        E(mov_reg, 0, 4)                                                      # pads 1-3: our page off
        E(movs_imm, 1, 0)
        E(bl, "c_sysetpg")
        a.label("pd_pg")
        E(cmp_imm, 5, PAD_GRAN)
        E(b_cond, "pd_p", "lo")
        E(cmp_imm, 5, PAD_LINE)
        E(b_cond, "pd_p", "hi")
        E(mov_reg, 0, 4)                                                      # pads 3-5: the synth off the track, then theirs
        E(bl, "c_sydrop")
        a.label("pd_p")
        E(raw, GP.popw([0, 1, 2, 3, 4, 5, 6], lr=True))
        a.label("pd_s")
        E(b_w, prev["pad"])
        a.label("pd_ours")
        E(bl, L["c_gpmst"])                                                   # its release swallowed by the menu's
        E(cmp_imm, 0, 0)
        E(b_cond, "pd_x", "eq")
        E(movs_imm, 1, 1 << PAD_SYN)
        E(ldr_imm, 2, 0, GP.M_SWAL)
        E(orrs_reg, 2, 1)
        E(str_imm, 2, 0, GP.M_SWAL)
        E(mov_reg, 0, 4)
        E(bl, "c_syslot")
        E(cmp_imm, 0, NSL)
        E(b_cond, "pd_new", "hs")
        E(mov_reg, 0, 4)                                                      # a synth track: on its page = off; else the page
        E(bl, "c_sypage")
        E(cmp_imm, 0, 0)
        E(b_cond, "pd_pgon", "eq")
        E(mov_reg, 0, 4)
        E(bl, "c_sydrop")
        E(b, "pd_x")
        a.label("pd_new")
        E(mov_reg, 0, 4)
        E(bl, "c_syassign")
        E(cmp_imm, 0, NSL)
        E(b_cond, "pd_x", "hs")                                               # none free: nothing
        E(mov_reg, 0, 4)
        E(bl, L["c_gndrop"])                                                  # the granular and the line input leave the track
        E(mov_reg, 0, 4)
        E(bl, "c_sylidrop")
        a.label("pd_pgon")
        E(mov_reg, 0, 4)                                                      # the Synth page: Stock+'s and Granular's off
        E(movs_imm, 1, 1)
        E(bl, "c_sysetpg")
        E(bl, L["c_spst"])
        E(cmp_imm, 0, 0)
        E(b_cond, "pd_g", "eq")
        E(movs_imm, 1, 1)
        E(lsls_reg, 1, 4)
        E(ldrb_imm, 2, 0, 0)
        E(bics_reg, 2, 1)
        E(strb_imm, 2, 0, 0)
        a.label("pd_g")
        E(bl, L["c_gpmst"])
        E(cmp_imm, 0, 0)
        E(b_cond, "pd_x", "eq")
        E(movs_imm, 1, 1)
        E(lsls_reg, 1, 4)
        E(ldrb_imm, 2, 0, GP.M_GRAN)
        E(bics_reg, 2, 1)
        E(strb_imm, 2, 0, GP.M_GRAN)
        a.label("pd_x")
        E(pop_list, [0, 1, 2, 3, 4, 5, 6], pc=True)

    # ---- c_syknob (the container's slot 4, the head of its chain: r0 = container, r1 = knob, r2 = delta)
    a.label("c_syknob")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(cmp_imm, 1, 8)
    bc("kn_p", "hs")
    E(bl, L["c_spview"])
    E(cmp_imm, 0, 8)
    bc("kn_p", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the track
    E(bl, "c_sypage")
    E(cmp_imm, 0, 0)
    bc("kn_p", "eq")                                                      # not its Synth page
    imm32(0, CONT)
    E(bl, SUBVIEW)
    E(cmp_imm, 0, 0)
    bc("kn_p", "eq")                                                      # no knobs in this mode
    E(ldr_sp, 5, 4)                                                       # r5 = k
    E(bl, L["c_spshift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "kn_n", "eq")
    E(adds_imm8, 5, 8)
    a.label("kn_n")
    E(mov_reg, 0, 4)
    E(bl, "c_syslot")
    E(mov_reg, 6, 0)                                                      # r6 = the slot
    E(bl, L["c_spheld"])
    E(lsls_imm, 0, 0, 31 - SP.BIT_CLEAR)
    E(b_cond, "kn_t", "pl")
    imm32(0, t_def)                                                       # Clear + the knob: its default
    E(ldrb_reg, 2, 0, 5)
    E(b, "kn_w")
    a.label("kn_t")
    E(mov_reg, 0, 6)
    E(mov_reg, 1, 5)
    E(bl, "c_syv")
    E(mov_reg, 7, 0)
    imm32(0, t_step)
    E(ldrb_reg, 0, 0, 5)
    E(ldr_sp, 1, 8)                                                       # the delta
    E(muls, 0, 1)
    E(adds_reg, 2, 7, 0)
    E(cmp_imm, 2, 0)
    E(b_cond, "kn_h", "ge")
    E(movs_imm, 2, 0)
    a.label("kn_h")
    E(cmp_imm, 2, 127)
    E(b_cond, "kn_w", "le")
    E(movs_imm, 2, 127)
    a.label("kn_w")
    E(mov_reg, 0, 6)
    E(mov_reg, 1, 5)
    E(bl, "c_syp")
    E(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)
    a.label("kn_p")
    E(raw, GP.popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    E(b_w, prev["knob"])

    # ---- c_synoff (0x08040852, the note-off's `ldrb r1, [r6, #1]; cbz r1`: r4 = the track, r6 = its parameters' copy): a one-shot track's
    # note-off sent too when it is a synth track; keeps r0, r4, r5
    a.label("c_synoff")
    E(ldrb_imm, 1, 6, 1)
    E(cmp_imm, 1, 0)
    E(b_cond, "no_r", "ne")
    E(push_list, [0, 4, 5], lr=True)
    E(mov_reg, 0, 4)
    E(bl, "c_syslot")
    E(cmp_imm, 0, NSL)
    E(pop_list, [0, 4, 5])
    E(pop_list, [1])                                                      # (lr into r1; the flags kept)
    E(mov_reg, 14, 1)
    E(b_cond, "no_r", "lo")
    imm32(1, NOFF_SKIP | 1)
    E(raw, h(0x4708))                                                     # bx r1: the stock's skip
    a.label("no_r")
    E(raw, h(0x4770))                                                     # bx lr

    # ---- c_syled (the LED task's calls: ctrl, frame): the chain; the words to core 0; the menu's pad 8; the Synth page's LEDs
    a.label("c_syled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)                                                      # r5 = the frame
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("ll_x", "eq")
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    bc("ll_x", "eq")
    E(ldrb_w, 1, 0, O_TH)
    E(cmp_imm, 1, TH.READY)
    bc("ll_m", "ne")                                                      # core 0 / 1 not seen up: no words
    E(bl, "c_syram")
    E(cmp_imm, 0, 0)
    bc("ll_m", "eq")
    E(mov_reg, 4, 0)                                                      # r4 = our RAM
    E(bl, "c_syb")
    E(cmp_imm, 0, 0)
    bc("ll_m", "eq")
    E(ldrb_imm, 0, 0, 1)                                                  # the block's check: another one = a project loaded
    E(ldrb_imm, 1, 4, R_SUM)
    E(ldrb_imm, 2, 4, R_SENT)
    E(cmp_imm, 2, 0)
    E(b_cond, "ll_all", "eq")
    E(cmp_reg, 0, 1)
    E(b_cond, "ll_pd", "eq")
    a.label("ll_all")
    E(strb_imm, 0, 4, R_SUM)
    E(movs_imm, 0, 1)
    E(strb_imm, 0, 4, R_SENT)
    E(movs_imm, 0, (1 << NSL) - 1)
    E(strb_imm, 0, 4, R_PEND)
    a.label("ll_pd")
    E(ldrb_imm, 7, 4, R_PEND)
    E(cmp_imm, 7, 0)
    E(b_cond, "ll_rd", "eq")
    E(movs_imm, 6, 0)                                                     # the lowest slot to send: its 16 words (the track, the key last)
    a.label("ll_fs")
    E(mov_reg, 0, 7)
    E(lsrs_reg, 0, 6)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "ll_go", "ne")
    E(adds_imm8, 6, 1)
    E(b, "ll_fs")
    a.label("ll_go")
    E(movs_imm, 0, 1)
    E(lsls_reg, 0, 6)
    E(bics_reg, 7, 0)
    E(strb_imm, 7, 4, R_PEND)
    E(movs_imm, 7, 0)
    a.label("ll_wa")
    imm32(0, t_order)
    E(ldrb_reg, 1, 0, 7)
    E(mov_reg, 0, 6)
    E(bl, "c_sywr")
    E(adds_imm8, 7, 1)
    E(cmp_imm, 7, NV)
    E(b_cond, "ll_wa", "lo")
    E(b, "ll_m")
    a.label("ll_rd")
    for _ in range(2):                                                    # else two words a frame in turn
        E(ldrb_imm, 6, 4, R_ROUND)
        E(lsrs_imm, 0, 6, 4)
        E(movs_imm, 1, 15)
        E(ands_reg, 1, 6)
        imm32(2, t_order)
        E(ldrb_reg, 1, 2, 1)
        E(bl, "c_sywr")
        E(adds_imm8, 6, 1)
        E(movs_imm, 0, 4 * NV - 1)
        E(ands_reg, 6, 0)
        E(strb_imm, 6, 4, R_ROUND)
    a.label("ll_m")
    E(bl, L["c_gpmopen"])                                                 # the menu open: pad 8; pads 1-3 none chosen on our page
    E(cmp_imm, 0, 8)
    bc("ll_pg", "hs")
    E(mov_reg, 4, 0)
    if ui:                                                                # (ui) pad 12 on / off, pad 4 the page; pads 1-3 dim on our page
        E(bl, "c_syslot")
        E(movs_imm, 1, UI_DIM)
        E(cmp_imm, 0, NSL)
        E(b_cond, "lu_on", "hs")
        E(movs_imm, 1, UI_KNOB)
        a.label("lu_on")
        E(strh_imm, 1, 5, 2 * UI_PAD_ON)
        E(mov_reg, 0, 4)
        E(bl, "c_sypage")
        E(movs_imm, 1, UI_DIM)
        E(cmp_imm, 0, 0)
        E(b_cond, "lu_pg", "eq")
        E(movs_imm, 1, UI_KNOB)
        for k in range(3):
            E(movs_imm, 0, GP.UI_PAGES[k][1])
            E(strh_imm, 0, 5, 2 * k)
        a.label("lu_pg")
        E(strh_imm, 1, 5, 2 * UI_PAD_PAGE)
        if menu2:                                                         # (menu2) the pages of another sound dark
            E(bl, "py_sound")
            E(movs_imm, 1, 0)
            for k in (1, 2, 3):
                if spall and k == 1:                                      # (spall) Stock+: dark only on a line track
                    E(cmp_imm, 0, SND_LINE)
                    E(b_cond, f"lu_d{k}", "ne")
                else:
                    E(cmp_imm, 0, PAGE_SND[k])
                    E(b_cond, f"lu_d{k}", "eq")
                E(strh_imm, 1, 5, 2 * k)
                a.label(f"lu_d{k}")
        E(b, "ll_pg")
    E(bl, "c_syslot")
    imm32(1, PAL + PAL_TOFF)
    E(cmp_imm, 0, NSL)
    E(b_cond, "ll_mc", "hs")
    E(mov_reg, 0, 4)
    E(bl, "c_sypage")
    imm32(1, PAL + PAL_TON)
    E(cmp_imm, 0, 0)
    E(b_cond, "ll_mc", "eq")
    imm32(1, PAL + PAL_ON)
    for k in range(3):
        imm32(2, PAL + PAL_OFF)
        E(raw, h(0x8810))                                                 # ldrh r0, [r2]
        E(strh_imm, 0, 5, 2 * k)
    a.label("ll_mc")
    E(raw, h(0x8808))                                                     # ldrh r0, [r1]
    E(strh_imm, 0, 5, 2 * PAD_SYN)
    a.label("ll_pg")
    E(bl, L["c_spview"])
    E(cmp_imm, 0, 8)
    bc("ll_x", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the track
    E(bl, "c_sypage")
    E(cmp_imm, 0, 0)
    bc("ll_x", "eq")
    E(mov_reg, 0, 4)
    E(bl, "c_syslot")
    E(mov_reg, 6, 0)                                                      # r6 = the slot
    E(bl, L["c_rst"])
    E(movw, 1, O_KB)
    E(adds_reg, 7, 0, 1)                                                  # r7 = kbright's overlay
    E(movs_imm, 0, 0xFF)
    E(strb_imm, 0, 7, K_MASK)
    for k in range(8):
        E(bl, L["c_spshift"])
        E(movs_imm, 1, k)
        E(cmp_imm, 0, 0)
        E(b_cond, f"lm_{k}", "eq")
        E(movs_imm, 1, k + 8)
        a.label(f"lm_{k}")
        E(push_list, [1])
        E(mov_reg, 0, 6)
        E(bl, "c_syv")
        E(pop_list, [1])
        imm32(2, t_bip)
        E(ldrb_reg, 2, 2, 1)
        if ui:
            E(movs_imm, 3, UI_KNOB)                                       # r3 = the colour
        E(cmp_imm, 2, 0)
        E(b_cond, f"lu_{k}", "eq")
        if ui and k < 2:                                                  # (ui) K1 / K2: the wave's colour; with Shift, K2: sync, a toggle
            E(cmp_imm, 2, 3)
            E(b_cond, f"lt_{k}", "ne")
            E(lsrs_imm, 0, 0, 5)
            E(lsls_imm, 0, 0, 1)
            imm32(2, t_wave)
            E(adds_reg, 2, 2, 0)
            E(ldrh_imm, 3, 2, 0)
            E(movs_imm, 0, 127)
            E(b, f"lu_{k}")
            a.label(f"lt_{k}")
            if k == 1:
                E(cmp_imm, 2, 2)
                E(b_cond, f"lb_{k}", "ne")
                E(movs_imm, 2, T_DIM)
                E(cmp_imm, 0, 64)
                E(b_cond, f"ly_{k}", "lo")
                E(movs_imm, 2, 127)
                a.label(f"ly_{k}")
                E(mov_reg, 0, 2)
                E(b, f"lu_{k}")
                a.label(f"lb_{k}")
        E(subs_imm8, 0, 64)                                               # from the middle: |v - 64| x 2
        E(b_cond, f"lq_{k}", "ge")
        E(raw, h(0x4240))                                                 # rsbs r0, r0, #0
        a.label(f"lq_{k}")
        E(lsls_imm, 0, 0, 1)
        E(cmp_imm, 0, 127)
        E(b_cond, f"lu_{k}", "le")
        E(movs_imm, 0, 127)
        a.label(f"lu_{k}")
        E(strb_imm, 0, 7, K_VAL + k)
        if ui:
            E(strh_imm, 3, 7, K_CODE + 2 * k)
            E(strh_w_imm, 3, 5, 2 * (LED_KNOB0 + k))
        else:
            imm32(0, COL_KNOB)
            E(strh_imm, 0, 7, K_CODE + 2 * k)
            E(strh_w_imm, 0, 5, 2 * (LED_KNOB0 + k))
    if not noblink:                                                       # (noblink, RH58: no blink; it also lit LED 40 + t, not a track's)
        imm32(0, CI.HAL_TICK)
        E(ldr_imm, 0, 0, 0)
        E(lsls_imm, 0, 0, 23)                                                 # bit 8 of the tick
        bc("ll_x", "pl")
        E(movs_imm, 0, UI_BLINK if ui else COL_BLINK)
        E(lsls_imm, 1, 4, 1)
        E(adds_reg, 1, 5, 1)
        E(strh_w_imm, 0, 1, 2 * LED_TRK0)
        E(strh_w_imm, 0, 1, 2 * LED_TRK1)
    a.label("ll_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr, ui=False, menu2=False, env=False, spall=False, noblink=False):
    """The controller's pad press (in front of slink's), the container's knob slot (in front of granpage's), the head of the LED calls, the
    note-off's one-shot test.  Needs granpage multi, linein two, slink, stockplus, kbright, cthresh, rhrec, rhstate ram2, and synth0 on core 0."""
    import rhbuild
    import struct
    BASE = rhbuild.BASE
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]                 # noqa: E731
    assert report["granpage"].get("multi") and "slink" in report and "c_liget" in report["linein"]["labels"]
    assert any(int(x[0], 16) == S.AT for x in report["core0"]["segs"]), "synthpage needs synth0's engine on core 0"
    L = dict(c_rst=lab("rhstate", "c_rst"), c_rram=lab("rhstate", "c_rram"), c_rrt=lab("rhrec", "c_rrt"), c_ciok=lab("countin", "c_ciok"),
             c_liget=lab("linein", "c_liget"), c_liput=lab("linein", "c_liput"),
             **{k: lab("granpage", k) for k in ("c_gpmopen", "c_gpmst", "c_gndrop", "c_gpw", "c_gnslot")},
             **{k: lab("stockplus", k) for k in ("c_spheld", "c_spshift", "c_spview", "c_spst")})
    prev = dict(pad=rhbuild.bw_target(img, GP.PP_ENTRY), knob=u(SLOT_KNOB) & ~1, ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert prev["pad"] == lab("slink", "c_slpad") and prev["knob"] == lab("granpage", "c_gpknob") and prev["ledtask"] == lab("slink", "c_slled")
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    assert not ui or report["granpage"].get("ui") and report["linein"].get("ui") and report["slink"].get("ui"), "synthpage ui needs the others' ui"
    if ui:
        prev["rel"] = lab("granpage", "c_gpmrel")
        assert rhbuild.bw_target(img, GP.PR_ENTRY) == prev["rel"]
    assert ui or not menu2
    assert not menu2 or report["granpage"].get("menu2"), "synthpage menu2 needs granpage's"
    assert menu2 or not env
    assert env or not spall
    code_, labels = arm_code(base_addr, L, prev, ui, menu2, env, spall, noblink)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code_
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, GP.PP_ENTRY, f"b.w #{prev['pad']:#x}", b_w(GP.PP_ENTRY, labels["c_sypad"]))
    rhbuild.patch_word(img, SLOT_KNOB, prev["knob"] | 1, labels["c_syknob"] | 1)
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_syled"]))
    rhbuild.patch(img, NOFF_AT, NOFF_HEAD, bl(NOFF_AT, labels["c_synoff"]))
    if ui:
        rhbuild.patch(img, GP.PR_ENTRY, f"b.w #{prev['rel']:#x}", b_w(GP.PR_ENTRY, labels["c_syrel"]))
    report["synthpage"] = dict(prev={k: hex(v) for k, v in prev.items()}, tables=hex(base_addr), **({"ui": True} if ui else {}), **({"menu2": True} if menu2 else {}), **({"env": True} if env else {}), **({"spall": True} if spall else {}),
                               labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    if noblink:
        report["synthpage"]["noblink"] = True
    return labels, code_
