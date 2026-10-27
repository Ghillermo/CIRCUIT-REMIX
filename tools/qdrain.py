"""Core 1 takes every waiting trigger, not one a block (MIT; pitchmod qdrain, RD26, docs/PRUEBA_RD26.md).

RD24 / RD25 on the device (2026-10-26): with 8 tracks on step 1, core 1 took the note-ons one per block (0.67 ms each) although the ARM
had written them 0.33 ms apart: the last track sounded 4.7 ms after the first, on every step where several tracks play together.

The stock (core 1, read in its program): the main loop calls P:$4CD once a block (P:$11C `jsr $4CD`); it reads one message of the ARM's
queue (16 pairs Y:$30410 + 2 i, write index Y:$307B5 = the ARM's 0x080406A8, read index Y:$307B6), and each handler ends in `rts`: note-on
$90 (P:$4F4..$508: Y:$307B7 + 2 t, the voice's state 4), note-off $80 (P:$509..$510: state 2), $B0 (P:$4E8..$4F3: a track parameter).
The ARM sends only $90 and $80 (its five calls of 0x080406A8; nothing else writes the queue): the $B0 path is never taken.

Ours, in place:
  * P:$4E4..$4F3 (the $B0 test and handler, 16 words) = NX: with the queue empty -> rts; else the next message's track (word 0 & 7) is
    compared with the one just handled (y1, which both handlers leave as it was): another track -> `jne $4CD` (the stock reads and
    handles it); the same track -> rts (it waits for the next block, as every message did: a note-off and the note-on after it on one
    track keep their block apart);
  * P:$4D2 (the empty queue's `beq $4E7`) -> `beq $4F3` (NX's rts; $4E7 is now inside NX);
  * the note-on and note-off handlers' rts (P:$508, $510) -> `jmp $4E4`;
  * unknown types (and $B0) fall into NX after the $80 test, as the stock skipped them (`bra $4CD`), now under the same rule.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rhdsppatch as DP  # noqa: E402

NX, NX_END, RTS_AT = 0x4E4, 0x4F4, 0x4F3
Q_READ, P_EMPTY, P_ON_RTS, P_OFF_RTS = 0x4CD, 0x4D2, 0x508, 0x510
OLD_EMPTY = 0x05A415                                            # beq $4E7
OLD_NX = (0x20004D, 0x05A403, 0x050FC7, 0x00000C, 0x2E0779, 0x44F476, 0x0307C8, 0x0C1C91, 0x015F8E, 0x45F448, 0x001000, 0x218400,
          0x2000AA, 0x21B200, 0x4E6200, 0x00000C)               # P:$4E4..$4F3 in the stock
RTS = 0x00000C


def bcc_short(cc, at, target):
    """Bcc with a 9-bit displacement (one word), as the stock's `beq $4E7` at P:$4D2 (05A415)"""
    d = (target - at) & 0x1FF
    return 0x050000 | cc << 12 | 0x400 | (d >> 5) << 6 | (d & 0x1F)


EQ, NE = 0xA, 0x2


def nx_words():
    w = (DP.asm([f"move y:>${0x307B6:x},a", f"move y:>${0x307B5:x},x0", "cmp x0,a"]) + [0x0E0000 | EQ << 12 | RTS_AT]
         + DP.asm(["and #<$f,a", "asl #1,a,b", "add #>$30410,b", "move b1,r0", "move y:(r0),b", "eor y1,b", "and #<$7,b"])
         + [0x0E0000 | NE << 12 | Q_READ] + [RTS])
    assert len(w) == NX_END - NX and NX + w.index(RTS) == RTS_AT, len(w)
    return w


def patches():
    """{P address: (stock word, ours)}"""
    p = {P_EMPTY: (OLD_EMPTY, bcc_short(EQ, P_EMPTY, RTS_AT)), P_ON_RTS: (RTS, 0x0C0000 | NX), P_OFF_RTS: (RTS, 0x0C0000 | NX)}
    assert bcc_short(EQ, P_EMPTY, 0x4E7) == OLD_EMPTY
    for i, (old, new) in enumerate(zip(OLD_NX, nx_words())):
        p[NX + i] = (old, new)
    return p
