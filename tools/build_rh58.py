"""Circuit Rhythm 5706 - RH58 (MIT): RH57 + (the user, 2026-10-29, «both in a single build»):
  * the page modules without their blink (noblink: «get rid of the unnecesary flashing»; it also lit LED 40 + t, the Samples button);
  * tools/smodes.py: the track's modes on Sample mode's free pads (sound 5-8, link 14, line in's source / gate 15 / 16), the track menu keeps
    the pages («put all modes in the free pads from Sample mode view, keep pages on track's double tap/hold view»);
  * tools/fxroute.py: an FX return taken by a line track leaves the master; that track's send back into the same FX halved («when an fx is
    routed to an input, it shouldnt be routed to master anymore. also limit feedback (but not crossfeed) as we did on Hacks»);
  * tools/autoinit.py + autorel init: the automation of CIRCUIT-HACKS (docs/export/REMIX_AUTOMATION.md): Velocity + Shift yellow steps with
    knob automation and their preview, Clear + step = its knob automation erased, a marked step = Project init (as loaded / saved), the
    track menu's pad 8 (red) = the voice back to Project init, the snapshot (Record held + a step).
docs/PRUEBA_RH58.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh57  # noqa: E402
import autoinit  # noqa: E402
import fxroute  # noqa: E402
import smodes  # noqa: E402

NAME = "RH58"


def build(name=NAME, ai=None, **kw):
    b = build_rh57.build(name, rh58=True, **kw)
    b.add("smodes", smodes)
    b.add("fxroute", fxroute)
    b.add("autoinit", autoinit, **(ai or {}))
    return b


if __name__ == "__main__":
    build().finish()
