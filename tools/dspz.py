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
                   subs_imm8, subs_reg, muls, ldrh_imm, strh_imm, bics_reg, ands_reg, lsls_reg, bx_lr, subs_imm3, adds_imm3)

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
    """the DZ2 header for a blob's pieces at places [(address, (bytes, words))] (RH95: a range-coded blob = RC_FLAG on the count)"""
    words, crc = struct.unpack_from("<II", blob, 4)
    h = MAGIC2 + struct.pack("<III", words, crc, len(places) | (RC_FLAG if blob[:4] == RC_MAGIC else 0))
    for at, (p, w) in places:
        h += struct.pack("<III", at, w, len(p))
    return h + bytes(ENT)


def unblob2(img, addr, base=0x08010000) -> bytes:
    """the raw stream of the DZ2 pieces whose header is at a flash address"""
    o = addr - base
    assert bytes(img[o:o + 4]) == MAGIC2
    words, crc, k = struct.unpack_from("<III", img, o + 4)
    rc = bool(k & RC_FLAG)
    st = b""
    for j in range(k & ~RC_FLAG):
        at, w, n = struct.unpack_from("<III", img, o + H_ENT + ENT * j)
        st += bytes(img[at - base:at - base + n])
    raw = (unpack_stream2 if rc else unpack_stream)(st, 3 * words)
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


# ================================================================ the range coder (RH95, OPT dzrc): CIRCUIT-HACKS' SC56 "DZ2" coder (our code, MIT)
# The user (2026-11-13): free the ITCM for the automation lanes; the flash for its tables comes from here (RH94's DSP blocks 72 994 -> ~52 000 B).
# LZ + adaptive binary range coding (LZMA's model with fewer parts: lc = lp = pb = 0, rep0 only, short rep, matched literals), the window 4 KB
# (ITCM RING_RC..+0xFFF) and the 1 738 probabilities (11 bits, in halfwords) at ITCM PROBS: both only while a block is sent.  The stream starts
# with the decoder's first four code bytes.  The encoder is integer only and deterministic (the installer's JavaScript gives the same bytes).
# In Remix the stream goes in the DZ2 piece header (the same layout as the LZSS pieces), its piece count with RC_FLAG: the pieces are cut
# anywhere (bytes), the sender sends all the words as one block, the byte reader walks the pieces.
WIN_RC = 0x1000
RING_RC = 0x3000
PROBS = 0x2000
MAXL_RC = 273
RC_MAGIC = b"DZR\0"
RC_FLAG = 0x80000000
S_RC = 0x2DA0                                       # (ITCM, after the probabilities) + 0 src, + 4 range, + 8 code, + 12 state, + 16 rep0,
                                                    # + 20 left, + 24 write index, + 28 the piece's end, + 32 the next entry, + 36 uploads
PBITS, PMOVE, PONE, PTOP = 11, 5, 1 << 11, 1 << 24
# probability indices: literals first (the literal loop adds nothing)
LIT, ISM, ISR, ISR0L = 0, 0x300, 0x30C, 0x318
MLEN, RLEN = 0x324, 0x324 + 274
SLOT = RLEN + 274
SPEC = SLOT + 256
ALIGN = SPEC + 114
NPROB = ALIGN + 16
NEXT_LIT = (0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 4, 5)


def _prices():
    P = []
    for i in range(PONE >> 4):
        w, bc = (i << 4) + 8, 0
        for _ in range(4):
            w = w * w; bc <<= 1
            while w >= 1 << 16: w >>= 1; bc += 1
        P.append((PBITS << 4) - 15 - bc)
    return P


_PT = _prices()


def _slot(d):
    if d < 4: return d
    n = d.bit_length() - 1
    return 2 * n + ((d >> (n - 1)) & 1)


def _lit_bits(byte, st, mbyte):
    """(index, bit) of a literal; matched (st >= 7) as LZMA's: offs = 0x100 while the bits agree with the match byte's."""
    offs = 0x100 if st >= 7 else 0
    m, sym, out = mbyte, 1, []
    for k in range(7, -1, -1):
        m <<= 1; bit = m & offs; b = (byte >> k) & 1
        out.append((LIT + offs + bit + sym, b))
        sym = sym << 1 | b
        offs = offs & bit if b else offs & ~bit
    return out


def _len_bits(o, l):
    l -= 2
    if l < 8: out, sub, nb, base = [(o, 0)], l, 3, o + 2
    elif l < 16: out, sub, nb, base = [(o, 1), (o + 1, 0)], l - 8, 3, o + 10
    else: out, sub, nb, base = [(o, 1), (o + 1, 1)], l - 16, 8, o + 18
    m = 1
    for j in range(nb - 1, -1, -1):
        b = (sub >> j) & 1; out.append((base + m, b)); m = m << 1 | b
    return out


def _dist_bits(l, d):
    """(index, bit) and ('D', value, n) for the direct bits."""
    sl, out, m = _slot(d), [], 1
    base = SLOT + 64 * min(l - 2, 3)
    for j in range(5, -1, -1):
        b = (sl >> j) & 1; out.append((base + m, b)); m = m << 1 | b
    if sl >= 4:
        nd = (sl >> 1) - 1; bse = (2 | (sl & 1)) << nd; rem = d - bse
        if sl < 14:
            o, m = SPEC + bse - sl - 1, 1
            for j in range(nd):
                b = (rem >> j) & 1; out.append((o + m, b)); m = m << 1 | b
        else:
            out.append(("D", rem >> 4, nd - 4)); m = 1
            for j in range(4):
                b = (rem >> j) & 1; out.append((ALIGN + m, b)); m = m << 1 | b
    return out


class _Enc:
    def __init__(s):
        s.low, s.rng, s.cache, s.csize, s.out = 0, 0xFFFFFFFF, 0, 1, bytearray()

    def _shift(s):
        if s.low < 0xFF000000 or s.low >= 1 << 32:
            c, t = s.low >> 32, s.cache
            while True:
                s.out.append((t + c) & 0xFF); t = 0xFF; s.csize -= 1
                if s.csize == 0: break
            s.cache = (s.low >> 24) & 0xFF
        s.csize += 1
        s.low = (s.low & 0x00FFFFFF) << 8

    def bits(s, P, seq):
        for t in seq:
            if t[0] == "D":
                v, n = t[1], t[2]
                for k in range(n - 1, -1, -1):
                    s.rng >>= 1
                    if (v >> k) & 1: s.low += s.rng
                    if s.rng < PTOP: s.rng = (s.rng << 8) & 0xFFFFFFFF; s._shift()
                continue
            i, b = t
            p = P[i]; bound = (s.rng >> PBITS) * p
            if b == 0: s.rng = bound; P[i] = p + ((PONE - p) >> PMOVE)
            else: s.low += bound; s.rng -= bound; P[i] = p - (p >> PMOVE)
            if s.rng < PTOP: s.rng = (s.rng << 8) & 0xFFFFFFFF; s._shift()

    def flush(s):
        for _ in range(5): s._shift()
        assert s.out[0] == 0
        return bytes(s.out[1:])


def _matches(raw):
    """At every position the (length, distance - 1) pairs of growing length, nearest first, inside the window."""
    n, heads, res = len(raw), {}, []
    for i in range(n):
        out = []
        if i + 2 <= n:
            key = raw[i] << 8 | raw[i + 1]
            ch = heads.get(key)
            if ch:
                bl_ = 1
                for k in range(len(ch) - 1, -1, -1):
                    j = ch[k]
                    if i - j > WIN_RC: break
                    l = 0
                    while l < MAXL_RC and i + l < n and raw[j + l] == raw[i + l]: l += 1
                    if l > bl_: bl_ = l; out.append((l, i - j - 1))
                    if l == MAXL_RC: break
                ch.append(i)
            else:
                heads[key] = [i]
        res.append(out)
    return res


def _pack2(raw: bytes) -> bytes:
    n = len(raw)
    cand = _matches(raw)
    P = [PONE // 2] * NPROB
    INF = 1 << 60
    for ps in range(2):
        Q = list(P) if ps else [PONE // 2] * NPROB                         # the prices of this pass (pass 0: every bit 1)
        def price(seq):
            c = 0
            for t in seq:
                if t[0] == "D": c += 16 * t[2]
                else: c += _PT[(Q[t[0]] if t[1] == 0 else PONE - Q[t[0]]) >> 4]
            return c
        def bp(i, b): return _PT[(Q[i] if b == 0 else PONE - Q[i]) >> 4]
        cost = [INF] * (n + 1); cost[0] = 0
        stt, rep, back = [0] * (n + 1), [0] * (n + 1), [None] * (n + 1)
        for i in range(n):
            c0 = cost[i]
            st, r0 = stt[i], rep[i]
            mb = raw[i - r0 - 1] if i - r0 - 1 >= 0 else 0
            pc = c0 + bp(ISM + st, 0) + price(_lit_bits(raw[i], st, mb))
            if pc < cost[i + 1]: cost[i + 1], stt[i + 1], rep[i + 1], back[i + 1] = pc, NEXT_LIT[st], r0, (i, 0, 1)
            if i > r0:
                lr, j = 0, i - r0 - 1
                while lr < MAXL_RC and i + lr < n and raw[j + lr] == raw[i + lr]: lr += 1
                if lr:
                    base = c0 + bp(ISM + st, 1) + bp(ISR + st, 1)
                    pc = base + bp(ISR0L + st, 0)
                    if pc < cost[i + 1]: cost[i + 1], stt[i + 1], rep[i + 1], back[i + 1] = pc, (9 if st < 7 else 11), r0, (i, 1, 1)
                    b2 = base + bp(ISR0L + st, 1)
                    for l in range(2, lr + 1):
                        pc = b2 + price(_len_bits(RLEN, l))
                        if pc < cost[i + l]: cost[i + l], stt[i + l], rep[i + l], back[i + l] = pc, (8 if st < 7 else 11), r0, (i, 2, l)
            base = c0 + bp(ISM + st, 1) + bp(ISR + st, 0)
            prevl = 1
            for l, d in cand[i]:
                for ll in range(max(2, prevl + 1), l + 1):
                    pc = base + price(_len_bits(MLEN, ll)) + price(_dist_bits(ll, d))
                    if pc < cost[i + ll]: cost[i + ll], stt[i + ll], rep[i + ll], back[i + ll] = pc, (7 if st < 7 else 10), d, (i, 3, ll)
                prevl = l
        ops, i = [], n
        while i > 0:
            b_ = back[i]; ops.append((b_[0], b_[1], b_[2], rep[i])); i = b_[0]
        ops.reverse()
        E, P, st, r0 = _Enc(), [PONE // 2] * NPROB, 0, 0
        for i, k, l, d in ops:
            if k == 0:
                mb = raw[i - r0 - 1] if i - r0 - 1 >= 0 else 0
                E.bits(P, [(ISM + st, 0)] + _lit_bits(raw[i], st, mb)); st = NEXT_LIT[st]
            elif k == 1:
                E.bits(P, [(ISM + st, 1), (ISR + st, 1), (ISR0L + st, 0)]); st = 9 if st < 7 else 11
            elif k == 2:
                E.bits(P, [(ISM + st, 1), (ISR + st, 1), (ISR0L + st, 1)] + _len_bits(RLEN, l)); st = 8 if st < 7 else 11
            else:
                E.bits(P, [(ISM + st, 1), (ISR + st, 0)] + _len_bits(MLEN, l) + _dist_bits(l, d)); st = 7 if st < 7 else 10; r0 = d
        out = E.flush()
    return out


def unpack_stream2(data: bytes, size: int) -> bytes:
    """The decoder as the ARM one (bytes past the stream read as 0xFF)."""
    pos = [4]
    def nb():
        b_ = data[pos[0]] if pos[0] < len(data) else 0xFF; pos[0] += 1; return b_
    code, rng = int.from_bytes(data[:4], "big"), 0xFFFFFFFF
    P = [PONE // 2] * NPROB
    def bit(i):
        nonlocal code, rng
        p = P[i]; bound = (rng >> PBITS) * p
        if code < bound: rng = bound; P[i] = p + ((PONE - p) >> PMOVE); b_ = 0
        else: code -= bound; rng -= bound; P[i] = p - (p >> PMOVE); b_ = 1
        if rng < PTOP: rng = (rng << 8) & 0xFFFFFFFF; code = ((code << 8) | nb()) & 0xFFFFFFFF
        return b_
    def direct(n):
        nonlocal code, rng
        v = 0
        for _ in range(n):
            rng >>= 1; v <<= 1
            if code >= rng: code -= rng; v |= 1
            if rng < PTOP: rng = (rng << 8) & 0xFFFFFFFF; code = ((code << 8) | nb()) & 0xFFFFFFFF
        return v
    def tr(base, n):
        m, v = 1, 0
        for j in range(n):
            b_ = bit(base + m); m = m << 1 | b_; v |= b_ << j
        return v, m - (1 << n)
    def dlen(o):
        if not bit(o): return 2 + tr(o + 2, 3)[1]
        if not bit(o + 1): return 10 + tr(o + 10, 3)[1]
        return 18 + tr(o + 18, 8)[1]
    out, st, r0 = bytearray(), 0, 0
    while len(out) < size:
        if not bit(ISM + st):
            offs, m, sym = (0x100, out[-r0 - 1], 1) if st >= 7 else (0, 0, 1)
            while sym < 0x100:
                m <<= 1; b0 = m & offs
                b_ = bit(LIT + offs + b0 + sym); sym = sym << 1 | b_
                offs = offs & b0 if b_ else offs & ~b0
            out.append(sym & 0xFF); st = NEXT_LIT[st]; continue
        if bit(ISR + st):
            if not bit(ISR0L + st): l, st = 1, (9 if st < 7 else 11)
            else: l, st = dlen(RLEN), (8 if st < 7 else 11)
        else:
            l = dlen(MLEN); st = 7 if st < 7 else 10
            sl = tr(SLOT + 64 * min(l - 2, 3), 6)[1]
            if sl < 4: r0 = sl
            else:
                nd = (sl >> 1) - 1; d = (2 | (sl & 1)) << nd
                if sl < 14: d += tr(SPEC + d - sl - 1, nd)[0]
                else: d += direct(nd - 4) << 4; d += tr(ALIGN, 4)[0]
                r0 = d
        for _ in range(l): out.append(out[-r0 - 1])
    return bytes(out[:size])


def pack_rc(raw: bytes) -> bytes:
    """(RH95) the range-coded blob: 'DZR\0', words, CRC-32, the stream; cached by the raw words' hash"""
    assert len(raw) % 3 == 0
    key = hashlib.sha256(raw).hexdigest()
    f = CACHE / f"{key}.dzr"
    if f.exists():
        blob = f.read_bytes()
    else:
        blob = RC_MAGIC + struct.pack("<II", len(raw) // 3, zlib.crc32(raw)) + _pack2(raw)
        CACHE.mkdir(parents=True, exist_ok=True)
        f.write_bytes(blob)
    assert unblob_rc(blob) == raw
    return blob


def unblob_rc(blob: bytes) -> bytes:
    assert blob[:4] == RC_MAGIC
    words, crc = struct.unpack_from("<II", blob, 4)
    raw = unpack_stream2(blob[12:], 3 * words)
    assert zlib.crc32(raw) == crc
    return raw


def split_rc(blob: bytes, caps):
    """a range-coded blob's stream cut for places of caps[i] bytes (anywhere: the reader walks the pieces), the last piece the rest
    -> [(stream bytes, 0)]"""
    st, out, pos = blob[12:], [], 0
    for cap in caps:
        n = max(0, min(cap, len(st) - pos))
        out.append((st[pos:pos + n], 0))
        pos += n
    out.append((st[pos:], 0))
    assert b"".join(p for p, _ in out) == st
    return out


# ---------------------------------------------------------------- the unpacker (ARM), into an Asm of the caller's
def emit(a, E, pieces=False):
    """c_dz(r0 = blob, r1 = core): the blob's stream sent as the stock's sender sends a block (its waits, select, chunks, end);
    dz_fill(dst, bytes) unpacks the next bytes.  pieces (RH80, OPT dzhole): c_dzp(r0 = a DZ2 header, r1 = core) instead: one stream
    in pieces at several places, each piece sent as a block of its own (its waits, select, chunks, end), the unpacker's state kept"""
    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, (v >> 16) & 0xFFFF)
    import rhbuild
    if pieces and rhbuild.OPT.get("dzrc", False):                       # (RH95) the range coder
        emit_range(a, E, imm32)
        return
    if pieces:
        emit_pieces(a, E, imm32)
    else:
        emit_one(a, E, imm32)
    emit_fill(a, E, imm32)


def emit_range(a, E, imm32):
    """(RH95, OPT dzrc) c_dzp(r0 = a DZ2 header with RC_FLAG, r1 = core): every word of the stream sent as one block (the stock's waits, select,
    chunks of 0xAA words, end), unpacked by CIRCUIT-HACKS' range decoder (arm_code2 there) into the staging buffer; the bytes read from the
    header's pieces in turn (dz_nb).  r4 range, r5 code, r6 src, r7 = S_RC in dz_fill."""
    def ring(rd):
        E(movs_imm, rd, RING_RC >> 8)
        E(lsls_imm, rd, rd, 8)
    a.label("c_dzp")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(mov_reg, 4, 1)                                                    # r4 = core
    E(movs_imm, 2, PROBS >> 8); E(lsls_imm, 2, 2, 8); E(movw, 3, NPROB); E(movs_imm, 1, 1); E(lsls_imm, 1, 1, 10)
    a.label("dz_ip")
    E(strh_imm, 1, 2, 0); E(adds_imm8, 2, 2); E(subs_imm8, 3, 1); E(b_cond, "dz_ip", "ne")   # every probability 1/2
    imm32(3, S_RC)
    E(ldr_imm, 1, 3, 36); E(adds_imm8, 1, 1); E(str_imm, 1, 3, 36)       # uploads + 1 (RH96: the lanes in the window see it)
    E(movs_imm, 2, 0); E(str_imm, 2, 3, 28)                             # the piece's end = src = 0: the first read takes piece 1
    E(mov_reg, 1, 0); E(adds_imm8, 1, H_ENT); E(str_imm, 1, 3, 32)
    E(push_list, [0])
    E(movs_imm, 6, 0); E(movs_imm, 5, 0)
    for _ in range(4):                                                  # code = the stream's first four bytes, big-endian
        E(bl, "dz_nb"); E(lsls_imm, 5, 5, 8); E(orrs_reg, 5, 2)
    imm32(3, S_RC)
    E(str_imm, 6, 3, 0); E(str_imm, 5, 3, 8)
    E(movs_imm, 2, 0); E(str_imm, 2, 3, 12); E(str_imm, 2, 3, 16); E(str_imm, 2, 3, 20); E(str_imm, 2, 3, 24)   # st, rep0, left, write index
    E(subs_imm8, 2, 1); E(str_imm, 2, 3, 4)                             # range
    E(pop_list, [0])
    E(ldr_imm, 6, 0, 4)                                                 # r6 = the stream's words
    E(movs_imm, 5, 0)                                                   # r5 = words sent
    E(bl, WAIT)
    E(mov_reg, 0, 4); E(bl, SELECT)
    a.label("dz_lp")
    E(subs_reg, 7, 6, 5); E(cmp_imm, 7, CHUNK); E(b_cond, "dz_k", "le"); E(movs_imm, 7, CHUNK)
    a.label("dz_k")
    E(adds_reg, 5, 5, 7)
    E(adds_reg, 1, 7, 7); E(adds_reg, 7, 1, 7)                          # r7 = bytes of this chunk
    imm32(0, STAGE); E(mov_reg, 1, 7); E(bl, "dz_fill")
    imm32(0, STAGE); E(mov_reg, 1, 7); E(bl, SPI)
    E(bl, WAIT)
    E(cmp_reg, 5, 6); E(b_cond, "dz_lp", "lt")
    E(bl, WAIT)
    E(mov_reg, 0, 4); E(bl, END)
    E(pop_list, [4, 5, 6, 7], pc=True)
    # ---- dz_nb: r2 = the next byte of the pieces (r6 = src); r3 used, r0 / r1 kept
    a.label("dz_nb")
    imm32(3, S_RC); E(ldr_imm, 3, 3, 28)
    E(cmp_reg, 6, 3); E(b_cond, "nb_rd", "ne")
    E(push_list, [0, 1])
    imm32(3, S_RC); E(ldr_imm, 0, 3, 32)
    E(ldr_imm, 6, 0, 0); E(ldr_imm, 1, 0, 8); E(adds_reg, 1, 6, 1); E(str_imm, 1, 3, 28)
    E(adds_imm8, 0, ENT); E(str_imm, 0, 3, 32)
    E(pop_list, [0, 1])
    E(b, "dz_nb")                                                       # (a piece of 0 bytes: the next)
    a.label("nb_rd")
    E(ldrb_imm, 2, 6, 0); E(adds_imm8, 6, 1)
    E(bx_lr)
    # ---- dz_fill(dst, bytes): [sp] dst, [sp + 4] end
    a.label("dz_fill")
    E(push_list, [4, 5, 6, 7], lr=True)
    E(adds_reg, 1, 0, 1); E(push_list, [0, 1])
    imm32(7, S_RC); E(ldr_imm, 6, 7, 0); E(ldr_imm, 4, 7, 4); E(ldr_imm, 5, 7, 8)
    a.label("df_lp")
    E(ldr_sp, 0, 0); E(ldr_sp, 1, 4); E(cmp_reg, 0, 1); E(b_cond, "df_x", "hs")
    E(ldr_imm, 0, 7, 20); E(cmp_imm, 0, 0); E(b_cond, "df_cp", "ne")
    E(bl, "dz_sym")
    E(lsrs_imm, 1, 0, 8); E(b_cond, "df_put", "eq")                     # a literal: r0 = the byte
    a.label("df_cp")
    E(ldr_imm, 1, 7, 20); E(subs_imm8, 1, 1); E(str_imm, 1, 7, 20)      # left - 1
    E(ldr_imm, 1, 7, 24); E(ldr_imm, 2, 7, 16); E(subs_reg, 1, 1, 2); E(subs_imm8, 1, 1); E(lsls_imm, 1, 1, 20); E(lsrs_imm, 1, 1, 20)
    ring(2); E(ldrb_reg, 0, 2, 1)
    a.label("df_put")
    E(ldr_imm, 1, 7, 24); ring(2); E(strb_reg, 0, 2, 1); E(adds_imm8, 1, 1); E(lsls_imm, 1, 1, 20); E(lsrs_imm, 1, 1, 20); E(str_imm, 1, 7, 24)
    E(ldr_sp, 1, 0); E(strb_imm, 0, 1, 0); E(adds_imm8, 1, 1); E(str_sp, 1, 0)
    E(b, "df_lp")
    a.label("df_x")
    E(str_imm, 6, 7, 0); E(str_imm, 4, 7, 4); E(str_imm, 5, 7, 8)
    E(add_sp_imm, 8); E(pop_list, [4, 5, 6, 7], pc=True)
    # ---- dz_rb(r0 = byte offset of the probability) -> r0 = the bit; r1-r3 used
    a.label("dz_rb")
    E(push_list, [], lr=True)
    E(movs_imm, 3, PROBS >> 8); E(lsls_imm, 3, 3, 8); E(adds_reg, 3, 3, 0)
    E(ldrh_imm, 1, 3, 0); E(lsrs_imm, 2, 4, PBITS); E(muls, 2, 1)       # bound = (range >> 11) * p
    E(cmp_reg, 5, 2); E(b_cond, "rb_1", "hs")
    E(mov_reg, 4, 2)
    E(movs_imm, 2, 1); E(lsls_imm, 2, 2, PBITS); E(subs_reg, 2, 2, 1); E(lsrs_imm, 2, 2, PMOVE); E(adds_reg, 1, 1, 2); E(strh_imm, 1, 3, 0)
    E(movs_imm, 0, 0); E(b, "rb_n")
    a.label("rb_1")
    E(subs_reg, 5, 5, 2); E(subs_reg, 4, 4, 2)
    E(lsrs_imm, 2, 1, PMOVE); E(subs_reg, 1, 1, 2); E(strh_imm, 1, 3, 0)
    E(movs_imm, 0, 1)
    a.label("rb_n")
    E(lsrs_imm, 2, 4, 24); E(b_cond, "rb_x", "ne")
    E(lsls_imm, 4, 4, 8); E(lsls_imm, 5, 5, 8); E(bl, "dz_nb"); E(orrs_reg, 5, 2)
    a.label("rb_x")
    E(pop_list, [], pc=True)
    # ---- dz_tr(r0 = byte offset of the tree, r1 = bits) -> r0 = the value read LSB first, r1 = MSB first; r7 kept
    a.label("dz_tr")
    E(movs_imm, 2, 0); E(movs_imm, 3, 1); E(push_list, [0, 1, 2, 3, 7], lr=True); E(movs_imm, 7, 1)
    a.label("tr_l")
    E(ldr_sp, 0, 0); E(adds_reg, 0, 0, 7); E(adds_reg, 0, 0, 7); E(bl, "dz_rb")
    E(lsls_imm, 7, 7, 1); E(orrs_reg, 7, 0)
    E(ldr_sp, 3, 12); E(cmp_imm, 0, 0); E(b_cond, "tr_z", "eq")
    E(ldr_sp, 2, 8); E(orrs_reg, 2, 3); E(str_sp, 2, 8)
    a.label("tr_z")
    E(lsls_imm, 3, 3, 1); E(str_sp, 3, 12)
    E(ldr_sp, 1, 4); E(subs_imm8, 1, 1); E(str_sp, 1, 4); E(b_cond, "tr_l", "ne")
    E(subs_reg, 1, 7, 3); E(ldr_sp, 0, 8)
    E(add_sp_imm, 16); E(pop_list, [7], pc=True)
    # ---- dz_len(r0 = byte offset of the length coder) -> r0 = length
    a.label("dz_len")
    E(push_list, [7], lr=True); E(mov_reg, 7, 0); E(bl, "dz_rb"); E(cmp_imm, 0, 0); E(b_cond, "dl_1", "ne")
    E(adds_imm3, 0, 7, 4); E(movs_imm, 7, 2); E(movs_imm, 1, 3); E(b, "dl_t")
    a.label("dl_1")
    E(adds_imm3, 0, 7, 2); E(bl, "dz_rb"); E(cmp_imm, 0, 0); E(b_cond, "dl_2", "ne")
    E(mov_reg, 0, 7); E(adds_imm8, 0, 20); E(movs_imm, 7, 10); E(movs_imm, 1, 3); E(b, "dl_t")
    a.label("dl_2")
    E(mov_reg, 0, 7); E(adds_imm8, 0, 36); E(movs_imm, 7, 18); E(movs_imm, 1, 8)
    a.label("dl_t")
    E(bl, "dz_tr"); E(adds_reg, 0, 1, 7); E(pop_list, [7], pc=True)
    # ---- dz_sym: one item -> r0 = a literal byte, or 0x100 with left / rep0 set; the state updated
    a.label("dz_sym")
    E(push_list, [], lr=True)
    E(ldr_imm, 0, 7, 12); E(lsls_imm, 0, 0, 1); E(movw, 1, 2 * ISM); E(adds_reg, 0, 0, 1); E(bl, "dz_rb")
    E(cmp_imm, 0, 0); E(b_cond, "sy_m", "ne")
    E(ldr_imm, 1, 7, 12); E(movs_imm, 2, 0); E(movs_imm, 3, 0)          # m = 0, offs = 0
    E(cmp_imm, 1, 7); E(b_cond, "sy_l", "lo")
    E(ldr_imm, 0, 7, 24); E(ldr_imm, 2, 7, 16); E(subs_reg, 0, 0, 2); E(subs_imm8, 0, 1); E(lsls_imm, 0, 0, 20); E(lsrs_imm, 0, 0, 20)
    ring(2); E(ldrb_reg, 2, 2, 0)                                       # m = the match byte
    E(movs_imm, 3, 1); E(lsls_imm, 3, 3, 8)                             # offs = 0x100
    a.label("sy_l")
    E(movs_imm, 0, 1); E(push_list, [0, 1, 2, 3])                       # [sp] sym, [sp + 4] bit, [sp + 8] m, [sp + 12] offs
    a.label("sy_ll")
    E(ldr_sp, 1, 8); E(lsls_imm, 1, 1, 1); E(str_sp, 1, 8)
    E(ldr_sp, 2, 12); E(ands_reg, 1, 2); E(str_sp, 1, 4)
    E(adds_reg, 0, 2, 1); E(ldr_sp, 3, 0); E(adds_reg, 0, 0, 3); E(lsls_imm, 0, 0, 1)
    E(bl, "dz_rb")
    E(ldr_sp, 3, 0); E(lsls_imm, 3, 3, 1); E(orrs_reg, 3, 0); E(str_sp, 3, 0)
    E(ldr_sp, 1, 4); E(ldr_sp, 2, 12)
    E(cmp_imm, 0, 0); E(b_cond, "sy_0", "eq")
    E(ands_reg, 2, 1); E(b, "sy_1")
    a.label("sy_0")
    E(bics_reg, 2, 1)
    a.label("sy_1")
    E(str_sp, 2, 12)
    E(lsrs_imm, 3, 3, 8); E(b_cond, "sy_ll", "eq")
    E(ldr_sp, 0, 0); E(lsls_imm, 0, 0, 24); E(lsrs_imm, 0, 0, 24)
    E(add_sp_imm, 16)
    E(ldr_imm, 1, 7, 12); E(cmp_imm, 1, 4); E(b_cond, "sy_s0", "lo")
    E(subs_imm8, 1, 3); E(cmp_imm, 1, 7); E(b_cond, "sy_s1", "lo"); E(subs_imm8, 1, 3); E(b, "sy_s1")
    a.label("sy_s0")
    E(movs_imm, 1, 0)
    a.label("sy_s1")
    E(str_imm, 1, 7, 12)
    E(pop_list, [], pc=True)
    a.label("sy_m")
    E(ldr_imm, 0, 7, 12); E(lsls_imm, 0, 0, 1); E(movw, 1, 2 * ISR); E(adds_reg, 0, 0, 1); E(bl, "dz_rb")
    E(cmp_imm, 0, 0); E(b_cond, "sy_n", "eq")
    E(ldr_imm, 0, 7, 12); E(lsls_imm, 0, 0, 1); E(movw, 1, 2 * ISR0L); E(adds_reg, 0, 0, 1); E(bl, "dz_rb")
    E(cmp_imm, 0, 0); E(b_cond, "sy_r", "ne")
    E(movs_imm, 0, 1); E(movs_imm, 1, 9); E(b, "sy_st")                 # short rep: one byte at rep0
    a.label("sy_r")
    E(movw, 0, 2 * RLEN); E(bl, "dz_len"); E(movs_imm, 1, 8); E(b, "sy_st")
    a.label("sy_n")
    E(movw, 0, 2 * MLEN); E(bl, "dz_len"); E(str_imm, 0, 7, 20)
    E(subs_imm8, 0, 2); E(cmp_imm, 0, 3); E(b_cond, "sy_k", "ls"); E(movs_imm, 0, 3)
    a.label("sy_k")
    E(lsls_imm, 0, 0, 7); E(movw, 1, 2 * SLOT); E(adds_reg, 0, 0, 1); E(movs_imm, 1, 6); E(bl, "dz_tr")   # r1 = the slot
    E(cmp_imm, 1, 4); E(b_cond, "sy_d", "lo")
    E(lsrs_imm, 2, 1, 1); E(subs_imm8, 2, 1)                            # r2 = bits
    E(movs_imm, 3, 1); E(ands_reg, 3, 1); E(adds_imm8, 3, 2); E(lsls_reg, 3, 2)   # r3 = base
    E(push_list, [3])
    E(cmp_imm, 1, 14); E(b_cond, "sy_dd", "hs")
    E(subs_reg, 0, 3, 1); E(subs_imm8, 0, 1); E(lsls_imm, 0, 0, 1); E(movw, 3, 2 * SPEC); E(adds_reg, 0, 0, 3); E(mov_reg, 1, 2)
    E(bl, "dz_tr"); E(b, "sy_da")
    a.label("sy_dd")
    E(subs_imm3, 1, 2, 4); E(bl, "dz_dir"); E(lsls_imm, 0, 0, 4)
    E(ldr_sp, 3, 0); E(adds_reg, 3, 3, 0); E(str_sp, 3, 0)
    E(movw, 0, 2 * ALIGN); E(movs_imm, 1, 4); E(bl, "dz_tr")
    a.label("sy_da")
    E(pop_list, [3]); E(adds_reg, 1, 0, 3)
    a.label("sy_d")
    E(str_imm, 1, 7, 16)                                                # rep0
    E(ldr_imm, 0, 7, 20); E(movs_imm, 1, 7)
    a.label("sy_st")                                                    # r0 = length, r1 = the next state after a state < 7
    E(str_imm, 0, 7, 20)
    E(ldr_imm, 2, 7, 12); E(cmp_imm, 2, 7); E(b_cond, "st_a", "hs")
    E(mov_reg, 2, 1); E(b, "st_b")
    a.label("st_a")
    E(movs_imm, 2, 11); E(cmp_imm, 1, 7); E(b_cond, "st_b", "ne"); E(movs_imm, 2, 10)
    a.label("st_b")
    E(str_imm, 2, 7, 12)
    E(movs_imm, 0, 1); E(lsls_imm, 0, 0, 8)
    E(pop_list, [], pc=True)
    # ---- dz_dir(r1 = bits) -> r0: the range coder's direct bits
    a.label("dz_dir")
    E(push_list, [], lr=True)
    E(movs_imm, 0, 0)
    a.label("dr_l")
    E(lsrs_imm, 4, 4, 1); E(lsls_imm, 0, 0, 1); E(cmp_reg, 5, 4); E(b_cond, "dr_n", "lo"); E(subs_reg, 5, 5, 4); E(adds_imm8, 0, 1)
    a.label("dr_n")
    E(lsrs_imm, 2, 4, 24); E(b_cond, "dr_c", "ne")
    E(lsls_imm, 4, 4, 8); E(lsls_imm, 5, 5, 8); E(bl, "dz_nb"); E(orrs_reg, 5, 2)
    a.label("dr_c")
    E(subs_imm8, 1, 1); E(b_cond, "dr_l", "ne")
    E(pop_list, [], pc=True)


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
