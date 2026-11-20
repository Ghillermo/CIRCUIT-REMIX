"""Circuit Remix Alpha 0.16 (MIT): RH104 without rdiag (no remote diagnostics: no memory reads or card writes over SysEx), under its public name
(the marker A0.16): Alpha 0.15 plus everything up to RH104 (RH95-RH104: more room in the flash and the RAM, the extra automation lanes in the
pack's patch bank, Easy Start removed, the synth pages automated, a lighter LED task, the FM algorithm map and custom routing, OSC 1's sub and
noise, the input gain, Duplicate + an empty patch slot, knob hold, and the fixes of RH103 / RH104: a project load no longer writes the
project's synth sounds and lanes over the loaded one's, the FX track survives saving scene 1).  Experimental."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh104  # noqa: E402

NAME = "A0.16"


def build(name=NAME, **kw):
    return build_rh104.build(name, diag=False, **kw)


if __name__ == "__main__":
    build().finish()
