"""Circuit Rhythm 5706 - RH78 (MIT): RH77 + the bipolar knobs' left half in the lighter shade of their colour and K7's zones in their own
colours (OPT leftlight; the user, 2026-11-06, after RH77: «sí, todas las zonas dentro de un knob tienen que ser distintas. los bipolares, con
un color en la misma gama (preferentemente más claro) hacia la izquierda»): kbright draws a code with bit 15 halfway to white; synthpage,
granpage, stockplus, envpage, fm8page, modmx, slinkofs and velcurve set it left of the middle (the overlay only, never the frame); the Synth
page's K7 (sync + bitwise) and its matrix view: none dark, sync blue, xor red-orange, or green, nor pink, and pale yellow, nand silver.
docs/PRUEBA_RH78.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh77  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH78"


def build(name=NAME, **kw):
    with rhbuild.options(leftlight=True):
        return build_rh77.build(name, **kw)


if __name__ == "__main__":
    build().finish()
