"""Cue mode in the Mixer: the left output = the mix, the right = the tracks sent to the cue, a muted track too (MIT; RH47, CIRCUIT-HACKS'
cue of SC43.6 for the Rhythm, written again on its code; pending #24 of docs/PORTADO.md: «Cue listen y Cue track»).

The stock of the Rhythm (read in its image and its core 0 program, run on the RAM dump):
  * core 0 mixes each track with the gains of P:$2EA: left = level x min(1, 2 (1 - p)), right = level x min(1, 2 p) (p = the pan word; a
    balance law: the centre at full gain on both sides), from the words it copies each block out of the track's block in shared memory
    (Y:$307C8 + $20 t: + $10 the level, + $11 the pan; P:$33E);
  * the ARM writes that block with 0x0804070E(t, index, value) (0x08031228, core 0), called only by the track flusher 0x0803081C(t) (at
    0x0803085E) for the indices marked in [0x20006B68 + 4 t] (bit i), the value read with 0x08046410(0x10 + t, i): 0x10 the level, 0x11 the
    pan, 0x12 / 0x13 the reverb / delay sends;
  * a mute is the sequencer's: the Mixer's pads toggle p0 of the track player's store [player + 0x28] (0x200470D4 + 0x190 t); the player
    (0x0805516E) skips a muted track's micro steps (p0 read by the bl at 0x08055176);
  * the Mixer (0x2004E090, vtable 0x08067918): its knob slot (+ 0x10, mixshift's in front) moves the levels, or the pans on its pan page
    (p0 of the store inside the view at + 0x68 = 1, button 19); Shift + knob on the pan page = the knob alone.
Ours (rhstate OFF2 "cue": + 0 the mode (0xC5 on), + 1 the mutes last seen, + 2 the tracks to send again, + 3 a zero byte, + 4 the cue sends c):
  * on the pan page: Shift + a knob to the right = the cue mode on, to the left = off; in the mode a knob (no Shift) = that track's cue send c
    (0..127, the knob's clicks), Clear + a knob = c to 0; the stock's pans are not touched;
  * in the mode, the values the flusher sends: L = the track's level (0 while it is muted), R = c; the level = max(L, R), the pan the one that
    gives L on the left and R on the right (L >= R: 64 R / L, else 127 - 63 L / R); a muted track's sends 0;
  * in the mode a muted track with c > 0 is played (the player's mute read gives 0), so it sounds only on the right; its pad stays muted;
  * the LED task: the tracks whose mute changed, every track when the mode or a send changed: their four values marked and the flusher run;
    the Mixer on the screen: button 19's LED pink in the mode; on the pan page in the mode, the knobs pink with c as brightness (kbright).
  The mode and the sends live in RAM (until power-off).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b, b_cond, b_w, bl, cmp_imm, cmp_reg, h, ldr_imm, ldrb_imm, ldrb_w, lsls_imm, lsls_reg,  # noqa: E402
                   lsrs_imm, lsrs_reg, mov_reg, movs_imm, movt, movw, muls, orrs_reg, pop_list, push_list, raw, str_imm, strb_imm, strh_imm,
                   strh_w_imm, subs_reg, tst_reg)
import countin as CI  # noqa: E402
import mixshift as MS  # noqa: E402
import rhstate  # noqa: E402

MIX_VIEW, MIX_VT, SLOT_KNOB = MS.MIX_VIEW, MS.MIX_VT, MS.SLOT_KNOB
O_PAGE, O_HELD, O_KNOBS, SPECIAL = MS.O_PAGE, MS.O_HELD, MS.O_KNOBS, MS.SPECIAL
MUTE_GET = 0x08055176                                      # the player's bl to the getter of its mute
FLUSH_CALL, PARAM_SEND, FLUSH = 0x0803085E, 0x0804070E, 0x0803081C
DIRTY = 0x20006B68
GROUP_GET = 0x08046410
DP0, DP_SZ, P_MUTE = 0x200470D4, 0x190, 0x28
I_LEVEL, I_PAN, I_REV, I_DEL = 0x10, 0x11, 0x12, 0x13
GET = CI.PARAM_GET
ON = 0xC5
LED_PANBTN, LED_KNOB0 = 51, 60
COL_PINK = 0x67
O = rhstate.OFF2["cue"][0]
R_MODE, R_MUTES, R_PEND, R_ZERO, R_C = 0, 1, 2, 3, 4
O_KB = rhstate.OFF["kbright"][0]
K_MASK, K_VAL, K_CODE = 0, 1, 10


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))
def udiv(rd, rn, rm): return h(0xFBB0 | rn) + h(0xF0F0 | rd << 8 | rm)
def ldrb_reg(rt, rn, rm): return h(0x5C00 | rm << 6 | rn << 3 | rt)
def strb_reg(rt, rn, rm): return h(0x5400 | rm << 6 | rn << 3 | rt)


def model(level, muted, c):
    """(level, pan) the DSP gets in the mode (the tests')"""
    L, R = (0 if muted else level), c
    lv = max(L, R)
    if L >= R:
        pan = 64 if L == 0 else 64 * R // L
    else:
        pan = 127 - 63 * L // R
    return lv, pan


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_curam() -> r0 = our RAM when the mode is on, else 0; r1 = our RAM (0 without it); clobbers r2, r3
    a.label("c_curam")
    E(push_list, [4], lr=True)
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "cr_0", "eq")
    E(movw, 1, O)
    E(adds_reg, 1, 0, 1)
    E(mov_reg, 0, 1)
    E(ldrb_imm, 2, 1, R_MODE)
    E(cmp_imm, 2, ON)
    E(b_cond, "cr_x", "eq")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)
    a.label("cr_0")
    E(movs_imm, 1, 0)
    a.label("cr_x")
    E(pop_list, [4], pc=True)

    # ---- c_cumuted(r0 = track) -> r0 = 1 when it is muted; clobbers r1-r3
    a.label("c_cumuted")
    E(push_list, [4], lr=True)
    E(movw, 1, DP_SZ)
    E(muls, 0, 1)
    imm32(1, DP0)
    E(adds_reg, 0, 0, 1)
    E(ldr_imm, 0, 0, P_MUTE)
    E(movs_imm, 1, 0)
    E(bl, GET)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "cm_x", "eq")
    E(movs_imm, 0, 1)
    a.label("cm_x")
    E(pop_list, [4], pc=True)

    # ---- c_cumute (the player's getter call of its mute: r0 = the store, r1 = 0; r4 = the player) -> r0 = the byte's pointer; a muted track
    #      sent to the cue in the mode: a zero byte (it plays)
    a.label("c_cumute")
    E(push_list, [4, 5], lr=True)
    E(bl, GET)
    E(ldrb_imm, 1, 0, 0)
    E(cmp_imm, 1, 0)
    E(b_cond, "mu_x", "eq")
    E(mov_reg, 5, 0)
    imm32(0, DP0)
    E(subs_reg, 4, 4, 0)
    E(movw, 0, DP_SZ)
    E(raw, udiv(4, 4, 0))                                                 # r4 = the track
    E(cmp_imm, 4, 8)
    E(b_cond, "mu_r", "hs")
    E(bl, "c_curam")
    E(cmp_imm, 0, 0)
    E(b_cond, "mu_r", "eq")
    E(adds_reg, 1, 0, 4)
    E(ldrb_imm, 1, 1, R_C)
    E(cmp_imm, 1, 0)
    E(b_cond, "mu_r", "eq")
    E(adds_imm8, 0, R_ZERO)
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 0, 0)
    E(pop_list, [4, 5], pc=True)
    a.label("mu_r")
    E(mov_reg, 0, 5)
    a.label("mu_x")
    E(pop_list, [4, 5], pc=True)

    # ---- c_cuparam (the flusher's call: r0 = track, r1 = index, r2 = value): in the mode, the level, the pan and the sends for the cue
    a.label("c_cuparam")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(cmp_imm, 1, I_LEVEL)
    E(b_cond, "cp_s", "lo")
    E(cmp_imm, 1, I_DEL)
    E(b_cond, "cp_s", "hi")
    E(cmp_imm, 0, 8)
    E(b_cond, "cp_s", "hs")
    E(bl, "c_curam")
    E(cmp_imm, 0, 0)
    E(b_cond, "cp_s", "eq")
    E(raw, h(0x9C00))                                                     # ldr r4, [sp]: the track
    E(adds_reg, 0, 0, 4)
    E(ldrb_imm, 6, 0, R_C)                                                # r6 = R
    E(mov_reg, 0, 4)
    E(bl, "c_cumuted")
    E(mov_reg, 7, 0)                                                      # r7 = muted
    E(raw, h(0x9901))                                                     # ldr r1, [sp, #4]: the index
    E(cmp_imm, 1, I_REV)
    E(b_cond, "cp_lp", "lo")
    E(cmp_imm, 7, 0)                                                      # the sends: 0 when muted
    E(b_cond, "cp_s", "eq")
    E(movs_imm, 2, 0)
    E(b, "cp_go")
    a.label("cp_lp")
    E(movs_imm, 5, 0)                                                     # r5 = L
    E(cmp_imm, 7, 0)
    E(b_cond, "cp_m", "ne")
    E(mov_reg, 0, 4)
    E(adds_imm8, 0, 0x10)
    E(movs_imm, 1, I_LEVEL)
    E(bl, GROUP_GET)
    E(raw, h(0xB2C5))                                                     # uxtb r5, r0
    a.label("cp_m")
    E(raw, h(0x9901))
    E(cmp_imm, 1, I_LEVEL)
    E(b_cond, "cp_pan", "ne")
    E(mov_reg, 2, 5)                                                      # the level = max(L, R)
    E(cmp_reg, 6, 5)
    E(b_cond, "cp_go", "ls")
    E(mov_reg, 2, 6)
    E(b, "cp_go")
    a.label("cp_pan")
    E(cmp_reg, 5, 6)
    E(b_cond, "cp_rl", "lo")
    E(movs_imm, 2, 64)                                                    # L >= R: 64 R / L (L = 0: the centre)
    E(cmp_imm, 5, 0)
    E(b_cond, "cp_go", "eq")
    E(lsls_imm, 2, 6, 6)
    E(raw, udiv(2, 2, 5))
    E(b, "cp_go")
    a.label("cp_rl")                                                      # L < R: 127 - 63 L / R
    E(movs_imm, 2, 63)
    E(muls, 2, 5)
    E(raw, udiv(2, 2, 6))
    E(movs_imm, 0, 127)
    E(subs_reg, 2, 0, 2)
    a.label("cp_go")
    E(raw, h(0x9800))                                                     # ldr r0, [sp]
    E(raw, h(0x9901))                                                     # ldr r1, [sp, #4]
    E(bl, PARAM_SEND)
    E(raw, popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    E(raw, h(0x4770))
    a.label("cp_s")
    E(raw, popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    E(b_w, PARAM_SEND)

    # ---- c_cuknob (the Mixer's knob slot: view, knob, delta): the pan page: Shift + knob = the mode, in the mode the cue sends
    a.label("c_cuknob")
    E(push_list, [0, 1, 2, 3, 4, 5, 6, 7], lr=True)
    E(cmp_imm, 1, 8)
    E(b_cond, "ck_s", "hs")
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ck_s", "eq")
    E(raw, h(0x9800))                                                     # ldr r0, [sp]: the view
    E(adds_imm8, 0, O_PAGE)                                               # (the page's store is inside the view)
    E(movs_imm, 1, 0)
    E(bl, GET)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, 1)
    E(b_cond, "ck_s", "ne")                                               # not the pan page
    E(raw, h(0x9800))
    E(adds_imm8, 0, O_KNOBS)
    E(bl, SPECIAL)
    E(cmp_imm, 0, 0)
    E(b_cond, "ck_s", "ne")
    E(bl, "c_curam")
    E(cmp_imm, 1, 0)
    E(b_cond, "ck_s", "eq")
    E(mov_reg, 4, 1)                                                      # r4 = our RAM
    E(mov_reg, 5, 0)                                                      # r5 = on (our RAM) / off (0)
    E(bl, L["c_cishift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ck_n", "eq")
    E(movs_imm, 0, ON)                                                    # Shift: the mode, right on / left off
    E(raw, h(0x9A02))                                                     # ldr r2, [sp, #8]: the delta
    E(cmp_imm, 2, 0)
    E(b_cond, "ck_w", "gt")
    E(movs_imm, 0, 0)
    a.label("ck_w")
    E(ldrb_imm, 1, 4, R_MODE)
    E(cmp_reg, 1, 0)
    E(b_cond, "ck_x", "eq")
    E(strb_imm, 0, 4, R_MODE)
    E(movs_imm, 0, 0xFF)
    E(strb_imm, 0, 4, R_PEND)
    E(b, "ck_x")
    a.label("ck_n")
    E(cmp_imm, 5, 0)
    E(b_cond, "ck_s", "eq")                                               # not in the mode: the stock's
    E(raw, h(0x9901))                                                     # ldr r1, [sp, #4]: the knob
    E(adds_reg, 6, 4, 1)
    E(ldrb_imm, 2, 6, R_C)
    E(raw, h(0x9800))
    E(ldr_imm, 0, 0, O_HELD)
    E(push_list, [2])
    E(movs_imm, 1, 0)
    E(bl, GET)
    E(pop_list, [2])
    E(ldrb_imm, 0, 0, 0)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "ck_cl", "mi")                                              # Clear held: 0
    E(raw, h(0x9B02))                                                     # ldr r3, [sp, #8]: the delta
    E(adds_reg, 2, 2, 3)
    E(b_cond, "ck_c0", "mi")
    E(cmp_imm, 2, 127)
    E(b_cond, "ck_cw", "le")
    E(movs_imm, 2, 127)
    E(b, "ck_cw")
    a.label("ck_cl")
    a.label("ck_c0")
    E(movs_imm, 2, 0)
    a.label("ck_cw")
    E(strb_imm, 2, 6, R_C)
    E(raw, h(0x9901))
    E(movs_imm, 0, 1)
    E(lsls_reg, 0, 1)
    E(ldrb_imm, 1, 4, R_PEND)
    E(orrs_reg, 1, 0)
    E(strb_imm, 1, 4, R_PEND)
    a.label("ck_x")
    E(pop_list, [0, 1, 2, 3, 4, 5, 6, 7], pc=True)
    a.label("ck_s")
    E(raw, popw([0, 1, 2, 3, 4, 5, 6, 7], lr=True))
    E(b_w, prev["knob"])

    # ---- c_cusend(r0 = track): its level, pan and sends marked and the flusher run (through c_cuparam); clobbers r0-r3
    a.label("c_cusend")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    imm32(1, DIRTY)
    E(lsls_imm, 2, 0, 2)
    E(adds_reg, 1, 1, 2)
    E(ldr_imm, 2, 1, 0)
    imm32(3, 0xF << I_LEVEL)
    E(orrs_reg, 2, 3)
    E(str_imm, 2, 1, 0)
    E(mov_reg, 0, 4)
    E(bl, FLUSH)
    E(pop_list, [4], pc=True)

    # ---- c_culed (the LED task's calls: ctrl, frame): the chain; the tracks to send again; the Mixer's LEDs in the mode
    a.label("c_culed")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)                                                      # r5 = the frame
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "cl_x", "eq")
    E(bl, "c_curam")
    E(cmp_imm, 1, 0)
    E(b_cond, "cl_x", "eq")
    E(mov_reg, 4, 1)                                                      # r4 = our RAM
    E(movs_imm, 6, 0)                                                     # r6 = the mutes now
    E(movs_imm, 7, 0)
    a.label("cl_m")
    E(mov_reg, 0, 7)
    E(bl, "c_cumuted")
    E(lsls_reg, 0, 7)
    E(orrs_reg, 6, 0)
    E(adds_imm8, 7, 1)
    E(cmp_imm, 7, 8)
    E(b_cond, "cl_m", "lo")
    E(ldrb_imm, 0, 4, R_MUTES)
    E(raw, h(0x4070))                                                     # eors r0, r6: the mutes changed
    E(strb_imm, 6, 4, R_MUTES)
    E(ldrb_imm, 1, 4, R_MODE)
    E(cmp_imm, 1, ON)
    E(b_cond, "cl_p", "ne")
    E(ldrb_imm, 1, 4, R_PEND)
    E(orrs_reg, 1, 0)
    E(strb_imm, 1, 4, R_PEND)
    a.label("cl_p")
    E(ldrb_imm, 6, 4, R_PEND)                                             # the tracks to send again
    E(cmp_imm, 6, 0)
    E(b_cond, "cl_l", "eq")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 4, R_PEND)
    E(movs_imm, 7, 0)
    a.label("cl_s")
    E(mov_reg, 0, 6)
    E(lsrs_reg, 0, 7)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "cl_n", "pl")
    E(mov_reg, 0, 7)
    E(bl, "c_cusend")
    a.label("cl_n")
    E(adds_imm8, 7, 1)
    E(cmp_imm, 7, 8)
    E(b_cond, "cl_s", "lo")
    a.label("cl_l")
    E(ldrb_imm, 0, 4, R_MODE)                                             # the Mixer on the screen, the mode on
    E(cmp_imm, 0, ON)
    E(b_cond, "cl_x", "ne")
    imm32(0, CI.CTRL)
    E(ldr_imm, 1, 0, 0x7C)
    imm32(0, MIX_VIEW)
    E(cmp_reg, 0, 1)
    E(b_cond, "cl_x", "ne")
    E(movs_imm, 0, COL_PINK)
    E(strh_w_imm, 0, 5, 2 * LED_PANBTN)
    imm32(0, MIX_VIEW + O_PAGE)
    E(movs_imm, 1, 0)
    E(bl, GET)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, 1)
    E(b_cond, "cl_x", "ne")                                               # not the pan page
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "cl_x", "eq")
    E(adds_imm8, 0, O_KB)
    E(mov_reg, 6, 0)                                                      # r6 = kbright's overlay
    E(movs_imm, 0, 0xFF)
    E(strb_imm, 0, 6, K_MASK)
    E(movs_imm, 7, 0)
    a.label("cl_k")
    E(adds_reg, 0, 4, 7)
    E(ldrb_imm, 0, 0, R_C)
    E(adds_reg, 1, 6, 7)
    E(strb_imm, 0, 1, K_VAL)
    E(lsls_imm, 1, 7, 1)
    E(adds_reg, 1, 6, 1)
    E(movs_imm, 0, COL_PINK)
    E(strh_imm, 0, 1, K_CODE)
    E(lsls_imm, 1, 7, 1)
    E(adds_reg, 1, 5, 1)
    E(strh_w_imm, 0, 1, 2 * LED_KNOB0)
    E(adds_imm8, 7, 1)
    E(cmp_imm, 7, 8)
    E(b_cond, "cl_k", "lo")
    a.label("cl_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """The player's mute read, the flusher's call, the head of the Mixer's knob slot, the head of the LED calls.  Needs mixshift, kbright,
    rhstate ram2."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]                 # noqa: E731
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    for need in ("mixshift", "kbright"):
        assert need in report, f"cue needs {need}"
    L = dict(c_rram=lab("rhstate", "c_rram"), c_rst=lab("rhstate", "c_rst"), c_ciok=lab("countin", "c_ciok"),
             c_cishift=lab("countin", "c_cishift"))
    prev = dict(knob=u(SLOT_KNOB) & ~1, ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, MUTE_GET, f"bl #{GET:#x}", bl(MUTE_GET, labels["c_cumute"]))
    rhbuild.patch(img, FLUSH_CALL, f"bl #{PARAM_SEND:#x}", bl(FLUSH_CALL, labels["c_cuparam"]))
    rhbuild.patch_word(img, SLOT_KNOB, prev["knob"] | 1, labels["c_cuknob"] | 1)
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_culed"]))
    report["cue"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
