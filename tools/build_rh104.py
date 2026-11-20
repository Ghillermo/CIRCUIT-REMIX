"""Circuit Rhythm 5706 - RH104 (MIT): RH103 + fixes ported from CIRCUIT-HACKS (the user, 2026-11-19: «keep porting Hacks fixes and features»;
docs/PRUEBA_RH104.md):
  * tools/paintguard.py: the stock's probability-view painter (0x0805761E) never writes past its 16 pads (Hacks' Beta 5.65: a probability
    byte of 16 or more wrote into the next object);
  * OPT fxbyte (fxseq): an FX track's flag off R + 0x61 (scene 1's + 33, which the stock rewrites whenever scene 1 is saved or cleared) to
    R + 0x42; a project of RH92-RH103 moved over once;
  * OPT scclr (patchain): Clear + a scene pad also puts the scene back in the normal mode and one play (Hacks' Alpha 7.04)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh103  # noqa: E402
import paintguard  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH104"


def build(name=NAME, **kw):
    with rhbuild.options(fxbyte=True, scclr=True):
        b = build_rh103.build(name, **kw)
        b.add("paintguard", paintguard)
    return b


if __name__ == "__main__":
    build().finish()
