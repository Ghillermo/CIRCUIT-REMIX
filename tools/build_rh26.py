"""Circuit Rhythm 5706 - RH26 = RH25 + pkdel (MIT): in the packs view (Projects twice), Clear + a pack's pad = asked (blinking red), Clear + the same
pad again within ~5 s = that pack deleted from the card (never the loaded pack nor the internal one); part of «gestión del pack»."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh25  # noqa: E402
import pkdel  # noqa: E402

NAME = "RH26"


def build(name=NAME, **kw):
    b = build_rh25.build(name, **kw)
    if not kw.get("nosd"):                             # (Alpha 0.01S) no pack delete
        b.add("pkdel", pkdel)
    return b


if __name__ == "__main__":
    build().finish()
