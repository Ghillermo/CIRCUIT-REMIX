"""Circuit Rhythm 5706 - RH96 (MIT): RH95 + the extra automation lanes (tools/xlanes.py; docs/DISENO_RH95.md; the user, 2026-11-13: «Per
step, shared pool. Apply interpolation during sweeps»): when a knob being recorded finds no stock lane and the matrix's extra lane is
another destination's, it takes a 6-bit lane (one value a step) from a pool of the RAM nobody uses (the ITCM, above the heap's limit, the
backup SRAM while the USB mass storage is off, the bottom of the task stacks); between two steps with a value the destination moves in a
straight line; saved with the project in its pack's patch bank."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh95  # noqa: E402
import rhbuild  # noqa: E402
import xlanes  # noqa: E402

NAME = "RH96"


def build(name=NAME, **kw):
    b = build_rh95.build(name, **kw)
    if not kw.get("nosd"):                                         # (Alpha 0.16S) the lanes are saved in the pack's patch bank: not with nosd
        b.add("xlanes", xlanes)
    return b


if __name__ == "__main__":
    build().finish()
