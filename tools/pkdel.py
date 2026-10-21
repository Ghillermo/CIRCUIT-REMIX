"""Delete a whole pack from the packs view (MIT; CIRCUIT-HACKS' packio (3., SC35 / SC37.2) for the Circuit Rhythm 5706; part of «gestión del
pack», approved by the user on 2026-10-19).  Novation's guide: «You can only remove packs using Components, and not from the Circuit Rhythm
directly»: the gesture is new.

The stock of the Rhythm (read in the firmware, emulated on the RAM dump):
  * the packs view 0x2004D7FC (vtable 0x08067954; Projects twice or Shift + Projects): slot 0 = the pads 0x0804E00A(view, pad, velocity):
    nothing without the card (bit 0 of p0 of [view + 0xC]) or on the loaded pack (p0 of [view + 0x10], the store 0x20012478); with Duplicate
    (bit 1 of p0 of [view + 0x1C]) an empty slot gets a copy of the loaded pack (the stock's own "duplicate pack"); else the pad is primed
    (p0 of [view + 0x18], Play loads it).  [view + 0x14] = the pack list: parameter p = pack p's colour, 0xFF = an empty slot; its listener
    (slot 9, 0x0804E0B6) repaints a pack whose parameter changes;
  * Clear held = bit 23 of [ctrl + 0xA0]; in the stock, Clear + pad there = the pad (it primes the pack): the gesture is free;
  * the storage task's op 5 (delete, 0x08046098(item, 0, 0), synchronous) with kind 1 = the whole pack (0x080413B0: the pack selected,
    0x0802E938 deletes all its items, 0x0802E3E0 its folder, then the storage task's current pack ([[0x20006E24]]) = 0xFF, none): the
    Tracks' code (0x080266D4), proven on the Tracks (SC37.4: «El borrado funciona»).  After it, an operation on the loaded pack by its own
    number (not 0xFE, which would mean "none" now) puts the storage task back on it (sesscopy's c_scresel).

Ours (slot 0 of the packs view; transport stopped, Clear held, Shift not held, the card present):
  * Clear + the pad of a pack (not the loaded one, not the internal pack 0, not an empty slot) = asked: the pad blinks red for ~5 s;
  * Clear + the same pad again within ~5 s = the pack deleted (op 5, kind 1), the storage task back on the loaded pack, the slot empty in the
    stock's list (the view repaints it); the pad shows green for ~1.5 s (red if the storage task refused: the internal pack is also refused by
    rodisk's guard, the Save LED red);
  * every other Clear + pad there does nothing (an empty slot, the loaded pack, pack 0, while playing).
State in our RAM (rhstate "pkdel"): [0] tag [1] 0x80 | the pack asked about [2..3] its time [4] 0x80 | the last deleted [5] status [6..7] its time
(times = the HAL tick / 256, 16 bits).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, ands_reg, b, b_cond, bl, cmp_imm, cmp_reg, h, ldr_imm, ldrb_imm, ldrh_imm, lsls_imm, lsrs_imm,  # noqa: E402
                   mov_reg, movs_imm, movt, movw, orrs_reg, pop_list, push_list, raw, str_imm, strb_imm, strh_imm, strh_reg, sub_sp_imm,
                   add_sp_imm, subs_reg, tst_reg)
import countin as CI  # noqa: E402
import rhstate  # noqa: E402
import rodisk  # noqa: E402

CTRL, CTRL_VT = CI.CTRL, CI.CTRL_VT
O_VIEW, O_HELD, O_SHIFT, BIT_CLEAR = 0x7C, 0xA0, 0xC, 23
PACKS_VIEW, PACKS_VT = 0x2004D7FC, 0x08067954
PAD_STOCK = 0x0804E00A
O_CARD, O_LOADED, O_LIST = 0xC, 0x10, 0x14
EXISTS, DELETE = 0x08045FB4, rodisk.DELETE
KIND_PACK, KIND_SESS = 1, 2
WPTR, COMMIT, PARAM_NEW = 0x0803FD26, 0x0803FBEC, CI.PARAM_NEW
TRANSPORT = CI.TRANSPORT
HAL_TICK = rodisk.HAL_TICK
LED_CALLS = CI.LED_CALLS
O_ST = rhstate.OFF["pkdel"][0]
S_TAG, S_ASK, S_ASKT, S_DEL, S_RES, S_REST = 0, 1, 2, 4, 5, 6
TAG = 0xD5
LIFE = 20                                    # the question stays open ~5 s (units of 256 ms)
SHOW = 6                                     # the result ~1.5 s
COL_ASK, COL_OK, COL_BAD = 0x55, 0x1E, 0x55  # red, green, red (the Rhythm's codes: tools/rhpalette.py)
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
        n = f"_p{zc[0]}"
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

    def newest(store_reg_or_none, idx):                                    # r0 = byte of parameter idx of the store in r0
        E(movs_imm, 1, idx)
        E(bl, PARAM_NEW)
        E(ldrb_imm, 0, 0, 0)

    # ---- c_pdst() -> r0 = our state (tagged on first use), 0 without our RAM; clobbers r1-r3
    a.label("c_pdst")
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
    E(strb_imm, 1, 0, S_ASK)
    E(strb_imm, 1, 0, S_DEL)
    a.label("st_x")
    E(pop_list, [4], pc=True)

    # ---- c_pdon() -> r0 = the packs view when it is the active view of the dump's controller, else 0; clobbers r1, r2
    a.label("c_pdon")
    imm32(0, CTRL)
    E(ldr_imm, 1, 0, 0)
    imm32(2, CTRL_VT)
    E(cmp_reg, 1, 2)
    E(b_cond, "on_0", "ne")
    E(ldr_imm, 0, 0, O_VIEW)
    imm32(1, PACKS_VIEW)
    E(cmp_reg, 0, 1)
    E(b_cond, "on_x", "ne")
    E(ldr_imm, 2, 0, 0)
    imm32(1, PACKS_VT)
    E(cmp_reg, 2, 1)
    E(b_cond, "on_x", "eq")
    a.label("on_0")
    E(movs_imm, 0, 0)
    a.label("on_x")
    E(raw, BX_LR)

    # ---- c_pdresel(r0 = pack): the storage task's current pack := that one (op 0 on its project 0)
    a.label("c_pdresel")
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

    # ---- c_pddel(r0 = pack, r1 = the loaded pack) -> r0 = status (0 = deleted): op 5 kind 1, then the storage task back on the loaded pack
    a.label("c_pddel")
    E(push_list, [4, 5, 6], lr=True)
    E(sub_sp_imm, 16)
    E(mov_reg, 5, 1)
    E(raw, h(0x9002))                                                      # str r0, [sp, #8]: the pack
    E(movs_imm, 0, KIND_PACK)
    E(raw, h(0x9000))                                                      # str r0, [sp]
    E(movs_imm, 0, 0)
    E(raw, h(0x9001))                                                      # str r0, [sp, #4]
    E(mov_reg, 0, 13)
    E(movs_imm, 1, 0)
    E(movs_imm, 2, 0)
    E(bl, DELETE)                                                          # synchronous (no callback); rodisk's guard first
    E(mov_reg, 6, 0)
    E(mov_reg, 0, 5)
    E(bl, "c_pdresel")
    E(mov_reg, 0, 6)
    E(add_sp_imm, 16)
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_pdpad (the view's slot 0: view, pad, velocity): Clear held = ask, then delete
    a.label("c_pdpad")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(cmp_imm, 5, 32)
    bc("pp_f", "hs")
    imm32(0, CTRL)
    E(ldr_imm, 1, 0, 0)
    imm32(2, CTRL_VT)
    E(cmp_reg, 1, 2)
    bc("pp_f", "ne")
    imm32(1, CTRL + O_HELD)
    E(ldr_imm, 1, 1, 0)
    E(lsls_imm, 1, 1, 31 - BIT_CLEAR)
    bc("pp_f", "pl")                                                       # Clear not held: the stock's
    E(ldr_imm, 0, 0, O_SHIFT)
    newest(None, 0)
    E(lsls_imm, 0, 0, 31)
    bc("pp_f", "mi")                                                       # Shift held: the stock's
    E(ldr_imm, 0, 4, O_CARD)
    newest(None, 0)
    E(lsls_imm, 0, 0, 31)
    bc("pp_f", "pl")                                                       # no card: the stock's (it does nothing)
    E(bl, "c_pdst")
    E(mov_reg, 7, 0)
    E(cmp_imm, 7, 0)
    bc("pp_f", "eq")
    imm32(0, TRANSPORT)
    newest(None, 0)
    E(cmp_imm, 0, 0)
    bc("pp_e", "ne")                                                       # playing: nothing
    E(cmp_imm, 5, 0)
    bc("pp_e", "eq")                                                       # never the internal pack
    E(ldr_imm, 0, 4, O_LOADED)
    newest(None, 0)
    E(mov_reg, 6, 0)                                                       # r6 = the loaded pack
    E(cmp_reg, 6, 5)
    bc("pp_e", "eq")                                                       # never the loaded pack
    E(ldr_imm, 0, 4, O_LIST)
    E(mov_reg, 1, 5)
    E(bl, PARAM_NEW)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, 0xFF)
    bc("pp_e", "eq")                                                       # an empty slot
    E(movs_imm, 0, 0x80)
    E(orrs_reg, 0, 5)
    E(ldrb_imm, 1, 7, S_ASK)
    E(cmp_reg, 1, 0)
    E(b_cond, "pp_ask", "ne")
    since(0, 7, S_ASKT)
    E(cmp_imm, 0, LIFE)
    E(b_cond, "pp_ask", "hs")
    E(movs_imm, 0, 0)                                                      # asked and confirmed: delete
    E(strb_imm, 0, 7, S_ASK)
    E(mov_reg, 0, 5)
    E(mov_reg, 1, 6)
    E(bl, "c_pddel")
    E(strb_imm, 0, 7, S_RES)
    E(movs_imm, 1, 0x80)
    E(orrs_reg, 1, 5)
    E(strb_imm, 1, 7, S_DEL)
    tick(1)
    E(strh_imm, 1, 7, S_REST)
    E(cmp_imm, 0, 0)
    bc("pp_e", "ne")
    E(ldr_imm, 0, 4, O_LIST)                                               # the slot empty in the stock's list (the view repaints it)
    E(mov_reg, 1, 5)
    E(bl, WPTR)
    E(movs_imm, 1, 0xFF)
    E(strb_imm, 1, 0, 0)
    E(ldr_imm, 0, 4, O_LIST)
    E(bl, COMMIT)
    E(b, "pp_e")
    a.label("pp_ask")
    E(movs_imm, 0, 0x80)
    E(orrs_reg, 0, 5)
    E(strb_imm, 0, 7, S_ASK)
    tick(0)
    E(strh_imm, 0, 7, S_ASKT)
    a.label("pp_e")
    E(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)
    a.label("pp_f")
    E(raw, popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    imm32(3, prev["pad"] | 1)
    E(raw, h(0x4718))                                                      # bx r3: the stock's slot 0

    # ---- c_pdput(r0 = 0x80 | pack or 0, r1 = colour; r5 = the frame): that pad; clobbers r0, r2
    a.label("c_pdput")
    E(movs_imm, 2, 0x80)
    E(tst_reg, 0, 2)
    E(b_cond, "pt_x", "eq")
    E(movs_imm, 2, 31)
    E(ands_reg, 0, 2)
    E(lsls_imm, 0, 0, 1)
    E(strh_reg, 1, 5, 0)
    a.label("pt_x")
    E(raw, BX_LR)

    # ---- c_pdled (the LED task's calls: r0 = ctrl, r1 = frame): the chain, then on the packs view: the question, the result
    a.label("c_pdled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)
    E(bl, prev["ledtask"])
    E(bl, "c_pdon")
    E(cmp_imm, 0, 0)
    bc("lt_x", "eq")
    E(bl, "c_pdst")
    E(mov_reg, 7, 0)
    E(cmp_imm, 7, 0)
    bc("lt_x", "eq")
    E(ldrb_imm, 0, 7, S_ASK)                                               # the question, blinking red, ~5 s
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
    imm32(2, HAL_TICK)                                                     # blinking ~4 times a second
    E(ldr_imm, 2, 2, 0)
    E(lsrs_imm, 2, 2, 7)
    E(movs_imm, 3, 1)
    E(tst_reg, 2, 3)
    E(b_cond, "lt_q2", "eq")
    E(movs_imm, 1, 0)
    a.label("lt_q2")
    E(ldrb_imm, 0, 7, S_ASK)
    E(bl, "c_pdput")
    a.label("lt_r")                                                        # the result, green or red, ~1.5 s
    E(ldrb_imm, 0, 7, S_DEL)
    E(cmp_imm, 0, 0)
    E(b_cond, "lt_x", "eq")
    since(0, 7, S_REST)
    E(cmp_imm, 0, SHOW)
    E(b_cond, "lt_r1", "lo")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 7, S_DEL)
    E(b, "lt_x")
    a.label("lt_r1")
    E(movs_imm, 1, COL_OK)
    E(ldrb_imm, 0, 7, S_RES)
    E(cmp_imm, 0, 0)
    E(b_cond, "lt_r2", "eq")
    E(movs_imm, 1, COL_BAD)
    a.label("lt_r2")
    E(ldrb_imm, 0, 7, S_DEL)
    E(bl, "c_pdput")
    a.label("lt_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; the packs view's slot 0 and the two LED task calls."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda ad: struct.unpack_from("<I", img, ad - BASE)[0]
    L = dict(c_rst=int(report["rhstate"]["labels"]["c_rst"], 16))
    prev = dict(pad=u(PACKS_VT) & ~1, ledtask=rhbuild.bl_target(img, LED_CALLS[0]))
    assert prev["pad"] == PAD_STOCK, hex(prev["pad"])
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in LED_CALLS)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch_word(img, PACKS_VT, PAD_STOCK | 1, labels["c_pdpad"] | 1)
    for c in LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_pdled"]))
    report["pkdel"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
