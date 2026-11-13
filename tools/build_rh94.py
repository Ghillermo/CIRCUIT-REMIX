"""Circuit Rhythm 5706 - RH94 (MIT): RH93 + fxseq OPT thrknob (docs/PRUEBA_RH94.md; the user on RH93): a throw saved on a pad with the
stock's assign mode (pad 15) keeps its macros 100 / 0 (the stock's defaults put 0: a silent throw); on a held throw K1 = the sends' level,
K3 = the delay's feedback / the reverb's decay (lit in its colour, the value as brightness); K2's list with Digitiser after Vinyl."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh93  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH94"


def build(name=NAME, **kw):
    with rhbuild.options(thrknob=True):
        return build_rh93.build(name, **kw)


if __name__ == "__main__":
    build().finish()
