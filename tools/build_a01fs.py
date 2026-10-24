"""Circuit Remix Alpha 0.01S + fix (MIT): Alpha 0.01S + tools/fixedrec.py, without rdiag (the marker A01FS: the 6-byte marker has no room
for A0.01FS)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_a001f  # noqa: E402

NAME = "A01FS"


def build(name=NAME):
    return build_a001f.build(name, nosd=True)


if __name__ == "__main__":
    build().finish()
