"""Circuit Rhythm 5706 - RH59 (MIT): RH58 + the rest of CIRCUIT-HACKS' automation that fits (the user, 2026-10-29: «review the last automation
changes on hacks and implement what's left»; chosen: «Record + step cue, Latched automation view», «Only what fits»):
  * autoinit cue (SC49.6): the track view, Record held + a step = its pad yellow until let go;
  * autoinit latch (SC49.5): Velocity again in the Velocity view (no Shift) = the automation view latched (as with Shift held: yellow steps
    and their preview, red marks, a tap = mark); again = off, leaving the view = off.
Not ported (no room in flash): the extra lane per drum and the state locks / ramps.  docs/PRUEBA_RH59.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh58  # noqa: E402

NAME = "RH59"


def build(name=NAME, **kw):
    return build_rh58.build(name, ai=dict(cue=True, latch=True), **kw)


if __name__ == "__main__":
    build().finish()
