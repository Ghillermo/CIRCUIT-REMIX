"""Circuit Rhythm 5706 - RH61 (MIT): RH60 + dqchain last (the user, 2026-10-30: «1 in N: make the playing step the last one»): a step "one in
n" plays on the last of its n passes.  docs/PRUEBA_RH61.md."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh60  # noqa: E402

NAME = "RH61"


def build(name=NAME, **kw):
    return build_rh60.build(name, dc=dict(last=True), **kw)


if __name__ == "__main__":
    build().finish()
