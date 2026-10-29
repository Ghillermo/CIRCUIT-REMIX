"""A mono VA synth with FM on the Circuit Rhythm's DSP core 0, any track (MIT; RD31 / RH51; the user, 2026-10-27: «Synths?» -> «both»; mono,
VA with FM, any track: docs/PORTADO.md «Diseño del sinte»).  Our own code, nothing of the Tracks' DSP program.

Where (the granular's and the line input's way): P:$224's chain GST -> SY -> LI -> SPL -> GR -> CH -> $367 (the stock's mix): SY writes a
synth track's 32 samples (Y:$304F0 + 64 t + 32 (y:$FFFFD0)) before the mix, so the track's level, pan, sends, side-chain, mute and cue
apply as to any track.  A synth on a track replaces its voice (core 1 still plays the track's sample, unheard).
The notes: core 0 reads the trigger queue itself (the ARM's 16 pairs at Y:$30410 + 2 i, its write index Y:$307B5; core 1 has its own read
index $307B6, ours is Y:QRD): note-on {$90 | t << 16 | velocity << 8 | t, (note - 60) << 16} (the pitch in our units: a semitone = $10000),
note-off {$80 | t ...} (the ARM sends one before a note-on while a note sounds, and at the end of a gated note; none in one-shot).
Checked in dsptool (RD31): core 1 does not start a voice whose sample slot is empty (stage 3, level 0, its gain 0): no envelope of the
stock to borrow, so the synth has its own, with the stock knob's meaning (the track's envelope knob, Y:$307C8 + $20 t + 9, as the stock's
voice: below 64 an instant attack and a decay, the half-life 12 x 2^(n / 8) blocks; 64 = hold; above, an attack of 23 x 1.7^((n - 65) / 8)
blocks; measured on the stock's voice in dsptool: docs/PORTADO.md), a release on the note-off (C_REL).
Per slot (NSLOT, any track; Y:Y0 + $40 s: controls +0..+15, written by the ARM or tools/rhsynth.py; state +16..), per block:
  * the pitch: the note (glided: C_GLD per block) + C_OCT + the track's pitch knob ((p6 - 64) / 5 semitones, as the stock's) -> OSC 1;
    + C_P2 -> OSC 2; each to an increment by the table INCT (a semitone apart, linearly between) and 1 / increment (for the polyBLEP);
  * OSC 2: its phases (reset at each wrap of OSC 1 with SYNC), its wave; OSC 1: its phases + 2 FM x OSC 2 (phase modulation; FM = C_FM +
    velocity x C_VFM), its wave; waves: saw, pulse (two saws, width C_K), triangle, sine (parabola, refined); saw and pulse with polyBLEP
    (naive under FM); the SUB (a square an octave under OSC 1) and the noise (an LCG) when their gains are on;
  * the mix G1 OSC 1 + G2 OSC 2 + GS SUB + GN noise, the envelope x velocity ramped across the block, then the track's filter knobs as the
    granular's chain has them (Chamberlin's SVF, 2x: low-pass from + $C, high-pass from + $B, the resonance + $D; the stock's cutoff curve),
    the low-pass index + C_EF x the envelope.
  * A slot whose envelope rests writes zeros (the track silent); a slot off (KEY, TRK) leaves the track's samples alone.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core0 as C0  # noqa: E402

AT = 0x2010                                            # P (granular0's single-track place, free since RH50's multi; RD20's test seg at $2000)
TAB = 0x2890                                           # P: the tables (after stsplit's $2600-$2883)
Y0, SN, NSLOT = 0x1A00, 0x40, 4                        # core 0 Y (free: docs/RECURSOS.md)
PB1, PB2, PB3 = 0x1B00, 0x1B20, 0x1B40                 # Y: OSC 1, OSC 2, SUB + noise for one block
GL = 0x1B60
(G_QKEY, G_QRD, G_THL, G_THH, G_RM, G_RE, G_K, G_T1, G_T2, G_P1O, G_GS, G_GSN, G_GN, G_PS, G_INCS, G_NZ) = range(GL, GL + 16)
SAVE = 0x1B70                                          # r0..r6, m0..m6
(C_TRK, C_SHP, C_P2, C_OCT, C_G1, C_G2, C_GS, C_GN, C_FM, C_K, C_GLD, C_VFM, C_REL, C_KEY, C_EF, C_SP) = range(16)
(S_MAG, S_PH1, S_PH2, S_PHS, S_NZ, S_PIT, S_TGT, S_STG, S_ENV, S_VEL, S_EC, S_ES, S_INC1, S_RM1, S_RE1, S_INC2, S_RM2, S_RE2, S_T, S_BUF,
 S_LL, S_LB, S_HL, S_HB, S_FL, S_FH, S_QL, S_LON, S_HON, S_TFL, S_TFH, S_INCS) = range(16, 48)
SHP_SYNC = 0x10                                        # C_SHP: bits 0-1 OSC 1's wave, 2-3 OSC 2's, 4 sync
SAW, PULSE, TRI, SINE = range(4)
ATT, DEC, REL, IDLE = range(4)
KEY, MAGIC, QMAGIC = 0x5C1A7E, 0x5E77A1, 0x9E0E1D
ONE, FLOOR = 0x7FFFFF, 0x000200
QBASE, QWIDX = 0x30410, 0x307B5
TRK_BUF, PAR = 0x304F0, 0x307C8
P_PITCH, P_ENV, HP_I, LP_I, RES_I = 6, 9, 0xB, 0xC, 0xD
K_LO, K_HI = -84, 60                                   # INCT's semitones from C4 (8.2 Hz .. 8.4 kHz)
P_MIN, P_MAX = K_LO << 16, ((K_HI - 1) << 16) | 0xFFFF
FS = 48000.0
LCG_A, LCG_C = 1664525 & 0xFFFFFF, 1013904223 & 0xFFFFFF
KNOB_PU = 0x3333                                       # the stock's pitch knob: a fifth of a semitone a step
# env2 (RH54; the user, 2026-10-28: «add start length for envelope controls (percussive env for one shot.  Unitary sustain: atk/release for
# gated, atk/sustain for loop), slope for env to amp and dist for env to filt»; the loop's: «Attack + sustain time»; the slope «From the
# centre»): the envelope by the track's play mode (C_MODE, the ARM's: 0 one-shot, 1 gated, 2 loop), linear segments shaped by the slope:
#   * one-shot: up by C_ATK a block, then down by C_DEC (percussive; the note-off ignored);
#   * gated: up by C_ATK, held at the top while the note is held, then down by C_DEC (the note-off during the attack: down from there);
#   * loop: up by C_ATK, held for C_HOLD blocks and while the note is held, whichever ends later, then down by C_RQ (a short release);
#   * the shape: out = e + C_SLP (e^2 - e) (C_SLP -1 .. 1: right = exponential, left = rounder), S_ENV = out (the VCA x velocity, the
#     filter's C_EF), S_VCA = out x velocity.
# The same blocks for the granular slots (GE0 + $40 g: the controls C_TRK, C_KEY, C_EF and these, written by the ARM): the queue's notes
# open and close them, granchain's env option takes S_VCA as the VCA and C_EF x S_ENV on the low-pass.
(C_ATK, C_DEC, C_HOLD, C_MODE, C_SLP, C_RQ) = range(48, 54)
(S_LIN, S_HC, S_GATE, S_VCA) = range(54, 58)
SUS = 4
M_ONESHOT, M_GATED, M_LOOP = 0, 1, 2
GE0, GE_N = 0x1C00, 4                                  # core 0 Y (free in the RH builds: latdiag's place in RD24 only)
# sp (RH55, tools/sp0.py: Stock+ for the synth): hooks to sp0's entries (their fixed addresses) - TICK after the queue, NOTE for each of
# its messages, SPIT (+ the pitch envelope / LFO), SFM (+ the scan LFO on the FM amount), SDS (the stock's distortion knob on the mix),
# SLP / SHP (the filter's follow, the comb: both off), S24 (24 dB: the filter run again with the second states S_LL2 ..)
(S_LL2, S_LB2, S_HL2, S_HB2) = range(58, 62)
# sl (RH58; the user, 2026-10-29: «On synth voices, start/length do nothing ... Something new?» -> «1 and 3»: the stock's start knob = a
# morph of the waves, its length = unison; «Offset from K1/K2», «2 per oscillator»): the track's start (word 7, K2: 0 = the stock's
# default, nothing) moves each oscillator's wave onward from its K1 / K2 shape: q = 3 start (0..381), the wave (shape + q >> 7) & 3
# crossfaded into the next one by (q & 127) / 128 (saw -> pulse -> triangle -> sine -> saw); its length (word 8, K3; 127 = the default,
# nothing) below 127 plays each oscillator twice, at the pitch + and - (127 - length) x 2^7 (a quarter of a semitone at 0), the two copies'
# phases their own (S_PH1 / S_PH2 and S_PH1B / S_PH2B), averaged.  Three pieces in core 0's free P: at SL_AT (sp0's part b ends at $3944,
# gstereo at $3A00) the jump table (+0 UNI, +2 MW), OSC, u_swap, u_inc; MW at SLM_AT (after fxroute's FXZ, below LI's $2E00); UNI at SLU_AT
# (after granular0's GZ, below the loader's $3FE0).  The main's s_play calls UNI (a <> 0: done, on to the SUB / mix), passes C / D's waves go
# through MW.
SL_AT, SLM_AT, SLU_AT = 0x3948, 0x2D80, 0x3F92
PBX, PBA1, PBA2 = 0x1B80, 0x1BA0, 0x1BC0              # Y (free: the stock's $1B80.. are in X)
GU = 0x1BE0
(G_MF, G_TC, G_DT, G_R1S, G_RJ, G_T3) = range(GU, GU + 6)
S_PH1B, S_PH2B = 62, 63
P_START, P_LEN = 7, 8


def frac(x):
    return max(-(1 << 23), min((1 << 23) - 1, round(x * (1 << 23)))) & 0xFFFFFF


def s24(v):
    v &= 0xFFFFFF
    return v - (1 << 24) if v & 0x800000 else v


def dec_hl(n):
    return 12 * 2 ** (n / 8)                           # blocks


def att_blocks(n):
    return 23 * 1.7 ** ((n - 65) / 8)


def tables():
    import granchain as GCH
    t = GCH.tables()                                   # F2 (the stock's cutoff curve, 2x), Q2
    t["INCT"] = [frac(2 * 261.6255653 * 2 ** (k / 12) / FS) for k in range(K_LO, K_HI + 1)]
    t["ENVT"] = [frac(2 ** (-1 / dec_hl(n))) if n < 64 else ONE if n == 64 else frac(1 / att_blocks(n)) for n in range(128)]
    return t


def items(tab_at, entry, env2=False, sp=False, sl=False):
    L = []
    if sp:
        import sp0 as SP0
        hook = lambda n: [("jsr", SP0.entry(n))]                         # noqa: E731
    else:
        hook = lambda n: []                                              # noqa: E731

    def e(*s):
        L.extend(s)

    def y(a):
        return f"y:>${a:x}"

    def ys(o):
        return f"y:(r6+${o:x})"

    def svf(r):
        """one pass of Chamberlin's filter (granchain's c_svf, inline): in x1, f x0, q / 2 y0, L / B at y:(r) / y:(r + 1) -> L there, H in y1"""
        return [f"move y:({r}),a", f"move y:({r}+$1),y1", "mac x0,y1,a", f"move a,y:({r})",
                "move x1,b", "sub a,b", "mac -y1,y0,b", "mac -y1,y0,b",
                "tfr y1,a", "move b,y1", "mac x0,y1,a", f"move a,y:({r}+$1)"]

    # ================================================================ SY: the queue, each slot, then the hook's next (LI)
    e(("label", "sy"))
    for k in range(7):
        e(f"move r{k},{y(SAVE + k)}", ("words", [0x057060 | k, SAVE + 7 + k]), ("words", [0x05F420 | k, 0xFFFFFF]))
    e(("jsr", "sy_q"), *hook("tick"))
    for s in range(NSLOT):
        e(f"move #>${Y0 + SN * s:x},r6", "nop", ("jsr", "sy_slot"))
    if env2:
        for g in range(GE_N):
            e(f"move #>${GE0 + SN * g:x},r6", "nop", ("jsr", "ge_slot"))
    for k in range(7):
        e(f"move {y(SAVE + k)},r{k}", ("words", [0x05F060 | k, SAVE + 7 + k]))
    e(("jmp", entry))

    # ================================================================ sy_q: the trigger queue from our read index to the ARM's write index
    e(("label", "sy_q"), f"move {y(G_QKEY)},a", f"move #>${QMAGIC:x},x0", "cmp x0,a", ("jcc", "eq", "q_ok"),
      f"move {y(QWIDX)},a", "and #>$f,a", f"move a1,{y(G_QRD)}", f"move x0,{y(G_QKEY)}", "rts",
      ("label", "q_ok"), f"move {y(QWIDX)},a", "and #>$f,a", "move a1,x1",
      ("label", "q_lp"), f"move {y(G_QRD)},a", "cmp x1,a", ("jcc", "eq", "q_done"),
      "move a1,b", "asl b", f"add #>${QBASE:x},b", "move b1,r1",
      "add #>$1,a", "and #>$f,a", f"move a1,{y(G_QRD)}",
      "move y:(r1)+,y0", "move y:(r1),y1")
    for s in range(NSLOT):
        e(f"move #>${Y0 + SN * s:x},r6", "nop", ("jsr", "q_slot"))
    if env2:                                                            # (env2) the granular slots' envelopes too
        for g in range(GE_N):
            e(f"move #>${GE0 + SN * g:x},r6", "nop", ("jsr", "q_slot"))
    e(*hook("note"), ("jmp", "q_lp"), ("label", "q_done"), "rts")
    # q_slot (r6 = the slot; y0 = w0, y1 = w1; keeps x1)
    e(("label", "q_slot"), f"move {ys(C_KEY)},a", f"move #>${KEY:x},x0", "cmp x0,a", ("jcc", "ne", "q_r"),
      f"move {ys(C_TRK)},a", "tst a", ("jcc", "eq", "q_r"),
      "move y0,b", "and #>$7,b", "move b1,b", "add #>$1,b", "cmp a,b", ("jcc", "ne", "q_r"),
      ("jsr", "s_init"),
      "move y0,b", "and #>$f00000,b", "move b1,b", "move #>$900000,x0", "cmp x0,b", ("jcc", "ne", "q_off"),
      # note-on: the velocity (v / 127 ~ (v << 16) + (v << 9)), the target pitch, snapped when resting or without glide, the attack
      "move y0,a", "asr #8,a,a", "and #>$7f,a", "move a1,a", "move a1,x0", "asl #16,a,a", "move x0,b", "asl #9,b,b", "add b,a",
      f"move a1,{ys(S_VEL)}", f"move y1,{ys(S_TGT)}",
      f"move {ys(S_STG)},a", f"move #>${IDLE:x},x0", "cmp x0,a", ("jcc", "eq", "q_snap"),
      f"move {ys(C_GLD)},a", f"move #>${ONE:x},x0", "cmp x0,a", ("jcc", "lt", "q_att"),
      ("label", "q_snap"), f"move y1,{ys(S_PIT)}",
      ("label", "q_att"), "clr a", f"move a,{ys(S_STG)}")
    if env2:                                                            # (env2) the note held: the gate
        e(f"move #>${ONE:x},a", f"move a,{ys(S_GATE)}", "rts",
          ("label", "q_off"), "move #>$800000,x0", "cmp x0,b", ("jcc", "ne", "q_r"),
          "clr a", f"move a,{ys(S_GATE)}",
          ("label", "q_r"), "rts")
    else:
        e("rts",
          ("label", "q_off"), "move #>$800000,x0", "cmp x0,b", ("jcc", "ne", "q_r"),
          f"move {ys(S_STG)},a", f"move #>${IDLE:x},x0", "cmp x0,a", ("jcc", "eq", "q_r"),
          f"move #>${REL:x},a", f"move a,{ys(S_STG)}",
          ("label", "q_r"), "rts")

    # ================================================================ sy_slot (r6): one slot's block
    e(("label", "sy_slot"), f"move {ys(C_KEY)},a", f"move #>${KEY:x},x0", "cmp x0,a", ("jcc", "ne", "s_r"),
      f"move {ys(C_TRK)},a", "tst a", ("jcc", "eq", "s_r"),
      ("jsr", "s_init"))
    # the track; a new one: the filter's states from zero
    e(f"move {ys(C_TRK)},a", "sub #>$1,a", "and #>$7,a", "move a1,a", f"move {ys(S_T)},b", "cmp a,b", ("jcc", "eq", "s_same"),
      f"move a1,{ys(S_T)}", "clr b", *[f"move b,{ys(o)}" for o in (S_LL, S_LB, S_HL, S_HB, S_LON, S_HON)], ("label", "s_same"),
      # the buffer Y:$304F0 + 64 t + 32 (y:$FFFFD0), the track's parameters Y:$307C8 + $20 t (r5)
      "move a1,x0", "movep y:<<$ffffd0,b", "asl #5,b,b", "move b1,x1", "tfr a,b", "asl #6,b,b", f"add #>${TRK_BUF:x},b", "add x1,b",
      f"move b1,{ys(S_BUF)}", "tfr a,b", "asl #5,b,b", f"add #>${PAR:x},b", "move b1,r5",
      # glide: PIT += (TGT - PIT) x C_GLD
      f"move {ys(S_TGT)},a", f"move {ys(S_PIT)},b", "sub b,a", "move a,x0", f"move {ys(C_GLD)},y0", "mac y0,x0,b", f"move b,{ys(S_PIT)}",
      # the stock's pitch knob: (p6 - 64) x $3333
      f"move y:(r5+${P_PITCH:x}),a", "and #>$7f,a", "move a1,a", "sub #>$40,a", "move a1,x0", f"move #>${KNOB_PU:x},y0", "mpy y0,x0,a",
      "asr a", "move a0,x0",
      f"move {ys(S_PIT)},a", "add x0,a", f"move {ys(C_OCT)},x0", "add x0,a", *hook("spit"), f"move a,{y(G_T1)}",
      f"lua (r6+${S_INC1:x}),r4", ("jsr", "s_inc"),
      f"move {y(G_T1)},a", f"move {ys(C_P2)},x0", "add x0,a", f"lua (r6+${S_INC2:x}),r4", ("jsr", "s_inc"),
      f"move {ys(S_INC1)},a", "asr a", f"move a,{ys(S_INCS)}",
      ("jsr", "s_env2" if env2 else "s_env"),
      # resting and silent: zeros, and nothing more
      f"move {ys(S_BUF)},r0", f"move {ys(S_STG)},a", f"move #>${IDLE:x},x0", "cmp x0,a", ("jcc", "ne", "s_play"),
      f"move {ys(S_EC)},a", "tst a", ("jcc", "ne", "s_play"),
      "clr a", "rep #$20", "move a,y:(r0)+", ("label", "s_r"), "rts",
      ("label", "s_play"), *([("jsr", SL_AT), "tst a", ("jcc", "ne", "sy_ps")] if sl else []))

    # ---- pass A: OSC 1's phases -> PB1 (its phase at the block's start kept, for the sync)
    e(f"move {ys(S_PH1)},a", f"move a,{y(G_P1O)}", f"move {ys(S_INC1)},x0", f"move #>${PB1:x},r1", "nop",
      "do #$20,${a_end:x}", "add x0,a", "move a1,a", "move a,y:(r1)+", ("label", "a_end"), f"move a,{ys(S_PH1)}")
    # ---- pass B: OSC 2's phases -> PB2, reset to -1 where OSC 1 wraps (sync)
    e(f"move {ys(S_PH2)},a", f"move {ys(S_INC2)},x0", f"move #>${PB2:x},r2", f"move {ys(C_SHP)},b", f"and #>${SHP_SYNC:x},b", "tst b",
      ("jcc", "ne", "b_sync"),
      "do #$20,${b_end:x}", "add x0,a", "move a1,a", "move a,y:(r2)+", ("label", "b_end"), ("jmp", "b_done"),
      ("label", "b_sync"), f"move #>${PB1:x},r1", f"move {y(G_P1O)},y1", "nop",
      "do #$20,${bs_end:x}", "add x0,a", "move a1,a", "move y:(r1)+,b", "cmp y1,b", ("jcc", "ge", "bs_n"), "move #>$800000,a",
      ("label", "bs_n"), "move b,y1", "move a,y:(r2)+", ("label", "bs_end"),
      ("label", "b_done"), f"move a,{ys(S_PH2)}")
    # ---- pass C: OSC 2's wave (polyBLEP)
    e(f"move {ys(S_INC2)},a", f"lua (r6+${S_INC2:x}),r4", ("jsr", "s_wset"),
      f"move {ys(C_SHP)},a", "asr #2,a,a", "and #>$3,a", "move a1,a", f"add #>${tab_at['WT']:x},a", "move a1,r3", f"move #>${PB2:x},r1",
      "nop", "move p:(r3),r2", "nop", ("jsr", SL_AT + 2) if sl else "jsr (r2)")
    # ---- pass D: FM (C_FM + velocity x C_VFM) into OSC 1's phases, then its wave (naive under FM)
    e(f"move {ys(S_VEL)},x0", f"move {ys(C_VFM)},y0", "mpy y0,x0,a", f"move {ys(C_FM)},x0", "add x0,a", *hook("sfm"), "move a,y0", "clr b",
      "tst a", ("jcc", "eq", "d_wave"),
      f"move #>${PB1:x},r1", f"move #>${PB2:x},r2", "nop",
      "do #$20,${d_end:x}", "move y:(r2)+,x0", "mpy y0,x0,b", "asl b", "move y:(r1),a", "add b,a", "move a1,a", "move a,y:(r1)+",
      ("label", "d_end"), "move #>$4,b",
      ("label", "d_wave"), "move b,x1", f"move {ys(S_INC1)},a", f"lua (r6+${S_INC1:x}),r4", ("jsr", "s_wset"),
      f"move {ys(C_SHP)},a", "and #>$3,a", "move a1,a", "add x1,a", f"add #>${tab_at['WT']:x},a", "move a1,r3", f"move #>${PB1:x},r1",
      "nop", "move p:(r3),r2", "nop", ("jsr", SL_AT + 2) if sl else "jsr (r2)")
    # ---- pass S: SUB + noise -> PB3 (only with GS or GN)
    e(*([("label", "sy_ps")] if sl else []), f"move {ys(C_GS)},x0", f"move {ys(C_GN)},x1", "move x0,a", "add x1,a", ("jcc", "eq", "e_basic"),
      f"move x0,{y(G_GS)}", "clr a", "sub x0,a", f"move a,{y(G_GSN)}", f"move x1,{y(G_GN)}",
      f"move {ys(S_PHS)},a", f"move a,{y(G_PS)}", f"move {ys(S_NZ)},a", f"move a,{y(G_NZ)}", f"move {ys(S_INCS)},x1",
      f"move #>${PB3:x},r3", "nop",
      "do #$20,${p_end:x}",
      f"move {y(G_PS)},a", "add x1,a", "move a1,a", f"move a,{y(G_PS)}",
      f"move {y(G_GS)},b", "tst a", ("jcc", "ge", "p_pos"), f"move {y(G_GSN)},b", ("label", "p_pos"), f"move b,{y(G_T2)}",
      f"move {y(G_NZ)},x0", f"move #>${LCG_A:x},y0", "mpy y0,x0,a", "asr a", "move a0,x0", "move x0,a", f"add #>${LCG_C:x},a", "move a1,a",
      f"move a,{y(G_NZ)}", "move a,x0", f"move {y(G_GN)},y0", "mpy y0,x0,a", f"move {y(G_T2)},b", "add b,a",
      "move a,y:(r3)+", ("label", "p_end"),
      f"move {y(G_PS)},a", f"move a,{ys(S_PHS)}", f"move {y(G_NZ)},a", f"move a,{ys(S_NZ)}",
      # the mix with PB3
      f"move #>${PB1:x},r1", f"move #>${PB2:x},r2", f"move #>${PB3:x},r3", f"move {ys(C_G1)},y0", f"move {ys(C_G2)},y1", "nop",
      "do #$20,${mf_end:x}", "move y:(r1)+,x0", "mpy y0,x0,a", "move y:(r2)+,x0", "mac x0,y1,a", "move y:(r3)+,b", "add b,a",
      "move a,y:(r0)+", ("label", "mf_end"), ("jmp", "e_vca"),
      # the mix without
      ("label", "e_basic"),
      f"move #>${PB1:x},r1", f"move #>${PB2:x},r2", f"move {ys(C_G1)},y0", f"move {ys(C_G2)},y1", "nop",
      "do #$20,${mb_end:x}", "move y:(r1)+,x0", "mpy y0,x0,a", "move y:(r2)+,x0", "mac x0,y1,a", "move a,y:(r0)+", ("label", "mb_end"))
    # ---- the VCA: the envelope x velocity, ramped (EC += ES each sample)
    e(("label", "e_vca"), *hook("sds"), f"move {ys(S_BUF)},r0", f"move {ys(S_EC)},b", f"move {ys(S_ES)},x1", "nop",
      "do #$20,${v_end:x}", "add x1,b", "move y:(r0),x0", "move b,y0", "mpy y0,x0,a", "move a,y:(r0)+", ("label", "v_end"),
      f"move b,{ys(S_EC)}")
    # ---- the filter: the track's low-pass (+ C_EF x the envelope) and high-pass, as granchain's
    e(f"move y:(r5+${LP_I:x}),a", "and #>$7f,a", "move a1,a", f"move {ys(S_ENV)},x0", f"move {ys(C_EF)},y0", "mpy y0,x0,b",
      "asr #16,b,b", "move b1,b", "add b,a", *hook("slp"), "tst a", ("jcc", "ge", "f_lo"), "clr a", ("label", "f_lo"),
      "move #>$7f,x0", "cmp x0,a", ("jcc", "lt", "f_on"),
      "clr b", f"move b,{ys(S_LON)}", ("jmp", "f_hp"),
      ("label", "f_on"), f"add #>${tab_at['F2']:x},a", "move a1,r4", "nop", "move p:(r4),x0", f"move x0,{ys(S_TFL)}",
      f"move {ys(S_LON)},a", "tst a", ("jcc", "ne", "f_lon"), f"move x0,{ys(S_FL)}", "clr a", f"move a,{ys(S_LL)}", f"move a,{ys(S_LB)}",
      ("label", "f_lon"), "move #>$1,a", f"move a,{ys(S_LON)}",
      ("label", "f_hp"), f"move y:(r5+${HP_I:x}),a", "and #>$7f,a", "move a1,a", *hook("shp"), "tst a", ("jcc", "ne", "f_hon0"),
      "clr b", f"move b,{ys(S_HON)}", ("jmp", "f_sm"),
      ("label", "f_hon0"), f"add #>${tab_at['F2']:x},a", "move a1,r4", "nop", "move p:(r4),x0", f"move x0,{ys(S_TFH)}",
      f"move {ys(S_HON)},a", "tst a", ("jcc", "ne", "f_hon"), f"move x0,{ys(S_FH)}", "clr a", f"move a,{ys(S_HL)}", f"move a,{ys(S_HB)}",
      ("label", "f_hon"), "move #>$1,a", f"move a,{ys(S_HON)}",
      ("label", "f_sm"))
    for fn, tf in ((S_FL, S_TFL), (S_FH, S_TFH)):                                  # f += (target - f) / 8
        e(f"move {ys(tf)},a", f"move {ys(fn)},b", "sub b,a", "asr #3,a,a", "add b,a", f"move a,{ys(fn)}")
    e(f"move y:(r5+${RES_I:x}),a", "and #>$7f,a", "move a1,a", f"add #>${tab_at['Q2']:x},a", "move a1,r4", "nop", "move p:(r4),y0",
      f"move y0,{y(G_T2)}",
      f"move {ys(S_BUF)},r0", f"lua (r6+${S_LL:x}),r4", f"lua (r6+${S_HL:x}),r5",
      *([("jsr", "f_run"), *hook("s24"), "tst a", ("jcc", "eq", "s_r"),                 # (sp) 24 dB: again, the second states
         f"move {ys(S_BUF)},r0", f"lua (r6+${S_LL2:x}),r4", f"lua (r6+${S_HL2:x}),r5", ("label", "f_run")] if sp else []),
      f"move {ys(S_LON)},a", "tst a", ("jcc", "eq", "fl_hp"),
      f"move {ys(S_HON)},a", "tst a", ("jcc", "ne", "fl_both"),
      # the low-pass alone
      f"move {ys(S_FL)},x0", "do #$20,${fl_end:x}", "move y:(r0),x1", *svf("r4"), *svf("r4"), "move y:(r4),a", "move a,y:(r0)+",
      ("label", "fl_end"), "rts",
      # the high-pass alone
      ("label", "fl_hp"), f"move {ys(S_HON)},a", "tst a", ("jcc", "eq", "s_r"),
      f"move {ys(S_FH)},x0", "do #$20,${fh_end:x}", "move y:(r0),x1", *svf("r5"), *svf("r5"), "move y1,y:(r0)+",
      ("label", "fh_end"), "rts",
      # both
      ("label", "fl_both"),
      "do #$20,${fb_end:x}", "move y:(r0),x1", f"move {ys(S_FL)},x0", *svf("r4"), *svf("r4"), "move y:(r4),x1",
      f"move {ys(S_FH)},x0", *svf("r5"), *svf("r5"), "move y1,y:(r0)+", ("label", "fb_end"), "rts")

    # ================================================================ s_init (r6): a slot's state from zero, once (MAGIC); keeps x1, y0, y1
    e(("label", "s_init"), f"move {ys(S_MAG)},a", f"move #>${MAGIC:x},x0", "cmp x0,a", ("jcc", "eq", "i_r"),
      "clr a", f"lua (r6+${S_PH1:x}),r1", "nop", f"do #${S_INCS - S_PH1 + 1:x},${{s_z:x}}", "move a,y:(r1)+", ("label", "s_z"),
      f"move #>${IDLE:x},a", f"move a,{ys(S_STG)}", "move #>$1,a", f"move a,{ys(S_NZ)}", "move #>$ff,a", f"move a,{ys(S_T)}",
      *(["clr a"] + [f"move a,{ys(o)}" for o in (S_LIN, S_HC, S_GATE, S_VCA)] if env2 else []),
      f"move x0,{ys(S_MAG)}",
      ("label", "i_r"), "rts")
    # ================================================================ s_inc: a = the pitch (a semitone = $10000) -> y:(r4)+ = inc, 1 / inc's
    # mantissa (0.25 / the normalized inc) and its left shift
    e(("label", "s_inc"), f"move #>${P_MIN & 0xFFFFFF:x},x0", "cmp x0,a", "tlt x0,a", f"move #>${P_MAX:x},x0", "cmp x0,a", "tgt x0,a",
      "asr #16,a,b", f"add #>${tab_at['INCT'] - K_LO:x},b", "move b1,r3",
      "and #>$ffff,a", "move a1,a", "asl #7,a,a", "move a,x0",
      "move p:(r3)+,x1", "move p:(r3),b", "sub x1,b", "move b,y0", "mpy y0,x0,b", "add x1,b", "move b,y:(r4)+",
      "tfr b,a", "move #>$0,r3", "nop", "rep #$17", "norm r3,a",
      "move a,x0", "move #>$200000,a", "andi #$fe,ccr", "rep #$18", "div x0,a", "move a0,y:(r4)+",
      "move r3,a", "neg a", "add #>$2,a", "move a1,y:(r4)+", "rts")
    # s_wset: a = inc, r4 -> inc / mantissa / shift: the polyBLEP's words for a wave routine
    e(("label", "s_wset"), f"move #>${ONE:x},b", "sub a,b", f"move b,{y(G_THH)}",
      "move y:(r4)+,a", f"move #>${ONE:x},b", "sub b,a", f"move a,{y(G_THL)}", "move y:(r4)+,a", f"move a,{y(G_RM)}",
      "move y:(r4)+,a", f"move a,{y(G_RE)}", f"move {ys(C_K)},a", f"move a,{y(G_K)}", "rts")

    # ================================================================ the waves: in place on y:(r1) .. + 31 (phases in, samples out)
    def blep(tag):
        """a = p -> a = the saw with polyBLEP (x1 THL, y1 THH, y0 the mantissa; G_RE the shift)"""
        return ["cmp x1,a", ("jcc", "lt", f"{tag}a"), "cmp y1,a", ("jcc", "le", f"{tag}x"),
                f"move a,{y(G_T2)}", "sub y1,a", "move a,x0", "mpy y0,x0,a", f"move {y(G_RE)},b", "asl b1,a,a", "move a,x0", "mpy x0,x0,b",
                f"move {y(G_T2)},a", "sub b,a", ("jmp", f"{tag}x"),
                ("label", f"{tag}a"), f"move a,{y(G_T2)}", "tfr x1,b", "sub a,b", "tfr b,a", "move a,x0", "mpy y0,x0,a",
                f"move {y(G_RE)},b", "asl b1,a,a", "move a,x0", "mpy x0,x0,b", f"move {y(G_T2)},a", "add b,a",
                ("label", f"{tag}x")]
    e(("label", "w_saw"), f"move {y(G_THL)},x1", f"move {y(G_THH)},y1", f"move {y(G_RM)},y0", "nop",
      "do #$20,${ws_end:x}", "move y:(r1),a", *blep("ws"), "move a,y:(r1)+", ("label", "ws_end"), "rts")
    e(("label", "w_pul"), f"move {y(G_THL)},x1", f"move {y(G_THH)},y1", f"move {y(G_RM)},y0", "nop",
      "do #$20,${wp_end:x}", "move y:(r1),a", *blep("wp1"), f"move a,{y(G_T1)}",
      "move y:(r1),a", f"move {y(G_K)},b", "add b,a", "move a1,a", *blep("wp2"),
      f"move {y(G_T1)},b", "sub a,b", "asr b", "move b,y:(r1)+", ("label", "wp_end"), "rts")
    e(("label", "w_tri"), "do #$20,${wt_end:x}", "move y:(r1),a", "abs a", "neg a", "add #>$400000,a", "asl a", "move a,y:(r1)+",
      ("label", "wt_end"), "rts")
    e(("label", "w_sin"), "do #$20,${wn_end:x}", "move y:(r1),a", "move a,y0", "abs a", "neg a", f"add #>${ONE:x},a", "move a,x0",
      "mpy y0,x0,a", "asl #2,a,a", "move a,x0", "abs a", "move a,y0", f"move #>${frac(0.775):x},a", f"move #>${frac(0.225):x},x1",
      "mac x1,y0,a", "move a,y0", "mpy y0,x0,a", "move a,y:(r1)+", ("label", "wn_end"), "rts")
    e(("label", "w_puln"), f"move {y(G_K)},x0", "do #$20,${wq_end:x}", "move y:(r1),a", "tfr a,b", "add x0,b", "move b1,b", "sub b,a", "asr a",
      "move a,y:(r1)+", ("label", "wq_end"), ("label", "w_sawn"), "rts")
    # ================================================================ s_env: the envelope's block (r5 = the track's parameters)
    e(("label", "s_env"), f"move y:(r5+${P_ENV:x}),a", "and #>$7f,a", "move a1,a", "move a1,y1", f"add #>${tab_at['ENVT']:x},a", "move a1,r3",
      "nop", "move p:(r3),x0", f"move {ys(S_STG)},b", "tst b", ("jcc", "ne", "e_d"),
      "move y1,a", "move #>$40,y0", "cmp y0,a", ("jcc", "gt", "e_slow"), f"move #>${ONE:x},a", ("jmp", "e_top"),
      ("label", "e_slow"), f"move {ys(S_ENV)},a", "add x0,a", f"move #>${ONE:x},y0", "cmp y0,a", ("jcc", "lt", "e_st"),
      f"move #>${ONE:x},a",
      ("label", "e_top"), f"move #>${DEC:x},b", f"move b,{ys(S_STG)}", ("jmp", "e_st"),
      ("label", "e_d"), f"move #>${DEC:x},y0", "cmp y0,b", ("jcc", "ne", "e_r"),
      f"move {ys(S_ENV)},a", "move y1,b", "move #>$40,y0", "cmp y0,b", ("jcc", "ge", "e_st"),
      f"move {ys(S_ENV)},y0", "mpy y0,x0,a", ("jmp", "e_fl"),
      ("label", "e_r"), f"move #>${REL:x},y0", "cmp y0,b", ("jcc", "ne", "e_idle"),
      f"move {ys(S_ENV)},y0", f"move {ys(C_REL)},x0", "mpy y0,x0,a", ("jmp", "e_fl"),
      ("label", "e_idle"), "clr a", ("jmp", "e_st"),
      ("label", "e_fl"), f"move #>${FLOOR:x},y0", "cmp y0,a", ("jcc", "ge", "e_st"), "clr a", f"move #>${IDLE:x},b", f"move b,{ys(S_STG)}",
      ("label", "e_st"), f"move a,{ys(S_ENV)}",
      "move a,x0", f"move {ys(S_VEL)},y0", "mpy y0,x0,a", f"move {ys(S_EC)},b", "sub b,a", "asr #5,a,a", f"move a,{ys(S_ES)}", "rts")
    if env2:
        # ============================================================ s_env2 (r6): the envelope by the play mode, shaped (env2 above)
        e(("label", "s_env2"), f"move {ys(S_STG)},b",
          f"move #>${ATT:x},x0", "cmp x0,b", ("jcc", "ne", "e2_d"),
          f"move {ys(S_LIN)},a", f"move {ys(C_ATK)},x0", "add x0,a", f"move #>${ONE:x},x0", "cmp x0,a", ("jcc", "lt", "e2_a1"),
          f"move #>${ONE:x},a", f"move a,{ys(S_LIN)}",
          f"move {ys(C_MODE)},b", "tst b", f"move #>${DEC:x},b", ("jcc", "eq", "e2_stg"),      # the top: one-shot down, else held
          f"move {ys(C_HOLD)},x0", f"move x0,{ys(S_HC)}", f"move #>${SUS:x},b",
          ("label", "e2_stg"), f"move b,{ys(S_STG)}", ("jmp", "e2_sh"),
          ("label", "e2_a1"), f"move a,{ys(S_LIN)}",
          f"move {ys(C_MODE)},b", f"move #>${M_GATED:x},x0", "cmp x0,b", ("jcc", "ne", "e2_sh"),   # gated, let go in the attack: down
          f"move {ys(S_GATE)},b", "tst b", ("jcc", "ne", "e2_sh"),
          f"move #>${REL:x},b", f"move b,{ys(S_STG)}", ("jmp", "e2_sh"),
          ("label", "e2_d"), f"move #>${SUS:x},x0", "cmp x0,b", ("jcc", "eq", "e2_s"),
          f"move #>${IDLE:x},x0", "cmp x0,b", ("jcc", "eq", "e2_i"),
          f"move {ys(C_DEC)},x0",                                                              # DEC / REL: down
          f"move #>${REL:x},y0", "cmp y0,b", ("jcc", "ne", "e2_dn"),
          f"move {ys(C_MODE)},a", f"move #>${M_LOOP:x},y0", "cmp y0,a", ("jcc", "ne", "e2_dn"), f"move {ys(C_RQ)},x0",
          ("label", "e2_dn"), f"move {ys(S_LIN)},a", "sub x0,a", ("jcc", "gt", "e2_dw"),
          "clr a", f"move #>${IDLE:x},b", f"move b,{ys(S_STG)}",
          ("label", "e2_dw"), f"move a,{ys(S_LIN)}", ("jmp", "e2_sh"),
          ("label", "e2_s"),                                                                   # held: the loop's time, then the note
          f"move {ys(C_MODE)},a", f"move #>${M_LOOP:x},y0", "cmp y0,a", ("jcc", "ne", "e2_sg"),
          f"move {ys(S_HC)},a", "tst a", ("jcc", "le", "e2_sg"), "sub #>$1,a", f"move a,{ys(S_HC)}", ("jmp", "e2_sh"),
          ("label", "e2_sg"), f"move {ys(S_GATE)},a", "tst a", ("jcc", "ne", "e2_sh"),
          f"move #>${REL:x},b", f"move b,{ys(S_STG)}", ("jmp", "e2_sh"),
          ("label", "e2_i"), "clr a", f"move a,{ys(S_LIN)}",
          ("label", "e2_sh"), f"move {ys(S_LIN)},x0", "mpy x0,x0,a", f"move {ys(S_LIN)},b", "sub b,a", "move a,x1",
          f"move {ys(C_SLP)},y0", "mac x1,y0,b", f"move b,{ys(S_ENV)}",
          "move b,x0", f"move {ys(S_VEL)},y0", "mpy y0,x0,a", f"move a,{ys(S_VCA)}",
          f"move {ys(S_EC)},b", "sub b,a", "asr #5,a,a", f"move a,{ys(S_ES)}", "rts")
        # ============================================================ ge_slot (r6): a granular slot's envelope (its block, no sound)
        e(("label", "ge_slot"), f"move {ys(C_KEY)},a", f"move #>${KEY:x},x0", "cmp x0,a", ("jcc", "ne", "ge_r"),
          f"move {ys(C_TRK)},a", "tst a", ("jcc", "eq", "ge_r"),
          ("jsr", "s_init"), ("jsr", "s_env2"),
          ("label", "ge_r"), "rts")
    return L


def sl_pieces(L, tab_at, sp=False):
    """(sl) -> {piece: items}: "a" at SL_AT (the jump table, OSC, u_swap, u_inc), "m" at SLM_AT (MW), "u" at SLU_AT (UNI); L = the main's
    labels (s_inc, s_wset) and the other pieces' (osc, u_swap, u_inc)"""
    if sp:
        import sp0 as SP0
        hook = lambda n: [("jsr", SP0.entry(n))]                         # noqa: E731
    else:
        hook = lambda n: []                                              # noqa: E731

    def y(a):
        return f"y:>${a:x}"

    def ys(o):
        return f"y:(r6+${o:x})"
    WT = tab_at["WT"]
    A, M, U = [], [], []
    # ---- the jump table
    A += [("jmp", SLU_AT), ("jmp", SLM_AT)]
    # ---- OSC: the main's passes A-D (the waves through MW)
    A += [("label", "osc"),
          f"move {ys(S_PH1)},a", f"move a,{y(G_P1O)}", f"move {ys(S_INC1)},x0", f"move #>${PB1:x},r1", "nop",
          "do #$20,${oa_e:x}", "add x0,a", "move a1,a", "move a,y:(r1)+", ("label", "oa_e"), f"move a,{ys(S_PH1)}",
          f"move {ys(S_PH2)},a", f"move {ys(S_INC2)},x0", f"move #>${PB2:x},r2", f"move {ys(C_SHP)},b", f"and #>${SHP_SYNC:x},b", "tst b",
          ("jcc", "ne", "ob_s"),
          "do #$20,${ob_e:x}", "add x0,a", "move a1,a", "move a,y:(r2)+", ("label", "ob_e"), ("jmp", "ob_d"),
          ("label", "ob_s"), f"move #>${PB1:x},r1", f"move {y(G_P1O)},y1", "nop",
          "do #$20,${obs_e:x}", "add x0,a", "move a1,a", "move y:(r1)+,b", "cmp y1,b", ("jcc", "ge", "obs_n"), "move #>$800000,a",
          ("label", "obs_n"), "move b,y1", "move a,y:(r2)+", ("label", "obs_e"),
          ("label", "ob_d"), f"move a,{ys(S_PH2)}",
          f"move {ys(S_INC2)},a", f"lua (r6+${S_INC2:x}),r4", ("jsr", L["s_wset"]),
          f"move {ys(C_SHP)},a", "asr #2,a,a", "and #>$3,a", "move a1,a", f"add #>${WT:x},a", "move a1,r3", f"move #>${PB2:x},r1",
          "nop", "move p:(r3),r2", "nop", ("jsr", SLM_AT),
          f"move {ys(S_VEL)},x0", f"move {ys(C_VFM)},y0", "mpy y0,x0,a", f"move {ys(C_FM)},x0", "add x0,a", *hook("sfm"), "move a,y0",
          "clr b", "tst a", ("jcc", "eq", "od_w"),
          f"move #>${PB1:x},r1", f"move #>${PB2:x},r2", "nop",
          "do #$20,${od_e:x}", "move y:(r2)+,x0", "mpy y0,x0,b", "asl b", "move y:(r1),a", "add b,a", "move a1,a", "move a,y:(r1)+",
          ("label", "od_e"), "move #>$4,b",
          ("label", "od_w"), "move b,x1", f"move {ys(S_INC1)},a", f"lua (r6+${S_INC1:x}),r4", ("jsr", L["s_wset"]),
          f"move {ys(C_SHP)},a", "and #>$3,a", "move a1,a", "add x1,a", f"add #>${WT:x},a", "move a1,r3", f"move #>${PB1:x},r1",
          "nop", "move p:(r3),r2", "nop", ("jsr", SLM_AT), "rts"]
    # u_swap: the phases of the copies swapped (S_PH1 <-> S_PH1B, S_PH2 <-> S_PH2B)
    A += [("label", "u_swap")]
    for a_, b_ in ((S_PH1, S_PH1B), (S_PH2, S_PH2B)):
        A += [f"move {ys(a_)},a", f"move {ys(b_)},b", f"move b,{ys(a_)}", f"move a,{ys(b_)}"]
    A += ["rts"]
    # u_inc: a = OSC 1's pitch -> S_INC1, + C_P2 -> S_INC2 (the main's s_inc)
    A += [("label", "u_inc"), f"move a,{y(G_T3)}", f"lua (r6+${S_INC1:x}),r4", ("jsr", L["s_inc"]),
          f"move {y(G_T3)},a", f"move {ys(C_P2)},x0", "add x0,a", f"lua (r6+${S_INC2:x}),r4", ("jsr", L["s_inc"]), "rts"]
    # ---- MW (r1 = the phases, r2 = shape s's wave, r3 = WT + g + s; r5 = the track's parameters): start = 0: the wave as the main's;
    #      else waves i and i + 1 (in the same group g, plain or naive) crossfaded
    M += [("label", "mw"), f"move y:(r5+${P_START:x}),a", "and #>$7f,a", "move a1,a", "tst a", ("jcc", "ne", "mw_m"), "jmp (r2)",
          ("label", "mw_m"), "tfr a,b", "asl a", "add b,a", "move a1,a",
          "move a1,b", "asr #7,b,b", "move b1,b", "and #>$7f,a", "asl #16,a,a", f"move a1,{y(G_MF)}",
          "move r3,a", f"sub #>${WT:x},a", "move a1,x0",
          "move x0,a", "and #>$3,a", "add b,a", "and #>$3,a", "move a1,y1",
          "move x0,b", "and #>$4,b", "move b1,x1",
          "move y1,a", "add x1,a", f"add #>${WT:x},a", "move a1,r3",
          "move y1,a", "add #>$1,a", "and #>$3,a", "add x1,a", f"add #>${WT:x},a", "move a1,r4", "nop",
          "move p:(r3),r2", "move p:(r4),x0", f"move x0,{y(G_RJ)}", f"move r1,{y(G_R1S)}",
          f"move #>${PBX:x},r4", "nop", "do #$20,${mw_c:x}", "move y:(r1)+,a", "move a,y:(r4)+", ("label", "mw_c"),
          f"move {y(G_R1S)},r1", "nop", "jsr (r2)",
          f"move #>${PBX:x},r1", f"move {y(G_RJ)},r2", "nop", "jsr (r2)",
          f"move {y(G_R1S)},r1", f"move #>${PBX:x},r4", f"move {y(G_MF)},y0", "nop",
          "do #$20,${mw_x:x}", "move y:(r1),a", "move y:(r4)+,b", "sub a,b", "move b,x0", "mac x0,y0,a", "move a,y:(r1)+",
          ("label", "mw_x"), "rts"]
    # ---- UNI (r5 = the track's parameters, r6 = the slot; r0 kept): length < 127: both copies -> PB1 / PB2 averaged, a = 1; else a = 0
    if "osc" in L:
        U += [("label", "uni"), f"move y:(r5+${P_LEN:x}),a", "and #>$7f,a", "move a1,b", "move #>$7f,a", "sub b,a", "tst a",
              ("jcc", "eq", "u_0"),
              "asl #7,a,a", f"move a1,{y(G_DT)}", f"move {y(G_T1)},a", f"move a,{y(G_TC)}",
              f"move {y(G_DT)},x0", "add x0,a", ("jsr", L["u_inc"]), ("jsr", L["osc"]),
              f"move #>${PB1:x},r1", f"move #>${PBA1:x},r4", "nop", "do #$40,${u_cp:x}", "move y:(r1)+,a", "move a,y:(r4)+",
              ("label", "u_cp"),
              ("jsr", L["u_swap"]),
              f"move {y(G_TC)},a", f"move {y(G_DT)},x0", "sub x0,a", ("jsr", L["u_inc"]), ("jsr", L["osc"]),
              ("jsr", L["u_swap"]),
              f"move #>${PB1:x},r1", f"move #>${PBA1:x},r4", "nop", "do #$40,${u_av:x}", "move y:(r4)+,a", "move y:(r1),b", "add b,a",
              "asr a", "move a,y:(r1)+", ("label", "u_av"),
              "move #>$1,a", "rts",
              ("label", "u_0"), "clr a", "rts"]
    return dict(a=A, m=M, u=U)


def sl_segs(L, tab_at, sp=False):
    """(sl) -> [(address, words)]: the three pieces"""
    wm, _ = C0.asm_at(sl_pieces(L, tab_at, sp)["m"], SLM_AT)
    assert SLM_AT + len(wm) <= 0x2E00, hex(SLM_AT + len(wm))         # (linein at $2E00)
    wa, la = C0.asm_at(sl_pieces(L, tab_at, sp)["a"], SL_AT)
    assert SL_AT + len(wa) <= 0x3A00, hex(SL_AT + len(wa))            # (gstereo at $3A00)
    wu, _ = C0.asm_at(sl_pieces(dict(L, **la), tab_at, sp)["u"], SLU_AT)
    assert SLU_AT + len(wu) <= C0.LD, hex(SLU_AT + len(wu))           # (the loader at $3FE0)
    return [(SL_AT, wa), (SLM_AT, wm), (SLU_AT, wu)]


def code(entry, env2=False, sp=False, sl=False):
    """-> (the code's words at P:AT, labels, the tables' words at P:TAB, the tables' addresses)"""
    tb = tables()
    names = ("WT", "INCT", "ENVT", "F2", "Q2")
    sizes = dict(WT=8, **{k: len(tb[k]) for k in names[1:]})
    at, tab_at = TAB, {}
    for k in names:
        tab_at[k] = at
        at += sizes[k]
    w, labels = C0.asm_at(items(tab_at, entry, env2, sp, sl), AT)
    assert AT + len(w) <= 0x2600, hex(AT + len(w))                 # (stsplit at $2600)
    tw = [labels[n] for n in ("w_saw", "w_pul", "w_tri", "w_sin", "w_sawn", "w_puln", "w_tri", "w_sin")]
    tw += tb["INCT"] + tb["ENVT"] + tb["F2"] + tb["Q2"]
    assert TAB + len(tw) <= 0x2E00, hex(TAB + len(tw))             # (linein at $2E00)
    return w, labels, tw, tab_at


def segs(entry, env2=False, sp=False, sl=False):
    """for granular0's extra, before gstereo's (GST calls SY, SY goes on to `entry`, the line input's LI); sl: also P:SL_AT"""
    w, labels, tw, tab_at = code(entry, env2, sp, sl)
    return [(AT, w), (TAB, tw)] + (sl_segs(labels, tab_at, sp) if sl else [])


# ================================================================ the model (the tests'): the DSP's arithmetic, bit for bit
def sp_dist_i():
    import sp0
    return sp0.DIST_I


def _sat(acc):
    """an accumulator (an int in units of 2^-47) moved to a register or memory: a1, limited"""
    return max(-(1 << 23), min((1 << 23) - 1, acc >> 24))


def _a1(acc):
    """`move a1,...` / `move a1,a`: a1's 24 bits, no limiting (the wrap)"""
    return s24(acc >> 24)


def _mpy(x, y):
    return 2 * s24(x) * s24(y)


class Model:
    """SY's blocks: ctl[s] = slot s's 16 control words; par[t] = track t's parameter words (6, 9, $B-$D read); msgs = the queue's 16
    pairs (w0, w1), widx = the ARM's write index -> {track: its 32 samples} (y:$FFFFD0 = 0, as in dsptool)"""

    def __init__(self, env2=False, sp=None, sl=False):
        """sp (RH55): a tools/sp0.py Model, the synth's hooks into it; sl (RH58): the start's morph, the length's unison"""
        self.sl = sl
        self.tab = tables()
        self.g = dict(qkey=0, qrd=0)
        self.env2 = env2
        self.sp = sp
        self.ge = [dict() for _ in range(GE_N)]                    # (env2) the granular slots' envelopes
        self.st = [dict(mag=0) for _ in range(NSLOT)]

    def inc(self, P):
        """s_inc: -> (inc, 1 / inc's mantissa, its shift)"""
        P = max(s24(P_MIN), min(P_MAX, P))
        k, f = P >> 16, (P & 0xFFFF) << 7
        i0, i1 = self.tab["INCT"][k - K_LO], self.tab["INCT"][k - K_LO + 1]
        acc = _mpy(_sat((i1 - i0) << 24), f) + (i0 << 24)
        inc, e = _sat(acc), 0
        while (acc >> 24) < 0x400000:
            acc <<= 1
            e += 1
        return inc, (0x200000 << 23) // (acc >> 24), e + 2           # (the DSP's div: checked in tests/emu_rd31.py)

    def queue(self, ctl, msgs, widx):
        g = self.g
        if g["qkey"] != QMAGIC:
            g["qrd"], g["qkey"] = widx & 15, QMAGIC
            return
        blocks = [(ctl[s], self.st[s]) for s in range(NSLOT)]
        if self.env2:
            blocks += [(self.gctl[k], self.ge[k]) for k in range(GE_N)]
        while g["qrd"] != widx & 15:
            w0, w1 = msgs[g["qrd"]]
            g["qrd"] = (g["qrd"] + 1) & 15
            for c, st in blocks:
                if c[C_KEY] != KEY or c[C_TRK] == 0 or (w0 & 7) + 1 != c[C_TRK]:
                    continue
                self.init(st)
                typ = w0 & 0xF00000
                if typ == 0x900000:
                    v = (w0 >> 8) & 0x7F
                    st["vel"] = (v << 16) + (v << 9)
                    st["tgt"] = s24(w1)
                    if st.get("stg") == IDLE or s24(c[C_GLD]) >= ONE:
                        st["pit"] = s24(w1)
                    st["stg"] = ATT
                    if self.env2:
                        st["gate"] = ONE
                elif typ == 0x800000 and self.env2:
                    st["gate"] = 0
                elif typ == 0x800000 and st.get("stg") != IDLE:
                    st["stg"] = REL
            if self.sp is not None:
                self.sp.note(w0)

    @staticmethod
    def init(st):
        if st.get("mag") != MAGIC:
            st.clear()
            st.update(mag=MAGIC, ph1=0, ph2=0, phs=0, nz=1, pit=0, tgt=0, stg=IDLE, env=0, vel=0, ec=0, es=0, t=0xFF,
                      ll=0, lb=0, hl=0, hb=0, fl=0, fh=0, lon=0, hon=0, tfl=0, tfh=0, lin=0, hc=0, gate=0, vca=0,
                      ll2=0, lb2=0, hl2=0, hb2=0, ph1b=0, ph2b=0)

    def block(self, ctl, par, msgs=(), widx=0, gctl=None, gslots=()):
        """(env2) gctl = the granular slots' envelope blocks' control words (64 a block, as the slots'); (sp) gslots: sp0's TICK's"""
        self.gctl = gctl or [[0] * SN for _ in range(GE_N)]
        self.queue(ctl, msgs, widx)
        if self.sp is not None:
            self.sp.tick(gslots)
        out = {}
        for s in range(NSLOT):
            r = self.slot(s, ctl[s], par)
            if r is not None:
                out[r[0]] = r[1]
        if self.env2:
            for k in range(GE_N):
                c, st = self.gctl[k], self.ge[k]
                if c[C_KEY] == KEY and c[C_TRK] != 0:
                    self.init(st)
                    self.env2_step(st, c)
        return out

    def env2_step(self, st, c):
        """(env2) s_env2: the envelope by the play mode, its shape, the VCA's target and step"""
        stg, lin, mode = st["stg"], st["lin"], s24(c[C_MODE])
        if stg == ATT:
            a = lin + s24(c[C_ATK])
            if a >= ONE:
                lin = ONE
                if mode == 0:
                    stg = DEC
                else:
                    st["hc"], stg = s24(c[C_HOLD]), SUS
            else:
                lin = a
                if mode == M_GATED and st["gate"] == 0:
                    stg = REL
        elif stg == SUS:
            if mode == M_LOOP and st["hc"] > 0:
                st["hc"] -= 1
            elif st["gate"] == 0:
                stg = REL
        elif stg == IDLE:
            lin = 0
        else:
            d = s24(c[C_RQ]) if stg == REL and mode == M_LOOP else s24(c[C_DEC])
            a = lin - d
            if a > 0:
                lin = a
            else:
                lin, stg = 0, IDLE
        st["lin"], st["stg"] = lin, stg
        x1 = _sat(_mpy(lin, lin) - (lin << 24))
        b = (lin << 24) + _mpy(x1, c[C_SLP])
        st["env"] = _sat(b)
        a = _mpy(st["env"], st["vel"])
        st["vca"] = _sat(a)
        st["es"] = _sat((a - (st["ec"] << 24)) >> 5)

    def slot(self, s, c, par):
        st = self.st[s]
        if c[C_KEY] != KEY or c[C_TRK] == 0:
            return None
        self.init(st)
        t = (c[C_TRK] - 1) & 7
        if st["t"] != t:
            st.update(t=t, ll=0, lb=0, hl=0, hb=0, lon=0, hon=0)
        p = par[t]
        st["pit"] = _sat(_mpy(c[C_GLD], _sat((st["tgt"] - st["pit"]) << 24)) + (st["pit"] << 24))
        knob = s24((_mpy(((p[P_PITCH] & 0x7F) - 64), KNOB_PU) >> 1) & 0xFFFFFF)
        acc1 = (st["pit"] + knob + s24(c[C_OCT])) << 24
        sp = self.sp if self.sp is not None and self.sp.on(t) else None
        if sp is not None:                                     # (sp) SPIT: + the pitch envelope / LFO, kept for the follow
            acc1 += sp.S(t)["pm"] << 24
            sp.S(t)["pit"] = _sat(acc1)
        inc1, rm1, re1 = self.inc(acc1 >> 24)
        inc2, rm2, re2 = self.inc(_sat(acc1) + s24(c[C_P2]))
        incs = inc1 >> 1
        self.env(st, c, p)
        if st["stg"] == IDLE and st["ec"] == 0:
            return t, [0] * 32
        morph = (p[P_START] & 0x7F) if self.sl else 0
        det = (0x7F - (p[P_LEN] & 0x7F)) if self.sl else 0

        def osc(i1, i2, k1, k2):
            """passes A-D on the phases st[k1] / st[k2] with these increments -> (OSC 1's, OSC 2's samples)"""
            (inc1, rm1, re1), (inc2, rm2, re2) = i1, i2
            pb1, ph, p1o = [], st[k1], st[k1]
            for _ in range(32):
                ph = s24(ph + inc1)
                pb1.append(ph)
            st[k1] = ph
            pb2, ph, prev = [], st[k2], p1o
            for i in range(32):
                ph = s24(ph + inc2)
                if c[C_SHP] & SHP_SYNC:
                    if pb1[i] < prev:
                        ph = -(1 << 23)
                    prev = pb1[i]
                pb2.append(ph)
            st[k2] = ph
            k = s24(c[C_K])
            o2 = self.wave_m((c[C_SHP] >> 2) & 3, pb2, inc2, rm2, re2, k, False, morph)
            afm = _mpy(st["vel"], c[C_VFM]) + (s24(c[C_FM]) << 24)
            if sp is not None:                                 # (sp) SFM: + the scan LFO
                afm += sp.S(t)["so"] << 24
            fm, naive = _sat(afm), afm != 0
            if naive:
                pb1 = [_a1((pb1[i] << 24) + (_mpy(fm, o2[i]) << 1)) for i in range(32)]
            return self.wave_m(c[C_SHP] & 3, pb1, inc1, rm1, re1, k, naive, morph), o2
        if det == 0:
            o1, o2 = osc((inc1, rm1, re1), (inc2, rm2, re2), "ph1", "ph2")
        else:                                                  # (sl) unison: + and - (127 - length) << 7, averaged
            ctr, dt = _sat(acc1), det << 7
            a1_, a2_ = osc(self.inc(ctr + dt), self.inc(ctr + dt + s24(c[C_P2])), "ph1", "ph2")
            b1_, b2_ = osc(self.inc(ctr - dt), self.inc(ctr - dt + s24(c[C_P2])), "ph1b", "ph2b")
            o1 = [_sat(((x << 24) + (y << 24)) >> 1) for x, y in zip(a1_, b1_)]
            o2 = [_sat(((x << 24) + (y << 24)) >> 1) for x, y in zip(a2_, b2_)]
        gs, gn = s24(c[C_GS]), s24(c[C_GN])
        if gs + gn != 0:
            gsn, ps, nz, pb3 = _sat(-(gs << 24)), st["phs"], st["nz"], []
            for i in range(32):
                ps = s24(ps + incs)
                sub = gs if ps >= 0 else gsn
                nz = _a1((s24((_mpy(nz, LCG_A) >> 1) & 0xFFFFFF) << 24) + (LCG_C << 24))
                pb3.append(_sat(_mpy(nz, gn) + (sub << 24)))
            st["phs"], st["nz"] = ps, nz
            buf = [_sat(_mpy(c[C_G1], o1[i]) + _mpy(o2[i], c[C_G2]) + (pb3[i] << 24)) for i in range(32)]
        else:
            buf = [_sat(_mpy(c[C_G1], o1[i]) + _mpy(o2[i], c[C_G2])) for i in range(32)]
        if sp is not None:                                     # (sp) SDS: the stock's distortion knob
            sp.dset(t, p[sp_dist_i()])
            buf = sp.drun(t, buf)
        ec, es = st["ec"] << 24, s24(st["es"])
        for i in range(32):
            ec += es << 24
            buf[i] = _sat(_mpy(_sat(ec), buf[i]))
        st["ec"] = _sat(ec)
        return t, self.filt(st, c, p, buf, sp, t)

    def wave_m(self, shape, ph, inc, rm, re, k, naive, morph):
        """(sl) MW: start 0 = the wave; else waves i = (shape + 3 start >> 7) & 3 and i + 1 crossfaded by (3 start & 127) / 128"""
        if morph == 0:
            return self.wave(shape, ph, inc, rm, re, k, naive)
        q = 3 * morph
        i = (shape + (q >> 7)) & 3
        f = (q & 0x7F) << 16
        wi = self.wave(i, ph, inc, rm, re, k, naive)
        wj = self.wave((i + 1) & 3, ph, inc, rm, re, k, naive)
        return [_sat((a << 24) + _mpy(_sat((b << 24) - (a << 24)), f)) for a, b in zip(wi, wj)]

    def wave(self, shape, ph, inc, rm, re, k, naive):
        THL, THH = s24(inc - ONE), s24(ONE - inc)

        def blep(p):                                   # the accumulator
            if p < THL:
                y = _sat(_mpy(THL - p, rm) << re)
                return (p << 24) + _mpy(y, y)
            if p > THH:
                y = _sat(_mpy(p - THH, rm) << re)
                return (p << 24) - _mpy(y, y)
            return p << 24
        out = []
        for p in ph:
            if shape == SAW:
                out.append(p if naive else _sat(blep(p)))
            elif shape == PULSE:
                q = s24(p + k)
                if naive:
                    out.append(_sat(((p << 24) - (q << 24)) >> 1))
                else:
                    out.append(_sat(((_sat(blep(p)) << 24) - blep(q)) >> 1))
            elif shape == TRI:
                out.append(_sat(((-abs(p) << 24) + (0x400000 << 24)) << 1))
            else:
                x0 = _sat((-abs(p) << 24) + (ONE << 24))
                af = _mpy(p, x0) << 2
                g = _sat(_mpy(frac(0.225), _sat(abs(af))) + (frac(0.775) << 24))
                out.append(_sat(_mpy(g, _sat(af))))
        return out

    def env(self, st, c, p):
        if self.env2:
            self.env2_step(st, c)
            return
        n = p[P_ENV] & 0x7F
        x0 = self.tab["ENVT"][n]
        if st["stg"] == ATT:
            a = ONE << 24 if n <= 64 else (st["env"] << 24) + (s24(x0) << 24)
            if a >= ONE << 24:
                a, st["stg"] = ONE << 24, DEC
        elif st["stg"] == DEC and n >= 64:
            a = st["env"] << 24
        elif st["stg"] in (DEC, REL):
            a = _mpy(st["env"], x0 if st["stg"] == DEC else c[C_REL])
            if a < FLOOR << 24:
                a, st["stg"] = 0, IDLE
        else:
            a = 0
        st["env"] = _sat(a)
        st["es"] = _sat((_mpy(st["env"], st["vel"]) - (st["ec"] << 24)) >> 5)

    def filt(self, st, c, p, buf, sp=None, t=0):
        idx = (p[LP_I] & 0x7F) + s24(_mpy(c[C_EF], st["env"]) >> 40)
        if sp is not None:                                     # (sp) SLP: the follow, the comb
            idx = sp.lpidx(t, idx)
        idx = max(0, idx)
        F2, Q2 = self.tab["F2"], self.tab["Q2"]
        if idx >= 127:
            st["lon"] = 0
        else:
            st["tfl"] = F2[idx]
            if not st["lon"]:
                st.update(fl=F2[idx], ll=0, lb=0)
            st["lon"] = 1
        hi = p[HP_I] & 0x7F
        if sp is not None:
            hi = sp.hpidx(t, hi)
        if hi == 0:
            st["hon"] = 0
        else:
            st["tfh"] = F2[hi]
            if not st["hon"]:
                st.update(fh=F2[hi], hl=0, hb=0)
            st["hon"] = 1
        for fn, tf in (("fl", "tfl"), ("fh", "tfh")):
            st[fn] = _sat((((s24(st[tf]) << 24) - (s24(st[fn]) << 24)) >> 3) + (s24(st[fn]) << 24))
        q = Q2[p[RES_I] & 0x7F]
        out = self._pass(st, q, buf, "")
        if sp is not None:                                     # (sp) S24: 24 dB = again on the second states; else those at zero
            from sp0 import C_KT
            if sp.ctl[t][C_KT] != 1:
                st.update(ll2=0, lb2=0, hl2=0, hb2=0)
            else:
                if not st["lon"]:
                    st.update(ll2=0, lb2=0)
                if not st["hon"]:
                    st.update(hl2=0, hb2=0)
                out = self._pass(st, q, out, "2")
        return out

    def _pass(self, st, q, buf, k):
        if not (st["lon"] or st["hon"]):
            return buf
        out = []
        for x1 in buf:
            if st["lon"]:
                st["ll" + k], st["lb" + k], _ = self._svf(st["ll" + k], st["lb" + k], st["fl"], q, x1)
                x1 = st["ll" + k]
            if st["hon"]:
                st["hl" + k], st["hb" + k], x1 = self._svf(st["hl" + k], st["hb" + k], st["fh"], q, x1)
            out.append(x1)
        return out

    @staticmethod
    def _svf(L, B, f, q, x1):
        y1 = B
        for _ in range(2):
            y1 = B
            a = (L << 24) + _mpy(f, y1)
            L = _sat(a)
            b = (x1 << 24) - a - 2 * _mpy(y1, q)
            a = y1 << 24
            y1 = _sat(b)
            B = _sat(a + _mpy(f, y1))
        return L, B, y1
