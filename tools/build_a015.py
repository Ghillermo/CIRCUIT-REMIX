"""Circuit Remix Alpha 0.15 (MIT): RH94 without rdiag (no remote diagnostics: no memory reads or card writes over SysEx), under its public name
(the marker A0.15): Alpha 0.14 plus the Grid FX throws as the stock's types: saved on a pad with the stock's assign mode (pad 15) they keep
their levels, K1 / K3 set them on a held throw, and Digitiser comes after Vinyl in K2's list.  Experimental."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh94  # noqa: E402

NAME = "A0.15"


def build(name=NAME, **kw):
    return build_rh94.build(name, diag=False, **kw)


if __name__ == "__main__":
    build().finish()
