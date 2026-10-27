"""Each voice's envelope x gain from DSP core 1 to shared memory, for core 0's chain after the granular (MIT; pitchmod envexp, RD30,
tools/granchain.py).

The stock's level of a voice (core 1, read in its program): the amp envelope's stage routine (the table $5CE, from $511's `jmp (r3+n3)`)
multiplies the voice's samples and keeps its level at x:(r6 + $B) = X:$4B + $10 v; the mix ($6AB) multiplies by the voice's gain
X:$44 + $10 v (0 = the voice is off); $244 the end-of-sample fade, already shared (Y:$37302 + 2 v).  Both of the first two are core 1's
own memory, which core 0 cannot read.
Ours: P:$240 (`jsr FX`, voicefx, right after $511) -> jsr EXP, 13 words in the loader's free P:$2B..$37 (tools/rhdsp1.py LAND_FREE; the
loop scan has $C..$2A): Y:$37400 + 16 v = gain x envelope (nothing of the stock's, of either core or the ARM, uses shared memory above
$37310), then jmp FX.  A voice that is off is not run (its word keeps the last value: 0 once its envelope ended).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

AT = 0x2B
SHARED = 0x37400                                   # + 16 v
GAIN, ENV = 0x44, 0x4B                             # X:$44 / $4B + $10 v in core 1
P_HOOK = 0x240


def words(fx_at):
    import rhdsppatch as DP
    w = DP.asm(["move y:>$1405,a", "asl #4,a,a", "move a1,n1", f"move #${GAIN:x},r1", "move x:(r1+n1),x0", f"move #${ENV:x},r1",
                "move x:(r1+n1),x1", "mpy x1,x0,a", f"move #>${SHARED:x},r1", "move a,y:(r1+n1)"]) + [0x0C0000 | fx_at]
    assert len(w) == 13, len(w)
    return w
