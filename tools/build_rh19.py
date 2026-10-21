"""Circuit Rhythm 5706 - RH19 = RH18 + clrknob (MIT): Clear + knob = back to the default in the FX view (the send to 0) and the Sidechain view
(K1-K4 the track's preset values, K6-K8 the compressor's factory values)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh18  # noqa: E402
import clrknob  # noqa: E402

NAME = "RH19"


def build(name=NAME, arp_rec=False, **kw):
    b = build_rh18.build(name, arp_rec, **kw)
    b.add("clrknob", clrknob, **({"single": True, "viewset": True} if kw.get("rh30") else {}))
    return b


if __name__ == "__main__":
    build().finish()
