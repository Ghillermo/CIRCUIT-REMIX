"""Circuit Remix Alpha 0.0 (MIT): RH25 without rdiag (no remote diagnostics: no memory reads or card writes over SysEx), under its public name (the marker A0.0): every function of RH12-RH25 on top of RH01-RH11."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh25  # noqa: E402

NAME = "A0.0"


def build(name=NAME):
    return build_rh25.build(name, diag=False)


if __name__ == "__main__":
    build().finish()
