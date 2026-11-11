"""Circuit Remix Alpha 0.13 (MIT): RD50 without rdiag (no remote diagnostics: no memory reads or card writes over SysEx), under its public name
(the marker A0.13): Alpha 0.12's functions plus RH81-RH92 and RD47-RD50 (the engine colours and patches of the pack, demo patches, the VA's
FM / RING fix, 2x oversampling and OSC 2 as a harmonic ratio, Pattern Mutate (mefisme's Rhythm Plus design), every parameter as a matrix
destination, starters per engine, the chosen preset back with Clear, the FX sequencer over the Grid FX with per-track sends, the looper /
live sampler in the Grid FX view, the firmware identity query).  Experimental."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rd50  # noqa: E402

NAME = "A0.13"


def build(name=NAME, **kw):
    return build_rd50.build(name, diag=False, **kw)


if __name__ == "__main__":
    build().finish()
