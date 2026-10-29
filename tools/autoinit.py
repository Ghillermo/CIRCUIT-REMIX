"""The automation of CIRCUIT-HACKS' RC4.01 / Beta 3.46-3.47 on the Rhythm (MIT; RH58; CIRCUIT-HACKS/docs/export/REMIX_AUTOMATION.md, the
user, 2026-10-29: «Port it» (the snapshot too); the voice back to Project init: «pad 8 on pages (doubletap/hold) view, red color»).  On top of
RH46's autorel (the marks, the playback at a marked step) with its `init` option (a marked step = Project init).

Project init of a track = its parameters as the project was loaded or last saved: trkcopy's photo (rhstate OFF2 "trkphoto": "TS", then 26
bytes a track: the 25 parameters of the group 0x10 + t, the selected sample); ours takes it again after each save (the two save calls of
mfsess, in front of whatever is there).  The knobs are written through the parameter router 0x20043740 (slinkofs.ROUTER: the view's store
and the group, as a turn), the rest through the group's setter.

The Velocity view (the container's mode 2), its step pads (the step views' slot 0 / 1, in front of autorel's):
  * Shift held: a step with knob automation (a value <> 0xFF in lanes 0-7, any of its 6 micro steps) and not marked = yellow (0x2F); the
    marked ones red (autorel keep's), the others the view's own;
  * Shift + a yellow step = its preview, no mark: for each knob lane with a value on that step, the first micro step's value goes to the knob
    and the sound; those knobs' LEDs yellow, the brightness = the value; another yellow step plays its values; each knob's value before its
    first change is kept once; Shift let go (or the view left): the kept values back, the LEDs as before;
  * Shift + any other step = autorel's mark (marks / unmarks);
  * Clear held + a step (with or without Shift) = that step's knob automation erased (lanes 0-7, its 6 micro steps); its notes, its mark and
    the mixer's lanes stay; the press and its release never reach the stock (whose Clear + step erases the notes).
The track view (mode 0), Record held + a step pad = the snapshot: each knob not at Project init goes into that step's lane (all 6 micro steps);
the mixer's lanes untouched; the recording state is put back as it was before Record was pressed when Record is let go.
The track menu (granpage's, open: its track), pad 8 (red 0x53) = that track's voice back to Project init: K1-K8, their low bits (14 / 15),
the parameters 1-5 and its selected sample (not the mixer's level, pan, sends or side-chain).
RAM: rhstate OFF2 "autoinit": + 0 the step pads swallowed (bit), + 4 the controller's pads swallowed (bit), + 8 the preview (on, track, the
kept knobs, the knobs shown), + 12 the kept values, + 20 the shown values, + 28 Record (held: the recording before + 1, a snapshot made),
+ 30 (latch) the automation view latched.

RH59 (CIRCUIT-HACKS' SC49.5 / SC49.6; the user, 2026-10-29: «Record + step cue, Latched automation view»):
  * cue: the track view, a step pad swallowed by a snapshot (its bit in + 0) = yellow until let go;
  * latch: Velocity pressed with the Velocity view on the screen, without Shift = the automation view latched / unlatched (as if Shift were
    held: ours and autorel's, whose c_arvel's Shift goes through c_aiauto); leaving the view = off.  The press goes on to the stock, whose
    Velocity again only sets the view again (its mode setter 0x0804D6B6: the step views' hold flag; the mode stays 2); Shift + Velocity = the
    stock's fixed velocity, the latch untouched.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm3, adds_imm8, adds_reg, b, b_cond, b_w, bics_reg, bl, blx_reg, cmp_imm, cmp_reg, h, ldr_imm, ldrb_imm,  # noqa: E402
                   ldrb_w, lsls_imm, lsls_reg, lsrs_imm, lsrs_reg, mov_reg, movs_imm, movt, movw, muls, orrs_reg, pop_list, push_list, raw,
                   str_imm, strb_imm, strh_imm, strh_w_imm, subs_imm8, subs_reg, tst_reg)
import autorel as AR  # noqa: E402
import countin as CI  # noqa: E402
import granpage as GP  # noqa: E402
import mfsess as MF  # noqa: E402
import rhstate  # noqa: E402
import slinkofs as SO  # noqa: E402
import stockplus as SP  # noqa: E402

O, O_LEN = rhstate.OFF2["autoinit"]
R_SWS, R_SWP, R_PV, R_KEPT, R_SHOWN, R_REC = 0, 4, 8, 12, 20, 28
PV_ON, PV_TRK, PV_KMASK, PV_SMASK = 0, 1, 2, 3
REC_SAVED, REC_USED = 0, 1                                # + 0: the recording before + 1 (0 = Record not held by us), + 1 a snapshot made
assert R_REC + 2 <= O_LEN
R_LATCH = 30                                              # (latch) the automation view latched
assert R_LATCH < O_LEN
ID_VEL = 10
TP_O = rhstate.OFF2["trkphoto"][0]
PH_REC = 26                                               # a track's photo: 25 parameters, the selected sample
NK, NMS, LANE_SZ = 8, 6, 192
KNOB0 = 6
YELLOW, RED = 0x2F, 0x53
PAD_INIT = 7                                              # the track menu's pad 8
ID_REC, BIT_CLEAR, BIT_REC = 16, SP.BIT_CLEAR, 16
MODE_MAIN, MODE_VEL = 0, AR.MODE_VEL
TRANSPORT, P_REC = 0x200122B0, 1
BREL_HEAD = "push {r3, r4, r5, lr}|mov r4, r0"                # the stock's button release (no hook of ours there before RH58)
WPTR, COMMIT = 0x0803FD26, 0x0803FBEC
O_KB = rhstate.OFF["kbright"][0]
K_MASK, K_VAL, K_CODE = SP.K_MASK, SP.K_VAL, SP.K_CODE
INIT_IDX = (1, 2, 3, 4, 5, 14, 15)                        # besides the knobs (6..13, through the router) and the sample


def model_has_auto(lanes, step):
    """lanes = the pattern's 12 x 192 bytes: True when one of the knob lanes has a value on that step"""
    return any(lanes[LANE_SZ * k + NMS * step + m] != 0xFF for k in range(NK) for m in range(NMS))


def model_preview(lanes, step):
    """{knob: value} the preview of a step: each knob lane's first micro step with a value"""
    out = {}
    for k in range(NK):
        for m in range(NMS):
            v = lanes[LANE_SZ * k + NMS * step + m]
            if v != 0xFF:
                out[k] = v
                break
    return out


def _is_bl(img, x, rhbuild):
    try:
        rhbuild.bl_target(img, x)
        return True
    except AssertionError:
        return False


def arm_code(base, L, prev, cue=False, latch=False):
    a = Asm(base)
    E = a.emit
    zc = [0]

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    def bc(target, cond):
        zc[0] += 1
        n = f"_e{zc[0]}"
        E(b_cond, n, SP.INV[cond])
        E(b, target)
        a.label(n)

    # ---- c_airam() -> r0 = our RAM (0 without it); clobbers r1-r3
    a.label("c_airam")
    E(push_list, [4], lr=True)
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ir_x", "eq")
    E(movw, 1, O)
    E(adds_reg, 0, 0, 1)
    a.label("ir_x")
    E(pop_list, [4], pc=True)

    # ---- c_aiph(r0 = track) -> r0 = its photo (26 bytes), 0 without a valid one; clobbers r1-r3
    a.label("c_aiph")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, L["c_rram"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ph_x", "eq")
    E(movw, 1, TP_O)
    E(adds_reg, 0, 0, 1)
    E(ldrb_imm, 1, 0, 0)
    E(cmp_imm, 1, ord("T"))
    E(b_cond, "ph_0", "ne")
    E(ldrb_imm, 1, 0, 1)
    E(cmp_imm, 1, ord("S"))
    E(b_cond, "ph_0", "ne")
    E(adds_imm8, 0, 2)
    E(movs_imm, 1, PH_REC)
    E(muls, 1, 4)
    E(adds_reg, 0, 0, 1)
    E(pop_list, [4], pc=True)
    a.label("ph_0")
    E(movs_imm, 0, 0)
    a.label("ph_x")
    E(pop_list, [4], pc=True)

    # ---- c_aiknob(r0 = track, r1 = knob 0..7, r2 = value): through the router; clobbers r0-r3, r12
    a.label("c_aiknob")
    E(push_list, [4], lr=True)
    E(lsls_imm, 0, 0, 4)
    E(adds_reg, 1, 0, 1)
    imm32(0, SO.ROUTER)
    E(ldr_imm, 3, 0, 0)
    E(ldr_imm, 3, 3, 0)
    E(blx_reg, 3)
    E(pop_list, [4], pc=True)

    # ---- c_ailanes(r0 = a step view) -> r0 = its pattern's lanes (the steps + 0x128); clobbers r1
    a.label("c_ailanes")
    E(push_list, [4], lr=True)
    E(bl, L["c_arsteps"])
    E(movw, 1, AR.LANES_OFF)
    E(adds_reg, 0, 0, 1)
    E(pop_list, [4], pc=True)

    # ---- c_aihas(r0 = lanes, r1 = step) -> r0 = 1 when a knob lane has a value on the step; clobbers r1-r3
    a.label("c_aihas")
    E(push_list, [4, 5], lr=True)
    E(movs_imm, 2, NMS)
    E(muls, 2, 1)
    E(adds_reg, 0, 0, 2)                                                  # the step's first byte in lane 0
    E(movs_imm, 4, 0)
    a.label("hs_k")
    E(movs_imm, 5, 0)
    a.label("hs_m")
    E(raw, AR.ldrb_reg(3, 0, 5))
    E(cmp_imm, 3, 0xFF)
    E(b_cond, "hs_1", "ne")
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, NMS)
    E(b_cond, "hs_m", "lo")
    E(adds_imm8, 0, 0xC0)                                                 # the next lane (192)
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, NK)
    E(b_cond, "hs_k", "lo")
    E(movs_imm, 0, 0)
    E(pop_list, [4, 5], pc=True)
    a.label("hs_1")
    E(movs_imm, 0, 1)
    E(pop_list, [4, 5], pc=True)

    # ---- c_aimode() -> r0 = the container's mode while it is on the screen (not Sidechain), else 0xFF; clobbers r1-r3
    a.label("c_aimode")
    E(push_list, [4], lr=True)
    E(bl, L["c_spview"])
    E(cmp_imm, 0, 8)
    E(b_cond, "md_n", "hs")
    imm32(1, SP.CONT + 0x264)
    E(ldrb_imm, 0, 1, 0)
    E(pop_list, [4], pc=True)
    a.label("md_n")
    E(movs_imm, 0, 0xFF)
    E(pop_list, [4], pc=True)

    # ---- c_aiend(): the preview, if any, ended: the kept values back; clobbers r0-r3
    a.label("c_aiend")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(bl, "c_airam")
    E(cmp_imm, 0, 0)
    E(b_cond, "en_x", "eq")
    E(mov_reg, 4, 0)
    E(ldrb_imm, 0, 4, R_PV + PV_ON)
    E(cmp_imm, 0, 0)
    E(b_cond, "en_x", "eq")
    E(ldrb_imm, 6, 4, R_PV + PV_TRK)
    E(ldrb_imm, 7, 4, R_PV + PV_KMASK)
    E(movs_imm, 5, 0)
    a.label("en_l")
    E(mov_reg, 0, 7)
    E(lsrs_reg, 0, 5)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "en_n", "eq")
    E(adds_reg, 2, 4, 5)
    E(ldrb_imm, 2, 2, R_KEPT)
    E(mov_reg, 0, 6)
    E(mov_reg, 1, 5)
    E(bl, "c_aiknob")
    a.label("en_n")
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, NK)
    E(b_cond, "en_l", "lo")
    E(movs_imm, 0, 0)
    E(str_imm, 0, 4, R_PV)
    a.label("en_x")
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_aiprev(r0 = track, r1 = lanes, r2 = step): the step's knob values to the knobs (the first change of each kept); clobbers r0-r3
    a.label("c_aiprev")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 6, 0)                                                      # r6 = the track
    E(movs_imm, 3, NMS)
    E(muls, 3, 2)
    E(adds_reg, 7, 1, 3)                                                  # r7 = the step in lane 0
    E(bl, "c_airam")
    E(cmp_imm, 0, 0)
    bc("pv_x", "eq")
    E(mov_reg, 4, 0)                                                      # r4 = our RAM
    E(ldrb_imm, 0, 4, R_PV + PV_ON)
    E(cmp_imm, 0, 0)
    E(b_cond, "pv_o", "eq")
    E(ldrb_imm, 0, 4, R_PV + PV_TRK)
    E(cmp_reg, 0, 6)
    E(b_cond, "pv_k", "eq")
    E(bl, "c_aiend")                                                      # another track's: ended first
    a.label("pv_o")
    E(movs_imm, 0, 0)
    E(str_imm, 0, 4, R_PV)
    E(movs_imm, 0, 1)
    E(strb_imm, 0, 4, R_PV + PV_ON)
    E(strb_imm, 6, 4, R_PV + PV_TRK)
    a.label("pv_k")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 4, R_PV + PV_SMASK)
    E(movs_imm, 5, 0)
    a.label("pv_l")
    E(movs_imm, 1, 0)
    a.label("pv_m")                                                       # the first micro step with a value
    E(raw, AR.ldrb_reg(2, 7, 1))
    E(cmp_imm, 2, 0xFF)
    E(b_cond, "pv_v", "ne")
    E(adds_imm8, 1, 1)
    E(cmp_imm, 1, NMS)
    E(b_cond, "pv_m", "lo")
    E(b, "pv_n")
    a.label("pv_v")
    E(adds_reg, 0, 4, 5)
    E(strb_imm, 2, 0, R_SHOWN)
    E(ldrb_imm, 0, 4, R_PV + PV_SMASK)
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 5)
    E(orrs_reg, 0, 1)
    E(strb_imm, 0, 4, R_PV + PV_SMASK)
    E(ldrb_imm, 0, 4, R_PV + PV_KMASK)
    E(tst_reg, 0, 1)
    E(b_cond, "pv_w", "ne")
    E(orrs_reg, 0, 1)                                                     # its value before: kept once
    E(strb_imm, 0, 4, R_PV + PV_KMASK)
    E(push_list, [2])
    E(mov_reg, 0, 6)
    E(adds_imm3, 1, 5, KNOB0)
    E(bl, L["c_tcget"])
    E(adds_reg, 1, 4, 5)
    E(strb_imm, 0, 1, R_KEPT)
    E(pop_list, [2])
    a.label("pv_w")
    E(mov_reg, 0, 6)
    E(mov_reg, 1, 5)
    E(bl, "c_aiknob")
    a.label("pv_n")
    E(adds_imm8, 7, 0xC0)
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, NK)
    E(b_cond, "pv_l", "lo")
    a.label("pv_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)

    # ---- c_aiclr(r0 = lanes, r1 = step): the step's knob lanes erased (6 micro steps each); clobbers r0-r3
    a.label("c_aiclr")
    E(movs_imm, 2, NMS)
    E(muls, 2, 1)
    E(adds_reg, 0, 0, 2)
    E(movs_imm, 2, 0xFF)
    E(movs_imm, 3, NK)
    a.label("cl_k")
    for m in range(NMS):
        E(strb_imm, 2, 0, m)
    E(adds_imm8, 0, 0xC0)
    E(subs_imm8, 3, 1)
    E(b_cond, "cl_k", "ne")
    E(raw, h(0x4770))

    # ---- c_aisnap(r0 = track, r1 = lanes, r2 = step): each knob not at Project init into the step's lane; clobbers r0-r3
    a.label("c_aisnap")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 6, 0)
    E(movs_imm, 3, NMS)
    E(muls, 3, 2)
    E(adds_reg, 7, 1, 3)                                                  # r7 = the step in lane 0
    E(bl, "c_aiph")
    E(cmp_imm, 0, 0)
    bc("sn_x", "eq")
    E(mov_reg, 4, 0)                                                      # r4 = the track's photo
    E(movs_imm, 5, 0)
    a.label("sn_l")
    E(mov_reg, 0, 6)
    E(adds_imm3, 1, 5, KNOB0)
    E(bl, L["c_tcget"])
    E(adds_reg, 1, 4, 5)
    E(ldrb_imm, 1, 1, KNOB0)
    E(cmp_reg, 0, 1)
    E(b_cond, "sn_n", "eq")
    for m in range(NMS):
        E(strb_imm, 0, 7, m)
    a.label("sn_n")
    E(adds_imm8, 7, 0xC0)
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, NK)
    E(b_cond, "sn_l", "lo")
    E(bl, "c_airam")                                                      # the recording put back when Record is let go
    E(cmp_imm, 0, 0)
    E(b_cond, "sn_x", "eq")
    E(movs_imm, 1, 1)
    E(strb_imm, 1, 0, R_REC + REC_USED)
    a.label("sn_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)

    # ---- c_aiswal(r0 = pad, r1 = the mask's offset): its release to swallow; clobbers r0-r3
    a.label("c_aiswal")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(bl, "c_airam")
    E(cmp_imm, 0, 0)
    E(b_cond, "aw_x", "eq")
    E(adds_reg, 0, 0, 5)
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(ldr_imm, 2, 0, 0)
    E(orrs_reg, 2, 1)
    E(str_imm, 2, 0, 0)
    a.label("aw_x")
    E(pop_list, [4, 5], pc=True)

    # ---- c_aiunsw(r0 = pad, r1 = the mask's offset) -> r0 = 1 when it was swallowed (now not); clobbers r0-r3
    a.label("c_aiunsw")
    E(push_list, [4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(mov_reg, 5, 1)
    E(bl, "c_airam")
    E(cmp_imm, 0, 0)
    E(b_cond, "au_x", "eq")
    E(adds_reg, 1, 0, 5)
    E(movs_imm, 2, 1)
    E(lsls_reg, 2, 4)
    E(ldr_imm, 3, 1, 0)
    E(movs_imm, 0, 0)
    E(tst_reg, 3, 2)
    E(b_cond, "au_x", "eq")
    E(bics_reg, 3, 2)
    E(str_imm, 3, 1, 0)
    E(movs_imm, 0, 1)
    a.label("au_x")
    E(pop_list, [4, 5], pc=True)

    # ---- c_aipress (the step views' slot 0: view, pad, velocity; autorel's after it)
    a.label("c_aipress")
    E(cmp_imm, 1, 16)
    bc("sp_s", "hs")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    imm32(1, AR.SV0)
    E(movw, 2, AR.SV_SZ)
    imm32(3, AR.SV_VT)
    E(bl, L["c_sgsvt"])
    E(cmp_imm, 0, 8)
    bc("sp_p", "hs")
    E(mov_reg, 6, 0)                                                      # r6 = the track
    E(bl, "c_aimode")
    E(mov_reg, 7, 0)                                                      # r7 = the mode
    E(raw, h(0x9800))                                                     # ldr r0, [sp]: the view
    E(raw, h(0x9901))                                                     # ldr r1, [sp, #4]: the pad
    E(bl, L["c_sgstep"])
    E(mov_reg, 5, 0)                                                      # r5 = the step
    E(raw, h(0x9800))
    E(bl, "c_ailanes")
    E(mov_reg, 4, 0)                                                      # r4 = its lanes
    E(bl, L["c_spheld"])
    E(cmp_imm, 7, MODE_VEL)
    E(b_cond, "sp_m", "ne")
    E(lsls_imm, 1, 0, 31 - BIT_CLEAR)
    E(b_cond, "sp_v", "pl")
    E(mov_reg, 0, 4)                                                      # Velocity, Clear held: the step's knob automation erased
    E(mov_reg, 1, 5)
    E(bl, "c_aiclr")
    E(b, "sp_w")
    a.label("sp_v")
    E(bl, "c_aiauto" if latch else L["c_cishift"])
    E(cmp_imm, 0, 0)
    bc("sp_p", "eq")
    E(lsls_imm, 0, 5, 3)                                                  # Shift: a yellow step (not marked, with knob automation)
    E(movw, 1, AR.LANES_OFF)
    E(subs_reg, 1, 4, 1)
    E(adds_reg, 0, 0, 1)
    E(ldrb_imm, 0, 0, AR.MARK_OFF)
    E(lsls_imm, 0, 0, 31)
    bc("sp_p", "mi")                                                      # marked: autorel's (unmarks)
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, "c_aihas")
    E(cmp_imm, 0, 0)
    bc("sp_p", "eq")                                                      # no automation: autorel's (marks)
    E(mov_reg, 0, 6)
    E(mov_reg, 1, 4)
    E(mov_reg, 2, 5)
    E(bl, "c_aiprev")
    E(b, "sp_w")
    a.label("sp_m")
    E(cmp_imm, 7, MODE_MAIN)
    bc("sp_p", "ne")
    E(lsls_imm, 1, 0, 31 - BIT_REC)
    bc("sp_p", "pl")                                                      # the track view, Record held: the snapshot
    E(mov_reg, 0, 6)
    E(mov_reg, 1, 4)
    E(mov_reg, 2, 5)
    E(bl, "c_aisnap")
    a.label("sp_w")
    E(raw, h(0x9801))                                                     # ldr r0, [sp, #4]: the pad
    E(movs_imm, 1, R_SWS)
    E(bl, "c_aiswal")
    E(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)
    a.label("sp_p")
    E(raw, AR.popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    a.label("sp_s")
    E(b_w, prev["press"])

    # ---- c_airel (the step views' slot 1: view, pad): one we took, swallowed
    a.label("c_airel")
    E(cmp_imm, 1, 16)
    E(b_cond, "sr_s", "hs")
    E(push_list, [0, 1, 2, 3, 4], lr=True)
    E(mov_reg, 0, 1)
    E(movs_imm, 1, R_SWS)
    E(bl, "c_aiunsw")
    E(cmp_imm, 0, 0)
    E(b_cond, "sr_q", "eq")
    E(pop_list, [0, 1, 2, 3, 4], pc=True)
    a.label("sr_q")
    E(raw, AR.popw([0, 1, 2, 3, 4], lr=True))
    a.label("sr_s")
    E(b_w, prev["rel"])

    # ---- c_aiinit(r0 = track): its voice back to Project init (K1-K8 through the router, 1-5 / 14 / 15, the selected sample); clobbers r0-r3
    a.label("c_aiinit")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 6, 0)
    E(bl, "c_aiph")
    E(cmp_imm, 0, 0)
    bc("in_x", "eq")
    E(mov_reg, 4, 0)                                                      # r4 = the photo
    E(movs_imm, 5, 0)
    a.label("in_k")
    E(adds_reg, 2, 4, 5)
    E(ldrb_imm, 2, 2, KNOB0)
    E(mov_reg, 0, 6)
    E(mov_reg, 1, 5)
    E(bl, "c_aiknob")
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, NK)
    E(b_cond, "in_k", "lo")
    for i in INIT_IDX:
        E(ldrb_imm, 2, 4, i)
        E(mov_reg, 0, 6)
        E(movs_imm, 1, i)
        E(bl, L["c_tcset"])
    E(ldrb_imm, 1, 4, PH_REC - 1)
    E(mov_reg, 0, 6)
    E(bl, L["c_tcsetsmp"])
    a.label("in_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)

    # ---- c_aipad (the controller's pad press, smodes's head after it: ctrl, pad, velocity): the track menu's pad 8
    a.label("c_aipad")
    E(cmp_imm, 1, PAD_INIT)
    bc("mp_s", "ne")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(bl, L["c_gpmopen"])
    E(cmp_imm, 0, 8)
    bc("mp_p", "hs")
    E(bl, "c_aiinit")
    E(movs_imm, 0, PAD_INIT)
    E(movs_imm, 1, R_SWP)
    E(bl, "c_aiswal")
    E(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)
    a.label("mp_p")
    E(raw, AR.popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    a.label("mp_s")
    E(b_w, prev["pad"])

    # ---- c_aiprel (the controller's pad release, smodes's head after it): one we took, swallowed
    a.label("c_aiprel")
    E(cmp_imm, 1, 32)
    E(b_cond, "mr_s", "hs")
    E(push_list, [0, 1, 2, 3, 4], lr=True)
    E(mov_reg, 0, 1)
    E(movs_imm, 1, R_SWP)
    E(bl, "c_aiunsw")
    E(cmp_imm, 0, 0)
    E(b_cond, "mr_q", "eq")
    E(pop_list, [0, 1, 2, 3, 4], pc=True)
    a.label("mr_q")
    E(raw, AR.popw([0, 1, 2, 3, 4], lr=True))
    a.label("mr_s")
    E(b_w, prev["rel_p"])

    # ---- c_aibtn (the controller's button press, the head: ctrl, id): Record pressed: the recording before kept
    a.label("c_aibtn")
    if latch:
        E(cmp_imm, 1, ID_VEL)
        bc("c_aivel", "eq")
    E(cmp_imm, 1, ID_REC)
    bc("bt_s", "ne")
    E(push_list, [0, 1, 2, 3, 4], lr=True)
    E(bl, "c_airam")
    E(cmp_imm, 0, 0)
    E(b_cond, "bt_q", "eq")
    E(mov_reg, 4, 0)
    imm32(0, TRANSPORT)
    E(movs_imm, 1, P_REC)
    E(bl, L["c_cinew"])
    E(adds_imm8, 0, 1)
    E(strb_imm, 0, 4, R_REC + REC_SAVED)
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 4, R_REC + REC_USED)
    a.label("bt_q")
    E(raw, AR.popw([0, 1, 2, 3, 4], lr=True))
    a.label("bt_s")
    E(b_w, prev["btn"])

    # ---- c_aibrel (the controller's button release, the head: ctrl, id): Record let go after a snapshot: the recording as before
    a.label("c_aibrel")
    E(cmp_imm, 1, ID_REC)
    bc("br_s", "ne")
    E(push_list, [0, 1, 2, 3, 4, 5], lr=True)
    E(bl, "c_airam")
    E(cmp_imm, 0, 0)
    E(b_cond, "br_q", "eq")
    E(mov_reg, 4, 0)
    E(ldrb_imm, 5, 4, R_REC + REC_SAVED)
    E(ldrb_imm, 1, 4, R_REC + REC_USED)
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 4, R_REC + REC_SAVED)
    E(strb_imm, 0, 4, R_REC + REC_USED)
    E(cmp_imm, 5, 0)
    E(b_cond, "br_q", "eq")
    E(cmp_imm, 1, 0)
    E(b_cond, "br_q", "eq")
    E(subs_imm8, 5, 1)
    imm32(0, TRANSPORT)                                                   # the recording's parameter written and committed
    E(movs_imm, 1, P_REC)
    E(bl, WPTR)
    E(strb_imm, 5, 0, 0)
    imm32(0, TRANSPORT)
    E(bl, COMMIT)
    a.label("br_q")
    E(raw, AR.popw([0, 1, 2, 3, 4, 5], lr=True))
    a.label("br_s")
    E(b, "c_aibrst")

    # ---- c_aisave0 / c_aisave1 (the two save calls, in front of what is there): the photo taken again (the state the save writes), then the
    #      save with the same arguments (r0-r3 and the stack), as mfsess's
    for k in (0, 1):
        a.label(f"c_aisave{k}")
        E(push_list, [0, 1, 2, 3, 4], lr=True)
        E(bl, L["c_tcphoto"])
        E(raw, AR.popw([0, 1, 2, 3, 4], lr=True))
        E(b_w, prev[f"save{k}"])

    # ---- c_aibrst (the stock's button release, its first two instructions in place of our b.w)
    a.label("c_aibrst")
    E(push_list, [3, 4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(b_w, CI.BTN_RELEASE + 4)

    # ---- c_ailed (the LED task's calls: ctrl, frame): the chain; the preview's end; Velocity + Shift's yellow steps; the preview's knobs;
    #      the track menu's pad 8
    a.label("c_ailed")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)                                                      # r5 = the frame
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(bl, L["c_gpmopen"])
    E(cmp_imm, 0, 8)
    E(b_cond, "ld_v", "hs")
    E(movs_imm, 0, RED)                                                   # the track menu: pad 8 red
    E(strh_imm, 0, 5, 2 * PAD_INIT)
    a.label("ld_v")
    E(bl, "c_aimode")
    E(mov_reg, 7, 0)
    if cue:                                                               # the track view: a snapshot's pad held = yellow
        E(cmp_imm, 7, MODE_MAIN)
        E(b_cond, "ld_q", "ne")
        E(bl, "c_airam")
        E(cmp_imm, 0, 0)
        E(b_cond, "ld_q", "eq")
        E(ldr_imm, 1, 0, R_SWS)
        E(movs_imm, 0, YELLOW)
        E(movs_imm, 2, 0)
        a.label("ld_c")
        E(lsrs_imm, 1, 1, 1)
        E(b_cond, "ld_cn", "lo")
        E(raw, AR.strh_reg(0, 5, 2))
        a.label("ld_cn")
        E(adds_imm8, 2, 2)
        E(cmp_imm, 2, 32)
        E(b_cond, "ld_c", "lo")
        a.label("ld_q")
    E(cmp_imm, 7, MODE_VEL)
    E(b_cond, "ld_e", "ne")
    E(bl, "c_aiauto" if latch else L["c_cishift"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ld_e", "eq")
    imm32(0, SP.CONT)                                                     # Velocity + Shift
    E(bl, SP.SELTRK)
    E(mov_reg, 4, 0)                                                      # r4 = the track
    E(movw, 1, AR.SV_SZ)
    E(muls, 0, 1)
    imm32(1, AR.SV0)
    E(adds_reg, 6, 0, 1)                                                  # r6 = its step view
    E(bl, "c_airam")
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(ldrb_imm, 1, 0, R_PV + PV_ON)
    E(cmp_imm, 1, 0)
    E(b_cond, "ld_y", "eq")
    E(ldrb_imm, 1, 0, R_PV + PV_TRK)
    E(cmp_reg, 1, 4)
    E(b_cond, "ld_y", "eq")
    E(bl, "c_aiend")                                                      # the preview of another track: ended
    a.label("ld_y")
    E(ldr_imm, 0, 6, AR.SV_PAGE)
    E(movs_imm, 1, 0)
    E(bl, CI.PARAM_GET)
    E(ldrb_imm, 7, 0, 0)
    E(cmp_imm, 7, 0)
    E(b_cond, "ld_pg", "eq")
    E(movs_imm, 7, 16)
    a.label("ld_pg")                                                      # r7 = the page's first step
    E(mov_reg, 0, 6)
    E(bl, "c_ailanes")
    E(mov_reg, 6, 0)                                                      # r6 = the lanes
    E(movs_imm, 4, 0)
    a.label("ld_s")
    E(adds_reg, 1, 4, 7)
    E(lsls_imm, 0, 1, 3)
    E(movw, 2, AR.LANES_OFF)
    E(subs_reg, 2, 6, 2)
    E(adds_reg, 0, 0, 2)
    E(ldrb_imm, 0, 0, AR.MARK_OFF)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "ld_sn", "mi")                                              # marked: autorel's red
    E(mov_reg, 0, 6)
    E(bl, "c_aihas")
    E(cmp_imm, 0, 0)
    E(b_cond, "ld_sn", "eq")
    E(movs_imm, 0, YELLOW)
    E(lsls_imm, 1, 4, 1)
    E(raw, AR.strh_reg(0, 5, 1))
    a.label("ld_sn")
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, 16)
    E(b_cond, "ld_s", "lo")
    E(bl, "c_airam")                                                      # the preview's knobs: yellow, the brightness = the value
    E(mov_reg, 4, 0)
    E(ldrb_imm, 0, 4, R_PV + PV_ON)
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(movw, 1, O_KB)
    E(adds_reg, 7, 0, 1)                                                  # r7 = kbright's overlay
    E(ldrb_imm, 6, 4, R_PV + PV_SMASK)
    E(ldrb_imm, 0, 7, K_MASK)
    E(orrs_reg, 0, 6)
    E(strb_imm, 0, 7, K_MASK)
    E(movs_imm, 3, 0)
    a.label("ld_k")
    E(mov_reg, 0, 6)
    E(lsrs_reg, 0, 3)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "ld_kn", "eq")
    E(adds_reg, 0, 4, 3)
    E(ldrb_imm, 0, 0, R_SHOWN)
    E(adds_reg, 1, 7, 3)
    E(strb_imm, 0, 1, K_VAL)
    E(movs_imm, 0, YELLOW)
    E(lsls_imm, 1, 3, 1)
    E(adds_reg, 2, 1, 7)
    E(strh_imm, 0, 2, K_CODE)
    E(adds_reg, 2, 1, 5)
    E(strh_w_imm, 0, 2, 2 * SP.LED_KNOB0)
    a.label("ld_kn")
    E(adds_imm8, 3, 1)
    E(cmp_imm, 3, NK)
    E(b_cond, "ld_k", "lo")
    E(b, "ld_x")
    a.label("ld_e")
    if latch:                                                             # not the automation view: the latch off (or already off)
        E(bl, "c_airam")
        E(cmp_imm, 0, 0)
        E(b_cond, "ld_l0", "eq")
        E(movs_imm, 1, 0)
        E(strb_imm, 1, 0, R_LATCH)
        a.label("ld_l0")
    E(bl, "c_aiend")                                                      # not Velocity + Shift: a preview ends
    a.label("ld_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)

    if latch:
        # ---- c_aiauto() -> r0 = <> 0 with Shift held or the automation view latched (the callers know the Velocity view); clobbers r1-r3
        a.label("c_aiauto")
        E(push_list, [4], lr=True)
        E(bl, L["c_cishift"])
        E(cmp_imm, 0, 0)
        E(b_cond, "aa_x", "ne")
        E(bl, "c_airam")
        E(cmp_imm, 0, 0)
        E(b_cond, "aa_x", "eq")
        E(ldrb_imm, 0, 0, R_LATCH)
        a.label("aa_x")
        E(pop_list, [4], pc=True)

        # ---- c_aivel (c_aibtn's, the button press: ctrl, id = Velocity): the Velocity view on the screen, no Shift = the latch flipped;
        #      from another view = off; then on to the stock
        a.label("c_aivel")
        E(push_list, [0, 1, 2, 3, 4], lr=True)
        E(bl, "c_airam")
        E(cmp_imm, 0, 0)
        E(b_cond, "vl_q", "eq")
        E(mov_reg, 4, 0)
        E(bl, "c_aimode")
        E(movs_imm, 1, 0)
        E(cmp_imm, 0, MODE_VEL)
        E(b_cond, "vl_w", "ne")
        E(bl, L["c_cishift"])
        E(cmp_imm, 0, 0)
        E(b_cond, "vl_q", "ne")                                           # Shift + Velocity: the stock's fixed velocity
        E(ldrb_imm, 1, 4, R_LATCH)
        E(movs_imm, 0, 1)
        E(raw, h(0x4041))                                                 # eors r1, r0
        a.label("vl_w")
        E(strb_imm, 1, 4, R_LATCH)
        a.label("vl_q")
        E(raw, AR.popw([0, 1, 2, 3, 4], lr=True))
        E(b_w, prev["btn"])
    return a.assemble()


def install(img, report, base_addr, cue=False, latch=False):
    """The step views' slots 0 / 1 (in front of autorel's), the controller's pad press / release (in front of smodes's), the button press /
    release heads, the two save calls, the LED calls; (latch) autorel's c_arvel's Shift test -> c_aiauto.  Needs autorel init (keep), trkcopy
    ram (the photo), stepgate, granpage menu2, smodes, stockplus, kbright, rhstate ram2; not latdiag."""
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]                 # noqa: E731
    lab = lambda m, k: int(report[m]["labels"][k], 16)                         # noqa: E731
    assert "latdiag" not in report and report["autorel"].get("init") and report["trkcopy"].get("ram"), "autoinit: needs autorel init, trkcopy ram"
    L = dict(c_rram=lab("rhstate", "c_rram"), c_rst=lab("rhstate", "c_rst"), c_ciok=lab("countin", "c_ciok"), c_cinew=lab("countin", "c_cinew"),
             c_cishift=lab("countin", "c_cishift"), c_sgsvt=lab("stepgate", "c_sgsvt"), c_sgstep=lab("stepgate", "c_sgstep"),
             c_arsteps=lab("autorel", "c_arsteps"), c_spview=lab("stockplus", "c_spview"), c_spheld=lab("stockplus", "c_spheld"),
             c_gpmopen=lab("granpage", "c_gpmopen"), **{k: lab("trkcopy", k) for k in ("c_tcget", "c_tcset", "c_tcsetsmp", "c_tcphoto")})
    saves = list(MF.SAVE_CALLS)
    prev = dict(press=u(AR.SV_VT) & ~1, rel=u(AR.SV_VT + 4) & ~1, pad=rhbuild.bw_target(img, GP.PP_ENTRY),
                rel_p=rhbuild.bw_target(img, GP.PR_ENTRY), btn=rhbuild.bw_target(img, CI.BTN_ENTRY),
                ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]),
                **{f"save{k}": rhbuild.bl_target(img, c) for k, c in enumerate(saves)})
    assert prev["press"] == lab("autorel", "c_arpress") and prev["rel"] == lab("autorel", "c_arrel")
    assert prev["pad"] == lab("smodes", "c_smpad") and prev["rel_p"] == lab("smodes", "c_smrel")
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    code_, labels = arm_code(base_addr, L, prev, cue, latch)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code_
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch_word(img, AR.SV_VT, prev["press"] | 1, labels["c_aipress"] | 1)
    rhbuild.patch_word(img, AR.SV_VT + 4, prev["rel"] | 1, labels["c_airel"] | 1)
    rhbuild.patch(img, GP.PP_ENTRY, f"b.w #{prev['pad']:#x}", b_w(GP.PP_ENTRY, labels["c_aipad"]))
    rhbuild.patch(img, GP.PR_ENTRY, f"b.w #{prev['rel_p']:#x}", b_w(GP.PR_ENTRY, labels["c_aiprel"]))
    rhbuild.patch(img, CI.BTN_ENTRY, f"b.w #{prev['btn']:#x}", b_w(CI.BTN_ENTRY, labels["c_aibtn"]))
    rhbuild.patch(img, CI.BTN_RELEASE, BREL_HEAD, b_w(CI.BTN_RELEASE, labels["c_aibrel"]))
    for k, c in enumerate(saves):
        rhbuild.patch(img, c, f"bl #{prev[f'save{k}']:#x}", bl(c, labels[f"c_aisave{k}"]))
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_ailed"]))
    if latch:                                                                  # autorel's Velocity-view-with-Shift test: Shift or the latch
        at = lab("autorel", "c_arvel")
        sites = [x for x in range(at, at + 0x40, 2) if _is_bl(img, x, rhbuild) and rhbuild.bl_target(img, x) == L["c_cishift"]]
        assert len(sites) == 1, sites
        rhbuild.patch(img, sites[0], f"bl #{L['c_cishift']:#x}", bl(sites[0], labels["c_aiauto"]))
    report["autoinit"] = dict(prev={k: hex(v) for k, v in prev.items()}, labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    if cue or latch:
        report["autoinit"].update(cue=cue, latch=latch)
    return labels, code_
