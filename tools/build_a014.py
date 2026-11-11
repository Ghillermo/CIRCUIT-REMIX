"""Circuit Remix Alpha 0.14 (MIT): RH93 without rdiag (no remote diagnostics: no memory reads or card writes over SysEx), under its public name
(the marker A0.14): Alpha 0.13 plus the Grid FX type knob (a slot held + K2, the stock's list: Auto-Filter and Digitiser included) going on to
the delay throw and the reverb throw, without Shift + K1, and a throw slot the Grid FX view already knows as one working again.  Experimental."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh93  # noqa: E402

NAME = "A0.14"


def build(name=NAME, **kw):
    return build_rh93.build(name, diag=False, **kw)


if __name__ == "__main__":
    build().finish()
