"""The LED task's heads with nothing of their own on the stack while the code below them runs (MIT; RH99; CIRCUIT-HACKS' use_lrram of SC56.7,
issue #22 of its public repository, for the whole chain of the Circuit Rhythm 5706).

Each module that draws over the LED frame is a head: its code is in front of the LED task's calls (countin.LED_CALLS, the stock's LED task
0x0803E80C(ctrl, frame)), it pushes registers and calls the head installed before it (`bl prev`), then draws.  The pushes nest: in RH98 56
heads keep about 1 270 B on the UI task's stack (2 KB, base 0x2000891C) before the stock's code runs.  The Pattern Settings views' slot 7
(their LED buffer, PS_VT + 0x1C: playmode, porder, drumpat, drumarp over the stock's 0x0805737C) nests the same way (≈ 84 B more).

Here each chain becomes a flat list run by a dispatcher that keeps its LR and the arguments in RAM (LS / LS + 16, the ITCM after xlanes'
second low region's slots: xlanes leaves 0x1B98 + 5 x 192 = 0x1F58 .. 0x1FFF unused) and calls, in the order the nesting ran them:
  * "pre" heads (work before their `bl prev`: kbright empties its overlay, arpext keeps the keyboard's arpeggio alive, granpage sends its DSP
    words), top to bottom, at their own entry; their chain call goes to a stub that, while the dispatcher runs (its next-entry word
    non-zero), ends the head (the pop of its own push, or `bx lr` for kbright's tail call), else calls the chain below as before (only a
    test calls a head by itself: nothing else in the image reaches one);
  * the stock's function;
  * every head's code after its chain call, bottom to top, through a trampoline: the head's own push and its leading `mov rN, r0 / r1` copied,
    then `b.w` just past its chain call (a chain that returns a value, slot 7, gets the value below in r0 there).
The heads' code is otherwise untouched; the order of everything that runs is the nesting's.  The walk checks each head (its push, the leading
moves, the pre work balanced and leaving r4-r11 alone, nothing else calling a head) and refuses the build otherwise.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capstone  # noqa: E402
from capstone.arm import ARM_REG_R0, ARM_REG_R4, ARM_REG_R11, ARM_REG_SP  # noqa: E402
from thumb import Asm, adds_imm8, movs_imm, b, b_cond, b_w, bl, blx_reg, cmp_imm, h, ldr_imm, mov_reg, movt, movw, raw, str_imm  # noqa: E402
import countin as CI  # noqa: E402
import playmode as PM  # noqa: E402

LS = 0x1F60                               # ITCM: main chain + 0 LR, + 4 ctrl, + 8 frame, + 12 the table's next entry
LS_PS = LS + 16                           # Pattern Settings' slot 7: + 0 LR, + 4 the view, + 8 the value so far, + 12 the next entry
TK, TK_LEN = LS + 32, 128                # (modmx with ledslim) c_mxtick's 64 targets (it ran them on the stack: 128 B under modmx's head)
LS_END = TK + TK_LEN
STOCK_LED = 0x0803E80C
PS_SLOT = PM.PS_VT + 0x1C
PS_STOCK = 0x0805737C
MD = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
MD.detail = True


def check_room():
    """LS .. LS_END in the ITCM nobody uses: past xlanes' slots in its region 0x1B98-0x1FFF, below dspz's window (0x2000)"""
    import xlanes
    lo = [(s, n) for s, n, k, _ in xlanes.REGS if s == 0x1B98]
    assert lo and lo[0][0] + lo[0][1] * xlanes.SLOT <= LS and LS_END <= 0x2000, "ledslim's RAM overlaps xlanes' pool"


def _prevs(report):
    """every address a module recorded as the one it hooked (its prev): the chain calls are to these"""
    out = set()

    def walk(d):
        if isinstance(d, dict):
            for k, v in d.items():
                if k in ("prev", "prev_led") and isinstance(v, str) and v.startswith("0x"):
                    out.add(int(v, 16))
                elif k == "prev" and isinstance(v, dict):
                    out.update(int(x, 16) for x in v.values() if isinstance(x, str) and x.startswith("0x"))
                else:
                    walk(v)
    walk(report)
    return out


def _regs(op):
    """'{r3, r4, lr}' -> [3, 4, 14]"""
    names = {"sb": 9, "sl": 10, "fp": 11, "ip": 12, "lr": 14, "pc": 15}
    return [names[r] if r in names else int(r[1:]) for r in op.strip("{} ").replace(" ", "").split(",")]


def head(img, base, at, prevs, stock):
    """-> dict(at, site, call ('bl' / 'b.w'), nxt, pro (the prologue's bytes), push (its registers), kind ('post' / 'pre' / 'both'))"""
    off = at - base
    ins = []
    for i in MD.disasm(bytes(img[off:off + 512]), at):
        ins.append(i)
        if i.mnemonic in ("bl", "b.w") and i.op_str.startswith("#") and (int(i.op_str[1:], 16) in prevs or int(i.op_str[1:], 16) == stock):
            break
        assert len(ins) < 64 and not (i.mnemonic.startswith("pop") and "pc" in i.op_str), f"{at:#x}: no chain call found"
    call = ins[-1]
    first = ins[0]
    assert first.mnemonic in ("push", "push.w"), f"{at:#x}: a head without its push ({first.mnemonic} {first.op_str})"
    push = _regs(first.op_str)
    assert 14 in push and 13 not in push and 15 not in push
    n = 1
    while n < len(ins) - 1 and ins[n].mnemonic == "mov" and ins[n].op_str.split(", ")[1] in ("r0", "r1") \
            and 4 <= _regs("{" + ins[n].op_str.split(", ")[0] + "}")[0] <= 11:
        n += 1
    pro = bytes(img[off:ins[n].address - base])
    rest = ins[n:-1]
    nxt = int(call.op_str[1:], 16)
    d = dict(at=at, site=call.address, call=call.mnemonic, nxt=nxt, pro=pro, push=push, moves=[i.op_str for i in ins[1:n]])
    if call.mnemonic == "b.w":                                           # a tail call: all of it before the chain (kbright)
        assert rest and rest[-1].mnemonic == "pop.w" and _regs(rest[-1].op_str) == push, f"{at:#x}: a tail call without its own pop"
        d["kind"] = "pre"
    elif not rest:
        d["kind"] = "post"
    else:                                                                 # work before the chain (arpext, granpage)
        sp = 0
        for i in rest:
            if i.mnemonic in ("push", "push.w"):
                sp += 4 * len(_regs(i.op_str))
                continue
            if i.mnemonic in ("pop", "pop.w"):
                sp -= 4 * len(_regs(i.op_str))
                assert 15 not in _regs(i.op_str)
                continue
            rd, wr = i.regs_access()
            assert not (i.mnemonic.startswith("st") and "sp" in i.op_str), f"{at:#x}: the pre work writes its stack ({i.mnemonic} {i.op_str})"
            assert ARM_REG_SP not in wr, f"{at:#x}: the pre work moves sp ({i.mnemonic} {i.op_str})"
            assert not [r for r in wr if ARM_REG_R4 <= r <= ARM_REG_R11], f"{at:#x}: the pre work writes r4-r11 ({i.mnemonic} {i.op_str})"
            assert i.mnemonic in ("bl",) or not i.mnemonic.startswith(("b", "cb", "tb")) or (i.op_str.startswith("#") and
                                                                                           at <= int(i.op_str[1:], 16) <= call.address), \
                f"{at:#x}: the pre work leaves it ({i.mnemonic} {i.op_str})"
        assert sp == 0, f"{at:#x}: the pre work's stack unbalanced"
        assert all(r <= 7 or r == 14 for r in push), f"{at:#x}: its push needs a 32-bit pop"
        d["kind"] = "both"
    return d


def walk(img, base, entry, stock, prevs):
    """the heads from the outermost (entry) down to the one that calls the stock's function"""
    out = []
    at = entry
    while at != stock:
        d = head(img, base, at, prevs, stock)
        out.append(d)
        at = d["nxt"]
        assert len(out) < 128
    return out


def popn(regs):
    return h(0xBC00 | sum(1 << r for r in regs if r < 8) | (0x100 if 14 in regs else 0))


def n_ents(heads):
    return sum(d["kind"] in ("pre", "both") for d in heads) + 1 + sum(d["kind"] != "pre" for d in heads)


def arm_code(base, chains, boot=None):
    """chains: [(name, heads, stock, ret, ram)] -> code, labels.  Per chain: the dispatcher c_ls<name>, the trampolines; the tables after
    the code (a word a call, 0 at the end).  boot = (c_ciok, c_rst) (OPT raminit): the main chain's dispatcher calls c_rst first once the
    stock is up, so its first call of a boot (rhstate raminit: our RAM outside its blocks zeroed) comes before any head reads that RAM"""
    def asm(tabs):
        a = Asm(base)
        E = a.emit

        def imm32(rd, v):
            E(movw, rd, v & 0xFFFF)
            E(movt, rd, (v >> 16) & 0xFFFF)

        for name, heads, stock, ret, ram in chains:
            a.label(f"c_ls{name}")
            E(movw, 2, ram)
            E(raw, h(0xF8C2) + h(0xE000))                                  # str.w lr, [r2]
            E(str_imm, 0, 2, 4)
            E(str_imm, 1, 2, 8)
            if boot and name == "main":
                E(bl, boot[0])                                             # c_ciok
                E(cmp_imm, 0, 0)
                E(b_cond, f"ls_{name}_nb", "eq")
                E(bl, boot[1])                                             # c_rst
                a.label(f"ls_{name}_nb")
                E(movw, 2, ram)
            imm32(3, tabs.get(name, 0))
            a.label(f"ls_{name}_lp")
            E(ldr_imm, 0, 3, 0)
            E(cmp_imm, 0, 0)
            E(b_cond, f"ls_{name}_x", "eq")
            E(adds_imm8, 3, 4)
            E(str_imm, 3, 2, 12)
            E(raw, h(0x4684))                                              # mov ip, r0
            E(ldr_imm, 0, 2, 4)
            E(ldr_imm, 1, 2, 8)
            E(blx_reg, 12)
            E(movw, 2, ram)
            if ret:
                E(str_imm, 0, 2, 8)                                        # the value so far (the slot's buffer)
            E(ldr_imm, 3, 2, 12)
            E(b, f"ls_{name}_lp")
            a.label(f"ls_{name}_x")
            if ret:
                E(ldr_imm, 0, 2, 8)
            E(movs_imm, 3, 0)
            E(str_imm, 3, 2, 12)                                           # not dispatching (the stubs below tell by it)
            E(raw, h(0xF8D2) + h(0xF000))                                  # ldr.w pc, [r2]
            for k, d in enumerate(heads):
                if d["kind"] in ("pre", "both"):                           # its chain call's stub: dispatching, its own end (the work
                    a.label(f"ls_{name}_s{k}")                             #   below comes after it); else the chain below as before
                    E(movw, 12, ram)                                       #   (a test that calls a head itself)
                    E(raw, h(0xF8DC) + h(0xC00C))                          # ldr.w ip, [ip, #12]
                    E(raw, h(0xF1BC) + h(0x0F00))                          # cmp.w ip, #0
                    E(b_cond, f"ls_{name}_d{k}", "ne")
                    E(b_w, d["nxt"])
                    a.label(f"ls_{name}_d{k}")
                    E(raw, h(0x4770) if d["kind"] == "pre" else popn(d["push"]))
            for k, d in enumerate(heads):
                if d["kind"] == "pre":
                    continue
                a.label(f"ls_{name}_t{k}")                                 # the head's own push and moves, then past its chain call
                E(raw, d["pro"])
                if ret:
                    E(mov_reg, 0, 1)
                E(b_w, d["site"] + 4)
        return a.assemble(plain=True)

    code, labels = asm({})
    tabs, at = {}, (base + len(code) + 3) & ~3
    for name, heads, *_ in chains:
        tabs[name] = at
        at += 4 * (n_ents(heads) + 1)
    code, labels = asm(tabs)
    out = bytearray(code)
    for name, heads, stock, ret, ram in chains:
        while (base + len(out)) % 4:
            out += h(0xBF00)
        assert base + len(out) == tabs[name]
        labels[f"ls_{name}_tab"] = tabs[name]
        ents = [d["at"] | 1 for d in heads if d["kind"] in ("pre", "both")]
        ents.append(stock | 1)
        ents += [labels[f"ls_{name}_t{k}"] | 1 for k in range(len(heads) - 1, -1, -1) if heads[k]["kind"] != "pre"]
        assert len(ents) == n_ents(heads)
        out += b"".join(struct.pack("<I", x) for x in ents) + bytes(4)
    return bytes(out), labels


def install(img, report, base_addr):
    """Last of all: the two chains walked and flattened (the LED task's calls, Pattern Settings' slot 7)"""
    import rhbuild
    BASE = rhbuild.BASE
    check_room()
    prevs = _prevs(report)
    top = rhbuild.bl_target(img, CI.LED_CALLS[0])
    assert all(rhbuild.bl_target(img, c) == top for c in CI.LED_CALLS)
    ps_top = struct.unpack_from("<I", img, PS_SLOT - BASE)[0] & ~1
    chains = [("main", walk(img, BASE, top, STOCK_LED, prevs), STOCK_LED, False, LS),
              ("ps", walk(img, BASE, ps_top, PS_STOCK, prevs), PS_STOCK, True, LS_PS)]
    for name, heads, stock, ret, ram in chains:
        if ret:
            assert all(d["kind"] == "post" for d in heads), f"{name}: work before the chain in a chain with a value"
            assert not any(m.endswith(", r1") for d in heads for m in d["moves"]), f"{name}: a head takes r1 (one argument)"
    # nothing but its upper head (or the entry) may reach a head
    hs = {d["at"] for _, heads, *_ in chains for d in heads}
    for off in range(0, len(img) - 4, 2):
        w = struct.unpack_from("<I", img, off)[0]
        assert not (w & 1 and (w & ~1) in hs and (w & ~1) not in (ps_top,)), f"a word at {BASE + off:#x} points at head {w & ~1:#x}"
    links = {d["site"] for _, heads, *_ in chains for d in heads} | set(CI.LED_CALLS)
    for off in range(0, len(img) - 4, 2):
        h1, h2 = struct.unpack_from("<HH", img, off)
        if h1 & 0xF800 == 0xF000 and h2 & 0xD000 in (0xD000, 0x9000):
            t = (rhbuild.bl_target if h2 & 0xD000 == 0xD000 else rhbuild.bw_target)(img, BASE + off)
            assert t not in hs or BASE + off in links, f"{BASE + off:#x} reaches head {t:#x}"
    boot = None
    if rhbuild.OPT.get("raminit"):
        boot = (int(report["countin"]["labels"]["c_ciok"], 16), int(report["rhstate"]["labels"]["c_rst"], 16))
    code, labels = arm_code(base_addr, chains, boot)
    img += bytes([0xFF]) * (base_addr - BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    for name, heads, *_ in chains:
        for k, d in enumerate(heads):
            if d["kind"] == "pre":
                rhbuild.patch(img, d["site"], f"b.w #{d['nxt']:#x}", b_w(d["site"], labels[f"ls_{name}_s{k}"]))
            elif d["kind"] == "both":
                rhbuild.patch(img, d["site"], f"bl #{d['nxt']:#x}", bl(d["site"], labels[f"ls_{name}_s{k}"]))
    for c in CI.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{top:#x}", bl(c, labels["c_lsmain"]))
    rhbuild.patch_word(img, PS_SLOT, ps_top | 1, labels["c_lsps"] | 1)
    report["ledslim"] = dict(ram=hex(LS), chains={name: [dict(at=hex(d["at"]), kind=d["kind"]) for d in heads] for name, heads, *_ in chains},
                             labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
