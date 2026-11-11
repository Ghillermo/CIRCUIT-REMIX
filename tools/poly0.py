"""Polyphony of the synth on DSP core 0 (MIT; RH72; the user, 2026-11-04: «can we have some polyphony for synths or samples¿?» -> «Per-track
switch, 4 voices shared», «Sample mode pad 13», «Up to 4, the free ones»; docs/PORTADO.md «Plan de RH72»).

The voices are synth0's slots: the ARM gives a poly track every free slot (its track, its values, its FM block).  Here, in synth0's code
(OPT poly; synth0 with its one-word moves, OPT s0short, so this fits after it):
  * PQW (q_slot's first move -> jmp PQW): a note-on of a poly track (X:PF + t <> 0) goes to one voice only: the first of its slots that
    sees the message picks it (a resting one, else the one whose note is the oldest; the ages X:AGE + s) for the message (Y:G_QRD, kept in
    X:QID / X:QTGT), the others skip it; note-offs reach every voice (the ARM sends one before each note-on of a track: the previous note
    releases on its own voice).  A slot that takes a note-on raises its own FM trigger (X:FTR + s, fm0's ftr with OPT poly);
  * SETB (S_BUF's store -> jsr SETB): each slot draws into its own 32 words (Y:PRIV + 32 s);
  * MIXG (the last envelope block's jsr ge_slot -> jsr MIXG, before SY puts the stock's registers back): each track with slots on =
    the sum of their buffers (the first one written over core 1's samples).
OPT polycap (RH73; RD39 on the device: STRESS B with 4 FM voices overloaded core 0, «Yes, cap it»): a new voice only with room for it.
  * IDL (P:$126 `jscs $1AE`, the main loop -> jsr IDL): the stock's call, then X:PC + 1 (the main loop's passes: idle time);
  * BUD (MIXG's start, once a block): H = min(H + 1/16, the block's passes) in X:H16 (x 16: it falls at once, it rises 1 pass in 16
    blocks), never below 0 (the power-on noise);
  * pq_sel: a resting voice is taken only while H >= THRESH passes; else it counts as the youngest (age 0), so the track's oldest sounding
    voice is taken (its load stays the same); a resting voice taken = H - COST, until the next blocks measure it.
  polycap=2 (RH74; RH73 on the device at rest: H median 24, never 120 — single blocks get few idle passes even when the average is ~640):
  BUD = a running average, H16 = H16 - H16 / 16 + the block's passes (16 x the mean over ≈ 16 blocks, ≈ 11 ms), never below 0.
  Measured on the device (RD39): stopped ≈ 640 passes a block, ≈ 94 instructions a pass; an FM voice ≈ 6 400 instructions ≈ 68 passes.
  polycap=3 (RH85; RD45 on the device, 2026-11-09: four VA voices at 2x broke the sound and the cap let them in): two faults of v2 mended.
  * BUD3: a block whose idle passes exceed MAXP (≈ 4.5 idle periods) counts as 0: when core 0 is late the stock's output ring (P:$1F5, one
    block of slack) stalls ≈ 10 ms and the main loop counts those ≈ 10 000 polls as idle, so v2's H rose while core 0 was overloaded;
  * pqa / pqc charge the voice's cost, the ARM's per slot (esel OPT va2x: X:$525C + $40 s, read from the track's slot r6): FM by its
    operators (20 + 19 N), two oscillators C1X, two at 2x C2X (dsptool: 110-220 / 190-430 passes), else C1 (= v2's COST, also while
    never written); a resting voice is taken only with H >= its cost + MARGIN (v2: THRESH 120 for every voice).  pqa / pqc at P:LOW_AT (the stock's unused vectors $10-$3D: no
    interrupt of core 0 is enabled there, IPRC 0, ESAI only TLIE, SHI HRIE0), so piece B ends before va0's va_osi (OSI2_AT).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core0 as C0  # noqa: E402

PF, AGE, QID, QTGT, FTR, MF = 0x5210, 0x5218, 0x521C, 0x521D, 0x5220, 0x5228   # X (free: RD37)
PRIV = 0x1F70                                                                 # Y: 4 x 32 words (free in the RH builds)
B_AT, B_END = 0x35F4, 0x36AB                                                  # piece B (SETB, MIXG): granular0's freed end (g0short)
SETB_N = 8                                                                    # SETB's words (MIXG right after)
PC, H16, ALW = 0x5230, 0x5231, 0x5232                                         # X (polycap; free in RD39's dumps: X:$5230-$5FFF)
COST, THRESH = 80, 120                                                        # passes (one voice; a new one only with THRESH left)
P_MAIN, OLD_MAIN = 0x126, (0x0BF0A8, 0x0001AE)                                # jscs $1AE (as tools/resmap.py)
C1, C1X, C2X, MARGIN, MAXP = 80, 176, 320, 40, 0xC00                          # (polycap 3) passes; MAXP: idle passes a block at most
PCS = 0x5233                                                                  # (polycap 3) X: the class's cost x 16 (pqa -> pqc)
COST_OFF = 4                                                                  # (polycap 3) X:$525C + $40 s = slot s's cost x 16 (the ARM's)
LOW_AT, LOW_END = 0x10, 0x3E                                                  # (polycap 3) P: pqa / pqc (the stock's nops; $3E = audio)


def cap():                                                                      # 1 = RH73 (the block's minimum), 2 = RH74 (an average)
    import rhbuild                                                              # 3 = RH85 (OPT polycap3: RH74's chain sets polycap = 2)
    if rhbuild.OPT.get("polycap3"):
        return 3
    return int(rhbuild.OPT.get("polycap") or 0)


def _s():
    import synth0
    return synth0


def _rh81():
    import rhbuild
    return bool(rhbuild.OPT.get("rh81"))


def _prt(ys):
    """(RH81) a poly voice that skips a note-on (another voice took it): with the track's F_PRT (vmode0) and sounding, its attack again (the
    choke's chord retrigger)"""
    import vmode0 as VM
    S = _s()
    return [f"move x:>${VM.VMK:x},a", f"move #>${VM.VKEY:x},x0", "cmp x0,a", ("bcc", "ne", "pk_x"),
            "move y0,a", "and #$7,a", f"add #>${VM.VMF:x},a", "move a1,r1", "nop", "move x:(r1),a",
            f"btst #${VM.F_PRT.bit_length() - 1:x},a1", ("bcc", "cc", "pk_x"),
            f"move {ys('r6', S.S_STG)},a", f"cmp #${S.IDLE:x},a", ("bcc", "eq", "pk_x"),
            "clr a", f"move a,{ys('r6', S.S_STG)}",
            ("label", "pk_x")]


def items(lab):
    """lab: synth0's labels (q_slot2, ge_slot); PQW, SETB, MIXG and pq_sel"""
    S = _s()
    ys = lambda r, o: f"y:({r}+${o:x})"                                                # noqa: E731
    L = []
    # ================================================================ PQW (r6 = a slot or an envelope block; y0 = w0, y1 = w1; keeps x1)
    L += [("label", "pqw"), "move r6,a", "move #>$1c00,x0", "cmp x0,a", ("jcc", "ge", "pq_n"),
          f"move {ys('r6', S.C_KEY)},a", f"move #>${S.KEY:x},x0", "cmp x0,a", ("jcc", "ne", "pq_n"),
          "move y0,a", "and #>$f00000,a", "move a1,a", "move #>$900000,x0", "cmp x0,a", ("jcc", "ne", "pq_n"),
          "move y0,a", "and #>$7,a", "move a1,a", "move a1,b", "add #>$1,b", f"move {ys('r6', S.C_TRK)},x0", "cmp x0,b", ("jcc", "ne", "pq_n"),
          f"add #>${PF:x},a", "move a1,r1", "nop", "move x:(r1),a", "tst a", ("jcc", "eq", "pq_go"),
          f"move y:>${S.G_QRD:x},a", f"move x:>${QID:x},x0", "cmp x0,a", ("jcc", "eq", "pq_hv"),
          f"move a1,x:>${QID:x}", ("jsr", "pq_sel"),
          ("label", "pq_hv"), f"move x:>${QTGT:x},a", "move r6,x0", "cmp x0,a", ("jcc", "ne", "pq_sk"),
          ("label", "pq_go"), "move r6,a", f"sub #>${S.Y0:x},a", "asr #6,a,a", f"add #>${FTR:x},a", "move a1,r1", "move #>$1,x0",
          "move x0,x:(r1)",
          ("label", "pq_n"), f"move {ys('r6', S.C_KEY)},a", ("jmp", lab["q_slot2"]),
          ("label", "pq_sk"), *(_prt(ys) if _rh81() else []), "rts"]
    # pq_sel (b = the track + 1; keeps x1, y0, y1): QTGT = a resting slot of the track, else the one whose note is the oldest; the track's
    # ages + 1, the chosen one's 0 (r3: a resting one chosen, r4: the oldest age seen)
    c = cap()
    L += [("label", "pq_sel")]
    if c:                                                                      # ALW = H >= THRESH (pqa, in piece B)
        L += [("jsr", lab.get("pqa", 0))]
    L += [f"move #>${S.Y0:x},r1", f"move #>${AGE:x},r2", f"move #>${S.SN:x},n1", "clr a", f"move a,x:>${QTGT:x}",
          "move #$0,r3", "move #>$ffffff,r4",
          "do #$4,${ps_l:x}",
          f"move {ys('r1', S.C_TRK)},x0", "cmp x0,b", ("jcc", "ne", "ps_n"),
          "move x:(r2),a", "add #>$1,a", "move a1,x:(r2)",
          f"move {ys('r1', S.S_STG)},a", f"move #>${S.IDLE:x},x0", "cmp x0,a", ("jcc", "ne", "ps_bz")]
    if c:                                                                      # no room: a resting voice = age 0 (any sounding one wins)
        L += [f"move x:>${ALW:x},a", "tst a", ("jcc", "eq", "ps_rz")]
    L += ["move r3,a", "tst a", ("jcc", "ne", "ps_n"), "move #$1,r3", ("jmp", "ps_tk")]
    if c:
        L += [("label", "ps_rz"), "clr a", ("jmp", "ps_cm")]
    L += [("label", "ps_bz"), "move r3,a", "tst a", ("jcc", "ne", "ps_n"),
          "move x:(r2),a", ("label", "ps_cm"), "move r4,x0", "cmp x0,a", ("jcc", "le", "ps_n"), "move a1,r4",
          ("label", "ps_tk"), "move r1,x0", f"move x0,x:>${QTGT:x}",
          ("label", "ps_n"), "move (r1)+n1", "move (r2)+", ("label", "ps_l"),
          f"move x:>${QTGT:x},a", "tst a", ("jcc", "eq", "ps_x"), f"sub #>${S.Y0:x},a", "asr #6,a,a", f"add #>${AGE:x},a", "move a1,r1",
          "clr a", "nop", "move a,x:(r1)"]
    if c:                                                                      # a resting voice taken: H - COST (pqc, in piece B)
        L += [("jsr", lab.get("pqc", 0))]
    L += [("label", "ps_x"), "rts"]
    # ================================================================ SETB (in sy_slot, in place of S_BUF's store: keeps a)
    L += [("label", "setb"), "move r6,b", f"sub #>${S.Y0:x},b", "asr b", f"add #>${PRIV:x},b", f"move b1,{ys('r6', S.S_BUF)}", "rts"]
    # ================================================================ MIXG (the last envelope block's jsr ge_slot)
    L += [("label", "mixg")]
    if cap() == 3:                                                             # BUD3: v2, but a block of more than MAXP passes adds 0
        L += [f"move x:>${H16:x},b", "asr #4,b,a", "sub a,b", f"move x:>${PC:x},a", f"cmp #>${MAXP:x},a", ("bcc", "gt", "bd_s"), "add a,b",
              ("label", "bd_s"), "clr a", f"move a,x:>${PC:x}", "tst b", ("bcc", "ge", "bd_p"), "clr b", ("label", "bd_p"),
              f"move b1,x:>${H16:x}"]
    elif cap() == 2:                                                             # BUD v2: H16 = max(0, H16 - H16 / 16 + passes); passes = 0
        L += [f"move x:>${H16:x},b", "asr #4,b,a", "sub a,b", f"move x:>${PC:x},a", "add a,b", "clr a", f"move a,x:>${PC:x}",
              "tst b", ("jcc", "ge", "bd_p"), "clr b", ("label", "bd_p"), f"move b1,x:>${H16:x}"]
    elif cap():                                                                # BUD: H16 = max(0, min(H16 + 1, 16 x passes)); passes = 0
        L += [f"move x:>${PC:x},a", "asl #4,a,a", "clr b", f"move b,x:>${PC:x}", f"move x:>${H16:x},b", "add #>$1,b",
              "cmp a,b", ("jcc", "le", "bd_m"), "tfr a,b", ("label", "bd_m"), "tst b", ("jcc", "ge", "bd_p"), "clr b",
              ("label", "bd_p"), f"move b1,x:>${H16:x}"]
    L += [("jsr", lab["ge_slot"]),
          "clr a", f"move #>${MF:x},r0", "nop", "rep #$8", "move a,x:(r0)+",
          f"move #>${S.Y0:x},r1", f"move #>${PRIV:x},r2", f"move #>${S.SN:x},n1", "move #>$20,n2", "nop",
          "do #$4,${mx_l:x}",
          f"move {ys('r1', S.C_KEY)},a", f"move #>${S.KEY:x},x0", "cmp x0,a", ("jcc", "ne", "mx_n"),
          f"move {ys('r1', S.C_TRK)},a", "tst a", ("jcc", "eq", "mx_n"), "sub #>$1,a", "and #>$7,a", "move a1,a",
          "tfr a,b", f"add #>${MF:x},b", "move b1,r4",
          "asl #6,a,a", f"add #>${S.TRK_BUF:x},a", "movep y:<<$ffffd0,b", "asl #5,b,b", "add b,a", "move a1,r3", "move r2,r5",
          "move x:(r4),a", "tst a", ("jcc", "ne", "mx_add"), "move #>$1,x0", "move x0,x:(r4)",
          "do #$20,${mx_c:x}", "move y:(r5)+,x0", "move x0,y:(r3)+", ("label", "mx_c"), ("jmp", "mx_n"),
          ("label", "mx_add"), "do #$20,${mx_a:x}", "move y:(r5)+,x0", "move y:(r3),a", "add x0,a", "move a,y:(r3)+", ("label", "mx_a"),
          ("label", "mx_n"), "move (r1)+n1", "move (r2)+n2", ("label", "mx_l"), "rts"]
    if cap():                                                                  # IDL (P:$126's jsr): the stock's call, then X:PC + 1
        L += [("label", "idl"), ("jscc", "cs", OLD_MAIN[1]), f"move x:>${PC:x},a", "add #$1,a", f"move a1,x:>${PC:x}", "rts"]
    if cap() == 3:
        L += [("label", "low")] + low_items()
    elif cap():
        # pqa (pq_sel's start; b = the track + 1: kept): ALW = H >= THRESH
        L += [("label", "pqa"), f"move x:>${H16:x},a", f"move #>${16 * THRESH:x},x0", "cmp x0,a", "move #>$1,a", ("jcc", "ge", "pq_dn"),
              "clr a", ("label", "pq_dn"), f"move a1,x:>${ALW:x}", "rts"]
        # pqc (pq_sel's end, QTGT chosen): the chosen voice resting = a new one: H - COST
        L += [("label", "pqc"), f"move x:>${QTGT:x},r1", "nop", f"move {ys('r1', S.S_STG)},a", f"move #>${S.IDLE:x},x0", "cmp x0,a",
              ("jcc", "ne", "pqc_x"), f"move x:>${H16:x},a", f"sub #>${16 * COST:x},a", f"move a1,x:>${H16:x}", ("label", "pqc_x"), "rts"]
    if _rh81():                                                                # (RH81) one-word branches: room for _prt
        k = next(i for i, x in enumerate(L) if x == ("label", "setb"))
        L = [("bcc", x[1], x[2]) if isinstance(x, tuple) and x[0] == "jcc" and i < k else x for i, x in enumerate(L)]
    return L


def low_items():
    """(polycap 3) pqa (pq_sel's start; r6 = a slot of the track, b = the track + 1: kept, as x1 / y0 / y1): PCS = the slot's cost x 16
    from the ARM (esel OPT va2x, c_oscls: FM 20 + 19 N, two oscillators C1X, at 2x C2X, else C1) at x:(r6 + COSTD), C1 while 0 (never
    written), ALW = max(0, H16 - PCS - 16 MARGIN); pqc (the target chosen in QTGT): a resting one (a new voice) = H16 - PCS"""
    import va0 as V
    S = _s()
    ys = lambda r, o: f"y:({r}+${o:x})"                                                # noqa: E731
    costd = V.OS2G + COST_OFF - S.Y0
    assert costd == 0x385C
    return [("label", "pqa"), f"move x:(r6+${costd:x}),x0", "move x0,a", "tst a", ("bcc", "ne", "pa_c"), f"move #>${16 * C1:x},x0",
            ("label", "pa_c"), f"move x0,x:>${PCS:x}", f"move x:>${H16:x},a", "sub x0,a", f"sub #>${16 * MARGIN:x},a", ("bcc", "gt", "pa_d"),
            "clr a", ("label", "pa_d"), f"move a1,x:>${ALW:x}", "rts",
            ("label", "pqc"), f"move x:>${QTGT:x},r1", f"move x:>${PCS:x},x0", f"move {ys('r1', S.S_STG)},a", f"cmp #${S.IDLE:x},a",
            ("bcc", "ne", "pqc_x"), f"move x:>${H16:x},a", "sub x0,a", f"move a1,x:>${H16:x}", ("label", "pqc_x"), "rts"]


def pieces(lab):
    """-> [(address, words)]: A (PQW, pq_sel) after synth0 (lab["poly"]["pqw"]), B (SETB, MIXG) at B_AT"""
    import sp0 as SP
    its = items(lab)
    k = next(i for i, x in enumerate(its) if x == ("label", "setb"))
    if cap() == 3:                                                             # pqa / pqc low, B = SETB, MIXG, IDL
        j = next(i for i, x in enumerate(its) if x == ("label", "low"))
        wl, ll = C0.asm_at(SP.short_items(its[j + 1:]), LOW_AT)
        assert LOW_AT + len(wl) <= LOW_END, f"poly0's low piece ends at {LOW_AT + len(wl):#x}"
        wb, lb = C0.asm_at(SP.short_items(its[k:j]), B_AT)
        import va0 as V
        assert B_AT + len(wb) <= V.OSI2_AT, f"poly0's piece B ends at {B_AT + len(wb):#x} (va0's va_osi at {V.OSI2_AT:#x})"
        its = items(dict(lab, pqa=ll["pqa"], pqc=ll["pqc"]))
        k = next(i for i, x in enumerate(its) if x == ("label", "setb"))
        a_at = lab["poly"]["pqw"]
        wa, la = C0.asm_at(SP.short_items(its[:k]), a_at)
        assert a_at + len(wa) <= 0x2600, f"poly0's piece A ends at {a_at + len(wa):#x}"
        assert lb["setb"] == B_AT and lb["mixg"] == B_AT + SETB_N, (hex(lb["mixg"]), SETB_N)
        return [(a_at, wa), (B_AT, wb), (LOW_AT, wl)]
    wb, lb = C0.asm_at(SP.short_items(its[k:]), B_AT)                         # B first: A calls pqa / pqc in it (polycap)
    if cap():
        its = items(dict(lab, pqa=lb["pqa"], pqc=lb["pqc"]))
        k = next(i for i, x in enumerate(its) if x == ("label", "setb"))
    a_at = lab["poly"]["pqw"]
    wa, la = C0.asm_at(SP.short_items(its[:k]), a_at)
    assert a_at + len(wa) <= 0x2600, f"poly0's piece A ends at {a_at + len(wa):#x}"
    assert B_AT + len(wb) <= B_END, f"poly0's piece B ends at {B_AT + len(wb):#x}"
    assert lb["setb"] == B_AT and lb["mixg"] == B_AT + SETB_N, (hex(lb["mixg"]), SETB_N)
    return [(a_at, wa), (B_AT, wb)]


def segs(lab):
    out = pieces(lab)
    if cap():                                                                  # P:$126 -> jsr IDL (sent after the stock's block)
        import rhbuild
        _, _, ws = C0.block_words(bytearray(rhbuild.load_stock()))
        assert tuple(ws[P_MAIN:P_MAIN + 2]) == OLD_MAIN, "core 0's jscs $1AE at P:$126 moved"
        import sp0 as SP
        its = items(lab)
        k = next(i for i, x in enumerate(its) if x == ("label", "setb"))
        j = next((i for i, x in enumerate(its) if x == ("label", "low")), len(its))
        _, lb = C0.asm_at(SP.short_items(its[k:j]), B_AT)
        out.append((P_MAIN, [0x0BF080, lb["idl"]]))
        if cap() == 3:                                                          # the low piece over the stock's nops only
            assert not any(ws[LOW_AT:LOW_END]), "core 0's P:$10-$3D are no longer nops"
    return out
