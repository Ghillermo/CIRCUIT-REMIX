"""Circuit Rhythm 5706 - RH32 (MIT): RH31 + the Stock+ knob page (tools/stockplus.py: the selected track's button pressed again = its knobs
on the Stock+ page, K1-K4 pitch envelope amount / decay, LFO rate / depth; Shift = fine control; saved with the project) + pitchmod in DSP core 1
(tools/pitchmod.py, RD6's code without the counters)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh31  # noqa: E402
import pitchmod  # noqa: E402
import stockplus  # noqa: E402

NAME = "RH32"


def build(name=NAME, **kw):
    b = build_rh31.build(name, **kw)
    b.add("pitchmod", pitchmod)
    b.add("stockplus", stockplus)
    return b


if __name__ == "__main__":
    build().finish()
