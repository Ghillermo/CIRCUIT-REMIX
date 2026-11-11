"""The looper / live sampler on core 0 (MIT; RD50; the user, 2026-11-11: «I want to make a looper/live sampler … A pad or two … samples audio
from the input/master mix. Either for the hold length or a set bar length … 4 pads play back the samples either in loop or one-shot modes.
Overdubbing»; docs/DISENO_LOOPER.md).  Called by drybus's DRY2 (P:$282: after the Grid FX, before the compressor), its registers saved.

Memory: the SDRAM no sample uses (RD35: Y:$D87000-$FFEFFF, 632 pages of 4 096 words): 4 buffers of 158 pages (323 584 stereo frames,
6.7 s at 48 kHz), L R interleaved, frame f of head h at Y:BASE(h) + 2 f.
Control (core 0 X, written by the ARM; LKEY at X:KEY or nothing runs): per head h at X:HD + 8 h: + 0 the state (0 stopped, 1 once, 2 loop),
+ 1 its length (frames; 0 = empty), + 2 its position (frame), + 3 its level (a fraction); the recording at X:RC: + 0 on (1) / off (0),
+ 1 its head, + 2 the source (0 the line input Y:$30710, 1 the mix before the loops X:$4B18), + 3 overdub (1) / replace (0), + 4 the
feedback (a fraction: the old audio's share on each overdub pass), + 5 its position (frames written, replace), + 6 (ours) the head's
starting position this block, + 7 the replace's limit (frames, a multiple of 32, <= CAP: the hold's CAP, or N bars).
A block (LOOP, its registers saved by DRY2):
  1. the recording on: the source's 32 frames to X:TMP;
  2. each head playing with a length (a counted loop: lp_head's do and lp_addr's jsr inside it are the deepest, DRY2 + 5 levels): 32 frames from its position into the bus X:$4B18 (x its level); at its length, a loop goes back to
     frame 0, a once stops (state 0); the recording's head (overdub) keeps its starting position in X:RC + 6;
  3. the recording: replace = the 32 frames at its position (up to the limit: then off), the head's length = the position; overdub = from the
     head's starting position (wrapping at its length) old x feedback + new.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

BUF0, PAGES = 0xD87000, 158
CAP = PAGES * 4096 // 2                                  # frames per head
STEP = PAGES * 4096                                      # words between two heads' buffers
assert BUF0 + 4 * STEP == 0xFFF000
HD, RC, KEY, TMP = 0x51A0, 0x51C0, 0x51C8, 0x4D90        # core 0 X (free: after drybus's DKEY $5188; $4D83-$4DFF after synth0's Q2)
LKEY = 0x10C9E4
BUS, INB = 0x4B18, 0x30710
N_HEADS = 4


def items():
    """the looper's body: called with jsr (r0-r5, a, b, x0, x1, y0, y1, n0-n5 free to use: drybus saves them); ends with rts"""
    hd = lambda h, k: f"x:>${HD + 8 * h + k:x}"                           # noqa: E731
    L = [("label", "loop"),
         f"move x:>${KEY:x},a", f"move #>${LKEY:x},x0", "cmp x0,a", ("jcc", "ne", "lp_x"),
         # 1. the recording's source to TMP
         f"move x:>${RC:x},a", "tst a", ("jcc", "eq", "lp_play"),
         f"move #>${TMP:x},r1", f"move x:>${RC + 2:x},a", "tst a", ("jcc", "ne", "lp_mix"),
         f"move #>${INB:x},r0", "nop", "do #$40,${lp_ci:x}", "move y:(r0)+,x0", "move x0,x:(r1)+", ("label", "lp_ci"), ("jmp", "lp_play"),
         ("label", "lp_mix"),
         f"move #>${BUS:x},r0", "nop", "do #$40,${lp_cm:x}", "move x:(r0)+,x0", "move x0,x:(r1)+", ("label", "lp_cm"),
         ("label", "lp_play")]
    # 2. the heads (r4 = the head's control block; b = frames left this block; r1 = the buffer; r0 = the bus)
    L += ["move #>$8,n4", f"move #>${HD:x},r4", "move #>$4,r2",                    # (a counted loop, not a do: two stack levels fewer)
          ("label", "lp_hl"),
          "move x:(r4),a", "tst a", ("jcc", "eq", "lp_hn"),
          "move x:(r4+$1),a", "tst a", ("jcc", "eq", "lp_hn"),
          ("jsr", "lp_head"),
          ("label", "lp_hn"), "move (r4)+n4", "move r2,a", "sub #$1,a", "move a,r2", ("jcc", "ne", "lp_hl")]
    # 3. the recording
    L += [f"move x:>${RC:x},a", "tst a", ("jcc", "eq", "lp_x"),
          f"move x:>${RC + 1:x},a", f"move #>${HD:x},r4", "asl #3,a,a", "move a1,n4", "nop", "move (r4)+n4",           # r4 = its head
          f"move x:>${RC + 3:x},a", "tst a", ("jcc", "ne", "lp_ovd"),
          # replace: frames at RC + 5 (up to CAP)
          f"move x:>${RC + 5:x},a", f"move x:>${RC + 7:x},b", "sub #$20,b", "cmp b,a", ("jcc", "gt", "lp_rend"),       # the limit (<= CAP)
          ("jsr", "lp_addr"), f"move #>${TMP:x},r0", "nop",
          "do #$40,${lp_rw:x}", "move x:(r0)+,x0", "move x0,y:(r1)+", ("label", "lp_rw"),
          f"move x:>${RC + 5:x},a", "add #$20,a", f"move a,x:>${RC + 5:x}", "move a,x:(r4+$1)", ("jmp", "lp_x"),
          ("label", "lp_rend"), "clr a", f"move a,x:>${RC:x}", ("jmp", "lp_x"),
          # overdub: from the head's starting position, wrapping at its length: old x feedback + new
          ("label", "lp_ovd"), "move x:(r4+$1),a", "tst a", ("jcc", "eq", "lp_x"),
          f"move x:>${RC + 6:x},a", ("jsr", "lp_addr"), f"move #>${TMP:x},r0",
          f"move x:>${RC + 4:x},y1", "move x:(r4+$1),b", f"move x:>${RC + 6:x},a", "sub a,b",                        # b = frames to the end
          "do #$20,${lp_ow:x}",
          "move y:(r1),x0", "mpy x0,y1,a", "move x:(r0)+,x0", "add x0,a", "move a,y:(r1)+",
          "move y:(r1),x0", "mpy x0,y1,a", "move x:(r0)+,x0", "add x0,a", "move a,y:(r1)+",
          "sub #$1,b", ("jcc", "ne", "lp_on"),
          "move x:(r4+$1),b", "clr a", ("jsr", "lp_addr"),
          ("label", "lp_on"), "nop",
          ("label", "lp_ow"),
          ("label", "lp_x"), "rts"]
    # lp_head (r4 = the head): its frames into the bus; the recording's head keeps its starting position (RC + 6)
    L += [("label", "lp_head"),
          f"move x:>${RC + 1:x},a", "move r4,b", f"move #>${HD:x},x0", "sub x0,b", "asr #3,b,b", "cmp b,a", ("jcc", "ne", "lh_0"),
          "move x:(r4+$2),a", f"move a,x:>${RC + 6:x}",
          ("label", "lh_0"),
          "move x:(r4+$2),a", ("jsr", "lp_addr"), f"move #>${BUS:x},r0", "move x:(r4+$3),y1",
          "move x:(r4+$1),b", "move x:(r4+$2),a", "sub a,b",                                                     # b = frames to the end
          "do #$20,${lh_e:x}",
          "move y:(r1)+,x0", "move x:(r0),a", "mac x0,y1,a", "move a,x:(r0)+",
          "move y:(r1)+,x0", "move x:(r0),a", "mac x0,y1,a", "move a,x:(r0)+",
          "sub #$1,b", ("jcc", "ne", "lh_n"),
          "move x:(r4),a", "move #>$2,x0", "cmp x0,a", ("jcc", "eq", "lh_w"),
          "clr a", "move a,x:(r4)", "enddo", ("jmp", "lh_e"),                                                   # once: stops
          ("label", "lh_w"), "move x:(r4+$1),b", "clr a", ("jsr", "lp_addr"),                                     # loop: frame 0
          ("label", "lh_n"), "nop",
          ("label", "lh_e"),
          "move x:(r4+$1),b", "move x:(r4+$2),a", "add #$20,a", "cmp b,a", ("jcc", "lt", "lh_s"), "sub b,a",
          ("label", "lh_s"), "move a,x:(r4+$2)", "rts"]
    # lp_addr (a = a frame, r4 = its head) -> r1 = its address in the buffer: BASE + h STEP + 2 frame (a, x0, x1 used)
    L += [("label", "lp_addr"),
          "asl a", "move a1,x1", "move r4,a", f"move #>${HD:x},x0", "sub x0,a", "asr #3,a,a",
          f"move a1,x0", f"move #>${STEP:x},a", "move a1,y0", "mpy x0,y0,a", "asr a", "move a0,a",
          f"add #>${BUF0:x},a", "add x1,a", "move a1,r1", "nop", "rts"]
    return L
