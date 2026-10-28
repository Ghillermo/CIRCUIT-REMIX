"""Circuit Remix Alpha 0.06 (MIT): RH54 without rdiag (no remote diagnostics: no memory reads or card writes over SysEx), under its public name
(the marker A0.06): Alpha 0.05's functions plus RH54 (the envelope by the play mode for the synth and the granular on an Envelope page,
the line input from the reverb's / delay's returns with the track's VCA and filter on its gate).  Experimental."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh54  # noqa: E402

NAME = "A0.06"


def build(name=NAME, **kw):
    return build_rh54.build(name, diag=False, **kw)


if __name__ == "__main__":
    build().finish()
