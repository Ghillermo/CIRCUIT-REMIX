"""Circuit Rhythm 5706 - FRD1 (test): stock + tools/fixedrec.py (Fixed Recording at the external clock's tempo) + tools/rdiag.py
(remote diagnostics over USB SysEx, read-only use), to test the fix on the device and read its RAM if it does not work.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rhbuild  # noqa: E402
import fixedrec  # noqa: E402
import rdiag  # noqa: E402

NAME = "FRD1"


def build(name=NAME):
    b = rhbuild.Build(name)
    b.add("fixedrec", fixedrec)
    b.add("rdiag", rdiag)
    return b


if __name__ == "__main__":
    build().finish()
