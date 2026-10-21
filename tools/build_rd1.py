"""Circuit Rhythm 5706 - RD1 (diagnostic): stock + tools/rdiag.py (remote diagnostics over USB SysEx, read-only use).

The first build for the device: it changes 4 stock bytes (the SysEx dispatcher's prologue) and the version marker, and lets
tools/rhremote.py read the RAM and the flash.  The RAM dump it gives is what the emulation tests of every later build start from
(the CIRCUIT-HACKS method: a live RAM dump of the device + Unicorn).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rhbuild  # noqa: E402
import rdiag  # noqa: E402

NAME = "RD1"


def build(name=NAME, dsp=False):
    b = rhbuild.Build(name)
    b.add("rdiag", rdiag, **({"dsp": dsp} if dsp else {}))
    return b


if __name__ == "__main__":
    build().finish()
