"""Circuit Rhythm 5706 - RH95 (MIT): RH94 with the room for the automation lanes (docs/DISENO_RH95.md; the user, 2026-11-13: «Try to free the
maximum amount of RAM ... make sure we're using the heap up to the hardware capacity»): the DSP blocks range-coded (tools/dspz.py OPT dzrc:
CIRCUIT-HACKS' SC56 coder), and in the flash that frees (the end of the stock core 1 block's place) the tables tabpack kept in the ITCM
(tools/tabpack.py OPT tabflash: read where they are): the ITCM keeps only its data (modmx's offsets, pclr's photos, rpatch's pointers).
Nothing changes in use."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh94  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH95"


def build(name=NAME, **kw):
    with rhbuild.options(dzrc=True, tabflash=True):
        return build_rh94.build(name, **kw)


if __name__ == "__main__":
    build().finish()
