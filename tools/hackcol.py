"""CIRCUIT-HACKS' engine colours for the Rhythm's engines and their views (MIT; RH81; the user, 2026-11-07: «Iguala los colores de los motores
con Hacks», «Las vistas toman el color nuevo», the table confirmed: docs/DISENO_RH81.md).

    with hackcol.applied(): ...build...

Sets, for the build inside, the modules' colour constants (the code reads them when it is made; the earlier builds keep theirs):
  * the engine row (esel): sample teal, input only white, input -> VCA / VCF / FX yellow, VA green, VA-drum orange, wavetable sand,
    granular magenta, FM violet (bright / dim pairs of the palette);
  * the views: the VA's (synthpage: its pages, knobs, the menu's pad) green, the granular's magenta, the FM's violet.
"""
from __future__ import annotations

import contextlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

TEAL, WHITE, YELLOW, GREEN, ORANGE, SAND, MAGENTA, VIOLET = (0x4B, 0x4E), (0x01, 0x09), (0xBC, 0xCA), (0xBE, 0xCC), (0xBA, 0xC8), \
    (0xA9, 0xA8), (0xC3, 0xD1), (0xC2, 0xD0)
COL_E = (TEAL, WHITE, YELLOW, GREEN, ORANGE, SAND, MAGENTA, VIOLET)


def _sets():
    import esel
    import fm8page
    import fmpage
    import granpage
    import smodes
    import stockplus as SP
    import synthpage
    import linein as LI
    return [(synthpage, "UI_KNOB", GREEN[0]), (synthpage, "UI_BLINK", GREEN[0]), (synthpage, "UI_DIM", GREEN[1]),
            (granpage, "UI_KNOB", MAGENTA[0]), (granpage, "UI_BLINK", MAGENTA[0]), (granpage, "UI_DIM", MAGENTA[1]),
            (granpage, "UI_PAGES", ((0x01, 0x09), (SP.UI_KNOB, SP.UI_DIM), MAGENTA)),
            (fmpage, "COL_FM", VIOLET[0]), (fmpage, "DIM_FM", VIOLET[1]), (fmpage, "COL_VA", GREEN[0]), (fmpage, "DIM_VA", GREEN[1]),
            (fm8page, "COL_FM", VIOLET[0]), (fm8page, "DIM_FM", VIOLET[1]),
            (smodes, "COLS", ((0x01, 0x09), MAGENTA, GREEN, (LI.UI_COL, LI.UI_DIM))),
            (esel, "COL_E", COL_E)]


@contextlib.contextmanager
def applied():
    sets = _sets()
    old = [(m, k, getattr(m, k)) for m, k, _ in sets]
    for m, k, v in sets:
        setattr(m, k, v)
    try:
        yield
    finally:
        for m, k, v in old:
            setattr(m, k, v)
