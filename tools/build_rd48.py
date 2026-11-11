"""Circuit Rhythm 5706 - RD48 (MIT, diagnostic): RD47 + esel's, vsel's and synthpage's lookup tables in the ITCM's low room 0x100-0x3FF
(tabpack OPT lowtab: early records, unpacked before core 0's block; outside dspz's window, never written by the stock).  Nothing changes on
the device but the flash (docs/PRUEBA_RD47.md covers both)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rd47  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RD48"


def build(name=NAME, **kw):
    with rhbuild.options(lowtab=True):
        b = build_rd47.build(name, **kw)
    return b


if __name__ == "__main__":
    build().finish()
