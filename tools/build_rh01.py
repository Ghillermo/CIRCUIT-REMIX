"""Circuit Rhythm 5706 - RH01 = RD1 + tools/rhstate.py (our RAM block at the top of the heap) + tools/rodisk.py (the pack of the internal
memory is read-only for the mod: every write / delete our code starts on pack 0 fails, with the Save LED red for 1.5 s).

The first feature of docs/PORTADO.md.  It keeps rdiag (the porting is still at the stage of reading the device), whose write command
(6) now goes through the guard like every later feature that writes.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rd1  # noqa: E402
import rhbuild  # noqa: E402
import rhstate  # noqa: E402
import rodisk  # noqa: E402

NAME = "RH01"


def build(name=NAME, diag=True, dsp=False, ram2=False):
    b = build_rd1.build(name, dsp=dsp) if diag else rhbuild.Build(name)   # diag=False: without rdiag (the public builds)
    b.add("rhstate", rhstate, **({"ram2": True} if ram2 else {}))      # ram2 (RH41+): the second RAM block
    b.add("rodisk", rodisk)
    return b


if __name__ == "__main__":
    build().finish()
