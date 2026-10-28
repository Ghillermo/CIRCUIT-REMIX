"""The Tracks' granular engine on the Circuit Rhythm's DSP core 0 (MIT; RD21, docs/PRUEBA_RD21.md): one track, mono, 16 grains.

The engine is ours from CIRCUIT-HACKS (tools/granular_dsp.py: the voice, its zone and playhead, the spawn of grains with their pitch,
position spray, reverse chance and window, the grain loop with linear interpolation, its tables), rewritten for the Rhythm's core 0:
  * where: core 0 mixes the eight tracks at P:$367 (`jsr $367` at P:$224 in its block): track t's 32 mono samples arrive from core 1 in
    shared Y:$304F0 + 64 t + 32 (y:$FFFFD0 & 1) (double-buffered), and get their level, pan, sends and sidechain there.  Ours: P:$224 ->
    `jsr GR` (a segment sent by core0.py's loader), GR writes the granular into the chosen track's 32 samples, then `jmp $367`: the stock
    voice's own samples are replaced, the mixer, FX and sidechain apply as to any track;
  * the sample: the track's (its parameter block Y:$307C8 + $20 t, word 0 = the sample n; its entry X:$30000 + 4 n = start, length;
    its pages Y:$308C8 + n $BC, two 12-bit page numbers a word, the high half for an even page: tools/stretch.py); each grain copies the
    words it reads in a block (a page boundary taken care of) into X:LB, the grain loop reads them there;
  * the gate (GATE = 1): the stock voice's own samples (before they are replaced) open it: the grains sound while the track's voice sounds
    (its steps, its envelope), ramping up in 4 blocks and down in 64; when it opens, the playhead goes back to the zone's start and a grain
    starts at once.  GATE = 0: always on (a drone).
  * the output: the sum of the grains x the gate (ramped through the block) x 1/2 (the stock voice's own level: core 1's resampler gives
    half the sample).
Controls (X:GB + k, written by tools/rhgran.py, which also writes KEY in X:GB + 15: without it GR does nothing, so power-up garbage in
those words cannot switch it on; the Tracks' knob codes in brackets):
  +0 TRK 1..8 (0 = off)   +1 GATE 0 / 1   +2 PITCH -24..24 semitones (P17)   +3 SIZE 0..127 = 5 .. 500 ms (P18)   +4 POS 0..127 (P19)
  +5 DENS 0..100 = 1 .. 16 grains (P20)   +6 SCAN -64..63 (P21: v |v| / 64 samples a block, 0 = still)   +7 ZONE 0..127 (P23: the zone =
  the sample x (ZONE + 1) / 128)   +8 FINE -64..63 (1/64 semitone, P28)   +9 PSPR 0..127 (pitch spray, +-12 semitones, P29)
  +10 WIN 0..100 (rectangle -> triangle -> percussive, P30)   +11 SPR 0..127 (position spray, P33)   +12 REV 0..127 (reverse chance, P34)
Memory (core 0; X / Y:$1400.. are zero in every dump, with no absolute operand in the stock: docs/RECURSOS.md): X:$1400-$14FF controls,
state and grains, X:$1500-$15FF the copies, Y:$1410-$142F the sum, Y:$1440-$1457 the registers of the stock (all r / n / m, saved and
restored around ours: m set linear inside).  Y:$1400-$1403 are RD20's counters.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core0 as C0  # noqa: E402

GB = 0x1400
(P_TRK, P_GATE, P_PITCH, P_SIZE, P_POS, P_DENS, P_SCAN, P_ZONE, P_FINE, P_PSPR, P_WIN, P_SPR, P_REV) = range(13)
P_NOTE = 13                                            # (RH40, note) the played note - 60 in semitones (the ARM writes it at each note-on)
P_SPRD = 14                                            # (RH47, stereo) the stereo spread 0..127: each grain's pan = rnd x SPRD / 128
PANOFF = 0x1C0                                         # (stereo) a grain's pan at Y:(its slot + PANOFF) = Y:$1600 + 12 k (to $16B4)
OUTS, SB = 0x14C0, 0x14E0                              # (stereo) Y: the grains' side sum, the side out (x the gate, like the track's)
P_KEY, KEY = 15, 0x6A7A4B                            # GR runs only with this word in X:GB + 15 (power-up garbage in TRK must not)
NAMES = ("trk", "gate", "pitch", "size", "pos", "dens", "scan", "zone", "fine", "pspr", "win", "spr", "rev")
DEFAULTS = dict(gate=1, pitch=0, size=64, pos=0, dens=40, scan=8, zone=127, fine=0, pspr=0, win=50, spr=0, rev=0)
RNG = GB + 0x10
VS = GB + 0x20
(V_ON, V_PH, V_PL, V_CD, V_Z, V_ZS, V_LGB, V_D, V_I, V_GAIN, V_NL, V_L, V_S, V_SPN, V_Q, V_LGG, V_SPAN, V_SPR, V_REV, V_TAB,
 V_GLV, V_GLO, V_BUF, V_LO0, V_LO, V_CNT, V_T, V_MAG, V_R) = range(29)   # (V_R: RH40, the note's ratio, Q19)
GR0, GW, MAXG = GB + 0x40, 12, 16
(G_TOT, G_SEG, G_SID, G_E, G_DE, G_PH, G_PL, G_IH, G_IL, G_LH, G_LR, G_DR) = range(12)
LB, LB_N = 0x1500, 0x100                               # X: a grain's words for one block
OUTB, SAVE = 0x1410, 0x1440                            # Y
TRK_BUF, PAR0, SMP, PAGES, PSTRIDE = 0x304F0, 0x307C8, 0x30000, 0x308C8, 0xBC
HOOK, OLD_HOOK, MIX = 0x224, (0x0BF080, 0x000367), 0x367
CODE = C0.SEG + 8                                      # after RD20's test segment (P:$2000 MAGIC, $2001 its counter)
MAGIC = 0x6A7A21
ONE = 0x7FFFFF
TH, ATT, REL = 0x2000, 0x200000, 0x20000              # the gate: a voice peak above 2^-10 opens it; +1/4 a block up, -1/64 down
PT_LO, PT_HI = -48, 25                                 # the pitch table's semitones (the copy buffer holds 32 x 5 + 2 words: up to +24)
PITCH_MAX = 24 * 64 + 63
# ---- (RH50, multi) several granular tracks (the user, 2026-10-27: «activar un granular desactiva el anterior¿? corregir"): NSLOT slots,
# each its controls (16 words, as X:GB's) and its voice state (32 words) in core 0's Y from SLOTY + $40 s (r6 / r7 point there, Y in place
# of X); the 16 grains shared, a slot taking at most CAP_T[running slots - 1] of them; a grain's slot (its r6) at Y:(grain + PANOFF + 1);
# each slot's sums at OUTY + $40 s (OUTB, then OUTS + $20), its side out at SBY + $20 s.  A slot runs while its KEY and its TRK say so.
NSLOT, SLOTY, SLOT_N = 4, 0x1700, 0x40
OUTY, SBY = 0x1800, 0x1900
V_NG, V_ACT = 29, 30                                   # (multi) the slot's live grains, active this block
GMAG, NACT, CAPW = 0x16F0, 0x16F1, 0x16F2              # (multi) Y: the pool's magic, the active slots, the cap
CAP_T = (16, 7, 4, 2)                                  # (multi) a slot's grains with 1..4 slots running: each running slot adds its chain,
                                                       #   so fewer grains in all (16 / 14 / 12 / 8): the worst case (+24, filters on, a
                                                       #   spread) stays near one track's on the device (tests/emu_rh50.py)
MCODE = 0x3000                                         # (multi) the engine's P (granular0's single place stays for later)


def slot_y(s):
    return SLOTY + SLOT_N * s


def Ym(r, off):
    return f"y:({r})" if off == 0 else f"y:({r}+${off:x})"


def tables():
    t = {}
    t["SIZE_T"] = [int(round(240 * 100 ** (v / 127))) for v in range(128)]                        # 5 .. 500 ms (the Tracks')
    t["PT"] = [int(round(2 ** (k / 12) * (1 << 19))) & 0xFFFFFF for k in range(PT_LO, PT_HI + 1)]  # Q19
    t["GAIN_T"] = [int(round(0.6 / math.sqrt(d) * (1 << 23))) for d in range(1, 17)]
    return t


def X(r, off):
    return f"x:({r})" if off == 0 else f"x:({r}+${off:x})"


def items(tab_at, note=False, post=None, stereo=False, multi=False, sp=False, mix=MIX):
    """the engine at P:CODE; tab_at = {table: P address}; note (RH40): the played note pitches the whole granular, as a sampler: r =
    2^((note - 60) / 12), each grain's increment x r, its length / r (the same source span, sooner), the spawn interval / r; multi (RH50):
    NSLOT slots, the controls and the voice state in Y"""
    V = Ym if multi else X
    L = []
    E = L.extend

    def e(*s):
        L.extend(s)

    # ================================================================ GR: from P:$224 (in place of `jsr $367`), then the stock's mix
    if multi:
        e(*gr_multi(tab_at, post, mix))
    else:
        e(("label", "gr"), f"move x:>${GB + P_KEY:x},a", f"move #>${KEY:x},x0", "cmp x0,a", ("jcc", "ne", MIX),
          f"move x:>${GB + P_TRK:x},a", "tst a", ("jcc", "eq", MIX), ("jsr", "g_save"), ("jsr", "g_block"), ("jsr", "g_rest"),
          ("jmp", post or MIX))                                 # (RD30, post) tools/granchain.py's chain before the mix
    # ---- the stock's registers: r / n / m to Y:SAVE (m: the raw MOVEC words), then m linear
    e(("label", "g_save"))
    for k in range(8):
        e(f"move r{k},y:>${SAVE + k:x}", f"move n{k},y:>${SAVE + 8 + k:x}", ("words", [0x057060 | k, SAVE + 16 + k]),
          ("words", [0x05F420 | k, 0xFFFFFF]))
    e("rts", ("label", "g_rest"))
    for k in range(8):
        e(f"move y:>${SAVE + k:x},r{k}", f"move y:>${SAVE + 8 + k:x},n{k}", ("words", [0x05F060 | k, SAVE + 16 + k]))
    e("rts")

    # ================================================================ g_block: one block of the track
    if multi:                                                           # (multi) g_pre: r6 / r7 = the slot's (GR), r3 = the pool
        e(("label", "g_pre"))
    else:
        e(("label", "g_block"), f"move #>${GB:x},r6", f"move #>${VS:x},r7", f"move #>${GR0:x},r3", "nop")
    # ---- the state, once (power-up garbage): cleared, MAGIC
    if multi:                                                           # (multi) the slot's own (the pool has its own magic, GR)
        e(f"move {V('r7', V_MAG)},a", f"move #>${MAGIC:x},x0", "cmp x0,a", ("jcc", "eq", "g_mok"),
          "clr a", "move r7,r0", "nop", "do #$20,${g_clr:x}", "move a,y:(r0)+", ("label", "g_clr"),
          f"move x0,{V('r7', V_MAG)}", "move #>$ffffff,x0", f"move x0,{V('r7', V_T)}", "move #>$1,x0", f"move x0,{V('r7', V_ACT)}",
          ("label", "g_mok"))
    else:
        e(f"move {V('r7', V_MAG)},a", f"move #>${MAGIC:x},x0", "cmp x0,a", ("jcc", "eq", "g_mok"),
          "clr a", f"move #>${VS:x},r0", "nop", f"do #${0x20 + MAXG * GW:x},${{g_clr:x}}", "move a,x:(r0)+", ("label", "g_clr"),
          f"move x0,{V('r7', V_MAG)}", "move #>$ffffff,x0", f"move x0,{V('r7', V_T)}", "move #>$1234,x0", f"move x0,x:>${RNG:x}",
          ("label", "g_mok"))
    # ---- the track T, a new one = the voice from scratch
    e(f"move {V('r6', P_TRK)},a", "sub #>$1,a", "and #>$7,a", "move a1,x0", f"move {V('r7', V_T)},b", "cmp x0,b", ("jcc", "eq", "g_same"),
      f"move x0,{V('r7', V_T)}", "clr b", f"move b,{V('r7', V_ON)}", f"move b,{V('r7', V_GLV)}", f"move b,{V('r7', V_GLO)}",
      ("label", "g_same"))
    # ---- its buffer: Y:$304F0 + 64 T + 32 x (y:$FFFFD0), as the stock's mix (P:$367)
    e("movep y:<<$ffffd0,b", "asl #5,b,b", "move a1,x0", "clr a", "move x0,a1", "asl #6,a,a", f"add #>${TRK_BUF:x},a", "move b1,x1",
      "add x1,a", f"move a1,{V('r7', V_BUF)}")
    # ---- its sample: n = Y:(PAR0 + $20 T) & $7F; start / length = X:$30000 + 4 n, + 1; the pages Y:$308C8 + n $BC
    e("clr a", "move x0,a1", "asl #5,a,a", f"add #>${PAR0:x},a", "move a1,r0", "nop", "move y:(r0),a", "and #>$7f,a",
      "move a1,x0", f"move #>${PSTRIDE:x},x1", "mpy x1,x0,b", "asr b", "move b0,b", f"add #>${PAGES:x},b", f"move b1,{V('r7', V_TAB)}",
      "asl #2,a,a", f"add #>${SMP:x},a", "move a1,r0", "nop", "move x:(r0)+,x0", f"move x0,{V('r7', V_S)}", "move x:(r0),a",
      f"move a1,{V('r7', V_L)}", "move #>$100,x0", "cmp x0,a", ("jcc", "ge", "g_smp"),
      "clr a", f"move a,{V('r7', V_ON)}", "rts",                         # no sample (or too short): the stock voice as it is
      ("label", "g_smp"))
    # ---- the gate
    e(f"move {V('r6', P_GATE)},a", "tst a", ("jcc", "ne", "g_fol"), f"move #>${ONE:x},x0", f"move x0,{V('r7', V_GLV)}", ("jmp", "g_gd"),
      ("label", "g_fol"), f"move {V('r7', V_BUF)},r0", "clr b", "nop",
      "do #$20,${g_pk:x}", "move y:(r0)+,a", "abs a", "cmp a,b", "tlt a,b", ("label", "g_pk"),
      f"move #>${TH:x},x0", "cmp x0,b", ("jcc", "lt", "g_gfall"),
      f"move {V('r7', V_GLV)},a", "tst a", ("jcc", "ne", "g_gup"),
      "clr a", f"move a,{V('r7', V_PH)}", f"move a,{V('r7', V_PL)}", f"move a,{V('r7', V_CD)}",        # it opens: the zone's start, a grain now
      ("label", "g_gup"), f"move {V('r7', V_GLV)},a", f"move #>${ATT:x},x0", "add x0,a", f"move #>${ONE:x},x0", "cmp x0,a", "tgt x0,a",
      f"move a1,{V('r7', V_GLV)}", ("jmp", "g_gd"),
      ("label", "g_gfall"), f"move {V('r7', V_GLV)},a", f"move #>${REL:x},x0", "sub x0,a", ("jcc", "ge", "g_gst"), "clr a",
      ("label", "g_gst"), f"move a1,{V('r7', V_GLV)}",
      ("label", "g_gd"))
    # ---- the voice, its grains into Y:OUTB
    if multi:                                                           # (multi) the pool and the out run from GR
        e(("jsr", "g_voice"), "rts")
        e(("label", "g_post"), "move r6,a", f"add #>${OUTY - SLOTY:x},a", "move a1,r1")
    else:
        e(("jsr", "g_voice"), "clr a", f"move #>${OUTB:x},r0", "nop", "do #$20,${g_oc:x}", "move a,y:(r0)+", ("label", "g_oc"))
        if stereo:                                                      # (stereo) the side sum too
            e(f"move #>${OUTS:x},r0", "nop", "do #$20,${g_os:x}", "move a,y:(r0)+", ("label", "g_os"))
        e(
          f"move #>${OUTB:x},r1", "move r3,r2", f"move #>${GW:x},n2", "nop", f"do #${MAXG:x},${{g_gl:x}}", ("jsr", "g_grain1"),
          "move (r2)+n2", ("label", "g_gl"))
    # ---- out: Y:BUF[i] = OUTB[i] x g x 1/2, g from the last block's gate to this one's
    e(f"move {V('r7', V_BUF)},r0", *([] if multi else [f"move #>${OUTB:x},r1"]), f"move {V('r7', V_GLV)},a", f"move {V('r7', V_GLO)},x0", "sub x0,a",
      "asr #5,a,a", "move a,x1", "clr b", "move x0,b1", "nop",
      "do #$20,${g_out:x}", "add x1,b", "move b,y0", "move y:(r1)+,x0", "mpy y0,x0,a", "asr a", "move a,y:(r0)+", ("label", "g_out"))
    if stereo:                                                          # (stereo) SB[i] = OUTS[i] x the same gate ramp x 1/2
        if multi:                                                       # (multi) the slot's: SBY + (r6 - SLOTY) / 2, OUTS = its OUTB + $20
            e("move r6,a", f"sub #>${SLOTY:x},a", "asr a", f"add #>${SBY:x},a", "move a1,r0",
              "move r6,a", f"add #>${OUTY - SLOTY + 0x20:x},a", "move a1,r1", f"move {V('r7', V_GLO)},x0", "clr b", "move x0,b1", "nop")
        else:
            e(f"move #>${SB:x},r0", f"move #>${OUTS:x},r1", f"move {V('r7', V_GLO)},x0", "clr b", "move x0,b1", "nop")
        e("do #$20,${g_ou2:x}", "add x1,b", "move b,y0", "move y:(r1)+,x0", "mpy y0,x0,a", "asr a", "move a,y:(r0)+", ("label", "g_ou2"))
    e(f"move {V('r7', V_GLV)},x0", f"move x0,{V('r7', V_GLO)}", "rts")

    # ================================================================ g_voice (the Tracks' voice): the zone, the playhead, the size, the density, the spawns
    if multi:                                                           # (multi) a new voice: its own grains gone, its count 0
        e(("label", "g_voice"), f"move {V('r7', V_ON)},a", "tst a", ("jcc", "ne", "g_von"),
          "move r3,r0", f"move #>${GW:x},n0", "move r6,x1", "move #>$0,x0", "nop",
          f"do #${MAXG:x},${{g_vc:x}}", f"move y:(r0+${PANOFF + 1:x}),b", "move x:(r0),a", "cmp x1,b", "teq x0,a", "move a,x:(r0)+n0",
          ("label", "g_vc"), "clr a", f"move a,{V('r7', V_NG)}")
    else:
        e(("label", "g_voice"), f"move {V('r7', V_ON)},a", "tst a", ("jcc", "ne", "g_von"),
          "clr a", "move r3,r0", f"move #>${GW:x},n0", "nop", f"do #${MAXG:x},${{g_vc:x}}", "move a,x:(r0)+n0", ("label", "g_vc"))
    e(
      f"move a,{V('r7', V_PH)}", f"move a,{V('r7', V_PL)}", f"move a,{V('r7', V_CD)}", "move #>$1,x0", f"move x0,{V('r7', V_ON)}",
      ("label", "g_von"))
    # ---- the zone Z = L (ZONE + 1) / 128 (>= 64), its start ZS = (L - Z) POS / 128
    e(f"move {V('r6', P_ZONE)},a", "and #>$7f,a", "add #>$1,a", "move a1,x0", f"move {V('r7', V_L)},x1", "mpy x1,x0,a", "asr a",
      "asr #7,a,a", "move a0,b", "move #>$40,x0", "cmp x0,b", "tlt x0,b", f"move b1,{V('r7', V_Z)}",
      f"move {V('r7', V_L)},a", "sub b,a", "move a1,x1", f"move {V('r6', P_POS)},a", "and #>$7f,a", *_hook(sp, "gpos"), "move a1,x0",
      "mpy x1,x0,a", "asr a",
      "asr #7,a,a", f"move a0,{V('r7', V_ZS)}")
    # ---- the playhead: += SCAN |SCAN| / 64 samples a block, inside [0, Z) (v |v| is in a0 after the asr: << 18 = / 64 in a1, the rest
    #      the fraction; the Tracks' line had `move a0,a` before the shift, which puts it in a1 and shifts it out: its scan never moved)
    e(f"move {V('r6', P_SCAN)},x0", "move x0,a", "abs a", "move a1,x1", "mpy x1,x0,a", "asr a", "asl #18,a,a",
      f"move {V('r7', V_PH)},b", f"move {V('r7', V_PL)},b0", "add a,b", f"move {V('r7', V_Z)},x0", "cmp x0,b", ("jcc", "lt", "g_w1"),
      "sub x0,b", "cmp x0,b", ("jcc", "lt", "g_w2"), "clr b", ("jmp", "g_w2"),
      ("label", "g_w1"), "tst b", ("jcc", "ge", "g_w2"), "add x0,b", "tst b", ("jcc", "ge", "g_w2"), "clr b",
      ("label", "g_w2"), f"move b1,{V('r7', V_PH)}", f"move b0,{V('r7', V_PL)}")
    # ---- the grain's length SIZE_T[SIZE]; the density D = 1 + DENS x 154 / 1024 (1..16), the spawn interval LGB / D, the gain GAIN_T[D - 1]
    e(f"move {V('r6', P_SIZE)},a", "and #>$7f,a", f"add #>${tab_at['SIZE_T']:x},a", "move a1,r0", "nop", "move p:(r0),x0",
      f"move x0,{V('r7', V_LGB)}", *(note_lgb(tab_at, V) if note else ()),
      f"move {V('r6', P_DENS)},x0", "move #>$9a,x1", "mpy x1,x0,a", "asr a", "asr #10,a,a", "move a0,a", "add #>$1,a",
      "move #>$1,x0", "cmp x0,a", "tlt x0,a", "move #>$10,x0", "cmp x0,a", "tgt x0,a", f"move a1,{V('r7', V_D)}",
      "move a1,x0", "clr a", f"move {V('r7', V_LGB)},a0", ("jsr", "g_udiv"), f"move a0,{V('r7', V_I)}",
      f"move {V('r7', V_D)},a", "sub #>$1,a", f"add #>${tab_at['GAIN_T']:x},a", "move a1,r0", "nop", "move p:(r0),x0",
      f"move x0,{V('r7', V_GAIN)}")
    # ---- the spawns: the countdown -= 32; while <= 0 (at most 4): a grain, += the interval; a debt is forgotten
    e(f"move {V('r7', V_CD)},a", "sub #>$20,a", f"move a1,{V('r7', V_CD)}", "move #>$4,x0", f"move x0,{V('r7', V_SPN)}",
      ("label", "g_sp"), f"move {V('r7', V_CD)},a", "tst a", ("jcc", "gt", "g_spd"), ("jsr", "g_spawn"),
      f"move {V('r7', V_CD)},a", f"move {V('r7', V_I)},x0", "add x0,a", f"move a1,{V('r7', V_CD)}",
      f"move {V('r7', V_SPN)},a", "sub #>$1,a", f"move a1,{V('r7', V_SPN)}", ("jcc", "ne", "g_sp"),
      f"move {V('r7', V_CD)},a", "tst a", ("jcc", "ge", "g_spd"), "clr a", f"move a,{V('r7', V_CD)}",
      ("label", "g_spd"), "rts")

    # ================================================================ g_spawn (the Tracks'): one grain into a free slot; r2 = the slot
    e(("label", "g_spawn"))
    if multi:                                                           # (multi) the slot at its cap: no grain
        e(f"move {V('r7', V_NG)},a", f"move y:>${CAPW:x},x0", "cmp x0,a", ("jcc", "lt", "g_scp"), "rts", ("label", "g_scp"))
    e("move r3,r2", f"move #>${MAXG:x},b", f"move #>${GW:x},n2", "nop",
      ("label", "g_sf"), "move x:(r2),a", "tst a", ("jcc", "eq", "g_sok"), "move (r2)+n2", "sub #>$1,b", ("jcc", "ne", "g_sf"), "rts",
      ("label", "g_sok"))
    if multi:                                                           # (multi) the grain's slot, the slot's count
        e(f"move r6,y:(r2+${PANOFF + 1:x})", f"move {V('r7', V_NG)},a", "add #>$1,a", f"move a1,{V('r7', V_NG)}")
    e(f"move {V('r7', V_LGB)},x0", f"move x0,{V('r7', V_LGG)}")
    # ---- the pitch in 1/64 semitone: PITCH (+-24) x 64 + FINE + the spray (rnd x PSPR / 128 x 12 semitones)
    e(f"move {V('r6', P_PITCH)},a", "move #>$18,x1", "cmp x1,a", "tgt x1,a", "move #>$ffffe8,x1", "cmp x1,a", "tlt x1,a", "asl #6,a,a",
      f"move {V('r6', P_FINE)},x0", "add x0,a", *_hook(sp, "gpm"), f"move a1,{V('r7', V_Q)}", ("jsr", "g_rnd"),
      f"move {V('r6', P_PSPR)},b", "and #>$7f,b", "asl #16,b,b", "move b,y0", "mpy y0,x0,b", "move b,x1", "move #>$300,x0", "mpy x1,x0,b",
      f"move {V('r7', V_Q)},a", "move b1,x0", "add x0,a",
      f"move #>${PITCH_MAX:x},x0", "cmp x0,a", "tgt x0,a", f"move #>${(PT_LO * 64) & 0xFFFFFF:x},x0", "cmp x0,a", "tlt x0,a")
    # ---- the increment q (Q19) = PT[st] + (PT[st + 1] - PT[st]) x frac / 64
    e("move a1,y1", "move a1,b", "asr #6,b,b", f"add #>${-PT_LO:x},b", f"add #>${tab_at['PT']:x},b", "move b1,r0", "nop",
      "move p:(r0)+,x0", "move p:(r0),b", "sub x0,b", "move b1,x1", "move y1,b", "and #>$3f,b", "asl #17,b,b", "move b1,y0",
      "mpy x1,y0,b", "add x0,b", f"move b1,{V('r7', V_Q)}", *(note_q(V) if note else ()))
    # ---- the span LGG x q >> 19; longer than L - 4: span = L - 4, LGG = (L - 4) << 19 / q
    e(f"move {V('r7', V_LGG)},x0", "move b1,x1", "mpy x1,x0,b", "asl #4,b,b",
      f"move {V('r7', V_L)},a", "sub #>$4,a", "cmp b,a", ("jcc", "ge", "g_ssp"),
      "move a1,b", "asr #5,a,a", f"move {V('r7', V_Q)},x0", ("jsr", "g_udiv"), f"move a0,{V('r7', V_LGG)}",
      ("label", "g_ssp"), f"move b1,{V('r7', V_SPAN)}")
    # ---- the position spray rnd x SPR / 128 x L / 2; g = ZS + PH + the spray, inside [0, L - 4 - span]
    e(("jsr", "g_rnd"), f"move {V('r6', P_SPR)},a", "and #>$7f,a", "asl #16,a,a", "move a,y0", "mpy y0,x0,a", "move a,x0",
      f"move {V('r7', V_L)},a", "asr a", "move a1,y0", "mpy y0,x0,a", f"move a1,{V('r7', V_SPR)}",
      f"move {V('r7', V_PH)},b", f"move {V('r7', V_ZS)},x0", "add x0,b", f"move {V('r7', V_SPR)},x0", "add x0,b",
      "tst b", ("jcc", "ge", "g_sc1"), "clr b", ("label", "g_sc1"),
      f"move {V('r7', V_L)},a", "sub #>$4,a", f"move {V('r7', V_SPAN)},x0", "sub x0,a", "move a1,x0", "cmp x0,b", "tgt x0,b",
      f"move b1,{V('r7', V_SPR)}")
    # ---- reversed with the chance REV / 128: it starts at g + span, the increment negated
    e(("jsr", "g_rnd"), "clr a", "move x0,a1", "and #>$7f0000,a", "asr #16,a,a", f"move {V('r6', P_REV)},x0", "clr b", "move #>$1,x1",
      "cmp x0,a", "tlt x1,b", f"move b1,{V('r7', V_REV)}",
      f"move {V('r7', V_SPR)},b", f"move {V('r7', V_S)},x0", "add x0,b",
      f"move {V('r7', V_Q)},a", "asr #19,a,a", f"move {V('r7', V_REV)},y0", "btst #$0,y0", ("jcc", "cc", "g_sfw"),
      "neg a", f"move {V('r7', V_SPAN)},x0", "add x0,b",
      ("label", "g_sfw"), f"move b1,{X('r2', G_PH)}", "clr b", f"move b,{X('r2', G_PL)}", f"move a1,{X('r2', G_IH)}",
      f"move a0,{X('r2', G_IL)}")
    # ---- the window: La = LGG fa / 256, Lr = LGG fr / 256 (>= 1), Lh = LGG - La - Lr (>= 0); de_a = gain / La, de_r = -(La de_a) / Lr
    e(f"move {V('r6', P_WIN)},a", "tst a", ("jcc", "ge", "g_w0"), "clr a", ("label", "g_w0"),
      "move #>$64,x0", "cmp x0,a", "tgt x0,a", "move #>$32,x0", "cmp x0,a", ("jcc", "gt", "g_wb"),
      "move a1,x0", "move #>$9d7,x1", "mpy x1,x0,a", "asr a", "asr #10,a,a", "move a0,a", "add #>$5,a", "move a1,y0", "move a1,y1",
      ("jmp", "g_wc"),
      ("label", "g_wb"), "sub x0,a", "move a1,x0", "move #>$9d7,x1", "mpy x1,x0,a", "asr a", "asr #10,a,a", "move a0,x0", "move #>$80,a",
      "sub x0,a", "move a1,y0", "move #>$80,a", "add x0,a", "move a1,y1",
      ("label", "g_wc"),
      f"move {V('r7', V_LGG)},x0", "mpy y0,x0,a", "asr a", "asr #8,a,a", "move a0,a", "move #>$1,x1", "cmp x1,a", "tlt x1,a",
      f"move a1,{X('r2', G_SEG)}", "move a1,b",
      "mpy x0,y1,a", "asr a", "asr #8,a,a", "move a0,a", "cmp x1,a", "tlt x1,a", f"move a1,{X('r2', G_LR)}",
      "add a,b", "move x0,a", "sub b,a", ("jcc", "ge", "g_slh"), "clr a", ("label", "g_slh"), f"move a1,{X('r2', G_LH)}",
      f"move {X('r2', G_SEG)},x0", "clr a", f"move {V('r7', V_GAIN)},a0", ("jsr", "g_udiv"),
      "move a0,x1", f"move x1,{X('r2', G_DE)}", "mpy x1,x0,a", "asr a", "move a0,a", "move a1,y0",
      "clr a", "move y0,a0", f"move {X('r2', G_LR)},x0", ("jsr", "g_udiv"), "move a0,a", "neg a", f"move a1,{X('r2', G_DR)}",
      f"move {X('r2', G_SEG)},a", f"move {X('r2', G_LH)},x0", "add x0,a", f"move {X('r2', G_LR)},x0", "add x0,a",
      f"move a1,{X('r2', G_TOT)}", "clr a", f"move a,{X('r2', G_SID)}", f"move a,{X('r2', G_E)}")
    if stereo:                                                          # (stereo) its pan: rnd x SPRD / 128 (no spread: 0, no draw, as mono)
        e("clr a", f"move {V('r6', P_SPRD)},a1", "and #>$7f,a", ("jcc", "eq", "g_snp"), ("jsr", "g_rnd"), "clr a",
          f"move {V('r6', P_SPRD)},a1", "and #>$7f,a", "asl #16,a,a", "move a1,y0", "mpy y0,x0,a", ("label", "g_snp"),
          f"move a,y:(r2+${PANOFF:x})")
    e("rts")

    # ================================================================ g_rnd: x0 = the next value (s x $0343FD + $269EC3, 24 bits); g_udiv: a0 = a / x0
    e(("label", "g_rnd"), f"move x:>${RNG:x},x0", "move #>$0343fd,y0", "mpy y0,x0,a", "asr a", "move a0,a", "add #>$269ec3,a",
      f"move a1,x:>${RNG:x}", "move a1,x0", "rts",
      ("label", "g_udiv"), "asl a", "andi #$fe,ccr", "rep #$18", "div x0,a", "rts")

    # ================================================================ g_grain1 / g_grain: a live grain's 32 samples (or until it ends) into Y:OUTB
    e(("label", "g_grain1"), f"move {X('r2', G_TOT)},a", "tst a", ("jcc", "gt", "g_grain"), "rts")
    # ---- the words this block may read: forward lo = PH, 32 (IH + 1) + 2 of them; reversed lo = PH + 32 IH, -32 IH + 2
    e(("label", "g_grain"), f"move {X('r2', G_PH)},a", f"move {X('r2', G_IH)},b", "tst b", ("jcc", "lt", "g_gneg"),
      "add #>$1,b", "asl #5,b,b", "add #>$2,b", ("jmp", "g_gcp"),
      ("label", "g_gneg"), "asl #5,b,b", "add b,a", "neg b", "add #>$2,b",
      ("label", "g_gcp"), f"move a1,{V('r7', V_LO0)}", f"move #>${LB:x},r5", f"move {V('r7', V_S)},x0", "cmp x0,a", ("jcc", "ge", "g_lok"),
      "sub x0,a", "add a,b", "neg a", "move a1,n5", "nop", "move (r5)+n5", "move x0,a",                # below the sample's start: from it
      ("label", "g_lok"), f"move a1,{V('r7', V_LO)}",
      f"move {V('r7', V_S)},a", f"move {V('r7', V_L)},x0", "add x0,a", f"move {V('r7', V_LO)},x0", "sub x0,a", "cmp b,a", "tlt a,b",
      f"move b1,{V('r7', V_CNT)}", ("jsr", "g_pcopy"))
    # ---- the grain loop (the Tracks'), its phase rebased into X:LB
    e("move r1,r0", "move #>$20,x0", f"move x0,{V('r7', V_NL)}", f"move {X('r2', G_PH)},a", f"move {X('r2', G_PL)},a0",
      f"move {V('r7', V_LO0)},x0", "sub x0,a", f"move #>${LB:x},x0", "add x0,a",
      ("label", "g_l"), f"move {V('r7', V_NL)},b", f"move {X('r2', G_SEG)},x0", "cmp x0,b", "tgt x0,b", "tst b", ("jcc", "eq", "g_seg"),
      "move b1,x1",
      f"move {V('r7', V_NL)},b", "sub x1,b", f"move b1,{V('r7', V_NL)}",
      f"move {X('r2', G_SEG)},b", "sub x1,b", f"move b1,{X('r2', G_SEG)}",
      f"move {X('r2', G_TOT)},b", "sub x1,b", f"move b1,{X('r2', G_TOT)}",
      *stereo_pick(stereo, V),
      "do x1,${g_e:x}",
      f"move {X('r2', G_E)},b", f"move {X('r2', G_DE)},x0", "add x0,b", f"move b1,{X('r2', G_E)}", "move b1,y1",
      "move a1,r4", "move a0,b", "lsr b", "move b1,x0", "move x:(r4)+,y0", "move x:(r4),b", "sub y0,b", "asr b", "move b1,x1",
      "mpy x1,x0,b", "asl b", "add y0,b",
      "move b1,x0", "mpy x0,y1,b", "move y:(r0),x1", "add x1,b", "move b,y:(r0)+", f"move {X('r2', G_IH)},x1", f"move {X('r2', G_IL)},x0",
      "add x,a", ("label", "g_e"),
      *stereo_loop(stereo, V, (0x20 if multi else OUTS - OUTB)),
      f"move {X('r2', G_SEG)},b", "tst b", ("jcc", "ne", "g_chk"),
      ("label", "g_seg"), f"move {X('r2', G_SID)},b", "add #>$1,b", f"move b1,{X('r2', G_SID)}", "cmp #>$1,b", ("jcc", "ne", "g_s2"),
      f"move {X('r2', G_LH)},x0", f"move x0,{X('r2', G_SEG)}", "clr b", f"move b,{X('r2', G_DE)}", ("jmp", "g_chk"),
      ("label", "g_s2"), "cmp #>$2,b", ("jcc", "ne", "g_dead"),
      f"move {X('r2', G_LR)},x0", f"move x0,{X('r2', G_SEG)}", f"move {X('r2', G_DR)},x0", f"move x0,{X('r2', G_DE)}", ("jmp", "g_chk"),
      ("label", "g_dead"), "clr b", f"move b,{X('r2', G_TOT)}",
      *([f"move {V('r7', V_NG)},b", "sub #>$1,b", f"move b1,{V('r7', V_NG)}"] if multi else []), ("jmp", "g_x"),
      ("label", "g_chk"), f"move {X('r2', G_TOT)},b", "tst b", ("jcc", "le", "g_dead"), f"move {V('r7', V_NL)},b", "tst b",
      ("jcc", "ne", "g_l"),
      ("label", "g_x"), f"move {V('r7', V_LO0)},x0", "add x0,a", f"move #>${LB:x},x0", "sub x0,a",
      f"move a1,{X('r2', G_PH)}", f"move a0,{X('r2', G_PL)}", "rts")

    # ================================================================ g_pcopy: X:(r5).. = CNT words of the sample from the virtual LO, page by page
    e(("label", "g_pcopy"), f"move {V('r7', V_CNT)},a", "tst a", ("jcc", "le", "g_pcx"),
      f"move {V('r7', V_LO)},a", "move a1,y1", "lsr #12,a", "move a1,x0", "lsr a", f"move {V('r7', V_TAB)},x1", "add x1,a", "move a1,r4",
      "nop", "move y:(r4),b", "btst #$0,x0", ("jcc", "cs", "g_podd"), "lsr #12,b", ("label", "g_podd"), "and #>$fff,b", "asl #12,b,b",
      "move y1,a", "and #>$fff,a", "move a1,x0", "add x0,b", "move b1,r4",
      "move #>$1000,a", "sub x0,a", f"move {V('r7', V_CNT)},x0", "cmp x0,a", "tgt x0,a", "move a1,n4", "nop",
      "do n4,${g_pce:x}", "move y:(r4)+,x0", "move x0,x:(r5)+", ("label", "g_pce"),
      f"move {V('r7', V_LO)},a", "move n4,x0", "add x0,a", f"move a1,{V('r7', V_LO)}",
      f"move {V('r7', V_CNT)},a", "sub x0,a", f"move a1,{V('r7', V_CNT)}", ("jmp", "g_pcopy"),
      ("label", "g_pcx"), "rts")
    return L


def stereo_pick(stereo, V=X):
    """(stereo) a spread: the stereo loop instead"""
    return [f"move {V('r6', P_SPRD)},b", "tst b", ("jcc", "ne", "g_ls")] if stereo else []


def stereo_loop(stereo, V=X, sofs=OUTS - OUTB):
    """(stereo) the grain loop with the side: OUTS[i] += s x e x the grain's pan (OUTS = OUTB + sofs)"""
    if not stereo:
        return []
    return [("jmp", "g_ed"), ("label", "g_ls"),
            "do x1,${g_es:x}",
            f"move {X('r2', G_E)},b", f"move {X('r2', G_DE)},x0", "add x0,b", f"move b1,{X('r2', G_E)}", "move b1,y1",
            "move a1,r4", "move a0,b", "lsr b", "move b1,x0", "move x:(r4)+,y0", "move x:(r4),b", "sub y0,b", "asr b", "move b1,x1",
            "mpy x1,x0,b", "asl b", "add y0,b",
            "move b1,x0", "mpy x0,y1,b", "move b,y0", "move y:(r0),x1", "add x1,b", "move b,y:(r0)",
            f"move y:(r2+${PANOFF:x}),x0", f"move y:(r0+${sofs:x}),b", "mac y0,x0,b", f"move b,y:(r0+${sofs:x})", "move (r0)+",
            f"move {X('r2', G_IH)},x1", f"move {X('r2', G_IL)},x0", "add x,a", ("label", "g_es"),
            ("label", "g_ed")]


def note_lgb(tab_at, V=X):
    """(RH40) r = PT[note + 48] (the note clamped to -48 .. +24), V_LGB = V_LGB << 19 / r"""
    return [f"move {V('r6', P_NOTE)},a", "move #>$18,x0", "cmp x0,a", "tgt x0,a", "move #>$ffffd0,x0", "cmp x0,a", "tlt x0,a",
            f"add #>${-PT_LO:x},a", f"add #>${tab_at['PT']:x},a", "move a1,r0", "nop", "move p:(r0),x0", f"move x0,{V('r7', V_R)}",
            f"move {V('r7', V_LGB)},a", "asr #5,a,a", ("jsr", "g_udiv"), f"move a0,{V('r7', V_LGB)}"]


def note_q(V=X):
    """(RH40) q = q x r >> 19, inside [1, Q_MAX] (b1 = q for what follows)"""
    return [f"move {V('r7', V_Q)},x0", f"move {V('r7', V_R)},x1", "mpy x1,x0,b", "asl #4,b,b", f"move #>${Q_MAX:x},x0", "cmp x0,b",
            "tgt x0,b", "move #>$1,x0", "cmp x0,b", "tlt x0,b", f"move b1,{V('r7', V_Q)}"]


Q_MAX = 0x27FFFF                                       # (RH40) < 5 x 2^19: the block's copy (32 x 5 + 2 words) still fits X:LB


def _hook(sp, name):
    """(RH55, sp) a jsr to tools/sp0.py's entry (Stock+: the grain's pitch + the pitch envelope / LFO, the position + the scan LFO)"""
    if not sp:
        return []
    import sp0 as SP0
    return [("jsr", SP0.entry(name))]


def gr_multi(tab_at, post, mix=MIX):
    """(multi) GR: the active slots (their KEY and TRK; V_ACT), the cap; each active slot's block (g_pre), the shared pool (g_gm), each
    slot's out (g_post), then the chain / the mix"""
    L = []

    def e(*s):
        L.extend(s)
    e(("label", "gr"), "clr b")
    for k in range(NSLOT):
        y = slot_y(k)
        e(f"move y:>${y + P_KEY:x},a", f"move #>${KEY:x},x0", "cmp x0,a", ("jcc", "ne", f"g_n{k}"),
          f"move y:>${y + P_TRK:x},a", "tst a", ("jcc", "eq", f"g_n{k}"),
          "move #>$1,a", f"move a1,y:>${y + 0x10 + V_ACT:x}", "add #>$1,b", ("jmp", f"g_d{k}"),
          ("label", f"g_n{k}"), "clr a", f"move a1,y:>${y + 0x10 + V_ACT:x}", ("label", f"g_d{k}"))
    e("tst b", ("jcc", "eq", mix), f"move b1,y:>${NACT:x}", f"add #>${tab_at['CAP_T'] - 1:x},b", "move b1,r0", "nop", "move p:(r0),x0",
      f"move x0,y:>${CAPW:x}", ("jsr", "g_save"))
    # the pool, once (power-up garbage): its grains and their slots cleared
    e(f"move y:>${GMAG:x},a", f"move #>${MAGIC:x},x0", "cmp x0,a", ("jcc", "eq", "g_pok"),
      "clr a", f"move #>${GR0:x},r0", "nop", f"do #${MAXG * GW:x},${{g_pc1:x}}", "move a,x:(r0)+", ("label", "g_pc1"),
      f"move #>${GR0 + PANOFF:x},r0", "nop", f"do #${MAXG * GW:x},${{g_pc2:x}}", "move a,y:(r0)+", ("label", "g_pc2"),
      f"move x0,y:>${GMAG:x}", "move #>$1234,x0", f"move x0,x:>${RNG:x}", ("label", "g_pok"), f"move #>${GR0:x},r3")
    for k in range(NSLOT):
        y = slot_y(k)
        e(f"move #>${y:x},r6", f"move #>${y + 0x10:x},r7", "nop", f"move {Ym('r7', V_ACT)},a", "tst a", ("jcc", "eq", f"g_q{k}"),
          ("jsr", "g_pre"), ("label", f"g_q{k}"))
    e("clr a", f"move #>${OUTY:x},r0", "nop", f"do #${NSLOT * SLOT_N:x},${{g_cs:x}}", "move a,y:(r0)+", ("label", "g_cs"),
      "move r3,r2", f"move #>${GW:x},n2", "nop", f"do #${MAXG:x},${{g_ml:x}}", ("jsr", "g_gm"), "move (r2)+n2", ("label", "g_ml"))
    for k in range(NSLOT):
        y = slot_y(k)
        e(f"move #>${y:x},r6", f"move #>${y + 0x10:x},r7", "nop", f"move {Ym('r7', V_ACT)},a", "tst a", ("jcc", "eq", f"g_o{k}"),
          f"move {Ym('r7', V_ON)},a", "tst a", ("jcc", "eq", f"g_o{k}"), ("jsr", "g_post"), ("label", f"g_o{k}"))
    e(("jsr", "g_rest"), ("jmp", post or mix))
    # ---- g_gm: a pool grain (r2): live, its slot's r6 / r7 / sums; a slot not running (or a new voice) kills it
    e(("label", "g_gm"), "move x:(r2),a", "tst a", ("jcc", "gt", "g_gml"), "rts",
      ("label", "g_gml"), f"move y:(r2+${PANOFF + 1:x}),r6", "nop", "move r6,a", "add #>$10,a", "move a1,r7", "nop",
      f"move {Ym('r7', V_ACT)},a", "tst a", ("jcc", "eq", "g_gk"), f"move {Ym('r7', V_ON)},a", "tst a", ("jcc", "eq", "g_gk"),
      "move r6,a", f"add #>${OUTY - SLOTY:x},a", "move a1,r1", ("jmp", "g_grain"),
      ("label", "g_gk"), "clr a", "move a,x:(r2)", f"move {Ym('r7', V_NG)},a", "sub #>$1,a", f"move a1,{Ym('r7', V_NG)}", "rts")
    return L


def code(note=False, post=None, stereo=False, multi=False, sp=False, mix=MIX):
    """-> (the segment's words from P:CODE (multi: P:MCODE), labels, {table: address})"""
    tb = tables()
    names = ("SIZE_T", "PT", "GAIN_T") + (("CAP_T",) if multi else ())
    if multi:
        tb["CAP_T"] = list(CAP_T)
    at0 = MCODE if multi else CODE
    w0, _ = C0.asm_at(items({k: 0x3000 for k in tb}, note=note, post=post, stereo=stereo, multi=multi, sp=sp, mix=mix), at0)
    at, tab_at = at0 + len(w0), {}
    for k in names:
        tab_at[k] = at
        at += len(tb[k])
    w, labels = C0.asm_at(items(tab_at, note=note, post=post, stereo=stereo, multi=multi, sp=sp, mix=mix), at0)
    assert len(w) == len(w0)
    for k in names:
        w += tb[k]
    assert at0 + len(w) <= C0.LD, hex(at0 + len(w))
    return w, labels, tab_at


def segs(note=False, post=None, stereo=False, multi=False, sp=False, mix=MIX):
    """-> core0.py's segments: RD20's test segment + 1 pad word + the engine at P:CODE, and the hook at P:$224; multi: the test segment
    alone, the engine at P:MCODE"""
    sw, _ = C0.asm_at(C0.seg_items(), C0.SEG)
    w, labels, _ = code(note=note, post=post, stereo=stereo, multi=multi, sp=sp, mix=mix)
    if multi:
        return [(C0.SEG, sw), (MCODE, w), (HOOK, [0x0BF080, labels["gr"]])], labels
    first = sw + [0] * (CODE - C0.SEG - len(sw)) + w
    return [(C0.SEG, first), (HOOK, [0x0BF080, labels["gr"]])], labels


def install(img, report, base_addr, counter=True, note=False, extra=None, post=None, stereo=False, multi=False, sp=False, mix=MIX):
    """counter: RD20's pass counter in core 0's vectors (diagnostic builds); the user builds (RH39 on) without it.  note (RH40): the
    played note pitches the granular (X:GB + P_NOTE, written by tools/granpage.py).  extra (RD23): f(labels) -> more core 0 segments,
    sent after ours (tools/stsplit.py: its code and P:$224 -> its SPL, which goes on to GR).  sp / mix (RH55): tools/sp0.py's hooks in the
    grains' pitch and position, and the end (with no slot running, or after `post`) to `mix` (sp0's SPX) in place of the stock's mix"""
    import voicefx
    sg, labels = segs(note=note, post=post, stereo=stereo, multi=multi, sp=sp, mix=mix)
    if extra:
        sg = sg + extra(labels)
    if multi:
        voicefx.check(sg[1][1][:labels["g_pcx"] + 1 - MCODE], MCODE)
    else:
        voicefx.check(sg[0][1][CODE - C0.SEG:CODE - C0.SEG + labels["g_pcx"] + 1 - CODE], CODE)
    _, _, ws = C0.block_words(img)
    assert tuple(ws[HOOK:HOOK + 2]) == OLD_HOOK, "core 0's jsr $367 at P:$224 moved"
    C0.install(img, report, base_addr, counter=counter, loader=True, segs=sg)
    report["granular0"] = dict(gr=hex(labels["gr"]), words=len(sg[0][1]), x=hex(GB), lb=hex(LB), outb=hex(OUTB), save=hex(SAVE), note=note,
                               **({"stereo": True} if stereo else {}), **({"multi": True} if multi else {}), **({"sp": True} if sp else {}))
    return labels
