"""The external input's gain, +0..+24 dB on Advanced Setup K3 (MIT; RH101; CIRCUIT-HACKS' SC52.6 / Beta 5.29 «ingain» on the Circuit Rhythm, ours).

The Rhythm already has an input gain stage on core 0 (the stock, read in its program): P:$209 `jsr $19DF`, in place on the block's frames
of the input ring before $19FA copies them to Y:$30710 (LI, the looper's source 0, core 1's Sample Rec and its trigger, stereorec, the
monitor all read that copy; the FX-return line sources and resampling do not): x1 += (X:$307B1 - x1) >> 8 a frame, then L / R =
`mpy y1,x1,a` / `asl #2,a,a` (P:$19F1) and `mpy x1,y0,b` / `asl #2,b,b` (P:$19F3), saturating stores.  X:$307B1 is sent by the ARM
(0x08030D84: the master sender, also in the full send at boot): get(0x21, 0x10) = Sample Rec's K8 (0..127, 100 = 0 dB) -> 0x08030DF0 (the
conversion, from the call at 0x08030DDC; v = 100 -> $200000 = x 4 = 0 dB, 127 -> $7A8000 = +11.7 dB) -> 0x08031228(0, w << 8, $307B1).
Ours (decision A of docs/PRUEBA_RH101.md: one stage for everything, zero DSP cost):
  * core 0: P:$19F1 / $19F3 `asl #4` (two one-word segments, the old words asserted): the stage reaches x 16 (+24 dB above K8's 0 dB);
  * the ARM: the call at 0x08030DDC -> c_igconv: the stock's conversion, then w x T[dB] >> 16 (T = 10^(dB / 20) x 2^14: 0 dB = w / 4, the
    stock's gain within the stage's smoothing; the word's 2 low bits go) at most $7FFFFF; dB = settings p3 byte 3 - $40 (0..24; anything
    else, or before c_ciok, = 0);
  * Advanced Setup K3 (tools/velcurve.py OPT ingain): 2 clicks a dB, 0..24, written to p3 byte 3 (tools/setsave.py OPT setp3b3 saves it
    with the transport stopped); the LED task sends the word again when the dB changes (OFF2 velcurve + 2 = $80 | the dB sent); K3's LED
    green $1E, brightness = dB x 127 / 24 (dark at 0 dB).
"""
from __future__ import annotations

SITE, CONV = 0x08030DDC, 0x08030DF0                    # the stock's call of the conversion, the conversion
GETTER, W24, PORT = 0x08046410, 0x08031228, 0x307B1
GROUP, INDEX = 0x21, 0x10
P_UNIT, B_GAIN, TAG, DBMAX, CLICKS, KNOB = 3, 3, 0x40, 24, 2, 2
O_ACC, O_SENT = 1, 2                                   # OFF2 velcurve + 1 the knob's accumulator, + 2 0x80 | the dB last sent
COL = 0x1E                                             # green: Advanced Setup's knobs (velcurve's K1)
STAGE = ((0x19F1, 0x0C1D04, 0x0C1D08), (0x19F3, 0x0C1D85, 0x0C1D89))   # asl #2,a,a -> asl #4,a,a; asl #2,b,b -> asl #4,b,b


def on():
    import rhbuild
    return bool(rhbuild.OPT.get("ingain"))


def table():
    """T[dB] = round(10^(dB / 20) x 2^14), 0..24"""
    return [round(10 ** (d / 20) * (1 << 14)) for d in range(DBMAX + 1)]


def conv(w, db):
    """c_igconv after the stock's conversion: w x T[dB] >> 16, at most $7FFFFF"""
    return min(0x7FFFFF, (w * table()[db]) >> 16)


def db_of(byte3):
    d = (byte3 - TAG) & 0xFFFFFFFF
    return d if d <= DBMAX else 0


def segs():
    """core 0's two one-word segments (the stock's words checked)"""
    import core0 as C0
    import rhbuild
    _, _, ws = C0.block_words(rhbuild.load_stock())
    out = []
    for at, old, new in STAGE:
        assert ws[at] == old, f"core 0 P:{at:#x} = {ws[at]:06x}, not the stock's {old:06x}"
        out.append((at, [new]))
    return out
