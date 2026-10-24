"""Circuit Remix Alpha 0.01F (MIT): Alpha 0.01 + tools/fixedrec.py (Fixed Recording at the external MIDI clock's tempo), without rdiag
(the marker A0.01F)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_a001  # noqa: E402
import fixedrec  # noqa: E402

NAME = "A0.01F"


def build(name=NAME, **kw):
    b = build_a001.build(name, **kw)
    b.add("fixedrec", fixedrec)
    return b


if __name__ == "__main__":
    build().finish()
