"""The retrigger de-click on the Circuit Rhythm's DSP core 0 (MIT; RH68).  The user, 2026-11-04: «Does the Crossfade feature apply on
retriggers? And gated/one-shot Mode?» -> «Add that», on Sample mode's pad 19 (and Sample Rec's pad 23 for every track), «Keep the current
de-clicker toggle for all modes, also reverse».

The stock (core 1, tools/rhdsp.py dis 1): a note-on in the ARM's trigger queue is read at the start of core 1's block (P:$4CD), the voices
are rendered (P:$221, into Y:$304F0 + 64 t + 32 (y:$FFFFD0)), and only then the waiting notes start (P:$2E4 -> P:$2FD): the read position
and the voice's sample ring are reset, the envelope level X:$4B + $10 t set to 0, nothing faded.  So a retrigger cuts the old sound at a
block's end and the new one starts with the next block: a step between two of the track's blocks (a click; also a sample whose region
starts away from a zero crossing).  It does not depend on the play mode or the direction.

Here (core 0; core 1 has no room): the track's 32 samples, right before the stock's mix, after every engine of ours (the end of sp0's
SPX, before its g_rest: every r / n / m register is ours there):
  * DCN, at each message of the trigger queue (synth0's queue reader, through sp0's NOTE entry, which this one goes on to): a note-on of
    track t = its window, N blocks;
  * DCX, every block: a track in its window with its switch on gets the offset ramp d (1 - i / 32), d = the last sample heard of the block
    before - its first sample; then the last sample heard is kept.  Core 0 sees the message one block before or after core 1 starts the
    note (its own read of the queue), so the window covers three blocks: on a block without a step, d is one sample's change of the
    waveform and the ramp is inaudible.
The switch of each track = loopxf's (the crossfade's flags of core 1, Y:$16E0 + t): granpage's crossfade round writes the same word to
Y:SW + t of core 0 (granpage with the OPT rtdc).  State from zero once (MAGIC); the switches from power-on garbage until the round writes
them (at most a second; a de-click switched on by garbage is harmless).
Core 0: P:AT (the unused vectors: $46..$FF are nop in the stock block, and no RH build since RD22 puts anything there), Y:$1F40..$1F58.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core0 as C0  # noqa: E402

AT, END = 0x46, 0x100
DCN_AT, DCX_AT = AT, AT + 2                       # fixed entries: sp0's NOTE entry jumps to DCN, its SPX calls DCX
CNT, LAST, SW, MAG = 0x1F40, 0x1F48, 0x1F50, 0x1F58   # core 0 Y (stsplit's job ends at $1F19; nothing else above $1EFF)
MAGIC = 0x0DEC11
NBLK = 3                                          # the window, in blocks
TRK_BUF = 0x304F0


def _fmopt():
    import rhbuild
    return rhbuild.OPT.get("fm", False)


def _fm():
    import fm0
    return fm0


def _probe():
    import rhbuild
    return rhbuild.OPT.get("c0probe", False)


def items(e_note):
    L = [("jmp", "dcn")]
    # ================================================================ DCX (from SPX, before g_rest): every track
    L += [("label", "dcx"), f"move y:>${MAG:x},a", f"move #>${MAGIC:x},x0", "cmp x0,a", ("jcc", "eq", "dx_ok"),
          "clr a", f"move #>${CNT:x},r0", "nop", "rep #$10", "move a,y:(r0)+", f"move x0,y:>${MAG:x}",
          ("label", "dx_ok"), "movep y:<<$ffffd0,b", "asl #5,b,b", f"add #>${TRK_BUF:x},b", "move b1,r0",
          f"move #>${CNT:x},r1", "move #>$40,n0", "nop",
          "do #$8,${dx_e:x}",
          "move y:(r1),a", "tst a", ("jcc", "eq", "dx_s"), "move #>$1,x0", "sub x0,a", "move a1,y:(r1)",
          f"move y:(r1+${SW - CNT:x}),a", "tst a", ("jcc", "eq", "dx_s"),
          f"move y:(r1+${LAST - CNT:x}),a", "move y:(r0),x0", "sub x0,a", "tfr a,b", "asr #5,b,b", "move b,y1", "move r0,r2", "nop",
          "do #$20,${dx_r:x}", "move y:(r2),b", "add a,b", "move b,y:(r2)+", "sub y1,a", ("label", "dx_r"),
          ("label", "dx_s"), "move y:(r0+$1f),x0", f"move x0,y:(r1+${LAST - CNT:x})", "move (r0)+n0", "move (r1)+",
          ("label", "dx_e"), *(["jmp $96"] if _probe() else ["rts"])]          # (RD37) then tools/c0probe.py's command check
    # ================================================================ DCN (sp0's NOTE entry; y0 = w0; keeps x1): a note-on opens its window
    L += [("label", "dcn"), "move y0,a", "and #>$f00000,a", "move a1,a", "move #>$900000,x0", "cmp x0,a", ("jcc", "ne", e_note),
          "move y0,a", "and #>$7,a", f"add #>${CNT:x},a", "move a1,r1", f"move #>${NBLK:x},x0", "move x0,y:(r1)",
          *([f"move x0,x:(r1+${_fm().NF - CNT:x})"] if _fmopt() else []), ("jmp", e_note)]            # (RD38) the FM's note-on flag
    return L


def code(e_note):
    """-> (words at P:AT, labels)"""
    import sp0 as SP
    w, labels = C0.asm_at(SP.short_items(items(e_note)), AT)
    assert AT + len(w) <= END, f"rtdc ends at {AT + len(w):#x}"
    assert labels["dcx"] == DCX_AT and w[0] == 0x0AF080 and w[1] == labels["dcn"], "rtdc's entries moved"
    return w, labels


def segs(e_note):
    return [(AT, code(e_note)[0])]


def check(e_note):
    """dsptool reads every word back (no mpysu)"""
    import voicefx
    return voicefx.check(code(e_note)[0], AT)


class Model:
    """DCN / DCX on 24-bit words (as the DSP: the 56-bit accumulators, limited moves)"""

    def __init__(self):
        self.cnt, self.last, self.sw = [0] * 8, [0] * 8, [0] * 8

    def note(self, w0):
        if (w0 & 0xF00000) == 0x900000:
            self.cnt[w0 & 7] = NBLK

    @staticmethod
    def _s(v):
        v &= 0xFFFFFF
        return v - (1 << 24) if v & 0x800000 else v

    def block(self, t, buf):
        """buf: 32 words (24-bit) -> 32 words"""
        buf = [self._s(x) for x in buf]
        if self.cnt[t]:
            self.cnt[t] -= 1
            if self.sw[t]:
                a = (self._s(self.last[t]) - buf[0]) << 24                  # a = L - s0, 56-bit (a1 at bits 24..47)
                y1 = self._lim(a >> 5)                                     # b = a >> 5, then y1 = b limited
                for i in range(32):
                    b = (buf[i] << 24) + a
                    buf[i] = self._lim(b)
                    a -= y1 << 24
        self.last[t] = buf[31]
        return [x & 0xFFFFFF for x in buf]

    @staticmethod
    def _lim(acc):
        """an accumulator moved to a 24-bit word: limited, else its a1 (truncated)"""
        hi = acc >> 24
        if hi > (1 << 23) - 1:
            return (1 << 23) - 1
        if hi < -(1 << 23):
            return -(1 << 23)
        return hi
