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
from thumb import Asm, b_cond, bl, cmp_reg, mov_reg, movs_imm, movt, movw, pop_list, push_list  # noqa: E402

BASE = rhdsp.BASE
UPLOAD_BL0, SEND = 0x0803115E, 0x080310B0
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
        return {"label": 0, "jcc": 2, "jmp": 2, "jsr": 2, "jscc": 2}.get(it[0], len(it[1]) if it[0] == "words" else 0)
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
    return out, labels


def loader_items(port=True):
    """our second-stage loader at P:LD; port=False (tests): the words from X:(r6)+ instead of the SHI"""
    def wait(lab):
        return [("label", lab), PORT_WAIT.replace("{a:x}", "{" + lab + ":x}")] if port else [("label", lab)]

    def read(r):
        return PORT_READ.format(r=r) if port else f"move x:(r6)+,{r}"
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
    o = BLK0 - BASE
    n, at = int.from_bytes(img[o:o + 3], "big"), int.from_bytes(img[o + 3:o + 6], "big")
    return n, at, [int.from_bytes(img[o + 6 + 3 * i:o + 9 + 3 * i], "big") for i in range(n)]


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
    lw, _ = asm_at(loader_items(), LD)
    assert LD + len(lw) <= 0x4000
    if segs is None:
        sw, _ = asm_at(seg_items(), SEG)
        segs = [(SEG, sw)]
    for a, w in segs:                                                     # (our free P; or a hook inside the stock program, its old words
        assert (N0 <= a and a + len(w) <= LD) or a + len(w) <= N0, hex(a)  #  checked by the caller: it lands after the stock block)
    pack = lambda xs: b"".join(x.to_bytes(3, "big") for x in xs)           # noqa: E731
    blks = [pack([len(lw), LD] + lw)] + [pack([len(w), a] + list(w)) for a, w in segs] + [pack([0, 0])]
    assert rhbuild.bl_target(img, UPLOAD_BL0) == SEND

    def gen(ats):
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
        E(b_cond, "d0_stock", "ne")
        send(ats[0])                                                      # our loader (a bootstrap block)
        E(mov_reg, 0, 4)
        E(movs_imm, 1, 0)
        E(bl, SEND)                                                       # the stock block, from its own place
        for x in ats[1:]:
            send(x)                                                       # our segments, the end
        E(pop_list, [4], pc=True)
        a.label("d0_stock")
        E(mov_reg, 0, 4)
        E(bl, SEND)
        E(pop_list, [4], pc=True)
        return a.assemble()
    size = len(gen([0] * len(blks))[0])
    ats, x = [], (base_addr + size + 3) & ~3
    for blk in blks:
        ats.append(x)
        x = (x + len(blk) + 3) & ~3
    code_arm, labels = gen(ats)
    assert (base_addr + len(code_arm) + 3) & ~3 == ats[0]
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code_arm
    for x, blk in zip(ats, blks):
        img += bytes([0xFF]) * (x - BASE - len(img)) + blk
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, UPLOAD_BL0, f"bl #{SEND:#x}", bl(UPLOAD_BL0, labels["c_d0up"]))
    rep.update(labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")}, blocks=[hex(b) for b in ats], ld=hex(LD),
               ld_words=len(lw), segs=[(hex(a), len(w)) for a, w in segs])
    return labels


def sent(img, report):
    """-> the words core 0 receives after the stub on a mode 0 upload of this image (for the tests): our blocks around the stock block"""
    def blk(at):
        o = at - BASE
        cnt = int.from_bytes(img[o + 1:o + 3], "big")
        return [int.from_bytes(img[o + 3 * i:o + 3 * i + 3], "big") for i in range(cnt + 2)]
    ats = [int(a, 16) for a in report["core0"]["blocks"]]
    return blk(ats[0]), blk(BLK0) + [w for a in ats[1:] for w in blk(a)]
