"""Circuit Rhythm 5706 - RH28 = RH27 + mfsess (MIT): the master filter's resonance (Shift + up / down in the FX view, RH13) saved with the project
in the record's tail and applied again after a load (the master group is global in the stock)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh27  # noqa: E402
import mfsess  # noqa: E402

NAME = "RH28"


def build(name=NAME, **kw):
    b = build_rh27.build(name, **kw)
    b.add("mfsess", mfsess, **({"track": True} if kw.get("rh30") else {}))
    return b


if __name__ == "__main__":
    build().finish()
