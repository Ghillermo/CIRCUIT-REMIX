"""Circuit Rhythm 5706 - RH88 (MIT): RH87 + the end of a mutating track's chain = its list's last slot (patchain / mutate OPT mtend: a
scene chain moves on after the whole list).  docs/PRUEBA_RH88.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh87  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH88"


def build(name=NAME, **kw):
    with rhbuild.options(mtend=True):
        b = build_rh87.build(name, **kw)
    return b


if __name__ == "__main__":
    build().finish()
