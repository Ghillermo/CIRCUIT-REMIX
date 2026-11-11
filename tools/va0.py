"""CIRCUIT-HACKS' VA oscillators in the Circuit Rhythm's synth on DSP core 0, in place of synth0's own two (MIT; RD41; the user, 2026-11-05:
«Se puede sustituir el antiguo sinte de 2OP por el VA de Hacks?» -> «Sí, RD41»).  Ours on both firmwares: Hacks' vcf21_dsp oscillator v3
(OSC3 + SINEFIX + SUPERSAW + BLEP + FOLDLIM + SCALEMAC + DUAL + TYPEZONE), here as a reduced port: its oscillators only, synth0 keeps the queue,
the glide, the stock's pitch knob, the envelope (env2), the VCA, the filter, Stock+ (sp0) and the polyphony (poly0).

Where: synth0's slot (OPT va): at s_play, in place of its passes A-D, the SUB and the noise, its waves and its old envelope; its tables keep
their places (WT zeros).  The start / length morph and unison of RH58 (synth0 sl) go: the morph is the VA's own.
Per slot an X block (XB0 + XS s, s = (r6 - Y0) / $40): OSC 1 at + 0, OSC 2 at + O2, Hacks' words at Hacks' offsets (vcf21_dsp OSB0 / OS2B0):
  OSC 1: +0 TUNE (semitones) +1 FINE (1/128 semitone) +2 WAVE (0..126: sine 0, triangle 42, saw 84, square 126) +3 PW (0..100, 50 the middle:
         the shape) +5 ENVP (-64..63: the envelope -> both pitches, +-24 semitones) +6 ENVW (-> the shape) +8 ENVM (-> the morph)
         +21 DFLAGS (bit 1: the dual oscillator); the block's own: +10 phase +11 increment +12 fold drive / 8 +13 the triangle's curve / 2
         +14 the pulse's threshold +15..18 the four waves' weights +28..33 the supersaw's side phases +35..37 D, 3 D, 6 D +42 the sides' weight
  OSC 2: +0 TUNE2 +1 FINE2 +2 WAVE2 +3 PW2 +4 MIX (0..127: OSC 1 -> OSC 2) +6 FM (OSC 2 -> OSC 1's phase) +7 RING +9 BITSYNC (0..127: 7 zones
         of Hacks' TYPEZONE knob: 0 none, 1 soft sync (every 1..8 cycles), 2 xor, 3 or, 4 nor, 5 and, 6 nand, the position in the zone);
         the block's own: +5 the zone +8 the position +10 phase +11 the signed increment +12..18 as OSC 1's +19 the increment +20 the
         direction +21 the sync's period +22 its count +23 the last sample +24..27 FM, MIX, the position, RING scaled
         +28..33 / +35..37 / +42 as OSC 1's; +47 VMAG (a block without it: zeros, PW / PW2 50, then VMAG).
Per block: the pitches (synth0's: the note glided, the stock's pitch knob, C_OCT, Stock+'s; + TUNE, FINE, ENVP x the envelope) through synth0's
s_inc; Hacks' osc_ctrl (the shape m = (PW - 50) / 50 + ENVW x env: the fold drive (limited by the pitch), the triangle's curve, the pulse's
threshold, the supersaw's detune and weights; the morph q = WAVE + ENVM x env, two neighbouring waves crossfaded); OSC 2's interactions.
Per sample: Hacks' loops (one oscillator, or OSC 2 then OSC 1 with the soft sync, FM, mix, ring, bitwise), x 2 (synth0's level); a wave whose
weight is 0 is skipped (Hacks computes all four: the same sum; the supersaw's side phases wait while the saw's weight is 0).
V2 (RD42, OPT va = 2; the user on RD41: «suena bien, hay algo de aliasing»): Hacks' level (x 1: synth0's x 2 clipped the supersaw and the
folded sine, the aliasing at -36 dB), and the pulse's rising edge's polyBLEP at the phase's wrap (-u; Hacks' -v = -(u - thr) is right only at 50 %:
-20..-36 dB at other widths, now -58..-83); RD41 = V1, as it was.
V3 (RD43, OPT va = 3; the user on RD42: «mejor la primera, aunque no es perfecto» -> «ok, y reduce el máximo de sierras si alguna vez resulta
un problema. incluye también FM, sync y bitwise»): the 2-sample polyBLEP becomes a 4-sample BLEP (the integrated cubic B-spline, no delay: a
sample within 2 increments of a wrap gets the residual at its distance x = (1 - |u|) / inc: 1 - 4x/3 + 2x^3/3 - x^4/4 for x < 1, (2 - x)^4 / 12
for 1 <= x < 2; va_bs4 at VB_AT); Hacks' SC52.4 interactions (vcf21_dsp use_osc4): the hard sync (zone 1: OSC 2 starts again at -1 + the
fraction since OSC 1's wrap x its increment; the zone's position = OSC 2 up 0..31.75 semitones; the soft sync goes), FM both ways (64 the centre:
right OSC 2 -> OSC 1, left OSC 1 -> OSC 2, 4 t^2 up to half, then to 50 / 50), OSC 1's BLEP with its effective increment (|its modulated phase's
step|), the bitwise term through a one-pole low-pass (k = 1/2); the two-oscillator loop at DL_AT.  A block of V1 / V2 (VMAGIC) is set up again.
Not here: Hacks' LFO terms (LFOP / LFOW / LFOM: no LFO on the synth yet), the paraphonic second note, the wavetable, the VA-drum, the sampler.
"""
from __future__ import annotations

XB0, XS, O2 = 0x4E00, 0x60, 0x30                      # core 0 X (free: RD37's map, below the stock's X:$4F85)
CTL_AT, CTL_END = 0x3948, 0x39ED                      # P: va_ctl in synth0 sl's place (its piece "a"; fm8c0's ex2 at $39ED)
VMAGIC = 0x7A5A01
VMAGIC3 = 0x7A5A03                                    # (V3) the blocks' magic: FM's default 64 (the centre)
DL_AT, DL_END = 0x2D7B, 0x2DDA                        # (V3) P: the two-oscillator loop (after fxroute's FXZ; synth0 sl's MW's place; fm0's FMW at $2DDA)
VB_AT, VB_END = 0x3F92, 0x3FE0                        # (V3) P: va_bs4 (synth0 sl's UNI's place; the loader at $3FE0)


def fmcap():
    """(RD44, OPT fmcap; the user, 2026-11-07: «el FM ha perdido volumen desde el antialiasing en las notas agudas?»): OSC 1's effective
    increment under FM (|its modulated phase's step|), the one its BLEP uses, held to 3 x its own increment.  Unlimited, a deep FM's step
    made almost every sample «within 2 increments of a wrap»: the BLEP corrected the ramp everywhere (measured on the model against a 16 x
    oversampled reference: a saw under FM -4.8 dB at its fundamental at C7, -0.7 at C6).  Held to 3 x: -1.5 / -0.2, the error against
    the reference as before at every note (2 x gave the level back whole but 1-2 dB more error at C5).  va_cap after va_bs4 (VB_AT),
    called from the loop (the same size as the two moves it replaces)."""
    import rhbuild
    return bool(rhbuild.OPT.get("fmcap"))
SIDES3 = (0, 1, 4, 5)                                 # (V3) the side saws kept: +-D, +-6D (the +-3D pair goes: 5 saws, the user's «reduce el máximo de sierras»)
O12 = 38                                              # (V3) OSC 2's block: the OSC 1 -> OSC 2 FM amount
O1P, BWS, PMP, ISV = 39, 40, 41, 44                   # (V3) OSC 1's block (Hacks' O1_PREV, BW_S, PM_PREV, INC_SV): OSC 1's last output, the bitwise
                                                      #   term smoothed, OSC 1's last modulated phase, its increment kept
(TUNE, FINE, WAVE, PW, MIX, ZONE, ENVW, FM, POS, BSR, PH, INC, FD, CV, TH, W0) = range(16)
ENVP, ENVM = 5, 8                                     # OSC 1's (OSC 2's +5 / +8 are the zone and the position)
RING = 7
DFL, IU, DIR, SPER, SCNT, OUT2, FMS, MIXS, POSS, RINGS = 21, 19, 20, 21, 22, 23, 24, 25, 26, 27
SS_PH, SS_D, SS_W = 28, 35, 42
VMAG = 47
DUAL = 2
SSD1 = 0x0257EB                                       # round(0.0183 x 2^23): Hacks' SS_D1
FOLD_K = 0x020000
FMOD = 6                                              # OSC 1's ENVW (+6); OSC 2's +6 is FM


def fmword():
    """(RH84, OPT fmword; found 2026-11-08 checking RD44): V3 read OSC 2's FM amount from +7 (FM in the names' tuple is 7, RING's word),
    while the ARM (synthpage.VA_WORDS) and CIRCUIT-HACKS (vcf21_dsp: OS2B0 +6 FM, +7 RING) put FM at +6: on RH77-RH83 the Synth page's
    FM knob (K6) did nothing and RING (Shift + K6) set both the ring and the FM (its value - 64: RING 0 = FM fully left, both ways at the
    ends, as soon as the second oscillator was on).  With fmword V3 reads FM from +6 (FMOD)."""
    import rhbuild
    return bool(rhbuild.OPT.get("fmword"))


def os2():
    """(RD45, OPT os2; the user, 2026-11-08: «Study oversampling» -> «Yes, RD45»): the two-oscillator loop at 2x for every slot on two
    oscillators while X:OS2G holds OS2KEY (set from the computer: tools/rhos2.py; zero after power-on = 1x): its increments halved where synth0's are
    copied into the blocks (so va_ctl's supersaw detune and fold limit follow the inner rate), 64 inner samples into the slot's Y buffer
    OB + OBS s (HIST words of history first), then a 23-tap halfband (OS2_COEF, 12 non-zero words at X:XC + the centre 1/2) down to the 32 of
    S_BUF.  Measured on the model: a saw under FM 90, C7 -4.7 -> -0.7 dB at its fundamental, the aliasing below 8 kHz C6 -37 -> -71 dB, C7
    -15 -> -41; the cost 1.5-1.9 x the loop.  Only with the second oscillator (DUAL): one oscillator stays 1x."""
    import rhbuild
    return bool(rhbuild.OPT.get("os2"))


OS2G, OS2KEY = 0x5258, 0x2C5A02                                # (os2) X: the switch (2x for every slot on two oscillators)
OS2S = 0x40                                                     # (os2slot) X:$5258 + $40 s = slot s's key (= x:(r6 + KEYD))
XC, OBS, HIST = 0x5300, 0x80, 22                               # (os2) X: the 12 coefficients; Y: the slots' buffers (22 + 64 words each)
OB = 0x3400                                                     # (os2) Y:$3400 + $80 s (= 2 r6 + OB - 2 Y0: synth0's slot blocks at $1A00 + $40 s)
OS2_COEF = (0xFFCF30, 0x00C402, 0xFDDF07, 0x04FB1D, 0xF49318, 0x27FA46, 0x27FA46, 0xF49318, 0x04FB1D, 0xFDDF07, 0x00C402, 0xFFCF30)
# (the halfband: scipy.signal.remez(23, [0, 16 / 96, 0.5 - 16 / 96, 0.5], [1, 0]), odd taps 0, the centre 1/2: flat to 16 kHz, -0.9 dB at
#  20 kHz, -6 dB at 24 kHz, 70 dB down from 32 kHz; the even taps n = 0, 2, .. 22 rounded to 24 bits)
OSI_P = ((0x36C4, 12), (0x3F44, 12), (0x39E4, 9))            # (os2) P: va_osi in three free pieces of RH84, chained
OSD_P = ((0x3FD4, 12), (0x2007, 9))                           # (os2) P: va_osd in two
OSI_AT, OSD_AT = OSI_P[0][0], OSD_P[0][0]
DX_AT = 0x25EE - 44                                            # (os2) P: the decimator at the end of the free tail before fm8c0's amp1
DX_END = 0x25EE


def os2slot():
    """(RH85, OPT os2 = 2; the user, 2026-11-09: «Per-track switch»): the 2x loop of RD45 per slot, the key at X:OS2G + OS2S s (written by the
    ARM: esel OPT va2x, OS2KEY for a slot whose track has the 2x pad on while core 0 has room, else 0), read as x:(r6 + KEYD) (r6 = synth0's slot at
    Y:$1A00 + $40 s); va_osi in one piece at OSI2_AT (poly0 polycap 3 frees the place); a slot at 1x (one oscillator, no key) clears its
    history (Y:2 r6 .. + HIST - 1) every block, so it enters 2x from zeros.  The halfband's coefficients at X:XC are the ARM's too."""
    import rhbuild
    o = rhbuild.OPT.get("os2")
    return o == 2 and o is not True


OSI2_AT, OSI2_END = 0x365A, 0x3675                             # (os2slot) P: after poly0's piece B (polycap 3), before fm8c0's fen


def ratio2():
    """(RH85, OPT ratio2; the user, 2026-11-10: «Hacks version sounds much cleaner» -> «Yes, port it»): OSC 2's FINE word in 1/256 semitone
    (OSC 1's stays 1/128): the ARM (synthpage) sends OSC 2's pitch as CIRCUIT-HACKS' RATIO2 does, an exact harmonic ratio of OSC 1 (0.25, 0.5,
    1, 2 .. 31: round(12 log2 r x 256)) + the detune (+-50 cents), the TUNE word 0.  Equal-tempered semitones put FM / sync's sidebands off the
    harmonics (+19 st = 2.997: -24 dB off them at C3 under FM 96; ratio 3: -57)"""
    import rhbuild
    return bool(rhbuild.OPT.get("ratio2"))


def key_addr(s):
    """(os2slot) slot s's key in core 0's X"""
    return OS2G + OS2S * s


def fm2():
    """OSC 2's FM word: +6 with fmword, else V3's +7 (RH77-RH83)"""
    return FMOD if fmword() else FM


def block_words(v=1, **kw):
    """{X offset: word} for a slot's block from Hacks' code values (OSC 1's names plain, OSC 2's with a 2: tune2, wave2, ...; dual=1); v = the
    version (V3: its magic, FM 64 = none by default)"""
    o1 = dict(tune=TUNE, fine=FINE, wave=WAVE, pw=PW, envp=ENVP, envw=ENVW, envm=ENVM)
    o2 = dict(tune2=TUNE, fine2=FINE, wave2=WAVE, pw2=PW, mix=MIX, fm=fm2(), ring=RING, bitsync=BSR)
    d = dict(pw=50, pw2=50, **({"fm": 64} if int(v) >= 3 else {}))
    d.update(kw)
    w = {o: 0 for o in range(2 * O2)}
    for k, val in d.items():
        if k in o1:
            w[o1[k]] = val & 0xFFFFFF
        elif k in o2:
            w[O2 + o2[k]] = val & 0xFFFFFF
        elif k == "dual":
            w[DFL] = DUAL if val else 0
        else:
            raise KeyError(k)
    w[O2 + VMAG] = VMAGIC3 if int(v) >= 3 else VMAGIC
    return w


# ================================================================ the DSP
def _helpers(S, ys):
    env = f"move {ys(S.S_ENV)},y0"

    def mod(off, scale, blk="r3"):                     # b = the depth (OSC 1's block) x the envelope (x scale)
        L = [f"move x:({blk}+${off:x}),b", "asl #17,b,b", "move b,x0", env, "mpy y0,x0,b"]
        if scale != 0x7FFFFF:
            L += ["move b,x0", f"move #>${scale:x},y0", "mpy y0,x0,b"]
        return L
    return mod


def _envx():
    import rhbuild
    return bool(rhbuild.OPT.get("envx"))


def items(S, ys, y, v=1):
    """the inline part at synth0's s_play (r6 = the slot, r5 = the track's parameters; ends at synth0's e_vca) and va_wv / va_bs; va_ctl is
    at CTL_AT (ctl_items)"""
    X1 = lambda o: f"x:(r3+${o:x})"                    # noqa: E731
    X2 = lambda o: f"x:(r4+${o:x})"                    # noqa: E731
    R1 = lambda o: f"x:(r1+${o:x})"                    # noqa: E731
    R2 = lambda o: f"x:(r2+${o:x})"                    # noqa: E731
    mod = _helpers(S, ys)
    v = int(v)
    v2, v3 = v >= 2, v >= 3
    L = []
    # ---- the blocks: r1 = OSC 1's, r2 = OSC 2's (X); a new block from zeros
    L += ["move r6,a", f"sub #>${S.Y0:x},a", "move a1,b", "asr b", "add b,a", f"add #>${XB0:x},a", "move a1,r1", f"add #>${O2:x},a", "move a1,r2",
          "nop", f"move {R2(VMAG)},a", f"move #>${VMAGIC3 if v3 else VMAGIC:x},x0", "cmp x0,a", ("jcc", "eq", "va_ok"),
          "clr a", "move r1,r0", "nop", f"rep #${2 * O2:x}", "move a,x:(r0)+", "move #>$32,a", f"move a,{R1(PW)}", f"move a,{R2(PW)}",
          *(["move #>$40,a", f"move a,{R2(fm2())}"] if v3 else []),
          f"move x0,{R2(VMAG)}",
          ("label", "va_ok")]
    if v3:                                                                     # (V3) the zone and its position first (the sync's sweep)
        L += [f"move {R2(BSR)},x0", "move x0,a", "asl #3,a,a", "sub x0,a", "move a1,b", "and #>$7f,b", f"move b1,{R2(POS)}", "asr #7,a,a",
              f"move a1,{R2(ZONE)}"]
    # ---- the pitches: synth0's (G_T1) + TUNE, FINE, ENVP x the envelope (Hacks' +-24 semitones) -> s_inc (S_INC1 / S_INC2)
    for blk, inc in (("r1", S.S_INC1), ("r2", S.S_INC2)):
        L += [f"move {y(S.G_T1)},a", f"move x:({blk}+${TUNE:x}),b", "asl #16,b,b", "add b,a", f"move x:({blk}+${FINE:x}),b",
              "asl #8,b,b" if ratio2() and blk == "r2" else "asl #9,b,b",
              "add b,a",
              *([f"move {R2(ZONE)},b", "cmp #>$1,b", ("jcc", "ne", "va_nsw"), f"move {R2(POS)},b", "asl #14,b,b", "add b,a",
                 ("label", "va_nsw")] if v3 and blk == "r2" else []),
              *mod(ENVP, 0x180000, "r1"), "add b,a", f"lua (r6+${inc:x}),r4", ("jsr", "s_inc")]
    L += ["move r1,r3", "move r2,r4", "nop",
          *([("jsr", OSI2_AT if os2slot() else OSI_AT)] if v3 and os2() else
            [f"move {ys(S.S_INC1)},x0", f"move x0,{X1(INC)}", f"move {ys(S.S_INC2)},x0", f"move x0,{X2(IU)}", f"move x0,{X2(INC)}"]),
          ("jsr", CTL_AT)]
    # ---- one oscillator
    L += [f"move {X1(DFL)},a", f"and #>${DUAL:x},a", ("jcc", "ne", "va_dual"),
          *([f"move {ys(S.S_INC1)},x0", f"move x0,{X1(INC)}"] if v3 and os2() else []),   # (os2) 1x here, whatever va_osi saw
          f"move {ys(S.S_BUF)},r0", "move r3,r4", "nop",
          "do #$20,${va_se:x}", f"move {X1(INC)},x0", f"move {X1(PH)},a", "add x0,a", f"move a1,{X1(PH)}", "move a1,x1", "clr a",
          ("jsr", "va_wv"), *([] if v2 else ["asl a"]), "move a,y:(r0)+", ("label", "va_se"),
          ("jmp", "e_vca")]
    if v3:                                                                     # (V3) two: OSC 2's controls, the amounts, FM's curve; the loop at DL_AT
        L += [("label", "va_dual"), "move r4,r1", "nop", ("jsr", CTL_AT), f"move {X2(IU)},x0", f"move x0,{X2(INC)}", "move #>$20800,y1"]
        envx = _envx()
        if envx:                                                               # (RH80, OPT envx) the envelope x synth0's C_GS / C_G2 / C_G1
            L += [f"move {ys(S.S_ENV)},y0", "move #0,x1"]                      # on the mix, the ring, the FM (0 at least, before the scale)
        for src, dst in ((MIX, MIXS), (RING, RINGS), (POS, POSS)):
            L += [f"move {X2(src)},a", "asl #16,a,a"]
            if envx and src != POS:
                L += [f"move {ys(S.C_GS if src == MIX else S.C_G2)},b", "asl #17,b,b", "move b,x0", "mac y0,x0,a", "tst a", "tlt x1,a"]
            L += ["move a,x0", "mac x0,y1,a", f"move a,{X2(dst)}"]
        L += [f"move {X2(fm2())},a", "sub #>$40,a", "asl #17,a,a"]
        if envx:
            L += [f"move {ys(S.C_G1)},b", "asl #17,b,b", "move b,x0", "mac y0,x0,a"]
        L += ["move a,x0", "move x0,b", "abs b", "move #>$400000,y0", "cmp y0,b",
              ("jcc", "gt", "va_fh"), "asl b", "move b,y0", "mpy y0,y0,b", "clr a", ("jmp", "va_fs"),
              ("label", "va_fh"), "move b,a", "sub y0,a", "move #>$7fffff,b", "sub a,b",
              ("label", "va_fs"), "move a,y0", "move x0,a", "tst a", "move y0,a", ("jcc", "ge", "va_ft"), "move b,a", "move y0,b",
              ("label", "va_ft"), f"move b,{X2(FMS)}", f"move a,{X2(O12)}",
              *([("jmp", OSD_AT)] if os2() else [f"move {ys(S.S_BUF)},r0", "nop", ("jmp", DL_AT)])]
        return L + wv_items(v) + bw_items()
    # ---- two: OSC 2's controls (its shape, morph; the signed increment, the zone, the amounts), then the loop
    L += [("label", "va_dual"), "move r4,r1", "nop", ("jsr", CTL_AT),
          f"move {X2(IU)},a", f"move {X2(DIR)},b", "tst b", ("jcc", "eq", "va_ip"), "neg a", ("label", "va_ip"), f"move a,{X2(INC)}",
          f"move {X2(BSR)},x0", "move x0,a", "asl #3,a,a", "sub x0,a", "move a1,b", "and #>$7f,b", f"move b1,{X2(POS)}", "asr #7,a,a",
          f"move a1,{X2(ZONE)}",
          "move #>$20800,y1"]
    for src, dst in ((MIX, MIXS), (FM, FMS), (RING, RINGS), (POS, POSS)):
        L += [f"move {X2(src)},a", "asl #16,a,a", "move a,x0", "mac x0,y1,a", f"move a,{X2(dst)}"]
    L += [f"move {X2(POS)},a", "lsr #4,a", "add #>$1,a", f"move a,{X2(SPER)}",
          f"move {ys(S.S_BUF)},r0", "nop",
          "do #$20,${va_de:x}",
          f"move {X2(INC)},x0", f"move {X2(PH)},a", "add x0,a", f"move a1,{X2(PH)}", "move a1,x1", "clr a", ("jsr", "va_wv"),
          f"move a,{X2(OUT2)}",
          f"move {X1(PH)},y1", f"move {X1(INC)},x0", "move y1,a", "add x0,a", f"move a1,{X1(PH)}", "move a1,x1",
          "move x1,a", "cmp y1,a", ("jcc", "ge", "va_ns"),                         # OSC 1 wrapped: a master cycle
          f"move {X2(ZONE)},a", "cmp #>$1,a", ("jcc", "ne", "va_ns"),
          f"move {X2(SCNT)},a", "add #>$1,a", f"move {X2(SPER)},x0", "cmp x0,a", ("jcc", "lt", "va_sk"),
          f"move {X2(INC)},a", "neg a", f"move a,{X2(INC)}", f"move {X2(DIR)},a", "eor #>$1,a", f"move a,{X2(DIR)}", "clr a",
          ("label", "va_sk"), f"move a,{X2(SCNT)}",
          ("label", "va_ns"),
          f"move {X2(OUT2)},y0", f"move {X2(FMS)},x0", "mpy y0,x0,b", "asl #3,b,b", "move x1,a", "add b,a", "move a1,x1", "clr a",
          "move r4,n4", "move r3,r4", ("jsr", "va_wv"), "move n4,r4",
          "move a,x1", f"move {X2(OUT2)},y0",
          "move y0,b", "sub x1,b", "move b,y1", f"move {X2(MIXS)},x0", "mpy x0,y1,b", "move x1,a", "add b,a",
          f"move {X2(RING)},b", "tst b", ("jcc", "eq", "va_nr"),
          f"move {X2(OUT2)},x0", "mpy x1,x0,b", "asl #1,b,b", "sub a,b", "move b,y1", f"move {X2(RINGS)},x0", "mpy x0,y1,b", "add b,a",
          ("label", "va_nr"),
          f"move {X2(ZONE)},b", "cmp #>$2,b", ("jcc", "lt", "va_nb"),
          "move a,y1", "move x1,a", f"move {X2(OUT2)},x0",
          "cmp #>$3,b", ("jcc", "lt", "va_bx"), ("jcc", "eq", "va_bo"), "cmp #>$4,b", ("jcc", "eq", "va_bn"), "cmp #>$5,b", ("jcc", "eq", "va_ba"),
          "and x0,a", "not a", ("jmp", "va_bd"),
          ("label", "va_bx"), "eor x0,a", ("jmp", "va_bd"),
          ("label", "va_bo"), "or x0,a", ("jmp", "va_bd"),
          ("label", "va_bn"), "or x0,a", "not a", ("jmp", "va_bd"),
          ("label", "va_ba"), "and x0,a",
          ("label", "va_bd"), "move a1,x0",
          "move x0,a", "move y1,b", "sub b,a", "move a,x0", f"move {X2(POSS)},y0", "mpy y0,x0,a", "move y1,b", "add b,a",
          ("label", "va_nb"), *([] if v2 else ["asl a"]), "move a,y:(r0)+", ("label", "va_de"),
          ("jmp", "e_vca")]

    return L + wv_items(v)


def dl_items(lab):
    """(V3) the two-oscillator loop at DL_AT (r3 = OSC 1's block, r4 = OSC 2's, r0 = the buffer; lab = the main's labels: va_wv, e_vca): Hacks'
    SC52.4 order: OSC 1's phase (its wrap: the hard sync), OSC 2 (+ OSC 1 -> OSC 2), OSC 1 (+ OSC 2 -> OSC 1, its BLEP with the effective
    increment), the mix, ring, the bitwise term smoothed"""
    X1 = lambda o: f"x:(r3+${o:x})"                    # noqa: E731
    X2 = lambda o: f"x:(r4+${o:x})"                    # noqa: E731
    WV = lab["va_wv"]
    return [
        "do n0,${dl_e:x}" if os2() else "do #$20,${dl_e:x}",
        f"move {X1(PH)},y1", f"move {X1(INC)},x0", "move y1,a", "add x0,a", f"move a1,{X1(PH)}", "move a1,y0",
        f"move {X2(PH)},b", f"move {X2(INC)},x1", "add x1,b", "move y0,a", "cmp y1,a", ("jcc", "ge", "dl_hs"),
        f"move {X2(ZONE)},a", "cmp #>$1,a", ("jcc", "ne", "dl_hs"),
        "bchg #23,y0", "move y0,a", "andi #$fe,ccr", "rep #$18", "div x0,a", "move a0,y0", "mpy x1,y0,b", "move b,y0", "bchg #23,y0", "move y0,b",
        ("label", "dl_hs"),
        f"move b1,{X2(PH)}", f"move {X2(O12)},x0", f"move {X1(O1P)},y0", "mpy y0,x0,a", "asl #3,a,a", "add b,a", "move a1,x1", "clr a",
        ("jsr", WV),
        f"move a,{X2(OUT2)}", f"move {X1(PH)},x1",
        f"move {X2(OUT2)},y0", f"move {X2(FMS)},x0", "mpy y0,x0,b", "asl #3,b,b", "move x1,a", "add b,a", "move a1,x1",
        f"move {X1(PMP)},y0", f"move x1,{X1(PMP)}", "move x1,b", "sub y0,b", "move b1,y0",
        *((("jsr", lab["va_cap"]),) if "va_cap" in lab else ("move y0,b", "abs b")),
        f"move {X1(INC)},y0", f"move y0,{X1(ISV)}", f"move b,{X1(INC)}", "clr a",
        "move r4,n4", "move r3,r4", ("jsr", WV), "move n4,r4",
        f"move {X1(ISV)},y0", f"move y0,{X1(INC)}", "move a,x1", f"move x1,{X1(O1P)}", f"move {X2(OUT2)},y0",
        "move y0,b", "sub x1,b", "move b,y1", f"move {X2(MIXS)},x0", "mpy x0,y1,b", "move x1,a", "add b,a",
        f"move {X2(RING)},b", "tst b", ("jcc", "eq", "dl_nr"),
        f"move {X2(OUT2)},x0", "mpy x1,x0,b", "asl #1,b,b", "sub a,b", "move b,y1", f"move {X2(RINGS)},x0", "mpy x0,y1,b", "add b,a",
        ("label", "dl_nr"), ("jsr", lab["va_bw"]), "move a,y:(r0)+", ("label", "dl_e"),
        ("jmp", DX_AT if os2() else lab["e_vca"])]


def osi_parts(S, ys):
    """(os2) va_osi (r3 / r4 = OSC 1's / OSC 2's blocks, r6 = the slot): synth0's increments into the blocks, halved when the slot runs at
    2x (the second oscillator on and the switch X:OS2G = OS2KEY); va_osd / va_dx tell the mode from OSC 1's increment (halved = 2x).  Three
    parts at OSI_P (the jumps absolute)"""
    (a1, _), (a2, _), (a3, _) = OSI_P
    return [
        [f"move {ys(S.S_INC1)},x0", f"move {ys(S.S_INC2)},y0", f"move x:(r3+${DFL:x}),a", f"move x:>${OS2G:x},b", f"and #>${DUAL:x},a",
         ("jcc", "eq", a3), ("jmp", a2)],
        [f"cmp #>${OS2KEY:x},b", ("jcc", "ne", a3), "move x0,a", "asr a", "move a,x0", "move y0,a", "asr a", "move a,y0", ("jmp", a3)],
        [f"move x0,x:(r3+${INC:x})", f"move y0,x:(r4+${IU:x})", f"move y0,x:(r4+${INC:x})", "rts"]]


def osi2_items(S, ys):
    """(os2slot) va_osi at OSI2_AT (r3 / r4 = OSC 1's / OSC 2's blocks, r6 = the slot): synth0's increments into the blocks, halved with the
    second oscillator on and the slot's key x:(r6 + KEYD) = OS2KEY; at 1x the slot's history Y:2 r6 .. + HIST - 1 = 0 (va_osd / va_dx tell
    the mode from OSC 1's increment, as RD45)"""
    keyd = OS2G - S.Y0
    assert keyd == 0x3858 and OB == 2 * S.Y0 and OBS == 2 * S.SN, (hex(keyd), hex(OB), hex(S.SN))
    return [
        f"move {ys(S.S_INC1)},x0", f"move {ys(S.S_INC2)},y0", f"move x:(r3+${DFL:x}),a", f"and #${DUAL:x},a", f"move x:(r6+${keyd:x}),b",
        ("bcc", "eq", "o_1x"), f"cmp #>${OS2KEY:x},b", ("bcc", "ne", "o_1x"),
        "move x0,a", "asr a", "move a,x0", "move y0,a", "asr a", "move a,y0", ("bra", "o_st"),
        ("label", "o_1x"), "move r6,a", "asl a", "move a1,r0", "clr a", f"rep #${HIST:x}", "move a,y:(r0)+",
        ("label", "o_st"), f"move x0,x:(r3+${INC:x})", f"move y0,x:(r4+${IU:x})", f"move y0,x:(r4+${INC:x})", "rts"]


def osd_parts(S, ys):
    """(os2) va_osd: the loop's buffer and count (2x: the slot's buffer after its history, 64), then the loop; two parts at OSD_P"""
    (a1, _), (a2, _) = OSD_P
    return [
        [f"move {ys(S.S_BUF)},r0", "move #$20,n0", f"move {ys(S.S_INC1)},a", f"move x:(r3+${INC:x}),x0", "cmp x0,a", ("jcc", "eq", DL_AT),
         "move r6,a", ("jmp", a2)],
        ["asl a", f"add #>${OB - 2 * S.Y0 + HIST:x},a", "move a1,r0", "move #$40,n0", ("jmp", DL_AT)]]


def dx_items(S, ys, e_vca):
    """(os2) va_dx at DX_AT, the loop's end: 1x = on to e_vca; 2x = the halfband (12 even taps from X:XC, the centre x 1/2, rounded) from the
    slot's buffer to S_BUF, then its last HIST words to the front (the next block's history); the XY MACs hand-encoded (dsptool's assembler
    has no ALU + XY form): D098D0 = mpy y0,x0,a x:(r0)+,x0 y:(r4)+n4,y0, D098D2 = mac (the same moves)"""
    return [
        f"move {ys(S.S_INC1)},a", f"move x:(r3+${INC:x}),x0", "cmp x0,a", ("jcc", "eq", e_vca),
        "move r6,a", "asl a", *([f"add #>${OB - 2 * S.Y0:x},a"] if OB != 2 * S.Y0 else []), "move a1,r4", "move a1,r3",
        f"move #>${XC:x},r0", "move #$2,n4", "move #$2,n1",
        "lua (r4+$c),r1", "lua (r4+$1),r4", f"move {ys(S.S_BUF)},r2", "move #>$400000,y1",
        "do #$20,${dc_e:x}",
        "move x:(r0)+,x0 y:(r4)+n4,y0",
        ("words", [0xD098D0]),
        "rep #$a",
        ("words", [0xD098D2]),
        "mac y0,x0,a y:(r1)+n1,y0",
        f"move #>${XC:x},r0",
        "macr y1,y0,a",
        "lua (r4-$16),r4",
        "move a,y:(r2)+",
        ("label", "dc_e"),
        "lua (r4-$1),r4", "nop",
        f"do #${HIST:x},${{hc_e:x}}", "move y:(r4)+,y0", "move y0,y:(r3)+", ("label", "hc_e"),
        ("jmp", e_vca)]


def bw_items():
    """(V3) va_bw (in the main; the loop at DL_AT calls it): the bitwise zones, the term (bitwise - base) smoothed (Hacks' s += (d - s) / 2)"""
    X1 = lambda o: f"x:(r3+${o:x})"                    # noqa: E731
    X2 = lambda o: f"x:(r4+${o:x})"                    # noqa: E731
    return [
        ("label", "va_bw"), f"move {X2(ZONE)},b", "cmp #>$2,b", ("jcc", "lt", "bw_x"),
        "move a,y1", "move x1,a", f"move {X2(OUT2)},x0",
        "cmp #>$3,b", ("jcc", "lt", "bw_bx"), ("jcc", "eq", "bw_bo"), "cmp #>$4,b", ("jcc", "eq", "bw_bn"), "cmp #>$5,b", ("jcc", "eq", "bw_ba"),
        "and x0,a", "not a", ("jmp", "bw_bd"),
        ("label", "bw_bx"), "eor x0,a", ("jmp", "bw_bd"),
        ("label", "bw_bo"), "or x0,a", ("jmp", "bw_bd"),
        ("label", "bw_bn"), "or x0,a", "not a", ("jmp", "bw_bd"),
        ("label", "bw_ba"), "and x0,a",
        ("label", "bw_bd"), "move a1,x0",
        "move x0,a", "move y1,b", "sub b,a", f"move {X1(BWS)},b", "sub b,a", "asr a", "add b,a", f"move a,{X1(BWS)}",
        "move a,x0", f"move {X2(POSS)},y0", "mpy y0,x0,a", "move y1,b", "add b,a",
        ("label", "bw_x"), "rts"]


def vb_items():
    """(V3) va_bs4 at VB_AT: a +-= 2 y1 h, h = half the 4-sample BLEP's residual at the distance from the wrap (b = |u| + 2 inc >= 1, x0 = inc,
    y0 = u: its sign; r1, r2, n2 keep x0, y0, x1)"""
    return [
        "move x0,r1", "move y0,r2", "move x1,n2",
        "asr b", "sub #>$400000,b", "move b1,b", "andi #$fe,ccr", "rep #$18", "div x0,b", "move b0,x0",          # q = (|u| + 2 inc - 1) / 2 inc
        "move #>$400000,b", "cmp x0,b", ("jcc", "le", "vb_nr"),
        "move x0,b", "asl b", "move b,x0", "mpy x0,x0,b", "move b,x0", "mpy x0,x0,b", "move b,x0", "move #>$55555,y0", "mpy y0,x0,b",
        ("jmp", "vb_ap"),                                                      # far (1 <= x < 2): t = 2 q, h = t^4 / 24
        ("label", "vb_nr"),                                                    # near (x < 1): t = 1 - (2 q - 1) = x, h = 1/2 - t (2/3 - t^2 (1/3 - t / 8))
        "move x0,b", "asl b", "bclr #23,b1", "neg b", "add #>$7fffff,b", "move b,x0", "mpy x0,x0,b", "move b,y0",
        "move x0,b", "asr #3,b,b", "neg b", "add #>$2aaaab,b", "move b,x1", "mpy x1,y0,b", "neg b", "add #>$555555,b", "move b,x1",
        "mpy x1,x0,b", "neg b", "add #>$400000,b",
        ("label", "vb_ap"), "move b,y0", "move r2,b", "tst b", ("jcc", "lt", "vb_ad"),
        "mpy -y1,y0,b", ("jmp", "vb_x"),
        ("label", "vb_ad"), "mpy y1,y0,b",
        ("label", "vb_x"), "asl b", "add b,a", "move r1,x0", "move n2,x1", "rts"] + (
        # (fmcap) va_cap: b = min(|the step|, 3 x OSC 1's increment) (r3 = OSC 1's block, y0 = the step; a is free here)
        [("label", "va_cap"), "move y0,b", "abs b", f"move x:(r3+${INC:x}),y0", "move y0,a", "asl #1,a,a", "add y0,a", "cmp a,b", "tgt a,b",
         "rts"]
        if fmcap() else [])


def ctl_items(S, ys, v=1):
    """va_ctl (r1 = the oscillator's block, r3 = OSC 1's): Hacks' osc_ctrl (V3: 4 side saws, each 3 / 2 of a side's weight)"""
    R1 = lambda o: f"x:(r1+${o:x})"                    # noqa: E731
    mod = _helpers(S, ys)
    L = [("label", "va_ctl"),
          f"move {R1(PW)},a", "sub #>$32,a", "asl #17,a,a", "move a,x0", "move #>$51eb85,y0", "mpy y0,x0,a", "asl a",
          *mod(ENVW, 0x7FFFFF), "add b,a",
          "move a,x0", "tst a", ("jcc", "ge", "va_w0"), "clr a", ("label", "va_w0"), "move a,y1", "move #>$6e147b,y0", "mpy y1,y0,b",
          f"move {R1(INC)},y1", f"move #>${FOLD_K:x},a", "cmp y1,a", ("jcc", "ge", "va_fl"),
          "andi #$fe,ccr", "rep #$18", "div y1,a", "move a0,a", "cmp a,b", "tgt a,b", ("label", "va_fl"),
          "move #>$100000,a", "add b,a", f"move a,{R1(FD)}",
          "move #>$7851ec,y0", "mpy y0,x0,b", f"move b,{R1(TH)}",
          "move x0,b", "neg b", "tst b", ("jcc", "ge", "va_tc"), "clr b", ("label", "va_tc"), "asr b", f"move b,{R1(CV)}",
          "move x0,b", "asr b", "add #>$400000,b", f"move b,{R1(SS_W)}",
          "move b,y0", f"move {R1(INC)},x0", "mpy y0,x0,b", "move b,x0", f"move #>${SSD1:x},y0", "mpy y0,x0,b",
          f"move b,{R1(SS_D)}", "move b,a", "asl a", "add b,a", f"move a,{R1(SS_D + 1)}", "asl a", f"move a,{R1(SS_D + 2)}",
          "move #>$20800,y1", f"move {R1(WAVE)},a", "asl #16,a,a", "move a,x0", "mac x0,y1,a",
          *mod(ENVM, 0x7FFFFF), "add b,a",
          "tst a", ("jcc", "ge", "va_m1"), "clr a", ("label", "va_m1"), "cmp #>$7fffff,a", ("jcc", "le", "va_m2"), "move #>$7fffff,a",
          ("label", "va_m2"),
          "asr #2,a,a", "tfr a,b", "asl a", "add b,a",
          "move a1,b", "and #>$1fffff,b", "asl #2,b,b", "move b1,y1", "asr #21,a,b",
          "clr a", *[f"move a,{R1(W0 + k)}" for k in range(4)],
          "move r1,a", f"add #>${W0:x},a", "add b,a", "move a,r0", "nop",
          "move #>$7fffff,a", "move y1,x0", "sub x0,a", "move a,x:(r0)+", "move y1,x:(r0)",
          f"move {R1(SS_W)},x0", f"move {R1(W0 + 2)},y0", "mpy y0,x0,b", "move y0,a", "asr b", "sub b,a", "asr a", f"move a,{R1(W0 + 2)}",
          *(["asr #4,b,b", "tfr b,a", "asl b", "add a,b"] if int(v) >= 3 else ["asr #3,b,b"]), f"move b,{R1(SS_W)}", "rts"]
    return L


def segs(S, ys, fix, v=1, lab=None):
    """the pieces away from synth0's main: [(CTL_AT, va_ctl's words)]; V3: + (DL_AT, the loop), (VB_AT, va_bs4)"""
    import core0 as C0
    w, _ = C0.asm_at(fix(ctl_items(S, ys, v)), CTL_AT)
    assert CTL_AT + len(w) <= CTL_END, hex(CTL_AT + len(w))
    out = [(CTL_AT, w)]
    if int(v) >= 3:
        wb, lb = C0.asm_at(fix(vb_items()), VB_AT)
        if fmcap():
            lab = dict(lab, va_cap=lb["va_cap"])
        extra = []
        if os2():
            assert not fmcap() and VB_AT + len(wb) <= OSD_P[0][0], "va0: os2's va_osd sits after va_bs4 (not with fmcap)"
            osi = ([(OSI2_AT, OSI2_END, osi2_items(S, ys))] if os2slot() else
                   [(a, a + n, it) for (a, n), it in zip(OSI_P, osi_parts(S, ys))])
            for at, end, its in (osi
                                 + [(a, a + n, it) for (a, n), it in zip(OSD_P, osd_parts(S, ys))]
                                 + [(DX_AT, DX_END, dx_items(S, ys, lab["e_vca"]))]):
                w_, _ = C0.asm_at(fix(its), at)
                assert at + len(w_) <= end, f"va0 os2: the piece at {at:#x} ends at {at + len(w_):#x} (> {end:#x})"
                extra.append((at, w_))
        wd, _ = C0.asm_at(fix(dl_items(lab)), DL_AT)
        assert DL_AT + len(wd) <= DL_END, hex(DL_AT + len(wd))
        assert VB_AT + len(wb) <= VB_END, hex(VB_AT + len(wb))
        out += [(DL_AT, wd), (VB_AT, wb)] + extra
    return out


def wv_items(v=1):
    """va_wv (r4 = the block, x1 = the phase): a += the four waves; va_bs (V3: va_bs4 at VB_AT, 2 increments around a wrap)"""
    v = int(v)
    v2, v3 = v >= 2, v >= 3
    W = lambda o: f"x:(r4+${o:x})"                    # noqa: E731

    def fold():
        return ["move b1,x0", "move x0,b", "sub #>$400000,b", "move b1,x0", "move x0,b", "abs b", "asl b", "neg b", "add #>$7fffff,b", "asr b"]

    def chk():
        if v3:
            return ["move y0,b", "abs b", "add x0,b", "add x0,b", ("jscc", "es", VB_AT)]
        return ["move y0,b", "abs b", "add x0,b", ("jscc", "es", "va_bs")]
    L = [("label", "va_wv"),
          f"move {W(W0)},b", "tst b", ("jcc", "eq", "va_n0"),                       # 0 sine (wavefold)
          "move x1,b", "abs b", "move b,y0", "move #>$7fffff,b", "sub y0,b", "move b,y0", "mpy x1,y0,b", "asl #2,b,b", "move b,y1", "move y1,b",
          "abs b", "move b,y0", "mpy y1,y0,b", "move b1,y0", "move #>$1ccccd,x0", "mpy y0,x0,b", "move #>$633333,x0", "mac x0,y1,b",
          "move b,y1", f"move {W(FD)},x0", "mpy x0,y1,b", "asl #2,b,b", *fold(),
          "move b1,y1", f"move {W(W0)},y0", "mac y1,y0,a",
          ("label", "va_n0"),
          f"move {W(W0 + 1)},b", "tst b", ("jcc", "eq", "va_n1"),                   # 1 triangle (its curve, wavefold)
          "move x1,b", "abs b", "asl b", "sub #>$7fffff,b",
          "move b,y1", "move b,y0", "mpy y0,y0,b", "move b,x0", "move #>$7fffff,b", "sub x0,b", "move b,x0", f"move {W(CV)},y0", "mpy y0,x0,b",
          "move b,x0", "move y1,b", "sub x0,b",
          "move b,y1", f"move {W(FD)},x0", "mpy x0,y1,b", "asl #2,b,b", *fold(),
          "move b1,y1", f"move {W(W0 + 1)},y0", "mac y1,y0,a",
          ("label", "va_n1"),
          f"move {W(W0 + 2)},b", "tst b", ("jcc", "eq", "va_n2"),                   # 2 the supersaw (polyBLEP)
          f"move {W(INC)},x0", "move x1,y0", f"move {W(W0 + 2)},y1", "mac y1,y0,a", *chk(),
          f"move {W(SS_W)},y1"]
    for k in (SIDES3 if v3 else range(6)):
        L += [f"move {W(SS_PH + k)},b", "add x0,b", f"move {W(SS_D + k // 2)},y0", "add y0,b" if k % 2 == 0 else "sub y0,b",
              f"move b1,{W(SS_PH + k)}", "move b1,y0", "mac y1,y0,a", *chk()]
    L += [("label", "va_n2"),
          f"move {W(W0 + 3)},b", "tst b", ("jcc", "eq", "va_n3")]                   # 3 pulse (polyBLEP at both edges)
    if v2:                                                                     # (V2) the rising edge at the phase's wrap: -u
        L += ["move b,y0", "move y0,b", "asr b", "move b,y1", f"move {W(INC)},x0", "move x1,b", "neg b", "move b,y0", *chk(),
              f"move {W(TH)},y0", "move x1,b", "sub y0,b", "move b1,x1", "asr #23,b,b", "and #>$800000,b", "eor #>$c00000,b",
              "move b1,y0", "mac y1,y0,a", "mac y1,y0,a",                       # +-0.5 x w (w / 2 twice)
              "bchg #23,x1", "move x1,y0", *chk()]
    else:
        L += [f"move {W(INC)},x0", f"move {W(TH)},y0", "move x1,b", "sub y0,b", "move b1,x1", "asr #23,b,b", "and #>$800000,b", "eor #>$c00000,b",
              "move b1,y1", f"move {W(W0 + 3)},y0", "mac y1,y0,a",
              "move y0,b", "asr b", "move b,y1", "move x1,b", "neg b", "move b,y0", *chk(),
              "bchg #23,x1", "move x1,y0", *chk()]
    L += [("label", "va_n3"), "rts"]
    if v3:
        return L
    L += [# va_bs: a += -sgn(y0) y1 r^2, r = (b - 1) / x0 (b = |u| + inc >= 1)
          ("label", "va_bs"), "bclr #23,b1", "andi #$fe,ccr", "rep #$18", "div x0,b", "btst #23,y0", "move b0,y0", "mpy y0,y0,b", "move b,y0",
          ("jcc", "cs", "va_bl"), "mac -y1,y0,a", "rts",
          ("label", "va_bl"), "mac y1,y0,a", "rts"]
    return L


# ================================================================ the model (the tests'): the DSP's arithmetic, bit for bit
W56 = 1 << 56


def s24(v):
    v &= 0xFFFFFF
    return v - (1 << 24) if v & 0x800000 else v


def wrap(a):
    a &= W56 - 1
    return a - W56 if a >> 55 else a


def lim(a):
    hi = a >> 24
    return (1 << 23) - 1 if hi > (1 << 23) - 1 else -(1 << 23) if hi < -(1 << 23) else hi


def a1(a): return s24(a >> 24)
def mpy(x, y): return (s24(x) * s24(y)) << 1
def ld(x): return s24(x) << 24


def a1op(a, f):
    """a logic / shift on a1 only (a2, a0 kept)"""
    u = a & (W56 - 1)
    lo, mid, hi = u & 0xFFFFFF, (u >> 24) & 0xFFFFFF, u >> 48
    return wrap(hi << 48 | (f(mid) & 0xFFFFFF) << 24 | lo)


def es(b):
    return not (-(1 << 47) <= b < (1 << 47))


def div24(a, d):
    """andi #$fe,ccr; rep #24; div d,a with 0 <= a1 < d (a0 = 0): the quotient in a0"""
    return (a1(a) << 23) // s24(d)


class Model:
    """the X blocks of the slots; block(s, t1, env, out) -> 32 samples (the VA part only; synth0.Model calls it)"""

    def __init__(self, v=1):
        self.x = {}
        self.v = int(v)
        self.v2, self.v3 = self.v >= 2, self.v >= 3
        self.fmcap = self.v3 and fmcap()
        self.fm2 = fm2()
        self.os2, self.hist = self.v3 and os2(), {}
        self.os2slot = self.v3 and os2slot()
        self.ratio2 = ratio2()

    def g(self, o): return s24(self.x.get(o, 0))
    def p(self, o, v): self.x[o] = v & 0xFFFFFF

    def mod(self, b1, off, scale, env):
        b = wrap(ld(self.g(b1 + off)) << 17)
        b = mpy(env, lim(b))
        if scale != 0x7FFFFF:
            b = mpy(lim(b), scale)
        return b

    def ctl(self, r1, r3, env):
        g, p = self.g, self.p
        a = wrap(ld(g(r1 + PW)) - ld(0x32))
        a = wrap(a << 17)
        a = wrap(mpy(0x51EB85, lim(a)) << 1)
        a = wrap(a + self.mod(r3, ENVW, 0x7FFFFF, env))
        x0 = lim(a)
        if a < 0:
            a = 0
        b = mpy(lim(a), 0x6E147B)
        y1 = g(r1 + INC)
        a = ld(FOLD_K)
        if not a >= ld(y1):
            a = ld(div24(a, y1))
            if b > a:
                b = a
        a = wrap(ld(0x100000) + b)
        p(r1 + FD, lim(a))
        b = mpy(0x7851EC, x0)
        p(r1 + TH, lim(b))
        b = wrap(-ld(x0))
        if b < 0:
            b = 0
        b >>= 1
        p(r1 + CV, lim(b))
        b = wrap((ld(x0) >> 1) + ld(0x400000))
        p(r1 + SS_W, lim(b))
        b = mpy(g(r1 + INC), lim(b))
        b = mpy(lim(b), SSD1)
        p(r1 + SS_D, lim(b))
        a = wrap((ld(lim(b)) << 1) + b)                 # (move b,a: 24 bits; add b,a: all of b)
        p(r1 + SS_D + 1, lim(a))
        a = wrap(a << 1)
        p(r1 + SS_D + 2, lim(a))
        a = wrap(ld(g(r1 + WAVE)) << 16)
        a = wrap(a + mpy(lim(a), 0x20800))
        a = wrap(a + self.mod(r3, ENVM, 0x7FFFFF, env))
        if a < 0:
            a = 0
        if a > ld(0x7FFFFF):
            a = ld(0x7FFFFF)
        a >>= 2
        a = wrap(a + (a << 1))
        b = ld(a1(a))
        b = a1op(b, lambda v: v & 0x1FFFFF)
        b = wrap(b << 2)
        y1 = a1(b)
        i = a1(a >> 21)
        for k in range(4):
            p(r1 + W0 + k, 0)
        p(r1 + W0 + i, lim(wrap(ld(0x7FFFFF) - ld(y1))))
        p(r1 + W0 + i + 1, y1)
        y0 = g(r1 + W0 + 2)
        b = mpy(g(r1 + SS_W), y0) >> 1
        a = wrap(ld(y0) - b) >> 1
        p(r1 + W0 + 2, lim(a))
        if self.v3:
            b >>= 4
            b = wrap((b << 1) + b)
        else:
            b >>= 3
        p(r1 + SS_W, lim(b))

    def bs(self, a, b, x0, y0, y1):
        neg = bool(y0 & 0x800000)
        b = a1op(b, lambda v: v & 0x7FFFFF)
        q = div24(b, x0)
        b = mpy(q, q)
        y0 = lim(b)
        return wrap(a + mpy(y1, y0)) if neg else wrap(a - mpy(y1, y0))

    def bs4(self, a, b, x0, y0, y1):
        neg = bool(y0 & 0x800000)
        b = wrap(b >> 1)
        b = wrap(b - ld(0x400000))
        b = ld(a1(b))
        q = div24(b, x0)
        if ld(0x400000) - ld(q) > 0:                    # far
            b = wrap(ld(q) << 1)
            t = lim(b)
            t2 = lim(mpy(t, t))
            t4 = lim(mpy(t2, t2))
            b = mpy(t4, 0x055555)
        else:
            b = wrap(ld(q) << 1)
            b = a1op(b, lambda v: v & 0x7FFFFF)
            b = wrap(-b)
            b = wrap(b + ld(0x7FFFFF))
            t = lim(b)
            t2 = lim(mpy(t, t))
            b = wrap(-(ld(t) >> 3))
            x1 = lim(wrap(b + ld(0x2AAAAB)))
            b = wrap(-mpy(x1, t2))
            x1 = lim(wrap(b + ld(0x555555)))
            b = wrap(-mpy(t, x1))
            b = wrap(b + ld(0x400000))
        b = mpy(y1, lim(b))
        if not neg:
            b = wrap(-b)
        return wrap(a + wrap(b << 1))

    def chk(self, a, x0, y0, y1):
        b = abs(ld(y0))
        b = wrap(b + ld(x0))
        if self.v3:
            b = wrap(b + ld(x0))
        if es(b):
            a = self.bs4(a, b, x0, y0, y1) if self.v3 else self.bs(a, b, x0, y0, y1)
        return a

    @staticmethod
    def fold(b):
        x0 = a1(b)
        b = wrap(ld(x0) - ld(0x400000))
        x0 = a1(b)
        b = abs(ld(x0))
        b = wrap(b << 1)
        b = wrap(-b)
        b = wrap(b + ld(0x7FFFFF))
        return b >> 1

    def wv(self, r4, x1, a):
        g, p = self.g, self.p
        if g(r4 + W0):
            b = abs(ld(x1))
            y0 = lim(b)
            b = wrap(ld(0x7FFFFF) - ld(y0))
            y0 = lim(b)
            b = wrap(mpy(x1, y0) << 2)
            y1 = lim(b)
            b = abs(ld(y1))
            y0 = lim(b)
            b = mpy(y1, y0)
            y0 = a1(b)
            b = mpy(y0, 0x1CCCCD)
            b = wrap(b + mpy(0x633333, y1))
            y1 = lim(b)
            b = wrap(mpy(g(r4 + FD), y1) << 2)
            b = self.fold(b)
            a = wrap(a + mpy(a1(b), g(r4 + W0)))
        if g(r4 + W0 + 1):
            b = wrap(abs(ld(x1)) << 1)
            b = wrap(b - ld(0x7FFFFF))
            y1 = y0 = lim(b)
            b = mpy(y0, y0)
            x0 = lim(b)
            b = wrap(ld(0x7FFFFF) - ld(x0))
            x0 = lim(b)
            b = mpy(g(r4 + CV), x0)
            x0 = lim(b)
            b = wrap(ld(y1) - ld(x0))
            y1 = lim(b)
            b = wrap(mpy(g(r4 + FD), y1) << 2)
            b = self.fold(b)
            a = wrap(a + mpy(a1(b), g(r4 + W0 + 1)))
        if g(r4 + W0 + 2):
            x0, y0, y1 = g(r4 + INC), x1, g(r4 + W0 + 2)
            a = wrap(a + mpy(y1, y0))
            a = self.chk(a, x0, y0, y1)
            y1 = g(r4 + SS_W)
            for k in (SIDES3 if self.v3 else range(6)):
                b = wrap(ld(g(r4 + SS_PH + k)) + ld(x0))
                d = ld(g(r4 + SS_D + k // 2))
                b = wrap(b + d) if k % 2 == 0 else wrap(b - d)
                p(r4 + SS_PH + k, a1(b))
                y0 = a1(b)
                a = wrap(a + mpy(y1, y0))
                a = self.chk(a, x0, y0, y1)
        if g(r4 + W0 + 3) and self.v2:
            w3, x0 = g(r4 + W0 + 3), g(r4 + INC)
            y1 = lim(ld(w3) >> 1)
            a = self.chk(a, x0, lim(wrap(-ld(x1))), y1)
            b = wrap(ld(x1) - ld(g(r4 + TH)))
            v = a1(b)
            b >>= 23
            b = a1op(b, lambda q: q & 0x800000)
            b = a1op(b, lambda q: q ^ 0xC00000)
            a = wrap(a + mpy(y1, a1(b)))
            a = wrap(a + mpy(y1, a1(b)))
            a = self.chk(a, x0, s24(v ^ 0x800000), y1)
        elif g(r4 + W0 + 3):
            x0, y0 = g(r4 + INC), g(r4 + TH)
            b = wrap(ld(x1) - ld(y0))
            x1 = a1(b)
            b >>= 23
            b = a1op(b, lambda v: v & 0x800000)
            b = a1op(b, lambda v: v ^ 0xC00000)
            y1, y0 = a1(b), g(r4 + W0 + 3)
            a = wrap(a + mpy(y1, y0))
            y1 = lim(ld(y0) >> 1)
            y0 = lim(wrap(-ld(x1)))
            a = self.chk(a, x0, y0, y1)
            x1 = s24(x1 ^ 0x800000)
            a = self.chk(a, x0, x1, y1)
        return a

    def decim(self, s, x):
        """(os2) va_dx: the halfband from the slot's history + 64 inner samples to 32 (the DSP's MACs, x 2 each, the centre x 1/2, macr's
        convergent rounding)"""
        buf = self.hist.get(s, [0] * HIST) + [s24(v) for v in x]
        c = [s24(self.x.get(XC + j, 0)) for j in range(12)]
        y = []
        for m in range(32):
            a = 0
            for j in range(12):
                a += (c[j] * buf[2 * m + 1 + 2 * j]) << 1
            a += (0x400000 * buf[2 * m + 12]) << 1
            r = (a + 0x800000) >> 24
            if (a & 0xFFFFFF) == 0x800000:
                r &= ~1
            y.append(max(-(1 << 23), min((1 << 23) - 1, r)) & 0xFFFFFF)
        self.hist[s] = buf[64:64 + HIST]
        return y

    def dual3(self, r3, r4, out):
        """(V3) Hacks' SC52.4 two oscillators"""
        g, p = self.g, self.p
        p(r4 + INC, g(r4 + IU))
        ext, env = getattr(self, "ext", None), getattr(self, "env", 0)
        for src, dst in ((MIX, MIXS), (RING, RINGS), (POS, POSS)):
            a = wrap(ld(g(r4 + src)) << 16)
            if ext is not None and src != POS:                          # (envx) + depth x the envelope, 0 at least
                d = ext[2] if src == MIX else ext[1]
                a = wrap(a + mpy(lim(wrap(ld(d) << 17)), env))
                if a < 0:
                    a = 0
            a = wrap(a + mpy(lim(a), 0x20800))
            p(r4 + dst, lim(a))
        a = wrap(ld(g(r4 + self.fm2)) - ld(0x40))
        a = wrap(a << 17)
        if ext is not None:
            a = wrap(a + mpy(lim(wrap(ld(ext[0]) << 17)), env))
        x0 = lim(a)
        b = abs(ld(x0))
        if b - ld(0x400000) > 0:
            a = wrap(ld(lim(b)) - ld(0x400000))
            b = wrap(ld(0x7FFFFF) - a)
        else:
            b = wrap(b << 1)
            y0 = lim(b)
            b = mpy(y0, y0)
            a = 0
        y0 = lim(a)
        if x0 >= 0:
            a = ld(y0)
        else:
            a, b = ld(lim(b)), ld(y0)
        p(r4 + FMS, lim(b))
        p(r4 + O12, lim(a))
        for _ in range(32):
            y1, x0 = g(r3 + PH), g(r3 + INC)
            a = wrap(ld(y1) + ld(x0))
            p(r3 + PH, a1(a))
            y0 = a1(a)
            x1 = g(r4 + INC)
            b = wrap(ld(g(r4 + PH)) + ld(x1))
            if ld(y0) < ld(y1) and g(r4 + ZONE) == 1:
                q = div24(ld(s24(y0 ^ 0x800000)), x0)
                b = ld(s24(lim(mpy(x1, q)) ^ 0x800000))
            p(r4 + PH, a1(b))
            a = wrap(wrap(mpy(g(r3 + O1P), g(r4 + O12)) << 3) + b)
            a = self.wv(r4, a1(a), 0)
            p(r4 + OUT2, lim(a))
            x1 = g(r3 + PH)
            b = wrap(mpy(g(r4 + OUT2), g(r4 + FMS)) << 3)
            x1 = a1(wrap(ld(x1) + b))
            y0 = g(r3 + PMP)
            p(r3 + PMP, x1)
            b = abs(ld(a1(wrap(ld(x1) - ld(y0)))))
            if getattr(self, "fmcap", False):                             # (fmcap) at most 3 x OSC 1's own increment
                cap = ld(g(r3 + INC)) * 3
                if b > cap:
                    b = cap
            p(r3 + ISV, g(r3 + INC))
            p(r3 + INC, lim(b))
            a = self.wv(r3, x1, 0)
            p(r3 + INC, g(r3 + ISV))
            x1 = lim(a)
            p(r3 + O1P, x1)
            y0 = g(r4 + OUT2)
            y1 = lim(wrap(ld(y0) - ld(x1)))
            a = wrap(ld(x1) + mpy(g(r4 + MIXS), y1))
            if g(r4 + RING):
                b = wrap(mpy(x1, g(r4 + OUT2)) << 1)
                b = wrap(b - a)
                a = wrap(a + mpy(g(r4 + RINGS), lim(b)))
            z = g(r4 + ZONE)
            if z >= 2:
                y1 = lim(a)
                u, v = x1 & 0xFFFFFF, g(r4 + OUT2) & 0xFFFFFF
                r = {2: u ^ v, 3: u | v, 4: ~(u | v), 5: u & v}.get(z, ~(u & v)) & 0xFFFFFF
                a = wrap(ld(r) - ld(y1))
                b = ld(g(r3 + BWS))
                a = wrap(wrap(a - b) >> 1)
                a = wrap(a + b)
                p(r3 + BWS, lim(a))
                a = mpy(g(r4 + POSS), lim(a))
                a = wrap(a + ld(y1))
            out.append(lim(a))
        return out

    def block(self, s, t1, env, inc_of, ext=None):
        """s = the slot, t1 = synth0's pitch (G_T1), env = S_ENV, inc_of(pitch) = synth0's s_inc's increment -> 32 samples; ext (envx) =
        synth0's (C_G1, C_G2, C_GS): the envelope's depths on the FM, the ring, the mix"""
        g, p = self.g, self.p
        self.ext, self.env = ext, env
        r1 = XB0 + XS * s
        r2 = r1 + O2
        mg = VMAGIC3 if self.v3 else VMAGIC
        if g(r2 + VMAG) != s24(mg):
            for o in range(2 * O2):
                p(r1 + o, 0)
            p(r1 + PW, 0x32)
            p(r2 + PW, 0x32)
            if self.v3:
                p(r2 + self.fm2, 0x40)
            p(r2 + VMAG, mg)
        if self.v3:
            x0 = g(r2 + BSR)
            a = wrap((ld(x0) << 3) - ld(x0))
            p(r2 + POS, a1(a) & 0x7F)
            p(r2 + ZONE, a1(a >> 7))
        incs = []
        for blk in (r1, r2):
            a = wrap(ld(t1) + (ld(g(blk + TUNE)) << 16))
            a = wrap(a + (ld(g(blk + FINE)) << (8 if self.ratio2 and blk == r2 else 9)))
            if self.v3 and blk == r2 and g(r2 + ZONE) == 1:
                a = wrap(a + (ld(g(r2 + POS)) << 14))
            a = wrap(a + self.mod(r1, ENVP, 0x180000, env))
            incs.append(inc_of(a))
        r3, r4 = r1, r2
        two = False
        key = g(key_addr(s)) if self.os2slot else g(OS2G)
        if self.os2 and g(r3 + DFL) & DUAL and key == s24(OS2KEY):              # (os2) 2x: the increments halved
            two = True
            incs = [s24(i) >> 1 for i in incs]
        elif self.os2slot:                                                       # (os2slot) at 1x the history from zeros
            self.hist[s] = [0] * HIST
        p(r3 + INC, incs[0])
        p(r4 + IU, incs[1])
        p(r4 + INC, incs[1])
        self.ctl(r3, r3, env)
        out = []
        if not g(r3 + DFL) & DUAL:
            for _ in range(32):
                a = wrap(ld(g(r3 + PH)) + ld(g(r3 + INC)))
                p(r3 + PH, a1(a))
                a = self.wv(r3, a1(a), 0)
                out.append(lim(a) if self.v2 else lim(wrap(a << 1)))
            return out
        self.ctl(r4, r3, env)
        if self.v3:
            if two:
                return self.decim(s, self.dual3(r3, r4, self.dual3(r3, r4, out)))
            return self.dual3(r3, r4, out)
        a = ld(g(r4 + IU))
        if g(r4 + DIR):
            a = wrap(-a)
        p(r4 + INC, lim(a))
        x0 = g(r4 + BSR)
        a = wrap((ld(x0) << 3) - ld(x0))
        p(r4 + POS, a1(a) & 0x7F)
        p(r4 + ZONE, a1(a >> 7))
        for src, dst in ((MIX, MIXS), (FM, FMS), (RING, RINGS), (POS, POSS)):
            a = wrap(ld(g(r4 + src)) << 16)
            a = wrap(a + mpy(lim(a), 0x20800))
            p(r4 + dst, lim(a))
        p(r4 + SPER, (g(r4 + POS) >> 4) + 1)
        for _ in range(32):
            a = wrap(ld(g(r4 + PH)) + ld(g(r4 + INC)))
            p(r4 + PH, a1(a))
            a = self.wv(r4, a1(a), 0)
            p(r4 + OUT2, lim(a))
            y1 = g(r3 + PH)
            a = wrap(ld(y1) + ld(g(r3 + INC)))
            p(r3 + PH, a1(a))
            x1 = a1(a)
            if ld(x1) < ld(y1) and g(r4 + ZONE) == 1:
                c = g(r4 + SCNT) + 1
                if c >= g(r4 + SPER):
                    p(r4 + INC, lim(wrap(-ld(g(r4 + INC)))))
                    p(r4 + DIR, g(r4 + DIR) ^ 1)
                    c = 0
                p(r4 + SCNT, c)
            b = wrap(mpy(g(r4 + OUT2), g(r4 + FMS)) << 3)
            x1 = a1(wrap(ld(x1) + b))
            a = self.wv(r3, x1, 0)
            x1 = lim(a)
            y0 = g(r4 + OUT2)
            y1 = lim(wrap(ld(y0) - ld(x1)))
            a = wrap(ld(x1) + mpy(g(r4 + MIXS), y1))
            if g(r4 + RING):
                b = wrap(mpy(x1, g(r4 + OUT2)) << 1)
                b = wrap(b - a)
                y1 = lim(b)
                a = wrap(a + mpy(g(r4 + RINGS), y1))
            z = g(r4 + ZONE)
            if z >= 2:
                y1 = lim(a)
                u, v = x1 & 0xFFFFFF, g(r4 + OUT2) & 0xFFFFFF
                r = {2: u ^ v, 3: u | v, 4: ~(u | v), 5: u & v}.get(z, ~(u & v)) & 0xFFFFFF
                a = wrap(ld(r) - ld(y1))
                a = mpy(g(r4 + POSS), lim(a))
                a = wrap(a + ld(y1))
            out.append(lim(a) if self.v2 else lim(wrap(a << 1)))
        return out
