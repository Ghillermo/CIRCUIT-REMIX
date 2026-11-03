"""Circuit Rhythm 5706 - RH65 (MIT): RH64 + modmx mxx (CIRCUIT-HACKS' lanex and slock's ramps): a ninth automation lane a track, one value a step, in
the steps' byte 7; ramps in the automation view (a yellow step held + another step).  docs/PRUEBA_RH65.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh64  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH65"


def build(name=NAME, **kw):
    with rhbuild.options(compact=True, mxx=True):
        return build_rh64.build(name, **kw)


if __name__ == "__main__":
    build().finish()
