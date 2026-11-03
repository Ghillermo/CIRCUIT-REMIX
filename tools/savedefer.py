"""The project save kept while the sequencer plays (MIT; CIRCUIT-HACKS' savedefer of SC49.7 / SC49.8 for the Circuit Rhythm 5706; the user,
2026-11-01: «Guardar al parar»).

The stock of the Rhythm (read in its image, the same shape as the Tracks'): Save twice commits a store of the session object 0x20042FF4
(vtable 0x08066F64); its listener 0x080385CA(manager, store, index, value, ...), reached through the thunk of the vtable word 0x08066F80
(this + 4), sees the request ([manager + 0x3C] = the save requests, the index = the slot), and at 0x08038676 calls the save routine
0x08037ED0(manager, slot, flag): the state «saving» (p1 of [manager + 0x48] = 2: the listener ignores everything meanwhile), the record copied and
posted to the storage task.  Writing it to the card while the transport runs is what upsets the clock.

Ours, only with Advanced Setup's pad 24 on (green / dim green; the stock's save by default, saved with the unit's settings: byte 1 of parameter 3,
FLAG = on, which the stock's comparer ignores):
  * that bl -> c_sdsave: the transport running = the call is only kept (slot, flag), nothing else happens; stopped, the stock's;
  * the LED task: a kept save runs once the transport stops (not while the manager is busy); meanwhile Save (LED 57) blinks yellow;
  * the vtable word -> c_sddisp: any other project request while a save is kept runs that save first (a load or a new project then finds the stock
    «saving» and is ignored, as the stock does while it saves: press again), except a save of the same slot;
  * turning the pad off with a save kept: it runs at once.
RAM: rhstate OFF2 "savedefer": + 0 kept, + 1 its slot, + 2 its flag.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_reg, b_cond, b_w, bl, cmp_imm, cmp_reg, h, ldr_imm, ldr_sp, ldrb_imm, lsls_imm, lsrs_imm, mov_reg, movs_imm, movt,  # noqa: E402
                   movw, pop_list, push_list, raw, strb_imm, strh_imm, strh_w_imm)
import countin as CI  # noqa: E402
import midithru as M  # noqa: E402
import pgmch as PG  # noqa: E402
import rhstate  # noqa: E402
import usbmerge as UM  # noqa: E402

MGR = 0x20042FF4
SAVE_CALL, SAVE = 0x08038676, 0x08037ED0
DISP_VT, DISP = 0x08066F80, 0x080385C8                    # the thunk (this + 4)
O_REQ, O_BUSY, BUSY = 0x3C, 0x48, 2
P_UNIT, B_FLAG, FLAG = 3, 1, 0xD1                          # the unit's settings: parameter 3, byte 1
PAD = 23                                                   # pad 24, beside the USB merge's
COL_ON, COL_DIM = UM.COL_ON, UM.UI_DIM
LED_SAVE, YELLOW = 57, 0x2F
HAL_TICK = 0x20006F3C
O = rhstate.OFF2["savedefer"][0]
R_KEPT, R_SLOT, R_FLAG = 0, 1, 2
GET, WPTR, COMMIT = CI.PARAM_GET, CI.WPTR, CI.COMMIT
SETUP_VT = PG.SETUP_VT


def popw(regs, lr=False): return UM.popw(regs, lr)


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_sdram() -> r0 = our RAM (0 without it); c_sdplay() -> r0 = the transport's p0; c_sdon() -> r0 = 1 with the pad on; clobber r1-r3
    a.label("c_sdram")
    E(push_list, [4], lr=True)
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "sr_x", "eq")
    E(movw, 1, O)
    E(adds_reg, 0, 0, 1)
    a.label("sr_x")
    E(pop_list, [4], pc=True)
    a.label("c_sdplay")
    E(push_list, [4], lr=True)
    imm32(0, CI.TRANSPORT)
    E(movs_imm, 1, 0)
    E(bl, GET)
    E(ldrb_imm, 0, 0, 0)
    E(pop_list, [4], pc=True)
    a.label("c_sdon")
    E(push_list, [4], lr=True)
    imm32(0, M.SETTINGS)
    E(movs_imm, 1, P_UNIT)
    E(bl, GET)
    E(ldrb_imm, 1, 0, B_FLAG)
    E(movs_imm, 0, 0)
    E(cmp_imm, 1, FLAG)
    E(b_cond, "so_x", "ne")
    E(movs_imm, 0, 1)
    a.label("so_x")
    E(pop_list, [4], pc=True)

    # ---- c_sdsave (the bl of the save: manager, slot, flag): playing, with the pad on = kept; else the stock's (and nothing kept any more)
    a.label("c_sdsave")
    E(push_list, [0, 1, 2, 4], lr=True)
    E(bl, "c_sdram")
    E(mov_reg, 4, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "ss_r", "eq")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 4, R_KEPT)
    E(bl, "c_sdon")
    E(cmp_imm, 0, 0)
    E(b_cond, "ss_r", "eq")
    E(bl, "c_sdplay")
    E(cmp_imm, 0, 0)
    E(b_cond, "ss_r", "eq")
    E(ldr_sp, 1, 4)
    E(strb_imm, 1, 4, R_SLOT)
    E(ldr_sp, 1, 8)
    E(strb_imm, 1, 4, R_FLAG)
    E(movs_imm, 1, 1)
    E(strb_imm, 1, 4, R_KEPT)
    E(pop_list, [0, 1, 2, 4], pc=True)
    a.label("ss_r")
    E(raw, popw([0, 1, 2, 4], lr=True))
    E(b_w, SAVE)

    # ---- c_sdflush(): a kept save run now (not while the manager is busy); clobbers r0-r3
    a.label("c_sdflush")
    E(push_list, [4], lr=True)
    E(bl, "c_sdram")
    E(mov_reg, 4, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "sf_x", "eq")
    E(ldrb_imm, 0, 4, R_KEPT)
    E(cmp_imm, 0, 0)
    E(b_cond, "sf_x", "eq")
    imm32(0, MGR)
    E(ldr_imm, 0, 0, O_BUSY)
    E(movs_imm, 1, 1)
    E(bl, GET)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, BUSY)
    E(b_cond, "sf_x", "eq")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 4, R_KEPT)
    E(ldrb_imm, 1, 4, R_SLOT)
    E(ldrb_imm, 2, 4, R_FLAG)
    imm32(0, MGR)
    E(bl, SAVE)
    a.label("sf_x")
    E(pop_list, [4], pc=True)

    # ---- c_sddisp (the listener's thunk: this + 4, store, index, value, [sp] more): a kept save first (not for a save of its slot), then the stock's
    a.label("c_sddisp")
    E(push_list, [0, 1, 2, 3], lr=True)
    E(ldr_imm, 3, 0, O_REQ - 4)
    E(cmp_reg, 1, 3)
    E(b_cond, "sd_f", "ne")
    E(bl, "c_sdram")
    E(cmp_imm, 0, 0)
    E(b_cond, "sd_g", "eq")
    E(ldrb_imm, 1, 0, R_SLOT)
    E(ldr_sp, 2, 8)
    E(cmp_reg, 1, 2)
    E(b_cond, "sd_g", "eq")
    a.label("sd_f")
    E(bl, "c_sdflush")
    a.label("sd_g")
    E(raw, popw([0, 1, 2, 3], lr=True))
    E(b_w, DISP)

    # ---- c_sdpad (the Setup view's slot 0: view, pad, velocity): Advanced Setup, pad 24 = on / off; off runs a kept save
    a.label("c_sdpad")
    E(cmp_imm, 1, PAD)
    E(b_cond, "sp_s", "ne")
    E(push_list, [0, 1, 2, 3, 4, 5], lr=True)
    E(raw, h(0xF890) + h(0x3024))                                         # ldrb.w r3, [r0, #0x24]
    E(cmp_imm, 3, 0)
    E(b_cond, "sp_p", "eq")                                               # not Advanced
    E(bl, "c_sdon")
    E(mov_reg, 4, 0)
    imm32(0, M.SETTINGS)
    E(movs_imm, 1, P_UNIT)
    E(bl, WPTR)
    E(movs_imm, 1, FLAG)
    E(cmp_imm, 4, 0)
    E(b_cond, "sp_w", "eq")
    E(movs_imm, 1, 0)
    a.label("sp_w")
    E(strb_imm, 1, 0, B_FLAG)
    imm32(0, M.SETTINGS)
    E(bl, COMMIT)
    E(bl, "c_sdflush")
    E(pop_list, [0, 1, 2, 3, 4, 5], pc=True)
    a.label("sp_p")
    E(raw, popw([0, 1, 2, 3, 4, 5], lr=True))
    a.label("sp_s")
    E(b_w, prev["pad"])

    # ---- c_sdled (the LED task's calls: ctrl, frame): the chain; Advanced Setup: pad 24; a kept save: run once stopped, else Save blinking yellow
    a.label("c_sdled")
    E(push_list, [3, 4, 5, 6], lr=True)
    E(mov_reg, 5, 1)
    E(bl, prev["ledtask"])
    UM.advanced(E, imm32, L, "sl_k")
    E(bl, "c_sdon")
    E(movs_imm, 1, COL_DIM)
    E(cmp_imm, 0, 0)
    E(b_cond, "sl_p", "eq")
    E(movs_imm, 1, COL_ON)
    a.label("sl_p")
    E(strh_imm, 1, 5, 2 * PAD)
    a.label("sl_k")
    E(bl, "c_sdram")
    E(cmp_imm, 0, 0)
    E(b_cond, "sl_x", "eq")
    E(ldrb_imm, 0, 0, R_KEPT)
    E(cmp_imm, 0, 0)
    E(b_cond, "sl_x", "eq")
    E(bl, "c_sdplay")
    E(cmp_imm, 0, 0)
    E(b_cond, "sl_b", "ne")
    E(bl, "c_sdflush")
    E(pop_list, [3, 4, 5, 6], pc=True)
    a.label("sl_b")
    imm32(0, HAL_TICK)
    E(ldr_imm, 0, 0, 0)
    E(lsls_imm, 0, 0, 23)                                                 # bit 8: ~¼ s on, ¼ s off
    E(lsrs_imm, 0, 0, 31)
    E(movs_imm, 1, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "sl_w", "eq")
    E(movs_imm, 1, YELLOW)
    a.label("sl_w")
    E(strh_w_imm, 1, 5, 2 * LED_SAVE)
    a.label("sl_x")
    E(pop_list, [3, 4, 5, 6], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """The bl of the save, the listener's vtable word, the head of the Setup view's slot 0, the head of the LED calls.  Needs usbmerge's helpers,
    rhstate ram2, setsave with its byte (OPT setp3)."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]                 # noqa: E731
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    assert u(DISP_VT) == DISP | 1 and rhbuild.bl_target(img, SAVE_CALL) == SAVE
    L = dict(c_rram=lab("rhstate", "c_rram"), c_ciok=lab("countin", "c_ciok"), c_cinew=lab("countin", "c_cinew"))
    prev = dict(pad=u(SETUP_VT) & ~1, ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, SAVE_CALL, f"bl #{SAVE:#x}", bl(SAVE_CALL, labels["c_sdsave"]))
    rhbuild.patch_word(img, DISP_VT, DISP | 1, labels["c_sddisp"] | 1)
    rhbuild.patch_word(img, SETUP_VT, prev["pad"] | 1, labels["c_sdpad"] | 1)
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_sdled"]))
    report["savedefer"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
