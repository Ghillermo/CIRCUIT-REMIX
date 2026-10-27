"""The card's long waits give the CPU to the other tasks (MIT; RD29, docs/PRUEBA_RD29.md): the stock's clock stumble while a sample is saved.

RD28 on the device (2026-10-26): the timers' dispatcher (a task: it runs the clock) stopped ~140 ms at a time while a sample was saved,
every sample of SysTick in one loop, in a task, with no masking: the card driver's transfer wait.  0x080237EC (its callers send the
card commands 17 / 18 / 24 / 25: read and write one or several blocks) polls the transfer's status byte ([[r4 + 0x30]] bit 4: still
going) until it is done; a card can stay busy ~140 ms on some writes, and the loop never yields.  The stock's tasks are cooperative and
yield with the stock's own sleep 0x08024150 (the main loop's sleep(1), the storage task's sleep(20)): while the scheduler runs (byte
0x20006F55) it sets PendSV (ICSR = 0x10000000, dsb, isb) until the RTOS tick [0x20000820] reaches the deadline.

Ours: the loop's test (0x08023880 `ldr r0, [r4, #0x40]; cmp r0, #1`, then `beq 0x08023864`) -> c_sdy: still going -> once this wait has
lasted 2 ms or more (its start in our RAM, by the RTOS tick), the stock's yield each pass, then the loop again; done -> the stock's exit
(0x08023886).  Short waits (nearly all) stay exactly the stock's.  Without our RAM set up (very early at power-up): as the stock.
Stats (OFF2["sdyield"]): +0 in a wait, +4 its start, +8 waits of 2 ms or more, +12 the longest wait (ms), +16 yields.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import Asm, adds_imm8, b_cond, b_w, cmp_imm, cmp_reg, h, ldr_imm, ldrb_imm, movs_imm, movt, movw, raw, str_imm, subs_reg  # noqa: E402
import rhstate  # noqa: E402

O = rhstate.OFF2["sdyield"][0]
BLOCK = rhstate.ST2 + O
SITE, SITE_HEAD = 0x08023880, "ldr r0, [r4, #0x40]|cmp r0, #1"
LOOP, EXIT = 0x08023864, 0x08023886
RTOS_TICK, SCHED_ON, ICSR, PENDSVSET = 0x20000820, 0x20006F55, 0xE000ED04, 0x10000000
AFTER = 2                                          # ms of waiting before we yield
(W_IN, W_ST, W_N, W_MAX, W_Y) = (0, 4, 8, 12, 16)


def arm_code(base):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # r4 = the driver (preserved), r0-r3 free: the loop and the exit set what they need
    a.label("c_sdy")
    imm32(2, rhstate.ST2)
    E(ldr_imm, 1, 2, 0)
    imm32(3, rhstate.MAGIC2)
    E(cmp_reg, 1, 3)
    E(b_cond, "y_stock", "ne")                                # our RAM not set up: the stock's test
    imm32(2, BLOCK)
    imm32(3, RTOS_TICK)
    E(ldr_imm, 3, 3, 0)                                       # r3 = now (ms)
    E(ldr_imm, 0, 4, 0x40)
    E(cmp_imm, 0, 1)
    E(b_cond, "y_done", "ne")
    E(ldrb_imm, 1, 2, W_IN)                                   # still going
    E(cmp_imm, 1, 0)
    E(b_cond, "y_on", "ne")
    E(movs_imm, 1, 1)
    E(raw, h(0x7000 | 2 << 3 | 1))                            # strb r1, [r2, #0]: in a wait
    E(str_imm, 3, 2, W_ST)
    E(b_w, LOOP)
    a.label("y_on")
    E(ldr_imm, 1, 2, W_ST)
    E(subs_reg, 1, 3, 1)
    E(cmp_imm, 1, AFTER)
    E(b_cond, "y_loop", "lo")
    imm32(0, SCHED_ON)                                        # the stock's yield (its sleep's)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "y_loop", "eq")
    E(ldr_imm, 1, 2, W_Y)
    E(adds_imm8, 1, 1)
    E(str_imm, 1, 2, W_Y)
    imm32(0, ICSR)
    imm32(1, PENDSVSET)
    E(str_imm, 1, 0, 0)
    E(raw, h(0xF3BF) + h(0x8F4F))                             # dsb sy
    E(raw, h(0xF3BF) + h(0x8F6F))                             # isb sy
    a.label("y_loop")
    E(b_w, LOOP)
    a.label("y_done")                                         # done: the stats, then the stock's exit
    E(ldrb_imm, 1, 2, W_IN)
    E(cmp_imm, 1, 0)
    E(b_cond, "y_exit", "eq")
    E(movs_imm, 1, 0)
    E(raw, h(0x7000 | 2 << 3 | 1))                            # strb r1, [r2, #0]
    E(ldr_imm, 1, 2, W_ST)
    E(subs_reg, 1, 3, 1)                                      # this wait's length
    E(cmp_imm, 1, AFTER)
    E(b_cond, "y_exit", "lo")
    E(ldr_imm, 0, 2, W_N)
    E(adds_imm8, 0, 1)
    E(str_imm, 0, 2, W_N)
    E(ldr_imm, 0, 2, W_MAX)
    E(cmp_reg, 1, 0)
    E(b_cond, "y_exit", "ls")
    E(str_imm, 1, 2, W_MAX)
    a.label("y_exit")
    E(b_w, EXIT)
    a.label("y_stock")                                        # the stock's own test and branch
    E(ldr_imm, 0, 4, 0x40)
    E(cmp_imm, 0, 1)
    E(b_cond, "y_sl", "eq")
    E(b_w, EXIT)
    a.label("y_sl")
    E(b_w, LOOP)
    return a.assemble()


def install(img, report, base_addr):
    import rhbuild
    BASE = rhbuild.BASE
    assert "c_rram" in report["rhstate"]["labels"], "sdyield needs rhstate ram2 (RH41)"
    code, labels = arm_code(base_addr)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, SITE, SITE_HEAD, b_w(SITE, labels["c_sdy"]))
    report["sdyield"] = dict(block=hex(BLOCK), after_ms=AFTER, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
