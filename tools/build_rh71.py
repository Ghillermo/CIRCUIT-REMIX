"""Circuit Rhythm 5706 - RH71 (MIT): RH70 with the FM starters retuned for a mono voice (fmvoice.STARTERS2, OPT fmst2; the user, 2026-11-04:
«patches need to be more percusive and pad, more full, since they aren't polyphonic» -> «Now, for mono»).  docs/PRUEBA_RH71.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh70  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH71"


def build(name=NAME, **kw):
    with rhbuild.options(fmst2=True):
        return build_rh70.build(name, **kw)


if __name__ == "__main__":
    build().finish()
