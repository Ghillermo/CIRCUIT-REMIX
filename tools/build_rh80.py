"""Circuit Rhythm 5706 - RH80 (MIT): RH79 + the room in the flash (core 0's stock block packed with ours: tools/dspz.py OPT dzhole) + the
synth's voice modes (tools/vmode0.py: CIRCUIT-HACKS' eight) + the engines in Sample mode + the track menu as Hacks' row 1 + the VA's OSC 1 /
OSC 2 pages (docs/DISENO_RH80.md).  docs/PRUEBA_RH80.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh79  # noqa: E402
import esel  # noqa: E402
import vsel  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH80"


def build(name=NAME, **kw):
    with rhbuild.options(dzhole=True, vmode=True, vsel=True, envx=True):
        b = build_rh79.build(name, **kw)
        b.add("esel", esel)
        b.add("vsel", vsel)
    return b


if __name__ == "__main__":
    build().finish()
