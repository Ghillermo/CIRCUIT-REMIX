"""Clear + knob = back to the default where the stock has none (MIT; CIRCUIT-HACKS' «Clear + knob = valor por defecto» (A4), for the Circuit Rhythm
5706): the FX view and the Sidechain view.

The stock of the Rhythm (emulated): Clear held + a sustained knob turn resets a knob in the track views and the Mixer; in the FX view (the
sends) and in the Sidechain view (whose knobs RH12 gives to the side-chain and the master compressor) Clear + a knob does nothing.
Ours (Clear held, without Shift, any turn of the knob):
  * the FX view (0x2004DAA0): the knob's send of the page shown (reverb 0x12 / delay 0x13 of the group 0x10 + t) to 0;
  * the Sidechain view: K1-K4 = the chosen track's side-chain back to its preset (the table 0x20003774, 4 values a preset, as the stock's listener
    0x08036DF4 writes them; RH12's bit of the track cleared); K6-K8 = the master compressor back to the factory values (soft clip on, attack and
    release 0; RH12's compressor flag cleared).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b, b_cond, b_w, bics_reg, bl, cmp_imm, cmp_reg, h, ldr_imm, ldrb_imm, ldrb_reg, lsls_imm,  # noqa: E402
                   lsls_reg, mov_reg, movs_imm, movt, movw, pop_list, push_list, raw, strb_imm, strb_w, tst_reg)
import countin as CI  # noqa: E402
import fxkeys as F  # noqa: E402
import sckn as SK  # noqa: E402

CTRL = CI.CTRL
BIT_CLEAR = 23
SC_STORES, PRESET_TAB = 0x20042354 + 0x10, 0x20003774
COMP_DEFAULT = (1, 0, 0)                                  # soft clip, attack, release (the dump's, a factory project's)
INV = SK.INV


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
        n = f"_k{zc[0]}"
        E(b_cond, n, INV[cond])
        E(b, target)
        a.label(n)

    t_cdef = base                                                         # the compressor's factory values, then their indices
    E(raw, bytes(COMP_DEFAULT) + bytes(SK.COMP_IDX) + bytes(2))

    # ---- c_ckclear() -> r0 = 1 when Clear is held and Shift is not (the controller the dump's); clobbers r1-r3
    a.label("c_ckclear")
    E(push_list, [4], lr=True)
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "kc_x", "eq")
    E(bl, L["c_cishift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "kc_0", "ne")
    imm32(0, CTRL)
    E(raw, h(0xF8D0) + h(0x10A0))                                         # ldr.w r1, [r0, #0xa0]
    E(movs_imm, 0, 1)
    E(lsls_imm, 0, 0, BIT_CLEAR)
    E(tst_reg, 1, 0)
    E(b_cond, "kc_0", "eq")
    E(movs_imm, 0, 1)
    E(pop_list, [4], pc=True)
    a.label("kc_0")
    E(movs_imm, 0, 0)
    a.label("kc_x")
    E(pop_list, [4], pc=True)

    # ---- c_ckset(r1 = group, r2 = index, r3 = value): the stock's setter; clobbers r0-r3, r12
    a.label("c_ckset")
    imm32(0, SK.SET_OBJ)
    E(b_w, SK.SETTER)

    # ---- c_ckfx (the FX view's slot 4: view, knob, delta): Clear + knob = the page's send to 0
    a.label("c_ckfx")
    E(cmp_imm, 1, 8)
    bc("kf_f", "hs")
    E(push_list, [0, 1, 2, 4], lr=True)
    E(bl, "c_ckclear")
    E(cmp_imm, 0, 0)
    bc("kf_p", "eq")
    E(bl, L["c_fxpage"])
    E(movs_imm, 2, F.IDX_REV_SEND)
    E(cmp_imm, 0, F.PAGE_DELAY)
    E(b_cond, "kf_s", "ne")
    E(movs_imm, 2, F.IDX_DEL_SEND)
    a.label("kf_s")
    E(raw, h(0x9901))                                                     # ldr r1, [sp, #4]: the knob = the track
    E(adds_imm8, 1, F.GRP_TRACK)
    E(movs_imm, 3, 0)
    E(bl, "c_ckset")
    E(pop_list, [0, 1, 2, 4], pc=True)
    a.label("kf_p")
    E(raw, popw([0, 1, 2, 4], lr=True))
    a.label("kf_f")
    E(b_w, prev["fxknob"])

    # ---- c_cksc (the container's slot 4: view, knob, delta): in the Sidechain view, Clear + K1-K4 / K6-K8 = the preset's values / the factory's
    a.label("c_cksc")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    imm32(3, SK.O_MODE)
    E(raw, h(0x5CC3))                                                     # ldrb r3, [r0, r3]
    E(cmp_imm, 3, SK.MODE_SC)
    bc("ks_p", "ne")
    E(cmp_imm, 1, 8)
    bc("ks_p", "hs")
    E(cmp_imm, 1, 4)
    bc("ks_p", "eq")
    E(mov_reg, 5, 1)                                                      # r5 = the knob
    E(bl, "c_ckclear")
    E(cmp_imm, 0, 0)
    bc("ks_p", "eq")
    E(bl, L["c_skblk"])
    E(mov_reg, 7, 0)                                                      # r7 = RH12's block (or 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "ks_v", "eq")
    E(bl, L["c_skok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ks_v", "ne")
    E(movs_imm, 7, 0)
    a.label("ks_v")
    E(cmp_imm, 5, 4)
    bc("ks_c", "hi")
    imm32(0, SK.SC_OBJ)                                                   # K1-K4: the chosen track's preset
    E(ldr_imm, 0, 0, SK.O_SRC)
    E(ldrb_imm, 4, 0, SK.SRC_TRACK)
    E(cmp_imm, 4, 8)
    bc("ks_x", "hs")
    imm32(0, SC_STORES)
    E(lsls_imm, 1, 4, 2)
    E(raw, h(0x5840))                                                     # ldr r0, [r0, r1]: the track's preset store
    E(movs_imm, 1, 0)
    E(bl, L["c_cinew"])
    E(lsls_imm, 0, 0, 2)
    imm32(6, PRESET_TAB)
    E(adds_reg, 6, 6, 0)                                                  # r6 = the preset's four values
    E(movs_imm, 5, 0)
    a.label("ks_l")
    E(ldrb_reg, 3, 6, 5)
    E(mov_reg, 2, 5)
    E(adds_imm8, 2, SK.IDX_SC0)
    E(mov_reg, 1, 4)
    E(adds_imm8, 1, SK.GRP_TRACK)
    E(bl, "c_ckset")
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, 4)
    E(b_cond, "ks_l", "lo")
    E(cmp_imm, 7, 0)
    bc("ks_x", "eq")
    E(ldrb_imm, 0, 7, SK.B_BITS)
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(bics_reg, 0, 1)
    E(strb_imm, 0, 7, SK.B_BITS)
    E(b, "ks_fix")
    a.label("ks_c")                                                       # K6-K8: the compressor's factory values
    E(movs_imm, 5, 0)
    a.label("ks_cl")
    imm32(0, t_cdef)
    E(ldrb_reg, 3, 0, 5)                                                  # the value
    E(adds_reg, 1, 0, 5)
    E(ldrb_imm, 2, 1, 3)                                                  # its index
    E(movs_imm, 1, SK.GRP_MASTER)
    E(bl, "c_ckset")
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, 3)
    E(b_cond, "ks_cl", "lo")
    E(cmp_imm, 7, 0)
    bc("ks_x", "eq")
    E(movs_imm, 0, 0)
    E(strb_w, 0, 7, SK.B_COMP)
    a.label("ks_fix")
    E(mov_reg, 0, 7)
    E(bl, L["c_skfix"])
    a.label("ks_x")
    E(raw, h(0xB003))                                                     # add sp, #12
    E(pop_list, [4, 5, 6, 7], pc=True)
    a.label("ks_p")
    E(raw, popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    E(b_w, prev["cknob"])
    return a.assemble()


def install(img, report, base_addr):
    """Append the code; slot 4 of the FX view's vtable and of the track views' container (in front of fxkeys' / sckn's)."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]
    lab = lambda sec, n: int(report[sec]["labels"][n], 16)
    L = dict(c_ciok=lab("countin", "c_ciok"), c_cishift=lab("countin", "c_cishift"), c_cinew=lab("countin", "c_cinew"),
             c_fxpage=lab("fxkeys", "c_fxpage"), c_skblk=lab("sckn", "c_skblk"), c_skok=lab("sckn", "c_skok"), c_skfix=lab("sckn", "c_skfix"))
    prev = dict(fxknob=u(F.SLOT_KNOB) & ~1, cknob=u(SK.SLOT_KNOB) & ~1)
    code, labels = arm_code(base_addr, L, prev)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch_word(img, F.SLOT_KNOB, prev["fxknob"] | 1, labels["c_ckfx"] | 1)
    rhbuild.patch_word(img, SK.SLOT_KNOB, prev["cknob"] | 1, labels["c_cksc"] | 1)
    report["clrknob"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
