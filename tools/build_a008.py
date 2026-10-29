"""Circuit Remix Alpha 0.08 (MIT): RH56 without rdiag (no remote diagnostics: no memory reads or card writes over SysEx), under its public name
(the marker A0.08): Alpha 0.07's functions plus RH56 (mefisme's pull request 7: the count-in on the music's clock, the visual metronome, the
faster step load on Play and the error light).  Experimental."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh56  # noqa: E402

NAME = "A0.08"


def build(name=NAME, **kw):
    return build_rh56.build(name, diag=False, **kw)


if __name__ == "__main__":
    build().finish()
