"""Circuit Rhythm 5706 - RH102 (MIT): RH101 + knob hold (CIRCUIT-HACKS' knobhold of SC56.7 / Beta 5.52, our own code for the Rhythm; the
user, 2026-11-14: «do your choices, we'll change the interface later if needed»; docs/PRUEBA_RH102.md lists the choices):
  * OPT knobhold (tools/knobhold.py): a turned knob keeps acting on what it acted on until it rests a second (view, mode, Shift, track, the
    container's mode, the Mixer / FX / Advanced / Sidechain pages, the Grid FX held slot, our pages); its LED kept meanwhile;
  * the switch on Setup pad 23 (settings p4 byte 1 = 0xC7), off at the factory: OPT setp4b1 (setsave saves it when stopped), OPT khsw
    (gmmode's c_gmled draws its LED through a stub);
  * OPT holeptr (tools/holes.py): no module at the start of a hole that a stock word names (noes' 0x080661DC, the mass storage class's
    vtable 0x08067730: ledslim refuses a head there)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh101  # noqa: E402
import knobhold  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH102"


def build(name=NAME, **kw):
    with rhbuild.options(knobhold=True, khsw=True, setp4b1=True, holeptr=True):
        b = build_rh101.build(name, **kw)
        b.add("knobhold", knobhold)
    return b


if __name__ == "__main__":
    build().finish()
