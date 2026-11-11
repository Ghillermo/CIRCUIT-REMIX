"""Circuit Rhythm 5706 - RH81 (MIT): RH80 + docs/DISENO_RH81.md (the user, 2026-11-07: «Construye»): CIRCUIT-HACKS' engine colours for the
engines and their views (tools/hackcol.py), the play mode gated when a track becomes a synth, reverse / choke on the synths, the FM's
operators in the track menu, the pack's patches for every engine in Sample mode (tools/rpatch.py; the Samples view and the patch flip: not
in RH81, no room).
docs/PRUEBA_RH81.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh80  # noqa: E402
import hackcol  # noqa: E402
import rpatch  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH81"


def build(name=NAME, **kw):
    with rhbuild.options(rh81=True), hackcol.applied():
        b = build_rh80.build(name, **kw)
        if not kw.get("nosd") or not rhbuild.OPT.get("nopatch"):          # (A0.13S, OPT nopatch) without the pack's patches (they need projsnd)
            b.add("rpatch", rpatch)
    return b


if __name__ == "__main__":
    build().finish()
