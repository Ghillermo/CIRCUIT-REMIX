"""Step 1 at Play without waiting for the Play handler to finish (MIT; RD25, docs/PRUEBA_RD25.md).

RD24 on the device (2026-10-26, the end of docs/PORTADO.md): the first sound came ≈ 19 ms after Play, the clock's first tick 16 ms after
it.  The stock plays tick 0 (step 1's notes, the first MIDI clock, the click) on the clock timer's first pass (the callback 0x0803242C that
0x080329C0(clock, 0) registers; the sequencer's listener sees the start flag SET_TICKS left and calls 0x08034B18), and that pass only comes
once the whole Play handler is over: ≈ 420 000 instructions, the timer registered at ≈ 232 000 of them, then the transport store's
listeners.  (The Tracks' armed capture met the same start in SC38.2 / SC38.4: SET_TICKS 0x0802BFE0 there, 0x08034082 here.)

Ours, internal clock only (the clock's state [0x200126E8 + 0x56] = 1 right after 0x080329C0(clock, 0); MIDI Start leaves it at 2 and
waits for the first MIDI clock, as before):
  * the clock's start 0x080329C0(clock, mode) (its first 4 bytes -> c_sfmode; every internal start comes through it: Play from the
    sequencer's start 0x08033D32, before it writes and commits p0 of the transport store; continue (stopped Shift + Play, 0x08033E06),
    after; MIDI Start with no clock) -> the stock's, then with mode 0 and state 1: p0 of the transport store ([clock + 0x10]) = 1 in the
    copy its readers see (the sequencer's listener plays tick 0 only with it), the clock's pass at once through its own callback
    0x0803242C (tick 0: the notes, 0xF8, the click), p0 back as it was (Play: the stock then writes and commits it as always, the store
    ends as the stock's), T0 = the HAL tick, N = 1, ACT;
  * the callback's address (the literal 0x08032D2C both registrations load) -> c_sfcb: while ACT (WINDOW ms after T0), the passes the
    clock is owed by real time: e = HAL tick - T0, k = e + 1 - N (none if <= 0, at most KMAX), N += k, each through the stock's callback:
    the passes the Play handler held back come at once, so the grid stays anchored to tick 0 (one pass = 1 ms of the clock); past the
    window, or without ACT, one pass a callback as the stock.
State in rhstate's second block (OFF2["startfix"]).
always (RD27): the catch-up past the window as well (True), or while a byte is set (its address: tools/clkprobe.py's switch from the
computer), for the stock's wobble while a sample is saved (the user, 2026-10-26: «during save (sample save) the clock becomes unstable»).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, b, b_cond, b_w, bl, cmp_imm, cmp_reg, h, ldr_imm, ldrb_imm, ldrb_w, mov_reg, movs_imm, movt, movw,  # noqa: E402
                   pop_list, push_list, raw, str_imm, strb_imm, subs_imm8, subs_reg)
import rhstate  # noqa: E402

CLK_MODE, CLK_MODE_CONT, CLK_MODE_HEAD = 0x080329C0, 0x080329C4, "push {r2, r3, r4, lr}|mov r4, r0"
CB_LIT, CB = 0x08032D2C, 0x0803242C                 # the literal both timer registrations load (0x080329DC, 0x08032BEA) = CB | 1
CLOCK, ST_OFF, STARTING = 0x200126E8, 0x56, 1
HAL_TICK = 0x20006F3C
PARAM_GET = 0x0803FC58                              # (store, i) -> the word of parameter i its readers see (no side effects)
WINDOW, KMAX = 64, 32
O = rhstate.OFF2["startfix"][0]
(S_ACT, S_N, S_T0) = (0, 4, 8)                      # byte, u32, u32


def popw(regs, lr=False):
    return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def arm_code(base, L, always=None):
    """always (RD27): the catch-up past the window too: True = always, an address = while the byte there is not 0 (a switch)"""
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_sfst() -> r0 = our state, 0 without our RAM; clobbers r1-r3
    a.label("c_sfst")
    E(push_list, [4], lr=True)
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ss_x", "eq")
    E(adds_imm8, 0, O)
    a.label("ss_x")
    E(pop_list, [4], pc=True)

    # ---- c_sfmode(clock, mode): the clock's start 0x080329C0 (Play, continue, MIDI Start without a clock: mode 0 = internal); after it,
    #      in mode 0 with the clock waiting for its first pass (state 1), that pass at once
    a.label("c_sfmode")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(bl, "c_sforig")
    E(cmp_imm, 5, 0)
    E(b_cond, "sm_x", "ne")
    E(ldrb_w, 0, 4, ST_OFF)
    E(cmp_imm, 0, STARTING)
    E(b_cond, "sm_x", "ne")
    E(bl, "c_sfst")
    E(cmp_imm, 0, 0)
    E(b_cond, "sm_x", "eq")
    E(mov_reg, 6, 0)                                          # r6 = our state
    E(ldr_imm, 0, 4, 0x10)                                    # the transport store's p0 as its readers see it (0x0803FC58): 1 for the pass
    E(movs_imm, 1, 0)
    E(bl, PARAM_GET)
    E(ldrb_imm, 1, 0, 0)
    E(push_list, [0, 1])                                      # its address and its value
    E(movs_imm, 1, 1)
    E(strb_imm, 1, 0, 0)
    imm32(1, HAL_TICK)
    E(ldr_imm, 1, 1, 0)
    E(str_imm, 1, 6, S_T0)
    E(movs_imm, 1, 1)
    E(str_imm, 1, 6, S_N)
    E(strb_imm, 1, 6, S_ACT)
    E(movs_imm, 0, 0)                                         # the clock's pass now: tick 0
    E(mov_reg, 1, 4)
    E(bl, CB)
    E(pop_list, [0, 1])                                       # p0 as it was (Play: 0, the stock writes and commits it next; continue: 1)
    E(strb_imm, 1, 0, 0)
    a.label("sm_x")
    E(pop_list, [4, 5, 6], pc=True)
    a.label("c_sforig")                                       # the stock's 0x080329C0: its first two instructions, then the rest
    E(push_list, [2, 3, 4], lr=True)
    E(mov_reg, 4, 0)
    E(b_w, CLK_MODE_CONT)

    # ---- c_sfcb(r0, r1 = the clock): the timer's callback; the passes owed while ACT, else one
    a.label("c_sfcb")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 6, 0)
    E(mov_reg, 7, 1)
    E(bl, "c_sfst")
    E(cmp_imm, 0, 0)
    E(b_cond, "sc_one", "eq")
    E(mov_reg, 5, 0)
    E(ldrb_w, 0, 5, S_ACT)
    E(cmp_imm, 0, 0)
    E(b_cond, "sc_one", "eq")
    imm32(1, HAL_TICK)
    E(ldr_imm, 1, 1, 0)
    E(ldr_imm, 2, 5, S_T0)
    E(subs_reg, 1, 1, 2)                                      # r1 = e
    E(cmp_imm, 1, WINDOW)
    E(b_cond, "sc_win", "lo")
    if always is True:
        E(b, "sc_win")
    elif always:
        imm32(0, always)                                      # (RD27) the switch: the catch-up goes on while it is set
        E(ldrb_imm, 0, 0, 0)
        E(cmp_imm, 0, 0)
        E(b_cond, "sc_win", "ne")
    E(movs_imm, 0, 0)                                         # past the window: as the stock from now on
    E(strb_imm, 0, 5, S_ACT)
    E(b, "sc_one")
    a.label("sc_win")
    E(adds_imm8, 1, 1)
    E(ldr_imm, 2, 5, S_N)
    E(subs_reg, 4, 1, 2)                                      # r4 = k = e + 1 - N
    E(b_cond, "sc_x", "le")                                   # ahead (or even): no pass now
    E(cmp_imm, 4, KMAX)
    E(b_cond, "sc_lp", "ls")
    E(movs_imm, 4, KMAX)
    a.label("sc_lp")
    E(ldr_imm, 0, 5, S_N)
    E(adds_imm8, 0, 1)
    E(str_imm, 0, 5, S_N)
    E(mov_reg, 0, 6)
    E(mov_reg, 1, 7)
    E(bl, CB)
    E(subs_imm8, 4, 1)
    E(b_cond, "sc_lp", "ne")
    a.label("sc_x")
    E(pop_list, [4, 5, 6, 7], pc=True)
    a.label("sc_one")
    E(mov_reg, 0, 6)
    E(mov_reg, 1, 7)
    E(raw, popw([4, 5, 6, 7], lr=True))
    E(b_w, CB)
    return a.assemble()


def install(img, report, base_addr, always=None):
    import struct
    import rhbuild
    BASE = rhbuild.BASE
    assert "c_rram" in report["rhstate"]["labels"], "startfix needs rhstate ram2 (RH41)"
    assert struct.unpack_from("<I", img, CB_LIT - BASE)[0] == CB | 1, "the clock callback's literal moved"
    L = dict(c_rram=int(report["rhstate"]["labels"]["c_rram"], 16))
    code, labels = arm_code(base_addr, L, always=always)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, CLK_MODE, CLK_MODE_HEAD, b_w(CLK_MODE, labels["c_sfmode"]))
    rhbuild.patch_word(img, CB_LIT, CB | 1, labels["c_sfcb"] | 1)
    report["startfix"] = dict(state=hex(rhstate.ST2 + O), window=WINDOW, kmax=KMAX, always=always if always in (None, True) else hex(always),
                              labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
