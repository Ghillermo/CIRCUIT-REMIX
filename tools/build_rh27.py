"""Circuit Rhythm 5706 - RH27 = RH26 + smpcopy (MIT): in the Sample Rec view, Duplicate + slot A = the source, Duplicate + slot B = A's sample
copied into B (this pack or another one; an occupied B asks first) and loaded into the DSP at once; part of «gestión del pack»."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh26  # noqa: E402
import smpcopy  # noqa: E402

NAME = "RH27"


def build(name=NAME, **kw):
    b = build_rh26.build(name, **kw)
    if not kw.get("nosd"):                             # (Alpha 0.01S) no sample copy
        b.add("smpcopy", smpcopy)
    return b


if __name__ == "__main__":
    build().finish()
