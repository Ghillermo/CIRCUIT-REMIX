"""Circuit Rhythm 5706 - RH70 (MIT): RH69 + tools/fm0.py (RD38's FM engine on core 0) + tools/fmpage.py, the FM played from the device, the
first part (the user, 2026-11-04: «Sample mode free pads» 11 VA / 12 FM / 13 VA-drum, «Hold the FM pad: pads 17-32», «Hacks' layout», the
colour 0x47): the values in RAM, the levels for one velocity; per-note velocity and the file per project next.  docs/PRUEBA_RH70.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh65  # noqa: E402
import fmpage  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH70"


def build(name=NAME, **kw):
    with rhbuild.options(rtdc=True, dspz=True, fm=True):
        b = build_rh65.build(name, bootok=True, **kw)
        b.add("fmpage", fmpage)
    return b


if __name__ == "__main__":
    build().finish()
