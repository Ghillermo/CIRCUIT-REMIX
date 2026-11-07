"""Our DSP code packed in the flash, unpacked while it is sent (MIT; RH69; CIRCUIT-HACKS' SC50.8 dspz, the same LZSS, on the Rhythm).

The user (2026-11-04): «Consider using the ITCM to save more room (unpack technique from Hacks)».  The flash was the limit (RH68: 3 088 B
left) and a third of our code is core 0's program: tools/core0.py's segments, ~24 KB as 3-byte words.

The stock's sender 0x080310B0(block, core): count = bytes 1-2 of the block's first word, + 2 header words; WAIT 0x08046414, SELECT
0x08031048(core), then the words in chunks of at most 0xAA through the SPI's DMA 0x08046504(pointer, bytes), WAIT after each, WAIT, and
the end 0x0803107A(core) (a tail call).  core0.py's c_d0up sends our loader, the stock block, then our segments and the end [0, 0], each
by that sender: the second-stage loader on the DSP just reads words, so the segments and the end can go as one stream.
Here (core0.install with OPT dspz): that stream packed into one blob at build time, sent by c_dz(blob, core) with the stock's own waits,
select, chunks and end, the chunks unpacked into a 510-byte staging buffer the DMA reads.  The blob: 'DZ1\\0', the words (+ 4), the
CRC-32 of the stream (+ 8), the LZSS stream (+ 12).  LZSS: a flag byte before every 8 items, bit 0 first, 1 = a literal byte, 0 = a match
of two bytes: (offset - 1) in bits 0-12, length - 3 in bits 13-15; 7 = an extra byte with length - 10 (10..265).  The window is the last
8 KB, kept in the ITCM at 0x2000..0x3FFF (16 KB at 0x0, never touched by the stock: RH66 on the device, 512 clean sweeps); the staging
buffer and the unpacker's state in the RAM above the stock's last allocation (0x2004EA98: the stock never allocates after boot,
tools/rhheap.py on the device), below rhstate's second block (0x2004EE60).
Not with modhost (its third RAM block at 0x2004EC60, its modules in the ITCM) nor bootrec (its log at 0x2004EB00).
"""
from __future__ import annotations

import hashlib
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from thumb import (add_sp_imm, str_sp, adds_imm8, adds_reg, b, b_cond, b_w, bl, cmp_imm, cmp_reg, ldr_imm, ldr_sp, ldrb_imm, ldrb_reg,  # noqa: E402
                   lsls_imm, lsrs_imm, mov_reg, movs_imm, movt, movw, orrs_reg, pop_list, push_list, str_imm, strb_imm, strb_reg,
                   subs_imm8, subs_reg)

WAIT, SELECT, SPI, END = 0x08046414, 0x08031048, 0x08046504, 0x0803107A
CHUNK = 0xAA                                        # 170 words a chunk, as the stock
MAGIC = b"DZ1\0"
WIN, WBITS = 0x2000, 13                             # 8 KB window ...
RING = 0x2000                                       # ... at ITCM 0x2000
STAGE = 0x2004EC00                                  # 512 B (510 used)
S = 0x2004EE00                                      # + 0 src, + 4 flags, + 8 match left, + 12 match index, + 16 write index
MAXL = 265
CACHE = Path(__file__).resolve().parents[1] / "build" / "dspz_cache"


# ---------------------------------------------------------------- packing (build side)
def _pack(raw: bytes) -> bytes:
    n = len(raw)
    best = [(0, 0)] * n
    heads: dict = {}
    for i in range(n):
        bl_, bo = 0, 0
        chain = heads.get(raw[i:i + 3])
        if chain and i + 3 <= n:
            for k in range(len(chain) - 1, max(-1, len(chain) - 1 - 2048), -1):
                j = chain[k]
                if i - j > WIN:
                    break
                ln = 0
                while ln < MAXL and i + ln < n and raw[j + ln] == raw[i + ln]:
                    ln += 1
                if ln > bl_:
                    bl_, bo = ln, i - j
                if ln == MAXL:
                    break
        best[i] = (bl_, bo)
        heads.setdefault(raw[i:i + 3], []).append(i)
    INF = 1 << 60
    cost = [INF] * (n + 1)
    cost[n] = 0
    pick = [0] * n                                   # 0 = literal, else the match length
    for i in range(n - 1, -1, -1):
        c, p = 9 + cost[i + 1], 0
        ln = best[i][0]
        for m in range(3, ln + 1):
            mc = (25 if m >= 10 else 17) + cost[i + m]
            if mc < c:
                c, p = mc, m
        cost[i], pick[i] = c, p
    out, flags, items, i, nf = bytearray(), 0, bytearray(), 0, 0
    while i < n:
        ln = pick[i]
        if ln == 0:
            flags |= 1 << nf
            items.append(raw[i])
            i += 1
        else:
            o = best[i][1] - 1
            code = 7 if ln >= 10 else ln - 3
            items += bytes([o & 0xFF, (o >> 8) | code << 5])
            if code == 7:
                items.append(ln - 10)
            i += ln
        nf += 1
        if nf == 8:
            out.append(flags)
            out += items
            flags, items, nf = 0, bytearray(), 0
    if nf:
        out.append(flags)
        out += items
    return bytes(out)


def unpack_stream(stream: bytes, size: int) -> bytes:
    out, i, flags = bytearray(), 0, 1
    while len(out) < size:
        if flags == 1:
            flags = stream[i] | 0x100
            i += 1
        lit = flags & 1
        flags >>= 1
        if lit:
            out.append(stream[i])
            i += 1
        else:
            t = stream[i] | stream[i + 1] << 8
            i += 2
            o, c = (t & 0x1FFF) + 1, t >> 13
            if c == 7:
                ln = 10 + stream[i]
                i += 1
            else:
                ln = c + 3
            for _ in range(ln):
                out.append(out[-o])
    assert len(out) == size
    return bytes(out)


def boundaries(stream: bytes, size: int):
    """-> [(stream index of the next read, bytes out)] after every item: where a piece may end (the unpacker reads lazily: a flag byte
    only when the next item starts)"""
    out, i, flags, bd = 0, 0, 1, []
    while out < size:
        if flags == 1:
            flags = stream[i] | 0x100
            i += 1
        lit = flags & 1
        flags >>= 1
        if lit:
            out += 1
            i += 1
        else:
            c = stream[i + 1] >> 5
            i += 2
            if c == 7:
                out += 10 + stream[i]
                i += 1
            else:
                out += c + 3
        bd.append((i, out))
    return bd


MAGIC2 = b"DZ2\0"
H_ENT, ENT = 16, 12                                 # DZ2 header: magic, words, CRC-32, pieces; then (address, words, bytes) a piece, (0, 0, 0)


def split(blob: bytes, caps):
    """a DZ1 blob's stream cut for places of caps[i] bytes (the last piece: the rest) -> [(stream bytes, words)]; each cut after an item,
    at a whole word"""
    words = struct.unpack_from("<I", blob, 4)[0]
    st = blob[12:]
    bd = [(i, o) for i, o in boundaries(st, 3 * words) if o % 3 == 0]
    out, pos, opos = [], 0, 0
    for cap in caps:
        best = (pos, opos)
        for i, o in bd:
            if i - pos > cap:
                break
            if i > pos:
                best = (i, o)
        out.append((st[pos:best[0]], (best[1] - opos) // 3))
        pos, opos = best
    out.append((st[pos:], words - opos // 3))
    assert sum(w for _, w in out) == words and b"".join(p for p, _ in out) == st
    return out


def header2(blob: bytes, places) -> bytes:
    """the DZ2 header for a blob's pieces at places [(address, (bytes, words))]"""
    words, crc = struct.unpack_from("<II", blob, 4)
    h = MAGIC2 + struct.pack("<III", words, crc, len(places))
    for at, (p, w) in places:
        h += struct.pack("<III", at, w, len(p))
    return h + bytes(ENT)


def unblob2(img, addr, base=0x08010000) -> bytes:
    """the raw stream of the DZ2 pieces whose header is at a flash address"""
    o = addr - base
    assert bytes(img[o:o + 4]) == MAGIC2
    words, crc, k = struct.unpack_from("<III", img, o + 4)
    st = b""
    for j in range(k):
        at, w, n = struct.unpack_from("<III", img, o + H_ENT + ENT * j)
        st += bytes(img[at - base:at - base + n])
    raw = unpack_stream(st, 3 * words)
    assert zlib.crc32(raw) == crc
    return raw


def pack(raw: bytes) -> bytes:
    """The whole blob (header + stream), cached by the stream's hash."""
    assert len(raw) % 3 == 0
    key = hashlib.sha256(raw).hexdigest()
    f = CACHE / f"{key}.dz"
    if f.exists():
        blob = f.read_bytes()
    else:
        blob = MAGIC + struct.pack("<II", len(raw) // 3, zlib.crc32(raw)) + _pack(raw)
        CACHE.mkdir(parents=True, exist_ok=True)
        f.write_bytes(blob)
    assert unblob(blob) == raw
    return blob


def unblob(blob: bytes) -> bytes:
    assert blob[:4] == MAGIC
    words, crc = struct.unpack_from("<II", blob, 4)
    raw = unpack_stream(blob[12:], 3 * words)
    assert zlib.crc32(raw) == crc
    return raw


def is_blob(img, addr, base=0x08010000) -> bool:
    return bytes(img[addr - base:addr - base + 4]) == MAGIC


def blob_at(img, addr, base=0x08010000) -> bytes:
    """the raw stream of the blob at a flash address (tools and tests)"""
    o = addr - base
    words = struct.unpack_from("<I", img, o + 4)[0]
    return unblob(bytes(img[o:o + 12 + 3 * words + 64]))      # (the stream is never longer than the raw words + a flag byte in 8)


# ---------------------------------------------------------------- the unpacker (ARM), into an Asm of the caller's
def emit(a, E, pieces=False):
    """c_dz(r0 = blob, r1 = core): the blob's stream sent as the stock's sender sends a block (its waits, select, chunks, end);
    dz_fill(dst, bytes) unpacks the next bytes.  pieces (RH80, OPT dzhole): c_dzp(r0 = a DZ2 header, r1 = core) instead: one stream
    in pieces at several places, each piece sent as a block of its own (its waits, select, chunks, end), the unpacker's state kept"""
    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)
    if pieces:
        emit_pieces(a, E, imm32)
    else:
        emit_one(a, E, imm32)
    emit_fill(a, E, imm32)


def emit_pieces(a, E, imm32):
    a.label("c_dzp")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 1)                                                    # r4 = core
    E(adds_imm8, 0, H_ENT)
    E(push_list, [0])                                                   # [sp] = the next piece's entry
    imm32(3, S)
    E(movs_imm, 2, 1)
    E(str_imm, 2, 3, 4)                                                 # flags: empty
    E(movs_imm, 2, 0)
    E(str_imm, 2, 3, 8)
    E(str_imm, 2, 3, 16)                                                # no match, write index 0
    a.label("dzp_pc")
    E(ldr_sp, 0, 0)
    E(ldr_imm, 6, 0, 4)                                                 # r6 = this piece's words
    E(cmp_imm, 6, 0)
    E(b_cond, "dzp_x", "eq")
    E(ldr_imm, 1, 0, 0)
    E(adds_imm8, 0, ENT)
    E(str_sp, 0, 0)
    imm32(3, S)
    E(str_imm, 1, 3, 0)                                                 # src = the piece
    E(movs_imm, 5, 0)                                                   # r5 = words sent
    E(bl, WAIT)
    E(mov_reg, 0, 4)
    E(bl, SELECT)
    a.label("dzp_lp")
    E(subs_reg, 7, 6, 5)
    E(cmp_imm, 7, CHUNK)
    E(b_cond, "dzp_k", "le")
    E(movs_imm, 7, CHUNK)
    a.label("dzp_k")
    E(adds_reg, 5, 5, 7)
    E(adds_reg, 1, 7, 7)
    E(adds_reg, 7, 1, 7)                                                # r7 = bytes of this chunk
    imm32(0, STAGE)
    E(mov_reg, 1, 7)
    E(bl, "dz_fill")
    imm32(0, STAGE)
    E(mov_reg, 1, 7)
    E(bl, SPI)
    E(bl, WAIT)
    E(cmp_reg, 5, 6)
    E(b_cond, "dzp_lp", "lt")
    E(bl, WAIT)
    E(mov_reg, 0, 4)
    E(bl, END)
    E(b, "dzp_pc")
    a.label("dzp_x")
    E(add_sp_imm, 4)
    E(pop_list, [4, 5, 6, 7], pc=True)


def emit_one(a, E, imm32):
    a.label("c_dz")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 1)                                                    # r4 = core
    imm32(3, S)
    E(adds_imm8, 0, 12)
    E(str_imm, 0, 3, 0)                                                 # src
    E(movs_imm, 2, 1)
    E(str_imm, 2, 3, 4)                                                 # flags: empty
    E(movs_imm, 2, 0)
    E(str_imm, 2, 3, 8)
    E(str_imm, 2, 3, 16)                                                # no match, write index 0
    E(subs_imm8, 0, 12)
    E(ldr_imm, 6, 0, 4)                                                 # r6 = the stream's words
    E(movs_imm, 5, 0)                                                   # r5 = words sent
    E(bl, WAIT)
    E(mov_reg, 0, 4)
    E(bl, SELECT)
    a.label("dz_lp")
    E(subs_reg, 7, 6, 5)
    E(cmp_imm, 7, CHUNK)
    E(b_cond, "dz_k", "le")
    E(movs_imm, 7, CHUNK)
    a.label("dz_k")
    E(adds_reg, 5, 5, 7)
    E(adds_reg, 1, 7, 7)
    E(adds_reg, 7, 1, 7)                                                # r7 = bytes of this chunk
    imm32(0, STAGE)
    E(mov_reg, 1, 7)
    E(bl, "dz_fill")
    imm32(0, STAGE)
    E(mov_reg, 1, 7)
    E(bl, SPI)
    E(bl, WAIT)
    E(cmp_reg, 5, 6)
    E(b_cond, "dz_lp", "lt")
    E(bl, WAIT)
    E(mov_reg, 0, 4)
    E(pop_list, [4, 5, 6, 7])
    E(pop_list, [3])                                                    # lr back through r3
    E(mov_reg, 14, 3)
    E(b_w, END)


def emit_fill(a, E, imm32):
    # ---- dz_fill(dst, bytes): r0 dst, [sp] end, r1 the ring, r2 src, r3 flags, r4 match left, r5 match index, r6 write index, r7 byte
    a.label("dz_fill")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(adds_reg, 1, 0, 1)
    E(push_list, [1])                                                   # [sp] = end
    imm32(7, S)
    E(ldr_imm, 2, 7, 0)
    E(ldr_imm, 3, 7, 4)
    E(ldr_imm, 4, 7, 8)
    E(ldr_imm, 5, 7, 12)
    E(ldr_imm, 6, 7, 16)
    E(movs_imm, 1, RING >> 8)
    E(lsls_imm, 1, 1, 8)
    a.label("df_lp")
    E(ldr_sp, 7, 0)
    E(cmp_reg, 0, 7)
    E(b_cond, "df_x", "hs")
    E(cmp_imm, 4, 0)
    E(b_cond, "df_cp", "ne")
    E(cmp_imm, 3, 1)
    E(b_cond, "df_fl", "ne")
    E(ldrb_imm, 3, 2, 0)
    E(adds_imm8, 2, 1)
    E(movs_imm, 7, 1)
    E(lsls_imm, 7, 7, 8)
    E(orrs_reg, 3, 7)
    a.label("df_fl")
    E(lsrs_imm, 3, 3, 1)
    E(b_cond, "df_m", "cc")
    E(ldrb_imm, 7, 2, 0)
    E(adds_imm8, 2, 1)
    E(b, "df_put")
    a.label("df_m")
    E(ldrb_imm, 7, 2, 0)
    E(ldrb_imm, 5, 2, 1)
    E(adds_imm8, 2, 2)
    E(lsrs_imm, 4, 5, 5)
    E(lsls_imm, 5, 5, 27)
    E(lsrs_imm, 5, 5, 19)
    E(orrs_reg, 5, 7)                                                   # r4 = length code, r5 = offset - 1
    E(cmp_imm, 4, 7)
    E(b_cond, "df_s", "ne")
    E(ldrb_imm, 7, 2, 0)
    E(adds_imm8, 2, 1)
    E(adds_reg, 4, 4, 7)                                                # 7 + extra (+ 3 below = 10 + extra)
    a.label("df_s")
    E(adds_imm8, 4, 3)
    E(subs_reg, 5, 6, 5)
    E(subs_imm8, 5, 1)
    E(lsls_imm, 5, 5, 32 - WBITS)
    E(lsrs_imm, 5, 5, 32 - WBITS)
    a.label("df_cp")
    E(ldrb_reg, 7, 1, 5)
    E(adds_imm8, 5, 1)
    E(lsls_imm, 5, 5, 32 - WBITS)
    E(lsrs_imm, 5, 5, 32 - WBITS)
    E(subs_imm8, 4, 1)
    a.label("df_put")
    E(strb_reg, 7, 1, 6)
    E(adds_imm8, 6, 1)
    E(lsls_imm, 6, 6, 32 - WBITS)
    E(lsrs_imm, 6, 6, 32 - WBITS)
    E(strb_imm, 7, 0, 0)
    E(adds_imm8, 0, 1)
    E(b, "df_lp")
    a.label("df_x")
    imm32(7, S)
    E(str_imm, 2, 7, 0)
    E(str_imm, 3, 7, 4)
    E(str_imm, 4, 7, 8)
    E(str_imm, 5, 7, 12)
    E(str_imm, 6, 7, 16)
    E(add_sp_imm, 4)
    E(pop_list, [4, 5, 6, 7], pc=True)


def check_ram(report):
    import rhbuild
    assert not rhbuild.OPT.get("modhost"), "dspz: its staging buffer is modhost's third RAM block, its window modhost's ITCM"
    assert "bootrec" not in report, "dspz: its staging buffer is in bootrec's log"
