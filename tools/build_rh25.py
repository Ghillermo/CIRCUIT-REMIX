"""Circuit Rhythm 5706 - RH25 = RH24 + pgmch (MIT): the project's Program Change channels: a listen channel and an output channel (16 by default),
the incoming ones forwarded to the output; in the Setup view pad 29 / 30 the first time shows them on pads 1-16, a channel pad sets them."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh24  # noqa: E402
import pgmch  # noqa: E402

NAME = "RH25"


def build(name=NAME, **kw):
    b = build_rh24.build(name, **kw)
    b.add("pgmch", pgmch)
    return b


if __name__ == "__main__":
    build().finish()
