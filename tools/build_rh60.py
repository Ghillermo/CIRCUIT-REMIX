"""Circuit Rhythm 5706 - RH60 (MIT): RH59 + (the user, 2026-10-29):
  * tools/dqchain.py: drumpat's frequency counted per pattern, also in a chain, and the stock's sample load skipped off its pass («each n
    steps plays anyway and makes notes shorter in the iterations when its not suppossed to play»);
  * tools/trigflash.py: with Shift held, the track buttons flash white when their track triggers («add a white flash cue on track pads for
    each track when they trigger (only visible when pressing shift)»);
  * fxroute more: an input track's send into its own FX at three quarters, not a half («allow a bit more feedback»);
  * autoinit allpages: the track menu's pad 8 also puts Stock+, the granular / synth page and the Envelope page back to their defaults
    («pad 8 on track pages clears all pages back to default (not just stock)»).
docs/PRUEBA_RH60.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh58  # noqa: E402
import dqchain  # noqa: E402
import trigflash  # noqa: E402

NAME = "RH60"


def build(name=NAME, dc=None, bootok=False, **kw):
    """bootok (A0.10): autoinit's photo at a save only once the controller is built (the cold-boot loop, RD34 / RD36)"""
    b = build_rh58.build(name, ai=dict(cue=True, latch=True, allpages=True, **({"bootok": True} if bootok else {})), fr=dict(more=True), **kw)
    b.add("dqchain", dqchain, **(dc or {}))
    b.add("trigflash", trigflash)
    return b


if __name__ == "__main__":
    build().finish()
