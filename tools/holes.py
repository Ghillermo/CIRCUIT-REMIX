"""Our modules in the flash's holes instead of the cave (MIT; RH97; the user, 2026-11-13: «compact the Code to make room»).

A build runs twice: the first as always (every module appended), which gives each module's size (Build.sizes) and the holes (Build.holes:
noes' Easy Start code; and with tabpack's tabflash2 the room after the tables, which only exists once core 0's blocks are packed: only for
modules added after core0); plan() fits the biggest modules first, each in the hole with the least room that takes it (SLACK bytes spare,
16-byte aligned); the second build puts them there (rhbuild.PLACE).  A module whose install does more than append its code (core 0's
blocks, pitchmod's, the fixed tables) stays in the cave (KEEP).
"""
from __future__ import annotations

SLACK = 16
KEEP = {"rhstate", "rodisk", "countin", "core0", "granular0", "pitchmod", "rdiag", "tabpack", "modhost", "fwid", "cthresh", "dspload", "rhdsp1"}


def holes_of(b):
    """[(lo, hi, after)] of a finished first build: after = the order index a module must come after to use it (-1 any)"""
    out = [(lo, hi, -1) for lo, hi in b.holes]
    import rhbuild
    if rhbuild.OPT.get("holeptr"):                                        # (RH102) no module at a hole's start that a stock word names
        import struct                                                     # (noes' 0x080661DC: the mass storage class's vtable 0x08067730)
        words = set(struct.unpack_from(f"<{len(b.stock) // 4}I", b.stock))
        out = [((lo + 16) if (lo | 1) in words or lo in words else lo, hi, after) for lo, hi, after in out]
    core = next((i for i, k in enumerate(b.order) if k.split("#")[0] in ("granular0", "core0")), None)   # (core0.install runs in granular0's)
    if core is None:
        return out
    fl = b.report.get("tabpack", {}).get("flash")
    if fl:
        out.append(((int(fl[1], 16) + 15) & ~15, int(fl[2], 16), core))
    dz = b.report.get("core0", {}).get("dspz", {})
    if "hole" in dz:                                                      # what core 0's packed stream leaves of its places
        import dspz as DZ
        R = [(int(x, 16), int(y, 16)) for x, y in dz["hole"]]
        HL = DZ.H_ENT + (len(R) + 2) * DZ.ENT
        for k, ((lo, hi), (n, _w)) in enumerate(zip(R, dz["pieces"])):
            lo2 = (lo + n + (HL if k == 0 else 0) + 15) & ~15
            if hi - lo2 >= 64:
                out.append((lo2, hi, core))
    return out


def plan(b):
    """-> {"key#n": address} for the second build"""
    room = [[lo, hi, after] for lo, hi, after in holes_of(b)]
    mods = sorted(((b.sizes[t], i, t) for i, t in enumerate(b.order) if t.split("#")[0] not in KEEP and b.sizes.get(t, 0) > 0),
                  reverse=True)
    out = {}
    for size, i, t in mods:
        need = (size + SLACK + 15) & ~15
        fit = [r for r in room if r[1] - r[0] >= need and i > r[2]]
        if not fit:
            continue
        r = min(fit, key=lambda r: r[1] - r[0])
        out[t] = r[0]
        r[0] += need
    return out


def report(b, plan_):
    moved = sum(b.sizes[t] for t in plan_)
    return dict(placed={t: hex(a) for t, a in sorted(plan_.items(), key=lambda x: x[1])}, bytes=moved,
                holes=[(hex(lo), hex(hi), after) for lo, hi, after in holes_of(b)])
