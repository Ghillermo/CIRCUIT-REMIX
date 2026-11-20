"""Circuit Rhythm 5706 - RH98 (MIT): RH97 with the automation of the synth pages fixed (the user, 2026-11-13: «Va synth dont get
automation», «mod matrix knobs change asignation instead of value when recorded»):
  * modmx OPT mxslot: the matrix's destinations 16-31 of a synth track found its slot by the track (RH64-RH97 asked c_syslot for the slot of
    the track numbered as c_sysnd's sound code: a VA knob recorded into a lane of a sample track's destination, and nothing played back);
  * vsel OPT mxfix: the matrix's Matrix / Sequenceable / Non-sequenceable views on top of a VA's OSC pages take the knobs and LEDs (vsel took
    them as OSC 1's); what vsel moves itself is recorded into its lane (OSC 1's extras, the Envelope's K1-K4, the level, the synth values it
    shows without Shift);
  * xlanes OPT lngap: the lanes' save fills the patch bank's gap up to the end of projsnd's records first (its write far past the end left
    the patches and the other projects' records over whatever the card held)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh97  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH98"


def build(name=NAME, **kw):
    with rhbuild.options(mxslot=True, mxfix=True, lngap=True):
        return build_rh97.build(name, **kw)


if __name__ == "__main__":
    build().finish()
