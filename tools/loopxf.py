"""De-click of the loop point in DSP core 1 (MIT; RD18: the user, 2026-10-25, on RD17: the loop's «click persists», «tick, i think»).

The stock (core 1's ring refill $16E, docs/PORTADO.md «RD17»): a looped voice's refill copies the tail up to the loop's end (jsr $73D), then
the overshoot from its start (P:$197 jmp $73D; P:$19F the same when the pointer is already past the end): the ring holds ...s[end-1], s[start]...
with nothing to join them, a step at every pass (the «tick»); $1E5's 16-tap FIR only rounds it over ~16 output samples.
Ours (per track, Y:XFON + t, 0 = the stock): the two jmp $73D -> jmp XF (short, our code in the loader area P:$C.., tools/rhdsp1.py landing):
the copy as the stock's, then the 32 ring words before the loop point (written by this refill or the last one, still unplayed: the ring is read
~400 words behind) get + d x (i + 1) / 32, d = s[start] - s[end - 1]: the tail ramps into the start, no step; a, r5 as the stock leaves them.
Cost: 32 x 4 instructions per loop pass of a voice.  Forward loops only (the reverse refill, P:$1BA / $1C2, untouched).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rhdsppatch as DP  # noqa: E402
import voicefx as V  # noqa: E402

XFON = 0x16E0                                             # + t: the de-click on (0 = the stock)
XR, XA, XE = 0x16DD, 0x16DE, 0x16DF                       # scratch: the splice's ring address, the stock's a, r5 after the copy
P_HOOKS = (0x197, 0x19F)
OLD_HOOK = 0x0C073D                                       # jmp $73D (short)
COPY = 0x73D
N = 32


def items():
    L = []
    E = L.append
    E(("label", "xf"))
    for s in (f"move a1,y:>${XA:x}",                       # (the stock's a: $73D keeps it in n5 and gives it back)
              "move y:>$1405,a", f"add #>${XFON:x},a", "move a1,r3", "move y:(r3),a", "tst a",
              f"move y:>${XA:x},a"):                       # (moves keep the CCR)
        E(s)
    E(("jcc", "eq", "xf_st"))
    E(f"move r5,y:>${XR:x}")
    E(("jsr", COPY))                                       # the copy from the start, as the stock's
    for s in (f"move r5,y:>${XE:x}",
              ("words", [0x05F425, 0x0001FF]),                              # move #>$1ff,m5 (the stock's words at P:$1A0)
              f"move y:>${XR:x},r5", "move (r5)-",
              "move y:(r5)+,x0", "move y:(r5),a", "sub x0,a", "asr #5,a,a", "move a,x1",   # x1 = d / 32 (r5 back at the splice)
              f"move #${N:x},n5", "move (r5)-n5", "clr b"):
        E(s)
    E(("doa", f"do #${N:x}", "xf_e"))
    for s in ("add x1,b", "move y:(r5),a", "add b,a", "move a,y:(r5)+"):
        E(s)
    E(("label", "xf_e"))
    for s in (("words", [0x0465A0]), f"move y:>${XE:x},r5", f"move y:>${XA:x},a", "rts"):     # move m0,m5 (P:$1A7)
        E(s)
    E(("label", "xf_st"))
    E(("jmp", COPY))
    return L


# Where (RD18, on RH38 whose landing area holds loopscan): P:$534..$56D, 58 words of the stock that nothing reaches: no jump, call or branch
# to them (the one indirect jump, P:$533 jmp (r3 + n3), goes to the envelope's stage table at $5CE + stage), not a fall-through ($533 is an
# unconditional jump), no P data read anywhere; a self-contained routine of an unused filter variant (its own bsr $559 inside).
AT, END = 0x534, 0x56E
FIRST, LAST = 0x0C1D20, 0x00000C                          # asl #$10,a,a / rts: the region as the stock has it


def code():
    """-> ({address: word} for P:AT.., XF's address)"""
    w, labels = V.assemble(items(), AT)
    assert AT + len(w) <= END, f"XF: {len(w)} words from ${AT:x}"
    return {AT + i: x for i, x in enumerate(w)}, labels["xf"]

# ---- v2 (RD19; RD18 on the device: «it's still there, but it sounds good when fine tuned», «minor, but it seems the de-click did something»):
# a real crossfade. The ramp only joined the value; the waveform's shape and phase still jumped. Now the N2 ring words before the loop point
# blend linearly into the N2 words of the sample just before the loop's start (fetched with the stock's own paged copy $73D into TEMP):
# at the loop point the tail has become the material that leads into the start, so it joins in value, slope and phase. A start closer than
# N2 to the sample's beginning (no material before it): the copy only, as the stock's.
N2 = 64
TEMP = 0x1480                                             # Y:$1480..$14BF (WSOLA's buffers end at $146E; the refill and WSB never overlap)
XS = 0x16DF                                               # (v2) the loop's start (virtual address)


def items2():
    L = []
    E = L.append
    E(("label", "xf"))
    for s in (f"move a1,y:>${XA:x}", "move y:>$1405,a", f"add #>${XFON:x},a", "move a1,r3", "move y:(r3),a", "tst a",
              f"move y:>${XA:x},a"):
        E(s)
    E(("jcc", "eq", "xf_st"))
    for s in (f"move r1,y:>${XS:x}", f"move r5,y:>${XR:x}"):
        E(s)
    E(("jsr", COPY))                                       # the copy from the start, as the stock's
    for s in (f"move y:>${XS:x},a", f"sub #>${N2:x},a"):
        E(s)
    E(("jcc", "lt", "xf_x"))                               # no material before the start
    for s in ("move a1,r1", f"move #>${N2:x},b", f"move #>${TEMP:x},r5"):
        E(s)
    E(("jsr", COPY))                                       # TEMP = the N2 words before the start (r5 left at TEMP + N2)
    for s in (f"move #${N2:x},n5", "lua (r5)-n5,r1"):     # r1 = TEMP
        E(s)
    E(("words", [0x05F425, 0x0001FF]))                     # move #>$1ff,m5 (the stock's words at P:$1A0)
    for s in (f"move y:>${XR:x},r5", "move (r5)-n5",
              "move #$02,x1",                              # 1 / N2 = $020000 (a short immediate goes to the top byte)
              "clr b"):
        E(s)
    E(("doa", f"do #${N2:x}", "xf_e"))
    for s in ("add x1,b", "move b,y1", "move y:(r5),x0", "move y:(r1)+,a", "sub x0,a", "move a,y0", "mpy y1,y0,a", "add x0,a",
              "move a,y:(r5)+"):                           # tail + w (before-start - tail), w = (i + 1) / N2
        E(s)
    E(("label", "xf_e"))
    E(("words", [0x0465A0]))                               # move m0,m5 (P:$1A7)
    E(("label", "xf_x"))
    for s in (f"move y:>${XA:x},a", "rts"):
        E(s)
    E(("label", "xf_st"))
    E(("jmp", COPY))
    return L


def code2():
    w, labels = V.assemble(items2(), AT)
    assert AT + len(w) <= END, f"XF v2: {len(w)} words from ${AT:x} (room {END - AT})"
    return {AT + i: x for i, x in enumerate(w)}, labels["xf"]

# ---- v3 (RD21; RD19 / RD20 on the device: «xfade no se nota mucho pero mejora un poco el sonido, ¿podría ajustarse la cantidad mediante
# parámetro para tener más o menos?»): v2 with the crossfade's length a parameter: N = Y:XN words (one length for every track; 0 = the
# copy only), its step 1 / N = Y:XQ (a fraction: both written together by tools/rhvfx.py xfade, N = 16 .. 256); Y:XFON + t = on / off as
# before.  Longer = smoother and more of the material before the start blended in; N <= 256 keeps the blended ring words unplayed (the
# ring is read ~400 words behind its refill) and TEMP inside Y:$1480..$157F.  The same 58 words: the jumps and calls take the stock's
# one-word forms (all targets below $1000).
XN, XQ = 0x16E8, 0x16E9
N_MAX = 256


def items3():
    L = []
    E = L.append
    E(("label", "xf"))
    for s in (f"move a1,y:>${XA:x}", "move y:>$1405,a", f"add #>${XFON:x},a", "move a1,r3", "move y:(r3),a", "tst a",
              f"move y:>${XA:x},a"):
        E(s)
    E(("jccs", "eq", "xf_st"))
    for s in (f"move r1,y:>${XS:x}", f"move r5,y:>${XR:x}"):
        E(s)
    E(("jsrs", COPY))                                      # the copy from the start, as the stock's
    for s in (f"move y:>${XN:x},a", "tst a"):
        E(s)
    E(("jccs", "le", "xf_x"))                              # N = 0: the copy only
    for s in ("move a1,x0", f"move y:>${XS:x},a", "sub x0,a"):
        E(s)
    E(("jccs", "lt", "xf_x"))                              # no material before the start
    for s in ("move a1,r1", "move x0,b", f"move #>${TEMP:x},r5"):
        E(s)
    E(("jsrs", COPY))                                      # TEMP = the N words before the start (r5 left at TEMP + N)
    for s in (f"move y:>${XN:x},n5", "lua (r5)-n5,r1"):
        E(s)
    E(("words", [0x05F425, 0x0001FF]))                     # move #>$1ff,m5 (the stock's words at P:$1A0)
    for s in (f"move y:>${XR:x},r5", "move (r5)-n5", f"move y:>${XQ:x},x1", "clr b"):
        E(s)
    E(("doa", "do n5", "xf_e"))
    for s in ("add x1,b", "move b,y1", "move y:(r5),x0", "move y:(r1)+,a", "sub x0,a", "move a,y0", "mpy y1,y0,a", "add x0,a",
              "move a,y:(r5)+"):                           # tail + w (before-start - tail), w = (i + 1) / N
        E(s)
    E(("label", "xf_e"))
    E(("words", [0x0465A0]))                               # move m0,m5 (P:$1A7)
    E(("label", "xf_x"))
    for s in (f"move y:>${XA:x},a", "rts"):
        E(s)
    E(("label", "xf_st"))
    E(("jmps", COPY))
    return L


def code3():
    w, labels = V.assemble(items3(), AT)
    assert AT + len(w) <= END, f"XF v3: {len(w)} words from ${AT:x} (room {END - AT})"
    return {AT + i: x for i, x in enumerate(w)}, labels["xf"]


def length_words(n):
    """-> (Y:XN, Y:XQ) for a crossfade of n words (16 .. 256; 0 = the copy only)"""
    if not n:
        return 0, 0
    assert 16 <= n <= N_MAX, n
    return n, min(0x7FFFFF, round((1 << 23) / n))

# ---- v4 (RD22; RD21 on the device, the user: «el grano es demasiado grande incluso al mínimo», a short loop in Sample mode): a stock bug,
# measured in dsptool: a forward loop shorter than the ring's refill (~128 words at 1x) is not a loop of its length: the refill copies the
# overshoot from the start in one piece (P:$197, P:$19F: jmp $73D with b = the count, r1 = the start) without wrapping again at the end,
# so a 2- or 34-word region repeats every ~128 samples, reading past its end.  Ours: WC, the copy from the start, wrapped every L = end -
# start words (L = Y:(r4) - r1: r4 = v + 3 there, r1 = the start the stock uses, the scanned one with loopscan), the refill pointer
# X:(r4) = the start + what is left; L <= 0: the stock's copy.  XF's two copies from the start (flag on: the first; flag off: xf_st)
# go to WC: every forward loop, the crossfade on or off.  A refill that wraps (a loop shorter than it) clears Y:XS: XF then sees no material
# before the start and does no crossfade (it would blend only the first of the wraps, an uneven tiny loop).  WC lives in the stock's P:$12A..$150, 39 words nothing reaches (no jump, call
# or branch to them, no `do` ending there, no P read; P:$129 is an unconditional bra: no fall-through), an unused sample-table routine
# and two unused ring copies (tests/emu_rd22.py checks it as tests/emu_rd18.py checks $534).  The reverse loop (P:$1BA / $1C2): untouched.
WC_AT, WC_END = 0x12A, 0x151
WC_FIRST, WC_LAST = 0x61F400, 0x00000C                    # move #>$30000,r1 / rts: the region as the stock has it
WR4, WS, WL, WB = 0x16EA, 0x16EB, 0x16EC, 0x16ED          # scratch (core 1 Y)


def wc_items():
    L = []
    E = L.append
    E(("label", "wc"))
    for s in (f"move r4,y:>${WR4:x}", f"move r1,y:>${WS:x}", "move y:(r4),a", "move r1,x0", "sub x0,a"):
        E(s)
    E(("jccs", "le", "wc_last"))                           # no loop length: the stock's copy (a = start + count, as the stock leaves it)
    E(f"move a1,y:>${WL:x}")
    E(("label", "wc_l"))
    for s in (f"move y:>${WL:x},x0", "cmp x0,b"):
        E(s)
    E(("jccs", "le", "wc_last"))                           # what is left fits in one pass
    for s in (f"move b1,y:>${WB:x}", "move x0,b", f"move y:>${WS:x},r1", "clr a",
              f"move a1,y:>${XS:x}"):                      # (a loop shorter than the refill: XF finds no material before the start = no crossfade)
        E(s)
    E(("jsrs", COPY))                                      # one whole pass of the loop
    for s in (f"move y:>${WB:x},b", f"move y:>${WL:x},x0", "sub x0,b"):
        E(s)
    E(("jmps", "wc_l"))
    E(("label", "wc_last"))
    for s in (f"move y:>${WS:x},r1", f"move y:>${WR4:x},r4", "move r1,a", "add b,a", "move a1,x:(r4)"):  # the next address: start + the rest
        E(s)
    E(("jmps", COPY))
    return L


def code4():
    """-> ({address: word} for XF at P:AT.. and WC at P:WC_AT.., XF's address)"""
    wcw, wl = V.assemble(wc_items(), WC_AT)
    assert WC_AT + len(wcw) <= WC_END, f"WC: {len(wcw)} words (room {WC_END - WC_AT})"
    items = []
    for it in items3():                                    # v3 with its two copies from the start going to WC
        if it == ("jsrs", COPY):
            it = ("jsrs", wl["wc"])
        elif it == ("jmps", COPY):
            it = ("jmps", wl["wc"])
        items.append(it)
    xw, xl = V.assemble(items, AT)
    assert AT + len(xw) <= END
    out = {AT + i: x for i, x in enumerate(xw)}
    out.update({WC_AT + i: x for i, x in enumerate(wcw)})
    return out, xl["xf"]
