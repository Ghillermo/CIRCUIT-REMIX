"""Circuit Rhythm 5706 - RH64 (MIT): RH63 + tools/modmx.py (the user, 2026-11-01): the modulation matrix on every track, the sequenceable and the
non-sequenceable controls (the track menu's pads 6, 7, 16), lanes that take their destination as they are recorded.  docs/PRUEBA_RH64.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh63  # noqa: E402
import modmx  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH64"


def build(name=NAME, **kw):
    with rhbuild.options(compact=True, mxsink=True, mxlane=True):
        b = build_rh63.build(name, **kw)
        b.add("modmx", modmx)
    return b


if __name__ == "__main__":
    build().finish()
