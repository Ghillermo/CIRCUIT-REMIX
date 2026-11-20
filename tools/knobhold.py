"""Knob hold (MIT; RH102; CIRCUIT-HACKS' knobhold of SC56.7 / Beta 5.52, rewritten for the Circuit Rhythm 5706).  The user (Hacks, 2026-11-12):
«Al mover un knob mientras se cambia de vista, el knob retiene su asignación anterior hasta que se deja de tocar durante un segundo», «Retén
[páginas] internas.  Shift no afecta al knob hasta que termine el segundo», «El comportamiento completo "retener knob" se activa o desactiva en
Setup»; for Remix (2026-11-14): «do your choices, we'll change the interface later if needed».

The stock of the Rhythm (read in its image, run on the RAM dump):
  * a knob turn = the input dispatcher 0x0804015E -> word 4 of the controller's vtable (0x080672F4 = 0x0803DDE1): 0x0803DDE0(ctrl, knob,
    delta), which hands it to the view on the screen ([ctrl + 0x7C], or the Setup view [ctrl + 0x78]) and its slot 4; clrtrk's direct
    `bl 0x0803DDE0` (Clear + track) and the older tests do not go through the vtable word;
  * what a knob does then depends on a few bytes of state: the view word, the global mode (p0 of [ctrl + 0x14]), Shift (p0 of [ctrl + 0xC]),
    the container's track (p0 of [cont + 0x25C]) and mode (byte cont + 0x264), the Mixer's page (the store embedded at Mixer + 0x68), the FX
    view's page (p0 of [0x2004DAA0 + 0x20]), Advanced Setup (byte 0x2004E434), the Sidechain view's track ([[0x20048E90 + 0x2C] + 0x14]), the
    Grid FX held slot (p0 of the store 0x20043820, 0xFF = none, and fxseq's byte 0x20043894, 0x10 = none), and our pages (Stock+, the menu's
    Granular / Envelope pages, the Synth page, vsel's page per track, modmx's page per track, the FM page / its operator / its track, esel's
    pad 16 dropdown, the cue mode);
  * a store (0x0803FC58 / 0x0803FC6C / 0x0803FD26 / 0x0803FBEC) keeps two banks of each parameter: [s + 0xC] / [s + 0x10] = the banks'
    arrays, [s + 4] bit i = the current bank of parameter i, [s + 8] bit i = dirty (FC6C reads the other bank then).

Ours (OPT knobhold; the switch on Setup pad 23, settings p4 byte 1 = 0xC7):
  * the controller's vtable word -> c_khknob: the first turn of a knob (0..7) after a second untouched (the HAL tick) takes a snapshot of those
    cells (the view word and 21 bytes) into one of two snapshot slots and passes; while it keeps turning (< 1 s between events) and the state
    differs from its snapshot, the event runs the stock's knob path with the snapshot written in (both banks of a store) and the current state
    put back after (the reverse order: the per-track cells follow the track cell); what the call wrote into those cells is discarded;
  * a Grid FX slot held at the snapshot and released (or another) since: the event is swallowed (no edit of a slot that is not held);
  * pass-through: knob >= 8, without c_ciok or our RAM, the switch off, Clear held (bit 23 of [ctrl + 0xA0]), a third knob with both slots
    taken, or a nested call (busy: the check is made before anything is stashed);
  * nothing of ours on the stack while the stock's knob path runs: the entry's registers and LR in RAM (the UI task's stack, RH99);
  * the knob LEDs: the output stage's call 0x0803E802 (kbright's c_kbout) -> c_khout: kbright's, then each knob held with the state changed
    shows the RGB it had in the last frame before (kept in RAM every other frame), and a knob a second idle loses its slot;
  * the switch: Setup (not Advanced, no Shift) pad 23 toggles p4 byte 1 of the unit's settings (0xC7 on, else off; off at the factory: the
    dump's p4 bytes 1-3 are 0), saved by setsave OPT setp4b1 when stopped; its LED (green 0x1E / dim 0x1F, the Setup toggles' colours) from
    gmmode's c_gmled through its OPT khsw stub (no new LED head, RH99).
RAM KH = fxseq.FXR + 320 (rhstate's second block, zeroed at each boot: all zero = no hold): + 0 busy, + 1 + k knob k's snapshot slot (0 none,
1 / 2), + 9 a spare byte (the place of a cell whose object is missing), + 10 + 2 k knob k's last event (ms, u16), + 28 / + 32 c_khout's LR and
`out`, + 36 the entry's r0-r2, r4-r7, LR, + 68 + 4 k the kept RGB, + 100 the swap's save (the view word, the cells' bytes, the stores' second
bank), + 132 / + 160 the two snapshots (the view word, the cells' bytes).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b, b_cond, b_w, bl, cmp_imm, cmp_reg, h, ldr_imm, ldrb_imm, ldrh_imm, lsls_imm,  # noqa: E402
                   lsrs_imm, mov_reg, movs_imm, movt, movw, pop_list, push_list, raw, str_imm, strb_imm, strh_imm, subs_imm8, subs_reg)
import countin as CI  # noqa: E402
import cue as CU  # noqa: E402
import esel as ES  # noqa: E402
import fm8page as F8  # noqa: E402
import fxseq as FX  # noqa: E402
import granpage as GP  # noqa: E402
import kbright as KB  # noqa: E402
import midithru as M  # noqa: E402
import modmx as MX  # noqa: E402
import rhstate  # noqa: E402
import stockplus as SP  # noqa: E402
import synthpage as SY  # noqa: E402
import vsel as VS  # noqa: E402

CTRL, CONT = CI.CTRL, 0x20048B9C
STOCK_KNOB, KNOB_VT = 0x0803DDE0, 0x080672F4
SETUP_VT = 0x08067C74
SETTINGS, P_SW, B_SW, SW_ON = M.SETTINGS, 4, 1, 0xC7          # the switch: p4 byte 1 of the unit's settings
GET, WPTR, COMMIT = CI.PARAM_GET, CI.WPTR, CI.COMMIT
HAL_TICK = CI.HAL_TICK
HOLD_MS = 1000
N_KNOBS = 8
PAD = 22                                                      # Setup pad 23
COL_ON, COL_DIM = 0x1E, 0x1F                                  # the Setup / Advanced toggles' green / dim green
CLEAR_BIT = 23                                                # [ctrl + 0xA0]: the buttons held
OUT_CALL = KB.OUT_CALL
LED_KNOB0 = KB.LED_KNOB0

ABS, STORE, PSTORE, DEREF, TRK = 0, 1, 2, 3, 4                # (kind): the byte at the address; p0 of the store whose pointer is at it; p0 of the
#                                                               store at it; the byte at [address] + x; the byte at address + the track
MIXER, FXV, SCV = 0x2004E090, 0x2004DAA0, 0x20048E90
GRIDFX, HELD = 0x20043820, FX.HELD
CELLS = [                                                     # (name, kind, address, x)
    ("mode", STORE, CTRL + 0x14, 0),
    ("shift", STORE, CTRL + 0xC, 0),
    ("track", STORE, CONT + 0x25C, 0),
    ("cmode", ABS, CONT + 0x264, 0),
    ("mixpage", PSTORE, MIXER + 0x68, 0),
    ("fxpage", STORE, FXV + 0x20, 0),
    ("adv", ABS, 0x2004E410 + 0x24, 0),
    ("sctrack", DEREF, SCV + 0x2C, 0x14),
    ("gridfx", PSTORE, GRIDFX, 0),
    ("held", ABS, HELD, 0),
    ("stockplus", ABS, rhstate.ST + rhstate.OFF["stockplus"][0], 0),
    ("menugran", ABS, rhstate.ST2 + GP.MN_O, 0),
    ("menuenv", ABS, rhstate.ST2 + GP.MN_O + SY.M_ENV, 0),
    ("synthpage", ABS, rhstate.ST2 + SY.O + SY.R_PAGE, 0),
    ("vselpage", TRK, VS.VSR + VS.O_VP, 0),
    ("modmxpage", TRK, rhstate.ST2 + MX.O + MX.R_PAGE, 0),
    ("fmopen", ABS, F8.FMR + F8.O_OPEN, 0),
    ("fmsel", ABS, F8.FMR + F8.O_SEL, 0),
    ("fmtrk", ABS, F8.FMR + F8.O_TRK, 0),
    ("h16", ABS, ES.ESR + ES.O_H16, 0),
    ("cue", ABS, rhstate.ST2 + CU.O + CU.R_MODE, 0),
]
NC = len(CELLS)
I_TRACK = [n for n, *_ in CELLS].index("track")
I_GRID = [n for n, *_ in CELLS].index("gridfx")
NSTORE = sum(1 for _, k, *_ in CELLS if k in (STORE, PSTORE))
assert all(k != TRK for _, k, *_ in CELLS[:I_TRACK + 1]), "a per-track cell before the track's"

KH = FX.FXR + 320
O_BUSY, O_SLOT, O_SPARE, O_TIME = 0, 1, 9, 10
O_LLR, O_LOUT, O_STASH, O_KEPT, O_SAVE = 28, 32, 36, 68, 100
O_SNAP, SNAP_LEN = 132, 28
SIZE = O_SNAP + 2 * SNAP_LEN
assert O_SAVE + 4 + NC + NSTORE <= O_SNAP and 4 + NC <= SNAP_LEN and O_TIME + 2 * N_KNOBS <= O_LLR
assert KH % 4 == 0 and KH + SIZE <= FX.FXR + 512, "knobhold: its RAM past FXR + 512"
STM_MASK = 0x40F7                                             # r0-r2, r4-r7, lr
STM_R3, LDM_R3 = h(0xE883) + h(STM_MASK), h(0xE893) + h(STM_MASK)
UXTH = {1: h(0xB289), 2: h(0xB292)}
INV = dict(eq="ne", ne="eq", lo="hs", hs="lo", hi="ls", ls="hi", mi="pl", pl="mi")


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def ram():
    """KH, checked against what is below it in FXR's 512 B (osc1x's 48 B end at FXR + 320)"""
    import osc1x as OX
    assert OX.ram() + 8 * OX.NE <= KH, "knobhold: its RAM over osc1x's"
    return KH


def table():
    out, x = b"", 0
    for name, kind, addr, extra in CELLS:
        if kind in (STORE, PSTORE):
            extra, x = x, x + 1                               # the store's second-bank save index
        out += struct.pack("<IBBH", addr, kind, extra, 0)
    return out


def model_on(p4):
    """the switch from p4's word (the unit's settings)"""
    return (p4 >> 8 & 0xFF) == SW_ON


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit
    zc = [0]

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    def bc(target, cond):
        zc[0] += 1
        n = f"_k{zc[0]}"
        E(b_cond, n, INV[cond])
        E(b, target)
        a.label(n)

    a.label("kh_tab")
    E(raw, table())

    # ---- c_khon() -> r0 = 1 with the switch on (c_ciok, our RAM, p4 byte 1 = 0xC7); clobbers r1-r3
    a.label("c_khon")
    E(push_list, [4], lr=True)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ho_0", "eq")
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ho_0", "eq")
    imm32(0, SETTINGS)
    E(movs_imm, 1, P_SW)
    E(bl, GET)
    E(ldrb_imm, 0, 0, B_SW)
    E(cmp_imm, 0, SW_ON)
    E(b_cond, "ho_0", "ne")
    E(movs_imm, 0, 1)
    E(pop_list, [4], pc=True)
    a.label("ho_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)

    # ---- c_khca(r0 = cell i) -> r0 = its place (bank 0's for a store), r1 = bank 1's (0 if not a store), r2 = the place read now (the
    # current bank), r3 = where the swap keeps bank 1's byte; a missing object = KH's spare byte; clobbers nothing else
    a.label("c_khca")
    E(push_list, [4], lr=True)
    E(lsls_imm, 0, 0, 3)
    imm32(1, base)
    E(adds_reg, 1, 1, 0)
    E(ldrb_imm, 2, 1, 4)                                      # kind
    E(ldrb_imm, 3, 1, 5)                                      # x
    E(ldr_imm, 0, 1, 0)                                       # address
    E(cmp_imm, 2, ABS)
    E(b_cond, "ca_abs", "eq")
    E(cmp_imm, 2, TRK)
    E(b_cond, "ca_trk", "eq")
    E(cmp_imm, 2, DEREF)
    E(b_cond, "ca_der", "eq")
    E(cmp_imm, 2, PSTORE)
    E(b_cond, "ca_st", "eq")
    E(ldr_imm, 0, 0, 0)                                       # STORE: the pointer
    a.label("ca_st")
    E(cmp_imm, 0, 0)
    E(b_cond, "ca_nil", "eq")
    imm32(1, KH + O_SAVE + 4 + NC)
    E(adds_reg, 3, 3, 1)                                      # r3 = bank 1's save byte
    E(ldr_imm, 4, 0, 4)                                       # the banks' bits
    E(ldr_imm, 1, 0, 0x10)
    E(ldr_imm, 0, 0, 0xC)
    E(lsls_imm, 4, 4, 31)                                     # N = parameter 0's bank
    E(mov_reg, 2, 0)
    E(b_cond, "ca_x", "pl")
    E(mov_reg, 2, 1)
    a.label("ca_x")
    E(pop_list, [4], pc=True)
    a.label("ca_der")
    E(ldr_imm, 0, 0, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "ca_nil", "eq")
    E(adds_reg, 0, 0, 3)
    a.label("ca_abs")
    E(movs_imm, 1, 0)
    E(mov_reg, 2, 0)
    E(pop_list, [4], pc=True)
    a.label("ca_nil")
    imm32(0, KH + O_SPARE)
    E(movs_imm, 1, 0)
    E(mov_reg, 2, 0)
    E(pop_list, [4], pc=True)
    a.label("ca_trk")
    E(mov_reg, 4, 0)
    E(movs_imm, 0, I_TRACK)
    E(bl, "c_khca")
    E(ldrb_imm, 3, 2, 0)
    E(lsls_imm, 3, 3, 29)
    E(lsrs_imm, 3, 3, 29)
    E(adds_reg, 0, 4, 3)
    E(movs_imm, 1, 0)
    E(mov_reg, 2, 0)
    E(pop_list, [4], pc=True)

    # ---- c_khsnap(r6 = a snapshot): the view word and the cells (as read now); clobbers r0-r3
    a.label("c_khsnap")
    E(push_list, [7], lr=True)
    imm32(0, CTRL)
    E(ldr_imm, 0, 0, 0x7C)
    E(str_imm, 0, 6, 0)
    E(movs_imm, 7, 0)
    a.label("sn_l")
    E(mov_reg, 0, 7)
    E(bl, "c_khca")
    E(ldrb_imm, 0, 2, 0)
    E(adds_reg, 1, 6, 7)
    E(strb_imm, 0, 1, 4)
    E(adds_imm8, 7, 1)
    E(cmp_imm, 7, NC)
    E(b_cond, "sn_l", "lo")
    E(pop_list, [7], pc=True)

    # ---- c_khcmp(r6 = a snapshot) -> r0 = 0 the same state, 1 changed; clobbers r1-r3
    a.label("c_khcmp")
    E(push_list, [7], lr=True)
    imm32(0, CTRL)
    E(ldr_imm, 0, 0, 0x7C)
    E(ldr_imm, 1, 6, 0)
    E(cmp_reg, 0, 1)
    E(b_cond, "cm_d", "ne")
    E(movs_imm, 7, 0)
    a.label("cm_l")
    E(mov_reg, 0, 7)
    E(bl, "c_khca")
    E(ldrb_imm, 0, 2, 0)
    E(adds_reg, 1, 6, 7)
    E(ldrb_imm, 1, 1, 4)
    E(cmp_reg, 0, 1)
    E(b_cond, "cm_d", "ne")
    E(adds_imm8, 7, 1)
    E(cmp_imm, 7, NC)
    E(b_cond, "cm_l", "lo")
    E(movs_imm, 0, 0)
    E(pop_list, [7], pc=True)
    a.label("cm_d")
    E(movs_imm, 0, 1)
    E(pop_list, [7], pc=True)

    # ---- c_khswap(r6 = a snapshot): the current state to the save, the snapshot written (both banks of a store); clobbers r0-r3
    a.label("c_khswap")
    E(push_list, [4, 5, 7], lr=True)
    imm32(5, KH + O_SAVE)
    imm32(0, CTRL)
    E(ldr_imm, 1, 0, 0x7C)
    E(str_imm, 1, 5, 0)
    E(ldr_imm, 1, 6, 0)
    E(str_imm, 1, 0, 0x7C)
    E(adds_imm8, 5, 4)
    E(movs_imm, 7, 0)
    a.label("sw_l")
    E(mov_reg, 0, 7)
    E(bl, "c_khca")
    E(adds_reg, 2, 5, 7)
    E(ldrb_imm, 4, 0, 0)
    E(strb_imm, 4, 2, 0)                                      # the save: bank 0 / the byte
    E(adds_reg, 2, 6, 7)
    E(ldrb_imm, 4, 2, 4)                                      # the snapshot's byte
    E(strb_imm, 4, 0, 0)
    E(cmp_imm, 1, 0)
    E(b_cond, "sw_n", "eq")
    E(ldrb_imm, 2, 1, 0)
    E(strb_imm, 2, 3, 0)                                      # the save: bank 1
    E(strb_imm, 4, 1, 0)
    a.label("sw_n")
    E(adds_imm8, 7, 1)
    E(cmp_imm, 7, NC)
    E(b_cond, "sw_l", "lo")
    E(pop_list, [4, 5, 7], pc=True)

    # ---- c_khrest: the saved state back, the last cell first (a per-track cell while the track is still the snapshot's); clobbers r0-r3
    a.label("c_khrest")
    E(push_list, [4, 5, 7], lr=True)
    imm32(5, KH + O_SAVE + 4)
    E(movs_imm, 7, NC)
    a.label("rs_l")
    E(subs_imm8, 7, 1)
    E(mov_reg, 0, 7)
    E(bl, "c_khca")
    E(adds_reg, 2, 5, 7)
    E(ldrb_imm, 4, 2, 0)
    E(strb_imm, 4, 0, 0)
    E(cmp_imm, 1, 0)
    E(b_cond, "rs_n", "eq")
    E(ldrb_imm, 4, 3, 0)
    E(strb_imm, 4, 1, 0)
    a.label("rs_n")
    E(cmp_imm, 7, 0)
    E(b_cond, "rs_l", "ne")
    imm32(5, KH + O_SAVE)
    E(ldr_imm, 1, 5, 0)
    imm32(0, CTRL)
    E(str_imm, 1, 0, 0x7C)
    E(pop_list, [4, 5, 7], pc=True)

    # ---- c_khsp(r0 = slot 1 / 2) -> r0 = its snapshot; clobbers r1
    a.label("c_khsp")
    imm32(1, KH + O_SNAP)
    E(cmp_imm, 0, 2)
    E(b_cond, "sp_1", "ne")
    E(adds_imm8, 1, SNAP_LEN)
    a.label("sp_1")
    E(mov_reg, 0, 1)
    E(raw, h(0x4770))

    # ---- c_khfree(r4 = KH, r5 = the knob, r6 = the tick) -> r0 = a snapshot slot no other knob holds (1 / 2), 0 if none; clobbers r1-r3
    a.label("c_khfree")
    E(movs_imm, 0, 1)
    a.label("fr_s")
    E(movs_imm, 1, 0)
    a.label("fr_k")
    E(cmp_reg, 1, 5)
    E(b_cond, "fr_n", "eq")
    E(adds_reg, 2, 4, 1)
    E(ldrb_imm, 2, 2, O_SLOT)
    E(cmp_reg, 2, 0)
    E(b_cond, "fr_n", "ne")
    E(lsls_imm, 2, 1, 1)
    E(adds_reg, 2, 2, 4)
    E(ldrh_imm, 2, 2, O_TIME)
    E(subs_reg, 2, 6, 2)
    E(raw, UXTH[2])
    E(movw, 3, HOLD_MS)
    E(cmp_reg, 2, 3)
    E(b_cond, "fr_u", "lo")
    a.label("fr_n")
    E(adds_imm8, 1, 1)
    E(cmp_imm, 1, N_KNOBS)
    E(b_cond, "fr_k", "lo")
    E(raw, h(0x4770))
    a.label("fr_u")
    E(adds_imm8, 0, 1)
    E(cmp_imm, 0, 3)
    E(b_cond, "fr_s", "lo")
    E(movs_imm, 0, 0)
    E(raw, h(0x4770))

    # ---- c_khknob (the controller's vtable word 4: ctrl, knob, delta).  Busy (a nested call) = the stock's at once, nothing stashed; else
    # the registers and LR to KH + O_STASH: nothing of ours on the stack while the stock's knob path runs
    a.label("c_khknob")
    imm32(3, KH)
    E(ldrb_imm, 3, 3, O_BUSY)
    E(cmp_imm, 3, 0)
    E(b_cond, "kk_go", "eq")
    E(b_w, STOCK_KNOB)
    a.label("kk_go")
    imm32(3, KH + O_STASH)
    E(raw, STM_R3)
    E(cmp_imm, 1, N_KNOBS)
    bc("kk_p", "hs")
    E(bl, "c_khon")
    E(cmp_imm, 0, 0)
    bc("kk_p", "eq")
    imm32(0, CTRL)
    E(raw, h(0xF8D0) + h(0x0000 | 0xA0))                      # ldr.w r0, [r0, #0xa0]: the buttons held
    E(lsls_imm, 0, 0, 31 - CLEAR_BIT)
    bc("kk_p", "mi")                                          # Clear held: Clear + knob at once
    imm32(4, KH)
    E(ldr_imm, 5, 4, O_STASH + 4)                             # r5 = the knob
    imm32(6, HAL_TICK)
    E(ldr_imm, 6, 6, 0)                                       # r6 = the tick
    E(adds_reg, 7, 4, 5)                                      # r7 = KH + the knob (its slot byte at + O_SLOT)
    E(ldrb_imm, 0, 7, O_SLOT)
    E(cmp_imm, 0, 0)
    bc("kk_f", "eq")
    E(lsls_imm, 1, 5, 1)
    E(adds_reg, 1, 1, 4)
    E(ldrh_imm, 2, 1, O_TIME)
    E(strh_imm, 6, 1, O_TIME)
    E(subs_reg, 2, 6, 2)
    E(raw, UXTH[2])
    E(movw, 3, HOLD_MS)
    E(cmp_reg, 2, 3)
    bc("kk_f", "hs")                                          # a second untouched: a fresh snapshot
    E(bl, "c_khsp")
    E(mov_reg, 6, 0)                                          # r6 = its snapshot
    E(bl, "c_khcmp")
    E(cmp_imm, 0, 0)
    bc("kk_p", "eq")                                          # the same state: the stock's
    E(ldrb_imm, 0, 6, 4 + I_GRID)
    E(cmp_imm, 0, 0xFF)
    E(b_cond, "kk_sw", "eq")
    E(movs_imm, 0, I_GRID)                                    # a Grid FX slot held at the snapshot: still that one, or swallowed
    E(bl, "c_khca")
    E(ldrb_imm, 0, 2, 0)
    E(ldrb_imm, 1, 6, 4 + I_GRID)
    E(cmp_reg, 0, 1)
    bc("kk_q", "ne")
    a.label("kk_sw")
    E(movs_imm, 0, 1)
    E(strb_imm, 0, 4, O_BUSY)
    E(bl, "c_khswap")
    imm32(3, KH + O_STASH)
    E(ldr_imm, 0, 3, 0)
    E(ldr_imm, 1, 3, 4)
    E(ldr_imm, 2, 3, 8)
    E(bl, STOCK_KNOB)                                         # (r4 / r6 kept by the callee)
    E(bl, "c_khrest")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 4, O_BUSY)
    a.label("kk_q")
    imm32(3, KH + O_STASH)
    E(raw, LDM_R3)
    E(raw, h(0x4770))
    a.label("kk_f")                                           # fresh: a free slot (or none: no hold), the time, the snapshot
    E(bl, "c_khfree")
    E(strb_imm, 0, 7, O_SLOT)
    E(lsls_imm, 1, 5, 1)
    E(adds_reg, 1, 1, 4)
    E(strh_imm, 6, 1, O_TIME)
    E(cmp_imm, 0, 0)
    E(b_cond, "kk_p", "eq")
    E(bl, "c_khsp")
    E(mov_reg, 6, 0)
    E(bl, "c_khsnap")
    a.label("kk_p")
    imm32(3, KH + O_STASH)
    E(raw, LDM_R3)
    E(b_w, STOCK_KNOB)

    # ---- c_khout (in place of the output stage's call: ctrl, out, frame): kbright's; then a knob held with the state changed shows the RGB
    # of the frame before, the others are kept; a knob a second idle loses its slot.  LR and `out` in RAM (nothing of ours on the stack below)
    a.label("c_khout")
    imm32(3, KH + O_LLR)
    E(raw, h(0xF8C3) + h(0xE000))                             # str.w lr, [r3]
    E(str_imm, 1, 3, 4)
    E(bl, prev["out"])
    E(push_list, [4, 5, 6, 7])
    E(bl, "c_khon")
    E(cmp_imm, 0, 0)
    bc("lo_x", "eq")
    imm32(4, KH)
    imm32(5, HAL_TICK)
    E(ldr_imm, 5, 5, 0)
    E(movs_imm, 7, 0)
    a.label("lo_l")
    E(adds_reg, 0, 4, 7)
    E(ldrb_imm, 0, 0, O_SLOT)
    E(cmp_imm, 0, 0)
    E(b_cond, "lo_k", "eq")
    E(lsls_imm, 1, 7, 1)
    E(adds_reg, 1, 1, 4)
    E(ldrh_imm, 1, 1, O_TIME)
    E(subs_reg, 1, 5, 1)
    E(raw, UXTH[1])
    E(movw, 2, HOLD_MS)
    E(cmp_reg, 1, 2)
    E(b_cond, "lo_h", "lo")
    E(adds_reg, 1, 4, 7)
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 1, O_SLOT)                                 # idle a second: no slot
    E(b, "lo_k")
    a.label("lo_h")
    E(bl, "c_khsp")
    E(mov_reg, 6, 0)
    E(bl, "c_khcmp")
    E(cmp_imm, 0, 0)
    E(b_cond, "lo_k", "eq")
    E(bl, "lo_ad")
    E(ldr_imm, 2, 1, 0)
    E(str_imm, 2, 0, 0)                                       # held, changed: the kept RGB
    E(b, "lo_n")
    a.label("lo_k")
    E(bl, "lo_ad")
    E(ldr_imm, 2, 0, 0)
    E(str_imm, 2, 1, 0)                                       # else: kept
    a.label("lo_n")
    E(adds_imm8, 7, 1)
    E(cmp_imm, 7, N_KNOBS)
    E(b_cond, "lo_l", "lo")
    a.label("lo_x")
    E(pop_list, [4, 5, 6, 7])
    imm32(3, KH + O_LLR)
    E(raw, h(0xF8D3) + h(0xF000))                             # ldr.w pc, [r3]
    a.label("lo_ad")                                          # r0 = &out[60 + k], r1 = &kept[k] (r7 = k); clobbers r2
    imm32(0, KH + O_LOUT)
    E(ldr_imm, 0, 0, 0)
    E(lsls_imm, 1, 7, 2)
    E(adds_reg, 0, 0, 1)
    E(adds_imm8, 0, 4 * LED_KNOB0)
    imm32(2, KH + O_KEPT)
    E(adds_reg, 1, 1, 2)
    E(raw, h(0x4770))

    # ---- c_khpad (the Setup view's slot 0: view, pad, velocity): the normal page (not Advanced), no Shift, pad 23 = the switch
    a.label("c_khpad")
    E(cmp_imm, 1, PAD)
    E(b_cond, "kp_s", "ne")
    E(push_list, [0, 1, 2, 3, 4], lr=True)
    E(raw, h(0xF890) + h(0x3024))                             # ldrb.w r3, [r0, #0x24]
    E(cmp_imm, 3, 0)
    E(b_cond, "kp_p", "ne")                                   # Advanced: the chain's
    E(bl, L["c_cishift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "kp_p", "ne")                                   # Shift: the chain's
    imm32(0, SETTINGS)
    E(movs_imm, 1, P_SW)
    E(bl, WPTR)
    E(ldrb_imm, 1, 0, B_SW)
    E(movs_imm, 2, SW_ON)
    E(cmp_imm, 1, SW_ON)
    E(b_cond, "kp_w", "ne")
    E(movs_imm, 2, 0)
    a.label("kp_w")
    E(strb_imm, 2, 0, B_SW)
    imm32(0, SETTINGS)
    E(bl, COMMIT)
    E(pop_list, [0, 1, 2, 3, 4], pc=True)
    a.label("kp_p")
    E(raw, popw([0, 1, 2, 3, 4], lr=True))
    a.label("kp_s")
    E(b_w, prev["pad"])

    # ---- c_khsw(r0 = the frame) (gmmode's c_gmled stub, on the normal Setup page): pad 23 green / dim green; clobbers r0-r3
    a.label("c_khsw")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_khon")
    E(movs_imm, 1, COL_DIM)
    E(cmp_imm, 0, 0)
    E(b_cond, "ks_w", "eq")
    E(movs_imm, 1, COL_ON)
    a.label("ks_w")
    E(strh_imm, 1, 4, 2 * PAD)
    E(pop_list, [4], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; the controller's vtable word 4, the head of the Setup view's slot 0, the output stage's call, gmmode's khsw stub.
    Needs countin, rhstate ram2, kbright, gmmode with OPT khsw, setsave with OPT setp4b1."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]                 # noqa: E731
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    assert rhbuild.OPT.get("knobhold") and rhbuild.OPT.get("khsw") and rhbuild.OPT.get("setp4b1")
    assert base_addr % 4 == 0
    ram()
    L = dict(c_ciok=lab("countin", "c_ciok"), c_cishift=lab("countin", "c_cishift"), c_rram=lab("rhstate", "c_rram"))
    stub = lab("gmmode", "c_gmkh")
    prev = dict(pad=u(SETUP_VT) & ~1, out=rhbuild.bl_target(img, OUT_CALL))
    assert prev["out"] == lab("kbright", "c_kbout"), "knobhold: the output stage's call is not kbright's"
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch_word(img, KNOB_VT, STOCK_KNOB | 1, labels["c_khknob"] | 1)
    rhbuild.patch_word(img, SETUP_VT, prev["pad"] | 1, labels["c_khpad"] | 1)
    rhbuild.patch(img, OUT_CALL, f"bl #{prev['out']:#x}", bl(OUT_CALL, labels["c_khout"]))
    rhbuild.patch(img, stub, "nop|bx lr", b_w(stub, labels["c_khsw"]))
    report["knobhold"] = dict(prev={k: hex(v) for k, v in prev.items()}, ram=hex(KH), size=SIZE,
                              labels={k: hex(v) for k, v in labels.items() if k.startswith("c_") or k == "kh_tab"})
    return labels, code
