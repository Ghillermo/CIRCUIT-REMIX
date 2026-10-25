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
probe (RD12, in place of the burn: the core's P memory above $1000, where nothing of ours can go yet): each block, Y:PCMD (shifted) not 0 ->
r1 = Y:PA; a negative PCMD first writes Y:PV to P:(r1) (movem); then P:(r1) -> Y:PRB and PCMD = 0 (tools/rhpmem.py: the host reads the old
word, writes a pattern, reads it back, looks at X:/Y: of the same address for an alias, writes the old word back).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rhdsp1  # noqa: E402
import rhdsppatch as DP  # noqa: E402

Y_IDLE, Y_BURN, Y_BLOCKS = 0x1300, 0x1301, 0x1302
Y_PCMD, Y_PA, Y_PV, Y_PRB = 0x13DC, 0x13DD, 0x13DE, 0x13DF        # (probe; + the shift: $16DC..)
P_WAIT, P_ACK = 0x111, 0x128
OLD_WAIT, OLD_ACK = 0x0D07F8, 0x09C510                 # jsr $7F8; movep x1,y:<<$ffffd0
JSR_SHORT = 0x0D0000


def code(shift=0, probe=False, hook=None, call=None):
    """-> (words for P:$D34.., the address of BLOCK); shift: our Y words moved up (RD8 on: $300, out of voice 7's sample ring)"""
    yi, yb, yk = Y_IDLE + shift, Y_BURN + shift, Y_BLOCKS + shift
    idle = DP.asm([f"move y:>${yi:x},a1", "add #>1,a", f"move a1,y:>${yi:x}"]) + DP.jmp(0x7F8)
    blk_at = rhdsp1.START + len(idle)
    if hook is not None:                                   # (RD16) the block's acknowledgement, the counter, then jmp hook (WSOLA's WSB)
        block = (DP.asm(["movep x1,y:<<$ffffd0", f"move y:>${yk:x},a1", "add #>1,a", f"move a1,y:>${yk:x}"])
                 + ([JSR_SHORT | call] if call is not None else []) + DP.jmp(hook))      # (RD17: call = a routine in the landing area)
        return idle + block, blk_at
    if probe:
        assert shift
        pc, pa, pv, pr = (y + shift for y in (Y_PCMD, Y_PA, Y_PV, Y_PRB))
        head = DP.asm(["movep x1,y:<<$ffffd0", f"move y:>${yk:x},a1", "add #>1,a", f"move a1,y:>${yk:x}",
                       f"move y:>${pc:x},a", "tst a"])
        mid = DP.asm([f"move y:>${pa:x},r1", f"move y:>${pv:x},x0"])
        wr = DP.asm(["move x0,p:(r1)"])
        rd = DP.asm(["move p:(r1),x0", f"move x0,y:>${pr:x}", "clr a", f"move a,y:>${pc:x}"])
        ret = DP.asm(["rts"])
        rd_at = blk_at + len(head) + 2 + len(mid) + 2 + len(wr)
        x_at = rd_at + len(rd)
        block = head + DP.jcc("eq", x_at) + mid + DP.jcc("pl", rd_at) + wr + rd + ret
        assert len(block) == x_at + 1 - blk_at
        return idle + block, blk_at
    head = DP.asm(["movep x1,y:<<$ffffd0", f"move y:>${yk:x},a1", "add #>1,a", f"move a1,y:>${yk:x}",
                   f"move y:>${yb:x},a", "tst a"])
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
