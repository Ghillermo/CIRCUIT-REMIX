"""Circuit Rhythm 5706 - RH24 = RH23 + midithru (MIT): Duplicate in Advanced Setup cycles the Thru jack through Thru -> Out 2 -> Merge (the DIN In
copied to it, with the unit's MIDI) -> Filter (the DIN In but the channels the unit listens on); its LED green / dim red / yellow / blue."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh23  # noqa: E402
import midithru  # noqa: E402

NAME = "RH24"


def build(name=NAME, **kw):
    b = build_rh23.build(name, **kw)
    b.add("midithru", midithru)
    return b


if __name__ == "__main__":
    build().finish()
