"""Level 1 emulation of the Fixed Recording tempo fix (Circuit Rhythm 5706).

Runs the stock functions 0x0803CE98 (samples + stop timer) and 0x08058F9C (length in ms) in Unicorn,
on the stock image and on the patched image, against hand-built stores and a fake clock object.
Usage: emu_fixedrec.py STOCK.bin [BUILT.bin]   (with BUILT.bin, "fixed" is that image, e.g. firmware/a0.01f/*.bin)
"""
import struct
import sys

from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, \
    UC_ARM_REG_R7, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC

APP = 0x08010000
RAM, RAM_SIZE = 0x20000000, 0x50000
GET = 0x0803FC58                       # store getter: &word i of the active buffer
TIMER = 0x08046DDE                     # timer start (id, x, ms, callback, [sp] = ctx): stubbed
SETUP = 0x0803CE98                     # fixedrec_setup_samples
LEN_MS = 0x08058F9C                    # fixedrec_length_ms (primary entry, this = object)
CALL_A, CALL_B = 0x0803CEA0, 0x08058FE0    # the two `bl GET` that read the BPM
CLOCK, CLOCK_VT = 0x200126E8, 0x08068EFC
HELPER = 0x0806B000                    # past the image end (0x0806A570); the real build uses Remix's free zone
EXIT = 0x0807FF00                      # return address the harness stops at

HELPER_ASM = f"""
    push {{r4, r5, r6, lr}}
    mov r4, r0
    ldr r5, =0x{CLOCK:08X}
    ldr r2, [r5]
    ldr r3, =0x{CLOCK_VT:08X}
    cmp r2, r3
    bne stock
    ldr r2, [r5, #0x14]
    cmp r2, r4
    bne stock
    ldr r0, [r5, #0x48]
    movs r1, #0
    bl 0x{GET:08X}
    ldrb r0, [r0]
    cmp r0, #0
    beq stock
    mov r0, r4
    movs r1, #1
    bl 0x{GET:08X}
    ldrb r2, [r0]
    subs r2, #40
    cmp r2, #200
    bhi stock
    pop {{r4, r5, r6, pc}}
stock:
    mov r0, r4
    movs r1, #0
    bl 0x{GET:08X}
    pop {{r4, r5, r6, pc}}
"""


def bl(src, dst):
    off = dst - (src + 4)
    s = (off >> 24) & 1
    i1, i2 = (off >> 23) & 1, (off >> 22) & 1
    j1, j2 = (1 - i1) ^ s, (1 - i2) ^ s
    h1 = 0xF000 | (s << 10) | ((off >> 12) & 0x3FF)
    h2 = 0xD000 | (j1 << 13) | (j2 << 11) | ((off >> 1) & 0x7FF)
    return struct.pack('<HH', h1, h2)


def bl_target(img, site):
    h1, h2 = struct.unpack_from('<HH', img, site - APP)
    s = (h1 >> 10) & 1
    i1, i2 = 1 - (((h2 >> 13) & 1) ^ s), 1 - (((h2 >> 11) & 1) ^ s)
    off = (s << 24) | (i1 << 23) | (i2 << 22) | ((h1 & 0x3FF) << 12) | ((h2 & 0x7FF) << 1)
    return site + 4 + off - ((1 << 25) if s else 0)


def build(stock, patched):
    img = bytearray(stock)
    if not patched:
        return bytes(img), 0
    ks = Ks(KS_ARCH_ARM, KS_MODE_THUMB)
    code, _ = ks.asm(HELPER_ASM, HELPER)
    for site in (CALL_A, CALL_B):
        assert bytes(img[site - APP:site - APP + 4]) == bl(site, GET), hex(site)
        img[site - APP:site - APP + 4] = bl(site, HELPER)
    return bytes(img), bytes(code)


class Heap:
    def __init__(self, uc, base):
        self.uc, self.p = uc, base

    def alloc(self, n):
        a = self.p
        self.p += (n + 7) & ~7
        return a

    def store(self, words, active_bits=0):
        """A double-buffered store: +4 active bits, +8 dirty bits, +0xC buf0, +0x10 buf1. Word i lives in buf[(active >> i) & 1]."""
        s = self.alloc(0x18)
        b0, b1 = self.alloc(4 * len(words)), self.alloc(4 * len(words))
        for i, w in enumerate(words):
            target = b1 if (active_bits >> i) & 1 else b0
            self.uc.mem_write(target + 4 * i, struct.pack('<I', w & 0xFFFFFFFF))
            other = b0 if target == b1 else b1
            self.uc.mem_write(other + 4 * i, struct.pack('<I', 0xDEAD0000 | i))   # stale copy: must never be read
        self.uc.mem_write(s, struct.pack('<IIIII', 0, active_bits, 0, b0, b1))
        return s


def run_case(image, helper, case):
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    uc.mem_map(0x08000000, 0x80000)
    uc.mem_write(APP, image)
    if helper:
        uc.mem_write(HELPER, helper)
    uc.mem_map(RAM, RAM_SIZE)
    heap = Heap(uc, 0x20030000)

    # clock object at its fixed address: vtable, +0x14 tempo store, +0x48 external-clock store
    tempo = heap.store([case['p0'], case['p1'], 50, 3], active_bits=case.get('active', 0))
    ext = heap.store([case['ext']])
    vt = case.get('clock_vt', CLOCK_VT)
    uc.mem_write(CLOCK, struct.pack('<I', vt))
    uc.mem_write(CLOCK + 0x14, struct.pack('<I', tempo))
    uc.mem_write(CLOCK + 0x48, struct.pack('<I', ext))
    rec_tempo = heap.store([case['p0'], case['p1']]) if case.get('other_store') else tempo

    timer = {}

    def hook(uc_, addr, size, _):
        if addr == TIMER:
            sp = uc_.reg_read(UC_ARM_REG_SP)
            timer['ms'] = uc_.reg_read(UC_ARM_REG_R2)
            timer['id'] = uc_.reg_read(UC_ARM_REG_R0)
            uc_.reg_write(UC_ARM_REG_PC, uc_.reg_read(UC_ARM_REG_LR))
        elif addr == EXIT:
            uc_.emu_stop()

    uc.hook_add(UC_HOOK_CODE, hook)
    callee = (0x11111111, 0x22222222, 0x33333333, 0x44444444)

    def call(fn, this):
        sp0 = 0x2004F000
        uc.reg_write(UC_ARM_REG_SP, sp0)
        uc.reg_write(UC_ARM_REG_R0, this)
        for reg, v in zip((UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7), callee):
            uc.reg_write(reg, v)
        uc.reg_write(UC_ARM_REG_LR, EXIT | 1)
        uc.emu_start(fn | 1, EXIT, count=20000)
        regs = tuple(uc.reg_read(r) for r in (UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7))
        return uc.reg_read(UC_ARM_REG_R0), uc.reg_read(UC_ARM_REG_SP) == sp0 and regs == callee

    # Fixed Recording controller: +0x10 tempo, +0x14 length index, +0x18 slot, +0x20.. targets, +0x224 slot bits
    fr = heap.alloc(0x240)
    slot = 5
    uc.mem_write(fr + 0x10, struct.pack('<I', rec_tempo))
    uc.mem_write(fr + 0x14, struct.pack('<I', heap.store([case['len']])))
    uc.mem_write(fr + 0x18, struct.pack('<I', heap.store([slot])))
    bits = heap.alloc(16)
    uc.mem_write(fr + 0x224, struct.pack('<I', bits))
    _, ok_a = call(SETUP, fr)
    samples = struct.unpack('<I', uc.mem_read(fr + 0x20 + 4 * slot, 4))[0]
    slot_bit = uc.mem_read(bits, 1)[0] & (1 << slot)

    # Sample Rec helper object: +0xC length index, +0x10 tempo
    obj = heap.alloc(0x40)
    uc.mem_write(obj + 0xC, struct.pack('<I', heap.store([case['len']])))
    uc.mem_write(obj + 0x10, struct.pack('<I', rec_tempo))
    ms, ok_b = call(LEN_MS, obj)
    return dict(samples=samples, timer=timer.get('ms'), timer_id=timer.get('id'), ms=ms, slot_bit=bool(slot_bit), abi=ok_a and ok_b)


STEPS = {0: 8, 1: 16, 2: 32, 3: 64}
MS_K = {0: 120000, 1: 240000, 2: 480000, 3: 960000}


def expect(bpm, idx):
    return dict(samples=720000 * STEPS[idx] // bpm, timer=(STEPS[idx] * 15000) // bpm + 50, ms=MS_K[idx] // bpm)


CASES = [
    # name, inputs, BPM the fixed build must use, BPM stock uses
    ("own clock, project 120",                  dict(p0=120, p1=0,   ext=0, len=1), 120, 120),
    ("own clock, stale measured 90 ignored",    dict(p0=120, p1=90,  ext=0, len=1), 120, 120),
    ("external 90, project 120 (the bug)",      dict(p0=120, p1=90,  ext=1, len=1), 90,  120),
    ("external 140, project 100",               dict(p0=100, p1=140, ext=1, len=3), 140, 100),
    ("external, measured not ready (0)",        dict(p0=120, p1=0,   ext=1, len=1), 120, 120),
    ("external, measured 39 (below range)",     dict(p0=120, p1=39,  ext=1, len=1), 120, 120),
    ("external, measured 40 (lowest valid)",    dict(p0=120, p1=40,  ext=1, len=1), 40,  120),
    ("external, measured 240 (highest valid)",  dict(p0=120, p1=240, ext=1, len=1), 240, 120),
    ("external, measured 241 (above range)",    dict(p0=120, p1=241, ext=1, len=1), 120, 120),
    ("external, measured in buffer 1",          dict(p0=120, p1=90,  ext=1, len=1, active=0b10), 90, 120),
    ("store is not the clock's tempo store",    dict(p0=120, p1=90,  ext=1, len=1, other_store=True), 120, 120),
    ("clock vtable does not match",             dict(p0=120, p1=90,  ext=1, len=1, clock_vt=0x08001234), 120, 120),
] + [(f"external 90, length index {i}", dict(p0=120, p1=90, ext=1, len=i), 90, 120) for i in range(4)]


def main():
    stock = open(sys.argv[1], 'rb').read()
    builds = {'stock': build(stock, False), 'fixed': build(stock, True)}
    if len(sys.argv) > 2:
        built = open(sys.argv[2], 'rb').read()
        targets = {hex(site): bl_target(built, site) for site in (CALL_A, CALL_B)}
        print(f"built image {sys.argv[2]}: calls -> {', '.join(f'{k}: {v:#x}' for k, v in targets.items())}")
        builds['fixed'] = (built, b'')
    else:
        print(f"helper: {len(builds['fixed'][1])} bytes at {HELPER:#x}")
    fails = 0
    for name, case, bpm_fixed, bpm_stock in CASES:
        line = []
        for label, (img, helper) in builds.items():
            got = run_case(img, helper, case)
            want = expect(bpm_fixed if label == 'fixed' else bpm_stock, case['len'])
            ok = (got['samples'] == want['samples'] and got['timer'] == want['timer'] and got['ms'] == want['ms']
                  and got['timer_id'] == 0xD and got['slot_bit'] and got['abi'])
            fails += not ok
            line.append(f"{label}: {'PASS' if ok else 'FAIL'} samples={got['samples']} timer={got['timer']}ms len={got['ms']}ms")
        print(f"{name:42} | " + " | ".join(line))
    off = run_case(builds['fixed'][0], builds['fixed'][1], dict(p0=120, p1=90, ext=1, len=0xFF))
    ok = off['ms'] == 32000
    fails += not ok
    print(f"{'fixed recording off (length 0xFF)':42} | fixed: {'PASS' if ok else 'FAIL'} len={off['ms']}ms (stock returns 32000)")
    print("ALL PASS" if not fails else f"{fails} FAIL")
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
