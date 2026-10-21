"""Pitch envelope and pitch LFO per track in the Circuit Rhythm 5706's DSP core 1, the voices (MIT; the first piece of the Stock+ sampler mode).

The stock (core 1's program, tools/rhdsp.py dis 1; docs/PORTADO.md «Núcleo 1 = las voces»):
  * P:$1C3 turns a pitch (y0, log: a semitone = $10000, an octave = $C0000; measured in dsptool, tests/emu_rd6.py) into the voice's resampling increment Y:(base) and its polyphase
    table Y:(base + 1), base = r4 = $40 + $10 t (track t's voice block);
  * it is called from two places: P:$168 (bsr, the note's start: P:$2FD -> P:$15A) and P:$2D8 (jsr, P:$289: once a block, one voice a
    block in turn, Y:$121 = the voice, so each voice's pitch is recomputed every 8 blocks); P:$2D6 clamps the pitch to $23CCCC before it;
  * a note's start comes from core 0's queue (P:$2E4: P:$2F2 jsne $2FD with y1 = the trigger word, its bits 0-2 = the track).
Ours (tools/rhdsp1.py puts the words at P:$D34.., after dspload's when both are in):
  * P:$2D8 jsr $1C3 -> jsr RR: Y:E[t] *= D[t] (the envelope's decay), the LFO's phase += R[t], pitch += A[t] * E + L[t] * triangle(phase),
    clamped to [-$480000, $23CCCC] (6 octaves below 0 .. the stock's top), then $1C3;
  * P:$2F3 (jsne $2FD's address) -> TRIG: the stock's start ($2FD), then E[t] = 1 and the voice's pitch recomputed at once through P:$289
    (Y:$121 set to t - 1 and given back), so the envelope begins with the note, not up to 8 blocks later;
  * all zero (as at power-on: P:$151 clears Y:$400..$13FF) = the stock's pitch.
Core 1's Y, per track t (written by the ARM through the host port, rhremote dspw 1 Y:...; zero in every dump of the device):
  Y:$1310 + t  E, the envelope (ours)          Y:$1320 + t  A, envelope amount (signed, pitch units: 12 semitones = $C0000)
  Y:$1318 + t  the LFO's phase (ours)          Y:$1328 + t  D, the envelope's factor per update (fraction: $7FFFFF = holds)
                                               Y:$1330 + t  R, the LFO's phase step per update (a full cycle = $1000000)
                                               Y:$1338 + t  L, LFO depth (signed, pitch units)
  Y:$1308 / $1309 scratch (TRIG).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dspload  # noqa: E402
import rhdsp1  # noqa: E402
import rhdsppatch as DP  # noqa: E402

Y_BASE = 0x1310
OFF_E, OFF_PH, OFF_A, OFF_D, OFF_R, OFF_L = 0x00, 0x08, 0x10, 0x18, 0x20, 0x28
Y_TMP0, Y_TMP1 = 0x1308, 0x1309
P_EXP, P_RR_CALL, P_TRIG_ADDR, P_START, P_RR = 0x1C3, 0x2D8, 0x2F3, 0x2FD, 0x289
OLD_RR_CALL = 0x0D01C3                                 # jsr $1c3 (short)
JSR_SHORT = 0x0D0000
PITCH_MAX, PITCH_MIN = 0x23CCCC, 0x1000000 - 0x240000


def code(at):
    """-> (words for P:at.., RR's address, TRIG's address)"""
    rr = DP.asm([
        "move r4,a", "sub #>$40,a", "lsr #4,a", "move a1,n1", f"move #>${Y_BASE:x},r1", "lua (r1)+n1,r1",
        "move y:(r1),x0", f"move y:(r1+${OFF_D:x}),x1", "mpyr x1,x0,a", "move a,y:(r1)",                    # E *= D
        "move a,x0", f"move y:(r1+${OFF_A:x}),x1", "mpy x1,x0,b",                                       # b = A * E
        f"move y:(r1+${OFF_PH:x}),a", f"move y:(r1+${OFF_R:x}),x0", "add x0,a", f"move a1,y:(r1+${OFF_PH:x})",  # phase += R
        "move a1,a", "abs a", "asl a", "move #>$7fffff,x0", "sub x0,a", "move a,x0",                     # triangle
        f"move y:(r1+${OFF_L:x}),x1", "mac x1,x0,b",                                                    # b += L * tri
        "move y0,a", "add b,a",
        f"move #>${PITCH_MAX:x},x0", "cmp x0,a", "tgt x0,a",
        f"move #>${PITCH_MIN:x},x0", "cmp x0,a", "tlt x0,a",
        "move a1,y0"]) + DP.jmp(P_EXP)
    trig_at = at + len(rr)
    trig = (DP.asm([f"move y1,y:>${Y_TMP0:x}"]) + DP.jsr(P_START) + DP.asm([
        f"move y:>${Y_TMP0:x},a", "and #>$7,a", "move a1,n1", f"move #>${Y_BASE:x},r1",
        "move #>$7fffff,x0", "move x0,y:(r1+n1)",                                                       # E = 1
        "move y:>$121,x0", f"move x0,y:>${Y_TMP1:x}", "sub #>$1,a", "and #>$7,a", "move a1,y:>$121"])
        + DP.jsr(P_RR) + DP.asm([f"move y:>${Y_TMP1:x},x0", "move x0,y:>$121", "rts"]))
    return rr + trig, at, trig_at


def install(img, report, base_addr, load=False):
    """our words through rhdsp1 (after dspload's counters when load: RD6); core 1's two stock words checked and redirected."""
    pre, rr_at, trig_at = [], rhdsp1.START, None
    if load:
        pre, blk_at = dspload.code()
        rhdsp1.patch_p(img, dspload.P_WAIT, dspload.OLD_WAIT, JSR_SHORT | rhdsp1.START)
        rhdsp1.patch_p(img, dspload.P_ACK, dspload.OLD_ACK, JSR_SHORT | blk_at)
    ours, rr_at, trig_at = code(rhdsp1.START + len(pre))
    words = pre + ours
    assert rhdsp1.START + len(words) <= 0x1000, "out of reach of a short jsr"
    rhdsp1.patch_p(img, P_RR_CALL, OLD_RR_CALL, JSR_SHORT | rr_at)
    rhdsp1.patch_p(img, P_TRIG_ADDR, P_START, trig_at)
    labels = rhdsp1.install(img, report, base_addr, words, "pitchmod")
    report["pitchmod"].update(rr=hex(rr_at), trig=hex(trig_at), y_base=hex(Y_BASE), load=load)
    if load:
        report["pitchmod"].update(block=hex(blk_at), y_idle=hex(dspload.Y_IDLE), y_burn=hex(dspload.Y_BURN), y_blocks=hex(dspload.Y_BLOCKS))
    return labels, b""
