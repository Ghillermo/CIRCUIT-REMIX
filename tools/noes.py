"""Easy Start (the stock's USB mass storage) gone, its code free for ours (MIT; RH97; the user, 2026-11-13: «You can drop the "easy start"
completely and compact the Code to make room»).

The stock (read in the firmware and on RD1's RAM dump):
  * Advanced Setup's button 9 flips bit 17 of the settings' p2 (store 0x20012478; its handler 0x08051456, the `cmp r1, #9; beq` at
    0x08051448) and its LED shows it (0x0805175A: the colour 0x402 with the bit, 0x404 without, into [frame + 0x52]);
  * 0x08035814 (at start-up and on a change of the bit): the bit picks the USB set-up 0x101 / 0x001 for 0x080432A8: with the bit, the device
    object 0x200000D0 registers a second class, 0x200000FC, whose vtable 0x08067730 is the mass storage's (0x080661DC .. : its init resets
    the bulk-only transport 0x0802F00C, its configuration descriptor 0x080688EC, interface 8 / 6 / 0x50, "Novation MSD"); so **bit 17 = 1 =
    Easy Start on** (RD1's dump: on, USB MIDI and the drive together).  Its buffer is the whole backup SRAM (0x08045DDC, 0x0802F17C).
  * The mass storage's object is made at start-up whatever the bit (0x080276B6: kept, the heap's layout stays).
Here:
  * 0x08035820 `ubfx r0, r1, #0x11, #1` -> `movs r0, #0; nop`: the USB set-up without the mass storage, always;
  * 0x0805144A `beq` (button 9) -> `nop`: the button does nothing; 0x0805176C `ldrh r0, [r5, r0]` -> `movs r0, #0`: its LED dark;
  * the two calls from the endpoints' service (0x0802764A `bl 0x0802F014`, 0x0802766E `b.w 0x0802F04A`) -> nothing: the transport and the
    SCSI layer can no longer run from anywhere;
  * the code only they reach, filled with 0xFF and given to the build as places for our code (HOLES): the bulk-only transport
    0x0802EFC8-0x0802F183, the SCSI layer 0x080458D0-0x08045DFB, the class's callbacks 0x080661DC-0x080662BB (their literals after, kept).
    Nothing else branches into them, loads from them or holds their addresses (checked over the whole stock image; the stray matches are
    data: three words that are instruction bytes, a `b` decoded from the bytes at 0x08065ECE and one at 0x080620D4).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import h  # noqa: E402

HOLES = ((0x0802EFC8, 0x0802F184), (0x080458D0, 0x08045DFC), (0x080661DC, 0x080662BC))
NOP, NOPW = h(0xBF00), h(0xF3AF) + h(0x8000)
HOOKS = ((0x08035820, "ubfx r0, r1, #0x11, #1", h(0x2000) + NOP),             # movs r0, #0; nop
         (0x0805144A, "beq #0x8051456", NOP),
         (0x0805176C, "ldrh r0, [r5, r0]", h(0x2000)),
         (0x0802764A, "bl #0x802f014", NOPW),
         (0x0802766E, "b.w #0x802f04a", h(0x4770) + NOP))                    # bx lr; nop (its pop.w {r4, lr} just before)


def free(b):
    """At the build's start: the hooks, the holes 0xFF and listed in b.holes."""
    for at, expect, new in HOOKS:
        b.hook(at, expect, new)
    for lo, hi in HOLES:
        o = lo - b.BASE
        b.img[o:hi - b.BASE] = bytes([0xFF]) * (hi - lo)
        b.patched.append((o, hi - lo))
        b.holes.append([lo, hi])
    b.report["noes"] = dict(hooks=[hex(a) for a, _, _ in HOOKS], holes=[(hex(lo), hex(hi)) for lo, hi in HOLES],
                            freed=sum(hi - lo for lo, hi in HOLES))
