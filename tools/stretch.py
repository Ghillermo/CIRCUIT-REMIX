"""Stretch per track in the Circuit Rhythm 5706's DSP core 1, the voices: the speed changes, the pitch does not (MIT; K7 of the Stock+ page,
the user, 2026-10-24: «k7: stretch (changes speed without changing pitch)», bipolar 0.25x .. 4x, centre = off).

The stock (core 1's program; traced in dsptool, docs/PORTADO.md «Estiramiento»):
  * a voice's samples are read by $1E5 (P:$23D jsr $1E5) from its 512-word ring Y:$400 + $200 v, which the refill ($16E -> $73D / $798) copies
    from the sample memory; X:(v + 0) is only the position inside the ring, Y:(v + 0) the increment (the pitch: samples x 2^15 per output
    sample);
  * the sample memory: the voice's sample n = y:(x:(v + 5)); its pages listed at Y:$308C8 + n x $BC (two 12-bit page numbers a word, the
    high half for an even page); the word at the virtual address A is Y:(page(A >> 12) << 12 | (A & $FFF)); the voice's start A0 = Y:(v + 4),
    its length Y:(v + 3) words.
Ours: P:$23D jsr $1E5 -> jsr STR (below P:$1000):
  * the voice's speed word (Y:STRETCH + v: speed / 4 as a fraction, $200000 = 1x) at 0: the stock's $1E5, as it was;
  * else a two-grain engine writes X:$2A02.. (x:$1 samples) and the ring is left alone: a playhead P (samples from the start, 24.24) moves by
    r x speed a sample (r = the increment / 2^15: the pitch, pitchmod's modulations included); two grains half a grain apart (G = 2048) each
    read the sample at P (taken when the grain starts) + r x its age, linearly interpolated, under triangular windows that add up to 1;
    past the end (P >= the length) the voice's envelope goes to its fast release (stage 4, x:(v + $A));
  * pitchmod's TRIG (option stretch) clears the voice's state at each note (P = 0, both grains at 0, the clock at 0).
State (Y, voice v): Y:$1780 + 16 v = P int, P frac, R0 int, R0 frac, R1 int, R1 frac, the clock; Y:$16D0 + v the speed word (from the ARM);
Y:$16F8..$16FC scratch.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import voicefx as V  # noqa: E402

STRETCH = 0x16D0                                          # + v: the speed word (0 = off; speed / 4, $200000 = 1x)
ST = 0x1780                                               # + 16 v
S_P, S_PF, S_R0, S_R0F, S_R1, S_R1F, S_CLK = range(7)                    # (S_CLK: v1)
T_SPEED, T_R, T_A0, T_LEN, T_TAB = 0x16F8, 0x16F9, 0x16FA, 0x16FB, 0x16FC
T_OUT = 0x16FD
T_END = 0x16FE                                            # (v5) A0 + the length - 1: the sample's last word
GSTEP, GNSTEP, GHALF, GMASK = 0x16D8, 0x16D9, 0x16DA, 0x16DB
GHM = 0x16DC                                              # (RD16, WSOLA v4) G / 2 - 1: RD12-RD15 had the P probe's command word there    # (grain, RD12) the grain size G for every track, from the host (tools/rhvfx.py
                                                              # grain): the window's step, its negation, G / 2, G - 1
P_HOOK, P_RESAMPLE = 0x23D, 0x1E5
OLD_HOOK = 0x0D01E5                                       # jsr $1e5 (short)
PAGES, PAGE_STRIDE = 0x308C8, 0xBC
G_BITS = 11
G = 1 << G_BITS
BUF = V.BUF
ONE = 0x7FFFFF


def _w(v3):
    """the windows' top and step: RD10 1 and 2 / G (triangles adding up to 1), v3 1/2 and 1 / G (adding up to 1/2, the stock's level)"""
    return (0x400000, (1 << 23) // G) if v3 else (ONE, (2 << 23) // G)


G_R, G_RF, G_W, G_DW, G_PH = range(5)                   # (v2) a grain's block (6 words): read position int / frac, window, its step, phase
G0, G1, INIT = 2, 8, 14                                  # the state: + 0 / 1 P, + 2 grain 0, + 8 grain 1, + 14 started
N_STATE = 15


def items(v3=False, grain=False, low=None):
    """v2: one grain at a time over the block (its read position in a, r in Y = y1:y0); keeps r0, n0, r4 (the voice block, as $1E5 gets
    it); uses what $1E5 uses.
    v3 (RD11 on; RD10 on the device: «a bit glitchy, … like bitcrushed or ring modulated»): the stock's level (its resampler gives half the
    sample: the windows top at 1/2 and add up to 1/2; RD10's were 6 dB louder and clipped).  (Tried: near equal-power windows 2w (1 - w):
    +3 dB over the stock on a tone in dsptool, so clipping again; left out.)
    grain (RD12, with v3; RD11 on the device: «still grainy on the slow ones, but sounds better»): G from the four words GSTEP.. that the host
    writes (one size for every track, to find by ear the size for each speed; 0 there = a broken stretch: tools/rhvfx.py writes them with the
    speed); a size changed while a note plays may click once (a window stepped by the other size).  And the interpolation's fix: x1 =
    a0 >> 1 is already f as a signed fraction, so RD10 / RD11's «asl b» after the mpy made it s0 + 2 f (s1 - s0) (found by tests/emu_rd12.py
    against a float model: right only when the position's fraction is 0, as in RD10's tests at r = 1).
    low (v5, RD13; RD12 on the device: the ring on drums, the wobble on pads, «some pads make a scratchy/white noise sound at the end»):
    the addresses of tools/wsola.py's routines in P:$7F..$FE (dict trp / ws): TRP moves there, a grain starting again asks WS where
    (WSOLA), and a position past the sample's last word (Y:T_END = A0 + length - 1) adds nothing (RD12's grains read up to a grain past
    the end: memory that is not the sample)."""
    half = f"move y:>${GHALF:x},x0" if grain else f"move #>${G // 2:x},x0"
    L = []
    E = L.append
    E(("label", "str"))
    for s in ("move y:>$1405,n1", f"move #>${STRETCH:x},r1", "move y:(r1+n1),a", "tst a"):
        E(s)
    E(("jcc", "eq", "stock"))
    for s in (f"move a,y:>${T_SPEED:x}",
              "move y:(r4+$4),x0", f"move x0,y:>${T_A0:x}",
              "move y:(r4+$3),x0", f"move x0,y:>${T_LEN:x}",
              *((f"move y:>${T_A0:x},a", "add x0,a", "sub #>$1,a", f"move a1,y:>${T_END:x}") if low else ()),
              "move x:(r4+$5),r1", "nop", "move y:(r1),y0",
              f"move #>${PAGE_STRIDE:x},x0", "mpy y0,x0,a", "asr a", "move a0,a",
              f"add #>${PAGES:x},a", f"move a1,y:>${T_TAB:x}",
              "move y:>$1405,a", "asl #4,a,a", f"add #>${ST:x},a", "move a1,r6",
              *((f"move y:>${T_TAB:x},x0", "move x0,y:(r6+$f)") if low and "wsb" in low else ()),   # (v6) for WSB
              f"move y:(r6+${INIT:x}),a", "tst a"):
        E(s)
    E(("jcc", "ne", "inited"))                    # a fresh note (cleared by pitchmod's TRIG): grain 1 half way, its window at 1 and coming down
    for s in (f"move y:>${T_A0:x},x0", f"move x0,y:(r6+${G1 + G_R:x})", half, f"move x0,y:(r6+${G1 + G_PH:x})",
              f"move #>${_w(v3)[0]:x},x0", f"move x0,y:(r6+${G1 + G_W:x})", f"move y:>${GNSTEP:x},x0" if grain else f"move #>${(-_w(v3)[1]) & 0xFFFFFF:x},x0",
              f"move x0,y:(r6+${G1 + G_DW:x})", "move #>$1,x0", f"move x0,y:(r6+${INIT:x})"):
        E(s)
    E(("label", "inited"))
    for s in ("clr a", f"move #>${BUF:x},r1", ("words", [0x060120]), "move a,x:(r1)+",   # the block's output at 0 (rep x:$1)
              "clr b", "move y:(r4),b1", "asr #15,b,b", "move b1,y1", "move b0,y0",      # Y = r (int.frac)
              "move r6,a", f"add #>${G0:x},a", "move a1,r2"):
        E(s)
    E(("jsr", "grn"))
    for s in ("move r6,a", f"add #>${G1:x},a", "move a1,r2"):
        E(s)
    E(("jsr", "grn"))
    # P += x:$1 x r x speed
    for s in ("move y:(r4),x0", f"move y:>${T_SPEED:x},y0", "mpy y0,x0,b", "asr #13,b,b",
              "clr a", "move y:(r6),a1", "move y:(r6+$1),a0"):
        E(s)
    E(("do", "p_end"))
    E("add b,a")
    E(("label", "p_end"))
    for s in ("move a1,y:(r6)", "move a0,y:(r6+$1)", f"move y:>${T_LEN:x},x0", "cmp x0,a"):
        E(s)
    E(("jcc", "lt", "s_x"))                       # past the end: the envelope's fast release
    for s in ("move x:(r4+$a),a", "cmp #>$4,a"):
        E(s)
    E(("jcc", "ge", "s_x"))
    E("move #>$4,x0"); E("move x0,x:(r4+$a)")
    E(("label", "s_x"))
    E("rts")
    E(("label", "stock"))
    E(("jmp", P_RESAMPLE))
    # ---- GRN (r2 = a grain's block, r6 = the voice's state, Y = r): its part of the block added into X:$2A02..
    E(("label", "grn"))
    for s in (f"move y:(r2+${G_R:x}),a1", f"move y:(r2+${G_RF:x}),a0", "move #$0,a2",
              f"move y:(r2+${G_PH:x}),n2", f"move #>${BUF:x},r1", "move #>$ffffff,n3"):          # n3: no page cached
        E(s)
    E(("do", "g_end"))
    E("move n2,b"); E("tst b"); E(("jcc", "ne", "g_go"))          # phase 0: a new grain at the playhead, its window from 0 up
    if low and "wsb" in low:                                     # (v6) the start WSB left in the grain's word + 5, else the playhead
        import wsola as WS
        for s in ("move y:(r6),a", "move y:(r6+$1),a0", f"move y:>${T_A0:x},x0", "add x0,a",
                  f"move y:(r2+${WS.PEND:x}),b", "tst b"):
            E(s)
        E(("jcc", "eq", "g_rs"))
        E("tfr b,a")
        E(f"move y:>${WS.RONF:x},a0")
        E(("label", "g_rs"))
        E("clr b")
        E(f"move b,y:(r2+${WS.PEND:x})")
    elif low:
        E(("jsr", low["ws"]))                                    # WSOLA: where the new grain starts (P + A0 or near it)
    for s in (*(() if low else ("move y:(r6),a1", "move y:(r6+$1),a0", "move #$0,a2", f"move y:>${T_A0:x},x0", "add x0,a")),
              "clr b", f"move b,y:(r2+${G_W:x})", f"move y:>${GSTEP:x},x0" if grain else f"move #>${_w(v3)[1]:x},x0", f"move x0,y:(r2+${G_DW:x})"):
        E(s)
    E(("label", "g_go"))
    if low:
        for s in (f"move y:>${T_END:x},x0", "cmp x0,a"):         # past the sample's last word: nothing
            E(s)
        E(("jcc", "ge", "g_sil"))
    for s in ("tfr a,b", "lsr #12,b", "move b1,x0", "move n3,b", "cmp x0,b"):
        E(s)
    E(("jcc", "eq", "g_pg"))
    E(("jsr", low["trp"] if low else "trp"))
    E(("label", "g_pg"))
    for s in ("move a1,b", "and #>$fff,b", "move r3,x0", "add x0,b", "move b1,r5", "nop",
              "move y:(r5)+,b", "move b1,n5", "move y:(r5),b", "move n5,x0", "sub x0,b", "move b,x0",   # x0 = s1 - s0
              "move a0,b", "lsr b", "move b1,x1",                                                      # x1 = f / 2
              "mpy x1,x0,b", *(() if grain else ("asl b",)), "move n5,x0", "add x0,b",              # s0 + f (s1 - s0)
              "move b,x1", f"move y:(r2+${G_W:x}),x0", "mpy x1,x0,b",   # x the window
              "move x:(r1),x0", "add x0,b", "move b,x:(r1)+"):
        E(s)
    if low:
        E(("jmp", "g_win"))
        E(("label", "g_sil"))
        E("move (r1)+")
        E(("label", "g_win"))
    for s in (f"move y:(r2+${G_W:x}),b", f"move y:(r2+${G_DW:x}),x0", "add x0,b", f"move b,y:(r2+${G_W:x})",
              "add y,a",                                                                                 # R += r
              "move n2,b", "add #>$1,b",
              *((f"move y:>${GMASK:x},x0", "and x0,b", "move b1,n2", f"move y:>${GHALF:x},x0", "cmp x0,b") if grain else
                (f"and #>${G - 1:x},b", "move b1,n2", f"cmp #>${G // 2:x},b"))):
        E(s)
    E(("jcc", "ne", "g_nx"))
    for s in (f"move y:(r2+${G_DW:x}),b", "neg b", f"move b,y:(r2+${G_DW:x})"):               # the window comes down
        E(s)
    E(("label", "g_nx"))
    E("nop")
    E(("label", "g_end"))
    for s in (f"move a1,y:(r2+${G_R:x})", f"move a0,y:(r2+${G_RF:x})", f"move n2,y:(r2+${G_PH:x})", "rts"):
        E(s)
    if low:
        return L
    # ---- TRP (x0 = the page number in the sample): r3 = its physical base, n3 = x0; uses b, x1; keeps a, Y
    E(("label", "trp"))
    for s in ("move x0,n3", "move x0,b", "lsr b", f"move y:>${T_TAB:x},x1", "add x1,b", "move b1,r3", "nop", "move y:(r3),b",
              "btst #0,x0"):
        E(s)
    E(("jcc", "cs", "tp_lo"))
    E("lsr #12,b")
    E(("jmp", "tp_pg"))
    E(("label", "tp_lo"))
    E("and #>$fff,b")
    E(("label", "tp_pg"))
    for s in ("asl #12,b,b", "move b1,r3", "rts"):
        E(s)
    return L


def code(at, v3=False, grain=False, low=None):
    assert v3 or not grain
    return V.assemble(items(v3, grain, low), at)


def low_consts():
    """what tools/wsola.py needs of ours"""
    import dspload
    return dict(T_A0=T_A0, T_LEN=T_LEN, T_END=T_END, T_TAB=T_TAB, G0=G0, G1=G1, BUF=BUF, BLOCKS=dspload.Y_BLOCKS + 0x300,
                GMASK=GMASK, GHALF=GHALF, ST=ST, STRETCH=STRETCH, GHM=GHM, INIT=INIT)


def grain_words(g, ghm=False):
    """-> {GSTEP: .., GNSTEP: .., GHALF: .., GMASK: ..} for a grain of g samples (a power of 2, 256 .. 16384; v3's windows: top 1/2);
    ghm (RD16 on, never before: RD12-RD15's probe command word): also GHM = G / 2 - 1"""
    assert g & (g - 1) == 0 and 256 <= g <= 16384, g
    step = 0x400000 // (g // 2)
    return {GSTEP: step, GNSTEP: -step & 0xFFFFFF, GHALF: g // 2, GMASK: g - 1, **({GHM: g // 2 - 1} if ghm else {})}
