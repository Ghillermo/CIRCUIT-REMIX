"""Circuit Rhythm 5706 - RH67 (MIT): RH65 + autoinit bootok (the cold-boot fix of RD36) + tools/modhost.py: Arrhythmia's module host, ABI 3,
over SysEx (the user, 2026-11-03: «consider importing Arhytmia modules (the goal is to be able to develop modules that work on both fw)» ->
«SysEx host first»).  The host table at 0x0806A570 comes first in our code area, so every module of the build sits 32 bytes higher than in
RH65; rhstate takes a third RAM block (512 B at 0x2004EC60) for the host.  docs/PRUEBA_RH67.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh65  # noqa: E402
import modhost  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH67"


def build(name=NAME, **kw):
    with rhbuild.options(modhost=True):
        b = build_rh65.build(name, bootok=True, **kw)
        b.add("modhost", modhost)
    return b


if __name__ == "__main__":
    build().finish()
