"""4-operator FM, an engine of the synth on the Circuit Rhythm's DSP core 0 (MIT; RD38; the user, 2026-11-04: the synth engines of
CIRCUIT-HACKS, FM first).  CIRCUIT-HACKS' FM (vcf21_dsp: the compact loop, operators 4 to 1, the refined sine, the smoothed AMP, the
averaged feedback; fmeng: the 16 parameters, the 16 algorithms, the starters), ours on both firmwares; the envelopes on the DSP here.

Where: synth0's slot (r6 = its Y block) calls FMW in place of its envelope (s_env2): FMW runs that envelope as before, then, when the slot's
FM block is on (G_KEY), writes the slot's 32 samples into the track's buffer and goes on to synth0's filter (s_filt): no VCA of synth0
(the operators' envelopes are the level, as Hacks' FMVCA), no Stock+ distortion.  Off: back to synth0, nothing changed.
The slot's FM block: X:FB0 + $80 s (= 2 r6 + $1C00), four operator blocks of FMS words (op 1 first) and the globals at + GB:
  per operator (the ARM's: R0, L, A, DH, DR, K, M1..M4, HC; the DSP's: OUT, PH, R, AMP, AS, O2, E, ST):
    R = R0 x (1 + 8 PD E4) (the pitch drop of the kick algorithms; PD = 0 otherwise), PH += R x the slot's increment x 128;
    u = PH + 4 (sum M_kj OUT_j + HC x O2); P = 4 (u - u |u|), 0.75 P + 0.25 P |P|; OUT = AS x P; the sample = sum K_k OUT_k;
    AS += (AMP - AS) / 32 each sample; AMP = E x L each block;
  the envelope E each block (Hacks' every millisecond, here every block): attacking (ST) E += A until 1; then with the note held (synth0's
  S_GATE) E x DH (DH = 1: held); let go: E x DR (ST off);
  a note-on of the slot's track (X:NF + t, set by rtdc's DCN): every operator attacking, a percussive one (DH < 1) from 0, and with
  G_FLG bit 1 the phases and outputs from 0;
  the noise: NA = NZ x the envelope of operator NOP, added after the FM (an LCG);
  all the envelopes resting and none attacking: the track's samples zero (no loop: no CPU).
Core 0: P:FL_AT (the sample loop and the noise), P:FMW_AT .. (the block's control, in four pieces), X:FB0.., X:NF..; Y:SV (n4 kept).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core0 as C0  # noqa: E402

FB0, FBS = 0x5000, 0x80                               # X: a slot's block (free X RAM: RD37)
NF = 0x5200                                           # X: a note-on flag per track (rtdc's DCN)
FMS = 20                                              # an operator's block
(F_OUT, F_PH, F_R, F_AMP, F_K, F_M1, F_M2, F_M3, F_M4, F_AS, F_O2, F_HC, F_E, F_ST, F_R0, F_L, F_A, F_DH, F_DR) = range(19)
GB = 4 * FMS                                          # the globals
(G_KEY, G_FLG, G_PD, G_NZ, G_NOP, G_NA, G_NS) = range(GB, GB + 7)
FMKEY = 0x0F4A11
SV = 0x1F68                                           # core 0 Y (above rtdc's, below c0probe's $1F70 alias words)
FL_AT = 0x98                                          # the sample loop (rtdc ends at $97 with the note flags)
PIECES = (0x2DDA, 0x36AB, 0x2FDA, 0x2D21, 0x39ED)     # FMW, its note-on, envelopes, R / noise, rest (38, 37, 38, 31, 19 words free in RH69)
FMW_AT = PIECES[0]
ONE = 0x7FFFFF
SILENT = 0x000400                                     # sum of E + ST below this: resting
TRK_S = 0x24                                          # synth0's S_T (the slot's track)
LCG_A, LCG_C = 1664525 & 0xFFFFFF, 1013904223 & 0xFFFFFF


def _syn():
    import synth0
    return synth0


def _trig_poly():
    """(RH72, OPT poly) the note-on flag of the slot itself (poly0's FTR + s), not of its track"""
    import rhbuild
    if not rhbuild.OPT.get("poly"):
        return None
    import poly0
    S = _syn()
    return ["move r6,a", f"sub #>${S.Y0:x},a", "asr #6,a,a", f"add #>${poly0.FTR:x},a"]


def loop_items():
    """FL (a = 0: resting, the samples zero): the sample loop (r3 = the block, r0 = the 32 samples, y1 = the increment), then the noise
    (NA <> 0)"""
    S = _syn()
    L = [("label", "fl"), "tst a", ("jcc", "ne", "fl_go"), "clr a", "rep #$20", "move a,y:(r0)+", "rts",        # resting: zeros
         ("label", "fl_go"), f"lua (r3+${3 * FMS:x}),r2", "move r3,r4", f"move #${FMS:x},n4",
         "do #$20,${fl_s:x}", "clr b", "do #$4,${fl_o:x}",
         f"move x:(r2+${F_AMP:x}),a", f"move x:(r2+${F_AS:x}),x0", "sub x0,a", "asr #5,a,a", "add x0,a", f"move a,x:(r2+${F_AS:x})",
         f"move x:(r2+${F_R:x}),x0", "mpy x0,y1,a", "asl #7,a,a", f"move x:(r2+${F_PH:x}),x0", "add x0,a", f"move a1,x:(r2+${F_PH:x})",
         "move a1,x1",
         f"move x:(r2+${F_M1:x}),x0", "move x:(r4)+n4,y0", ("words", [0x46CCD0]),               # mpy y0,x0,a x:(r4)+n4,y0
         f"move x:(r2+${F_M2:x}),x0", ("words", [0x46CCD2]),                                    # mac y0,x0,a x:(r4)+n4,y0
         f"move x:(r2+${F_M3:x}),x0", ("words", [0x46CCD2]),
         f"move x:(r2+${F_M4:x}),x0", "mac y0,x0,a", "move r3,r4",
         f"move x:(r2+${F_HC:x}),x0", f"move x:(r2+${F_O2:x}),y0", "mac y0,x0,a",
         "asl #2,a,a", "add x1,a", "move a1,x1",
         "move x1,a", "abs a", "move a,y0", "mpy -x1,y0,a", "add x1,a", "asl #2,a,a",
         "abs a a,x0", "move a,y0", "mpy y0,x0,a", "sub x0,a", "asr #2,a,a", "add x0,a", "move a,x0",
         f"move x:(r2+${F_AS:x}),y0", ("words", [0x45E2D0]),                                    # mpy y0,x0,a x:(r2),x1
         ("words", [0x182200]),                                                                 # move a,x:(r2) a,y0
         f"move x1,x:(r2+${F_O2:x})",
         f"move x:(r2+${F_K:x}),x0", f"lua (r2-${FMS:x}),r2",
         "mac y0,x0,b", ("label", "fl_o"), f"lua (r3+${3 * FMS:x}),r2", "move b,y:(r0)+", ("label", "fl_s"),
         # the noise
         f"move x:(r3+${G_NA:x}),y1", "move y1,a", "tst a", ("jcc", "eq", "fl_x"),
         f"lua (r0-$20),r0", f"move x:(r3+${G_NS:x}),x1", "nop",
         "do #$20,${fn_e:x}",
         f"move #>${LCG_A:x},y0", "mpy x1,y0,a", "asr a", "move a0,x1", "move x1,a", f"add #>${LCG_C:x},a", "move a1,x1",
         "move x1,x0", "mpy x0,y1,a", "move y:(r0),x0", "add x0,a", "move a,y:(r0)+", ("label", "fn_e"),
         f"move x1,x:(r3+${G_NS:x})",
         ("label", "fl_x"), "rts"]
    del S
    return L


def ctl_items(lab):
    """the block's control: FMW and its pieces; lab = synth0's labels (s_env2, s_filt) and FL's address"""
    S = _syn()
    ys = lambda o: f"y:(r6+${o:x})"                                                  # noqa: E731
    p0 = [("label", "fmw"), ("jsr", lab["s_env2"]),
          "move r6,a", "asl a", "add #>$1c00,a", "move a1,r3",
          f"move x:(r3+${G_KEY:x}),a", f"move #>${FMKEY:x},x0", "cmp x0,a", ("jcc", "eq", "fw_go"), "rts",
          ("label", "fw_go"), f"move n4,y:>${SV:x}", ("jsr", PIECES[1]), ("jsr", PIECES[2]), ("jsr", PIECES[3]), ("jsr", PIECES[4]),
          f"move {ys(S.S_BUF)},r0", f"move {ys(S.S_INC1)},y1",
          ("jsr", FL_AT), f"move y:>${SV:x},n4", "move ssh,x0", ("jmp", lab["s_filt"])]
    # ---- piece 1: the note-on flag of the slot's track
    p1 = [("label", "ftr"), *(_trig_poly() or [f"move {ys(S.S_T)},a", "and #>$7,a", f"add #>${NF:x},a"]), "move a1,r1", "nop", "move x:(r1),a", "tst a",
          ("jcc", "eq", "ft_x"), "clr a", "move a,x:(r1)", "move r3,r2", f"move x:(r3+${G_FLG:x}),b", f"move #>${ONE:x},x1",
          "do #$4,${ft_l:x}",
          f"move x1,x:(r2+${F_ST:x})", f"move x:(r2+${F_DH:x}),a", "cmp x1,a", ("jcc", "eq", "ft_s"), f"move a0,x:(r2+${F_E:x})",
          ("label", "ft_s"), "btst #1,b1", ("jcc", "cc", "ft_n"),
          f"move a0,x:(r2+${F_PH:x})", f"move a0,x:(r2+${F_OUT:x})", f"move a0,x:(r2+${F_O2:x})",
          ("label", "ft_n"), f"lua (r2+${FMS:x}),r2", ("label", "ft_l"),
          ("label", "ft_x"), "rts"]
    # ---- piece 2: the envelopes, AMP
    p2 = [("label", "fen"), f"move {ys(S.S_GATE)},b", "move r3,r2", f"move #>${ONE:x},x1",
          "do #$4,${fe_l:x}",
          f"move x:(r2+${F_E:x}),x0", "tst b", ("jcc", "ne", "fe_g"),
          f"move b,x:(r2+${F_ST:x})", f"move x:(r2+${F_DR:x}),y0", "mpy y0,x0,a", ("jmp", "fe_a"),
          ("label", "fe_g"), f"move x:(r2+${F_ST:x}),a", "tst a", ("jcc", "eq", "fe_h"),
          "move x0,a", f"move x:(r2+${F_A:x}),x0", "add x0,a", "cmp x1,a", ("jcc", "lt", "fe_a"),
          "move x1,a", f"move a0,x:(r2+${F_ST:x})", ("jmp", "fe_a"),
          ("label", "fe_h"), f"move x:(r2+${F_DH:x}),y0", "mpy y0,x0,a",
          ("label", "fe_a"), f"move a,x:(r2+${F_E:x})", "move a,x0", f"move x:(r2+${F_L:x}),y0", "mpy y0,x0,a",
          f"move a,x:(r2+${F_AMP:x})", f"lua (r2+${FMS:x}),r2", ("label", "fe_l"), "rts"]
    # ---- piece 3: R (the pitch drop), the noise's amplitude
    p3 = [("label", "fpr"), f"move x:(r3+${G_PD:x}),x0", f"move x:(r3+${3 * FMS + F_E:x}),y0", "mpy y0,x0,a", "move a,y1", "move r3,r2",
          "do #$4,${fp_l:x}",
          f"move x:(r2+${F_R0:x}),x0", "mpy x0,y1,b", "asl #3,b,b", "add x0,b", f"move b,x:(r2+${F_R:x})", f"lua (r2+${FMS:x}),r2",
          ("label", "fp_l"),
          "move r3,b", f"move x:(r3+${G_NOP:x}),x0", "add x0,b", "move b1,r1", f"move x:(r3+${G_NZ:x}),x0", f"move x:(r1+${F_E:x}),y0",
          "mpy y0,x0,a", f"move a,x:(r3+${G_NA:x})", "rts"]
    # ---- piece 4: the resting test (a = 0: resting)
    p4 = [("label", "frs"), "clr a", "move r3,r2", "do #$4,${fs_l:x}", f"move x:(r2+${F_E:x}),x0", "add x0,a", f"move x:(r2+${F_ST:x}),x0", "add x0,a",
          f"lua (r2+${FMS:x}),r2", ("label", "fs_l"),
          f"move #>${SILENT:x},x0", "cmp x0,a", "tlt x0,a", ("jcc", "ge", "fp_x"), "clr a",
          ("label", "fp_x"), "rts"]
    del S
    return [p0, p1, p2, p3, p4]


def code(lab):
    """-> [(address, words)] for FL and the four pieces; lab: synth0's labels"""
    import sp0 as SP
    out = []
    w, _ = C0.asm_at(SP.short_items(loop_items()), FL_AT)
    assert FL_AT + len(w) <= 0x100, f"FL ends at {FL_AT + len(w):#x}"
    out.append((FL_AT, w))
    room = {0x2DDA: 38, 0x2FDA: 38, 0x36AB: 37, 0x2D21: 31, 0x39ED: 19}
    for at, its in zip(PIECES, ctl_items(lab)):
        w, _ = C0.asm_at(SP.short_items(its), at)
        assert len(w) <= room[at], f"FM piece at {at:#x}: {len(w)} words > {room[at]}"
        out.append((at, w))
    return out


def sizes(lab=None):
    lab = lab or dict(s_env2=0x2100, s_filt=0x2200)
    return [(hex(a), len(w)) for a, w in code(lab)]
