"""Circuit Rhythm 5706 - RH55 (MIT): RH54 + Stock+ for every sound (the user, 2026-10-28: «Stock+ for every sound»; «Start RH55: Stock+ for
every sound (LFO, pitch envelope, waveshaping, FX for granular and synth on core 0)»; the choices: the stock's distortion knob on the
granular and the synth too, K7 = a waveshaper + its type, K8 = the grains' position / the synth's FM amount):
  * core 0 (tools/sp0.py, synth0 / granular0 / granchain sp): the pitch envelope and LFO, the scan LFO, K6's filter types and follow, the
    ring mod, the waveshaper and the stock's distortion knob on the granular and synth tracks;
  * the ARM (tools/spall.py): the track menu's Stock+ page (pad 2) for a granular or synth track too; K7 / Shift + K7 there = the
    waveshaper's amount / type; their words to core 0, core 1's Stock+ words neutral for those tracks.
docs/PRUEBA_RH55.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh54  # noqa: E402
import spall  # noqa: E402

NAME = "RH55"


def build(name=NAME, **kw):
    b = build_rh54.build(name, rh55=True, **kw)
    b.add("spall", spall)
    return b


if __name__ == "__main__":
    build().finish()
