"""Circuit Rhythm 5706 - RH63 (MIT): RH62 + what the user chose of CIRCUIT-HACKS (2026-11-01: «Modificadores del arpegio, Nudge de tramo, Guardar al
parar, Curva de velocity»):
  * tools/savedefer.py: Advanced Setup pad 24: the project save waits for the transport to stop (Save blinks yellow meanwhile);
  * tools/velcurve.py: Advanced Setup K1: the pads' velocity curve, -8 .. +8;
  * playmode nudge2: Pattern Settings pad 26 moves the selected range one step back, Shift + pad 26 forward;
  * tools/arpmods.py: Pattern Settings, Shift, the arpeggiator on: pads 1-16 = octave spread and position, groove, reset.
docs/PRUEBA_RH63.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh62  # noqa: E402
import rhbuild  # noqa: E402
import savedefer  # noqa: E402
import velcurve  # noqa: E402

NAME = "RH63"


def build(name=NAME, **kw):
    with rhbuild.options(compact=True, setp3=True, nudge2=True, armods=True):
        b = build_rh62.build(name, **kw)
        b.add("savedefer", savedefer)
        b.add("velcurve", velcurve)
    return b


if __name__ == "__main__":
    build().finish()
