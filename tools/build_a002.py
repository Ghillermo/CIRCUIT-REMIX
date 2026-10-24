"""Circuit Remix Alpha 0.02 (MIT): RH34 without rdiag (no remote diagnostics: no memory reads or card writes over SysEx), under its public name
(the marker A0.02): every function up to RH34 (the full Stock+ knob page: pitch envelope / LFO, ring mod, filter types and pitch follow, the
stretch with WSOLA, bitcrush, the start-point scan; Fixed Recording at the external clock's tempo)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh34  # noqa: E402

NAME = "A0.02"


def build(name=NAME, **kw):
    return build_rh34.build(name, diag=False, **kw)


if __name__ == "__main__":
    build().finish()
