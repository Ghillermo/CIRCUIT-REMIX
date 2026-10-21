"""Circuit Rhythm 5706 - RH30 = RH29 with the fixes of the RH28 device test (MIT; the user, 2026-10-20, «arregla los fallos del informe»):
  * fxkeys viewset: Duplicate (the reset) in the FX view also writes the sends' view stores, so the knob LEDs follow («works, leds dont update»);
  * clrknob viewset: Clear + an FX knob the same; clrknob single: Clear + a Sidechain knob resets that knob only («knobs should clear
    individually»);
  * mfsess track: the resonance's block follows every change, so the project keeps it whatever save path the stock takes («resonance stays»);
  * drumpat rowfix: the dynamics row stays on the LEDs after the stock's repaint of row 3 («dynamics apply, but they are not being displayed»);
  * cthresh: the master compressor's threshold on K5 of the Sidechain view («add threshold»): the DSP's gain table rewritten from the ARM.
The count-in's tempo («pre count is fixed») is RH29's bpm0."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh29  # noqa: E402
import cthresh  # noqa: E402

NAME = "RH30"


def build(name=NAME, **kw):
    b = build_rh29.build(name, rh30=True, **kw)
    b.add("cthresh", cthresh)
    return b


if __name__ == "__main__":
    build().finish()
