"""The track menu as CIRCUIT-HACKS' row 1, views only, and the pages it adds (MIT; RH80; the user, 2026-11-06 / 07: «para el selector de vistas
(aguantar pad pulsado) usa el mismo row1 que en Hacks, los knobs en disposición similar. Las opciones que no existan en Hacks, al row2»,
«Make sure all functions are selectable, and no stock control is stepped on», «En los menús de pista, sólo vistas, no modos»;
docs/DISENO_RH80.md).

The track menu open (granpage's c_gpmopen: a held track button, or a tap on the selected one), our head in front of its pads: each pad of
the new layout plays the old menu pad (pressed with it, let go with it: a tap keeps the page, a hold shows it until let go, as before) and
the LEDs are moved after the old ones are drawn:
  row 1: 1 the sequenceable lanes (Shift + 1: the non-sequenceable ones; modmx), 2 the sound's page (sample / line: stock; granular:
         Granular; VA: OSC 1; FM: its operators on the Synth page), 3 VA: OSC 2 / FM: its pitch envelope, 4 Filter / VCA, 5 Envelope + LFO,
         6 the matrix; 7 / 8 dark (the FM's lists: Sample mode, pad 24 held, and the FM page);
  row 2: 9 stock, 10 Stock+, 16 Project init (autoinit); the rest dark.
Our pages (VP + t), on the stock page (Filter / VCA, Envelope + LFO) or the Synth page (OSC 1 / OSC 2), until another page is picked or the
track's engine changes; the knobs go to the modules that own the values (their page bit or Shift set around the call: their steps, Clear,
the matrix's recording stay theirs), the LEDs drawn here:
  * Filter / VCA (lime): K1 the level (the Mixer's store), K4 the stock's envelope, K6 / K7 / K8 the stock's high-pass, low-pass, resonance,
    K5 (granular / synth) the envelope -> low-pass (the Envelope page's K4); K2 / K3 dark;
  * Envelope + LFO: K1-K4 the Envelope page's (granular / synth; rose), K5 / K6 Stock+'s LFO rate / depth (sky blue);
  * OSC 1 (VA): K1 tune, K2 fine, K3 wave, K4 shape, K5-K8 envelope -> FM / ring / morph / mix; Shift: K1 envelope -> pitch, K2 glide,
    K3 octave, K4 envelope -> shape;  OSC 2: K1 tune 2, K2 fine 2, K3 wave 2, K4 shape 2, K5 FM, K6 ring, K7 sync + bitwise, K8 mix.
    OSC 1's tune, fine and the three envelope depths are new values (ours, per track, XOR 64; the project's record, projsnd OPT vsel):
    synthpage's c_syext stub -> c_vsext gives them to its words (OSC 1's TUNE / FINE, synth0's C_G1 / C_G2 / C_GS -> va0 OPT envx).
RAM: VSR (above dspz's state): + 0 MAG, + 4 the pages (8), + 12 the old pad each new one plays (16, + 1), + 28 the press's tick, + 32 the
page before it, + 33 the engines the pages were set with (8), + 41 the round; ESR + 72 the new values (5 a track).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, ands_reg, b, b_cond, b_w, bics_reg, bl, cmp_imm, cmp_reg, h, ldr_imm, ldr_sp, ldrb_imm,  # noqa: E402
                   ldrb_reg, lsls_imm, lsls_reg, lsrs_imm, lsrs_reg, mov_reg, movs_imm, movt, movw, muls, orrs_reg, pop_list, push_list,
                   raw, str_imm, strb_imm, strh_imm, strh_w_imm, subs_imm8, subs_reg, tst_reg, ldrb_w, strb_w)
import countin as CI  # noqa: E402
import esel as ES  # noqa: E402
import envpage as EV  # noqa: E402
import granpage as GP  # noqa: E402
import stockplus as SP  # noqa: E402
import synthpage as SY  # noqa: E402

VSR, VSR_LEN = 0x2004EE20, 64
MAG = 0x4C455356                                       # "VSEL"
O_MAG, O_VP, O_MAP, O_TICK, O_PREV, O_ENG, O_RR = 0, 4, 12, 28, 32, 33, 41
EXT0, NEXT = 72, 5                                     # ESR + 72: tune 1, fine 1, env -> FM, env -> ring, env -> mix (XOR 64), 5 a track
VP_NONE, VP_FILT, VP_MOD, VP_OSC2, VP_OSC1 = 0, 1, 2, 3, 4
PAGE_HOLD = SY.PAGE_HOLD
# the old menu's pads
OLD_STOCK, OLD_SP, OLD_GRAN, OLD_SYNTH, OLD_ENV, OLD_MX, OLD_SEQ, OLD_INIT, OLD_NSEQ = 0, 1, 2, 3, 4, 5, 6, 7, 15
COL_FILT, DIM_FILT = 0xBF, 0xCD                        # lime (docs/INTERFAZ.md)
COL_MOD, DIM_MOD = EV.COL, EV.DIM
COL_STOCK, DIM_STOCK = 0x01, 0x09
K_EXT = 0x80                                           # (the knob maps) 0x80 | e = our value e; 0xFF = nothing
# OSC 1 / OSC 2: knob k (+ 8 with Shift) -> synthpage's knob index, or ours
OSC1 = (K_EXT | 0, K_EXT | 1, 0, 1, K_EXT | 2, K_EXT | 3, SY.K_ENVM, K_EXT | 4, 8, SY.K_GLIDE, SY.K_OCT, 9, 0xFF, 0xFF, 0xFF, 0xFF)
OSC2 = (4, 12, 2, 3, 5, SY.K_RING, 6, 7) + (0xFF,) * 8
EXT_SEMI = (1, 0, 0, 0, 0)                             # tune 1 in semitones (as OSC 2's: ((3 v + 4) >> 3) - 24); the rest v - 64
LEVELS, SETTER, GETTER = 0x20012098, 0x08038A08, 0x08046410
GSET_OBJ, ID_LEVEL0 = 0x20011998, 0x91                 # (found in emulation: ids 0x91 + t write the Mixer's levels)


def model_menu_old(new, eng, shift=False):
    """the old menu pad a new one plays (None: dark), and the page it sets (the tests')"""
    if new == 0:
        return (OLD_NSEQ if shift else OLD_SEQ), VP_NONE
    if new == 1:
        return {ES.E_GR: OLD_GRAN, ES.E_VA: OLD_SYNTH, ES.E_FM: OLD_SYNTH}.get(eng, OLD_STOCK), (VP_OSC1 if eng == ES.E_VA else VP_NONE)
    if new == 2:
        return (OLD_SYNTH, VP_OSC2) if eng == ES.E_VA else (OLD_SYNTH, VP_NONE) if eng == ES.E_FM else (None, None)
    return {3: (OLD_STOCK, VP_FILT), 4: (OLD_STOCK, VP_MOD), 5: (OLD_MX, VP_NONE), 8: (OLD_STOCK, VP_NONE), 9: (OLD_SP, VP_NONE),
            15: (OLD_INIT, VP_NONE)}.get(new, (None, None))


def ext_word(e, v):
    """our value e (stored XOR 64) -> its DSP word"""
    v ^= 64
    return ((3 * v + 4) >> 3) - 24 if EXT_SEMI[e] else v - 64


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

    data = bytearray()
    T = {}

    def put(name, bs):
        while len(data) % 4:
            data.append(0)
        T[name] = base + len(data)
        data.extend(bs)
    put("osc1", bytes(OSC1))
    put("osc2", bytes(OSC2))
    put("waves", bytes(SY.UI_WAVES_VA))
    put("zones", bytes(SY.VA_ZONES))
    put("bip", bytes(SY.BIP_VA))                                          # synthpage's knob indices: bipolar
    while len(data) % 4:
        data.append(0)
    E(raw, bytes(data))

    # ---- c_vsram() -> r0 = our RAM (from zero once); clobbers r1-r3
    a.label("c_vsram")
    imm32(0, VSR)
    E(ldr_imm, 1, 0, O_MAG)
    imm32(2, MAG)
    E(cmp_reg, 1, 2)
    E(b_cond, "vr_x", "eq")
    E(movs_imm, 1, 0)
    E(movs_imm, 3, VSR_LEN)
    a.label("vr_z")
    E(subs_imm8, 3, 4)
    E(raw, h(0x50C1))                                                     # str r1, [r0, r3]
    E(b_cond, "vr_z", "ne")
    E(str_imm, 2, 0, O_MAG)
    a.label("vr_x")
    E(raw, h(0x4770))

    # ---- c_vspage(r0 = track) -> r0 = its page of ours (0 = none; dropped when its engine changed since); clobbers r1-r3
    a.label("c_vspage")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_vsram")
    E(adds_reg, 5, 0, 4)
    E(ldrb_imm, 0, 5, O_VP)
    E(cmp_imm, 0, 0)
    E(b_cond, "vp_0", "eq")
    E(mov_reg, 0, 4)
    E(bl, L["c_eseng"])
    E(ldrb_w, 1, 5, O_ENG)
    E(cmp_reg, 0, 1)
    E(b_cond, "vp_d", "ne")
    E(ldrb_imm, 0, 5, O_VP)
    E(cmp_imm, 0, VP_OSC2)                                                # OSC 1 / 2: only on the Synth page
    E(b_cond, "vp_x", "lo")
    E(mov_reg, 0, 4)
    E(bl, L["c_sypage"])
    E(cmp_imm, 0, 0)
    E(b_cond, "vp_d", "eq")
    E(ldrb_imm, 0, 5, O_VP)
    E(b, "vp_x")
    a.label("vp_d")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 5, O_VP)
    a.label("vp_0")                                                       # none of ours: a VA on its Synth page = OSC 1
    E(mov_reg, 0, 4)
    E(bl, L["c_eseng"])
    E(cmp_imm, 0, ES.E_VA)
    E(b_cond, "vp_n", "ne")
    E(mov_reg, 0, 4)
    E(bl, L["c_sypage"])
    E(cmp_imm, 0, 0)
    E(b_cond, "vp_x", "eq")
    E(movs_imm, 0, VP_OSC1)
    E(b, "vp_x")
    a.label("vp_n")
    E(movs_imm, 0, 0)
    a.label("vp_x")
    E(pop_list, [4, 5], pc=True)

    # ---- c_vsext(r0 = slot, r1 = e) -> r0 = our value e's word for that slot's track (synthpage's stub c_syext); clobbers r1-r3
    a.label("c_vsext")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 5, 1)
    E(mov_reg, 4, 0)
    E(bl, L["c_syb"])
    E(cmp_imm, 0, 0)
    E(b_cond, "vx_0", "eq")
    E(movs_imm, 1, SY.SL)
    E(muls, 1, 4)
    E(adds_reg, 0, 0, 1)
    E(ldrb_imm, 4, 0, 2)                                                  # r4 = the track + 1
    E(cmp_imm, 4, 0)
    E(b_cond, "vx_0", "eq")
    E(subs_imm8, 4, 1)
    E(bl, L["c_esram"])
    E(movs_imm, 1, NEXT)
    E(muls, 1, 4)
    E(adds_reg, 0, 0, 1)
    E(adds_reg, 0, 0, 5)
    E(ldrb_w, 0, 0, EXT0)
    E(movs_imm, 1, 64)
    E(raw, h(0x4048))                                                     # eors r0, r1
    E(cmp_imm, 5, 0)
    E(b_cond, "vx_b", "ne")
    E(movs_imm, 1, 3)                                                     # tune 1: ((3 v + 4) >> 3) - 24
    E(muls, 0, 1)
    E(adds_imm8, 0, 4)
    E(lsrs_imm, 0, 0, 3)
    E(subs_imm8, 0, 24)
    E(pop_list, [4, 5], pc=True)
    a.label("vx_b")
    E(subs_imm8, 0, 64)
    E(pop_list, [4, 5], pc=True)
    a.label("vx_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4, 5], pc=True)

    # ---- c_vsextv(r0 = track, r1 = e) -> r0 = the address of our value e
    a.label("c_vsextv")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(bl, L["c_esram"])
    E(movs_imm, 1, NEXT)
    E(muls, 1, 4)
    E(adds_reg, 0, 0, 1)
    E(adds_reg, 0, 0, 5)
    E(adds_imm8, 0, EXT0)
    E(pop_list, [4, 5], pc=True)

    # ---- c_vspad (the controller's pad press, ours first: r0 = ctrl, r1 = pad, r2 = velocity)
    a.label("c_vspad")
    E(cmp_imm, 1, 16)
    bc("pd_p", "hs")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)                                                      # r5 = the new pad
    E(bl, L["c_gpmopen"])
    E(cmp_imm, 0, 8)
    bc("pd_q", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the menu's track
    E(bl, L["c_eseng"])
    E(mov_reg, 6, 0)                                                      # r6 = its engine
    E(bl, "c_vsram")
    E(mov_reg, 7, 0)                                                      # r7 = our RAM
    # the old pad (r1) and our page (r2); 0xFF = dark
    E(movs_imm, 1, 0xFF)
    E(movs_imm, 2, VP_NONE)
    E(cmp_imm, 5, 0)
    E(b_cond, "pm_1", "ne")
    E(bl, L["c_spshift"])
    E(movs_imm, 1, OLD_SEQ)
    E(cmp_imm, 0, 0)
    E(b_cond, "pm_x0", "eq")
    E(movs_imm, 1, OLD_NSEQ)
    a.label("pm_x0")
    E(movs_imm, 2, VP_NONE)
    E(b, "pm_go")
    a.label("pm_1")
    E(cmp_imm, 5, 1)
    E(b_cond, "pm_2", "ne")
    E(movs_imm, 1, OLD_STOCK)
    E(cmp_imm, 6, ES.E_GR)
    E(b_cond, "pm_1a", "ne")
    E(movs_imm, 1, OLD_GRAN)
    a.label("pm_1a")
    E(cmp_imm, 6, ES.E_FM)
    E(b_cond, "pm_1b", "ne")
    E(movs_imm, 1, OLD_SYNTH)
    a.label("pm_1b")
    E(cmp_imm, 6, ES.E_VA)
    E(b_cond, "pm_go", "ne")
    E(movs_imm, 1, OLD_SYNTH)
    E(movs_imm, 2, VP_OSC1)
    E(b, "pm_go")
    a.label("pm_2")
    E(cmp_imm, 5, 2)
    E(b_cond, "pm_3", "ne")
    E(cmp_imm, 6, ES.E_FM)
    E(b_cond, "pm_2a", "eq")
    E(cmp_imm, 6, ES.E_VA)
    E(b_cond, "pm_go", "ne")
    E(movs_imm, 2, VP_OSC2)
    a.label("pm_2a")
    E(movs_imm, 1, OLD_SYNTH)
    E(b, "pm_go")
    a.label("pm_3")
    for new, old, vp in ((3, OLD_STOCK, VP_FILT), (4, OLD_STOCK, VP_MOD), (5, OLD_MX, VP_NONE), (8, OLD_STOCK, VP_NONE),
                         (9, OLD_SP, VP_NONE), (15, OLD_INIT, VP_NONE)):
        E(cmp_imm, 5, new)
        E(b_cond, f"pm_n{new}", "ne")
        E(movs_imm, 1, old)
        E(movs_imm, 2, vp)
        E(b, "pm_go")
        a.label(f"pm_n{new}")
    a.label("pm_go")
    E(adds_reg, 0, 7, 5)
    E(cmp_imm, 1, 0xFF)
    E(b_cond, "pd_dk", "ne")
    E(movs_imm, 1, 0)                                                     # dark: swallowed (its release too: map 0xFF + 1 = 0 below)
    E(strb_imm, 1, 0, O_MAP)
    E(movs_imm, 1, 0x80)
    E(strb_imm, 1, 0, O_MAP)                                              # (0x80: ours, nothing to let go)
    E(b, "pd_x")
    a.label("pd_dk")
    E(adds_imm8, 1, 1)
    E(strb_imm, 1, 0, O_MAP)
    E(subs_imm8, 1, 1)
    E(push_list, [1, 2])
    E(cmp_imm, 5, 15)                                                     # (Project init: the page stays)
    E(b_cond, "pd_old", "eq")
    # our page: kept with the engine; the page before (a hold puts it back)
    E(adds_reg, 3, 7, 4)
    E(ldrb_imm, 0, 3, O_VP)
    E(strb_w, 0, 7, O_PREV)
    E(strb_imm, 2, 3, O_VP)
    E(strb_w, 6, 3, O_ENG)
    imm32(0, CI.HAL_TICK)
    E(ldr_imm, 0, 0, 0)
    E(str_imm, 0, 7, O_TICK)
    E(cmp_imm, 5, 2)                                                      # FM: pad 2 = its first operator, pad 3 = its pitch envelope
    E(b_cond, "pd_f2", "eq")
    E(cmp_imm, 5, 1)
    E(b_cond, "pd_old", "ne")
    a.label("pd_f2")
    E(cmp_imm, 6, ES.E_FM)
    E(b_cond, "pd_old", "ne")
    E(bl, L["c_f8ram"])
    E(movs_imm, 1, 0)
    E(cmp_imm, 5, 2)
    E(b_cond, "pd_f3", "ne")
    E(movs_imm, 1, 8)
    a.label("pd_f3")
    E(strb_imm, 1, 0, L["F8_SEL"])
    a.label("pd_old")
    E(pop_list, [1, 2])
    E(ldr_sp, 0, 0)
    E(ldr_sp, 2, 8)
    E(bl, prev["pad"])                                                    # the old pad pressed
    a.label("pd_x")
    E(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)
    a.label("pd_q")
    E(raw, GP.popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    a.label("pd_p")
    E(b_w, prev["pad"])

    # ---- c_vsrel (the controller's pad release, ours first: r0 = ctrl, r1 = pad): the old pad let go; our page held past PAGE_HOLD = back
    a.label("c_vsrel")
    E(cmp_imm, 1, 16)
    bc("rl_p", "hs")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)
    E(bl, "c_vsram")
    E(mov_reg, 7, 0)
    E(adds_reg, 6, 7, 5)
    E(ldrb_imm, 1, 6, O_MAP)
    E(cmp_imm, 1, 0)
    bc("rl_q", "eq")                                                      # not pressed through us
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 6, O_MAP)
    E(cmp_imm, 1, 0x80)
    bc("rl_x", "eq")                                                      # a dark one
    E(subs_imm8, 1, 1)
    E(ldr_sp, 0, 0)
    E(bl, prev["rel"])                                                    # the old pad let go
    imm32(0, CI.HAL_TICK)                                                 # held: our page back as it was
    E(ldr_imm, 0, 0, 0)
    E(ldr_imm, 1, 7, O_TICK)
    E(subs_reg, 0, 0, 1)
    E(movw, 1, PAGE_HOLD)
    E(cmp_reg, 0, 1)
    bc("rl_x", "lo")
    E(bl, L["c_gpmopen"])
    E(cmp_imm, 0, 8)
    bc("rl_x", "hs")
    E(adds_reg, 0, 7, 0)
    E(ldrb_w, 1, 7, O_PREV)
    E(strb_imm, 1, 0, O_VP)
    a.label("rl_x")
    E(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)
    a.label("rl_q")
    E(raw, GP.popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    a.label("rl_p")
    E(b_w, prev["rel"])

    # ---- c_vsfwd(r0, r1 = knob, r2 = delta, r3 = Shift wanted 0 / 1 or 2 = as it is): the knob through the chain after ours (Shift set
    # around it); clobbers r0-r3
    a.label("c_vsfwd")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(mov_reg, 6, 2)
    E(movs_imm, 7, 0xFF)
    E(cmp_imm, 3, 2)
    E(b_cond, "fw_c", "eq")
    E(push_list, [3])
    imm32(0, SP.CTRL)
    E(ldr_imm, 0, 0, 0xC)
    E(movs_imm, 1, 0)
    E(bl, CI.PARAM_GET)
    E(pop_list, [3])
    E(ldrb_imm, 7, 0, 0)                                                  # r7 = Shift as it was
    E(strb_imm, 3, 0, 0)
    a.label("fw_c")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(mov_reg, 2, 6)
    E(bl, prev["knob"])
    E(cmp_imm, 7, 0xFF)
    E(b_cond, "fw_x", "eq")
    imm32(0, SP.CTRL)
    E(ldr_imm, 0, 0, 0xC)
    E(movs_imm, 1, 0)
    E(bl, CI.PARAM_GET)
    E(strb_imm, 7, 0, 0)
    a.label("fw_x")
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_vsbit(r0 = the byte's address, r1 = track, r2 = 1 set / 0 clear) -> r0 = the byte as it was; clobbers r1-r3
    a.label("c_vsbit")
    E(push_list, [4], lr=True)
    E(ldrb_imm, 4, 0, 0)
    E(movs_imm, 3, 1)
    E(lsls_reg, 3, 1)
    E(mov_reg, 1, 4)
    E(bics_reg, 1, 3)
    E(cmp_imm, 2, 0)
    E(b_cond, "vb_w", "eq")
    E(orrs_reg, 1, 3)
    a.label("vb_w")
    E(strb_imm, 1, 0, 0)
    E(mov_reg, 0, 4)
    E(pop_list, [4], pc=True)

    # ---- c_vspg(r0, r1 = knob, r2 = delta, r3 = the page's byte address, [sp] .. : the track in r4 of the caller): that page's bit set for
    # the track around the knob (Shift as it is); clobbers r0-r3.  Here: c_vsenv(knob 0-3), c_vssp(knob 2 / 3)
    for nm, addr_of in (("c_vsenv", "env"), ("c_vssp", "sp")):
        a.label(nm)                                                       # (r0 = track, r1 = knob, r2 = delta, r3 = the slot's r0)
        E(push_list, [3, 4, 5, 6, 7], lr=True)
        E(mov_reg, 4, 0)
        E(mov_reg, 5, 1)
        E(mov_reg, 6, 2)
        if addr_of == "env":
            E(bl, L["c_rram"])
            E(movw, 1, GP.MN_O + SY.M_ENV)
        else:
            E(bl, L["c_rst"])
            E(movw, 1, SP.O_ST)
        E(adds_reg, 7, 0, 1)                                              # r7 = the byte
        E(mov_reg, 0, 7)
        E(mov_reg, 1, 4)
        E(movs_imm, 2, 1)
        E(bl, "c_vsbit")
        E(push_list, [0])
        E(ldr_sp, 0, 4)                                                   # (the slot's r0, pushed first)
        E(mov_reg, 1, 5)
        E(mov_reg, 2, 6)
        E(movs_imm, 3, 2)
        E(bl, "c_vsfwd")
        E(pop_list, [0])
        E(strb_imm, 0, 7, 0)
        E(pop_list, [3, 4, 5, 6, 7], pc=True)

    # ---- c_vsknob (the container's knob slot, ours first: r0, r1 = knob, r2 = delta)
    a.label("c_vsknob")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(cmp_imm, 1, 8)
    bc("kn_q", "hs")
    E(bl, L["c_spview"])
    E(cmp_imm, 0, 8)
    bc("kn_q", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the track
    E(bl, "c_vspage")
    E(cmp_imm, 0, 0)
    bc("kn_q", "eq")
    E(mov_reg, 6, 0)                                                      # r6 = our page
    E(ldr_sp, 5, 4)                                                       # r5 = k
    E(cmp_imm, 6, VP_FILT)
    bc("kn_mod", "ne")
    # Filter / VCA
    E(cmp_imm, 5, 0)
    E(b_cond, "kf_1", "ne")
    imm32(0, LEVELS)                                                      # K1: the level
    E(mov_reg, 1, 4)
    E(bl, L["c_cinew"])
    E(ldr_sp, 1, 8)
    E(adds_reg, 0, 0, 1)
    E(bl, "c_vsclamp")
    E(mov_reg, 2, 0)
    imm32(0, GSET_OBJ)                                                    # the stock's generic setter: the level of track t = 0x91 + t
    E(mov_reg, 1, 4)
    E(adds_imm8, 1, ID_LEVEL0)
    E(bl, SETTER)
    E(b, "kn_x")
    a.label("kf_1")
    E(cmp_imm, 5, 4)
    E(b_cond, "kf_2", "ne")
    E(mov_reg, 0, 4)                                                      # K5: the envelope -> low-pass (granular / synth)
    E(movs_imm, 1, 3)
    E(ldr_sp, 2, 8)
    E(ldr_sp, 3, 0)
    E(bl, "c_vsenv")
    E(b, "kn_x")
    a.label("kf_2")
    E(cmp_imm, 5, 1)
    E(b_cond, "kn_x", "eq")
    E(cmp_imm, 5, 2)
    E(b_cond, "kn_x", "eq")
    E(ldr_sp, 0, 0)                                                       # K4, K6-K8: the stock's own
    E(mov_reg, 1, 5)
    E(ldr_sp, 2, 8)
    E(movs_imm, 3, 2)
    E(bl, "c_vsfwd")
    E(b, "kn_x")
    a.label("kn_mod")
    E(cmp_imm, 6, VP_MOD)
    bc("kn_osc", "ne")
    E(cmp_imm, 5, 4)                                                      # Envelope + LFO: K1-K4 the Envelope page's
    E(b_cond, "km_s", "hs")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(ldr_sp, 2, 8)
    E(ldr_sp, 3, 0)
    E(bl, "c_vsenv")
    E(b, "kn_x")
    a.label("km_s")
    E(cmp_imm, 5, 6)                                                      # K5 / K6: Stock+'s K3 / K4 (the LFO's rate / depth)
    E(b_cond, "kn_x", "hs")
    E(mov_reg, 0, 4)
    E(subs_imm8, 5, 2)
    E(mov_reg, 1, 5)
    E(ldr_sp, 2, 8)
    E(ldr_sp, 3, 0)
    E(bl, "c_vssp")
    E(b, "kn_x")
    a.label("kn_osc")                                                     # OSC 1 / OSC 2
    E(bl, L["c_spshift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ko_n", "eq")
    E(adds_imm8, 5, 8)
    a.label("ko_n")
    imm32(0, T["osc2"])
    E(cmp_imm, 6, VP_OSC2)
    E(b_cond, "ko_t", "eq")
    imm32(0, T["osc1"])
    a.label("ko_t")
    E(ldrb_reg, 1, 0, 5)                                                  # r1 = the target
    E(cmp_imm, 1, 0xFF)
    E(b_cond, "kn_x", "eq")
    E(cmp_imm, 1, K_EXT)
    E(b_cond, "ko_e", "hs")
    E(movs_imm, 3, 0)                                                     # synthpage's knob: through the chain, Shift as it needs
    E(cmp_imm, 1, 8)
    E(b_cond, "ko_s", "lo")
    E(movs_imm, 3, 1)
    E(subs_imm8, 1, 8)
    a.label("ko_s")
    E(ldr_sp, 0, 0)
    E(ldr_sp, 2, 8)
    E(bl, "c_vsfwd")
    E(b, "kn_x")
    a.label("ko_e")                                                       # ours: +- the delta, 0..127 (stored XOR 64), Clear = the centre
    E(subs_imm8, 1, K_EXT)
    E(mov_reg, 0, 4)
    E(bl, "c_vsextv")
    E(mov_reg, 5, 0)                                                      # r5 = its address
    E(bl, L["c_spheld"])
    E(lsls_imm, 0, 0, 31 - SP.BIT_CLEAR)
    E(movs_imm, 0, 64)
    E(b_cond, "ko_w", "mi")
    E(ldrb_imm, 0, 5, 0)
    E(movs_imm, 1, 64)
    E(raw, h(0x4048))                                                     # eors r0, r1
    E(ldr_sp, 1, 8)
    E(adds_reg, 0, 0, 1)
    E(bl, "c_vsclamp")
    a.label("ko_w")
    E(movs_imm, 1, 64)
    E(raw, h(0x4048))
    E(strb_imm, 0, 5, 0)
    E(mov_reg, 0, 4)                                                      # its slots' words
    E(bl, "c_vspend")
    a.label("kn_x")
    E(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)
    a.label("kn_q")
    E(raw, GP.popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    E(b_w, prev["knob"])

    # ---- c_vsclamp(r0) -> 0..127
    a.label("c_vsclamp")
    E(cmp_imm, 0, 0)
    E(b_cond, "vc_h", "ge")
    E(movs_imm, 0, 0)
    a.label("vc_h")
    E(cmp_imm, 0, 127)
    E(b_cond, "vc_x", "le")
    E(movs_imm, 0, 127)
    a.label("vc_x")
    E(raw, h(0x4770))

    # ---- c_vspend(r0 = track): its slots' words pending; clobbers r0-r3
    a.label("c_vspend")
    E(push_list, [4, 5], lr=True)
    E(adds_imm8, 0, 1)
    E(mov_reg, 4, 0)
    E(movs_imm, 5, 0)
    a.label("vd_l")
    E(bl, L["c_syb"])
    E(cmp_imm, 0, 0)
    E(b_cond, "vd_x", "eq")
    E(movs_imm, 1, SY.SL)
    E(muls, 1, 5)
    E(adds_reg, 0, 0, 1)
    E(ldrb_imm, 0, 0, 2)
    E(cmp_reg, 0, 4)
    E(b_cond, "vd_n", "ne")
    E(mov_reg, 0, 5)
    E(bl, L["c_sypend"])
    a.label("vd_n")
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, ES.NSL)
    E(b_cond, "vd_l", "lo")
    a.label("vd_x")
    E(pop_list, [4, 5], pc=True)

    # ---- c_vsled (the LED task's calls: ctrl, frame): the chain; the menu's pads moved; our pages' knobs
    a.label("c_vsled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)                                                      # r5 = the frame
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(bl, L["c_gpmopen"])
    E(cmp_imm, 0, 8)
    bc("ld_k", "hs")
    E(mov_reg, 4, 0)                                                      # the menu: r4 = its track
    E(bl, L["c_eseng"])
    E(mov_reg, 6, 0)                                                      # r6 = its engine
    E(mov_reg, 0, 4)
    E(bl, "c_vspage")
    E(mov_reg, 7, 0)                                                      # r7 = our page
    E(raw, h(0xB088))                                                     # sub sp, #32: the old menu's 16 LEDs
    E(movs_imm, 0, 0)
    a.label("lm_c")
    E(lsls_imm, 1, 0, 1)
    E(raw, h(0x5A6A))                                                     # ldrh r2, [r5, r1]
    E(raw, h(0xAB00))                                                     # add r3, sp, #0
    E(raw, h(0x525A))                                                     # strh r2, [r3, r1]
    E(movs_imm, 2, 0)
    E(raw, h(0x526A))                                                     # strh r2, [r5, r1]: dark
    E(adds_imm8, 0, 1)
    E(cmp_imm, 0, 16)
    E(b_cond, "lm_c", "lo")

    def old(o, new):                                                      # frame[new] = the old LED o
        E(raw, h(0x4668))                                                 # mov r0, sp
        E(raw, h(0x8800 | o << 6))                                        # ldrh r0, [r0, #2 o]
        E(strh_imm, 0, 5, 2 * new)
    E(bl, L["c_spshift"])                                                 # pad 1: the sequenceable (Shift: the non-sequenceable)
    E(cmp_imm, 0, 0)
    E(b_cond, "lm_ns", "ne")
    old(OLD_SEQ, 0)
    E(b, "lm_1")
    a.label("lm_ns")
    old(OLD_NSEQ, 0)
    a.label("lm_1")
    for new, o in ((5, OLD_MX), (9, OLD_SP), (15, OLD_INIT)):
        old(o, new)
    # pad 2 the sound's page, pad 3 OSC 2 / the pitch envelope; pad 9 stock
    E(cmp_imm, 6, ES.E_GR)
    E(b_cond, "lm_2a", "ne")
    old(OLD_GRAN, 1)
    E(b, "lm_9")
    a.label("lm_2a")
    E(cmp_imm, 6, ES.E_VA)
    E(b_cond, "lm_2f", "eq")
    E(cmp_imm, 6, ES.E_FM)
    E(b_cond, "lm_2f", "eq")
    old(OLD_STOCK, 1)                                                     # sample / line: stock
    E(b, "lm_9")
    a.label("lm_2f")
    E(mov_reg, 0, 4)
    E(bl, L["c_sypage"])
    E(movs_imm, 1, SY.UI_DIM)                                             # synth: OSC 1 (VA) / operators (FM) on pad 2, OSC 2 / pitch env on 3
    E(movs_imm, 2, SY.UI_DIM)
    E(cmp_imm, 0, 0)
    E(b_cond, "lm_2w", "eq")
    E(cmp_imm, 6, ES.E_FM)
    E(b_cond, "lm_2v", "eq")
    E(movs_imm, 1, SY.UI_KNOB)
    E(cmp_imm, 7, VP_OSC2)
    E(b_cond, "lm_2w", "ne")
    E(movs_imm, 1, SY.UI_DIM)
    E(movs_imm, 2, SY.UI_KNOB)
    E(b, "lm_2w")
    a.label("lm_2v")
    E(push_list, [1, 2])
    E(bl, L["c_f8ram"])
    E(ldrb_imm, 3, 0, L["F8_SEL"])
    E(pop_list, [1, 2])
    E(movs_imm, 1, SY.UI_KNOB)
    E(cmp_imm, 3, 8)
    E(b_cond, "lm_2w", "ne")
    E(movs_imm, 1, SY.UI_DIM)
    E(movs_imm, 2, SY.UI_KNOB)
    a.label("lm_2w")
    E(strh_imm, 1, 5, 2 * 1)
    E(strh_imm, 2, 5, 2 * 2)
    a.label("lm_9")
    old(OLD_STOCK, 8)
    E(cmp_imm, 7, VP_FILT)                                                # (our stock-page pages: pad 9 dim)
    E(b_cond, "lm_9d", "eq")
    E(cmp_imm, 7, VP_MOD)
    E(b_cond, "lm_9n", "ne")
    a.label("lm_9d")
    E(movs_imm, 0, DIM_STOCK)
    E(strh_imm, 0, 5, 2 * 8)
    a.label("lm_9n")
    for new, vp, col, dim in ((3, VP_FILT, COL_FILT, DIM_FILT), (4, VP_MOD, COL_MOD, DIM_MOD)):
        E(movs_imm, 0, dim)
        E(cmp_imm, 7, vp)
        E(b_cond, f"lm_p{new}", "ne")
        E(movs_imm, 0, col)
        a.label(f"lm_p{new}")
        E(strh_imm, 0, 5, 2 * new)
    E(raw, h(0xB008))                                                     # add sp, #32
    a.label("ld_k")
    E(bl, "c_vsknobled")
    a.label("ld_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)

    # ---- c_vsknobled (r5 = the frame): our pages' knobs on the track views
    a.label("c_vsknobled")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(bl, L["c_spview"])
    E(cmp_imm, 0, 8)
    bc("kl_x", "hs")
    E(mov_reg, 4, 0)
    E(bl, "c_vspage")
    E(cmp_imm, 0, 0)
    bc("kl_x", "eq")
    E(mov_reg, 6, 0)                                                      # r6 = our page
    E(bl, L["c_rst"])
    E(movw, 1, SY.O_KB)
    E(adds_reg, 7, 0, 1)                                                  # r7 = kbright's overlay
    E(movs_imm, 0, 0xFF)
    E(strb_imm, 0, 7, SP.K_MASK)
    E(movs_imm, 0, 0)
    for k in range(8):
        E(strb_imm, 0, 7, SP.K_VAL + k)
        E(strh_imm, 0, 7, SP.K_CODE + 2 * k)
    E(push_list, [5])
    E(movs_imm, 5, 0)                                                     # r5 = k
    a.label("kl_l")
    E(bl, "c_vskv")                                                       # r0 = the value (0..127), r1 = its code (0 = dark, bit 15 left)
    E(adds_reg, 2, 7, 5)
    E(strb_imm, 0, 2, SP.K_VAL)
    E(lsls_imm, 2, 5, 1)
    E(adds_reg, 2, 2, 7)
    E(strh_imm, 1, 2, SP.K_CODE)
    E(lsls_imm, 1, 1, 17)
    E(lsrs_imm, 1, 1, 17)
    E(ldr_sp, 3, 0)
    E(lsls_imm, 2, 5, 1)
    E(adds_reg, 2, 2, 3)
    E(strh_w_imm, 1, 2, 2 * SP.LED_KNOB0)
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, 8)
    E(b_cond, "kl_l", "lo")
    E(pop_list, [5])
    a.label("kl_x")
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_vskv (r4 = track, r5 = k, r6 = our page) -> r0 = the knob's brightness value, r1 = its colour code (bit 15: the left half)
    a.label("c_vskv")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(cmp_imm, 6, VP_FILT)
    bc("kv_m", "ne")
    E(cmp_imm, 5, 0)                                                      # Filter / VCA
    E(b_cond, "kv_f1", "ne")
    imm32(0, LEVELS)
    E(mov_reg, 1, 4)
    E(bl, L["c_cinew"])
    E(movs_imm, 1, COL_FILT)
    E(pop_list, [4, 5, 6, 7], pc=True)
    a.label("kv_f1")
    E(cmp_imm, 5, 4)
    E(b_cond, "kv_f2", "ne")
    E(mov_reg, 0, 4)                                                      # K5: the envelope -> low-pass (bipolar)
    E(movs_imm, 1, 3)
    E(bl, L["c_evget"])
    E(cmp_imm, 1, 0)
    bc("kv_0", "eq")
    E(movs_imm, 6, COL_FILT)
    E(b, "kv_bip")
    a.label("kv_f2")
    E(cmp_imm, 5, 3)
    E(b_cond, "kv_fs", "eq")
    E(cmp_imm, 5, 5)
    bc("kv_0", "lo")
    a.label("kv_fs")
    E(adds_imm8, 4, 0x10)                                                 # K4, K6-K8: the stock's value (group 0x10 + t, 6 + k)
    E(mov_reg, 0, 4)
    E(adds_imm8, 5, 6)
    E(mov_reg, 1, 5)
    E(bl, GETTER)
    E(movs_imm, 1, COL_FILT)
    E(pop_list, [4, 5, 6, 7], pc=True)
    a.label("kv_m")
    E(cmp_imm, 6, VP_MOD)
    bc("kv_o", "ne")
    E(cmp_imm, 5, 4)                                                      # Envelope + LFO
    E(b_cond, "kv_ms", "hs")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, L["c_evget"])
    E(cmp_imm, 1, 0)
    bc("kv_0", "eq")
    E(movs_imm, 6, COL_MOD)
    E(cmp_imm, 5, 2)
    bc("kv_bip", "hs")
    E(movs_imm, 1, COL_MOD)
    E(pop_list, [4, 5, 6, 7], pc=True)
    a.label("kv_ms")
    E(cmp_imm, 5, 6)
    bc("kv_0", "hs")
    E(mov_reg, 0, 4)
    E(subs_imm8, 5, 2)
    E(mov_reg, 1, 5)
    E(bl, L["c_spval"])
    E(lsrs_imm, 0, 0, 7)                                                  # (14 bits)
    E(movs_imm, 6, SP.UI_KNOB)
    E(cmp_imm, 5, 2)
    bc("kv_bip", "eq")                                                    # K3: from the centre
    E(movs_imm, 1, SP.UI_KNOB)
    E(pop_list, [4, 5, 6, 7], pc=True)
    a.label("kv_o")                                                       # OSC 1 / OSC 2
    E(bl, L["c_spshift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "kv_on", "eq")
    E(adds_imm8, 5, 8)
    a.label("kv_on")
    imm32(0, T["osc2"])
    E(cmp_imm, 6, VP_OSC2)
    E(b_cond, "kv_ot", "eq")
    imm32(0, T["osc1"])
    a.label("kv_ot")
    E(ldrb_reg, 5, 0, 5)                                                  # r5 = the target
    E(cmp_imm, 5, 0xFF)
    bc("kv_0", "eq")
    E(movs_imm, 6, SY.UI_KNOB)
    E(cmp_imm, 5, K_EXT)
    E(b_cond, "kv_oe", "lo")
    E(mov_reg, 0, 4)                                                      # ours: bipolar
    E(subs_imm8, 5, K_EXT)
    E(mov_reg, 1, 5)
    E(bl, "c_vsextv")
    E(ldrb_imm, 0, 0, 0)
    E(movs_imm, 1, 64)
    E(raw, h(0x4048))
    E(b, "kv_bip")
    a.label("kv_oe")
    E(mov_reg, 0, 4)
    E(bl, L["c_syslot"])
    E(cmp_imm, 0, ES.NSL)
    bc("kv_0", "hs")
    E(mov_reg, 1, 5)
    E(bl, L["c_syv"])                                                     # r0 = its value
    E(cmp_imm, 5, 0)                                                      # the waves: the nearest one's colour
    E(b_cond, "kv_w", "eq")
    E(cmp_imm, 5, 2)
    E(b_cond, "kv_w", "eq")
    E(cmp_imm, 5, 6)                                                      # sync + bitwise: its zones
    E(b_cond, "kv_z", "eq")
    imm32(1, T["bip"])
    E(ldrb_reg, 1, 1, 5)
    E(cmp_imm, 1, 0)
    E(b_cond, "kv_bip", "ne")
    E(movs_imm, 1, SY.UI_KNOB)
    E(pop_list, [4, 5, 6, 7], pc=True)
    a.label("kv_w")
    E(adds_imm8, 0, 21)
    E(movs_imm, 1, 42)
    E(raw, h(0xFBB0) + h(0xF0F1))                                         # udiv r0, r0, r1
    imm32(1, T["waves"])
    E(ldrb_reg, 1, 1, 0)
    E(movs_imm, 0, 127)
    E(pop_list, [4, 5, 6, 7], pc=True)
    a.label("kv_z")
    E(movs_imm, 1, 7)                                                     # zone (7 v) >> 7, its position (7 v) & 127 -> 24 + pos x 13 / 16
    E(muls, 0, 1)
    E(lsrs_imm, 1, 0, 7)
    E(movs_imm, 2, 127)
    E(ands_reg, 0, 2)
    E(movs_imm, 2, 13)
    E(muls, 0, 2)
    E(lsrs_imm, 0, 0, 4)
    E(adds_imm8, 0, 24)
    imm32(2, T["zones"])
    E(ldrb_reg, 1, 2, 1)
    E(cmp_imm, 1, 0)
    E(b_cond, "kv_zx", "ne")
    E(movs_imm, 0, 0)
    a.label("kv_zx")
    E(pop_list, [4, 5, 6, 7], pc=True)
    a.label("kv_bip")                                                     # (r0 = v, r6 = the colour) |v - 64| x 2, the left half lighter
    E(subs_imm8, 0, 64)
    E(mov_reg, 1, 6)
    E(b_cond, "kv_bp", "ge")
    E(raw, h(0x4240))                                                     # rsbs r0, r0
    E(movw, 2, SY.KB_LEFT)
    E(orrs_reg, 1, 2)
    a.label("kv_bp")
    E(lsls_imm, 0, 0, 1)
    E(cmp_imm, 0, 127)
    E(b_cond, "kv_bx", "le")
    E(movs_imm, 0, 127)
    a.label("kv_bx")
    E(pop_list, [4, 5, 6, 7], pc=True)
    a.label("kv_0")
    E(movs_imm, 0, 0)
    E(movs_imm, 1, 0)
    E(pop_list, [4, 5, 6, 7], pc=True)
    return a.assemble(), T


def install(img, report, base_addr):
    """Our heads in front of the pad press / release, the knob slot and the LED calls; synthpage's c_syext stub -> c_vsext.  Needs esel,
    synthpage (OPT vmode), envpage, stockplus, granpage menu2, modmx, autoinit, fm8page."""
    import struct
    import fm8page as F8
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]                 # noqa: E731
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    assert "esel" in report and ES.ESR + EXT0 + 8 * NEXT <= ES.ESR + 128
    import dspz
    assert dspz.S + 20 <= VSR and VSR + VSR_LEN <= 0x2004EE60
    L = dict(c_rst=lab("rhstate", "c_rst"), c_rram=lab("rhstate", "c_rram"), c_ciok=lab("countin", "c_ciok"),
             c_cinew=lab("countin", "c_cinew"), c_spshift=lab("stockplus", "c_spshift"), c_spheld=lab("stockplus", "c_spheld"),
             c_spview=lab("stockplus", "c_spview"), c_spval=lab("stockplus", "c_spval"), c_gpmopen=lab("granpage", "c_gpmopen"),
             c_sypage=lab("synthpage", "c_sypage"), c_syslot=lab("synthpage", "c_syslot"), c_syb=lab("synthpage", "c_syb"),
             c_syv=lab("synthpage", "c_syv"), c_sypend=lab("synthpage", "c_sypend"), c_evget=lab("envpage", "c_evget"),
             c_eseng=lab("esel", "c_eseng"), c_esram=lab("esel", "c_esram"), c_f8ram=lab("fm8page", "c_f8ram"), F8_SEL=F8.O_SEL)
    prev = dict(pad=rhbuild.bw_target(img, GP.PP_ENTRY), rel=rhbuild.bw_target(img, GP.PR_ENTRY), knob=u(SY.SLOT_KNOB) & ~1,
                ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    (code_, labels), T = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code_
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, GP.PP_ENTRY, f"b.w #{prev['pad']:#x}", b_w(GP.PP_ENTRY, labels["c_vspad"]))
    rhbuild.patch(img, GP.PR_ENTRY, f"b.w #{prev['rel']:#x}", b_w(GP.PR_ENTRY, labels["c_vsrel"]))
    rhbuild.patch_word(img, SY.SLOT_KNOB, prev["knob"] | 1, labels["c_vsknob"] | 1)
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_vsled"]))
    stub = lab("synthpage", "c_syext")                                         # synthpage's stub (movs r0, #0; bx lr) -> b.w c_vsext
    rhbuild.patch(img, stub, "movs r0, #0|bx lr", b_w(stub, labels["c_vsext"]))
    report["vsel"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")},
                          tables={k: hex(v) for k, v in T.items()}, ram=hex(VSR))
    return labels, code_
