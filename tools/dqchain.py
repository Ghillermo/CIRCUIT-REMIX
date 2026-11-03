"""drumpat's frequency per pattern, also in a chain (MIT; RH60, the user, 2026-10-29: «each n steps plays anyway and makes notes shorter in
the iterations when its not suppossed to play»).

Seen in emulation, the real sequencer running on the RAM dump (its project chains the patterns of every track):
  * the players' slot 2 gets the pattern that plays; drumpat (RH09) counted a track's passes from the first step of its pattern and started
    again at 0 whenever the pattern changed: in a chain every pass was pass 0, so a step "one in n" played on every pass;
  * the players' slot 4 (0x0804B060: player, pattern, step), called at each step's start before slot 2's micro step 0, sets the step's
    sample (its flip, else the selected one) through [player + 0x58] slot 0 for a step with a hit: on a pass where drumpat keeps the hit
    from the stock that still happened, and loading the sample cuts the note still sounding.
Ours, a head of slot 4 (drumpat unchanged): in a marked project, at the first step of a pattern the pass begins: its count for that track and
that pattern (OFF2 "dqchain" + 8 t + p, mod 240: exact for n = 1-6 and 8; n = 7 once every 240 passes) goes into drumpat's state as the pass
before (its slot 2 adds one there: [state + 2] = pattern + 1, so it never starts again at 0); a step with a frequency n > 1 off its pass =
the stock's slot 4 skipped (no sample loaded, nothing cut).  A track's counts start again after the transport stops (drumpat clears its
state then: [state + 2] = 0 at the next first step).

RH61 (last; the user, 2026-10-30: «1 in N: make the playing step the last one»): a step "one in n" plays on the last of its n passes (the
n-th, the 2n-th...).  drumpat's test stays pass % n = 0: it gets this pattern's count + 1 as its pass.  A pass that starts in the middle of
the pattern after a stop (Shift + Play), with no count yet, is the first: drumpat's pass 1, or it would see 0 and play.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b, b_cond, b_w, bl, cmp_imm, cmp_reg, ldr_imm, ldr_sp, ldrb_imm, lsls_imm, lsrs_imm,  # noqa: E402
                   mov_reg, movs_imm, movt, movw, muls, pop_list, push_list, raw, strb_imm, subs_imm8)
import drumpat as DQ  # noqa: E402
import rhstate  # noqa: E402

O, O_LEN = rhstate.OFF2["dqchain"]
MOD, NPAT = 240, 8
assert O_LEN == 8 * NPAT
SLOT4 = DQ.DP_VT + 0x10                                   # the players' slot 4 (0x0804B060 in the stock)
FIRST_OFF = DQ.FIRST_OFF


def model_passes(patterns):
    """the pass each pattern of a track gets, for the patterns played in order (from a stop)"""
    cnt, out = [0] * NPAT, []
    for p in patterns:
        out.append(cnt[p])
        cnt[p] = (cnt[p] + 1) % MOD
    return out


def model_plays(byte, pass_, last=False):
    """drumpat's byte of a step: does it play on this pass (its frequency); (last, RH61) on the last of its n passes"""
    n = ((byte >> 3) & 7) + 1
    return (pass_ + 1 if last else pass_) % n == 0


def arm_code(base, L, prev, last=False):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_dcs4 (the players' slot 4: player, pattern, step)
    a.label("c_dcs4")
    E(push_list, [0, 1, 2, 3, 4, 5, 6, 7], lr=True)                       # sp + 0 player, + 4 pattern, + 8 step
    E(mov_reg, 4, 0)
    E(ldr_imm, 0, 4, 0)
    imm32(1, DQ.DP_VT)
    E(cmp_reg, 0, 1)
    E(b_cond, "s4_s", "ne")
    imm32(1, DQ.DP0)
    E(raw, DQ.h(0x1A60))                                                  # subs r0, r4, r1
    imm32(1, DQ.DP_SZ)
    E(raw, DQ.udiv(6, 0, 1))                                              # r6 = the track
    E(cmp_imm, 6, 7)
    E(b_cond, "s4_s", "hi")
    E(ldr_sp, 1, 4)
    E(cmp_imm, 1, NPAT - 1)
    E(b_cond, "s4_s", "hi")
    imm32(0, DQ.PAT_SZ)
    E(muls, 0, 1)
    E(ldr_imm, 5, 4, 0x50)
    E(adds_reg, 5, 5, 0)                                                  # r5 = the pattern's base
    E(mov_reg, 0, 5)
    E(ldr_sp, 1, 8)
    E(bl, L["c_dqbyte"])                                                  # 0 in a project not marked
    E(push_list, [0])                                                     # (the byte: sp + 0; the frame one word up)
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "s4_p", "eq")
    E(movs_imm, 1, 6)
    E(muls, 1, 6)
    E(adds_reg, 0, 0, 1)
    E(adds_imm8, 0, DQ.O_PLAY)
    E(mov_reg, 7, 0)                                                      # r7 = drumpat's state of the track
    E(bl, L["c_dqon"])
    E(cmp_imm, 0, 0)
    E(b_cond, "s4_p", "eq")
    # a pass begins: the first step of the pattern
    E(ldr_sp, 2, 4 + 8)
    imm32(1, FIRST_OFF)
    E(raw, DQ.h(0x5C68))                                                  # ldrb r0, [r5, r1]
    E(cmp_reg, 0, 2)
    E(b_cond, "s4_f", "ne")
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "s4_f", "eq")
    E(movw, 1, O)
    E(adds_reg, 0, 0, 1)
    E(lsls_imm, 1, 6, 3)
    E(adds_reg, 0, 0, 1)                                                  # r0 = the track's counts
    E(ldrb_imm, 1, 7, 2)
    E(cmp_imm, 1, 0)
    E(b_cond, "s4_c", "ne")
    E(movs_imm, 1, 0)                                                     # the first pass since a stop: its counts from 0
    for k in range(0, NPAT, 4):
        E(raw, DQ.h(0x6000 | (k // 4) << 6 | 0 << 3 | 1))                 # str r1, [r0, #k]
    a.label("s4_c")
    E(ldr_sp, 1, 4 + 4)
    E(adds_reg, 0, 0, 1)                                                  # r0 = this pattern's count
    E(ldrb_imm, 2, 0, 0)                                                  # r2 = this pass
    E(adds_imm8, 1, 1)
    E(strb_imm, 1, 7, 2)                                                  # drumpat's pattern + 1
    E(raw, DQ.h(0x1C53))                                                  # adds r3, r2, #1
    E(cmp_imm, 3, MOD)
    E(b_cond, "s4_m", "lo")
    E(movs_imm, 3, 0)
    a.label("s4_m")
    E(strb_imm, 3, 0, 0)
    if last:                                                              # drumpat's pass = this pass + 1 (its slot 2 adds the one)
        E(strb_imm, 2, 7, 0)
        E(movs_imm, 3, 0)
        E(strb_imm, 3, 7, 1)
        E(adds_imm8, 2, 1)
    else:
        E(raw, DQ.h(0x1E53))                                              # subs r3, r2, #1: the pass before, for drumpat's slot 2 to add one
        E(b_cond, "s4_w", "pl")
        imm32(3, 839)
        a.label("s4_w")
        E(strb_imm, 3, 7, 0)
        E(lsrs_imm, 3, 3, 8)
        E(strb_imm, 3, 7, 1)
    E(b, "s4_n")
    a.label("s4_f")
    E(ldrb_imm, 2, 7, 0)                                                  # r2 = the pass (drumpat's)
    E(ldrb_imm, 3, 7, 1)
    E(lsls_imm, 3, 3, 8)
    E(raw, DQ.h(0x431A))                                                  # orrs r2, r3
    if last:
        E(ldrb_imm, 3, 7, 2)
        E(cmp_imm, 3, 0)
        E(b_cond, "s4_n", "ne")
        E(movs_imm, 2, 1)                                                 # no pass begun since a stop: this one is the first
        E(strb_imm, 2, 7, 0)
    # off its pass: the stock's slot 4 skipped
    a.label("s4_n")
    E(ldr_sp, 0, 0)                                                       # the byte
    E(lsrs_imm, 1, 0, 3)
    E(movs_imm, 0, 7)
    E(raw, DQ.h(0x4001))                                                  # ands r1, r0
    E(cmp_imm, 1, 0)
    E(b_cond, "s4_p", "eq")
    E(adds_imm8, 1, 1)
    E(raw, DQ.udiv(0, 2, 1))
    E(raw, DQ.mls_(0, 0, 1, 2))                                           # r0 = pass % n
    E(cmp_imm, 0, 0)
    E(b_cond, "s4_p", "eq")
    E(pop_list, [0])
    E(pop_list, [0, 1, 2, 3, 4, 5, 6, 7], pc=True)
    a.label("s4_p")
    E(pop_list, [0])
    a.label("s4_s")
    E(raw, DQ.popw([0, 1, 2, 3, 4, 5, 6, 7], lr=True))
    E(b_w, prev["s4"])
    return a.assemble()


def install(img, report, base_addr, last=False):
    """The players' slot 4 (its first head).  Needs drumpat (its state, c_dqbyte, c_dqon) and rhstate ram2; not latdiag."""
    import struct
    import rhbuild
    BASE = rhbuild.BASE
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    assert "latdiag" not in report and "drumpat" in report
    L = dict(c_rst=lab("rhstate", "c_rst"), c_rram=lab("rhstate", "c_rram"), c_dqbyte=lab("drumpat", "c_dqbyte"), c_dqon=lab("drumpat", "c_dqon"))
    prev = dict(s4=struct.unpack_from("<I", img, SLOT4 - BASE)[0] & ~1)
    assert prev["s4"] == 0x0804B060, hex(prev["s4"])
    code_, labels = arm_code(base_addr, L, prev, last)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code_
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch_word(img, SLOT4, prev["s4"] | 1, labels["c_dcs4"] | 1)
    report["dqchain"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    if last:
        report["dqchain"]["last"] = True
    return labels, code_
