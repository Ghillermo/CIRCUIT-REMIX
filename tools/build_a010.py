"""Circuit Remix Alpha 0.10 (MIT): RH65 without rdiag (no remote diagnostics: no memory reads or card writes over SysEx), with the cold-boot fix
(autoinit bootok: RD34 / RD36), under its public name (the marker A0.10): Alpha 0.09's functions plus RH60-RH65 (1-in-n per pattern in a chain,
on its last pass, the track's trigger flash, more FX feedback, pad 8 resets every page, Clear + track through the parameter router,
CIRCUIT-HACKS' arpeggio modifiers, range Nudge, save on stop and velocity curve, the modulation matrix, the sequenceable and non-sequenceable
pages, the extra lane and ramps).  Without RH66's ideas from Arrhythmia (dspgate, itcm; the user, 2026-11-03).  Experimental."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh65  # noqa: E402

NAME = "A0.10"


def build(name=NAME, **kw):
    return build_rh65.build(name, diag=False, bootok=True, **kw)


if __name__ == "__main__":
    build().finish()
