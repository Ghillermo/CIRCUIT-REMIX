"""Circuit Rhythm 5706 - RH86 (MIT): RH85 + mefisme's Pattern Mutate (rhythm-plus, MIT; credit mefisme), our own code on its findings
(docs/DISENO_RH86.md): tools/mutate.py; the flash for it from fm8page's tables packed into the ITCM (OPT itab).  docs/PRUEBA_RH86.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh85  # noqa: E402
import mutate  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH86"


def build(name=NAME, **kw):
    with rhbuild.options(itab=True, mutate=True):
        b = build_rh85.build(name, **kw)
        b.add("mutate", mutate)
    return b


if __name__ == "__main__":
    build().finish()
