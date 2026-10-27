"""USB merge: the DIN In also sent to the computer by USB (MIT; RH46, as CIRCUIT-HACKS' usbmerge of Beta 3.21, issue #10 of its public
repository: «i connect midi keyboard … using midi cable, i want then that device is outputting both midi combined to a computer»).

The stock of the Rhythm (read in its image, run on the RAM dump): the MIDI out router [0x20006F04]'s ports ([router + 0x14]: 0 USB, 1 the MIDI
Out, 2 the Thru jack in Out 2; slot 2 of each = its send (port, message)); the DIN In = input port 1, every short message posted at
0x08029C4C (the bl to 0x08024B68(queue, port, message), now midithru's c_thin); the transmitter 0x200126B0: [+ 0x18] bit 3 = Clock Tx (Setup
pad 32); the Advanced Setup view (the Setup view [ctrl + 0x78] with byte + 0x24 set, vtable 0x08067C74, slot 0 = its pads) does nothing with
its pads.  Ours:
  * c_umin, in place of that bl: with the USB merge on, a DIN In message is also sent to port 0 (through its slot 2), then the chain as
    before; with Clock Tx on, the DIN In's clock and transport (0xF8, 0xFA, 0xFB, 0xFC) are not copied (the computer would get two clocks);
  * Advanced Setup pad 23 = on / off (bit 28 of the device settings' parameter 2, written and committed; saved by setsave); its LED green on,
    dim off.
SysEx from the DIN In takes another path: not copied.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, b_cond, b_w, bl, cmp_imm, h, ldr_imm, ldrb_imm, ldrb_w, lsls_imm, mov_reg, movs_imm, movt, movw, pop_list,  # noqa: E402
                   push_list, raw, str_imm, strh_imm, eors_reg)
import countin as CI  # noqa: E402
import midithru as M  # noqa: E402
import pgmch as PG  # noqa: E402

BIT = 1 << 28
PAD = 22                                                  # pad 23
TX, O_TXF, CLOCK_TX = 0x200126B0, 0x18, 0x08
DIN_IN, USB = 1, 0
COL_ON, COL_DIM = 0x1E, 0x09
SETUP_VT, SETUP_MODE = PG.SETUP_VT, PG.SETUP_MODE
GET, WPTR, COMMIT = CI.PARAM_GET, CI.WPTR, CI.COMMIT


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def advanced(E, imm32, L, no):
    """the code of 'the Advanced Setup view is on the screen' (r4 = CTRL afterwards); clobbers r0-r3; to `no` if not"""
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, no, "eq")
    imm32(4, CI.CTRL)
    E(ldr_imm, 0, 4, 0x7C)
    E(cmp_imm, 0, 0)
    E(b_cond, no, "ne")
    E(ldr_imm, 0, 4, 0x14)
    E(movs_imm, 1, 0)
    E(bl, L["c_cinew"])
    E(cmp_imm, 0, SETUP_MODE)
    E(b_cond, no, "ne")
    E(ldr_imm, 0, 4, 0x78)
    E(ldrb_w, 0, 0, 0x24)
    E(cmp_imm, 0, 0)
    E(b_cond, no, "eq")


def toggle(E, imm32, bit):
    """parameter 2 of the device settings XOR bit, committed; clobbers r0-r3"""
    imm32(0, M.SETTINGS)
    E(movs_imm, 1, 2)
    E(bl, WPTR)
    E(ldr_imm, 1, 0, 0)
    imm32(2, bit)
    E(eors_reg, 1, 2)
    E(str_imm, 1, 0, 0)
    imm32(0, M.SETTINGS)
    E(bl, COMMIT)


def p2bit(E, imm32, bit):
    """r0 = bit `bit` of parameter 2 (0 / non-zero); clobbers r1-r3"""
    imm32(0, M.SETTINGS)
    E(movs_imm, 1, 2)
    E(bl, GET)
    E(ldr_imm, 0, 0, 0)
    imm32(1, bit)
    E(raw, h(0x4008))                                                     # ands r0, r1


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_umin (queue, port, message) in place of the post of a short input message
    a.label("c_umin")
    E(push_list, [0, 1, 2, 3, 4, 5], lr=True)
    E(cmp_imm, 1, DIN_IN)
    E(b_cond, "um_x", "ne")
    E(mov_reg, 5, 2)                                                      # r5 = the message
    p2bit(E, imm32, BIT)
    E(cmp_imm, 0, 0)
    E(b_cond, "um_x", "eq")
    E(ldrb_imm, 0, 5, 0)
    E(cmp_imm, 0, 0xF8)
    E(b_cond, "um_c", "eq")
    E(cmp_imm, 0, 0xFA)
    E(b_cond, "um_s", "lo")
    E(cmp_imm, 0, 0xFC)
    E(b_cond, "um_s", "hi")
    a.label("um_c")                                                       # clock / transport: not with Clock Tx on
    imm32(0, TX)
    E(ldrb_imm, 0, 0, O_TXF)
    E(lsls_imm, 0, 0, 28)
    E(b_cond, "um_x", "mi")
    a.label("um_s")
    imm32(0, M.ROUTER_PTR)
    E(ldr_imm, 0, 0, 0)
    E(ldr_imm, 0, 0, 0x14)
    E(ldr_imm, 0, 0, 4 * USB)                                             # the USB port
    E(cmp_imm, 0, 0)
    E(b_cond, "um_x", "eq")
    E(ldr_imm, 3, 0, 0)
    E(ldr_imm, 3, 3, 8)
    E(mov_reg, 1, 5)
    E(raw, h(0x4798))                                                     # blx r3: its send
    a.label("um_x")
    E(raw, popw([0, 1, 2, 3, 4, 5], lr=True))
    E(b_w, prev["post"])

    # ---- c_umpad (the Setup view's slot 0: view, pad, velocity): Advanced Setup pad 23
    a.label("c_umpad")
    E(cmp_imm, 1, PAD)
    E(b_cond, "up_s", "ne")
    E(push_list, [0, 1, 2, 3, 4, 5], lr=True)
    E(ldrb_w, 3, 0, 0x24)
    E(cmp_imm, 3, 0)
    E(b_cond, "up_p", "eq")                                               # not Advanced
    toggle(E, imm32, BIT)
    E(pop_list, [0, 1, 2, 3, 4, 5], pc=True)
    a.label("up_p")
    E(raw, popw([0, 1, 2, 3, 4, 5], lr=True))
    a.label("up_s")
    E(b_w, prev["pad"])

    # ---- c_umled (the LED task's calls: ctrl, frame): the chain, then pad 23 in Advanced Setup
    a.label("c_umled")
    E(push_list, [3, 4, 5, 6], lr=True)
    E(mov_reg, 5, 1)
    E(bl, prev["ledtask"])
    advanced(E, imm32, L, "ul_x")
    p2bit(E, imm32, BIT)
    E(movs_imm, 1, COL_DIM)
    E(cmp_imm, 0, 0)
    E(b_cond, "ul_w", "eq")
    E(movs_imm, 1, COL_ON)
    a.label("ul_w")
    E(strh_imm, 1, 5, 2 * PAD)
    a.label("ul_x")
    E(pop_list, [3, 4, 5, 6], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """The DIN In's post (midithru's c_thin in front), the head of the Setup view's slot 0, the head of the LED calls.  Needs midithru, countin."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]                 # noqa: E731
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    assert "midithru" in report, "usbmerge needs midithru"
    L = dict(c_ciok=lab("countin", "c_ciok"), c_cinew=lab("countin", "c_cinew"))
    prev = dict(post=rhbuild.bl_target(img, M.POST_CALL), pad=u(SETUP_VT) & ~1, ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, M.POST_CALL, f"bl #{prev['post']:#x}", bl(M.POST_CALL, labels["c_umin"]))
    rhbuild.patch_word(img, SETUP_VT, prev["pad"] | 1, labels["c_umpad"] | 1)
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_umled"]))
    report["usbmerge"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
