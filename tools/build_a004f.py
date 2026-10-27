"""Circuit Remix A0.04F (MIT): RH50 (Alpha 0.04 with rdiag, for reading the count-in's log over USB) + tools/vismet.py (Clear flashes on each
silent click) + tools/clkci.py (the count-in on the music's clock, master or slave, with a held start) + tools/stepload.py (a faster step load
on Play) + tools/errled.py (the Clear LED blinks red while one of these features is off).  Slots: vismet in rhstate's OFF, clkci in OFF2.
The marker A0.04F."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh50  # noqa: E402
import vismet  # noqa: E402
import clkci  # noqa: E402
import stepload  # noqa: E402
import errled  # noqa: E402

NAME = "A0.04F"


def build(name=NAME, diag=True, **kw):
    b = build_rh50.build(name, diag=diag, **kw)
    b.add("vismet", vismet)
    b.add("clkci", clkci)
    b.add("stepload", stepload)
    b.add("errled", errled)                       # last: it checks the features above
    return b


if __name__ == "__main__":
    build().finish()
