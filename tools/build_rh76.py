"""Circuit Rhythm 5706 - RH76 (MIT): RH75 + the 8-operator FM played from the device: tools/fm8c0.py on core 0 (RD40's engine) and
tools/fm8page.py (the FM page on Sample mode's pad 12, CIRCUIT-HACKS' panel), fmpage without the 4-operator FM (OPT fm8page); the first phase of
docs/DISENO_FM8.md (the user, 2026-11-05: «Start RH76»).  docs/PRUEBA_RH76.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh75  # noqa: E402
import fm8page  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH76"


def build(name=NAME, **kw):
    with rhbuild.options(fm8=True, fm8page=True):
        b = build_rh75.build(name, **kw)
        b.add("fm8page", fm8page)
    return b


if __name__ == "__main__":
    build().finish()
