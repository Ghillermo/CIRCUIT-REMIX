"""The stereo recording's split, on the Circuit Rhythm 5706's DSP core 0 (MIT; tools/stereorec.py, «Sample Rec del Rhythm» in docs/PORTADO.md).

A stereo recording leaves slot A with 2N words L0 R0 L1 R1.. (core 1's write, tools/stereorec.py).  After core 1 has normalized it, the ARM
gives core 0 a job (Y:JOB..): core 0 moves the odd words into slot B and packs the even ones at the start of A, in the DSP's memory, a
piece a block, so the stock's writer saves two plain mono slots and nothing has to be uploaded again (RD23's first version uploaded A and B
from their files: new sample memory each time, from the LED task: on the device both came out empty and the unit hung).

The samples' memory, as core 1 keeps it (P:$B83 takes a page, P:$8F2 gives a slot's pages back; read in core 1's program):
  * a slot's entry X / Y:$30000 + 4n (+ 1 / + 2 = its words, + 3 = the words normalized), its page table Y:$308C8 + n x $BC (two 12-bit
    page numbers a word: the even page in the high half), its page count Y:$366C8 + n; a page = 4 096 words at page << 12;
  * the free pages: a ring of their addresses Y:$36748 + i ($A87 places), the head index Y:$371CF and its address Y:$371D0, the count
    Y:$371D1, and Y:$371D2 = the head's address (0 with none: the uploads start there).
Ours, from the hook at P:$224 (SPL ahead of granular0's GR, which goes on to the stock's mix), only while Y:JOB = JKEY (the ARM writes the
job's words, then JOB; power-up garbage is never JKEY):
  * init: N = A's words / 2; B's first page = one free page of the ring, taken as P:$B83 takes it; with none (the stereo recording used
    up the memory, the user's case on RD23 v3) A's last page instead, and N cut to the frames before it (at most 2 048 lost, 43 ms);
  * then STEP (128) frames a block, A's pages in pairs: pair m (frames 4 096 m ..) = A's pages 2m and 2m + 1, 2 048 frames L R each;
    its L into page 2m (every position written is already read), its R into B's page m = the first page (m = 0) or A's page 2m - 1
    (the pair before's second page, read through by then).  So the split needs one free page in all, not as many as B takes (RD23 v3
    asked the ring for all of them and made no B when memory was short).  The page table stays the old one until the end;
  * the end, a stage a block (each <= ~6 400 instructions for a full slot): B's table (as P:$B83 fills one) and count; A's pages nobody
    keeps back into the ring (as P:$8F2 gives them); A's table = its pages 0, 2, 4.. and the entries of A (and B) = N words, all
    normalized; RES = 1 (B made) / 2 (A alone: B was not empty, or one page and no free one) / 3 (nothing recorded), JOB = 0.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core0 as C0  # noqa: E402

AT = 0x2600                                            # our P (after granular0's 1 314 words from P:$2000)
HOOK = 0x224                                           # granular0's `jsr GR` there becomes `jsr SPL`
Y0 = 0x1F00                                            # core 0 Y (no absolute operand of the stock there: docs/RECURSOS.md)
(JOB, PTA, PTB, EA, EB, CA, CB, RES, S, NW, IW, PA, QA, SCR, DROP) = range(Y0, Y0 + 15)
SV = Y0 + 0x10                                         # r0, r1, r2, r4, then m0, m1, m2, m4
M2, FW = Y0 + 0x18, Y0 + 0x19                          # s_cp's 2m and f
JKEY = 0x5A71E5
STEP = 0x80                                            # frames a block (RD23 v2 had 1 024: about 4 096 sample-memory accesses a block, too many for core 0 on the device)
SMP, PAGES, PSTRIDE, COUNTS = 0x30000, 0x308C8, 0xBC, 0x366C8
RING, RLEN, R_HEAD, R_HADDR, R_FREE, R_NEXT = 0x36748, 0xA87, 0x371CF, 0x371D0, 0x371D1, 0x371D2
REGS = (0, 1, 2, 4)


def items(gr):
    L = []

    def e(*s):
        L.extend(s)

    # ---- SPL: from P:$224; the step only with a job, then granular0's GR (which ends in the stock's mix)
    e(("label", "spl"), f"move y:>${JOB:x},a", f"move #>${JKEY:x},x0", "cmp x0,a", ("jcc", "ne", gr),
      ("jsr", "s_step"), ("jmp", gr))
    # ---- s_step: our registers saved, m linear; the state's step; restored
    e(("label", "s_step"))
    for i, k in enumerate(REGS):
        e(f"move r{k},y:>${SV + i:x}", ("words", [0x057060 | k, SV + 4 + i]), ("words", [0x05F420 | k, 0xFFFFFF]))
    e(f"move y:>${S:x},a", "tst a", ("jcc", "eq", "s_init"),
      "move #>$1,x0", "cmp x0,a", ("jcc", "eq", "s_copy"),
      "move #>$2,x0", "cmp x0,a", ("jcc", "eq", "s_d2"),
      "move #>$3,x0", "cmp x0,a", ("jcc", "eq", "s_d3"),
      ("jsr", "s_et"), ("jmp", "s_out"),                                 # the end, a stage a block: 2 B's table, 3 the pages back, 4 A's
      ("label", "s_d2"), ("jsr", "s_end"), ("jmp", "s_out"),
      ("label", "s_d3"), ("jsr", "s_ef"), ("jmp", "s_out"),
      ("label", "s_init"), ("jsr", "s_go"), ("jmp", "s_out"),
      ("label", "s_copy"), ("jsr", "s_cp"))
    e(("label", "s_out"))
    for i, k in enumerate(REGS):
        e(f"move y:>${SV + i:x},r{k}", ("words", [0x05F060 | k, SV + 4 + i]))
    e("rts")

    # ---- s_pg: x1 = a page table, x0 = a page index -> a1 = the page's address (a2 = a0 = 0); r4 = the table's word; clobbers b
    e(("label", "s_pg"),
      "clr a", "move x0,a1", "asr #$1,a,a", "clr b", "move x1,b1", "add a,b", "move b1,r4", "clr a", "btst #$0,x0",
      "move y:(r4),a1", ("jcc", "cs", "s_pgo"),                         # (moves keep the C of the btst: k odd)
      "and #>$fff000,a", "rts",
      ("label", "s_pgo"), "and #>$fff,a", "asl #$c,a,a", "rts")

    # ---- s_go: the job's start.  B's first page (the spare one): a free page of the ring, as P:$B83 takes it; none (the recording used
    #      all the memory) -> A's last page, its frames dropped (at most 2 048, the end of the recording)
    e(("label", "s_go"),
      f"move y:>${EA:x},r4", "nop", "move (r4)+", "move (r4)+", "clr a", "nop", "move y:(r4),a1",   # A's words
      "tst a", ("jcc", "ne", "s_g1"),
      "move #>$3,x0", f"move x0,y:>${RES:x}", ("jmp", "s_fin"),
      ("label", "s_g1"),
      "asr #$1,a,a", f"move a1,y:>${NW:x}",                                 # N
      f"move y:>${CA:x},r4", "nop", "nop", "move y:(r4),x0", f"move x0,y:>${QA:x}",
      "clr a", f"move a1,y:>${DROP:x}",
      f"move y:>${PTB:x},a", "tst a", ("jcc", "eq", "s_g9"),
      f"move y:>${CB:x},r4", "nop", "nop", "clr a", "move y:(r4),a1", "tst a", ("jcc", "ne", "s_gnb"),   # B not empty: A alone
      f"move y:>${R_FREE:x},a", "tst a", ("jcc", "eq", "s_g0"),
      # a free page: the head's address, the head on, the count down, the next head's address (as P:$B83)
      f"move y:>${R_HADDR:x},r4", "nop", "nop", "clr a", "move y:(r4),a1", f"move a1,y:>${SCR:x}",
      f"move y:>${R_HEAD:x},a", "add #>$1,a", f"move #>${RLEN:x},x1", "cmp x1,a", ("jcc", "lt", "s_gw"), "clr a",
      ("label", "s_gw"), f"move a1,y:>${R_HEAD:x}", f"add #>${RING:x},a", f"move a1,y:>${R_HADDR:x}",
      f"move y:>${R_FREE:x},a", "sub #>$1,a", f"move a1,y:>${R_FREE:x}", "tst a", ("jcc", "eq", "s_gn0"),
      f"move y:>${R_HADDR:x},r4", "nop", "nop", "move y:(r4),x0", f"move x0,y:>${R_NEXT:x}", ("jmp", "s_g9"),
      ("label", "s_gn0"), f"move a1,y:>${R_NEXT:x}", ("jmp", "s_g9"),
      # no free page: A's last page is B's first; N = at most the frames of the pages before it
      ("label", "s_g0"),
      f"move y:>${QA:x},a", "move #>$2,x0", "cmp x0,a", ("jcc", "lt", "s_gnb"),
      "sub #>$1,a", "move a1,x0", f"move y:>${PTA:x},x1", ("jsr", "s_pg"), f"move a1,y:>${SCR:x}",
      "move #>$1,x0", f"move x0,y:>${DROP:x}",
      f"move y:>${QA:x},a", "sub #>$1,a", "asl #$b,a,a", f"move y:>${NW:x},x0", "cmp x0,a", ("jcc", "ge", "s_g9"),
      f"move a1,y:>${NW:x}", ("jmp", "s_g9"),
      ("label", "s_gnb"), "clr a", f"move a1,y:>${PTB:x}",                 # A alone
      ("label", "s_g9"),
      f"move y:>${NW:x},a", "move #>$fff,x0", "add x0,a", "asr #$c,a,a", f"move a1,y:>${PA:x}",   # PA = (N + 4095) >> 12
      "clr a", f"move a1,y:>${IW:x}", "move #>$1,x0", f"move x0,y:>${S:x}", "rts")

    # ---- s_cp: one piece of STEP frames (fewer at the end).  A's pages go in pairs: pair m (frames 4 096 m ..) = A's pages 2m, 2m + 1
    #      (each holds 2 048 frames L R); its L into page 2m (positions already read), its R into B's page m = the spare page (m = 0) or
    #      A's page 2m - 1 (the pair before's second page, read through by then).  The page table is the old one until the end.
    e(("label", "s_cp"),
      f"move y:>${NW:x},a", f"move y:>${IW:x},x0", "sub x0,a", f"move #>${STEP:x},x1", "cmp x1,a", ("jcc", "lt", "s_ck"),
      "move x1,a",
      ("label", "s_ck"), "move a1,y1",                                    # y1 = K
      f"move y:>${IW:x},a", "move a1,y0",                                 # y0 = i
      "move y0,b", "and #>$fff,b", f"move b1,y:>${FW:x}",                  # f = i mod 4 096
      "clr a", "move y0,a1", "asr #$c,a,a", "clr b", "move a1,b1", "asl #$1,b,b", f"move b1,y:>${M2:x}",   # 2m
      # r1 = A's page 2m + f (L)
      f"move y:>${M2:x},x0", f"move y:>${PTA:x},x1", ("jsr", "s_pg"), f"move y:>${FW:x},x0", "add x0,a", "move a1,r1",
      # r0 = A's page 2m + f / 2 048, + 2 (f mod 2 048)
      "clr a", f"move y:>${FW:x},a1", "asr #$b,a,a", "move a1,x0", "clr a", f"move y:>${M2:x},a1", "add x0,a", "move a1,x0",
      f"move y:>${PTA:x},x1", ("jsr", "s_pg"),
      "clr b", f"move y:>${FW:x},b1", "and #>$7ff,b", "asl #$1,b,b", "move b1,x0", "add x0,a", "move a1,r0",
      f"move y:>${PTB:x},a", "tst a", ("jcc", "eq", "s_c1"),
      # r2 = B's page m + f (R): the spare page for m = 0, else A's page 2m - 1
      f"move y:>${M2:x},a", "tst a", ("jcc", "ne", "s_c5"),
      "clr a", f"move y:>${SCR:x},a1", ("jmp", "s_c6"),
      ("label", "s_c5"), "sub #>$1,a", "move a1,x0", f"move y:>${PTA:x},x1", ("jsr", "s_pg"),
      ("label", "s_c6"), f"move y:>${FW:x},x0", "add x0,a", "move a1,r2", "nop",
      f"do y1,${{s_c2:x}}",
      "move y:(r0)+,a", "move y:(r0)+,b", "move a,y:(r1)+", "move b,y:(r2)+",
      ("label", "s_c2"), ("jmp", "s_c3"),
      ("label", "s_c1"), "nop",
      f"do y1,${{s_c4:x}}",
      "move y:(r0)+,a", "move y:(r0)+,b", "move a,y:(r1)+",
      ("label", "s_c4"),
      ("label", "s_c3"),
      f"move y:>${IW:x},a", "move y1,x0", "add x0,a", f"move a1,y:>${IW:x}",
      f"move y:>${NW:x},x0", "cmp x0,a", ("jcc", "lt", "s_cx"),
      "move #>$2,x0", f"move x0,y:>${S:x}",
      ("label", "s_cx"), "rts")

    # ---- s_end: 1) B's table (as P:$B83 fills it) and count; 2) A's pages nobody keeps back into the ring (as P:$8F2 gives them);
    #      3) A's table = its pages 0, 2, 4.. (read from the old table before each word is written over); 4) the count, entries, result
    e(("label", "s_end"),
      f"move y:>${PTB:x},a", "tst a", ("jcc", "eq", "s_e2x"),
      f"move y:>${PTB:x},r2", "move #>$0,r1", f"move y:>${PA:x},x0", "nop",
      f"do x0,${{s_eb:x}}",
      "move r1,b", "tst b", ("jcc", "ne", "s_eb1"),
      "clr a", f"move y:>${SCR:x},a1", ("jmp", "s_eb2"),
      ("label", "s_eb1"), "clr a", "move r1,a1", "asl #$1,a,a", "sub #>$1,a", "move a1,x0", f"move y:>${PTA:x},x1", ("jsr", "s_pg"),
      ("label", "s_eb2"),
      "move r1,b", "btst #$0,b1", ("jcc", "cs", "s_ebo"),
      "move a1,y:(r2)", ("jmp", "s_ebn"),                                  # even: the word = the address
      ("label", "s_ebo"),
      "asr #$c,a,a", "and #>$fff,a", "move a1,x1", "clr b", "move y:(r2),b1", "or x1,b", "move b1,y:(r2)+",
      ("label", "s_ebn"), "move (r1)+", "nop",
      ("label", "s_eb"),
      f"move y:>${CB:x},r4", f"move y:>${PA:x},x0", "nop", "move x0,y:(r4)",
      ("label", "s_e2x"), "move #>$3,x0", f"move x0,y:>${S:x}", "rts",
      # 2) old pages k = 0 .. QA - 1: kept = k even and k / 2 < PA (A), with B: k odd and (k + 1) / 2 < PA, or the spare page taken from A
      ("label", "s_ef"),
      f"move y:>${QA:x},a", "tst a", ("jcc", "eq", "s_e3x"),
      "move #>$0,r1", f"move y:>${QA:x},x0", "nop",
      f"do x0,${{s_fe:x}}",
      f"move y:>${DROP:x},a", "tst a", ("jcc", "eq", "s_f1"),
      "clr a", "move r1,a1", "add #>$1,a", f"move y:>${QA:x},x0", "cmp x0,a", ("jcc", "eq", "s_fn"),   # the spare page (k = QA - 1)
      ("label", "s_f1"),
      "move r1,b", "btst #$0,b1", ("jcc", "cs", "s_fo"),
      "clr a", "move r1,a1", "asr #$1,a,a", f"move y:>${PA:x},x0", "cmp x0,a", ("jcc", "lt", "s_fn"), ("jmp", "s_fd"),
      ("label", "s_fo"), f"move y:>${PTB:x},a", "tst a", ("jcc", "eq", "s_fd"),
      "clr a", "move r1,a1", "add #>$1,a", "asr #$1,a,a", f"move y:>${PA:x},x0", "cmp x0,a", ("jcc", "lt", "s_fn"),
      ("label", "s_fd"),
      "move r1,x0", f"move y:>${PTA:x},x1", ("jsr", "s_pg"), "tst a", ("jcc", "eq", "s_fn"),
      "move a1,y0",                                                       # the ring's tail: (head + count) mod RLEN
      f"move y:>${R_HEAD:x},a", f"move y:>${R_FREE:x},x0", "add x0,a", f"move #>${RLEN:x},x1", "cmp x1,a", ("jcc", "lt", "s_ft"),
      "sub x1,a",
      ("label", "s_ft"), f"add #>${RING:x},a", "move a1,r2", f"move y:>${R_FREE:x},a", "add #>$1,a", f"move a1,y:>${R_FREE:x}",
      "move y0,y:(r2)",
      ("label", "s_fn"), "move (r1)+", "nop",
      ("label", "s_fe"),
      ("label", "s_e3x"), "move #>$4,x0", f"move x0,y:>${S:x}", "rts",
      # 3) A's table: word w = page 4w << 12 | page 4w + 2 (if 2w + 1 < PA); the words after cleared up to the old count's
      ("label", "s_et"),
      f"move y:>${PTA:x},r2", "move #>$0,r1", f"move y:>${PA:x},a", "add #>$1,a", "asr #$1,a,a", "move a1,x0", "nop",
      f"do x0,${{s_te:x}}",
      "clr a", "move r1,a1", "asl #$2,a,a", "move a1,x0", f"move y:>${PTA:x},x1", ("jsr", "s_pg"), "move a1,y0",
      "clr a", "move r1,a1", "asl #$1,a,a", "add #>$1,a", f"move y:>${PA:x},x0", "cmp x0,a", ("jcc", "ge", "s_tz"),
      "clr a", "move r1,a1", "asl #$2,a,a", "add #>$2,a", "move a1,x0", f"move y:>${PTA:x},x1", ("jsr", "s_pg"),
      "asr #$c,a,a", "and #>$fff,a", ("jmp", "s_tw"),
      ("label", "s_tz"), "clr a",
      ("label", "s_tw"), "move a1,x0", "clr a", "move y0,a1", "or x0,a", "move a1,y:(r2)+", "move (r1)+", "nop",
      ("label", "s_te"),
      f"move y:>${QA:x},a", "add #>$1,a", "asr #$1,a,a", f"move y:>${PA:x},b", "add #>$1,b", "asr #$1,b,b", "move b1,x0", "sub x0,a",
      ("jcc", "le", "s_e2"),
      "move a1,x0", "clr a", "nop",
      f"do x0,${{s_tc:x}}", "move a1,y:(r2)+", ("label", "s_tc"),
      # 4) the counts, the entries, the result
      ("label", "s_e2"),
      f"move y:>${CA:x},r4", f"move y:>${PA:x},x0", "nop", "move x0,y:(r4)",
      f"move y:>${NW:x},x0", f"move y:>${EA:x},r4", "nop", "nop", "move (r4)+", "move x0,y:(r4)+", "move x0,y:(r4)+", "move x0,y:(r4)",
      "move #>$2,x1", f"move y:>${PTB:x},a", "tst a", ("jcc", "eq", "s_e3"),
      f"move y:>${EB:x},r4", "clr a", "nop", "move a1,y:(r4)+", "move x0,y:(r4)+", "move x0,y:(r4)+", "move x0,y:(r4)",
      "move #>$1,x1",
      ("label", "s_e3"), f"move x1,y:>${RES:x}",
      ("label", "s_fin"), "clr a", f"move a1,y:>${S:x}", f"move a1,y:>${JOB:x}", "rts")
    return L


def code(gr):
    """-> (the words at P:AT, labels)"""
    w, labels = C0.asm_at(items(gr), AT)
    assert AT + len(w) <= C0.LD, hex(AT + len(w))
    return w, labels


def segs(gr_labels):
    """for granular0's extra: our code at P:AT and P:$224 -> jsr SPL (after granular0's own `jsr GR` there: the loader writes it last)"""
    w, labels = code(gr_labels["gr"])
    return [(AT, w), (HOOK, [0x0BF080, labels["spl"]])]


def job_words(a, b):
    """the ARM's job for slots a (and b, or None): {Y address: word}, JOB last"""
    ws = {PTA: PAGES + a * PSTRIDE, PTB: PAGES + b * PSTRIDE if b is not None else 0, EA: SMP + 4 * a, EB: SMP + 4 * (b or 0),
          CA: COUNTS + a, CB: COUNTS + (b or 0), RES: 0, S: 0}
    return ws
