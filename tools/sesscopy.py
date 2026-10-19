"""A project copied to another slot, of the same pack or of another one, from the Projects view (MIT; CIRCUIT-HACKS' sesscopy of SC39.6, the
user 2026-10-12: «copiar proyectos (sessions) completos entre packs», moved to the Circuit Rhythm 5706; #12 of docs/PORTADO.md).

The stock of the Rhythm (read in the firmware, emulated on the RAM dump, and read on the device with RD2 on 2026-10-19):
  * the Projects view 0x2004DA10 (vtable 0x080679CC, the Tracks' 0x0805A71C: its ten slots map one to one): slot 0 = the pads 0x0804F09E(view,
    pad, velocity), [view + 0x36] = the page (slot = pad + 32 x page), [view + 0x20] = the store 0x20012478 that also holds the loaded pack
    (p0, the packs view's [+ 0x10]): p11 = the loaded project, p12 / p13 = the slots that hold a project (bit = slot, 0-31 / 32-63), p16..p31 =
    the slots' colours (a byte each, 4 a word); the view paints its LEDs from them (slots 2 / 9), 0xB5 = empty;
  * Duplicate held = bit 24 of [ctrl + 0xA0]; in the stock, Duplicate + pad there = the pad (the load request 0x08047038): the gesture is free;
  * the content API of the storage task: a project = kind 2, its index = its slot (pad - 1 + 32 x page: seen on the device, pads 1 / 3 / 5 =
    indices 0 / 2 / 4), its file = the session record, 0x29484 B; op 1 size 0x08045FCE, op 6 read 0x08046054, op 7 write 0x0804607A (rodisk's
    guard: our writes on pack 0 fail); any operation on another pack moves the storage task's current pack ([[0x20006E24]]): one operation on
    the loaded pack puts it back (as tools/rhprobe.py does);
  * the 4 KB shared buffer 0x20003F94 under its lock 0x0802EF6A(owner) / 0x0802EF98() (the Tracks' 0x08026D06 / 0x08026D34, the same code).

Ours (slot 0 of the view, with the transport stopped and Duplicate held):
  * Duplicate + pad A (a slot with a project) = A is the source: it blinks yellow while its pack is loaded; Duplicate + A again forgets it;
  * with a source, Duplicate + pad B (in this pack or, after loading another pack, in that one) = the project is copied into B.  An empty B is
    written at once; a B that holds a project blinks white first and Duplicate + B again within ~5 s writes; the slot of the loaded project is
    never written; the internal pack (pack 0) is never written (rodisk: the Save LED red).  The file in 4 KB pieces through the shared buffer,
    then the storage task back on the loaded pack, and B marked in the stock's own list (its bit, A's colour), so the view shows it and loads
    it as any other; B shows green for ~1.5 s (red if the copy failed).  The source stays, for more copies, until the power goes.
State in our RAM (rhstate "sesscopy"): [0] tag [1] 0x80 | A [2] A's pack [3] 0x80 | the B asked about [4..5] the question's time [6] 0x80 |
the last B [7] its pack [8] A's colour [9] the last copy's status [10..11] its time (times = the HAL tick / 256, 16 bits).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, ands_reg, b, b_cond, bl, cmp_imm, cmp_reg, h, ldr_imm, ldrb_imm, ldrh_imm, lsls_imm,  # noqa: E402
                   lsls_reg, lsrs_imm, mov_reg, movs_imm, movt, movw, orrs_reg, pop_list, push_list, raw, str_imm, strb_imm, strh_imm,
                   strh_reg, sub_sp_imm, add_sp_imm, subs_reg, tst_reg, ldrb_w)
import countin as CI  # noqa: E402
import rhstate  # noqa: E402
import rodisk  # noqa: E402

CTRL, CTRL_VT = CI.CTRL, CI.CTRL_VT
O_VIEW, O_HELD, BIT_DUP = 0x7C, 0xA0, 24
PROJ_VT = 0x080679CC                         # its first word = slot 0 (the pads)
PAD_STOCK = 0x0804F09E
O_PAGE, O_PSTORE = 0x36, 0x20
P_LOADED, P_USED, P_COL = 11, 12, 16
PACKS_VIEW, PACKS_VT = 0x2004D7FC, 0x08067954   # [+ 0x10] p0 = the loaded pack
CUR_PACK_PTR = 0x20006E24
EXISTS, SIZE, READ, WRITE = 0x08045FB4, 0x08045FCE, 0x08046054, rodisk.WRITE
BUF_LOCK, BUF_UNLOCK, BUF, LOCK_OWNER = 0x0802EF6A, 0x0802EF98, 0x20003F94, 5
BUF_LDR = 0x0802EF94                         # the lock's `ldr r0, [pc, #n]`: the buffer it hands out
KIND_SESS = 2
FILE_SIZE = 0x29484
CHUNK_SHIFT = 12                             # 4 KB pieces (the shared buffer)
WPTR, COMMIT, PARAM_NEW = 0x0803FD26, 0x0803FBEC, CI.PARAM_NEW
TRANSPORT = CI.TRANSPORT
HAL_TICK = rodisk.HAL_TICK
LED_CALLS = CI.LED_CALLS
O_ST = rhstate.OFF["sesscopy"][0]
S_TAG, S_A, S_PA, S_ASK, S_ASKT, S_B, S_PB, S_COL, S_RES, S_REST = 0, 1, 2, 3, 4, 6, 7, 8, 9, 10
TAG = 0xC5
LIFE = 20                                    # the question stays open ~5 s (units of 256 ms)
SHOW = 6                                     # the result ~1.5 s
COL_SRC, COL_ASK, COL_OK, COL_BAD = 0x2F, 0x01, 0x1E, 0x55     # yellow, white, green, red (the Rhythm's codes: tools/rhpalette.py)
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
        n = f"_s{zc[0]}"
        E(b_cond, n, INV[cond])
        E(b, target)
        a.label(n)

    def tick(rd):                                                          # rd = the HAL tick / 256, 16 bits
        imm32(rd, HAL_TICK)
        E(ldr_imm, rd, rd, 0)
        E(lsrs_imm, rd, rd, 8)
        E(lsls_imm, rd, rd, 16)
        E(lsrs_imm, rd, rd, 16)

    def since(rd, rt, off):                                                # rd = (now - [rt + off]) & 0xFFFF; clobbers r1
        tick(rd)
        E(ldrh_imm, 1, rt, off)
        E(subs_reg, rd, rd, 1)
        E(lsls_imm, rd, rd, 16)
        E(lsrs_imm, rd, rd, 16)

    # ---- c_scst() -> r0 = our state (tagged on first use), 0 without our RAM; clobbers r1-r3
    a.label("c_scst")
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

    # ---- c_scok() -> r0 = 1 when the controller is the dump's; clobbers r1
    a.label("c_scok")
    imm32(0, CTRL)
    E(ldr_imm, 0, 0, 0)
    imm32(1, CTRL_VT)
    E(cmp_reg, 0, 1)
    E(movs_imm, 0, 0)
    E(b_cond, "ok_x", "ne")
    E(movs_imm, 0, 1)
    a.label("ok_x")
    E(raw, BX_LR)

    # ---- c_scon() -> r0 = the Projects view when it is the active view, else 0; clobbers r1, r2
    a.label("c_scon")
    E(push_list, [3], lr=True)
    E(bl, "c_scok")
    E(cmp_imm, 0, 0)
    E(b_cond, "on_x", "eq")
    imm32(0, CTRL)
    E(ldr_imm, 0, 0, O_VIEW)
    E(cmp_imm, 0, 0)
    E(b_cond, "on_x", "eq")
    E(ldr_imm, 1, 0, 0)
    imm32(2, PROJ_VT)
    E(cmp_reg, 1, 2)
    E(b_cond, "on_x", "eq")
    E(movs_imm, 0, 0)
    a.label("on_x")
    E(pop_list, [3], pc=True)

    # ---- c_scnew(r0 = store, r1 = parameter) -> r0 = its word (the newest copy, no side effects)
    a.label("c_scnew")
    E(push_list, [3], lr=True)
    E(bl, PARAM_NEW)
    E(ldr_imm, 0, 0, 0)
    E(pop_list, [3], pc=True)

    # ---- c_sccur() -> r0 = the loaded pack (p0 of the packs view's store; the storage task's current pack without that view)
    a.label("c_sccur")
    E(push_list, [4], lr=True)
    imm32(4, PACKS_VIEW)
    E(ldr_imm, 0, 4, 0)
    imm32(1, PACKS_VT)
    E(cmp_reg, 0, 1)
    E(b_cond, "cu_ff", "ne")
    E(ldr_imm, 0, 4, 0x10)
    E(movs_imm, 1, 0)
    E(bl, "c_scnew")
    E(lsls_imm, 0, 0, 24)
    E(lsrs_imm, 0, 0, 24)
    E(pop_list, [4], pc=True)
    a.label("cu_ff")
    imm32(0, CUR_PACK_PTR)
    E(ldr_imm, 0, 0, 0)
    E(ldrb_imm, 0, 0, 0)
    E(pop_list, [4], pc=True)

    # ---- c_scsize(r0 = slot, r1 = pack) -> r0 = the size of its file (0: no project there)
    a.label("c_scsize")
    E(push_list, [4], lr=True)
    E(sub_sp_imm, 16)
    E(movs_imm, 2, KIND_SESS)
    E(raw, h(0x9200))                                                      # str r2, [sp]
    E(raw, h(0x9001))                                                      # str r0, [sp, #4]
    E(raw, h(0x9102))                                                      # str r1, [sp, #8]
    E(mov_reg, 0, 13)
    E(bl, SIZE)
    E(add_sp_imm, 16)
    E(pop_list, [4], pc=True)

    # ---- c_scresel(r0 = pack): the storage task's current pack := that one (an operation on it: op 0 on its project 0)
    a.label("c_scresel")
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

    # ---- c_sccopy(r0 = slot A, r1 = its pack, r2 = slot B, r3 = its pack) -> r0 = status (0 = copied): the file in 4 KB pieces
    #      frame r7: [0] cb [4] ctx [8] &done [12] done [16..27] item A [28..39] item B [40] size [44] offset
    a.label("c_sccopy")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(sub_sp_imm, 48)
    E(mov_reg, 7, 13)
    E(str_imm, 0, 7, 20)
    E(str_imm, 1, 7, 24)
    E(str_imm, 2, 7, 32)
    E(str_imm, 3, 7, 36)
    E(movs_imm, 0, KIND_SESS)
    E(str_imm, 0, 7, 16)
    E(str_imm, 0, 7, 28)
    E(movs_imm, 0, 0)
    E(str_imm, 0, 7, 44)
    E(mov_reg, 0, 7)
    E(adds_imm8, 0, 16)
    E(bl, SIZE)
    E(str_imm, 0, 7, 40)
    imm32(1, FILE_SIZE)
    E(cmp_reg, 0, 1)
    E(b_cond, "cp_go", "eq")                                               # only a whole project of the Rhythm's size
    E(movs_imm, 6, 8)
    E(b, "cp_rs")                                                          # (the size asked A's pack: the storage task moved)
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
    a.label("cp_rs")
    E(bl, "c_sccur")
    E(bl, "c_scresel")
    E(mov_reg, 0, 6)
    E(add_sp_imm, 48)
    E(pop_list, [3, 4, 5, 6, 7], pc=True)

    # ---- c_sccol(r0 = the view's store, r1 = slot) -> r0 = the slot's colour in the stock's list; clobbers r1-r3
    a.label("c_sccol")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 1)
    E(lsrs_imm, 1, 1, 2)
    E(adds_imm8, 1, P_COL)
    E(bl, "c_scnew")
    E(movs_imm, 1, 3)
    E(ands_reg, 4, 1)
    E(lsls_imm, 4, 4, 3)
    E(raw, h(0x40E0))                                                      # lsrs r0, r4
    E(lsls_imm, 0, 0, 24)
    E(lsrs_imm, 0, 0, 24)
    E(pop_list, [4], pc=True)

    # ---- c_scmark(r0 = the view's store, r1 = slot, r2 = colour): the slot holds a project in the stock's list (its bit, its colour), committed
    a.label("c_scmark")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(mov_reg, 6, 2)
    E(lsrs_imm, 1, 5, 5)
    E(adds_imm8, 1, P_USED)
    E(bl, WPTR)
    E(movs_imm, 1, 31)
    E(ands_reg, 1, 5)
    E(movs_imm, 2, 1)
    E(lsls_reg, 2, 1)
    E(ldr_imm, 1, 0, 0)
    E(orrs_reg, 1, 2)
    E(str_imm, 1, 0, 0)
    E(mov_reg, 0, 4)
    E(lsrs_imm, 1, 5, 2)
    E(adds_imm8, 1, P_COL)
    E(bl, WPTR)
    E(movs_imm, 1, 3)
    E(ands_reg, 1, 5)
    E(raw, h(0x5446))                                                      # strb r6, [r0, r1]
    E(mov_reg, 0, 4)
    E(bl, COMMIT)
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_scpad (the view's slot 0: view, pad, velocity): Duplicate held (stopped) = the source, then the copies
    a.label("c_scpad")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(cmp_imm, 5, 32)
    bc("sp_f", "hs")
    E(bl, "c_scok")
    E(cmp_imm, 0, 0)
    bc("sp_f", "eq")
    imm32(0, CTRL + O_HELD)
    E(ldr_imm, 0, 0, 0)
    E(lsls_imm, 0, 0, 31 - BIT_DUP)
    bc("sp_f", "pl")                                                       # Duplicate not held: the stock's
    E(bl, "c_scst")
    E(mov_reg, 7, 0)
    E(cmp_imm, 7, 0)
    bc("sp_f", "eq")
    imm32(0, TRANSPORT)
    E(movs_imm, 1, 0)
    E(bl, "c_scnew")
    E(lsls_imm, 0, 0, 24)
    bc("sp_e", "ne")                                                       # playing: nothing (no card access while it plays)
    E(ldrb_w, 0, 4, O_PAGE)
    E(lsls_imm, 0, 0, 5)
    E(adds_reg, 5, 5, 0)                                                   # r5 = the slot
    E(cmp_imm, 5, 64)
    bc("sp_e", "hs")
    E(bl, "c_sccur")
    E(mov_reg, 6, 0)                                                       # r6 = the loaded pack
    E(ldrb_imm, 0, 7, S_A)
    E(movs_imm, 1, 0x80)
    E(tst_reg, 0, 1)
    bc("sp_src", "eq")
    E(movs_imm, 1, 0x7F)
    E(ands_reg, 0, 1)
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
    E(ldr_imm, 0, 4, O_PSTORE)
    E(movs_imm, 1, P_LOADED)
    E(bl, "c_scnew")
    E(lsls_imm, 0, 0, 24)
    E(lsrs_imm, 0, 0, 24)
    E(cmp_reg, 0, 5)
    bc("sp_e", "eq")                                                       # never the loaded project
    E(mov_reg, 0, 5)
    E(mov_reg, 1, 6)
    E(bl, "c_scsize")
    E(cmp_imm, 0, 0)
    E(b_cond, "sp_go", "eq")                                               # an empty B: at once
    E(movs_imm, 0, 0x80)
    E(orrs_reg, 0, 5)
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
    E(movs_imm, 1, 0x7F)
    E(ands_reg, 0, 1)
    E(ldrb_imm, 1, 7, S_PA)
    E(mov_reg, 2, 5)
    E(mov_reg, 3, 6)
    E(bl, "c_sccopy")
    E(strb_imm, 0, 7, S_RES)
    E(movs_imm, 1, 0x80)
    E(orrs_reg, 1, 5)
    E(strb_imm, 1, 7, S_B)
    E(strb_imm, 6, 7, S_PB)
    tick(1)
    E(strh_imm, 1, 7, S_REST)
    E(cmp_imm, 0, 0)
    bc("sp_e", "ne")
    E(ldr_imm, 0, 4, O_PSTORE)                                             # B in the stock's list
    E(mov_reg, 1, 5)
    E(ldrb_imm, 2, 7, S_COL)
    E(bl, "c_scmark")
    E(b, "sp_e")
    a.label("sp_ask")
    E(movs_imm, 0, 0x80)
    E(orrs_reg, 0, 5)
    E(strb_imm, 0, 7, S_ASK)
    tick(0)
    E(strh_imm, 0, 7, S_ASKT)
    E(b, "sp_e")
    a.label("sp_src")
    E(mov_reg, 0, 5)
    E(mov_reg, 1, 6)
    E(bl, "c_scsize")
    E(cmp_imm, 0, 0)
    E(b_cond, "sp_e", "eq")                                                # an empty slot is no source
    E(ldr_imm, 0, 4, O_PSTORE)
    E(mov_reg, 1, 5)
    E(bl, "c_sccol")
    E(strb_imm, 0, 7, S_COL)
    E(movs_imm, 0, 0x80)
    E(orrs_reg, 0, 5)
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

    # ---- c_scput(r0 = 0x80 | slot or 0, r1 = colour; r4 = the view, r5 = the frame): that pad of the page shown; clobbers r0, r2, r3
    a.label("c_scput")
    E(movs_imm, 2, 0x80)
    E(tst_reg, 0, 2)
    E(b_cond, "pt_x", "eq")
    E(movs_imm, 2, 0x7F)
    E(ands_reg, 0, 2)
    E(lsrs_imm, 2, 0, 5)
    E(ldrb_w, 3, 4, O_PAGE)
    E(cmp_reg, 2, 3)
    E(b_cond, "pt_x", "ne")
    E(movs_imm, 2, 31)
    E(ands_reg, 0, 2)
    E(lsls_imm, 0, 0, 1)
    E(strh_reg, 1, 5, 0)
    a.label("pt_x")
    E(raw, BX_LR)

    # ---- c_scblink(r1 = colour) -> r1 = the colour or 0 (dark), blinking ~4 times a second; clobbers r2, r3
    a.label("c_scblink")
    imm32(2, HAL_TICK)
    E(ldr_imm, 2, 2, 0)
    E(lsrs_imm, 2, 2, 7)
    E(movs_imm, 3, 1)
    E(tst_reg, 2, 3)
    E(b_cond, "bl_x", "eq")
    E(movs_imm, 1, 0)
    a.label("bl_x")
    E(raw, BX_LR)

    # ---- c_scled (the LED task's calls: r0 = ctrl, r1 = frame): the chain, then on the Projects view: the source, the question, the result
    a.label("c_scled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)
    E(bl, prev["ledtask"])
    E(bl, "c_scon")
    E(mov_reg, 4, 0)
    E(cmp_imm, 4, 0)
    bc("lt_x", "eq")
    E(bl, "c_scst")
    E(mov_reg, 7, 0)
    E(cmp_imm, 7, 0)
    bc("lt_x", "eq")
    E(bl, "c_sccur")
    E(mov_reg, 6, 0)
    E(ldrb_imm, 0, 7, S_PA)                                                # the source, blinking yellow, in its pack
    E(cmp_reg, 0, 6)
    E(b_cond, "lt_q", "ne")
    E(movs_imm, 1, COL_SRC)
    E(bl, "c_scblink")
    E(ldrb_imm, 0, 7, S_A)
    E(bl, "c_scput")
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
    E(bl, "c_scblink")
    E(ldrb_imm, 0, 7, S_ASK)
    E(bl, "c_scput")
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
    E(bl, "c_scput")
    a.label("lt_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; the Projects view's slot 0 and the two LED task calls."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda ad: struct.unpack_from("<I", img, ad - BASE)[0]
    ins = struct.unpack_from("<H", img, BUF_LDR - BASE)[0]
    assert ins & 0xFF00 == 0x4800, hex(ins)                                # ldr r0, [pc, #n]
    assert u(((BUF_LDR + 4) & ~3) + 4 * (ins & 0xFF)) == BUF               # the buffer the lock hands out
    L = dict(c_rst=int(report["rhstate"]["labels"]["c_rst"], 16))
    prev = dict(pad=u(PROJ_VT) & ~1, ledtask=rhbuild.bl_target(img, LED_CALLS[0]))
    assert prev["pad"] == PAD_STOCK, hex(prev["pad"])
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in LED_CALLS)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch_word(img, PROJ_VT, PAD_STOCK | 1, labels["c_scpad"] | 1)
    for c in LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_scled"]))
    report["sesscopy"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
