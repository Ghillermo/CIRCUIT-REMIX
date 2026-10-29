"""Circuit Rhythm 5706 - RH56 (MIT): RH55 + mefisme's count-in on the music's clock (pull request 7 of Ghillermo/CIRCUIT-REMIX, A0.04F;
the user, 2026-10-28: «check out current PR, make sure it's safe to include and merge with existing features»):
  * tools/vismet.py: with the click's level at 0, Clear flashes orange on each count-in click and each beat with the metronome on;
  * tools/clkci.py: the count-in timed by the clock (master: its 1 ms tick; slave: the incoming pulses, on the master's bar when known),
    Play's work during the count with the clock's start held until pulse 96, nothing recorded and the Play LED stopped meanwhile;
  * tools/stepload.py: Play's step load writes each word once (56 calls instead of 224, the same buffers and marks);
  * tools/errled.py: Clear blinks red while one of these features is off because the firmware is not as expected.
clkci's RAM is in latdiag's room of the second block (rhstate.SHARED: RH51-RH54 took A0.04F's offset 1820).  And linein srcdim (the user,
2026-10-29: «no fx into line in must remain dim»): the track menu's pad 15 with the inputs as the source, dim amber.  docs/PRUEBA_RH56.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh55  # noqa: E402
import clkci  # noqa: E402
import errled  # noqa: E402
import stepload  # noqa: E402
import vismet  # noqa: E402

NAME = "RH56"


def build(name=NAME, **kw):
    b = build_rh55.build(name, rh56=True, **kw)
    b.add("vismet", vismet)
    b.add("clkci", clkci)
    b.add("stepload", stepload)
    b.add("errled", errled)                       # last: it checks the features above
    return b


if __name__ == "__main__":
    build().finish()
