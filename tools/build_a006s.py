"""Circuit Remix Alpha 0.06S (MIT): Alpha 0.06 without the functions that create, change or delete files on the card by themselves (project copy
sesscopy, pack delete pkdel, sample copy smpcopy; the nosd option of build_rh21 / build_rh26 / build_rh27) and without rdiag (the marker A0.06S)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_a006  # noqa: E402

NAME = "A0.06S"


def build(name=NAME):
    return build_a006.build(name, nosd=True)


if __name__ == "__main__":
    build().finish()
