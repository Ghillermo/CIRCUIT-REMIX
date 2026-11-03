"""The track buttons flash white when their track triggers, while Shift is held (MIT; RH60, the user, 2026-10-29: «add a white flash cue on
track pads for each track when they trigger (only visible when pressing shift)»; CIRCUIT-HACKS' trigled of SC48.8, as a flash).

Every note to the DSP goes through 0x08040778(code, note, velocity) (the pads, the sequencer, the arpeggios, MIDI; the track = code & 7; a
note from 0x6F up does nothing there): its entry (push.w {r4-r9, r11, lr}) -> c_tfon, which keeps the HAL tick's low 16 bits for the track
(OFF2 "trigflash" + 2 t), then the stock's prologue and on.  The LED calls -> c_tfled: the chain, then with Shift held each track button
(LEDs 32 + t) white for FLASH ms after its last note; a time older than FLASH is moved along with the clock, so the 16-bit tick never wraps
back into a flash.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b, b_cond, b_w, bl, cmp_imm, ldr_imm, ldrh_imm, lsls_imm, mov_reg, movs_imm, movt, movw,  # noqa: E402
                   pop_list, push_list, raw, strh_imm, strh_w_imm, subs_reg)
import countin as CI  # noqa: E402
import drumpat as DQ  # noqa: E402
import rhstate  # noqa: E402
import stockplus as SP  # noqa: E402

O, O_LEN = rhstate.OFF2["trigflash"]
NOTE_DSP, MAX_NOTE = 0x08040778, 0x6F
HEAD = "push.w {r4, r5, r6, r7, r8, sb, fp, lr}"
HAL_TICK = 0x20006F3C
FLASH = 100                                                 # ms
WHITE = 0x01
LED_TRK0 = SP.LED_TRK0


def model_lit(now, last):
    """the button lit (Shift held): its last note within FLASH ms"""
    return (now - last) & 0xFFFF < FLASH


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_tfon (0x08040778's entry: code, note, velocity): the track's time, then the stock's prologue and on
    a.label("c_tfon")
    E(push_list, [0, 1, 2, 3, 4], lr=True)
    E(cmp_imm, 1, MAX_NOTE)
    E(b_cond, "on_x", "hs")
    E(mov_reg, 4, 0)
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "on_x", "eq")
    E(movs_imm, 1, 7)
    E(raw, DQ.h(0x400C))                                                  # ands r4, r1
    E(lsls_imm, 4, 4, 1)
    E(adds_reg, 0, 0, 4)
    imm32(1, HAL_TICK)
    E(ldr_imm, 1, 1, 0)
    E(movw, 2, O)
    E(raw, DQ.h(0x5281))                                                  # strh r1, [r0, r2]
    a.label("on_x")
    E(raw, DQ.popw([0, 1, 2, 3, 4], lr=True))
    E(raw, DQ.pushw([4, 5, 6, 7, 8, 9, 11], lr=True))                     # the stock's prologue
    E(b_w, NOTE_DSP + 4)

    # ---- c_tfled (the LED task's calls: ctrl, frame): the chain; the old times moved along; Shift held: the buttons of recent notes white
    a.label("c_tfled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)                                                      # r5 = the frame
    E(bl, prev["ledtask"])
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ld_x", "eq")
    E(movw, 1, O)
    E(adds_reg, 4, 0, 1)                                                  # r4 = the times
    E(bl, L["c_cishift"])
    E(mov_reg, 7, 0)                                                      # r7 = Shift held
    imm32(0, HAL_TICK)
    E(ldr_imm, 6, 0, 0)                                                   # r6 = now
    E(movs_imm, 3, 0)
    a.label("ld_l")
    E(lsls_imm, 2, 3, 1)
    E(adds_reg, 2, 2, 4)
    E(ldrh_imm, 1, 2, 0)
    E(subs_reg, 0, 6, 1)
    E(lsls_imm, 0, 0, 16)
    E(raw, DQ.h(0x0C00))                                                  # lsrs r0, r0, #16: (now - its time) & 0xFFFF
    E(cmp_imm, 0, FLASH)
    E(b_cond, "ld_o", "hs")
    E(cmp_imm, 7, 0)
    E(b_cond, "ld_n", "eq")
    E(movs_imm, 0, WHITE)
    E(lsls_imm, 1, 3, 1)
    E(adds_reg, 1, 1, 5)
    E(strh_w_imm, 0, 1, 2 * LED_TRK0)
    a.label("ld_n")
    E(adds_imm8, 3, 1)
    E(cmp_imm, 3, 8)
    E(b_cond, "ld_l", "lo")
    a.label("ld_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    a.label("ld_o")                                                       # older than a flash: kept just out of it (now - FLASH)
    E(movs_imm, 0, FLASH)
    E(subs_reg, 1, 6, 0)
    E(strh_imm, 1, 2, 0)
    E(b, "ld_n")
    return a.assemble()


def install(img, report, base_addr):
    """0x08040778's entry, the LED calls (their outermost head).  Needs countin (Shift) and rhstate ram2; not latdiag."""
    import rhbuild
    BASE = rhbuild.BASE
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    assert "latdiag" not in report
    L = dict(c_rram=lab("rhstate", "c_rram"), c_cishift=lab("countin", "c_cishift"))
    prev = dict(ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code_, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code_
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, NOTE_DSP, HEAD, b_w(NOTE_DSP, labels["c_tfon"]))
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_tfled"]))
    report["trigflash"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code_
