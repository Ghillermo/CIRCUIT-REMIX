"""tools/dspz.py's LZSS (pack, the pieces, the DZ2 header) in JavaScript for the installer (MIT; RH80): the page packs the official image's
core 0 block with our stream itself, so no byte of Novation's code travels in it.  The same bytes as dspz.pack / split / header2
(tests/dzjs_test.py checks them in a browser).  (RH95+, Alpha 0.16) the range coder too (dspz.pack_rc / split_rc; CIRCUIT-HACKS' dzPack2, our
code): op 2 v3 packs every DSP block in the page (the stock's as they are, ours / patched in place from their patch)."""
JS = r"""
function dzCrc32(u) { let c, t = dzCrc32.t; if (!t) { t = dzCrc32.t = new Uint32Array(256); for (let n = 0; n < 256; n++) { c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } }
  c = 0xFFFFFFFF; for (let i = 0; i < u.length; i++) c = t[(c ^ u[i]) & 0xFF] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; }
function dzStream(raw) {
  const n = raw.length, WIN = 0x2000, MAXL = 265, bestL = new Int32Array(n), bestO = new Int32Array(n), heads = new Map();
  for (let i = 0; i < n; i++) {
    let bl = 0, bo = 0;
    if (i + 3 <= n) {
      const key = raw[i] << 16 | raw[i + 1] << 8 | raw[i + 2], chain = heads.get(key);
      if (chain) {
        const lo = Math.max(-1, chain.length - 1 - 2048);
        for (let k = chain.length - 1; k > lo; k--) {
          const j = chain[k]; if (i - j > WIN) break;
          let ln = 0; while (ln < MAXL && i + ln < n && raw[j + ln] === raw[i + ln]) ln++;
          if (ln > bl) { bl = ln; bo = i - j; }
          if (ln === MAXL) break;
        }
        chain.push(i);
      } else heads.set(key, [i]);
    }
    bestL[i] = bl; bestO[i] = bo;
  }
  const cost = new Float64Array(n + 1), pick = new Int32Array(n);
  for (let i = n - 1; i >= 0; i--) {
    let c = 9 + cost[i + 1], p = 0; const ln = bestL[i];
    for (let m = 3; m <= ln; m++) { const mc = (m >= 10 ? 25 : 17) + cost[i + m]; if (mc < c) { c = mc; p = m; } }
    cost[i] = c; pick[i] = p;
  }
  const out = []; let flags = 0, items = [], i = 0, nf = 0;
  while (i < n) {
    const ln = pick[i];
    if (ln === 0) { flags |= 1 << nf; items.push(raw[i]); i++; }
    else { const o = bestO[i] - 1, code = ln >= 10 ? 7 : ln - 3; items.push(o & 0xFF, (o >> 8) | code << 5); if (code === 7) items.push(ln - 10); i += ln; }
    nf++; if (nf === 8) { out.push(flags); for (const x of items) out.push(x); flags = 0; items = []; nf = 0; }
  }
  if (nf) { out.push(flags); for (const x of items) out.push(x); }
  return Uint8Array.from(out);
}
function dzU32(a, o, v) { a[o] = v & 0xFF; a[o + 1] = v >>> 8 & 0xFF; a[o + 2] = v >>> 16 & 0xFF; a[o + 3] = v >>> 24 & 0xFF; }
function dzPack(raw) {   // -> {words, crc, st}
  return { words: raw.length / 3, crc: dzCrc32(raw), st: dzStream(raw) };
}
function dzBounds(st, size) {
  const bd = []; let out = 0, i = 0, flags = 1;
  while (out < size) {
    if (flags === 1) { flags = st[i] | 0x100; i++; }
    const lit = flags & 1; flags >>= 1;
    if (lit) { out++; i++; }
    else { const c = st[i + 1] >> 5; i += 2; if (c === 7) { out += 10 + st[i]; i++; } else out += c + 3; }
    bd.push([i, out]);
  }
  return bd;
}
function dzSplit(b, caps) {   // -> [[bytes, words], ...]
  const st = b.st, bd = dzBounds(st, 3 * b.words).filter(x => x[1] % 3 === 0), out = [];
  let pos = 0, opos = 0;
  for (const cap of caps) {
    let best = [pos, opos];
    for (const [i, o] of bd) { if (i - pos > cap) break; if (i > pos) best = [i, o]; }
    out.push([st.subarray(pos, best[0]), (best[1] - opos) / 3]); pos = best[0]; opos = best[1];
  }
  out.push([st.subarray(pos), b.words - opos / 3]);
  return out;
}
function dzHeader(b, places) {   // places: [[address, [bytes, words]], ...]
  const h = new Uint8Array(16 + 12 * places.length + 12);
  h.set([0x44, 0x5A, 0x32, 0]); dzU32(h, 4, b.words); dzU32(h, 8, b.crc); dzU32(h, 12, b.rc ? (places.length | 0x80000000) >>> 0 : places.length);
  places.forEach(([at, [p, w]], j) => { dzU32(h, 16 + 12 * j, at); dzU32(h, 20 + 12 * j, w); dzU32(h, 24 + 12 * j, p.length); });
  return h;
}
function dzB64(s) { const a = atob(s), u = new Uint8Array(a.length); for (let i = 0; i < a.length; i++) u[i] = a.charCodeAt(i); return u; }
// (RH95+) the range-coded format: tools/dspz.py _pack2, byte for byte (LZ with an optimal parse, two passes, integer prices + LZMA's range coder)
const DZRC = (() => {
  const PB = 11, ONE = 2048, MOVE = 5, TOP = 16777216, WIN = 4096, MAXL = 273;
  const ISM = 0x300, ISR = 0x30C, ISR0L = 0x318, MLEN = 0x324, RLEN = 0x324 + 274, SLOT = RLEN + 274, SPEC = SLOT + 256, ALIGN = SPEC + 114, NPROB = ALIGN + 16;
  const NEXT_LIT = [0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 4, 5];
  const PT = [];
  for (let i = 0; i < ONE >> 4; i++) {
    let w = (i << 4) + 8, bc = 0;
    for (let k = 0; k < 4; k++) { w = w * w; bc <<= 1; while (w >= 65536) { w = Math.floor(w / 2); bc++; } }
    PT.push((PB << 4) - 15 - bc);
  }
  const slotOf = d => { if (d < 4) return d; const n = 31 - Math.clz32(d); return 2 * n + ((d >> (n - 1)) & 1); };
  // the coders push (index, bit) pairs to a flat list; direct bits as (-1 - value, n)
  function litBits(L, byte, st, mbyte) {
    let offs = st >= 7 ? 0x100 : 0, m = mbyte, sym = 1;
    for (let k = 7; k >= 0; k--) { m <<= 1; const bit = m & offs, b = (byte >> k) & 1; L.push(offs + bit + sym, b); sym = sym << 1 | b; offs = b ? offs & bit : offs & ~bit; }
  }
  function lenBits(L, o, l) {
    l -= 2; let sub, nb, base;
    if (l < 8) { L.push(o, 0); sub = l; nb = 3; base = o + 2; }
    else if (l < 16) { L.push(o, 1, o + 1, 0); sub = l - 8; nb = 3; base = o + 10; }
    else { L.push(o, 1, o + 1, 1); sub = l - 16; nb = 8; base = o + 18; }
    let m = 1; for (let j = nb - 1; j >= 0; j--) { const b = (sub >> j) & 1; L.push(base + m, b); m = m << 1 | b; }
  }
  function distBits(L, l, d) {
    const sl = slotOf(d), base = SLOT + 64 * Math.min(l - 2, 3); let m = 1;
    for (let j = 5; j >= 0; j--) { const b = (sl >> j) & 1; L.push(base + m, b); m = m << 1 | b; }
    if (sl >= 4) {
      const nd = (sl >> 1) - 1, bse = (2 | (sl & 1)) << nd, rem = d - bse;
      if (sl < 14) { const o = SPEC + bse - sl - 1; m = 1; for (let j = 0; j < nd; j++) { const b = (rem >> j) & 1; L.push(o + m, b); m = m << 1 | b; } }
      else { L.push(-1 - (rem >> 4), nd - 4); m = 1; for (let j = 0; j < 4; j++) { const b = (rem >> j) & 1; L.push(ALIGN + m, b); m = m << 1 | b; } }
    }
  }
  function encoder() {
    let low = 0, rng = 0xFFFFFFFF, cache = 0, csize = 1; const out = [];
    const shift = () => {
      if (low < 0xFF000000 || low >= 4294967296) {
        const c = low >= 4294967296 ? 1 : 0; let t = cache;
        while (true) { out.push((t + c) & 0xFF); t = 0xFF; if (--csize === 0) break; }
        cache = Math.floor(low / 16777216) & 0xFF;
      }
      csize++; low = (low % 16777216) * 256;
    };
    return {
      bits(P, L) {
        for (let q = 0; q < L.length; q += 2) {
          const i = L[q], b = L[q + 1];
          if (i < 0) {
            const v = -1 - i;
            for (let k = b - 1; k >= 0; k--) { rng = Math.floor(rng / 2); if ((v >> k) & 1) low += rng; if (rng < TOP) { rng *= 256; shift(); } }
            continue;
          }
          const p = P[i], bound = Math.floor(rng / 2048) * p;
          if (b === 0) { rng = bound; P[i] = p + ((ONE - p) >> MOVE); } else { low += bound; rng -= bound; P[i] = p - (p >> MOVE); }
          if (rng < TOP) { rng *= 256; shift(); }
        }
      },
      flush() { for (let k = 0; k < 5; k++) shift(); if (out[0] !== 0) throw Error("dz2"); return out.slice(1); }
    };
  }
  function pack(raw) {
    const n = raw.length, cand = new Array(n), heads = new Map();
    for (let i = 0; i < n; i++) {
      const out = [];
      if (i + 2 <= n) {
        const key = raw[i] << 8 | raw[i + 1], ch = heads.get(key);
        if (ch) {
          let bl = 1;
          for (let k = ch.length - 1; k >= 0; k--) {
            const j = ch[k]; if (i - j > WIN) break;
            let l = 0; while (l < MAXL && i + l < n && raw[j + l] === raw[i + l]) l++;
            if (l > bl) { bl = l; out.push(l, i - j - 1); }
            if (l === MAXL) break;
          }
          ch.push(i);
        } else heads.set(key, [i]);
      }
      cand[i] = out;
    }
    let P = new Array(NPROB).fill(ONE / 2), res = null;
    for (let ps = 0; ps < 2; ps++) {
      const Q = ps ? P.slice() : new Array(NPROB).fill(ONE / 2);
      const bp = (i, b) => PT[(b === 0 ? Q[i] : ONE - Q[i]) >> 4];
      const price = L => { let c = 0; for (let q = 0; q < L.length; q += 2) c += L[q] < 0 ? 16 * L[q + 1] : bp(L[q], L[q + 1]); return c; };
      const cost = new Float64Array(n + 1).fill(Infinity); cost[0] = 0;
      const stt = new Int32Array(n + 1), rep = new Int32Array(n + 1), bi = new Int32Array(n + 1), bk = new Int32Array(n + 1), bln = new Int32Array(n + 1);
      const set = (j, pc, s, r, i, k, l) => { if (pc < cost[j]) { cost[j] = pc; stt[j] = s; rep[j] = r; bi[j] = i; bk[j] = k; bln[j] = l; } };
      for (let i = 0; i < n; i++) {
        const c0 = cost[i], st = stt[i], r0 = rep[i], mb = i - r0 - 1 >= 0 ? raw[i - r0 - 1] : 0;
        let L = []; litBits(L, raw[i], st, mb);
        set(i + 1, c0 + bp(ISM + st, 0) + price(L), NEXT_LIT[st], r0, i, 0, 1);
        if (i > r0) {
          let lr = 0; const j = i - r0 - 1;
          while (lr < MAXL && i + lr < n && raw[j + lr] === raw[i + lr]) lr++;
          if (lr) {
            const base = c0 + bp(ISM + st, 1) + bp(ISR + st, 1);
            set(i + 1, base + bp(ISR0L + st, 0), st < 7 ? 9 : 11, r0, i, 1, 1);
            const b2 = base + bp(ISR0L + st, 1);
            for (let l = 2; l <= lr; l++) { L = []; lenBits(L, RLEN, l); set(i + l, b2 + price(L), st < 7 ? 8 : 11, r0, i, 2, l); }
          }
        }
        const base = c0 + bp(ISM + st, 1) + bp(ISR + st, 0), cd = cand[i]; let prevl = 1;
        for (let q = 0; q < cd.length; q += 2) {
          const l = cd[q], d = cd[q + 1];
          for (let ll = Math.max(2, prevl + 1); ll <= l; ll++) {
            L = []; lenBits(L, MLEN, ll); const a = price(L); L = []; distBits(L, ll, d);
            set(i + ll, base + a + price(L), st < 7 ? 7 : 10, d, i, 3, ll);
          }
          prevl = l;
        }
      }
      const ops = []; let i = n;
      while (i > 0) { ops.push([bi[i], bk[i], bln[i], rep[i]]); i = bi[i]; }
      ops.reverse();
      const E = encoder(); P = new Array(NPROB).fill(ONE / 2); let st = 0, r0 = 0;
      for (const [i, k, l, d] of ops) {
        const L = [];
        if (k === 0) { const mb = i - r0 - 1 >= 0 ? raw[i - r0 - 1] : 0; L.push(ISM + st, 0); litBits(L, raw[i], st, mb); st = NEXT_LIT[st]; }
        else if (k === 1) { L.push(ISM + st, 1, ISR + st, 1, ISR0L + st, 0); st = st < 7 ? 9 : 11; }
        else if (k === 2) { L.push(ISM + st, 1, ISR + st, 1, ISR0L + st, 1); lenBits(L, RLEN, l); st = st < 7 ? 8 : 11; }
        else { L.push(ISM + st, 1, ISR + st, 0); lenBits(L, MLEN, l); distBits(L, l, d); st = st < 7 ? 7 : 10; r0 = d; }
        E.bits(P, L);
      }
      res = E.flush();
    }
    return res;
  }
  return { pack };
})();
function dzPackRc(raw) {   // -> {words, crc, st, rc}
  return { words: raw.length / 3, crc: dzCrc32(raw), st: Uint8Array.from(DZRC.pack(raw)), rc: 1 };
}
function dzSplitRc(b, caps) {   // the stream cut anywhere (the reader walks the pieces), the last piece the rest; words 0
  const st = b.st, out = []; let pos = 0;
  for (const cap of caps) { const n = Math.max(0, Math.min(cap, st.length - pos)); out.push([st.subarray(pos, pos + n), 0]); pos += n; }
  out.push([st.subarray(pos), 0]);
  return out;
}
function dzApply3(src, out, spec) {   // op 2 v3 (RH95+): every packed DSP block in the page, then core 0's stream in its holes (only its bytes)
  const BASE = 0x08010000, HE = 16, EN = 12;
  for (const [o, size, blen, ops] of spec.more) {
    const raw = ops ? applyPatch(src, ops) : src.subarray(o, o + size), b1 = dzPackRc(raw);
    const hd = dzHeader(b1, [[BASE + o + HE + 2 * EN, [b1.st, b1.words]]]);
    if (hd.length + b1.st.length !== blen) throw Error("dz: a block");
    out.set(hd, o); out.set(b1.st, o + hd.length);
  }
  const ours = applyPatch(src, spec.ours), raw = new Uint8Array(spec.blk[1] + ours.length);
  raw.set(src.subarray(spec.blk[0], spec.blk[0] + spec.blk[1])); raw.set(ours, spec.blk[1]);
  const b = dzPackRc(raw), H = spec.holes, hl = spec.hl;
  const ps = dzSplitRc(b, [H[0][1] - hl].concat(H.slice(1).map(h => h[1])));
  const places = [[BASE + H[0][0] + hl, ps[0]]];
  for (let k = 1; k < H.length; k++) places.push([BASE + H[k][0], ps[k]]);
  places.push([BASE + spec.cave[0], ps[ps.length - 1]]);
  const hd = dzHeader(b, places);
  if (hd.length !== hl || ps[ps.length - 1][0].length !== spec.cave[1]) throw Error("dz: sizes");
  H.forEach(([ho, hn], k) => { if (k === 0) { out.set(hd, ho); out.set(ps[0][0], ho + hl); } else out.set(ps[k][0], ho); });
  out.set(ps[ps.length - 1][0], spec.cave[0]);
}
function dzApply2(src, out, spec) {   // op 2 v2 (RD47+): the stock's other DSP blocks packed in place, then core 0's stream in its holes
  if (spec.rc) return dzApply3(src, out, spec);
  const BASE = 0x08010000, HE = 16, EN = 12;
  for (const [o, size] of spec.more) {
    const b1 = dzPack(src.subarray(o, o + size)), hd = dzHeader(b1, [[BASE + o + HE + 2 * EN, [b1.st, b1.words]]]);
    if (hd.length + b1.st.length > size) throw Error("dz: a block");
    out.fill(0xFF, o, o + size); out.set(hd, o); out.set(b1.st, o + hd.length);
  }
  const ours = applyPatch(src, spec.ours), raw = new Uint8Array(spec.blk[1] + ours.length);
  raw.set(src.subarray(spec.blk[0], spec.blk[0] + spec.blk[1])); raw.set(ours, spec.blk[1]);
  const b = dzPack(raw), H = spec.holes, hl = spec.hl;
  const ps = dzSplit(b, [H[0][1] - hl].concat(H.slice(1).map(h => h[1])));
  const places = [[BASE + H[0][0] + hl, ps[0]]];
  for (let k = 1; k < H.length; k++) places.push([BASE + H[k][0], ps[k]]);
  places.push([BASE + spec.cave[0], ps[ps.length - 1]]);
  const hd = dzHeader(b, places);
  if (hd.length !== hl || ps[ps.length - 1][0].length !== spec.cave[1]) throw Error("dz: sizes");
  H.forEach(([ho, hn], k) => { out.fill(0xFF, ho, ho + hn); if (k === 0) { out.set(hd, ho); out.set(ps[0][0], ho + hl); } else out.set(ps[k][0], ho); });
  out.set(ps[ps.length - 1][0], spec.cave[0]);
}
function dzApply(src, out, spec) {   // op 2: the pieces from the official image (src) into out (in place)
  if (spec.holes) return dzApply2(src, out, spec);
  const ours = applyPatch(src, spec.ours), raw = new Uint8Array(spec.blk[1] + ours.length);   // (our stream: a patch of the official image)
  raw.set(src.subarray(spec.blk[0], spec.blk[0] + spec.blk[1])); raw.set(ours, spec.blk[1]);
  const b = dzPack(raw), [o1, n1] = spec.r1, [o2, n2] = spec.r2, [o3, n3] = spec.r3, hl = spec.hl, BASE = 0x08010000;
  const ps = dzSplit(b, [n1 - hl, n2]);
  const hd = dzHeader(b, [[BASE + o1 + hl, ps[0]], [BASE + o2, ps[1]], [BASE + o3, ps[2]]]);
  if (hd.length !== hl || ps[2][0].length !== n3) throw Error("dz: sizes");
  out.fill(0xFF, o1, o1 + n1); out.set(hd, o1); out.set(ps[0][0], o1 + hl);
  out.fill(0xFF, o2, o2 + n2); out.set(ps[1][0], o2);
  out.set(ps[2][0], o3);
}
"""
