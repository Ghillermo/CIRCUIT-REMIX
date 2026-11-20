"""Circuit Rhythm 5706 - RH99 (MIT): RH98 with the LED task's stack slimmed and our RAM checked at power-on (the user, 2026-11-14, from a survey
of CIRCUIT-HACKS' recent changes: its issue #22 and the morph's O_RR):
  * tools/ledslim.py (OPT ledslim): the LED task's 56 heads and Pattern Settings' slot 7 (4 heads) run one after the other by a dispatcher
    that keeps LR and the arguments in the ITCM, each with only its own registers on the stack (RH98: about 1 300-1 450 B nested before the
    stock's code ran, on the UI task's 2 KB stack); modmx's c_mxtick keeps its 64 targets in the ITCM too (128 B it took on that stack);
  * OPT raminit (the audit of the RAM our modules read before writing it, docs/PRUEBA_RH99.md): rhstate's first c_rst of a boot zeroes too
    the areas of ours outside its blocks that lived "from zero once" behind a magic (rpatch, latch, fm8page, esel, vsel) and the lanes'
    magic (xlanes): the SRAM keeps them across a reset or an install, so the boot before (or another build, or the bootloader) left their
    values; ledslim's dispatcher calls c_rst first once the stock is up, so that clear comes before any head reads them."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh98  # noqa: E402
import ledslim  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH99"


def build(name=NAME, **kw):
    with rhbuild.options(ledslim=True, raminit=True):
        b = build_rh98.build(name, **kw)
        b.add("ledslim", ledslim)
    return b


if __name__ == "__main__":
    build().finish()
