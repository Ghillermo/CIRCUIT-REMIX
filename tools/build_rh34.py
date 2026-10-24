"""Circuit Rhythm 5706 - RH34 (MIT): RH33 with K6 / Shift + K6 swapped (K6 = pitch follow, Shift + K6 = the filter type: stock / 24 dB /
comb) and K6's LED in the filter type's colour (stockplus k6swap; the user, 2026-10-25, after RH33 on the device: «everything Ok, switch k6 and
s+k6, give each filter type different colors»).  The base of Circuit Remix Alpha 0.02.  docs/PRUEBA_RH33.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh31  # noqa: E402
import fixedrec  # noqa: E402
import pitchmod  # noqa: E402
import stockplus  # noqa: E402

NAME = "RH34"


def build(name=NAME, **kw):
    b = build_rh31.build(name, dsp=2, **kw)
    b.add("pitchmod", pitchmod, load=True, fx=True, shift=0x300, filt=True, clear=True, lite=True, stretch=8)
    b.add("stockplus", stockplus, shift=0x300, v2=True, k6swap=True)
    b.add("fixedrec", fixedrec)
    return b


if __name__ == "__main__":
    build().finish()
