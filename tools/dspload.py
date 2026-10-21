"""How busy is the Circuit Rhythm 5706's DSP core 1 (the voices)? Counters and a burn loop in its main loop (MIT; RD5, the DSP study before the
two sampler modes).

The stock (core 1's program, tools/rhdsp.py dis 1): the main loop P:$111..$129 waits for a new block (P:$111 jsr $7F8, the mailbox from
core 0; then Y:$FFFFD1 against Y:$FFFFD0), runs the block's routines (P:$11C..$126: the voices at $221, the queue of triggers $2E4, …) and
acknowledges it (P:$127 movep y:$FFFFD1,x1; P:$128 movep x1,y:$FFFFD0); $7F8 loads a and x1 itself, so a is free before it and after P:$128.
Ours (tools/rhdsp1.py puts the code at P:$D34):
  * P:$111 jsr $7F8 -> jsr IDLE: Y:$1300 + 1 (one turn of the wait), then $7F8;
  * P:$128 movep x1,y:$FFFFD0 -> jsr BLOCK: the acknowledgement, Y:$1302 + 1 (one block), then Y:$1301 cycles of nop (rep; 0 = none):
    the ARM sets Y:$1301 (rhremote dspw 1 Y:1301 N) to load the core by a known amount;
  * counters in a1 only (24 bits, they wrap); Y:$1300-$1302 are zero in every dump of the device (probe/dsp1_y*.bin).
tools/rhdspload.py reads them on the device: turns of the wait per block with and without the burn = the free cycles per block.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rhdsp1  # noqa: E402
import rhdsppatch as DP  # noqa: E402

Y_IDLE, Y_BURN, Y_BLOCKS = 0x1300, 0x1301, 0x1302
P_WAIT, P_ACK = 0x111, 0x128
OLD_WAIT, OLD_ACK = 0x0D07F8, 0x09C510                 # jsr $7F8; movep x1,y:<<$ffffd0
JSR_SHORT = 0x0D0000


def code():
    """-> (words for P:$D34.., the address of BLOCK)"""
    idle = DP.asm([f"move y:>${Y_IDLE:x},a1", "add #>1,a", f"move a1,y:>${Y_IDLE:x}"]) + DP.jmp(0x7F8)
    blk_at = rhdsp1.START + len(idle)
    head = DP.asm(["movep x1,y:<<$ffffd0", f"move y:>${Y_BLOCKS:x},a1", "add #>1,a", f"move a1,y:>${Y_BLOCKS:x}",
                   f"move y:>${Y_BURN:x},a", "tst a"])
    tail = DP.asm(["rep a1", "nop"])
    ret = DP.asm(["rts"])
    x_at = blk_at + len(head) + 2 + len(tail)
    block = head + DP.jcc("eq", x_at) + tail + ret
    return idle + block, blk_at


def install(img, report, base_addr):
    """core 1's two stock words checked and redirected; our words through rhdsp1."""
    words, blk_at = code()
    assert rhdsp1.START + len(words) <= 0x1000, "out of reach of a short jsr"
    rhdsp1.patch_p(img, P_WAIT, OLD_WAIT, JSR_SHORT | rhdsp1.START)
    rhdsp1.patch_p(img, P_ACK, OLD_ACK, JSR_SHORT | blk_at)
    labels = rhdsp1.install(img, report, base_addr, words, "dspload")
    report["dspload"].update(idle=hex(rhdsp1.START), block=hex(blk_at), y_idle=hex(Y_IDLE), y_burn=hex(Y_BURN), y_blocks=hex(Y_BLOCKS))
    return labels, b""
