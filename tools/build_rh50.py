"""Circuit Rhythm 5706 - RH50 (MIT): RH49 + the granular on several tracks at once (granular0 / granchain / gstereo / granpage multi: 4
slots, any track, the 16 grains shared) (the user, 2026-10-27: «activar un granular desactiva el anterior¿? corregir»).  docs/PRUEBA_RH50.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh46  # noqa: E402
import cue  # noqa: E402
import gstereo  # noqa: E402
import linein  # noqa: E402
import slink  # noqa: E402
import stsplit  # noqa: E402

NAME = "RH50"


def build(name=NAME, synth=False, **kw):
    """synth (RD31): tools/synth0.py's engine on core 0, between GST and LI; rh54 (RH54): synth0 env2, granchain env, linein fx (the FX
    returns, the filter on a gated slot), granpage env, trkcopy ram; rh55 (RH55): tools/sp0.py (Stock+ on core 0 for the granular and the
    synth) with synth0 / granular0 / granchain sp (their hooks; the granular's end to sp0's SPX)"""
    rh54 = kw.pop("rh54", False)
    rh55 = kw.pop("rh55", False)
    assert not rh55 or (rh54 and synth)
    if rh54:
        kw["tcram"] = True
    import sp0 as SP0
    spx = {"sp": True, "mix": SP0.entry("spx")} if rh55 else {}

    def more(L):
        spl = stsplit.code(L["gr"])[1]["spl"]
        if synth and rh54:
            import synth0
            tabs = synth0.code(0, env2=True)[3]
            li = linein.code(spl, two=True, fx=tabs)[1]["li"]
            return (linein.segs(spl, two=True, fx=tabs) + synth0.segs(li, env2=True, sp=rh55) + (SP0.segs(L) if rh55 else [])
                    + gstereo.segs(synth0.code(li, env2=True, sp=rh55)[1]["sy"], multi=True))
        li = linein.code(spl, two=True)[1]["li"]
        if synth:
            import synth0
            return linein.segs(spl, two=True) + synth0.segs(li) + gstereo.segs(synth0.code(li)[1]["sy"], multi=True)
        return linein.segs(spl, two=True) + gstereo.segs(li, multi=True)
    env = {"env": True} if rh54 else {}
    b = build_rh46.build(name, g0more=more, g0={"stereo": True, "multi": True, **spx}, chain={"stereo": True, "multi": True, **env, **spx},
                         gpx={"stereo": True, "multi": True, **env}, **kw)
    ui = {"ui": True} if kw.get("ui") else {}                         # (RH52: docs/INTERFAZ.md)
    b.add("cue", cue)
    b.add("linein", linein, two=True, **ui, **({"fx": True} if rh54 else {}))
    b.add("slink", slink, **ui)
    return b


if __name__ == "__main__":
    build().finish()
