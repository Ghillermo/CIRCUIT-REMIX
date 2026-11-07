"""The 8-operator FM's patch (MIT; RD40): CIRCUIT-HACKS' tools/fm8.py data model, ours, for the Circuit Rhythm (the same 216 parameter bytes,
the same 56 algorithms, the same DX7 import and own-slot record: a bank copied between a Tracks pack and a Rhythm pack keeps its sounds).  Not
here: the 4-operator patches' conversion (it needs the Tracks' engine tables).  tools/fm8c0.py's words from a patch: words()."""
from __future__ import annotations
import math
import struct
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

OPS = 8
OPB = 24
PEG = 192
GLB = 200
PLEN = 216
(O_R, O_L, O_BP, O_LD, O_RD, O_LC, O_RC, O_RS, O_AMS, O_KVS, O_OL, O_MODE, O_CRS, O_FINE, O_DET) = (0, 4, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
                                                                                                    18, 19, 20)
G_ALG, G_FB, G_SYNC, G_TRN, G_LFO, G_NZ, G_NZOP = 0, 1, 2, 3, 4, 11, 12
NALG = 48

EMAX = 99 * 32
STEP = 32                                       # u a DX7 level step
FLOOR = 1800                                    # a rising stage starts here at least (the DX7's attack jump)
ATT_MUL = 4                                     # a rising stage is that much faster
AMP0 = 126                                      # AMP = EXP[f] x AMP0 >> q (0x7E0000 at att 0: the 4-operator engine's full level)
EXP = [round(65535 * 2 ** (-f / 256)) for f in range(256)]
SLOPE = [round(256 * 0.04 * 2 ** (r / 6.75)) for r in range(128)]    # rate -> u / ms x 256 (rate 0: 79 s for the whole range; 99: ~3 ms)
VEL_K = 49                                      # att += KVS x (127 - velocity) x VEL_K >> 5 (KVS 7, velocity 0: ~32 dB)
LS_K = 7                                        # att += depth x semitones past the break point x LS_K >> 4 (linear curves; 99, 4 octaves: ~48 dB)
RS_K = 5                                        # rate += RS x (note - 24) x RS_K >> 6
PEG_C = 50 * 32                                 # the pitch envelope's centre
PEG_K = 1024 * 4096 // (49 * 32)               # 1/256 octave = (pe - PEG_C) x PEG_K >> 12 (L 99 = +4 octaves)
FIX = [round(10 ** (f / 100) * (1 << 40) / 48000 / 8) for f in range(100)]    # fixed mode: R = FIX[fine] x 8 x 10^c / inc ... (1 Hz base)
KW_CAR = 0x3FFFFF
M_FULL = 0x7FFFFF
THR = 16                                        # an AMP is sent again when its attenuation moved this much (the DSP smooths AMP)


# ---------------------------------------------------------------------------------------------------------------------------- the algorithms
# The DX7's 32 (modulation pairs (source, destination), carriers, feedback (source, destination)): the routing of the DX7 (as the msfa / Dexed
# table describes it, decoded to pairs); the 4-operator engine's 16 from fmeng.ALGS (op 4 of the "pitch" ones is not heard: the pitch envelope).
DX7 = [
    ([(6, 5), (5, 4), (4, 3), (2, 1)], [1, 3], (6, 6)), ([(6, 5), (5, 4), (4, 3), (2, 1)], [1, 3], (2, 2)),
    ([(6, 5), (5, 4), (3, 2), (2, 1)], [1, 4], (6, 6)), ([(6, 5), (5, 4), (3, 2), (2, 1)], [1, 4], (4, 6)),
    ([(6, 5), (4, 3), (2, 1)], [1, 3, 5], (6, 6)), ([(6, 5), (4, 3), (2, 1)], [1, 3, 5], (5, 6)),
    ([(6, 5), (5, 3), (4, 3), (2, 1)], [1, 3], (6, 6)), ([(6, 5), (5, 3), (4, 3), (2, 1)], [1, 3], (4, 4)),
    ([(6, 5), (5, 3), (4, 3), (2, 1)], [1, 3], (2, 2)), ([(6, 4), (5, 4), (3, 2), (2, 1)], [1, 4], (3, 3)),
    ([(6, 4), (5, 4), (3, 2), (2, 1)], [1, 4], (6, 6)), ([(6, 3), (5, 3), (4, 3), (2, 1)], [1, 3], (2, 2)),
    ([(6, 3), (5, 3), (4, 3), (2, 1)], [1, 3], (6, 6)), ([(6, 4), (5, 4), (4, 3), (2, 1)], [1, 3], (6, 6)),
    ([(6, 4), (5, 4), (4, 3), (2, 1)], [1, 3], (2, 2)), ([(6, 5), (4, 3), (5, 1), (3, 1), (2, 1)], [1], (6, 6)),
    ([(6, 5), (4, 3), (5, 1), (3, 1), (2, 1)], [1], (2, 2)), ([(6, 5), (5, 4), (4, 1), (3, 1), (2, 1)], [1], (3, 3)),
    ([(6, 5), (6, 4), (3, 2), (2, 1)], [1, 4, 5], (6, 6)), ([(6, 4), (5, 4), (3, 2), (3, 1)], [1, 2, 4], (3, 3)),
    ([(6, 5), (6, 4), (3, 2), (3, 1)], [1, 2, 4, 5], (3, 3)), ([(6, 5), (6, 4), (6, 3), (2, 1)], [1, 3, 4, 5], (6, 6)),
    ([(6, 5), (6, 4), (3, 2)], [1, 2, 4, 5], (6, 6)), ([(6, 5), (6, 4), (6, 3)], [1, 2, 3, 4, 5], (6, 6)),
    ([(6, 5), (6, 4)], [1, 2, 3, 4, 5], (6, 6)), ([(6, 4), (5, 4), (3, 2)], [1, 2, 4], (6, 6)),
    ([(6, 4), (5, 4), (3, 2)], [1, 2, 4], (3, 3)), ([(5, 4), (4, 3), (2, 1)], [1, 3, 6], (5, 5)),
    ([(6, 5), (4, 3)], [1, 2, 3, 5], (6, 6)), ([(5, 4), (4, 3)], [1, 2, 3, 6], (5, 5)),
    ([(6, 5)], [1, 2, 3, 4, 5], (6, 6)), ([], [1, 2, 3, 4, 5, 6], (6, 6)),
]
assert len(DX7) == 32
DX8 = [                                                              # (use_alg8) eight operators, algorithms 49-56
    ([(8, 7), (7, 6), (6, 5), (4, 3), (3, 2), (2, 1)], [1, 5], (8, 8)),                   # two 4-operator stacks
    ([(2, 1), (4, 3), (6, 5), (8, 7)], [1, 3, 5, 7], (8, 8)),                             # four 2-operator pairs
    ([(8, 7), (7, 6), (6, 5), (5, 4), (4, 3), (3, 2), (2, 1)], [1], (8, 8)),              # an 8-operator stack
    ([(k, 1) for k in range(2, 9)], [1], (8, 8)),                                         # seven modulators on one carrier
    ([], list(range(1, 9)), (8, 8)),                                                      # eight carriers (organ)
    ([(3, 2), (2, 1), (6, 5), (5, 4), (8, 7)], [1, 4, 7], (8, 8)),                        # three stacks: 3, 3, 2
    ([(2, 1), (4, 3), (8, 7), (7, 6), (6, 5)], [1, 3, 5], (8, 8)),                        # two pairs and a 4-operator stack
    (DX7[0][0] + [(8, 7)], DX7[0][1] + [7], DX7[0][2]),                                   # the DX7's algorithm 1 and a pair
]
ALG8 = False                                                     # (RD40: on, the 56 of Beta 5.21; use_alg8() below)


def use_alg8():
    """SC51.8 / Beta 5.21 (the user, 2026-11-05: «how do I create or load more operators?» -> «Add 8 new»): no algorithm used operators 7-8; now
    eight more, 49-56 (DX8), with N = 8: two 4-operator stacks, four pairs, an 8-operator stack, seven modulators on one carrier, eight carriers, three
    stacks 3 / 3 / 2, two pairs and a 4-operator stack, the DX7's algorithm 1 and a pair (the question said «two 3-op stacks + 2 pairs»: ten
    operators; this one is in its place)."""
    global ALG8, NALG
    ALG8, NALG = True, 56
OLD_DEF = [  # the 4-operator engine's ALGS as (mods, carriers, feedback op or 0, pitch, noise op, sus, det, relofs)
    (((4, 3), (3, 2), (2, 1)), (1,), 4, 0, 1, (1, 1, 1, 1), (1, 1, 1, 1), (0, 0, 0, 0)),
    (((4, 2), (3, 2), (2, 1)), (1,), 4, 0, 1, (1, 1, 1, 1), (1, 1, 1, 1), (0, 0, 0, 0)),
    (((4, 1), (3, 2), (2, 1)), (1,), 4, 0, 1, (1, 1, 1, 1), (1, 1, 1, 1), (0, 0, 0, 0)),
    (((4, 3), (3, 1), (2, 1)), (1,), 4, 0, 1, (1, 1, 1, 1), (1, 1, 1, 1), (0, 0, 0, 0)),
    (((4, 3), (2, 1)), (1, 3), 4, 0, 1, (1, 1, 1, 1), (1, 1, 1, 1), (0, 0, 0, 0)),
    (((4, 1), (4, 2), (4, 3)), (1, 2, 3), 4, 0, 1, (1, 1, 1, 1), (1, 1, 1, 1), (0, 0, 0, 0)),
    (((4, 3),), (1, 2, 3), 4, 0, 1, (1, 1, 1, 1), (1, 1, 1, 1), (0, 0, 0, 0)),
    ((), (1, 2, 3, 4), 4, 0, 1, (1, 1, 1, 1), (1, 1, 1, 1), (0, 0, 0, 0)),
    (((2, 1),), (1,), 2, 1, 1, (0, 0, 0, 0), (1, 1, 1, 1), (0, -8, 0, -10)),
    (((2, 1),), (1,), 2, 1, 3, (0, 0, 0, 0), (1, 1, 1, 1), (0, -6, 0, -8)),
    (((2, 1), (3, 1), (4, 1)), (1,), 4, 0, 1, (0, 0, 0, 0), (1, 1.414, 2.71, 3.49), (0, -4, -4, -4)),
    (((3, 2), (2, 1)), (1,), 3, 1, 1, (0, 0, 0, 0), (1, 1, 1, 1), (0, -6, -6, 0)),
    (((2, 1), (4, 3)), (1, 3), 4, 0, 1, (0, 0, 0, 0), (1, 3.5, 2.0, 2.76), (6, 0, 6, 0)),
    (((2, 1), (3, 1)), (1, 4), 4, 0, 1, (0, 0, 0, 0), (1, 2.76, 5.4, 2.0), (8, 0, -4, 8)),
    (((2, 1), (4, 3)), (1, 3), 4, 0, 1, (1, 1, 1, 1), (1.0, 1.0, 1.007, 1.007), (0, 0, 0, 0)),
    (((4, 1), (4, 2), (4, 3)), (1, 2, 3), 4, 0, 1, (1, 1, 1, 1), (0.994, 1.0, 1.006, 1.0), (0, 0, 0, 0)),
]
ALEN = 16
A_N, A_CAR, A_FBS, A_FBD, A_NZ, A_FAM, A_USED, A_MASK = 0, 1, 2, 3, 4, 5, 6, 8     # an entry: N, carriers, feedback source / destination (0xFF
                                                                          # none), the noise's operator, the family (overlay colour), the operators
                                                                          # heard or modulating, the mask (bit 8 d + s: s modulates d)


def alg_entry(mods, car, fb, nz=0, fam=0):
    n = max([s for s, d in mods] + [d for s, d in mods] + list(car) + ([fb[0], fb[1]] if fb else []))
    n = 4 if n <= 4 else 6 if n <= 6 else 8
    mask = sum(1 << (8 * (d - 1) + (s - 1)) for s, d in mods)
    fs, fd = (fb[0] - 1, fb[1] - 1) if fb else (0xFF, 0xFF)
    used = sum(1 << (o - 1) for o in set([s for s, d in mods] + list(car)))
    return struct.pack("<7BxQ", n, sum(1 << (c - 1) for c in car), fs, fd, nz, fam, used, mask)


def algs():
    out = bytearray()
    for i, (m, c, fb, pitch, nz, sus, det, rof) in enumerate(OLD_DEF):
        out += alg_entry(m, c, (fb, fb) if fb else None, nz - 1, 0)
    for m, c, fb in DX7 + (DX8 if ALG8 else []):
        out += alg_entry(m, c, fb, 0, 4)
    assert len(out) == NALG * ALEN
    return bytes(out)


def alg_of(table, i):
    n, car, fs, fd, nz, fam, used, mask = struct.unpack_from("<7BxQ", table, ALEN * i)
    return dict(n=n, car=car, fs=fs, fd=fd, nz=nz, fam=fam, used=used, mask=mask)


# ---------------------------------------------------------------------------------------------------------------------------- 4-op -> 8-op
def rate_of_slope(s):                                                # u / ms -> the nearest rate
    return max(0, min(99, round(6.75 * math.log2(max(s, 1e-9) / 0.04))))


def ratio_cf(x):                                                     # a ratio x 4096 -> (coarse, fine) (integers: the ARM's)
    if x < 4096:
        return 0, max(0, min(99, ((x - 2048) * 100 + 1024) // 2048))
    c = min(31, x >> 12)
    return c, max(0, min(99, ((x - c * 4096) * 100 + c * 2048) // (c * 4096)))


def op_default(k):                                                   # an operator 5-8 of a converted patch: silent, ratio 1, held
    b = bytearray(OPB)
    b[O_R:O_R + 8] = bytes((99, 99, 99, 60, 99, 99, 99, 0))
    b[O_BP], b[O_CRS], b[O_DET] = 39, 1, 7
    return bytes(b)


FB_DX7 = [0, 16, 23, 32, 45, 64, 90, 127]           # the DX7's feedback 0..7 -> fm8's (as fm8inst)
VOP = ("r1", "r2", "r3", "r4", "l1", "l2", "l3", "l4", "bp", "ld", "rd", "lc", "rc", "rs", "ams", "kvs", "ol", "mode", "crs", "fine", "det")
VMAX = dict(r1=99, r2=99, r3=99, r4=99, l1=99, l2=99, l3=99, l4=99, bp=99, ld=99, rd=99, lc=3, rc=3, rs=7, ams=3, kvs=7, ol=99, mode=1, crs=31,
            fine=99, det=14)
VGLB = ("pr1", "pr2", "pr3", "pr4", "pl1", "pl2", "pl3", "pl4", "alg", "fb", "oks", "lfs", "lfd", "pmd", "amd", "lks", "lfw", "pms", "trn")
GMAX = dict(pr1=99, pr2=99, pr3=99, pr4=99, pl1=99, pl2=99, pl3=99, pl4=99, alg=31, fb=7, oks=1, lfs=99, lfd=99, pmd=99, amd=99, lks=1, lfw=5,
            pms=7, trn=48)


def dx7_unpack(v):
    """128 packed bytes (VMEM) -> ({op 1..6: fields}, globals, name)."""
    ops = {}
    for i in range(6):
        b = v[17 * i:17 * i + 17]
        o = dict(zip(VOP[:11], b[:11]))
        o.update(lc=b[11] & 3, rc=b[11] >> 2 & 3, rs=b[12] & 7, det=b[12] >> 3 & 15, ams=b[13] & 3, kvs=b[13] >> 2 & 7, ol=b[14], mode=b[15] & 1,
                 crs=b[15] >> 1 & 31, fine=b[16])
        ops[6 - i] = o
    g = dict(zip(VGLB[:8], v[102:110]))
    g.update(alg=v[110] & 31, fb=v[111] & 7, oks=v[111] >> 3 & 1, lfs=v[112], lfd=v[113], pmd=v[114], amd=v[115], lks=v[116] & 1,
             lfw=v[116] >> 1 & 7, pms=v[116] >> 4 & 7, trn=v[117])
    return ops, g, v[118:128]


def dx7_vced(v):
    """155 unpacked bytes (VCED, a single voice) -> the same."""
    ops = {6 - i: dict(zip(VOP, v[21 * i:21 * i + 21])) for i in range(6)}
    return ops, dict(zip(VGLB, v[126:145])), v[145:155]


def dx7_name(b):
    return "".join(chr(c) if 32 <= c < 127 else " " for c in (x & 127 for x in b)).rstrip()


def dx7_voices(data):
    """A .syx (one or more messages; a bare 4096-byte bank too) -> [(name, ops, globals)], bad check bytes accepted."""
    out = []
    if len(data) == 4096 and data[0] != 0xF0:
        return [(dx7_name(u[2]),) + u[:2] for u in (dx7_unpack(data[128 * k:128 * k + 128]) for k in range(32))]
    i = 0
    while True:
        s = data.find(b"\xF0", i)
        if s < 0: return out
        e = data.find(b"\xF7", s)
        if e < 0: return out
        m, i = data[s:e + 1], e + 1
        if len(m) >= 4104 and m[1] == 0x43 and m[3] == 9:
            for k in range(32):
                u = dx7_unpack(m[6 + 128 * k:6 + 128 * k + 128])
                out.append((dx7_name(u[2]),) + u[:2])
        elif len(m) >= 163 and m[1] == 0x43 and m[3] == 0:
            u = dx7_vced(m[6:6 + 155])
            out.append((dx7_name(u[2]),) + u[:2])


def from_dx7(ops, g):
    """A DX7 voice -> PLEN bytes: DX7 operator k + 1 = fm8's operator k, its fields in fm8's native units."""
    out = bytearray(PLEN)
    for k in range(6):
        o, b = {f: min(VMAX[f], ops[k + 1][f] & 127) for f in VOP}, OPB * k
        out[b + O_R:b + O_R + 8] = bytes(o[f] for f in VOP[:8])
        for at, f in ((O_BP, "bp"), (O_LD, "ld"), (O_RD, "rd"), (O_LC, "lc"), (O_RC, "rc"), (O_RS, "rs"), (O_AMS, "ams"), (O_KVS, "kvs"),
                      (O_OL, "ol"), (O_MODE, "mode"), (O_CRS, "crs"), (O_FINE, "fine"), (O_DET, "det")):
            out[b + at] = o[f]
    for k in range(6, 8):
        out[OPB * k:OPB * k + OPB] = op_default(k)
    q = {f: min(GMAX[f], g[f] & 127) for f in VGLB}
    out[PEG:PEG + 8] = bytes(q[f] for f in VGLB[:8])
    G = GLB
    out[G + G_ALG], out[G + G_FB], out[G + G_SYNC], out[G + G_TRN] = 16 + q["alg"], FB_DX7[q["fb"]], q["oks"], q["trn"]
    out[G + G_LFO:G + G_LFO + 7] = bytes(q[f] for f in ("lfs", "lfd", "pmd", "amd", "lks", "lfw", "pms"))
    return bytes(out)


REC_HDR, REC_SUM0, REC_N = b"FM8\x01", 0x5A38, 224   # fm8store's HDR / SUM0 / RECN (asserted there)


def record(params):
    """An own slot's FM record (fm8store.c_fsput): "FM8" 1, the parameters, their 16-bit sum, 0xFF to 224."""
    s = (REC_SUM0 + sum(params)) & 0xFFFF
    return REC_HDR + bytes(params) + s.to_bytes(2, "little") + b"\xFF" * (REC_N - 6 - PLEN)


# ---------------------------------------------------------------------------------------------------------------------------- reference model
class Voice:
    def __init__(s):
        s.e = [0] * 9                    # x 256
        s.st = [5] * 9
        s.gate = 0
        s.last = [0xFFFF] * 8
        s.e[8] = PEG_C << 8


def ref_tick(P, v, gate, note, vel, dt, new):
    """One tick of a voice: the envelopes, then {op: (att or None, R)} and the pitch factor (x 4096)."""
    g = GLB
    if new:
        for i in range(9): v.st[i] = 0
    elif v.gate and not gate:
        for i in range(9): v.st[i] = 3
    v.gate = gate
    rs_note = max(0, note - 24)
    for i in range(9):
        b = OPB * i if i < 8 else PEG - O_R
        if v.st[i] in (4, 5): continue
        s_ = v.st[i]
        T = P[b + O_L + s_] * STEP << 8
        r = P[b + O_R + s_] + ((P[b + O_RS] * rs_note * RS_K) >> 6 if i < 8 else 0)
        sl = SLOPE[min(127, r)] * dt
        e = v.e[i]
        if T > e:
            if i < 8:
                if e < FLOOR << 8: e = FLOOR << 8
                sl *= ATT_MUL
            e = min(T, e + sl)
        else:
            e = max(T, e - sl)
        v.e[i] = e
        if e == T:
            v.st[i] = 4 if s_ == 2 else 5 if s_ == 3 else s_ + 1
    pu = ((v.e[8] >> 8) - PEG_C) * PEG_K >> 12
    pu += (P[g + G_TRN] - 24) * 85 >> 2
    q, f = pu >> 8, pu & 255
    pf = 4096 if f == 0 else (EXP[256 - f] * 8192) >> 16
    pf = pf << q if q >= 0 else pf >> -q
    out = {}
    for k in range(OPS):
        b = OPB * k
        if P[b + O_OL] == 0 or v.e[k] < 256:
            att = None
        else:
            att = (EMAX - (v.e[k] >> 8)) + (99 - P[b + O_OL]) * STEP + (P[b + O_KVS] * (127 - vel) * VEL_K >> 5)
            dist = note - (P[b + O_BP] + 21)
            if dist > 0: att += P[b + O_RD] * dist * LS_K >> 4
            elif dist < 0: att += P[b + O_LD] * (-dist) * LS_K >> 4
        out[k] = att
    return out, pf


def amp_of(att):
    if att is None: return 0
    q, f = att >> 8, att & 255
    return 0 if q >= 24 else (EXP[f] * AMP0) >> q


def ratio_r(P, k, inc):
    """R (ratio x 2^16) of operator k before the pitch factor."""
    b = OPB * k
    if P[b + O_MODE]:
        c = P[b + O_CRS] & 3
        return min(0x7FFFFF, ((FIX[P[b + O_FINE]] * 8 // max(1, inc)) * 10 ** c) >> 3)
    x = 2048 if P[b + O_CRS] == 0 else P[b + O_CRS] * 4096
    x = x * (100 + P[b + O_FINE]) // 100
    x = x * (4096 + (P[b + O_DET] - 7) * 4) >> 12
    return x << 4
use_alg8()


# ---------------------------------------------------------------------------------------------------------------------------- RD40's words
DT = 32 / 48                                    # a block, in ms
SILENT = 40 << 16                               # BASE of an operator not heard (40 octaves: the shift leaves 0)


def fixed_ratio(P, k, ref=261.63):
    """(not in the reduced port: a fixed operator follows the key) its frequency over the middle C's"""
    b = OPB * k
    return 10 ** ((P[b + O_CRS] & 3) + P[b + O_FINE] / 100) / ref


T2 = [round(2 ** ((n - 24) / 12) * 4096) for n in range(49)]               # the transposition, Q12 (the ARM's table)
FXQ = [round(10 ** (f / 100) * 65536 / 261.63) for f in range(100)]           # a fixed operator: its frequency / the middle C's x 2^16 at 1 Hz
POW10 = (1, 10, 100, 1000)
SLB = [round(SLOPE[r] * 32 / 48) for r in range(128)]                       # a rate's slope a block (2 / 3 ms)
NZ_K = 260                                                                  # the noise word = nz^2 x NZ_K (~ nz^2 / 127^2 / 2)
PK_W = round(PEG_K / 4096 * (1 << 23))


def r0_word(P, k):
    """R0 of operator k (the ratio x 2^16, the transposition in it), integer as the ARM: a fixed operator's frequency over the middle C's
    (it follows the key in the reduced port)"""
    b = OPB * k
    if P[b + O_MODE]:
        x = FXQ[min(99, P[b + O_FINE])] * POW10[P[b + O_CRS] & 3]
    else:
        x = 2048 if P[b + O_CRS] == 0 else P[b + O_CRS] * 4096
        x = x * (100 + P[b + O_FINE]) // 100
        x = x * (4096 + (P[b + O_DET] - 7) * 4) >> 12
        x = (x * T2[min(48, P[GLB + G_TRN])]) >> 8
    return min(0x7FFFFF, x)


def words(P, base, note=60):
    """216 parameter bytes -> {offset: word} of a slot's block in tools/fm8c0.py (base = the block's X address: G_TOPA / G_NOPA are
    absolute).  The level / rate scaling at `note` (the middle C: not by note in the reduced port), the brightness 1, the LFO left out."""
    import fm8c0 as C
    al = alg_of(algs(), P[GLB + G_ALG] % NALG)
    n, car, mask, fs, fd = al["n"], al["car"], al["mask"], al["fs"], al["fd"]
    ncar = max(1, bin(car).count("1"))
    fbc = min(0x7FFFFF, P[GLB + G_FB] ** 2 * 256)
    rs_note = max(0, note - 24)
    w = {}
    for k in range(8):
        b, o = OPB * k, C.OP0 + C.OPS * k
        for i in range(4):
            w[o + C.F_T1 + i] = (P[b + O_L + i] * STEP) << 8
            r = P[b + O_R + i] + ((P[b + O_RS] * rs_note * RS_K) >> 6)
            w[o + C.F_S1 + i] = SLB[min(127, r)]
        dist = note - (P[b + O_BP] + 21)
        ls = (P[b + O_RD] * dist * LS_K >> 4) if dist > 0 else (P[b + O_LD] * -dist * LS_K >> 4) if dist < 0 else 0     # (note 60)
        heard = P[b + O_OL] and k < n
        w[o + C.F_BASE] = min(SILENT, ((EMAX + (99 - P[b + O_OL]) * STEP + ls) << 8) + C.AMP0_ATT) if heard else SILENT
        w[o + C.F_VS] = (P[b + O_KVS] * 127 * VEL_K >> 5) << 8
        w[o + C.F_R0] = r0_word(P, k)
        w.update({o + C.F_FL: FLOOR << 8, o + C.F_RM: 1, o + C.F_ST: 5, o + C.F_K: (KW_CAR // ncar) if car >> k & 1 else 0,
                  o + C.F_HC: fbc if (k == fd and fs == fd) else 0})
        for j in range(8):
            m = M_FULL if mask >> (8 * k + j) & 1 else 0
            if k == fd and j == fs:
                m = fbc if fs == fd else min(0x7FFFFF, 2 * fbc)
            w[o + C.F_M1 + j] = m
        for f in (C.F_E, C.F_OFS, C.F_OUT, C.F_PH, C.F_R, C.F_AMP, C.F_AS, C.F_O2):
            w[o + f] = 0
    pb = C.PEGB
    for i in range(4):
        w[pb + C.F_T1 + i] = (P[PEG + 4 + i] * STEP) << 8
        w[pb + C.F_S1 + i] = SLB[min(127, P[PEG + i])]
    w.update({pb + C.F_E: PEG_C << 8, pb + C.F_ST: 5, pb + C.F_FL: 0, pb + C.F_RM: 0})
    nz = P[GLB + G_NZ]
    w.update({C.G_FLG: 2 if P[GLB + G_SYNC] else 0, C.G_N: n, C.G_TOPA: base + C.OP0 + C.OPS * (n - 1),
              C.G_NZ: nz * nz * NZ_K, C.G_NOPA: base + C.OP0 + C.OPS * (P[GLB + G_NZOP] & 7) + C.F_AMP,
              C.G_NA: 0, C.G_NS: 1, C.G_PG: 0, C.G_PC: PEG_C << 8, C.G_PK: PK_W, C.G_A1: C.A1, C.G_A2: C.A2})
    return {o: v & 0xFFFFFF for o, v in w.items()}


def bank_records(data):
    """a patch bank file (NN_PATCHBANK.cpb, the Tracks' or the Rhythm's) -> {slot 0-7: 216 parameter bytes} of its valid FM records"""
    out = {}
    for n in range(8):
        r = data[4096 + 512 * n:4096 + 512 * n + REC_N]
        if len(r) >= 6 + PLEN and r[:4] == REC_HDR:
            p = r[4:4 + PLEN]
            if int.from_bytes(r[4 + PLEN:6 + PLEN], "little") == (REC_SUM0 + sum(p)) & 0xFFFF:
                out[n] = bytes(p)
    return out
