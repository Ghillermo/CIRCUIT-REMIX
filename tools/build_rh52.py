"""Circuit Rhythm 5706 - RH52 (MIT): RH51 with the interface made to follow docs/INTERFAZ.md (the user, 2026-10-28: «Summarize and note
this.  Follow it on new implementations and make sure current ones follow»; the choices: own colour per page, the track menu with the
pages on pads 1-4 and the toggles under them, off = the dim of its own colour).  The `ui` option of stockplus, granpage, linein, slink,
synthpage, stepgate, usbmerge, arpext, gmmode, autorel and drumarp:
  * Stock+ K3 / K8 synced half the other way round (faster towards the left end); the pages in their own colours (Stock+ sky blue,
    Granular lilac, Synth mint: knobs, blinking track button, menu pads); Stock+ K6's filter types not in the FX view's colours;
  * the track menu: pads 1-4 = the pages (stock, Stock+, Granular, Synth); pad 9 stereo link, 11 granular on / off, 12 synth on / off,
    13 line input, 14 its gate;
  * the Synth page's K1 / K2 in the wave's colour; Granular Shift + K8 and Synth Shift + K2 (on / off) as toggles;
  * off = the dim of its own colour (Micro Step, Setup GM, Advanced 22 / 23, the arpeggiator's pads); Velocity's marks bright / dim red.
docs/PRUEBA_RH52.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh51  # noqa: E402

NAME = "RH52"


def build(name=NAME, **kw):
    return build_rh51.build(name, ui=True, **kw)


if __name__ == "__main__":
    build().finish()
