"""tools/dspz.py's LZSS (pack, the pieces, the DZ2 header) in JavaScript for the installer (MIT; RH80): the page packs the official image's
core 0 block with our stream itself, so no byte of Novation's code travels in it.  The same bytes as dspz.pack / split / header2
(tests/dzjs_test.py checks them in a browser)."""
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
  h.set([0x44, 0x5A, 0x32, 0]); dzU32(h, 4, b.words); dzU32(h, 8, b.crc); dzU32(h, 12, places.length);
  places.forEach(([at, [p, w]], j) => { dzU32(h, 16 + 12 * j, at); dzU32(h, 20 + 12 * j, w); dzU32(h, 24 + 12 * j, p.length); });
  return h;
}
function dzB64(s) { const a = atob(s), u = new Uint8Array(a.length); for (let i = 0; i < a.length; i++) u[i] = a.charCodeAt(i); return u; }
function dzApply(src, out, spec) {   // op 2: the pieces from the official image (src) into out (in place)
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
