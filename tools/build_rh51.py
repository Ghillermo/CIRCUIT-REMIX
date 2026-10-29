"""Circuit Rhythm 5706 - RH51 (MIT): RH50 + the synth (tools/synth0.py on DSP core 0, RD31's engine) with its page on the device
(tools/synthpage.py: the track menu's pad 8, the Synth page's knobs, saved with the project, the note-off of a one-shot synth track) (the
user, 2026-10-27: «Start the synth: RD31 first (...), then RH51»).  docs/PRUEBA_RH51.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh50  # noqa: E402
import synthpage  # noqa: E402

NAME = "RH51"


def build(name=NAME, **kw):
    b = build_rh50.build(name, synth=True, **kw)
    b.add("synthpage", synthpage, **({"ui": True} if kw.get("ui") else {}), **({"menu2": True} if kw.get("menu2") else {}),
          **({"env": True} if kw.get("rh54") else {}), **({"spall": True} if kw.get("rh55") else {}),
          **({"noblink": True} if kw.get("rh58") else {}))
    return b


if __name__ == "__main__":
    build().finish()
