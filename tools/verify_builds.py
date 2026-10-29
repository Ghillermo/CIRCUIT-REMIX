"""Rebuild every build and compare it with its manifest (a new build must never change an old one), MIT.

    python tools/verify_builds.py        -> ALL IDENTICAL, or the builds that changed
Also checks that no two builds share the 6-byte marker (the bootloader would not install one over the other).
"""
import importlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
BUILDS = {"A0.09": "build_a009", "A0.09S": "build_a009s", "A0.08": "build_a008", "A0.08S": "build_a008s", "A0.07": "build_a007", "A0.07S": "build_a007s", "A0.06": "build_a006", "A0.06S": "build_a006s", "A0.05": "build_a005", "A0.05S": "build_a005s", "A0.04": "build_a004", "A0.04S": "build_a004s", "A0.03": "build_a003", "A0.03S": "build_a003s", "A0.02": "build_a002", "A0.02S": "build_a002s", "A0.01F": "build_a001f", "A01FS": "build_a01fs", "A0.01": "build_a001", "A0.01S": "build_a001s", "A0.0": "build_a00", "A0.0S": "build_a00s"}


def main():
    bad = []
    marks = {}
    for name, mod in BUILDS.items():
        m = importlib.import_module(mod)
        man = json.loads((ROOT / "firmware" / name.lower() / "manifest.json").read_text())
        with tempfile.TemporaryDirectory() as td:
            out = m.build(name).finish(Path(td))
            new = json.loads((out / "manifest.json").read_text())
        same = new["syx_sha256"] == man["syx_sha256"]
        print(("same   " if same else "CHANGED"), name)
        bad += [] if same else [name]
        mk = name.encode()[:6]
        if mk in marks:
            bad.append(f"{name} shares its marker with {marks[mk]}")
        marks[mk] = name
    print("ALL IDENTICAL" if not bad else f"DIFFER: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
