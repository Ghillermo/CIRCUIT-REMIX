"""Circuit Remix Alpha 0.09 (MIT): RH59 without rdiag (no remote diagnostics: no memory reads or card writes over SysEx), under its public name
(the marker A0.09): Alpha 0.08's functions plus RH57-RH59 (the stereo link's second track as offsets, steady page LEDs, the track's modes on
Sample mode's pads, an FX return routed to a line track, CIRCUIT-HACKS' automation, the stock's start / length on granular and synth).
Experimental."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh59  # noqa: E402

NAME = "A0.09"


def build(name=NAME, **kw):
    return build_rh59.build(name, diag=False, **kw)


if __name__ == "__main__":
    build().finish()
