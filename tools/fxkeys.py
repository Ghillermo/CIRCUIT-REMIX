"""The FX view's keys and Shift + knob parameters (MIT; CIRCUIT-HACKS' fxkeys (SC17.5 / SC17.6 / SC19) and fxparams (SC21.2), for the Circuit
Rhythm 5706).  The user (2026-10-19): «Faltan también todos los controles y accesos directos de la vista FX».

The stock of the Rhythm (read in the firmware and on the RAM dump, emulated):
  * the FX view = 0x2004DAA0 (vtable 0x08067990), the Tracks' FX view: two sub-views of the eight knobs, [+ 0xC] = the delay sends (shown when
    p0 of the store [+ 0x20] = 1), [+ 0x10] = the reverb sends (p0 = 0); a knob = parameter 0x13 (delay send) / 0x12 (reverb send) of the group
    0x10 + t; the only way to change the page is to touch a preset: pads 1-16 = delay presets (page 1), 17-24 = reverb presets (page 0);
  * the project group 0x20: 0..2 reverb type, decay, damping; 3..8 delay time, sync, feedback, width, ratio, slew (the order the DSP senders read
    them, 0x0803087A / 0x080308D8, as the Tracks' 8..10 / 19..24); the master group 0x21: 0 the master filter, 1 its resonance (0x08030CF0);
  * in the FX view Shift + knob = the plain knob; ▼ / ▲ (19 / 20), Shift + ▼ / ▲ and Duplicate (24) do nothing (their LEDs dark).

Ours, in the FX view only:
  * ▲ = the delay sends, ▼ = the reverb sends (the page store, as a preset pad sets it, without changing the preset); LED of the page shown white,
    the other dim;
  * Shift + knob = the page's parameters: delay K1 time, K2 sync (0-35), K3 feedback, K4 width, K5 ratio (0-12), K6 slew; reverb K1 type (0-5),
    K2 decay, K3 damping; stepped ones one step a click; through the stock's setter (store, DSP, MIDI out; saved with the project as a preset's);
    with Shift held the knob LEDs of those parameters lit in the page's colour, the others dark;
  * Duplicate = reset: the delay and reverb sends of the eight tracks to 0, the master filter to the centre (64);
  * Shift + ▲ / ▼ = the master filter's resonance up / down by 16.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b, b_cond, b_w, bl, cmp_imm, cmp_reg, h, ldr_imm, ldr_sp, ldrb_imm, ldrb_reg, lsls_imm,  # noqa: E402
                   mov_reg, movs_imm, movt, movw, pop_list, push_list, raw, strb_imm, strh_w_imm, subs_imm8)
import countin as CI  # noqa: E402
import rhstate  # noqa: E402
import sckn as SK  # noqa: E402

CTRL = CI.CTRL
FXV, FX_VT = 0x2004DAA0, 0x08067990
SLOT_KNOB = FX_VT + 0x10
O_PAGE = 0x20
PAGE_DELAY, PAGE_REVERB = 1, 0
BTN_DOWN, BTN_UP, BTN_DUP = 19, 20, 24
LED_DOWN, LED_UP = 51, 52
LED_KNOB0 = 60
GRP_PROJ, GRP_MASTER, GRP_TRACK = 0x20, 0x21, 0x10
IDX_REV_SEND, IDX_DEL_SEND = 0x12, 0x13
IDX_FILTER, IDX_RES, FILTER_MID, RES_STEP = 0, 1, 64, 16
WPTR, COMMIT = 0x0803FD26, 0x0803FBEC
# (index, maximum) per knob: delay K1..K6, reverb K1..K3
DELAY = ((3, 127), (4, 35), (5, 127), (6, 127), (7, 12), (8, 127))
REVERB = ((0, 5), (1, 127), (2, 127))
COL_DELAY, COL_REVERB = 0x139, 0x141                  # the stock's knob colours of the two pages
COL_ON, COL_DIM = 0x01, 0x09
INV = SK.INV
BRIGHT = False                                        # RH22 (install(bright=True)): with Shift the parameters' values as brightness (kbright)
COLS = False                                          # RH23 (install(cols=True)): the user, 2026-10-19: «octave keys on fx view dont change color,
COL_DEL_ON, COL_DEL_DIM = 0x74, 0x75                  #   duplicate light either»: up = the delay presets' peach, down = the reverb presets' cream
COL_REV_ON, COL_REV_DIM = 0x29, 0x2A                  #   (the page shown bright, the other dim), Duplicate (the reset) light blue, with Shift
COL_RESET, COL_SHIFT = 0x18, 0x2F                     #   up / down yellow (Shift + up / down = the resonance); CIRCUIT-HACKS' SC18.2 colours
LED_DUP = 56
VIEWSET = False                                       # RH30 (install(viewset=True)): the reset also writes the sends' view stores, which the knob LEDs
GSET, GSET_OBJ = 0x08038A08, 0x20011998               #   read (the user: «Duplicate. -> works, leds dont update»): the stock's knob calls the generic
ID_REV0, ID_DEL0 = 0x80, 0x88                         #   0x08038A08(0x20011998, id, value) (reverb 0x80 + t, delay 0x88 + t), which writes only those
                                                      #   stores (its value is the group setter's, called as before)


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
        n = f"_f{zc[0]}"
        E(b_cond, n, INV[cond])
        E(b, target)
        a.label(n)

    t_par = base                                                          # 2 bytes a knob (index, maximum): delay K1..K8, reverb K1..K8 (0xFF = none)
    tab = bytearray()
    for page in (DELAY, REVERB):
        for k in range(8):
            tab += bytes(page[k]) if k < len(page) else b"\xFF\x00"
    E(raw, bytes(tab))

    # ---- c_fxon() -> r0 = 1 when the FX view is the active view (and the controller is the dump's); clobbers r1-r3
    a.label("c_fxon")
    E(push_list, [4], lr=True)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "fo_x", "eq")
    imm32(0, CTRL)
    E(ldr_imm, 1, 0, 0x7C)
    imm32(0, FXV)
    E(cmp_reg, 0, 1)
    E(b_cond, "fo_0", "ne")
    E(movs_imm, 0, 1)
    E(pop_list, [4], pc=True)
    a.label("fo_0")
    E(movs_imm, 0, 0)
    a.label("fo_x")
    E(pop_list, [4], pc=True)

    # ---- c_fxpage() -> r0 = the page shown (1 delay, 0 reverb); clobbers r1-r3
    a.label("c_fxpage")
    imm32(0, FXV)
    E(ldr_imm, 0, 0, O_PAGE)
    E(movs_imm, 1, 0)
    E(b_w, L["c_cinew"])

    # ---- c_fxsetpage(r0 = page): the page store, as a preset pad writes it (its listeners redraw the view); clobbers r0-r3
    a.label("c_fxsetpage")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 5, 0)
    imm32(0, FXV)
    E(ldr_imm, 4, 0, O_PAGE)
    E(mov_reg, 0, 4)
    E(movs_imm, 1, 0)
    E(bl, WPTR)
    E(strb_imm, 5, 0, 0)
    E(mov_reg, 0, 4)
    E(bl, COMMIT)
    E(pop_list, [4, 5], pc=True)

    # ---- c_fxset(r1 = group, r2 = index, r3 = value): the stock's setter; clobbers r0-r3, r12
    a.label("c_fxset")
    imm32(0, SK.SET_OBJ)
    E(b_w, SK.SETTER)

    # ---- c_fxget(r0 = group, r1 = index) -> r0 = its value; clobbers r1-r3
    a.label("c_fxget")
    E(push_list, [4], lr=True)
    E(bl, SK.GETTER)
    E(movs_imm, 1, 0x7F)
    E(raw, h(0x4008))                                                     # ands r0, r1
    E(pop_list, [4], pc=True)

    # ---- c_fxbtn (the head of the button chain: ctrl, button)
    a.label("c_fxbtn")
    E(cmp_imm, 1, BTN_DOWN)
    E(b_cond, "fb_in", "eq")
    E(cmp_imm, 1, BTN_UP)
    E(b_cond, "fb_in", "eq")
    E(cmp_imm, 1, BTN_DUP)
    E(b_cond, "fb_in", "eq")
    E(b_w, prev["btn"])
    a.label("fb_in")
    E(push_list, [0, 1, 4, 5, 6, 7], lr=True)
    E(bl, "c_fxon")
    E(cmp_imm, 0, 0)
    bc("fb_c", "eq")
    E(ldr_sp, 4, 4)                                                       # r4 = the button
    E(bl, L["c_cishift"])
    E(mov_reg, 5, 0)                                                      # r5 = Shift
    E(cmp_imm, 4, BTN_DUP)
    bc("fb_dup", "eq")
    E(cmp_imm, 5, 0)
    bc("fb_res", "ne")
    E(movs_imm, 0, PAGE_REVERB)                                           # ▼ reverb / ▲ delay
    E(cmp_imm, 4, BTN_UP)
    E(b_cond, "fb_p", "ne")
    E(movs_imm, 0, PAGE_DELAY)
    a.label("fb_p")
    E(bl, "c_fxsetpage")
    E(b, "fb_x")
    a.label("fb_res")                                                     # Shift + ▲ / ▼: the resonance
    E(movs_imm, 0, GRP_MASTER)
    E(movs_imm, 1, IDX_RES)
    E(bl, "c_fxget")
    E(cmp_imm, 4, BTN_UP)
    E(b_cond, "fb_rd", "ne")
    E(adds_imm8, 0, RES_STEP)
    E(cmp_imm, 0, 0x7F)
    E(b_cond, "fb_rw", "le")
    E(movs_imm, 0, 0x7F)
    E(b, "fb_rw")
    a.label("fb_rd")
    E(subs_imm8, 0, RES_STEP)
    E(cmp_imm, 0, 0)
    E(b_cond, "fb_rw", "ge")
    E(movs_imm, 0, 0)
    a.label("fb_rw")
    E(mov_reg, 3, 0)
    E(movs_imm, 1, GRP_MASTER)
    E(movs_imm, 2, IDX_RES)
    E(bl, "c_fxset")
    E(b, "fb_x")
    a.label("fb_dup")                                                     # Duplicate: the reset
    E(movs_imm, 6, 0)
    if VIEWSET:                                                           # the view stores of the 16 sends (their values follow below)
        a.label("fb_gl")
        for id0 in (ID_REV0, ID_DEL0):
            imm32(0, GSET_OBJ)
            E(mov_reg, 1, 6)
            E(adds_imm8, 1, id0)
            E(movs_imm, 2, 0)
            E(bl, GSET)
        E(adds_imm8, 6, 1)
        E(cmp_imm, 6, 8)
        E(b_cond, "fb_gl", "lo")
        E(movs_imm, 6, 0)
    a.label("fb_dl")
    E(mov_reg, 1, 6)
    E(adds_imm8, 1, GRP_TRACK)
    E(movs_imm, 2, IDX_REV_SEND)
    E(movs_imm, 3, 0)
    E(bl, "c_fxset")
    E(mov_reg, 1, 6)
    E(adds_imm8, 1, GRP_TRACK)
    E(movs_imm, 2, IDX_DEL_SEND)
    E(movs_imm, 3, 0)
    E(bl, "c_fxset")
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, 8)
    E(b_cond, "fb_dl", "lo")
    E(movs_imm, 1, GRP_MASTER)
    E(movs_imm, 2, IDX_FILTER)
    E(movs_imm, 3, FILTER_MID)
    E(bl, "c_fxset")
    a.label("fb_x")
    E(pop_list, [0, 1, 4, 5, 6, 7], pc=True)
    a.label("fb_c")
    E(raw, popw([0, 1, 4, 5, 6, 7], lr=True))
    E(b_w, prev["btn"])

    # ---- c_fxknob (the FX view's slot 4: view, knob, delta): Shift + knob = the page's parameters
    a.label("c_fxknob")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(cmp_imm, 1, 8)
    bc("fk_c", "hs")
    E(cmp_imm, 2, 0)
    bc("fk_c", "eq")
    E(mov_reg, 5, 1)                                                      # r5 = the knob
    E(mov_reg, 6, 2)                                                      # r6 = the turn
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("fk_c", "eq")
    E(bl, L["c_cishift"])
    E(cmp_imm, 0, 0)
    bc("fk_c", "eq")
    E(bl, "c_fxpage")
    E(lsls_imm, 1, 5, 1)
    E(cmp_imm, 0, PAGE_DELAY)
    E(b_cond, "fk_t", "eq")
    E(adds_imm8, 1, 16)
    a.label("fk_t")
    imm32(0, t_par)
    E(adds_reg, 7, 0, 1)                                                  # r7 = (index, maximum)
    E(ldrb_imm, 4, 7, 0)
    E(cmp_imm, 4, 0xFF)
    bc("fk_x", "eq")                                                      # no parameter on that knob: nothing (Shift + knob = the plain knob in the stock)
    E(movs_imm, 0, GRP_PROJ)
    E(mov_reg, 1, 4)
    E(bl, "c_fxget")
    E(ldrb_imm, 1, 7, 1)
    E(cmp_imm, 1, 0x7F)
    E(b_cond, "fk_add", "eq")
    E(movs_imm, 6, 1)                                                     # a stepped one: a step a click
    E(ldr_sp, 2, 8)
    E(cmp_imm, 2, 0)
    E(b_cond, "fk_add", "gt")
    E(movs_imm, 6, 0)
    E(subs_imm8, 6, 1)
    a.label("fk_add")
    E(adds_reg, 0, 0, 6)
    E(cmp_imm, 0, 0)
    E(b_cond, "fk_lo", "ge")
    E(movs_imm, 0, 0)
    a.label("fk_lo")
    E(cmp_reg, 0, 1)
    E(b_cond, "fk_hi", "le")
    E(mov_reg, 0, 1)
    a.label("fk_hi")
    E(mov_reg, 3, 0)
    E(mov_reg, 2, 4)
    E(movs_imm, 1, GRP_PROJ)
    E(bl, "c_fxset")
    a.label("fk_x")
    E(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)
    a.label("fk_c")
    E(raw, popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    E(b_w, prev["knob"])

    # ---- c_fxled (the LED task's calls: ctrl, frame): in the FX view, ▼ / ▲ = the page; with Shift the parameters' knobs
    a.label("c_fxled")
    E(raw, h(0xE92D) + h(0x41F0))                                         # push.w {r4-r8, lr}
    E(mov_reg, 5, 1)
    E(bl, prev["ledtask"])
    E(bl, "c_fxon")
    E(cmp_imm, 0, 0)
    bc("fl_x", "eq")
    E(bl, "c_fxpage")
    E(mov_reg, 6, 0)                                                      # r6 = the page
    E(movs_imm, 0, COL_REV_DIM if COLS else COL_DIM)
    E(movs_imm, 1, COL_DEL_ON if COLS else COL_ON)
    E(cmp_imm, 6, PAGE_DELAY)
    E(b_cond, "fl_p", "eq")
    E(movs_imm, 0, COL_REV_ON if COLS else COL_ON)
    E(movs_imm, 1, COL_DEL_DIM if COLS else COL_DIM)
    a.label("fl_p")
    E(strh_w_imm, 0, 5, 2 * LED_DOWN)
    E(strh_w_imm, 1, 5, 2 * LED_UP)
    if COLS:
        E(movs_imm, 0, COL_RESET)
        E(strh_w_imm, 0, 5, 2 * LED_DUP)
    E(bl, L["c_cishift"])
    E(cmp_imm, 0, 0)
    bc("fl_x", "eq")
    if COLS:                                                              # Shift: up / down = the resonance (yellow), Duplicate as the stock's (dark)
        E(movs_imm, 0, COL_SHIFT)
        E(strh_w_imm, 0, 5, 2 * LED_DOWN)
        E(strh_w_imm, 0, 5, 2 * LED_UP)
        E(movs_imm, 0, 0)
        E(strh_w_imm, 0, 5, 2 * LED_DUP)
    imm32(7, COL_DELAY)
    E(movs_imm, 1, 0)
    E(cmp_imm, 6, PAGE_DELAY)
    E(b_cond, "fl_c", "eq")
    imm32(7, COL_REVERB)
    E(movs_imm, 1, 16)
    a.label("fl_c")
    imm32(0, t_par)
    E(adds_reg, 4, 0, 1)                                                  # r4 = the page's table
    if BRIGHT:                                                            # r8 = kbright's overlay (0 without our RAM)
        E(bl, L["c_rst"])
        E(cmp_imm, 0, 0)
        E(b_cond, "fl_o", "eq")
        E(adds_imm8, 0, rhstate.OFF["kbright"][0])
        a.label("fl_o")
        E(raw, h(0x4680))                                                 # mov r8, r0
    E(movs_imm, 6, 0)
    a.label("fl_k")
    E(lsls_imm, 0, 6, 1)
    E(ldrb_reg, 0, 4, 0)
    E(movs_imm, 2, 0)
    E(cmp_imm, 0, 0xFF)
    E(b_cond, "fl_w", "eq")
    if BRIGHT:
        E(bl, "c_fxkb")
    E(mov_reg, 2, 7)
    a.label("fl_w")
    E(mov_reg, 0, 6)
    E(adds_imm8, 0, LED_KNOB0)
    E(lsls_imm, 0, 0, 1)
    E(raw, h(0x5200 | 0 << 6 | 5 << 3 | 2))                              # strh r2, [r5, r0]
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, 8)
    E(b_cond, "fl_k", "lo")
    a.label("fl_x")
    E(raw, popw([4, 5, 6, 7, 8], lr=True))
    E(raw, h(0x4770))

    if BRIGHT:
        # ---- c_fxkb(r0 = the parameter; r4 = the page's table, r6 = the knob, r7 = the colour, r8 = the overlay): its value scaled to 0..127
        a.label("c_fxkb")
        E(push_list, [4, 5, 6, 7], lr=True)
        E(mov_reg, 1, 0)
        E(movs_imm, 0, GRP_PROJ)
        E(bl, L["c_skget"])
        E(lsls_imm, 1, 6, 1)
        E(adds_reg, 1, 1, 4)
        E(ldrb_imm, 1, 1, 1)                                              # its maximum
        E(movs_imm, 2, 127)
        E(raw, h(0x4350))                                                 # muls r0, r2
        E(raw, h(0xFBB0) + h(0xF0F1))                                     # udiv r0, r0, r1
        E(cmp_imm, 0, 127)
        E(b_cond, "kb_c", "ls")
        E(movs_imm, 0, 127)
        a.label("kb_c")
        E(raw, h(0x4642))                                                 # mov r2, r8
        E(cmp_imm, 2, 0)
        E(b_cond, "kb_x", "eq")
        E(adds_reg, 3, 2, 6)
        E(strb_imm, 0, 3, 1)
        E(lsls_imm, 3, 6, 1)
        E(adds_reg, 3, 3, 2)
        E(raw, h(0x815F))                                                 # strh r7, [r3, #10]
        E(ldrb_imm, 0, 2, 0)
        E(movs_imm, 1, 1)
        E(raw, h(0x40B1))                                                 # lsls r1, r6
        E(raw, h(0x4308))                                                 # orrs r0, r1
        E(strb_imm, 0, 2, 0)
        a.label("kb_x")
        E(pop_list, [4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr, bright=False, cols=False, viewset=False):
    """Append the code; the head of the button chain, slot 4 of the FX view's vtable, the LED task calls."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]
    lab = lambda sec, n: int(report[sec]["labels"][n], 16)
    L = dict(c_ciok=lab("countin", "c_ciok"), c_cishift=lab("countin", "c_cishift"), c_cinew=lab("countin", "c_cinew"))
    global BRIGHT, COLS, VIEWSET
    BRIGHT, COLS, VIEWSET = bright, cols, viewset
    if bright:
        L.update(c_rst=lab("rhstate", "c_rst"), c_skget=lab("sckn", "c_skget"))
    prev = dict(btn=rhbuild.bw_target(img, CI.BTN_ENTRY), knob=u(SLOT_KNOB) & ~1, ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, CI.BTN_ENTRY, f"b.w #{prev['btn']:#x}", b_w(CI.BTN_ENTRY, labels["c_fxbtn"]))
    rhbuild.patch_word(img, SLOT_KNOB, prev["knob"] | 1, labels["c_fxknob"] | 1)
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_fxled"]))
    report["fxkeys"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
