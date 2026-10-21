"""A sample copied to another slot, of the same pack or from another pack, in the Sample Rec view (MIT; CIRCUIT-HACKS' packio (2., 4., 8.:
COPYX, «al duplicar un sample ENTRE PACKS, copia el primer sample al segundo») for the Circuit Rhythm 5706; part of «gestión del pack», approved
by the user on 2026-10-19).  The stock records, trims and deletes samples, but cannot copy one to another slot.

The stock of the Rhythm (read in the firmware, emulated on the RAM dump):
  * the Sample Rec view 0x2004DC90 (vtable 0x08067A08; button 18, one of the bootloader's three): slot 0 = the pads 0x0804F9D8(view, pad,
    velocity): pads 1-16 = the slots pad + 16 x page ([view + 0xC], a byte: 8 pages of 16 = 128 samples); [view + 0x20] p0 = the selected slot;
    Clear + the selected slot = delete it (unless its bit is set in [view + 0x38]); in the stock Duplicate + a slot = the slot (Duplicate held =
    bit 24 of [ctrl + 0xA0]): the gesture is free;
  * the samples manager SM = 0x20043DC0 (vtable 0x08067570): [SM + 0x14] = the 128 occupied bits (4 parameters), [SM + 0x18] = the store
    0x20012478 (p0 = the loaded pack), [SM + 0x20] = its own state (p1 != 0 = busy: a save or a delete of the stock under way);
    0x08039FB4(SM, slot) = the slot's bit from the card (exists, kind 4), committed; 0x0803A0D8(SM, slot) = the slot reloaded into the DSP:
    0x0804A4A8(slot) frees its entry, then if the file exists 0x080460B8(slot) -> 0x08053E8C(slot) uploads it (kind 4, pack 0xFE = the
    storage task's current pack) - the stock's own path when a slot's file changes (its event 4 | slot << 16, 0x08039F58);
  * the samples live in the DSP's memory, a bump allocator: its free pointer = DSP word 0x371D2 >> 8 (core 0; read with 0x080314D6(0, addr),
    which takes the DSP service's lock); the upload refuses beyond 0xE00000 words ("Sample Memory Exceeded"; 16-bit data = bytes / 2 words);
    a reloaded slot takes new memory (the old one is reused at the next pack load);
  * the card: a sample = kind 4, index = the slot (the stock's own save deletes the old file and writes the new one, 0x08047316 / 0x080472E4).

Ours (slot 0 of the view, transport stopped, Duplicate held):
  * Duplicate + a slot with a sample (A) = the source: it blinks yellow while its pack is loaded; Duplicate + A again forgets it;
  * with a source, Duplicate + a slot B (this pack or, after loading another pack, that one) = A's file copied into B: an empty B at once; a B
    that holds a sample blinks white first and Duplicate + B again within ~5 s writes.  Refused, nothing touched, when the samples manager is
    busy or the DSP's memory cannot take it; the internal pack is never written (rodisk: the Save LED red).  B's old file deleted, A's copied
    in 4 KB pieces (shared buffer), the storage task back on the loaded pack, B's bit and its upload into the DSP by the stock's own routines:
    B sounds at once.  B green for ~1.5 s (red if refused or failed; a failed copy deletes the partial file).  The source stays until power-off.
State in our RAM (rhstate "smpcopy"): [0] tag [1] source + 1 [2] its pack [3] the slot asked about + 1 [4..5] the question's time [6] the last
B + 1 [7] its pack [8] the last copy's status [10..11] its time (times = the HAL tick / 256, 16 bits).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, ands_reg, b, b_cond, bl, cmp_imm, cmp_reg, h, ldr_imm, ldrb_imm, ldrh_imm, lsls_imm,  # noqa: E402
                   lsrs_imm, mov_reg, movs_imm, movt, movw, pop_list, push_list, raw, str_imm, strb_imm, strh_imm, strh_reg, sub_sp_imm,
                   add_sp_imm, subs_reg, subs_imm8, tst_reg, ldrb_w)
import countin as CI  # noqa: E402
import rhstate  # noqa: E402
import rodisk  # noqa: E402
import sesscopy as SC  # noqa: E402

CTRL, CTRL_VT = CI.CTRL, CI.CTRL_VT
O_VIEW, O_HELD, BIT_DUP = 0x7C, 0xA0, 24
SR_VIEW, SR_VT = 0x2004DC90, 0x08067A08
PAD_STOCK = 0x0804F9D8
O_PAGE, O_PROT = 0xC, 0x38
SM, SM_VT = 0x20043DC0, 0x08067570
O_SMSTATE = 0x20
REFRESH, RELOAD = 0x08039FB4, 0x0803A0D8
DSP_READ, DSP_FREE, DSP_LIMIT, MARGIN = 0x080314D6, 0x371D2, 0xE00000, 0x400
EXISTS, SIZE, READ, WRITE, DELETE = SC.EXISTS, SC.SIZE, SC.READ, SC.WRITE, rodisk.DELETE
BUF_LOCK, BUF_UNLOCK, BUF, LOCK_OWNER = SC.BUF_LOCK, SC.BUF_UNLOCK, SC.BUF, SC.LOCK_OWNER
KIND_PCM, KIND_SESS = 4, 2
CHUNK_SHIFT = 12
PACKS_VIEW, PACKS_VT, CUR_PACK_PTR = SC.PACKS_VIEW, SC.PACKS_VT, SC.CUR_PACK_PTR
PARAM_NEW = CI.PARAM_NEW
TRANSPORT = CI.TRANSPORT
HAL_TICK = rodisk.HAL_TICK
LED_CALLS = CI.LED_CALLS
O_ST = rhstate.OFF["smpcopy"][0]
S_TAG, S_A, S_PA, S_ASK, S_ASKT, S_B, S_PB, S_RES, S_REST = 0, 1, 2, 3, 4, 6, 7, 8, 10
TAG = 0xC9
ST_EMPTY, ST_FULL, ST_BUSY = 8, 9, 10        # our own statuses: no source file, no room in the DSP, the stock busy
LIFE, SHOW = 20, 6
COL_SRC, COL_ASK, COL_OK, COL_BAD = 0x2F, 0x01, 0x1E, 0x55
INV = {"eq": "ne", "ne": "eq", "lo": "hs", "hs": "lo", "hi": "ls", "ls": "hi", "mi": "pl", "pl": "mi"}


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit
    zc = [0]
    BX_LR = h(0x4770)

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    def bc(target, cond):
        zc[0] += 1
        n = f"_c{zc[0]}"
        E(b_cond, n, INV[cond])
        E(b, target)
        a.label(n)

    def tick(rd):
        imm32(rd, HAL_TICK)
        E(ldr_imm, rd, rd, 0)
        E(lsrs_imm, rd, rd, 8)
        E(lsls_imm, rd, rd, 16)
        E(lsrs_imm, rd, rd, 16)

    def since(rd, rt, off):
        tick(rd)
        E(ldrh_imm, 1, rt, off)
        E(subs_reg, rd, rd, 1)
        E(lsls_imm, rd, rd, 16)
        E(lsrs_imm, rd, rd, 16)

    def item(sp_off, slot_reg, pack_reg):                                  # [r7 + sp_off] = {kind 4, slot, pack}
        E(movs_imm, 0, KIND_PCM)
        E(str_imm, 0, 7, sp_off)
        E(str_imm, slot_reg, 7, sp_off + 4)
        E(str_imm, pack_reg, 7, sp_off + 8)

    # ---- c_cpst() -> r0 = our state (tagged on first use), 0 without our RAM; clobbers r1-r3
    a.label("c_cpst")
    E(push_list, [4], lr=True)
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "st_x", "eq")
    E(adds_imm8, 0, O_ST)
    E(ldrb_imm, 1, 0, S_TAG)
    E(cmp_imm, 1, TAG)
    E(b_cond, "st_x", "eq")
    E(movs_imm, 1, TAG)
    E(strb_imm, 1, 0, S_TAG)
    E(movs_imm, 1, 0)
    for o in (S_A, S_ASK, S_B):
        E(strb_imm, 1, 0, o)
    a.label("st_x")
    E(pop_list, [4], pc=True)

    # ---- c_cpok() -> r0 = 1 when the controller and the samples manager are the dump's; clobbers r1
    a.label("c_cpok")
    imm32(0, CTRL)
    E(ldr_imm, 0, 0, 0)
    imm32(1, CTRL_VT)
    E(cmp_reg, 0, 1)
    E(b_cond, "ok_0", "ne")
    imm32(0, SM)
    E(ldr_imm, 0, 0, 0)
    imm32(1, SM_VT)
    E(cmp_reg, 0, 1)
    E(b_cond, "ok_0", "ne")
    E(movs_imm, 0, 1)
    E(raw, BX_LR)
    a.label("ok_0")
    E(movs_imm, 0, 0)
    E(raw, BX_LR)

    # ---- c_cpon() -> r0 = the Sample Rec view when it is the active view, else 0; clobbers r1, r2
    a.label("c_cpon")
    E(push_list, [3], lr=True)
    E(bl, "c_cpok")
    E(cmp_imm, 0, 0)
    E(b_cond, "on_x", "eq")
    imm32(0, CTRL)
    E(ldr_imm, 0, 0, O_VIEW)
    imm32(1, SR_VIEW)
    E(cmp_reg, 0, 1)
    E(b_cond, "on_0", "ne")
    E(ldr_imm, 1, 0, 0)
    imm32(2, SR_VT)
    E(cmp_reg, 1, 2)
    E(b_cond, "on_x", "eq")
    a.label("on_0")
    E(movs_imm, 0, 0)
    a.label("on_x")
    E(pop_list, [3], pc=True)

    # ---- c_cpnew(r0 = store, r1 = parameter) -> r0 = its word (the newest copy)
    a.label("c_cpnew")
    E(push_list, [3], lr=True)
    E(bl, PARAM_NEW)
    E(ldr_imm, 0, 0, 0)
    E(pop_list, [3], pc=True)

    # ---- c_cpcur() -> r0 = the loaded pack (p0 of the packs view's store; the storage task's current pack without that view)
    a.label("c_cpcur")
    E(push_list, [4], lr=True)
    imm32(4, PACKS_VIEW)
    E(ldr_imm, 0, 4, 0)
    imm32(1, PACKS_VT)
    E(cmp_reg, 0, 1)
    E(b_cond, "cu_ff", "ne")
    E(ldr_imm, 0, 4, 0x10)
    E(movs_imm, 1, 0)
    E(bl, "c_cpnew")
    E(lsls_imm, 0, 0, 24)
    E(lsrs_imm, 0, 0, 24)
    E(pop_list, [4], pc=True)
    a.label("cu_ff")
    imm32(0, CUR_PACK_PTR)
    E(ldr_imm, 0, 0, 0)
    E(ldrb_imm, 0, 0, 0)
    E(pop_list, [4], pc=True)

    # ---- c_cpsize(r0 = slot, r1 = pack) -> r0 = the size of its file (0: no sample there)
    a.label("c_cpsize")
    E(push_list, [4], lr=True)
    E(sub_sp_imm, 16)
    E(movs_imm, 2, KIND_PCM)
    E(raw, h(0x9200))                                                      # str r2, [sp]
    E(raw, h(0x9001))                                                      # str r0, [sp, #4]
    E(raw, h(0x9102))                                                      # str r1, [sp, #8]
    E(mov_reg, 0, 13)
    E(bl, SIZE)
    E(add_sp_imm, 16)
    E(pop_list, [4], pc=True)

    # ---- c_cpresel(r0 = pack): the storage task's current pack := that one (op 0 on its project 0)
    a.label("c_cpresel")
    E(push_list, [4], lr=True)
    E(sub_sp_imm, 16)
    E(raw, h(0x9002))                                                      # str r0, [sp, #8]
    E(movs_imm, 0, KIND_SESS)
    E(raw, h(0x9000))                                                      # str r0, [sp]
    E(movs_imm, 0, 0)
    E(raw, h(0x9001))                                                      # str r0, [sp, #4]
    E(mov_reg, 0, 13)
    E(bl, EXISTS)
    E(add_sp_imm, 16)
    E(pop_list, [4], pc=True)

    # ---- c_cpcopy(r0 = slot A, r1 = its pack, r2 = slot B, r3 = its pack = the loaded one) -> r0 = status (0 = copied and loaded)
    #      frame r7: [0] cb [4] ctx [8] &done [12] done [16..27] item A [28..39] item B [40] size [44] offset [48] B [52] status
    a.label("c_cpcopy")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(sub_sp_imm, 56)
    E(mov_reg, 7, 13)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    item(16, 4, 5)
    item(28, 2, 3)
    E(str_imm, 2, 7, 48)
    E(movs_imm, 0, 0)
    E(str_imm, 0, 7, 44)
    E(mov_reg, 0, 7)                                                       # A's size
    E(adds_imm8, 0, 16)
    E(bl, SIZE)
    E(str_imm, 0, 7, 40)
    E(movs_imm, 6, ST_EMPTY)
    E(cmp_imm, 0, 0)
    bc("cp_rs", "eq")
    E(movs_imm, 0, 0)                                                      # room in the DSP's memory: free + size / 2 + margin <= limit
    imm32(1, DSP_FREE)
    E(bl, DSP_READ)
    E(lsrs_imm, 0, 0, 8)
    E(ldr_imm, 1, 7, 40)
    E(lsrs_imm, 1, 1, 1)
    E(adds_reg, 0, 0, 1)
    imm32(1, DSP_LIMIT - MARGIN)
    E(movs_imm, 6, ST_FULL)
    E(cmp_reg, 0, 1)
    bc("cp_rs", "hs")
    E(mov_reg, 0, 7)                                                       # B's old file deleted (refused on the internal pack: nothing touched)
    E(adds_imm8, 0, 28)
    E(bl, SIZE)
    E(cmp_imm, 0, 0)
    E(b_cond, "cp_go", "eq")
    E(mov_reg, 0, 7)
    E(adds_imm8, 0, 28)
    E(movs_imm, 1, 0)
    E(movs_imm, 2, 0)
    E(bl, DELETE)
    E(mov_reg, 6, 0)
    E(cmp_imm, 6, 0)
    bc("cp_rs", "ne")
    a.label("cp_go")
    E(movs_imm, 0, LOCK_OWNER)
    E(bl, BUF_LOCK)
    a.label("cp_l")
    E(ldr_imm, 4, 7, 44)
    E(ldr_imm, 5, 7, 40)
    E(cmp_reg, 4, 5)
    bc("cp_ok", "hs")
    E(subs_reg, 5, 5, 4)
    E(movs_imm, 6, 1)
    E(lsls_imm, 6, 6, CHUNK_SHIFT)
    E(cmp_reg, 5, 6)
    E(b_cond, "cp_n", "ls")
    E(mov_reg, 5, 6)
    a.label("cp_n")                                                        # r4 = the offset, r5 = the bytes of this piece
    for fn, it in ((READ, 16), (WRITE, 28)):
        E(movs_imm, 0, 0)
        E(str_imm, 0, 7, 0)
        E(str_imm, 0, 7, 4)
        E(str_imm, 0, 7, 12)
        E(mov_reg, 0, 7)
        E(adds_imm8, 0, 12)
        E(str_imm, 0, 7, 8)
        E(mov_reg, 0, 7)
        E(adds_imm8, 0, it)
        E(mov_reg, 1, 4)
        imm32(2, BUF)
        E(mov_reg, 3, 5)
        E(bl, fn)
        E(cmp_imm, 0, 0)
        bc("cp_f", "ne")
        if fn == READ:
            E(ldr_imm, 0, 7, 12)
            E(cmp_reg, 0, 5)
            bc("cp_f8", "ne")
    E(adds_reg, 4, 4, 5)
    E(str_imm, 4, 7, 44)
    E(b, "cp_l")
    a.label("cp_ok")
    E(movs_imm, 6, 0)
    E(b, "cp_u")
    a.label("cp_f8")
    E(movs_imm, 0, 8)
    a.label("cp_f")
    E(mov_reg, 6, 0)
    a.label("cp_u")
    E(bl, BUF_UNLOCK)
    E(cmp_imm, 6, 0)
    E(b_cond, "cp_rl", "eq")
    E(mov_reg, 0, 7)                                                       # a failed copy: the partial file deleted
    E(adds_imm8, 0, 28)
    E(movs_imm, 1, 0)
    E(movs_imm, 2, 0)
    E(bl, DELETE)
    a.label("cp_rl")
    E(str_imm, 6, 7, 52)
    E(bl, "c_cpcur")
    E(bl, "c_cpresel")
    imm32(0, SM)                                                           # B's bit and its upload: the stock's own routines
    E(ldr_imm, 1, 7, 48)
    E(bl, REFRESH)
    imm32(0, SM)
    E(ldr_imm, 1, 7, 48)
    E(bl, RELOAD)
    E(ldr_imm, 6, 7, 52)
    E(b, "cp_x")
    a.label("cp_rs")
    E(bl, "c_cpcur")
    E(bl, "c_cpresel")
    a.label("cp_x")
    E(mov_reg, 0, 6)
    E(add_sp_imm, 56)
    E(pop_list, [3, 4, 5, 6, 7], pc=True)

    # ---- c_cppad (the view's slot 0: view, pad, velocity): Duplicate held (stopped) = the source, then the copies
    a.label("c_cppad")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(cmp_imm, 5, 16)
    bc("sp_f", "hs")
    E(bl, "c_cpok")
    E(cmp_imm, 0, 0)
    bc("sp_f", "eq")
    imm32(0, CTRL + O_HELD)
    E(ldr_imm, 0, 0, 0)
    E(lsls_imm, 0, 0, 31 - BIT_DUP)
    bc("sp_f", "pl")                                                       # Duplicate not held: the stock's
    E(bl, "c_cpst")
    E(mov_reg, 7, 0)
    E(cmp_imm, 7, 0)
    bc("sp_f", "eq")
    imm32(0, TRANSPORT)
    E(movs_imm, 1, 0)
    E(bl, "c_cpnew")
    E(lsls_imm, 0, 0, 24)
    bc("sp_e", "ne")                                                       # playing: nothing
    E(ldrb_imm, 0, 4, O_PAGE)
    E(lsls_imm, 0, 0, 4)
    E(adds_reg, 5, 5, 0)                                                   # r5 = the slot
    E(bl, "c_cpcur")
    E(mov_reg, 6, 0)                                                       # r6 = the loaded pack
    E(ldrb_imm, 0, 7, S_A)
    E(cmp_imm, 0, 0)
    bc("sp_src", "eq")
    E(subs_imm8, 0, 1)
    E(ldrb_imm, 1, 7, S_PA)
    E(cmp_reg, 1, 6)
    E(b_cond, "sp_paste", "ne")
    E(cmp_reg, 0, 5)
    E(b_cond, "sp_paste", "ne")
    E(movs_imm, 0, 0)                                                      # the source again: forgotten
    E(strb_imm, 0, 7, S_A)
    E(strb_imm, 0, 7, S_ASK)
    E(b, "sp_e")
    a.label("sp_paste")
    imm32(0, SM)                                                           # the samples manager busy (a save / delete of the stock): refused
    E(ldr_imm, 0, 0, O_SMSTATE)
    E(movs_imm, 1, 1)
    E(bl, "c_cpnew")
    E(lsls_imm, 0, 0, 24)
    E(b_cond, "sp_busy", "ne")
    E(mov_reg, 0, 5)
    E(mov_reg, 1, 6)
    E(bl, "c_cpsize")
    E(cmp_imm, 0, 0)
    E(b_cond, "sp_go", "eq")                                               # an empty B: at once
    E(mov_reg, 0, 5)
    E(adds_imm8, 0, 1)
    E(ldrb_imm, 1, 7, S_ASK)
    E(cmp_reg, 1, 0)
    E(b_cond, "sp_ask", "ne")
    since(0, 7, S_ASKT)
    E(cmp_imm, 0, LIFE)
    E(b_cond, "sp_ask", "hs")
    a.label("sp_go")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 7, S_ASK)
    E(ldrb_imm, 0, 7, S_A)
    E(subs_imm8, 0, 1)
    E(ldrb_imm, 1, 7, S_PA)
    E(mov_reg, 2, 5)
    E(mov_reg, 3, 6)
    E(bl, "c_cpcopy")
    E(b, "sp_res")
    a.label("sp_busy")
    E(movs_imm, 0, ST_BUSY)
    a.label("sp_res")                                                      # r0 = the status
    E(strb_imm, 0, 7, S_RES)
    E(mov_reg, 1, 5)
    E(adds_imm8, 1, 1)
    E(strb_imm, 1, 7, S_B)
    E(strb_imm, 6, 7, S_PB)
    tick(1)
    E(strh_imm, 1, 7, S_REST)
    E(b, "sp_e")
    a.label("sp_ask")
    E(mov_reg, 0, 5)
    E(adds_imm8, 0, 1)
    E(strb_imm, 0, 7, S_ASK)
    tick(0)
    E(strh_imm, 0, 7, S_ASKT)
    E(b, "sp_e")
    a.label("sp_src")
    E(mov_reg, 0, 5)
    E(mov_reg, 1, 6)
    E(bl, "c_cpsize")
    E(cmp_imm, 0, 0)
    E(b_cond, "sp_e", "eq")                                                # an empty slot is no source
    E(mov_reg, 0, 5)
    E(adds_imm8, 0, 1)
    E(strb_imm, 0, 7, S_A)
    E(strb_imm, 6, 7, S_PA)
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 7, S_ASK)
    a.label("sp_e")
    E(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)
    a.label("sp_f")
    E(raw, popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    imm32(3, prev["pad"] | 1)
    E(raw, h(0x4718))                                                      # bx r3: the stock's slot 0

    # ---- c_cpput(r0 = slot + 1 or 0, r1 = colour; r4 = the view, r5 = the frame): that pad of the page shown; clobbers r0, r2, r3
    a.label("c_cpput")
    E(cmp_imm, 0, 0)
    E(b_cond, "pt_x", "eq")
    E(subs_imm8, 0, 1)
    E(lsrs_imm, 2, 0, 4)
    E(ldrb_imm, 3, 4, O_PAGE)
    E(cmp_reg, 2, 3)
    E(b_cond, "pt_x", "ne")
    E(movs_imm, 2, 15)
    E(ands_reg, 0, 2)
    E(lsls_imm, 0, 0, 1)
    E(strh_reg, 1, 5, 0)
    a.label("pt_x")
    E(raw, BX_LR)

    # ---- c_cpblink(r1 = colour) -> r1 = the colour or 0, ~4 times a second; clobbers r2, r3
    a.label("c_cpblink")
    imm32(2, HAL_TICK)
    E(ldr_imm, 2, 2, 0)
    E(lsrs_imm, 2, 2, 7)
    E(movs_imm, 3, 1)
    E(tst_reg, 2, 3)
    E(b_cond, "bl_x", "eq")
    E(movs_imm, 1, 0)
    a.label("bl_x")
    E(raw, BX_LR)

    # ---- c_cpled (the LED task's calls: r0 = ctrl, r1 = frame): the chain, then on the Sample Rec view: the source, the question, the result
    a.label("c_cpled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)
    E(bl, prev["ledtask"])
    E(bl, "c_cpon")
    E(mov_reg, 4, 0)
    E(cmp_imm, 4, 0)
    bc("lt_x", "eq")
    E(bl, "c_cpst")
    E(mov_reg, 7, 0)
    E(cmp_imm, 7, 0)
    bc("lt_x", "eq")
    E(bl, "c_cpcur")
    E(mov_reg, 6, 0)
    E(ldrb_imm, 0, 7, S_PA)                                                # the source, blinking yellow, in its pack
    E(cmp_reg, 0, 6)
    E(b_cond, "lt_q", "ne")
    E(movs_imm, 1, COL_SRC)
    E(bl, "c_cpblink")
    E(ldrb_imm, 0, 7, S_A)
    E(bl, "c_cpput")
    a.label("lt_q")                                                        # the question, blinking white, ~5 s
    E(ldrb_imm, 0, 7, S_ASK)
    E(cmp_imm, 0, 0)
    E(b_cond, "lt_r", "eq")
    since(0, 7, S_ASKT)
    E(cmp_imm, 0, LIFE)
    E(b_cond, "lt_q1", "lo")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 7, S_ASK)
    E(b, "lt_r")
    a.label("lt_q1")
    E(movs_imm, 1, COL_ASK)
    E(bl, "c_cpblink")
    E(ldrb_imm, 0, 7, S_ASK)
    E(bl, "c_cpput")
    a.label("lt_r")                                                        # the result, green or red, ~1.5 s
    E(ldrb_imm, 0, 7, S_B)
    E(cmp_imm, 0, 0)
    E(b_cond, "lt_x", "eq")
    E(ldrb_imm, 0, 7, S_PB)
    E(cmp_reg, 0, 6)
    E(b_cond, "lt_x", "ne")
    since(0, 7, S_REST)
    E(cmp_imm, 0, SHOW)
    E(b_cond, "lt_r1", "lo")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 7, S_B)
    E(b, "lt_x")
    a.label("lt_r1")
    E(movs_imm, 1, COL_OK)
    E(ldrb_imm, 0, 7, S_RES)
    E(cmp_imm, 0, 0)
    E(b_cond, "lt_r2", "eq")
    E(movs_imm, 1, COL_BAD)
    a.label("lt_r2")
    E(ldrb_imm, 0, 7, S_B)
    E(bl, "c_cpput")
    a.label("lt_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; the Sample Rec view's slot 0 and the two LED task calls."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda ad: struct.unpack_from("<I", img, ad - BASE)[0]
    ins = struct.unpack_from("<H", img, SC.BUF_LDR - BASE)[0]
    assert ins & 0xFF00 == 0x4800 and u(((SC.BUF_LDR + 4) & ~3) + 4 * (ins & 0xFF)) == BUF
    L = dict(c_rst=int(report["rhstate"]["labels"]["c_rst"], 16))
    prev = dict(pad=u(SR_VT) & ~1, ledtask=rhbuild.bl_target(img, LED_CALLS[0]))
    assert prev["pad"] == PAD_STOCK, hex(prev["pad"])
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in LED_CALLS)
    for fn, head in ((REFRESH, "push {r4, r5, lr}|sub sp, #0xc"), (RELOAD, "push {r4, r5, lr}|sub sp, #0xc"),
                     (DSP_READ, "push {r2, r3, r4, r5, r6, lr}|mov r5, r1")):
        assert "|".join(rhbuild.disasm(bytes(img[fn - BASE:fn - BASE + 4]), fn)) == head, hex(fn)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch_word(img, SR_VT, PAD_STOCK | 1, labels["c_cppad"] | 1)
    for c in LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_cpled"]))
    report["smpcopy"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
