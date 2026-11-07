"""Circuit Rhythm 5706 - RH72 (MIT): RH71 + the synth's polyphony (tools/poly0.py on core 0, fmpage's pad 13 on the ARM; the user,
2026-11-04: «can we have some polyphony for synths or samples¿?» -> «Per-track switch, 4 voices shared», «Sample mode pad 13», «Up to 4, the
free ones»).  Room on core 0: synth0 and granular0 with their one-word moves (s0short / g0short).  docs/PRUEBA_RH72.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh71  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH72"


def build(name=NAME, **kw):
    with rhbuild.options(poly=True):
        return build_rh71.build(name, **kw)


if __name__ == "__main__":
    build().finish()
