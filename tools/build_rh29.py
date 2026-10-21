"""Circuit Rhythm 5706 - RH29 = RH28 + patchain iterled (MIT): in the Mixer with Shift held, while a scene with 2 or more repeats plays, the
pad of the repeat now playing (pad 9 = the first time) is white; on the last one the green pad blinks white / green (the user, 2026-10-20:
«during scene repeat, i want a led to point the current iteration inside shift view»); and a fix: the count-in and the stopped arpeggio
follow the project's tempo, p0 of the tempo store (they read p1, which is not the tempo: «pre count doesnt get the right beat»)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh28  # noqa: E402

NAME = "RH29"


def build(name=NAME, **kw):
    return build_rh28.build(name, scniter=True, bpm0=True, **kw)


if __name__ == "__main__":
    build().finish()
