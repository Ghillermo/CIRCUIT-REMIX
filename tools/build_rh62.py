"""Circuit Rhythm 5706 - RH62 (MIT): RH61 with flash freed and trkcopy's knobs fixed (the user, 2026-11-01: «continúa, añade esas cosas»):
  * thumb.COMPACT, CIRCUIT-HACKS' literal pools: a movw + movt pair = one LDR from a shared word;
  * cthresh thgen: the compressor's 15 gain tables worked out when applied (288 B, not 7 740 B; within 0.005 dB);
  * trim: the code that later options leave unreachable (granpage multi, clrknob's loops);
  * trkcopy trkrouter: K1-K8 through the parameter router, so the destination's knob view is up to date.
Nothing changes in use but trkcopy's view.  docs/PRUEBA_RH62.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh61  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH62"


def build(name=NAME, **kw):
    with rhbuild.options(compact=True, thgen=True, trkrouter=True, trim=True):
        return build_rh61.build(name, **kw)


if __name__ == "__main__":
    build().finish()
