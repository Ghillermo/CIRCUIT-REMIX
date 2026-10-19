"""Build framework of the Circuit Rhythm 5706 patches (MIT).

The method of CIRCUIT-HACKS, for the Rhythm:
  * the stock image is checked by SHA-256 before anything is patched;
  * every hook names the stock instructions it replaces (Capstone text) and fails the build if they differ, or if any
    branch of the stock lands inside the replaced bytes;
  * our code is appended after the stock image (a "cave"); the image grows (keep it small: the Rhythm bootloader's limit
    is not verified, see LEEME.md);
  * the 6-byte marker goes in the zero tail of the version block (offset 0x1C8 + 0x20): the bootloader only installs an
    image whose version block differs;
  * the .syx comes out of rh_fw.encode and is decoded back (CRC) before it is written;
  * provenance: no 16-byte run of our code may also appear in the Circuit Tracks image (the final build carries only
    Circuit Rhythm code and ours); the Tracks image is only read, when it is present, for this check.
"""

from __future__ import annotations

import json
import re
import struct
from pathlib import Path

import capstone

import rh_fw

ROOT = Path(__file__).resolve().parent.parent
STOCK = ROOT / "stock" / "circuitrhythm-firmware-5706-STOCK.bin"
TRACKS = ROOT.parent / "CIRCUIT-HACKS" / "stock" / "circuittracks-firmware-4486-STOCK.bin"
BASE = rh_fw.APP_BASE
MD = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
_TARGETS = None


def load_stock() -> bytes:
    data = STOCK.read_bytes()
    if rh_fw.sha256(data) != rh_fw.STOCK_5706["image_sha256"]:
        raise SystemExit(f"{STOCK} is not the stock Circuit Rhythm 5706 image")
    return data


def disasm(data: bytes, addr: int):
    return [f"{i.mnemonic} {i.op_str}".strip() for i in MD.disasm(data, addr)]


def branch_targets(stock: bytes):
    """Every direct branch target of the stock image."""
    global _TARGETS
    if _TARGETS is None:
        t = set()
        for i in MD.disasm(stock, BASE):
            if i.mnemonic.startswith(("b", "cb")) and i.mnemonic not in ("bic", "bics", "bfi", "bfc", "bkpt"):
                m = re.match(r"(?:\w+, )?#0x([0-9a-f]+)$", i.op_str)
                if m:
                    t.add(int(m.group(1), 16))
        _TARGETS = t
    return _TARGETS


def bl_target(img, addr: int) -> int:
    """Target of the Thumb-2 `bl` at addr in img."""
    h1, h2 = struct.unpack_from("<HH", img, addr - BASE)
    assert h1 & 0xF800 == 0xF000 and h2 & 0xD000 == 0xD000, f"no bl at {addr:#x}"
    s = (h1 >> 10) & 1
    j1, j2 = (h2 >> 13) & 1, (h2 >> 11) & 1
    i1, i2 = 1 - (j1 ^ s), 1 - (j2 ^ s)
    off = s << 24 | i1 << 23 | i2 << 22 | (h1 & 0x3FF) << 12 | (h2 & 0x7FF) << 1
    if off & (1 << 24):
        off -= 1 << 25
    return addr + 4 + off


def bw_target(img, addr: int) -> int:
    """Target of the Thumb-2 `b.w` at addr in img."""
    h1, h2 = struct.unpack_from("<HH", img, addr - BASE)
    assert h1 & 0xF800 == 0xF000 and h2 & 0xD000 == 0x9000, f"no b.w at {addr:#x}"
    s = (h1 >> 10) & 1
    j1, j2 = (h2 >> 13) & 1, (h2 >> 11) & 1
    i1, i2 = 1 - (j1 ^ s), 1 - (j2 ^ s)
    off = s << 24 | i1 << 23 | i2 << 22 | (h1 & 0x3FF) << 12 | (h2 & 0x7FF) << 1
    if off & (1 << 24):
        off -= 1 << 25
    return addr + 4 + off


def patch(img, addr: int, expect: str, new: bytes):
    """For a module: replace len(new) bytes at addr, which must disassemble (as they are now in img, so a chain of hooks
    sees the previous module's edit) to `expect`; no direct branch of the stock may land inside them."""
    off = addr - BASE
    got = "|".join(disasm(bytes(img[off:off + len(new)]), addr))
    if got != expect:
        raise SystemExit(f"patch {addr:#x}: found '{got}', expected '{expect}'")
    stock = load_stock()
    for x in range(addr + 1, addr + len(new)):
        if x in branch_targets(stock):
            raise SystemExit(f"patch {addr:#x}: something branches into {x:#x}")
    img[off:off + len(new)] = new


def patch_word(img, addr: int, old: int, new: int):
    """For a module: a data word (a vtable entry) at addr, which must hold `old` (as it is now in img: a chain sees the previous module's)."""
    off = addr - BASE
    got = struct.unpack_from("<I", img, off)[0]
    if got != old:
        raise SystemExit(f"patch_word {addr:#x}: found {got:#x}, expected {old:#x}")
    struct.pack_into("<I", img, off, new)


class Build:
    def __init__(self, name: str):
        if len(name.encode()) > 6:
            raise SystemExit(f"marker {name!r} longer than 6 bytes: the bootloader would see it cut")
        self.name = name
        self.stock = load_stock()
        self.img = bytearray(self.stock)
        self.report = {}
        self.patched = []                      # (offset, length) of the changed stock bytes
        self.cave_start = self.next_base()

    # ---- placement
    def next_base(self, align: int = 16) -> int:
        end = BASE + len(self.img)
        return (end + align - 1) & ~(align - 1)

    def hook(self, addr: int, expect: str, new: bytes):
        """Replace len(new) stock bytes at addr, which must disassemble to `expect` ('|' between instructions)."""
        off = addr - BASE
        old = self.stock[off:off + len(new)]
        got = "|".join(disasm(old, addr))
        if got != expect:
            raise SystemExit(f"hook {addr:#x}: stock is '{got}', expected '{expect}'")
        for x in range(addr + 1, addr + len(new)):
            if x in branch_targets(self.stock):
                raise SystemExit(f"hook {addr:#x}: something branches into {x:#x}")
        self.img[off:off + len(new)] = new
        self.patched.append((off, len(new)))

    def add(self, key: str, module, **kw):
        """A module with install(img, report, base) that appends its code; its stock edits are tracked by diff."""
        before = bytes(self.img[:len(self.stock)])
        base = self.next_base()
        module.install(self.img, self.report, base, **kw)
        for i, (a, b) in enumerate(zip(before, self.img[:len(self.stock)])):
            if a != b:
                self.patched.append((i, 1))
        self.report.setdefault(key, {})["base"] = hex(base)

    # ---- checks
    def provenance(self, run: int = 16):
        if not TRACKS.exists():
            return "not checked (no Tracks image here)"
        tracks = TRACKS.read_bytes()
        cave = bytes(self.img[len(self.stock):])
        seen = set(tracks[i:i + run] for i in range(len(tracks) - run))
        for i in range(0, max(0, len(cave) - run)):
            w = cave[i:i + run]
            if w.count(0xFF) < run // 2 and w.count(0) < run // 2 and w in seen:
                raise SystemExit(f"provenance: our code at {BASE + len(self.stock) + i:#x} repeats {run} bytes of the Circuit Tracks image")
        return f"ok ({len(cave)} B, no {run}-byte run of the Tracks image)"

    # ---- output
    def finish(self, outdir: Path | None = None) -> Path:
        img = self.img
        img[rh_fw.MARK_OFF:rh_fw.MARK_OFF + 6] = self.name.encode().ljust(6, b"\0")
        self.patched.append((rh_fw.MARK_OFF, 6))
        assert self.stock[rh_fw.MARK_OFF:rh_fw.MARK_OFF + 6] == b"\0" * 6
        while len(img) % 4:
            img.append(0xFF)
        if len(img) > rh_fw.MAX_IMAGE_SIZE:
            raise SystemExit("image too large")
        img = bytes(img)
        syx = rh_fw.encode(img)
        info = rh_fw.decode(syx)
        assert info["image"] == img and info["product"] == rh_fw.PRODUCT_RHYTHM
        prov = self.provenance()
        outdir = outdir or ROOT / "firmware" / self.name.lower()
        outdir.mkdir(parents=True, exist_ok=True)
        stem = f"circuitrhythm-5706-{self.name}"
        (outdir / f"{stem}.bin").write_bytes(img)
        (outdir / f"{stem}.syx").write_bytes(syx)
        changed = sorted({o for o, n in self.patched for o in range(o, o + n)
                          if o < len(self.stock) and img[o] != self.stock[o]})
        manifest = dict(base="circuitrhythm-firmware-5706 (DR1.1.5143.5706)", marker=self.name, image_size=hex(len(img)),
                        free_to_0x70000=hex(rh_fw.MAX_IMAGE_SIZE - len(img)), grown_by=len(img) - len(self.stock),
                        stock_bytes_changed=len(changed), image_sha256=rh_fw.sha256(img), syx_sha256=rh_fw.sha256(syx),
                        crc32=hex(info["crc"]), provenance=prov, report=self.report)
        (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        print(f"{self.name}: image {len(img):#x} (+{len(img) - len(self.stock)} B), {len(changed)} stock bytes changed, "
              f"syx {manifest['syx_sha256'][:16]}..., crc {manifest['crc32']}, provenance {prov}")
        return outdir
