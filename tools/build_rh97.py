"""Circuit Rhythm 5706 - RH97 (MIT): RH96 without Easy Start, its code and the free flash used for ours (the user, 2026-11-13: «You can drop
the "easy start" completely and compact the Code to make room»): tools/noes.py (the USB mass storage never set up, Advanced Setup's
button 9 nothing and dark, its code free), the lanes' backup SRAM always ours (xlanes with noes), the tables from just after core 1's packed
block (tabpack's tabflash2), and the modules that fit put in the holes instead of the cave (tools/holes.py: two passes)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh96  # noqa: E402
import holes  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH97"


def build(name=NAME, place=True, **kw):
    old = dict(rhbuild.PLACE)
    rhbuild.PLACE.clear()
    try:
        with rhbuild.options(noes=True, tabflash2=True):
            b = build_rh96.build(name, **kw)
            if not place:
                return b
            p = holes.plan(b)
            rhbuild.PLACE.update(p)
            b2 = build_rh96.build(name, **kw)
        b2.report["holes"] = holes.report(b, p)
        return b2
    finally:
        rhbuild.PLACE.clear()
        rhbuild.PLACE.update(old)


if __name__ == "__main__":
    build().finish()
