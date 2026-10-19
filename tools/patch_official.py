"""Build a Circuit Remix firmware from the OFFICIAL Novation firmware that you provide (the repository does not ship any Novation code; MIT, from
CIRCUIT-HACKS' patch_official.py).

    python tools/patch_official.py OFFICIAL.syx|OFFICIAL.bin [--version A0.0] [--all] [--list]
  1. The official file: the Circuit Rhythm 2.0.1 (build 5706) update as Components serves it (.syx,
     https://components.novationmusic.com/api/v2/firmwares/169/file), or its application image (.bin).
     It is checked against the SHA-256 in stock/SHA256SUMS.txt; another version is refused.
  2. It is stored as stock/circuitrhythm-firmware-5706-STOCK.bin (+ .syx).
  3. The builder of the version runs (tools/build_*.py) and writes firmware/<dir>/: .bin, .syx, manifest.json.  The result must have the SHA-256 the
     repository records (firmware/<dir>/manifest.json): the build is reproducible, so a mismatch means a different toolchain (capstone) or a modified tree.
  4. Send the .syx with tools/rm_uploader.html (Chrome / Edge, Web MIDI; it can also patch the official file by itself).
     Recovery: Sample Rec + Samples + Note at power-on (Novation's bootloader mode), then the official firmware.
Requirements: Python 3.10+, `pip install -r tools/requirements.txt`.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rh_fw  # noqa: E402
from verify_builds import BUILDS  # noqa: E402

STOCK_BIN = ROOT / "stock/circuitrhythm-firmware-5706-STOCK.bin"
STOCK_SYX = ROOT / "stock/circuitrhythm-firmware-5706-STOCK.syx"


def sums():
    out = {}
    for line in (ROOT / "stock/SHA256SUMS.txt").read_text().splitlines():
        if line.strip():
            h, n = line.split()
            out[n] = h
    return out


def load_official(path: Path):
    data = path.read_bytes()
    want = sums()
    sha = hashlib.sha256(data).hexdigest()
    if data[:1] == b"\xF0":
        try:
            img = rh_fw.decode(data)["image"]
        except ValueError as e:
            raise SystemExit(f"{path}: not a Circuit Rhythm firmware update ({e})")
        if hashlib.sha256(img).hexdigest() != want["circuitrhythm-firmware-5706-STOCK.bin"]:
            raise SystemExit(f"{path}: not the official Circuit Rhythm 2.0.1 (build 5706) update (sha256 {sha})")
        return img, data
    if sha != want["circuitrhythm-firmware-5706-STOCK.bin"]:
        raise SystemExit(f"{path}: not the official 2.0.1 (build 5706) application image (sha256 {sha})")
    return data, rh_fw.encode(data)


def build_one(name, module):
    d = name.lower()
    man_p = ROOT / "firmware" / d / "manifest.json"
    want = json.loads(man_p.read_text())["syx_sha256"] if man_p.exists() else None
    with tempfile.TemporaryDirectory() as td:
        out = importlib.import_module(module).build(name).finish(Path(td))
        syx = next(out.glob("*.syx"))
        got = hashlib.sha256(syx.read_bytes()).hexdigest()
        if want and got != want:
            raise SystemExit(f"{name}: built {got[:16]}…, the repository records {want[:16]}… (another capstone version? see tools/requirements.txt)")
        dst = ROOT / "firmware" / d
        dst.mkdir(parents=True, exist_ok=True)
        for f in out.iterdir():
            if f.suffix in (".syx", ".bin") or not (dst / f.name).exists():
                shutil.copy2(f, dst / f.name)
    print(f"{name}: {dst / syx.name}  sha256 {got}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("official", type=Path, nargs="?")
    ap.add_argument("--version", default="A0.0")
    ap.add_argument("--all", action="store_true", help="every version of tools/verify_builds.py")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    vs = {n.upper(): (n, m) for n, m in BUILDS.items()}
    if a.list:
        for n, m in BUILDS.items():
            print(f"{n:8s} {m}")
        return
    if not a.official:
        ap.error("the official firmware file is needed")
    todo = list(BUILDS.items()) if a.all else [vs[a.version.upper()]] if a.version.upper() in vs else None
    if todo is None:
        raise SystemExit(f"unknown version {a.version}; --list shows them")
    img, syx = load_official(a.official)
    STOCK_BIN.parent.mkdir(exist_ok=True)
    STOCK_BIN.write_bytes(img)
    STOCK_SYX.write_bytes(syx)
    for n, m in todo:
        build_one(n, m)


if __name__ == "__main__":
    main()
