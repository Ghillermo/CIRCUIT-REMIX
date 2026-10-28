"""Circuit Rhythm 5706 - RH18 = RH17 with the open points fixed (MIT):
  * countin v2: Shift + Play from stopped (the stock's «play from where it stopped») with the count-in on keeps its Shift through the count;
  * dqfix: drumpat's step bytes follow the stock's step paste (Duplicate + step A + step B) and Mutate (Shift + Duplicate).
The chain is built again from RD1 (countin is early in it), with every module of RH17."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh01  # noqa: E402
import clrtrk  # noqa: E402
import countin  # noqa: E402
import cscale  # noqa: E402
import dqfix  # noqa: E402
import drumarp  # noqa: E402
import drumpat  # noqa: E402
import fxkeys  # noqa: E402
import mixshift  # noqa: E402
import patchain  # noqa: E402
import playmode  # noqa: E402
import porder  # noqa: E402
import qmute  # noqa: E402
import quant  # noqa: E402
import rhrec  # noqa: E402
import sckn  # noqa: E402
import trkcopy  # noqa: E402

NAME = "RH18"


def build(name=NAME, arp_rec=False, bright=False, arp1=False, fxcols=False, diag=True, dsp=False, scniter=False, bpm0=False, rh30=False, rh31=False, ram2=False, ui=False, tcram=False):
    b = build_rh01.build(name, diag=diag, dsp=dsp, ram2=ram2)
    b.add("countin", countin, v2=True, **({"bpm0": True} if bpm0 else {}))
    b.add("quant", quant, v2=True)
    b.add("qmute", qmute)
    b.add("mixshift", mixshift)
    b.add("clrtrk", clrtrk)
    b.add("playmode", playmode, v2=True)
    b.add("porder", porder)
    b.add("rhrec", rhrec)
    b.add("drumpat", drumpat, v2=True, **({"rowfix": True} if rh30 else {}), **({"recdyn": True} if rh31 else {}))
    b.add("patchain", patchain, **({"iterled": True} if scniter else {}))
    b.add("sckn", sckn, **({"bright": True} if bright else {}))
    b.add("fxkeys", fxkeys, **({"bright": True} if bright else {}), **({"cols": True} if fxcols else {}), **({"viewset": True} if rh30 else {}))
    b.add("drumarp", drumarp, notes=True, **({"rec": True} if arp_rec else {}), **({"single": True} if arp1 else {}), **({"bpm0": True} if bpm0 else {}),
          **({"ui": True} if ui else {}))
    b.add("cscale", cscale)
    b.add("trkcopy", trkcopy, **({"ram": True} if tcram else {}))   # (RH54: the photos in RAM)
    b.add("dqfix", dqfix)
    return b


if __name__ == "__main__":
    build().finish()
