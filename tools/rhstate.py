"""Our own RAM on the Circuit Rhythm 5706 (MIT; the c_gst of CIRCUIT-HACKS' SC14, for the Rhythm).

The stock allocator 0x08025A98 is a bump allocator (the Tracks' 0x0801D7D8, the same code): limit [0x20002B54], current [0x20002B58].
In the RAM dump of RD1 (stock/ram_rd1.bin, 51 s after power-on) the limit is 0x2004F760 and the current 0x2004EA98: 3 272 B never
allocated (they still hold the random power-on content of the SRAM).  Above the limit is the main stack; the dump shows it used only
from 0x2004FDE0 up (1.6 KB of untouched SRAM between the limit and its deepest point).

c_rst() -> r0 = our block (SIZE bytes at LIMIT - SIZE), or 0 when the stock already allocated that far (every feature then stays off).
On its first call it lowers the limit to the block, so no stock allocation can ever reach it, and zeroes the block (magic at + 0).
Clobbers r1-r3.  The offsets each module uses are listed in OFF (a new module adds its own and checks that nothing overlaps).

install(ram2=True) (RH41+): c_rst reserves a second block of SIZE2 bytes just below (ST2 = 0x2004EE60) in the same first call (the
limit = ST2), and c_rram() -> r0 = ST2 (or 0 as c_rst).  Without it the code is the same byte for byte (the builds before RH41).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import Asm, adds_imm8, b, b_cond, bl, cmp_imm, cmp_reg, ldr_imm, movs_imm, movt, movw, pop_list, push_list, raw, h, str_imm, subs_imm8  # noqa: E402

HEAP_LIMIT_PTR, HEAP_CUR_PTR = 0x20002B54, 0x20002B58
HEAP_LIMIT = 0x2004F760                    # the stock's limit, as in the dump
SIZE = 256
ST = HEAP_LIMIT - SIZE                     # 0x2004F660
MAGIC = 0x31545352                         # "RST1"
# ---- (RH41, install(ram2=True)) a second block below: the heap's tail.  RH40 on the device (2026-10-26, tools/rhheap.py): after a pack
# change, a project load and save, a recording and its save, a delete, every view and Setup, the current pointer was still 0x2004EA98 (as
# 51 s after power-on): the stock does not allocate after start-up.  SIZE2 leaves 968 B between it and the stock's last allocation.
SIZE2 = 0x800
ST2 = ST - SIZE2                           # 0x2004EE60
MAGIC2 = 0x32545352                        # "RST2"
OUR_LIMIT = ST2                            # the heap limit once c_rst has run with ram2
OFF2 = {                                   # module -> (offset, length) inside the second block
    "magic": (0, 4),
    "latdiag": (4, 224),                   # (RD24) the playback start's times: state, the start, the clock's first pass, 16 queue writes, the freeze
    "startfix": (228, 12),                 # (RD25) tick 0 played at the start: ACT, the passes N, T0 (HAL tick)
    "clkprobe": (240, 112),                # (RD27) the clock timer's gaps: the switch, the time source, stats since the last internal start
    "stallprof": (352, 1072),              # (RD28) SysTick's samples of what runs while the timers' dispatcher is stalled
    "sdyield": (1424, 20),                 # (RD29) the card's long waits yield: in a wait, its start, long waits, the longest, yields
    "menu": (1480, 16),                    # (RH45, granpage v2) + 0 the Granular pages, + 1 the held track + 1, + 2 flags, + 4 its press, + 8 pads taken
    "stfit": (1444, 36),                   # (RH44) Sample mode's stretch fit: + 0 the tracks whose options are known, + 4 + 4 t pad 9's / pad 10's option
    "stepgate": (1496, 76),                # (RH46) the Micro Step selector's track + 1, the presses' track + 1, steps empty at their press, pressed, 32 press times
    "setsave": (1572, 8),                  # (RH46) the last bits 20..31 of the settings' parameter 2 seen, + 4 0x5E when known
    "gmmode": (1580, 20),                  # (RH46) + 0 the GM note sounding per track (0 none), + 8 the knobs' clicks (signed), + 16 the last preview
    "qfull": (1600, 4),                    # (RH46) core 1's read index of the trigger queue last read, 0x80 | it (0 never)
    "autorel": (1604, 132),                # (RH46) the swallowed step pads, per track: the taken lanes, marks in the pattern, this step marked, 12 bases
    "cue": (1736, 12),                     # (RH47) the cue mode (0xC5 on), the mutes last seen, the tracks to send again, a zero byte, 8 cue sends
    "linein": (1748, 4),                   # (RH47) + 0 the line input's words to send now, + 1 the round; (RH48) + 0 sent once, + 2 / + 3 the pair sent
    "slink": (1752, 4),                    # (RH49) + 0 the stereo link's leaders applied, + 1 applied once
    "granmulti": (1756, 64),               # (RH50) + 0 the granular slots to send, + 1 the round, + 2 sent once, + 4 their low 7 bits (13 a slot)
    "clkci": (1820, 52),                   # (A0.04F) the count-in on the music's clock: flags, the held mode, the master, clicks, times, its log
}
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
    "spwait": (222, 1),
    "k8tick": (224, 4),                    # (RH38, stockplus k8sync) the sequencer's global tick last seen (the synced scans' phase written on a new one)                    # (RH35) frames since core 1's program was seen uploaded (stockplus writes to core 1 only after SP_WAIT)
    "stockplus": (218, 4),                 # (RH32) + 0 the tracks on the Stock+ page (bit t), + 1 the tracks to push to core 1, + 2 the round, + 3 Duplicate's source + 1
    "granpage": (228, 4),                  # (RH39) + 0 to push (bit 0 the granular's words to core 0, bit 1 the crossfade's to core 1), + 1 / + 2 their rounds
    "smpcopy": (202, 12),                  # the sample copy: tag, source + 1, its pack, the slot asked about + 1, time, the last copy + 1, its pack, status, time
    "vismet": (232, 4),                    # (A0.04F) the visual metronome: the last silent beat or click (HAL tick, 0 = none)
    "stereorec": (248, 8),                 # (RD23) Sample Rec in stereo: phase, A, B, STF written, our functors installed
}


def check_layout():
    for off, size in ((OFF, SIZE), (OFF2, SIZE2)):
        used = sorted(off.values())
        for (a, n), (b2, _) in zip(used, used[1:]):
            assert a + n <= b2, f"rhstate offsets overlap at {b2}"
        assert used[-1][0] + used[-1][1] <= size


def arm_code(base, ram2=False):
    """ram2 (RH41): c_rst claims both blocks at once (the limit = ST2) and takes the limit ST2 as its own; c_rram() -> r0 = the second
    block (or 0, as c_rst)"""
    check_layout()
    if ram2:
        return arm_code2(base)
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


def arm_code2(base):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)

    a.label("c_rst")
    imm32(0, ST)
    imm32(3, HEAP_LIMIT_PTR)
    E(ldr_imm, 1, 3, 0)                                        # the limit
    imm32(2, ST2)
    E(cmp_reg, 1, 2)
    E(b_cond, "r2_res", "ne")
    E(ldr_imm, 1, 0, 0)                                        # the limit is already ours: ready unless a magic is gone
    imm32(2, MAGIC)
    E(cmp_reg, 1, 2)
    E(b_cond, "r2_in", "ne")
    imm32(2, ST2)
    E(ldr_imm, 1, 2, 0)
    imm32(2, MAGIC2)
    E(cmp_reg, 1, 2)
    E(b_cond, "r2_ok", "eq")
    E(b, "r2_in")
    a.label("r2_res")
    imm32(2, HEAP_LIMIT)
    E(cmp_reg, 1, 2)
    E(b_cond, "r2_off", "ne")                                  # an unexpected limit: stay off
    E(ldr_imm, 1, 3, 4)                                        # the current
    imm32(2, ST2)
    E(cmp_reg, 1, 2)
    E(b_cond, "r2_off", "hi")                                  # already allocated into the blocks: stay off
    E(str_imm, 2, 3, 0)                                        # limit = the second block: both reserved
    a.label("r2_in")
    imm32(2, ST2)                                              # both blocks zeroed (ST2 .. ST + SIZE), their magics
    imm32(3, ST + SIZE)
    E(movs_imm, 1, 0)
    a.label("r2_clr")
    E(str_imm, 1, 2, 0)
    E(adds_imm8, 2, 4)
    E(cmp_reg, 2, 3)
    E(b_cond, "r2_clr", "lo")
    imm32(2, MAGIC)
    E(str_imm, 2, 0, 0)
    imm32(1, ST2)
    imm32(2, MAGIC2)
    E(str_imm, 2, 1, 0)
    a.label("r2_ok")
    E(raw, h(0x4770))
    a.label("r2_off")
    E(movs_imm, 0, 0)
    E(raw, h(0x4770))

    a.label("c_rram")                                          # -> r0 = the second block, 0 without our RAM; clobbers r1-r3
    E(push_list, [4], lr=True)
    E(bl, "c_rst")
    E(cmp_imm, 0, 0)
    E(b_cond, "rr_x", "eq")
    imm32(0, ST2)
    a.label("rr_x")
    E(pop_list, [4], pc=True)
    return a.assemble()


def install(img, report, base_addr, ram2=False):
    import rh_fw
    BASE = rh_fw.APP_BASE
    code, labels = arm_code(base_addr, ram2=ram2)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    report["rhstate"] = dict(block=hex(ST), size=SIZE, off={k: v[0] for k, v in OFF.items()},
                             **({"block2": hex(ST2), "size2": SIZE2, "off2": {k: v[0] for k, v in OFF2.items()}} if ram2 else {}),
                             labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
