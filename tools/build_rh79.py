"""Circuit Rhythm 5706 - RH79 (MIT): RH78 + tools/projsnd.py: each project's synth sounds on the card, in its pack's patch bank (the 8-operator
FM's 216 parameters of each slot now travel with the project; room for the VA's own values of RH80) (the user, 2026-11-06: «Card storage
first»).  docs/PRUEBA_RH79.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh78  # noqa: E402
import projsnd  # noqa: E402

NAME = "RH79"


def build(name=NAME, **kw):
    b = build_rh78.build(name, **kw)
    if not kw.get("nosd"):                                              # (the S alphas: nothing of ours writes to the card)
        b.add("projsnd", projsnd)
    return b


if __name__ == "__main__":
    build().finish()
