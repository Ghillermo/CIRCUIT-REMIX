"""Circuit Rhythm 5706 - RH85 (MIT): RH84 + the VA's 2x per track (the user, 2026-11-09: RD45 on the device «cleaner» on one voice, worse on
some settings and in poly -> «Per-track switch», «Sample mode pad», «With project and patches»): tools/va0.py OPT os2 = 2 (the key per slot
at X:$5258 + $40 s, the history cleared at 1x), tools/poly0.py polycap 3 (a stall can no longer raise the room; the voice's class charged),
the Sample mode pad, the slots' keys and the halfband's coefficients from the ARM, the bit in the project's sound and in VA patches (OPT va2x),
and OSC 1's envelope depths turn the second oscillator on (OPT dualext).  docs/PRUEBA_RH85.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh84  # noqa: E402
import rhbuild  # noqa: E402
import steadyled  # noqa: E402

NAME = "RH85"


def build(name=NAME, **kw):
    with rhbuild.options(os2=2, polycap3=True, va2x=True, dualext=True, modkeep=True, ratio2=True, va2x1=True), steadyled.applied():
        b = build_rh84.build(name, **kw)
    return b


if __name__ == "__main__":
    build().finish()
