"""The pack of the internal memory is read-only for the mod (MIT; CIRCUIT-HACKS' rodisk of SC41.3, the user 2026-10-14: «implementa
sólo lectura en pack interno», moved to the Circuit Rhythm 5706).

Found in the Rhythm: the storage task's pack switch 0x08040E28 (the Tracks' 0x0803676C, the same code) takes pack 0 to the volume of
[0x20006E1C] ("0:/Rhythm", drive 0 = the internal memory) and every other pack to [0x20006E20] ("1:/Rhythm", the microSD card).
**Its two special codes are swapped from the Tracks: 0xFE = the loaded pack ([[0x20006E24]] byte 0), 0xFF = none** (the Tracks: 0xFF loaded,
0xFE none).  The item of the content API is the same {u32 kind, u32 index, u8 pack}: every caller of the pack switch reads item + 8.

Every write or delete of the mod goes through the stock's two entry points: 0x0804607A (op 7, write) and 0x08046098 (op 5, delete).  Both get
a guard (their first 4 bytes -> b.w; the 4 bytes are moved into the guard): a call from our code (return address at or above MOD_START, the
end of the stock image) on an item of pack 0, or of 0xFE while pack 0 is loaded, returns «failed» (0xFFFFFFFD) without touching the memory,
and the Save LED (panel LED 57: the Rhythm's LED table 0x08066744 is the Tracks' one, entry 57 = source 5 = the Save object [ctrl + 0x48],
whose 9 functions are the Tracks' Save object's) shows red (0x53 = R 251, G 0, B 6 in the Rhythm's colour table) for 1.5 s.  The stock's
own writes (its project saves) are never stopped, and reads are never stopped.

The time of the last refusal lives in our RAM block (rhstate.OFF["rodisk"]).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, b_cond, b_w, bl, cmp_imm, cmp_reg, ldr_imm, ldrb_imm, mov_reg, movs_imm, movt, movw, pop_list, push_list, raw, h,  # noqa: E402
                   str_imm, strh_reg, subs_reg)
import rhstate  # noqa: E402

WRITE, DELETE = 0x0804607A, 0x08046098
EXPECT = {WRITE: "push {r2, r3, r4, r6, lr}|sub sp, #0x14", DELETE: "mov r3, r2|movs r2, #0"}
OLD = {WRITE: bytes.fromhex("5cb585b0"), DELETE: bytes.fromhex("13460022")}
MOD_START = 0x0806A570                     # the end of the stock image: our code is all above it
CUR_PACK = 0x20006E24                      # [[it]] byte 0 = the loaded pack
LOADED, NONE = 0xFE, 0xFF                  # the Rhythm's special pack codes
INTERNAL = 0
HAL_TICK = 0x20006F3C                      # incremented by the SysTick handler 0x08066BD0 (51 473 ms in the dump)
LED_CALLS = (0x0803E0B6, 0x0803E7D0)       # the two calls of the LED task 0x0803E80C(ctrl, frame of 69 halfwords)
LED_TASK = 0x0803E80C
LED_SAVE, COL_NO, SHOW_MS = 57, 0x53, 1500
FAIL = 0xFFFFFFFD
T_OFF = rhstate.OFF["rodisk"][0]


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))
def pushw(regs, lr=False): return h(0xE92D) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def arm_code(base, prev, c_rst):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_rointernal (r0 = an item) -> r0 = 1 when it is in the internal pack; clobbers r1
    a.label("c_rointernal")
    E(ldrb_imm, 1, 0, 8)
    E(cmp_imm, 1, LOADED)
    E(b_cond, "ri_c", "ne")
    imm32(1, CUR_PACK)
    E(ldr_imm, 1, 1, 0)
    E(ldrb_imm, 1, 1, 0)
    a.label("ri_c")
    E(movs_imm, 0, 0)
    E(cmp_imm, 1, INTERNAL)
    E(b_cond, "ri_x", "ne")
    E(movs_imm, 0, 1)
    a.label("ri_x")
    E(raw, h(0x4770))

    # ---- c_rowr / c_rodel (in place of the first 4 bytes of the stock's write / delete)
    for name, fn in (("c_rowr", WRITE), ("c_rodel", DELETE)):
        a.label(name)
        E(raw, pushw([0, 1, 2, 3], lr=True))
        imm32(1, MOD_START)
        E(mov_reg, 2, 14)
        E(cmp_reg, 2, 1)
        E(b_cond, f"{name}_p", "lo")                                      # lr below our code: a stock caller
        E(bl, "c_rointernal")
        E(cmp_imm, 0, 0)
        E(b_cond, f"{name}_p", "eq")
        E(bl, "c_ronote")
        E(raw, popw([0, 1, 2, 3], lr=True))
        imm32(0, FAIL)
        E(raw, h(0x4770))
        a.label(f"{name}_p")
        E(raw, popw([0, 1, 2, 3], lr=True))
        E(raw, OLD[fn])
        E(b_w, fn + 4)

    # ---- c_ronote(): the time of this refusal, for the LED; clobbers r0-r3
    a.label("c_ronote")
    E(push_list, [4], lr=True)
    E(bl, c_rst)
    E(cmp_imm, 0, 0)
    E(b_cond, "rn_x", "eq")
    imm32(2, HAL_TICK)
    E(ldr_imm, 2, 2, 0)
    E(str_imm, 2, 0, T_OFF)
    a.label("rn_x")
    E(pop_list, [4], pc=True)

    # ---- c_roledtask (the LED task's calls: r0 = ctrl, r1 = frame): the chain; a refusal within 1.5 s: the Save LED red
    a.label("c_roledtask")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)
    E(bl, prev["ledtask"])
    E(bl, c_rst)
    E(cmp_imm, 0, 0)
    E(b_cond, "rl_x", "eq")
    E(ldr_imm, 1, 0, T_OFF)
    E(cmp_imm, 1, 0)
    E(b_cond, "rl_x", "eq")
    imm32(2, HAL_TICK)
    E(ldr_imm, 2, 2, 0)
    E(subs_reg, 2, 2, 1)
    imm32(3, SHOW_MS)
    E(cmp_reg, 2, 3)
    E(b_cond, "rl_x", "hs")
    E(movs_imm, 2, COL_NO)
    E(movs_imm, 0, 2 * LED_SAVE)
    E(strh_reg, 2, 5, 0)                                                  # strh r2, [r5, r0]
    a.label("rl_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; the first 4 bytes of the stock's write and delete, the two LED task calls."""
    import rhbuild
    BASE = rhbuild.BASE
    c_rst = int(report["rhstate"]["labels"]["c_rst"], 16)
    prev = dict(ledtask=rhbuild.bl_target(img, LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in LED_CALLS)
    code, labels = arm_code(base_addr, prev, c_rst)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    for fn in (WRITE, DELETE):
        assert bytes(img[fn - BASE:fn - BASE + 4]) == OLD[fn]
        rhbuild.patch(img, fn, EXPECT[fn], b_w(fn, labels["c_rowr" if fn == WRITE else "c_rodel"]))
    for c in LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_roledtask"]))
    report["rodisk"] = dict(write=hex(WRITE), delete=hex(DELETE), led_calls=[hex(c) for c in LED_CALLS], prev={k: hex(v) for k, v in prev.items()},
                            labels={k: hex(v) for k, v in labels.items() if k.startswith(("c_", "ro_"))})
    return labels, code
