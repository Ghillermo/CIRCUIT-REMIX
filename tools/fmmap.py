"""The FM algorithm map and the custom algorithm on the FM page (MIT; RH100; the user, 2026-11-14, from a survey of CIRCUIT-HACKS' recent
changes: «Like Hacks»).  CIRCUIT-HACKS' SC56.3 / Beta 5.48 (its tools/fmmap.py, co-authored with mefisme) on the Circuit Rhythm, ours: the
same gestures, the same layout and the same custom algorithm in the same spare bytes of the 216 parameters (a patch moves between the two
firmwares with its routing); the code here is new, for tools/fm8page.py's page and tools/fm8c0.py's engine (fm8page OPT fmmap).

  * the FM page (Sample mode, pad 24 / pad 12): pad 7 tapped = the map pinned (again = unpinned), held 1/2 s = the map until it is let go;
    Shift + pad 7 = the 56 algorithms while held (what pad 7 held did in RH76-RH99, with its ▼ / ▲ pages); Clear + pad 7 = the voicing, as
    before (it keeps a custom routing now: the operators' + 21 untouched).  The old «a tap on pad 7 closes the page» goes: the page closes
    as the other pages, by leaving Sample mode or the track views (fm8page's c_f8page, as before), by a page picked in the track menu (vsel
    OPT fmmap: c_f8shut) or by a tap on pad 24, the engine selector's FM pad, lit in the FM's colour on the page (when no list or map covers it);
  * the map on pads 9-32 (rows 2-4, over the operators' row): each row = whole paths, a leaf on the left (modulator) to its carrier on the
    right, right-aligned; paths share a row with at least one dark pad between them; an operator on several paths is drawn on each; longest
    paths first, first fit (what does not fit is left out); a tap on an operator picks it (the knobs edit it); Shift + operator = muted while
    the map shows (its level held at 0 in its words, dark; nothing saved); one held + a tap on another (any copy) = the link held -> tapped
    on / off = the custom algorithm; a link that would close a loop is refused, and so is the cross feedback's own pair (its modulation is the
    feedback amount: fm8v.words); while one is held its targets are white, its sources steady,
    the rest dim, and the layout stays until it is let go;
  * colour = the operator's ratio class: integer green, x.5 mint, any other orange, fixed red (the engine plays a fixed operator as the ratio
    frequency / 261.63 Hz: it follows the key, RD40; the class shows what K1 holds), the feedback operator lilac (Hacks: its FM violet, which
    here is pad 7's and pad 24's; the lilac is the VA's reciprocal FM zone, Hacks' violet too); steady when its output level (the
    feedback amount) is at least half, dim below; the picked operator pulses (ours: steady / dim every 256 ms, no animated code);
  * the custom algorithm (index 56): + 21 of operator k = the operators that modulate it (bit s), GLB + 13 = feedback source | destination << 4
    (15 = none), GLB + 14 = 0xC0 | N (tools/fm8v.py custom_entry); the first link copies the routing of the algorithm that sounds, with
    N = 1 + the highest operator it uses (used_n: algorithms 8, 9, 11 leave operators unused, which would become carriers; the noise's operator
    past N still runs, not a carrier: fm8v.words, fm8page's c_f8cv); Shift + K1
    or the list goes back to one of the 56.  fm8page's c_f8ent builds its 16-byte entry (c_f8cv's words, the operators' LEDs, the track
    menu's row 3, the map); fm8c0's loop sums the eight operators' outputs weighted by M1-M8 (any routing; an operator modulated by a lower
    one hears it one sample late: the loop runs top down, as Hacks' and as the DX7 algorithms' feedback).
RAM FMAP (in rhstate's second block, modmx's old offsets after fxseq / looper: zeroed at each boot's first c_rst): see the O_* below.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (adds_imm3, adds_imm8, adds_reg, ands_reg, b, b_cond, bics_reg, bl, bx_lr, cmp_imm, cmp_reg, eors_reg, h, ldr_imm, ldrb_imm,  # noqa: E402
                   ldrb_reg, ldrb_w, ldrh_imm, ldr_sp, str_sp, lsls_imm, lsls_reg, lsrs_imm, lsrs_reg, mov_reg, movs_imm, movt, movw, muls, orrs_reg, pop_list,
                   push_list, raw, str_imm, strb_imm, strb_reg, strb_w, strh_imm, subs_imm3, subs_imm8, subs_reg, tst_reg)
import fm8v as V  # noqa: E402
import fxseq as FX  # noqa: E402
import looper as LP  # noqa: E402

FMAP = FX.FXR + 160                               # (after fxseq's 84 B and looper's 56 at + 96)
SIG = 0x314D4D46                                  # "FMM1"
(O_MG, O_CELL, O_MODE, O_HELD, O_PR, O_MUTE, O_TIME, O_STAMP, O_MSL, O_RR, O_CSL, O_SRC, O_CLS, O_CENT, O_ENT, O_SCR, O_FBHI, O_SEL2,
 O_PUL, LEN) = (0, 4, 28, 29, 30, 31, 32, 36, 40, 41, 42, 43, 44, 52, 68, 84, 108, 109, 110, 112)
# + 4 the layout (24 cells: operator + 1), + 28 bit 0 pinned / bit 1 pad 7 held, + 29 the operator held + 1, + 30 pad 7's press (bit 0 ours,
# bit 1 the map was pinned), + 31 the muted operators, + 32 pad 7's press tick, + 36 the last frame the map was drawn, + 40 the slot the
# mutes are for + 1, + 41 the classes' round, + 42 the slot the classes are for + 1, + 43 the parameters' slot, + 44 the classes (8: family
# | level >= 50 << 3 | 0x80), + 52 the entry the layout was made from, + 68 c_f8ent's buffer (a custom algorithm's entry), + 84 the layout's
# walk (stk 8, nxt 8, used 3, L, c, the path's operators, the visits u16), + 108 / 109 / 110 the frame's feedback level, picked operator, pulse
S_STK, S_NXT, S_USED, S_L, S_C, S_IN, S_VIS = 0, 8, 16, 19, 20, 21, 22
HOLD_MS, FRESH_MS, PULSE_SH = 500, 300, 8
CAP = 512                                         # the layout's walk: steps a (length, carrier) at most (a loop in garbage parameters)
PAD_CLOSE = 23                                    # pad 24: the engine selector's FM pad
WHITE = 0x01
# the families: integer green, x.5 mint, other orange, fixed red, feedback lilac.  The fixed red 0xB6 (#fa0005) / 0xE8 (#4c1624), not the stock's
# own Sample mode slice codes 0x9F / 0xA0 (pads 31 / 32 of the view the FM page lies over).  The feedback lilac 0x60 (#ffa2ff) / 0x61 (#291a29):
# Hacks draws the feedback, the FM and the VA's reciprocal FM in one violet; here 0xC2 is pad 7's and pad 24's on the same page, and the
# reciprocal zone of the VA's FM knob (fmviolet) is this lilac, so the feedback takes it (the first choice, yellow 0xBB / 0x73, was looper's
# 1/2 bar on K8 and arpmods' spread dim).  None of these is drawn elsewhere by Remix (the tour of tests/emu_rh99.py, kbright's layers and the
# modules' colour constants) or by the stock's Sample mode (every track, 2026-11-14)
FAM_FIXED = ((0x7D, 0xA2), (0x4F, 0x50), (0x8A, 0x9A), (0xB6, 0xE8))
FAM_FB = (0x60, 0x61)
INV = dict(eq="ne", ne="eq", lo="hs", hs="lo", cc="cs", cs="cc", hi="ls", ls="hi", ge="lt", lt="ge", gt="le", le="gt", mi="pl", pl="mi")
assert FMAP + LEN <= FX.FXR + 512 and FX.RAM_LEN_S <= 96 and 96 + LP.LP_LEN <= 160


def fams():
    """the five families' (steady, dim) codes"""
    return FAM_FIXED + (FAM_FB,)


# ---------------------------------------------------------------------------------------------------------------------------- the model
def table_entry(i):
    """fm8page's table entry of algorithm i (an index past the list: algorithm 0)"""
    import fm8page as F8
    t = F8.alg_table()
    i = i if i < V.NALG else 0
    return t[16 * i:16 * i + 16]


def entry(P):
    """the entry the ARM plays for these parameters (fm8page's c_f8ent)"""
    return V.custom_entry(P) if V.is_custom(P) else table_entry(P[V.GLB + V.G_ALG])


def layout(e, cap=CAP):
    """an entry -> 24 cells (operator + 1 or 0) for pads 9-32, as c_mmlay draws them (the same walk, step for step)"""
    n, car, src = e[0], e[1], list(e[8:16])
    cells, used = [0] * 24, [0, 0, 0]

    def emit(stk, L):
        if len(stk) != L:
            return
        for r in range(3):
            if used[r] + L <= 8:
                base = 8 * r + 7 - used[r]
                for i, o in enumerate(stk):
                    cells[base - i] = o + 1
                used[r] += L + 1
                return
    for L in range(8, 0, -1):
        for c in range(8):
            if c >= n or not (car >> c & 1):
                continue
            stk, nxt, inpath, vis = [c], [0], 1 << c, 0
            if src[c] & ~inpath & 0xFF == 0:
                emit(stk, L)
                continue
            while True:
                vis += 1
                if vis >= cap:
                    break
                d = len(stk) - 1
                avail = src[stk[d]] & ~inpath & 0xFF
                s = nxt[d]
                while s < 8 and not (avail >> s & 1):
                    s += 1
                if s < 8:
                    nxt[d] = s + 1
                    stk.append(s)
                    nxt.append(0)
                    inpath |= 1 << s
                    if src[s] & ~inpath & 0xFF:
                        continue
                    emit(stk, L)
                d = len(stk) - 1
                inpath &= ~(1 << stk[d])
                stk.pop()
                nxt.pop()
                if not stk:
                    break
    return cells


def ratio_family(mode, crs, fine):
    """0 integer, 1 x.5, 2 other, 3 fixed (CIRCUIT-HACKS' ratio_family)"""
    if mode:
        return 3
    v = (100 + fine) if crs == 0 else 2 * crs * (100 + fine)
    return 0 if v % 200 == 0 else 1 if v % 100 == 0 else 2


def op_class(P, k):
    b = V.OPB * k
    return ratio_family(P[b + V.O_MODE], P[b + V.O_CRS], P[b + V.O_FINE]), P[b + V.O_OL] >= 50


def cells_codes(P, cells, held=0, sel=8, mute=0, pul=0, F=None):
    """the 24 pads' codes the map draws (pul: the pulse's half, 1 = dim; F: the families' codes, fams() by default)"""
    e = entry(P)
    F = F or fams()
    fbhi = e[2] < 8 and P[V.GLB + V.G_FB] >= 64
    out = []
    for c in cells:
        if not c or mute >> (c - 1) & 1:
            out.append(0)
            continue
        o = c - 1
        fam, hi = (4, fbhi) if o == e[2] else op_class(P, o)
        if held:
            h_ = held - 1
            if o == h_:
                out.append(F[fam][pul])
            elif e[8 + o] >> h_ & 1:
                out.append(WHITE)
            elif e[8 + h_] >> o & 1:
                out.append(F[fam][0])
            else:
                out.append(F[fam][1])
        elif o == sel:
            out.append(F[fam][pul])
        else:
            out.append(F[fam][0 if hi else 1])
    return out


def used_n(e):
    """1 + the highest operator an entry uses (a carrier or a modulator; c_mmn).  A custom entry: its N (every operator below N that
    modulates nobody is a carrier).  A list's entry can leave operators below its N unused (algorithms 8, 9, 11: the 4-operator engine's
    pitch ones): the conversion to the custom algorithm keeps them out, or they would turn into carriers (heard, and the real carriers'
    share of the output smaller).  The list's feedback operators are always among the used ones (tests/emu_rh100.py's custom part)."""
    u = e[1]
    for k in range(8):
        u |= e[8 + k]
    return u.bit_length()


def link(P, a, b):
    """a modulates b on / off (c_mmlink) -> (the parameters after, 0 nothing / 1 changed / 2 refused: a loop, or the cross feedback's own
    pair a = its source, b = its destination: its modulation is the feedback's amount, M[fd][fs] in fm8v.words); the operators linked are
    those below used_n (the ones the map can draw), and the first link converts to the custom algorithm with N = used_n"""
    P = bytearray(P)
    e = entry(P)
    n = used_n(e)
    if a >= n or b >= n or a == b:
        return bytes(P), 0
    src = e[8 + b]
    if src >> a & 1:
        new = src & ~(1 << a)
    else:
        if a == e[2] and b == e[3]:                       # the cross feedback's pair (fs != fd: a != b): the engine plays it at the
            return bytes(P), 2                            #   feedback's amount (fm8v.words), not as a link: refused, as a loop
        reach = 1 << b
        for _ in range(8):
            for j in range(8):
                if e[8 + j] & reach:
                    reach |= 1 << j
        if reach >> a & 1:
            return bytes(P), 2
        new = src | 1 << a
    if not V.is_custom(P):
        for k in range(8):
            P[V.OPB * k + V.SPARE] = e[8 + k]
        P[V.GLB + V.G_CFB] = min(e[2], 15) | min(e[3], 15) << 4
        P[V.GLB + V.G_CN] = V.CUS | n
        P[V.GLB + V.G_ALG] = V.CUSTOM
    P[V.OPB * b + V.SPARE] = new
    return bytes(P), 1


# ---------------------------------------------------------------------------------------------------------------------------- the code
def emit(a, L, T, F8):
    """Our functions inside fm8page's assembler (OPT fmmap).  L: the addresses of c_rst, c_spshift, HAL; T: fm8page's tables (alg, mfam);
    F8: the fm8page module (its RAM offsets and colours).  fm8page's own functions (c_f8ram, c_f8rd, c_f8wr, c_f8src, c_f8page, c_f8dirty) by
    their labels."""
    E = a.emit
    zc = [0]

    def LB(rt, rn, off):                                                  # ldrb, the 32-bit form past + 31
        E(ldrb_imm if off < 32 else ldrb_w, rt, rn, off)

    def SB(rt, rn, off):
        E(strb_imm if off < 32 else strb_w, rt, rn, off)

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        if v >> 16:
            E(movt, rd, (v >> 16) & 0xFFFF)

    def bc(target, cond):
        zc[0] += 1
        n_ = f"_mm{zc[0]}"
        E(b_cond, n_, INV[cond])
        E(b, target)
        a.label(n_)

    def udiv(rd, rn, rm): return h(0xFBB0 | rn) + h(0xF0F0 | rd << 8 | rm)
    G = V.GLB
    NSL = F8.NSL

    # ---- c_mmst() -> r0 = FMAP (from zero when its magic is missing), 0 without rhstate's block; clobbers r1-r3
    a.label("c_mmst")
    E(push_list, [], lr=True)
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ms_0", "eq")
    imm32(0, FMAP)
    E(ldr_imm, 1, 0, 0)
    imm32(2, SIG)
    E(cmp_reg, 1, 2)
    E(b_cond, "ms_x", "eq")
    E(movs_imm, 1, 0)
    E(movs_imm, 3, LEN)
    a.label("ms_z")
    E(subs_imm8, 3, 4)
    E(raw, h(0x50C1))                                                     # str r1, [r0, r3]
    E(b_cond, "ms_z", "ne")
    E(str_imm, 2, 0, 0)
    a.label("ms_x")
    E(pop_list, [], pc=True)
    a.label("ms_0")
    E(movs_imm, 0, 0)
    E(pop_list, [], pc=True)

    # ---- c_f8ent(r0 = the parameters' slot, r1 = the algorithm) -> r0 = its 16-byte entry (the list's; a custom one built in FMAP + O_ENT;
    #      an index past the list: algorithm 0); clobbers r1-r3
    a.label("c_f8ent")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(cmp_imm, 1, V.NALG)
    E(b_cond, "fe_t", "lo")
    E(mov_reg, 4, 0)
    bc("fe_0", "ne")
    E(bl, "c_mmst")
    E(cmp_imm, 0, 0)
    bc("fe_0", "eq")
    E(adds_imm8, 0, O_ENT)
    E(mov_reg, 6, 0)                                                      # r6 = the buffer
    E(mov_reg, 0, 4)
    E(movs_imm, 1, G + V.G_CN)
    E(bl, "c_f8rd")
    E(lsrs_imm, 1, 0, 4)
    E(cmp_imm, 1, V.CUS >> 4)
    bc("fe_0", "ne")
    E(movs_imm, 1, 15)
    E(ands_reg, 0, 1)
    bc("fe_0", "eq")                                                      # N = 0: no custom algorithm
    E(cmp_imm, 0, 8)
    E(b_cond, "fe_n", "ls")
    E(movs_imm, 0, 8)
    a.label("fe_n")
    SB(0, 6, 0)
    E(movs_imm, 5, 0)                                                     # r5 = any modulator
    E(movs_imm, 7, 0)                                                     # r7 = k
    a.label("fe_k")
    E(movs_imm, 0, 0)
    LB(1, 6, 0)
    E(cmp_reg, 7, 1)
    E(b_cond, "fe_w", "hs")
    E(movs_imm, 0, V.OPB)
    E(muls, 0, 7)
    E(adds_imm8, 0, V.SPARE)
    E(mov_reg, 1, 0)
    E(mov_reg, 0, 4)
    E(bl, "c_f8rd")
    LB(1, 6, 0)
    E(movs_imm, 2, 1)
    E(lsls_reg, 2, 1)
    E(subs_imm8, 2, 1)
    E(ands_reg, 0, 2)                                                     # its sources & full
    E(orrs_reg, 5, 0)
    a.label("fe_w")
    E(adds_reg, 1, 6, 7)
    SB(0, 1, 8)
    E(adds_imm8, 7, 1)
    E(cmp_imm, 7, 8)
    E(b_cond, "fe_k", "lo")
    LB(1, 6, 0)
    E(movs_imm, 2, 1)
    E(lsls_reg, 2, 1)
    E(subs_imm8, 2, 1)
    E(bics_reg, 2, 5)                                                     # the carriers = full & ~any
    SB(2, 6, 1)
    E(movs_imm, 3, 0)
    a.label("fe_c")                                                       # their count (1 at least)
    E(cmp_imm, 2, 0)
    E(b_cond, "fe_cd", "eq")
    E(subs_imm3, 0, 2, 1)
    E(ands_reg, 2, 0)
    E(adds_imm8, 3, 1)
    E(b, "fe_c")
    a.label("fe_cd")
    E(cmp_imm, 3, 0)
    E(b_cond, "fe_c1", "ne")
    E(movs_imm, 3, 1)
    a.label("fe_c1")
    SB(3, 6, 4)
    E(mov_reg, 0, 4)
    E(movs_imm, 1, G + V.G_CFB)
    E(bl, "c_f8rd")
    E(movs_imm, 1, 15)
    E(ands_reg, 1, 0)
    E(cmp_imm, 1, 15)
    E(b_cond, "fe_s", "ne")
    E(movs_imm, 1, 0xFF)
    a.label("fe_s")
    SB(1, 6, 2)
    E(lsrs_imm, 1, 0, 4)
    E(cmp_imm, 1, 15)
    E(b_cond, "fe_d", "ne")
    E(movs_imm, 1, 0xFF)
    a.label("fe_d")
    SB(1, 6, 3)
    E(movs_imm, 0, 0)
    SB(0, 6, 5)
    SB(0, 6, 6)
    SB(0, 6, 7)
    E(mov_reg, 0, 6)
    E(pop_list, [4, 5, 6, 7], pc=True)
    a.label("fe_0")
    E(movs_imm, 1, 0)
    a.label("fe_t")
    E(lsls_imm, 1, 1, 4)
    imm32(0, T["alg"])
    E(adds_reg, 0, 0, 1)
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_mmmute(r0 = the parameters' slot, r1 = an operator) -> r0 = 1 when the map holds it muted; clobbers r1-r3
    a.label("c_mmmute")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(bl, "c_mmst")
    E(cmp_imm, 0, 0)
    E(b_cond, "mu_0", "eq")
    LB(1, 0, O_MSL)
    E(subs_imm8, 1, 1)
    E(cmp_reg, 1, 4)
    E(b_cond, "mu_0", "ne")
    LB(0, 0, O_MUTE)
    E(lsrs_reg, 0, 5)
    E(movs_imm, 1, 1)
    E(ands_reg, 0, 1)
    E(pop_list, [4, 5], pc=True)
    a.label("mu_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4, 5], pc=True)

    # ---- c_mmshow() -> r0 = 1 while the map is shown (no list, pinned or pad 7 held; the page's own check is the caller's); clobbers r1-r3
    a.label("c_mmshow")
    E(push_list, [4], lr=True)
    E(bl, "c_mmst")
    E(mov_reg, 4, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "sh_0", "eq")
    E(bl, "c_f8ram")
    LB(0, 0, F8.O_HOLD)
    E(cmp_imm, 0, 0)
    E(b_cond, "sh_0", "ne")
    LB(0, 4, O_MODE)
    E(movs_imm, 1, 3)
    E(ands_reg, 0, 1)
    E(b_cond, "sh_0", "eq")
    E(movs_imm, 0, 1)
    E(pop_list, [4], pc=True)
    a.label("sh_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)

    # ---- c_f8shut(): the FM page closed (a page picked in the track menu, vsel); every register kept
    a.label("c_f8shut")
    E(push_list, [0, 1, 2, 3], lr=True)
    E(bl, "c_f8ram")
    E(movs_imm, 1, 0)
    SB(1, 0, F8.O_OPEN)
    SB(1, 0, F8.O_HOLD)
    E(pop_list, [0, 1, 2, 3], pc=True)

    # ---- c_mmoff(): the page opened: the map off, nothing held, the mutes back; clobbers r0-r3
    a.label("c_mmoff")
    E(push_list, [4], lr=True)
    E(bl, "c_mmst")
    E(mov_reg, 4, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "mf_x", "eq")
    E(movs_imm, 0, 0)
    SB(0, 4, O_MODE)
    SB(0, 4, O_PR)
    E(b, "mt_h")                                                          # (c_mmtick's end: nothing held, the mutes back)
    a.label("mf_x")
    E(pop_list, [4], pc=True)

    # ---- c_mm7press(): pad 7 pressed on the page (no Shift, no Clear): the map while held; clobbers r0-r3
    a.label("c_mm7press")
    E(push_list, [4], lr=True)
    E(bl, "c_mmst")
    E(mov_reg, 4, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "m7_x", "eq")
    LB(0, 4, O_MODE)
    E(movs_imm, 1, 1)
    E(ands_reg, 1, 0)
    E(lsls_imm, 1, 1, 1)
    E(adds_imm8, 1, 1)
    SB(1, 4, O_PR)                                               # ours, | 2 when it was pinned
    E(movs_imm, 1, 2)
    E(orrs_reg, 0, 1)
    SB(0, 4, O_MODE)
    imm32(0, L["HAL"])
    E(ldr_imm, 0, 0, 0)
    E(str_imm, 0, 4, O_TIME)
    a.label("m7_x")
    E(pop_list, [4], pc=True)

    # ---- c_mmrel(r0 = pad): pad 7 let go (before HOLD_MS: pinned / unpinned), the held operator let go; clobbers r0-r3
    a.label("c_mmrel")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 5, 0)
    E(bl, "c_mmst")
    E(mov_reg, 4, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "mr_x", "eq")
    E(cmp_imm, 5, F8.PAD_ALG)
    E(b_cond, "mr_m", "ne")
    LB(2, 4, O_PR)
    E(movs_imm, 0, 1)
    E(tst_reg, 2, 0)
    E(b_cond, "mr_x", "eq")
    E(movs_imm, 0, 0)
    SB(0, 4, O_PR)
    LB(1, 4, O_MODE)
    E(movs_imm, 0, 2)
    E(bics_reg, 1, 0)                                                     # pad 7 no longer held
    imm32(0, L["HAL"])
    E(ldr_imm, 0, 0, 0)
    E(ldr_imm, 3, 4, O_TIME)
    E(subs_reg, 0, 0, 3)
    E(movw, 3, HOLD_MS)
    E(cmp_reg, 0, 3)
    E(b_cond, "mr_w", "hs")
    E(movs_imm, 0, 2)                                                     # a tap: pinned -> off, else on
    E(tst_reg, 2, 0)
    E(b_cond, "mr_p", "eq")
    E(movs_imm, 0, 1)
    E(bics_reg, 1, 0)
    E(b, "mr_w")
    a.label("mr_p")
    E(movs_imm, 0, 1)
    E(orrs_reg, 1, 0)
    a.label("mr_w")
    SB(1, 4, O_MODE)
    E(b, "mr_x")
    a.label("mr_m")
    E(cmp_imm, 5, F8.PAD_OP0)
    E(b_cond, "mr_x", "lo")
    E(cmp_imm, 5, 32)
    E(b_cond, "mr_x", "hs")
    LB(1, 4, O_HELD)
    E(cmp_imm, 1, 0)
    E(b_cond, "mr_x", "eq")
    E(subs_imm3, 0, 5, 0)
    E(subs_imm8, 0, F8.PAD_OP0)
    E(adds_reg, 0, 0, 4)
    LB(0, 0, O_CELL)
    E(cmp_reg, 0, 1)
    E(b_cond, "mr_x", "ne")
    E(movs_imm, 0, 0)
    SB(0, 4, O_HELD)
    a.label("mr_x")
    E(pop_list, [4, 5], pc=True)

    # ---- c_mmn(r0 = an entry) -> r0 = 1 + the highest operator it uses (its carriers and its sources: fmmap.used_n); clobbers r1-r3
    a.label("c_mmn")
    LB(1, 0, 1)
    E(movs_imm, 2, 8)
    a.label("mn_l")
    E(subs_imm8, 2, 1)
    E(adds_reg, 3, 0, 2)
    LB(3, 3, 8)
    E(orrs_reg, 1, 3)
    E(cmp_imm, 2, 0)
    E(b_cond, "mn_l", "ne")
    E(movs_imm, 0, 0)
    a.label("mn_c")
    E(cmp_imm, 1, 0)
    E(b_cond, "mn_x", "eq")
    E(lsrs_imm, 1, 1, 1)
    E(adds_imm8, 0, 1)
    E(b, "mn_c")
    a.label("mn_x")
    E(bx_lr)

    # ---- c_mmlink(r0 = slot, r1 = a, r2 = b): a modulates b on / off (the custom algorithm) -> r0 = 0 nothing, 1 changed, 2 refused (a loop)
    a.label("c_mmlink")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 6, 1)
    E(mov_reg, 7, 2)
    E(movs_imm, 1, G + V.G_ALG)
    E(bl, "c_f8rd")
    E(mov_reg, 1, 0)
    E(mov_reg, 0, 4)
    E(bl, "c_f8ent")
    E(mov_reg, 5, 0)                                                      # r5 = the entry it plays
    E(bl, "c_mmn")                                                        # r0 = the operators it uses (used_n)
    E(cmp_reg, 6, 0)
    bc("lk_0", "hs")
    E(cmp_reg, 7, 0)
    bc("lk_0", "hs")
    E(cmp_reg, 6, 7)
    bc("lk_0", "eq")
    E(adds_reg, 0, 5, 7)
    LB(2, 0, 8)                                                  # r2 = b's sources
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 6)
    E(tst_reg, 2, 1)
    E(b_cond, "lk_on", "eq")
    E(bics_reg, 2, 1)                                                     # on -> off
    E(b, "lk_cv")
    a.label("lk_on")                                                      # the cross feedback's pair (a = fs, b = fd): refused
    LB(0, 5, 2)
    E(cmp_reg, 0, 6)
    E(b_cond, "lk_nf", "ne")
    LB(0, 5, 3)
    E(cmp_reg, 0, 7)
    bc("lk_r", "eq")
    a.label("lk_nf")                                                      # a loop? reach = what b reaches downstream
    E(push_list, [2])
    E(movs_imm, 0, 1)
    E(lsls_reg, 0, 7)
    E(movs_imm, 3, 8)
    a.label("lk_p")
    E(movs_imm, 1, 0)
    a.label("lk_j")
    E(adds_reg, 2, 5, 1)
    LB(2, 2, 8)
    E(tst_reg, 2, 0)
    E(b_cond, "lk_n", "eq")
    E(movs_imm, 2, 1)
    E(lsls_reg, 2, 1)
    E(orrs_reg, 0, 2)
    a.label("lk_n")
    E(adds_imm8, 1, 1)
    E(cmp_imm, 1, 8)
    E(b_cond, "lk_j", "lo")
    E(subs_imm8, 3, 1)
    E(b_cond, "lk_p", "ne")
    E(lsrs_reg, 0, 6)
    E(lsrs_imm, 0, 0, 1)
    E(pop_list, [2])
    bc("lk_r", "hs")                                                      # a reaches b's targets: refused
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 6)
    E(orrs_reg, 2, 1)
    a.label("lk_cv")                                                      # (r2 = b's new sources) the list's algorithm: its routing copied
    E(push_list, [2])
    E(bl, "c_mmst")
    E(adds_imm8, 0, O_ENT)
    E(cmp_reg, 5, 0)
    bc("lk_ed", "eq")                                                     # already custom
    E(movs_imm, 0, 0)
    E(push_list, [0])
    a.label("lk_cl")
    E(ldr_sp, 1, 0)
    E(adds_reg, 0, 5, 1)
    LB(2, 0, 8)
    E(movs_imm, 0, V.OPB)
    E(muls, 0, 1)
    E(adds_imm8, 0, V.SPARE)
    E(mov_reg, 1, 0)
    E(mov_reg, 0, 4)
    E(bl, "c_f8wr")
    E(ldr_sp, 0, 0)
    E(adds_imm8, 0, 1)
    E(str_sp, 0, 0)
    E(cmp_imm, 0, 8)
    E(b_cond, "lk_cl", "lo")
    E(pop_list, [0])
    LB(2, 5, 2)
    E(cmp_imm, 2, 15)
    E(b_cond, "lk_f1", "ls")
    E(movs_imm, 2, 15)
    a.label("lk_f1")
    LB(1, 5, 3)
    E(cmp_imm, 1, 15)
    E(b_cond, "lk_f2", "ls")
    E(movs_imm, 1, 15)
    a.label("lk_f2")
    E(lsls_imm, 1, 1, 4)
    E(orrs_reg, 2, 1)
    E(mov_reg, 0, 4)
    E(movs_imm, 1, G + V.G_CFB)
    E(bl, "c_f8wr")
    E(mov_reg, 0, 5)
    E(bl, "c_mmn")                                                        # N = used_n (the list's unused operators stay out)
    E(mov_reg, 2, 0)
    E(movs_imm, 1, V.CUS)
    E(orrs_reg, 2, 1)
    E(mov_reg, 0, 4)
    E(movs_imm, 1, G + V.G_CN)
    E(bl, "c_f8wr")
    E(mov_reg, 0, 4)
    E(movs_imm, 1, G + V.G_ALG)
    E(movs_imm, 2, V.CUSTOM)
    E(bl, "c_f8wr")
    a.label("lk_ed")
    E(pop_list, [2])
    E(movs_imm, 0, V.OPB)
    E(muls, 0, 7)
    E(adds_imm8, 0, V.SPARE)
    E(mov_reg, 1, 0)
    E(mov_reg, 0, 4)
    E(bl, "c_f8wr")
    E(mov_reg, 0, 4)
    E(movw, 1, 0x2FF)
    E(bl, "c_f8dirty")
    E(movs_imm, 0, 1)
    E(pop_list, [4, 5, 6, 7], pc=True)
    a.label("lk_r")
    E(movs_imm, 0, 2)
    E(pop_list, [4, 5, 6, 7], pc=True)
    a.label("lk_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_mmpad(r0 = the page's slot, r1 = pad 8-31) while the map is shown: pick, Shift = mute, held + another = link; clobbers r0-r3
    a.label("c_mmpad")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 6, 0)
    E(mov_reg, 5, 1)
    E(bl, "c_mmst")
    E(mov_reg, 4, 0)
    E(cmp_imm, 0, 0)
    bc("mp_x", "eq")
    E(subs_imm3, 0, 5, 0)
    E(subs_imm8, 0, F8.PAD_OP0)
    E(adds_reg, 0, 0, 4)
    LB(7, 0, O_CELL)                                             # r7 = the operator + 1 (0: a dark pad)
    E(cmp_imm, 7, 0)
    bc("mp_x", "eq")
    E(bl, L["c_spshift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "mp_ns", "eq")
    E(subs_imm8, 7, 1)                                                    # Shift: muted / back
    E(movs_imm, 0, 1)
    E(lsls_reg, 0, 7)
    LB(1, 4, O_MUTE)
    E(eors_reg, 1, 0)
    SB(1, 4, O_MUTE)
    E(adds_imm3, 1, 6, 1)
    SB(1, 4, O_MSL)
    E(mov_reg, 1, 0)
    E(mov_reg, 0, 6)
    E(bl, "c_f8dirty")
    E(b, "mp_x")
    a.label("mp_ns")
    LB(0, 4, O_HELD)
    E(cmp_imm, 0, 0)
    E(b_cond, "mp_lk", "ne")
    SB(7, 4, O_HELD)                                             # the first: held and picked
    E(bl, "c_f8ram")
    E(subs_imm8, 7, 1)
    SB(7, 0, F8.O_SEL)
    E(b, "mp_x")
    a.label("mp_lk")
    E(cmp_reg, 0, 7)
    E(b_cond, "mp_x", "eq")
    E(subs_imm3, 1, 0, 1)
    E(subs_imm3, 2, 7, 1)
    E(mov_reg, 0, 6)
    E(bl, "c_mmlink")
    a.label("mp_x")
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_mmtick() (each frame, the LED task): the page closed = the map off; not shown = nothing held, the mutes back; clobbers r0-r3
    a.label("c_mmtick")
    E(push_list, [4], lr=True)
    E(bl, "c_mmst")
    E(mov_reg, 4, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "mt_x", "eq")
    E(bl, "c_f8page")
    E(cmp_imm, 0, NSL)
    E(b_cond, "mt_o", "lo")
    E(movs_imm, 0, 0)
    SB(0, 4, O_MODE)
    SB(0, 4, O_PR)
    E(b, "mt_h")
    a.label("mt_o")
    E(bl, "c_mmshow")
    E(cmp_imm, 0, 0)
    E(b_cond, "mt_x", "ne")
    a.label("mt_h")
    E(movs_imm, 0, 0)
    SB(0, 4, O_HELD)
    LB(1, 4, O_MUTE)
    E(cmp_imm, 1, 0)
    E(b_cond, "mt_x", "eq")
    SB(0, 4, O_MUTE)
    LB(0, 4, O_MSL)
    E(subs_imm8, 0, 1)
    E(cmp_imm, 0, NSL)
    E(b_cond, "mt_x", "hs")
    E(bl, "c_f8dirty")                                                    # (r1 = the operators that were muted)
    a.label("mt_x")
    E(pop_list, [4], pc=True)

    # ---- c_mmcls(r0 = FMAP, r1 = an operator): its class (family | level >= 50 << 3 | 0x80) from the parameters' slot; clobbers r0-r3
    a.label("c_mmcls")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    LB(6, 4, O_SRC)
    E(movs_imm, 7, V.OPB)
    E(muls, 7, 5)
    E(mov_reg, 0, 6)
    E(mov_reg, 1, 7)
    E(adds_imm8, 1, V.O_MODE)
    E(bl, "c_f8rd")
    E(cmp_imm, 0, 0)
    E(b_cond, "cl_r", "eq")
    E(movs_imm, 0, 3)                                                     # fixed
    E(b, "cl_f")
    a.label("cl_r")
    E(mov_reg, 0, 6)
    E(mov_reg, 1, 7)
    E(adds_imm8, 1, V.O_FINE)
    E(bl, "c_f8rd")
    E(adds_imm8, 0, 100)
    E(push_list, [0])
    E(mov_reg, 0, 6)
    E(mov_reg, 1, 7)
    E(adds_imm8, 1, V.O_CRS)
    E(bl, "c_f8rd")
    E(pop_list, [1])                                                      # r1 = 100 + fine, r0 = the coarse
    E(cmp_imm, 0, 0)
    E(b_cond, "cl_v", "eq")
    E(lsls_imm, 0, 0, 1)
    E(muls, 1, 0)                                                         # 200 x the ratio
    a.label("cl_v")
    E(movs_imm, 2, 200)
    E(raw, udiv(3, 1, 2))
    E(muls, 3, 2)
    E(subs_reg, 3, 1, 3)
    E(movs_imm, 0, 0)
    E(cmp_imm, 3, 0)
    E(b_cond, "cl_f", "eq")
    E(movs_imm, 0, 1)
    E(cmp_imm, 3, 100)
    E(b_cond, "cl_f", "eq")
    E(movs_imm, 0, 2)
    a.label("cl_f")
    E(push_list, [0])
    E(mov_reg, 0, 6)
    E(mov_reg, 1, 7)
    E(adds_imm8, 1, V.O_OL)
    E(bl, "c_f8rd")
    E(pop_list, [1])
    E(cmp_imm, 0, 50)
    E(b_cond, "cl_l", "lo")
    E(movs_imm, 0, 8)
    E(orrs_reg, 1, 0)
    a.label("cl_l")
    E(movs_imm, 0, 0x80)
    E(orrs_reg, 1, 0)
    E(adds_reg, 0, 4, 5)
    SB(1, 0, O_CLS)
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_mmlay(r0 = entry, r1 = the 24 cells, r2 = the walk's scratch): the layout (fmmap.layout, step for step); clobbers r0-r3
    a.label("c_mmlay")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(mov_reg, 6, 2)
    E(movs_imm, 0, 0)
    E(movs_imm, 1, 0)
    a.label("ly_z")
    E(strb_reg, 0, 5, 1)
    E(adds_imm8, 1, 1)
    E(cmp_imm, 1, 24)
    E(b_cond, "ly_z", "lo")
    SB(0, 6, S_USED)
    SB(0, 6, S_USED + 1)
    SB(0, 6, S_USED + 2)
    E(movs_imm, 0, 8)
    SB(0, 6, S_L)
    a.label("ly_L")
    E(movs_imm, 0, 0)
    SB(0, 6, S_C)
    a.label("ly_c")
    LB(0, 6, S_C)
    LB(1, 4, 0)
    E(cmp_reg, 0, 1)
    bc("ly_cn", "hs")                                                     # c >= N
    LB(1, 4, 1)
    E(lsrs_reg, 1, 0)
    E(lsrs_imm, 1, 1, 1)
    bc("ly_cn", "cc")                                                     # not a carrier
    SB(0, 6, S_STK)
    E(movs_imm, 1, 0)
    SB(1, 6, S_NXT)
    E(strh_imm, 1, 6, S_VIS)
    E(movs_imm, 7, 0)                                                     # r7 = the depth
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 0)
    SB(1, 6, S_IN)
    E(adds_reg, 0, 4, 0)
    LB(0, 0, 8)
    E(bics_reg, 0, 1)
    E(cmp_imm, 0, 0)
    E(b_cond, "ly_lp", "ne")
    E(bl, "c_mmemit")                                                     # a lone carrier
    E(b, "ly_cn")
    a.label("ly_lp")
    E(ldrh_imm, 0, 6, S_VIS)
    E(adds_imm8, 0, 1)
    E(strh_imm, 0, 6, S_VIS)
    E(movw, 1, CAP)
    E(cmp_reg, 0, 1)
    bc("ly_cn", "hs")
    E(ldrb_reg, 0, 6, 7)                                                  # stk[d]
    E(adds_reg, 0, 4, 0)
    LB(1, 0, 8)
    LB(0, 6, S_IN)
    E(bics_reg, 1, 0)                                                     # r1 = what modulates it, not on the path
    E(adds_reg, 3, 6, 7)
    LB(2, 3, S_NXT)                                              # r2 = s from nxt[d]
    a.label("ly_f")
    E(cmp_imm, 2, 8)
    E(b_cond, "ly_pop", "hs")
    E(mov_reg, 0, 1)
    E(lsrs_reg, 0, 2)
    E(lsrs_imm, 0, 0, 1)
    E(b_cond, "ly_got", "hs")
    E(adds_imm8, 2, 1)
    E(b, "ly_f")
    a.label("ly_got")
    E(adds_imm3, 0, 2, 1)
    SB(0, 3, S_NXT)                                              # nxt[d] = s + 1
    E(adds_imm8, 7, 1)
    E(strb_reg, 2, 6, 7)                                                  # stk[d + 1] = s
    E(adds_reg, 3, 6, 7)
    E(movs_imm, 0, 0)
    SB(0, 3, S_NXT)
    E(movs_imm, 0, 1)
    E(lsls_reg, 0, 2)
    LB(1, 6, S_IN)
    E(orrs_reg, 1, 0)
    SB(1, 6, S_IN)
    E(adds_reg, 0, 4, 2)
    LB(0, 0, 8)
    E(bics_reg, 0, 1)
    E(cmp_imm, 0, 0)
    E(b_cond, "ly_lp", "ne")
    E(bl, "c_mmemit")                                                     # a leaf: emitted, then popped
    a.label("ly_pop")
    E(ldrb_reg, 0, 6, 7)
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 0)
    LB(0, 6, S_IN)
    E(bics_reg, 0, 1)
    SB(0, 6, S_IN)
    E(cmp_imm, 7, 0)
    E(b_cond, "ly_cn", "eq")
    E(subs_imm8, 7, 1)
    E(b, "ly_lp")
    a.label("ly_cn")
    LB(0, 6, S_C)
    E(adds_imm8, 0, 1)
    SB(0, 6, S_C)
    E(cmp_imm, 0, 8)
    bc("ly_c", "lo")
    LB(0, 6, S_L)
    E(subs_imm8, 0, 1)
    SB(0, 6, S_L)
    bc("ly_L", "ne")
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_mmemit (c_mmlay's: the path stk[0..r7]): placed when its length is L, first fit; clobbers r0-r3
    a.label("c_mmemit")
    E(push_list, [7], lr=True)
    E(adds_imm8, 7, 1)                                                    # r7 = the length
    LB(0, 6, S_L)
    E(cmp_reg, 7, 0)
    E(b_cond, "em_x", "ne")
    E(movs_imm, 3, 0)
    a.label("em_r")
    E(adds_reg, 0, 6, 3)
    LB(2, 0, S_USED)                                             # r2 = used[r]
    E(adds_reg, 1, 2, 7)
    E(cmp_imm, 1, 8)
    E(b_cond, "em_put", "ls")
    E(adds_imm8, 3, 1)
    E(cmp_imm, 3, 3)
    E(b_cond, "em_r", "lo")
    E(b, "em_x")
    a.label("em_put")
    E(adds_imm8, 1, 1)
    SB(1, 0, S_USED)                                             # used[r] += L + 1
    E(lsls_imm, 3, 3, 3)
    E(adds_imm8, 3, 7)
    E(subs_reg, 3, 3, 2)                                                  # r3 = 8 r + 7 - used: the carrier's cell
    E(movs_imm, 1, 0)
    a.label("em_i")
    E(ldrb_reg, 0, 6, 1)
    E(adds_imm8, 0, 1)
    E(strb_reg, 0, 5, 3)
    E(subs_imm8, 3, 1)
    E(adds_imm8, 1, 1)
    E(cmp_reg, 1, 7)
    E(b_cond, "em_i", "lo")
    a.label("em_x")
    E(pop_list, [7], pc=True)

    # ---- c_mmops(r0 = the page's slot, r1 = the algorithm, r2 = the frame): pads 9-32 of the page (no list): the map when shown, else the
    #      operators (c_f8ent's entry: carriers green, modulators blue, the chosen one bright) and pad 24 (the FM's colour: a tap closes)
    a.label("c_mmops")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 6, 1)
    E(mov_reg, 5, 2)
    E(bl, "c_mmshow")
    E(cmp_imm, 0, 0)
    bc("mo_map", "ne")
    E(mov_reg, 0, 4)
    E(bl, "c_f8src")
    E(mov_reg, 1, 6)
    E(bl, "c_f8ent")
    E(mov_reg, 6, 0)
    E(bl, "c_f8ram")
    LB(4, 0, F8.O_SEL)
    E(movs_imm, 7, 0)
    a.label("mo_op")
    LB(0, 6, 0)
    E(cmp_reg, 7, 0)
    E(b_cond, "mo_on", "hs")
    E(movs_imm, 2, F8.DIM_MOD)
    E(movs_imm, 3, F8.COL_MOD)
    LB(0, 6, 1)
    E(lsrs_reg, 0, 7)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "mo_oc", "eq")
    E(movs_imm, 2, F8.DIM_CAR)
    E(movs_imm, 3, F8.COL_CAR)
    a.label("mo_oc")
    E(cmp_reg, 7, 4)
    E(b_cond, "mo_ow", "ne")
    E(mov_reg, 2, 3)
    a.label("mo_ow")
    E(lsls_imm, 0, 7, 1)
    E(adds_reg, 0, 0, 5)
    E(strh_imm, 2, 0, 2 * F8.PAD_OP0)
    a.label("mo_on")
    E(adds_imm8, 7, 1)
    E(cmp_imm, 7, 8)
    E(b_cond, "mo_op", "lo")
    E(movs_imm, 0, F8.COL_FM)
    E(strh_imm, 0, 5, 2 * PAD_CLOSE)
    E(pop_list, [4, 5, 6, 7], pc=True)
    # the map
    a.label("mo_map")
    E(bl, "c_mmst")
    E(mov_reg, 7, 0)                                                      # r7 = FMAP
    E(movs_imm, 0, F8.COL_FM)
    E(strh_imm, 0, 5, 2 * F8.PAD_ALG)                                     # pad 7 bright
    E(mov_reg, 0, 4)
    E(bl, "c_f8src")
    SB(0, 7, O_SRC)
    E(mov_reg, 1, 6)
    E(bl, "c_f8ent")
    E(mov_reg, 6, 0)                                                      # r6 = the entry
    LB(0, 7, O_HELD)
    E(cmp_imm, 0, 0)
    E(b_cond, "mo_nl", "ne")                                              # held: the layout kept
    E(movs_imm, 2, 0)
    E(movs_imm, 3, 0)
    a.label("mo_ce")                                                      # the entry against the one the layout was made from
    E(ldrb_reg, 0, 6, 2)
    E(adds_reg, 1, 7, 2)
    LB(1, 1, O_CENT)
    E(cmp_reg, 0, 1)
    E(b_cond, "mo_cq", "eq")
    E(movs_imm, 3, 1)
    E(adds_reg, 1, 7, 2)
    SB(0, 1, O_CENT)
    a.label("mo_cq")
    E(adds_imm8, 2, 1)
    E(cmp_imm, 2, 16)
    E(b_cond, "mo_ce", "lo")
    E(cmp_imm, 3, 0)
    E(b_cond, "mo_nl", "eq")
    E(mov_reg, 0, 6)
    E(mov_reg, 1, 7)
    E(adds_imm8, 1, O_CELL)
    E(mov_reg, 2, 7)
    E(adds_imm8, 2, O_SCR)
    E(bl, "c_mmlay")
    a.label("mo_nl")                                                      # the classes: all when the map just came up, else the picked + one
    imm32(0, L["HAL"])
    E(ldr_imm, 0, 0, 0)
    E(ldr_imm, 1, 7, O_STAMP)
    E(str_imm, 0, 7, O_STAMP)
    E(subs_reg, 0, 0, 1)
    E(movw, 1, FRESH_MS)
    E(cmp_reg, 0, 1)
    E(b_cond, "mo_all", "hs")
    LB(0, 7, O_SRC)
    E(adds_imm8, 0, 1)
    LB(1, 7, O_CSL)
    E(cmp_reg, 0, 1)
    E(b_cond, "mo_all", "ne")
    E(bl, "c_f8ram")
    LB(1, 0, F8.O_SEL)
    E(cmp_imm, 1, 8)
    E(b_cond, "mo_rr", "hs")
    E(mov_reg, 0, 7)
    E(bl, "c_mmcls")
    a.label("mo_rr")
    LB(1, 7, O_RR)
    E(adds_imm8, 1, 1)
    E(movs_imm, 0, 7)
    E(ands_reg, 1, 0)
    SB(1, 7, O_RR)
    E(mov_reg, 0, 7)
    E(bl, "c_mmcls")
    E(b, "mo_cd")
    a.label("mo_all")
    LB(0, 7, O_SRC)
    E(adds_imm8, 0, 1)
    SB(0, 7, O_CSL)
    E(movs_imm, 4, 0)
    a.label("mo_al")
    E(mov_reg, 0, 7)
    E(mov_reg, 1, 4)
    E(bl, "c_mmcls")
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, 8)
    E(b_cond, "mo_al", "lo")
    a.label("mo_cd")                                                      # the feedback's level, the picked operator, the pulse
    E(movs_imm, 0, 0)
    SB(0, 7, O_FBHI)
    LB(0, 6, 2)
    E(cmp_imm, 0, 8)
    E(b_cond, "mo_nf", "hs")
    LB(0, 7, O_SRC)
    E(movs_imm, 1, G + V.G_FB)
    E(bl, "c_f8rd")
    E(cmp_imm, 0, 64)
    E(b_cond, "mo_nf", "lo")
    E(movs_imm, 0, 1)
    SB(0, 7, O_FBHI)
    a.label("mo_nf")
    E(bl, "c_f8ram")
    LB(0, 0, F8.O_SEL)
    SB(0, 7, O_SEL2)
    imm32(0, L["HAL"])
    E(ldr_imm, 0, 0, 0)
    E(lsrs_imm, 0, 0, PULSE_SH)
    E(movs_imm, 1, 1)
    E(ands_reg, 0, 1)
    SB(0, 7, O_PUL)
    E(movs_imm, 4, 0)                                                     # r4 = the cell
    a.label("mo_c")
    E(adds_reg, 0, 7, 4)
    LB(0, 0, O_CELL)
    E(movs_imm, 3, 0)
    E(cmp_imm, 0, 0)
    bc("mo_w", "eq")
    E(subs_imm8, 0, 1)                                                    # r0 = the operator
    LB(1, 7, O_MUTE)
    E(lsrs_reg, 1, 0)
    E(lsrs_imm, 1, 1, 1)
    bc("mo_w", "cs")                                                      # muted: dark
    LB(1, 6, 2)
    E(cmp_reg, 1, 0)
    E(b_cond, "mo_rt", "ne")
    E(movs_imm, 2, 4)                                                     # the feedback's source: lilac, its amount
    LB(1, 7, O_FBHI)
    E(b, "mo_lv")
    a.label("mo_rt")
    E(adds_reg, 1, 7, 0)
    LB(1, 1, O_CLS)
    E(movs_imm, 2, 7)
    E(ands_reg, 2, 1)
    E(lsrs_imm, 1, 1, 3)
    E(movs_imm, 3, 1)
    E(ands_reg, 1, 3)
    a.label("mo_lv")                                                      # r0 = the operator, r1 = its level >= half, r2 = the family
    LB(3, 7, O_HELD)
    E(cmp_imm, 3, 0)
    E(b_cond, "mo_sel", "eq")
    E(subs_imm8, 3, 1)
    E(cmp_reg, 0, 3)
    E(b_cond, "mo_pu", "eq")                                              # the held one: pulse
    E(adds_reg, 1, 6, 0)
    LB(1, 1, 8)
    E(lsrs_reg, 1, 3)
    E(lsrs_imm, 1, 1, 1)
    E(b_cond, "mo_wh", "hs")                                              # its target: white
    E(adds_reg, 1, 6, 3)
    LB(1, 1, 8)
    E(lsrs_reg, 1, 0)
    E(lsrs_imm, 1, 1, 1)
    E(b_cond, "mo_st", "hs")                                              # its source: steady
    E(b, "mo_dm")
    a.label("mo_sel")
    LB(3, 7, O_SEL2)
    E(cmp_reg, 0, 3)
    E(b_cond, "mo_pu", "eq")                                              # the picked one: pulse
    E(cmp_imm, 1, 0)
    E(b_cond, "mo_st", "ne")
    a.label("mo_dm")
    E(lsls_imm, 2, 2, 1)
    E(adds_imm8, 2, 1)
    E(b, "mo_tb")
    a.label("mo_pu")
    LB(1, 7, O_PUL)
    E(lsls_imm, 2, 2, 1)
    E(adds_reg, 2, 2, 1)
    E(b, "mo_tb")
    a.label("mo_st")
    E(lsls_imm, 2, 2, 1)
    E(b, "mo_tb")
    a.label("mo_wh")
    E(movs_imm, 3, WHITE)
    E(b, "mo_w")
    a.label("mo_tb")
    imm32(3, T["mfam"])
    E(ldrb_reg, 3, 3, 2)
    a.label("mo_w")
    E(lsls_imm, 0, 4, 1)
    E(adds_reg, 0, 0, 5)
    E(strh_imm, 3, 0, 2 * F8.PAD_OP0)
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, 24)
    bc("mo_c", "lo")
    E(pop_list, [4, 5, 6, 7], pc=True)


# ---------------------------------------------------------------------------------------------------------------------------- the VA's FM knob
# (RH100, synthpage / vsel / modmx OPT fmviolet; CIRCUIT-HACKS' SC52.6 «Dirección + recíproco violeta») va0's FM (V3) has Hacks' curve: 64 the
# centre; within +-32 one way only (right OSC 2 -> OSC 1, left OSC 1 -> OSC 2, 4 t^2); past +-32 the reciprocal grows to 50 / 50 at the ends.
# Its LED: within +-32 the page's colour, |d| x 4 (dark at the centre, full at +-32, the left lighter: kbright.BIPLEFT); past it the lilac,
# (|d| - 32) x 4 (both ends go to the same 50 / 50: no lighter side).  Lilac 0x60 (#ffa2ff): the Rhythm's palette has no free steady violet
# (0x47 is arpmods' reset, 0x62 the matrix, 0x64 Stock+'s comb, 0xC2 the FM; 0x49 / 0x4A pulse); 0x60, RH39-RH80's granular, is unused
# since RH81 moved the granular to magenta.
FM_RECIP = 0x60
FM_KNOB = 5                                       # synthpage's VA knob index of the FM (raw 5 -> OSC 2's + 6)


def fm_knob_led(v):
    """the VA's FM value 0..127 -> (colour: None = the page's / FM_RECIP, the brightness 0..127, the left lighter)"""
    d = v - 64
    ad = abs(d)
    if ad <= 32:
        return None, min(127, 4 * ad), d < 0
    return FM_RECIP, min(127, 4 * (ad - 32)), False


def emit_fmled(E, a, lab, left, vio_ok=True):
    """(r0 = the value 0..127) -> r0 = the brightness, r2 = the left flag (left: its code), r3 = FM_RECIP past +-32 (else untouched);
    clobbers nothing else.  lab: a unique prefix"""
    E(movs_imm, 2, 0)
    E(subs_imm8, 0, 64)
    E(b_cond, f"{lab}p", "ge")
    E(raw, h(0x4240))                                                     # rsbs r0, r0, #0
    E(movw, 2, left)
    a.label(f"{lab}p")
    E(cmp_imm, 0, 32)
    E(b_cond, f"{lab}d", "ls")
    E(subs_imm8, 0, 32)
    E(movs_imm, 2, 0)
    E(movs_imm, 3, FM_RECIP)
    a.label(f"{lab}d")
    E(lsls_imm, 0, 0, 2)
    E(cmp_imm, 0, 127)
    E(b_cond, f"{lab}x", "ls")
    E(movs_imm, 0, 127)
    a.label(f"{lab}x")


def fmviolet():
    import rhbuild
    return bool(rhbuild.OPT.get("fmviolet"))


def fam_table():
    """the families' codes for the table mfam: steady, dim (x 5)"""
    return bytes(c for f in fams() for c in f)
