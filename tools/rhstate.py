"""Our own RAM on the Circuit Rhythm 5706 (MIT; the c_gst of CIRCUIT-HACKS' SC14, for the Rhythm).

The stock allocator 0x08025A98 is a bump allocator (the Tracks' 0x0801D7D8, the same code): limit [0x20002B54], current [0x20002B58].
In the RAM dump of RD1 (stock/ram_rd1.bin, 51 s after power-on) the limit is 0x2004F760 and the current 0x2004EA98: 3 272 B never
allocated (they still hold the random power-on content of the SRAM).  Above the limit is the main stack; the dump shows it used only
from 0x2004FDE0 up (1.6 KB of untouched SRAM between the limit and its deepest point).

c_rst() -> r0 = our block (SIZE bytes at LIMIT - SIZE), or 0 when the stock already allocated that far (every feature then stays off).
On its first call it lowers the limit to the block, so no stock allocation can ever reach it, and zeroes the block (magic at + 0).
Clobbers r1-r3.  The offsets each module uses are listed in OFF (a new module adds its own and checks that nothing overlaps).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import Asm, b, b_cond, cmp_imm, cmp_reg, ldr_imm, movs_imm, movt, movw, raw, h, str_imm, subs_imm8  # noqa: E402

HEAP_LIMIT_PTR, HEAP_CUR_PTR = 0x20002B54, 0x20002B58
HEAP_LIMIT = 0x2004F760                    # the stock's limit, as in the dump
SIZE = 256
ST = HEAP_LIMIT - SIZE                     # 0x2004F660
MAGIC = 0x31545352                         # "RST1"
OFF = {                                    # module -> (offset, length) inside the block
    "magic": (0, 4),
    "rodisk": (4, 4),                      # the HAL tick of the last refused write / delete (the Save LED)
    "countin": (8, 8),                     # + 0 the count-in on (0xC1), + 1 clicks sent, + 2 the pass flag, + 4 the count's start (HAL tick, 0 = none)
    "quant": (16, 1),                      # the last Shift + Play while Shift is held: 0xD1 quantized, 0xD0 refused, 0 none
    "qmute": (17, 2),                      # + 0 the pending mute toggles (bit t), + 1 the clock's bar tick last seen (0xFF stopped)
    "porder": (19, 8),                     # the fractal order's group size - 1, a byte per track (0 while the transport is stopped)
    "drumpat": (28, 50),                   # 6 B a track (passes lo / hi, pattern + 1, a pending hit's micro step + 1 / velocity / sample + 1),
                                           # + 48 the probability view's state (bit 0 mode 2, bit 1 row 3 to redraw, bit 2 mode 2 asked, bits 4-5 LED passes)
    "patchain": (78, 1),                   # 0xC7 = the running part in the record's tail is made for the loaded project (0 after a load)
    "sckn": (79, 1),                       # 0xC5 = the side-chain / compressor values of the loaded project written again (0 after a load)
    "drumarp": (80, 32),                   # the sample arpeggio running: n, magic, track, order state, 6 samples, 6 velocities, flags, times, page
    "cscale": (112, 32),                   # the scale each track's keyboard holds (4 B a track)
    "polydiag": (144, 8),                  # (RD2 only) the polyphony test: pad + 1, track, note, stage, the next time
    "trkcopy": (152, 2),                   # 0xC3 = the photo of the loaded project taken (0 after a load), the copy's source track + 1
    "sesscopy": (156, 12),                 # the project copy: tag, source, its pack, the question + time, the last copy + pack, colour, status, time
    "kbright": (168, 26),                  # the knob LEDs overlay of the frame: [0] knobs (bit k), [1..8] values, [10..25] colour codes
    "pgmch": (154, 1),                     # the Setup view: 0, 1 the listen channel shown, 2 the output channel shown
    "pkdel": (194, 8),                     # the pack delete: tag, the pack asked about (0x80 | p) + time, the last delete (0x80 | p), status, time
    "mfsess": (214, 1),                    # 0xC1 = a project was loaded: the LED task applies its resonance once
    "mfsess2": (215, 1),
    "cthresh": (216, 2),                   # (RH30) the compressor threshold applied + 0x80 (0 unknown), 0xB1 = core 0 holds another program                   # (RH30, mfsess track) the resonance the LED task last saw + 0x80 (0 = none yet)
    "stockplus": (218, 4),                 # (RH32) + 0 the tracks on the Stock+ page (bit t), + 1 the tracks to push to core 1, + 2 the round, + 3 Duplicate's source + 1
    "smpcopy": (202, 12),                  # the sample copy: tag, source + 1, its pack, the slot asked about + 1, time, the last copy + 1, its pack, status, time
}


def check_layout():
    used = sorted(OFF.values())
    for (a, n), (b2, _) in zip(used, used[1:]):
        assert a + n <= b2, f"rhstate.OFF overlaps at {b2}"
    assert used[-1][0] + used[-1][1] <= SIZE


def arm_code(base):
    check_layout()
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    a.label("c_rst")
    imm32(0, ST)
    imm32(3, HEAP_LIMIT_PTR)
    E(ldr_imm, 1, 3, 0)                                        # the limit
    E(cmp_reg, 1, 0)
    E(b_cond, "rs_res", "ne")
    E(ldr_imm, 1, 0, 0)                                        # the limit is already ours: the block is ready unless the magic is gone
    imm32(2, MAGIC)
    E(cmp_reg, 1, 2)
    E(b_cond, "rs_ok", "eq")
    E(b, "rs_init")
    a.label("rs_res")
    imm32(2, HEAP_LIMIT)
    E(cmp_reg, 1, 2)
    E(b_cond, "rs_off", "ne")                                  # an unexpected limit: stay off
    E(ldr_imm, 1, 3, 4)                                        # the current
    E(cmp_reg, 1, 0)
    E(b_cond, "rs_off", "hi")                                  # already allocated into the block: stay off
    E(str_imm, 0, 3, 0)                                        # limit = the block: reserved
    a.label("rs_init")
    E(movs_imm, 1, 0)
    E(movw, 2, SIZE)
    a.label("rs_clr")                                          # + SIZE - 4 down to + 4
    E(subs_imm8, 2, 4)
    E(raw, h(0x5081))                                          # str r1, [r0, r2]
    E(cmp_imm, 2, 4)
    E(b_cond, "rs_clr", "ne")
    imm32(2, MAGIC)
    E(str_imm, 2, 0, 0)
    a.label("rs_ok")
    E(raw, h(0x4770))
    a.label("rs_off")
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
    report["rhstate"] = dict(block=hex(ST), size=SIZE, off={k: v[0] for k, v in OFF.items()},
                             labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
