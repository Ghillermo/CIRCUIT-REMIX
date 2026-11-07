"""CIRCUIT-HACKS' FM voice data on the Rhythm (MIT; RD38): the 16 parameters, the ratios, the attack / release tables, the 16 algorithms, the
voicings and the 16 starters (fmeng.py, SC45.6-SC48: our own), and the words of fm0's block from them.

Parameters (Hacks' P_*): 0-3 the ratio positions of operators 1-4 (24 ratios; the clicks inside one = a fine detune), 4-7 their levels, 8-11
their Shift knobs (64.. = attack (v - 64) >> 1, the algorithm's sustain; < 64 = percussive, a decay of index v), 12 the algorithm (x 8),
13 feedback, 14 noise, 15 release.  words(): Hacks' c_fmenv / c_fmsend arithmetic at the note (velocity, note), the per-millisecond
envelope rates turned into per-block ones (a block = 2 / 3 ms); fm0 runs the envelopes.  Not yet: the brightness (no oscillator shape on
the Rhythm: x 1) and the aliasing caps of the modulators.
"""
from __future__ import annotations

import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fm0 as F  # noqa: E402

P_RAT, P_LEV, P_ATK, P_ALG, P_FB, P_NZ, P_REL = 0, 4, 8, 12, 13, 14, 15
RATIOS = (0.5, 0.71, 1, 1.41, 1.5, 2, 2.5, 3, 3.5, 4, 4.24, 5, 5.5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16)
ATK_MS = [0] + [round(2 * 1500 ** (i / 30)) for i in range(31)]                       # 32 attack times
REL_TAU = [3 * (8000 / 3) ** (i / 63) for i in range(64)]                             # 64 release time constants (ms)
BLOCK_MS = 32 / 48.0
CENTRE = 64
VS = (96,) * 8 + (160, 160, 112, 160, 128, 128, 48, 48)                               # velocity -> index per algorithm
KS = (2, 2, 2, 2, 2, 2, 2, 0, 0, 0, 0, 0, 3, 3, 2, 2)                                  # keyboard scaling per algorithm


def alg(name, fam, mods=(), car=(1,), sus=(1, 1, 1, 1), pitch=False, noise=1, det=(1, 1, 1, 1), relofs=(0, 0, 0, 0), fb=4):
    mask = 0
    for s_, d_ in mods:
        mask |= 1 << (4 * (d_ - 1) + (s_ - 1))
    return dict(name=name, fam=fam, mask=mask, car=car, sus=sus, pitch=pitch, noise=noise, det=det, relofs=relofs, fb=fb)


ALGS = [
    alg("stack 4-3-2-1", 0, mods=((4, 3), (3, 2), (2, 1))),
    alg("3+4 on 2, on 1", 0, mods=((4, 2), (3, 2), (2, 1))),
    alg("4 on 1, 3-2-1", 0, mods=((4, 1), (3, 2), (2, 1))),
    alg("4-3 on 1, 2 on 1", 0, mods=((4, 3), (3, 1), (2, 1))),
    alg("two stacks", 0, mods=((4, 3), (2, 1)), car=(1, 3)),
    alg("4 on three", 0, mods=((4, 1), (4, 2), (4, 3)), car=(1, 2, 3)),
    alg("4-3, 2, 1", 0, mods=((4, 3),), car=(1, 2, 3)),
    alg("organ", 0, car=(1, 2, 3, 4)),
    alg("kick", 1, mods=((2, 1),), sus=(0, 0, 0, 0), pitch=True, relofs=(0, -8, 0, -10), fb=2),
    alg("snare", 1, mods=((2, 1),), sus=(0, 0, 0, 0), pitch=True, noise=3, relofs=(0, -6, 0, -8), fb=2),
    alg("metal / hat", 1, mods=((2, 1), (3, 1), (4, 1)), sus=(0, 0, 0, 0), det=(1, 1.414, 2.71, 3.49), relofs=(0, -4, -4, -4)),
    alg("tom / zap", 1, mods=((3, 2), (2, 1)), sus=(0, 0, 0, 0), pitch=True, relofs=(0, -6, -6, 0), fb=3),
    alg("bell", 2, mods=((2, 1), (4, 3)), car=(1, 3), sus=(0, 0, 0, 0), det=(1, 3.5, 2.0, 2.76), relofs=(6, 0, 6, 0)),
    alg("tubular", 2, mods=((2, 1), (3, 1)), car=(1, 4), sus=(0, 0, 0, 0), det=(1, 2.76, 5.4, 2.0), relofs=(8, 0, -4, 8)),
    alg("strings", 3, mods=((2, 1), (4, 3)), car=(1, 3), det=(1.0, 1.0, 1.007, 1.007)),
    alg("ensemble", 3, mods=((4, 1), (4, 2), (4, 3)), car=(1, 2, 3), det=(0.994, 1.0, 1.006, 1.0)),
]


def rpos(r):
    return (RATIOS.index(r) * 128 + 23) // 24


def atk(i):
    return CENTRE + 2 * i


R1 = rpos(1)
DEFAULTS2 = (R1, R1, R1, R1, 127, 64, 48, 32, CENTRE, CENTRE, CENTRE, CENTRE, 0, 0, 0, 64)
VOICINGS = [
    DEFAULTS2,
    (R1, R1, R1, rpos(2), 127, 72, 44, 40, atk(11), atk(14), CENTRE, CENTRE, 1 << 3, 24, 0, 50),
    (R1, R1, R1, rpos(14), 127, 56, 28, 36, CENTRE, 40, CENTRE, 22, 2 << 3, 0, 0, 70),
    (R1, R1, R1, rpos(2), 127, 72, 30, 30, CENTRE, 34, CENTRE, CENTRE, 3 << 3, 30, 0, 40),
    (R1, R1, R1, rpos(3), 110, 52, 110, 30, CENTRE, 44, CENTRE, 28, 4 << 3, 0, 0, 64),
    (rpos(0.5), R1, rpos(2), R1, 100, 100, 90, 40, atk(8), atk(8), atk(8), CENTRE, 5 << 3, 10, 0, 50),
    (R1, rpos(2), rpos(3), R1, 110, 80, 70, 40, 40, 40, 36, 34, 6 << 3, 0, 0, 40),
    (rpos(0.5), R1, rpos(2), rpos(3), 110, 127, 90, 70, CENTRE, CENTRE, CENTRE, CENTRE, 7 << 3, 0, 0, 30),
    (R1, R1, R1, R1, 127, 40, 0, 115, CENTRE, CENTRE, CENTRE, CENTRE, 8 << 3, 20, 0, 40),
    (R1, rpos(1.41), R1, R1, 110, 50, 0, 60, CENTRE, CENTRE, CENTRE, CENTRE, 9 << 3, 30, 90, 36),
    (R1, R1, R1, R1, 100, 90, 80, 70, CENTRE, CENTRE, CENTRE, CENTRE, 10 << 3, 60, 40, 20),
    (R1, R1, R1, R1, 127, 40, 30, 70, CENTRE, CENTRE, CENTRE, CENTRE, 11 << 3, 0, 0, 48),
    (R1, R1, R1, R1, 127, 70, 110, 60, CENTRE, CENTRE, CENTRE, CENTRE, 12 << 3, 0, 0, 100),
    (R1, R1, R1, R1, 127, 64, 50, 127, CENTRE, CENTRE, CENTRE, CENTRE, 13 << 3, 0, 0, 110),
    (R1, R1, R1, R1, 120, 50, 120, 50, atk(22), atk(20), atk(22), atk(20), 14 << 3, 0, 0, 90),
    (R1, R1, R1, R1, 110, 110, 110, 40, atk(21), atk(21), atk(21), atk(18), 15 << 3, 0, 0, 90),
]
STARTERS = [
    ("piano", (R1, R1, R1 + 1, rpos(3), 127, 70, 110, 52, 52, 44, 50, 30, 4 << 3, 0, 0, 50)),
    ("e-piano", (R1, R1, R1, rpos(14), 127, 56, 28, 36, 54, 40, CENTRE, 22, 2 << 3, 0, 0, 70)),
    ("organ", VOICINGS[7]),
    ("pluck", (R1, R1, rpos(3), R1, 127, 96, 34, 0, 42, 28, 24, CENTRE, 0, 0, 0, 30)),
    ("harp", (R1, rpos(2), R1, R1, 127, 34, 24, 0, 52, 38, 44, CENTRE, 3 << 3, 0, 0, 56)),
    ("marimba", (R1, rpos(4), rpos(4), R1, 127, 60, 40, 0, 38, 18, 28, CENTRE, 4 << 3, 0, 0, 30)),
    ("bass", VOICINGS[3]),
    ("bell", VOICINGS[12]),
    ("strings", VOICINGS[14]),
    ("pad", (rpos(0.5), R1 + 1, rpos(2), R1, 100, 100, 80, 36, atk(24), atk(24), atk(26), atk(26), 5 << 3, 8, 0, 100)),
    ("flute", (R1, R1, R1, R1, 127, 26, 0, 0, atk(16), atk(18), CENTRE, CENTRE, 0, 0, 22, 44)),
    ("clarinet", (R1, rpos(2), R1, R1, 127, 60, 0, 0, atk(14), atk(15), CENTRE, CENTRE, 0, 0, 4, 40)),
    ("brass", VOICINGS[1]),
    ("kick", VOICINGS[8]),
    ("snare", VOICINGS[9]),
    ("hat", VOICINGS[10]),
]
assert len(STARTERS) == 16 and len(VOICINGS) == 16 and len(ALGS) == 16
# RH71 (the user, 2026-11-04, after RH70: «patches need to be more percusive and pad, more full, since they aren't polyphonic» -> «Now, for
# mono»): the percussive ones decay while held (carriers ~0.2-0.7 s, modulators faster) with short releases; organ / strings / pad detuned
# between operators (the fine clicks), with feedback, fuller modulators and longer releases; the winds and drums as they were
_S2 = {
    "piano": (R1, R1, R1 + 1, rpos(3), 127, 70, 110, 52, 40, 30, 38, 22, 4 << 3, 0, 0, 30),
    "e-piano": (R1, R1, R1, rpos(14), 127, 56, 28, 36, 44, 30, 40, 18, 2 << 3, 0, 0, 40),
    "organ": (rpos(0.5), R1 + 1, rpos(2) + 1, rpos(3) + 1, 110, 127, 90, 70, CENTRE, CENTRE, CENTRE, CENTRE, 7 << 3, 16, 0, 40),
    "pluck": (R1, R1, rpos(3), R1, 127, 96, 34, 0, 34, 22, 18, CENTRE, 0, 0, 0, 24),
    "harp": (R1, rpos(2), R1, R1, 127, 34, 24, 0, 42, 30, 34, CENTRE, 3 << 3, 0, 0, 36),
    "marimba": (R1, rpos(4), rpos(4), R1, 127, 60, 40, 0, 30, 14, 22, CENTRE, 4 << 3, 0, 0, 24),
    "bass": (R1, R1, R1, rpos(2), 127, 72, 30, 30, 46, 30, CENTRE, CENTRE, 3 << 3, 30, 0, 30),
    "bell": (R1, R1, R1, R1, 127, 70, 110, 60, CENTRE, CENTRE, CENTRE, CENTRE, 12 << 3, 0, 0, 80),
    "strings": (R1, R1 + 1, R1, R1 + 2, 120, 64, 120, 64, atk(22), atk(20), atk(22), atk(20), 14 << 3, 20, 0, 100),
    "pad": (rpos(0.5), R1 + 2, rpos(2) + 1, R1 + 1, 110, 100, 90, 48, atk(24), atk(24), atk(26), atk(26), 5 << 3, 24, 0, 110),
}
STARTERS2 = [(n, _S2.get(n, v)) for n, v in STARTERS]
assert len({v for _, v in STARTERS2}) == 16 and all(max(v) <= 127 for _, v in STARTERS2)


def _f(x):
    return F.ONE if x >= 1 else max(0, round(x * (1 << 23)))


T_RAT = [round(r * 65536) for r in RATIOS]                                      # the tables the ARM has too (fmpage)
T_ATK = [F.ONE if m == 0 else _f(BLOCK_MS / m) for m in ATK_MS]
T_COEF = [_f(math.exp(-BLOCK_MS / t)) for t in REL_TAU]
PARAMS = (F.F_R0, F.F_L, F.F_K, F.F_M1, F.F_M2, F.F_M3, F.F_M4, F.F_HC, F.F_A, F.F_DH, F.F_DR)   # the ARM's words of an operator, in order
GLOBALS = (F.G_FLG, F.G_PD, F.G_NZ, F.G_NOP)


def coef(i):
    """a decay index (clamped 0..63) -> the factor a block"""
    return T_COEF[max(0, min(63, i))]


def words(p, vel=100, note=60):
    """the 16 parameters -> {offset: word} of fm0's block (the key included); integer arithmetic, as fmpage's ARM code"""
    ai = (p[P_ALG] >> 3) & 15
    a = ALGS[ai]
    gv = 256 - ((VS[ai] * (127 - min(127, vel))) >> 7)
    ks = max(32, 256 - KS[ai] * max(0, note - 60))
    G = (gv * ks) >> 8
    off = (vel - 64) >> 3
    if KS[ai] and note > 60:
        off -= (note - 60) >> 3
    w = {}
    for k in range(4):
        b = k * F.FMS
        pos = p[P_RAT + k] * 24
        fine = 4096 + 6 * (((pos & 127) * 171) >> 12)
        det = round(4096 * a["det"][k])
        w[b + F.F_R0] = min(0x7FFFFF, (((T_RAT[pos >> 7] * det) >> 12) * fine) >> 12)
        carrier = (k + 1) in a["car"]
        lv = p[P_LEV + k] * p[P_LEV + k] * 512
        if not carrier:
            lv = (lv * G) >> 8
        if a["pitch"] and k == 3:
            lv = 0
        w[b + F.F_L] = min(F.ONE, lv)
        w[b + F.F_K] = (0x3FFFFF // len(a["car"])) if carrier else 0
        v = p[P_ATK + k]
        ri = (p[P_REL] >> 1) + a["relofs"][k] + off
        if v >= CENTRE:
            w[b + F.F_A] = T_ATK[(v - CENTRE) >> 1]
            w[b + F.F_DH] = F.ONE if a["sus"][k] else coef(ri)
            w[b + F.F_DR] = coef(ri)
        else:
            w[b + F.F_A] = F.ONE
            w[b + F.F_DH] = coef(v + off)
            w[b + F.F_DR] = coef(min(v + off, ri))
        for j in range(4):
            w[b + F.F_M1 + j] = F.ONE if a["mask"] >> (4 * k + j) & 1 else 0
    fbk = a["fb"]
    hc = p[P_FB] * p[P_FB] * 512
    for k in range(4):
        w[k * F.FMS + F.F_HC] = hc if fbk == k + 1 else 0
    if fbk:
        w[(fbk - 1) * F.FMS + F.F_M1 + fbk - 1] = hc
    w[F.G_FLG] = 2 if a["fam"] in (1, 2) else 0
    w[F.G_PD] = (p[P_LEV + 3] * p[P_LEV + 3] * gv * 7) >> 2 if a["pitch"] else 0
    w[F.G_NZ] = p[P_NZ] * p[P_NZ] * 255
    w[F.G_NOP] = (a["noise"] - 1) * F.FMS
    w[F.G_KEY] = F.FMKEY
    return w


def starter(name, v2=False):
    return dict(STARTERS2 if v2 else STARTERS)[name]


def starters():
    """the set the build has (RH71 on: STARTERS2, OPT fmst2)"""
    import rhbuild
    return STARTERS2 if rhbuild.OPT.get("fmst2") else STARTERS
