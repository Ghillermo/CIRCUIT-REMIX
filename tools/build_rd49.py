"""Circuit Rhythm 5706 - RD49 (MIT, diagnostic): RD48 + room in core 0's program memory: synth0's four tables (INCT, ENVT, F2, Q2: 530
words) in core 0's X (synth0 OPT xtab; core0's loader writes X segments, told by bit 14 of their address) + the dry bus for the FX
sequencer's per-track sends (docs/DISENO_RH92.md; docs/PRUEBA_RD49.md) + fwid (the firmware identity query of the apps)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rd48  # noqa: E402
import rhbuild  # noqa: E402
import fwid  # noqa: E402

NAME = "RD49"


def build(name=NAME, **kw):
    with rhbuild.options(xtab=True, drybus=True, sends=True):
        b = build_rd48.build(name, **kw)
    b.add("fwid", fwid)                                          # the firmware identity query (the apps; CIRCUIT-HACKS' SC56.2 bytes)
    return b


if __name__ == "__main__":
    build().finish()
