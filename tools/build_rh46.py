"""Circuit Rhythm 5706 - RH46 (MIT): RH45 + tools/stepgate.py (the user, 2026-10-26: «Falta portar fixed length y user input length de Tracks
en la vista microstep»): Micro Step pad 31 = a fixed length for the steps entered by hand (its selector on pads 17-32), pad 32 = their gate
= the time the step pad was held.  docs/PRUEBA_RH46.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh45  # noqa: E402
import arpext  # noqa: E402
import autorel  # noqa: E402
import dqclear  # noqa: E402
import gmmode  # noqa: E402
import qfull  # noqa: E402
import setsave  # noqa: E402
import stepgate  # noqa: E402
import usbmerge  # noqa: E402

NAME = "RH46"


def build(name=NAME, **kw):
    ui = {"ui": True} if kw.get("ui") else {}                         # (RH52: docs/INTERFAZ.md)
    b = build_rh45.build(name, sp={"fitflag": True, "k3sync": True}, **kw)
    b.add("stepgate", stepgate, **ui)
    b.add("dqclear", dqclear)
    b.add("setsave", setsave)
    b.add("usbmerge", usbmerge, **ui)
    b.add("arpext", arpext, **ui)
    b.add("gmmode", gmmode, **ui)
    b.add("qfull", qfull)
    b.add("autorel", autorel, **ui, **({"keep": True} if kw.get("menu2") else {}))   # (RH53: menu2 builds keep the stock's colours)
    return b


if __name__ == "__main__":
    build().finish()
