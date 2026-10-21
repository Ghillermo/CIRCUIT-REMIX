"""The master filter's resonance saved with the project (MIT; the per-session master values of CIRCUIT-HACKS' fxsess (SC40.9), for the Circuit
Rhythm 5706).  Found with RD2 on the device (2026-10-19, docs/PORTADO.md): the master group 0x21 (filter, resonance, compressor, soft clip, gain)
is global - a project does not keep it -, so the resonance RH13 lets the FX view set (Shift + up / down) did not travel with the project; the
compressor already does (sckn's block in the record's tail).

The stock of the Rhythm (read in the firmware):
  * the project is saved from the session record R = [0x2003C0CC] (0x29484 B, kind 2) by two calls: 0x08037FD6 (bl 0x080472E2: Save, the
    loaded slot or another one) and 0x08038734 (bl 0x08047270, the other save path of the session object); the tail of R (rhrec) travels with it;
  * after a load «apply the record» ends at 0x080379AE (b.w 0x08031A10; patchain's and sckn's hooks are chained there);
  * the master resonance = group 0x21, index 1: getter 0x08046410(group, index), setter 0x08031A38(0x20010E10, group, index, value) (store, DSP,
    MIDI out), as RH13 (fxkeys) uses them.

Ours: at each save, just before the stock writes R, the current resonance goes into the tail's block "MF" (+ the value and a check byte); after a
load (rhstate "mfsess" set by the load hook) the LED task applies the block's value once through the setter.  A project without the block (saved
by the stock or before RH28) leaves the resonance as it is, as the stock.
RH30 (install(track=True)): the block also follows every change of the resonance (the LED task compares it with the value it last saw,
rhstate "mfsess2"), as sckn keeps the compressor's block, so the project file has it whatever path the stock saves by (on the device RH28's
reload left the resonance as it was: «resonance stays»); the applied value of a load counts as seen (no write while a project loads).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, b, b_cond, b_w, bl, cmp_imm, cmp_reg, eors_reg, h, ldrb_imm, mov_reg, movs_imm, movt, movw, pop_list,  # noqa: E402
                   push_list, raw, strb_imm, ldrb_w, strb_w)
import countin as CI  # noqa: E402
import patchain as PC  # noqa: E402
import rhrec  # noqa: E402
import rhstate  # noqa: E402

SAVE_CALLS = {0x08037FD6: 0x080472E2, 0x08038734: 0x08047270}
LOAD_TAIL = PC.LOAD_TAIL
SETTER, SET_OBJ, GETTER = 0x08031A38, 0x20010E10, 0x08046410
GRP_MASTER, IDX_RES = 0x21, 1
LED_CALLS = CI.LED_CALLS
BLK, BLK_LEN = rhrec.OFF["mfsess"]
O_ST = rhstate.OFF["mfsess"][0]
MARK0, MARK1, CHECK = ord("M"), ord("F"), 0xA5
PEND = 0xC1
O_SEEN = rhstate.OFF["mfsess2"][0]
TRACK = False
assert BLK_LEN == 4 and BLK + 3 < 256 * 4


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def arm_code(base, L, prev):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_mfblk() -> r0 = our block in the record's tail, 0 without a record; clobbers r1, r2
    a.label("c_mfblk")
    E(push_list, [3], lr=True)
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "bk_x", "eq")
    imm32(1, BLK)
    E(raw, h(0x1840))                                                      # adds r0, r0, r1
    a.label("bk_x")
    E(pop_list, [3], pc=True)

    # ---- c_mfsnap(): the current resonance into the block; clobbers r0-r3, r12
    a.label("c_mfsnap")
    E(push_list, [4], lr=True)
    E(bl, "c_mfblk")
    E(mov_reg, 4, 0)
    E(cmp_imm, 4, 0)
    E(b_cond, "sn_x", "eq")
    E(movs_imm, 0, GRP_MASTER)
    E(movs_imm, 1, IDX_RES)
    E(bl, GETTER)
    E(movs_imm, 1, 0x7F)
    E(raw, h(0x4008))                                                      # ands r0, r1
    E(strb_imm, 0, 4, 2)
    E(movs_imm, 1, CHECK)
    E(eors_reg, 1, 0)
    E(strb_imm, 1, 4, 3)
    E(movs_imm, 0, MARK0)
    E(strb_imm, 0, 4, 0)
    E(movs_imm, 0, MARK1)
    E(strb_imm, 0, 4, 1)
    a.label("sn_x")
    E(pop_list, [4], pc=True)

    # ---- c_mfsv0 / c_mfsv1 (in place of the two save calls): the snapshot, then the stock's write with the same arguments (r0-r3 and the stack)
    for k, tgt in enumerate(prev["save"]):
        a.label(f"c_mfsv{k}")
        E(push_list, [0, 1, 2, 3, 4], lr=True)
        E(bl, "c_mfsnap")
        E(raw, popw([0, 1, 2, 3, 4], lr=True))
        E(b_w, tgt)

    # ---- c_mfload (at the end of «apply the record», in front of the hooks already there): the LED task applies the block once
    a.label("c_mfload")
    E(push_list, [0, 1, 2, 3, 4], lr=True)
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ld_x", "eq")
    E(movs_imm, 1, PEND)
    E(strb_w, 1, 0, O_ST)
    a.label("ld_x")
    E(raw, popw([0, 1, 2, 3, 4], lr=True))
    E(b_w, prev["load"])

    # ---- c_mfled (the LED task's calls: r0 = ctrl, r1 = frame): the chain, then, once after a load, the block's resonance
    a.label("c_mfled")
    E(push_list, [3, 4], lr=True)
    E(bl, prev["ledtask"])
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "lt_x", "eq")
    E(ldrb_w, 1, 0, O_ST)
    E(cmp_imm, 1, PEND)
    E(b_cond, "lt_t" if TRACK else "lt_x", "ne")
    E(movs_imm, 1, 0)
    E(strb_w, 1, 0, O_ST)
    E(bl, "c_mfblk")
    E(mov_reg, 4, 0)
    E(cmp_imm, 4, 0)
    E(b_cond, "lt_x", "eq")
    E(ldrb_imm, 0, 4, 0)
    E(cmp_imm, 0, MARK0)
    E(b_cond, "lt_x", "ne")
    E(ldrb_imm, 0, 4, 1)
    E(cmp_imm, 0, MARK1)
    E(b_cond, "lt_x", "ne")
    E(ldrb_imm, 3, 4, 2)
    E(cmp_imm, 3, 0x7F)
    E(b_cond, "lt_x", "hi")
    E(ldrb_imm, 0, 4, 3)
    E(movs_imm, 1, CHECK)
    E(eors_reg, 1, 3)
    E(cmp_reg, 0, 1)
    E(b_cond, "lt_x", "ne")
    imm32(0, SET_OBJ)
    E(movs_imm, 1, GRP_MASTER)
    E(movs_imm, 2, IDX_RES)
    if TRACK:
        E(mov_reg, 4, 3)                                                   # r4 = the value (c_rst clobbers r3)
        E(bl, SETTER)
        E(bl, L["c_rst"])
        E(movs_imm, 1, 0x80)
        E(raw, h(0x4321))                                                  # orrs r1, r4: the applied value, seen
        E(strb_w, 1, 0, O_SEEN)
        a.label("lt_x")
        E(pop_list, [3, 4], pc=True)
        a.label("lt_t")                                                    # no load pending: a change of the resonance into the block
        E(mov_reg, 4, 0)                                                   # r4 = our RAM
        E(movs_imm, 0, GRP_MASTER)
        E(movs_imm, 1, IDX_RES)
        E(bl, GETTER)
        E(movs_imm, 1, 0x7F)
        E(raw, h(0x4008))                                                  # ands r0, r1
        E(movs_imm, 1, 0x80)
        E(raw, h(0x4301))                                                  # orrs r1, r0
        E(ldrb_w, 0, 4, O_SEEN)
        E(cmp_reg, 0, 1)
        E(b_cond, "lt_x", "eq")
        E(strb_w, 1, 4, O_SEEN)
        E(bl, "c_mfsnap")
        E(b, "lt_x")
    else:
        E(bl, SETTER)
        a.label("lt_x")
        E(pop_list, [3, 4], pc=True)
    return a.assemble()


def install(img, report, base_addr, track=False):
    """Append the code; the two save calls, the end of «apply the record» (in front of the hooks there), the LED task calls."""
    global TRACK
    TRACK = track
    import rhbuild
    BASE = rhbuild.BASE
    lab = lambda m, n: int(report[m]["labels"][n], 16)
    L = dict(c_rst=lab("rhstate", "c_rst"), c_rrt=lab("rhrec", "c_rrt"))
    for c, t in SAVE_CALLS.items():
        assert rhbuild.bl_target(img, c) == t, hex(c)
    prev = dict(save=list(SAVE_CALLS.values()), load=rhbuild.bw_target(img, LOAD_TAIL), ledtask=rhbuild.bl_target(img, LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in LED_CALLS)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    for k, (c, t) in enumerate(SAVE_CALLS.items()):
        rhbuild.patch(img, c, f"bl #{t:#x}", bl(c, labels[f"c_mfsv{k}"]))
    rhbuild.patch(img, LOAD_TAIL, f"b.w #{prev['load']:#x}", b_w(LOAD_TAIL, labels["c_mfload"]))
    for c in LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_mfled"]))
    report["mfsess"] = dict(prev=dict(save=[hex(v) for v in prev["save"]], load=hex(prev["load"]), ledtask=hex(prev["ledtask"])),
                            labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
