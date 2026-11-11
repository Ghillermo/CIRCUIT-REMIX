"""Circuit Rhythm 5706 - RD47 (MIT, diagnostic): RH92 with the other three DSP programs packed in place (core 0 mode 1, core 1 modes 0 and
1; core0 OPT dzmore): c_dzs unpacks a packed block as the stock sends one, their freed tails take core 0's packed stream, our late ITCM
tables are unpacked after core 1's block (tabpack late1).  Nothing changes on the device but the flash (docs/PRUEBA_RD47.md)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh92  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RD47"


def build(name=NAME, **kw):
    with rhbuild.options(dzmore=True):
        b = build_rh92.build(name, **kw)
    return b


if __name__ == "__main__":
    build().finish()
