"""OSC 1's sub-oscillator and noise for the VA in one-oscillator mode (MIT; RH101; CIRCUIT-HACKS' SC52.8 / Beta 5.31 «osc1x» on the
Circuit Rhythm, ours: the same knobs, the same arithmetic and the same 8 bytes in a patch; the code is new, for tools/synth0.py's VA slots
on core 0 and tools/vsel.py's OSC 1 page).

DSP (core 0, SUBN at P:AT, the free piece after linein's tables; OPT osc1x of tools/sp0.py: its SDS entry jumps here, SUBN ends `jmp e_sds`,
so it runs at synth0's e_vca for every VA slot after any of its loops: one oscillator, two, 2x after va_dx; FM slots never get there):
  * per block, as Hacks' om_sx: level = clamp(base / 128 + LFO x its depth + S_ENV x its depth, >= 0) / 2, for the sub and the noise;
    the LFO = Stock+'s per-track triangle 2 |C_PH| - 1 (tools/sp0.py's block Y:$1D80 + $20 t, 0 when its key is not SPKEY: its rate is
    the Envelope + LFO page's K5); a level 0 skips its loop (all at 0 = RH100 sample for sample);
  * the sub: a square an octave under OSC 1 (its phase S_PHS += Y S_INC1 / 2: OSC 1's increment with its tune, fine and env -> pitch, 1x
    even when the slot runs at 2x), the edge at the zero crossing ramped (the phase << 5, saturated), the wrap hard (as Hacks: no BLEP);
  * the noise: Hacks' LCG s = s x $0343FD + $269EC3 (mod 2^24) on S_NZ (s_init seeds it with the slot's own Y base, once a slot: seeded 1,
    unison voices and poly voices triggered in one block played the identical sequence and summed coherently), x level, added;
  * the words (synth0's slot Y, which the VA does not use; the ARM sends them in its round, 0 with two oscillators: tools/vsel.py's c_vsext):
    C_K the sub's level 0..127, C_FM env -> sub, C_GN the noise's level, C_VFM env -> noise, C_SHP LFO -> sub, C_P2 LFO -> noise (the
    depths -64..63); the levels kept a block in the slot's S_PH1B / S_PH2B (the start's unison's phases: never with the VA).
ARM (RAM OSX = fxseq.FXR + 272 + 6 t, in rhstate's second block: zeroed at each boot): + 0 the sub's level, + 1 env -> sub, + 2 the noise's
level, + 3 env -> noise, + 4 LFO -> sub, + 5 LFO -> noise = vsel's values e 5..10; a level plain (0 = off), a depth XOR 64 (0 = the centre).
The matrix's live offsets reach the words in vsel's c_vsext (destinations 32 + e and 50 + (e - 5), modmx's c_mxadd, as c_mxsyv does for the
synth knobs; a lane writes the store itself); the one / two-oscillator decision (synthpage's c_sydual) reads the BASE knob values (c_syv),
never the offsets: a source on MIX / RING / K7 / FM must not flip the mode, mute the sub or move OSC 1's K5 / K6 / K8 to hidden targets.
A patch (rpatch): Hacks' block at padding + 142..149 = $C5, LFO -> sub, LFO -> noise, noise level, env -> noise, sub level, env -> sub
(each value - 64, as a byte), (0x5A + bytes 0..6) & 0xFF.  A project (projsnd): VA_AT + 9 .. 14 = the RAM's 6 bytes.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

AT, END = 0x2A37, 0x2AB0                               # core 0 P: free since RD49's xtab (synth0's tables moved to X); sp0 starts at $2AB0
NE, E0 = 6, 5                                          # vsel's values e 5..10
KEYS = (0, 64, 0, 64, 64, 64)                          # stored XOR: the levels plain, the depths XOR 64
LEVELS = (0, 2)                                        # the levels' places (e - 5)
HX = (5, 6, 3, 4, 1, 2)                                # each value's byte in Hacks' block (e - 5 -> 1..6)
HMARK, HCHK0, HOFF, HLEN = 0xC5, 0x5A, 142, 8          # the patch's block: its mark, its check's start, its place in the padding
LCG_K, LCG_C = 0x0343FD, 0x269EC3


def on():
    import rhbuild
    return bool(rhbuild.OPT.get("osc1x"))


def ram():
    """the 8 tracks' 6 bytes: right after fmmap's FMAP (RH100: FXR + 160, 112 B), inside the 512 B of modmx's old offsets (rhstate's
    second block: zeroed at each boot)"""
    import fmmap as MM
    import fxseq as FX
    r = FX.FXR + 272
    assert r >= MM.FMAP + MM.LEN and r + 8 * NE <= FX.FXR + 512, "osc1x: its RAM over fmmap's or past FXR + 512"
    return r


def words_of(c):
    """the C_* words SUBN reads, (base, LFO depth, env depth) for the sub and for the noise"""
    import synth0 as S
    return (S.C_K, S.C_SHP, S.C_FM), (S.C_GN, S.C_P2, S.C_VFM)


def items(e_sds):
    """SUBN (r6 = the slot's Y block, r5 the track's parameters: both kept; a, b, x0, x1, y0, y1, r0, r1 used) -> ends jmp e_sds"""
    import sp0 as SP
    import synth0 as S
    ys = lambda o: f"y:(r6+${o:x})"                                         # noqa: E731
    LS, LN = S.S_PH1B, S.S_PH2B                                              # (sl's phases: never with the VA)
    L = [("label", "subn"),
         # x1 = the LFO: Stock+'s triangle of the slot's track, 0 when its block is not keyed
         f"move {ys(S.S_T)},a", "and #$7,a", "asl #5,a,a", f"add #>${SP.Y0:x},a", "move a1,r1", "nop",
         f"move y:(r1+${SP.C_KEY:x}),a", f"move #>${SP.SPKEY:x},x0", "clr b", "cmp x0,a", ("bcc", "ne", "sn_l"),
         f"move y:(r1+${SP.C_PH:x}),a", "abs a", "asl a", f"move #>${SP.ONE:x},x0", "sub x0,a", "move a,b",
         ("label", "sn_l"), "move b,x1"]
    for (base, dl, de), store in zip(words_of(None), (LS, LN)):          # level = clamp(base / 128 + LFO x dl + env x de, >= 0) / 2
        L += [f"move {ys(base)},a", "asl #16,a,a",
              f"move {ys(dl)},b", "asl #17,b,b", "move b,x0", "mpy x1,x0,b", "add b,a",
              f"move {ys(de)},b", "asl #17,b,b", "move b,x0", f"move {ys(S.S_ENV)},y0", "mpy y0,x0,b", "add b,a",
              "clr b", "tst a", "tlt b,a", "asr a", f"move a,{ys(store)}"]
    # the sub: y1 = its level, x0 = OSC 1's increment / 2, a = the phase
    L += [f"move {ys(LS)},a", "tst a", ("bcc", "eq", "sn_n"), "move a,y1", f"move {ys(S.S_BUF)},r0",
          f"move {ys(S.S_INC1)},a", "asr a", "move a,x0", f"move {ys(S.S_PHS)},a",
          "do #$20,${sn_se:x}",
          "add x0,a", "move a1,a", "tfr a,b", "asl #5,b,b", "move b,y0", "mpy y1,y0,b", "move y:(r0),x1", "add x1,b", "move b,y:(r0)+",
          ("label", "sn_se"),
          f"move a,{ys(S.S_PHS)}"]
    # the noise: y1 = its level, x0 = the state, y0 / x1 = the LCG's constants
    L += [("label", "sn_n"), f"move {ys(LN)},a", "tst a", ("bcc", "eq", "sn_x"), "move a,y1", f"move {ys(S.S_BUF)},r0",
          f"move {ys(S.S_NZ)},x0", f"move #>${LCG_K:x},y0", f"move #>${LCG_C:x},x1",
          "do #$20,${nz_e:x}",
          "mpy y0,x0,a", "asr a", "move a0,b", "add x1,b", "move b1,x0", "move y:(r0),a", "mac x0,y1,a", "move a,y:(r0)+",
          ("label", "nz_e"),
          f"move x0,{ys(S.S_NZ)}",
          ("label", "sn_x"), ("jmp", e_sds)]
    return L


def code(e_sds):
    """-> (SUBN's words at P:AT, labels)"""
    import core0 as C0
    import sp0 as SP
    w, lab = C0.asm_at(SP.short_items(items(e_sds)), AT)
    assert AT + len(w) <= END, f"SUBN ends at {AT + len(w):#x}"
    return w, lab


def check(e_sds):
    """dsptool reads every word back (no mpysu: voicefx.check)"""
    import voicefx
    return voicefx.check(code(e_sds)[0], AT)


# ================================================================ the model (the tests'): SUBN's arithmetic, bit for bit
def lfo_of(ph, keyed):
    """Stock+'s triangle from its phase C_PH (0 when the track's block is not keyed)"""
    from synth0 import _sat, s24
    if not keyed:
        return 0
    return _sat(((abs(s24(ph)) << 24) << 1) - (0x7FFFFF << 24))


def levels(c, env, lfo):
    """-> (the sub's level, the noise's level) from the slot's control words c"""
    from synth0 import _mpy, _sat, s24
    out = []
    for base, dl, de in words_of(c):
        a = (s24(c[base]) << 24) << 16
        a += _mpy(lfo, _sat((s24(c[dl]) << 24) << 17))
        a += _mpy(env, _sat((s24(c[de]) << 24) << 17))
        if a < 0:
            a = 0
        out.append(_sat(a >> 1))
    return tuple(out)


def model(buf, st, c, inc1, env, lfo):
    """SUBN on the slot's 32 samples (signed or 24-bit words: va0's decimator gives the latter; st: synth0.Model's slot state, phs / nz
    kept there) -> the samples"""
    from synth0 import _mpy, _sat, s24
    ls, ln = levels(c, env, lfo)
    buf = list(buf)
    if ls:
        x0 = _sat((s24(inc1) << 24) >> 1)
        ph = s24(st.get("phs", 0))
        for i in range(32):
            ph = s24(ph + x0)
            y0 = _sat((ph << 24) << 5)
            buf[i] = _sat(_mpy(ls, y0) + (s24(buf[i]) << 24))
        st["phs"] = ph
    if ln:
        x0 = s24(st.get("nz", 1))
        for i in range(32):
            a0 = (_mpy(x0, LCG_K) >> 1) & 0xFFFFFF
            x0 = s24((s24(a0) + LCG_C) & 0xFFFFFF)
            buf[i] = _sat((s24(buf[i]) << 24) + _mpy(x0, ln))
        st["nz"] = x0
    return buf


# ================================================================ the ARM's values (vsel's e 5..10) and the patch's block
def word(e, stored):
    """the DSP word of value e (5..10) from its stored byte: a level plain, a depth - 64"""
    k = KEYS[e - E0]
    return (stored ^ k) - k


def hacks_block(stored6):
    """the RAM's 6 bytes (e 5..10 stored) -> Hacks' 8 bytes"""
    b = [HMARK] + [0] * 6
    for i in range(NE):
        b[HX[i]] = ((stored6[i] ^ KEYS[i]) - 64) & 0xFF
    return bytes(b + [(HCHK0 + sum(b)) & 0xFF])


def from_hacks(blk):
    """Hacks' 8 bytes -> the RAM's 6 (a block without its mark or check: all 0, off and the centre)"""
    if len(blk) < HLEN or blk[0] != HMARK or blk[7] != (HCHK0 + sum(blk[:7])) & 0xFF:
        return bytes(NE)
    out = []
    for i in range(NE):
        v = min(127, (blk[HX[i]] + 64) & 0xFF)
        out.append(v ^ KEYS[i])
    return bytes(out)
