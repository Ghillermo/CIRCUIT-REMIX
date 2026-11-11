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
import rhbuild  # noqa: E402
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
# va (RH77, OPT vapage: tools/va0.py's oscillators (OPT va >= 3); the user, 2026-11-06: «haz la build de rythm con el VA», the layout «Like Hacks»: its OSC
# pages): K1 WAVE (the morph: sine 0, triangle 42, saw 84, square 126), K2 SHAPE (50 the middle), K3 WAVE 2, K4 SHAPE 2, K5 TUNE 2 (+-24
# semitones), K6 FM (64 none: right OSC 2 -> OSC 1, left OSC 1 -> OSC 2), K7 sync + bitwise (7 zones), K8 MIX; Shift: K1 env -> pitch, K2 env
# -> shape, K3 glide, K4 octave, K5 FINE 2, K6 RING, K7 env -> morph, K8 the release (the Envelope page's length).  The project's 16 bytes
# a slot: the knob k's value at raw MAP_VA[k]; raw 13 / 14 / 15 stay the Envelope page's (length, env -> low-pass, start), so RING and env ->
# morph (raw 16 / 17) live in bit 7 of bytes 0-6 / 7-13 (every value is 7-bit; env -> morph XOR 64: a cleared byte = the middle).  The
# Envelope page and Project init use the raw indices (c_syvr / c_sypr), the knobs, the LEDs and the matrix the knob ones (c_syv / c_syp).
# Core 0: the slot's VA block (va0.XB0 + XS s) gets 17 X words (VA_WORDS: the 13 knobs', OSC 1's TUNE / FINE 0, DFLAGS = OSC 2 heard or
# used, VMAG last: the words a block never wrote are only phases and smoothed states); synth0's Y words keep C_OCT, C_GLD, C_REL (knob 15),
# C_EF (raw 14), the track and the key (the others 0: unused by the VA).  A project block of RH51-RH76 (the old meanings) is made anew.
VA_CHECK = 0x3B
MAP_VA = tuple(range(13)) + (16, 17, 13)
K_RING, K_ENVM, K_LEN = 13, 14, 15                                   # (va) the knob indices
DEF_VA_RAW = (84, 64, 84, 64, 64, 64, 0, 0, 64, 64, 0, 64, 64, LEN_DEF, 64, 0, 0, 64)
DEF_VA = tuple(DEF_VA_RAW[MAP_VA[k]] for k in range(16))
STEP_VA = (1,) * 11 + (8,) + (1,) * 4
BIP_VA = (0, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0)
BIP_UI_VA0 = (3,) + BIP_VA[1:2] + (3,) + BIP_VA[3:]                  # (ui, RH77) K1 / K3 the morph's nearest wave in its colour
BIP_UI_VA = BIP_UI_VA0[:6] + (4,) + BIP_UI_VA0[7:]                    # (leftlight) and K7 (4)
# its zone's colour (leftlight, RH78; the user: «todas las zonas dentro de un knob tienen que ser distintas»): none dark, sync blue, xor
# red-orange, or green, nor pink, and pale yellow, nand silver; the brightness 24 + the position in the zone (as va0: 7 v = zone << 7 | pos)
VA_ZONES = (0x00, 0x12, 0x43, 0x7B, 0x66, 0x2D, 0x1B)
UI_WAVES_VA = (0x01, 0x1E, 0x55, 0x2F)                               # sine white, triangle green, saw red, square yellow (UI_WAVES' colours)
VA_PW, VA_SEMI, VA_BIP, VA_ZERO, VA_DUAL, VA_MAG = 1, 2, 3, 4, 5, 6  # (kind 0: the value as it is)
VA_EXT = 7                                                           # (RH80, OPT vsel) tools/vsel.py's value (the knob field = which)
VA_R2F = 8                                                           # (RH85, OPT ratio2) OSC 2's FINE word: the ratio (knob 4) + the detune (knob 12)
VA_DUALW, VMAGIC3 = 2, 0x7A5A03                                      # va0.DUAL, va0.VMAGIC3
VA_XB0, VA_XS = 0x4E00, 0x60                                         # va0.XB0, XS
KB_LEFT = 0x8000                                                    # kbright.BIPLEFT
# (va0 X offset, the knob, the kind)
VA_WORDS = ((2, 0, 0), (3, 1, VA_PW), (0x30 + 2, 2, 0), (0x30 + 3, 3, VA_PW), (0x30 + 0, 4, VA_SEMI), (0x30 + 6, 5, 0), (0x30 + 9, 6, 0),
            (0x30 + 4, 7, 0), (5, 8, VA_BIP), (6, 9, VA_BIP), (0x30 + 1, 12, VA_BIP), (0x30 + 7, 13, 0), (8, 14, VA_BIP), (0, 0, VA_ZERO),
            (1, 0, VA_ZERO), (21, 0, VA_DUAL), (0x30 + 47, 0, VA_MAG))
NVA = len(VA_WORDS)
VA_WORDS_EXT = tuple((o, (0 if o == 0 else 1), VA_EXT) if kind == VA_ZERO else (o, k, kind) for o, k, kind in VA_WORDS)   # (OSC 1's TUNE / FINE)
Y_EXT = ((S.C_G1, 2), (S.C_G2, 3), (S.C_GS, 4))                    # (OPT vsel) synth0's words: the envelope -> FM / ring / mix (va0 envx)
ORDER_VA = tuple(range(16, 15 + NVA, 2)) + tuple(range(17, 15 + NVA, 2)) + (15 + NVA,) + ORDER   # the bulk send: the VA's words (VMAG
                                                                     # last; not 16..31 in a row: a plain run the provenance check finds
                                                                     # in any image), then synth0's (the key last)
ORDER_VA64 = ORDER_VA + ORDER_VA[:64 - len(ORDER_VA)]                # (in turn: 64 a slot)



def pclr():
    """(RH90, OPT pclr; the user, 2026-11-10: «clear+track should restore to chosen preset, knob+clear should restore knobs» -> «Preset,
    else as now», «Only the sound's pages»): Clear + a knob of this page = the value of the preset the track loaded last (rpatch's stub)"""
    import rhbuild
    return bool(rhbuild.OPT.get("pclr"))

def ratio2():
    """(RH85, OPT ratio2; CIRCUIT-HACKS' SC52.2 RATIO2): OSC 2's coarse knob (4: the Synth page's TUNE 2, the OSC 2 page's K1) = a harmonic
    ratio of OSC 1, r2_ratio(v - 64) (0.25, 0.5, 1, 2 .. 31), its fine knob (12: FINE 2, the OSC 2 page's K2) = the detune, +-50 cents; both
    in OSC 2's FINE word in 1/256 semitone (va0 OPT ratio2), its TUNE word 0"""
    import rhbuild
    return bool(rhbuild.OPT.get("ratio2"))


def r2_ratio(v):
    """(ratio2) OSC 2's TUNE value -64..63 -> its ratio, as CIRCUIT-HACKS' vcf21.r2_ratio: 0 = 1; -1..-32 = 0.5, -33..-64 = 0.25; 1..63 = 2..31"""
    if v == 0:
        return 1
    if v < 0:
        return 0.5 if v >= -32 else 0.25
    return 2 + (v - 1) * 30 // 63


def r2_word(k):
    """(ratio2) the knob 0..127 -> the ratio's offset in 1/256 semitone"""
    import math
    return round(12 * math.log2(r2_ratio(k - 64)) * 256)


def va_words_table():
    """the (offset, knob, kind) table the ARM reads (vsel's EXT kinds, ratio2's)"""
    import rhbuild
    t = VA_WORDS_EXT if rhbuild.OPT.get("vsel") else VA_WORDS
    if ratio2():
        t = tuple((o, k, VA_ZERO if (o, k) == (0x30, 4) else VA_R2F if (o, k) == (0x31, 12) else kind) for o, k, kind in t)
    return t


def dualext():
    """(RH85, OPT dualext with vsel; the bug since RH80: OSC 1's K5 / K8 silent while OSC 2 was off) DFLAGS' DUAL also for OSC 1's envelope
    -> FM (c_syext 2 <> 0) or -> mix upwards (c_syext 4 > 0): va0 applies them (envx) only in the two-oscillator loop; -> ring (K6) needs
    RING > 0, which already turns it on"""
    import rhbuild
    return bool(rhbuild.OPT.get("dualext") and rhbuild.OPT.get("vsel"))


def va():
    """(RH77) OPT vapage: the Synth page drives the VA (needs OPT va >= 3: RD43's engine; RD41-RD43 themselves keep the old page)"""
    import rhbuild
    if not rhbuild.OPT.get("vapage"):
        return False
    assert int(rhbuild.OPT.get("va", 0) or 0) >= 3, "synthpage vapage needs va0 V3"
    return True


def va_raw(vals_raw, r):
    """(va) the value at raw index r (0..17) of a slot's 16 bytes"""
    if r < 16:
        return vals_raw[r] & 0x7F
    base = 7 * (r - 16)
    v = sum(((vals_raw[base + i] >> 7) & 1) << i for i in range(7))
    return v ^ 64 if r == 17 else v


def va_put(vals_raw, r, v):
    """(va) the 16 bytes with raw index r set to v"""
    b = list(vals_raw)
    if r < 16:
        b[r] = (b[r] & 0x80) | v
    else:
        base, v = 7 * (r - 16), v ^ 64 if r == 17 else v
        for i in range(7):
            b[base + i] = (b[base + i] & 0x7F) | ((v >> i) & 1) << 7
    return bytes(b)


def va_knobs(vals_raw):
    """(va) the 16 knob values of a slot's bytes"""
    return [va_raw(vals_raw, MAP_VA[k]) for k in range(16)]


def va_raw_bytes(knobs, raw13=LEN_DEF, raw14=64, raw15=0):
    """(va) a slot's 16 bytes from its 16 knob values (+ the Envelope page's three)"""
    b = bytes(16)
    for k in range(16):
        b = va_put(b, MAP_VA[k], knobs[k])
    for r, v in ((14, raw14), (15, raw15)):
        b = va_put(b, r, v)
    return b


def va_words(knobs, ext=None, granted=False):
    """(va) {va0 X offset in the block: word} the ARM writes for a slot's 16 knob values (the tests'); ext = tools/vsel.py's 5 stored bytes of
    the track (OPT dualext, RH85: OSC 1's envelope -> FM (a stored byte <> 0) or -> mix upwards (stored 1 .. 63: XOR 64) turns the second
    oscillator on; -> ring alone changes nothing with RING 0)"""
    import va0 as V
    out = {}
    for off, k, kind in VA_WORDS:
        v = knobs[k]
        dual = knobs[7] or knobs[5] != 64 or knobs[K_RING] or knobs[6] >= 19 or (ext is not None and (ext[2] or 1 <= ext[4] <= 63)) or granted
        w = {0: v, VA_PW: (v * 807) >> 10, VA_SEMI: ((3 * v + 4) >> 3) - 24, VA_BIP: v - 64, VA_ZERO: 0,
             VA_DUAL: V.DUAL if dual else 0, VA_MAG: V.VMAGIC3}[kind]
        if ratio2() and off == 0x30:                                    # (ratio2) TUNE 2's word 0, FINE 2's = the ratio + the detune
            w = 0
        elif ratio2() and off == 0x31:
            w = r2_word(knobs[4]) + 2 * (knobs[12] - 64)
        out[off] = w & 0xFFFFFF
    return out


def va_model_words(knobs, trk1, raw14=64):
    """(va) synth0's 16 Y words of a slot (the ARM's: the unused ones 0)"""
    c = [0] * 16
    c[S.C_TRK] = trk1
    c[S.C_OCT] = (((knobs[K_OCT] * 7) >> 7) - 3) * 0xC0000
    c[S.C_GLD], c[S.C_REL] = glide_t()[knobs[K_GLIDE]], rel_t()[knobs[K_LEN]]
    c[S.C_EF] = (raw14 - 64) * 131072
    c[S.C_KEY] = S.KEY if trk1 else 0
    return [x & 0xFFFFFF for x in c]


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


def model_block(slots, check=CHECK):
    """the project's block for [(track + 1, [16 values])] (the tests'; va: check = VA_CHECK, the values the raw bytes)"""
    blk = bytearray(BLK_LEN)
    blk[0] = MARK
    for s, (t1, vals) in enumerate(slots):
        blk[2 + SL * s] = t1
        blk[3 + SL * s:3 + SL * s + NV] = bytes(vals)
    x = check ^ MARK
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
    if menu2 and not rhbuild.OPT.get("menustay"):                         # (menu2) a menu pad let go: the sticky menu closes (RH82 menustay:
                                                                          # it stays open; the track button, another button or leaving closes it)
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

    V = va()
    CHK = VA_CHECK if V else CHECK
    t_def = base
    if V:                                                                 # (va) raw defaults (18), knob defaults, steps, bipolar, the
        assert env and ui                                                 # orders, the map, the VA words (offset, knob, kind)
        tb = bytes(DEF_VA_RAW) + bytes(2) + bytes(DEF_VA) + bytes(STEP_VA) + bytes(BIP_UI_VA if rhbuild.OPT.get("leftlight") else BIP_UI_VA0)
        tb += bytes(ORDER_VA64) + bytes(MAP_VA)
        t_kdef, t_step, t_bip = t_def + 20, t_def + 36, t_def + 52
        t_order, t_map = t_def + 68, t_def + 132
        t_vw = t_def + 148
        tb += b"".join(bytes(w) for w in va_words_table()) + bytes(1)
        assert len(tb) == 148 + 3 * NVA + 1 and len(tb) % 4 == 0
        import tabpack as TBP_L
        if TBP_L.lowtab():                                                # (lowtab) in the ITCM's low room
            lo = TBP_L.region("synthpage_v", [(tb, 1)], low=True)
            t_def, t_kdef, t_step, t_bip = lo, lo + 20, lo + 36, lo + 52
            t_order, t_map, t_vw = lo + 68, lo + 132, lo + 148
            t_gld = base
        else:
            E(raw, tb)
            t_gld = t_def + len(tb)
    else:
        t_kdef = t_def
        dft = DEF[:K_REL] + (LEN_DEF,) + DEF[K_REL + 1:] if env else DEF
        E(raw, bytes(dft) + bytes(STEP) + bytes(BIP_UI if ui else BIP) + bytes(ORDER))
        t_step, t_bip, t_order = t_def + 16, t_def + 32, t_def + 48
        t_gld = t_def + 64
    import tabpack as TBP
    LL = rhbuild.OPT.get("leftlight")
    R2 = V and ratio2()
    parts = [(b"".join(x.to_bytes(4, "little") for x in glide_t()), 4), (b"".join(x.to_bytes(4, "little") for x in rel_t()), 4)]
    if ui:
        parts.append((b"".join(x.to_bytes(2, "little") for x in (UI_WAVES_VA if V else UI_WAVES)), 1))
    if V and LL:
        parts.append((b"".join(x.to_bytes(2, "little") for x in VA_ZONES + (0,)), 1))
    if R2:                                                                # (ratio2) the 128 ratios' offsets (1/256 semitone, signed halfwords)
        parts.append((b"".join((r2_word(k) & 0xFFFF).to_bytes(2, "little") for k in range(128)), 1))
    if TBP.on():                                                          # (RH87, tabpack: in the ITCM)
        t_gld = TBP.region("synthpage", parts)
    else:
        for x, _ in parts:
            E(raw, x)
    t_rel = t_gld + 512
    t_wave = t_rel + 512
    t_zone = t_wave + 8
    t_r2 = t_zone + (16 if V and LL else 0)

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
    E(movs_imm, 1, CHK ^ MARK)
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
    E(movs_imm, 1, CHK ^ MARK)
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
    if V:                                                                 # (va) the knob k -> its raw index; c_syvr(r0 = slot, r1 = raw)
        imm32(2, t_map)
        E(ldrb_reg, 1, 2, 1)
        a.label("c_syvr")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(bl, "c_syb")
    E(cmp_imm, 0, 0)
    E(b_cond, "yv_d", "eq")
    E(movs_imm, 1, SL)
    E(muls, 1, 4)
    E(adds_reg, 0, 0, 1)
    if V:
        E(adds_imm8, 0, 3)                                                # r0 = the slot's 16 bytes
        if pclr():                                                        # (RH90) a preset's copy instead (rpatch's, while it asks)
            imm32(2, 0x33f4)
            E(ldr_imm, 2, 2, 0)
            E(cmp_imm, 2, 0)
            E(b_cond, "yv_r", "eq")
            E(mov_reg, 0, 2)
            a.label("yv_r")
        E(cmp_imm, 5, 16)
        E(b_cond, "yv_pk", "hs")
        E(ldrb_reg, 0, 0, 5)
        E(lsls_imm, 0, 0, 25)
        E(lsrs_imm, 0, 0, 25)
        E(pop_list, [4, 5], pc=True)
        a.label("yv_pk")                                                  # raw 16 / 17: bit 7 of bytes 0-6 / 7-13
        E(subs_imm8, 5, 16)
        E(movs_imm, 1, 7)
        E(muls, 1, 5)
        E(adds_reg, 0, 0, 1)
        E(movs_imm, 4, 0)
        E(movs_imm, 2, 0)
        a.label("yv_pl")
        E(ldrb_reg, 3, 0, 2)
        E(lsrs_imm, 3, 3, 7)
        E(lsls_reg, 3, 2)
        E(orrs_reg, 4, 3)
        E(adds_imm8, 2, 1)
        E(cmp_imm, 2, 7)
        E(b_cond, "yv_pl", "lo")
        E(lsls_imm, 5, 5, 6)                                              # env -> morph: XOR 64
        E(eors_reg, 4, 5)
        E(mov_reg, 0, 4)
        E(pop_list, [4, 5], pc=True)
    else:
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
    if V:                                                                 # (va) the knob k -> its raw index; c_sypr(r0 = slot, r1 = raw, r2)
        imm32(3, t_map)
        E(ldrb_reg, 1, 3, 1)
        a.label("c_sypr")
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
    if V:
        E(adds_imm8, 1, 3)                                                # r1 = the slot's 16 bytes
        E(cmp_imm, 5, 16)
        E(b_cond, "yq_pk", "hs")
        E(ldrb_reg, 2, 1, 5)                                              # bit 7 kept
        E(movs_imm, 3, 0x80)
        E(ands_reg, 2, 3)
        E(orrs_reg, 2, 6)
        E(strb_reg, 2, 1, 5)
        E(b, "yq_s")
        a.label("yq_pk")
        E(subs_imm8, 5, 16)
        E(movs_imm, 2, 7)
        E(muls, 2, 5)
        E(adds_reg, 1, 1, 2)
        E(lsls_imm, 5, 5, 6)                                              # env -> morph: XOR 64
        E(eors_reg, 6, 5)
        E(push_list, [0])
        E(movs_imm, 5, 0)
        a.label("yq_pl")
        E(ldrb_reg, 2, 1, 5)
        E(lsls_imm, 2, 2, 25)
        E(lsrs_imm, 2, 2, 25)
        E(mov_reg, 3, 6)
        E(lsrs_reg, 3, 5)
        E(lsls_imm, 3, 3, 31)
        E(lsrs_imm, 3, 3, 24)
        E(orrs_reg, 2, 3)
        E(strb_reg, 2, 1, 5)
        E(adds_imm8, 5, 1)
        E(cmp_imm, 5, 7)
        E(b_cond, "yq_pl", "lo")
        E(pop_list, [0])
        a.label("yq_s")
    else:
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
    if rhbuild.OPT.get("poly"):                                           # (RH72) none free: a poly track's borrowed one (not the first
        E(movs_imm, 6, 0)                                                 # of its track; fmpage's c_plsync turns its FM off)
        a.label("ya_s")
        E(movs_imm, 0, SL)
        E(muls, 0, 6)
        E(adds_reg, 0, 5, 0)
        E(ldrb_imm, 0, 0, 2)
        E(subs_imm8, 0, 1)
        E(bl, "c_syslot")
        E(cmp_reg, 0, 6)
        E(b_cond, "ya_st", "ne")
        E(adds_imm8, 6, 1)
        E(cmp_imm, 6, NSL)
        E(b_cond, "ya_s", "lo")
        E(b, "ya_n")
        a.label("ya_st")
        E(movs_imm, 0, SL)
        E(muls, 0, 6)
        E(adds_reg, 0, 5, 0)
        E(adds_imm8, 0, 2)
        E(b, "ya_g")
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
    SYV = "c_syv"
    if rhbuild.OPT.get("mxsink"):                                         # (RH64) the matrix's offsets
        SYV = "c_sywv"
        a.label("c_sywv")
        E(b_w, "c_syv")
    if rhbuild.OPT.get("vmode"):                                          # (RH80) c_sydt(r0 = slot, r1 = C_OCT) -> r0: esel's b.w c_esdt
        a.label("c_sydt")
        E(mov_reg, 0, 1)
        E(raw, h(0x4770))
    if rhbuild.OPT.get("mx64"):                                           # (RH87) c_syevr: b.w c_syvr, modmx's b.w c_mxsyr
        a.label("c_syevr")
        E(b_w, "c_syvr")
    if rhbuild.OPT.get("vsel"):                                           # (RH80) c_syext(r0 = slot, r1 = e) -> r0: vsel's b.w c_vsext
        a.label("c_syext")
        E(movs_imm, 0, 0)
        E(raw, h(0x4770))
    if pclr():                                                            # (RH90) c_sycd(r0 = slot, r1 = k) -> the default; rpatch's b.w
        a.label("c_sycd")
        E(b_w, "sycd_d")
        a.label("sycd_d")
        imm32(0, t_kdef)
        E(ldrb_reg, 0, 0, 1)
        E(raw, h(0x4770))
    a.label("c_syword")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)

    def val(k, rd=0):
        E(mov_reg, 0, 4)
        E(movs_imm, 1, k)
        E(bl, SYV)
        if rd != 0:
            E(mov_reg, rd, 0)

    def case(i, nxt):
        E(cmp_imm, 5, i)
        E(b_cond, nxt, "ne")

    def val_r1():
        E(mov_reg, 0, 4)
        E(bl, SYV)

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
    if V:                                                                 # (va) C_OCT, C_GLD, C_REL (knob 15), C_EF (raw 14); the
        case(S.C_OCT, "v4")                                               # VA's X words (i >= 16); the others 0
        val(K_OCT)
        E(movs_imm, 1, 7)
        E(muls, 0, 1)
        E(lsrs_imm, 0, 0, 7)
        E(subs_imm8, 0, 3)
        imm32(1, 0xC0000)
        E(muls, 0, 1)
        if rhbuild.OPT.get("vmode"):                                      # (RH80) + the unison's detune (esel patches the stub)
            E(mov_reg, 1, 0)
            E(mov_reg, 0, 4)
            E(bl, "c_sydt")
        E(b, "w_x")
        a.label("v4")
        for i, k, t in ((S.C_GLD, K_GLIDE, t_gld), (S.C_REL, K_LEN, t_rel)):
            nx = f"vt{i}"
            case(i, nx)
            val(k)
            imm32(1, t)
            E(lsls_imm, 0, 0, 2)
            E(adds_reg, 0, 0, 1)
            E(ldr_imm, 0, 0, 0)
            E(b, "w_x")
            a.label(nx)
        case(S.C_EF, "v7")
        E(mov_reg, 0, 4)                                                  # the Envelope page's (raw 14): (v - 64) << 17
        E(movs_imm, 1, 14)
        E(bl, "c_syevr" if rhbuild.OPT.get("mx64") else "c_syvr")        # (RH87: + the matrix's destination 39, modmx's c_mxsyr)
        E(subs_imm8, 0, 64)
        E(lsls_imm, 0, 0, 17)
        E(b, "w_x")
        a.label("v7")
        if rhbuild.OPT.get("vsel"):                                       # (RH80) the envelope -> FM / ring / mix: vsel's
            for i, x in Y_EXT:
                E(cmp_imm, 5, i)
                E(b_cond, f"vy{i}", "ne")
                E(mov_reg, 0, 4)
                E(movs_imm, 1, x)
                E(bl, "c_syext")
                E(b, "w_x")
                a.label(f"vy{i}")
        E(movs_imm, 0, 0)
        E(cmp_imm, 5, 16)
        bc("w_x", "lo")
        E(subs_imm8, 5, 16)                                               # j: (offset, knob, kind) at t_vw + 3 j
        E(movs_imm, 0, 3)
        E(muls, 5, 0)
        imm32(0, t_vw + 1)
        E(adds_reg, 5, 5, 0)
        E(ldrb_imm, 6, 5, 1)                                              # r6 = the kind
        E(cmp_imm, 6, VA_ZERO)
        E(b_cond, "vz", "eq")
        if rhbuild.OPT.get("vsel"):                                       # (RH80) vsel's value (the knob field)
            E(cmp_imm, 6, VA_EXT)
            E(b_cond, "vx", "ne")
            E(ldrb_imm, 1, 5, 0)
            E(mov_reg, 0, 4)
            E(bl, "c_syext")
            E(b, "w_x")
            a.label("vx")
        if R2:                                                            # (ratio2) the ratio's offset + 2 (detune - 64)
            E(cmp_imm, 6, VA_R2F)
            E(b_cond, "vr2", "ne")
            val(12)
            E(subs_imm8, 0, 64)
            E(lsls_imm, 6, 0, 1)
            val(4)
            E(lsls_imm, 0, 0, 1)
            imm32(1, t_r2)
            E(adds_reg, 1, 1, 0)
            E(ldrh_imm, 0, 1, 0)
            E(raw, h(0xB200))                                             # sxth r0, r0
            E(adds_reg, 0, 0, 6)
            E(b, "w_x")
            a.label("vr2")
        E(cmp_imm, 6, VA_MAG)
        E(b_cond, "vm", "eq")
        E(cmp_imm, 6, VA_DUAL)
        E(b_cond, "vd", "eq")
        E(ldrb_imm, 1, 5, 0)
        val_r1()
        E(cmp_imm, 6, VA_PW)
        E(b_cond, "vp", "ne")
        imm32(1, 807)                                                     # (v x 807) >> 10: 0..100
        E(muls, 0, 1)
        E(lsrs_imm, 0, 0, 10)
        E(b, "w_x")
        a.label("vp")
        E(cmp_imm, 6, VA_SEMI)
        E(b_cond, "vs", "ne")
        E(movs_imm, 1, 3)                                                 # ((3 v + 4) >> 3) - 24
        E(muls, 0, 1)
        E(adds_imm8, 0, 4)
        E(lsrs_imm, 0, 0, 3)
        E(subs_imm8, 0, 24)
        E(b, "w_x")
        a.label("vs")
        E(cmp_imm, 6, VA_BIP)
        bc("w_x", "ne")
        E(subs_imm8, 0, 64)
        E(b, "w_x")
        a.label("vz")
        E(movs_imm, 0, 0)
        E(b, "w_x")
        a.label("vm")
        imm32(0, VMAGIC3)
        E(b, "w_x")
        a.label("vd")                                                     # DFLAGS: OSC 2 heard (MIX) or used (FM off the middle, RING, a zone)
        if rhbuild.OPT.get("va2x1"):                                      # (RH85, va2x1) or its slot granted 2x (esel ESR + O_OSENT, bit s)
            import esel as _ES
            imm32(0, _ES.ESR + _ES.O_OSENT)
            E(ldrb_imm, 0, 0, 0)
            E(lsrs_reg, 0, 4)
            E(lsls_imm, 0, 0, 31)
            E(b_cond, "vd1", "ne")
        val(7)
        E(cmp_imm, 0, 0)
        E(b_cond, "vd1", "ne")
        val(K_RING)
        E(cmp_imm, 0, 0)
        E(b_cond, "vd1", "ne")
        val(6)
        E(cmp_imm, 0, 19)
        E(b_cond, "vd1", "hs")
        val(5)
        E(cmp_imm, 0, 64)
        E(b_cond, "vd1", "ne")
        if dualext():                                                     # (RH85) or OSC 1's envelope -> FM, or -> mix upwards (vsel's 2 / 4;
            E(mov_reg, 0, 4)                                              # -> ring needs RING > 0, -> mix down from 0 changes nothing)
            E(movs_imm, 1, 2)
            E(bl, "c_syext")
            E(cmp_imm, 0, 0)
            E(b_cond, "vd1", "ne")
            E(mov_reg, 0, 4)
            E(movs_imm, 1, 4)
            E(bl, "c_syext")
            E(cmp_imm, 0, 0)
            E(b_cond, "vd1", "gt")
        E(movs_imm, 0, 0)
        E(b, "w_x")
        a.label("vd1")
        E(movs_imm, 0, VA_DUALW)
    else:
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
    if V:                                                                 # (va) i >= 16: X:va0.XB0 + XS slot + its offset
        E(cmp_imm, 5, 16)
        E(b_cond, "yw_y", "lo")
        E(subs_imm8, 5, 16)
        E(movs_imm, 1, 3)
        E(muls, 5, 1)
        imm32(1, t_vw)
        E(ldrb_reg, 5, 1, 5)
        E(movs_imm, 1, VA_XS)
        E(muls, 1, 4)
        E(adds_reg, 1, 1, 5)
        E(movw, 2, VA_XB0)
        E(adds_reg, 1, 1, 2)
        E(b, "yw_w")
        a.label("yw_y")
    E(lsls_imm, 1, 4, 6)
    E(adds_reg, 1, 1, 5)
    E(movw, 2, 0x8000 | S.Y0)
    E(adds_reg, 1, 1, 2)
    a.label("yw_w")
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
    if pclr():                                                            # (RH90) Clear + the knob: the preset's, else the default
        E(mov_reg, 0, 6)
        E(mov_reg, 1, 5)
        E(bl, "c_sycd")
        E(mov_reg, 2, 0)
    else:
        imm32(0, t_kdef)                                                  # Clear + the knob: its default
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
    E(cmp_imm, 7, len(ORDER_VA) if V else NV)
    E(b_cond, "ll_wa", "lo")
    E(b, "ll_m")
    a.label("ll_rd")
    for _ in range(2):                                                    # else two words a frame in turn
        E(ldrb_imm, 6, 4, R_ROUND)
        E(lsrs_imm, 0, 6, 6 if V else 4)                                  # (va) 64 a slot
        E(movs_imm, 1, 63 if V else 15)
        E(ands_reg, 1, 6)
        imm32(2, t_order)
        E(ldrb_reg, 1, 2, 1)
        E(bl, "c_sywr")
        E(adds_imm8, 6, 1)
        E(movs_imm, 0, 255 if V else 4 * NV - 1)
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
        if ui and V and k in (0, 2):                                      # (va) K1 / K3: the morph's nearest wave ((v + 21) / 42)
            E(cmp_imm, 2, 3)
            E(b_cond, f"lb_{k}", "ne")
            E(adds_imm8, 0, 21)
            imm32(2, 1561)
            E(muls, 0, 2)
            E(lsrs_imm, 0, 0, 16)
            E(lsls_imm, 0, 0, 1)
            imm32(2, t_wave)
            E(adds_reg, 2, 2, 0)
            E(ldrh_imm, 3, 2, 0)
            E(movs_imm, 0, 127)
            if LL:
                E(movs_imm, 2, 0)
            E(b, f"lu_{k}")
            a.label(f"lb_{k}")
        if ui and V and LL and k == 6:                                    # (va, leftlight) K7: its zone's colour, the position
            E(cmp_imm, 2, 4)
            E(b_cond, f"lz_{k}", "ne")
            E(movs_imm, 2, 7)
            E(muls, 0, 2)
            E(lsrs_imm, 2, 0, 7)                                          # r2 = the zone
            E(lsls_imm, 2, 2, 1)
            imm32(3, t_zone)
            E(adds_reg, 3, 3, 2)
            E(ldrh_imm, 3, 3, 0)
            E(lsls_imm, 0, 0, 25)                                         # the position x 13 / 16 + 24
            E(lsrs_imm, 0, 0, 25)
            E(movs_imm, 2, 13)
            E(muls, 0, 2)
            E(lsrs_imm, 0, 0, 4)
            E(adds_imm8, 0, 24)
            E(movs_imm, 2, 0)
            E(b, f"lu_{k}")
            a.label(f"lz_{k}")
        if ui and not V and k < 2:                                        # (ui) K1 / K2: the wave's colour; with Shift, K2: sync, a toggle
            E(cmp_imm, 2, 3)
            E(b_cond, f"lt_{k}", "ne")
            E(lsrs_imm, 0, 0, 5)
            E(lsls_imm, 0, 0, 1)
            imm32(2, t_wave)
            E(adds_reg, 2, 2, 0)
            E(ldrh_imm, 3, 2, 0)
            E(movs_imm, 0, 127)
            if LL:
                E(movs_imm, 2, 0)
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
                if LL:
                    E(movs_imm, 2, 0)
                E(b, f"lu_{k}")
                a.label(f"lb_{k}")
        if LL:
            E(movs_imm, 2, 0)
        E(subs_imm8, 0, 64)                                               # from the middle: |v - 64| x 2
        E(b_cond, f"lq_{k}", "ge")
        E(raw, h(0x4240))                                                 # rsbs r0, r0, #0
        if LL:                                                            # (leftlight) left: the lighter shade
            E(movw, 2, KB_LEFT)
        a.label(f"lq_{k}")
        E(lsls_imm, 0, 0, 1)
        E(cmp_imm, 0, 127)
        E(b_cond, f"lu_{k}", "le")
        E(movs_imm, 0, 127)
        a.label(f"lu_{k}")
        E(strb_imm, 0, 7, K_VAL + k)
        if ui and LL:
            E(mov_reg, 1, 3)
            E(orrs_reg, 1, 2)
            E(strh_imm, 1, 7, K_CODE + 2 * k)
            E(strh_w_imm, 3, 5, 2 * (LED_KNOB0 + k))
        elif ui:
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
    report["synthpage"] = dict(prev={k: hex(v) for k, v in prev.items()}, tables=hex(base_addr), **({"va": True} if va() else {}), **({"ui": True} if ui else {}), **({"menu2": True} if menu2 else {}), **({"env": True} if env else {}), **({"spall": True} if spall else {}),
                               labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    if noblink:
        report["synthpage"]["noblink"] = True
    return labels, code_
