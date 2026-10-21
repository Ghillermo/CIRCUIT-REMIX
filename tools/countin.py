"""The metronome's four states and a count-in of one bar before recording (MIT; CIRCUIT-HACKS' countin of SC41.8 / SC42.3, issue #2 of
the public repo: «usa un toggle en el metrónomo: sin metrónomo, con metrónomo, sólo countdown, countdown y metrónomo», moved to the Rhythm 5706).

The stock of the Rhythm (read in the firmware and on the RAM dump, emulated):
  * the controller 0x200487C8 (vtable 0x080672E4): button press 0x0803D8B8(ctrl, id), release 0x0803DDB0(ctrl, id); Shift = p0 of [ctrl + 0xC];
    ids as the Tracks: 16 Record, 17 Play, 23 Clear (the Shift mask 0x07DFFF00 lets Clear through);
  * Shift + Clear toggles the metronome through the generic parameter setter 0x08038A08(0x20011998, 0xC7, value) (the Tracks' 0x08031608(0x200109D8,
    0x64, v), re-coded): parameter 3 of the store [0x20011998 + 0x3C] = 0x20012200;
  * the click: 0x080333AA(clock 0x2003C200) on the beats, with the metronome on: 0x08046780(0xFF, 0, 0x60) (the Tracks' 0x0803BD58, the same function);
  * [0x2003C200 + 8] = 0x200126E8: + 0x10 the transport store 0x200122B0 (p0 playing, p1 recording), + 0x14 the tempo store 0x20012788 (p1 = BPM);
  * a store keeps two copies of each parameter; 0x0803FC6C(store, i) returns the newest one without side effects (the write getter 0x0803FD26,
    which the Tracks version reads with, marks the parameter as written): every read here uses 0x0803FC6C.

Ours, as in the Tracks:
  * a new head of the button chain (0x0803D8B8): Shift + Clear walks four states: 0 no metronome, 1 metronome, 2 count-in only, 3 count-in and
    metronome (the metronome through the stock's setter, the count-in a byte of ours);
  * Play from stopped with Record armed and the count-in on: the press is kept; the LED task sends a click on each of 4 beats at the project's tempo
    (60000 / BPM ms; the stock's click call: the stock's sound) with the Record LED blinking, then presses Play itself (a pass flag lets that press
    through); Play again during the count cancels it; a transport started otherwise cancels it;
  * (v2, RH18) a kept Shift + Play (the stock's «play from where it stopped») is pressed with Shift at the end of the count;
  * Shift held: the Clear LED = red no metronome, green metronome, magenta count-in only, cyan both (the SC42.3 colours; the Rhythm's codes of the
    same RGB, tools/rhpalette.py).
Unlike the Tracks, the count-in setting lives in our RAM (rhstate), not in the project: the Rhythm's session file is not studied yet.  It is
off at power-on.  Every entry checks that the controller and the metronome's owner are where the dump has them (else the stock path, untouched).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, b, b_cond, b_w, bl, cmp_imm, cmp_reg, ldr_imm, ldrb_imm, lsls_imm, mov_reg, movs_imm, movt, movw, muls, pop_list,  # noqa: E402
                   push_list, raw, h, str_imm, strb_imm, subs_reg, adds_imm8)
import rhstate  # noqa: E402
import rodisk  # noqa: E402

CTRL, CTRL_VT = 0x200487C8, 0x080672E4
BTN_ENTRY, BTN_RELEASE = 0x0803D8B8, 0x0803DDB0
ENTRY_EXPECT, ENTRY_OLD = "push {r3, r4, r5, r6, r7, lr}|mov r4, r0", bytes.fromhex("f8b50446")
ID_CLEAR, ID_PLAY = 23, 17
PARAM_GET, PARAM_NEW = 0x0803FC58, 0x0803FC6C
SETTER, SET_OBJ, ID_METRO = 0x08038A08, 0x20011998, 0xC7
METRO_STORE = 0x20012200                                  # [SET_OBJ + 0x3C]: parameter 3 = the metronome
TRANSPORT, TEMPO = 0x200122B0, 0x20012788                 # p0 playing, p1 recording / p1 = BPM
CLICK = 0x08046780
HAL_TICK = rodisk.HAL_TICK
LED_CALLS = rodisk.LED_CALLS
O_FLAG, O_N, O_PASS, O_T0 = (rhstate.OFF["countin"][0] + k for k in (0, 1, 2, 4))
CI_ON = 0xC1
BEATS = 4
LED_REC, LED_CLEAR = 48, 55
COL_REC = 0x55                                            # red (Tracks 0x53)
COLS = (0x55, 0x1E, 0x37, 0x4B)                           # state 0..3: red, green, magenta, cyan (Tracks 0x53, 0x17, 0x32, 0x4D)


def udiv(rd, rn, rm): return h(0xFBB0 | rn) + h(0xF0F0 | rd << 8 | rm)
def pushw(regs, lr=False): return h(0xE92D) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))
def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


V2 = False                                               # RH18 (install(v2=True)): Shift + Play from stopped keeps its Shift through the count-in
BPM0 = False                                             # RH29 (install(bpm0=True)): the beat from p0 of the tempo store, the project's BPM (the Tempo
                                                         # view's knob 1 writes p0; p1, which RH02-RH28 read, is not the tempo: «pre count doesnt get
                                                         # the right beat», the user, 2026-10-20; the same fix as the Tracks' RC2.03 use_bpm0)
O_SH = rhstate.OFF["countin"][0] + 3                      # (v2) Shift held at the kept press
WPTR, COMMIT = 0x0803FD26, 0x0803FBEC


def arm_code(base, prev, c_rst):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- the stock's own start of the button press (when no other module took the head before us)
    if prev["btn"] is None:
        a.label("c_cibtn_stock")
        E(raw, ENTRY_OLD)
        E(b_w, BTN_ENTRY + 4)
        prev = dict(prev, btn="c_cibtn_stock")

    # ---- c_ciok() -> r0 = 1 when the controller and the metronome's owner are the dump's; clobbers r1, r2
    a.label("c_ciok")
    imm32(0, CTRL)
    E(ldr_imm, 0, 0, 0)
    imm32(1, CTRL_VT)
    E(cmp_reg, 0, 1)
    E(b_cond, "ok_no", "ne")
    imm32(0, SET_OBJ)
    E(ldr_imm, 0, 0, 0x3C)
    imm32(1, METRO_STORE)
    E(cmp_reg, 0, 1)
    E(b_cond, "ok_no", "ne")
    E(movs_imm, 0, 1)
    E(raw, h(0x4770))
    a.label("ok_no")
    E(movs_imm, 0, 0)
    E(raw, h(0x4770))

    # ---- c_cinew(r0 = store, r1 = parameter) -> r0 = its byte (the newest copy, no side effects)
    a.label("c_cinew")
    E(push_list, [3], lr=True)
    E(bl, PARAM_NEW)
    E(ldrb_imm, 0, 0, 0)
    E(pop_list, [3], pc=True)

    if V2:
        # ---- c_cisetsh(r0 = 0 / 1): Shift's parameter (p0 of [ctrl + 0xC]) written and committed; clobbers r0-r3
        a.label("c_cisetsh")
        E(push_list, [4, 5], lr=True)
        E(mov_reg, 5, 0)
        imm32(0, CTRL)
        E(ldr_imm, 4, 0, 0xC)
        E(mov_reg, 0, 4)
        E(movs_imm, 1, 0)
        E(bl, WPTR)
        E(strb_imm, 5, 0, 0)
        E(mov_reg, 0, 4)
        E(bl, COMMIT)
        E(pop_list, [4, 5], pc=True)

    # ---- c_cishift() -> r0 = Shift held
    a.label("c_cishift")
    E(push_list, [3], lr=True)
    imm32(0, CTRL)
    E(ldr_imm, 0, 0, 0xC)
    E(movs_imm, 1, 0)
    E(bl, PARAM_GET)
    E(ldrb_imm, 0, 0, 0)
    E(pop_list, [3], pc=True)

    # ---- c_cistate(r0 = our block) -> r0 = 0..3 (bit 0 the metronome, bit 1 the count-in); clobbers r1-r3
    a.label("c_cistate")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 5, 0)
    imm32(0, METRO_STORE)
    E(movs_imm, 1, 3)
    E(bl, "c_cinew")
    E(movs_imm, 1, 1)
    E(raw, h(0x4008))                                                     # ands r0, r1
    E(mov_reg, 4, 0)
    E(ldrb_imm, 1, 5, O_FLAG)
    E(cmp_imm, 1, CI_ON)
    E(b_cond, "cs_x", "ne")
    E(adds_imm8, 4, 2)
    a.label("cs_x")
    E(mov_reg, 0, 4)
    E(pop_list, [4, 5], pc=True)

    # ---- c_cibtn (the head of the button chain: r0 = ctrl, r1 = id)
    a.label("c_cibtn")
    E(push_list, [0, 1, 2, 4, 5], lr=True)
    E(mov_reg, 5, 1)
    E(bl, c_rst)
    E(cmp_imm, 0, 0)
    E(b_cond, "cb_f", "eq")
    E(mov_reg, 4, 0)
    E(ldrb_imm, 0, 4, O_PASS)
    E(cmp_imm, 0, 0)
    E(b_cond, "cb_f", "ne")                                               # our own Play press
    E(bl, "c_ciok")
    E(cmp_imm, 0, 0)
    E(b_cond, "cb_f", "eq")
    E(cmp_imm, 5, ID_CLEAR)
    E(b_cond, "cb_p", "ne")
    E(bl, "c_cishift")
    E(cmp_imm, 0, 0)
    E(b_cond, "cb_f", "eq")
    E(mov_reg, 0, 4)
    E(bl, "c_cistate")
    E(adds_imm8, 0, 1)
    E(movs_imm, 1, 3)
    E(raw, h(0x4008))                                                     # ands r0, r1
    E(mov_reg, 5, 0)                                                      # r5 = the next state
    E(movs_imm, 0, 0)
    E(lsls_imm, 2, 5, 30)
    E(b_cond, "cb_s", "pl")
    E(movs_imm, 0, CI_ON)                                                 # bit 1: the count-in
    a.label("cb_s")
    E(strb_imm, 0, 4, O_FLAG)
    imm32(0, SET_OBJ)
    E(movs_imm, 1, ID_METRO)
    E(movs_imm, 2, 1)
    E(raw, h(0x402A))                                                     # ands r2, r5 -> the metronome
    E(bl, SETTER)
    E(b, "cb_x")
    a.label("cb_p")
    E(cmp_imm, 5, ID_PLAY)
    E(b_cond, "cb_f", "ne")
    E(ldr_imm, 0, 4, O_T0)
    E(cmp_imm, 0, 0)
    E(b_cond, "cb_go", "eq")
    E(movs_imm, 0, 0)
    E(str_imm, 0, 4, O_T0)
    E(b, "cb_x")                                                          # Play during the count: cancelled
    a.label("cb_go")
    E(mov_reg, 0, 4)
    E(bl, "c_cistate")
    E(lsls_imm, 0, 0, 30)
    E(b_cond, "cb_f", "pl")                                               # no count-in
    imm32(0, TRANSPORT)
    E(movs_imm, 1, 0)
    E(bl, "c_cinew")
    E(cmp_imm, 0, 0)
    E(b_cond, "cb_f", "ne")                                               # playing already
    imm32(0, TRANSPORT)
    E(movs_imm, 1, 1)
    E(bl, "c_cinew")
    E(cmp_imm, 0, 0)
    E(b_cond, "cb_f", "eq")                                               # Record not armed
    imm32(0, HAL_TICK)
    E(ldr_imm, 0, 0, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "cb_t", "ne")
    E(movs_imm, 0, 1)                                                     # never 0
    a.label("cb_t")
    E(str_imm, 0, 4, O_T0)
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 4, O_N)
    if V2:                                                                # Shift + Play (play from where it stopped): kept for the end
        E(bl, "c_cishift")
        E(strb_imm, 0, 4, O_SH)
    a.label("cb_x")
    E(pop_list, [0, 1, 2, 4, 5], pc=True)
    a.label("cb_f")
    E(raw, popw([0, 1, 2, 4, 5], lr=True))
    E(b_w, prev["btn"])

    # ---- c_ciledtask (the LED task's calls: r0 = ctrl, r1 = frame): the chain; the count's clicks and its end; the Record and Clear LEDs
    a.label("c_ciledtask")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)
    E(bl, prev["ledtask"])
    E(bl, c_rst)
    E(cmp_imm, 0, 0)
    E(b_cond, "cl_x", "eq")
    E(mov_reg, 4, 0)
    E(bl, "c_ciok")
    E(cmp_imm, 0, 0)
    E(b_cond, "cl_x", "eq")
    E(ldr_imm, 0, 4, O_T0)
    E(cmp_imm, 0, 0)
    E(b_cond, "cl_sh", "eq")
    imm32(0, TRANSPORT)
    E(movs_imm, 1, 0)
    E(bl, "c_cinew")
    E(cmp_imm, 0, 0)
    E(b_cond, "cl_end", "ne")                                             # started otherwise: no count
    imm32(0, TEMPO)
    E(movs_imm, 1, 0 if BPM0 else 1)
    E(bl, "c_cinew")
    E(cmp_imm, 0, 30)
    E(b_cond, "cl_bt", "hs")
    E(movs_imm, 0, 120)
    a.label("cl_bt")
    E(mov_reg, 1, 0)
    imm32(0, 60000)
    E(raw, udiv(6, 0, 1))                                                 # r6 = ms per beat
    imm32(0, HAL_TICK)
    E(ldr_imm, 0, 0, 0)
    E(ldr_imm, 1, 4, O_T0)
    E(subs_reg, 7, 0, 1)                                                  # r7 = ms since the press
    E(b_cond, "cl_pos", "pl")
    E(movs_imm, 7, 0)
    a.label("cl_pos")
    E(raw, udiv(0, 7, 6))                                                 # r0 = the beat
    E(cmp_imm, 0, BEATS)
    E(b_cond, "cl_go", "hs")
    E(ldrb_imm, 1, 4, O_N)
    E(cmp_reg, 0, 1)
    E(b_cond, "cl_led", "lo")
    E(adds_imm8, 0, 1)
    E(strb_imm, 0, 4, O_N)
    E(movs_imm, 0, 0xFF)
    E(movs_imm, 1, 0)
    E(movs_imm, 2, 0x60)
    E(bl, CLICK)
    a.label("cl_led")                                                     # Record blinks: red the first half of each beat
    E(raw, udiv(0, 7, 6))
    E(muls, 0, 6)
    E(subs_reg, 0, 7, 0)
    E(lsls_imm, 0, 0, 1)
    E(movs_imm, 1, 0)
    E(cmp_reg, 0, 6)
    E(b_cond, "cl_lw", "hs")
    E(movs_imm, 1, COL_REC)
    a.label("cl_lw")
    E(movs_imm, 0, 2 * LED_REC)
    E(raw, h(0x5229))                                                     # strh r1, [r5, r0]
    E(b, "cl_sh")
    a.label("cl_go")                                                      # the bar is over: Play
    E(movs_imm, 0, 0)
    E(str_imm, 0, 4, O_T0)
    E(movs_imm, 0, 1)
    E(strb_imm, 0, 4, O_PASS)
    if V2:                                                                # the kept press had Shift: Play with Shift
        E(ldrb_imm, 0, 4, O_SH)
        E(cmp_imm, 0, 0)
        E(b_cond, "cl_ps", "eq")
        E(movs_imm, 0, 1)
        E(bl, "c_cisetsh")
        a.label("cl_ps")
    imm32(0, CTRL)
    E(movs_imm, 1, ID_PLAY)
    E(bl, BTN_ENTRY)
    imm32(0, CTRL)
    E(movs_imm, 1, ID_PLAY)
    E(bl, BTN_RELEASE)
    if V2:
        E(ldrb_imm, 0, 4, O_SH)
        E(cmp_imm, 0, 0)
        E(b_cond, "cl_ns", "eq")
        E(movs_imm, 0, 0)
        E(bl, "c_cisetsh")
        E(movs_imm, 0, 0)
        E(strb_imm, 0, 4, O_SH)
        a.label("cl_ns")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 4, O_PASS)
    E(b, "cl_sh")
    a.label("cl_end")
    E(movs_imm, 0, 0)
    E(str_imm, 0, 4, O_T0)
    a.label("cl_sh")                                                      # Shift held: the Clear LED = the state
    E(bl, "c_cishift")
    E(cmp_imm, 0, 0)
    E(b_cond, "cl_x", "eq")
    E(mov_reg, 0, 4)
    E(bl, "c_cistate")
    for k, col in enumerate(COLS):
        E(movs_imm, 1, col)
        E(cmp_imm, 0, k)
        E(b_cond, "cl_cw", "eq")
    a.label("cl_cw")
    E(movs_imm, 0, 2 * LED_CLEAR)
    E(raw, h(0x5229))                                                     # strh r1, [r5, r0]
    a.label("cl_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr, v2=False, bpm0=False):
    """Append the code; the head of the button chain, the two LED task calls."""
    global V2, BPM0
    V2, BPM0 = v2, bpm0
    import rhbuild
    BASE = rhbuild.BASE
    c_rst = int(report["rhstate"]["labels"]["c_rst"], 16)
    head = bytes(img[BTN_ENTRY - BASE:BTN_ENTRY - BASE + 4])
    prev = dict(btn=None if head == ENTRY_OLD else rhbuild.bw_target(img, BTN_ENTRY), ledtask=rhbuild.bl_target(img, LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in LED_CALLS)
    code, labels = arm_code(base_addr, prev, c_rst)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    if prev["btn"] is None:
        rhbuild.patch(img, BTN_ENTRY, ENTRY_EXPECT, b_w(BTN_ENTRY, labels["c_cibtn"]))
    else:
        rhbuild.patch(img, BTN_ENTRY, f"b.w #{prev['btn']:#x}", b_w(BTN_ENTRY, labels["c_cibtn"]))
    for c in LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_ciledtask"]))
    report["countin"] = dict(btn_entry=hex(BTN_ENTRY), led_calls=[hex(c) for c in LED_CALLS],
                             prev={k: (hex(v) if isinstance(v, int) else v) for k, v in prev.items()},
                             labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
