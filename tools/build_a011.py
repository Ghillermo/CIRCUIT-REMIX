"""Circuit Remix Alpha 0.11 (MIT): RH67 without rdiag (no remote diagnostics: no memory reads or card writes over SysEx), under its public name
(the marker A0.11): Alpha 0.10 plus the module host of tools/modhost.py (Arrhythmia's modules, ABI 3, uploaded over USB SysEx; the same .mod
files run on both firmwares).  Experimental."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh67  # noqa: E402

NAME = "A0.11"


def build(name=NAME, **kw):
    return build_rh67.build(name, diag=False, **kw)


if __name__ == "__main__":
    build().finish()
