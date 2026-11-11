"""Circuit Rhythm 5706 - RH93 (MIT): RD50 + fxseq OPT k2type (docs/PRUEBA_RH93.md): the Grid FX view's type knob (a slot held + K2, the
stock's list of types 0-6) goes on to our delay throw (7) and reverb throw (8): the list loop's bound, K2 in their knob layout, their macros
(100, 0) on a type change, and the old type's off for them (the stock would write parameter id 0)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rd50  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH93"


def build(name=NAME, **kw):
    with rhbuild.options(k2type=True):
        return build_rd50.build(name, **kw)


if __name__ == "__main__":
    build().finish()
