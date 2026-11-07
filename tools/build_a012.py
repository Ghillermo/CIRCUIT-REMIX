"""Circuit Remix Alpha 0.12 (MIT): RH80 without rdiag (no remote diagnostics: no memory reads or card writes over SysEx), under its public name
(the marker A0.12): Alpha 0.10's functions plus RH68-RH80 (the retriggers' de-click, core 0's code packed (dspz), the 8-operator FM, the
polyphony with a cap, the latch, the VA, the bipolar knobs' lighter left half, each project's synth sounds on the card, the engines in Sample
mode with the voice modes, the track menu as CIRCUIT-HACKS' row 1 with the Filter / VCA, Envelope + LFO and OSC 1 / OSC 2 pages).
Without Arrhythmia's module host (dspz does not go with modhost).  Experimental."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh80  # noqa: E402

NAME = "A0.12"


def build(name=NAME, **kw):
    return build_rh80.build(name, diag=False, **kw)


if __name__ == "__main__":
    build().finish()
