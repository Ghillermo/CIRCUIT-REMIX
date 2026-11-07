"""Each project's synth sounds on the card, in its pack's patch bank (MIT; RH79; the user, 2026-11-06: «Card storage first»: the room the
VA's OSC 1 / OSC 2 pages need, and the 8-operator FM's 216 parameters, which lived only in core 0 until a project was loaded or the power went;
docs/DISENO_FM8.md § 4, «el sonido de cada proyecto»).

The stock of the Rhythm (read in the firmware; docs/PORTADO.md «Bancos de patches en el Rhythm»):
  * the content API's kind 3 = `Patches/NN_PATCHBANK.cpb`, 8 a pack (index 0-7); a write past the end makes the file longer (the gap is not
    cleared), one inside writes in place; the files survive a pack change and the power;
  * the project is saved by two calls of the session object, 0x08037FD6 (bl 0x080472E2) and 0x08038734 (bl 0x08047270), r1 = the item
    {kind 2, index = the slot, pack}; both queue the stock's write with a callback (they do not wait); some arguments are on the stack
    (a hook must not move sp before it hands over: ours works, then b.w);
  * after a load the session object's «apply the record» ends at 0x080379AE (b.w; mfsess', patchain's and sckn's hooks chained there); the
    loaded project = p11 of the store 0x20012478; the content API's calls from our code wait for the storage task (sesscopy).

Ours (the record of project p: bank p >> 3 of the pack, at OFF0 + 2048 (p & 7), REC_LEN bytes; before it, Hacks' 8 KB of patches untouched;
a gap before our offset filled with 0xFF, as Hacks):
  * [0] "R" [1] "S" [2] VER [3] the check (CHECK0 XOR the bytes 4 .. REC_LEN - 1); per synth slot s at 4 + SLOT s: [0] its track + 1 (as the
    project's synth block), [1] flags (bit 0 FM on), [2 .. 31] the VA's own (RH80; zeros), [32 .. 247] the FM's 216 parameters (fm8page's,
    read from core 0);
  * at a save (both calls; not before the controller is up, c_ciok, as autoinit's bootok; not on the internal pack, read-only for the mod),
    the record written before the stock's own write is queued (the 4 KB shared buffer under its lock, the gap first);
  * after a load (the apply hook sets our flag), the LED task (core 0 / 1 up: cthresh READY) reads the loaded project's record: each slot whose
    track matches the project's synth block gets its FM back (on, the 216 parameters to core 0, valid: no E.Piano, not keyed: fm8page makes
    its words from zero); every other slot's FM off (a project without a record: the internal pack, one saved before RH79, one copied).
RAM: rhstate "projsnd" [0] PEND (a load to apply), [1] the last status (0 ok, 1 written, 2 no record, 3 the internal pack, 4 a card error).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, add_sp_imm, adds_imm8, adds_reg, b, b_cond, b_w, bl, cmp_imm, cmp_reg, eors_reg, h, ldr_imm, ldrb_imm, ldrb_reg,  # noqa: E402
                   lsls_imm, lsls_reg, lsrs_imm, mov_reg, movs_imm, movt, movw, orrs_reg, pop_list, push_list, raw, str_imm, strb_imm,
                   strb_reg, sub_sp_imm, subs_reg, bics_reg, ldr_sp, ldrb_w)
import countin as CI  # noqa: E402
import cthresh as TH  # noqa: E402
import mfsess as MF  # noqa: E402
import rhstate  # noqa: E402
import rodisk  # noqa: E402
import sesscopy as SC  # noqa: E402

SAVE_CALLS = MF.SAVE_CALLS
LOAD_TAIL = MF.LOAD_TAIL
LED_CALLS = CI.LED_CALLS
READ, WRITE, SIZE = SC.READ, SC.WRITE, SC.SIZE
BUF_LOCK, BUF_UNLOCK, BUF, LOCK_OWNER = SC.BUF_LOCK, SC.BUF_UNLOCK, SC.BUF, SC.LOCK_OWNER
STORE, P_LOADED = 0x20012478, 11
PARAM_GET = CI.PARAM_GET
CUR_PACK = rodisk.CUR_PACK
KIND_BANK = 3
OFF0, REC_STEP, REC_LEN = 8192, 2048, 1024
NSL, SLOT, FM_AT, VA_AT = 4, 248, 32, 2
NPAR = 216
VER, CHECK0 = 1, 0x5A
O_PS = rhstate.OFF["projsnd"][0]
PEND, ST = 0, 1
PEND_ON = 0xC9
ST_OK, ST_WROTE, ST_NONE, ST_INT, ST_ERR = 0, 1, 2, 3, 4
assert 4 + NSL * SLOT <= REC_LEN and REC_LEN <= 4096


def model_record(slots):
    """the record for [(track + 1, fm_on, va 30 bytes, 216 params)] (the tests')"""
    rec = bytearray(REC_LEN)
    rec[0:3] = b"RS" + bytes([VER])
    for s, (t1, fm, va, par) in enumerate(slots):
        o = 4 + SLOT * s
        rec[o], rec[o + 1] = t1, 1 if fm else 0
        rec[o + VA_AT:o + VA_AT + 30] = bytes(va)
        rec[o + FM_AT:o + FM_AT + NPAR] = bytes(par)
    x = CHECK0
    for c in rec[4:]:
        x ^= c
    rec[3] = x
    return bytes(rec)


def arm_code(base, L, prev):
    import rhbuild
    VMODE = rhbuild.OPT.get("vmode")
    VSEL = rhbuild.OPT.get("vsel")
    if VMODE:
        from esel import ESR, O_MODE, O_DET
    else:
        ESR = O_MODE = O_DET = 0
    from vsel import EXT0
    a = Asm(base)
    E = a.emit
    zc = [0]

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    def bc(target, cond):
        INV = {"eq": "ne", "ne": "eq", "lo": "hs", "hs": "lo", "hi": "ls", "ls": "hi", "lt": "ge", "ge": "lt", "gt": "le", "le": "gt",
               "mi": "pl", "pl": "mi"}
        zc[0] += 1
        n = f"_p{zc[0]}"
        E(b_cond, n, INV[cond])
        E(b, target)
        a.label(n)

    # ---- c_psram() -> r0 = our RAM, 0 without; clobbers r1-r3
    a.label("c_psram")
    E(push_list, [4], lr=True)
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "pr_x", "eq")
    E(adds_imm8, 0, O_PS)
    a.label("pr_x")
    E(pop_list, [4], pc=True)

    # ---- c_psst(r0 = status): our last status; clobbers r0-r3
    a.label("c_psst")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_psram")
    E(cmp_imm, 0, 0)
    E(b_cond, "ps_x", "eq")
    E(strb_imm, 4, 0, ST)
    a.label("ps_x")
    E(pop_list, [4], pc=True)

    # ---- c_psint(r0 = pack code) -> r0 = 1 when it is the internal pack (0, or 0xFE while pack 0 is loaded); clobbers r1-r3
    a.label("c_psint")
    E(cmp_imm, 0, 0)
    E(b_cond, "pi_y", "eq")
    E(cmp_imm, 0, rodisk.LOADED)
    E(b_cond, "pi_n", "ne")
    imm32(1, CUR_PACK)
    E(ldr_imm, 1, 1, 0)
    E(ldrb_imm, 1, 1, 0)
    E(cmp_imm, 1, 0)
    E(b_cond, "pi_y", "eq")
    a.label("pi_n")
    E(movs_imm, 0, 0)
    E(raw, h(0x4770))
    a.label("pi_y")
    E(movs_imm, 0, 1)
    E(raw, h(0x4770))

    # ---- c_psio(r0 = 0 read / 1 write, r1 = offset, r2 = bytes, r3 = the item's index; [sp] = the pack): the buffer to / from the bank
    #      -> r0 = 0 when every byte went; clobbers r0-r3 (the API waits for the storage task)
    a.label("c_psio")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(ldr_sp, 4, 20)                                                      # the pack (the caller's [sp])
    E(sub_sp_imm, 32)
    E(mov_reg, 7, 13)
    E(mov_reg, 5, 0)
    E(movs_imm, 0, 0)
    E(str_imm, 0, 7, 0)                                                   # [0] the callback: none (wait)
    E(str_imm, 0, 7, 4)
    E(str_imm, 0, 7, 12)                                                  # [12] the bytes done
    E(mov_reg, 0, 7)
    E(adds_imm8, 0, 12)
    E(str_imm, 0, 7, 8)                                                   # [8] -> [12]
    E(movs_imm, 0, KIND_BANK)
    E(str_imm, 0, 7, 16)                                                  # the item {3, index, pack} at [16]
    E(str_imm, 3, 7, 20)
    E(strb_imm, 4, 7, 24)
    E(mov_reg, 6, 2)                                                      # r6 = the bytes
    E(mov_reg, 0, 7)
    E(adds_imm8, 0, 16)
    imm32(2, BUF)
    E(mov_reg, 3, 6)
    E(cmp_imm, 5, 0)
    E(b_cond, "io_w", "ne")
    E(bl, READ)
    E(b, "io_r")
    a.label("io_w")
    E(bl, WRITE)
    a.label("io_r")
    E(cmp_imm, 0, 0)
    E(b_cond, "io_x", "ne")
    E(cmp_imm, 5, 0)
    E(b_cond, "io_x", "ne")
    E(ldr_imm, 0, 7, 12)                                                  # (a read: every byte)
    E(subs_reg, 0, 0, 6)
    a.label("io_x")
    E(add_sp_imm, 32)
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_pssize(r0 = the item's index, r1 = the pack) -> r0 = the bank file's size (negative: none); clobbers r0-r3
    a.label("c_pssize")
    E(push_list, [4], lr=True)
    E(sub_sp_imm, 16)
    E(movs_imm, 2, KIND_BANK)
    E(raw, h(0x9200))                                                     # str r2, [sp]
    E(raw, h(0x9001))                                                     # str r0, [sp, #4]
    E(raw, h(0x9102))                                                     # str r1, [sp, #8]
    E(mov_reg, 0, 13)
    E(bl, SIZE)
    E(add_sp_imm, 16)
    E(pop_list, [4], pc=True)

    # ---- c_psfill(r0 = word): the buffer's first 4 KB; clobbers r1, r2
    a.label("c_psfill")
    imm32(1, BUF)
    imm32(2, 4096)
    a.label("pf_l")
    E(raw, h(0x3A04))                                                     # subs r2, #4
    E(raw, h(0x5088))                                                     # str r0, [r1, r2]
    E(b_cond, "pf_l", "ne")
    E(raw, h(0x4770))

    # ---- c_pssave(r0 = the project's slot, r1 = its pack code): its record written (see above); clobbers r0-r3
    a.label("c_pssave")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)                                                      # r4 = p
    E(mov_reg, 5, 1)                                                      # r5 = the pack
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("sv_x", "eq")
    E(mov_reg, 0, 5)
    E(bl, "c_psint")
    E(cmp_imm, 0, 0)
    E(b_cond, "sv_go", "eq")
    E(movs_imm, 0, ST_INT)
    E(bl, "c_psst")
    E(b, "sv_x")
    a.label("sv_go")
    E(movs_imm, 0, LOCK_OWNER)
    E(bl, BUF_LOCK)
    E(lsrs_imm, 0, 4, 3)                                                  # the gap: 0xFF up to our offset
    E(mov_reg, 1, 5)
    E(bl, "c_pssize")
    E(mov_reg, 6, 0)                                                      # r6 = its size
    E(cmp_imm, 6, 0)
    E(b_cond, "sv_s", "ge")
    E(movs_imm, 6, 0)
    a.label("sv_s")
    E(movs_imm, 0, 7)
    E(raw, h(0x4020))                                                     # ands r0, r4
    E(lsls_imm, 7, 0, 11)
    imm32(0, OFF0)
    E(adds_reg, 7, 7, 0)                                                  # r7 = our offset
    E(cmp_reg, 6, 7)
    bc("sv_rec", "hs")
    E(movs_imm, 0, 0)
    E(raw, h(0x43C0))                                                     # mvns r0, r0
    E(bl, "c_psfill")
    a.label("sv_g")
    E(subs_reg, 2, 7, 6)                                                  # the bytes left (4 KB at most)
    imm32(0, 4096)
    E(cmp_reg, 2, 0)
    E(b_cond, "sv_gn", "ls")
    E(mov_reg, 2, 0)
    a.label("sv_gn")
    E(push_list, [2])
    E(push_list, [5])                                                     # [sp] = the pack
    E(movs_imm, 0, 1)
    E(mov_reg, 1, 6)
    E(lsrs_imm, 3, 4, 3)
    E(bl, "c_psio")
    E(add_sp_imm, 4)
    E(pop_list, [2])
    E(cmp_imm, 0, 0)
    bc("sv_err", "ne")
    E(adds_reg, 6, 6, 2)
    E(cmp_reg, 6, 7)
    E(b_cond, "sv_g", "lo")
    a.label("sv_rec")                                                     # the record
    E(movs_imm, 0, 0)
    E(bl, "c_psfill")
    imm32(6, BUF)
    E(movs_imm, 0, ord("R"))
    E(strb_imm, 0, 6, 0)
    E(movs_imm, 0, ord("S"))
    E(strb_imm, 0, 6, 1)
    E(movs_imm, 0, VER)
    E(strb_imm, 0, 6, 2)
    E(push_list, [4, 5, 7])
    E(movs_imm, 4, 0)                                                     # r4 = the slot
    a.label("sv_sl")
    E(movs_imm, 0, SLOT)
    E(raw, h(0x4360))                                                     # muls r0, r4
    E(adds_reg, 5, 6, 0)
    E(adds_imm8, 5, 4)                                                    # r5 = its bytes
    E(bl, L["c_syb"])
    E(cmp_imm, 0, 0)
    bc("sv_sn", "eq")
    E(movs_imm, 1, L["SY_SL"])
    E(raw, h(0x4361))                                                     # muls r1, r4
    E(adds_reg, 0, 0, 1)
    E(ldrb_imm, 0, 0, 2)                                                  # the track + 1
    E(strb_imm, 0, 5, 0)
    E(cmp_imm, 0, 0)
    bc("sv_sn", "eq")
    if VMODE:                                                             # (RH80) its track's voice mode (+ 1, 0 never set) and detune
        imm32(1, ESR - 1)
        E(adds_reg, 1, 1, 0)
        E(ldrb_imm, 2, 1, O_MODE)
        E(strb_imm, 2, 5, VA_AT)
        E(ldrb_imm, 2, 1, O_DET)
        E(strb_imm, 2, 5, VA_AT + 1)
    if VSEL:                                                              # (RH80) its track's OSC 1 tune / fine, envelope -> FM / ring / mix
        E(movs_imm, 1, 5)
        E(raw, h(0x4341))                                                 # muls r1, r0 (5 (t + 1))
        imm32(2, ESR + EXT0 - 5)
        E(adds_reg, 1, 1, 2)
        for i in range(5):
            E(ldrb_imm, 2, 1, i)
            E(strb_imm, 2, 5, VA_AT + 2 + i)
    E(mov_reg, 0, 4)
    E(bl, L["c_fmon"])
    E(strb_imm, 0, 5, 1)
    E(cmp_imm, 0, 0)
    bc("sv_sn", "eq")
    E(mov_reg, 0, 4)
    E(bl, L["c_f8src"])
    E(mov_reg, 7, 0)                                                      # r7 = the slot whose parameters it plays
    E(adds_imm8, 5, FM_AT)
    E(movs_imm, 0, 0)
    a.label("sv_p")
    E(push_list, [0])
    E(mov_reg, 1, 0)
    E(mov_reg, 0, 7)
    E(bl, L["c_f8rd"])
    E(pop_list, [1])
    E(raw, h(0x5468))                                                     # strb r0, [r5, r1]
    E(adds_imm8, 1, 1)
    E(mov_reg, 0, 1)
    E(cmp_imm, 0, NPAR)
    E(b_cond, "sv_p", "lo")
    a.label("sv_sn")
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, NSL)
    bc("sv_sl", "lo")
    E(pop_list, [4, 5, 7])
    E(movs_imm, 0, CHECK0)                                                # the check
    E(movs_imm, 1, 4)
    imm32(2, REC_LEN)
    a.label("sv_c")
    E(ldrb_reg, 3, 6, 1)
    E(eors_reg, 0, 3)
    E(adds_imm8, 1, 1)
    E(cmp_reg, 1, 2)
    E(b_cond, "sv_c", "lo")
    E(strb_imm, 0, 6, 3)
    E(push_list, [5])
    E(movs_imm, 0, 1)
    E(mov_reg, 1, 7)
    imm32(2, REC_LEN)
    E(lsrs_imm, 3, 4, 3)
    E(bl, "c_psio")
    E(add_sp_imm, 4)
    E(cmp_imm, 0, 0)
    bc("sv_err", "ne")
    E(bl, BUF_UNLOCK)
    E(movs_imm, 0, ST_WROTE)
    E(bl, "c_psst")
    E(b, "sv_x")
    a.label("sv_err")
    E(bl, BUF_UNLOCK)
    E(movs_imm, 0, ST_ERR)
    E(bl, "c_psst")
    a.label("sv_x")
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_pssv0 / c_pssv1 (the two save calls, r1 = the item): the record first, then the chain (sp untouched: the stock's stack arguments)
    for k, tgt in enumerate(prev["save"]):
        a.label(f"c_pssv{k}")
        E(push_list, [0, 1, 2, 3], lr=True)
        E(ldr_imm, 0, 1, 4)
        E(ldrb_imm, 1, 1, 8)
        E(bl, "c_pssave")
        E(raw, MF_POPW([0, 1, 2, 3]))
        E(b_w, tgt)

    # ---- c_psload (the end of «apply the record»): our flag, then the chain
    a.label("c_psload")
    E(push_list, [0, 1, 2, 3], lr=True)
    E(bl, "c_psram")
    E(cmp_imm, 0, 0)
    E(b_cond, "pl_x", "eq")
    E(movs_imm, 1, PEND_ON)
    E(strb_imm, 1, 0, PEND)
    a.label("pl_x")
    E(raw, MF_POPW([0, 1, 2, 3]))
    E(b_w, prev["load"])

    # ---- c_psapply(r0 = 1 a valid record in the buffer / 0 none): each slot's FM as the record says (or off); clobbers r0-r3
    a.label("c_psapply")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 7, 0)                                                      # r7 = a record
    if VMODE:                                                             # (RH80) the voice modes and detunes: none until the record's
        imm32(1, ESR)
        E(movs_imm, 2, 0)
        for o in (O_MODE, O_MODE + 4, O_DET, O_DET + 4) + (tuple(range(EXT0, EXT0 + 40, 4)) if VSEL else ()):
            E(str_imm, 2, 1, o)
    E(movs_imm, 4, 0)
    a.label("ap_sl")
    E(cmp_imm, 7, 0)
    E(b_cond, "ap_off", "eq")
    imm32(5, BUF + 4)
    E(movs_imm, 0, SLOT)
    E(raw, h(0x4360))                                                     # muls r0, r4
    E(adds_reg, 5, 5, 0)                                                  # r5 = its bytes
    E(ldrb_imm, 6, 5, 0)                                                  # r6 = its track + 1
    E(cmp_imm, 6, 0)
    E(b_cond, "ap_off", "eq")
    E(bl, L["c_syb"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ap_off", "eq")
    E(movs_imm, 1, L["SY_SL"])
    E(raw, h(0x4361))                                                     # muls r1, r4
    E(adds_reg, 0, 0, 1)
    E(ldrb_imm, 0, 0, 2)
    E(cmp_reg, 0, 6)
    E(b_cond, "ap_off", "ne")                                             # another track there now: not this sound
    if VMODE:                                                             # (RH80) its track's voice mode and detune
        imm32(1, ESR - 1)
        E(adds_reg, 1, 1, 6)
        E(ldrb_imm, 2, 5, VA_AT)
        E(strb_imm, 2, 1, O_MODE)
        E(ldrb_imm, 2, 5, VA_AT + 1)
        E(strb_imm, 2, 1, O_DET)
    if VSEL:
        E(movs_imm, 1, 5)
        E(raw, h(0x4371))                                                 # muls r1, r6 (5 (t + 1))
        imm32(2, ESR + EXT0 - 5)
        E(adds_reg, 1, 1, 2)
        for i in range(5):
            E(ldrb_imm, 2, 5, VA_AT + 2 + i)
            E(strb_imm, 2, 1, i)
    E(ldrb_imm, 0, 5, 1)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "ap_off", "eq")
    E(adds_imm8, 5, FM_AT)
    E(movs_imm, 6, 0)
    a.label("ap_p")
    E(ldrb_reg, 2, 5, 6)
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 6)
    E(bl, L["c_f8wr"])
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, NPAR)
    E(b_cond, "ap_p", "lo")
    E(mov_reg, 0, 4)
    E(movs_imm, 1, 1)
    E(bl, L["c_fmset"])
    E(bl, L["c_f8ram"])                                                   # valid (no E.Piano), not keyed (its words from zero)
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(ldrb_imm, 2, 0, L["F8_VALID"])
    E(orrs_reg, 2, 1)
    E(strb_imm, 2, 0, L["F8_VALID"])
    E(ldrb_imm, 2, 0, L["F8_KEYED"])
    E(bics_reg, 2, 1)
    E(strb_imm, 2, 0, L["F8_KEYED"])
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 0, L["F8_INST"])
    E(b, "ap_n")
    a.label("ap_off")
    E(mov_reg, 0, 4)
    E(bl, L["c_fmon"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ap_n", "eq")
    E(mov_reg, 0, 4)
    E(movs_imm, 1, 0)
    E(bl, L["c_fmset"])
    a.label("ap_n")
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, NSL)
    bc("ap_sl", "lo")
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_psled (the LED calls: ctrl, frame): the chain; a load to apply (core 0 / 1 up): the loaded project's record
    a.label("c_psled")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(ldrb_w, 1, 0, L["TH_ST"])
    E(cmp_imm, 1, TH.READY)
    bc("ld_x", "ne")
    E(adds_imm8, 0, O_PS)
    E(mov_reg, 7, 0)                                                      # r7 = our RAM
    E(ldrb_imm, 1, 7, PEND)
    E(cmp_imm, 1, PEND_ON)
    bc("ld_x", "ne")
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 7, PEND)
    imm32(0, STORE)
    E(movs_imm, 1, P_LOADED)
    E(bl, PARAM_GET)
    E(ldr_imm, 4, 0, 0)                                                   # r4 = the loaded project
    E(movs_imm, 0, rodisk.LOADED)
    E(bl, "c_psint")
    E(cmp_imm, 0, 0)
    E(b_cond, "ld_c", "eq")
    E(movs_imm, 0, 0)
    E(bl, "c_psapply")
    E(movs_imm, 0, ST_INT)
    E(bl, "c_psst")
    E(b, "ld_x")
    a.label("ld_c")
    E(movs_imm, 0, LOCK_OWNER)
    E(bl, BUF_LOCK)
    E(movs_imm, 0, rodisk.LOADED)
    E(push_list, [0])
    E(movs_imm, 0, 7)
    E(raw, h(0x4020))                                                     # ands r0, r4
    E(lsls_imm, 1, 0, 11)
    imm32(0, OFF0)
    E(adds_reg, 1, 1, 0)
    E(movs_imm, 0, 0)
    imm32(2, REC_LEN)
    E(lsrs_imm, 3, 4, 3)
    E(bl, "c_psio")
    E(add_sp_imm, 4)
    E(movs_imm, 5, 0)                                                     # r5 = a valid record
    E(cmp_imm, 0, 0)
    E(b_cond, "ld_ap", "ne")
    imm32(6, BUF)
    E(ldrb_imm, 0, 6, 0)
    E(cmp_imm, 0, ord("R"))
    E(b_cond, "ld_ap", "ne")
    E(ldrb_imm, 0, 6, 1)
    E(cmp_imm, 0, ord("S"))
    E(b_cond, "ld_ap", "ne")
    E(ldrb_imm, 0, 6, 2)
    E(cmp_imm, 0, VER)
    E(b_cond, "ld_ap", "ne")
    E(movs_imm, 0, CHECK0)
    E(movs_imm, 1, 4)
    imm32(2, REC_LEN)
    a.label("ld_k")
    E(ldrb_reg, 3, 6, 1)
    E(eors_reg, 0, 3)
    E(adds_imm8, 1, 1)
    E(cmp_reg, 1, 2)
    E(b_cond, "ld_k", "lo")
    E(ldrb_imm, 1, 6, 3)
    E(cmp_reg, 0, 1)
    E(b_cond, "ld_ap", "ne")
    E(movs_imm, 5, 1)
    a.label("ld_ap")
    E(mov_reg, 0, 5)
    E(bl, "c_psapply")
    E(bl, BUF_UNLOCK)
    E(movs_imm, 0, ST_OK)
    E(cmp_imm, 5, 0)
    E(b_cond, "ld_s", "ne")
    E(movs_imm, 0, ST_NONE)
    a.label("ld_s")
    E(bl, "c_psst")
    a.label("ld_x")
    E(pop_list, [4, 5, 6, 7], pc=True)
    return a.assemble()


def MF_POPW(regs):
    return h(0xE8BD) + h(sum(1 << r for r in regs) | 1 << 14)


def install(img, report, base_addr):
    """The two save calls, the end of «apply the record», the head of the LED calls.  Needs synthpage, fmpage with fm8page (the FM's
    parameters), mfsess (its save / load hooks), cthresh, countin, rhstate."""
    import rhbuild
    import fm8page as F8
    import synthpage as SY
    BASE = rhbuild.BASE
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    assert "fm8page" in report and "mfsess" in report
    L = dict(c_rst=lab("rhstate", "c_rst"), c_ciok=lab("countin", "c_ciok"), c_syb=lab("synthpage", "c_syb"),
             c_fmon=lab("fmpage", "c_fmon"), c_fmset=lab("fmpage", "c_fmset"),
             **{k: lab("fm8page", k) for k in ("c_f8rd", "c_f8wr", "c_f8src", "c_f8ram")},
             SY_SL=SY.SL, F8_VALID=F8.O_VALID, F8_KEYED=F8.O_KEYED, F8_INST=F8.O_INST, TH_ST=TH.O_ST + 1)
    prev = dict(save=[rhbuild.bl_target(img, c) for c in SAVE_CALLS], load=rhbuild.bw_target(img, LOAD_TAIL),
                ledtask=rhbuild.bl_target(img, LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in LED_CALLS)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    for k, c in enumerate(SAVE_CALLS):
        rhbuild.patch(img, c, f"bl #{prev['save'][k]:#x}", bl(c, labels[f"c_pssv{k}"]))
    rhbuild.patch(img, LOAD_TAIL, f"b.w #{prev['load']:#x}", b_w(LOAD_TAIL, labels["c_psload"]))
    for c in LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_psled"]))
    report["projsnd"] = dict(prev=dict(save=[hex(v) for v in prev["save"]], load=hex(prev["load"]), ledtask=hex(prev["ledtask"])),
                             labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
