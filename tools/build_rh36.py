"""Circuit Rhythm 5706 - RH36 (MIT): RH35 with pitchmod shiboot: core 1's start clears bit 21 of X:$8 before it sets up its host port
(RH35 on the device: still out of step right after a cold start, the 200-frame wait made no difference; the cause is in the stock: X:$8,
the host's config word, is never loaded or cleared, and with bits 21 and 8 of its power-on value the first block turns core 1's port to
16-bit words while the ARM sends 24).  docs/PRUEBA_RH36.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh31  # noqa: E402
import fixedrec  # noqa: E402
import pitchmod  # noqa: E402
import stockplus  # noqa: E402

NAME = "RH36"


def build(name=NAME, **kw):
    b = build_rh31.build(name, dsp=2, **kw)
    b.add("pitchmod", pitchmod, load=True, fx=True, shift=0x300, filt=True, clear=True, lite=True, stretch=8, shiboot=True)
    b.add("stockplus", stockplus, shift=0x300, v2=True, k6swap=True, wait=True)
    b.add("fixedrec", fixedrec)
    return b


if __name__ == "__main__":
    build().finish()
