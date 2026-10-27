"""The granular in stereo: the grains' side signal into the main mix after the stock's mix (MIT; RH47; CIRCUIT-HACKS' Beta 3.12 «Granular en
estéreo», for the Rhythm's core 0; the user, 2026-10-27: Shift + K2 = the spread).

The stock (core 0's program): P:$367 mixes each track's 32 mono samples into three stereo buses of shared X memory, the main one X:$30430
(L R interleaved), with per-sample gains X:$DE + 64 t + 2 i (left) / + 1 (right) (level, pan, side-chain: P:$BEF; the sends' gains at
+ $200 / + $400).  Ours, with granular0 / granchain stereo (each grain a pan p = rnd x SPRD / 128: the grains' mono sum M as always into
the track's samples, their side S = sum of the grains x p, through the same gate, VCA and filter, into Y:SB):
  * GST at P:$224 (`jsr GST`, the last of the hook's chain: GST calls LI, which goes on to SPL, GR, the chain and the stock's mix, and comes
    back here), then, while the granular engine runs with a spread (its key, its track, SPRD <> 0, a sample): the main bus's
    L[i] += S[i] x gL[i], R[i] -= S[i] x gR[i], with the granular track's own gains: so a grain panned p sounds (1 + p) left, (1 - p) right
    of the track's level and pan; the sends get M only.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core0 as C0  # noqa: E402
import granular0 as G  # noqa: E402

AT = 0x2F00                                            # P (linein at $2E00)
AT_M = 0x3A00                                          # (RH50, multi) every running slot with a spread: its side SBY + $20 s
HOOK = 0x224
GAINS, MAIN = 0xDE, 0x30430
Y0 = 0x1530                                            # core 0 Y: r0, r1, r4, then m0, m1, m4
SV = Y0


def items(entry, multi=False):
    L = []

    def e(*s):
        L.extend(s)
    if multi:
        e(("label", "gst"), ("jsr", entry))
        for i, k in enumerate((0, 1, 4)):
            e(f"move r{k},y:>${SV + i:x}", ("words", [0x057060 | k, SV + 3 + i]), ("words", [0x05F420 | k, 0xFFFFFF]))
        for s in range(G.NSLOT):
            y = G.slot_y(s)
            v = y + 0x10
            e(f"move y:>${y + G.P_KEY:x},a", f"move #>${G.KEY:x},x0", "cmp x0,a", ("jcc", "ne", f"gs_n{s}"),
              f"move y:>${y + G.P_TRK:x},a", "tst a", ("jcc", "eq", f"gs_n{s}"),
              f"move y:>${y + G.P_SPRD:x},a", "tst a", ("jcc", "eq", f"gs_n{s}"),
              f"move y:>${v + G.V_ACT:x},a", "tst a", ("jcc", "eq", f"gs_n{s}"),
              f"move y:>${v + G.V_ON:x},a", "tst a", ("jcc", "eq", f"gs_n{s}"),
              f"move y:>${v + G.V_T:x},a", "and #>$7,a", "asl #6,a,a", f"add #>${GAINS:x},a", "move a1,r4",
              f"move #>${G.SBY + 0x20 * s:x},r1", f"move #>${MAIN:x},r0", "nop",
              "do #$20,${" + f"gs_l{s}" + ":x}",
              "move y:(r1)+,y0",
              "move x:(r4)+,x0", "move x:(r0),a", "mac y0,x0,a", "move a,x:(r0)+",
              "move x:(r4)+,x0", "move x:(r0),a", "mac -y0,x0,a", "move a,x:(r0)+",
              ("label", f"gs_l{s}"), ("label", f"gs_n{s}"))
        for i, k in enumerate((0, 1, 4)):
            e(f"move y:>${SV + i:x},r{k}", ("words", [0x05F060 | k, SV + 3 + i]))
        e("rts")
        return L
    e(("label", "gst"), ("jsr", entry),
      f"move x:>${G.GB + G.P_KEY:x},a", f"move #>${G.KEY:x},x0", "cmp x0,a", ("jcc", "ne", "gs_x"),
      f"move x:>${G.GB + G.P_TRK:x},a", "tst a", ("jcc", "eq", "gs_x"),
      f"move x:>${G.GB + G.P_SPRD:x},a", "tst a", ("jcc", "eq", "gs_x"),
      f"move x:>${G.VS + G.V_ON:x},a", "tst a", ("jcc", "eq", "gs_x"))
    for i, k in enumerate((0, 1, 4)):
        e(f"move r{k},y:>${SV + i:x}", ("words", [0x057060 | k, SV + 3 + i]), ("words", [0x05F420 | k, 0xFFFFFF]))
    e(f"move x:>${G.VS + G.V_T:x},a", "and #>$7,a", "asl #6,a,a", f"add #>${GAINS:x},a", "move a1,r4",
      f"move #>${G.SB:x},r1", f"move #>${MAIN:x},r0", "nop",
      "do #$20,${gs_l:x}",
      "move y:(r1)+,y0",
      "move x:(r4)+,x0", "move x:(r0),a", "mac y0,x0,a", "move a,x:(r0)+",
      "move x:(r4)+,x0", "move x:(r0),a", "mac -y0,x0,a", "move a,x:(r0)+",
      ("label", "gs_l"))
    for i, k in enumerate((0, 1, 4)):
        e(f"move y:>${SV + i:x},r{k}", ("words", [0x05F060 | k, SV + 3 + i]))
    e(("label", "gs_x"), "rts")
    return L


def code(entry, multi=False):
    at = AT_M if multi else AT
    w, labels = C0.asm_at(items(entry, multi), at)
    assert at + len(w) <= C0.LD, hex(at + len(w))
    return w, labels


def segs(entry, multi=False):
    """for granular0's extra, the last: our code at P:AT and P:$224 -> jsr GST (GST calls `entry`, the hook's previous target)"""
    w, labels = code(entry, multi)
    return [(AT_M if multi else AT, w), (HOOK, [0x0BF080, labels["gst"]])]


def model(main, side, gains):
    """the main bus after GST (floats; main = 64 L R words, side = 32, gains = 64 gL gR words)"""
    out = list(main)
    for i in range(32):
        out[2 * i] += side[i] * gains[2 * i]
        out[2 * i + 1] -= side[i] * gains[2 * i + 1]
    return out
