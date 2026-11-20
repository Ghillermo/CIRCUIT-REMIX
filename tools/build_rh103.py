"""Circuit Rhythm 5706 - RH103 (MIT): RH102 + the fixes of the bug hunt of 2026-11-14 (the user, 2026-11-19: «both. keep porting Hacks fixes
and features»; docs/PRUEBA_RH103.md):
  * OPT nolsave (projsnd, xlanes): 0x08038734 is the stock's project LOAD (0x08047270 = op 6, a read), not a save: a load or a pack change wrote
    the project being left (its synths, FM, VA extras, lanes) into the bank records of the one being loaded (RH79+ / RH96+, A0.12-A0.15);
  * OPT limpy (linein): the gate gain `mpy y1,x0` (no such pair: dsptool made it mpysu) -> `mpy x0,y1`: a closed gate played at about 2x;
  * OPT dsplint (granular0, looper0, synth0): the other `mpy / mac x0,y0` (no such pair) as `y0,x0`: the same product with their positive
    operands, no mpysu / macsu left in core 0;
  * OPT lnnew (xlanes): a new project (the stock's «new session» call in the load) does not read the slot's old lanes record;
  * OPT lprel (looper): a pad release the looper did not take goes on down the chain also in Grid FX;
  * OPT gmoff (gmmode): a GM knob's pending note-off goes out in any view, not only in Setup;
  * OPT srdark (granpage): Sample Rec pads 23 / 24 drawn only where the stock left them dark (its record region's bar);
  * OPT vtfix (qmute, sesscopy): the two vtable checks that always answered 1 (a movs between the cmp and its branch);
  * OPT lnnostk (xlanes): no lanes in the tasks' stacks (92 at most; past that they were played or saved with stack frames in them)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh102  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH103"
FIXES = dict(nolsave=True, limpy=True, dsplint=True, lnnew=True, lprel=True, gmoff=True, srdark=True, vtfix=True, lnnostk=True)


def build(name=NAME, **kw):
    with rhbuild.options(**FIXES):
        return build_rh102.build(name, **kw)


if __name__ == "__main__":
    build().finish()
