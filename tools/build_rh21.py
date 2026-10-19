"""Circuit Rhythm 5706 - RH21 = RH20 + tools/sesscopy.py (MIT): in the Projects view, with the transport stopped, Duplicate + pad A = the source,
Duplicate + pad B = A's project copied into B (this pack or, after loading another pack, that one; a B that holds a project asks first: Duplicate +
B again within ~5 s); #12 of docs/PORTADO.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh20  # noqa: E402
import sesscopy  # noqa: E402

NAME = "RH21"


def build(name=NAME, **kw):
    b = build_rh20.build(name, **kw)
    b.add("sesscopy", sesscopy)
    return b


if __name__ == "__main__":
    build().finish()
