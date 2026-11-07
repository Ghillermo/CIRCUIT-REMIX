"""The synth's voice modes on DSP core 0 (MIT; RH80; the user, 2026-11-07: «Los 8 en RH80» — CIRCUIT-HACKS' pad 32 voice modes: retrigger,
legato, glide, uni retrig, uni legato, uni glide, uni always-glide, poly; docs/DISENO_RH80.md).

The ARM gives each track flags (X:VMF + t, valid with the key X:VMK = VKEY; 0 = the old behaviour, byte for byte):
  * F_SNAP (8): a mode was chosen (retrigger, legato, poly: the pitch jumps to the note);
  * F_LEG (1): legato: a note-on while the previous note is held (its gate on, or its note-off in this block or the previous one: the ARM
    sends a note-off right before the note-on of an overlapping note) only changes the pitch: no new attack (a release begun goes back to
    held), and the FM's note flag (poly0's FTR + s) back to 0;
  * F_GLD (2): glide: the pitch slides (synth0's C_GLD) on a legato note, snaps on a new one;
  * F_ALW (4): always glide: the pitch slides from the last note even after a release.
Unison is the ARM's: the track takes the free slots as poly does but every slot plays every note (poly0's PF + t = 0), each slot's C_OCT
detuned; here only its level: X:UG + t (0 = none) scales the track's 32 samples after poly0's MIXG sums its slots.
  * VMN (synth0's note-on, OPT vmode: after S_VEL / S_TGT, `jmp VMN` in place of the snap and the attack; r6 = the slot; keeps x1, y0, y1);
  * VMO (synth0's note-off with env2, after S_GATE = 0): X:OFF + s = the block (X:VBLK);
  * VMX (SY's jsr MIXG -> jsr VMX): VBLK + 1, MIXG, then the unison tracks' gain.
The granular's envelope blocks (r6 >= GE0) go through the old path.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core0 as C0  # noqa: E402

VMF, UG, OFF, VBLK, VMK = 0x5240, 0x5248, 0x5250, 0x5254, 0x5255     # X (free: RD37 / RD39's dumps, X:$5233..$53FF unused)
VKEY = 0x7D0E5A
F_LEG, F_GLD, F_ALW, F_SNAP = 1, 2, 4, 8
END = 0x25EE                                                            # (fm8c0's amp1)
# the 8 modes (Hacks' order) -> (flags, unison, poly)
MODES = ((F_SNAP, 0, 0), (F_SNAP | F_LEG, 0, 0), (F_LEG | F_GLD, 0, 0),
         (F_SNAP, 1, 0), (F_SNAP | F_LEG, 1, 0), (F_LEG | F_GLD, 1, 0), (F_LEG | F_ALW, 1, 0),
         (F_SNAP, 0, 1))
UNI_GAIN = {1: 0, 2: 0, 3: 0x68F5C3, 4: 0x5AE148}                       # 0.82, 0.71 (Hacks' chords); 1-2 voices: as they are


def _s():
    import synth0
    return synth0


def items(mixg, part):
    """part "n" (VMN, after poly0's piece A), "o" (VMO), "x" (VMX), "x2" (its tail); short relative branches (core0's bcc / bra)"""
    S = _s()
    ys = lambda o: f"y:(r6+${o:x})"                                     # noqa: E731
    if part == "n":                                                     # VMN (the note-on; S_VEL, S_TGT stored)
        return [("label", "vmn"), "move r6,a", f"move #>${S.GE0:x},x0", "cmp x0,a", ("bcc", "ge", "vm_old"),
                f"sub #>${S.Y0:x},a", "asr #6,a,a", "move a1,n1",                       # n1 = the slot
                "clr b", f"move x:>${VMK:x},a", f"move #>${VKEY:x},x0", "cmp x0,a", ("bcc", "ne", "vm_fl"),
                f"move {ys(S.C_TRK)},a", "sub #$1,a", "and #$7,a", f"add #>${VMF:x},a", "move a1,r1", "nop", "move x:(r1),b",
                ("label", "vm_fl"), "tst b", ("bcc", "eq", "vm_old"),
                # L (a = 1 / 0): sounding and (the gate on, or its note-off this block or the last)
                f"move {ys(S.S_STG)},a", f"cmp #${S.IDLE:x},a", ("bcc", "eq", "vm_n0"),
                f"move {ys(S.S_GATE)},a", "tst a", ("bcc", "ne", "vm_y"),
                f"move #>${OFF:x},r1", f"move x:>${VBLK:x},a", "move x:(r1+n1),x0", "sub x0,a", "move a1,a",
                "tst a", ("bcc", "lt", "vm_n0"), "cmp #$1,a", ("bcc", "gt", "vm_n0"),
                ("label", "vm_y"), "clr a", "add #$1,a", ("bra", "vm_d"),
                ("label", "vm_n0"), "clr a",
                ("label", "vm_d"),
                "btst #$2,b1", ("bcc", "cs", "vm_ng"),
                "btst #$1,b1", ("bcc", "cc", "vm_sn"),
                "tst a", ("bcc", "ne", "vm_ng"),
                ("label", "vm_sn"), f"move y1,{ys(S.S_PIT)}",
                ("label", "vm_ng"), "btst #$0,b1", ("bcc", "cc", "vm_rt"), "tst a", ("bcc", "eq", "vm_rt"),
                # legato: no attack; a release begun held again; the FM's note flag back
                f"move {ys(S.S_STG)},a", f"cmp #${S.REL:x},a", ("bcc", "ne", "vm_lf"),
                f"move #>${S.SUS:x},a", f"move a,{ys(S.S_STG)}",
                ("label", "vm_lf"), f"move #>${_ftr():x},r1", "clr a", "nop", "move a,x:(r1+n1)", ("bra", "vm_g"),
                # the old way (no flags, or a granular block): snapped when resting or without glide; the attack (b = 0: vm_ng -> vm_rt)
                ("label", "vm_old"), "clr b", f"move {ys(S.S_STG)},a", f"cmp #${S.IDLE:x},a", ("bcc", "eq", "vm_sn"),
                f"move {ys(S.C_GLD)},a", f"move #>${S.ONE:x},x0", "cmp x0,a", ("bcc", "ge", "vm_sn"),
                ("label", "vm_rt"), "clr a", f"move a,{ys(S.S_STG)}",
                ("label", "vm_g"), f"move #>${S.ONE:x},a", f"move a,{ys(S.S_GATE)}", "rts"]
    if part == "o":                                                     # VMO (the note-off, env2: after S_GATE = 0): OFF + s = the block
        return [("label", "vmo"), "move r6,a", f"move #>${S.GE0:x},x0", "cmp x0,a", ("bcc", "ge", "vo_x"),
                f"sub #>${S.Y0:x},a", "asr #6,a,a", "move a1,n1", f"move #>${OFF:x},r1", f"move x:>${VBLK:x},a", "move a1,x:(r1+n1)",
                ("label", "vo_x"), "rts"]
    if part == "x":                                                     # VMX (SY's last envelope block): the block's count, MIXG, the key
        return [("label", "vmx"), f"move x:>${VBLK:x},a", "add #$1,a", f"move a1,x:>${VBLK:x}", ("jsr", mixg),
                f"move x:>${VMK:x},a", f"move #>${VKEY:x},x0", "cmp x0,a", ("bcc", "ne", "vx_r"), ("jmp", X2_AT),
                ("label", "vx_r"), "rts"]
    # VMX2: the unison tracks' gain (X:UG + t, 0 = none) on their 32 samples
    return [("label", "vmx2"), "movep y:<<$ffffd0,b", "asl #5,b,b", f"add #>${S.TRK_BUF:x},b", "move b1,r3", f"move #>${UG:x},r1",
            "move #$40,n3",
            "do #$8,${vx_l:x}",
            "move x:(r1)+,y1", "move y1,a", "tst a", ("bcc", "eq", "vx_n"),
            "move r3,r0", "do #$20,${vx_s:x}", "move y:(r0),x0", "mpy x0,y1,a", "move a,y:(r0)+", ("label", "vx_s"),
            ("label", "vx_n"), "move (r3)+n3", ("label", "vx_l"),
            "rts"]


def _ftr():
    import poly0
    return poly0.FTR


O_AT, O_END = 0x1FED, 0x2000                                          # free P (RH80's map): VMO before RD20's test segment,
X_AT, X_END = 0x3AED, 0x3B00                                          # VMX before granchain's env,
X2_AT, X2_END = 0x39CE, 0x39ED                                        # VMX2 before fm8c0's ex2


def pieces(at, mixg, n_end=END):
    """-> [(address, words)] and the labels: VMN at P:at (after poly0's piece A), VMO at O_AT, VMX at X_AT"""
    import sp0 as SP
    out, lab = [], {}
    for part, a, end in (("n", at, n_end), ("o", O_AT, O_END), ("x", X_AT, X_END), ("x2", X2_AT, X2_END)):
        w, lb = C0.asm_at(SP.short_items(items(mixg, part)), a)
        assert a + len(w) <= end, f"vmode0's {part} ends at {a + len(w):#x} (> {end:#x})"
        out.append((a, w))
        lab.update(lb)
    return out, lab


def sizes(mixg=0x3000):
    import sp0 as SP
    return {p: len(C0.asm_at(SP.short_items(items(mixg, p)), 0x2000)[0]) for p in ("n", "o", "x", "x2")}


# ================================================================ the model (the tests'): synth0.Model's note-on / note-off with the flags
def note_on(st, c, flags, vblk, off, y1):
    """st = a slot's state (synth0.Model), c its controls, flags = X:VMF + t (0 = the old way), off = X:OFF + s; -> legato (bool)"""
    S = _s()
    if not flags:
        if st.get("stg") == S.IDLE or S.s24(c[S.C_GLD]) >= S.ONE:
            st["pit"] = S.s24(y1)
        st["stg"] = S.ATT
        st["gate"] = S.ONE
        return False
    d = (vblk - off) & 0xFFFFFF
    d = d - (1 << 24) if d & 0x800000 else d
    L = st.get("stg") != S.IDLE and (st.get("gate") != 0 or 0 <= d <= 1)
    snap = not (flags & F_ALW) and not ((flags & F_GLD) and L)
    if snap:
        st["pit"] = S.s24(y1)
    if (flags & F_LEG) and L:
        if st.get("stg") == S.REL:
            st["stg"] = S.SUS
    else:
        st["stg"] = S.ATT
    st["gate"] = S.ONE
    return bool((flags & F_LEG) and L)
