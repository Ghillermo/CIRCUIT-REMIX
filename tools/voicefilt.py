"""K6 filter types, pitch follow and the start-point scan per track in the Circuit Rhythm 5706's DSP core 1, the voices (MIT; the user,
2026-10-24: «k6: filter type (affects default filters) … by default, stock filter (sound is unaffected) shift: pitch follow to lpf»; «k8: scan
lfo speed (changes start point)», Shift: scan depth).

The stock (core 1's program, tools/rhdsp.py dis 1; measured in dsptool, docs/PORTADO.md «Modos del sampler»):
  * a voice's filter is two biquads in $511: $56E = the high-pass (cutoff index y:(r7 + $B), P:$51D loads it into n5), then $590 = the
    low-pass (cutoff index y:(r7 + $C), P:$523; resonance y:(r7 + $D), P:$525 into b); r7 = the voice's parameters; the index is in semitones
    (the curve X:$2A4E, 129 words); each computes 5 coefficients into Y:$1400..$1404 and runs the biquad loop $5B3 (state: 4 words at y:(r4),
    input X:$2A00.. -> output X:$2A24.. for the high-pass, back for the low-pass; P:$58E is $56E's jmp $5B3);
  * a note's start: P:$32D (in $2FD) turns the start knob's words into the fraction of the sample to start at (b), then the address.
Ours (after pitchmod's and voicefx's words, tools/rhdsp1.py; only with the Y words moved up: shift = $300):
  * P:$51D -> jsr HPIDX: the stock's index, or 0 (open) for the comb;
  * P:$523 -> jsr LPIDX, P:$525 -> nop: the stock's index + follow x the pitch in semitones (pitchmod's store_pitch), clamped to 0..128,
    and the resonance; for the comb 128 (open) and no resonance;
  * P:$58E -> jmp HPSAVE: the high-pass's coefficients kept per voice (for the second pass), then $5B3;
  * POST (voicefx calls it first): type 1 = 24 dB, both biquads run again on the voice's buffer with their own state (the high-pass with the
    kept coefficients, the low-pass with Y:$1400.., still the voice's); type 2 = comb: voicefx's comb (mode 5) tuned by the low-pass's index
    (D = 2 pi / c(index) samples, c = the stock's cutoff curve, so the comb's pitch
    is the low-pass's cutoff; 8..255 samples, 188 Hz .. 6 kHz) with the resonance as feedback (0.3 .. 0.95);
  * P:$32D -> jsr SCAN: the stock's shift, then the start fraction + depth x |phase| (pitchmod's scan phase; clamped below the end).
Core 1's Y, track t at + t (from pitchmod's base $1610): $16A0 type (0 stock, 1 24 dB, 2 comb), $16A8 follow (fraction), $16B0 the pitch
(pitchmod), $16B8 scan step per pitch update, $16C0 scan depth (fraction of the sample), $16C8 scan phase (pitchmod); $16F0.. scratch;
Y:$1700 + 8 v the second biquads' states, Y:$1740 + 8 v the kept high-pass coefficients.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pitchmod as PM  # noqa: E402
import voicefx as V  # noqa: E402

SHIFT = 0x300
YB = PM.Y_BASE + SHIFT
KTYPE, FOLLOW, PITCH, SCANR, SCAND, SCANPH = (YB + o for o in (0x90, 0x98, PM.OFF_PITCH, PM.OFF_SCANR, 0xB0, PM.OFF_SCANPH))
TMP = YB + 0xE0
STATE2, HPC = 0x1700, 0x1740
FXB = V.Y_BASE + SHIFT
P_HPIDX, P_LPIDX, P_RES, P_HPSAVE, P_SCAN = 0x51D, 0x523, 0x525, 0x58E, 0x32D
OLD = {P_HPIDX: (0x0B77DD, 0x00000B), P_LPIDX: (0x0B77DD, 0x00000C), P_RES: (0x0237FF,), P_HPSAVE: (0x0AF080, 0x0005B3), P_SCAN: (0x0C1D93,)}
BIQUAD = 0x5B3
FS = 48000.0
JSR_SHORT = 0x0D0000


C_LO = round(2 * math.pi / 256 * 0x800000)                                    # the cutoff curve's value for a delay of 256 samples
FB_0, FB_K = round(0.3 * 0x800000), round(0.65 * 128 / 127 * 0x800000)      # the comb's feedback: 0.3 + 0.65 x resonance / 127


def items():
    L = []
    E = L.append
    # ---- HPIDX (P:$51D): n5 = the high-pass's index (comb: 0)
    E(("label", "hpidx"))
    for s in ("move y:>$1405,n1", f"move #>${KTYPE:x},r1", "move y:(r7+$b),n5", "move y:(r1+n1),a", "cmp #>$2,a"):
        E(s)
    E(("jcc", "ne", "hp_x"))
    E("move #>$0,n5")
    E(("label", "hp_x"))
    E("rts")
    # ---- LPIDX (P:$523, P:$525 nop): n5 = the low-pass's index (+ follow), b = the resonance (comb: 128, 0)
    E(("label", "lpidx"))
    for s in ("move y:>$1405,n1", f"move #>${KTYPE:x},r1", "move y:(r1+n1),a", "cmp #>$2,a"):
        E(s)
    E(("jcc", "eq", "lp_c"))
    for s in ("move y:(r7+$c),a", f"move #>${FOLLOW:x},r1", "move y:(r1+n1),x0", f"move #>${PITCH:x},r1", "move y:(r1+n1),b",
              "asr #16,b,b", "move b1,y0", "mpyr y0,x0,b", "add b,a", "move #>$80,x0", "cmp x0,a", "tgt x0,a", "move #>$0,x0",
              "cmp x0,a", "tlt x0,a", "move a1,n5", "move y:(r7+$d),b", "rts"):
        E(s)
    E(("label", "lp_c"))
    E("move #>$80,n5"); E("clr b"); E("rts")
    # ---- HPSAVE (P:$58E): the high-pass's 5 coefficients (Y:$1400..) kept for this voice, then the stock's loop
    E(("label", "hpsave"))
    for s in ("move y:>$1405,a", "asl #3,a,a", f"add #>${HPC:x},a", "move a1,r2"):
        E(s)
    for k in range(5):
        E(f"move y:>${0x1400 + k:x},x0"); E("move x0,y:(r2)+")
    E(("jmp", BIQUAD))
    # ---- POST (voicefx's FX calls it first; r0 = the voice + 4 is kept)
    E(("label", "post"))
    for s in ("move y:>$1405,n1", f"move #>${KTYPE:x},r1", "move y:(r1+n1),a", "cmp #>$1,a"):
        E(s)
    E(("jcc", "eq", "p24"))
    E("cmp #>$2,a")
    E(("jcc", "eq", "pcomb"))
    E("rts")
    E(("label", "p24"))
    for s in ("move y:>$1405,a", "asl #3,a,a", "move a,b", f"add #>${STATE2:x},a", "move a1,r4", f"add #>${HPC:x},b", "move b1,r5",
              "move #>$2a00,r1", "move #>$2a24,r3", "move #>$fffffc,n5", "move #>$2,n1", "move #>$2,n3", "move #>$fffffd,n4"):
        E(s)
    E(("jsr", BIQUAD))                                                              # the high-pass again: X:$2A02.. -> X:$2A26..
    for s in ("move #>$2a24,r1", "move #>$2a00,r3", "move #>$1400,r5"):
        E(s)
    E(("jsr", BIQUAD))                                                              # the low-pass again: -> X:$2A02..
    E("rts")
    E(("label", "pcomb"))                                                           # D = 2 pi / c(index), c = the stock's cutoff curve X:$2A4E
    for s in ("move x:(r0+$1),r2", "nop", "move y:(r2+$c),n3", "move #>$2a4e,r3", "move x:(r3+n3),x0", f"move #>${C_LO:x},a",
              "cmp x0,a", "move #>$ff,x1"):                                         # c below 2 pi / 256: the longest delay
        E(s)
    E(("jcc", "ge", "pc_d"))
    for s in ("andi #$fe,ccr", "rep #$18", "div x0,a", "move a0,a", "lsr #15,a", "move a1,x1", "move #>$8,x0", "move x1,a", "cmp x0,a",
              "tlt x0,a", "move a1,x1"):
        E(s)
    E(("label", "pc_d"))                                                            # x1 = D; the feedback 0.3 + 0.65 x resonance / 127
    for s in ("move y:(r2+$d),a", "asl #16,a,a", "move a,y0", f"move #>${FB_K:x},x0", "mpy y0,x0,a", f"add #>${FB_0:x},a",
              "move a,y0", f"move #>${FXB:x},r1", "lua (r1)+n1,r1", f"move x1,y:(r1+${V.FF:x})", f"move y0,y:(r1+${V.FQ:x})",
              "move #>$5,x0", f"move x0,y:(r1+${V.FMODE:x})", "rts"):
        E(s)
    # ---- SCAN (P:$32D): the stock's shift, then the start fraction + depth x |phase|
    E(("label", "scan"))
    E("asl #9,b,b")
    saves = (("a1", 0), ("a0", 1), ("a2", 2), ("x0", 3), ("x1", 4), ("r1", 5), ("n1", 6))
    for r, k in saves:
        E(f"move {r},y:>${TMP + k:x}")
    for s in ("move n3,a", "and #>$7,a", "move a1,n1", f"move #>${YB:x},r1", "lua (r1)+n1,r1",
              f"move y:(r1+${SCANPH - YB:x}),a", "abs a", "move a,x1", f"move y:(r1+${SCAND - YB:x}),x0", "mpy x1,x0,a",
              "add a,b", "move #>$7f0000,x0", "cmp x0,b", "tgt x0,b"):
        E(s)
    for r, k in reversed(saves):
        E(f"move y:>${TMP + k:x},{r}")
    E("rts")
    return L


def code(at):
    """-> (words for P:at.., labels)"""
    return V.assemble(items(), at)


def patches(labels):
    """-> [(P address, old word, new word)] in core 1's stock program"""
    jsr = lambda a: [0x0BF080, a]                                                 # noqa: E731
    out = []
    for pa, new in ((P_HPIDX, jsr(labels["hpidx"])), (P_LPIDX, jsr(labels["lpidx"])), (P_RES, [0x000000]),
                    (P_HPSAVE, [0x0AF080, labels["hpsave"]]), (P_SCAN, [JSR_SHORT | labels["scan"]])):
        for k, (o, n) in enumerate(zip(OLD[pa], new)):
            out.append((pa + k, o, n))
    return out
