"""8-operator FM with DX7 envelopes, an engine of the synth on the Circuit Rhythm's DSP core 0 (MIT; RD40; the user, 2026-11-05: «can we port
the new 8OP engine from tracks» -> «Yes, reduced port»).  CIRCUIT-HACKS' FM8 (granular_dsp / vcf21_dsp use_fm8: the loop of N operators with
an 8-wide modulation sum; fm8.py: the patch, the 56 algorithms, the DX7 envelopes of ref_tick), ours on both firmwares; here the envelopes
run on the DSP (the Rhythm's ARM has no time or RAM for them) and it replaces tools/fm0.py's 4 operators in the same places.

Where: as fm0, synth0's slot (r6 = its Y block) calls FMW in place of its envelope (s_env2); FMW runs that envelope, then with the slot's
block on (G_KEY) writes its 32 samples into the track's buffer and goes on to synth0's filter (s_filt).  The slot's block: X:FB0 + $200 s
(= 8 r6 - $7C00): globals at + 0, operator k at + 16 + 32 k, the pitch envelope at + PEGB (its first 12 words as an operator's).
  per operator: the envelope E (level x 256, u = 1/256 octave of amplitude as fm8), its stage ST (0-2 the attack and decays, 3 the release,
  4 held, 5 done), T1-T4 (the stages' targets), S1-S4 (their slopes a block), FL (a rising stage starts at least there), RM (1: a rising
  stage 4x faster; the pitch envelope 0), BASE ((EMAX + (99 - OL) x 32 + the level scaling) x 256, an operator not heard: huge), VS (the
  velocity's attenuation: OFS = VS x (1 - velocity) at the note-on), R0 (the ratio x 2^16); the sample loop's OUT, PH, R, AMP, K, M1-M8, AS,
  O2, HC (fm0's / Hacks');
  each block (fm8.ref_tick in block steps): a falling gate = every stage 3; a stage below 4 goes to its target (rising: from FL at least,
  RM x 4 faster), reached = the next (2 -> 4 held, 3 -> 5); AMP = 2^-(att / 65536) with att = BASE + OFS - E (BASE holds AMP0's
  0.13 dB) (0 under E 256); the
  pitch factor pf = 2^((E_peg - PC) x PK + TRN) / 65536) gives R = R0 x pf; the noise's amplitude NA = NZ x the AMP of operator NOP (the last block's);
  the note-on (rtdc's DCN flag of the slot's track, or poly0's of the slot): the nine stages to 0, OFS, with G_FLG bit 1 the phases and
  outputs to 0; every AMP 0 = resting: the track's samples zero (no loop).
Not in the reduced port: the operators' fixed frequency (they follow the key), rate scaling, the level scaling by note (the tool's, for the
middle C), the DX7 LFO.
Core 0: P:FL_AT (the sample loop), the pieces (FMW, note-on, envelopes, pitch / noise amplitude, 2^-x, the noise), X:FB0..
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core0 as C0  # noqa: E402

FB0, FBS = 0x5400, 0x200                              # X: a slot's block (free X RAM: RD37 / RD39; fm0's $5000-$51FF unused)
NF = 0x5200                                           # X: a note-on flag per track (rtdc's DCN), as fm0
OPS, OP0 = 32, 16                                     # an operator's words; operator 0's offset
(F_E, F_ST, F_T1, F_T2, F_T3, F_T4, F_S1, F_S2, F_S3, F_S4, F_FL, F_RM, F_BASE, F_VS, F_OFS, F_R0,
 F_OUT, F_PH, F_R, F_AMP, F_K, F_M1, F_M2, F_M3, F_M4, F_M5, F_M6, F_M7, F_M8, F_AS, F_O2, F_HC) = range(32)
PEGB = OP0 + 8 * OPS                                  # the pitch envelope (F_E .. F_RM)
(G_KEY, G_FLG, G_N, G_TOPA, G_NZ, G_NOPA, G_NA, G_NS, G_PG, G_PC, G_PK, G_A1, G_A2) = range(13)
FMKEY = 0x0F4A18
SV = 0x1F68                                           # core 0 Y (n4 kept, as fm0)
ONE = 0x7FFFFF
AMPF = 0x7E0000                                       # AMP at att 0 (fm8.AMP0: the 4-operator engine's full level) = BASE + AMP0_ATT
AMP0_ATT = 1521                                       # -log2(0x7E0000 / 2^23) x 65536 (in the tool's BASE)
A1, A2 = 0x55BE4D, 0x15BE4D                            # 2^-f ~ 1 - f (A1 - A2 f), A1 = 0.5 + A2 (G_A1 / G_A2: 0.023 dB at most; f = 0 exact)
FL_AT = 0x98                                          # the sample loop: P:$98-$FF (fm0's and the 9 words after)
PIECES = dict(fmw=(0x2DDA, 38), ftr=(0x2FDA, 38), fen=(0x3675, 91), fpr=(0x2D21, 31), ex2=(0x39ED, 19), amp1=(0x25EE, 18), fna=(0x2884, 12))
FL_END = 0x100                                        # FL and the noise (fnz) in P:$98-$FF
LCG_A, LCG_C = 1664525 & 0xFFFFFF, 1013904223 & 0xFFFFFF
X = lambda r, o: f"x:({r}+${o:x})"                      # noqa: E731


def _syn():
    import synth0
    return synth0


def _trig():
    """the note-on flag's address in a: the slot's track's (rtdc's DCN), or with OPT poly the slot's own (poly0's FTR + s)"""
    import rhbuild
    S = _syn()
    if rhbuild.OPT.get("poly"):
        import poly0
        return ["move r6,a", f"sub #>${S.Y0:x},a", "asr #6,a,a", f"add #>${poly0.FTR:x},a"]
    return [f"move y:(r6+${S.S_T:x}),a", "and #>$7,a", f"add #>${NF:x},a"]


def loop_items():
    """FL (a = 0: resting, the samples zero): r3 = the slot's block, r0 = the 32 samples, y1 = the increment; G_TOPA = the top operator's
    block's address (the tool's: the loop runs top down), G_N operators; the modulation sum reads the eight operators' OUT (r4, n4 = OPS)"""
    M = [f"move {X('r2', F_M1 + j)},x0" for j in range(8)]
    L = [("label", "fl"), "tst a", ("jcc", "ne", "fl_go"), "clr a", "rep #$20", "move a,y:(r0)+", "rts",
         ("label", "fl_go"), f"move #${OPS:x},n4",
         "do #$20,${fl_s:x}", f"move {X('r3', G_TOPA)},r2", f"move {X('r3', G_N)},x0", "clr b", f"lua (r3+${OP0 + F_OUT:x}),r4",
         "do x0,${fl_o:x}",
         f"move {X('r2', F_AMP)},a", f"move {X('r2', F_AS)},x0", "sub x0,a", "asr #5,a,a", "add x0,a", f"move a,{X('r2', F_AS)}",
         f"move {X('r2', F_R)},x0", "mpy x0,y1,a", "asl #7,a,a", f"move {X('r2', F_PH)},x0", "add x0,a", f"move a1,{X('r2', F_PH)}",
         "move a1,x1",
         M[0], "move x:(r4)+n4,y0", ("words", [0x46CCD0])]                   # mpy y0,x0,a x:(r4)+n4,y0
    for j in range(1, 7):
        L += [M[j], ("words", [0x46CCD2])]                                  # mac y0,x0,a x:(r4)+n4,y0
    L += [M[7], "mac y0,x0,a", f"lua (r3+${OP0 + F_OUT:x}),r4",
          f"move {X('r2', F_HC)},x0", f"move {X('r2', F_O2)},y0", "mac y0,x0,a",
          "asl #2,a,a", "add x1,a", "move a1,x1",
          "move x1,a", "abs a", "move a,y0", "mpy -x1,y0,a", "add x1,a", "asl #2,a,a",
          "abs a a,x0", "move a,y0", "mpy y0,x0,a", "sub x0,a", "asr #2,a,a", "add x0,a", "move a,x0",
          f"move {X('r2', F_AS)},y0", "mpy y0,x0,a", f"move {X('r2', F_OUT)},x1", f"move a,{X('r2', F_OUT)}", "move a,y0",
          f"move x1,{X('r2', F_O2)}",
          f"move {X('r2', F_K)},x0", f"lua (r2-${OPS:x}),r2",
          "mac y0,x0,b", ("label", "fl_o"), "move b,y:(r0)+", ("label", "fl_s"), "rts"]
    return L


def noise_items():
    """fnz, right after FL in its place"""
    return [("label", "fnz"),
            f"move {X('r3', G_NA)},y1", "move y1,a", "tst a", ("jcc", "eq", "fz_x"),
            "lua (r0-$20),r0", f"move {X('r3', G_NS)},x1", "nop",
            "do #$20,${fz_e:x}",
            f"move #>${LCG_A:x},y0", "mpy x1,y0,a", "asr a", "move a0,x1", "move x1,a", f"add #>${LCG_C:x},a", "move a1,x1",
            "move x1,x0", "mpy x0,y1,a", "move y:(r0),x0", "add x0,a", "move a,y:(r0)+", ("label", "fz_e"),
            f"move x1,{X('r3', G_NS)}",
            ("label", "fz_x"), "rts"]


def piece_items(lab):
    """{name: items}; lab: synth0's labels (s_env2, s_filt)"""
    S = _syn()
    ys = lambda o: f"y:(r6+${o:x})"                                                  # noqa: E731
    P = {}
    # ---- FMW: synth0's envelope, the block's key, the note-on, the envelopes (a = resting), the loop, the noise, synth0's filter
    P["fmw"] = [("label", "fmw"), ("jsr", lab["s_env2"]),
                "move r6,a", "asl #3,a,a", "sub #>$7c00,a", "move a1,r3",
                f"move {X('r3', G_KEY)},a", f"move #>${FMKEY:x},x0", "cmp x0,a", ("jcc", "eq", "fw_go"), "rts",
                ("label", "fw_go"), f"move n4,y:>${SV:x}", ("jsr", "ftr"), ("jsr", "fna"), ("jsr", "fen"),
                f"move {ys(S.S_BUF)},r0", f"move {ys(S.S_INC1)},y1", ("jsr", "fl"), ("jsr", "fnz"),
                f"move y:>${SV:x},n4", "move ssh,x0", ("jmp", lab["s_filt"])]
    # ---- the note-on: the nine stages to 0, OFS = VS - VS x velocity, with G_FLG bit 1 the phases and outputs to 0
    P["ftr"] = [("label", "ftr"), *_trig(), "move a1,r1", "nop", "move x:(r1),a", "tst a", ("jcc", "eq", "ft_x"),
                "clr a", "move a,x:(r1)", f"lua (r3+${OP0:x}),r2", f"move {X('r3', G_FLG)},b", f"move {ys(S.S_VEL)},x1",
                "do #$8,${ft_l:x}",
                "clr a", f"move a,{X('r2', F_ST)}", f"move {X('r2', F_VS)},x0", "mpy -x1,x0,a", "add x0,a", f"move a,{X('r2', F_OFS)}",
                "btst #1,b1", ("jcc", "cc", "ft_n"),
                "clr a", f"move a,{X('r2', F_PH)}", f"move a,{X('r2', F_OUT)}", f"move a,{X('r2', F_O2)}",
                ("label", "ft_n"), f"lua (r2+${OPS:x}),r2", ("label", "ft_l"),
                "clr a", f"move a,{X('r2', F_ST)}",
                ("label", "ft_x"), "rts"]
    # ---- the envelopes: a falling gate -> stage 3; the nine envelopes; AMP; the pitch (fpr); a = 0 when every AMP is 0
    env1 = [("label", "env1"),
            f"move {X('r2', F_ST)},a", "cmp #4,a", ("jcc", "ge", "e1_x"),
            "move r2,b", "add a,b", "move b1,r1", f"move {X('r2', F_E)},b",
            f"move {X('r1', F_T1)},x0", f"move {X('r1', F_S1)},y0",
            "cmp x0,b", ("jcc", "ge", "e1_dn"),
            f"move {X('r2', F_FL)},x1", "cmp x1,b", "tlt x1,b",
            f"move {X('r2', F_RM)},a", "tst a", ("jcc", "eq", "e1_r"), "move y0,a", "asl #2,a,a", "move a1,y0",
            ("label", "e1_r"), "add y0,b", "cmp x0,b", "tgt x0,b", ("jmp", "e1_st"),
            ("label", "e1_dn"), "sub y0,b", "cmp x0,b", "tlt x0,b",
            ("label", "e1_st"), f"move b1,{X('r2', F_E)}", "cmp x0,b", ("jcc", "ne", "e1_x"),
            f"move {X('r2', F_ST)},a", "add #1,a", "cmp #3,a", ("jcc", "lt", "e1_w"), "add #1,a",
            ("label", "e1_w"), f"move a1,{X('r2', F_ST)}",
            ("label", "e1_x"), "rts"]
    amp1 = [("label", "amp1"),
            f"move {X('r2', F_E)},a", "move #>$100,x0", "cmp x0,a", ("jcc", "lt", "a1_z"),
            f"move {X('r2', F_BASE)},b", "sub a,b", f"move {X('r2', F_OFS)},x0", "add x0,b", "tfr b,a", ("jsr", "ex2"),
            ("label", "a1_w"), f"move a,{X('r2', F_AMP)}", "rts",
            ("label", "a1_z"), "clr a", ("jmp", "a1_w")]
    P["fen"] = [("label", "fen"),
                f"move {ys(S.S_GATE)},b", f"move {X('r3', G_PG)},a", f"move b,{X('r3', G_PG)}", "tst b", ("jcc", "ne", "fe_0"),
                "tst a", ("jcc", "eq", "fe_0"),
                f"lua (r3+${OP0:x}),r2", "move #>$3,x0", "do #$9,${fe_r:x}", f"move x0,{X('r2', F_ST)}", f"lua (r2+${OPS:x}),r2",
                ("label", "fe_r"),
                ("label", "fe_0"), f"lua (r3+${OP0:x}),r2",
                "do #$8,${fe_l:x}", ("jsr", "env1"), ("jsr", "amp1"), f"lua (r2+${OPS:x}),r2", ("label", "fe_l"),
                ("jsr", "env1"), ("jsr", "fpr"),
                f"lua (r3+${OP0:x}),r2", "clr a", "do #$8,${fe_s:x}", f"move {X('r2', F_AMP)},x0", "or x0,a", f"lua (r2+${OPS:x}),r2",
                ("label", "fe_s"), "rts", *env1]
    P["amp1"] = amp1
    # ---- the pitch factor (r2 = the pitch envelope's block): R = R0 x 2^pu, pu = (E - PC) x PK (1/65536 octave; the transpose is in R0)
    P["fpr"] = [("label", "fpr"),
                f"move {X('r2', F_E)},a", f"move {X('r3', G_PC)},x0", "sub x0,a", "move a,x0", f"move {X('r3', G_PK)},y0", "mpy y0,x0,a",
                "move a1,b", "asr #16,b,b", "add #1,b", "move b1,y1",                  # k = (pu >> 16) + 1; 2^pu = 2^k x 2^-(k x 65536 - pu)
                "asl #16,b,b", "sub a,b", "tfr b,a", ("jsr", "ex2"), "move a,x1",
                "move #>$8,a", "sub y1,a", "move a1,y1",                                # z = 8 - k (k from -4 to 5): R = (R0 x m << 8) >> z
                f"lua (r3+${OP0:x}),r2",
                "do #$8,${fp_l:x}", f"move {X('r2', F_R0)},x0", "mpy x1,x0,a", "asl #8,a,a", "asr y1,a,a", f"move a,{X('r2', F_R)}",
                f"lua (r2+${OPS:x}),r2",
                ("label", "fp_l"), "rts"]
    # ---- the noise's amplitude: NA = NZ x the AMP of the operator whose AMP word is at G_NOPA
    P["fna"] = [("label", "fna"), f"move {X('r3', G_NOPA)},r1", f"move {X('r3', G_NZ)},x0", "move x:(r1),y0", "mpy y0,x0,a",
                f"move a,{X('r3', G_NA)}", "rts"]
    # ---- 2^-(a / 65536) (0 <= a < 64 octaves) -> a (Q23; from 24 octaves the shift leaves 0 in a1); clobbers b, x0, y0
    P["ex2"] = [("label", "ex2"),
                "move a1,b", "and #>$ffff,b", "asl #7,b,b", "move b1,x0",
                f"move {X('r3', G_A2)},y0", "mpy y0,x0,b", f"move {X('r3', G_A1)},y0", "sub y0,b", "move b1,y0", "mpy y0,x0,b",
                f"add #>${ONE:x},b", "asr #16,a,a", "move a1,x0", "asr x0,b,a", "rts"]
    return P


def entries():
    """the pieces' entry addresses (their first label), and FL's"""
    import sp0 as SP
    w, _ = C0.asm_at(SP.short_items(loop_items()), FL_AT)
    return dict(fl=FL_AT, fnz=FL_AT + len(w), **{n: at for n, (at, _) in PIECES.items()})


def code(lab):
    """-> [(address, words)] for FL and the pieces (fm0's places and the free words next to them); lab: synth0's labels"""
    import sp0 as SP
    ent = entries()
    out = []
    w, _ = C0.asm_at(SP.short_items(loop_items() + noise_items()), FL_AT)
    assert FL_AT + len(w) <= FL_END, f"FL and the noise end at {FL_AT + len(w):#x}"
    out.append((FL_AT, w))
    for n, its in piece_items(lab).items():
        at, room = PIECES[n]
        its = [(x[0], ent[x[1]]) if isinstance(x, tuple) and x[0] in ("jsr", "jmp") and x[1] in ent and x[1] != n else x for x in its]
        w, _ = C0.asm_at(SP.short_items(its), at)
        assert len(w) <= room, f"FM8 piece {n} at {at:#x}: {len(w)} words > {room}"
        out.append((at, w))
    return out


def sizes(lab=None):
    lab = lab or dict(s_env2=0x2100, s_filt=0x2200)
    return [(hex(a), len(w)) for a, w in code(lab)]
