"""Pattern Settings, pad 26 = NUDGE (MIT; the pad 26 of CIRCUIT-HACKS' playmode, SC40.8 / SC40.9, for the Circuit Rhythm 5706): the pattern is
written again so that its first step is step 1; what was in front of it goes to the end («reescribe el patrón, poniendo el inicio de
reproducción seleccionado al principio; rellenar hasta el final con lo que haya antes del inicio»; «rota los 16 / 32 según la longitud de la
secuencia, el paso completo con sus knobs, el inicio queda en paso 1»).

The stock of the Rhythm (read in the firmware and on the RAM dump, emulated):
  * Pattern Settings = button 12; a view per track, 0x2004C4B8 + 0x60 t (vtable 0x08067EA4); slot 0 = 0x08057218(view, pad, velocity): pads 0-15
    (+ 16 x the page) the last step (or the first, while one is held), 16-23 the sync rate, 28-31 the direction (parameters 0 (last | first << 8),
    1, 2 of [view + 0xC] = the track's settings store ST3, then its commit); pads 24-27 do nothing; slot 7 = its LEDs (0x0805737C, the pad buffer
    [[view + 4]], a halfword per pad);
  * the pattern and its two step stores as in quant.py (ST1 / ST2 hold its steps; their listener's [+ 0x24] = ST3, whose commit writes the settings
    bytes + 0x100..); the 12 automation lanes (+ 0x128 + 192 l, 6 micro steps a step) are not in any store.
Ours: slot 0 (in front of the stock): pad index 25 on a track whose stores hold its pattern = nudge: n = 16 when the first and the last step are
below 16, else 32; the steps (8 B) and each lane (6 B a step) rotate left by the first step over n; then first = 0 and last = (last - first) mod n
through ST3 (write getter + commit, as the stock's pads); ST1 / ST2 get the new words in both copies.  Pad 26 orange (slot 7, after the stock).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, add_sp_imm, adds_imm8, adds_reg, b, b_cond, b_w, bl, cmp_imm, cmp_reg, h, ldr_imm, ldr_sp, ldrb_imm, lsls_imm,  # noqa: E402
                   mov_reg, movs_imm, movt, movw, muls, pop_list, push_list, raw, str_sp, strb_imm, strh_reg, sub_sp_imm, subs_imm8, subs_reg)
import countin as CI  # noqa: E402
import quant as Q  # noqa: E402

PS0, PS_SZ, PS_VT = 0x2004C4B8, 0x60, 0x08067EA4
PAD_NUDGE = 25
COL_NUDGE = 0x12                                           # orange (Tracks 0x09)
LANES, LANE_STEP = 12, 6
PARAM_WPTR, COMMIT = 0x0803FD26, 0x0803FBEC
PARAM_NEW = CI.PARAM_NEW


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def arm_code(base, L, prev, v2=False):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_pmrev(r0 = lo, r1 = hi, exclusive): the bytes reversed; clobbers r0-r3
    a.label("c_pmrev")
    a.label("rv_l")
    E(subs_imm8, 1, 1)
    E(cmp_reg, 0, 1)
    E(b_cond, "rv_x", "hs")
    E(ldrb_imm, 2, 0, 0)
    E(ldrb_imm, 3, 1, 0)
    E(strb_imm, 3, 0, 0)
    E(strb_imm, 2, 1, 0)
    E(adds_imm8, 0, 1)
    E(b, "rv_l")
    a.label("rv_x")
    E(raw, h(0x4770))

    # ---- c_pmrot(r0 = base, r1 = bytes, r2 = shift in bytes): rotated left (three reversals); clobbers r0-r3
    a.label("c_pmrot")
    E(push_list, [4, 5, 6], lr=True)
    E(mov_reg, 4, 0)
    E(adds_reg, 5, 0, 1)                                                  # r5 = the end
    E(adds_reg, 6, 0, 2)                                                  # r6 = the cut
    E(cmp_imm, 2, 0)
    E(b_cond, "ro_x", "eq")
    E(mov_reg, 1, 6)
    E(bl, "c_pmrev")
    E(mov_reg, 0, 6)
    E(mov_reg, 1, 5)
    E(bl, "c_pmrev")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, "c_pmrev")
    a.label("ro_x")
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_pmfind(r0 = track) -> r0 = its pattern when both step stores hold it (else 0), r4 = the listener, r6 = ST1, r7 = ST2;
    #      clobbers r1-r3 (r4, r6, r7 are outputs: the caller saves them)
    a.label("c_pmfind")
    E(push_list, [5], lr=True)
    E(cmp_imm, 0, 7)
    E(b_cond, "pf_0", "hi")
    E(lsls_imm, 0, 0, 6)
    imm32(1, Q.PV0)
    E(adds_reg, 0, 0, 1)
    E(ldr_imm, 1, 0, 0)
    imm32(2, Q.PV_VT)
    E(cmp_reg, 1, 2)
    E(b_cond, "pf_0", "ne")
    E(ldr_imm, 0, 0, 0xC)
    E(ldr_imm, 6, 0, 0)
    E(ldr_imm, 7, 0, 4)
    E(ldr_imm, 0, 6, 0x14)
    E(ldr_imm, 4, 0, 0)
    E(ldr_imm, 1, 4, 0)
    imm32(2, Q.LIS_VT)
    E(cmp_reg, 1, 2)
    E(b_cond, "pf_0", "ne")
    E(ldr_imm, 1, 4, 0x1C)
    E(cmp_reg, 1, 6)
    E(b_cond, "pf_0", "ne")
    E(ldr_imm, 1, 4, 0x20)
    E(cmp_reg, 1, 7)
    E(b_cond, "pf_0", "ne")
    E(ldr_imm, 0, 4, 0x28)
    E(movs_imm, 1, 0)
    E(bl, PARAM_NEW)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, 7)
    E(b_cond, "pf_0", "hi")
    imm32(1, Q.PAT_SZ)
    E(muls, 0, 1)
    E(ldr_imm, 1, 4, 4)
    E(adds_reg, 5, 0, 1)                                                  # r5 = the pattern
    E(ldr_imm, 0, 6, 0x18)
    imm32(1, Q.LANES_OFF)
    E(adds_reg, 1, 1, 5)
    E(cmp_reg, 0, 1)
    E(b_cond, "pf_0", "ne")
    for st, m in ((6, Q.ST1_MAP), (7, Q.ST2_MAP)):
        E(mov_reg, 0, st)
        E(mov_reg, 1, 5)
        imm32(2, Q.packed(m, False))
        E(bl, L["c_qzst"])
        E(cmp_imm, 0, 0)
        E(b_cond, "pf_0", "ne")
    E(mov_reg, 0, 5)
    E(pop_list, [5], pc=True)
    a.label("pf_0")
    E(movs_imm, 0, 0)
    E(pop_list, [5], pc=True)

    # ---- c_pmnudge(r0 = track) -> r0 = 1 done, 0 refused (nothing written)
    a.label("c_pmnudge")
    E(push_list, [2, 3, 4, 5, 6, 7], lr=True)
    E(sub_sp_imm, 12)                                                     # sp + 0 the first step, + 4 n, + 8 the new last
    E(bl, "c_pmfind")
    E(cmp_imm, 0, 0)
    E(b_cond, "nf_0", "eq")
    E(mov_reg, 5, 0)                                                      # r5 = the pattern
    imm32(0, Q.SET_OFF)
    E(adds_reg, 0, 0, 5)
    E(ldrb_imm, 2, 0, 0)                                                  # the last step
    E(ldrb_imm, 1, 0, 1)                                                  # the first
    E(cmp_imm, 1, 31)
    E(b_cond, "nf_0", "hi")
    E(cmp_imm, 2, 31)
    E(b_cond, "nf_0", "hi")
    E(str_sp, 1, 0)
    E(movs_imm, 3, 32)
    E(cmp_imm, 1, 16)
    E(b_cond, "nf_n", "hs")
    E(cmp_imm, 2, 16)
    E(b_cond, "nf_n", "hs")
    E(movs_imm, 3, 16)
    a.label("nf_n")
    E(str_sp, 3, 4)
    E(subs_reg, 2, 2, 1)                                                  # the new last step
    E(b_cond, "nf_l", "pl")
    E(adds_reg, 2, 2, 3)
    a.label("nf_l")
    E(str_sp, 2, 8)
    E(mov_reg, 0, 5)                                                      # the steps
    E(lsls_imm, 1, 3, 3)
    E(ldr_sp, 2, 0)
    E(lsls_imm, 2, 2, 3)
    E(bl, "c_pmrot")
    if v2:                                                                # drumpat's step bytes too (one a step)
        E(mov_reg, 0, 5)
        E(adds_imm8, 0, 0xFF)
        E(adds_imm8, 0, 0x108 - 0xFF)
        E(ldr_sp, 1, 4)
        E(ldr_sp, 2, 0)
        E(bl, "c_pmrot")
    E(movs_imm, 4, 0)
    a.label("nf_a")                                                       # the lanes
    E(movs_imm, 0, 192)
    E(muls, 0, 4)
    E(adds_reg, 0, 0, 5)
    imm32(1, Q.LANES_OFF)
    E(adds_reg, 0, 0, 1)
    E(ldr_sp, 1, 4)
    E(movs_imm, 2, LANE_STEP)
    E(muls, 1, 2)
    E(ldr_sp, 3, 0)
    E(muls, 2, 3)
    E(bl, "c_pmrot")
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, LANES)
    E(b_cond, "nf_a", "lo")
    for st, m in ((6, Q.ST1_MAP), (7, Q.ST2_MAP)):                        # the step stores: both copies
        E(mov_reg, 0, st)
        E(mov_reg, 1, 5)
        imm32(2, Q.packed(m, True))
        E(bl, L["c_qzst"])
    E(ldr_imm, 0, 6, 0x14)                                                # the settings through ST3: first 0, the new last
    E(ldr_imm, 4, 0, 0)
    E(ldr_imm, 0, 4, 0x24)
    E(movs_imm, 1, 0)
    E(bl, PARAM_WPTR)
    E(ldr_sp, 1, 8)
    E(strb_imm, 1, 0, 0)
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 0, 1)
    E(ldr_imm, 0, 4, 0x24)
    E(bl, COMMIT)
    E(movs_imm, 0, 1)
    E(b, "nf_x")
    a.label("nf_0")
    E(movs_imm, 0, 0)
    a.label("nf_x")
    E(add_sp_imm, 12)
    E(pop_list, [2, 3, 4, 5, 6, 7], pc=True)

    # ---- c_pmtrk(r0 = a Pattern Settings view) -> r0 = its track, 0xFF: none; clobbers r1-r3
    a.label("c_pmtrk")
    E(ldr_imm, 1, 0, 0)
    imm32(2, PS_VT)
    E(cmp_reg, 1, 2)
    E(b_cond, "pt_0", "ne")
    imm32(1, PS0)
    E(movs_imm, 3, 0)
    a.label("pt_l")
    E(cmp_reg, 0, 1)
    E(b_cond, "pt_y", "eq")
    E(adds_imm8, 1, PS_SZ)
    E(adds_imm8, 3, 1)
    E(cmp_imm, 3, 8)
    E(b_cond, "pt_l", "lo")
    a.label("pt_0")
    E(movs_imm, 0, 0xFF)
    E(raw, h(0x4770))
    a.label("pt_y")
    E(mov_reg, 0, 3)
    E(raw, h(0x4770))

    # ---- c_pmpad (the Pattern Settings view's slot 0: view, pad, velocity): pad 26 = nudge
    a.label("c_pmpad")
    E(cmp_imm, 1, PAD_NUDGE)
    E(b_cond, "pp_f", "ne")
    E(push_list, [0, 1, 2, 3, 4], lr=True)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "pp_x", "eq")
    E(ldr_sp, 0, 0)
    E(bl, "c_pmtrk")
    E(bl, "c_pmnudge")
    a.label("pp_x")
    E(pop_list, [0, 1, 2, 3, 4], pc=True)
    a.label("pp_f")
    E(b_w, prev["pad"])

    # ---- c_pmled (the view's slot 7: view): the stock's, then pad 26 orange; the stock's r0 returned
    a.label("c_pmled")
    E(push_list, [0, 1, 4], lr=True)
    E(bl, prev["led"])
    E(str_sp, 0, 4)
    E(ldr_sp, 1, 0)
    E(ldr_imm, 1, 1, 4)
    E(ldr_imm, 1, 1, 0)
    E(movs_imm, 2, COL_NUDGE)
    E(movs_imm, 3, 2 * PAD_NUDGE)
    E(strh_reg, 2, 1, 3)
    E(ldr_sp, 0, 4)
    E(add_sp_imm, 8)
    E(pop_list, [4], pc=True)
    return a.assemble()


def install(img, report, base_addr, v2=False):
    """Append the code; slots 0 and 7 of the Pattern Settings views' vtable.  v2 (RH11): the nudge rotates drumpat's step bytes too."""
    import rhbuild
    BASE = rhbuild.BASE
    lab = lambda sec, n: int(report[sec]["labels"][n], 16)
    L = dict(c_ciok=lab("countin", "c_ciok"), c_qzst=lab("quant", "c_qzst"))
    old = [struct.unpack_from("<I", img, PS_VT + 4 * k - BASE)[0] for k in (0, 7)]
    prev = dict(pad=old[0] & ~1, led=old[1] & ~1)
    code, labels = arm_code(base_addr, L, prev, v2)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch_word(img, PS_VT, old[0], labels["c_pmpad"] | 1)
    rhbuild.patch_word(img, PS_VT + 0x1C, old[1], labels["c_pmled"] | 1)
    report["playmode"] = dict(ps_slots=[hex(PS_VT), hex(PS_VT + 0x1C)], prev={k: hex(v) for k, v in prev.items()},
                              labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
