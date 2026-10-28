"""Circuit Remix Alpha 0.07 (MIT): RH55 without rdiag (no remote diagnostics: no memory reads or card writes over SysEx), under its public name
(the marker A0.07): Alpha 0.06's functions plus RH55 (Stock+ for every sound: the Stock+ page on granular and synth tracks, on DSP core
0; K7 there a waveshaper; the stock's distortion knob on them too).  Experimental."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh55  # noqa: E402

NAME = "A0.07"


def build(name=NAME, **kw):
    return build_rh55.build(name, diag=False, **kw)


if __name__ == "__main__":
    build().finish()
