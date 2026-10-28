"""Circuit Remix Alpha 0.05 (MIT): RH53 without rdiag (no remote diagnostics: no memory reads or card writes over SysEx), under its public name
(the marker A0.05): Alpha 0.04's functions plus the synth (RH51) and the interface of docs/INTERFAZ.md (RH52 / RH53: the pages' colours, the track
menu with the pages on pads 1-4 and the toggles under them, sticky on a tap, the synced halves faster towards the left end, off = the dim of its own colour).
Experimental."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh53  # noqa: E402

NAME = "A0.05"


def build(name=NAME, **kw):
    return build_rh53.build(name, diag=False, **kw)


if __name__ == "__main__":
    build().finish()
