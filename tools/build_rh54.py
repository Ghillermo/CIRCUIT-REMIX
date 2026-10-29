"""Circuit Rhythm 5706 - RH54 (MIT): RH53 + the envelope by the play mode for the synth and the granular, on a new Envelope page (the track
menu's pad 5) + the line input from the reverb's or the delay's return (pad 15) with the track's filter on a gated line track (the user,
2026-10-28: «Start RH54: the envelope for synth and granular, and the line-in modes from the FX returns with the gated VCA/VCF mode»):
synth0 env2, granchain env, linein fx (core 0's P:$5C0 hook FXH), granpage / synthpage env, tools/envpage.py; trkcopy's photo in RAM
(its 212 B of the project's tail for the envelope's block).  docs/PRUEBA_RH54.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh53  # noqa: E402
import envpage  # noqa: E402

NAME = "RH54"


def build(name=NAME, **kw):
    b = build_rh53.build(name, rh54=True, **kw)
    b.add("envpage", envpage, **({"noblink": True} if kw.get("rh58") else {}))
    return b


if __name__ == "__main__":
    build().finish()
