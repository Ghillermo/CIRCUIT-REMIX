"""The project's Program Change channels: a listen channel and an output channel, the incoming ones forwarded (MIT; CIRCUIT-HACKS' pgmch of
SC41.5, for the Circuit Rhythm 5706).  The user (2026-10-19): «heredar MIDI merge/filtro y parámetros de setup»; the Tracks' request
(2026-10-14): «canal de escucha y envío a PGM.  Cuando se toca el pad de PGM Rx, se ilumina el canal de escucha, y cuando se toca el de Tx, se
ilumina el de salida.  Por defecto, 16.  Además de escuchar / recibir en esos canales, se hace forward de los mensajes entrantes al canal de salida».

The stock of the Rhythm (read in the firmware, the Tracks' code moved; the RAM dump, emulated):
  * receive: the receiver A = [0x20006EEC] (0x0805AF94 through the thunk 0x08052274); with its flag (A + 0x1C bit 2) a program change's channel
    is checked by 0x0805F8E2(A + 4, channel) (bl at 0x0805B152) against the table A + 0xC..0x15 (the 8 tracks, the project's two = channel 16),
    then a track's channel = id 0x10 + t, any other = 0x20, the project (its handler [[A] + 8] slot 0 (id, program) loads it);
  * send: 0x080320B0(X = 0x200126B0, port, id, program) (a project chosen on the panel: port 7, id 0x20): the channel of the table's entry
    (0x20 -> 8, 0x21 -> 9) = [[X + 0xC] + 8 + entry] (15), then `orr #0xc0` (0x08032112); the entry is added at 0x08032106 (both paths);
  * the Setup view (Shift + Save: the controller's mode 9, no active view; [ctrl + 0x78], + 0x24 = Advanced): its slot 0 = pads (1-16 the channel
    of the track chosen, 29 / 30 = PGM Rx / Tx: bits 9 / 8 of the device settings' parameter 2), slot 2 = buttons;
  * the device settings 0x20012478 are saved whole when they change; parameter 2's bits 20..27 are zero and no reader of the settings uses them.
Ours:
  * the two channels in parameter 2: bits 20-23 the listen channel, 24-27 the output one, as channel XOR 15 (0 = channel 16, the stock's);
  * receive (c_pgrx in place of the check): a program change on the listen channel is the project's, and when the output channel is another
    one it is forwarded (the stock's send, port 7, id 0x20, so on the output channel if PGM Tx is on; with both on 16, as the stock: no echo);
    on a track's channel as the stock's; channel 16 is the project's only as the listen channel;
  * send (c_pgtx at 0x08032106): the project's entries (8 / 9) take the output channel;
  * the Setup view (not Advanced): pad 29 (PGM Rx) the first time shows the listen channel on pads 1-16 (the chosen one white, the others dim),
    touched again = the stock's on / off; pad 30 the same for the output channel; a channel pad sets it; another pad or a button goes back to the
    stock's channels (rhstate "pgmch").
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b, b_cond, b_w, bics_reg, bl, cmp_imm, cmp_reg, eors_reg, h, ldr_imm, ldrb_imm, ldrb_reg,  # noqa: E402
                   lsls_imm, lsls_reg, lsrs_imm, lsrs_reg, mov_reg, movs_imm, movt, movw, orrs_reg, pop_list, push_list, raw, str_imm, strb_imm,
                   strh_imm)
import countin as CI  # noqa: E402
import midithru as M  # noqa: E402
import rhstate  # noqa: E402

CTRL = CI.CTRL
SETTINGS = M.SETTINGS
PARAM_GET, PARAM_WPTR, COMMIT = M.PARAM_GET, M.PARAM_WPTR, 0x0803FBEC
RX_CALL, RX_CHECK = 0x0805B152, 0x0805F8E2
TX_HOOK = 0x08032106
TX_OBJ, TX_SEND = 0x200126B0, 0x080320B0
SETUP_VT = 0x08067C74
SETUP_MODE = 9
L_SHIFT, O_SHIFT = 20, 24
PAD_RX, PAD_TX = 28, 29                                  # pads 29 / 30
O_ST = rhstate.OFF["pgmch"][0]
COL_ON, COL_DIM = 0x01, 0x09
INV = dict(eq="ne", ne="eq", lo="hs", hs="lo", hi="ls", ls="hi")


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit
    zc = [0]

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    def bc(target, cond):
        zc[0] += 1
        n = f"_g{zc[0]}"
        E(b_cond, n, INV[cond])
        E(b, target)
        a.label(n)

    # ---- c_pgch(r0 = shift: 20 listen / 24 output) -> r0 = that channel (0..15); clobbers r1-r3
    a.label("c_pgch")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    imm32(0, SETTINGS)
    E(movs_imm, 1, 2)
    E(bl, PARAM_GET)
    E(ldr_imm, 0, 0, 0)
    E(lsrs_reg, 0, 4)
    E(movs_imm, 1, 15)
    E(raw, h(0x4008))                                                     # ands r0, r1
    E(eors_reg, 0, 1)
    E(pop_list, [4], pc=True)

    # ---- c_pgsetch(r0 = shift, r1 = channel 0..15): written into parameter 2 and committed; clobbers r0-r3
    a.label("c_pgsetch")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(movs_imm, 5, 15)
    E(eors_reg, 5, 1)                                                     # r5 = channel ^ 15
    imm32(0, SETTINGS)
    E(movs_imm, 1, 2)
    E(bl, PARAM_WPTR)
    E(mov_reg, 6, 0)
    E(ldr_imm, 1, 6, 0)
    E(movs_imm, 2, 15)
    E(lsls_reg, 2, 4)
    E(raw, h(0x4391))                                                     # bics r1, r2
    E(lsls_reg, 5, 4)
    E(orrs_reg, 1, 5)
    E(str_imm, 1, 6, 0)
    imm32(0, SETTINGS)
    E(bl, COMMIT)
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_pgrx (in place of the receive check of a program change: r0 = A + 4, r1 = channel; the caller's r5 = the message) -> r0 = 1 / 0
    a.label("c_pgrx")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 6, 1)
    E(movs_imm, 0, L_SHIFT)
    E(bl, "c_pgch")
    E(cmp_reg, 0, 6)
    E(b_cond, "rx_t", "ne")
    E(movs_imm, 0, O_SHIFT)                                               # the listen channel: the project's, forwarded when the output differs
    E(bl, "c_pgch")
    E(cmp_reg, 0, 6)
    E(b_cond, "rx_1", "eq")
    imm32(0, TX_OBJ)
    E(movs_imm, 1, 7)
    E(movs_imm, 2, 0x20)
    E(ldrb_imm, 3, 5, 1)
    E(bl, TX_SEND)
    E(movs_imm, 0, 1)
    E(pop_list, [4, 5, 6], pc=True)
    a.label("rx_t")
    E(movs_imm, 2, 8)                                                     # a track's channel (A + 0xC..0x13): the stock's
    a.label("rx_l")
    E(ldrb_reg, 1, 4, 2)
    E(cmp_reg, 1, 6)
    E(b_cond, "rx_1", "eq")
    E(adds_imm8, 2, 1)
    E(cmp_imm, 2, 16)
    E(b_cond, "rx_l", "lo")
    E(movs_imm, 0, 0)
    E(pop_list, [4, 5, 6], pc=True)
    a.label("rx_1")
    E(movs_imm, 0, 1)
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_pgtx (at 0x08032106: r0 = the table, r1 = the entry; r3 = the program, r4 = the port) -> r0 = table + entry, r5 = the channel
    a.label("c_pgtx")
    E(push_list, [1, 2, 3, 4], lr=True)
    E(adds_reg, 0, 0, 1)
    E(push_list, [0])
    E(ldrb_imm, 5, 0, 8)
    E(cmp_imm, 1, 8)
    E(b_cond, "tx_x", "lo")
    E(cmp_imm, 1, 9)
    E(b_cond, "tx_x", "hi")
    E(movs_imm, 0, O_SHIFT)                                               # the project's entries: the output channel
    E(bl, "c_pgch")
    E(mov_reg, 5, 0)
    a.label("tx_x")
    E(pop_list, [0])
    E(pop_list, [1, 2, 3, 4], pc=True)

    # ---- c_pgsetup() -> r0 = 1 when the Setup view (not Advanced) is on the screen; clobbers r1-r3
    a.label("c_pgsetup")
    E(push_list, [4], lr=True)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "su_x", "eq")
    imm32(4, CTRL)
    E(ldr_imm, 0, 4, 0x7C)
    E(cmp_imm, 0, 0)
    E(b_cond, "su_0", "ne")
    E(ldr_imm, 0, 4, 0x14)
    E(movs_imm, 1, 0)
    E(bl, L["c_cinew"])
    E(cmp_imm, 0, SETUP_MODE)
    E(b_cond, "su_0", "ne")
    E(raw, h(0x6FA0))                                                     # ldr r0, [r4, #0x78]: the Setup view
    E(raw, h(0xF890) + h(0x0024))                                         # ldrb.w r0, [r0, #0x24]
    E(cmp_imm, 0, 0)
    E(b_cond, "su_0", "ne")
    E(movs_imm, 0, 1)
    E(pop_list, [4], pc=True)
    a.label("su_0")
    E(movs_imm, 0, 0)
    a.label("su_x")
    E(pop_list, [4], pc=True)

    # ---- c_pgst() -> r0 = our state byte's place (0 without our RAM); clobbers r1-r3
    a.label("c_pgst")
    E(push_list, [4], lr=True)
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "gs_x", "eq")
    E(adds_imm8, 0, O_ST)
    a.label("gs_x")
    E(pop_list, [4], pc=True)

    # ---- c_pgpad (the Setup view's slot 0: view, pad, velocity)
    a.label("c_pgpad")
    E(push_list, [0, 1, 2, 4, 5], lr=True)
    E(raw, h(0xF890) + h(0x3024))                                         # ldrb.w r3, [r0, #0x24]
    E(cmp_imm, 3, 0)
    bc("gp_p", "ne")                                                      # Advanced: the stock's
    E(bl, "c_pgst")
    E(cmp_imm, 0, 0)
    bc("gp_p", "eq")
    E(mov_reg, 4, 0)                                                      # r4 = our state
    E(ldrb_imm, 5, 4, 0)                                                  # r5 = 0, 1 listen shown, 2 output shown
    E(raw, h(0x9901))                                                     # ldr r1, [sp, #4]: the pad
    E(cmp_imm, 1, PAD_RX)
    E(b_cond, "gp_rx", "eq")
    E(cmp_imm, 1, PAD_TX)
    E(b_cond, "gp_tx", "eq")
    E(cmp_imm, 5, 0)
    bc("gp_p", "eq")
    E(cmp_imm, 1, 16)
    E(b_cond, "gp_ch", "lo")
    E(movs_imm, 0, 0)                                                     # another pad: back to the stock's channels
    E(strb_imm, 0, 4, 0)
    E(b, "gp_p")
    a.label("gp_ch")                                                      # a channel pad: that channel
    E(movs_imm, 0, L_SHIFT)
    E(cmp_imm, 5, 1)
    E(b_cond, "gp_c2", "eq")
    E(movs_imm, 0, O_SHIFT)
    a.label("gp_c2")
    E(bl, "c_pgsetch")
    E(b, "gp_x")
    a.label("gp_rx")
    E(movs_imm, 0, 1)
    E(b, "gp_t")
    a.label("gp_tx")
    E(movs_imm, 0, 2)
    a.label("gp_t")
    E(cmp_reg, 5, 0)
    E(b_cond, "gp_tog", "eq")                                             # shown already: the stock's on / off
    E(strb_imm, 0, 4, 0)                                                  # the first touch: its channel shown
    E(b, "gp_x")
    a.label("gp_tog")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 4, 0)
    a.label("gp_p")
    E(raw, popw([0, 1, 2, 4, 5], lr=True))
    E(b_w, prev["pad"])
    a.label("gp_x")
    E(pop_list, [0, 1, 2, 4, 5], pc=True)

    # ---- c_pgbtn (the Setup view's slot 2: view, button): back to the stock's channels
    a.label("c_pgbtn")
    E(push_list, [0, 1, 4], lr=True)
    E(bl, "c_pgst")
    E(cmp_imm, 0, 0)
    E(b_cond, "gb_x", "eq")
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 0, 0)
    a.label("gb_x")
    E(raw, popw([0, 1, 4], lr=True))
    E(b_w, prev["btn"])

    # ---- c_pgled (the LED task's calls: ctrl, frame): a channel shown on pads 1-16; out of the Setup view, the state back to 0
    a.label("c_pgled")
    E(push_list, [3, 4, 5, 6], lr=True)
    E(mov_reg, 5, 1)
    E(bl, prev["ledtask"])
    E(bl, "c_pgst")
    E(cmp_imm, 0, 0)
    bc("gl_x", "eq")
    E(mov_reg, 4, 0)
    E(ldrb_imm, 6, 4, 0)
    E(cmp_imm, 6, 0)
    bc("gl_x", "eq")
    E(bl, "c_pgsetup")
    E(cmp_imm, 0, 0)
    E(b_cond, "gl_on", "ne")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 4, 0)
    E(b, "gl_x")
    a.label("gl_on")
    E(movs_imm, 0, L_SHIFT)
    E(cmp_imm, 6, 1)
    E(b_cond, "gl_c", "eq")
    E(movs_imm, 0, O_SHIFT)
    a.label("gl_c")
    E(bl, "c_pgch")
    E(mov_reg, 6, 0)                                                      # r6 = the channel shown
    E(movs_imm, 3, 0)
    a.label("gl_l")
    E(movs_imm, 2, COL_DIM)
    E(cmp_reg, 3, 6)
    E(b_cond, "gl_w", "ne")
    E(movs_imm, 2, COL_ON)
    a.label("gl_w")
    E(lsls_imm, 0, 3, 1)
    E(raw, h(0x5200 | 0 << 6 | 5 << 3 | 2))                              # strh r2, [r5, r0]
    E(adds_imm8, 3, 1)
    E(cmp_imm, 3, 16)
    E(b_cond, "gl_l", "lo")
    a.label("gl_x")
    E(pop_list, [3, 4, 5, 6], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; the receive check's call, the send's entry, the Setup view's slots 0 / 2, the LED task calls."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]
    lab = lambda sec, n: int(report[sec]["labels"][n], 16)
    L = dict(c_rst=lab("rhstate", "c_rst"), c_ciok=lab("countin", "c_ciok"), c_cinew=lab("countin", "c_cinew"))
    prev = dict(pad=u(SETUP_VT) & ~1, btn=u(SETUP_VT + 8) & ~1, ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, RX_CALL, f"bl #{RX_CHECK:#x}", bl(RX_CALL, labels["c_pgrx"]))
    rhbuild.patch(img, TX_HOOK, "add r0, r1|mov r1, sp|ldrb r5, [r0, #8]", bl(TX_HOOK, labels["c_pgtx"]) + h(0x4669))
    rhbuild.patch_word(img, SETUP_VT, prev["pad"] | 1, labels["c_pgpad"] | 1)
    rhbuild.patch_word(img, SETUP_VT + 8, prev["btn"] | 1, labels["c_pgbtn"] | 1)
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_pgled"]))
    report["pgmch"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
