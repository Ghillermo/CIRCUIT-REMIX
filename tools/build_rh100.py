"""Circuit Rhythm 5706 - RH100 (MIT): RH99 with three FM things from CIRCUIT-HACKS (the user, 2026-11-14, from a survey of its recent changes:
SC56.3 / Beta 5.48's FM map and custom algorithm, SC52.6 / Beta 5.29's violet reciprocal of the FM knob):
  * fm8page OPT fmmap (tools/fmmap.py): on the FM page pad 7 tapped = the algorithm map pinned, held 1/2 s = the map while held, Shift + pad 7
    = the 56 algorithms (RH76-RH99's pad 7 held); the map on pads 9-32 (paths leaf -> carrier, the ratio's class as colour, the picked one
    pulsing), a tap picks, Shift + operator mutes while the map shows, one held + another = a link on / off = the custom algorithm (index 56
    in the parameters' spare bytes, as Hacks: saved with the patch and the project); pad 24 closes the page (no more a tap on pad 7); vsel OPT
    fmmap: a page picked in the track menu closes it too;
  * synthpage / vsel / modmx OPT fmviolet: the VA's FM knob (OSC 2 K5, the Synth page's K6, the matrix): up to +-32 from the centre the
    page's colour (dark at the centre, the left lighter), past it the reciprocal stretch towards 50 / 50 in lilac (docs/INTERFAZ.md)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh99  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH100"


def build(name=NAME, **kw):
    with rhbuild.options(fmmap=True, fmviolet=True):
        return build_rh99.build(name, **kw)


if __name__ == "__main__":
    build().finish()
