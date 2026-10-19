"""MIDI Thru with Merge and Filter (MIT; CIRCUIT-HACKS' midithru of SC38.3, for the Circuit Rhythm 5706).  The user (2026-10-19): «heredar MIDI
merge/filtro y parámetros de setup»; the Tracks' request (2026-10-11): «Midi Merge: se clona todo lo de MIDI in a MIDI thru y también el MIDI
generado por el aparato.  Midi Filter: se clona todo lo de MIDI in menos los canales en los que Circuit está escuchando».

The stock of the Rhythm (read in the firmware, the Tracks' code moved; the RAM dump):
  * the toggle is Duplicate (button 24) in the Advanced Setup view (the Setup view [ctrl + 0x78] with byte + 0x24 set; its button slot
    0x080513F0, the case at 0x0805149A): the device settings' parameter 2 bit 16 (the store 0x20012478 = [view + 0xC]): 1 = Thru (a hardware
    switch copies the DIN In to the Thru jack), 0 = Out 2; after the commit the stock shows its message 0xA / 0xB (0x0805152A); the listener
    0x08035698 writes the bit to the pin; Duplicate's LED (0x08051724) = the palette codes [0x08062AB0 + 0x3D6] (0x7E green, Thru) / + 0x3D8
    (0x57 dim red, Out 2) into [[view + 4]] + 0x70;
  * MIDI out: the router [0x20006F04] (0x0802986A, the Tracks' code) sends to the ports of a mask: [router + 0x14] = the ports (3: 0 USB, 1 the
    MIDI Out, 2 the Thru jack in Out 2), class 0x08068AA8, slot 2 = send 0x080401FE;
  * MIDI in: the DIN In = port 1; the poll 0x08029C1A posts each short message with 0x08024B68(queue, port, bytes) at 0x08029C4C;
  * the channels the unit listens on: the receiver A = [0x20006EEC] (the receive method 0x0805AF94, through the thunk 0x08052274): its table
    A + 0xC..0x15 = the eight tracks' channels (the settings' parameters 3..10) and the project's two (16), as 0x0805F8E2 reads it;
  * the settings are saved whole (memcpy) and compared word by word: bits 30 / 31 of parameter 2 (zero, unused) are kept as they are.
Ours, as the Tracks': two more modes, a software thru on the Out 2 wiring (bit 16 clear, so the stock's pin stays on USART2):
  * Merge (bit 30): every DIN In message is also sent to port 2; the unit's own MIDI goes there as in Out 2;
  * Filter (bit 31): the DIN In messages, but the channel messages on a channel the unit listens on, go to port 2; the unit's own messages to port 2
    are dropped;
  * Duplicate in Advanced Setup: Thru -> Out 2 -> Merge -> Filter -> Thru (the stock's commit and message after it: Thru's / Out 2's);
    its LED: green Thru, dim red Out 2, yellow Merge, blue Filter.
SysEx from the DIN In is not copied (another path).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, ands_reg, b, b_cond, b_w, bics_reg, bl, cmp_imm, cmp_reg, h, ldr_imm, ldrb_imm, ldrb_reg,  # noqa: E402
                   lsls_imm, mov_reg, movs_imm, movt, movw, orrs_reg, pop_list, push_list, raw, str_imm)

SETTINGS = 0x20012478
PARAM_GET, PARAM_WPTR = 0x0803FC58, 0x0803FD26
ROUTER_PTR = 0x20006F04
PORT_VT, PORT_SEND = 0x08068AA8, 0x080401FE
POST, POST_CALL = 0x08024B68, 0x08029C4C
RECV_PTR = 0x20006EEC
O_TABLE, N_TABLE = 0xC, 10                             # the receive table: 8 tracks, the project's 2
BTN_TOGGLE, BTN_COMMIT = 0x080514A2, 0x080514CC        # the case of Duplicate: ldr r0,[r4,#0xc]; movs r1,#2; bl wptr -> ours; its commit
LED_CODE, LED_BACK = 0x08051734, 0x08051748            # Duplicate's LED: ubfx .. ldrh (20 bytes) -> r0 = the code, r1 = [view + 4]
PAL = 0x08062AB0
B16, B30, B31 = 1 << 16, 1 << 30, 1 << 31
DIN_IN, PORT2 = 1, 2
COL_MERGE, COL_FILTER = 0x2F, 0x12                     # yellow, blue (the Tracks' 0x2D / 0x09: the same RGB)


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))
def ldrh_imm_(rt, rn, imm): return h(0x8800 | (imm // 2) << 6 | rn << 3 | rt)


def arm_code(base):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    def port2(rd):                                                        # rd = the out port 2
        imm32(rd, ROUTER_PTR)
        E(ldr_imm, rd, rd, 0)
        E(ldr_imm, rd, rd, 0x14)
        E(ldr_imm, rd, rd, 4 * PORT2)

    # ---- c_tmode() -> r0 = 2 Merge, 3 Filter, 0 otherwise (Thru by the hardware switch, Out 2); clobbers r1-r3
    a.label("c_tmode")
    E(push_list, [4], lr=True)
    imm32(0, SETTINGS)
    E(movs_imm, 1, 2)
    E(bl, PARAM_GET)
    E(ldr_imm, 0, 0, 0)
    E(lsls_imm, 1, 0, 15)
    E(b_cond, "tm_0", "mi")                                               # bit 16: the hardware thru
    E(cmp_imm, 0, 0)
    E(b_cond, "tm_f", "lt")                                               # bit 31
    E(lsls_imm, 1, 0, 1)
    E(b_cond, "tm_0", "pl")                                               # bit 30
    E(movs_imm, 0, 2)
    E(pop_list, [4], pc=True)
    a.label("tm_f")
    E(movs_imm, 0, 3)
    E(pop_list, [4], pc=True)
    a.label("tm_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)

    # ---- c_thin (queue, port, bytes) in place of the post of a short input message: Merge / Filter copy the DIN In message to port 2, then the post
    a.label("c_thin")
    E(push_list, [0, 1, 2, 4, 5], lr=True)
    E(cmp_imm, 1, DIN_IN)
    E(b_cond, "ti_go", "ne")
    E(mov_reg, 4, 2)                                                      # r4 = the message
    E(bl, "c_tmode")
    E(cmp_imm, 0, 2)
    E(b_cond, "ti_go", "lo")
    E(cmp_imm, 0, 3)
    E(b_cond, "ti_fw", "ne")
    E(ldrb_imm, 0, 4, 0)                                                  # Filter: a channel message on a listened channel stays
    E(cmp_imm, 0, 0x80)
    E(b_cond, "ti_fw", "lo")
    E(cmp_imm, 0, 0xF0)
    E(b_cond, "ti_fw", "hs")
    E(movs_imm, 1, 0x0F)
    E(ands_reg, 0, 1)                                                     # r0 = its channel
    imm32(5, RECV_PTR)
    E(ldr_imm, 5, 5, 0)                                                   # r5 = the receiver
    E(movs_imm, 2, O_TABLE)
    a.label("ti_lp")
    E(ldrb_reg, 1, 5, 2)
    E(cmp_reg, 1, 0)
    E(b_cond, "ti_go", "eq")
    E(adds_imm8, 2, 1)
    E(cmp_imm, 2, O_TABLE + N_TABLE)
    E(b_cond, "ti_lp", "lo")
    a.label("ti_fw")
    port2(0)
    E(mov_reg, 1, 4)
    E(bl, PORT_SEND)
    a.label("ti_go")
    E(raw, popw([0, 1, 2, 4, 5], lr=True))
    E(b_w, POST)

    # ---- c_thtx (port, message): slot 2 of the out ports; Filter drops the unit's own messages to port 2
    a.label("c_thtx")
    E(push_list, [0, 1, 4], lr=True)
    port2(4)
    E(cmp_reg, 0, 4)
    E(b_cond, "tx_go", "ne")
    E(bl, "c_tmode")
    E(cmp_imm, 0, 3)
    E(b_cond, "tx_go", "ne")
    E(raw, popw([0, 1, 4], lr=True))
    E(movs_imm, 0, 1)
    E(raw, h(0x4770))
    a.label("tx_go")
    E(raw, popw([0, 1, 4], lr=True))
    E(b_w, PORT_SEND)

    # ---- c_thbtn (r0 = the Setup view): Duplicate in Advanced Setup, Thru -> Out 2 -> Merge -> Filter -> Thru (written; the caller commits)
    a.label("c_thbtn")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(ldr_imm, 0, 4, 0xC)
    E(movs_imm, 1, 2)
    E(bl, PARAM_GET)
    E(ldr_imm, 6, 0, 0)                                                   # r6 = the mode now
    E(ldr_imm, 0, 4, 0xC)
    E(movs_imm, 1, 2)
    E(bl, PARAM_WPTR)
    E(mov_reg, 5, 0)
    E(ldr_imm, 1, 5, 0)
    imm32(2, B16 | B30 | B31)
    E(bics_reg, 1, 2)
    E(lsls_imm, 0, 6, 15)
    E(b_cond, "tb_w", "mi")                                               # Thru -> Out 2 (no bit)
    imm32(2, B16)
    E(cmp_imm, 6, 0)
    E(b_cond, "tb_o", "lt")                                               # Filter -> Thru
    imm32(2, B31)
    E(lsls_imm, 0, 6, 1)
    E(b_cond, "tb_o", "mi")                                               # Merge -> Filter
    imm32(2, B30)                                                         # Out 2 -> Merge
    a.label("tb_o")
    E(orrs_reg, 1, 2)
    a.label("tb_w")
    E(str_imm, 1, 5, 0)
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_thled (r1 = parameter 2, r4 = the Setup view, r5 = the palette) -> r0 = the code of Duplicate's LED, r1 = [view + 4]
    a.label("c_thled")
    E(movs_imm, 0, COL_FILTER)
    E(cmp_imm, 1, 0)
    E(b_cond, "tl_x", "lt")
    E(movs_imm, 0, COL_MERGE)
    E(lsls_imm, 2, 1, 1)
    E(b_cond, "tl_x", "mi")
    E(movw, 0, 0x3D6)
    E(lsls_imm, 2, 1, 15)
    E(b_cond, "tl_p", "mi")
    E(movw, 0, 0x3D8)
    a.label("tl_p")
    E(adds_reg, 0, 0, 5)
    E(raw, ldrh_imm_(0, 0, 0))
    a.label("tl_x")
    E(ldr_imm, 1, 4, 4)
    E(raw, h(0x4770))
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; the post call, the ports' slot 2, Duplicate's toggle and LED in Advanced Setup."""
    import struct
    import rhbuild
    BASE = rhbuild.BASE
    code, labels = arm_code(base_addr)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, POST_CALL, f"bl #{POST:#x}", bl(POST_CALL, labels["c_thin"]))
    old = struct.unpack_from("<I", img, PORT_VT + 8 - BASE)[0]
    rhbuild.patch_word(img, PORT_VT + 8, old if old == PORT_SEND | 1 else PORT_SEND | 1, labels["c_thtx"] | 1)
    rhbuild.patch(img, BTN_TOGGLE, "ldr r0, [r4, #0xc]|movs r1, #2|bl #0x803fd26",
                  h(0x4620) + bl(BTN_TOGGLE + 2, labels["c_thbtn"]) + b(BTN_TOGGLE + 6, BTN_COMMIT))
    rhbuild.patch(img, LED_CODE, "ubfx r0, r1, #0x10, #1|cmp r0, #0|ldr r1, [r4, #4]|ite ne|movwne r0, #0x3d6|moveq.w r0, #0x3d8|ldrh r0, [r5, r0]",
                  bl(LED_CODE, labels["c_thled"]) + h(0xBF00) * 8)
    report["midithru"] = dict(labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
