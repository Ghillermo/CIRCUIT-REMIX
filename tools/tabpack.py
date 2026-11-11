"""Curve tables packed in the flash, rebuilt in the ITCM (MIT; RH87, OPT tabpack; the idea of CIRCUIT-HACKS' SC55.8 tabpack).

The modules with big tables (stockplus's decay / rate / ring / speed / scan, synthpage's glide / release, spall's gain: 129 or 128 words,
smooth curves the LZSS of dspz cannot pack) ask region(name, parts) for an ITCM address while they build: parts = [(bytes, kind)], kind 4 = a
curve of words (kept as zigzag varints: the first value, the first difference, then the second differences, exact modulo 2^32), kind 1 = bytes
as they are.  The region keeps the parts' layout, so the modules' offsets stay.  install() (the last of the build) writes the stream and
c_tbunp, and the core 0 upload's bl (fm8page's c_f8up) goes through c_tbup: the upload, then the tables.  They live in 0x2000-0x3FFF, dspz's
window, which only the upload of core 0's program uses: rebuilt after it, every time (the same bytes).

Stream: 'TBP1', then records: u32 destination (0 = the end), u16 count (words for kind 4, bytes for kind 1), u8 kind, u8 0, the body,
each record on a word.  tests/rhemu.py rebuilds the tables the same way when it maps an image.

RH91 (OPT tabpack2, v2()): kind 5 = a curve of half-words (the same varints); kind 2 = bytes packed with dspz's LZSS (the output its own
window): the byte parts (kind 1) and the zeroed ranges (kind 0) that touch, or are at most GAP bytes apart, go out as one kind 2 record (the
gaps zero).  Regions fill AREAS2 one after the other; region(at=) puts one at its own address and region(early=True) makes it one of the
records before a separator (destination 1): c_tbup unpacks those, then calls the upload, then the rest (fm8page's tables, below dspz's
window, as before the upload in RH86-RH90).  The stream also packs fm8page's tables (its LZSS blob and c_itunp go).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (Asm, adds_imm8, adds_reg, b, b_cond, bl, cmp_imm, eors_reg, h, ldr_imm, ldrb_imm, ldrh_imm, lsls_imm,  # noqa: E402
                   lsls_reg, lsrs_imm, mov_reg, movs_imm, movt, movw, orrs_reg, pop_list, push_list, raw, str_imm, strb_imm, subs_imm8,
                   add_sp_imm, cmp_reg, ldr_sp, strh_imm, subs_reg)

MAGIC = b"TBP1"
AREA = (0x2000, 0x4000)
AREAS2 = ((0x2000, 0x33F0), (0x3C40, 0x4000), (0x1BA0, 0x2000))       # (v2) the ITCM's free room: rpatch's pointers at 0x33F0 and its
GAP = 16                                                                  # snapshots 0x3400-0x3C3F, modmx's 0x1780-0x1B97, fm8page's 0x400..
SEP = 1
ST = {"items": [], "at": AREA[0], "areas": None, "low": None}
LOW = (0x100, 0x400)                                                      # (lowtab) never written by the stock (RH66), outside dspz's window


def on():
    import rhbuild
    return bool(rhbuild.OPT.get("tabpack"))


def v2():
    import rhbuild
    return bool(rhbuild.OPT.get("tabpack2"))


def reset():
    ST["items"] = []
    ST["at"] = AREA[0]
    ST["areas"] = None
    ST["low"] = None


def lowtab():
    import rhbuild
    return v2() and bool(rhbuild.OPT.get("lowtab"))


def region(name, parts, at=None, early=False, low=False):
    """the ITCM address of a region made of parts [(bytes, kind)] laid out one after the other (the same offsets as in the flash)"""
    for it in ST["items"]:
        if it["name"] == name:
            assert it["parts"] == [(bytes(p), k) for p, k in parts], name
            return it["at"]
    size = sum(len(p) for p, _ in parts)
    if low:                                                               # (lowtab) ITCM 0x100-0x3FF, unpacked before core 0's block
        assert lowtab()
        if ST["low"] is None:
            ST["low"] = list(LOW)
        at = ST["low"][0]
        assert at + size <= ST["low"][1], f"tabpack: no low room for {name} ({size} B)"
        ST["low"][0] = (at + size + 3) & ~3
        ST["items"].append(dict(name=name, at=at, parts=[(bytes(p), k) for p, k in parts], early=True))
        return at
    if at is not None:
        assert v2() and 0x400 <= at and at + size <= AREA[1], name
        ST["items"].append(dict(name=name, at=at, parts=[(bytes(p), k) for p, k in parts], early=early))
        return at
    if v2():
        if ST["areas"] is None:
            ST["areas"] = [[lo, hi] for lo, hi in AREAS2]
        for ar in ST["areas"]:
            if ar[0] + size <= ar[1]:
                at = ar[0]
                ar[0] = (at + size + 3) & ~3
                break
        else:
            raise AssertionError(f"tabpack: no room in the ITCM for {name} ({size} B)")
        ST["items"].append(dict(name=name, at=at, parts=[(bytes(p), k) for p, k in parts], early=early))
        return at
    at = ST["at"]
    assert at + size <= AREA[1], name
    ST["items"].append(dict(name=name, at=at, parts=[(bytes(p), k) for p, k in parts]))
    ST["at"] = (at + size + 3) & ~3
    return at


def fixed(name, at, n):
    """a range zeroed at every rebuild (kind 0), at its own address (modmx's offsets in the ITCM)"""
    for it in ST["items"]:
        if it["name"] == name:
            return it["at"]
    ST["items"].append(dict(name=name, at=at, parts=[(bytes(n), 0)]))
    return at


def where(name):
    return next(it["at"] for it in ST["items"] if it["name"] == name)


def contents():
    """{address: byte} of every region (the build's checks)"""
    out = {}
    for it in ST["items"]:
        a = it["at"]
        for p, _ in it["parts"]:
            for i, x in enumerate(p):
                out[a + i] = x
            a += len(p)
    return out


def _zz(x):
    x = x - (1 << 32) if x & 0x80000000 else x
    return ((x << 1) ^ (x >> 31)) & 0xFFFFFFFF


def _vi(x):
    z = _zz(x & 0xFFFFFFFF)
    out = bytearray()
    while True:
        b_ = z & 0x7F
        z >>= 7
        out.append(b_ | (0x80 if z else 0))
        if not z:
            return bytes(out)


def _d2(vals):
    body = bytearray(_vi(vals[0]))
    if len(vals) > 1:
        body += _vi(vals[1] - vals[0])
    for i in range(2, len(vals)):
        body += _vi((vals[i] - 2 * vals[i - 1] + vals[i - 2]) & 0xFFFFFFFF)
    return bytes(body)


def _flat(items):
    for it in items:
        a = it["at"]
        for p, kind in it["parts"]:
            yield a, p, kind
            a += len(p)


def _recs2(items):
    """(v2) the records of some items: curves on their own, touching byte / zero parts merged into one LZSS record"""
    import dspz
    parts = sorted(((a, p, k) for a, p, k in _flat(items) if p), key=lambda x: x[0])
    out = bytearray()
    grp = [None]

    def flush():
        if grp[0] is None:
            return
        a0, buf = grp[0]
        grp[0] = None
        if not any(buf):
            out.extend(struct.pack("<IHBB", a0, len(buf), 0, 0))
            return
        st = dspz._pack(bytes(buf))
        assert dspz.unpack_stream(st, len(buf)) == bytes(buf)
        out.extend(struct.pack("<IHBB", a0, len(buf), 2, 0) + st)
        while len(out) % 4:
            out.append(0)
    for a, p, k in parts:
        if k in (4, 5):
            flush()
            w = 4 if k == 4 else 2
            assert len(p) % w == 0
            v = list(struct.unpack("<%d%s" % (len(p) // w, "I" if w == 4 else "H"), p))
            out.extend(struct.pack("<IHBB", a, len(v), k, 0) + _d2(v))
            while len(out) % 4:
                out.append(0)
            continue
        body = bytes(len(p)) if k == 0 else bytes(p)
        g = grp[0]
        if g is not None:
            end = g[0] + len(g[1])
            assert a >= end, "tabpack: overlapping regions"
        if g is not None and a - end <= GAP and a + len(p) - g[0] < 0x10000:
            g[1].extend(bytes(a - end) + body)
        else:
            flush()
            grp[0] = (a, bytearray(body))
    flush()
    return bytes(out)


def stream(items=None):
    items = ST["items"] if items is None else items
    if v2():
        out = bytearray(MAGIC)
        out += _recs2([it for it in items if it.get("early")])
        out += struct.pack("<IHBB", SEP, 0, 0, 0)
        out += _recs2([it for it in items if not it.get("early")])
        out += bytes(8)
        return bytes(out)
    out = bytearray(MAGIC)
    for it in items:
        a = it["at"]
        for p, kind in it["parts"]:
            if not p:
                continue
            if kind == 0:
                out += struct.pack("<IHBB", a, len(p), 0, 0)
                a += len(p)
                continue
            if kind == 4:
                assert len(p) % 4 == 0
                v = list(struct.unpack("<%dI" % (len(p) // 4), p))
                body = bytearray(_vi(v[0]))
                if len(v) > 1:
                    body += _vi(v[1] - v[0])
                for i in range(2, len(v)):
                    body += _vi((v[i] - 2 * v[i - 1] + v[i - 2]) & 0xFFFFFFFF)
                out += struct.pack("<IHBB", a, len(v), 4, 0) + body
            else:
                out += struct.pack("<IHBB", a, len(p), 1, 0) + p
            while len(out) % 4:
                out.append(0)
            a += len(p)
    out += bytes(8)
    return bytes(out)


def unpack(st):
    """[(address, bytes)] from a stream (the emulators')"""
    assert st[:4] == MAGIC
    i, out = 4, []
    while True:
        dest, n, kind, _ = struct.unpack_from("<IHBB", st, i)
        i += 8
        if dest == 0:
            return out
        if dest == SEP:
            continue
        if kind == 2:
            buf, flags = bytearray(), 1
            while len(buf) < n:
                if flags == 1:
                    flags = st[i] | 0x100
                    i += 1
                lit = flags & 1
                flags >>= 1
                if lit:
                    buf.append(st[i])
                    i += 1
                else:
                    x = st[i] | st[i + 1] << 8
                    i += 2
                    o, ln = (x & 0x1FFF) + 1, x >> 13
                    if ln == 7:
                        ln += st[i]
                        i += 1
                    for _ in range(ln + 3):
                        buf.append(buf[-o])
            out.append((dest, bytes(buf)))
        elif kind == 0:
            out.append((dest, bytes(n)))
        elif kind == 1:
            out.append((dest, bytes(st[i:i + n])))
            i += n
        else:
            vals, v, d = [], 0, 0
            for k in range(n):
                z, sh = 0, 0
                while True:
                    c = st[i]
                    i += 1
                    z |= (c & 0x7F) << sh
                    sh += 7
                    if not c & 0x80:
                        break
                x = ((z >> 1) ^ -(z & 1)) & 0xFFFFFFFF
                if k == 0:
                    v = x
                elif k == 1:
                    d = x
                    v = (v + d) & 0xFFFFFFFF
                else:
                    d = (d + x) & 0xFFFFFFFF
                    v = (v + d) & 0xFFFFFFFF
                vals.append(v)
            out.append((dest, struct.pack("<%dI" % n, *vals) if kind == 4 else struct.pack("<%dH" % n, *(x & 0xFFFF for x in vals))))
        i = (i + 3) & ~3


def arm_code2(base, prev_up, late1=False, prev1=None):
    """(v2) c_tbunp(r0 = a record) -> r0 = past the separator / the end; c_tbup: the early records, the upload, the rest"""
    a = Asm(base)
    E = a.emit
    st = stream()
    t_st = base
    E(raw, st + bytes(-len(st) % 4))

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        if v >> 16:
            E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- tb_vi(r0 = the stream) -> r1 = the next varint, decoded; r0 past it; clobbers r6, r7
    a.label("tb_vi")
    E(push_list, [4])
    E(movs_imm, 1, 0)
    E(movs_imm, 6, 0)
    a.label("vi_l")
    E(ldrb_imm, 7, 0, 0)
    E(adds_imm8, 0, 1)
    E(lsls_imm, 4, 7, 25)
    E(lsrs_imm, 4, 4, 25)
    E(lsls_reg, 4, 6)
    E(orrs_reg, 1, 4)
    E(adds_imm8, 6, 7)
    E(lsrs_imm, 7, 7, 8)                                                  # the carry = bit 7: more
    E(b_cond, "vi_l", "cs")
    E(lsrs_imm, 4, 1, 1)
    E(lsls_imm, 1, 1, 31)
    E(raw, h(0x1000 | 31 << 6 | 1 << 3 | 1))                              # asrs r1, r1, #31
    E(eors_reg, 1, 4)
    E(pop_list, [4])
    E(raw, h(0x4770))

    # ---- tb_sv: r2 to [r4] as the record's kind ([sp] after tb_sv's bl: 4 = a word, 5 = a half-word), r4 past it; clobbers r7
    a.label("tb_sv")
    E(ldr_sp, 7, 0)
    E(cmp_imm, 7, 5)
    E(b_cond, "sv_h", "eq")
    E(str_imm, 2, 4, 0)
    E(adds_imm8, 4, 4)
    E(raw, h(0x4770))
    a.label("sv_h")
    E(strh_imm, 2, 4, 0)
    E(adds_imm8, 4, 2)
    E(raw, h(0x4770))

    # ---- c_tbunp(r0 = a record) -> r0 = past the separator (or the end); clobbers r1-r3
    a.label("c_tbunp")
    E(push_list, [4, 5, 6, 7], lr=True)
    a.label("tu_r")
    E(ldr_imm, 4, 0, 0)                                                   # the destination: 0 the end, 1 the separator
    E(adds_imm8, 0, 8)
    E(cmp_imm, 4, SEP)
    E(b_cond, "tu_x", "ls")
    E(subs_imm8, 0, 8)
    E(ldrh_imm, 5, 0, 4)
    E(ldrb_imm, 6, 0, 6)
    E(adds_imm8, 0, 8)
    E(cmp_imm, 6, 4)
    E(b_cond, "tu_w", "hs")
    E(cmp_imm, 6, 2)
    E(b_cond, "tu_z", "eq")
    a.label("tu_b")                                                       # zeros (kind 0)
    E(movs_imm, 1, 0)
    E(strb_imm, 1, 4, 0)
    E(adds_imm8, 4, 1)
    E(subs_imm8, 5, 1)
    E(b_cond, "tu_b", "ne")
    E(b, "tu_a")
    a.label("tu_z")                                                       # LZSS (kind 2): the output its own window
    E(adds_reg, 2, 4, 5)
    E(movs_imm, 3, 1)
    a.label("lz_l")
    E(cmp_reg, 4, 2)
    E(b_cond, "tu_a", "hs")
    E(cmp_imm, 3, 1)
    E(b_cond, "lz_f", "ne")
    E(ldrb_imm, 3, 0, 0)
    E(adds_imm8, 0, 1)
    E(movs_imm, 6, 1)
    E(lsls_imm, 6, 6, 8)
    E(orrs_reg, 3, 6)
    a.label("lz_f")
    E(lsrs_imm, 3, 3, 1)
    E(b_cond, "lz_m", "cc")
    E(ldrb_imm, 6, 0, 0)
    E(adds_imm8, 0, 1)
    E(strb_imm, 6, 4, 0)
    E(adds_imm8, 4, 1)
    E(b, "lz_l")
    a.label("lz_m")                                                       # a match: (offset - 1) bits 0-12, length - 3 bits 13-15
    E(ldrb_imm, 6, 0, 0)
    E(ldrb_imm, 7, 0, 1)
    E(adds_imm8, 0, 2)
    E(lsls_imm, 7, 7, 8)
    E(orrs_reg, 6, 7)
    E(lsrs_imm, 7, 6, 13)
    E(lsls_imm, 6, 6, 19)
    E(lsrs_imm, 6, 6, 19)
    E(adds_imm8, 6, 1)
    E(cmp_imm, 7, 7)
    E(b_cond, "lz_n", "ne")
    E(ldrb_imm, 1, 0, 0)
    E(adds_imm8, 0, 1)
    E(adds_reg, 7, 7, 1)
    a.label("lz_n")
    E(adds_imm8, 7, 3)
    E(subs_reg, 6, 4, 6)
    a.label("lz_c")
    E(ldrb_imm, 1, 6, 0)
    E(adds_imm8, 6, 1)
    E(strb_imm, 1, 4, 0)
    E(adds_imm8, 4, 1)
    E(subs_imm8, 7, 1)
    E(b_cond, "lz_c", "ne")
    E(b, "lz_l")
    a.label("tu_w")                                                       # curves (kind 4 words, 5 half-words): v0, d1, then d2
    E(push_list, [6])
    E(bl, "tb_vi")
    E(mov_reg, 2, 1)
    E(bl, "tb_sv")
    E(subs_imm8, 5, 1)
    E(b_cond, "tu_wx", "eq")
    E(bl, "tb_vi")
    E(mov_reg, 3, 1)
    E(adds_reg, 2, 2, 3)
    E(bl, "tb_sv")
    E(subs_imm8, 5, 1)
    E(b_cond, "tu_wx", "eq")
    a.label("tu_dl")
    E(bl, "tb_vi")
    E(adds_reg, 3, 3, 1)
    E(adds_reg, 2, 2, 3)
    E(bl, "tb_sv")
    E(subs_imm8, 5, 1)
    E(b_cond, "tu_dl", "ne")
    a.label("tu_wx")
    E(raw, add_sp_imm(4))
    a.label("tu_a")
    E(adds_imm8, 0, 3)
    E(lsrs_imm, 0, 0, 2)
    E(lsls_imm, 0, 0, 2)
    E(b, "tu_r")
    a.label("tu_x")
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_tbup (the core 0 upload's bl): the early records (fm8page's), the upload, the rest
    a.label("c_tbup")
    E(push_list, [0, 1, 2, 4, 5], lr=True)
    imm32(0, t_st + 4)
    E(bl, "c_tbunp")
    E(mov_reg, 5, 0)
    E(ldr_sp, 0, 0)
    E(ldr_sp, 1, 4)
    E(ldr_sp, 2, 8)
    E(bl, prev_up)
    if late1:                                                             # (RD47, OPT dzmore) the rest after core 1's block (its unpacking
        E(raw, add_sp_imm(12))                                            #  uses the ITCM's window too): c_tb1
        E(pop_list, [4, 5], pc=True)
        late = t_st + len(MAGIC) + len(_recs2([it for it in ST["items"] if it.get("early")])) + 8
        a.label("c_tb1")                                                  # (r0 = block, r1 = core; in place of core 1's send)
        E(push_list, [4], lr=True)
        E(bl, prev1)
        E(mov_reg, 4, 0)
        imm32(0, late)
        E(bl, "c_tbunp")
        E(mov_reg, 0, 4)
        E(pop_list, [4], pc=True)
        return a.assemble()
    E(mov_reg, 4, 0)
    E(mov_reg, 0, 5)
    E(bl, "c_tbunp")
    E(mov_reg, 0, 4)
    E(raw, add_sp_imm(12))
    E(pop_list, [4, 5], pc=True)
    return a.assemble()


def arm_code(base, prev_up, late1=False, prev1=None):
    if v2():
        return arm_code2(base, prev_up, late1, prev1)
    a = Asm(base)
    E = a.emit
    st = stream()
    t_st = base
    E(raw, st + bytes(-len(st) % 4))

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        if v >> 16:
            E(movt, rd, (v >> 16) & 0xFFFF)

    # ---- tb_vi(r0 = the stream) -> r1 = the next varint, decoded; r0 past it; clobbers r6, r7
    a.label("tb_vi")
    E(push_list, [4])
    E(movs_imm, 1, 0)
    E(movs_imm, 6, 0)
    a.label("vi_l")
    E(ldrb_imm, 7, 0, 0)
    E(adds_imm8, 0, 1)
    E(lsls_imm, 4, 7, 25)
    E(lsrs_imm, 4, 4, 25)
    E(lsls_reg, 4, 6)
    E(orrs_reg, 1, 4)
    E(adds_imm8, 6, 7)
    E(lsrs_imm, 7, 7, 8)                                                  # the carry = bit 7: more
    E(b_cond, "vi_l", "cs")
    E(lsrs_imm, 4, 1, 1)
    E(lsls_imm, 1, 1, 31)
    E(raw, h(0x1000 | 31 << 6 | 1 << 3 | 1))                              # asrs r1, r1, #31
    E(eors_reg, 1, 4)
    E(pop_list, [4])
    E(raw, h(0x4770))

    # ---- c_tbunp(): the tables into the ITCM; clobbers r0-r3
    a.label("c_tbunp")
    E(push_list, [4, 5, 6, 7], lr=True)
    imm32(0, t_st + 4)
    a.label("tu_r")
    E(ldr_imm, 4, 0, 0)                                                   # the destination
    E(cmp_imm, 4, 0)
    E(b_cond, "tu_x", "eq")
    E(ldrh_imm, 5, 0, 4)
    E(ldrb_imm, 6, 0, 6)
    E(adds_imm8, 0, 8)
    E(cmp_imm, 6, 4)
    E(b_cond, "tu_w", "eq")
    a.label("tu_b")                                                       # bytes (kind 1), zeros (kind 0)
    E(movs_imm, 1, 0)
    E(cmp_imm, 6, 0)
    E(b_cond, "tu_bz", "eq")
    E(ldrb_imm, 1, 0, 0)
    E(adds_imm8, 0, 1)
    a.label("tu_bz")
    E(strb_imm, 1, 4, 0)
    E(adds_imm8, 4, 1)
    E(subs_imm8, 5, 1)
    E(b_cond, "tu_b", "ne")
    E(b, "tu_a")
    a.label("tu_w")                                                       # words: v0, d1, then second differences
    E(bl, "tb_vi")
    E(mov_reg, 2, 1)
    E(str_imm, 2, 4, 0)
    E(adds_imm8, 4, 4)
    E(subs_imm8, 5, 1)
    E(b_cond, "tu_a", "eq")
    E(bl, "tb_vi")
    E(mov_reg, 3, 1)
    E(adds_reg, 2, 2, 3)
    E(str_imm, 2, 4, 0)
    E(adds_imm8, 4, 4)
    E(subs_imm8, 5, 1)
    E(b_cond, "tu_a", "eq")
    a.label("tu_dl")
    E(bl, "tb_vi")
    E(adds_reg, 3, 3, 1)
    E(adds_reg, 2, 2, 3)
    E(str_imm, 2, 4, 0)
    E(adds_imm8, 4, 4)
    E(subs_imm8, 5, 1)
    E(b_cond, "tu_dl", "ne")
    a.label("tu_a")
    E(adds_imm8, 0, 3)
    E(lsrs_imm, 0, 0, 2)
    E(lsls_imm, 0, 0, 2)
    E(b, "tu_r")
    a.label("tu_x")
    E(pop_list, [4, 5, 6, 7], pc=True)

    # ---- c_tbup (the core 0 upload's bl, ahead of the one before): the upload, then the tables
    a.label("c_tbup")
    E(push_list, [4], lr=True)
    E(bl, prev_up)
    E(mov_reg, 4, 0)
    E(bl, "c_tbunp")
    E(mov_reg, 0, 4)
    E(pop_list, [4], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    """The last module of a build with OPT tabpack: the stream, its unpacker, the upload's bl."""
    import rhbuild
    import core0
    assert on() and ST["items"]
    BASE = rhbuild.BASE
    prev = rhbuild.bl_target(img, core0.UPLOAD_BL0)
    late1 = v2() and "dzmore" in report.get("core0", {})                 # (RD47) core 1's block packed: the late tables after it
    prev1 = rhbuild.bl_target(img, core0.UPLOAD_BL1) if late1 else None
    code_, labels = arm_code(base_addr, prev, late1, prev1)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code_
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, core0.UPLOAD_BL0, f"bl #{prev:#x}", bl(core0.UPLOAD_BL0, labels["c_tbup"]))
    if late1:
        rhbuild.patch(img, core0.UPLOAD_BL1, f"bl #{prev1:#x}", bl(core0.UPLOAD_BL1, labels["c_tb1"]))
    want = contents()
    got = {}
    for a_, bs in unpack(stream()):
        for i, x in enumerate(bs):
            got[a_ + i] = x
    if v2():                                                              # (the gaps merged into an LZSS record: zeros, never another's)
        extra = {k: v for k, v in got.items() if k not in want}
        assert not any(extra.values()) and len(extra) <= 64 * GAP, "tabpack: gaps"
        assert all(not (0x3400 <= k < 0x3C40 or 0x33F0 <= k < 0x33F8) for k in extra)
        got = {k: v for k, v in got.items() if k in want}
    assert got == want, "tabpack: the stream does not give the tables back"
    if late1:                                                             # (RD47) what the stream writes, for the tests
        ks = sorted(set(got) | set(range(0x33F0, 0x33F8)))
        runs_ = []
        for k in ks:
            if runs_ and k == runs_[-1][1]:
                runs_[-1][1] = k + 1
            else:
                runs_.append([k, k + 1])
        written = [(hex(lo), hex(hi)) for lo, hi in runs_]
    report["tabpack"] = dict(prev=hex(prev), labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")},
                             regions={it["name"]: hex(it["at"]) for it in ST["items"]}, stream=len(stream()),
                             raw=sum(len(p) for it in ST["items"] for p, _ in it["parts"]))
    if late1:
        report["tabpack"]["written"] = written
    return labels, code_
