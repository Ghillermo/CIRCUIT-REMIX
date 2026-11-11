"""Circuit Rhythm 5706 - RH87 (MIT): RH86 + the matrix's destinations for every parameter but the FM's operators, in the views' order;
Sample mode: a held engine pad = its starters only, pad 8 held = every saved patch (docs/DISENO_RH87.md); the room from the curve tables
packed into the ITCM (tools/tabpack.py).  docs/PRUEBA_RH87.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh86  # noqa: E402
import modmx  # noqa: E402
import rhbuild  # noqa: E402
import tabpack  # noqa: E402

NAME = "RH87"


def build(name=NAME, **kw):
    tabpack.reset()
    with rhbuild.options(tabpack=True, mx64=True, starters=True):
        b = build_rh86.build(name, **kw)
        modmx.late(b.img, b.report)
        b.add("tabpack", tabpack)
    return b


if __name__ == "__main__":
    build().finish()
