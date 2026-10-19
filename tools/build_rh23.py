"""Circuit Rhythm 5706 - RH23 = RH22 with fxkeys (cols=True) (MIT): the user, 2026-10-19: «octave keys on fx view dont change color, duplicate
light either»: in the FX view up = the delay presets' peach, down = the reverb presets' cream (the page shown bright, the other dim), Duplicate
(the reset) light blue; with Shift up / down yellow (Shift + up / down = the master filter's resonance)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh21  # noqa: E402
import kbright  # noqa: E402

NAME = "RH23"


def build(name=NAME, **kw):
    b = build_rh21.build(name, bright=True, arp1=True, fxcols=True, **kw)
    b.add("kbright", kbright)
    return b


if __name__ == "__main__":
    build().finish()
