"""Circuit Rhythm 5706 - RH84 (MIT): RH83 + tools/va0.py OPT fmword (2026-11-08; the user: «Fix FM/RING first»): the VA's OSC 2 FM amount read
from its word +6, where the ARM writes the Synth page's FM knob (RH77-RH83 read +7, RING's: K6 FM did nothing and RING set the FM too).
docs/PRUEBA_RH84.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh83  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH84"


def build(name=NAME, **kw):
    with rhbuild.options(fmword=True):
        b = build_rh83.build(name, **kw)
    return b


if __name__ == "__main__":
    build().finish()
