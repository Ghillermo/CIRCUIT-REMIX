"""Stock+ knob page of a track: pitch envelope and pitch LFO on K1-K4 (MIT; the first part of the Stock+ sampler mode, for the Circuit Rhythm
5706).  The user (2026-10-21): «the new sample version has all stock rythm functions, plus some 8 functions on shift»; «in stock, shift+knob is
fine control»; «Use the page toggle: press the track's button again to flip to the Stock+ knob page; Shift stays fine control».

The stock of the Rhythm (emulated on the RAM dump, $TMP checks of 2026-10-21):
  * a track button (ids 0-7) in the track views re-selects the track and its view mode (0x0804D662 / 0x0804D6B6) every time: pressed again it
    changes nothing (the bytes that seem to move are the double copies of the stores; the LEDs stay);
  * a knob: 0x0803DDE0(ctrl, knob, delta) -> slot 4 of the active view; the container's (0x20048B9C, vtable 0x080678DC) hands it to the subview
    of 0x0804DB78 (none in the Sidechain mode, [+ 0x264] = 8); the knob's value is a halfword 0..16383 (the parameter = value >> 7): a turn
    moves it by 128 a click, by 4 with Shift (fine control);
  * the selected track = 0x0805800E(container); Shift = p0 of [ctrl + 0xC]; the held buttons = [ctrl + 0xA0] (Clear 23, Duplicate 24);
  * the track buttons' LEDs: 32 + t and 40 + t of the frame (0x4B the selected one, 0x09 the others); the knob LEDs 60-67; 0x01 white;
    0x151 = white for the knob LEDs.
Ours:
  * the second press of the selected track's button (track views on the screen, not the Sidechain mode, no Shift / Clear / Duplicate held)
    flips that track's knob page: stock / Stock+ (rhstate "stockplus" + 0, bit t; until power-off); the stock's press is run as well;
  * on the Stock+ page the container's knob slot (head of the chain) takes the knobs: K1 pitch envelope amount (centre = none, +- 24 semitones),
    K2 its decay (5 ms .. 4 s, to 10 %), K3 LFO rate (0.05 .. 30 Hz), K4 LFO depth (0 .. 24 semitones); 128 a click, 4 with Shift; Clear held +
    a knob = its default; K5-K8 nothing yet (dark);
  * the values (14 bits, as the stock's knobs) travel with the project in the record's tail (rhrec "stockplus": "SP", a check byte, 8 tracks x
    8 halfwords; a project without it = the defaults: no modulation); Clear + a track button (track views) = that track's defaults; Duplicate +
    track A, then track B = A's values copied to B (as trkcopy does with the stock's parameters); without our block both write nothing (every
    track already has the defaults);
  * the LED task (after the chain): on the Stock+ page K1-K4 white with their value as brightness (kbright's overlay; K1 |v - 64| x 2), K5-K8
    dark, the track's button blinking white (256 ms); and the DSP: each frame one track in turn plus every track a knob changed, its four words
    into core 1 (tools/pitchmod.py: Y:$1320 / $1328 / $1330 / $1338 + t) with 0x08031200(1, word << 8, $8000 | address) (the RD4 command that
    worked on the device, RD6), only while core 0 / 1 hold the mode 0 program (cthresh's state READY: an upload of mode 0 seen); the round
    writes again what a lost write or an upload (core 1 clears Y:$400..$13FF at its start) undid.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, ldr_sp, adds_imm8, adds_reg, b, b_cond, b_w, bl, cmp_imm, cmp_reg, eors_reg, h, ldr_imm, ldrb_imm, ldrb_reg, ldrh_imm,  # noqa: E402
                   lsls_imm, lsls_reg, lsrs_imm, lsrs_reg, mov_reg, movs_imm, movt, movw, muls, orrs_reg, pop_list, push_list, raw, strb_imm,
                   strh_imm, subs_imm8, subs_reg, tst_reg, ldrb_w, strb_w, strh_w_imm, bics_reg, str_imm)
import countin as CI  # noqa: E402
import cthresh as TH  # noqa: E402
import pitchmod as PM  # noqa: E402
import rhrec  # noqa: E402
import rhstate  # noqa: E402
import sckn as SK  # noqa: E402

CTRL = CI.CTRL
CONT, CONT_VT, O_MODE, MODE_SC = SK.CONT, SK.CONT_VT, SK.O_MODE, SK.MODE_SC
SLOT_KNOB = SK.SLOT_KNOB
SELTRK, SUBVIEW = 0x0805800E, 0x0804DB78
O_HELD, BIT_CLEAR, BIT_DUP = 0xA0, 23, 24
WR16 = TH.WR16
HAL_TICK = CI.HAL_TICK
LED_TRK0, LED_TRK1, LED_KNOB0 = 32, 40, 60
COL_BLINK, COL_KNOB = 0x01, 0x151
BLK, BLK_LEN = rhrec.OFF["stockplus"]
O_ST, ST_LEN = rhstate.OFF["stockplus"]               # + 0 the tracks on the Stock+ page, + 1 the tracks to push, + 2 the round, + 3 Duplicate's source + 1
O_KB, O_TH = rhstate.OFF["kbright"][0], rhstate.OFF["cthresh"][0] + 1
K_MASK, K_VAL, K_CODE = 0, 1, 10
YB = PM.Y_BASE                                        # (install(shift=$300), RD10 on) pitchmod's words moved up, out of voice 7's sample ring
MARK0, MARK1, CHECK = ord("S"), ord("P"), 0xA5
NPAR, NTRK = 8, 8
FULL, STEP, FINE = 16383, 128, 4
DEF = (8192, 8192, 8192, 0, 0, 0, 0, 0)               # K1 none, K2 / K3 the middle, K4 no depth; K5-K8 for later
UPD = 1500 / 8                                        # the voices' pitch updates a second (RD6 on the device: 1 500 blocks / s, one voice a block)
A_SCALE, L_SCALE = 192, 96                            # (v - 8192) x 192: +- 24 semitones ($180000); v x 96: 24 semitones at the top
T_MIN, T_MAX = 0.005, 4.0
HZ_MIN, HZ_MAX = 0.05, 30.0
INV = SK.INV
assert BLK_LEN == 4 + 2 * NPAR * NTRK and ST_LEN == 4 and 0 < O_ST - O_TH < 256 and 0 < O_ST - O_KB < 256


# ---- v2 (RH33): K5-K8 on the Stock+ page, each with a Shift layer (the user, 2026-10-24: «k5: rmod amount, shift: frequency. k6: filter
# type (affects default filters) … stock filter (sound is unaffected) shift: pitch follow to lpf. k7: stretch (changes speed without changing
# pitch). shift: bitcrush. k8: scan lfo speed (changes start point) shift: …» depth; K1-K4 keep Shift = fine control).  Knob indices 0..7 =
# K1-K8 (the "SP" block, as RH32), 8..11 = Shift + K5..K8 (the "SQ" block, rhrec "stockplus2").  K7 is stored XOR 8192: RH32 projects hold 0
# in that slot, which reads as 8192 = no stretch.
BLK2, BLK2_LEN = rhrec.OFF["stockplus2"]
MARK2 = ord("Q")
NK = 12
DEF2 = (8192, 0, 0, 0)                                # Shift + K5 ring frequency in the middle (~316 Hz), no follow, no bitcrush, no scan depth
DEFU = DEF[:6] + (8192, DEF[7]) + DEF2                # the knobs' defaults as values (K7's stored 0 = 8192)
K7, X7 = 6, 8192
RING_LO, RING_HI = 20.0, 5000.0
SCAN_LO, SCAN_HI = 0.05, 20.0
DEAD = 128                                            # K7 within one click of the middle: no stretch (the stock's resampler)
GRAIN = 2048                                          # the stretch's grain (RD12 on the device: drum loops best at 2048)
# k6swap (RH34; the user, 2026-10-25, after RH33 on the device: «switch k6 and s+k6, give each filter type different colors»): K6 = pitch
# follow, Shift + K6 = the filter type (the stored indices stay: 5 type, 9 follow); K6's LED always in its filter type's colour (stock white,
# 24 dB the FX view's delay colour, comb its reverb colour), as bright as the follow (at least K6_MIN) or fully with Shift held; and Clear +
# K5-K8 = both of the knob's layers back to their defaults («make clear +knob affect shift functions too»)
K6, I_TYPE, I_FOLLOW = 5, 5, 9
# wait (RH35; the user, 2026-10-25, on RH34: «stock+ does nothing after reboot, only works when flashed»; on the device after a power-up
# core 1's host port answered out of step and none of our words had arrived): the first write to core 1 only SP_WAIT LED frames after its
# program was seen uploaded (cthresh READY), not at once: core 1 is still starting then, its host handler (which takes the words in address /
# data pairs) not yet running, and a word lost there leaves every later pair one word out of step
O_W = rhstate.OFF["spwait"][0]
SP_WAIT = 200
COL_TYPES = (0x151, 0x139, 0x141)
K6_MIN = 24
# k8sync (RH38; the user, 2026-10-25: «make the rate knob free running to the right and bpm synced to the left»): K8 (the scan's rate) is
# bipolar and stored XOR 8192 as K7 (a stored 0, every project's default so far, = the middle):
#   * the middle (within DEAD) = the scan stands still (SCANR = 0);
#   * right of it = free, scan_table over the right half (0.05 .. 20 Hz);
#   * left of it = at the tempo: 16 divisions of 4 clicks from the middle out (DIVS, ticks of 24 a quarter note: 1/16T, 1/16, 1/8T, 1/8,
#     1/4T, 1/4, 1/2T, 1/2, 1 bar T, 1 bar, 2T, 2, 4T, 4, 8T, 8 bars): SCANR = BPM x KQ[i] >> 8 (BPM = p0 of the tempo store, the cycle's
#     length in pitch updates), written at each push; and, in every LED frame where the sequencer's global tick (parameter 0 of
#     [SEQ + 0x90], counted by the tick 0x080344B8, 0 at Play) moved, the phase SCANPH = (tick mod DIVS[i]) x 2^24 / DIVS[i]: each cycle
#     starts on the bar's first beat at the scan's 0 (no offset), and keeps in step; between ticks (and stopped) the DSP runs at SCANR.
K8 = 7
SEQ, TEMPO = 0x2003C380, 0x20012788
DIVS = (4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512, 768)
KQ = tuple(round((1 << 24) * 24 * 256 / (60 * UPD * d)) for d in DIVS)
PHQ = tuple(round((1 << 24) / d) for d in DIVS)
O_K8T = rhstate.OFF["k8tick"][0]
DIV_SHIFT = 9                                         # 512 = 4 clicks a division
DEFU8 = DEFU[:K8] + (8192,) + DEFU[K8 + 1:]           # (k8sync) the defaults as values: K8's stored 0 = 8192
# k3sync (RH46; from CIRCUIT-HACKS' lfosync): K3 (the pitch LFO's rate) bipolar as K8, stored as it was (its default 8192 = the middle): the
# middle (within DEAD) = the LFO off at its centre (R = 0, the phase at K3_MIDPH: no pitch offset); right = free, rate_table over the right
# half (0.05 .. 30 Hz); left = at the tempo, K8's 16 divisions (R = BPM x KQ[i] >> 8; at each new global tick the phase = (tick mod D) / D
# of a cycle from the centre rising, so the cycle starts on the bar's first beat).  Projects with K3 set change their meaning (below the
# middle: synced; the default, the middle, is now off).
K3 = 2
K3_MIDPH = 0x400000                                   # a quarter cycle: pitchmod's triangle at 0, rising


def k8_index(v):
    """(k8sync) K8's value -> None (the middle), ("free", x) or ("sync", the division's index)"""
    d = v - X7
    if abs(d) < DEAD:
        return None
    if d > 0:
        return ("free", d << 1)
    return ("sync", min(15, (-d - DEAD) >> DIV_SHIFT))


def k8_rate(v, bpm):
    """(k8sync) SCANR for K8's value v at bpm (the ARM's: BPM < 30 counts as 120, as countin)"""
    k = k8_index(v)
    if k is None:
        return 0
    if k[0] == "free":
        tab, x = scan_table(), k[1]
        i, f = x >> 7, x & 127
        return tab[i] + ((tab[i + 1] - tab[i]) * f >> 7)
    bpm = bpm if bpm >= 30 else 120
    return (bpm * KQ[k[1]] >> 8) & 0xFFFFFFFF


def k3_rate(v, bpm):
    """(k3sync) R for K3's value v at bpm: 0 in the middle, the rate table right of it, BPM x KQ[i] >> 8 left of it"""
    d = v - X7
    if abs(d) < DEAD:
        return 0
    if d > 0:
        tab, x = rate_table(), d << 1
        i, f = x >> 7, x & 127
        return tab[i] + ((tab[i + 1] - tab[i]) * f >> 7)
    bpm = bpm if bpm >= 30 else 120
    return (bpm * KQ[min(15, (-d - DEAD) >> DIV_SHIFT)] >> 8) & 0xFFFFFFFF


def k3_phase(v, tick):
    """(k3sync) the LFO's phase the LED task writes for K3's value v at the global tick (None: not synced)"""
    d = v - X7
    if d > -DEAD:
        return None
    i = min(15, (-d - DEAD) >> DIV_SHIFT)
    return ((tick % DIVS[i]) * PHQ[i] + K3_MIDPH) & 0xFFFFFF


def k8_phase(v, tick):
    """(k8sync) the phase the LED task writes for K8's value v at the global tick (None: not synced)"""
    k = k8_index(v)
    if k is None or k[0] != "sync":
        return None
    return ((tick % DIVS[k[1]]) * PHQ[k[1]]) & 0xFFFFFF
assert BLK2_LEN == 4 + 2 * 4 * NTRK


def ring_table():
    return [round(RING_LO * (RING_HI / RING_LO) ** (i / 128) / 48000 * (1 << 24)) for i in range(129)]


def speed_table():
    return [min(0x7FFFFF, round(4 ** ((i - 64) / 64) / 4 * (1 << 23))) for i in range(129)]


def scan_table():
    return [round(SCAN_LO * (SCAN_HI / SCAN_LO) ** (i / 128) / UPD * (1 << 24)) for i in range(129)]


def words2(v, t, k8sync=False, bpm=120, k7flag=False):
    """{core 1 Y address: word} that c_spdsp (v2) writes for track t with the 12 values v (K7 as its value, not stored; with k8sync K8 too):
    for the tests"""
    import stretch as STR
    import voicefilt as F
    import voicefx as V

    def interp(tab, x):
        i, f = x >> 7, x & 127
        return tab[i] + ((tab[i + 1] - tab[i]) * f >> 7)
    vy, yb = V.Y_BASE + 0x300, PM.Y_BASE + 0x300                       # (v2 always with the shift)
    out = dict(zip((yb + PM.OFF_A + t, yb + PM.OFF_D + t, yb + PM.OFF_R + t, yb + PM.OFF_L + t), words(v[:4])))
    out[vy + V.RAM + t] = v[4] << 9
    out[vy + V.RST + t] = interp(ring_table(), v[8])
    kt = v[5] * 3 >> 14
    out[F.KTYPE + t] = kt
    if kt != 2:
        out[vy + V.FMODE + t] = 0
    out[F.FOLLOW + t] = v[9] << 9
    off = v[6] == X7 if k7flag else abs(v[6] - X7) < DEAD                  # (fitflag: K7 stored with bit 14 = off only at the middle)
    out[STR.STRETCH + t] = 0 if off else interp(speed_table(), v[6])
    if v[10]:
        bits = 16 - (v[10] * 14 >> 14)
        out[vy + V.DG + t], out[vy + V.DMASK + t], out[vy + V.DTYPE + t] = 0x080000, (0xFFFFFF << (24 - bits)) & 0xFFFFFF, 4
    else:
        out[vy + V.DTYPE + t] = 0
    out[F.SCANR + t] = k8_rate(v[7], bpm) if k8sync else interp(scan_table(), v[7])
    out[F.SCAND + t] = v[11] << 9
    return out


def popw(regs, lr=False): return h(0xE8BD) + h(sum(1 << r for r in regs) | (1 << 14 if lr else 0))


def decay_table():
    out = []
    for i in range(129):
        n = max(T_MIN * (T_MAX / T_MIN) ** (i / 128) * UPD, 1.0)
        out.append(min(round(0.1 ** (1 / n) * (1 << 23)), 0x7FFFFF))
    return out


def rate_table():
    return [round(HZ_MIN * (HZ_MAX / HZ_MIN) ** (i / 128) / UPD * (1 << 24)) for i in range(129)]


def words(v):
    """the four core 1 words of a track's values (as c_spdsp computes them): for the tests"""
    def interp(t, x):
        i, f = x >> 7, x & 127
        return t[i] + ((t[i + 1] - t[i]) * f >> 7)
    return [((v[0] - 8192) * A_SCALE) & 0xFFFFFF, interp(decay_table(), v[1]), interp(rate_table(), v[2]), v[3] * L_SCALE]


def arm_code(base, L, prev, v2=False, k6swap=False, wait=False, k8sync=False, fitflag=False, k3sync=False):
    a = Asm(base)
    E = a.emit
    zc = [0]

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    def bc(target, cond):
        zc[0] += 1
        n = f"_p{zc[0]}"
        E(b_cond, n, INV[cond])
        E(b, target)
        a.label(n)

    t_dec = base
    E(raw, b"".join(w.to_bytes(4, "little") for w in decay_table()))
    t_rate = base + 4 * 129
    E(raw, b"".join(w.to_bytes(4, "little") for w in rate_table()))
    t_def = base + 8 * 129
    E(raw, b"".join(v.to_bytes(2, "little") for v in DEF))
    VAL, PUT = ("c_spval_a", "c_spput_a") if v2 else ("c_spval", "c_spput")
    if v2:
        t_ring = base + 8 * 129 + 2 * NPAR
        E(raw, b"".join(w.to_bytes(4, "little") for w in ring_table()))
        t_spd = t_ring + 4 * 129
        E(raw, b"".join(w.to_bytes(4, "little") for w in speed_table()))
        t_scan = t_spd + 4 * 129
        E(raw, b"".join(w.to_bytes(4, "little") for w in scan_table()))
        t_defu = t_scan + 4 * 129
        E(raw, b"".join(v.to_bytes(2, "little") for v in (DEFU8 if k8sync else DEFU)))
        t_def2 = t_defu + 2 * NK
        E(raw, b"".join(v.to_bytes(2, "little") for v in DEF2))
        if k6swap:
            t_cols = t_def2 + 2 * len(DEF2)
            E(raw, b"".join(v.to_bytes(2, "little") for v in COL_TYPES))
        if k8sync:
            assert k6swap
            t_divs = (t_cols + 2 * len(COL_TYPES) + 3) & ~3
            E(raw, bytes(t_divs - t_cols - 2 * len(COL_TYPES)))
            E(raw, b"".join(x.to_bytes(4, "little") for x in DIVS + KQ + PHQ))
            t_kq, t_phq = t_divs + 4 * len(DIVS), t_divs + 8 * len(DIVS)

    # ---- c_spst() -> r0 = our state (rhstate), 0 without our RAM; clobbers r1-r3
    a.label("c_spst")
    E(push_list, [4], lr=True)
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "ss_x", "eq")
    E(adds_imm8, 0, O_ST)
    a.label("ss_x")
    E(pop_list, [4], pc=True)

    # ---- c_spblk() -> r0 = our block in the record's tail, 0 without the record; clobbers r1-r3
    a.label("c_spblk")
    E(push_list, [4], lr=True)
    E(bl, L["c_rrt"])
    E(cmp_imm, 0, 0)
    E(b_cond, "sb_x", "eq")
    E(movw, 1, BLK)
    E(adds_reg, 0, 0, 1)
    a.label("sb_x")
    E(pop_list, [4], pc=True)

    # ---- c_spsum(r0 = block) -> r0 = the check byte of its values; clobbers r1-r3
    a.label("c_spsum")
    E(adds_imm8, 0, 4)
    E(movs_imm, 1, 2 * NPAR * NTRK)
    E(movs_imm, 2, CHECK)
    a.label("su_l")
    E(ldrb_imm, 3, 0, 0)
    E(eors_reg, 2, 3)
    E(adds_imm8, 0, 1)
    E(subs_imm8, 1, 1)
    E(b_cond, "su_l", "ne")
    E(mov_reg, 0, 2)
    E(raw, h(0x4770))                                                     # bx lr

    # ---- c_spok(r0 = block) -> r0 = 1 when it holds our values; clobbers r1-r3
    a.label("c_spok")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(ldrb_imm, 1, 4, 0)
    E(cmp_imm, 1, MARK0)
    E(b_cond, "ok_0", "ne")
    E(ldrb_imm, 1, 4, 1)
    E(cmp_imm, 1, MARK1)
    E(b_cond, "ok_0", "ne")
    E(bl, "c_spsum")
    E(ldrb_imm, 1, 4, 2)
    E(cmp_reg, 0, 1)
    E(b_cond, "ok_0", "ne")
    E(movs_imm, 0, 1)
    E(pop_list, [4], pc=True)
    a.label("ok_0")
    E(movs_imm, 0, 0)
    E(pop_list, [4], pc=True)

    # ---- c_spval(r0 = track, r1 = knob) -> r0 = its value (the default without our block); clobbers r1-r3  (v2: c_spval_a, block "SP")
    a.label(VAL)
    E(push_list, [4, 5, 6], lr=True)
    E(lsls_imm, 4, 0, 3)
    E(adds_reg, 4, 4, 1)
    E(lsls_imm, 4, 4, 1)                                                  # r4 = 2 (8 t + k)
    E(lsls_imm, 6, 1, 1)                                                  # r6 = 2 k
    E(bl, "c_spblk")
    E(cmp_imm, 0, 0)
    E(b_cond, "sv_d", "eq")
    E(mov_reg, 5, 0)
    E(bl, "c_spok")
    E(cmp_imm, 0, 0)
    E(b_cond, "sv_d", "eq")
    E(adds_reg, 5, 5, 4)
    E(ldrh_imm, 0, 5, 4)
    E(pop_list, [4, 5, 6], pc=True)
    a.label("sv_d")
    imm32(0, t_def)
    E(adds_reg, 0, 0, 6)
    E(ldrh_imm, 0, 0, 0)
    E(pop_list, [4, 5, 6], pc=True)

    # ---- c_spput(r0 = track, r1 = knob, r2 = value): into our block (made with the defaults if missing), its check byte; clobbers r0-r3
    a.label(PUT)
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(lsls_imm, 4, 0, 3)
    E(adds_reg, 4, 4, 1)
    E(lsls_imm, 4, 4, 1)                                                  # r4 = 2 (8 t + k)
    E(mov_reg, 6, 2)
    E(bl, "c_spblk")
    E(cmp_imm, 0, 0)
    E(b_cond, "sp_x", "eq")
    E(mov_reg, 5, 0)
    E(bl, "c_spok")
    E(cmp_imm, 0, 0)
    E(b_cond, "sp_w", "ne")
    E(movs_imm, 0, MARK0)                                                 # a new block: every track's defaults
    E(strb_imm, 0, 5, 0)
    E(movs_imm, 0, MARK1)
    E(strb_imm, 0, 5, 1)
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 5, 3)
    E(movs_imm, 7, 0)
    a.label("sp_i")
    imm32(0, t_def)
    E(movs_imm, 1, 2 * NPAR - 1)
    E(raw, h(0x4039))                                                     # ands r1, r7: (2 i) mod 16 = 2 k
    E(adds_reg, 0, 0, 1)
    E(ldrh_imm, 0, 0, 0)
    E(adds_reg, 1, 5, 7)
    E(strh_imm, 0, 1, 4)
    E(adds_imm8, 7, 2)
    E(cmp_imm, 7, 2 * NPAR * NTRK)
    E(b_cond, "sp_i", "lo")
    a.label("sp_w")
    E(adds_reg, 1, 5, 4)
    E(strh_imm, 6, 1, 4)
    E(mov_reg, 0, 5)
    E(bl, "c_spsum")
    E(strb_imm, 0, 5, 2)
    a.label("sp_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)

    # ---- c_spdirty(r0 = track): to push; clobbers r0-r3
    a.label("c_spdirty")
    E(push_list, [4], lr=True)
    E(mov_reg, 4, 0)
    E(bl, "c_spst")
    E(cmp_imm, 0, 0)
    E(b_cond, "sd_x", "eq")
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(ldrb_imm, 2, 0, 1)
    E(orrs_reg, 2, 1)
    E(strb_imm, 2, 0, 1)
    a.label("sd_x")
    E(pop_list, [4], pc=True)

    # ---- c_spreset(r0 = track): its defaults; clobbers r0-r3
    a.label("c_spreset")
    E(push_list, [3, 4, 5], lr=True)
    E(mov_reg, 4, 0)
    if not v2:                                                            # (v2: the "SQ" block may exist without "SP": always written)
        E(bl, "c_spvalid")
        E(cmp_imm, 0, 0)
        E(b_cond, "sr_x", "eq")                                           # no block: already the defaults (nothing written)
    E(movs_imm, 5, 0)
    a.label("sr_l")
    imm32(2, t_defu if v2 else t_def)
    E(lsls_imm, 1, 5, 1)
    E(adds_reg, 2, 2, 1)
    E(ldrh_imm, 2, 2, 0)
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, "c_spput")
    E(adds_imm8, 5, 1)
    E(cmp_imm, 5, NK if v2 else NPAR)
    E(b_cond, "sr_l", "lo")
    E(mov_reg, 0, 4)
    E(bl, "c_spdirty")
    a.label("sr_x")
    E(pop_list, [3, 4, 5], pc=True)

    # ---- c_spvalid() -> r0 = 1 when the project holds our block; clobbers r1-r3
    a.label("c_spvalid")
    E(push_list, [4], lr=True)
    E(bl, "c_spblk")
    E(cmp_imm, 0, 0)
    E(b_cond, "vl_x", "eq")
    E(bl, "c_spok")
    a.label("vl_x")
    E(pop_list, [4], pc=True)

    # ---- c_spview() -> r0 = the selected track when the track views (not the Sidechain mode) are on the screen, else 8; clobbers r1-r3
    a.label("c_spview")
    E(push_list, [4], lr=True)
    imm32(0, CTRL)
    E(ldr_imm, 1, 0, 0x7C)
    imm32(0, CONT)
    E(cmp_reg, 0, 1)
    E(b_cond, "vw_n", "ne")
    E(ldr_imm, 1, 0, 0)
    imm32(2, CONT_VT)
    E(cmp_reg, 1, 2)
    E(b_cond, "vw_n", "ne")
    E(ldrb_w, 1, 0, O_MODE)
    E(cmp_imm, 1, MODE_SC)
    E(b_cond, "vw_n", "eq")
    E(bl, SELTRK)
    E(cmp_imm, 0, NTRK)
    E(b_cond, "vw_x", "lo")
    a.label("vw_n")
    E(movs_imm, 0, NTRK)
    a.label("vw_x")
    E(pop_list, [4], pc=True)

    # ---- c_spheld() -> r0 = the held buttons; clobbers r1
    a.label("c_spheld")
    imm32(1, CTRL + O_HELD)
    E(ldr_imm, 0, 1, 0)
    E(raw, h(0x4770))

    # ---- c_spshift() -> r0 = Shift held; clobbers r1-r3
    a.label("c_spshift")
    E(push_list, [4], lr=True)
    imm32(0, CTRL)
    E(ldr_imm, 0, 0, 0xC)
    E(movs_imm, 1, 0)
    E(bl, CI.PARAM_GET)
    E(ldrb_imm, 0, 0, 0)
    E(pop_list, [4], pc=True)

    # ---- c_spbtn (the head of the button chain: r0 = ctrl, r1 = id)
    a.label("c_spbtn")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)                          # 8 words
    E(cmp_imm, 1, NTRK)
    bc("bt_p", "hs")
    E(mov_reg, 4, 1)                                                      # r4 = the track of the button
    E(bl, "c_spst")
    E(cmp_imm, 0, 0)
    bc("bt_p", "eq")
    E(mov_reg, 5, 0)                                                      # r5 = our state
    E(bl, "c_spheld")
    E(mov_reg, 6, 0)                                                      # r6 = the held buttons
    E(lsls_imm, 0, 6, 31 - BIT_DUP)
    E(b_cond, "bt_nd", "pl")
    E(lsls_imm, 0, 6, 31 - BIT_CLEAR)
    bc("bt_p", "mi")                                                      # Clear and Duplicate: nothing of ours
    E(ldrb_imm, 7, 5, 3)                                                  # Duplicate: the source + 1
    E(cmp_imm, 7, 0)
    E(b_cond, "bt_cp", "ne")
    E(adds_imm8, 4, 1)
    E(strb_imm, 4, 5, 3)                                                  # the first button = the source
    E(b, "bt_p")
    a.label("bt_cp")
    E(subs_imm8, 7, 1)
    E(cmp_reg, 7, 4)
    bc("bt_p", "eq")
    if not v2:
        E(bl, "c_spvalid")
        E(cmp_imm, 0, 0)
        bc("bt_p", "eq")                                                  # no block: every track has the defaults
    E(movs_imm, 6, 0)                                                     # r6 = the knob
    a.label("bt_cl")
    E(mov_reg, 0, 7)
    E(mov_reg, 1, 6)
    E(bl, "c_spval")
    E(mov_reg, 2, 0)
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 6)
    E(bl, "c_spput")
    E(adds_imm8, 6, 1)
    E(cmp_imm, 6, NK if v2 else NPAR)
    E(b_cond, "bt_cl", "lo")
    E(mov_reg, 0, 4)
    E(bl, "c_spdirty")
    E(b, "bt_p")
    a.label("bt_nd")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 5, 3)                                                  # no Duplicate: no source
    E(lsls_imm, 0, 6, 31 - BIT_CLEAR)
    E(b_cond, "bt_nc", "pl")
    E(bl, "c_spview")                                                     # Clear + the button, track views on the screen: the defaults
    E(cmp_imm, 0, NTRK)
    bc("bt_p", "hs")
    E(mov_reg, 0, 4)
    E(bl, "c_spreset")
    E(b, "bt_p")
    a.label("bt_nc")
    E(bl, "c_spshift")
    E(cmp_imm, 0, 0)
    bc("bt_p", "ne")
    E(bl, "c_spview")
    E(cmp_reg, 0, 4)
    bc("bt_p", "ne")                                                      # not the selected track (or not the track views)
    E(movs_imm, 1, 1)
    E(lsls_reg, 1, 4)
    E(ldrb_imm, 0, 5, 0)
    E(eors_reg, 0, 1)
    E(strb_imm, 0, 5, 0)                                                  # the page flipped
    a.label("bt_p")
    E(raw, popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    E(b_w, prev["btn"])

    # ---- c_spknob (the container's slot 4, the head of its chain: r0 = container, r1 = knob, r2 = delta)
    a.label("c_spknob")
    E(push_list, [0, 1, 2, 4, 5, 6, 7], lr=True)
    E(cmp_imm, 1, NPAR)
    bc("kn_p", "hs")
    E(bl, "c_spview")
    E(cmp_imm, 0, NTRK)
    bc("kn_p", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the track
    E(bl, "c_spst")
    E(cmp_imm, 0, 0)
    bc("kn_p", "eq")
    E(ldrb_imm, 0, 0, 0)
    E(lsrs_reg, 0, 4)
    E(lsls_imm, 0, 0, 31)
    bc("kn_p", "eq")                                                      # the stock page
    imm32(0, CONT)
    E(bl, SUBVIEW)
    E(cmp_imm, 0, 0)
    bc("kn_p", "eq")                                                      # no knobs in this mode
    E(ldr_sp, 5, 4)                                                       # r5 = the knob
    if v2:
        E(movs_imm, 7, STEP)                                              # r7 = the step
        E(bl, "c_spshift")
        E(cmp_imm, 5, 4)
        E(b_cond, "kn_hi", "hs")
        E(cmp_imm, 0, 0)
        E(b_cond, "kn_c", "eq")
        E(movs_imm, 7, FINE)                                              # K1-K4: Shift = fine control
        E(b, "kn_c")
        a.label("kn_hi")
        if k6swap:                                                        # K6: follow; Shift + K6: the type
            E(cmp_imm, 5, K6)
            E(b_cond, "kn_n6", "ne")
            E(cmp_imm, 0, 0)
            E(b_cond, "kn_c", "ne")
            E(movs_imm, 5, I_FOLLOW)
            E(b, "kn_c")
            a.label("kn_n6")
        E(cmp_imm, 0, 0)
        E(b_cond, "kn_c", "eq")
        E(adds_imm8, 5, 4)                                                # Shift + K5-K8: the second layer (8..11)
        a.label("kn_c")
        E(bl, "c_spheld")
        E(lsls_imm, 0, 0, 31 - BIT_CLEAR)
        E(b_cond, "kn_t2", "pl")
        if k6swap:                                                        # (RH34) Clear + K5-K8: both layers back to their defaults
            E(cmp_imm, 5, 4)                                              # (the user, 2026-10-25: «make clear +knob affect shift functions too»)
            E(b_cond, "kn_cd", "lo")
            E(mov_reg, 1, 5)
            E(cmp_imm, 5, NPAR)
            E(b_cond, "kn_ol", "hs")
            E(adds_imm8, 1, 4)
            E(b, "kn_o")
            a.label("kn_ol")
            E(subs_imm8, 1, 4)
            a.label("kn_o")                                               # r1 = the knob's other layer
            imm32(0, t_defu)
            E(lsls_imm, 2, 1, 1)
            E(adds_reg, 0, 0, 2)
            E(ldrh_imm, 2, 0, 0)
            E(mov_reg, 0, 4)
            E(bl, "c_spput")
            a.label("kn_cd")
        imm32(0, t_defu)                                                  # Clear + the knob: its default (of the layer)
        E(lsls_imm, 1, 5, 1)
        E(adds_reg, 0, 0, 1)
        E(ldrh_imm, 6, 0, 0)
        E(b, "kn_w")
        a.label("kn_t2")
        E(mov_reg, 0, 4)
        E(mov_reg, 1, 5)
        E(bl, "c_spval")
        E(mov_reg, 6, 0)
        E(b, "kn_s")
    else:
        E(cmp_imm, 5, 4)
        bc("kn_x", "hs")                                                  # K5-K8: nothing yet
    E(bl, "c_spheld")
    E(lsls_imm, 0, 0, 31 - BIT_CLEAR)
    E(b_cond, "kn_t", "pl")
    imm32(0, t_def)                                                       # Clear + the knob: its default
    E(lsls_imm, 1, 5, 1)
    E(adds_reg, 0, 0, 1)
    E(ldrh_imm, 6, 0, 0)
    E(b, "kn_w")
    a.label("kn_t")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(bl, "c_spval")
    E(mov_reg, 6, 0)                                                      # r6 = the value
    E(bl, "c_spshift")
    E(movs_imm, 7, STEP)
    E(cmp_imm, 0, 0)
    E(b_cond, "kn_s", "eq")
    E(movs_imm, 7, FINE)
    a.label("kn_s")
    E(ldr_sp, 0, 8)                                                       # the delta
    E(muls, 7, 0)
    E(adds_reg, 6, 6, 7)
    E(cmp_imm, 6, 0)
    E(b_cond, "kn_h", "ge")
    E(movs_imm, 6, 0)
    a.label("kn_h")
    E(movw, 0, FULL)
    E(cmp_reg, 6, 0)
    E(b_cond, "kn_w", "le")
    E(mov_reg, 6, 0)
    a.label("kn_w")
    E(mov_reg, 0, 4)
    E(mov_reg, 1, 5)
    E(mov_reg, 2, 6)
    E(bl, "c_spput")
    E(mov_reg, 0, 4)
    E(bl, "c_spdirty")
    a.label("kn_x")
    E(pop_list, [0, 1, 2, 4, 5, 6, 7], pc=True)
    a.label("kn_p")
    E(raw, popw([0, 1, 2, 4, 5, 6, 7], lr=True))
    E(b_w, prev["knob"])

    if v2:
        # ---- the "SQ" block (Shift + K5-K8): c_sqblk, c_sqsum, c_sqok, c_sqval(t, k'), c_sqput(t, k', v) as block "SP"'s
        a.label("c_sqblk")
        E(push_list, [4], lr=True)
        E(bl, L["c_rrt"])
        E(cmp_imm, 0, 0)
        E(b_cond, "qb_x", "eq")
        E(movw, 1, BLK2)
        E(adds_reg, 0, 0, 1)
        a.label("qb_x")
        E(pop_list, [4], pc=True)
        a.label("c_sqsum")
        E(adds_imm8, 0, 4)
        E(movs_imm, 1, 2 * 4 * NTRK)
        E(movs_imm, 2, CHECK)
        a.label("qs_l")
        E(ldrb_imm, 3, 0, 0)
        E(eors_reg, 2, 3)
        E(adds_imm8, 0, 1)
        E(subs_imm8, 1, 1)
        E(b_cond, "qs_l", "ne")
        E(mov_reg, 0, 2)
        E(raw, h(0x4770))
        a.label("c_sqok")
        E(push_list, [4], lr=True)
        E(mov_reg, 4, 0)
        E(ldrb_imm, 1, 4, 0)
        E(cmp_imm, 1, MARK0)
        E(b_cond, "qo_0", "ne")
        E(ldrb_imm, 1, 4, 1)
        E(cmp_imm, 1, MARK2)
        E(b_cond, "qo_0", "ne")
        E(bl, "c_sqsum")
        E(ldrb_imm, 1, 4, 2)
        E(cmp_reg, 0, 1)
        E(b_cond, "qo_0", "ne")
        E(movs_imm, 0, 1)
        E(pop_list, [4], pc=True)
        a.label("qo_0")
        E(movs_imm, 0, 0)
        E(pop_list, [4], pc=True)
        a.label("c_sqval")                                                # (r0 = track, r1 = k' 0..3) -> the value
        E(push_list, [4, 5, 6], lr=True)
        E(lsls_imm, 4, 0, 2)
        E(adds_reg, 4, 4, 1)
        E(lsls_imm, 4, 4, 1)                                              # r4 = 2 (4 t + k')
        E(lsls_imm, 6, 1, 1)
        E(bl, "c_sqblk")
        E(cmp_imm, 0, 0)
        E(b_cond, "qv_d", "eq")
        E(mov_reg, 5, 0)
        E(bl, "c_sqok")
        E(cmp_imm, 0, 0)
        E(b_cond, "qv_d", "eq")
        E(adds_reg, 5, 5, 4)
        E(ldrh_imm, 0, 5, 4)
        E(pop_list, [4, 5, 6], pc=True)
        a.label("qv_d")
        imm32(0, t_def2)
        E(adds_reg, 0, 0, 6)
        E(ldrh_imm, 0, 0, 0)
        E(pop_list, [4, 5, 6], pc=True)
        a.label("c_sqput")                                                # (r0 = track, r1 = k', r2 = value)
        E(push_list, [3, 4, 5, 6, 7], lr=True)
        E(lsls_imm, 4, 0, 2)
        E(adds_reg, 4, 4, 1)
        E(lsls_imm, 4, 4, 1)
        E(mov_reg, 6, 2)
        E(bl, "c_sqblk")
        E(cmp_imm, 0, 0)
        E(b_cond, "qp_x", "eq")
        E(mov_reg, 5, 0)
        E(bl, "c_sqok")
        E(cmp_imm, 0, 0)
        E(b_cond, "qp_w", "ne")
        E(movs_imm, 0, MARK0)
        E(strb_imm, 0, 5, 0)
        E(movs_imm, 0, MARK2)
        E(strb_imm, 0, 5, 1)
        E(movs_imm, 0, 0)
        E(strb_imm, 0, 5, 3)
        E(movs_imm, 7, 0)
        a.label("qp_i")
        imm32(0, t_def2)
        E(movs_imm, 1, 2 * 4 - 1)
        E(raw, h(0x4039))                                                 # ands r1, r7: (2 i) mod 8 = 2 k'
        E(adds_reg, 0, 0, 1)
        E(ldrh_imm, 0, 0, 0)
        E(adds_reg, 1, 5, 7)
        E(strh_imm, 0, 1, 4)
        E(adds_imm8, 7, 2)
        E(cmp_imm, 7, 2 * 4 * NTRK)
        E(b_cond, "qp_i", "lo")
        a.label("qp_w")
        E(adds_reg, 1, 5, 4)
        E(strh_imm, 6, 1, 4)
        E(mov_reg, 0, 5)
        E(bl, "c_sqsum")
        E(strb_imm, 0, 5, 2)
        a.label("qp_x")
        E(pop_list, [3, 4, 5, 6, 7], pc=True)
        # ---- c_spval(r0 = track, r1 = 0..11) -> the value (K7 unXORed); c_spput(r0, r1, r2 = value); clobber r1-r3 / r0-r3
        a.label("c_spval")
        E(push_list, [4], lr=True)
        E(mov_reg, 4, 1)
        E(cmp_imm, 1, NPAR)
        E(b_cond, "xv_b", "hs")
        E(bl, VAL)
        if k8sync:
            E(cmp_imm, 4, K8)
            E(b_cond, "xv_x", "eq")
        E(cmp_imm, 4, K7)
        E(b_cond, "xv_r", "ne")
        a.label("xv_x")
        E(movw, 1, X7)
        E(eors_reg, 0, 1)
        if fitflag:                                                       # (bit 14 of K7: stfit's «on near the middle» flag, not the value)
            E(lsls_imm, 0, 0, 18)
            E(lsrs_imm, 0, 0, 18)
        a.label("xv_r")
        E(pop_list, [4], pc=True)
        a.label("xv_b")
        E(subs_imm8, 1, NPAR)
        E(bl, "c_sqval")
        E(pop_list, [4], pc=True)
        a.label("c_spput")
        E(push_list, [4], lr=True)
        E(cmp_imm, 1, NPAR)
        E(b_cond, "xp_b", "hs")
        if k8sync:
            E(cmp_imm, 1, K8)
            E(b_cond, "xp_x", "eq")
        E(cmp_imm, 1, K7)
        E(b_cond, "xp_a", "ne")
        a.label("xp_x")
        E(movw, 3, X7)
        E(eors_reg, 2, 3)
        a.label("xp_a")
        E(bl, PUT)
        E(pop_list, [4], pc=True)
        a.label("xp_b")
        E(subs_imm8, 1, NPAR)
        E(bl, "c_sqput")
        E(pop_list, [4], pc=True)

    # ---- c_spint(r0 = table, r1 = value) -> r0 = the table at value / 128, interpolated; clobbers r1-r3
    a.label("c_spint")
    E(lsrs_imm, 2, 1, 7)
    E(lsls_imm, 2, 2, 2)
    E(adds_reg, 0, 0, 2)
    E(ldr_imm, 2, 0, 0)
    E(ldr_imm, 3, 0, 4)
    E(subs_reg, 3, 3, 2)
    E(lsls_imm, 1, 1, 25)
    E(lsrs_imm, 1, 1, 25)
    E(muls, 3, 1)
    E(lsrs_imm, 3, 3, 7)
    E(adds_reg, 0, 2, 3)
    E(raw, h(0x4770))

    # ---- c_spw(r0 = word, r1 = Y address of core 1): 0x08031200(1, word << 8, $8000 | address); clobbers r0-r3, r12
    a.label("c_spw")
    E(push_list, [4], lr=True)
    E(lsls_imm, 0, 0, 8)
    E(mov_reg, 2, 1)
    E(movw, 1, 0x8000)
    E(orrs_reg, 2, 1)
    E(mov_reg, 1, 0)
    E(movs_imm, 0, 1)
    E(bl, WR16)
    E(pop_list, [4], pc=True)

    # ---- c_spdsp(r0 = track): its four words into core 1; clobbers r0-r3, r12
    a.label("c_spdsp")
    E(push_list, [3, 4, 5], lr=True)
    E(mov_reg, 4, 0)
    E(movs_imm, 1, 0)
    E(bl, "c_spval")
    E(movw, 1, 8192)
    E(subs_reg, 0, 0, 1)
    E(movs_imm, 1, A_SCALE)
    E(muls, 0, 1)
    E(movw, 1, YB + PM.OFF_A)
    E(adds_reg, 1, 1, 4)
    E(bl, "c_spw")
    for k, tab, off in ((1, t_dec, PM.OFF_D),) + (() if k3sync else ((2, t_rate, PM.OFF_R),)):
        E(mov_reg, 0, 4)
        E(movs_imm, 1, k)
        E(bl, "c_spval")
        E(mov_reg, 1, 0)
        imm32(0, tab)
        E(bl, "c_spint")
        E(movw, 1, YB + off)
        E(adds_reg, 1, 1, 4)
        E(bl, "c_spw")
    if k3sync:                                                            # K3: the LFO's rate (free / at the tempo / off: the phase at the centre)
        E(mov_reg, 0, 4)
        E(bl, "c_k3r")
        E(mov_reg, 5, 0)
        E(movw, 1, YB + PM.OFF_R)
        E(adds_reg, 1, 1, 4)
        E(bl, "c_spw")
        E(cmp_imm, 5, 0)
        E(b_cond, "sd_k3", "ne")
        imm32(0, K3_MIDPH)
        E(movw, 1, YB + PM.OFF_PH)
        E(adds_reg, 1, 1, 4)
        E(bl, "c_spw")
        a.label("sd_k3")
    E(mov_reg, 0, 4)
    E(movs_imm, 1, 3)
    E(bl, "c_spval")
    E(movs_imm, 1, L_SCALE)
    E(muls, 0, 1)
    E(movw, 1, YB + PM.OFF_L)
    E(adds_reg, 1, 1, 4)
    E(bl, "c_spw")
    if v2:
        import stretch as STR
        import voicefilt as F
        import voicefx as V
        vy = V.Y_BASE + (YB - PM.Y_BASE)

        def val(k):
            E(mov_reg, 0, 4)
            E(movs_imm, 1, k)
            E(bl, "c_spval")

        def put(addr):                                                    # r0 = the word -> Y:addr + t
            E(movw, 1, addr)
            E(adds_reg, 1, 1, 4)
            E(bl, "c_spw")

        def tab(k, t, addr):
            val(k)
            E(mov_reg, 1, 0)
            imm32(0, t)
            E(bl, "c_spint")
            put(addr)
        val(4)                                                            # K5: the ring's amount
        E(lsls_imm, 0, 0, 9)
        put(vy + V.RAM)
        tab(8, t_ring, vy + V.RST)                                        # Shift + K5: its frequency
        val(5)                                                            # K6: the filter type, 3 zones: stock / 24 dB / comb
        E(movs_imm, 1, 3)
        E(muls, 0, 1)
        E(lsrs_imm, 0, 0, 14)
        E(mov_reg, 5, 0)
        put(F.KTYPE)
        E(cmp_imm, 5, 2)
        E(b_cond, "sd_nc", "eq")
        E(movs_imm, 0, 0)                                                 # not the comb: voicefx's mode off (voicefilt's POST sets 5 for the comb)
        put(vy + V.FMODE)
        a.label("sd_nc")
        val(9)                                                            # Shift + K6: pitch follow
        E(lsls_imm, 0, 0, 9)
        put(F.FOLLOW)
        val(K7)                                                           # K7: the stretch, 0.25x .. 4x, the middle (+- a click) = off
        E(mov_reg, 5, 0)
        E(movw, 1, X7)
        E(subs_reg, 0, 0, 1)
        E(b_cond, "sd_pos", "ge")
        E(raw, h(0x4240))                                                 # rsbs r0, r0, #0
        a.label("sd_pos")
        if fitflag:                                                       # K7 stored with bit 14 (stfit): off only at the middle itself
            E(push_list, [0])
            E(mov_reg, 0, 4)
            E(movs_imm, 1, K7)
            E(bl, VAL)
            E(lsls_imm, 1, 0, 17)
            E(pop_list, [0])
            E(b_cond, "sd_nf", "pl")
            E(movs_imm, 1, 0)
            E(cmp_imm, 0, 1)
            E(b_cond, "sd_sw", "lt")
            E(b, "sd_on")
            a.label("sd_nf")
        E(movs_imm, 1, 0)
        E(cmp_imm, 0, DEAD)
        E(b_cond, "sd_sw", "lt")
        if fitflag:
            a.label("sd_on")
        E(mov_reg, 1, 5)
        imm32(0, t_spd)
        E(bl, "c_spint")
        E(mov_reg, 1, 0)
        a.label("sd_sw")
        E(mov_reg, 0, 1)
        put(STR.STRETCH)
        val(10)                                                           # Shift + K7: the bitcrush (0 = off)
        E(cmp_imm, 0, 0)
        E(b_cond, "sd_cr", "ne")
        put(vy + V.DTYPE)
        E(b, "sd_k8")
        a.label("sd_cr")
        E(movs_imm, 1, 14)
        E(muls, 0, 1)
        E(lsrs_imm, 0, 0, 14)
        E(movs_imm, 1, 8)                                                 # 24 - bits = 24 - (16 - x) = 8 + x
        E(adds_reg, 5, 0, 1)
        imm32(0, 0x080000)                                                # the gain: 0 dB (voicefx's 1/16)
        put(vy + V.DG)
        imm32(0, 0xFFFFFF)
        E(lsls_reg, 0, 5)
        imm32(1, 0xFFFFFF)
        E(raw, h(0x4008))                                                 # ands r0, r1
        put(vy + V.DMASK)
        E(movs_imm, 0, 4)
        put(vy + V.DTYPE)
        a.label("sd_k8")
        if k8sync:
            E(mov_reg, 0, 4)
            E(bl, "c_k8r")                                                # K8: the scan's rate (free / at the tempo / still)
            put(F.SCANR)
        else:
            tab(7, t_scan, F.SCANR)                                       # K8: the scan's speed
        val(11)                                                           # Shift + K8: its depth
        E(lsls_imm, 0, 0, 9)
        put(F.SCAND)
    E(pop_list, [3, 4, 5], pc=True)

    if k8sync:
        import voicefilt as F

        def k8div(rn):                                                    # r0 = K8's value - 8192 < 0 -> r0 = its division's index (0..15)
            E(raw, h(0x4240))                                             # rsbs r0, r0, #0
            E(subs_imm8, 0, DEAD)
            E(lsrs_imm, 0, 0, DIV_SHIFT)
            E(cmp_imm, 0, 15)
            E(b_cond, f"kd_{rn}", "le")
            E(movs_imm, 0, 15)
            a.label(f"kd_{rn}")

        # ---- c_k8r(r0 = track) -> r0 = SCANR: 0 in the middle, the free table right of it, BPM x KQ[i] >> 8 left of it; clobbers r1-r3
        a.label("c_k8r")
        E(push_list, [4], lr=True)
        E(movs_imm, 1, K8)
        E(bl, "c_spval")
        E(movw, 1, X7)
        E(subs_reg, 0, 0, 1)
        E(b_cond, "kr_l", "lt")
        E(cmp_imm, 0, DEAD)
        E(b_cond, "kr_0", "lt")
        E(lsls_imm, 1, 0, 1)
        imm32(0, t_scan)
        E(bl, "c_spint")
        E(pop_list, [4], pc=True)
        a.label("kr_l")
        E(mov_reg, 1, 0)
        E(raw, h(0x4249))                                                 # rsbs r1, r1, #0
        E(cmp_imm, 1, DEAD)
        E(b_cond, "kr_0", "lt")
        k8div("r")
        E(lsls_imm, 4, 0, 2)
        imm32(0, TEMPO)
        E(movs_imm, 1, 0)
        E(bl, CI.PARAM_NEW)
        E(ldrb_imm, 0, 0, 0)                                              # the BPM
        E(cmp_imm, 0, 30)
        E(b_cond, "kr_b", "hs")
        E(movs_imm, 0, 120)
        a.label("kr_b")
        imm32(1, t_kq)
        E(adds_reg, 1, 1, 4)
        E(ldr_imm, 1, 1, 0)
        E(muls, 0, 1)
        E(lsrs_imm, 0, 0, 8)
        E(pop_list, [4], pc=True)
        a.label("kr_0")
        E(movs_imm, 0, 0)
        E(pop_list, [4], pc=True)

        # ---- c_k8sync(): the global tick moved since the last frame -> every synced track's scan phase from it; clobbers r0-r3
        a.label("c_k8sync")
        E(push_list, [4, 5, 6, 7], lr=True)
        E(bl, L["c_rst"])
        E(cmp_imm, 0, 0)
        E(b_cond, "ks_x", "eq")
        E(adds_imm8, 0, O_K8T)
        E(mov_reg, 5, 0)                                                  # r5 = the tick last seen
        imm32(0, SEQ + 0x90)
        E(ldr_imm, 0, 0, 0)
        E(movs_imm, 1, 0)
        E(bl, CI.PARAM_NEW)
        E(ldr_imm, 7, 0, 0)                                               # r7 = the global tick
        E(ldr_imm, 0, 5, 0)
        E(cmp_reg, 0, 7)
        E(b_cond, "ks_x", "eq")
        E(str_imm, 7, 5, 0)
        E(movs_imm, 4, 0)
        a.label("ks_t")
        E(mov_reg, 0, 4)
        E(movs_imm, 1, K8)
        E(bl, "c_spval")
        E(movw, 1, X7)
        E(subs_reg, 0, 0, 1)
        E(b_cond, "ks_n", "ge")                                           # the middle or free: not ours
        E(mov_reg, 1, 0)
        E(raw, h(0x4249))                                                 # rsbs r1, r1, #0
        E(cmp_imm, 1, DEAD)
        E(b_cond, "ks_n", "lt")
        k8div("s")
        E(lsls_imm, 6, 0, 2)
        imm32(1, t_divs)
        E(adds_reg, 1, 1, 6)
        E(ldr_imm, 1, 1, 0)                                               # D
        E(raw, CI.udiv(0, 7, 1))
        E(muls, 0, 1)
        E(subs_reg, 0, 7, 0)                                              # tick mod D
        imm32(1, t_phq)
        E(adds_reg, 1, 1, 6)
        E(ldr_imm, 1, 1, 0)
        E(muls, 0, 1)                                                     # the phase (c_spw keeps its 24 low bits)
        E(movw, 1, F.SCANPH)
        E(adds_reg, 1, 1, 4)
        E(bl, "c_spw")
        a.label("ks_n")
        E(adds_imm8, 4, 1)
        E(cmp_imm, 4, NTRK)
        E(b_cond, "ks_t", "lo")
        a.label("ks_x")
        E(pop_list, [4, 5, 6, 7], pc=True)

    if k3sync:
        # ---- c_k3r(r0 = track) -> r0 = R, the LFO's step: 0 in the middle, the rate table right of it, BPM x KQ[i] >> 8 left of it;
        #      clobbers r1-r3
        a.label("c_k3r")
        E(push_list, [4], lr=True)
        E(movs_imm, 1, K3)
        E(bl, "c_spval")
        E(movw, 1, X7)
        E(subs_reg, 0, 0, 1)
        E(b_cond, "k3_l", "lt")
        E(cmp_imm, 0, DEAD)
        E(b_cond, "k3_0", "lt")
        E(lsls_imm, 1, 0, 1)
        imm32(0, t_rate)
        E(bl, "c_spint")
        E(pop_list, [4], pc=True)
        a.label("k3_l")
        E(mov_reg, 1, 0)
        E(raw, h(0x4249))                                                 # rsbs r1, r1, #0
        E(cmp_imm, 1, DEAD)
        E(b_cond, "k3_0", "lt")
        k8div("3r")
        E(lsls_imm, 4, 0, 2)
        imm32(0, TEMPO)
        E(movs_imm, 1, 0)
        E(bl, CI.PARAM_NEW)
        E(ldrb_imm, 0, 0, 0)                                              # the BPM
        E(cmp_imm, 0, 30)
        E(b_cond, "k3_b", "hs")
        E(movs_imm, 0, 120)
        a.label("k3_b")
        imm32(1, t_kq)
        E(adds_reg, 1, 1, 4)
        E(ldr_imm, 1, 1, 0)
        E(muls, 0, 1)
        E(lsrs_imm, 0, 0, 8)
        E(pop_list, [4], pc=True)
        a.label("k3_0")
        E(movs_imm, 0, 0)
        E(pop_list, [4], pc=True)

        # ---- c_k3sync(): the global tick moved since the last frame (c_k8sync keeps it, after this) -> every synced track's LFO phase:
        #      (tick mod D) / D of a cycle from the centre rising; clobbers r0-r3
        a.label("c_k3sync")
        E(push_list, [4, 5, 6, 7], lr=True)
        E(bl, L["c_rst"])
        E(cmp_imm, 0, 0)
        E(b_cond, "k3s_x", "eq")
        E(adds_imm8, 0, O_K8T)
        E(mov_reg, 5, 0)                                                  # r5 = the tick last seen
        imm32(0, SEQ + 0x90)
        E(ldr_imm, 0, 0, 0)
        E(movs_imm, 1, 0)
        E(bl, CI.PARAM_NEW)
        E(ldr_imm, 7, 0, 0)                                               # r7 = the global tick
        E(ldr_imm, 0, 5, 0)
        E(cmp_reg, 0, 7)
        E(b_cond, "k3s_x", "eq")
        E(movs_imm, 4, 0)
        a.label("k3s_t")
        E(mov_reg, 0, 4)
        E(movs_imm, 1, K3)
        E(bl, "c_spval")
        E(movw, 1, X7)
        E(subs_reg, 0, 0, 1)
        E(b_cond, "k3s_n", "ge")                                          # the middle or free: not ours
        E(mov_reg, 1, 0)
        E(raw, h(0x4249))                                                 # rsbs r1, r1, #0
        E(cmp_imm, 1, DEAD)
        E(b_cond, "k3s_n", "lt")
        k8div("3s")
        E(lsls_imm, 6, 0, 2)
        imm32(1, t_divs)
        E(adds_reg, 1, 1, 6)
        E(ldr_imm, 1, 1, 0)                                               # D
        E(raw, CI.udiv(0, 7, 1))
        E(muls, 0, 1)
        E(subs_reg, 0, 7, 0)                                              # tick mod D
        imm32(1, t_phq)
        E(adds_reg, 1, 1, 6)
        E(ldr_imm, 1, 1, 0)
        E(muls, 0, 1)
        imm32(1, K3_MIDPH)
        E(adds_reg, 0, 0, 1)                                              # from the centre (c_spw keeps the 24 low bits)
        E(movw, 1, YB + PM.OFF_PH)
        E(adds_reg, 1, 1, 4)
        E(bl, "c_spw")
        a.label("k3s_n")
        E(adds_imm8, 4, 1)
        E(cmp_imm, 4, NTRK)
        E(b_cond, "k3s_t", "lo")
        a.label("k3s_x")
        E(pop_list, [4, 5, 6, 7], pc=True)

    if v2:
        # ---- c_spgrain(): the stretch's grain words (one size for every track: 2048)
        import stretch as STR
        a.label("c_spgrain")
        E(push_list, [4], lr=True)
        for addr, w in STR.grain_words(GRAIN, ghm=True).items():
            imm32(0, w)
            E(movw, 1, addr)
            E(bl, "c_spw")
        E(pop_list, [4], pc=True)

    # ---- c_spled (the LED task's calls: ctrl, frame): the chain, then the DSP's round and the Stock+ page's LEDs
    a.label("c_spled")
    E(push_list, [3, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 1)                                                      # r5 = the frame
    E(bl, prev["ledtask"])
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(bl, "c_spst")
    E(cmp_imm, 0, 0)
    bc("ld_x", "eq")
    E(mov_reg, 6, 0)                                                      # r6 = our state
    E(bl, "c_spheld")
    E(lsls_imm, 0, 0, 31 - BIT_DUP)
    E(b_cond, "ld_h", "mi")
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 6, 3)                                                  # Duplicate let go: no source
    a.label("ld_h")
    E(mov_reg, 0, 6)
    E(subs_imm8, 0, O_ST - O_TH)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, TH.READY)
    if wait:
        E(b_cond, "ld_rdy", "eq")
        E(movs_imm, 0, 0)                                                 # not the mode 0 program: no DSP writes, the wait from 0
        E(strb_imm, 0, 6, O_W - O_ST)
        E(b, "ld_v")
        a.label("ld_rdy")
        E(ldrb_imm, 0, 6, O_W - O_ST)
        E(cmp_imm, 0, SP_WAIT)
        E(b_cond, "ld_go", "hs")
        E(adds_imm8, 0, 1)                                                # core 1 still starting: wait
        E(strb_imm, 0, 6, O_W - O_ST)
        E(b, "ld_v")
        a.label("ld_go")
    else:
        E(b_cond, "ld_v", "ne")                                           # not the mode 0 program: no DSP writes
    E(ldrb_imm, 7, 6, 2)
    E(adds_imm8, 7, 1)
    E(movs_imm, 0, NTRK - 1)
    E(raw, h(0x4007))                                                     # ands r7, r0
    E(strb_imm, 7, 6, 2)                                                  # the round's track
    if v2:
        E(cmp_imm, 7, 0)
        E(b_cond, "ld_ng", "ne")
        E(bl, "c_spgrain")                                                # once a round: the grain words (core 1 clears them at its start)
        E(ldrb_imm, 7, 6, 2)
        a.label("ld_ng")
    E(movs_imm, 0, 1)
    E(lsls_reg, 0, 7)
    E(ldrb_imm, 7, 6, 1)
    E(orrs_reg, 7, 0)                                                     # r7 = the tracks to push
    E(movs_imm, 0, 0)
    E(strb_imm, 0, 6, 1)
    E(movs_imm, 4, 0)
    a.label("ld_d")
    E(mov_reg, 0, 7)
    E(lsrs_reg, 0, 4)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "ld_dn", "eq")
    E(mov_reg, 0, 4)
    E(bl, "c_spdsp")
    a.label("ld_dn")
    E(adds_imm8, 4, 1)
    E(cmp_imm, 4, NTRK)
    E(b_cond, "ld_d", "lo")
    if k3sync:
        E(bl, "c_k3sync")
    if k8sync:
        E(bl, "c_k8sync")
    a.label("ld_v")
    E(bl, "c_spview")
    E(cmp_imm, 0, NTRK)
    bc("ld_x", "hs")
    E(mov_reg, 4, 0)                                                      # r4 = the track
    E(ldrb_imm, 0, 6, 0)
    E(lsrs_reg, 0, 4)
    E(lsls_imm, 0, 0, 31)
    bc("ld_x", "eq")                                                      # the stock page
    E(mov_reg, 7, 6)
    E(subs_imm8, 7, O_ST - O_KB)                                          # r7 = kbright's overlay
    E(movs_imm, 0, 0xFF if v2 else 0x0F)
    E(strb_imm, 0, 7, K_MASK)
    for k in range(8 if v2 else 4):
        if k6swap and k == K6:                                            # K6: the type's colour, the follow's brightness (Shift: full)
            E(mov_reg, 0, 4)
            E(movs_imm, 1, I_TYPE)
            E(bl, "c_spval")
            E(movs_imm, 1, 3)
            E(muls, 0, 1)
            E(lsrs_imm, 0, 0, 14)                                         # 0 / 1 / 2
            E(lsls_imm, 0, 0, 1)
            imm32(1, t_cols)
            E(adds_reg, 1, 1, 0)
            E(ldrh_imm, 0, 1, 0)
            E(strh_imm, 0, 7, K_CODE + 2 * k)
            E(strh_w_imm, 0, 5, 2 * (LED_KNOB0 + k))
            E(bl, "c_spshift")
            E(cmp_imm, 0, 0)
            E(b_cond, "lk_f6", "eq")
            E(movs_imm, 0, 127)
            E(b, "lk_w6")
            a.label("lk_f6")
            E(mov_reg, 0, 4)
            E(movs_imm, 1, I_FOLLOW)
            E(bl, "c_spval")
            E(lsrs_imm, 0, 0, 7)
            E(cmp_imm, 0, K6_MIN)
            E(b_cond, "lk_w6", "ge")
            E(movs_imm, 0, K6_MIN)
            a.label("lk_w6")
            E(strb_imm, 0, 7, K_VAL + k)
            continue
        if k >= 4:                                                        # (v2) K5-K8: the Shift layer while Shift is held
            E(bl, "c_spshift")
            E(movs_imm, 1, k)
            E(cmp_imm, 0, 0)
            E(b_cond, f"lk_m{k}", "eq")
            E(movs_imm, 1, k + 4)
            a.label(f"lk_m{k}")
            E(mov_reg, 0, 4)
        else:
            E(mov_reg, 0, 4)
            E(movs_imm, 1, k)
        mid = k == K7 or (k8sync and k == K8) or (k3sync and k == K3)     # K7 (the stretch; k8sync: K8, k3sync: K3 too): from the middle
        if mid:
            E(mov_reg, 6, 1)
            E(push_list, [6])
        E(bl, "c_spval")
        if mid:
            E(pop_list, [1])
            E(cmp_imm, 1, k)
            E(b_cond, f"lk_q{k}", "ne")
            E(movw, 1, X7)
            E(subs_reg, 0, 0, 1)
            E(b_cond, f"lk_n{k}", "ge")
            E(raw, h(0x4240))
            a.label(f"lk_n{k}")
            E(lsls_imm, 0, 0, 1)
            a.label(f"lk_q{k}")
            E(mov_reg, 6, 7)
            E(adds_imm8, 6, O_ST - O_KB)                                  # (r6 back: our state = the overlay + (O_ST - O_KB))
        E(lsrs_imm, 0, 0, 7)                                              # 0..127
        if mid:
            E(cmp_imm, 0, 127)
            E(b_cond, f"lk_c{k}", "le")
            E(movs_imm, 0, 127)
            a.label(f"lk_c{k}")
        if k == 0:
            E(subs_imm8, 0, 64)
            E(b_cond, f"lk_p{k}", "ge")
            E(raw, h(0x4240))                                             # rsbs r0, r0, #0
            a.label(f"lk_p{k}")
            E(lsls_imm, 0, 0, 1)
            E(cmp_imm, 0, 127)
            E(b_cond, f"lk_c{k}", "le")
            E(movs_imm, 0, 127)
            a.label(f"lk_c{k}")
        E(strb_imm, 0, 7, K_VAL + k)
        imm32(0, COL_KNOB)
        E(strh_imm, 0, 7, K_CODE + 2 * k)
        E(strh_w_imm, 0, 5, 2 * (LED_KNOB0 + k))
    if not v2:
        E(movs_imm, 0, 0)
        for k in range(4, 8):
            E(strh_w_imm, 0, 5, 2 * (LED_KNOB0 + k))
    imm32(0, HAL_TICK)
    E(ldr_imm, 0, 0, 0)
    E(lsls_imm, 0, 0, 23)                                                 # bit 8 of the tick
    E(b_cond, "ld_x", "pl")
    E(movs_imm, 0, COL_BLINK)
    E(lsls_imm, 1, 4, 1)
    E(adds_reg, 1, 5, 1)
    E(strh_w_imm, 0, 1, 2 * LED_TRK0)
    E(strh_w_imm, 0, 1, 2 * LED_TRK1)
    a.label("ld_x")
    E(pop_list, [3, 4, 5, 6, 7], pc=True)
    return a.assemble()


def install(img, report, base_addr, shift=0, v2=False, k6swap=False, wait=False, k8sync=False, fitflag=False, k3sync=False):
    """Append the code; the head of the button chain, the head of the container's knob slot, the LED task calls (outermost).  pitchmod's
    core 1 code (tools/pitchmod.py, without dspload) must be in the build too, with the same shift."""
    global YB
    YB = PM.Y_BASE + shift
    assert report["pitchmod"]["y_base"] == hex(YB), "stockplus and pitchmod with different shifts"
    import struct
    import rhbuild
    BASE = rhbuild.BASE
    u = lambda a_: struct.unpack_from("<I", img, a_ - BASE)[0]
    lab = lambda m, k: int(report[m]["labels"][k], 16)
    for need in ("kbright", "cthresh", "pitchmod"):
        assert need in report, f"stockplus needs {need}"
    L = dict(c_rst=lab("rhstate", "c_rst"), c_rrt=lab("rhrec", "c_rrt"), c_ciok=lab("countin", "c_ciok"))
    prev = dict(btn=rhbuild.bw_target(img, CI.BTN_ENTRY), knob=u(SLOT_KNOB) & ~1, ledtask=rhbuild.bl_target(img, CI.LED_CALLS[0]))
    assert all(rhbuild.bl_target(img, c) == prev["ledtask"] for c in CI.LED_CALLS)
    assert v2 or not k6swap
    assert k6swap or not k8sync
    assert v2 or not fitflag
    assert k8sync or not k3sync
    code, labels = arm_code(base_addr, L, prev, v2=v2, k6swap=k6swap, wait=wait, k8sync=k8sync, fitflag=fitflag, k3sync=k3sync)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, CI.BTN_ENTRY, f"b.w #{prev['btn']:#x}", b_w(CI.BTN_ENTRY, labels["c_spbtn"]))
    rhbuild.patch_word(img, SLOT_KNOB, prev["knob"] | 1, labels["c_spknob"] | 1)
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{prev['ledtask']:#x}", bl(c, labels["c_spled"]))
    report["stockplus"] = dict(prev={k: hex(v) for k, v in prev.items()}, tables=hex(base_addr), v2=v2, k6swap=k6swap, wait=wait, k8sync=k8sync,
                               **({"fitflag": True, "t_spd": hex(base_addr + 8 * 129 + 2 * NPAR + 4 * 129)} if fitflag else {}),
                               **({"k3sync": True} if k3sync else {}),
                               labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
