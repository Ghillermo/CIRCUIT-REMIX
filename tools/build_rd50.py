"""Circuit Rhythm 5706 - RD50 (MIT, diagnostic): RD49 + the looper / live sampler (docs/DISENO_LOOPER.md; docs/PRUEBA_RD50.md): its engine on
core 0 (tools/looper0.py, called from drybus's DRY2: after the Grid FX, before the compressor; 4 stereo buffers in the SDRAM above the
samples' list) and its controls in the Grid FX view (tools/looper.py: pads 9 / 10 record the line input / resample the mix, pads 11-14 the
four loops, Shift + K8 the bars)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rd49  # noqa: E402
import rhbuild  # noqa: E402
import looper  # noqa: E402

NAME = "RD50"


def build(name=NAME, **kw):
    with rhbuild.options(looper=True, xclr=True, fxbright=True, fxhold=True):                # (xclr: RD49's synth tables kept through the stock's start-up clear; fxbright: the FX track's slots like the keyboard)
        b = build_rd49.build(name, **kw)
        b.add("looper", looper)
    return b


if __name__ == "__main__":
    build().finish()
