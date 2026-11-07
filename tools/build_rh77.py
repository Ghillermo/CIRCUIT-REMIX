"""Circuit Rhythm 5706 - RH77 (MIT): RH76 with RD43's VA (tools/va0.py V3: CIRCUIT-HACKS' oscillators with the 4-sample BLEP, the hard sync,
FM both ways, ring and bitwise) played from the device: the Synth page laid out as Hacks' OSC pages (synthpage OPT vapage; the user,
2026-11-06: «haz la build de rythm con el VA», «Like Hacks»): K1 WAVE, K2 SHAPE, K3 WAVE 2, K4 SHAPE 2, K5 TUNE 2, K6 FM, K7 sync + bitwise,
K8 MIX; Shift: env -> pitch, env -> shape, glide, octave, FINE 2, RING, env -> morph, release.  docs/PRUEBA_RH77.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh76  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH77"


def build(name=NAME, **kw):
    with rhbuild.options(va=3, vapage=True):
        return build_rh76.build(name, **kw)


if __name__ == "__main__":
    build().finish()
