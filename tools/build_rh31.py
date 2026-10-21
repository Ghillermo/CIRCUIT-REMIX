"""Circuit Rhythm 5706 - RH31 = RH30 + drumpat recdyn (MIT; the user, 2026-10-21: «with Record on, write each played step's dynamics (velocity
and micro step) into the step, as on the Tracks»): playing with Record, a step whose dynamics (Pattern Settings pad 25, row 3) vary its hit gets
that velocity and that later micro step written into the step (the pattern and both copies of its step store), and its dynamics cleared."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh30  # noqa: E402

NAME = "RH31"


def build(name=NAME, **kw):
    return build_rh30.build(name, rh31=True, **kw)


if __name__ == "__main__":
    build().finish()
