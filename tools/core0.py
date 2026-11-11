"""Code of ours in the Circuit Rhythm 5706's DSP core 0 (MIT): a second-stage loader, so our code can live in core 0's never-loaded
P:$1FED..$3FFF without copying its program (docs/RECURSOS.md, route 1), and RD20's probe of it (docs/PRUEBA_RD20.md).

The stock (0x08031110(mode), read in the firmware): the ARM sends core 0 the 8-word stub 0x08031638 (the DSP's bootstrap loads it at P:$0:
it sets OMR bits 7 / 22, clears 21 (16K words of P, the Tracks' stub) and jumps back into the bootstrap), then core 1's loader, then (the bl
at 0x0803115E) core 0's block 0x08031658[mode] by SEND = 0x080310B0(block, core): its two header words (count, load address) and its
words (count = bytes 1-2 of the first word).  The bootstrap loads that one block (mode 0: 0x1FED words at P:$0) and jumps to its address:
nothing after P:$1FEC is ever loaded.  Both cores take host words on the SHI (HCSR X:$FFFF91 bit 17 = a word waits, HRX X:$FFFF94).
Ours (`loader`): the bl at 0x0803115E -> c_d0up: for the mode 0 block, SEND our loader as a bootstrap block [n, LD, n words] (the bootstrap
loads it at P:LD and jumps there), then the stock block from its own place, unchanged ([0x1FED, 0, words]: to our loader a P segment like
any other), then our segments [count, address, words], then the end [0, 0] (count 0 = jump to the address: the stock's P:$0, jmp $100).
Any other block: the stock's SEND alone.
RD20's probe (`counter`, in place in the stock block, which the bootstrap or our loader loads anyway): P:$126 `jscs $1AE` (main loop, the C
of P:$125 `bclr #21,x:$12`) -> `jsr VEC`; at P:VEC (the unused vectors, all `nop` in the stock): the stock's jscs, the pass counter
Y:Y_PASS + 1, then `jseq SEG + 1` if P:SEG holds MAGIC (only when our loader has loaded the test segment, which counts in Y:Y_SEG).
"""
from __future__ import annotations

import struct
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rhdsp  # noqa: E402
import rhdsppatch as DP  # noqa: E402
from thumb import Asm, b, b_cond, b_w, bl, cmp_reg, ldr_imm, mov_reg, movs_imm, movt, movw, pop_list, push_list  # noqa: E402

BASE = rhdsp.BASE
UPLOAD_BL0, SEND = 0x0803115E, 0x080310B0
UPLOAD_BL1 = 0x08031170                     # (RD47) the bl that sends core 1's block (both modes)
BLK0, N0 = 0x0801A838, 0x1FED                          # core 0's mode 0 block (0x08031658[0])
LD = 0x3FE0                                            # our loader (top of the 16K of P)
VEC = 0x46                                             # our probe routine, in the unused vectors (P:$46..$FF are nop in the stock)
P_HOOK, OLD_HOOK = 0x126, (0x0BF0A8, 0x0001AE)         # jscs $1AE
SEG, MAGIC = 0x2000, 0x2D0C20                          # the test segment: P:SEG = MAGIC (data), P:SEG + 1 = its routine
Y_PASS, Y_SEG, Y_R1 = 0x1400, 0x1401, 0x1403           # core 0 Y (zero in every dump, no absolute operand in the stock: docs/RECURSOS.md)
PORT_WAIT, PORT_READ = "jclr #$11,x:<<$ffff91,${a:x}", "movep x:<<$ffff94,{r}"


def asm_at(items, at):
    """items: lines with {label:x} placeholders, ("label", name), ("jcc", cond, target), ("jmp", target), ("jsr", target), ("jscc", cond, target)
    (a target = a label or an address),
    ("words", [..]) -> (words, labels); two passes (every placeholder form has a fixed size)"""
    def lines_of(it, labels):
        return DP.asm([it.format_map(labels)])

    def size(it):
        if isinstance(it, str):
            return len(lines_of(it, defaultdict(lambda: 0x3FFF)))
        return {"label": 0, "jcc": 2, "jmp": 2, "jsr": 2, "jscc": 2, "bcc": 1, "bra": 1}.get(it[0], len(it[1]) if it[0] == "words" else 0)
    labels, a = {}, at
    for it in items:
        if isinstance(it, tuple) and it[0] == "label":
            labels[it[1]] = a
        a += size(it)
    out = []

    def at_(t):
        return labels[t] if isinstance(t, str) else t
    for it in items:
        if isinstance(it, str):
            w = lines_of(it, labels)
            assert len(w) == size(it), it
            out += w
        elif it[0] == "jcc":
            out += DP.jcc(it[1], at_(it[2]))
        elif it[0] == "jmp":
            out += DP.jmp(at_(it[1]))
        elif it[0] == "jsr":
            out += DP.jsr(at_(it[1]))
        elif it[0] == "jscc":
            out += DP.jscc(it[1], at_(it[2]))
        elif it[0] == "words":
            out += list(it[1])
        elif it[0] in ("bcc", "bra"):                                     # (RH80) the short relative forms, one word: +-255
            here = at + len(out)
            d = at_(it[-1]) - here
            assert -256 <= d <= 255, (it, hex(here))
            d &= 0x1FF
            out.append((0x050C00 if it[0] == "bra" else 0x050400 | DP.CC[it[1]] << 12) | (d >> 5) << 6 | (d & 0x1F))
    return out, labels


def shorten(items, at):
    """(RH81) the long conditional jumps to a label of these items that a one-word bcc reaches (in the long layout: shortening only brings
    the targets closer) -> bcc"""
    probe = []
    for i, it in enumerate(items):
        if isinstance(it, tuple) and it[0] == "jcc" and isinstance(it[2], str):
            probe.append(("label", f"__j{i}"))
        probe.append(it)
    _, lab = asm_at(probe, at)
    out = []
    for i, it in enumerate(items):
        if isinstance(it, tuple) and it[0] == "jcc" and isinstance(it[2], str) and it[2] in lab:
            d = lab[it[2]] - lab[f"__j{i}"]
            if -200 <= d <= 200:
                it = ("bcc", it[1], it[2])
        out.append(it)
    return out


def loader_items(port=True, xl=False):
    """our second-stage loader at P:LD; port=False (tests): the words from X:(r6)+ instead of the SHI; xl (RD49, OPT xtab): an address with
    bit 23 = an X segment: sent with its X address, $4000 or above (P ends at $3FFF), which the loader tells by its bit 14"""
    def wait(lab):
        return [("label", lab), PORT_WAIT.replace("{a:x}", "{" + lab + ":x}")] if port else [("label", lab)]

    def read(r):
        return PORT_READ.format(r=r) if port else f"move x:(r6)+,{r}"
    if xl:
        return [*wait("l_cnt"), read("y1"),
                *wait("l_adr"), read("x1"), "move x1,r7",
                "move y1,a", "tst a", ("jcc", "eq", "l_go"),
                "jclr #14,x1,${l_p:x}",
                "do y1,${l_xe:x}", *wait("l_xw"), read("x0"), "move x0,x:(r7)+", ("label", "l_xe"), ("jmp", "l_cnt"),
                ("label", "l_p"),
                "do y1,${l_end:x}", *wait("l_w"), read("x0"), "move x0,p:(r7)+", ("label", "l_end"), ("jmp", "l_cnt"),
                ("label", "l_go"), "jmp (r7)"]
    return [*wait("l_cnt"), read("y1"),                    # the count
            *wait("l_adr"), read("r7"),                    # the address
            "move y1,a", "tst a", ("jcc", "eq", "l_go"),   # count 0: the end
            "do y1,${l_end:x}",
            *wait("l_w"), read("x0"),
            "move x0,p:(r7)+",
            ("label", "l_end"), ("jmp", "l_cnt"),
            ("label", "l_go"), "jmp (r7)"]


def vec_items():
    return [("jscc", "cs", 0x1AE),                          # the stock's call (moves keep the C of P:$125)
            f"move y:>${Y_PASS:x},a", "add #$1,a", f"move a1,y:>${Y_PASS:x}",          # the main loop's passes
            f"move r1,y:>${Y_R1:x}", f"move #>${SEG:x},r1", f"move #>${MAGIC:x},x0", "move p:(r1),a", "cmp x0,a",
            f"move y:>${Y_R1:x},r1",
            ("jscc", "eq", SEG + 1),                        # the test segment, only once our loader has put it there
            "rts"]


def seg_items():
    return [("words", [MAGIC]), f"move y:>${Y_SEG:x},a", "add #$1,a", f"move a1,y:>${Y_SEG:x}", "rts"]


def block_words(img):
    _, n, at, code = rhdsp.block(img, 0, 0)                               # (RH80: also packed in pieces, tools/dspz.py)
    return n, at, [int.from_bytes(code[3 * i:3 * i + 3], "big") for i in range(n)]


def hole_places():
    """(RH80, OPT dzhole) the flash core 0's block leaves: up to cthresh's table (read at run time, kept), and after it"""
    import cthresh as CT
    return [(BLK0, CT.TAB_FLASH), (CT.TAB_FLASH + 3 * CT.TAB_N, BLK0 + 6 + 3 * N0)]


def more_blocks(img, report):
    """(RD47) the blocks packed by OPT dzmore: the stock's core 0 mode 1, core 1 modes 0 and 1 (from the upload table), and rhdsp1's core 1
    blocks of ours (c_d1up sends them) when packing saves more than its header"""
    out = [struct.unpack_from("<I", img, rhdsp.TABLE - BASE + 4 * k)[0] for k in (1, 2, 3)]
    pm = report.get("pitchmod", {})
    out += [int(x, 16) for x in pm.get("blocks", [pm[k] for k in ("blk_a", "blk_b") if k in pm])]
    return out


def d1up_sends(img, report):
    """(RD47) the bl SEND sites of rhdsp1's c_d1up (its code runs up to its first block)"""
    import rhbuild
    pm = report["pitchmod"]
    lo = int(pm["labels"]["c_d1up"], 16)
    hi = min(int(x, 16) for x in pm.get("blocks", [pm["blk_a"]]))
    out = []
    for x in range(lo, hi - 2, 2):
        h1, h2 = struct.unpack_from("<HH", img, x - BASE)
        if (h1 & 0xF800) == 0xF000 and (h2 & 0xD000) == 0xD000 and rhbuild.bl_target(img, x) == SEND:
            out.append(x)
    assert out and rhbuild.bl_target(img, UPLOAD_BL1) == lo
    return out


def pack_more(img, rep, rep_all):
    """(RD47, OPT dzmore) each of the other three DSP blocks packed where it is (a DZ2 header with one piece: c_dzs sends it as the stock
    sends a block); -> the tails they free [(start, end)], for core 0's stream"""
    import dspz as DZ
    out = []
    info = []
    for at in more_blocks(img, rep_all):
        o = at - BASE
        assert bytes(img[o:o + 4]) != DZ.MAGIC2
        n = int.from_bytes(img[o + 1:o + 3], "big")                      # (the stock sender's count: bytes 1-2 of the first word)
        size = 6 + 3 * n
        b1 = DZ.pack(bytes(img[o:o + size]))
        st_, words = b1[12:], struct.unpack_from("<I", b1, 4)[0]
        hl = DZ.H_ENT + 2 * DZ.ENT
        hd = DZ.header2(b1, [(at + hl, (st_, words))])
        body = hd + st_
        if len(body) + 16 >= size:
            continue                                                      # (not worth it: left as it is)
        img[o:o + size] = body + bytes([0xFF]) * (size - len(body))
        assert DZ.unblob2(img, at, BASE) == DZ.unblob(b1)
        lo = at + len(body)
        out.append((lo, at + size))
        info.append((hex(at), size, len(body)))
    rep["dzmore"] = dict(blocks=info, freed=sum(hi - lo for lo, hi in out))
    return out


def patch_p0(img, addr, old, new):
    o = BLK0 - BASE + 6 + 3 * addr
    have = int.from_bytes(img[o:o + 3], "big")
    assert have == old, (hex(addr), hex(have), hex(old))
    img[o:o + 3] = new.to_bytes(3, "big")


def install(img, report, base_addr, counter=True, loader=True, segs=None):
    """counter: RD20's probe in place in the stock block; loader: the second-stage loader + segs ([(address, words)]; None = RD20's test
    segment at P:SEG) sent after the mode 0 block"""
    import rhbuild
    assert struct.unpack_from("<I", img, rhdsp.TABLE - BASE)[0] == BLK0, "core 0's mode 0 block moved"
    n, at, ws = block_words(img)
    assert (n, at) == (N0, 0), (hex(n), hex(at))
    rep = report.setdefault("core0", {})
    if counter:
        vw, _ = asm_at(vec_items(), VEC)
        assert VEC + len(vw) <= 0x100
        for i, w in enumerate(vw):
            patch_p0(img, VEC + i, 0, w)
        patch_p0(img, P_HOOK, OLD_HOOK[0], 0x0BF080)
        patch_p0(img, P_HOOK + 1, OLD_HOOK[1], VEC)
        rep.update(vec=hex(VEC), vec_words=len(vw), y_pass=hex(Y_PASS))
    if not loader:
        return {}
    xl = any(a & 0x800000 for a, _ in (segs or []))                      # (RD49) X segments: the loader writes X too
    lw, _ = asm_at(loader_items(xl=xl), LD)
    assert LD + len(lw) <= 0x4000
    if segs is None:
        sw, _ = asm_at(seg_items(), SEG)
        segs = [(SEG, sw)]
    for a, w in segs:                                                     # (our free P; or a hook inside the stock program, its old words
        if a & 0x800000:                                                  #  checked by the caller: it lands after the stock block)
            assert 0x4000 <= a & 0xFFFF and (a & 0xFFFF) + len(w) <= 0x6000, hex(a)    # (RD49: X, told by bit 14)
            continue
        assert (N0 <= a and a + len(w) <= LD) or a + len(w) <= N0, hex(a)
    pack = lambda xs: b"".join(x.to_bytes(3, "big") for x in xs)           # noqa: E731
    blks = [pack([len(lw), LD] + lw)] + [pack([len(w), a & 0xFFFF] + list(w)) for a, w in segs] + [pack([0, 0])]
    assert rhbuild.bl_target(img, UPLOAD_BL0) == SEND
    dz = rhbuild.OPT.get("dspz", False)                                   # (RH69) the segments and the end as one packed stream (tools/dspz.py)
    if dz:
        import dspz as DZ
        DZ.check_ram(report)
        raw = b"".join(blks[1:])
        blks = [blks[0], DZ.pack(raw)]
        rep["dspz"] = dict(raw=len(raw), packed=len(blks[1]), ring=hex(DZ.RING), stage=hex(DZ.STAGE), state=hex(DZ.S))
    hole = dz and rhbuild.OPT.get("dzhole", False)                        # (RH80) the stock block too, the stream in pieces in its flash
    more = hole and rhbuild.OPT.get("dzmore", False)                     # (RD47) the other three DSP blocks packed in place too
    if hole:
        o = BLK0 - BASE
        blob = DZ.pack(bytes(img[o:o + 6 + 3 * N0]) + raw)
        R = hole_places()
        if more:
            R = R + pack_more(img, rep, report)
        HL = DZ.H_ENT + (len(R) + 2) * DZ.ENT                             # the pieces + the cave's + the end entry
        pieces = DZ.split(blob, [R[0][1] - R[0][0] - HL] + [hi - lo for lo, hi in R[1:]])
        blks = [blks[0], pieces[-1][0]]
        rep["dspz"].update(hole=[(hex(a), hex(b)) for a, b in R], packed=len(blob), pieces=[(len(p), w) for p, w in pieces])

    def gen(ats, inv=False):
        a = Asm(base_addr)
        E = a.emit

        def imm32(rd, v):
            E(movw, rd, v & 0xFFFF)
            E(movt, rd, (v >> 16) & 0xFFFF)

        def send(at):
            imm32(0, at)
            E(movs_imm, 1, 0)
            E(bl, SEND)
        a.label("c_d0up")                                                 # (r0 = block, r1 = core 0): ours around the mode 0 block
        E(push_list, [4], lr=True)
        E(mov_reg, 4, 0)
        imm32(0, BLK0)
        E(cmp_reg, 4, 0)
        if inv:                                                           # (more segments than a forward b<c> reaches, RH58: the stock's first)
            E(b_cond, "d0_ours", "eq")
            E(mov_reg, 0, 4)
            E(bl, "c_dzs" if more else SEND)
            E(pop_list, [4], pc=True)
            a.label("d0_ours")
        else:
            E(b_cond, "d0_stock", "ne")
        send(ats[0])                                                      # our loader (a bootstrap block)
        if hole:                                                          # the stock block, ours and the end: one stream in pieces
            imm32(0, BLK0)
            E(movs_imm, 1, 0)
            E(bl, "c_dzp")
        else:
            E(mov_reg, 0, 4)
            E(movs_imm, 1, 0)
            E(bl, SEND)                                                   # the stock block, from its own place
        if hole:
            pass
        elif dz:                                                          # our segments and the end, one packed stream
            imm32(0, ats[1])
            E(movs_imm, 1, 0)
            E(bl, "c_dz")
        else:
            for x in ats[1:]:
                send(x)                                                   # our segments, the end
        E(pop_list, [4], pc=True)
        if not inv:
            a.label("d0_stock")
            E(mov_reg, 0, 4)
            E(bl, "c_dzs" if more else SEND)
            E(pop_list, [4], pc=True)
        if more:                                                          # (OPT dzmore) c_dzs(r0 = block, r1 = core): a DZ2 one unpacked, else the stock's
            a.label("c_dzs")
            E(ldr_imm, 2, 0, 0)
            imm32(3, int.from_bytes(DZ.MAGIC2, "little"))
            E(cmp_reg, 2, 3)
            E(b_cond, "dzs_s", "ne")
            E(b, "c_dzp")
            a.label("dzs_s")
            E(b_w, SEND)
        if dz:
            DZ.emit(a, E, pieces=hole)
        return a.assemble(plain=True)
    inv = False
    try:
        size = len(gen([0] * len(blks))[0])
    except AssertionError:                                                # the forward branch out of reach: the other order
        inv = True
        size = len(gen([0] * len(blks), True)[0])
    ats, x = [], (base_addr + size + 3) & ~3
    for blk in blks:
        ats.append(x)
        x = (x + len(blk) + 3) & ~3
    code_arm, labels = gen(ats, inv)
    assert (base_addr + len(code_arm) + 3) & ~3 == ats[0]
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code_arm
    for x, blk in zip(ats, blks):
        img += bytes([0xFF]) * (x - BASE - len(img)) + blk
    while len(img) % 4:
        img += bytes([0xFF])
    if hole:                                                              # the header and the pieces in the holes, the last in the cave
        hd = DZ.header2(blob, [(R[0][0] + HL, pieces[0])] + [(R[k][0], pieces[k]) for k in range(1, len(R))] + [(ats[1], pieces[-1])])
        assert len(hd) == HL
        for (lo, hi), body in zip(R, [hd + pieces[0][0]] + [pieces[k][0] for k in range(1, len(R))]):
            assert len(body) <= hi - lo
            img[lo - BASE:hi - BASE] = body + bytes([0xFF]) * (hi - lo - len(body))
        assert DZ.unblob2(img, BLK0, BASE) == DZ.unblob(blob)
    rhbuild.patch(img, UPLOAD_BL0, f"bl #{SEND:#x}", bl(UPLOAD_BL0, labels["c_d0up"]))
    if more:                                                              # core 1's sends (rhdsp1's c_d1up: the stock block, ours) through c_dzs
        for x in d1up_sends(img, report):
            rhbuild.patch(img, x, f"bl #{SEND:#x}", bl(x, labels["c_dzs"]))
    rep.update(labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")}, blocks=[hex(b) for b in ats], ld=hex(LD),
               ld_words=len(lw), segs=[(hex(a), len(w)) for a, w in segs])
    return labels


def sent(img, report):
    """-> the words core 0 receives after the stub on a mode 0 upload of this image (for the tests): our blocks around the stock block"""
    def blk(at):
        o = at - BASE
        if bytes(img[o:o + 4]) == b"DZ1\0":                              # (RH69, dspz) a packed stream: all its words
            import dspz as DZ
            raw = DZ.blob_at(img, at, BASE)
            return [int.from_bytes(raw[i:i + 3], "big") for i in range(0, len(raw), 3)]
        cnt = int.from_bytes(img[o + 1:o + 3], "big")
        return [int.from_bytes(img[o + 3 * i:o + 3 * i + 3], "big") for i in range(cnt + 2)]
    ats = [int(a, 16) for a in report["core0"]["blocks"]]
    o = BLK0 - BASE
    if bytes(img[o:o + 4]) == b"DZ2\0":                                  # (RH80) the stock block and ours, one stream in pieces
        import dspz as DZ
        raw = DZ.unblob2(img, BLK0, BASE)
        return blk(ats[0]), [int.from_bytes(raw[i:i + 3], "big") for i in range(0, len(raw), 3)]
    return blk(ats[0]), blk(BLK0) + [w for a in ats[1:] for w in blk(a)]
