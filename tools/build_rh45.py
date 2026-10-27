"""Circuit Rhythm 5706 - RH45 (MIT): RH44 + RD30's chain after the granular (pitchmod envexp + tools/granchain.py: the stock's VCA and a
filter of ours from the track's knobs) + granpage v2 (the user, 2026-10-26: «en lugar de doble pulsación, mantener el pad de pista abre un
desplegable de vistas (stock, stock+, granular). Actualmente al salir de la vista de granular se desactiva el granular» and «en vista Sample
Rec también falta un toggle para guardado estéreo (pad 24 de sample rec) y el toggle de de-clicker sobre loop (activo por defecto)»): a track
button held = the page menu on pads 1-4 (stock / Stock+ / Granular / the granular on-off), the granular engine kept off the page; Sample
Rec pad 23 = the loops' de-clicker (on at power-up), pad 24 = stereo recording.  docs/PRUEBA_RH45.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh40  # noqa: E402
import dsprd  # noqa: E402
import granchain  # noqa: E402
import sdyield  # noqa: E402
import startfix  # noqa: E402
import stereorec  # noqa: E402
import stfit  # noqa: E402
import stsplit  # noqa: E402

NAME = "RH45"


def build(name=NAME, sp=None, g0more=None, gpx=None, chain=None, **kw):
    b = build_rh40.build(name, ram2=True, pm={"qdrain": True, "stereo": True, "envexp": True},
                         g0extra=lambda L: granchain.segs(L, **(chain or {})) + stsplit.segs(L) + (g0more(L) if g0more else []),
                         g0post=granchain.AT_M if (chain or {}).get("multi") else granchain.AT, sp=sp or {"fitflag": True},
                         gp={"v2": True, **(gpx or {})}, **kw)
    b.add("startfix", startfix)
    if "rdiag" not in b.report:
        b.add("dsprd", dsprd)                    # (the public builds: c_d16r without rdiag)
    b.add("stereorec", stereorec)
    b.add("sdyield", sdyield)
    b.add("stfit", stfit)
    return b


if __name__ == "__main__":
    build().finish()
