"""Stock+ for the granular and the synth on the Circuit Rhythm's DSP core 0 (MIT; RH55; the user, 2026-10-28: «Stock+ for every sound»,
«Start RH55: Stock+ for every sound (LFO, pitch envelope, waveshaping, FX for granular and synth on core 0)»; the choices: the stock's
distortion knob on them too, K7 = a waveshaper + its type, K8 = the grains' position / the synth's FM amount).  Our own code.

Core 1 plays the samples: its Stock+ (tools/pitchmod.py, voicefx.py, voicefilt.py) acts on a voice, which a granular or synth track no
longer plays (core 0 rewrites the track's 32 samples: granular0 / synth0).  Here, for those tracks, the same Stock+ on core 0, with the
same words the ARM writes for core 1 (and its own: the waveshaper), a block of 32 per track at Y:Y0 + $20 t:
  * the pitch envelope and LFO (pitchmod's RR, the same arithmetic, one track a block in turn: TICK from synth0's SY; a note-on in the
    trigger queue, which synth0's SY reads, sets E = 1 and updates its track at once: NOTE): S_PM, the pitch offset (a semitone =
    $10000) -> the synth's pitch (SPIT: both oscillators), each new grain's pitch (GPM, in 1/64 semitone);
  * the scan LFO (K8, voicefilt's: SO = depth x |phase|) -> the grains' position (GPOS: + SO x 128 of the 0..127 knob), the synth's FM
    amount (SFM: + SO);
  * the stock's distortion knob (the track's parameter $A, core 1's P:$648 on a voice: y = c2 x / (1 - c1 + c1 |x|), c1 = 1 - (1 - 0.9 d)^4,
    c2 = 1 - 0.72 c1, d the knob / 128 smoothed 1/8 a block, c1 / c2 ramped across the block; its 1 / x from a table of our own,
    1 / (4 m) for m in [0.5, 1) in 128 steps) on every granular and synth track, before the filter (SDS: the synth's mix; GDM / GDS:
    the granular's sums at the chain's start);
  * K6's filter type and pitch follow in the chains (synth0's filter, granchain's): the low-pass index + follow x the pitch in semitones
    (SLP / GLP, kept in S_LPI for the comb); 24 dB = both filters run twice (synth0 / granchain sp: their second states); the comb = both
    off (LP 127, HP 0: SHP / GHP) and the comb after;
  * after the chains (SPX, between the granular's / its chain's end and the stock's mix P:$367; granular0 / granchain `mix`): per track,
    the comb (D samples = 2 pi / the stock's cutoff curve at S_LPI, 8 .. 239; feedback 0.3 + 0.65 x the resonance / 127, voicefilt's),
    the ring mod (voicefx's), the waveshaper (voicefx's drives: 1 soft, 2 hard, 3 fold, 4 bitcrush, the gain x 16 first); on the track's
    32 samples and, for a granular track with a spread, its side part (granular0's SBY + $20 k).
A track's block is ours while its key is SPKEY (the ARM writes it last, only for a granular or synth track; 0 = core 1's Stock+ as
before); a block's state from zero once (MAGIC).  Comb buffers in shared Y above the stock's ($37310: docs/PORTADO.md): 240 words a track
from COMB_M, a granular slot's side from COMB_S.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core0 as C0  # noqa: E402

AT, END = 0x2AB0, 0x2E00                               # P (synth0's tables end at $2AA9, linein at $2E00)
TAB, TAB_END = 0x36D0, 0x3A00                          # P: the tables (granular0 multi + sp ends at $36CB, gstereo at $3A00)
Y0, SN, NT = 0x1D80, 0x20, 8                           # core 0 Y (free: docs/RECURSOS.md, RH54's audit)
(C_KEY, C_A, C_D, C_R, C_L, C_RAM, C_RST, C_KT, C_FOL, C_WT, C_WG, C_WM, C_SCR, C_SCD, C_PH, C_SPH) = range(16)
(S_E, S_PM, S_SO, S_RPH, S_PIT, S_LPI, S_CW, S_CW2, S_DD, S_C1, S_C2, S_C1S, S_C2S, S_C1D, S_C2D, S_DON) = range(16, 32)
G0 = 0x1E80
G_MAG, G_RR, G_SB, G_SC, G_X1, G_R1, G_MB, G_T, G_D, G_FB, G_SCI = range(G0, G0 + 11)
DC1, DC2, TMP = 0x1EA0, 0x1EC0, 0x1EE0                # Y: the distortion's c1 / c2 across the block, the ring's gains
COMB_M, COMB_S, COMB_N = 0x37480, 0x37C00, 240
SPKEY, MAGIC = 0x5B7A11, 0x5B0A9E
ONE = 0x7FFFFF
PAR, TRK_BUF, DIST_I, RES_I = 0x307C8, 0x304F0, 0xA, 0xD
D_MIN, D_MAX = 8, COMB_N - 1
FB_0, FB_K = round(0.3 * 0x800000), round(0.65 * 128 / 127 * 0x800000)   # voicefilt's comb feedback
D_SMOOTH, D_FLOOR, D_K, D_C2 = 0x100000, 0x20C5, 0x733333, 0x5C28F6     # the stock distortion's constants (core 1, P:$648)
MIX = 0x367
SYNC_GAP = 0
# the entries (fixed: synth0, granular0 and granchain jsr to them; sp0 is assembled after them)
ENTRIES = ("spx", "tick", "note", "spit", "sfm", "sds", "slp", "shp", "s24", "gpm", "gpos", "gdm", "gds", "glp", "ghp")


def entry(name):
    return AT + 2 * ENTRIES.index(name)


def frac(x):
    return max(-(1 << 23), min((1 << 23) - 1, round(x * (1 << 23)))) & 0xFFFFFF


def s24(v):
    v &= 0xFFFFFF
    return v - (1 << 24) if v & 0x800000 else v


def tables():
    import granchain as GCH
    curve = GCH.stock_curve()
    dt = [max(D_MIN, min(D_MAX, int(2 * math.pi / c))) if c > 0 else D_MAX for c in curve]
    rt = [round((64 / (j + 0.5)) * (1 << 23)) for j in range(128, 256)]                 # 1 / (4 m), m = (j + 0.5) / 256
    return dict(DT=dt, RT=rt)


def blk(t):
    return Y0 + SN * t


def items(tab_at, gr, part="a", spx=None):
    """gr: granular0's labels (g_save / g_rest, for SPX); part "a" (at P:AT: the entries, the hooks, the distortion) or "b" (after the
    tables at P:TAB: SPX and its effects); spx = part b's SPX (for part a's entry)"""
    import granular0 as G
    L = []

    def e(*s):
        L.extend(s)

    def yv(a):
        return f"y:>${a:x}"

    def yr(o):
        return f"y:(r1+${o:x})"

    def key_r1(lab, src="a"):
        """r1 = the block of the track in `src`'s a1 (0..7); not ours: jump to lab"""
        return [f"asl #5,{src},{src}", f"add #>${Y0:x},{src}", f"move {src}1,r1", "nop", f"move {yr(C_KEY)},{src}",
                f"move #>${SPKEY:x},x0", f"cmp x0,{src}", ("jcc", "ne", lab)]

    # ---- the entries
    e(("label", "entries"))
    for n in ENTRIES:
        e(("jmp", spx if n == "spx" else f"e_{n}"))

    # ================================================================ TICK (from SY, once a block): one track's update in turn; the
    # granular slots' pitch (for the follow); the blocks from zero once
    e(("label", "e_tick"), f"move {yv(G_MAG)},a", f"move #>${MAGIC:x},x0", "cmp x0,a", ("jcc", "eq", "tk_ok"),
      "clr a", f"move #>${Y0 + C_PH:x},r0", f"move #>${SN:x},n0", "nop",
      f"do #${NT:x},${{tk_z:x}}", "move r0,r1", "nop", f"rep #${SN - C_PH:x}", "move a,y:(r1)+", "move (r0)+n0", ("label", "tk_z"),
      f"move #>${G0:x},r0", "nop", "do #$20,${tk_z2:x}", "move a,y:(r0)+", ("label", "tk_z2"),
      f"move #>${COMB_M:x},r0", "nop", f"do #${COMB_N * (NT + 4):x},${{tk_z3:x}}", "move a,y:(r0)+", ("label", "tk_z3"),
      f"move x0,{yv(G_MAG)}",
      ("label", "tk_ok"), f"move {yv(G_RR)},a", "add #>$1,a", "and #>$7,a", "move a1,a", f"move a1,{yv(G_RR)}", ("jsr", "upd"))
    e(f"move #>${G.slot_y(0):x},r5", f"move #>${G.SLOT_N:x},n5", "nop", f"do #${G.NSLOT:x},${{tk_g:x}}",
      f"move y:(r5+${G.P_KEY:x}),a", f"move #>${G.KEY:x},x0", "cmp x0,a", ("jcc", "ne", "tk_n"),
      f"move y:(r5+${G.P_TRK:x}),a", "tst a", ("jcc", "eq", "tk_n"), "sub #>$1,a", "and #>$7,a", "move a1,a", *key_r1("tk_n"),
      f"move y:(r5+${G.P_PITCH:x}),a", f"move y:(r5+${G.P_NOTE:x}),x0", "add x0,a", "asl #16,a,a", f"move {yr(S_PM)},x0", "add x0,a",
      f"move a1,{yr(S_PIT)}", ("label", "tk_n"), "move (r5)+n5", "nop", ("label", "tk_g"), "rts")

    # ---- upd (a1 = the track): pitchmod's RR: E *= D; PM = A E + L tri(PH += R); the scan: SO = depth x |SPH += SCR|
    e(("label", "upd"), *key_r1("up_x"),
      f"move {yr(S_E)},x0", f"move {yr(C_D)},x1", "mpyr x1,x0,a", f"move a,{yr(S_E)}",
      "move a,x0", f"move {yr(C_A)},x1", "mpy x1,x0,b",
      f"move {yr(C_PH)},a", f"move {yr(C_R)},x0", "add x0,a", f"move a1,{yr(C_PH)}",
      "move a1,a", "abs a", "asl a", f"move #>${ONE:x},x0", "sub x0,a", "move a,x0",
      f"move {yr(C_L)},x1", "mac x1,x0,b", f"move b,{yr(S_PM)}",
      f"move {yr(C_SPH)},a", f"move {yr(C_SCR)},x0", "add x0,a", f"move a1,{yr(C_SPH)}",
      "move a1,a", "abs a", "move a,x1", f"move {yr(C_SCD)},x0", "mpy x1,x0,a", f"move a,{yr(S_SO)}",
      ("label", "up_x"), "rts")

    # ================================================================ NOTE (sy_q, each message: y0 = w0; keeps x1): a note-on sets E = 1
    # and updates its track now
    e(("label", "e_note"), "move y0,a", "and #>$f00000,a", "move a1,a", "move #>$900000,x0", "cmp x0,a", ("jcc", "ne", "nt_x"),
      "move y0,a", "and #>$7,a", "move a1,a", f"move a1,{yv(G_T)}", *key_r1("nt_x"),
      f"move #>${ONE:x},a", f"move a,{yr(S_E)}", f"move x1,{yv(G_X1)}", f"move {yv(G_T)},a", ("jsr", "upd"), f"move {yv(G_X1)},x1",
      ("label", "nt_x"), "rts")

    # ================================================================ the synth's hooks (r6 = its slot, y:(r6 + S_T) = the track; r5 kept)
    import synth0 as SY

    def syn_r1(lab):
        return [f"move y:(r6+${SY.S_T:x}),b", *key_r1(lab, "b")]
    # SPIT (a = the pitch, an accumulator): + PM; the pitch kept for the follow
    e(("label", "e_spit"), *syn_r1("si_x"), f"move {yr(S_PM)},x0", "add x0,a", f"move a,{yr(S_PIT)}", ("label", "si_x"), "rts")
    # SFM (a = the FM amount): + SO
    e(("label", "e_sfm"), *syn_r1("sf_x"), f"move {yr(S_SO)},x0", "add x0,a", ("label", "sf_x"), "rts")
    # SDS (at the VCA: the mix in the slot's buffer; r5 = the track's parameters): the stock's distortion
    e(("label", "e_sds"), *syn_r1("sd_x"), f"move y:(r5+${DIST_I:x}),a", ("jsr", "dset"),
      f"move y:(r6+${SY.S_BUF:x}),r0", "nop", ("jsr", "drun"), ("label", "sd_x"), "rts")
    # SLP (a = the low-pass index): + the follow; kept (0..128) for the comb; the comb: 127 (off)
    e(("label", "e_slp"), *syn_r1("sl_x"), ("jsr", "lpidx"), ("label", "sl_x"), "rts")
    # SHP (a = the high-pass index): the comb: 0 (off)
    e(("label", "e_shp"), *syn_r1("sh_x"), ("jsr", "hpidx"), ("label", "sh_x"), "rts")
    # S24 (after the first pass of the filter): a = 1 to run it again (24 dB: the second states), else 0 (and the second states zero)
    e(("label", "e_s24"), "clr a", f"move a,{yv(G_R1)}", *syn_r1("s2_z"), f"move {yr(C_KT)},a", "move #>$1,x0", "cmp x0,a",
      ("jcc", "ne", "s2_z"), f"move y:(r6+${SY.S_LON:x}),a", "tst a", ("jcc", "ne", "s2_l"))
    for o in (SY.S_LL2, SY.S_LB2):
        e("clr b", f"move b,y:(r6+${o:x})")
    e(("label", "s2_l"), f"move y:(r6+${SY.S_HON:x}),a", "tst a", ("jcc", "ne", "s2_h"))
    for o in (SY.S_HL2, SY.S_HB2):
        e("clr b", f"move b,y:(r6+${o:x})")
    e(("label", "s2_h"), "move #>$1,a", "rts", ("label", "s2_z"), "clr b")
    for o in (SY.S_LL2, SY.S_LB2, SY.S_HL2, SY.S_HB2):
        e(f"move b,y:(r6+${o:x})")
    e("clr a", "rts")

    # ================================================================ the granular's hooks
    import granchain as GCH
    # GPM (g_spawn: a = the grain's pitch in 1/64 semitone; r7 = the slot's state): + PM / 1024
    e(("label", "e_gpm"), f"move r1,{yv(G_R1)}", f"move y:(r7+${G.V_T:x}),b", "and #>$7,b", "move b1,b", *key_r1("gp_x", "b"),
      f"move {yr(S_PM)},b", "asr #10,b,b", "add b,a", ("label", "gp_x"), f"move {yv(G_R1)},r1", "rts")
    # GPOS (g_pre: a = the position knob 0..127; r7 = the slot's state): + SO x 128, at most 127
    e(("label", "e_gpos"), f"move r1,{yv(G_R1)}", f"move y:(r7+${G.V_T:x}),b", "and #>$7,b", "move b1,b", *key_r1("go_x", "b"),
      f"move {yr(S_SO)},b", "asr #16,b,b", "add b,a", "move #>$7f,x0", "cmp x0,a", "tgt x0,a",
      ("label", "go_x"), f"move {yv(G_R1)},r1", "rts")
    # GDM (the chain, before its loop): the stock's distortion on the slot's sums (CIN_BUF); GDS: on its side (CIN_SB), the same block's
    e(("label", "e_gdm"), f"move {yv(GCH.C_T)},a", "and #>$7,a", "move a1,a", f"move a1,{yv(G_T)}", *key_r1("gd_x"),
      f"move {yv(G_T)},a", "asl #5,a,a", f"add #>${PAR + DIST_I:x},a", "move a1,r0", "nop", "move y:(r0),a", ("jsr", "dset"),
      f"move {yv(GCH.CIN_BUF)},r0", "nop", ("jsr", "drun"), ("label", "gd_x"), "rts")
    e(("label", "e_gds"), f"move {yv(GCH.C_T)},a", "and #>$7,a", "move a1,a", *key_r1("gs_x"),
      f"move {yv(GCH.CIN_SB)},r0", "nop", ("jsr", "drun"), ("label", "gs_x"), "rts")
    # GLP / GHP (the chain's low-pass / high-pass index in a): as SLP / SHP; GLP also sets the chain's 24 dB flag (C24)
    # (r1 = the chain's track parameters, kept)
    e(("label", "e_glp"), f"move r1,{yv(G_R1)}", "clr b", f"move b,{yv(GCH.C24)}", f"move {yv(GCH.C_T)},b", "and #>$7,b", "move b1,b",
      *key_r1("gl_x", "b"),
      f"move {yr(C_KT)},b", "move #>$1,x0", "cmp x0,b", ("jcc", "ne", "gl_n"), f"move x0,{yv(GCH.C24)}", ("label", "gl_n"),
      ("jsr", "lpidx"), ("label", "gl_x"), f"move {yv(G_R1)},r1", "rts")
    e(("label", "e_ghp"), f"move r1,{yv(G_R1)}", f"move {yv(GCH.C_T)},b", "and #>$7,b", "move b1,b", *key_r1("gh_x", "b"),
      ("jsr", "hpidx"), ("label", "gh_x"), f"move {yv(G_R1)},r1", "rts")

    # ---- lpidx (r1 = the block, a = the index): + round(follow x the pitch in semitones) (voicefilt's); S_LPI = it in 0..128; comb: 127
    e(("label", "lpidx"), f"move {yr(C_FOL)},x0", f"move {yr(S_PIT)},b", "asr #16,b,b", "move b1,y0", "mpyr y0,x0,b", "add b,a",
      "tfr a,b", "tst b", ("jcc", "ge", "lx_0"), "clr b", ("label", "lx_0"), "move #>$80,x0", "cmp x0,b", "tgt x0,b",
      f"move b1,{yr(S_LPI)}", f"move {yr(C_KT)},b", "move #>$2,x0", "cmp x0,b", ("jcc", "ne", "lx_x"), "move #>$7f,a",
      ("label", "lx_x"), "rts")
    # ---- hpidx (r1 = the block, a = the index): comb: 0
    e(("label", "hpidx"), f"move {yr(C_KT)},b", "move #>$2,x0", "cmp x0,b", ("jcc", "ne", "hx_x"), "clr a", ("label", "hx_x"), "rts")

    # ================================================================ the stock's distortion
    # dset (r1 = the block, a = the knob 0..127): d smoothed, c1 / c2, their ramps across the block into DC1 / DC2; S_DON = d x d' (0 = off)
    e(("label", "dset"), "and #>$7f,a", "move a1,a", "asl #16,a,a", "move a,y0", f"move #>${D_SMOOTH:x},x1", f"move {yr(S_DD)},x0",
      "move x0,a", "mac -x1,x0,a", "mac x1,y0,a",
      f"move {yr(S_DD)},x1", "move a,x0", "mpy x1,x0,b", f"move a,{yr(S_DD)}", f"move b,{yr(S_DON)}",
      f"move #>${D_FLOOR:x},x0", "cmp x0,a", "tlt x0,a",
      "move a,x0", f"move #>${D_K:x},x1", "mpy x1,x0,a", f"move #>${ONE:x},y1", "eor y1,a", "move a,x0", "mpy x0,x0,a", "move a,x0",
      "mpy x0,x0,a", "eor y1,a",                                                          # a = c1
      f"move {yr(S_C1)},x0", f"move a,{yr(S_C1)}", "sub x0,a", "asr #5,a,a", f"move a,{yr(S_C1D)}", f"move x0,{yr(S_C1S)}",
      f"move {yr(S_C1)},y0", f"move #>${ONE:x},a", f"move #>${D_C2:x},x0", "mac -y0,x0,a",   # a = c2
      f"move {yr(S_C2)},x0", f"move a,{yr(S_C2)}", "sub x0,a", "asr #5,a,a", f"move a,{yr(S_C2D)}", f"move x0,{yr(S_C2S)}",
      f"move {yr(S_C1S)},a", f"move {yr(S_C1D)},x0", f"move {yr(S_C2S)},b", f"move {yr(S_C2D)},y0", f"move #>${DC1:x},r4",
      f"move #>${DC2:x},r2", "nop",
      "do #$20,${ds_r:x}", "move a,y:(r4)+", "add x0,a", "move b,y:(r2)+", "add y0,b", ("label", "ds_r"), "rts")
    # drun (r1 = the block, r0 = 32 samples): y = 4 (c2 x 2^s) T[m], m = D 2^s in [0.5, 1), D = 1 - c1 + c1 |x|
    e(("label", "drun"), f"move {yr(S_DON)},a", "tst a", ("jcc", "eq", "dr_x"),
      f"move #>${DC1:x},r4", f"move #>${DC2:x},r2", "nop",
      "do #$20,${dr_l:x}",
      "move y:(r0),y0", "move y0,a", "abs a", "move a,x0", "move y:(r4)+,x1", f"move #>${ONE:x},a", "sub x1,a", "mac x1,x0,a",
      "clb a,b", "normf b1,a", "asr #15,a,a", f"add #>${tab_at['RT'] - 128:x},a", "move a1,r3", "move y:(r2)+,x0",
      "mpy y0,x0,a", "normf b1,a", "move p:(r3),x1", "move a,y0", "mpy x1,y0,a", "asl #2,a,a", "move a,y:(r0)+",
      ("label", "dr_l"),
      ("label", "dr_x"), "rts")

    if part == "a":
        return L
    L = []
    # ================================================================ SPX: after the engines and their chains, before the stock's mix
    e(("label", "e_spx"), ("jsr", gr["g_save"]), f"move {yv(G_MAG)},a", f"move #>${MAGIC:x},x0", "cmp x0,a", ("jcc", "ne", "sx_x"))
    for t in range(NT):
        e(f"move #>${t:x},a", ("jsr", "px_t"))
    e(("label", "sx_x"), ("jsr", gr["g_rest"]), ("jmp", MIX))
    # px_t (a1 = the track)
    e(("label", "px_t"), f"move a1,{yv(G_T)}", *key_r1("pt_x"),
      f"move {yv(G_T)},a", "asl #6,a,a", f"add #>${TRK_BUF:x},a", "movep y:<<$ffffd0,b", "asl #5,b,b", "add b,a",
      f"move a1,{yv(G_MB)}", "clr a", f"move a,{yv(G_SB)}")
    # the side: a running granular slot of this track with a spread (r5 = its controls, r4 = its side, G_SCI = its comb)
    e(f"move #>${G.slot_y(0):x},r5", f"move #>${G.SLOT_N:x},n5", f"move #>${G.SBY:x},r4", "move #>$20,n4", f"move #>${COMB_S:x},x0",
      f"move x0,{yv(G_SCI)}", "nop", f"do #${G.NSLOT:x},${{ps_l:x}}",
      f"move y:(r5+${G.P_KEY:x}),a", f"move #>${G.KEY:x},x0", "cmp x0,a", ("jcc", "ne", "ps_n"),
      f"move y:(r5+${G.P_SPRD:x}),a", "tst a", ("jcc", "eq", "ps_n"),
      f"move y:(r5+${0x10 + G.V_ACT:x}),a", "tst a", ("jcc", "eq", "ps_n"), f"move y:(r5+${0x10 + G.V_ON:x}),a", "tst a", ("jcc", "eq", "ps_n"),
      f"move y:(r5+${0x10 + G.V_T:x}),a", "and #>$7,a", "move a1,a", f"move {yv(G_T)},x0", "cmp x0,a", ("jcc", "ne", "ps_n"),
      f"move r4,{yv(G_SB)}", f"move {yv(G_SCI)},x0", f"move x0,{yv(G_SC)}",
      ("label", "ps_n"), "move (r5)+n5", "move (r4)+n4", f"move {yv(G_SCI)},a", f"add #>${COMB_N:x},a", f"move a1,{yv(G_SCI)}", "nop",
      ("label", "ps_l"))
    # the comb: D = DT[S_LPI], the feedback from the resonance; the track's buffer COMB_M + 240 t, the side's COMB_S + 240 k
    e(f"move {yr(C_KT)},a", "move #>$2,x0", "cmp x0,a", ("jcc", "ne", "pt_r"),
      f"move {yr(S_LPI)},a", f"add #>${tab_at['DT']:x},a", "move a1,r3", "nop", "move p:(r3),x0", f"move x0,{yv(G_D)}",
      f"move {yv(G_T)},a", "asl #5,a,a", f"add #>${PAR + RES_I:x},a", "move a1,r3", "nop", "move y:(r3),a", "and #>$7f,a", "move a1,a",
      "asl #16,a,a", "move a,y0", f"move #>${FB_K:x},x1", "mpy x1,y0,a", f"add #>${FB_0:x},a", f"move a,{yv(G_FB)}",
      f"move {yv(G_T)},a", "tfr a,b", "asl #8,a,a", "asl #4,b,b", "sub b,a", f"add #>${COMB_M:x},a", "move a1,r3",
      f"move {yv(G_D)},x0", f"move {yv(G_FB)},x1", f"lua (r1+${S_CW:x}),r2", f"move {yv(G_MB)},r0", "nop", ("jsr", "comb"),
      f"move {yv(G_SB)},a", "tst a", ("jcc", "eq", "pt_r"), f"move {yv(G_SC)},r3", f"lua (r1+${S_CW2:x}),r2", "move a1,r0",
      f"move {yv(G_D)},x0", f"move {yv(G_FB)},x1", "nop", ("jsr", "comb"),
      ("label", "pt_r"))
    # the ring
    e(f"move {yr(C_RAM)},a", "tst a", ("jcc", "eq", "pt_w"),
      f"move {yr(S_RPH)},b", f"move {yr(C_RST)},x0", f"move {yr(C_RAM)},y1", f"move #>${TMP:x},r2", "nop",
      "do #$20,${rg_l:x}",
      "add x0,b", "move b1,y0", "move y0,b", "tfr b,a", "abs a", "asl a", f"sub #>${ONE:x},a", "move a,x1", "abs a", "move a,y0",
      "mpy -x1,y0,a", "add x1,a", "add x1,a", "move a,x1", "mpy y1,x1,a", "sub y1,a", f"add #>${ONE:x},a", "move a,y:(r2)+",
      ("label", "rg_l"), f"move b1,{yr(S_RPH)}",
      f"move {yv(G_MB)},r0", "nop", ("jsr", "rmul"), f"move {yv(G_SB)},a", "tst a", ("jcc", "eq", "pt_w"), "move a1,r0", "nop",
      ("jsr", "rmul"),
      ("label", "pt_w"))
    # the waveshaper
    e(f"move {yr(C_WT)},a", "tst a", ("jcc", "eq", "pt_x"), f"move {yv(G_MB)},r0", "nop", ("jsr", "wshape"),
      f"move {yv(G_SB)},a", "tst a", ("jcc", "eq", "pt_x"), "move a1,r0", "nop", ("jsr", "wshape"),
      ("label", "pt_x"), "rts")
    # comb (r0 = 32 samples, r3 = its buffer, r2 -> its write index, x0 = D, x1 = the feedback): y = x + fb y[n - D]
    e(("label", "comb"), "move y:(r2),n2", f"move #>${COMB_N:x},y1",
      "do #$20,${cb_l:x}",
      "move n2,a", "sub x0,a", "tfr a,b", "add y1,b", "tst a", "tlt b,a", "move a1,n3", "nop", "move y:(r3+n3),y0",
      "move y:(r0),a", "mac x1,y0,a", "move a,y:(r0)+", "move n2,n3", "nop", "move a,y:(r3+n3)",
      "move n2,a", "add #>$1,a", "cmp y1,a", ("jcc", "lt", "cb_w"), "clr a", ("label", "cb_w"), "move a1,n2", "nop",
      ("label", "cb_l"), "move n2,y:(r2)", "rts")
    # rmul (r0 = 32 samples): x TMP
    e(("label", "rmul"), f"move #>${TMP:x},r2", "nop", "do #$20,${rm_l:x}", "move y:(r2)+,x0", "move y:(r0),y0", "mpy y0,x0,a",
      "move a,y:(r0)+", ("label", "rm_l"), "rts")
    # wshape (r1 = the block, r0 = 32 samples): voicefx's drives on Y
    bodies = {
        1: ["move y:(r0),y0", "mpy y0,x0,a", "asl #4,a,a", "move a,x1", "move a,y0", "mpy x1,y0,a", "move a,y0", "mpy -x1,y0,a",
            "add x1,a", "add x1,a", "add x1,a", "asr a", "move a,y:(r0)+"],
        2: ["move y:(r0),y0", "mpy y0,x0,a", "asl #4,a,a", "move a,y:(r0)+"],
        3: ["move y:(r0),y0", "mpy y0,x0,a", "asl #3,a,a", "add #>$400000,a", "move a1,y0", "move y0,a", "abs a", "asl a",
            f"sub #>${ONE:x},a", "move a,y:(r0)+"],
        4: ["move y:(r0),y0", "mpy y0,x0,a", "asl #4,a,a", "move a,x1", "move x1,a", "and y1,a", "move a,y:(r0)+"],
    }
    e(("label", "wshape"), f"move {yr(C_WG)},x0", f"move {yr(C_WM)},y1", f"move {yr(C_WT)},a")
    for t in (1, 2, 3, 4):
        e(("label", f"ws{t}"), f"cmp #>${t:x},a", ("jcc", "ne", f"ws{t + 1}"), f"do #$20,${{w{t}_l:x}}", *bodies[t], ("label", f"w{t}_l"),
          "rts")
    e(("label", "ws5"), "rts")
    return L


VALID_PAIRS = {("x0", "x0"), ("y0", "y0"), ("x1", "x0"), ("y1", "y0"), ("x0", "y1"), ("y0", "x0"), ("x1", "y0"), ("y1", "x1")}


def lint(its):
    """every mpy / mpyr / mac / macr's operand pair is one the DSP has (dsptool's asm turns the others into mpysu without a word)"""
    for it in its:
        if isinstance(it, str):
            m = re.match(r"(mpyr?|macr?)\s+-?(\w+),(\w+),", it)
            assert not m or (m.group(2), m.group(3)) in VALID_PAIRS, it
    return its


def short_items(its):
    """the one-word forms of «move X:/Y:(Rn+d)» where dsptool's disassembler knows them (rhdsppatch.short)"""
    import rhdsppatch as DP
    return [DP.short(it) if isinstance(it, str) else it for it in lint(its)]


def code(gr):
    """-> (part a's words at P:AT, labels, the tables and part b at P:TAB, {table: address})"""
    tb = tables()
    at, tab_at, tw = TAB, {}, []
    for k in ("DT", "RT"):
        tab_at[k] = at
        at += len(tb[k])
        tw += tb[k]
    wb, lb = C0.asm_at(short_items(items(tab_at, gr, "b")), at)
    assert at + len(wb) <= TAB_END, f"sp0's part b ends at {at + len(wb):#x}"
    w, labels = C0.asm_at(short_items(items(tab_at, gr, "a", spx=lb["e_spx"])), AT)
    assert AT + len(w) <= END, f"sp0 ends at {AT + len(w):#x}"
    labels.update(lb)
    for n in ENTRIES:
        assert w[entry(n) - AT:entry(n) - AT + 2] == [0x0AF080, labels[f"e_{n}"]], n
    return w, labels, tw + wb, tab_at


def segs(gr):
    """for granular0's extra: our code at P:AT, the tables at P:TAB"""
    w, labels, tw, _ = code(gr)
    return [(AT, w), (TAB, tw)]


def check(gr):
    """dsptool reads every word back (no mpysu: voicefx.check)"""
    import voicefx
    w, labels, tw, tab_at = code(gr)
    n = len(tables()["DT"]) + len(tables()["RT"])
    return voicefx.check(w, AT) + voicefx.check(tw[n:], TAB + n)


# ================================================================ the model (the tests'): the DSP's arithmetic, bit for bit
def _sat(acc):
    return max(-(1 << 23), min((1 << 23) - 1, acc >> 24))


def _a1(acc):
    return s24(acc >> 24)


def _mpy(x, y):
    return 2 * s24(x) * s24(y)


def _rnd(acc):
    """the DSP's convergent rounding of an accumulator to a1"""
    lo, hi = acc & 0xFFFFFF, acc >> 24
    if lo > 0x800000 or (lo == 0x800000 and hi & 1):
        hi += 1
    return hi << 24


def _mpyr(x, y):
    return _rnd(_mpy(x, y))


def _clb_norm(acc):
    """clb a,b / normf b1,a on a positive accumulator: -> (shift s, acc << s) with acc's a1 in [$400000, $7FFFFF]"""
    s = 0
    if acc <= 0:
        return 0, acc
    while acc < (0x400000 << 24):
        acc <<= 1
        s += 1
    while acc >= (0x800000 << 24):
        acc >>= 1
        s -= 1
    return s, acc


class Model:
    """the tracks' blocks: ctl[t] = its 16 control words (the ARM's); state per track; the granular slots' (key, track, pitch, note,
    spread, act, on, side) for TICK and SPX"""

    def __init__(self):
        self.tab = tables()
        self.st = [dict() for _ in range(NT)]
        self.ctl = [[0] * 16 for _ in range(NT)]
        self.rr = 0
        self.mag = False
        self.combm = [[0] * COMB_N for _ in range(NT)]
        self.combs = [[0] * COMB_N for _ in range(4)]
        self.res = [0] * NT                                    # the tracks' resonance knobs (their parameter $D), for the comb

    def on(self, t):
        return self.ctl[t][C_KEY] == SPKEY

    def S(self, t):
        st = self.st[t]
        if not st:
            st.update({k: 0 for k in ("e", "pm", "so", "rph", "pit", "lpi", "cw", "cw2", "dd", "c1", "c2", "c1s", "c2s", "c1d", "c2d", "don",
                                      "ph", "sph")})
        return st

    def tick(self, gslots=()):
        """gslots: [(track, pitch, note)] of the running granular slots (key and track set), in slot order"""
        if not self.mag:
            self.mag = True
            for t in range(NT):
                self.st[t] = {}
                self.S(t)
                self.ctl[t][C_PH] = self.ctl[t][C_SPH] = 0
            self.combm = [[0] * COMB_N for _ in range(NT)]
            self.combs = [[0] * COMB_N for _ in range(4)]
            self.rr = 0
        self.rr = (self.rr + 1) & 7
        self.upd(self.rr)
        for t, pitch, note in gslots:
            if self.on(t):
                st = self.S(t)
                st["pit"] = s24(((s24(pitch) + s24(note)) << 16) + st["pm"])

    def upd(self, t):
        if not self.on(t):
            return
        c, st = self.ctl[t], self.S(t)
        st["e"] = _sat(_mpyr(c[C_D], st["e"]))
        b = _mpy(st["e"], c[C_A])
        st["ph"] = s24(st["ph"] + c[C_R])
        tri = _sat((abs(st["ph"]) << 25) - (ONE << 24))
        b += _mpy(c[C_L], tri)
        st["pm"] = _sat(b)
        st["sph"] = s24(st["sph"] + c[C_SCR])
        st["so"] = _sat(_mpy(min(ONE, abs(st["sph"])), c[C_SCD]))

    def note(self, w0):
        if (w0 & 0xF00000) == 0x900000:
            t = w0 & 7
            if self.on(t):
                self.S(t)["e"] = ONE
                self.upd(t)

    def set_ctl(self, t, words):
        self.ctl[t] = list(words)
        st = self.S(t)
        st["ph"], st["sph"] = words[C_PH], words[C_SPH]

    def lpidx(self, t, idx):
        c, st = self.ctl[t], self.S(t)
        sem = s24(st["pit"]) >> 16
        idx += _a1(_mpyr(sem, c[C_FOL]))
        st["lpi"] = max(0, min(0x80, idx))
        return 0x7F if c[C_KT] == 2 else idx

    def hpidx(self, t, idx):
        return 0 if self.ctl[t][C_KT] == 2 else idx

    def dset(self, t, knob):
        st = self.S(t)
        y0 = (knob & 0x7F) << 16
        d = st["dd"]
        a = (d << 24) - _mpy(D_SMOOTH, d) + _mpy(D_SMOOTH, y0)
        d1 = _sat(a)
        st["don"] = _sat(_mpy(d, d1))
        st["dd"] = d1
        if a < (D_FLOOR << 24):
            a = D_FLOOR << 24
        a = _mpy(_sat(a), D_K)                                   # positive: eor y1,a = a1 ^ $7FFFFF, a2 / a0 kept
        x0 = (a >> 24) ^ ONE
        x0 = _sat(_mpy(x0, x0))
        a = _mpy(x0, x0)
        c1 = (a >> 24) ^ ONE
        st["c1d"] = _sat(((c1 - st["c1"]) << 24) >> 5)
        st["c1s"], st["c1"] = st["c1"], c1
        c2 = _sat((ONE << 24) - _mpy(c1, D_C2))
        st["c2d"] = _sat(((c2 - st["c2"]) << 24) >> 5)
        st["c2s"], st["c2"] = st["c2"], c2
        self.ramp1 = [s24(st["c1s"] + i * s24(st["c1d"])) for i in range(32)]
        self.ramp2 = [s24(st["c2s"] + i * s24(st["c2d"])) for i in range(32)]

    def drun(self, t, buf):
        st = self.S(t)
        if st["don"] == 0:
            return list(buf)
        out = []
        for i, x in enumerate(buf):
            x = s24(x)
            c1, c2 = self.ramp1[i], self.ramp2[i]
            a = ((ONE - c1) << 24) + _mpy(c1, min(ONE, abs(x)))
            s, m = _clb_norm(a)
            j = (m >> 24) >> 15
            r = self.tab["RT"][j - 128]
            a = _mpy(c2, x)
            a = a << s if s >= 0 else a >> -s
            y0 = _sat(a)
            out.append(_sat(_mpy(r, y0) << 2))
        return out

    def comb(self, t, buf, side=None):
        """side: the granular slot k (its comb), else the track's"""
        c, st = self.ctl[t], self.S(t)
        D = self.tab["DT"][st["lpi"]]
        res = self.res[t] & 0x7F
        fb = _sat(_mpy(res << 16, FB_K) + (FB_0 << 24))
        cb = self.combm[t] if side is None else self.combs[side]
        key = "cw" if side is None else "cw2"
        w = st[key]
        out = []
        for x in buf:
            rd = w - D
            if rd < 0:
                rd += COMB_N
            y = _sat((s24(x) << 24) + _mpy(fb, cb[rd]))
            out.append(y)
            cb[w] = y
            w = w + 1 if w + 1 < COMB_N else 0
        st[key] = w
        return out

    def ring(self, t):
        c, st = self.ctl[t], self.S(t)
        b, g = st["rph"], []
        y1 = s24(c[C_RAM])
        for _ in range(32):
            b = s24(b + c[C_RST])
            a = (abs(b) << 25) - (ONE << 24)
            x1 = _sat(a)
            y0 = _sat(abs(a))
            a = -_mpy(x1, y0) + (x1 << 24) + (x1 << 24)
            x1 = _sat(a)
            a = _mpy(y1, x1) - (y1 << 24) + (ONE << 24)
            g.append(_sat(a))
        st["rph"] = b
        return g

    @staticmethod
    def rmul(buf, g):
        return [_sat(_mpy(g[i], buf[i])) for i in range(32)]

    def wshape(self, t, buf):
        c = self.ctl[t]
        typ, x0, y1 = c[C_WT], c[C_WG], c[C_WM]
        out = []
        for x in buf:
            if typ == 1:
                u = _sat(_mpy(x, x0) << 4)
                y0 = _sat(_mpy(u, u))
                a = -_mpy(u, y0) + 3 * (u << 24)
                out.append(_sat(a >> 1))
            elif typ == 2:
                out.append(_sat(_mpy(x, x0) << 4))
            elif typ == 3:
                a = (_mpy(x, x0) << 3) + (0x400000 << 24)
                y0 = _a1(a)
                out.append(_sat((abs(y0) << 25) - (ONE << 24)))
            elif typ == 4:
                u = _sat(_mpy(x, x0) << 4)
                out.append(s24((u & y1) & 0xFFFFFF))
            else:
                out.append(s24(x))
        return out

    def spx(self, t, buf, side=None, sidek=None):
        """the post effects of track t on its 32 samples (and its side) -> (buf, side)"""
        if not self.on(t):
            return buf, side
        c = self.ctl[t]
        if c[C_KT] == 2:
            buf = self.comb(t, buf)
            if side is not None:
                side = self.comb(t, side, sidek)
        if c[C_RAM] != 0:
            g = self.ring(t)
            buf = self.rmul(buf, g)
            if side is not None:
                side = self.rmul(side, g)
        if c[C_WT] != 0:
            buf = self.wshape(t, buf)
            if side is not None:
                side = self.wshape(t, side)
        return buf, side
