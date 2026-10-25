"""Pitch envelope and pitch LFO per track in the Circuit Rhythm 5706's DSP core 1, the voices (MIT; the first piece of the Stock+ sampler mode).

The stock (core 1's program, tools/rhdsp.py dis 1; docs/PORTADO.md «Núcleo 1 = las voces»):
  * P:$1C3 turns a pitch (y0, log: a semitone = $10000, an octave = $C0000; measured in dsptool, tests/emu_rd6.py) into the voice's resampling increment Y:(base) and its polyphase
    table Y:(base + 1), base = r4 = $40 + $10 t (track t's voice block);
  * it is called from two places: P:$168 (bsr, the note's start: P:$2FD -> P:$15A) and P:$2D8 (jsr, P:$289: once a block, one voice a
    block in turn, Y:$121 = the voice, so each voice's pitch is recomputed every 8 blocks); P:$2D6 clamps the pitch to $23CCCC before it;
  * a note's start comes from core 0's queue (P:$2E4: P:$2F2 jsne $2FD with y1 = the trigger word, its bits 0-2 = the track).
Ours (tools/rhdsp1.py puts the words at P:$D34.., after dspload's when both are in):
  * P:$2D8 jsr $1C3 -> jsr RR: Y:E[t] *= D[t] (the envelope's decay), the LFO's phase += R[t], pitch += A[t] * E + L[t] * triangle(phase),
    clamped to [-$480000, $23CCCC] (6 octaves below 0 .. the stock's top), then $1C3;
  * P:$2F3 (jsne $2FD's address) -> TRIG: the stock's start ($2FD), then E[t] = 1 and the voice's pitch recomputed at once through P:$289
    (Y:$121 set to t - 1 and given back), so the envelope begins with the note, not up to 8 blocks later;
  * all zero (as at power-on: P:$151 clears Y:$400..$13FF) = the stock's pitch.
Core 1's Y, per track t (written by the ARM through the host port, rhremote dspw 1 Y:...; zero in every dump of the device):
  Y:$1310 + t  E, the envelope (ours)          Y:$1320 + t  A, envelope amount (signed, pitch units: 12 semitones = $C0000)
  Y:$1318 + t  the LFO's phase (ours)          Y:$1328 + t  D, the envelope's factor per update (fraction: $7FFFFF = holds)
                                               Y:$1330 + t  R, the LFO's phase step per update (a full cycle = $1000000)
                                               Y:$1338 + t  L, LFO depth (signed, pitch units)
  Y:$1308 / $1309 scratch (TRIG).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dspload  # noqa: E402
import rhdsp1  # noqa: E402
import rhdsppatch as DP  # noqa: E402

Y_BASE = 0x1310
OFF_E, OFF_PH, OFF_A, OFF_D, OFF_R, OFF_L = 0x00, 0x08, 0x10, 0x18, 0x20, 0x28
Y_TMP0, Y_TMP1 = 0x1308, 0x1309
P_EXP, P_RR_CALL, P_TRIG_ADDR, P_START, P_RR = 0x1C3, 0x2D8, 0x2F3, 0x2FD, 0x289
OLD_RR_CALL = 0x0D01C3                                 # jsr $1c3 (short)
JSR_SHORT = 0x0D0000
P_CLEAR_N, OLD_CLEAR_N, NEW_CLEAR_N = 0x154, 0x001000, 0x001C00   # (clear) P:$153 move #>$1000,y1: core 1's start clears Y:$400.. this many words
PITCH_MAX, PITCH_MIN = 0x23CCCC, 0x1000000 - 0x240000


OFF_PITCH, OFF_SCANR, OFF_SCANPH = 0xA0, 0xA8, 0xB8       # (RD8 on, from Y_BASE) the voice's pitch as $1C3 gets it, the scan LFO's step / phase


STRETCH_ST, STRETCH_N = 0x1780, 15                         # (stretch) the voice's stretch state cleared at each note: Y:$1780 + 16 v

# (shiboot) core 1's host port setup: P:$10B jsr $72D (the SHI as a 24-bit SPI slave); the main loop (P:$119 bclr #21,x:$8 / jscs $72A)
# sets it up again whenever bit 21 of X:$8 (the host's config word, P:$6DD) is set, 16-bit words if its bit 8 is set (P:$735, HCSR $10A4).
# No segment loads X:$6..$8, so after a power-up they hold whatever the RAM came up with: with bits 21 and 8 the first block turns the
# port to 16-bit words while the ARM sends 24 (RH34 / RH35 on the device: out of step after a cold start, every write lost).
P_SHI_SETUP, OLD_SHI_SETUP = 0x10B, 0x0D072D               # jsr $72d (short)
SHI_BOOT = [0x0A0815,                                      # bclr #$15,x:$8   (as P:$119)
            0x0C072D]                                      # jmp $72d (short)


def code(at, shift=0, store_pitch=False, scan=False, stretch=False):
    """-> (words for P:at.., RR's address, TRIG's address).  shift: our Y words moved up (RD8 on: $300, out of voice 7's sample ring
    Y:$1200..$13FF); store_pitch: RR keeps the pitch it gets (voicefilt's pitch follow); scan: RR moves the scan LFO's phase (voicefilt)."""
    yb, t0, t1 = Y_BASE + shift, Y_TMP0 + shift, Y_TMP1 + shift
    extra = ([f"move y0,y:(r1+${OFF_PITCH:x})"] if store_pitch else []) + (
        [f"move y:(r1+${OFF_SCANPH:x}),a", f"move y:(r1+${OFF_SCANR:x}),x0", "add x0,a", f"move a1,y:(r1+${OFF_SCANPH:x})"] if scan else [])
    rr = DP.asm([
        "move r4,a", "sub #>$40,a", "lsr #4,a", "move a1,n1", f"move #>${yb:x},r1", "lua (r1)+n1,r1", *extra,
        "move y:(r1),x0", f"move y:(r1+${OFF_D:x}),x1", "mpyr x1,x0,a", "move a,y:(r1)",                    # E *= D
        "move a,x0", f"move y:(r1+${OFF_A:x}),x1", "mpy x1,x0,b",                                       # b = A * E
        f"move y:(r1+${OFF_PH:x}),a", f"move y:(r1+${OFF_R:x}),x0", "add x0,a", f"move a1,y:(r1+${OFF_PH:x})",  # phase += R
        "move a1,a", "abs a", "asl a", "move #>$7fffff,x0", "sub x0,a", "move a,x0",                     # triangle
        f"move y:(r1+${OFF_L:x}),x1", "mac x1,x0,b",                                                    # b += L * tri
        "move y0,a", "add b,a",
        f"move #>${PITCH_MAX:x},x0", "cmp x0,a", "tgt x0,a",
        f"move #>${PITCH_MIN:x},x0", "cmp x0,a", "tlt x0,a",
        "move a1,y0"]) + DP.jmp(P_EXP)
    trig_at = at + len(rr)
    trig = (DP.asm([f"move y1,y:>${t0:x}"]) + DP.jsr(P_START) + DP.asm([
        f"move y:>${t0:x},a", "and #>$7,a", "move a1,n1", f"move #>${yb:x},r1",
        "move #>$7fffff,x0", "move x0,y:(r1+n1)",                                                       # E = 1
        "move y:>$121,x0", f"move x0,y:>${t1:x}", "sub #>$1,a", "and #>$7,a", "move a1,y:>$121"])
        + DP.jsr(P_RR) + DP.asm([f"move y:>${t1:x},x0", "move x0,y:>$121"]
                                + ([f"move y:>${t0:x},a", "and #>$7,a", "asl #4,a,a", f"add #>${STRETCH_ST:x},a", "move a1,r1", "clr a",
                                    f"rep #{STRETCH_N}", "move a,y:(r1)+"] if stretch else []) + ["rts"]))
    return rr + trig, at, trig_at


P_DUCK, OLD_DUCK = 0x25D, (0x56E400, 0x5FDC00, 0x205C00, 0x4FE400)        # move x:(r4),a / move y:(r4)+,b / move (r4)+ / move y:(r4),y1
NEW_DUCK = (0x4ADC00, 0x0204F7, 0x0BC761, 0x0E8268)                         # move l:(r4)+,ab / move y:(r4+$1),y1 / btst #$1,y1 / jcs $268
LAND_CNT = 0x16DD                                                           # (RD17) the landing routine's counter


def landing_code():
    """(RD17) the test routine at P:$C (the landing area): Y:LAND_CNT + 1, called from the block hook (it proves code runs there)"""
    return 0xC, DP.asm([f"move y:>${LAND_CNT:x},a", "add #>1,a", f"move a1,y:>${LAND_CNT:x}", "rts"])


def install(img, report, base_addr, load=False, fx=False, shift=0, filt=False, clear=False, lite=False, stretch=False, probe=False,
            duck=False, landing=False, shiboot=False):
    """our words through rhdsp1 (after dspload's counters when load: RD6); core 1's two stock words checked and redirected.
    fx (RD7): tools/voicefx.py's words after ours (ring mod, filter modes, drive), P:$240 redirected to them.
    shift (RD8 on: $300): every Y word of ours moved up, out of voice 7's sample ring Y:$1200..$13FF; filt (RD8, needs fx and shift):
    tools/voicefilt.py (K6 filter types, pitch follow, the start-point scan) before voicefx's words, RR keeping the pitch and the scan phase.
    clear (RD9 on, with shift): core 1's start clears Y:$400..$1FFF, not only $400..$13FF, so our moved words start at 0 (RD8 had the
    power-on garbage there: random ring / drive / filter types / scan and a burn loop of any length, «sound is glitchy»).
    lite (RD10 on): voicefx without the SVF modes and the soft / hard / fold drives (the Stock+ page uses ring, comb, bitcrush);
    stretch (RD10 on, needs shift): tools/stretch.py after the others, P:$23D redirected, TRIG clearing the voice's stretch state;
    stretch=3 (RD11 on): its v3 (the stock's level); stretch=4 (RD12): v3 + the grain size from the host (stretch.GSTEP..);
    stretch=5 (RD13): + tools/wsola.py in P:$46..$FF (the grains start in step) and silence past the sample's end;
    stretch=6 (RD14): WSOLA v2 (cheaper, one search every 4 blocks: RD13 hung core 1 with 7-8 tracks stretched);
    stretch=7 (RD15): WSOLA v3 (v2, off unless the host sets the gap: RD14 hung core 1 too);
    stretch=8 (RD16): WSOLA v4 from the main loop (dspload's block hook jumps to WSB; RD15 showed the cause: the hardware stack).
    probe (RD12, with load): dspload's burn replaced by its probe of the P memory (tools/rhpmem.py).
    duck (RD17): the stock's end-of-sample fade (P:$25C) skipped for looped voices (P:$25D..$260 in place): it ducked a looped voice once
    every pass, -35 dB some 10-15 ms before the loop point, and silenced loops under ~260 words (the user's «click» of short looped grains).
    landing (RD17, with stretch >= 8): the last P segment P:$2..$45 (tools/rhdsp1.py landing_words), with landing_code() at P:$C called from
    the block hook.
    shiboot (RH36): P:$10B jsr $72D -> jsr SHI_BOOT, which clears bit 21 of X:$8 first: the host port stays at 24-bit words after a
    power-up whatever X:$8 came up with."""
    assert not filt or (fx and shift == 0x300)
    if clear:
        assert shift
        rhdsp1.patch_p(img, P_CLEAR_N, OLD_CLEAR_N, NEW_CLEAR_N)
    pre, rr_at, trig_at = [], rhdsp1.START, None
    if load:
        hook = None
        if stretch >= 8:                                   # (RD16) WSOLA v4 from the main loop: its code first, for WSB's address
            import stretch as STR0
            import wsola as WS0
            low_w, low_labels, low_ci = WS0.code(STR0.low_consts(), WS0.V4)
            hook = low_labels["wsb"]
        land_at = None
        if landing:
            assert stretch >= 8
            land_at, land_w = landing_code()
        pre, blk_at = dspload.code(shift, probe=probe, hook=hook, call=land_at)
        rhdsp1.patch_p(img, dspload.P_WAIT, dspload.OLD_WAIT, JSR_SHORT | rhdsp1.START)
        rhdsp1.patch_p(img, dspload.P_ACK, dspload.OLD_ACK, JSR_SHORT | blk_at)
    ours, rr_at, trig_at = code(rhdsp1.START + len(pre), shift, store_pitch=filt, scan=filt, stretch=stretch)
    words = pre + ours
    flabels = None
    if fx:
        import voicefx
        if filt:
            import voicefilt
            fw, flabels = voicefilt.code(rhdsp1.START + len(words))
            voicefx.check(fw, flabels["hpidx"])
            words += fw
            for pa, old, new in voicefilt.patches(flabels):
                rhdsp1.patch_p(img, pa, old, new)
        vw, fx_at = voicefx.code(rhdsp1.START + len(words), shift, pre=flabels["post"] if flabels else None, lite=lite)
        voicefx.check(vw, fx_at)
        words += vw
        rhdsp1.patch_p(img, voicefx.P_HOOK, voicefx.OLD_HOOK, JSR_SHORT | fx_at)
    slabels, low = None, None
    if stretch:
        import stretch as STR
        import voicefx
        assert shift == 0x300
        if stretch >= 5:
            import wsola
            assert load, "WSOLA counts blocks with dspload's counter (v4: WSB runs from its block hook)"
            if stretch < 8:
                low_w, low_labels, low_ci = wsola.code(STR.low_consts(), wsola.V3 if stretch >= 7 else wsola.V2 if stretch >= 6 else wsola.V1)
            voicefx.check(low_w[:low_ci], wsola.AT)
            voicefx.check(low_w[low_ci + 1:], wsola.AT + low_ci + 1)
            low = (wsola.AT, low_w, low_ci)
        sw, slabels = STR.code(rhdsp1.START + len(words), v3=stretch >= 3, grain=stretch >= 4, low=low_labels if stretch >= 5 else None)
        voicefx.check(sw, slabels["str"])
        words += sw
        rhdsp1.patch_p(img, STR.P_HOOK, STR.OLD_HOOK, JSR_SHORT | slabels["str"])
    shi_at = None
    if shiboot:
        shi_at = rhdsp1.START + len(words)
        words += SHI_BOOT
        rhdsp1.patch_p(img, P_SHI_SETUP, OLD_SHI_SETUP, JSR_SHORT | shi_at)
    assert rhdsp1.START + len(words) <= 0x1000, "out of reach of a short jsr"
    rhdsp1.patch_p(img, P_RR_CALL, OLD_RR_CALL, JSR_SHORT | rr_at)
    rhdsp1.patch_p(img, P_TRIG_ADDR, P_START, trig_at)
    if duck:
        for k, (old, new) in enumerate(zip(OLD_DUCK, NEW_DUCK)):
            rhdsp1.patch_p(img, P_DUCK + k, old, new)
    land = {land_at + i: w for i, w in enumerate(land_w)} if landing else None
    labels = rhdsp1.install(img, report, base_addr, words, "pitchmod", low=low, landing=land)
    report["pitchmod"].update(rr=hex(rr_at), trig=hex(trig_at), y_base=hex(Y_BASE + shift), load=load)
    if shiboot:
        report["pitchmod"].update(shiboot=hex(shi_at))
    if fx:
        report["pitchmod"].update(fx=hex(fx_at), fx_y_base=hex(voicefx.Y_BASE + shift), words=len(words))
    if flabels:
        report["pitchmod"].update(shift=hex(shift), filt={k: hex(v) for k, v in flabels.items()})
    if slabels:
        report["pitchmod"].update(stretch={k: hex(v) for k, v in slabels.items() if k in ("str", "grn", "trp", "stock")}, end=hex(rhdsp1.START + len(words) - 1))
        if low:
            report["pitchmod"]["wsola"] = {k: hex(v) for k, v in low_labels.items() if k in ("trp", "ws", "copy", "corr", "wsb")}
    if load:
        report["pitchmod"].update(probe=probe, duck=duck, landing=landing, block=hex(blk_at), y_idle=hex(dspload.Y_IDLE + shift), y_burn=hex(dspload.Y_BURN + shift),
                                  y_blocks=hex(dspload.Y_BLOCKS + shift))
    return labels, b""
