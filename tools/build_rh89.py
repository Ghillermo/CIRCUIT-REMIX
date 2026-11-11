"""Circuit Rhythm 5706 - RH89 (MIT): RH88 + the mutate's Amount in two columns: every slot, then 7 .. 1 slots of the chain change
(mutate OPT amt8; Repeats / Keep slot 1 one column to the right).  docs/PRUEBA_RH89.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh88  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH89"


def build(name=NAME, **kw):
    with rhbuild.options(amt8=True):
        b = build_rh88.build(name, **kw)
    return b


if __name__ == "__main__":
    build().finish()
