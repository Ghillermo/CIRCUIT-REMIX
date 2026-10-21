"""Frequency, dynamics and random-mutate of the sample, per step (MIT; CIRCUIT-HACKS' drumpat of SC43, for the Circuit Rhythm 5706: «incluir
también el resto de funciones de pattern settings (dynamics, pitch mutate, each N iterations…) [en los drums]; en vez de modificar el pitch,
modifica el sample elegido»; «C. Random-mutate con 4 niveles … 25 % ± 1, 25 % ± 8, 12 % de ambas»).

The stock of the Rhythm (read in the firmware and on the RAM dump, emulated):
  * the probability view (Pattern Settings twice, or Shift + Pattern Settings): 0x2004C7B8 + 0x40 t (vtable 0x08067E6C); [view + 0xC] = ctx:
    [ctx] = ST1 (the steps' store, [ST1 + 0x18] = its pattern + 0x128), [ctx + 0xC] p1 = the selected step; pads 17-32 arrive as 0..15: 0..7 the
    probability of the step, 8..15 nothing; slot 7 (0x0805210E) returns its 16 LEDs [[view + 4]]; 0x0805761E(view) redraws row 3;
    0x08054AE0(ST1, step) = the step's velocity (0 = no hit);
  * the track players 0x200470D4 + 0x190 t (vtable 0x08068D24): [+ 0x50] the track's patterns (0xA28 each), slot 2 = 0x0804AFBC(player,
    pattern, step, micro step) plays the step's note when bit micro of [player + 0x14C] is set: the voice of that note released
    (0x0804B19E(player, [player + 0xAB + note])), then 0x0804B0D4(player, note, velocity, gate x [0x08068D9C + 4 rate] / 6 (at least 1),
    [sp] tie) (note = step byte 0, or 0x30; velocity byte 3; gate byte 1; tie byte 6 bit 0; rate = p1 of [player + 0x10]); slot 4 sets the
    step's sample at its start: the flip (byte 5), else the selected one (p0 of [player + 0x60]), by [player + 0x58] slot 0 (obj,
    [[player + 0x5C] + 0x18] halfword, sample);
  * the settings bytes 8..39 of a pattern (+ 0x108..0x127) are zero in the 64 patterns of the dump; the stock's stores never write them; they
    are in the session record, so in the project file.
Ours (as CIRCUIT-HACKS'): a byte a step at the pattern + 0x108 + step: bits 0-2 the dynamics, 3-5 the frequency - 1, 6-7 the mutate; read only
in a project marked "DQ" in the record's tail (rhrec); the first value set marks the project and clears the bytes 8..39 of its 64 patterns.
  * Pattern Settings pad 25 (peach) = the probability view in mode 2; the probability view: mode 1 row 4 = the frequency (the step plays on
    the passes of its pattern that are multiples of n), mode 2 row 3 = the dynamics (CIRCUIT-HACKS' DYN: the velocity, and later in the step by
    micro steps), row 4 pads 25-28 = the mutate (the sample of the hit: ± 1 inside its row of 8, ± 8 to the other row of its page of 16);
  * slot 2 of the players -> c_dqplay: the passes counted per track (from the pattern's first step; a new pattern = 0; stopped = 0); a hit with
    a byte of ours is taken from the stock (the bit cleared around the stock's call, so its other work runs) and played as the stock plays it,
    with our velocity / sample, now or at its later micro step.
RAM: rhstate "drumpat".
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, add_sp_imm, adds_imm8, adds_reg, ands_reg, b, b_cond, b_w, bics_reg, bl, cmp_imm, cmp_reg, h, ldr_imm, ldr_sp,  # noqa: E402
                   ldrb_imm, ldrb_reg, ldrb_w, lsls_imm, lsls_reg, lsrs_imm, lsrs_reg, mov_reg, movs_imm, movt, movw, muls, orrs_reg, pop_list,
                   push_list, raw, str_sp, strb_imm, strb_reg, strb_w, strh_reg, sub_sp_imm, subs_imm8, subs_reg, tst_reg)
import countin as CI  # noqa: E402
import playmode as PM  # noqa: E402
import rhrec  # noqa: E402
import rhstate  # noqa: E402

CTRL, BTN_PRESS, BTN_RELEASE, BTN_PS = CI.CTRL, CI.BTN_ENTRY, CI.BTN_RELEASE, 12
PS_VT = PM.PS_VT
PROB_VT, PROB_LISTEN, PROB0, PROB_SZ = 0x08067E6C, 0x0805761E, 0x2004C7B8, 0x40
HASHIT = 0x08054AE0
DP0, DP_SZ, DP_VT = 0x200470D4, 0x190, 0x08068D24
NOTE_ON, VOICE_OFF, GATE_TAB, RANDOM = 0x0804B0D4, 0x0804B19E, 0x08068D9C, 0x080543A4
PARAM_GET = CI.PARAM_GET
TRANSPORT = CI.TRANSPORT
PAT_SZ, TRK_SZ, PAT0_OFF, LANES_OFF = 0xA28, 0x5140, 0x2E4, 0x128
FIRST_OFF, DQ_OFF = 0x101, 0x108
O_PLAY = rhstate.OFF["drumpat"][0]
O_UI = O_PLAY + 48
O_MARK = rhrec.OFF["drumpat"][0]
PS_PAD = 24                                                  # pad 25
COL_TOGGLE, COL_FREQ, COL_DYN, COL_MUT, COL_DIM = 0x74, 0x2F, 0x1E, 0x74, 0x09   # (Tracks 0x6A, 0x2D, 0x17, 0x6A, 0x02)
DYN = ((0, 0, 0, 0), (-2, 2, 0, 0), (-2, 2, 0, 32), (0, 0, 0, 32), (-1, 3, 0, 32), (-1, 3, 0, 0), (0, 0, -32, 32), (0, 0, -32, 64))
MUT = ((0, 0), (0, 4), (4, 0), (2, 2))
LED_CALLS = CI.LED_CALLS
LIS_VT = 0x080696A0                                          # (v2) the class of the steps' listener (slot 0 = 0x08048208)
ROWFIX = False                                               # RH30 (install(rowfix=True)): slot 8 of the probability view (PROB_LISTEN, its change
                                                             # callback) repaints row 3 with the stock's probability straight into the LED buffer, at
                                                             # any time on the device: our rows drawn again after it (the user: «dynamics apply, but
                                                             # they are not being displayed»; the mutate row, which it does not touch, showed)


RECDYN = False                                               # RH31 (install(recdyn=True)): with Record on, a step played with dynamics gets them written
                                                             # in (its velocity byte, its hit moved to the later micro step, in the pattern and in both
                                                             # copies of ST1) and its dynamics cleared (the user, 2026-10-21: «with Record on, write each
                                                             # played step's dynamics (velocity and micro step) into the step, as on the Tracks»)


def pushw(regs, lr=False): return h(0xE92D) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))
def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))
def mls_(rd, rn, rm, ra): return h(0xFB00 | rn) + h(ra << 12 | rd << 8 | 0x10 | rm)      # rd = ra - rn * rm
def udiv(rd, rn, rm): return h(0xFBB0 | rn) + h(0xF0F0 | rd << 8 | rm)
def ldrh_imm_(rt, rn, imm): return h(0x8800 | (imm // 2) << 6 | rn << 3 | rt)


def tables():
    t = b""
    for ml, mh, vl, vh in DYN:
        t += bytes([ml + 8, mh + 8, vl + 64, vh + 64])
    for r_, c_ in MUT:
        t += bytes([r_, c_])
    return t


def arm_code(base, L, prev, v2=False):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)
    zc = [0]
    INV = {"eq": "ne", "ne": "eq", "hs": "lo", "lo": "hs", "hi": "ls", "ls": "hi", "mi": "pl", "pl": "mi", "ge": "lt", "lt": "ge", "gt": "le", "le": "gt"}

    def bc(target, cond):
        zc[0] += 1
        n = f"_q{zc[0]}"
        E(b_cond, n, INV[cond])
        E(b, target)
        a.label(n)
    RET = h(0x4770)
    E(raw, tables())
    t_dyn, t_mut = base, base + 4 * len(DYN)

    # ---- c_dqon() -> r0 = 1 when the project is marked; clobbers r1, r2
    a.label("c_dqon")
    E(push_list, [3], lr=True)
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "on_x", "eq")
    E(ldrb_imm, 1, 0, O_MARK)
    E(cmp_imm, 1, 0x44)
    E(b_cond, "on_0", "ne")
    E(ldrb_imm, 1, 0, O_MARK + 1)
    E(cmp_imm, 1, 0x51)
    E(b_cond, "on_0", "ne")
    E(movs_imm, 0, 1)
    E(pop_list, [3], pc=True)
    a.label("on_0")
    E(movs_imm, 0, 0)
    a.label("on_x")
    E(pop_list, [3], pc=True)

    # ---- c_dqmark(): the project marked; the first time the bytes 8..39 of its 64 patterns cleared; clobbers r0-r3
    a.label("c_dqmark")
    E(push_list, [4, 5], lr=True)
    E(bl, "c_dqon")
    E(cmp_imm, 0, 0)
    E(b_cond, "mk_x", "ne")
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "mk_x", "eq")
    E(movs_imm, 1, 0x44)
    E(strb_imm, 1, 0, O_MARK)
    E(movs_imm, 1, 0x51)
    E(strb_imm, 1, 0, O_MARK + 1)
    imm32(1, rhrec.TAIL - PAT0_OFF - DQ_OFF)
    E(subs_reg, 5, 0, 1)                                                  # r5 = the first pattern's step bytes
    E(movs_imm, 4, 0)                                                     # r4 = track x 8 + pattern
    a.label("mk_d")
    E(lsrs_imm, 0, 4, 3)
    imm32(1, TRK_SZ)
    E(muls, 0, 1)
    E(movs_imm, 1, 7)
    E(ands_reg, 1, 4)
    imm32(2, PAT_SZ)
    E(muls, 1, 2)
    E(adds_reg, 0, 0, 1)
    E(adds_reg, 0, 0, 5)
    E(movs_imm, 1, 0)
    E(movs_imm, 2, 0)
    a.label("mk_z")
    E(strb_reg, 1, 0, 2)
    E(adds_imm8, 2, 1)
    E(cmp_imm, 2, 32)
    E(b_cond, "mk_z", "lo")
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, 64)
    E(b_cond, "mk_d", "lo")
    a.label("mk_x")
    E(pop_list, [4, 5], pc=True)

    # ---- c_dqbyte(r0 = a pattern's base, r1 = step) -> r0 = its byte (0 in a project not marked); clobbers r1-r3
    a.label("c_dqbyte")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(bl, "c_dqon")
    E(cmp_imm, 0, 0)
    E(b_cond, "by_x", "eq")
    E(adds_reg, 0, 4, 5)
    E(adds_imm8, 0, 0xFF)
    E(ldrb_imm, 0, 0, DQ_OFF - 0xFF)
    a.label("by_x")
    E(pop_list, [4, 5], pc=True)

    # ---- c_dqui() -> r0 = the view's state byte's address, or 0; clobbers r1-r3
    a.label("c_dqui")
    E(push_list, [4], lr=True)
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ui_x", "eq")
    E(adds_imm8, 0, O_UI)
    a.label("ui_x")
    E(pop_list, [4], pc=True)

    # ---- c_dqrnd(r0 = n) -> r0 = 0..n - 1 at random; clobbers r1-r3
    a.label("c_dqrnd")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, RANDOM)
    E(lsrs_imm, 0, 0, 4)
    E(raw, udiv(1, 0, 4))
    E(raw, mls_(0, 1, 4, 0))
    E(pop_list, [4], pc=True)

    # ---- c_dqmut(r0 = sample, r1 = level 1..3) -> r0 = the sample moved as MUT says (± 1 inside its row of 8, ± 8 inside its page of 16)
    a.label("c_dqmut")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(lsls_imm, 1, 1, 1)
    imm32(2, t_mut)
    E(adds_reg, 5, 2, 1)                                                  # r5 = the level's chances
    E(bl, RANDOM)
    E(mov_reg, 6, 0)                                                      # r6 = random bits
    E(movs_imm, 0, 15)
    E(ands_reg, 0, 6)
    E(ldrb_imm, 1, 5, 1)
    E(cmp_reg, 0, 1)
    E(b_cond, "mu_r", "hs")                                               # inside the row
    E(movs_imm, 0, 7)
    E(ands_reg, 0, 4)
    E(movs_imm, 1, 1)
    E(lsls_imm, 2, 6, 27)
    E(b_cond, "mu_p", "pl")
    E(movs_imm, 1, 7)                                                     # bit 4: down
    a.label("mu_p")
    E(adds_reg, 0, 0, 1)
    E(movs_imm, 1, 7)
    E(ands_reg, 0, 1)
    E(bics_reg, 4, 1)
    E(orrs_reg, 4, 0)
    a.label("mu_r")
    E(lsrs_imm, 0, 6, 5)
    E(movs_imm, 1, 15)
    E(ands_reg, 0, 1)
    E(ldrb_imm, 1, 5, 0)
    E(cmp_reg, 0, 1)
    E(b_cond, "mu_x", "hs")                                               # the other row of the page
    E(movs_imm, 1, 8)
    E(raw, h(0x404C))                                                     # eors r4, r1
    a.label("mu_x")
    E(mov_reg, 0, 4)
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_dqsmp(r0 = player, r1 = the step) -> r0 = the sample its hit plays now: the step's flip, else the selected one; clobbers r1-r3
    a.label("c_dqsmp")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(ldrb_imm, 0, 1, 5)
    E(cmp_imm, 0, 0xFF)
    E(b_cond, "sm_x", "ne")
    E(ldr_imm, 0, 4, 0x60)
    E(movs_imm, 1, 0)
    E(bl, PARAM_GET)
    E(ldrb_imm, 0, 0, 0)
    a.label("sm_x")
    E(pop_list, [4], pc=True)

    # ---- c_dqhit(r0 = player, r1 = the step, r2 = velocity, r3 = sample + 1 or 0): the step's note played as the stock's slot 2 plays it
    a.label("c_dqhit")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(sub_sp_imm, 8)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(mov_reg, 6, 2)
    E(cmp_imm, 3, 0)
    E(b_cond, "ht_n", "eq")
    E(subs_imm8, 3, 1)
    E(mov_reg, 2, 3)                                                      # the sample, as the stock's slot 4 sets it
    E(ldr_imm, 0, 4, 0x5C)
    E(raw, ldrh_imm_(1, 0, 0x18))
    E(ldr_imm, 0, 4, 0x58)
    E(ldr_imm, 3, 0, 0)
    E(ldr_imm, 3, 3, 0)
    E(raw, h(0x4798))                                                     # blx r3
    a.label("ht_n")
    E(ldrb_imm, 7, 5, 0)                                                  # r7 = the note (0: 0x30)
    E(cmp_imm, 7, 0)
    E(b_cond, "ht_v", "ne")
    E(movs_imm, 7, 0x30)
    a.label("ht_v")
    E(adds_reg, 0, 4, 7)
    E(ldrb_w, 1, 0, 0xAB)
    E(cmp_imm, 1, 0xFF)
    E(b_cond, "ht_g", "eq")
    E(mov_reg, 0, 4)
    E(bl, VOICE_OFF)                                                      # the voice of that note released
    a.label("ht_g")
    E(ldr_imm, 0, 4, 0x10)
    E(movs_imm, 1, 1)
    E(bl, PARAM_GET)
    E(ldrb_imm, 0, 0, 0)                                                  # the rate
    E(lsls_imm, 0, 0, 2)
    imm32(1, GATE_TAB)
    E(raw, h(0x5808))                                                     # ldr r0, [r1, r0]
    E(ldrb_imm, 3, 5, 1)
    E(muls, 3, 0)
    E(movs_imm, 0, 6)
    E(raw, udiv(3, 3, 0))
    E(cmp_imm, 3, 0)
    E(b_cond, "ht_t", "ne")
    E(movs_imm, 3, 1)
    a.label("ht_t")
    E(ldrb_imm, 0, 5, 6)
    E(movs_imm, 1, 1)
    E(ands_reg, 0, 1)
    E(str_sp, 0, 0)                                                       # [sp] = the tie
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 7)
    E(mov_reg, 2, 6)
    E(bl, NOTE_ON)
    E(add_sp_imm, 8)
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_dqplay (slot 2 of the track players: player, pattern, step, micro step)
    a.label("c_dqplay")
    E(raw, pushw([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], lr=True))           # sp + 0 player, + 4 pattern, + 8 step, + 12 micro step
    E(mov_reg, 4, 0)
    E(ldr_imm, 0, 4, 0)
    imm32(1, DP_VT)
    E(cmp_reg, 0, 1)
    bc("pl_stock", "ne")
    imm32(1, DP0)
    E(subs_reg, 0, 4, 1)
    imm32(1, DP_SZ)
    E(raw, udiv(6, 0, 1))                                                 # r6 = the track
    E(cmp_imm, 6, 7)
    bc("pl_stock", "hi")
    E(ldr_sp, 0, 4)
    imm32(1, PAT_SZ)
    E(muls, 0, 1)
    E(ldr_imm, 5, 4, 0x50)
    E(adds_reg, 5, 5, 0)                                                  # r5 = the pattern's base
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    bc("pl_stock", "eq")
    E(movs_imm, 1, 6)
    E(muls, 1, 6)
    E(adds_reg, 0, 0, 1)
    E(adds_imm8, 0, O_PLAY)
    E(mov_reg, 7, 0)                                                      # r7 = its play state
    # a pass begins: the first step's micro step 0 (a new pattern from 0)
    E(ldr_sp, 2, 8)
    imm32(1, FIRST_OFF)
    E(raw, h(0x5C68))                                                     # ldrb r0, [r5, r1]
    E(cmp_reg, 0, 2)
    E(b_cond, "pl_pd", "ne")
    E(ldr_sp, 0, 12)
    E(cmp_imm, 0, 0)
    E(b_cond, "pl_pd", "ne")
    E(ldr_sp, 0, 4)
    E(adds_imm8, 0, 1)
    E(ldrb_imm, 1, 7, 2)
    E(cmp_reg, 0, 1)
    E(b_cond, "pl_c", "eq")
    E(strb_imm, 0, 7, 2)
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 7, 0)
    E(strb_imm, 0, 7, 1)
    E(b, "pl_pd")
    a.label("pl_c")
    E(ldrb_imm, 0, 7, 0)
    E(ldrb_imm, 1, 7, 1)
    E(lsls_imm, 1, 1, 8)
    E(orrs_reg, 0, 1)
    E(adds_imm8, 0, 1)
    imm32(1, 840)
    E(cmp_reg, 0, 1)
    E(b_cond, "pl_w", "lo")
    E(movs_imm, 0, 0)
    a.label("pl_w")
    E(strb_imm, 0, 7, 0)
    E(lsrs_imm, 0, 0, 8)
    E(strb_imm, 0, 7, 1)
    # r10 = 1: a hit kept for this micro step
    a.label("pl_pd")
    E(movs_imm, 0, 0)
    E(mov_reg, 10, 0)
    E(ldrb_imm, 0, 7, 3)
    E(cmp_imm, 0, 0)
    E(b_cond, "pl_h", "eq")
    E(ldr_sp, 1, 12)
    E(adds_imm8, 1, 1)
    E(cmp_reg, 0, 1)
    E(b_cond, "pl_h", "ne")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 7, 3)
    E(movs_imm, 0, 1)
    E(mov_reg, 10, 0)
    # a hit of the stock now, with a byte of ours?
    a.label("pl_h")
    E(movs_imm, 0, 0xA6)
    E(lsls_imm, 0, 0, 1)                                                  # 0x14C
    E(ldrb_reg, 0, 4, 0)
    E(ldr_sp, 1, 12)
    E(lsrs_reg, 0, 1)
    E(lsls_imm, 0, 0, 31)
    bc("pl_plain", "pl")
    E(ldr_sp, 1, 8)
    E(mov_reg, 0, 5)
    E(bl, "c_dqbyte")
    E(mov_reg, 8, 0)                                                      # r8 = our byte
    E(cmp_imm, 0, 0)
    bc("pl_plain", "eq")
    E(ldr_sp, 1, 8)
    E(lsls_imm, 1, 1, 3)
    E(adds_reg, 1, 1, 5)
    E(ldrb_imm, 6, 1, 3)                                                  # r6 = the velocity
    # the frequency: pass % n = 0
    E(mov_reg, 0, 8)
    E(lsrs_imm, 1, 0, 3)
    E(movs_imm, 2, 7)
    E(ands_reg, 1, 2)
    E(cmp_imm, 1, 0)
    E(b_cond, "pl_dy", "eq")
    E(adds_imm8, 1, 1)
    E(ldrb_imm, 0, 7, 0)
    E(ldrb_imm, 2, 7, 1)
    E(lsls_imm, 2, 2, 8)
    E(orrs_reg, 0, 2)
    E(raw, udiv(2, 0, 1))
    E(raw, mls_(0, 2, 1, 0))
    E(cmp_imm, 0, 0)
    bc("pl_skip", "ne")
    # the dynamics: the velocity, a later micro step (r9)
    a.label("pl_dy")
    E(movs_imm, 0, 0)
    E(mov_reg, 9, 0)
    E(mov_reg, 0, 8)
    E(movs_imm, 1, 7)
    E(ands_reg, 0, 1)
    E(cmp_imm, 0, 0)
    bc("pl_mu", "eq")
    E(lsls_imm, 0, 0, 2)
    imm32(1, t_dyn)
    E(adds_reg, 0, 0, 1)
    E(mov_reg, 2, 0)
    E(push_list, [2])
    E(ldrb_imm, 1, 2, 3)
    E(ldrb_imm, 0, 2, 2)
    E(subs_reg, 0, 1, 0)
    E(adds_imm8, 0, 1)
    E(bl, "c_dqrnd")
    E(pop_list, [2])
    E(push_list, [2])
    E(ldrb_imm, 1, 2, 2)
    E(adds_reg, 6, 6, 0)
    E(adds_reg, 6, 6, 1)
    E(subs_imm8, 6, 64)
    E(cmp_imm, 6, 1)
    E(b_cond, "pl_v1", "ge")
    E(movs_imm, 6, 1)
    a.label("pl_v1")
    E(cmp_imm, 6, 127)
    E(b_cond, "pl_v2", "le")
    E(movs_imm, 6, 127)
    a.label("pl_v2")
    E(pop_list, [2])
    E(ldrb_imm, 1, 2, 1)
    E(ldrb_imm, 0, 2, 0)
    E(push_list, [0])
    E(subs_reg, 0, 1, 0)
    E(adds_imm8, 0, 1)
    E(bl, "c_dqrnd")
    E(pop_list, [1])
    E(adds_reg, 0, 0, 1)
    E(subs_imm8, 0, 8)
    E(cmp_imm, 0, 0)
    E(b_cond, "pl_mu", "le")                                              # later only
    E(ldr_sp, 1, 12)
    E(adds_reg, 1, 1, 0)
    E(cmp_imm, 1, 5)
    E(b_cond, "pl_m5", "le")
    E(movs_imm, 1, 5)
    a.label("pl_m5")
    E(ldr_sp, 2, 12)
    E(subs_reg, 0, 1, 2)
    E(mov_reg, 9, 0)
    # the mutate: the sample (r3 = sample + 1, 0: as it is)
    a.label("pl_mu")
    E(movs_imm, 3, 0)
    E(mov_reg, 0, 8)
    E(lsrs_imm, 0, 0, 6)
    E(cmp_imm, 0, 0)
    E(b_cond, "pl_go", "eq")
    E(push_list, [0])
    E(ldr_sp, 1, 4 + 8)
    E(lsls_imm, 1, 1, 3)
    E(adds_reg, 1, 1, 5)
    E(mov_reg, 0, 4)
    E(bl, "c_dqsmp")
    E(pop_list, [1])
    E(movs_imm, 3, 0)
    E(cmp_imm, 0, 0x7F)
    E(b_cond, "pl_go", "hi")
    E(bl, "c_dqmut")
    E(adds_imm8, 0, 1)
    E(mov_reg, 3, 0)
    a.label("pl_go")
    if RECDYN:                                                            # Record on: the dynamics written into the step
        E(push_list, [3])
        E(mov_reg, 0, 8)
        E(movs_imm, 1, 7)
        E(ands_reg, 0, 1)
        E(cmp_imm, 0, 0)
        E(b_cond, "pl_nr", "eq")
        E(mov_reg, 0, 5)
        E(ldr_sp, 1, 8 + 4)
        E(mov_reg, 2, 6)
        E(ldr_sp, 3, 12 + 4)
        E(lsls_imm, 3, 3, 4)
        E(raw, h(0x444B))                                                 # add r3, r9: micro step << 4 | the delay
        E(bl, "c_dqrec")
        a.label("pl_nr")
        E(pop_list, [3])
    E(push_list, [3])
    E(bl, "c_dqstock0")                                                   # the stock's call without the hit
    E(pop_list, [3])
    E(mov_reg, 0, 9)
    E(cmp_imm, 0, 0)
    E(b_cond, "pl_now", "eq")
    E(ldr_sp, 1, 12)
    E(adds_reg, 0, 0, 1)
    E(adds_imm8, 0, 1)
    E(strb_imm, 0, 7, 3)
    E(strb_imm, 6, 7, 4)
    E(strb_imm, 3, 7, 5)
    E(b, "pl_kept")
    a.label("pl_now")
    E(mov_reg, 0, 4)
    E(ldr_sp, 1, 8)
    E(lsls_imm, 1, 1, 3)
    E(adds_reg, 1, 1, 5)
    E(mov_reg, 2, 6)
    E(bl, "c_dqhit")
    E(b, "pl_kept")
    a.label("pl_skip")
    E(push_list, [3])                                                     # (c_dqstock0 finds the frame one word up)
    E(bl, "c_dqstock0")
    E(pop_list, [3])
    E(b, "pl_kept")
    a.label("pl_plain")
    E(ldr_sp, 0, 0)
    E(ldr_sp, 1, 4)
    E(ldr_sp, 2, 8)
    E(ldr_sp, 3, 12)
    E(bl, prev["play"])
    a.label("pl_kept")                                                    # a hit kept for this micro step
    E(mov_reg, 0, 10)
    E(cmp_imm, 0, 0)
    E(b_cond, "pl_x", "eq")
    E(mov_reg, 0, 4)
    E(ldr_sp, 1, 8)
    E(lsls_imm, 1, 1, 3)
    E(adds_reg, 1, 1, 5)
    E(ldrb_imm, 2, 7, 4)
    E(ldrb_imm, 3, 7, 5)
    E(bl, "c_dqhit")
    E(b, "pl_x")
    a.label("pl_stock")
    E(ldr_sp, 0, 0)
    E(ldr_sp, 1, 4)
    E(ldr_sp, 2, 8)
    E(ldr_sp, 3, 12)
    E(bl, prev["play"])
    a.label("pl_x")
    E(raw, popw([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], lr=True))
    E(raw, RET)

    if RECDYN:
        # ---- c_dqrec(r0 = pattern, r1 = step, r2 = velocity, r3 = micro step << 4 | delay; r4 = the player): with Record on, the step takes the
        #      velocity and its hit the later micro step, in the pattern and in both copies of ST1 when they hold this pattern; its dynamics cleared
        a.label("c_dqrec")
        E(raw, pushw([4, 5, 6, 7, 8, 9, 10, 11], lr=True))
        E(mov_reg, 8, 0)                                                  # r8 = pattern
        E(mov_reg, 9, 1)                                                  # r9 = step
        E(mov_reg, 10, 2)                                                 # r10 = velocity
        E(mov_reg, 11, 3)                                                 # r11 = micro << 4 | delay
        imm32(0, TRANSPORT)
        E(movs_imm, 1, 1)
        E(bl, PARAM_GET)
        E(ldrb_imm, 0, 0, 0)
        E(cmp_imm, 0, 0)
        bc("rc_x", "eq")                                                  # not recording
        imm32(0, DP0)
        E(subs_reg, 0, 4, 0)
        imm32(1, DP_SZ)
        E(raw, udiv(5, 0, 1))                                             # r5 = the track
        E(mov_reg, 0, 5)                                                  # the stores first: c_pmfind compares them with the pattern
        E(bl, L["c_pmfind"])
        E(mov_reg, 1, 8)
        E(cmp_reg, 0, 1)
        E(b_cond, "rc_st", "eq")
        E(movs_imm, 6, 0)                                                 # r6 = ST1 when it holds this pattern, else 0
        a.label("rc_st")
        E(mov_reg, 0, 9)
        E(lsls_imm, 0, 0, 3)
        E(mov_reg, 1, 8)
        E(adds_reg, 0, 0, 1)                                              # r0 = the step
        E(mov_reg, 1, 10)
        E(strb_imm, 1, 0, 3)                                              # the velocity
        E(mov_reg, 1, 11)
        E(lsrs_imm, 2, 1, 4)                                              # r2 = micro step
        E(movs_imm, 3, 15)
        E(ands_reg, 1, 3)                                                 # r1 = the delay
        E(ldrb_imm, 3, 0, 2)                                              # the micro steps' mask
        E(cmp_imm, 1, 0)
        E(b_cond, "rc_m", "eq")
        E(movs_imm, 7, 1)
        E(lsls_reg, 7, 2)
        E(bics_reg, 3, 7)
        E(adds_reg, 2, 2, 1)
        E(movs_imm, 7, 1)
        E(lsls_reg, 7, 2)
        E(orrs_reg, 3, 7)
        E(strb_imm, 3, 0, 2)
        a.label("rc_m")
        E(mov_reg, 7, 3)                                                  # r7 = the new mask
        E(mov_reg, 0, 8)                                                  # our byte: the dynamics cleared
        E(movs_imm, 1, DQ_OFF >> 2)
        E(lsls_imm, 1, 1, 2)
        E(adds_reg, 0, 0, 1)
        E(mov_reg, 1, 9)
        E(ldrb_reg, 2, 0, 1)
        E(movs_imm, 3, 7)
        E(bics_reg, 2, 3)
        E(strb_reg, 2, 0, 1)
        E(cmp_imm, 6, 0)
        bc("rc_x", "eq")                                                  # the stores hold another pattern: the pattern only
        for o in (0xC, 0x10):
            E(ldr_imm, 0, 6, o)
            E(mov_reg, 1, 9)
            E(mov_reg, 2, 10)
            E(strb_reg, 2, 0, 1)                                          # the velocity group (words 0-7)
            E(adds_imm8, 0, 64)
            E(strb_reg, 7, 0, 1)                                          # the micro steps' group (words 16-23)
        a.label("rc_x")
        E(raw, popw([4, 5, 6, 7, 8, 9, 10, 11], lr=True))
        E(raw, h(0x4770))                                                 # bx lr

    # ---- c_dqstock0 (inside c_dqplay: r4 = player, the caller's frame above): the stock's slot 2 with this micro step's bit cleared, then put back
    a.label("c_dqstock0")
    E(push_list, [4, 5, 6], lr=True)                                      # the caller's sp + 0 is now at sp + 16 (+ 4 more for the pushed r3)
    F = 16 + 4
    E(movs_imm, 5, 0xA6)
    E(lsls_imm, 5, 5, 1)
    E(adds_reg, 5, 5, 4)                                                  # r5 = the player's micro step mask
    E(ldrb_imm, 6, 5, 0)
    E(ldr_sp, 1, F + 12)
    E(movs_imm, 0, 1)
    E(lsls_reg, 0, 1)
    E(mov_reg, 1, 6)
    E(bics_reg, 1, 0)
    E(strb_imm, 1, 5, 0)
    E(ldr_sp, 0, F + 0)
    E(ldr_sp, 1, F + 4)
    E(ldr_sp, 2, F + 8)
    E(ldr_sp, 3, F + 12)
    E(bl, prev["play"])
    E(strb_imm, 6, 5, 0)
    E(pop_list, [4, 5, 6], pc=True)

    # ---- the views
    # c_dqpspad: Pattern Settings pad 25 (no Shift) = the probability view in mode 2
    a.label("c_dqpspad")
    E(cmp_imm, 1, PS_PAD)
    E(b_cond, "pp_f", "ne")
    E(push_list, [0, 1, 2, 4], lr=True)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "pp_p", "eq")
    E(bl, L["c_cishift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "pp_p", "ne")
    E(bl, "c_dqui")
    E(cmp_imm, 0, 0)
    E(b_cond, "pp_p", "eq")
    E(ldrb_imm, 1, 0, 0)
    E(movs_imm, 2, 4)
    E(orrs_reg, 1, 2)
    E(strb_imm, 1, 0, 0)
    imm32(0, CTRL)
    E(movs_imm, 1, BTN_PS)
    E(bl, BTN_PRESS)
    imm32(0, CTRL)
    E(movs_imm, 1, BTN_PS)
    E(bl, BTN_RELEASE)
    E(pop_list, [0, 1, 2, 4], pc=True)
    a.label("pp_p")
    E(raw, popw([0, 1, 2, 4], lr=True))
    a.label("pp_f")
    E(b_w, prev["pspad"])
    # c_dqpsled: Pattern Settings' LEDs: the chain, then pad 25 peach (unless something else lit it)
    a.label("c_dqpsled")
    E(push_list, [0, 1, 4], lr=True)
    E(bl, prev["psled"])
    E(str_sp, 0, 4)
    E(ldr_sp, 1, 0)
    E(ldr_imm, 1, 1, 4)
    E(ldr_imm, 1, 1, 0)
    E(movs_imm, 3, 2 * PS_PAD)
    E(raw, h(0x5ACA))                                                     # ldrh r2, [r1, r3]
    E(cmp_imm, 2, 0)
    E(b_cond, "pl_l", "ne")
    E(movs_imm, 2, COL_TOGGLE)
    E(strh_reg, 2, 1, 3)
    a.label("pl_l")
    E(ldr_sp, 0, 4)
    E(raw, h(0xB002))                                                     # add sp, #8
    E(pop_list, [4], pc=True)

    # c_dqview(r0 = view) -> r0 = track, r1 = the edited pattern's base, r2 = the selected step
    a.label("c_dqview")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 0)
    imm32(1, PROB0)
    E(subs_reg, 0, 0, 1)
    E(lsrs_imm, 5, 0, 6)
    E(ldr_imm, 0, 4, 0xC)
    E(ldr_imm, 0, 0, 0xC)
    E(movs_imm, 1, 1)
    E(bl, PARAM_GET)
    E(ldrb_imm, 2, 0, 0)
    E(ldr_imm, 0, 4, 0xC)
    E(ldr_imm, 0, 0, 0)
    E(ldr_imm, 1, 0, 0x18)
    imm32(0, LANES_OFF)
    E(subs_reg, 1, 1, 0)
    E(mov_reg, 0, 5)
    E(pop_list, [4, 5], pc=True)

    # c_dqhas(r0 = view) -> r0 = 1 when the selected step has a hit; clobbers r1-r3
    a.label("c_dqhas")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(ldr_imm, 0, 4, 0xC)
    E(ldr_imm, 0, 0, 0xC)
    E(movs_imm, 1, 1)
    E(bl, PARAM_GET)
    E(ldrb_imm, 1, 0, 0)
    E(ldr_imm, 0, 4, 0xC)
    E(ldr_imm, 0, 0, 0)
    E(bl, HASHIT)
    E(pop_list, [4], pc=True)

    # c_dqpad (the probability view's slot 0: view, pad 0..15, velocity)
    a.label("c_dqpad")
    E(cmp_imm, 1, 15)
    bc("dp_f", "hi")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(mov_reg, 7, 1)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("dp_p", "eq")
    E(bl, "c_dqui")
    E(movs_imm, 6, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "dp_m", "eq")
    E(ldrb_imm, 6, 0, 0)
    E(movs_imm, 0, 1)
    E(ands_reg, 6, 0)                                                     # r6 = mode 2
    a.label("dp_m")
    E(cmp_imm, 6, 0)
    E(b_cond, "dp_2", "ne")
    E(cmp_imm, 7, 8)
    bc("dp_p", "lo")                                                      # mode 1: row 3 the stock's
    E(subs_imm8, 7, 8)
    E(movs_imm, 5, 3)
    E(b, "dp_s")                                                          # row 4: the frequency (bits 3-5)
    a.label("dp_2")
    E(cmp_imm, 7, 8)
    E(b_cond, "dp_d", "lo")
    E(subs_imm8, 7, 8)
    E(cmp_imm, 7, 3)
    bc("dp_t", "hi")
    E(movs_imm, 5, 6)
    E(b, "dp_s")                                                          # pads 25-28: the mutate (bits 6-7)
    a.label("dp_d")
    E(movs_imm, 5, 0)                                                     # row 3: the dynamics (bits 0-2)
    a.label("dp_s")
    E(ldr_sp, 0, 0)
    E(bl, "c_dqhas")
    E(cmp_imm, 0, 0)
    bc("dp_t", "eq")                                                      # a step without a hit
    E(bl, "c_dqmark")
    E(ldr_sp, 0, 0)
    E(bl, "c_dqview")
    E(adds_reg, 1, 1, 2)
    E(adds_imm8, 1, 0xFF)
    E(adds_imm8, 1, DQ_OFF - 0xFF)
    E(mov_reg, 4, 1)                                                      # r4 = our byte's address
    E(ldrb_imm, 0, 4, 0)
    E(movs_imm, 1, 7)
    E(cmp_imm, 5, 6)
    E(b_cond, "dp_k", "ne")
    E(movs_imm, 1, 3)
    a.label("dp_k")
    E(lsls_reg, 1, 5)
    E(bics_reg, 0, 1)
    E(lsls_reg, 7, 5)
    E(orrs_reg, 0, 7)
    E(strb_imm, 0, 4, 0)
    a.label("dp_t")
    E(raw, h(0xB003))                                                     # add sp, #12
    E(pop_list, [4, 5, 6, 7], pc=True)
    a.label("dp_p")
    E(raw, popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    a.label("dp_f")
    E(b_w, prev["ppad"])

    # c_dqrows(r0 = view): our rows into its 16 LEDs
    a.label("c_dqrows")
    E(raw, pushw([4, 5, 6, 7, 8], lr=True))
    E(mov_reg, 4, 0)
    E(ldr_imm, 0, 4, 4)
    E(ldr_imm, 5, 0, 0)                                                   # r5 = the LEDs
    E(bl, "c_dqui")
    E(movs_imm, 6, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "rw_m", "eq")
    E(ldrb_imm, 6, 0, 0)
    E(movs_imm, 0, 1)
    E(ands_reg, 6, 0)
    a.label("rw_m")
    E(mov_reg, 0, 4)
    E(bl, "c_dqhas")
    E(mov_reg, 8, 0)                                                      # r8 = a hit
    E(mov_reg, 0, 4)
    E(bl, "c_dqview")
    E(mov_reg, 0, 1)
    E(mov_reg, 1, 2)
    E(bl, "c_dqbyte")
    E(mov_reg, 7, 0)                                                      # r7 = our byte
    E(cmp_imm, 6, 0)
    bc("rw_2", "ne")
    E(lsrs_imm, 7, 7, 3)                                                  # mode 1: row 4 = the frequency as a yellow bar
    E(movs_imm, 0, 7)
    E(ands_reg, 7, 0)
    E(movs_imm, 3, 0)
    a.label("rw_f")
    E(movs_imm, 2, 0)
    E(mov_reg, 0, 8)
    E(cmp_imm, 0, 0)
    E(b_cond, "rw_fw", "eq")
    E(movs_imm, 2, COL_DIM)
    E(cmp_reg, 3, 7)
    E(b_cond, "rw_fw", "hi")
    E(movs_imm, 2, COL_FREQ)
    a.label("rw_fw")
    E(mov_reg, 0, 3)
    E(adds_imm8, 0, 8)
    E(lsls_imm, 0, 0, 1)
    E(strh_reg, 2, 5, 0)
    E(adds_imm8, 3, 1)
    E(cmp_imm, 3, 8)
    E(b_cond, "rw_f", "lo")
    E(b, "rw_x")
    a.label("rw_2")                                                       # mode 2: row 3 = the dynamics, pads 25-28 = the mutate bar
    E(movs_imm, 3, 0)
    a.label("rw_d")
    E(movs_imm, 2, 0)
    E(mov_reg, 0, 8)
    E(cmp_imm, 0, 0)
    E(b_cond, "rw_dw", "eq")
    E(movs_imm, 2, COL_DIM)
    E(movs_imm, 0, 7)
    E(ands_reg, 0, 7)
    E(cmp_reg, 0, 3)
    E(b_cond, "rw_dw", "ne")
    E(movs_imm, 2, COL_DYN)
    a.label("rw_dw")
    E(lsls_imm, 0, 3, 1)
    E(strh_reg, 2, 5, 0)
    E(adds_imm8, 3, 1)
    E(cmp_imm, 3, 8)
    E(b_cond, "rw_d", "lo")
    E(lsrs_imm, 7, 7, 6)
    E(movs_imm, 3, 0)
    a.label("rw_u")
    E(movs_imm, 2, 0)
    E(mov_reg, 0, 8)
    E(cmp_imm, 0, 0)
    E(b_cond, "rw_uw", "eq")
    E(cmp_imm, 3, 4)
    E(b_cond, "rw_uw", "hs")
    E(movs_imm, 2, COL_DIM)
    E(cmp_reg, 3, 7)
    E(b_cond, "rw_uw", "hi")
    E(movs_imm, 2, COL_MUT)
    a.label("rw_uw")
    E(mov_reg, 0, 3)
    E(adds_imm8, 0, 8)
    E(lsls_imm, 0, 0, 1)
    E(strh_reg, 2, 5, 0)
    E(adds_imm8, 3, 1)
    E(cmp_imm, 3, 8)
    E(b_cond, "rw_u", "lo")
    a.label("rw_x")
    E(raw, popw([4, 5, 6, 7, 8], lr=True))
    E(raw, RET)

    # c_dqbuf (the probability view's slot 7: view) -> its LEDs: the view on the screen (a view that opens takes the mode asked, else mode 1;
    # row 3 back to the stock's after mode 2), then our rows
    a.label("c_dqbuf")
    E(push_list, [3, 4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "bf_y", "eq")
    E(bl, "c_dqui")
    E(cmp_imm, 0, 0)
    E(b_cond, "bf_r", "eq")
    E(mov_reg, 5, 0)
    E(ldrb_imm, 1, 5, 0)
    E(lsrs_imm, 2, 1, 4)
    E(b_cond, "bf_o", "ne")
    E(movs_imm, 2, 1)
    E(tst_reg, 1, 2)
    E(b_cond, "bf_a", "eq")
    E(movs_imm, 2, 2)
    E(orrs_reg, 1, 2)                                                     # it was in mode 2: row 3 to be redrawn
    a.label("bf_a")
    E(lsrs_imm, 2, 1, 2)
    E(movs_imm, 3, 1)
    E(ands_reg, 2, 3)
    E(movs_imm, 3, 0x0D)
    E(bics_reg, 1, 3)
    E(orrs_reg, 1, 2)                                                     # mode = asked, asked off
    a.label("bf_o")
    E(movs_imm, 2, 0x30)
    E(orrs_reg, 1, 2)
    E(movs_imm, 2, 1)
    E(tst_reg, 1, 2)
    E(b_cond, "bf_s", "ne")                                               # mode 1 with row 3 to redraw: the stock's listener
    E(movs_imm, 2, 2)
    E(tst_reg, 1, 2)
    E(b_cond, "bf_s", "eq")
    E(bics_reg, 1, 2)
    E(strb_imm, 1, 5, 0)
    E(mov_reg, 0, 4)
    E(bl, PROB_LISTEN)
    E(b, "bf_r")
    a.label("bf_s")
    E(strb_imm, 1, 5, 0)
    a.label("bf_r")
    E(mov_reg, 0, 4)
    E(bl, "c_dqrows")
    a.label("bf_y")
    E(mov_reg, 0, 4)
    E(pop_list, [3, 4, 5])
    E(raw, h(0xF85D) + h(0xEB04))                                         # ldr lr, [sp], #4
    E(b_w, prev["pbuf"])

    if ROWFIX:
        # c_dqlis (the probability view's slot 8: view, ...): the stock's repaint of row 3, then our rows; the stock's r0 returned
        a.label("c_dqlis")
        E(push_list, [0, 1, 4], lr=True)
        E(bl, prev["plis"])
        E(str_sp, 0, 4)
        E(bl, L["c_ciok"])
        E(cmp_imm, 0, 0)
        E(b_cond, "li_x", "eq")
        E(ldr_sp, 0, 0)
        E(bl, "c_dqrows")
        a.label("li_x")
        E(ldr_sp, 0, 4)
        E(raw, h(0xB002))                                                 # add sp, #8
        E(pop_list, [4], pc=True)

    # c_dqledtask (the LED task's calls): the chain; one LED pass less to "on the screen"; stopped: the passes and the kept hits to 0
    a.label("c_dqledtask")
    E(push_list, [3, 4], lr=True)
    E(bl, prev["ledtask"])
    E(bl, "c_dqui")
    E(cmp_imm, 0, 0)
    E(b_cond, "lt_x", "eq")
    E(ldrb_imm, 1, 0, 0)
    E(lsrs_imm, 2, 1, 4)
    E(b_cond, "lt_t", "eq")
    E(subs_imm8, 1, 0x10)
    E(strb_imm, 1, 0, 0)
    a.label("lt_t")
    E(mov_reg, 4, 0)
    imm32(0, TRANSPORT)
    E(movs_imm, 1, 0)
    E(bl, PARAM_GET)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "lt_x", "ne")
    E(mov_reg, 0, 4)
    E(subs_imm8, 0, 48)
    E(movs_imm, 1, 0)
    E(movs_imm, 2, 0)
    a.label("lt_z")
    E(strb_reg, 1, 0, 2)
    E(adds_imm8, 2, 1)
    E(cmp_imm, 2, 48)
    E(b_cond, "lt_z", "lo")
    a.label("lt_x")
    E(pop_list, [3, 4], pc=True)

    if v2:
        # c_dqsweep (v2: slot 0 of the steps' listener, class 0x080696A0: listener, store, mask): the stock's commit, then in a marked project the
        # byte of every step without a hit back to 0 (a hit the stock adds later, or a cleared pattern, does not take an old value)
        a.label("c_dqsweep")
        E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
        E(bl, prev["lis"])
        E(ldr_sp, 4, 0)
        E(ldr_imm, 0, 4, 0)
        imm32(1, LIS_VT)
        E(cmp_reg, 0, 1)
        E(b_cond, "sw_x", "ne")
        E(ldr_imm, 0, 4, 0x1C)
        E(ldr_sp, 1, 4)
        E(cmp_reg, 0, 1)
        E(b_cond, "sw_x", "ne")                                           # not the steps' store ST1
        E(bl, "c_dqon")
        E(cmp_imm, 0, 0)
        E(b_cond, "sw_x", "eq")
        E(ldr_imm, 0, 4, 0x28)
        E(movs_imm, 1, 0)
        E(bl, PARAM_GET)
        E(ldrb_imm, 0, 0, 0)
        E(cmp_imm, 0, 7)
        E(b_cond, "sw_x", "hi")
        imm32(1, PAT_SZ)
        E(muls, 0, 1)
        E(ldr_imm, 1, 4, 4)
        E(adds_reg, 5, 0, 1)                                              # r5 = the pattern
        E(movs_imm, 6, 0)
        a.label("sw_l")
        E(lsls_imm, 0, 6, 3)
        E(adds_reg, 0, 0, 5)
        E(ldrb_imm, 0, 0, 3)
        E(cmp_imm, 0, 0)
        E(b_cond, "sw_n", "ne")
        E(adds_reg, 1, 5, 6)
        E(adds_imm8, 1, 0xFF)
        E(movs_imm, 2, 0)
        E(strb_imm, 2, 1, DQ_OFF - 0xFF)
        a.label("sw_n")
        E(adds_imm8, 6, 1)
        E(cmp_imm, 6, 32)
        E(b_cond, "sw_l", "lo")
        a.label("sw_x")
        E(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr, v2=False, rowfix=False, recdyn=False):
    """Append the code; slot 2 of the track players, slots 0 / 7 of Pattern Settings and of the probability view, the LED task calls."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]
    lab = lambda m, k: int(report[m]["labels"][k], 16)
    L = dict(c_rst=lab("rhstate", "c_rst"), c_rrt=lab("rhrec", "c_rrt"), c_ciok=lab("countin", "c_ciok"), c_cishift=lab("countin", "c_cishift"))
    global ROWFIX, RECDYN
    ROWFIX, RECDYN = rowfix, recdyn
    if recdyn:
        L["c_pmfind"] = lab("playmode", "c_pmfind")
    old = dict(play=u(DP_VT + 8), pspad=u(PS_VT), psled=u(PS_VT + 28), ppad=u(PROB_VT), pbuf=u(PROB_VT + 28))
    if rowfix:
        old["plis"] = u(PROB_VT + 0x20)
        assert old["plis"] == PROB_LISTEN | 1, hex(old["plis"])
    prev = {k: v & ~1 for k, v in old.items()}
    prev["ledtask"] = rhbuild.bl_target(img, LED_CALLS[0])
    if v2:
        old["lis"] = u(LIS_VT)
        prev["lis"] = old["lis"] & ~1
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in LED_CALLS)
    code, labels = arm_code(base_addr, L, prev, v2)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    for addr, k, nm in ((DP_VT + 8, "play", "c_dqplay"), (PS_VT, "pspad", "c_dqpspad"), (PS_VT + 28, "psled", "c_dqpsled"),
                        (PROB_VT, "ppad", "c_dqpad"), (PROB_VT + 28, "pbuf", "c_dqbuf")):
        rhbuild.patch_word(img, addr, old[k], labels[nm] | 1)
    if v2:
        rhbuild.patch_word(img, LIS_VT, old["lis"], labels["c_dqsweep"] | 1)
    if rowfix:
        rhbuild.patch_word(img, PROB_VT + 0x20, old["plis"], labels["c_dqlis"] | 1)
    for c in LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_dqledtask"]))
    report["drumpat"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
