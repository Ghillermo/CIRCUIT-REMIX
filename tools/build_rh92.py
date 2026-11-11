"""Circuit Rhythm 5706 - RH92 (MIT): RH91 + the FX sequencer over the Grid FX (tools/fxseq.py; docs/DISENO_RH92.md, docs/PRUEBA_RH92.md):
an FX track (Sample mode's selector, pad 21) is silent, its sample picks a Grid FX slot and its notes gate it (Octave down / up + step =
random / the last again); two new Grid FX types, delay throw and reverb throw / wash (a slot held + Shift + K1 in the Grid FX view)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh91  # noqa: E402
import fxseq  # noqa: E402

NAME = "RH92"


def build(name=NAME, **kw):
    b = build_rh91.build(name, **kw)
    b.add("fxseq", fxseq)
    return b


if __name__ == "__main__":
    build().finish()
