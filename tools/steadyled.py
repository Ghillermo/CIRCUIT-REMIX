"""Steady LED colours (MIT; RH85; the user, 2026-11-10: «toggles and selectors should show dim when off, bright when on. Bug: now some are
bright, others dim and others flicker» -> «whatever you choose must be consistent all over the mod options»).

The Rhythm's colour table (RAM 0x20003974, 4 bytes a code: B, G, R, 0) animates about 50 codes (read on the device: 0x0A-0x0D, 0x14,
0x15, 0x1A, 0x1B, 0x20-0x24, 0x27, 0x28, 0x31, 0x32, 0x39, 0x3A, 0x3D, 0x3E, 0x45, 0x46, 0x49, 0x4A, 0x4D, 0x4E, 0x58-0x5D, 0x69,
0x6A, 0xA8, 0xC4-0xD1); on the Tracks the same codes are plain colours, so the dims taken from CIRCUIT-HACKS (RH81, tools/hackcol.py)
pulse here.  The rule for the whole mod: off = a steady dim, on / selected = a steady bright; no code of ours in ANIMATED.

    with steadyled.applied(): ...build...

replaces, for the build inside, every animated code our modules use by a steady one of the same hue (the stock table's nearest at the
same level), as hackcol.applied() does for its colours: hackcol's pairs (the engines, the voice modes through esel.COL_M), vsel's
Filter / VCA dim, fm8page's 4-operator lists dim, latch's colour, synthpage's K7 nand zone.
"""
from __future__ import annotations

import contextlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ANIMATED = frozenset([0x0A, 0x0B, 0x0C, 0x0D, 0x14, 0x15, 0x1A, 0x1B, 0x20, 0x21, 0x22, 0x23, 0x24, 0x27, 0x28, 0x31, 0x32, 0x39, 0x3A,
                      0x3D, 0x3E, 0x45, 0x46, 0x49, 0x4A, 0x4D, 0x4E, 0x58, 0x59, 0x5A, 0x5B, 0x5C, 0x5D, 0x69, 0x6A, 0xA8]
                     + list(range(0xC4, 0xD2)))
STEADY = {0x4E: 0x4C,          # sample teal's dim
          0xCA: 0x30,          # yellow (input -> VCA, legato)
          0xCC: 0x1F,          # VA green (retrigger): the green toggles' dim
          0xC8: 0x52,          # VA-drum orange (drawn dark today)
          0xA8: 0x91,          # wavetable sand (drawn dark today)
          0xD1: 0x38,          # granular magenta (poly)
          0xD0: 0x63,          # FM violet (always-glide): the only steady violet dim (also the matrix's)
          0xCD: 0x34,          # Filter / VCA lime: no steady lime dim, the nearest green-grey
          0x27: 0xE6,          # FM's 4-operator lists
          0x1A: 0xA1,          # latch (bright): pale aqua, no steady ice blue
          0x1B: 0x08}          # synth K7 nand zone: silver


def fix(c):
    return STEADY.get(c, c)


def fix_t(t):
    """a colour, or a tuple / list of them (nested), with every animated code replaced"""
    if isinstance(t, int):
        return fix(t)
    return type(t)(fix_t(x) for x in t)


def _sets():
    import esel
    import fm8page
    import hackcol
    import latch
    import synthpage
    import vsel
    out = [(hackcol, k, fix_t(getattr(hackcol, k))) for k in ("TEAL", "WHITE", "YELLOW", "GREEN", "ORANGE", "SAND", "MAGENTA", "VIOLET",
                                                               "COL_E")]
    out += [(esel, "COL_M", fix_t(esel.COL_M)), (vsel, "DIM_FILT", fix(vsel.DIM_FILT)), (fm8page, "ALG_COL", fix_t(fm8page.ALG_COL)),
            (latch, "COL", fix(latch.COL)), (synthpage, "VA_ZONES", fix_t(synthpage.VA_ZONES))]
    return out


@contextlib.contextmanager
def applied():
    import esel
    sets = _sets()
    old = [(m, k, getattr(m, k)) for m, k, _ in sets]
    old_cm = esel.col_m
    for m, k, v in sets:
        setattr(m, k, v)
    esel.col_m = lambda: fix_t(old_cm())                                     # (RH81's always-glide pair appended)
    try:
        yield
    finally:
        esel.col_m = old_cm
        for m, k, v in old:
            setattr(m, k, v)
