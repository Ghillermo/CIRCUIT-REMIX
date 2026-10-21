"""Remote diagnostics of the Circuit Rhythm over USB SysEx (MIT; the CIRCUIT-HACKS rdiag of SC35D8 moved to the Rhythm 5706), driven from the PC
with tools/rhremote.py: ping, RAM / flash reads (the RAM dump the emulation tests start from), and the stock content API of the storage task.

Hook: the incoming SysEx dispatcher 0x08026DE8(port, msg = {buf, len}, x) (Tracks 0x0801EB30, the same code).  Its first 4 bytes
(push.w {r4-r8, lr}) become `b.w c_rdin`: a message that starts with SIG (F0 7D 43 54: 7D = the non-commercial manufacturer id, no stock
handler answers it) is ours; anything else runs the original prologue and goes on at 0x08026DEC.

Request  F0 7D 43 54 cmd seq payload.. F7      Reply  F0 7D 43 54 cmd|0x40 seq payload.. F7 (through the stock SysEx output router
0x080298B8, as the identity responder 0x08026F0C does).  Numbers travel as 8 nibbles, bytes as 2 nibbles; the PC pads every request
to PAD bytes and the reply is built in the request buffer.  Commands (status 0 = done):
  1 ping                                  -> VERSION, port
  2 mem   addr32 len(1 byte, <= NMAX)     -> status (1 = outside flash 0x08000000-0x0807FFFF / RAM 0x20000000-0x2004FFFF), the bytes
  4 info  kind idx pack                   -> exists (op 0), size (op 1)          (the storage task's content API: 0x08045FB4 / 0x08045FCE /
  5 read  kind idx pack off32 len         -> status, done, the bytes (op 6)       0x08046054 / 0x0804607A, the Tracks functions moved)
  6 write kind idx pack off32 len data    -> status (op 7)                        -- writes to the SD card: only with the user's go-ahead
  3 dspr  core addr32 n (<= NR)           -> status (1 = no such core), n DSP words (6 nibbles each)    (dsp=True only: RD3, the DSP tests)
  9 dspw  core addr32 value32             -> status                                                       (dsp=True only)
    The DSP address is the Rhythm's host address: X:a = a, Y:a = a | 0x8000, bits 16-17 = the other spaces (0x30000 + 4 n = the sample
    table, 0x371D2 = the sample memory's free pointer); read with 0x080314D6(core, addr) -> word << 8, written with 0x08031228(core,
    value << 8, addr): the stock's own accessors, which take the DSP service's lock (0x08029C8C on 0x20003688).  A write changes the DSP's
    RAM only (gone at the next power-up or program upload).
    dsp=2 (RD4): below 0x10000 the stock's 16-bit accessors instead, 0x08031268(core, addr) (command 0x80, under the same lock) and
    0x08031200(core, value << 8, addr) (command 0x00, the master sender's): the DSP's host handler (core 0 P:$158) takes bit 15 of a
    16-bit command as the space (Y) and the address as addr & 0x7FFF, while the wide commands 0x88 / 0x08 keep bit 15 in the address
    (0x810A = Y:$810A, not Y:$10A: seen on the device with RD3, 2026-10-19) and 0x08 leaves the space of the previous command.  The host
    port has no P space.
The Tracks-only commands (DSP memory, the DWT watchpoint) are not built here: they stay in CIRCUIT-HACKS.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, b, b_cond, b_w, bl, cmp_imm, cmp_reg, ldr_imm, ldrb_imm, ldrb_reg, lsls_imm, lsrs_imm, mov_reg, movs_imm, movt, movw,  # noqa: E402
                   adds_imm8, subs_imm8, pop_list, push_list, raw, h, ands_reg, adds_reg, subs_reg, str_imm, strb_imm, strb_reg, add_sp_imm, sub_sp_imm,
                   orrs_reg, tst_reg, str_sp)

HOOK = 0x08026DE8
HOOK_CONT = HOOK + 4
PROLOGUE = bytes.fromhex("2de9f041")             # push.w {r4, r5, r6, r7, r8, lr}
ROUTER = 0x080298B8                              # the stock SysEx output (router, port mask, &{buf, len}), as the identity responder 0x08026F0C calls it
ROUTER_LIT = 0x08027088                          # word that holds the address of the router pointer (0x08026F1E: ldr r0, [pc, #0x168]; ldr r0, [r0])
EXISTS, SIZE, READ, WRITE = 0x08045FB4, 0x08045FCE, 0x08046054, 0x0804607A
DELETE = False                                   # command 7 = delete an item (op 5, 0x08046098(item, 0, 0) synchronous); kinds 2-6 only (kind 1 = a whole pack:
DEL_FN = 0x08046098                              #   refused with status 0xFFFFFFFE); the storage task closes the file, unlinks it and re-indexes the pack
DEL_PACK = False                                 # command 7 with kind 1 = delete a whole pack: not ported (needs the Rhythm's current-pack pointer)
SIG = (0xF0, 0x7D, 0x43, 0x54)
VERSION = 0x5201
NMAX = 64
RAW = 160                                        # offset of the raw byte area in the request buffer (read / write)
PAD = 232                                        # every request is padded to this length (>= RAW + NMAX + some slack)
DSP_READ, DSP_WRITE = 0x080314D6, 0x08031228
DSP_RD16, DSP_WR16 = 0x08031268, 0x08031200     # (dsp=2) 16-bit host commands 0x80 / 0x00
DSP_LOCK, DSP_UNLOCK, DSP_WADDR = 0x08029C8C, 0x08030EB8, 0x20003684   # the service's lock (byte at DSP_WADDR + 4), the cached write address
NR = 24                                          # DSP words per dspr
FLASH = (0x08000000, 0x08080000)
RAM = (0x20000000, 0x20050000)
INV = {"eq": "ne", "ne": "eq", "lo": "hs", "hs": "lo", "hi": "ls", "ls": "hi"}


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def arm_code(base, router_ptr, dsp=False):
    a = Asm(base)
    zc = [0]

    def bc(target, cond):
        zc[0] += 1; n = f"_r{zc[0]}"
        a.emit(b_cond, n, INV[cond]); a.emit(b, target); a.label(n)

    def imm32(rd, v): a.emit(movw, rd, v & 0xFFFF); a.emit(movt, rd, v >> 16)

    # ---- c_rdin: the hooked entry (r0 = port, r1 = msg {buf, len}, r2)
    a.label("c_rdin")
    a.emit(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    a.emit(ldr_imm, 4, 1, 0); a.emit(ldr_imm, 5, 1, 4)                          # r4 = buf, r5 = len
    a.emit(cmp_imm, 5, 8); bc("ri_fwd", "lo")
    for i, v in enumerate(SIG):
        a.emit(ldrb_imm, 3, 4, i); a.emit(cmp_imm, 3, v); bc("ri_fwd", "ne")
    a.emit(mov_reg, 6, 0)                                                      # r6 = port
    a.emit(bl, "c_rdcmd")
    a.emit(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)                           # swallowed
    a.label("ri_fwd")
    a.emit(raw, popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    a.emit(raw, PROLOGUE)
    a.emit(b_w, HOOK_CONT)

    # ---- c_g32 (r0 = ptr) -> r0 = u32 from 8 nibbles; clobbers r1-r3
    a.label("c_g32")
    a.emit(movs_imm, 1, 0); a.emit(movs_imm, 2, 8)
    a.label("g32_l")
    a.emit(ldrb_imm, 3, 0, 0); a.emit(adds_imm8, 0, 1); a.emit(lsls_imm, 1, 1, 4)
    a.emit(lsls_imm, 3, 3, 28); a.emit(lsrs_imm, 3, 3, 28); a.emit(orrs_reg, 1, 3)
    a.emit(subs_imm8, 2, 1); a.emit(b_cond, "g32_l", "ne")
    a.emit(mov_reg, 0, 1); a.emit(raw, h(0x4770))

    # ---- c_p32 (r0 = ptr, r1 = value) -> 8 nibbles, r0 = ptr + 8; clobbers r2, r3
    a.label("c_p32")
    a.emit(movs_imm, 2, 8)
    a.label("p32_l")
    a.emit(lsrs_imm, 3, 1, 28); a.emit(strb_imm, 3, 0, 0); a.emit(adds_imm8, 0, 1); a.emit(lsls_imm, 1, 1, 4)
    a.emit(subs_imm8, 2, 1); a.emit(b_cond, "p32_l", "ne")
    a.emit(raw, h(0x4770))

    # ---- c_pbytes (r0 = dst, r1 = src, r2 = n) -> 2 nibbles per byte, r0 = dst end; clobbers r1-r3
    a.label("c_pbytes")
    a.emit(cmp_imm, 2, 0); a.emit(b_cond, "pb_x", "eq")
    a.label("pb_l")
    a.emit(ldrb_imm, 3, 1, 0); a.emit(adds_imm8, 1, 1)
    a.emit(push_list, [3]); a.emit(lsrs_imm, 3, 3, 4); a.emit(strb_imm, 3, 0, 0); a.emit(pop_list, [3])
    a.emit(lsls_imm, 3, 3, 28); a.emit(lsrs_imm, 3, 3, 28); a.emit(strb_imm, 3, 0, 1); a.emit(adds_imm8, 0, 2)
    a.emit(subs_imm8, 2, 1); a.emit(b_cond, "pb_l", "ne")
    a.label("pb_x"); a.emit(raw, h(0x4770))

    # ---- c_gbytes (r0 = dst, r1 = src nibbles, r2 = n); clobbers r1-r3
    a.label("c_gbytes")
    a.emit(cmp_imm, 2, 0); a.emit(b_cond, "gb_x", "eq")
    a.emit(push_list, [4])
    a.label("gb_l")
    a.emit(ldrb_imm, 3, 1, 0); a.emit(lsls_imm, 3, 3, 28); a.emit(lsrs_imm, 3, 3, 24)
    a.emit(ldrb_imm, 4, 1, 1); a.emit(lsls_imm, 4, 4, 28); a.emit(lsrs_imm, 4, 4, 28); a.emit(orrs_reg, 3, 4)
    a.emit(strb_imm, 3, 0, 0); a.emit(adds_imm8, 0, 1); a.emit(adds_imm8, 1, 2)
    a.emit(subs_imm8, 2, 1); a.emit(b_cond, "gb_l", "ne")
    a.emit(pop_list, [4])
    a.label("gb_x"); a.emit(raw, h(0x4770))

    # ---- c_rdcmd (r4 = buf, r5 = len, r6 = port): the reply is written over buf; r7 = write pointer
    a.label("c_rdcmd")
    a.emit(cmp_imm, 5, PAD - 4); a.emit(b_cond, "rc_go", "hs"); a.emit(raw, h(0x4770))     # not padded: no reply
    a.label("rc_go")
    a.emit(push_list, [4, 5, 6, 7], lr=True)
    a.emit(sub_sp_imm, 40); a.emit(mov_reg, 7, 13)                             # frame: [0] cb [4] ctx [8] &done [12] done [16..27] item [32] msg {buf, len}
    a.emit(movs_imm, 0, 0)
    for o in range(0, 40, 4): a.emit(str_imm, 0, 7, o)
    a.emit(ldrb_imm, 0, 4, 4); a.emit(movs_imm, 1, 0x40); a.emit(orrs_reg, 1, 0); a.emit(strb_imm, 1, 4, 4)   # cmd | 0x40 (r0 = cmd)
    a.emit(push_list, [0]); a.emit(mov_reg, 0, 4); a.emit(adds_imm8, 0, 6); a.emit(mov_reg, 1, 0); a.emit(pop_list, [0])  # r1 = payload pointer
    for cmd, lab in ((1, "rc_ping"), (2, "rc_mem"), (4, "rc_info"), (5, "rc_read"), (6, "rc_write")) + (((7, "rc_del"),) if DELETE else ())             + (((3, "rc_dspr"), (9, "rc_dspw")) if dsp else ()):
        a.emit(cmp_imm, 0, cmd); bc(lab, "eq")
    a.emit(mov_reg, 0, 1); imm32(1, 0xFFFFFFFF); a.emit(bl, "c_p32"); a.emit(b, "rc_send")   # unknown command: status -1

    a.label("rc_ping")
    a.emit(mov_reg, 0, 1); imm32(1, VERSION + (1 if DELETE else 0) + (0x10 if dsp else 0) + (0x02 if dsp == 2 else 0) + (0x20 if DEL_PACK else 0)); a.emit(bl, "c_p32")
    a.emit(mov_reg, 1, 6); a.emit(bl, "c_p32"); a.emit(b, "rc_send")

    def item_from(off):                          # the item {kind, idx, pack} from buf[off..off+2] into the frame; pack 0x7F -> 0xFF
        a.emit(ldrb_imm, 0, 4, off); a.emit(str_imm, 0, 7, 16)
        a.emit(ldrb_imm, 0, 4, off + 1); a.emit(str_imm, 0, 7, 20)
        a.emit(ldrb_imm, 0, 4, off + 2); a.emit(cmp_imm, 0, 0x7F); zc[0] += 1; n = f"_pk{zc[0]}"
        a.emit(b_cond, n, "ne"); a.emit(movs_imm, 0, 0xFF); a.label(n); a.emit(strb_imm, 0, 7, 24)

    def item_ptr(rd): a.emit(mov_reg, rd, 7); a.emit(adds_imm8, rd, 16)

    def raw_ptr(rd): a.emit(mov_reg, rd, 4); a.emit(adds_imm8, rd, RAW)

    def clamp_n(off, rd):                        # rd = min(buf[off], NMAX)
        a.emit(ldrb_imm, rd, 4, off); a.emit(cmp_imm, rd, NMAX); zc[0] += 1; n = f"_cl{zc[0]}"
        a.emit(b_cond, n, "ls"); a.emit(movs_imm, rd, NMAX); a.label(n)

    # mem: addr = g32(buf + 6), n = buf[14]
    a.label("rc_mem")
    a.emit(mov_reg, 0, 4); a.emit(adds_imm8, 0, 6); a.emit(bl, "c_g32"); a.emit(push_list, [0])     # [sp] = addr
    clamp_n(14, 2); a.emit(pop_list, [1])                                     # r1 = addr, r2 = n
    a.emit(adds_reg, 3, 1, 2)                                                  # r3 = end
    for k, (lo, hi) in enumerate((FLASH, RAM)):
        imm32(0, lo); a.emit(cmp_reg, 1, 0); bc(f"mm_n{k}", "lo")
        imm32(0, hi); a.emit(cmp_reg, 3, 0); bc(f"mm_n{k}", "hi")
        a.emit(b, "mm_ok")
        a.label(f"mm_n{k}")
    a.emit(mov_reg, 0, 4); a.emit(adds_imm8, 0, 6); a.emit(movs_imm, 1, 1); a.emit(bl, "c_p32"); a.emit(b, "rc_send")
    a.label("mm_ok")
    a.emit(push_list, [1, 2])
    a.emit(mov_reg, 0, 4); a.emit(adds_imm8, 0, 6); a.emit(movs_imm, 1, 0); a.emit(bl, "c_p32")
    a.emit(pop_list, [1, 2]); a.emit(bl, "c_pbytes"); a.emit(b, "rc_send")

    # info: exists, size
    a.label("rc_info")
    item_from(6)
    item_ptr(0); a.emit(bl, EXISTS); a.emit(mov_reg, 1, 0); a.emit(mov_reg, 0, 4); a.emit(adds_imm8, 0, 6); a.emit(bl, "c_p32"); a.emit(push_list, [0])
    item_ptr(0); a.emit(bl, SIZE); a.emit(mov_reg, 1, 0); a.emit(pop_list, [0]); a.emit(bl, "c_p32"); a.emit(b, "rc_send")

    # read: item, off = g32(buf + 9), n = buf[17] -> status, done, bytes
    a.label("rc_read")
    item_from(6)
    a.emit(mov_reg, 0, 4); a.emit(adds_imm8, 0, 9); a.emit(bl, "c_g32"); a.emit(mov_reg, 1, 0)       # r1 = offset
    clamp_n(17, 3); a.emit(str_imm, 3, 7, 36)                                 # n kept at [36]
    a.emit(mov_reg, 0, 7); a.emit(adds_imm8, 0, 12); a.emit(str_imm, 0, 7, 8)    # &done
    item_ptr(0); raw_ptr(2)
    a.emit(bl, READ)
    a.emit(mov_reg, 1, 0); a.emit(mov_reg, 0, 4); a.emit(adds_imm8, 0, 6); a.emit(bl, "c_p32")
    a.emit(ldr_imm, 1, 7, 12); a.emit(bl, "c_p32")
    raw_ptr(1); a.emit(ldr_imm, 2, 7, 12); a.emit(ldr_imm, 3, 7, 36); a.emit(cmp_reg, 2, 3); zc[0] += 1
    a.emit(b_cond, f"_dn{zc[0]}", "ls"); a.emit(mov_reg, 2, 3); a.label(f"_dn{zc[0]}")
    a.emit(bl, "c_pbytes"); a.emit(b, "rc_send")

    # write: item, off = g32(buf + 9), n = buf[17], data nibbles from buf + 18 -> status
    a.label("rc_write")
    item_from(6)
    clamp_n(17, 2); a.emit(str_imm, 2, 7, 36)
    raw_ptr(0); a.emit(mov_reg, 1, 4); a.emit(adds_imm8, 1, 18); a.emit(bl, "c_gbytes")
    a.emit(mov_reg, 0, 4); a.emit(adds_imm8, 0, 9); a.emit(bl, "c_g32"); a.emit(mov_reg, 1, 0)
    item_ptr(0); raw_ptr(2); a.emit(ldr_imm, 3, 7, 36)
    a.emit(bl, WRITE)
    a.emit(mov_reg, 1, 0); a.emit(mov_reg, 0, 4); a.emit(adds_imm8, 0, 6); a.emit(bl, "c_p32"); a.emit(b, "rc_send")

    if DELETE:
        # delete: kinds 2-6 only
        a.label("rc_del")
        item_from(6)
        a.emit(ldr_imm, 0, 7, 16); a.emit(subs_imm8, 0, 2); a.emit(cmp_imm, 0, 4); bc("rd_bad", "hi")
        item_ptr(0); a.emit(movs_imm, 1, 0); a.emit(movs_imm, 2, 0); a.emit(bl, DEL_FN)
        a.emit(mov_reg, 1, 0); a.emit(mov_reg, 0, 4); a.emit(adds_imm8, 0, 6); a.emit(bl, "c_p32"); a.emit(b, "rc_send")
        a.label("rd_bad")
        a.emit(mov_reg, 0, 4); a.emit(adds_imm8, 0, 6); imm32(1, 0xFFFFFFFE); a.emit(bl, "c_p32"); a.emit(b, "rc_send")

    if dsp:
        def core_addr():                         # [28] = core (buf[6]), [16] = addr (g32(buf + 7)); a core above 1 -> status 1
            a.emit(ldrb_imm, 0, 4, 6); a.emit(str_imm, 0, 7, 28); a.emit(cmp_imm, 0, 1); bc("ds_bad", "hi")
            a.emit(mov_reg, 0, 4); a.emit(adds_imm8, 0, 7); a.emit(bl, "c_g32"); a.emit(str_imm, 0, 7, 16)

        # dspr: core, addr, n = buf[15] (<= NR) -> status 0, n words as 6 nibbles
        a.label("rc_dspr")
        core_addr()
        a.emit(ldrb_imm, 0, 4, 15); a.emit(cmp_imm, 0, NR); a.emit(b_cond, "dr_nr", "ls"); a.emit(movs_imm, 0, NR)
        a.label("dr_nr"); a.emit(str_imm, 0, 7, 20)
        a.emit(mov_reg, 0, 4); a.emit(adds_imm8, 0, 6); a.emit(movs_imm, 1, 0); a.emit(bl, "c_p32"); a.emit(str_imm, 0, 7, 24)
        a.label("dr_l")
        a.emit(ldr_imm, 0, 7, 20); a.emit(cmp_imm, 0, 0); bc("dr_x", "eq"); a.emit(subs_imm8, 0, 1); a.emit(str_imm, 0, 7, 20)
        a.emit(ldr_imm, 0, 7, 28); a.emit(ldr_imm, 1, 7, 16)
        if dsp == 2:
            a.emit(movs_imm, 2, 1); a.emit(lsls_imm, 2, 2, 16); a.emit(cmp_reg, 1, 2); a.emit(b_cond, "dr_w", "hs")
            a.emit(bl, "c_d16r"); a.emit(b, "dr_got")
            a.label("dr_w")
        a.emit(bl, DSP_READ)
        a.label("dr_got"); a.emit(lsrs_imm, 1, 0, 8)
        a.emit(ldr_imm, 0, 7, 16); a.emit(adds_imm8, 0, 1); a.emit(str_imm, 0, 7, 16)
        a.emit(ldr_imm, 0, 7, 24); a.emit(lsls_imm, 1, 1, 8); a.emit(bl, "c_p32"); a.emit(subs_imm8, 0, 2); a.emit(str_imm, 0, 7, 24)   # 6 nibbles
        a.emit(b, "dr_l")
        a.label("dr_x")
        a.emit(ldr_imm, 0, 7, 24); a.emit(b, "rc_send")

        # dspw: core, addr, value = g32(buf + 15) -> status 0
        a.label("rc_dspw")
        core_addr()
        a.emit(mov_reg, 0, 4); a.emit(adds_imm8, 0, 15); a.emit(bl, "c_g32"); a.emit(lsls_imm, 1, 0, 8)
        a.emit(ldr_imm, 0, 7, 28); a.emit(ldr_imm, 2, 7, 16)
        if dsp == 2:
            a.emit(movs_imm, 3, 1); a.emit(lsls_imm, 3, 3, 16); a.emit(cmp_reg, 2, 3); a.emit(b_cond, "dw_w", "hs")
            a.emit(bl, DSP_WR16); a.emit(b, "dw_x")                              # (takes the lock itself)
            a.label("dw_w")
        a.emit(bl, DSP_WRITE)
        a.label("dw_x")
        a.emit(mov_reg, 0, 4); a.emit(adds_imm8, 0, 6); a.emit(movs_imm, 1, 0); a.emit(bl, "c_p32"); a.emit(b, "rc_send")
        a.label("ds_bad")
        a.emit(mov_reg, 0, 4); a.emit(adds_imm8, 0, 6); a.emit(movs_imm, 1, 1); a.emit(bl, "c_p32"); a.emit(b, "rc_send")

    if dsp == 2:
        # ---- c_d16r (r0 = core, r1 = addr < 0x10000) -> r0 = word << 8: 0x08031268 under the lock, as 0x080314D6 runs its own body;
        #      the cached write address is dropped (the DSP's pointer moved)
        a.label("c_d16r")
        a.emit(push_list, [4, 5, 6], lr=True); a.emit(sub_sp_imm, 8)
        a.emit(mov_reg, 4, 0); a.emit(mov_reg, 5, 1)
        imm32(6, DSP_WADDR); a.emit(mov_reg, 0, 6); a.emit(adds_imm8, 0, 4); a.emit(str_sp, 0, 0); a.emit(mov_reg, 1, 0)
        a.emit(bl, DSP_LOCK)
        a.emit(mov_reg, 0, 4); a.emit(mov_reg, 1, 5); a.emit(bl, DSP_RD16); a.emit(mov_reg, 5, 0)
        a.emit(movw, 0, 0xFFFF); a.emit(str_imm, 0, 6, 0)
        a.emit(mov_reg, 0, 13); a.emit(bl, DSP_UNLOCK)
        a.emit(mov_reg, 0, 5); a.emit(add_sp_imm, 8); a.emit(pop_list, [4, 5, 6], pc=True)

    # r0 = end of the payload: F7, then send {buf, end + 1 - buf} to the port it came from
    a.label("rc_send")
    a.emit(movs_imm, 1, 0xF7); a.emit(strb_imm, 1, 0, 0); a.emit(adds_imm8, 0, 1); a.emit(subs_reg, 0, 0, 4)
    a.emit(str_imm, 4, 7, 32); a.emit(str_imm, 0, 7, 36)
    imm32(0, router_ptr); a.emit(ldr_imm, 0, 0, 0)                             # r0 = the router
    a.emit(movs_imm, 1, 1); a.emit(raw, h(0x40B1))                             # lsls r1, r6 -> mask = 1 << port
    a.emit(mov_reg, 2, 7); a.emit(adds_imm8, 2, 32)
    a.emit(bl, ROUTER)
    a.emit(add_sp_imm, 40); a.emit(pop_list, [4, 5, 6, 7], pc=True)

    return a.assemble()


def install(img, report, base_addr, dsp=False):
    """Append the code; the first 4 bytes of the incoming SysEx dispatcher -> b.w c_rdin.  dsp=True: the DSP commands 3 / 9 (RD3)."""
    import struct
    import rh_fw
    BASE = rh_fw.APP_BASE
    assert not DEL_PACK
    assert bytes(img[HOOK - BASE:HOOK - BASE + 4]) == PROLOGUE, img[HOOK - BASE:HOOK - BASE + 4].hex()
    router_ptr = struct.unpack_from("<I", img, ROUTER_LIT - BASE)[0]
    if dsp:
        heads = [(DSP_READ, "push {r2, r3, r4, r5, r6, lr}|mov r5, r1"), (DSP_WRITE, "push {r3, r4, r5, r6, r7, lr}|mov r5, r1")]
        if dsp == 2:
            heads += [(DSP_RD16, "push {r3, r4, r5, lr}|mov r4, r0"), (DSP_WR16, "push {r2, r3, r4, r5, r6, lr}|mov r4, r0"),
                      (DSP_LOCK, "push {r4, lr}|mov r4, r0"), (DSP_UNLOCK, "ldr r2, [r0]|ldrexb r1, [r2]|ldrb r3, [r2, #1]")]
        for fn, head in heads:
            import rhbuild
            n = 8 if fn == DSP_UNLOCK else 4
            assert "|".join(rhbuild.disasm(bytes(img[fn - BASE:fn - BASE + n]), fn)) == head, hex(fn)
    code, labels = arm_code(base_addr, router_ptr, dsp)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    img[HOOK - BASE:HOOK - BASE + 4] = b_w(HOOK, labels["c_rdin"])
    report["rdiag"] = dict(hook=hex(HOOK), router_ptr=hex(router_ptr), version=hex(VERSION + (0x10 if dsp else 0) + (0x02 if dsp == 2 else 0)), dsp=dsp, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
