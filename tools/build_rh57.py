"""Circuit Rhythm 5706 - RH57 (MIT): RH56 + the stereo link's second track as offsets from the first (tools/slinkofs.py; the user, 2026-10-29:
«second track's view retain knob destinations and store deviations: they become bipolar and they affect how much the parameters add or
subtract from the first.  Pad selection by default is still left index+1, but can now be changed by selecting a different pad»):
  * the follower's K1-K8 = offsets (bipolar, the centre = none) added to the leader's; Clear + knob = the centre; its knob LEDs steel blue
    from the centre;
  * the follower's sample = the leader's + the gap between their selections (default + 1, a pad picked on it changes it; the leader's
    selection moved = the follower's follows);
  * linking centres the follower's knobs, unlinking bakes them (its sound does not jump);
  * the follower plays the leader's notes and its own steps («right channel sequencer works too. So right channel plays everything on left
    plus their own»).  docs/PRUEBA_RH57.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh56  # noqa: E402
import slinkofs  # noqa: E402

NAME = "RH57"


def build(name=NAME, **kw):
    b = build_rh56.build(name, **kw)
    b.add("slinkofs", slinkofs)
    return b


if __name__ == "__main__":
    build().finish()
