"""Circuit Remix Alpha 0.15S (MIT): Alpha 0.15 without the functions that create, change or delete files on the card by themselves (project copy
sesscopy, pack delete pkdel, sample copy smpcopy, the project's synth sounds projsnd; the nosd option), so without the pack's patches either (rpatch: they
write the pack's patch bank and need projsnd; OPT nopatch) and without rdiag (the marker A0.15S)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_a015  # noqa: E402
import rhbuild  # noqa: E402

NAME = "A0.15S"


def build(name=NAME):
    with rhbuild.options(nopatch=True):                          # without the pack's patches (rpatch needs projsnd), as Alpha 0.13S / 0.14S
        return build_a015.build(name, nosd=True)


if __name__ == "__main__":
    build().finish()
