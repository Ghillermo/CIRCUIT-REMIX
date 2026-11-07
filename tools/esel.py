"""The engines in Sample mode and the synth's voice modes (MIT; RH80; the user, 2026-11-07: «Quiero añadir los selectores de motor en row 3
de Hacks a la vista sample mode … En los menús de pista, sólo vistas, no modos»; docs/DISENO_RH80.md).

Sample mode (Samples twice) on the selected track t, Shift not held, the FM page closed; our heads in front of every other one:
  * closed (as RH79, less the mode pads): the stock's pads, pad 8 = the selector (the engine's colour, dim), the sample's shortcuts 9 / 10
    (stfit), 14 (the link), 19 (the de-clicker); pads 5-7, 11-13, 15, 16 (RH58-RH79's modes) dark and swallowed;
  * open (a tap on pad 8; pad 8 again, or leaving Sample mode, closes it; picking an engine keeps it open): rows 1-3 ours, row 4 the stock's
    (25-28 the play modes, 29-30) but the slices' 31 / 32 (dark); pads 17-24 = the engines (Hacks' Beta 5.29 row, the sampler's place
    taken by the line input): 17 sample (cyan), 18 the input alone (white: the line input without its gate), 19 the input -> VCA / VCF / FX
    (amber: with its gate), 20 VA (mint), 21 VA-drum and 22 wavetable (dark: not on the Rhythm yet), 23 granular (lilac), 24 FM (lavender);
    the track's bright, the others dim.  Each plays the old pads (smodes 5-8 / 16 through the chain, fmpage's c_fmset), so the exclusions,
    the project's blocks and the DSP words stay the modules' own.  Each engine's options in its column: 18 -> pad 2, 19 -> pad 3 = the
    input's source (smodes' pad 15); pad 8 = close (the engine's colour, bright); pad 14 = the link; pad 16 = the voice (VA / FM only).
    Pad 24 on FM already: a tap = the FM page (fm8page's pad 12 tap); held (HOLD) = the 24 instruments on rows 1, 2 and 4 (their family's
    colour, the loaded one bright; a press loads it);
  * pad 16 (VA / FM): a tap = poly on / off (back to the last mono mode); held (HOLD) = Hacks' voice modes on pads 17-24 (retrigger green,
    legato yellow, glide teal, uni retrig green, uni legato yellow, uni glide teal, uni always-glide violet, poly magenta; the track's bright;
    pad 16 itself in the mode's colour), K1 = glide (teal: synthpage's), K2 = the unison's detune (blue: 0 .. +-50 cents at the ends);
    Clear + knob = 0.
The voice modes on core 0 (tools/vmode0.py): X:VMF + t the flags, X:UG + t the unison's gain, the key; a track never set = flags 0 (the old
way: RH79's sound).  Poly and unison borrow the free slots through fmpage's c_plon (unison: PF 0 (fmpage OPT vmode), each slot's C_OCT
detuned by c_esdt through synthpage's stub c_sydt).  The modes and the detune travel with the project in projsnd's record (OPT vm).
RAM: ESR (after fm8page's FMR, under dspz's staging buffer): + 0 open, + 1 pad 16 (1 pressed, 2 held), + 2 pad 24 (1 / 2), + 3 FM before
pad 24, + 4 the press's tick, + 8 the modes (8; 0 = never set, else mode + 1), + 16 the detunes (8), + 24 the last mono modes (8, + 1),
+ 32 the unison tracks (bit), + 33 the key sent, + 34 the round, + 40 the signatures sent (8), + 48 the detunes sent (8), + 56 the pads
swallowed (bit), + 64 MAG.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, ands_reg, b, b_cond, b_w, bics_reg, bl, cmp_imm, cmp_reg, h, ldr_imm, ldr_sp, ldrb_imm,  # noqa: E402
                   ldrb_reg, lsls_imm, lsls_reg, lsrs_imm, lsrs_reg, mov_reg, movs_imm, movt, movw, muls, orrs_reg, pop_list, push_list,
                   raw, str_imm, strb_imm, strh_imm, strh_w_imm, subs_imm8, subs_reg, tst_reg, ldrb_w, strb_w)
import countin as CI  # noqa: E402
import cthresh as TH  # noqa: E402
import granpage as GP  # noqa: E402
import rhstate  # noqa: E402
import smodes as SM  # noqa: E402
import stockplus as SP  # noqa: E402
import synthpage as SY  # noqa: E402
import vmode0 as VM  # noqa: E402

ESR, ESR_LEN = 0x2004EB80, 112                      # (+ 72..111: tools/vsel.py's values)
MAG = 0x4C455345                                       # "ESEL"
(O_OPEN, O_H16, O_H24, O_WASFM, O_TICK, O_MODE, O_DET, O_MONO, O_UNI, O_KEYED, O_RR, O_SENT, O_DSENT, O_SWAL, O_MAG) = (
    0, 1, 2, 3, 4, 8, 16, 24, 32, 33, 34, 40, 48, 56, 64)
HOLD = 500
E_SAMPLE, E_IN, E_INV, E_VA, E_VD, E_WT, E_GR, E_FM = range(8)
P_SRC_IN, P_SRC_INV, P_SEL, P_LINK, P_VOICE, P_ENG0, P_FMPAGE = 1, 2, 7, 13, 15, 16, 11
HIDE_CLOSED = (4, 5, 6, 10, 11, 12, 14, 15)            # RH58-RH79's mode pads (smodes 5-7, 15, 16; fmpage 11-13)
COL_E = ((0xC0, 0xCE), (0x01, 0x09), (0x2B, 0x2C), (0x4F, 0x50), (0, 0), (0, 0), (0x60, 0x61), (0x47, 0x48))
COL_M = ((0xBE, 0xCC), (0xBC, 0xCA), (0x4B, 0x4E), (0xBE, 0xCC), (0xBC, 0xCA), (0x4B, 0x4E), (0xC2, 0xD0), (0xC3, 0xD1))
COL_GLIDE, COL_DET = 0x4B, 0xC1
M_POLY = 7
DET_UNITS = 258                                        # (50 cents for the knob at 127: $10000 / 100 x 50 / 127)
NSL = 4


def model_engine(snd, line_byte, fm):
    """the engine index of a track (the tests')"""
    if snd == SY.SND_SAMPLE:
        return E_SAMPLE
    if snd == SY.SND_GRAN:
        return E_GR
    if snd == SY.SND_LINE:
        return E_INV if line_byte >> 4 & 1 else E_IN
    return E_FM if fm else E_VA


def model_detune(det, k, n):
    """the C_OCT offset of the k-th (by slot) of a unison track's n slots (the ARM's sdiv: towards zero)"""
    if n < 2:
        return 0
    x = det * DET_UNITS * (2 * k - (n - 1))
    q = abs(x) // (n - 1)
    return q if x >= 0 else -q


def inst_cols():
    import fm8inst as I
    import fm8page as F8
    import fmpage as FP
    return [FP.ST_FAM[F8.FAM[x["fam"]]] for x in I.INST]


def inst_pad(i):
    """instrument i (0-23) -> its pad (rows 1, 2 and 4)"""
    return i if i < 16 else i + 8


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

    def sdiv(rd, rn, rm): return h(0xFB90 | rn) + h(0xF0F0 | rd << 8 | rm)

    # ---- the tables (at the start)
    data = bytearray()
    T = {}

    def put(name, bs):
        while len(data) % 4:
            data.append(0)
        T[name] = base + len(data)
        data.extend(bs)
    put("ce", bytes(x for p in COL_E for x in p))
    put("cm", bytes(x for p in COL_M for x in p))
    put("fl", bytes(m[0] for m in VM.MODES))                              # each mode's flags
    put("un", bytes(m[1] | m[2] << 1 for m in VM.MODES))                  # bit 0 unison, bit 1 poly
    put("ic", bytes(x for p in inst_cols() for x in p))
    put("ug", b"".join(VM.UNI_GAIN[n].to_bytes(4, "little") for n in range(1, 5)))
    while len(data) % 4:
        data.append(0)
    E(raw, bytes(data))

    # ---- c_esram() -> r0 = our RAM (from zero once: MAG); clobbers r1-r3
    a.label("c_esram")
    imm32(0, ESR)
    E(ldr_imm, 1, 0, O_MAG)
    imm32(2, MAG)
    E(cmp_reg, 1, 2)
    E(b_cond, "er_x", "eq")
    E(movs_imm, 1, 0)
    E(movs_imm, 3, ESR_LEN)
    a.label("er_z")
    E(subs_imm8, 3, 4)
    E(raw, h(0x50C1))                                                     # str r1, [r0, r3]
    E(b_cond, "er_z", "ne")
    E(str_imm, 2, 0, O_MAG)
    a.label("er_x")
    E(raw, h(0x4770))                                                     # bx lr

    # ---- c_esslots(r0 = track) -> r0 = how many slots it has; clobbers r1-r3
    a.label("c_esslots")
    E(push_list, [4, 5], lr=True)
    E(adds_imm8, 0, 1)
    E(mov_reg, 4, 0)
    E(bl, L["c_syb"])
    E(movs_imm, 5, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "sl_x", "eq")
    E(movs_imm, 1, 0)
    a.label("sl_l")
    E(ldrb_imm, 2, 0, 2)
    E(cmp_reg, 2, 4)
    E(b_cond, "sl_n", "ne")
    E(adds_imm8, 5, 1)
    a.label("sl_n")
    E(adds_imm8, 0, SY.SL)
    E(adds_imm8, 1, 1)
    E(cmp_imm, 1, NSL)
    E(b_cond, "sl_l", "lo")
    a.label("sl_x")
    E(mov_reg, 0, 5)
    E(pop_list, [4, 5], pc=True)

    # ---- c_eseng(r0 = track) -> r0 = its engine (E_*); clobbers r1-r3
    a.label("c_eseng")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, L["c_sysnd"])
    E(cmp_imm, 0, SY.SND_GRAN)
    E(b_cond, "ee_1", "ne")
    E(movs_imm, 0, E_GR)
    E(pop_list, [4], pc=True)
    a.label("ee_1")
    E(cmp_imm, 0, SY.SND_LINE)
    E(b_cond, "ee_2", "ne")
    E(mov_reg, 0, 4)
    E(bl, L["c_smline"])
    E(lsrs_imm, 0, 0, SM.GATE_BIT)
    E(movs_imm, 1, 1)
    E(ands_reg, 0, 1)
    E(adds_imm8, 0, E_IN)
    E(pop_list, [4], pc=True)
    a.label("ee_2")
    E(cmp_imm, 0, SY.SND_SYNTH)
    E(b_cond, "ee_s", "eq")
    E(movs_imm, 0, E_SAMPLE)
    E(pop_list, [4], pc=True)
    a.label("ee_s")
    E(mov_reg, 0, 4)
    E(bl, L["c_syslot"])
    E(bl, L["c_fmon"])
    E(movs_imm, 1, E_VA)
    E(cmp_imm, 0, 0)
    E(b_cond, "ee_v", "eq")
    E(movs_imm, 1, E_FM)
    a.label("ee_v")
    E(mov_reg, 0, 1)
    E(pop_list, [4], pc=True)

    # ---- c_esmode(r0 = track) -> r0 = its mode 0-7 (never set: poly when poly, else retrigger); clobbers r1-r3
    a.label("c_esmode")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_esram")
    E(adds_reg, 0, 0, 4)
    E(ldrb_imm, 0, 0, O_MODE)
    E(cmp_imm, 0, 0)
    E(b_cond, "em_n", "eq")
    E(subs_imm8, 0, 1)
    E(pop_list, [4], pc=True)
    a.label("em_n")
    E(mov_reg, 0, 4)
    E(bl, L["c_plis"])
    E(cmp_imm, 0, 0)
    E(b_cond, "em_x", "eq")
    E(movs_imm, 0, M_POLY)
    a.label("em_x")
    E(pop_list, [4], pc=True)

    # ---- c_esset(r0 = track, r1 = mode 0-7, or 0xFF = never set): stored; poly / unison borrow the free slots, the others give them
    # back; its words again; clobbers r0-r3
    a.label("c_esset")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(bl, "c_esram")
    E(mov_reg, 6, 0)
    E(adds_reg, 1, 6, 4)
    E(adds_imm8, 5, 1)
    E(movs_imm, 0, 0xFF)
    E(ands_reg, 5, 0)                                                     # (0xFF + 1 = 0: never set)
    E(strb_imm, 5, 1, O_MODE)
    E(movs_imm, 2, 0)                                                     # r2 = bit 0 unison, bit 1 poly
    E(cmp_imm, 5, 0)
    E(b_cond, "es_t", "eq")
    E(cmp_imm, 5, M_POLY + 1)
    E(b_cond, "es_m", "eq")
    E(strb_imm, 5, 1, O_MONO)                                             # the last mono mode (+ 1; poly's tap goes back to it)
    a.label("es_m")
    imm32(0, T["un"] - 1)
    E(ldrb_reg, 2, 0, 5)
    a.label("es_t")
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(ldrb_w, 3, 6, O_UNI)
    E(bics_reg, 3, 1)
    E(lsrs_imm, 0, 2, 1)
    E(b_cond, "es_u", "cc")
    E(orrs_reg, 3, 1)
    a.label("es_u")
    E(strb_w, 3, 6, O_UNI)
    E(push_list, [2])
    E(mov_reg, 0, 4)
    E(bl, L["c_plis"])
    E(pop_list, [2])
    E(cmp_imm, 2, 0)
    E(b_cond, "es_o", "eq")
    E(cmp_imm, 0, 0)                                                      # poly / unison: the free slots
    E(b_cond, "es_s", "ne")
    E(mov_reg, 0, 4)
    E(bl, L["c_plon"])
    E(b, "es_s")
    a.label("es_o")
    E(cmp_imm, 0, 0)                                                      # mono: given back
    E(b_cond, "es_s", "eq")
    E(mov_reg, 0, 4)
    E(bl, L["c_ploff"])
    a.label("es_s")
    E(movs_imm, 0, 0xFF)                                                  # its words again
    E(adds_reg, 1, 6, 4)
    E(strb_w, 0, 1, O_SENT)
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_esdt(r0 = slot, r1 = its C_OCT word) -> r0 = the word + its unison detune (synthpage's stub c_sydt); clobbers r1-r3
    a.label("c_esdt")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 7, 1)                                                      # r7 = the word
    E(mov_reg, 4, 0)                                                      # r4 = the slot
    E(bl, "c_esram")
    E(mov_reg, 6, 0)                                                      # r6 = our RAM
    E(bl, L["c_syb"])
    E(cmp_imm, 0, 0)
    bc("dt_x", "eq")
    E(movs_imm, 1, SY.SL)
    E(muls, 1, 4)
    E(adds_reg, 1, 0, 1)
    E(ldrb_imm, 5, 1, 2)                                                  # r5 = its track + 1
    E(cmp_imm, 5, 0)
    bc("dt_x", "eq")
    E(subs_imm8, 5, 1)
    E(ldrb_w, 1, 6, O_UNI)
    E(lsrs_reg, 1, 5)
    E(lsrs_imm, 1, 1, 1)
    bc("dt_x", "lo")                                                      # not unison
    E(adds_imm8, 5, 1)
    E(movs_imm, 2, 0)                                                     # r2 = n, r3 = k (the slots of the track below this one)
    E(movs_imm, 3, 0)
    E(movs_imm, 1, 0)
    a.label("dt_l")
    E(push_list, [1])
    E(ldrb_imm, 1, 0, 2)
    E(cmp_reg, 1, 5)
    E(pop_list, [1])
    E(b_cond, "dt_n", "ne")
    E(adds_imm8, 2, 1)
    E(cmp_reg, 1, 4)
    E(b_cond, "dt_n", "hs")
    E(adds_imm8, 3, 1)
    a.label("dt_n")
    E(adds_imm8, 0, SY.SL)
    E(adds_imm8, 1, 1)
    E(cmp_imm, 1, NSL)
    E(b_cond, "dt_l", "lo")
    E(subs_imm8, 2, 1)                                                    # r2 = n - 1
    E(cmp_imm, 2, 0)
    bc("dt_x", "le")
    E(lsls_imm, 3, 3, 1)
    E(subs_reg, 3, 3, 2)                                                  # 2k - (n - 1)
    E(subs_imm8, 5, 1)
    E(adds_reg, 0, 6, 5)
    E(ldrb_imm, 0, 0, O_DET)
    E(movw, 1, DET_UNITS)
    E(muls, 0, 1)
    E(muls, 0, 3)
    E(raw, sdiv(0, 0, 2))
    E(adds_reg, 7, 7, 0)
    a.label("dt_x")
    E(mov_reg, 0, 7)
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_estrk() -> r0 = the selected track in Sample mode, ours to take (no Shift, the FM page closed), else 8; clobbers r1-r3
    a.label("c_estrk")
    E(push_list, [4], lr=True)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "et_8", "eq")
    E(bl, L["c_smview"])
    E(cmp_imm, 0, 8)
    E(b_cond, "et_x", "hs")
    E(mov_reg, 4, 0)
    E(bl, L["c_spshift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "et_8", "ne")
    E(bl, L["c_f8page"])
    E(cmp_imm, 0, NSL)
    E(b_cond, "et_8", "lo")
    E(mov_reg, 0, 4)
    E(pop_list, [4], pc=True)
    a.label("et_8")
    E(movs_imm, 0, 8)
    a.label("et_x")
    E(pop_list, [4], pc=True)

    # ---- c_esplay(r0 = ctrl, r1 = pad): that pad pressed and let go through the chain after ours; clobbers r0-r3
    a.label("c_esplay")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(movs_imm, 2, 100)
    E(bl, prev["pad"])
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, prev["rel"])
    E(pop_list, [4, 5], pc=True)

    # ---- c_esswal(r0 = pad): its release swallowed; clobbers r0-r3
    a.label("c_esswal")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_esram")
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(ldr_imm, 2, 0, O_SWAL)
    E(orrs_reg, 2, 1)
    E(str_imm, 2, 0, O_SWAL)
    E(pop_list, [4], pc=True)

    # ---- c_estick(r0 = our RAM): the press's tick = now; clobbers r1
    a.label("c_estick")
    imm32(1, CI.HAL_TICK)
    E(ldr_imm, 1, 1, 0)
    E(str_imm, 1, 0, O_TICK)
    E(raw, h(0x4770))

    # ---- c_espad (the controller's pad press, ours first: r0 = ctrl, r1 = pad, r2 = velocity)
    a.label("c_espad")
    E(cmp_imm, 1, 32)
    bc("pd_p", "hs")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)                                                      # r5 = the pad
    E(bl, "c_estrk")
    E(cmp_imm, 0, 8)
    bc("pd_q", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the track
    E(bl, "c_esram")
    E(mov_reg, 7, 0)                                                      # r7 = our RAM
    E(mov_reg, 0, 4)
    E(bl, "c_eseng")
    E(mov_reg, 6, 0)                                                      # r6 = its engine
    # pad 16 held: the voice modes on 17-24
    E(ldrb_imm, 0, 7, O_H16)
    E(cmp_imm, 0, 2)
    E(b_cond, "pd_1", "ne")
    E(subs_imm8, 5, P_ENG0)
    E(cmp_imm, 5, 8)
    E(b_cond, "pd_1r", "hs")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, "c_esset")
    a.label("pd_1r")
    E(adds_imm8, 5, P_ENG0)
    E(b, "pd_w")
    a.label("pd_1")
    # pad 24 held: the instruments on rows 1, 2, 4
    E(ldrb_imm, 0, 7, O_H24)
    E(cmp_imm, 0, 2)
    E(b_cond, "pd_2", "ne")
    E(mov_reg, 1, 5)
    E(cmp_imm, 1, 16)
    E(b_cond, "pd_2i", "lo")
    E(subs_imm8, 1, 8)
    E(cmp_imm, 1, 16)
    bc("pd_w", "lo")                                                      # (row 3: nothing)
    a.label("pd_2i")
    E(push_list, [1])
    E(mov_reg, 0, 4)
    E(bl, L["c_syslot"])
    E(pop_list, [1])
    E(cmp_imm, 0, NSL)
    bc("pd_w", "hs")
    E(bl, L["c_f8load"])
    E(b, "pd_w")
    a.label("pd_2")
    E(cmp_imm, 5, P_SEL)                                                  # pad 8: open / close
    E(b_cond, "pd_3", "ne")
    E(ldrb_imm, 0, 7, O_OPEN)
    E(movs_imm, 1, 1)
    E(raw, h(0x4048))                                                     # eors r0, r1
    E(strb_imm, 0, 7, O_OPEN)
    E(b, "pd_w")
    a.label("pd_3")
    E(ldrb_imm, 0, 7, O_OPEN)
    E(cmp_imm, 0, 0)
    E(b_cond, "pd_open", "ne")
    for p in HIDE_CLOSED:                                                 # closed: the old mode pads dark
        E(cmp_imm, 5, p)
        bc("pd_w", "eq")
    E(b, "pd_q")
    a.label("pd_open")
    E(cmp_imm, 5, P_LINK)
    bc("pd_q", "eq")                                                      # the link: smodes'
    E(cmp_imm, 5, 24)
    E(b_cond, "pd_lo", "lo")
    E(cmp_imm, 5, 30)
    bc("pd_w", "hs")                                                      # 31 / 32: the slices, hidden
    E(b, "pd_q")                                                      # 25-30: the stock's
    a.label("pd_lo")
    E(cmp_imm, 5, P_VOICE)                                                # pad 16: the voice (VA / FM)
    E(b_cond, "pd_4", "ne")
    E(cmp_imm, 6, E_VA)
    E(b_cond, "pd_v", "eq")
    E(cmp_imm, 6, E_FM)
    bc("pd_w", "ne")
    a.label("pd_v")
    E(movs_imm, 0, 1)
    E(strb_imm, 0, 7, O_H16)
    E(mov_reg, 0, 7)
    E(bl, "c_estick")
    E(b, "pd_w")
    a.label("pd_4")
    for pad, eng in ((P_SRC_IN, E_IN), (P_SRC_INV, E_INV)):                # the input's source in its engine's column
        E(cmp_imm, 5, pad)
        E(b_cond, f"pd_s{pad}", "ne")
        E(cmp_imm, 6, eng)
        bc("pd_w", "ne")
        E(ldr_sp, 0, 0)
        E(movs_imm, 1, SM.P_SRC)
        E(bl, "c_esplay")
        E(b, "pd_w")
        a.label(f"pd_s{pad}")
    E(cmp_imm, 5, P_ENG0)
    bc("pd_w", "lo")                                                      # rows 1-2: hidden
    # the engines
    E(subs_imm8, 5, P_ENG0)                                               # r5 = the engine picked
    E(mov_reg, 0, 4)
    E(bl, L["c_sysnd"])
    E(mov_reg, 1, 0)                                                      # r1 = its sound
    E(cmp_imm, 5, E_SAMPLE)
    E(b_cond, "pg_1", "ne")
    E(cmp_imm, 1, SY.SND_SAMPLE)
    bc("pg_w", "eq")
    E(movs_imm, 1, SM.P_SAMPLE)
    E(b, "pg_play")
    a.label("pg_1")
    E(cmp_imm, 5, E_GR)
    E(b_cond, "pg_2", "ne")
    E(cmp_imm, 1, SY.SND_GRAN)
    bc("pg_w", "eq")
    E(movs_imm, 1, SM.P_GRAN)
    E(b, "pg_play")
    a.label("pg_2")
    E(cmp_imm, 5, E_IN)
    E(b_cond, "pg_3", "eq")
    E(cmp_imm, 5, E_INV)
    E(b_cond, "pg_3", "eq")
    E(cmp_imm, 5, E_VA)
    E(b_cond, "pg_4", "eq")
    E(cmp_imm, 5, E_FM)
    E(b_cond, "pg_4", "eq")
    E(b, "pg_w")                                                      # VA-drum, wavetable: not yet
    a.label("pg_3")                                                       # the input: its sound, then its gate as the pad wants it
    E(cmp_imm, 1, SY.SND_LINE)
    E(b_cond, "pg_3g", "eq")
    E(ldr_sp, 0, 0)
    E(movs_imm, 1, SM.P_LINE)
    E(bl, "c_esplay")
    a.label("pg_3g")
    E(mov_reg, 0, 4)
    E(bl, L["c_smline"])
    E(lsrs_imm, 0, 0, SM.GATE_BIT)
    E(movs_imm, 1, 1)
    E(ands_reg, 0, 1)
    E(mov_reg, 1, 5)
    E(subs_imm8, 1, E_IN)                                                 # (the gate the pad wants: 18 off, 19 on)
    E(cmp_reg, 0, 1)
    bc("pg_w", "eq")
    E(movs_imm, 1, SM.P_GATE)
    E(b, "pg_play")
    a.label("pg_4")                                                       # VA / FM: the synth, then the FM on / off
    E(movs_imm, 0, 0)
    E(cmp_imm, 6, E_FM)
    E(b_cond, "pg_4f", "ne")
    E(movs_imm, 0, 1)
    a.label("pg_4f")
    E(strb_imm, 0, 7, O_WASFM)
    E(cmp_imm, 1, SY.SND_SYNTH)
    E(b_cond, "pg_4s", "eq")
    E(ldr_sp, 0, 0)
    E(movs_imm, 1, SM.P_SYNTH)
    E(bl, "c_esplay")
    a.label("pg_4s")
    E(mov_reg, 0, 4)
    E(bl, L["c_syslot"])
    E(cmp_imm, 0, NSL)
    bc("pg_w", "hs")
    E(movs_imm, 1, 1)
    E(cmp_imm, 5, E_FM)
    E(b_cond, "pg_4o", "eq")
    E(movs_imm, 1, 0)
    a.label("pg_4o")
    E(push_list, [0, 1])
    E(bl, L["c_fmon"])
    E(pop_list, [2, 3])
    E(cmp_reg, 0, 3)
    E(b_cond, "pg_4h", "eq")
    E(mov_reg, 0, 2)
    E(mov_reg, 1, 3)
    E(bl, L["c_fmset"])
    a.label("pg_4h")
    E(cmp_imm, 5, E_FM)                                                   # FM: its tap / hold
    bc("pg_w", "ne")
    E(movs_imm, 0, 1)
    E(strb_imm, 0, 7, O_H24)
    E(mov_reg, 0, 7)
    E(bl, "c_estick")
    E(b, "pg_w")
    a.label("pg_play")
    E(ldr_sp, 0, 0)
    E(bl, "c_esplay")
    a.label("pg_w")
    E(adds_imm8, 5, P_ENG0)
    a.label("pd_w")
    E(mov_reg, 0, 5)
    E(bl, "c_esswal")
    E(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)
    a.label("pd_q")
    E(raw, GP.popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    a.label("pd_p")
    E(b_w, prev["pad"])

    # ---- c_esrel (the controller's pad release, ours first: r0 = ctrl, r1 = pad): pad 16's tap = poly on / off; pad 24's tap on FM = the
    # FM page; a pad we took, swallowed
    a.label("c_esrel")
    E(cmp_imm, 1, 32)
    bc("rl_p", "hs")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)
    E(bl, "c_esram")
    E(mov_reg, 7, 0)
    E(cmp_imm, 5, P_VOICE)
    E(b_cond, "rl_1", "ne")
    E(ldrb_imm, 6, 7, O_H16)
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 7, O_H16)
    E(cmp_imm, 6, 1)
    E(b_cond, "rl_s", "ne")
    E(bl, L["c_smview"])                                                  # a tap: poly on, or back to the last mono mode
    E(cmp_imm, 0, 8)
    E(b_cond, "rl_s", "hs")
    E(mov_reg, 4, 0)
    E(bl, "c_esmode")
    E(movs_imm, 1, M_POLY)
    E(cmp_imm, 0, M_POLY)
    E(b_cond, "rl_t", "ne")
    E(adds_reg, 1, 7, 4)
    E(ldrb_imm, 1, 1, O_MONO)
    E(subs_imm8, 1, 1)                                                    # (0 - 1 = 0xFF: never set)
    E(movs_imm, 0, 0xFF)
    E(ands_reg, 1, 0)
    a.label("rl_t")
    E(mov_reg, 0, 4)
    E(bl, "c_esset")
    E(b, "rl_s")
    a.label("rl_1")
    E(cmp_imm, 5, P_ENG0 + E_FM)
    E(b_cond, "rl_s", "ne")
    E(ldrb_imm, 6, 7, O_H24)
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 7, O_H24)
    E(cmp_imm, 6, 1)
    E(b_cond, "rl_s", "ne")
    E(ldrb_imm, 0, 7, O_WASFM)
    E(cmp_imm, 0, 0)
    E(b_cond, "rl_s", "eq")
    E(ldr_sp, 0, 0)                                                       # a tap on FM already: fm8page's pad 12 tap = its page
    E(movs_imm, 1, P_FMPAGE)
    E(bl, "c_esplay")
    a.label("rl_s")
    E(ldr_imm, 2, 7, O_SWAL)
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 5)
    E(tst_reg, 2, 1)
    E(b_cond, "rl_q", "eq")
    E(bics_reg, 2, 1)
    E(str_imm, 2, 7, O_SWAL)
    E(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)
    a.label("rl_q")
    E(raw, GP.popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    a.label("rl_p")
    E(b_w, prev["rel"])

    # ---- c_esknob (the container's knob slot, ours first: r0 = ?, r1 = knob, r2 = delta): pad 16 held: K1 glide, K2 the detune
    a.label("c_esknob")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(cmp_imm, 1, 8)
    bc("kn_q", "hs")
    E(bl, "c_esram")
    E(mov_reg, 7, 0)
    E(ldrb_imm, 0, 7, O_H16)
    E(cmp_imm, 0, 2)
    bc("kn_q", "ne")
    E(bl, "c_estrk")
    E(cmp_imm, 0, 8)
    bc("kn_q", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the track
    E(ldr_sp, 5, 4)                                                       # r5 = k
    E(cmp_imm, 5, 2)
    bc("kn_x", "hs")                                                      # K3-K8: nothing
    E(bl, L["c_spheld"])
    E(movs_imm, 6, 1)                                                     # r6 = 0: Clear held (movs before the shift: the flags)
    E(lsls_imm, 0, 0, 31 - SP.BIT_CLEAR)
    E(b_cond, "kn_v", "pl")
    E(movs_imm, 6, 0)
    a.label("kn_v")
    E(cmp_imm, 5, 0)
    E(b_cond, "kn_d", "ne")
    E(mov_reg, 0, 4)                                                      # K1: the glide (synthpage's)
    E(bl, L["c_syslot"])
    E(cmp_imm, 0, NSL)
    bc("kn_x", "hs")
    E(mov_reg, 5, 0)
    E(movs_imm, 1, SY.K_GLIDE)
    E(bl, L["c_syv"])
    E(bl, "kn_add")
    E(mov_reg, 2, 0)
    E(mov_reg, 0, 5)
    E(movs_imm, 1, SY.K_GLIDE)
    E(bl, L["c_syp"])
    E(b, "kn_x")
    a.label("kn_d")                                                       # K2: the detune
    E(adds_reg, 5, 7, 4)
    E(ldrb_imm, 0, 5, O_DET)
    E(bl, "kn_add")
    E(strb_imm, 0, 5, O_DET)
    a.label("kn_x")
    E(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)
    a.label("kn_q")
    E(raw, GP.popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    E(b_w, prev["knob"])
    a.label("kn_add")                                                     # (r0 = v, r6 = 0: Clear) -> v + the delta, 0..127
    E(cmp_imm, 6, 0)
    E(b_cond, "ka_c", "ne")
    E(movs_imm, 0, 0)
    E(raw, h(0x4770))
    a.label("ka_c")
    E(ldr_sp, 1, 8 + 0)                                                   # (bl kn_add: sp as at the head's push) the delta
    E(adds_reg, 0, 0, 1)
    E(cmp_imm, 0, 0)
    E(b_cond, "ka_h", "ge")
    E(movs_imm, 0, 0)
    a.label("ka_h")
    E(cmp_imm, 0, 127)
    E(b_cond, "ka_x", "le")
    E(movs_imm, 0, 127)
    a.label("ka_x")
    E(raw, h(0x4770))

    # ---- c_esled (the LED task's calls: ctrl, frame): the chain; the core 0 words; Sample mode's pads and pad 16's knobs
    a.label("c_esled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)                                                      # r5 = the frame
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(bl, "c_esram")
    E(mov_reg, 7, 0)                                                      # r7 = our RAM
    # the holds
    imm32(0, CI.HAL_TICK)
    E(ldr_imm, 0, 0, 0)
    E(ldr_imm, 1, 7, O_TICK)
    E(subs_reg, 0, 0, 1)
    E(movw, 1, HOLD)
    E(cmp_reg, 0, 1)
    E(b_cond, "ld_h", "lo")
    E(movs_imm, 2, 2)
    for o in (O_H16, O_H24):
        E(ldrb_imm, 0, 7, o)
        E(cmp_imm, 0, 1)
        E(b_cond, f"ld_h{o}", "ne")
        E(strb_imm, 2, 7, o)
        a.label(f"ld_h{o}")
    a.label("ld_h")
    # the core 0 words (cthresh READY)
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    bc("ld_v", "eq")
    E(movw, 1, TH.O_ST + 1)                                               # (+ 1: the program in core 0)
    E(adds_reg, 0, 0, 1)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, TH.READY)
    bc("ld_v", "ne")
    E(bl, "c_eswords")
    a.label("ld_v")
    # Sample mode's pads
    E(bl, "c_estrk")
    E(cmp_imm, 0, 8)
    E(b_cond, "ld_t", "lo")
    E(bl, L["c_smview"])                                                  # leaving Sample mode closes the selector
    E(cmp_imm, 0, 8)
    bc("ld_x", "lo")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 7, O_OPEN)
    E(strb_imm, 0, 7, O_H16)
    E(strb_imm, 0, 7, O_H24)
    E(b, "ld_x")
    a.label("ld_t")
    E(mov_reg, 4, 0)                                                      # r4 = the track
    E(bl, "c_eseng")
    E(mov_reg, 6, 0)                                                      # r6 = its engine
    imm32(3, T["ce"])
    E(lsls_imm, 1, 6, 1)
    E(adds_reg, 3, 3, 1)                                                  # r3 = its colours
    E(ldrb_imm, 0, 7, O_OPEN)
    E(cmp_imm, 0, 0)
    E(b_cond, "ld_o", "ne")
    E(ldrb_imm, 0, 3, 1)                                                  # closed: pad 8 dim, the old mode pads dark
    E(strh_imm, 0, 5, 2 * P_SEL)
    E(movs_imm, 0, 0)
    for p in HIDE_CLOSED:
        E(strh_imm, 0, 5, 2 * p)
    E(b, "ld_x")
    a.label("ld_o")
    E(movs_imm, 0, 0)                                                     # open: rows 1-3 ours (the link as smodes drew it), 31 / 32 dark
    for p in list(range(24)) + [30, 31]:
        if p != P_LINK:
            E(strh_imm if 2 * p < 64 else strh_w_imm, 0, 5, 2 * p)
    E(ldrb_imm, 0, 3, 0)
    E(strh_imm, 0, 5, 2 * P_SEL)                                          # pad 8: the engine's colour, bright
    imm32(3, T["ce"])
    for e in range(8):                                                    # the engines
        if COL_E[e] == (0, 0):
            continue
        E(ldrb_imm, 0, 3, 2 * e + 1)
        E(cmp_imm, 6, e)
        E(b_cond, f"ld_e{e}", "ne")
        E(ldrb_imm, 0, 3, 2 * e)
        a.label(f"ld_e{e}")
        E(strh_w_imm, 0, 5, 2 * (P_ENG0 + e))
    for pad, eng in ((P_SRC_IN, E_IN), (P_SRC_INV, E_INV)):               # the input's source in its column
        E(cmp_imm, 6, eng)
        E(b_cond, f"ld_s{pad}", "ne")
        E(mov_reg, 0, 4)
        E(bl, L["c_smline"])
        E(lsrs_imm, 0, 0, SM.SRC_SHIFT)
        E(movs_imm, 1, 3)
        E(ands_reg, 0, 1)
        E(movs_imm, 1, SM.SRC_COLS[0])
        for k in (1, 2):
            E(cmp_imm, 0, k)
            E(b_cond, f"ld_s{pad}{k}", "ne")
            E(movs_imm, 1, SM.SRC_COLS[k])
            a.label(f"ld_s{pad}{k}")
        E(strh_imm, 1, 5, 2 * pad)
        a.label(f"ld_s{pad}")
    E(cmp_imm, 6, E_VA)                                                   # pad 16: the voice, in its mode's colour
    E(b_cond, "ld_vc", "eq")
    E(cmp_imm, 6, E_FM)
    bc("ld_i", "ne")
    a.label("ld_vc")
    E(mov_reg, 0, 4)
    E(bl, "c_esmode")
    E(mov_reg, 6, 0)                                                      # r6 = its mode
    imm32(3, T["cm"])
    E(lsls_imm, 1, 6, 1)
    E(ldrb_reg, 0, 3, 1)
    E(strh_imm, 0, 5, 2 * P_VOICE)
    E(ldrb_imm, 0, 7, O_H16)
    E(cmp_imm, 0, 2)
    bc("ld_i", "ne")
    for m in range(8):                                                    # held: the modes on 17-24
        E(ldrb_imm, 0, 3, 2 * m + 1)
        E(cmp_imm, 6, m)
        E(b_cond, f"ld_m{m}", "ne")
        E(ldrb_imm, 0, 3, 2 * m)
        a.label(f"ld_m{m}")
        E(strh_w_imm, 0, 5, 2 * (P_ENG0 + m))
    E(bl, "c_esknobs")
    a.label("ld_i")
    E(ldrb_imm, 0, 7, O_H24)                                              # pad 24 held: the instruments on rows 1, 2, 4
    E(cmp_imm, 0, 2)
    bc("ld_x", "ne")
    E(mov_reg, 0, 4)
    E(bl, L["c_syslot"])
    E(cmp_imm, 0, NSL)
    bc("ld_x", "hs")
    imm32(1, L["FMR"] + L["O_INST"])
    E(ldrb_reg, 6, 1, 0)                                                  # r6 = the loaded one + 1
    E(subs_imm8, 6, 1)
    imm32(3, T["ic"])
    E(movs_imm, 4, 0)
    a.label("ld_il")
    E(lsls_imm, 1, 4, 1)
    E(adds_imm8, 1, 1)
    E(cmp_reg, 4, 6)
    E(b_cond, "ld_ib", "ne")
    E(subs_imm8, 1, 1)
    a.label("ld_ib")
    E(ldrb_reg, 0, 3, 1)
    E(mov_reg, 1, 4)
    E(cmp_imm, 1, 16)
    E(b_cond, "ld_ip", "lo")
    E(adds_imm8, 1, 8)
    a.label("ld_ip")
    E(lsls_imm, 1, 1, 1)
    E(raw, h(0x5268))                                                     # strh r0, [r5, r1]
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, 24)
    E(b_cond, "ld_il", "lo")
    a.label("ld_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)

    # ---- c_esknobs (r4 = the track, r5 = the frame, r7 = our RAM): pad 16 held: K1 glide (teal), K2 the detune (blue), the rest dark
    a.label("c_esknobs")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(bl, L["c_rst"])
    E(movw, 1, SY.O_KB)
    E(adds_reg, 6, 0, 1)                                                  # r6 = kbright's overlay
    E(movs_imm, 0, 0xFF)
    E(strb_imm, 0, 6, SP.K_MASK)
    E(movs_imm, 0, 0)
    for k in range(8):
        E(strb_imm, 0, 6, SP.K_VAL + k)
        E(strh_imm, 0, 6, SP.K_CODE + 2 * k)
        E(strh_w_imm, 0, 5, 2 * (SP.LED_KNOB0 + k))
    E(mov_reg, 0, 4)
    E(bl, L["c_syslot"])
    E(cmp_imm, 0, NSL)
    E(b_cond, "kl_d", "hs")
    E(movs_imm, 1, SY.K_GLIDE)
    E(bl, L["c_syv"])
    E(strb_imm, 0, 6, SP.K_VAL)
    E(movs_imm, 0, COL_GLIDE)
    E(strh_imm, 0, 6, SP.K_CODE)
    E(strh_w_imm, 0, 5, 2 * SP.LED_KNOB0)
    a.label("kl_d")
    E(adds_reg, 0, 7, 4)
    E(ldrb_imm, 0, 0, O_DET)
    E(strb_imm, 0, 6, SP.K_VAL + 1)
    E(movs_imm, 0, COL_DET)
    E(strh_imm, 0, 6, SP.K_CODE + 2)
    E(strh_w_imm, 0, 5, 2 * (SP.LED_KNOB0 + 1))
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_eswords (r7 = our RAM): each track's flags and gain to core 0 when its mode, slots or detune change (and its slots' words for
    # the detune); one track a frame in turn; the key once; poly / unison kept with their slots
    a.label("c_eswords")
    E(push_list, [4, 5, 6], lr=True)
    E(movs_imm, 4, 0)
    a.label("ew_l")
    E(adds_reg, 0, 7, 4)
    E(ldrb_imm, 5, 0, O_MODE)                                             # r5 = the mode + 1 (0 = never set)
    E(movs_imm, 2, 0)                                                     # its unison bit (a project's record sets the modes alone)
    E(cmp_imm, 5, 0)
    E(b_cond, "ew_ub", "eq")
    imm32(0, T["un"] - 1)
    E(ldrb_reg, 2, 0, 5)
    E(movs_imm, 0, 1)
    E(ands_reg, 2, 0)
    a.label("ew_ub")
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(ldrb_w, 0, 7, O_UNI)
    E(bics_reg, 0, 1)
    E(cmp_imm, 2, 0)
    E(b_cond, "ew_u2", "eq")
    E(orrs_reg, 0, 1)
    a.label("ew_u2")
    E(strb_w, 0, 7, O_UNI)
    E(cmp_imm, 5, 0)
    E(b_cond, "ew_n", "eq")
    imm32(0, T["un"] - 1)
    E(ldrb_reg, 0, 0, 5)
    E(cmp_imm, 0, 0)
    E(b_cond, "ew_n", "eq")                                               # poly / unison: their slots back if the track lost them
    E(mov_reg, 0, 4)
    E(bl, L["c_sysnd"])
    E(cmp_imm, 0, SY.SND_SYNTH)
    E(b_cond, "ew_n", "ne")
    E(mov_reg, 0, 4)
    E(bl, L["c_plis"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ew_n", "ne")
    E(mov_reg, 0, 4)
    E(bl, L["c_plon"])
    a.label("ew_n")
    E(mov_reg, 0, 4)
    E(bl, "c_esslots")
    E(lsls_imm, 6, 0, 4)
    E(orrs_reg, 6, 5)                                                     # r6 = the signature: mode + 1 | slots << 4
    E(adds_reg, 0, 7, 4)
    E(ldrb_w, 1, 0, O_SENT)
    E(ldrb_imm, 2, 0, O_DET)
    E(ldrb_w, 3, 0, O_DSENT)
    E(cmp_reg, 1, 6)
    E(b_cond, "ew_w", "ne")
    E(cmp_reg, 2, 3)
    E(b_cond, "ew_w", "ne")
    E(ldrb_w, 1, 7, O_RR)
    E(cmp_reg, 1, 4)
    E(b_cond, "ew_c", "ne")
    E(bl, "c_esw")                                                        # its turn: the two words again
    E(b, "ew_c")
    a.label("ew_w")
    E(strb_w, 6, 0, O_SENT)
    E(strb_w, 2, 0, O_DSENT)
    E(bl, "c_esw")
    E(movs_imm, 6, 0)                                                     # its slots' words (the detune)
    a.label("ew_s")
    E(bl, L["c_syb"])
    E(movs_imm, 1, SY.SL)
    E(muls, 1, 6)
    E(adds_reg, 1, 0, 1)
    E(ldrb_imm, 1, 1, 2)
    E(subs_imm8, 1, 1)
    E(cmp_reg, 1, 4)
    E(b_cond, "ew_sn", "ne")
    E(mov_reg, 0, 6)
    E(bl, L["c_sypend"])
    a.label("ew_sn")
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, NSL)
    E(b_cond, "ew_s", "lo")
    a.label("ew_c")
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, 8)
    bc("ew_l", "lo")
    E(ldrb_w, 0, 7, O_RR)
    E(adds_imm8, 0, 1)
    E(movs_imm, 1, 7)
    E(ands_reg, 0, 1)
    E(strb_w, 0, 7, O_RR)
    E(cmp_imm, 0, 0)                                                      # the key: once a round of 8 frames
    E(b_cond, "ew_x", "ne")
    imm32(0, VM.VKEY)
    E(movw, 1, VM.VMK)
    E(movs_imm, 2, 0)
    E(bl, L["c_gpw"])
    a.label("ew_x")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_esw (r4 = the track, r7 = our RAM): X:VMF + t = its flags (0 never set), X:UG + t = its unison's gain; clobbers r0-r3
    a.label("c_esw")
    E(push_list, [5], lr=True)
    E(adds_reg, 0, 7, 4)
    E(ldrb_imm, 5, 0, O_MODE)
    E(movs_imm, 0, 0)
    E(cmp_imm, 5, 0)
    E(b_cond, "ww_f", "eq")
    imm32(0, T["fl"] - 1)
    E(ldrb_reg, 0, 0, 5)
    a.label("ww_f")
    E(movw, 1, VM.VMF)
    E(adds_reg, 1, 1, 4)
    E(movs_imm, 2, 0)
    E(bl, L["c_gpw"])
    E(movs_imm, 5, 0)                                                     # the gain: unison with 3 slots or more
    E(ldrb_w, 0, 7, O_UNI)
    E(lsrs_reg, 0, 4)
    E(lsrs_imm, 0, 0, 1)
    E(b_cond, "ww_g", "cc")
    E(mov_reg, 0, 4)
    E(bl, "c_esslots")
    E(cmp_imm, 0, 0)
    E(b_cond, "ww_g", "eq")
    E(subs_imm8, 0, 1)
    E(lsls_imm, 0, 0, 2)
    imm32(1, T["ug"])
    E(raw, h(0x5845))                                                     # ldr r5, [r0, r1]
    a.label("ww_g")
    E(mov_reg, 0, 5)
    E(movw, 1, VM.UG)
    E(adds_reg, 1, 1, 4)
    E(movs_imm, 2, 0)
    E(bl, L["c_gpw"])
    E(pop_list, [5], pc=True)
    return a.assemble(), T


def install(img, report, base_addr):
    """Our heads in front of the pad press / release, the knob slot and the LED calls; synthpage's c_sydt stub -> c_esdt.  Needs smodes,
    fmpage (OPT poly, vmode), fm8page, synthpage (OPT vmode), vmode0 on core 0 (OPT vmode)."""
    import struct
    import fm8page as F8
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]                 # noqa: E731
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    assert rhbuild.OPT.get("vmode") and "fm8page" in report and "smodes" in report
    assert F8.FMR + F8.RAM_LEN <= ESR and ESR + ESR_LEN <= 0x2004EC00
    L = dict(c_rst=lab("rhstate", "c_rst"), c_ciok=lab("countin", "c_ciok"), c_spshift=lab("stockplus", "c_spshift"),
             c_spheld=lab("stockplus", "c_spheld"), c_smview=lab("smodes", "c_smview"), c_smline=lab("smodes", "c_smline"),
             c_sysnd=lab("synthpage", "c_sysnd"), c_syslot=lab("synthpage", "c_syslot"), c_syb=lab("synthpage", "c_syb"),
             c_syv=lab("synthpage", "c_syv"), c_syp=lab("synthpage", "c_syp"), c_sypend=lab("synthpage", "c_sypend"),
             c_fmon=lab("fmpage", "c_fmon"), c_fmset=lab("fmpage", "c_fmset"), c_plis=lab("fmpage", "c_plis"),
             c_plon=lab("fmpage", "c_plon"), c_ploff=lab("fmpage", "c_ploff"), c_f8page=lab("fm8page", "c_f8page"),
             c_f8load=lab("fm8page", "c_f8load"), c_gpw=lab("granpage", "c_gpw"), FMR=F8.FMR, O_INST=F8.O_INST)
    prev = dict(pad=rhbuild.bw_target(img, GP.PP_ENTRY), rel=rhbuild.bw_target(img, GP.PR_ENTRY), knob=u(SY.SLOT_KNOB) & ~1,
                ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    (code_, T) = arm_code(base_addr, L, prev)
    code_, labels = code_
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code_
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, GP.PP_ENTRY, f"b.w #{prev['pad']:#x}", b_w(GP.PP_ENTRY, labels["c_espad"]))
    rhbuild.patch(img, GP.PR_ENTRY, f"b.w #{prev['rel']:#x}", b_w(GP.PR_ENTRY, labels["c_esrel"]))
    rhbuild.patch_word(img, SY.SLOT_KNOB, prev["knob"] | 1, labels["c_esknob"] | 1)
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_esled"]))
    stub = lab("synthpage", "c_sydt")                                          # synthpage's stub (mov r0, r1; bx lr) -> b.w c_esdt
    rhbuild.patch(img, stub, "mov r0, r1|bx lr", b_w(stub, labels["c_esdt"]))
    report["esel"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")},
                          tables={k: hex(v) for k, v in T.items()}, ram=hex(ESR))
    return labels, code_
