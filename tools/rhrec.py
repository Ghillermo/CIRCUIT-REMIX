"""The tail of the Rhythm's session record: the bytes that travel with the project (MIT; the record's tail of CIRCUIT-HACKS, for the Rhythm 5706).

The stock (read in the firmware and on the RAM dump): the session record R = [0x2003C0CC] (= [[engine 0x2003C380 + 0x20]]) is 0x29484 B and is
the project file (the load, 0x08049A30, takes a file whose header says RUSE / RDEM and 0x29484 B); "new project" zeroes R + 0x29110 .. + 0x29483
(0x08032E9C), and no literal of the firmware points inside: 884 B of the record nobody uses (zero in the dump), as the Tracks' 1000 B tail.
Like the Tracks' tail it may hold garbage in packs made elsewhere: every block of ours carries a mark.  Not yet checked on the device that the
stock saves and loads it (docs/PORTADO.md).

c_rrt() -> r0 = R + 0x29110, or 0 when the engine or the record are not where the dump has them; clobbers r1, r2.
OFF: module -> (offset, length) inside the tail.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import Asm, b_cond, cmp_reg, h, ldr_imm, movs_imm, movt, movw, raw, adds_reg  # noqa: E402

ENG, ENG_VT, REC_OWNER = 0x2003C380, 0x08066B34, 0x2003C0CC
TAIL, TAIL_LEN = 0x29110, 0x374
FREE_LEN = 0x372                           # the last 2 bytes of the record are the stock's (seen on the unit, 2026-10-19)
OFF = {                                    # module -> (offset, length) in the tail
    "drumpat": (0, 2),
    "granmulti": (2, 58),                  # (RH50) "N", a check byte, 4 granular slots x 14 B: the track + 1 (0 = free), the 13 values >> 7                     # "DQ": the project's step bytes (pattern + 0x108 + step) are ours
    "patchain": (64, 128),                 # + 0..47 "CTC1", sum, the tracks on the rules, 16 scene flags, 16 scene repeats; + 64..127 the running part
    "sckn": (192, 40),                     # "SK", sum, the tracks whose side-chain values are ours, 8 x 4 values, the compressor's flag + 3 values
    "drumarp": (232, 68),                  # "AD", sum, the arpeggiator's setting of each track and pattern (8 x 8)
    "cscale": (300, 28),                   # "CS", sum, the custom scale of each track (3 B: bits 1..24 = the intervals)
    "trkcopy": (328, 212),                 # "TS", each track's photo at the load: 25 parameters, the selected sample
    "mfsess": (540, 4),                    # "MF", the master filter's resonance, its check byte (written when the project is saved)
    "cthresh": (544, 4),                   # "TH", the compressor's threshold (0..127, 127 = the stock's), its check byte
    "stockplus": (548, 132),               # (RH32) "SP", a check byte, 0, then 8 tracks x 8 halfwords: the Stock+ knob page's values
    "stockplus2": (680, 68),
    "granpage": (748, 32),                 # (RH39) "GP", a check byte, the granular track + 1, the crossfade's tracks (bit t), 0, 12 halfwords: its knobs               # (RH33) "SQ", a check byte, 0, then 8 tracks x 4 halfwords: K5-K8's Shift layer on the Stock+ page
    "stepgate": (780, 12),                 # (RH46) "SG", a check byte, the gate-by-holding tracks (bit t), each track's fixed length (bit 7 on, 1..16)
    "gmmode": (792, 12),                   # (RH46) "GM", a check byte, the flags (bit 0 on), the GM note of each track (35..81)
    "linein": (804, 4),                    # (RH47) "L", a check byte, the line input's track + 1, its gate (1 = the track's notes); (RH48) the two line tracks, each track + 1 | gate << 4
    "slink": (808, 4),                     # (RH49) "S", a check byte, the stereo link's leaders (bit t: t leads, t + 1 follows), 0
    "synth": (812, 70),                    # (RH51) "Y", a check byte, 4 synth slots x 17 B: the track + 1 (0 = free), its 16 knob values (7 bits)
}


# (RH54) with trkcopy's photo in RAM (trkcopy ram, rhstate OFF2 «trkphoto»), its 212 B of the tail hold these (the builds before: the photo,
# rewritten at each load; a project of theirs gives these blocks a bad mark: their defaults)
REUSE = (328, 212)
OFF54 = {
    "envelope": (328, 22),                 # (RH54) "E", a check byte, the synth slots' slope (4 B), the granular slots' start, length, slope, env -> filter (4 x 4 B)
}


def check_layout():
    used = sorted(OFF.values())
    for (a, n), (b2, _) in zip(used, used[1:]):
        assert a + n <= b2, f"rhrec.OFF overlaps at {b2}"
    assert used[-1][0] + used[-1][1] <= FREE_LEN
    for a, n in OFF54.values():
        assert REUSE[0] <= a and a + n <= REUSE[0] + REUSE[1]


def arm_code(base):
    check_layout()
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    a.label("c_rrt")
    imm32(0, ENG)
    E(ldr_imm, 1, 0, 0)
    imm32(2, ENG_VT)
    E(cmp_reg, 1, 2)
    E(b_cond, "rt_0", "ne")
    E(ldr_imm, 0, 0, 0x20)
    imm32(1, REC_OWNER)
    E(cmp_reg, 0, 1)
    E(b_cond, "rt_0", "ne")
    E(ldr_imm, 0, 0, 0)                                        # R
    imm32(1, 0x20000000)
    E(cmp_reg, 0, 1)
    E(b_cond, "rt_0", "lo")
    imm32(1, 0x20050000 - 0x29484)
    E(cmp_reg, 0, 1)
    E(b_cond, "rt_0", "hi")
    imm32(1, TAIL)
    E(adds_reg, 0, 0, 1)
    E(raw, h(0x4770))
    a.label("rt_0")
    E(movs_imm, 0, 0)
    E(raw, h(0x4770))
    return a.assemble()


def install(img, report, base_addr):
    import rh_fw
    BASE = rh_fw.APP_BASE
    code, labels = arm_code(base_addr)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    report["rhrec"] = dict(tail=hex(TAIL), size=TAIL_LEN, off={k: v[0] for k, v in OFF.items()},
                           labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
