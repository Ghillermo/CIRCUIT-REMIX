"""Circuit Rhythm 5706 - RH40 (MIT): RH39 with the played note pitching the granular (the user, 2026-10-26, on RH39: «pitch on granular
does nothing … Pitch needs to both speed up the grain and the repetition cycles»): the DSP note-on's trigger (0x08040778 -> bl 0x080406A8)
also sends the granular track's note to core 0 (granpage note), and the engine (granular0 note) scales the grains as a sampler: r =
2^((note - 60) / 12), each grain's increment x r, its length and the spawn interval / r.  docs/PRUEBA_RH40.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh31  # noqa: E402
import fixedrec  # noqa: E402
import granpage  # noqa: E402
import granular0  # noqa: E402
import pitchmod  # noqa: E402
import stockplus  # noqa: E402

NAME = "RH40"


def build(name=NAME, g0extra=None, pm=None, g0post=None, sp=None, gp=None, g0=None, **kw):
    """g0extra (RD24): more core 0 segments after granular0's (its `extra`); pm (RD26): more pitchmod options; g0post (RD30): GR's end
    jumps there (granular0 post); sp (RH44): more stockplus options; gp (RH45): more granpage options"""
    b = build_rh31.build(name, dsp=2, **kw)
    b.add("pitchmod", pitchmod, load=True, fx=True, shift=0x300, filt=True, clear=True, lite=True, stretch=9, shiboot=True,
          duck=True, landing=True, loopscan=True, loopxf=4, **(pm or {}))
    b.add("stockplus", stockplus, shift=0x300, v2=True, k6swap=True, wait=True, k8sync=True, **(sp or {}))
    b.add("fixedrec", fixedrec)
    b.add("granular0", granular0, counter=False, note=True, **({"extra": g0extra} if g0extra else {}), **({"post": g0post} if g0post else {}),
          **(g0 or {}))
    b.add("granpage", granpage, note=True, **(gp or {}))
    return b


if __name__ == "__main__":
    build().finish()
