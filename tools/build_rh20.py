"""Circuit Rhythm 5706 - RH20 = RH19 with drumarp's recorder (MIT): playing with Record, each hit of the arpeggio (samples or notes) is written
into the pattern at the micro step it sounds on (the sample flip / the note; an empty step gets the hit's velocity and probability 7), and into
the edit copies when they hold that pattern."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh19  # noqa: E402

NAME = "RH20"


def build(name=NAME, **kw):
    return build_rh19.build(name, arp_rec=True, **kw)


if __name__ == "__main__":
    build().finish()
