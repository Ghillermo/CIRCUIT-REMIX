"""Circuit Rhythm 5706 - RH82 (MIT): RH81 + the sticky track menu stays open after a view is picked (synthpage OPT menustay; the user,
2026-11-07: «pages view no longer close after selecting a view»): a tap on the selected track's button, another button or leaving the track
views closes it.  docs/PRUEBA_RH82.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh81  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH82"


def build(name=NAME, **kw):
    with rhbuild.options(menustay=True):
        b = build_rh81.build(name, **kw)
    return b


if __name__ == "__main__":
    build().finish()
