"""Circuit Rhythm 5706 - RH53 (MIT): RH52 with the track menu as the user asked after trying RH52 (2026-10-28: «Tap the track button»,
«granular page is still selectable on synth mode (shouldnt)»): granpage / synthpage menu2:
  * a tap on the selected track's button opens the menu and leaves it open until a menu pad is let go, the button is pressed again, another
    track's button is pressed or the track views are left; held = the menu while held, as in RH52;
  * the page pads only offer the track's own sound's pages (a sample: stock, Stock+; granular: stock, Granular; synth: stock, Synth; the
    line input: stock), the others dark and doing nothing; the sound changes only with pads 11-13 (switched on: its page; off: stock).
docs/PRUEBA_RH53.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh52  # noqa: E402

NAME = "RH53"


def build(name=NAME, **kw):
    return build_rh52.build(name, menu2=True, **kw)


if __name__ == "__main__":
    build().finish()
