"""Circuit Rhythm 5706 - RH91 (MIT): RH90 with the optimizations that change nothing the device does (docs/PRUEBA_RH91.md):
  * tabpack2: fm8page's tables, envpage's curves, rpatch's tables and the byte parts of the earlier regions in tabpack's stream (LZSS for bytes,
    second differences for curves), unpacked into the ITCM at the core 0 upload (fm8page's before it, as in RH86-RH90);
  * mfsess out (the master resonance stays global on the device: RH28 / RH30);
  * modmx's high bits' cache with one look-up of the record a frame (c_mxhrf: 26 before)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh90  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH91"


def build(name=NAME, **kw):
    with rhbuild.options(tabpack2=True, nomfsess=True, mxhrf1=True):
        b = build_rh90.build(name, **kw)
    return b


if __name__ == "__main__":
    build().finish()
