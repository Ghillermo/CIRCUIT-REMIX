"""Sample Rec in stereo: the two inputs L and R into two slots, with the same start and end (MIT; Circuit Rhythm 5706).  The user,
2026-10-25: «can we sample record L/R to separate samples (same start and end)?».  The stock's capture and save: «Sample Rec del Rhythm»
in docs/PORTADO.md.

The stock records one mono slot: core 1 mixes the inputs to (L + R) / 2 (P:$8A6, Y:$30790) and its write (P:$8BD) copies those 32 words a
block into the slot's pages; after the stop core 1 normalizes the slot (P:$CE2: entry + 3 = the words done) and the ARM's writer
(0x20010B68, its periodic task 0x0802F1F4) streams it to the card as a mono 16-bit WAV, header last, through the save queue 0x2003CBF8.

Ours (A = the slot being recorded, B = A + 1, empty, the loaded pack not the internal one; asked from the computer: core 1 Y:STQ != 0,
tools/rhstereo.py):
  * core 1: with Y:STF = the source (0x30710 the inputs, 0x30750 with resampling; 0 = the stock's mono), the write copies the 64
    interleaved words L0 R0 L1 R1.. instead of the 32 of the mix: P:$8D7 (`move #>$30790,r0`) -> jmp ST (core1_code, P:$FEF..).  The
    trigger and its threshold keep the mix.  A slot holds 376 pages: about 16 s of stereo;
  * the ARM, on arming (0x0803CCE0 `b.w 0x0804B280` -> c_srarm): reads STQ, checks B, writes STF (and 0 for a mono recording after a
    stereo one); a stop before the trigger (the two calls of 0x0804B290 -> c_srstop) forgets it;
  * the writer's functors 0x20006EC8 / 0x20006ED0 / 0x20006ED8 (recording seen started / core 1 stopped by itself / a save ended): ours
    from a stereo arming until the uploads (the RAM stays the stock's otherwise).  At the start the peak of A = $7FFFFF (core 1's
    normalization keeps the level: the mix's gain could clip one side); at the end (the stop call, which resets the writer's watcher, or
    core 1 out of pages) STF = 0 and Fixed Recording's trim of A off (it would cut the interleaved words by half);
  * the split, in the DSP's memory (tools/stsplit.py, core 0): the writer's call of the sampler's words normalized (+ 0x38) for A gives 0
    (nothing to write yet) until it is done: once core 1 has normalized A (entry + 3 = + 2) we give core 0 its job (A, B: their page
    tables, entries and page counts, the go word last); core 0 moves the odd words to new pages of B and packs the even ones in A, a
    piece a block; then B into the save queue (after A) and the writer saves two plain mono slots.  No room in the free pages for B: A
    alone (L).  RD23's first version split while saving and uploaded A and B again from their files: new sample memory each time, from
    the LED task; on the device both came out empty and the unit hung;
  * B saved (the queue's end functor) -> our LED call, with the samples manager and the queue idle: the stock's functors back, B's bit
    from the card.
State in our RAM (rhstate "stereorec"): [0] phase (0 idle, 1 armed in stereo, 3 recording, 6 normalizing, 7 splitting, 4 B queued, 5 B
saved) [1] A [2] B [3] STF written non-zero [4] our functors installed (INST)."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b, b_cond, b_w, bl, blx_reg, cmp_imm, cmp_reg, h, ldr_imm, ldr_sp, ldrb_imm, ldrb_w,  # noqa: E402
                   lsls_imm, lsrs_imm, mov_reg, movs_imm, movt, movw, muls, orrs_reg, pop_list, push_list, raw, str_imm, str_sp, strb_imm,
                   sub_sp_imm, add_sp_imm)
import rhstate  # noqa: E402
import stsplit as SP  # noqa: E402

# ---- core 1
STF, STQ = 0x16EE, 0x16EF                                 # core 1 Y (cleared at its start: pitchmod clear): the source / the request
P_HOOK, OLD_HOOK, P_RET = 0x8D7, 0x60F400, 0x8DD          # move #>$30790,r0 (its first word) / the stock's copy loop (dor x1)
SRC_IN, SRC_RS, RS_FLAG = 0x30710, 0x30750, 0x371E8       # the inputs / the master (resampling) / core 1's resample flag
PEAK0 = 0x371F2                                           # + n: the slot's peak (core 1's normalization)
NORM_SLOT = 0x372F4                                       # the slot core 1 normalizes ($80 = none)
MONO_SRC = 0x30790
MOVE_M0_M5 = 0x0465A0                                     # movec m0,m5 (dsptool's asm does not take it)


def core1_code(at):
    """ST at P:at: the stock's two first moves, then the stereo source and 64 words when Y:STF != 0; back to the copy loop."""
    import rhdsppatch as DP
    stm = at + 10
    head = ["move #>$30790,r0", "move x:$1,x1", f"move y:>${STF:x},b", "tst b", f"jeq ${stm:x}", "move b,r0", "move #>$40,x1",
            "asr #$18,a,a"]
    ws = DP.asm(head) + [MOVE_M0_M5] + DP.asm(["move a0,r5", f"jmp ${P_RET:x}"])
    assert len(DP.asm(head[:7])) == 10 and len(ws) == 14, "ST's words moved"
    return ws


# ---- the ARM
O_ST = rhstate.OFF["stereorec"][0]
S_PH, S_A, S_B, S_STF, S_INST = 0, 1, 2, 3, 4
INST = 0xC5
PH_ARMED, PH_REC, PH_BQ, PH_BSAVED, PH_NORM, PH_SPLIT = 1, 3, 4, 5, 6, 7
ARM_SITE, RECARM = 0x0803CCE0, 0x0804B280                 # b.w (the controller's arming, tail call: r1 = the slot)
STOP_BL, STOP_BW, RECSTOP = 0x0803CCFA, 0x0803CD26, 0x0804B290
PROC_SITE = 0x0802F478                                    # the writer: ldr r3, [r2, #0x38] | blx r3 (the sampler's words normalized)
F_START, FN_START = 0x20006EC8, 0x0803C9DD                # {fn, ctx}: the writer saw the recording start / end; the queue's end
F_STOP, FN_STOP = 0x20006ED0, 0x0803C9E1
F_SAVED, FN_SAVED = 0x20006ED8, 0x08035011
SQ, SQ_ADD, SQ_BUSY, SQ_SLOT = 0x2003CBF8, 0x08035056, 8, 0x24
SM, O_OCC, O_PACK, O_SMSTATE = 0x20043DC0, 0x14, 0x18, 0x20
GET = 0x0803FC58
REFRESH = 0x08039FB4                                      # the samples manager: a slot's bit from the card
FIX_OBJ, FIX_BITS, FIX_VT = 0x20048560, 0x224, 0x08068FDC  # Fixed Recording's trim: a bit a slot (0x0803CDE6 / 0x0803CE16)
DSP_READ, DSP_WRITE = 0x080314D6, 0x08031228              # (0, addr) -> word << 8 / (0, word << 8, addr): core 0's host port, shared
WR16 = 0x08031200                                         # (core, word << 8, address; $8000 = Y): the 16-bit host command
SAMPLER_VT = 0x08066E58


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def arm_code(base, L, prev_led, known=None):
    """known = the labels of a first pass (c_srled stores our functors' addresses as movw / movt)"""
    a = Asm(base)
    E = a.emit
    zc = [0]
    inv = {"eq": "ne", "ne": "eq", "lo": "hs", "hs": "lo", "hi": "ls", "ls": "hi"}

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    def bc(target, cond):
        zc[0] += 1
        n = f"_s{zc[0]}"
        E(b_cond, n, inv[cond])
        E(b, target)
        a.label(n)

    # ---- c_srst() -> r0 = our state (rhstate), 0 without our RAM; clobbers r1-r3
    a.label("c_srst")
    E(push_list, [4], lr=True)
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ss_x", "eq")
    E(adds_imm8, 0, O_ST)
    a.label("ss_x")
    E(pop_list, [4], pc=True)

    # ---- c_srw0(r0 = word, r1 = Y address of core 0): 0x08031200(0, word << 8, $8000 | address); clobbers r0-r3, r12
    a.label("c_srw0")
    E(push_list, [4], lr=True)
    E(lsls_imm, 0, 0, 8)
    E(mov_reg, 2, 1)
    E(movw, 1, 0x8000)
    E(orrs_reg, 2, 1)
    E(mov_reg, 1, 0)
    E(movs_imm, 0, 0)
    E(bl, WR16)
    E(pop_list, [4], pc=True)

    # ---- c_srr0(r0 = Y address of core 0) -> r0 = its word (rdiag's 16-bit read, under the DSP's lock); clobbers r1-r3, r12
    a.label("c_srr0")
    E(push_list, [4], lr=True)
    E(movw, 1, 0x8000)
    E(orrs_reg, 1, 0)
    E(movs_imm, 0, 0)
    E(bl, L["c_d16r"])
    E(lsrs_imm, 0, 0, 8)
    E(pop_list, [4], pc=True)

    # ---- c_srrd(r0 = a shared address) -> r0 = its word (core 0's host port); clobbers r1-r3, r12
    a.label("c_srrd")
    E(push_list, [4], lr=True)
    E(mov_reg, 1, 0)
    E(movs_imm, 0, 0)
    E(bl, DSP_READ)
    E(lsrs_imm, 0, 0, 8)
    E(pop_list, [4], pc=True)

    # ---- c_srjob(r6 = state): core 0's job for A and B (tools/stsplit.py), its go word last; clobbers r0-r3
    a.label("c_srjob")
    E(push_list, [4, 5], lr=True)
    E(ldrb_imm, 4, 6, S_A)
    E(ldrb_imm, 5, 6, S_B)
    for adr in (SP.RES, SP.S):
        E(movs_imm, 0, 0)
        E(movw, 1, adr)
        E(bl, "c_srw0")
    for r, adr in ((4, SP.PTA), (5, SP.PTB)):
        E(movs_imm, 0, SP.PSTRIDE)
        E(muls, 0, r)
        imm32(1, SP.PAGES)
        E(adds_reg, 0, 0, 1)
        E(movw, 1, adr)
        E(bl, "c_srw0")
    for r, adr in ((4, SP.EA), (5, SP.EB)):
        E(lsls_imm, 0, r, 2)
        imm32(1, SP.SMP)
        E(adds_reg, 0, 0, 1)
        E(movw, 1, adr)
        E(bl, "c_srw0")
    for r, adr in ((4, SP.CA), (5, SP.CB)):
        imm32(0, SP.COUNTS)
        E(adds_reg, 0, 0, r)
        E(movw, 1, adr)
        E(bl, "c_srw0")
    imm32(0, SP.JKEY)
    E(movw, 1, SP.JOB)
    E(bl, "c_srw0")
    E(pop_list, [4, 5], pc=True)

    # ---- c_srproc (the writer's call of the sampler's + 0x38, the words normalized: r0 = sampler, r1 = slot, r2 = its vtable).
    #      A in a stereo recording: 0 (nothing to write yet) while it records, core 1 normalizes it and core 0 splits it; then core 0's
    #      job; once core 0 is done, B into the save queue (after A) and from then the stock's (A is a mono slot of N words)
    a.label("c_srproc")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(sub_sp_imm, 8)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(bl, "c_srst")
    E(cmp_imm, 0, 0)
    bc("pr_st", "eq")
    E(mov_reg, 6, 0)
    E(ldrb_imm, 0, 6, S_A)
    E(cmp_reg, 0, 5)
    bc("pr_st", "ne")
    E(ldrb_imm, 0, 6, S_PH)
    E(cmp_imm, 0, PH_SPLIT)
    bc("pr_sp", "eq")
    E(cmp_imm, 0, PH_REC)
    bc("pr_zero", "eq")                                                  # recording: A is interleaved, nothing of it to write
    E(cmp_imm, 0, PH_NORM)
    bc("pr_st", "ne")
    imm32(0, SP.SMP + 2)                                                 # NORM: A's words and the words normalized
    E(lsls_imm, 1, 5, 2)
    E(adds_reg, 7, 0, 1)
    E(mov_reg, 0, 7)
    E(bl, "c_srrd")
    E(str_sp, 0, 0)
    E(cmp_imm, 0, 0)
    bc("pr_none", "eq")                                                  # nothing recorded
    E(adds_imm8, 7, 1)
    E(mov_reg, 0, 7)
    E(bl, "c_srrd")
    E(ldr_sp, 1, 0)
    E(cmp_reg, 0, 1)
    bc("pr_zero", "ne")                                                  # core 1 still normalizing
    imm32(0, NORM_SLOT)
    E(bl, "c_srrd")
    E(cmp_imm, 0, 0x80)
    bc("pr_zero", "lo")                                                  # its last call not made yet (it reads A's words once more)
    E(bl, "c_srjob")
    E(movs_imm, 0, PH_SPLIT)
    E(strb_imm, 0, 6, S_PH)
    E(b, "pr_zero")
    a.label("pr_sp")                                                     # SPLIT: core 0 done?
    E(movw, 0, SP.JOB)
    E(bl, "c_srr0")
    E(cmp_imm, 0, 0)
    bc("pr_zero", "ne")
    E(movw, 0, SP.RES)
    E(bl, "c_srr0")
    E(cmp_imm, 0, 1)
    bc("pr_none", "ne")                                                  # A alone (no room for B, or nothing)
    imm32(0, SQ)
    E(ldrb_imm, 1, 6, S_B)
    E(bl, SQ_ADD)
    E(movs_imm, 0, PH_BQ)
    E(strb_imm, 0, 6, S_PH)
    E(b, "pr_st")
    a.label("pr_none")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 6, S_PH)
    E(mov_reg, 7, 4)
    E(mov_reg, 4, 6)
    E(bl, "c_srfun")                                                     # (r0 = 0: the stock's functors back)
    E(mov_reg, 4, 7)
    E(b, "pr_st")
    a.label("pr_zero")
    E(movs_imm, 0, 0)
    E(b, "pr_x")
    a.label("pr_st")                                                     # the stock's
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(ldr_imm, 2, 0, 0)
    E(ldr_imm, 3, 2, 0x38)
    E(blx_reg, 3)
    a.label("pr_x")
    E(add_sp_imm, 8)
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_srstf(r4 = state, r0 = the word): STF of core 1 (only when it changes from or to 0); clobbers r0-r3
    a.label("c_srstf")
    E(push_list, [5], lr=True)
    E(mov_reg, 5, 0)
    E(ldrb_imm, 1, 4, S_STF)
    E(cmp_imm, 0, 0)
    E(b_cond, "sf_w", "ne")
    E(cmp_imm, 1, 0)
    E(b_cond, "sf_x", "eq")                                              # 0 and already 0: no write
    a.label("sf_w")
    E(movw, 1, STF)
    E(bl, L["c_spw"])
    E(movs_imm, 0, 0)
    E(cmp_imm, 5, 0)
    E(b_cond, "sf_s", "eq")
    E(movs_imm, 0, 1)
    a.label("sf_s")
    E(strb_imm, 0, 4, S_STF)
    a.label("sf_x")
    E(pop_list, [5], pc=True)

    # ---- c_srocc(r0 = slot) -> r0 = its occupied bit (the samples manager's); clobbers r1-r3
    a.label("c_srocc")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    imm32(0, SM)
    E(ldr_imm, 0, 0, O_OCC)
    E(lsrs_imm, 1, 4, 5)
    E(bl, GET)
    E(ldr_imm, 0, 0, 0)
    E(movs_imm, 1, 31)
    E(raw, h(0x400C))                                                    # ands r4, r1
    E(raw, h(0x40E0))                                                    # lsrs r0, r4
    E(movs_imm, 1, 1)
    E(raw, h(0x4008))                                                    # ands r0, r1
    E(pop_list, [4], pc=True)

    # ---- c_srfun(r4 = state, r0 = 1 put ours / 0 the stock's back) -> r0 = 1, or 0 when the functors are not the stock's; clobbers r0-r3.
    #      Ours only while a stereo recording runs: the RAM is the stock's otherwise
    a.label("c_srfun")
    E(push_list, [5, 6], lr=True)
    E(mov_reg, 6, 0)
    imm32(5, F_START)
    E(ldrb_imm, 0, 4, S_INST)
    E(cmp_imm, 6, 0)
    E(b_cond, "fu_in", "ne")
    E(cmp_imm, 0, INST)
    bc("fu_ok", "ne")
    for k, fn in enumerate((FN_START, FN_STOP, FN_SAVED)):
        imm32(0, fn)
        E(str_imm, 0, 5, 8 * k)
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 4, S_INST)
    E(b, "fu_ok")
    a.label("fu_in")
    E(cmp_imm, 0, INST)
    bc("fu_ok", "eq")
    for k, fn in enumerate((FN_START, FN_STOP, FN_SAVED)):
        E(ldr_imm, 0, 5, 8 * k)
        imm32(1, fn)
        E(cmp_reg, 0, 1)
        bc("fu_no", "ne")
    for k, fn in enumerate(("c_srfstart", "c_srfstop", "c_srfsaved")):
        imm32(0, (known or {}).get(fn, 0) | 1)
        E(str_imm, 0, 5, 8 * k)
    E(movs_imm, 0, INST)
    E(strb_imm, 0, 4, S_INST)
    a.label("fu_ok")
    E(movs_imm, 0, 1)
    E(pop_list, [5, 6], pc=True)
    a.label("fu_no")
    E(movs_imm, 0, 0)
    E(pop_list, [5, 6], pc=True)

    # ---- c_srend(r4 = state): the recording ended -> STF = 0, Fixed Recording's trim of A off, the split due; clobbers r0-r3
    a.label("c_srend")
    E(push_list, [5], lr=True)
    E(movs_imm, 0, 0)
    E(bl, "c_srstf")
    imm32(0, FIX_OBJ)
    E(ldr_imm, 1, 0, 0)
    imm32(2, FIX_VT)
    E(cmp_reg, 1, 2)
    E(b_cond, "en_q", "ne")                                              # (not the object of the dump: leave it)
    E(movw, 1, FIX_BITS)
    E(adds_reg, 0, 0, 1)
    E(ldr_imm, 0, 0, 0)                                                  # the bits
    E(ldrb_imm, 1, 4, S_A)
    E(lsrs_imm, 2, 1, 3)
    E(adds_reg, 0, 0, 2)                                                 # its byte
    E(movs_imm, 2, 7)
    E(raw, h(0x4011))                                                    # ands r1, r2
    E(movs_imm, 2, 1)
    E(raw, h(0x408A))                                                    # lsls r2, r1
    E(ldrb_imm, 1, 0, 0)
    E(raw, h(0x4391))                                                    # bics r1, r2
    E(strb_imm, 1, 0, 0)
    a.label("en_q")
    E(movs_imm, 0, PH_NORM)                                              # core 1 normalizes A, then core 0 splits it (c_srproc)
    E(strb_imm, 0, 4, S_PH)
    E(pop_list, [5], pc=True)

    # ---- c_srarm (0x0803CCE0's tail call of the arming: r0, r1 = slot, r2 as the stock gives them; lr = the controller's caller)
    a.label("c_srarm")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)
    E(bl, "c_srst")
    E(cmp_imm, 0, 0)
    bc("ar_go", "eq")
    E(mov_reg, 4, 0)
    E(ldrb_imm, 0, 4, S_PH)
    E(cmp_imm, 0, PH_REC)
    bc("ar_go", "hs")                                                    # a stereo save under way: this one stays mono, its state untouched
    E(movs_imm, 6, 0)                                                    # r6 = STF (0 = mono)
    E(movs_imm, 0, 1)
    E(movw, 1, 0x8000 | STQ)
    E(bl, L["c_d16r"])
    E(cmp_imm, 0, 0)
    bc("ar_set", "eq")
    E(cmp_imm, 5, 126)
    bc("ar_set", "hi")
    imm32(0, SM)
    E(ldr_imm, 0, 0, O_PACK)
    E(movs_imm, 1, 0)
    E(bl, GET)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, 0)
    bc("ar_set", "eq")                                                   # the internal pack: never written (rodisk), so mono
    E(mov_reg, 0, 5)
    E(adds_imm8, 0, 1)
    E(bl, "c_srocc")
    E(cmp_imm, 0, 0)
    bc("ar_set", "ne")                                                   # B holds a sample
    E(movs_imm, 0, 1)
    E(bl, "c_srfun")
    E(cmp_imm, 0, 0)
    bc("ar_set", "eq")                                                   # the functors are not the stock's: mono
    E(movs_imm, 0, 0)
    imm32(1, RS_FLAG)
    E(bl, DSP_READ)
    imm32(6, SRC_IN)
    E(cmp_imm, 0, 0)
    E(b_cond, "ar_src", "eq")
    imm32(6, SRC_RS)
    a.label("ar_src")
    E(strb_imm, 5, 4, S_A)
    E(adds_imm8, 5, 1)
    E(strb_imm, 5, 4, S_B)
    a.label("ar_set")
    E(movs_imm, 0, PH_ARMED)
    E(cmp_imm, 6, 0)
    E(b_cond, "ar_ph", "ne")
    E(movs_imm, 0, 0)                                                    # mono: the stock's functors back, if ours were left
    E(bl, "c_srfun")
    E(movs_imm, 0, 0)
    a.label("ar_ph")
    E(strb_imm, 0, 4, S_PH)
    E(mov_reg, 0, 6)
    E(bl, "c_srstf")
    a.label("ar_go")
    E(raw, popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    E(b_w, RECARM)

    # ---- c_srstop (in place of the controller's two calls of 0x0804B290): the stock's stop (it resets the writer's watcher: its end
    #      functor only runs when core 1 stops by itself), then: recording in stereo -> the end; armed but not triggered -> forgotten
    a.label("c_srstop")
    E(push_list, [4], lr=True)
    E(bl, RECSTOP)
    E(bl, "c_srst")
    E(cmp_imm, 0, 0)
    E(b_cond, "sp_x", "eq")
    E(mov_reg, 4, 0)
    E(ldrb_imm, 0, 4, S_PH)
    E(cmp_imm, 0, PH_REC)
    E(b_cond, "sp_a", "ne")
    E(bl, "c_srend")
    E(b, "sp_x")
    a.label("sp_a")
    E(cmp_imm, 0, PH_ARMED)
    E(b_cond, "sp_x", "ne")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 4, S_PH)
    E(bl, "c_srstf")
    E(movs_imm, 0, 0)
    E(bl, "c_srfun")
    a.label("sp_x")
    E(pop_list, [4], pc=True)

    # ---- c_srfstart (the functor 0x20006EC8: r0 = its context): the recording started -> A's peak = $7FFFFF; then the stock's
    a.label("c_srfstart")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 6, 0)
    E(bl, "c_srst")
    E(cmp_imm, 0, 0)
    E(b_cond, "fa_go", "eq")
    E(mov_reg, 4, 0)
    E(ldrb_imm, 0, 4, S_PH)
    E(cmp_imm, 0, PH_ARMED)
    E(b_cond, "fa_go", "ne")
    E(movs_imm, 0, PH_REC)
    E(strb_imm, 0, 4, S_PH)
    E(ldrb_imm, 2, 4, S_A)
    imm32(1, PEAK0)
    E(adds_reg, 2, 2, 1)
    imm32(1, 0x7FFFFF00)
    E(movs_imm, 0, 0)
    E(bl, DSP_WRITE)
    a.label("fa_go")
    E(mov_reg, 0, 6)
    E(raw, popw([4, 5, 6], lr=True))
    E(b_w, FN_START & ~1)

    # ---- c_srfstop (the functor 0x20006ED0): core 1 stopped by itself (no pages left) -> the end; then the stock's
    a.label("c_srfstop")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 6, 0)
    E(bl, "c_srst")
    E(cmp_imm, 0, 0)
    E(b_cond, "fo_go", "eq")
    E(mov_reg, 4, 0)
    E(ldrb_imm, 0, 4, S_PH)
    E(cmp_imm, 0, PH_REC)
    E(b_cond, "fo_go", "ne")
    E(bl, "c_srend")
    a.label("fo_go")
    E(mov_reg, 0, 6)
    E(raw, popw([4, 5, 6], lr=True))
    E(b_w, FN_STOP & ~1)

    # ---- c_srfsaved (the functor 0x20006ED8: r0 = the queue): the stock's end of a save, then B saved -> the uploads are due
    a.label("c_srfsaved")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 6, 0)
    E(ldrb_w, 5, 6, SQ_SLOT)
    E(bl, FN_SAVED & ~1)
    E(bl, "c_srst")
    E(cmp_imm, 0, 0)
    E(b_cond, "fs_x", "eq")
    E(ldrb_imm, 1, 0, S_PH)
    E(cmp_imm, 1, PH_BQ)
    E(b_cond, "fs_x", "ne")
    E(ldrb_imm, 1, 0, S_B)
    E(cmp_reg, 1, 5)
    E(b_cond, "fs_x", "ne")
    E(movs_imm, 1, PH_BSAVED)
    E(strb_imm, 1, 0, S_PH)
    a.label("fs_x")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_srled (the LED task's calls: ctrl, frame): the chain; B saved and the manager idle -> the stock's functors, B's bit
    a.label("c_srled")
    E(push_list, [4, 5, 6], lr=True)
    E(bl, prev_led)
    E(bl, "c_srst")
    E(cmp_imm, 0, 0)
    bc("sl_x", "eq")
    E(mov_reg, 4, 0)
    E(ldrb_imm, 0, 4, S_PH)
    E(cmp_imm, 0, PH_BSAVED)
    bc("sl_x", "ne")
    imm32(5, SM)
    E(ldr_imm, 0, 5, O_SMSTATE)
    E(movs_imm, 1, 1)
    E(bl, GET)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, 0)
    bc("sl_x", "ne")                                                     # the manager busy: next frame
    imm32(0, SQ)
    E(ldr_imm, 0, 0, SQ_BUSY)
    E(cmp_imm, 0, 1)
    bc("sl_x", "eq")                                                     # the queue saving: next frame
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 4, S_PH)
    E(bl, "c_srfun")
    E(mov_reg, 0, 5)
    E(ldrb_imm, 1, 4, S_B)
    E(bl, REFRESH)                                                       # B's bit (its file is there now)
    a.label("sl_x")
    E(pop_list, [4, 5, 6], pc=True)
    return a


def build_code(base, L, prev_led):
    """Two passes: the second one knows the functors' addresses (movw / movt: the same size either way)."""
    code, labels = arm_code(base, L, prev_led).assemble()
    code2, labels2 = arm_code(base, L, prev_led, labels).assemble()
    assert labels2 == labels and len(code2) == len(code)
    return code2, labels2


def install(img, report, base_addr):
    """The ARM side; core 1's words come with pitchmod's (stereo=True).  Needs rdiag dsp=2 (c_d16r; without rdiag, tools/dsprd.py), stockplus (c_spw) and the
    LED chain's head (granpage on RH39)."""
    import rhbuild
    from countin import LED_CALLS
    BASE = rhbuild.BASE
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    assert report.get("pitchmod", {}).get("stereo"), "stereorec needs pitchmod stereo=True (core 1's words)"
    sg = [tuple(x) for x in report.get("core0", {}).get("segs", [])]
    assert (hex(SP.AT), SP.code(int(report["granular0"]["gr"], 16))[0].__len__()) in sg and sg[-1] == (hex(SP.HOOK), 2),         "stereorec needs granular0 extra=stsplit.segs (core 0's split, P:$224 -> SPL last)"
    L = dict(c_rst=lab("rhstate", "c_rst"), c_d16r=lab("rdiag" if "rdiag" in report else "dsprd", "c_d16r"), c_spw=lab("stockplus", "c_spw"))
    prev_led = rhbuild.bl_target(img, LED_CALLS[0])
    assert all(rhbuild.bl_target(img, c) == prev_led for c in LED_CALLS)
    assert rhbuild.bw_target(img, ARM_SITE) == RECARM and rhbuild.bl_target(img, STOP_BL) == RECSTOP
    assert rhbuild.bw_target(img, STOP_BW) == RECSTOP
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]                 # noqa: E731
    assert u(SAMPLER_VT + 0x38) & ~1 == 0x080645B0, "the sampler's vtable moved"
    code, labels = build_code(base_addr, L, prev_led)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, ARM_SITE, f"b.w #{RECARM:#x}", b_w(ARM_SITE, labels["c_srarm"]))
    rhbuild.patch(img, STOP_BL, f"bl #{RECSTOP:#x}", bl(STOP_BL, labels["c_srstop"]))
    rhbuild.patch(img, STOP_BW, f"b.w #{RECSTOP:#x}", b_w(STOP_BW, labels["c_srstop"]))
    rhbuild.patch(img, PROC_SITE, "ldr r3, [r2, #0x38]|blx r3", bl(PROC_SITE, labels["c_srproc"]))
    for c in LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev_led:#x}", bl(c, labels["c_srled"]))
    report["stereorec"] = dict(prev_led=hex(prev_led), stf=hex(STF), stq=hex(STQ),
                               labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
