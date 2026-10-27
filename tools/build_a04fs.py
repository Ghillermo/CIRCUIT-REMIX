"""Circuit Remix A04FS (MIT): Alpha 0.04S (no functions that create, change or delete files on the card by themselves, no rdiag) + the
features of tools/build_a004f.py, none of which writes to the card.  The 6-byte marker has no room for A0.04FS."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_a004f  # noqa: E402

NAME = "A04FS"


def build(name=NAME):
    return build_a004f.build(name, diag=False, nosd=True)


if __name__ == "__main__":
    build().finish()
