"""The 16-bit DSP read for the builds without rdiag (MIT; Alpha 0.04): rdiag's c_d16r (dsp=2) alone, for stereorec (core 0's split, RH43+)
and anything else that reads the DSP below 0x10000 from the LED task.  Without it the public builds (diag=False) had no c_d16r.

c_d16r (r0 = core, r1 = addr < 0x10000) -> r0 = word << 8: the stock's 16-bit read 0x08031268 under the DSP service's lock, as 0x080314D6
runs its own body; the cached write address is dropped (the DSP's pointer moved).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import Asm, add_sp_imm, adds_imm8, bl, mov_reg, movt, movw, pop_list, push_list, str_imm, str_sp, sub_sp_imm  # noqa: E402
from rdiag import DSP_LOCK, DSP_RD16, DSP_UNLOCK, DSP_WADDR  # noqa: E402


def arm_code(base):
    a = Asm(base)
    E = a.emit
    a.label("c_d16r")
    E(push_list, [4, 5, 6], lr=True); E(sub_sp_imm, 8)
    E(mov_reg, 4, 0); E(mov_reg, 5, 1)
    E(movw, 6, DSP_WADDR & 0xFFFF); E(movt, 6, DSP_WADDR >> 16)
    E(mov_reg, 0, 6); E(adds_imm8, 0, 4); E(str_sp, 0, 0); E(mov_reg, 1, 0)
    E(bl, DSP_LOCK)
    E(mov_reg, 0, 4); E(mov_reg, 1, 5); E(bl, DSP_RD16); E(mov_reg, 5, 0)
    E(movw, 0, 0xFFFF); E(str_imm, 0, 6, 0)
    E(mov_reg, 0, 13); E(bl, DSP_UNLOCK)
    E(mov_reg, 0, 5); E(add_sp_imm, 8); E(pop_list, [4, 5, 6], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    import rhbuild
    assert "rdiag" not in report, "dsprd is for the builds without rdiag (rdiag dsp=2 has its own c_d16r)"
    code, labels = arm_code(base_addr)
    img += bytes([0xFF]) * (base_addr - rhbuild.BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    report["dsprd"] = dict(labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
