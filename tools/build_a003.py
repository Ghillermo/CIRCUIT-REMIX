"""Circuit Remix Alpha 0.03 (MIT): RH36 without rdiag (no remote diagnostics: no memory reads or card writes over SysEx), under its public name
(the marker A0.03): Alpha 0.02's functions with the Stock+ page working right after a cold start (core 1's host port set up at 24-bit words
whatever X:$8 holds at power-up: pitchmod shiboot; in A0.01 / A0.02 the page could do nothing for minutes after switching on)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh36  # noqa: E402

NAME = "A0.03"


def build(name=NAME, **kw):
    return build_rh36.build(name, diag=False, **kw)


if __name__ == "__main__":
    build().finish()
