"""Circuit Rhythm 5706 - RH83 (MIT): RH82 + demo patches (tools/rpatch.py OPT demos; the user, 2026-11-07: «Escoge algunos presets demo y
úsalos como presets por defecto hasta que el usuario los escriba»): the first page of the pack's patch list holds 8 VA, 8 FM (fm8inst's
instruments) and 8 granular demos in its empty slots until something is saved there.  docs/PRUEBA_RH83.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh82  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH83"


def build(name=NAME, **kw):
    with rhbuild.options(demos=True):
        b = build_rh82.build(name, **kw)
    return b


if __name__ == "__main__":
    build().finish()
