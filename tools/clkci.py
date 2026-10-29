"""A count-in on the clock the music follows, master or slave (MIT; Circuit Rhythm 5706).

  * master: the count runs in the clock's 1 ms tick (the thunk 0x0803242C in front of clock_tick 0x08032430), in pulses of the
    project's tempo since the first click (24 a beat: ms x BPM x 0x1A36E3 / 2^32, the clock's own per-ms step);
  * slave (an external clock: bit 1 of [clock + 0x54]): the count is the incoming pulses (the clock's MIDI clock-in, vtable [0]
    0x08032BB6); the first click on the first pulse after the press, or on the first pulse of the master's next bar when its position is
    known: its clock counted from its Start or Song Position while it runs (the MIDI-in receivers, vtable 0x08066654: Start, Continue,
    Stop, Song Position);
  * clicks on pulses 0, 24, 48, 72 (the stock click through vismet's c_vmclick, at the metronome's level);
  * a gated start: Play is pressed at the count's start, so its work runs during the first beat; the clock's start (set_mode
    0x080329C0, its one call 0x0803333A) is held, then made on pulse 96: in that tick (master) or just before that pulse's own handling
    (slave), so step 1 is the bar's end;
  * the sampler's record function on pulse 96, before step 1;
  * a count begun while the music plays (not gated) follows the song's beats instead: the stock's beat check 0x080333AA(driver) on
    each pulse, a beat when [[driver + 8] + 0x20] (the pulse in the bar, 0-95) % 24 == 0; clicks on the beats left in the bar, a full
    bar when the next beat is its 1 (silent when the stock's metronome clicks: [driver + 0xC] p3), the sampler's record function on
    the bar's 1 after a click; over when the music stops;
  * nothing recorded while the start is held: the recorder's three record methods (vtable 0x08068CE4) read its store's p2 as set;
  * the Play LED as stopped while the start is held: its draw 0x08050384 reads the transport's p0 as 0; drawn again when the hold ends.
countin's Play (count-in on, Record armed, stopped) starts a gated count: master, the press goes on to the stock at once; slave, it is
pressed after the first click.  Play during a gated count stops it (the stock's stop once Play went through).  The count stops when the
transport stops or the clock starts from elsewhere (a master's Start).  The LED task: Record red 100 ms from each click and a queued
Play press.
RAM, slot "clkci": + 0 flags, + 1 the held mode, + 2 the master (bit 0 running, bit 1 position known), + 3 clicks made, + 4 the first click (uwTick, master), + 8 pulses since
the first click (slave), + 12 the last click (uwTick), + 16 the log (uwTick): begin, start held, clicks 1-4, pulse 96, record call,
+ 48 the master's pulses since its bar 1 (counted after each, 1 = its first pulse).
Install after countin and vismet, before srcount.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from thumb import (Asm, adds_imm3, adds_imm8, adds_reg, ands_reg, b, b_cond, b_w, bics_reg, bl, cmp_imm, cmp_reg, h, ldr_imm, ldr_sp, ldrb_imm,  # noqa: E402
                   ldrb_w, lsls_imm, mov_reg, movs_imm, movt, movw, muls, orrs_reg, pop_list, push_list, raw, str_imm, strb_imm, strb_w,
                   strh_reg, subs_reg, tst_reg)
import countin as C  # noqa: E402
import rhstate  # noqa: E402

ACT, GATE, SAMP, HELD, SLAVE, WAIT1, PLAYQ, SONG = 1, 2, 4, 8, 0x10, 0x20, 0x40, 0x80
RAM2 = "clkci" in getattr(rhstate, "OFF2", {})       # Circuit Remix: our slot in its second block, r4 = that block, countin's slot + CO
if RAM2:
    BASE, BMAGIC, O, CO = rhstate.ST2, rhstate.MAGIC2, rhstate.OFF2["clkci"][0], rhstate.ST - rhstate.ST2
else:
    BASE, BMAGIC, O, CO = rhstate.ST, rhstate.MAGIC, rhstate.OFF["clkci"][0], 0
O_FL, O_MODE, O_MS, O_N, O_T0, O_P, O_TB, O_LOG, O_MP = O, O + 1, O + 2, O + 3, O + 4, O + 8, O + 12, O + 16, O + 48
MS_RUN, MS_POS = 1, 2
MIDI_RT_VT = 0x08066654                                # the MIDI-in receivers' [0] Start, [1] Continue, [2] Stop, [3] Song Position (r1)
RT_START, RT_CONT, RT_STOP, RT_SPP = 0x0803F746, 0x0803F750, 0x0803F75A, 0x0803F764
LG_BEGIN, LG_HELD, LG_CLICK, LG_REL, LG_REC = 0, 4, 8, 24, 28
CLOCK, O_EXT, O_STATE = 0x200126E8, 0x54, 0x56
CLOCK_VT0, PULSE_IN = 0x08068EFC, 0x08032BB6
THUNK, CLOCK_TICK = 0x0803242C, 0x08032430
SETMODE, SETMODE_CALL = 0x080329C0, 0x0803333A
PARAM_GET, REC_P2_CALLS = 0x0803FC58, (0x08036AA6, 0x08036AE8, 0x08036B2A)   # each method records when p0 and p1 are set and p2 is 0
PLED_OBJ, PLED_VT, PLED_DRAW, PLED_P0_CALLS = 0x2004DFF0, 0x08067CAC, 0x08050384, (0x0805039A, 0x080503AA)
ZERO = 0x0801001C                                      # a reserved vector table word: always 0
UWTICK = 0x20000820
BEAT_FN, O_PULSE, METRO_P, RUNNING = 0x080333AA, 0x20, 3, 3
K = 0x1A36E3                                           # round(2^32 * 24 / 60000): pulses per ms per BPM, as the clock
PULSES, BAR = 24, 96
SAMPLER, SAMPLER_VT, O_SSTATE, READY, REC_FN = 0x200484F0, 0x08068B38, 0x14, 1, 0x0803CC2A
FLASH_MS = 100


def umull(rdlo, rdhi, rn, rm): return h(0xFBA0 | rn) + h(rdlo << 12 | rdhi << 8 | rm)


def arm_code(base, L):
    a = Asm(base)
    E = a.emit

    def imm32(rd, v):
        E(movw, rd, v & 0xFFFF)
        E(movt, rd, v >> 16)

    def ldb(rt, rn, off): E(ldrb_imm if off < 32 else ldrb_w, rt, rn, off)
    def stb(rt, rn, off): E(strb_imm if off < 32 else strb_w, rt, rn, off)

    def ldw(rt, rn, off):                              # LDR, or LDR.W Rt, [Rn, #imm12] past the narrow form's 124
        E(ldr_imm, rt, rn, off) if off < 128 else E(raw, h(0xF8D0 | rn) + h(rt << 12 | off))

    def stw(rt, rn, off):
        E(str_imm, rt, rn, off) if off < 128 else E(raw, h(0xF8C0 | rn) + h(rt << 12 | off))

    def flag(mask, out, cond="eq"):                     # r0 = the flags; branch to out on (flags & mask) == 0 ("eq") / != 0 ("ne"); clobbers r1
        ldb(0, 4, O_FL)
        E(movs_imm, 1, mask)
        E(tst_reg, 0, 1)
        E(b_cond, out, cond)

    def stamp(off):                                    # the log word = uwTick; clobbers r0
        imm32(0, UWTICK)
        E(ldr_imm, 0, 0, 0)
        stw(0, 4, O_LOG + off)

    # ---- c_ckblk() -> r0 = our block when set up, else 0 (never sets it up: the tick and the clock-in use it); clobbers r1, r2
    a.label("c_ckblk")
    imm32(0, BASE)
    imm32(1, rhstate.HEAP_LIMIT_PTR)
    E(ldr_imm, 1, 1, 0)
    E(cmp_reg, 1, 0)
    E(b_cond, "kb_no", "ne")
    E(ldr_imm, 1, 0, 0)
    imm32(2, BMAGIC)
    E(cmp_reg, 1, 2)
    E(b_cond, "kb_no", "ne")
    E(raw, h(0x4770))
    a.label("kb_no")
    E(movs_imm, 0, 0)
    E(raw, h(0x4770))

    # ---- c_ckready() -> r0 = 1 when the sampler is ready, in any view; clobbers r1-r3
    a.label("c_ckready")
    E(push_list, [3], lr=True)
    imm32(0, SAMPLER)
    E(ldr_imm, 1, 0, 0)
    imm32(2, SAMPLER_VT)
    E(cmp_reg, 1, 2)
    E(b_cond, "kr_no", "ne")
    E(ldr_imm, 0, 0, O_SSTATE)
    E(movs_imm, 1, 0)
    E(bl, C.PARAM_NEW)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, READY)
    E(b_cond, "kr_no", "ne")
    E(movs_imm, 0, 1)
    E(pop_list, [3], pc=True)
    a.label("kr_no")
    E(movs_imm, 0, 0)
    E(pop_list, [3], pc=True)

    # ---- c_ckmark(r4 = block) -> r0 = 1 when a click was due: counted, timed and logged, not sent; clobbers r1-r3
    a.label("c_ckmark")
    E(push_list, [5], lr=True)
    ldb(5, 4, O_N)
    E(cmp_imm, 5, 4)
    E(b_cond, "kc_no", "hs")
    E(adds_imm3, 0, 5, 1)
    stb(0, 4, O_N)
    imm32(0, UWTICK)
    E(ldr_imm, 0, 0, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "kc_t", "ne")
    E(movs_imm, 0, 1)                                  # never 0
    a.label("kc_t")
    stw(0, 4, O_TB)
    E(lsls_imm, 1, 5, 2)
    E(raw, h(0x1909))                                  # adds r1, r1, r4
    stw(0, 1, O_LOG + LG_CLICK)
    E(movs_imm, 0, 1)
    E(pop_list, [5], pc=True)
    a.label("kc_no")
    E(movs_imm, 0, 0)
    E(pop_list, [5], pc=True)

    # ---- c_ckclick(r4 = block): c_ckmark, and the click sent; clobbers r0-r3
    a.label("c_ckclick")
    E(push_list, [3], lr=True)
    E(bl, "c_ckmark")
    E(cmp_imm, 0, 0)
    E(b_cond, "kc_x", "eq")
    E(movs_imm, 0, 0xFF)
    E(movs_imm, 1, 0)
    E(movs_imm, 2, 0x60)
    E(bl, L["c_vmclick"])
    a.label("kc_x")
    E(pop_list, [3], pc=True)

    # ---- c_ckplay(r4 = block): Play pressed and released past countin and us (with Shift when countin's O_SH is set); clobbers r0-r3
    a.label("c_ckplay")
    E(push_list, [5], lr=True)
    ldb(5, 4, CO + C.O_SH)
    E(cmp_imm, 5, 0)
    E(b_cond, "kp_1", "eq")
    E(movs_imm, 0, 1)
    E(bl, L["c_cisetsh"])
    a.label("kp_1")
    E(movs_imm, 0, 1)
    stb(0, 4, CO + C.O_PASS)
    imm32(0, C.CTRL)
    E(movs_imm, 1, C.ID_PLAY)
    E(bl, C.BTN_ENTRY)
    imm32(0, C.CTRL)
    E(movs_imm, 1, C.ID_PLAY)
    E(bl, C.BTN_RELEASE)
    E(movs_imm, 0, 0)
    stb(0, 4, CO + C.O_PASS)
    E(cmp_imm, 5, 0)
    E(b_cond, "kp_x", "eq")
    E(movs_imm, 0, 0)
    E(bl, L["c_cisetsh"])
    E(movs_imm, 0, 0)
    stb(0, 4, CO + C.O_SH)
    a.label("kp_x")
    E(pop_list, [5], pc=True)

    # ---- c_ckbegin(r0 = GATE / SAMP / PLAYQ, r4 = block): a new count; master: the first click now; clobbers r0-r3
    a.label("c_ckbegin")
    E(push_list, [5], lr=True)
    E(movs_imm, 2, ACT)
    E(orrs_reg, 0, 2)
    E(mov_reg, 5, 0)
    E(movs_imm, 0, 0)
    stb(0, 4, O_N)
    stb(0, 4, CO + C.O_SH)
    stw(0, 4, O_P)
    stw(0, 4, O_TB)
    for k in range(8):
        stw(0, 4, O_LOG + 4 * k)
    stamp(LG_BEGIN)
    E(movs_imm, 0, GATE)
    E(tst_reg, 5, 0)
    E(b_cond, "kg_c", "ne")
    imm32(0, CLOCK)
    E(ldrb_w, 0, 0, O_STATE)
    E(cmp_imm, 0, RUNNING)
    E(b_cond, "kg_c", "ne")
    E(movs_imm, 0, SONG)                               # the music plays: the clicks on its next beats
    E(orrs_reg, 5, 0)
    stb(5, 4, O_FL)
    E(pop_list, [5], pc=True)
    a.label("kg_c")
    imm32(0, CLOCK)
    E(ldrb_w, 0, 0, O_EXT)
    E(lsls_imm, 0, 0, 30)
    E(b_cond, "kg_m", "pl")
    E(movs_imm, 0, SLAVE | WAIT1)                      # slave: the first click on the first pulse
    E(orrs_reg, 5, 0)
    stb(5, 4, O_FL)
    E(pop_list, [5], pc=True)
    a.label("kg_m")
    stb(5, 4, O_FL)
    imm32(0, UWTICK)
    E(ldr_imm, 0, 0, 0)
    stw(0, 4, O_T0)
    E(bl, "c_ckclick")
    E(pop_list, [5], pc=True)

    # ---- c_ckcancel(r4 = block): the count stopped; a held start: Play again (the stock's stop); clobbers r0-r3
    a.label("c_ckcancel")
    E(push_list, [5], lr=True)
    ldb(5, 4, O_FL)
    E(movs_imm, 0, 0)
    stb(0, 4, O_FL)
    E(movs_imm, 0, HELD)
    E(tst_reg, 5, 0)
    E(b_cond, "kn_x", "eq")
    E(bl, "c_ckplay")
    a.label("kn_x")
    E(pop_list, [5], pc=True)

    # ---- c_ckabort(r4 = block, r5 = clock) -> r0 = 1 when a held start stopped: the transport stopped, or the clock started elsewhere
    a.label("c_ckabort")
    E(push_list, [3], lr=True)
    flag(HELD, "ka_no")
    E(ldrb_w, 0, 5, O_STATE)
    E(cmp_imm, 0, 0)
    E(b_cond, "ka_stop", "ne")
    imm32(0, C.TRANSPORT)
    E(movs_imm, 1, 0)
    E(bl, C.PARAM_NEW)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "ka_stop", "eq")
    a.label("ka_no")
    E(movs_imm, 0, 0)
    E(pop_list, [3], pc=True)
    a.label("ka_stop")
    E(movs_imm, 0, 0)
    stb(0, 4, O_FL)
    E(bl, "c_ckpled")
    E(movs_imm, 0, 1)
    E(pop_list, [3], pc=True)

    # ---- c_ckrelease(r4 = block, r5 = clock): pulse 96: the held start made, the sampler's record function; the count over
    a.label("c_ckrelease")
    E(push_list, [6], lr=True)
    ldb(6, 4, O_FL)
    stamp(LG_REL)
    E(movs_imm, 0, GATE | HELD)
    E(mov_reg, 1, 6)
    E(ands_reg, 1, 0)
    E(cmp_reg, 1, 0)
    E(b_cond, "kl_s", "ne")
    E(mov_reg, 0, 5)
    ldb(1, 4, O_MODE)
    E(bl, SETMODE)
    a.label("kl_s")
    E(movs_imm, 0, SAMP)
    E(tst_reg, 6, 0)
    E(b_cond, "kl_x", "eq")
    E(bl, "c_ckready")
    E(cmp_imm, 0, 0)
    E(b_cond, "kl_x", "eq")
    stamp(LG_REC)
    imm32(0, SAMPLER)
    E(bl, REC_FN)
    a.label("kl_x")
    E(movs_imm, 0, 0)
    stb(0, 4, O_FL)
    E(movs_imm, 0, HELD)
    E(tst_reg, 6, 0)
    E(b_cond, "kl_y", "eq")
    E(bl, "c_ckpled")
    a.label("kl_y")
    E(pop_list, [6], pc=True)

    # ---- c_cktick (the thunk: r1 = clock): the master's count, then clock_tick(clock)
    a.label("c_cktick")
    E(mov_reg, 0, 1)
    E(push_list, [0, 4, 5, 6, 7], lr=True)
    E(mov_reg, 5, 0)
    E(bl, "c_ckblk")
    E(cmp_imm, 0, 0)
    E(b_cond, "kt_x", "eq")
    E(mov_reg, 4, 0)
    flag(ACT, "kt_x")
    flag(SONG, "kt_ns")
    E(ldrb_w, 0, 5, O_STATE)
    E(cmp_imm, 0, RUNNING)
    E(b_cond, "kt_x", "eq")
    E(movs_imm, 0, 0)                                  # the music stopped: the count over
    stb(0, 4, O_FL)
    E(b, "kt_x")
    a.label("kt_ns")
    flag(SLAVE, "kt_x", "ne")
    E(bl, "c_ckabort")
    E(cmp_imm, 0, 0)
    E(b_cond, "kt_x", "ne")
    imm32(0, C.TEMPO)
    E(movs_imm, 1, 0)
    E(bl, C.PARAM_NEW)
    E(ldrb_imm, 6, 0, 0)
    E(cmp_imm, 6, 30)
    E(b_cond, "kt_b", "hs")
    E(movs_imm, 6, 120)
    a.label("kt_b")
    imm32(0, UWTICK)
    E(ldr_imm, 0, 0, 0)
    ldw(1, 4, O_T0)
    E(subs_reg, 0, 0, 1)                               # ms since the first click
    E(muls, 0, 6)
    imm32(1, K)
    E(raw, umull(2, 3, 0, 1))                          # r3 = pulses since the first click
    E(cmp_imm, 3, BAR)
    E(b_cond, "kt_rel", "hs")
    ldb(0, 4, O_N)
    E(movs_imm, 1, PULSES)
    E(muls, 1, 0)
    E(cmp_reg, 3, 1)
    E(b_cond, "kt_x", "lo")
    E(bl, "c_ckclick")
    E(b, "kt_x")
    a.label("kt_rel")
    E(bl, "c_ckrelease")
    a.label("kt_x")
    E(raw, C.popw([0, 4, 5, 6, 7], lr=True))
    E(b_w, CLOCK_TICK)

    # ---- c_ckpulse (the clock's vtable [0]: r0 = clock, a MIDI clock pulse in): the slave's count, then the stock's handler
    a.label("c_ckpulse")
    E(push_list, [0, 4, 5], lr=True)
    E(mov_reg, 5, 0)
    E(bl, "c_ckblk")
    E(cmp_imm, 0, 0)
    E(b_cond, "ku_x", "eq")
    E(mov_reg, 4, 0)
    ldb(0, 4, O_MS)
    E(lsls_imm, 0, 0, 31)
    E(b_cond, "ku_c", "pl")
    ldw(0, 4, O_MP)
    E(adds_imm8, 0, 1)
    stw(0, 4, O_MP)
    a.label("ku_c")
    flag(ACT, "ku_x")
    flag(SLAVE, "ku_x")
    flag(SONG, "ku_x", "ne")
    E(bl, "c_ckabort")
    E(cmp_imm, 0, 0)
    E(b_cond, "ku_x", "ne")
    flag(WAIT1, "ku_n")
    ldb(2, 4, O_MS)
    E(cmp_imm, 2, MS_RUN | MS_POS)
    E(b_cond, "ku_go", "ne")
    ldw(2, 4, O_MP)
    E(movs_imm, 3, BAR)
    E(raw, C.udiv(1, 2, 3))
    E(muls, 1, 3)
    E(subs_reg, 2, 2, 1)
    E(cmp_imm, 2, 1)
    E(b_cond, "ku_x", "ne")                            # not the master's bar 1
    E(movs_imm, 1, WAIT1)
    a.label("ku_go")
    E(bics_reg, 0, 1)                                  # the first pulse: the first click; a gated count queues Play
    E(movs_imm, 1, GATE)
    E(tst_reg, 0, 1)
    E(b_cond, "ku_q", "eq")
    E(movs_imm, 1, PLAYQ)
    E(orrs_reg, 0, 1)
    a.label("ku_q")
    stb(0, 4, O_FL)
    E(bl, "c_ckclick")
    E(b, "ku_x")
    a.label("ku_n")
    ldw(0, 4, O_P)
    E(adds_imm8, 0, 1)
    stw(0, 4, O_P)
    E(cmp_imm, 0, BAR)
    E(b_cond, "ku_rel", "hs")
    ldb(1, 4, O_N)
    E(movs_imm, 2, PULSES)
    E(muls, 2, 1)
    E(cmp_reg, 0, 2)
    E(b_cond, "ku_x", "lo")
    E(bl, "c_ckclick")
    E(b, "ku_x")
    a.label("ku_rel")
    E(bl, "c_ckrelease")
    a.label("ku_x")
    E(raw, C.popw([0, 4, 5], lr=True))
    E(b_w, PULSE_IN)

    # ---- c_ckbeat (a head of the stock's beat check: r0 = the transport driver, a pulse): a count that follows the song's beats
    a.label("c_ckbeat")
    E(push_list, [0, 1, 2, 3, 4, 5, 6], lr=True)          # 8 words: the stack stays 8-byte aligned
    E(mov_reg, 5, 0)
    E(bl, "c_ckblk")
    E(cmp_imm, 0, 0)
    E(b_cond, "kw_x", "eq")
    E(mov_reg, 4, 0)
    flag(SONG, "kw_x")
    E(ldr_imm, 1, 5, 8)
    E(ldrb_w, 1, 1, O_PULSE)
    E(movs_imm, 2, PULSES)
    E(raw, C.udiv(3, 1, 2))
    E(muls, 3, 2)
    E(subs_reg, 1, 1, 3)
    E(b_cond, "kw_x", "ne")                            # not a beat; r3 = the beat's pulse in the bar
    E(cmp_imm, 3, 0)
    E(b_cond, "kw_c", "ne")
    ldb(0, 4, O_N)
    E(cmp_imm, 0, 0)
    E(b_cond, "kw_rel", "ne")                          # the bar's 1 after a click
    a.label("kw_c")
    E(ldr_imm, 0, 5, 0xC)
    E(movs_imm, 1, METRO_P)
    E(bl, PARAM_GET)
    E(ldrb_imm, 0, 0, 0)
    E(cmp_imm, 0, 0)
    E(b_cond, "kw_m", "ne")
    E(bl, "c_ckclick")
    E(b, "kw_x")
    a.label("kw_m")
    E(bl, "c_ckmark")                                  # the stock's metronome clicks this beat
    E(b, "kw_x")
    a.label("kw_rel")
    E(movs_imm, 0, 0)
    stb(0, 4, O_FL)
    stamp(LG_REL)
    E(bl, "c_ckready")
    E(cmp_imm, 0, 0)
    E(b_cond, "kw_x", "eq")
    stamp(LG_REC)
    imm32(0, SAMPLER)
    E(bl, REC_FN)
    a.label("kw_x")
    E(raw, C.popw([0, 1, 2, 3, 4, 5, 6], lr=True))
    E(b_w, L["prev_beat"])

    # ---- the MIDI-in receivers (r0 = this, r1 = Song Position's value): the master's position kept, then the stock's receiver
    def receiver(name, stock, body):
        a.label(name)
        E(push_list, [0, 1, 2, 3, 4], lr=True)
        E(bl, "c_ckblk")
        E(cmp_imm, 0, 0)
        E(b_cond, name + "_x", "eq")
        body()
        a.label(name + "_x")
        E(raw, C.popw([0, 1, 2, 3, 4], lr=True))
        E(b_w, stock)

    def ms(op, bits):
        ldb(1, 0, O_MS)
        E(movs_imm, 2, bits)
        E(op, 1, 2)
        stb(1, 0, O_MS)

    def on_start():
        E(movs_imm, 1, 0)
        stw(1, 0, O_MP)
        E(movs_imm, 1, MS_RUN | MS_POS)
        stb(1, 0, O_MS)

    def on_spp():
        E(ldr_sp, 1, 4)
        E(movs_imm, 2, 6)                              # a Song Position step = 6 pulses
        E(muls, 1, 2)
        stw(1, 0, O_MP)
        ms(orrs_reg, MS_POS)

    receiver("c_ckmstart", RT_START, on_start)
    receiver("c_ckmcont", RT_CONT, lambda: ms(orrs_reg, MS_RUN))
    receiver("c_ckmstop", RT_STOP, lambda: ms(bics_reg, MS_RUN))
    receiver("c_ckmspp", RT_SPP, on_spp)

    # ---- c_cksetmode (0x0803333A, b.w: r0 = clock, r1 = mode): a gated count's start held, else the stock's set_mode
    a.label("c_cksetmode")
    E(push_list, [0, 1, 4], lr=True)
    E(bl, "c_ckblk")
    E(cmp_imm, 0, 0)
    E(b_cond, "ks_go", "eq")
    E(mov_reg, 4, 0)
    ldb(0, 4, O_FL)
    E(movs_imm, 1, GATE | HELD)
    E(ands_reg, 1, 0)
    E(cmp_imm, 1, GATE)
    E(b_cond, "ks_go", "ne")
    E(movs_imm, 1, HELD)
    E(orrs_reg, 0, 1)
    stb(0, 4, O_FL)
    E(ldr_sp, 1, 4)
    stb(1, 4, O_MODE)
    stamp(LG_HELD)
    E(pop_list, [0, 1, 4], pc=True)
    a.label("ks_go")
    E(raw, C.popw([0, 1, 4], lr=True))
    E(b_w, SETMODE)

    # ---- c_ckheld() -> r0 = our block while a start is held, else 0; clobbers r1, r2
    a.label("c_ckheld")
    E(push_list, [3], lr=True)
    E(bl, "c_ckblk")
    E(cmp_imm, 0, 0)
    E(b_cond, "kh_x", "eq")
    ldb(1, 0, O_FL)
    E(movs_imm, 2, HELD)
    E(tst_reg, 1, 2)
    E(b_cond, "kh_x", "ne")
    E(movs_imm, 0, 0)
    a.label("kh_x")
    E(pop_list, [3], pc=True)

    # ---- c_ckrec (the recorder's p2 read: r0 = store, r1 = 2) -> r0 = that byte, or our flags (not 0) while a start is held
    a.label("c_ckrec")
    E(push_list, [4], lr=True)
    E(bl, PARAM_GET)
    E(mov_reg, 4, 0)
    E(bl, "c_ckheld")
    E(cmp_imm, 0, 0)
    E(b_cond, "kq_x", "eq")
    E(movw, 2, O_FL)
    E(adds_reg, 4, 0, 2)
    a.label("kq_x")
    E(mov_reg, 0, 4)
    E(pop_list, [4], pc=True)

    # ---- c_ckplp0 (the Play LED draw's transport p0 read: r0 = store, r1 = 0) -> r0 = that byte, or a 0 while a start is held
    a.label("c_ckplp0")
    E(push_list, [4], lr=True)
    E(bl, PARAM_GET)
    E(mov_reg, 4, 0)
    E(bl, "c_ckheld")
    E(cmp_imm, 0, 0)
    E(b_cond, "kz_x", "eq")
    imm32(4, ZERO)
    a.label("kz_x")
    E(mov_reg, 0, 4)
    E(pop_list, [4], pc=True)

    # ---- c_ckpled(): the Play LED drawn again (its object checked by its vtable); clobbers r0-r3
    a.label("c_ckpled")
    E(push_list, [3], lr=True)
    imm32(0, PLED_OBJ)
    E(ldr_imm, 1, 0, 0)
    imm32(2, PLED_VT)
    E(cmp_reg, 1, 2)
    E(b_cond, "ke_x", "ne")
    E(bl, PLED_DRAW)
    a.label("ke_x")
    E(pop_list, [3], pc=True)

    # ---- c_ckbtn (a head of the button chain: r0 = ctrl, r1 = id): countin's Play starts a gated count; Play during one stops it
    a.label("c_ckbtn")
    E(cmp_imm, 1, C.ID_PLAY)
    E(b_cond, "kb_g", "ne")
    E(push_list, [0, 1, 2, 4, 5], lr=True)
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "kb_f", "eq")
    E(mov_reg, 4, 0)
    ldb(0, 4, CO + C.O_PASS)
    E(cmp_imm, 0, 0)
    E(b_cond, "kb_f", "ne")                            # our own press
    flag(GATE, "kb_new")
    E(movs_imm, 1, 0)
    stb(1, 4, O_FL)
    E(movs_imm, 1, HELD)
    E(tst_reg, 0, 1)
    E(b_cond, "kb_f", "ne")                            # Play went through: the stock stops
    E(b, "kb_x")
    a.label("kb_new")
    E(cmp_imm, 0, 0)
    E(b_cond, "kb_f", "ne")                            # a sample count without a gate: Play is the stock's
    E(bl, L["c_ciok"])
    E(cmp_imm, 0, 0)
    E(b_cond, "kb_f", "eq")
    if RAM2:
        imm32(0, rhstate.ST)                           # countin's block
    else:
        E(mov_reg, 0, 4)
    E(bl, L["c_cistate"])
    E(lsls_imm, 0, 0, 30)
    E(b_cond, "kb_f", "pl")                            # no count-in
    imm32(0, C.TRANSPORT)
    E(movs_imm, 1, 0)
    E(bl, L["c_cinew"])
    E(cmp_imm, 0, 0)
    E(b_cond, "kb_f", "ne")                            # playing
    imm32(0, C.TRANSPORT)
    E(movs_imm, 1, 1)
    E(bl, L["c_cinew"])
    E(cmp_imm, 0, 0)
    E(b_cond, "kb_f", "eq")                            # Record not armed
    E(movs_imm, 0, GATE)
    E(bl, "c_ckbegin")
    flag(SLAVE, "kb_pass")
    E(bl, L["c_cishift"])                              # slave: pressed after the first click, with this Shift
    stb(0, 4, CO + C.O_SH)
    E(b, "kb_x")
    a.label("kb_pass")
    E(movs_imm, 0, 1)
    stb(0, 4, CO + C.O_PASS)
    E(raw, h(0x9800))                                  # ldr r0, [sp]
    E(raw, h(0x9901))                                  # ldr r1, [sp, #4]
    E(bl, L["prev_btn"])
    E(movs_imm, 0, 0)
    stb(0, 4, CO + C.O_PASS)
    a.label("kb_x")
    E(pop_list, [0, 1, 2, 4, 5], pc=True)
    a.label("kb_f")
    E(raw, C.popw([0, 1, 2, 4, 5], lr=True))
    a.label("kb_g")
    E(b_w, L["prev_btn"])

    # ---- c_ckled (a head of the LED task's chain: r0 = ctrl, r1 = frame): a queued Play press; Record red after each click
    a.label("c_ckled")
    E(push_list, [3, 4, 5], lr=True)
    E(mov_reg, 5, 1)
    E(bl, L["prev_led"])
    E(bl, L["c_rst"])
    E(cmp_imm, 0, 0)
    E(b_cond, "kd_x", "eq")
    E(mov_reg, 4, 0)
    flag(ACT, "kd_x")
    flag(PLAYQ, "kd_l")
    flag(WAIT1, "kd_l", "ne")
    E(movs_imm, 1, PLAYQ)
    E(bics_reg, 0, 1)
    stb(0, 4, O_FL)
    imm32(0, C.TRANSPORT)
    E(movs_imm, 1, 0)
    E(bl, L["c_cinew"])
    E(cmp_imm, 0, 0)
    E(b_cond, "kd_l", "ne")                            # playing already: a press would stop it
    E(bl, "c_ckplay")
    a.label("kd_l")
    E(movs_imm, 1, 0)
    ldw(3, 4, O_TB)
    E(cmp_imm, 3, 0)
    E(b_cond, "kd_w", "eq")
    imm32(0, UWTICK)
    E(ldr_imm, 0, 0, 0)
    E(subs_reg, 0, 0, 3)
    E(cmp_imm, 0, FLASH_MS)
    E(b_cond, "kd_w", "hs")
    E(movs_imm, 1, C.COL_REC)
    a.label("kd_w")
    E(movs_imm, 0, 2 * C.LED_REC)
    E(strh_reg, 1, 5, 0)
    a.label("kd_x")
    E(pop_list, [3, 4, 5], pc=True)
    return a.assemble()


def install(img, report, base_addr):
    import rh_fw
    import rhbuild
    assert "latdiag" not in report, "clkci shares its RAM slot with latdiag (rhstate.SHARED)"
    L = {k: int(v, 16) for k, v in report["countin"]["labels"].items()}
    L["c_rst"] = int(report["rhstate"]["labels"]["c_rram" if RAM2 else "c_rst"], 16)
    L["c_vmclick"] = int(report["vismet"]["labels"]["c_vmclick"], 16)
    L["prev_btn"] = rhbuild.bw_target(img, C.BTN_ENTRY)
    L["prev_beat"] = rhbuild.bw_target(img, BEAT_FN)
    L["prev_led"] = rhbuild.bl_target(img, C.LED_CALLS[0])
    assert all(rhbuild.bl_target(img, c) == L["prev_led"] for c in C.LED_CALLS)
    code, labels = arm_code(base_addr, L)
    img += bytes([0xFF]) * (base_addr - rh_fw.APP_BASE - len(img)) + code
    while len(img) % 4:
        img += bytes([0xFF])
    rhbuild.patch(img, C.BTN_ENTRY, f"b.w #{L['prev_btn']:#x}", b_w(C.BTN_ENTRY, labels["c_ckbtn"]))
    for c in C.LED_CALLS:
        rhbuild.patch(img, c, f"bl #{L['prev_led']:#x}", bl(c, labels["c_ckled"]))
    rhbuild.patch(img, THUNK, "mov r0, r1|nop", b_w(THUNK, labels["c_cktick"]))
    rhbuild.patch(img, SETMODE_CALL, f"b.w #{SETMODE:#x}", b_w(SETMODE_CALL, labels["c_cksetmode"]))
    rhbuild.patch_word(img, CLOCK_VT0, PULSE_IN | 1, labels["c_ckpulse"] | 1)
    for c in REC_P2_CALLS:
        rhbuild.patch(img, c, f"bl #{PARAM_GET:#x}", bl(c, labels["c_ckrec"]))
    rhbuild.patch(img, BEAT_FN, f"b.w #{L['prev_beat']:#x}", b_w(BEAT_FN, labels["c_ckbeat"]))
    for k, (stock, name) in enumerate(((RT_START, "c_ckmstart"), (RT_CONT, "c_ckmcont"), (RT_STOP, "c_ckmstop"), (RT_SPP, "c_ckmspp"))):
        rhbuild.patch_word(img, MIDI_RT_VT + 4 * k, stock | 1, labels[name] | 1)
    for c in PLED_P0_CALLS:
        rhbuild.patch(img, c, f"bl #{PARAM_GET:#x}", bl(c, labels["c_ckplp0"]))
    assert img[ZERO - rh_fw.APP_BASE:ZERO - rh_fw.APP_BASE + 4] == bytes(4)
    report["clkci"] = dict(slot=hex(BASE + O), prev_btn=hex(L["prev_btn"]), prev_led=hex(L["prev_led"]),
                           labels={k: hex(v) for k, v in labels.items() if k.startswith("c_")})
    return labels, code
