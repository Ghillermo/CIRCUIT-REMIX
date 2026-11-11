"""Circuit Rhythm 5706 - RH90 (MIT): RH89 + GM mode's knobs (one colour, the brightness = the GM note, a new note plays its track;
gmmode OPT gmui2) + Clear + track / Clear + knob back to the track's chosen preset (docs/PRUEBA_RH90.md)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh89  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH90"


def build(name=NAME, **kw):
    with rhbuild.options(gmui2=True, pclr=True):
        b = build_rh89.build(name, **kw)
    return b


if __name__ == "__main__":
    build().finish()
