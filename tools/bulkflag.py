"""The PCM upload's bulk interval as a flag, for sdyield (MIT; RH101; the user, 2026-11-14: RH66's fix «sdyield OPT sdbulk» accepted).

What RH66's tools/dspgate.py found in the stock: a PCM upload to core 0 (the pack's load 0x08053E24, a single sample 0x080460B8 -> 0x08053E8C,
the SysEx / USB one 0x080536D2) puts core 0's host port in bulk mode with 0x0803153C(core) and leaves it with 0x0803157E(core); between them the
uploader reads the card (a job for the storage task) with core 0's chip select low and without the DSP service's lock.  sdyield (RD29) makes a
long card wait yield the CPU after 2 ms: inside that interval another task could then write the DSP and its words would go into the PCM stream.
With OPT sdbulk sdyield does not yield inside an interval (the stock's spin, as before RD29); outside one it yields as ever.

Here only what sdbulk needs: the heads of 0x0803153C / 0x0803157E set and clear a byte (and count the intervals); dspgate's dropping of our own
writes is not brought in (OPT bulkflag: sdyield reads this module's byte).  RAM rhstate OFF2 "bulkflag": + 0 in an interval, + 4 the intervals.
The address is written without c_rst (those bytes are never allocated; c_rst zeroes them at the first LED frame of a boot).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import Asm, adds_imm8, b_w, ldr_imm, mov_reg, movs_imm, movt, movw, push_list, str_imm, strb_imm  # noqa: E402
import dspgate as DG  # noqa: E402
import rhstate  # noqa: E402

O = rhstate.OFF2["bulkflag"][0]
BLOCK = rhstate.ST2 + O
R_IN, R_N = 0, 4
ENTER, LEAVE, HEAD = DG.ENTER, DG.LEAVE, DG.BULK_HEAD


def arm_code(base):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- c_bfon / c_bfoff (the heads of 0x0803153C / 0x0803157E: r0 = the core; r1, r2 free in both): the flag, then the stock's own
    a.label("c_bfon")
    imm32(1, BLOCK)
    E(movs_imm, 2, 1)
    E(strb_imm, 2, 1, R_IN)
    E(ldr_imm, 2, 1, R_N)
    E(adds_imm8, 2, 1)
    E(str_imm, 2, 1, R_N)
    E(push_list, [3, 4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(b_w, ENTER + 4)
    a.label("c_bfoff")
    imm32(1, BLOCK)
    E(movs_imm, 2, 0)
    E(strb_imm, 2, 1, R_IN)
    E(push_list, [3, 4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(b_w, LEAVE + 4)
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; the heads of the bulk mode's two functions.  Not with dspgate (the same heads)."""
    import rhbuild
    BASE = rhbuild.BASE
    assert "dspgate" not in report and rhbuild.OPT.get("bulkflag") and rhbuild.OPT.get("sdbulk")
    code, labels = arm_code(base_addr)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    for site, lb in ((ENTER, "c_bfon"), (LEAVE, "c_bfoff")):
        rhbuild.patch(img, site, HEAD, b_w(site, labels[lb]))
    report["bulkflag"] = dict(block=hex(BLOCK), labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
