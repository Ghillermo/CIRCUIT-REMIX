"""Circuit Rhythm 5706 - RH75 (MIT): RH74 + the latch (tools/latch.py; cscale OPT latch; the user, 2026-11-05: «custom scale now lives on
shift+note during note expand view. Shift any note pad is now latch. Playing or sequencing a new note after the latch transposes the whole
latch, making a moving chord», «Arpeggios also play the latched notes»).  docs/PRUEBA_RH75.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh72  # noqa: E402
import latch  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH75"


def build(name=NAME, **kw):
    with rhbuild.options(polycap=2, latch=True):
        b = build_rh72.build(name, **kw)
        b.add("latch", latch)
    return b


if __name__ == "__main__":
    build().finish()
