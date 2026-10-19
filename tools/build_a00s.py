"""Circuit Remix Alpha 0.0S (MIT): Alpha 0.0 without any function that creates, changes or deletes files on the card by itself (no project
copy, sesscopy) and without rdiag (no remote diagnostics): the chain of RH23 / RH24 / RH25 on RH20 instead of RH21 (the marker A0.0S)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh20  # noqa: E402
import kbright  # noqa: E402
import midithru  # noqa: E402
import pgmch  # noqa: E402

NAME = "A0.0S"


def build(name=NAME):
    b = build_rh20.build(name, bright=True, arp1=True, fxcols=True, diag=False)
    b.add("kbright", kbright)
    b.add("midithru", midithru)
    b.add("pgmch", pgmch)
    return b


if __name__ == "__main__":
    build().finish()
