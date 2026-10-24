"""WSOLA for the stretch of the Circuit Rhythm 5706's DSP core 1 (MIT; RD13, tools/stretch.py v5): when a grain starts again, it starts
where the sample best matches what the other grain is about to play, not exactly at the playhead.  RD12 on the device: two grains out of
phase gave «a metallic ringy sound» on drum loops and «a bit wobbly» pads.

Where (RD12 on the device, docs/PRUEBA_RD12.md): core 1 has no P memory above $FFF; P:$46..$FF (unused interrupt vectors, never loaded by
the stock) are free; P:$44 is the host vector (jsr $6D0).  The loader reads {type, count, address, words}; the stock's block sender
0x080310B0 sends a block's two header words and then as many words as the low 16 bits of its first word.  So the segment goes in three
blocks (tools/rhdsp1.py low): [0 (P), k] (no more words), [$46, w0 .. w70] (the address: $46 + 1 words), [w71, w72, then w71's low 16 bits
of words].  w71 = P:$8D is a data word that never runs (after an rts and nop padding): its low 16 bits = k - 73.

The search (WS, called by GRN in place of «R = P + A0» when a grain's phase comes back to 0):
  * the plain start S0 = P + A0 (the playhead); at most one search per block for the 8 voices (Y:WS_BLK against dspload's block counter),
    none near the sample's ends (P < 128, P + 189 past the length, the other grain's reference past the end): then S0, as RD12;
  * the reference: 32 samples, every second one, from where the other grain reads now (its stored position moved to this sample: + i x r
    when this is grain 0, processed first; - (32 - i) x r when this is grain 1, whose block is already done);
  * the candidates: 158 samples, every second one, from S0 - 128: 64 starts 4 samples apart (S0 - 128 .. S0 + 124), each scored by the
    sum of its 32 products with the reference (cross-correlation);
  * the grain starts at the best, with the fraction of the other grain's position (both then read the same waveform in step).
Cost: 190 fetches through the page table and 2 048 multiply-adds, about 7 000 cycles, in at most one block of every 32 per voice pair
(RD12 measured ~19 000 cycles a block still free with stretch + ring + comb + bitcrush on the 8 voices).
Y scratch $1410.. (REF 32, CAND 158, words): Y:$140C..$15FF are free (docs/PORTADO.md «Presupuesto de recursos»), cleared at the start.
Registers: a, b, x0, x1, r3, n3, r5, n5, r7 (saved); keeps r1, r2, r4, r6, n2, Y; n3 = $FFFFFF (no page) when it searched.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import voicefx as V  # noqa: E402

AT, END = 0x46, 0x100
CW = 2 * AT + 1                                           # P:$8D, the count word (never runs)
REF, CAND = 0x1410, 0x1430
NR, NC, D0 = 32, 158, 128
NCAND = 64
V1 = dict(nr=NR, stride=2, nc=NC, d0=D0, ncand=NCAND, cstep=2, gap=0)
# v2 (RD14; RD13 on the device hung core 1 with the stretch on 7-8 tracks: a search almost every block, each ~190 reads of the external
# sample memory): a 16-sample reference and 48 starts 4 apart (S0 - 96 .. S0 + 92), every fourth sample (~80 reads, 768 multiply-adds),
# and at most one search every 4 blocks for the 8 voices
V2 = dict(nr=16, stride=4, nc=48 + 16 - 1, d0=96, ncand=48, cstep=1, gap=4)
# v3 (RD15; RD14 on the device: with the stretch on 6-8 tracks of a light pattern the blocks fell below 1 500/s, then core 1 hung, its host
# port echoing): the same search, off unless the host says (Y:WS_NG = the gap in blocks XOR $7FFFFF: 0 at the start = a gap of $7FFFFF, no
# search; tools/rhvfx.py wsola GAP), to find on the device whether a search hangs it or their rate does
V3 = dict(V2, gap="host")
WS_NG = 0x1526
# v4 (RD16; RD15 on the device: one search every 150 blocks hung core 1 within a second; the cause is the hardware stack: the stock's voice
# loop leaves one level per voice (P:$242 jsr $6AB, which ends in bra $234), so the stretch of voice v starts 2 + v levels down and a search
# from inside GRN's do loop overflowed the 16 levels on the high tracks): WSB, from the main loop (dspload's block hook at P:$128, after the
# block's acknowledgement, about 1 level down): it scans the 8 voices for the first active, stretched one whose grain starts again in the
# next block, searches as v2, and leaves the start in that grain's word + 5 (its fraction in Y:RONF); GRN takes it when the grain starts
# again (stretch v6).  At most one search a block; no gap word.
V4 = dict(V2, gap=0, block=True)
PEND = 5                                                  # (v4) a grain's word + 5: the start WSB found for it (0 = none)
S0, RON, RONF, BEST, WS_BLK, SV_R7 = 0x1520, 0x1521, 0x1522, 0x1523, 0x1524, 0x1525


def chunks(st, v=V1):
    """[(name, items)], each ending in an rts (so the count word can follow one)"""
    if v.get("block"):
        return chunks4(st, v)
    trp = [("label", "trp"), "move x0,n3", "move x0,b", "lsr b", f"move y:>${st['T_TAB']:x},x1", "add x1,b", "move b1,r3", "nop",
           "move y:(r3),b", "btst #0,x0", ("jcc", "cs", "tp_lo"), "lsr #12,b", ("jmp", "tp_pg"), ("label", "tp_lo"), "and #>$fff,b",
           ("label", "tp_pg"), "asl #12,b,b", "move b1,r3", "rts"]
    # COPY: n5 samples, every second one, from the sample's address a1 to Y:(r7)+ (uses b, x0, x1, r3, n3, r5)
    copy = [("label", "copy"), "move #>$ffffff,n3", ("doa", "do n5", "cp_e"),
            "tfr a,b", "lsr #12,b", "move b1,x0", "move n3,b", "cmp x0,b", ("jcc", "eq", "cp_g"), ("jsr", "trp"),
            ("label", "cp_g"), "move a1,b", "and #>$fff,b", "move r3,x0", "add x0,b", "move b1,r5", "nop", "move y:(r5),b",
            "move b,y:(r7)+", f"add #${v['stride']:x},a", ("label", "cp_e"), "rts"]
    # CORR: n5 candidates from Y:(r3), n3 apart, each against the 32 of REF -> Y:BEST = the best one's address
    corr = [("label", "corr"), "move #>$800000,b", "asl #5,b,b", ("doa", "do n5", "co_e"),                     # best = -32
            "move r3,r5", f"move #>${REF:x},r7", "clr a", "move y:(r5)+,x1", ("doa", f"do #${v['nr']:x}", "ci_e"),
            "move y:(r7)+,x0", "mac x1,x0,a y:(r5)+,x1", ("label", "ci_e"),
            "cmp b,a", ("jcc", "le", "co_n"), "tfr a,b", f"move r3,y:>${BEST:x}", ("label", "co_n"), "move (r3)+n3", ("label", "co_e"),
            "rts"]
    ws = [("label", "ws"), "move y:(r6),a", "move y:(r6+$1),a0", f"move y:>${st['T_A0']:x},x0", "add x0,a",                  # S0
          *((f"move y:>${WS_BLK:x},x0", f"move y:>${st['BLOCKS']:x},b", "cmp x0,b", ("jcc", "eq", "ws_r")) if not v["gap"] else
            ((f"move y:>${st['BLOCKS']:x},b", f"move y:>${WS_BLK:x},x0", "sub x0,b", "move b1,b", f"cmp #${v['gap']:x},b",  # (24-bit wrap)
              ("jcc", "lt", "ws_r")) if v["gap"] != "host" else
             (f"move y:>${WS_NG:x},b", "eor #>$7fffff,b", "move b1,x1",                                        # x1 = the gap
              f"move y:>${st['BLOCKS']:x},b", f"move y:>${WS_BLK:x},x0", "sub x0,b", "move b1,b", "cmp x1,b",
              ("jcc", "lt", "ws_r")))),
          "move y:(r6),b", f"cmp #>${v['d0']:x},b", ("jcc", "lt", "ws_r"),
          f"add #>${(2 * NC - D0 + 2) if v is V1 else (v['stride'] * v['nc'] - v['d0'] + 2):x},b", f"move y:>${st['T_LEN']:x},x0", "cmp x0,b", ("jcc", "gt", "ws_r"),
          "move r6,b", "asl b", f"add #${st['G0'] + st['G1']:x},b", "move r2,x0", "sub x0,b", "move b1,r5",  # r5 = the other grain (2 r6 + G0 + G1 - r2)
          "move r1,b", f"sub #>${st['BUF'] - 1:x},b", "move b1,x1",                                          # x1 = i + 1
          # the other grain's position now: grain 0 (processed first) + i x r; grain 1 - (32 - i) x r = - 33 r + (i + 1) r
          "move r2,b", "move r6,x0", "sub x0,b", f"cmp #${st['G0']:x},b",
          "move y:(r5),b", "move y:(r5+$1),b0", ("jcc", "eq", "ws_0"),                                       # (moves keep the CCR)
          "rep #$20", "sub y,b",
          ("label", "ws_0"), "sub y,b", "rep x1", "add y,b",
          ("label", "ws_c"), f"move b1,y:>${RON:x}", f"move b0,y:>${RONF:x}",
          f"add #>${v['stride'] * v['nr'] if v is not V1 else 2 * NR:x},b", f"move y:>${st['T_END']:x},x0", "cmp x0,b", ("jcc", "gt", "ws_r"),
          f"move y:>${st['BLOCKS']:x},x0", f"move x0,y:>${WS_BLK:x}", f"move a1,y:>${S0:x}", f"move r7,y:>${SV_R7:x}",
          f"move y:>${RON:x},a", f"move #>${REF:x},r7", f"move #${v['nr']:x},n5", ("jsr", "copy"),
          f"move y:>${S0:x},a", f"sub #>${v['d0']:x},a", f"move #>${CAND:x},r7", f"move #${v['nc']:x},n5", ("jsr", "copy"),
          f"move #>${CAND:x},r3", f"move #${v['cstep']:x},n3", f"move #${v['ncand']:x},n5", ("jsr", "corr"),
          f"move y:>${BEST:x},a", f"sub #>${CAND:x},a", "asl a" if v["stride"] == 2 else "asl #2,a,a",            # S0 - d0 + stride t
          f"move y:>${S0:x},x0", "add x0,a", f"sub #>${v['d0']:x},a",
          f"move y:>${RONF:x},a0", f"move y:>${SV_R7:x},r7", "move #>$ffffff,n3",
          ("label", "ws_r"), "rts"]
    return [("trp", trp), ("copy", copy), ("corr", corr), ("ws", ws)]


def chunks4(st, v):
    """v4: COPY as v2; TRP without branches (an odd page: its 12 bits moved up first, then down); CORR inside WSB; WSB from the main loop
    (registers free there: the main loop loads its own).  -> [(name, items)]; WSB's no-candidate rts is where the count word may go."""
    ch = dict(chunks(st, dict(v, block=False)))
    d0, nr, nc, ncand = v["d0"], v["nr"], v["nc"], v["ncand"]
    trp = [("label", "trp"), "move x0,n3", "move x0,b", "lsr b", f"move y:>${st['T_TAB']:x},x1", "add x1,b", "move b1,r3", "nop",
           "move y:(r3),b", "btst #0,x0", ("jcc", "cc", "tp_e"), "lsl #12,b", ("label", "tp_e"), "lsr #12,b",
           "asl #12,b,b", "move b1,r3", "rts"]
    ST, G0, G1 = st["ST"], st["G0"], st["G1"]
    head = [("label", "wsb"),
            f"move y:>${st['GHM']:x},y0",                                               # G / 2 - 1 (from the host, with the grain)
            f"move #>${ST:x},r6", "move #>$40,r4",
            ("doa", "do #$8", "w_le"),
            "move x:(r4+$4),b", "tst b", ("jcc", "eq", "w_n"),                   # the voice plays (X:$44 + 16 v, as the stock's $235)
            f"move y:(r6+${st['INIT']:x}),b", "tst b", ("jcc", "eq", "w_n"),       # stretched since its note (STR set INIT)
            f"move y:(r6+${G0 + 4:x}),b", "neg b", "move b1,x0", "and y0,b", "move b1,b", "cmp #$20,b",       # (b2 kept the sign)
            ("jcc", "lt", "w_go"),                                                 # a grain starts next block
            ("label", "w_n"), "lua (r6+$10),r6", "lua (r4+$10),r4",
            ("label", "w_le"),
            ("label", "w_x"), "rts"]
    body = [("label", "w_go"), "enddo", "add #$1,b", "move b1,x1",              # x1 = i + 1 (i: the grain's sample in the next block)
            f"move y:>${st['GMASK']:x},b", "and x0,b", "cmp #$20,b",                # grain 0 if its own distance is under 32
            f"lua (r6+${G0:x}),r2", f"lua (r6+${G1:x}),r5", ("jcc", "lt", "w_s"),
            f"lua (r6+${G1:x}),r2", f"lua (r6+${G0:x}),r5",                         # grain 1 (r2 = it, r5 = the other)
            ("label", "w_s"),
            "move y:(r6+$f),x0", f"move x0,y:>${st['T_TAB']:x}",                   # its page table (STR keeps it in word + 15)
            "clr b", "move y:(r4),b1", "asr #15,b,b", "move b1,y1", "move b0,y0",    # Y = r
            "move y:(r4+$3),x0",                                                    # x0 = the length
            "move y:(r6),b", f"cmp #>${d0:x},b", ("jcc", "lt", "w_x"),
            f"add #>${v['stride'] * nc - d0 + 2:x},b", "cmp x0,b", ("jcc", "gt", "w_x"),
            "move y:(r5),b", "move y:(r5+$1),b0", "sub y,b", "rep x1", "add y,b",   # the other grain at sample i
            f"move b1,y:>${RON:x}", f"move b0,y:>${RONF:x}",
            "move y:(r4+$4),y1", "sub y1,b", f"add #>${v['stride'] * nr + 1:x},b", "cmp x0,b", ("jcc", "gt", "w_x"),
            "move y:(r6),a", "move y:(r6+$1),a0", "move y:(r4+$4),x0", "add x0,a", f"move a1,y:>${S0:x}",   # S0 = P + A0
            f"move y:>${RON:x},a", f"move #>${REF:x},r7", f"move #${nr:x},n5", ("jsr", "copy"),
            f"move y:>${S0:x},a", f"sub #>${d0:x},a", f"move #>${CAND:x},r7", f"move #${nc:x},n5", ("jsr", "copy"),
            # CORR (inline): 48 starts from CAND, each against the 16 of REF -> r? the best's address in Y:BEST
            f"move #>${CAND:x},r3", "move #>$800000,b", "asl #5,b,b", ("doa", f"do #${ncand:x}", "co_e"),
            "move r3,r5", f"move #>${REF:x},r7", "clr a", "move y:(r5)+,x1", ("doa", f"do #${nr:x}", "ci_e"),
            "move y:(r7)+,x0", "mac x1,x0,a y:(r5)+,x1", ("label", "ci_e"),
            "cmp b,a", ("jcc", "le", "co_n"), "tfr a,b", f"move r3,y:>${BEST:x}", ("label", "co_n"), "move (r3)+", ("label", "co_e"),
            f"move y:>${BEST:x},a", f"sub #>${CAND:x},a", "asl #2,a,a", f"move y:>${S0:x},x0", "add x0,a", f"sub #>${d0:x},a",
            f"move a1,y:(r2+${PEND:x})", "rts"]
    return [("trp", trp), ("copy", ch["copy"]), ("wsb_head", head), ("wsb", body)]


def layout(st, v=V1):
    """-> the items for P:AT..: the chunks that fit before the count word, nop padding, the count word (0 for now), the rest"""
    ch = chunks(st, v)
    size = lambda its: len(V.assemble(its, AT)[0]) if its else 0      # noqa: E731 (labels of other chunks: assembled whole below)
    first, rest, used = [], [], 0
    for name, its in ch:
        n = len(V.assemble(its + [("label", x) for x in ("trp", "copy", "corr", "ws", "ws_r", "wsb", "w_go", "w_x", "w_s")
                                  if not any(i == ("label", x) for i in its)], AT)[0])
        if not rest and used + n <= CW - AT:
            first += its
            used += n
        else:
            rest += its
    pad = CW - AT - used
    return first + ["nop"] * pad + [("words", [0])] + rest, pad


def code(st, v=V1):
    """-> (the words for P:AT.., labels, the count word's index)"""
    items, pad = layout(st, v)
    w, labels = V.assemble(items, AT)
    assert AT + len(w) <= END, f"WSOLA: {len(w)} words from ${AT:x}, past ${END - 1:x}"
    k = len(w)
    ci = CW - AT
    assert w[ci] == 0
    w[ci] = k - AT - 3                                     # the third block's length (see above)
    return w, labels, ci
