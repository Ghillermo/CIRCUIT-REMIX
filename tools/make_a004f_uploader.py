"""firmware/a0.04f/a004f_uploader.html: the installer of A0.04F and A04FS, made with tools/make_rm_uploader.py's code and page (MIT).
tools/rm_uploader.html stays as it is.

    python tools/make_a004f_uploader.py          (needs firmware/a0.04f/*.bin, firmware/a04fs/*.bin and the stock image)
"""
import base64
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_rm_uploader as m  # noqa: E402
import rh_fw  # noqa: E402

VERSIONS = ("A0.04F", "A04FS")
DESC = {"A0.04F": ("Alpha 0.04 (experimental) + la cuenta atrás con el reloj de la música (maestro o esclavo, el 1 a tiempo, nada se graba durante la cuenta), "
                   "metrónomo visual, carga de pasos más rápida, luz de error; con diagnóstico remoto por USB",
                   "Alpha 0.04 (experimental) + the count-in on the music's clock (master or slave, the 1 on time, nothing records during the count), "
                   "visual metronome, faster step load, error light; with remote diagnostics over USB"),
        "A04FS": ("Alpha 0.04S (experimental, más segura) + las mismas funciones, sin diagnóstico remoto",
                  "Alpha 0.04S (experimental, safer) + the same features, no remote diagnostics")}
OUT = m.ROOT / "firmware/a0.04f/a004f_uploader.html"


def main():
    stock = m.STOCK_BIN.read_bytes()
    assert hashlib.sha256(stock).hexdigest() == rh_fw.STOCK_5706["image_sha256"]
    patches = {}
    for v in VERSIONS:
        d = m.ROOT / "firmware" / v.lower(); man = json.loads((d / "manifest.json").read_text())
        img = next(d.glob("*.bin")).read_bytes()
        assert hashlib.sha256(img).hexdigest() == man["image_sha256"]
        ops = m.make_patch(stock, img)
        assert m.apply(stock, ops) == img
        m.check_add(stock, ops)
        assert hashlib.sha256(rh_fw.encode(img)).hexdigest() == man["syx_sha256"]
        patches[v] = dict(dir=v.lower(), image_sha256=man["image_sha256"], syx_sha256=man["syx_sha256"], size=len(img), ops=ops)
        print(v, len(ops), "ops,", sum(len(base64.b64decode(o[1])) for o in ops if o[0] == 1), "bytes of our own")
    desc = {**m.DESC, **DESC}
    tpl = m.TEMPLATE.replace("const DESC = " + json.dumps(m.DESC, ensure_ascii=False), "const DESC = " + json.dumps(desc, ensure_ascii=False))
    assert tpl != m.TEMPLATE
    page = tpl.replace("__PATCHES__", json.dumps(patches, separators=(",", ":"))).replace("__STOCK_SYX__", rh_fw.STOCK_5706["syx_sha256"]) \
        .replace("__STOCK_IMG__", rh_fw.STOCK_5706["image_sha256"]).replace("__VERSIONS__", ", ".join(VERSIONS)).replace("__SAFER__", VERSIONS[1])
    OUT.write_text(page, encoding="utf-8", newline="")
    print(OUT, len(page), "bytes")


if __name__ == "__main__":
    main()
