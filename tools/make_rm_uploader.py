"""tools/rm_uploader.html: the Circuit Remix installer, a web page that takes the OFFICIAL Circuit Rhythm firmware from the user, patches it in
the browser and sends it (no Novation code inside; MIT, from CIRCUIT-HACKS' make_rc_uploader.py).

    python tools/make_rm_uploader.py [VERSION ...]          (default: A0.04 A0.04S A0.03 A0.03S A0.02 A0.02S A0.01 A0.01S A0.0 A0.0S; needs firmware/<dir>/*.bin and the stock image of a full checkout)
Each version becomes a patch against the official image: COPY (offset, length) from the user's official image, or ADD (our bytes).  The matching is greedy
on 8-byte keys, so an ADD run never holds 8 or more consecutive bytes that also occur in the official image: the page carries only our own work
(checked again below).  The page:
  1. reads the official .syx (Components: https://components.novationmusic.com/api/v2/firmwares/169/file, Circuit Rhythm 2.0.1, build 5706) or its .bin,
     checks its SHA-256;
  2. applies the patch of the chosen version, checks the SHA-256 of the result against the published one, encodes the update (same format as
     rh_fw.encode) and checks the SHA-256 of that .syx against the published one too;
  3. sends it with the pull protocol of Components (the code of tools/rh_uploader.html).  "Oficial" sends the official file untouched (to go back).
"""
from __future__ import annotations
import base64
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rh_fw  # noqa: E402

STOCK_BIN = ROOT / "stock/circuitrhythm-firmware-5706-STOCK.bin"
DEFAULT = ["A0.04", "A0.04S", "A0.03", "A0.03S", "A0.02", "A0.02S", "A0.01", "A0.01S", "A0.0", "A0.0S"]

MIN = 8


def make_patch(src: bytes, dst: bytes):
    idx = {}
    for i in range(len(src) - MIN + 1):
        idx.setdefault(src[i:i + MIN], []).append(i)
    ops, lit, i, last = [], bytearray(), 0, -1
    def flush():
        if lit: ops.append([1, base64.b64encode(bytes(lit)).decode()]); lit.clear()
    while i < len(dst):
        best_len, best_off = 0, -1
        cands = []
        if last >= 0: cands.append(last)                      # the copy goes on where the previous one ended
        if i < len(src): cands.append(i)                      # the same place
        cands += idx.get(dst[i:i + MIN], [])[:64]
        for o in cands:
            if o < 0 or o >= len(src) or src[o:o + MIN] != dst[i:i + MIN]: continue
            n = MIN
            while i + n < len(dst) and o + n < len(src) and src[o + n] == dst[i + n]: n += 1
            if n > best_len: best_len, best_off = n, o
        if best_len >= MIN:
            flush(); ops.append([0, best_off, best_len]); i += best_len; last = best_off + best_len
        else:
            lit.append(dst[i]); i += 1; last = -1
    flush()
    return ops


def apply(src: bytes, ops):
    out = bytearray()
    for op in ops:
        out += src[op[1]:op[1] + op[2]] if op[0] == 0 else base64.b64decode(op[1])
    return bytes(out)


def check_add(stock: bytes, ops):
    """No ADD run may hold MIN or more consecutive bytes of the official image."""
    keys = {stock[i:i + MIN] for i in range(len(stock) - MIN + 1)}
    for o in ops:
        if o[0] == 1:
            lit = base64.b64decode(o[1])
            assert not any(lit[i:i + MIN] in keys for i in range(len(lit) - MIN + 1)), "an ADD run holds bytes of the official image"


def main(versions):
    stock = STOCK_BIN.read_bytes()
    assert hashlib.sha256(stock).hexdigest() == rh_fw.STOCK_5706["image_sha256"]
    patches = {}
    for v in versions:
        d = ROOT / "firmware" / v.lower(); man = json.loads((d / "manifest.json").read_text())
        img = next(d.glob("*.bin")).read_bytes()
        assert hashlib.sha256(img).hexdigest() == man["image_sha256"]
        ops = make_patch(stock, img)
        assert apply(stock, ops) == img
        check_add(stock, ops)
        lit = sum(len(base64.b64decode(o[1])) for o in ops if o[0] == 1)
        assert hashlib.sha256(rh_fw.encode(img)).hexdigest() == man["syx_sha256"]
        patches[v] = dict(dir=v.lower(), image_sha256=man["image_sha256"], syx_sha256=man["syx_sha256"], size=len(img), ops=ops)
        print(f"{v}: {len(ops)} ops, {lit} bytes of our own, {len(img) - lit} copied from the official image")
    page = TEMPLATE.replace("__PATCHES__", json.dumps(patches, separators=(",", ":"))).replace("__STOCK_SYX__", rh_fw.STOCK_5706["syx_sha256"]) \
        .replace("__STOCK_IMG__", rh_fw.STOCK_5706["image_sha256"]).replace("__VERSIONS__", ", ".join(versions)) \
        .replace("__SAFER__", next((v for v in versions if v.endswith("S")), versions[0]))
    (ROOT / "tools/rm_uploader.html").write_text(page, encoding="utf-8", newline="")
    print("tools/rm_uploader.html", len(page), "bytes")


DESC = {"A0.04": ("⚠️ experimental, necesita pulirse — Alpha 0.04 — la versión completa: Alpha 0.03 más el menú de pista (mantener su botón), el granular en hasta 4 pistas, la entrada de línea como sonido de pista, el enlace estéreo, Sample Rec estéreo, el de-clicker de loops, el modo cue, General MIDI y más; la copia de proyectos y de samples y el borrado de packs escriben en la tarjeta",
                  "⚠️ experimental, needs refinement — Alpha 0.04 — full build: Alpha 0.03 plus the track menu (hold its button), granular on up to 4 tracks, the line input as a track sound, the stereo link, stereo Sample Rec, the loop de-clicker, the cue mode, General MIDI and more; the project and sample copy and the pack delete write to the card"),
        "A0.04S": ("⚠️ experimental, necesita pulirse — Alpha 0.04S — versión más segura: Alpha 0.04 sin la copia de proyectos, el borrado de packs ni la copia de samples; nada de Circuit Remix escribe ni borra ficheros en la SD ni en la memoria interna",
                   "⚠️ experimental, needs refinement — Alpha 0.04S — safer build: Alpha 0.04 without the project copy, the pack delete and the sample copy; nothing of Circuit Remix writes or deletes files on the SD card or in the internal memory"),
        "A0.03": ("Alpha 0.03 — la versión completa: todas las funciones de Circuit Remix, con la página Stock+ completa (envolvente y LFO de tono, ring mod, tipos de filtro y pitch follow, stretch sin cambiar el tono, bitcrush, scan), que ya funciona desde el encendido, y Fixed Recording al tempo del reloj externo; la copia de proyectos y de samples y el borrado de packs escriben en la tarjeta",
                  "Alpha 0.03 — full build: every Circuit Remix feature, with the full Stock+ page (pitch envelope and LFO, ring mod, filter types and pitch follow, stretch without changing pitch, bitcrush, scan), now working right after power-on, and Fixed Recording at the external clock's tempo; the project and sample copy and the pack delete write to the card"),
        "A0.03S": ("Alpha 0.03S — versión más segura: Alpha 0.03 sin la copia de proyectos, el borrado de packs ni la copia de samples; nada de Circuit Remix escribe ni borra ficheros en la SD ni en la memoria interna",
                   "Alpha 0.03S — safer build: Alpha 0.03 without the project copy, the pack delete and the sample copy; nothing of Circuit Remix writes or deletes files on the SD card or in the internal memory"),
        "A0.02": ("⚠️ Stock+ puede no hacer nada unos minutos tras encender, arreglado en 0.03 — Alpha 0.02 — la versión completa: todas las funciones de Circuit Remix, con la página Stock+ completa (envolvente y LFO de tono, ring mod, tipos de filtro y pitch follow, stretch sin cambiar el tono, bitcrush, scan) y Fixed Recording al tempo del reloj externo; la copia de proyectos y de samples y el borrado de packs escriben en la tarjeta",
                  "⚠️ Stock+ may do nothing for a few minutes after power-on, fixed in 0.03 — Alpha 0.02 — full build: every Circuit Remix feature, with the full Stock+ page (pitch envelope and LFO, ring mod, filter types and pitch follow, stretch without changing pitch, bitcrush, scan) and Fixed Recording at the external clock's tempo; the project and sample copy and the pack delete write to the card"),
        "A0.02S": ("⚠️ Stock+ puede no hacer nada unos minutos tras encender, arreglado en 0.03S — Alpha 0.02S — versión más segura: Alpha 0.02 sin la copia de proyectos, el borrado de packs ni la copia de samples; nada de Circuit Remix escribe ni borra ficheros en la SD ni en la memoria interna",
                   "⚠️ Stock+ may do nothing for a few minutes after power-on, fixed in 0.03S — Alpha 0.02S — safer build: Alpha 0.02 without the project copy, the pack delete and the sample copy; nothing of Circuit Remix writes or deletes files on the SD card or in the internal memory"),
        "A0.01": ("⚠️ fallo en la pista 8 (chirridos, clics, tono), arreglado en 0.02; Stock+ tras encender, arreglado en 0.03 — Alpha 0.01 — la versión completa: todas las funciones de Circuit Remix, con la página Stock+ de los knobs de pista (envolvente y LFO de tono); la copia de proyectos y de samples y el borrado de packs escriben en la tarjeta",
                  "⚠️ track 8 bug (chirps, clicks, pitch), fixed in 0.02; Stock+ after power-on, fixed in 0.03 — Alpha 0.01 — full build: every Circuit Remix feature, with the Stock+ track knob page (pitch envelope and LFO); the project and sample copy and the pack delete write to the card"),
        "A0.01S": ("⚠️ fallo en la pista 8 (chirridos, clics, tono), arreglado en 0.02S; Stock+ tras encender, arreglado en 0.03S — Alpha 0.01S — versión más segura: Alpha 0.01 sin la copia de proyectos, el borrado de packs ni la copia de samples; nada de Circuit Remix escribe ni borra ficheros en la SD ni en la memoria interna",
                   "⚠️ track 8 bug (chirps, clicks, pitch), fixed in 0.02S; Stock+ after power-on, fixed in 0.03S — Alpha 0.01S — safer build: Alpha 0.01 without the project copy, the pack delete and the sample copy; nothing of Circuit Remix writes or deletes files on the SD card or in the internal memory"),
        "A0.0": ("Alpha 0.0 — la versión completa: todas las funciones de Circuit Remix (incluida la copia de proyectos, que escribe en la tarjeta)",
                 "Alpha 0.0 — full build: every Circuit Remix feature (including the project copy, which writes to the card)"),
        "A0.0S": ("Alpha 0.0S — versión más segura: Alpha 0.0 sin la copia de proyectos; nada de Circuit Remix escribe ni borra ficheros en la SD ni en la memoria interna",
                  "Alpha 0.0S — safer build: Alpha 0.0 without the project copy; nothing of Circuit Remix writes or deletes files on the SD card or in the internal memory")}


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Circuit Remix Installer</title>
<style>
  :root { --bg:#111317; --panel:#1a1d23; --line:#2b2f38; --ink:#e8e9ec; --dim:#9aa0ab; --ok:#7ee787; --warn:#ffb86b; --bad:#ff7b72; --acc:#79c0ff; }
  * { box-sizing:border-box; }
  body { margin:0; padding:24px 16px 64px; background:var(--bg); color:var(--ink); font:15px/1.55 system-ui,"Segoe UI",sans-serif; }
  main { max-width:760px; margin:0 auto; }
  h1 { font-size:1.4rem; margin:0 0 4px; }
  .sub { color:var(--dim); margin:0 0 20px; }
  section { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px 16px; margin-bottom:12px; }
  h2 { font-size:.8rem; letter-spacing:.08em; text-transform:uppercase; color:var(--dim); margin:0 0 10px; }
  button { font:inherit; font-weight:600; background:var(--acc); color:#0b0d10; border:0; border-radius:7px; padding:8px 14px; cursor:pointer; }
  button:disabled { background:#363b45; color:#7c838f; cursor:not-allowed; }
  select, input[type=file] { font:inherit; color:var(--ink); background:#0f1114; border:1px solid var(--line); border-radius:7px; padding:6px; width:100%; }
  .row { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
  .mono { font-family:ui-monospace,Consolas,monospace; font-size:.82rem; word-break:break-all; }
  .ok { color:var(--ok); } .bad { color:var(--bad); } .warn { color:var(--warn); }
  #log { height:220px; overflow:auto; background:#0b0d10; border:1px solid var(--line); border-radius:7px; padding:8px; white-space:pre-wrap; }
  progress { width:100%; height:14px; }
  ol { margin:0; padding-left:20px; } a { color:var(--acc); }
  .note { border-left:4px solid var(--warn); padding-left:10px; }
  .sub-steps { margin:4px 0 0; }
  html[lang="es"] .en, html[lang="en"] .es { display:none !important; }
  .top { display:flex; justify-content:space-between; align-items:baseline; gap:12px; flex-wrap:wrap; }
  .lang { display:flex; gap:4px; }
  .lang button { font-size:.8rem; padding:4px 10px; background:#2b2f38; color:var(--ink); }
  .lang button.on { background:var(--acc); color:#0b0d10; }
</style>
</head>
<body>
<main>
  <div class="top"><h1>Circuit Remix · <span class="es">Instalador</span><span class="en">Installer</span></h1>
    <div class="lang" role="group" aria-label="Idioma / Language"><button type="button" data-lang="es">Español</button><button type="button" data-lang="en">English</button></div></div>
  <p class="sub"><span class="es">Parchea en tu navegador el firmware oficial del Circuit Rhythm con Circuit Remix (__VERSIONS__) y lo envía al aparato. Circuit Remix es un port de las funciones de CIRCUIT-HACKS al Circuit Rhythm, con características exclusivas. Esta página no contiene código de Novation: solo el trabajo del mod.</span><span class="en">Patches the official Circuit Rhythm firmware with Circuit Remix (__VERSIONS__) in your browser and sends it to the device. Circuit Remix is a port of the CIRCUIT-HACKS features to the Circuit Rhythm, with exclusive features. This page contains no Novation code: only the mod’s own work.</span></p>

  <section>
    <h2><span class="es">Antes de empezar</span><span class="en">Before you start</span></h2>
    <ol>
      <li class="note"><span class="es"><b>Haz una copia de seguridad de la tarjeta SD</b> (proyectos, packs y samples) y no trabajes con proyectos importantes mientras pruebas el mod. Es una versión alfa: las funciones se han comprobado en emulación y en parte en el aparato. Si no quieres arriesgar la SD, elige __SAFER__.</span><span class="en"><b>Back up the SD card</b> (projects, packs and samples) and do not work on important projects while you test the mod. This is an alpha: the features were checked in emulation and partly on the device. If you do not want to risk the card, pick __SAFER__.</span></li>
      <li><span class="es">Descarga el firmware oficial <b>Circuit Rhythm 2.0.1 (build 5706)</b> desde Novation: <a href="https://components.novationmusic.com/api/v2/firmwares/169/file" target="_blank" rel="noopener">circuitrhythm-firmware-5706.syx</a> (descarga directa de Novation Components: el navegador guarda el <code>.syx</code>, 508 861 bytes). Novation Components: <a href="https://components.novationmusic.com/" target="_blank" rel="noopener">components.novationmusic.com</a>.</span><span class="en">Download the official <b>Circuit Rhythm 2.0.1 (build 5706)</b> firmware from Novation: <a href="https://components.novationmusic.com/api/v2/firmwares/169/file" target="_blank" rel="noopener">circuitrhythm-firmware-5706.syx</a> (Novation Components’ direct download: the browser saves the <code>.syx</code>, 508,861 bytes). Novation Components: <a href="https://components.novationmusic.com/" target="_blank" rel="noopener">components.novationmusic.com</a>.</span></li>
      <li><span class="es">Cierra Novation Components y cualquier DAW o programa MIDI (en Windows, un puerto MIDI solo lo puede abrir una aplicación).</span><span class="en">Close Novation Components and any DAW or MIDI program (on Windows a MIDI port can only be opened by one application).</span></li>
      <li><span class="es">Conecta el Circuit Rhythm por USB y enciéndelo de forma normal (o en modo bootloader: Sample Rec + Samples + Note al encender). No lo desconectes durante el envío.</span><span class="en">Connect the Circuit Rhythm over USB and power it on normally (or in bootloader mode: Sample Rec + Samples + Note at power-on). Do not disconnect it while sending.</span></li>
      <li><span class="es">Usa Chrome o Edge (Web MIDI con SysEx).</span><span class="en">Use Chrome or Edge (Web MIDI with SysEx).</span></li>
      <li class="note"><div class="es"><b>En caso de brick</b> (el aparato no arranca):<ol class="sub-steps"><li>Desconéctalo de la corriente.</li><li>Pulsa el botón de apagado 15-30 s.</li><li>Mantén <b>Sample Rec + Samples + Note</b> mientras lo enciendes.</li><li>Sube la última versión estable o el firmware de stock («Oficial») a través de esta misma página.</li></ol></div><div class="en"><b>If the device is bricked</b> (it does not start):<ol class="sub-steps"><li>Unplug it from power.</li><li>Press the power button for 15-30 s.</li><li>Hold <b>Sample Rec + Samples + Note</b> while you power it on.</li><li>Send the latest stable version or the stock firmware (“Official”) with this same page.</li></ol></div></li>
    </ol>
  </section>

  <section>
    <h2><span class="es">1 · Firmware oficial</span><span class="en">1 · Official firmware</span></h2>
    <input type="file" id="file" accept=".syx,.bin">
    <div id="fileInfo" class="mono" style="margin-top:8px"></div>
  </section>

  <section>
    <h2><span class="es">2 · Versión</span><span class="en">2 · Version</span></h2>
    <select id="ver"></select>
    <div id="verInfo" class="mono" style="margin-top:8px"></div>
    <label id="ackRow" class="row" style="margin-top:10px;align-items:flex-start;display:none"><input type="checkbox" id="ack" style="margin-top:3px"><span><span class="es">He copiado los datos de la tarjeta microSD a otro almacenamiento y no usaré la memoria interna de Circuit para guardar proyectos.</span><span class="en">I have copied the data of the microSD card to another storage and I will not use the Circuit’s internal memory to save projects.</span></span></label>
  </section>

  <section>
    <h2>3 · MIDI</h2>
    <div class="row"><button id="btnMidi"><span class="es">Permitir acceso MIDI</span><span class="en">Allow MIDI access</span></button><span id="midiState" class="warn"></span></div>
    <p><span class="es">Salida hacia el Rhythm</span><span class="en">Output to the Rhythm</span></p><select id="outSel"></select>
    <p><span class="es">Entrada desde el Rhythm</span><span class="en">Input from the Rhythm</span></p><select id="inSel"></select>
    <div class="row" style="margin-top:10px"><button id="btnId" disabled><span class="es">Identificar</span><span class="en">Identify</span></button><span id="idState"></span></div>
  </section>

  <section>
    <h2><span class="es">4 · Envío</span><span class="en">4 · Send</span></h2>
    <div class="row"><button id="btnSend" disabled><span class="es">Enviar</span><span class="en">Send</span></button><button id="btnAbort" disabled><span class="es">Cancelar</span><span class="en">Cancel</span></button></div>
    <p id="phase" class="warn"></p>
    <progress id="prog" value="0" max="100"></progress>
    <p class="sub"><span class="es">Durante el envío el Circuit Rhythm pide confirmación: pulsa <b>Play</b> en el aparato. Para volver al firmware oficial, elige «Oficial» y envíalo, o usa Novation Components.</span><span class="en">While sending, the Circuit Rhythm asks for confirmation: press <b>Play</b> on the device. To go back to the official firmware, pick “Official” and send it, or use Novation Components.</span></p>
  </section>

  <section>
    <h2><span class="es">Registro</span><span class="en">Log</span></h2>
    <div id="log" class="mono"></div>
  </section>
  <p class="sub"><span class="es">Circuit Remix no está afiliado a Novation. Circuit Rhythm, Components y Novation son marcas de Focusrite Audio Engineering Ltd. Proyecto desarrollado usando Claude (Anthropic).</span><span class="en">Circuit Remix is not affiliated with Novation. Circuit Rhythm, Components and Novation are trademarks of Focusrite Audio Engineering Ltd. Developed using Claude (Anthropic).</span></p>
</main>
<script>
"use strict";
const PATCHES = __PATCHES__;
const STOCK_SYX = "__STOCK_SYX__", STOCK_IMG = "__STOCK_IMG__";
const DESC = """ + json.dumps(DESC, ensure_ascii=False) + r""";
const NOV = [0xF0, 0x00, 0x20, 0x29, 0x00];
const $ = id => document.getElementById(id);
// ---------- the language: ?lang=, then the last choice, then the browser's
let LANG = (() => { const q = new URLSearchParams(location.search).get("lang"); if (q === "es" || q === "en") return q;
  try { const s = localStorage.getItem("cr-lang"); if (s === "es" || s === "en") return s; } catch (e) {}
  return /^es\b/i.test(navigator.language || "") ? "es" : "en"; })();
const t = (es, en) => LANG === "en" ? en : es;
const log = (m, cls) => { const d = document.createElement("div"); if (cls) d.className = cls;
  d.textContent = new Date().toLocaleTimeString() + "  " + m; $("log").appendChild(d); $("log").scrollTop = 1e9; };
// Text that goes into innerHTML is escaped: a file name like "<img onerror=…>.syx" must not run script on a page with SysEx access.
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const hex = a => Array.from(a, b => b.toString(16).padStart(2, "0")).join(" ");
let midi = null, packets = null, stockImg = null, stockSyx = null, xfer = null, idPending = null;

// ---------- the versions ("Oficial" = the official firmware, its value in either language)
const verLabel = v => v === "Oficial" ? t("Oficial — el firmware de Novation sin cambios (para volver atrás)", "Official — Novation’s firmware unchanged (to go back)")
  : (DESC[v] ? DESC[v][LANG === "en" ? 1 : 0] : v);
for (const v of [...Object.keys(PATCHES), "Oficial"]) { const o = document.createElement("option"); o.value = v; o.textContent = verLabel(v); $("ver").appendChild(o); }
let midiNote = null;                                       // the MIDI state shown, [es, en, class]
function setMidiState(es, en, cls) { midiNote = [es, en, cls]; $("midiState").textContent = t(es, en); $("midiState").className = cls; }
function setLang(l) {
  LANG = l; document.documentElement.lang = l; try { localStorage.setItem("cr-lang", l); } catch (e) {}
  for (const b of document.querySelectorAll(".lang button")) b.classList.toggle("on", b.dataset.lang === l);
  for (const o of $("ver").options) o.textContent = verLabel(o.value);
  if (midiNote) setMidiState(...midiNote);
  if (!stockImg) $("verInfo").textContent = t("Primero elige el firmware oficial.", "Pick the official firmware first.");
  fillPorts();
}
for (const b of document.querySelectorAll(".lang button")) b.onclick = () => setLang(b.dataset.lang);

// ---------- CRC-32/MPEG-2, 7-bit blocks
const CRC_T = (() => { const t = new Uint32Array(256); for (let i = 0; i < 256; i++) { let c = i << 24;
  for (let k = 0; k < 8; k++) c = (c & 0x80000000) ? ((c << 1) ^ 0x04C11DB7) : (c << 1); t[i] = c >>> 0; } return t; })();
function crc32mpeg(u8) { let c = 0xFFFFFFFF; for (const b of u8) c = ((c << 8) ^ CRC_T[((c >>> 24) ^ b) & 0xFF]) >>> 0; return c >>> 0; }
function nib(arr) { let v = 0; for (const b of arr) { if (b > 15) throw Error("nibble"); v = v * 16 + b; } return v; }
function nibbles(v, n) { const o = []; for (let i = n - 1; i >= 0; i--) o.push(Math.floor(v / 16 ** i) % 16); return o; }
function unpackBlock(p) { if (p.length !== 37) throw Error(t("bloque de longitud ", "block of length ") + p.length);
  let bits = 0n; for (const b of p) { if (b & 0x80) throw Error(t("byte no MIDI", "not a MIDI byte")); bits = (bits << 7n) | BigInt(b); }
  bits >>= 3n; const out = new Uint8Array(32); for (let i = 31; i >= 0; i--) { out[i] = Number(bits & 0xFFn); bits >>= 8n; } return out; }
function packBlock(b) { let bits = 0n; for (const x of b) bits = (bits << 8n) | BigInt(x); bits <<= 3n;
  const o = new Array(37); for (let i = 36; i >= 0; i--) { o[i] = Number(bits & 0x7Fn); bits >>= 7n; } return o; }
function splitSyx(u) { const msgs = []; for (let i = 0; i < u.length;) { const s = u.indexOf(0xF0, i); if (s < 0) break; const e = u.indexOf(0xF7, s); if (e < 0) throw Error(t("SysEx sin terminar", "unterminated SysEx"));
  const m = u.slice(s, e + 1); for (let k = 0; k < 5; k++) if (m[k] !== NOV[k]) throw Error(t("cabecera no Novation", "not a Novation header")); msgs.push(m); i = e + 1; } return msgs; }
function decodeSyx(buf) {
  const msgs = splitSyx(new Uint8Array(buf)), cmd = msgs.map(m => m[5]);
  if (cmd[0] !== 0x71 || cmd[1] !== 0x7C || cmd[cmd.length - 1] !== 0x73 || cmd.slice(2, -1).some(c => c !== 0x72)) throw Error(t("orden de mensajes inesperado", "unexpected message order"));
  const init = msgs[0].slice(6, -1); if (init[0] !== 0x01 || init[1] !== 0x63) throw Error(t("no es un firmware de Circuit Rhythm", "not a Circuit Rhythm firmware"));
  const hdr = msgs[1].slice(6, -1); const size = nib(hdr.slice(7, 15)), crc = nib(hdr.slice(15, 23));
  const blocks = [unpackBlock(msgs[msgs.length - 1].slice(6, -1))]; for (const m of msgs.slice(2, -1)) blocks.push(unpackBlock(m.slice(6, -1)));
  const img = new Uint8Array(blocks.length * 32); blocks.forEach((b, i) => img.set(b, i * 32));
  if (size > img.length || size > 0x70000) throw Error(t("tamaño inválido", "invalid size"));
  const im = img.slice(0, size); if (crc32mpeg(im) !== crc) throw Error(t("CRC no coincide", "CRC mismatch")); return { msgs, img: im };
}
function encodeSyx(img) {                               // = rh_fw.encode (protocol 0x731, product 0x63)
  const pad = new Uint8Array(Math.ceil(img.length / 32) * 32).fill(0xFF); pad.set(img);
  const msgs = [], H = NOV;
  msgs.push(Uint8Array.from([...H, 0x71, 0x01, 0x63, 0x00, 0x00, ...nibbles(0x731, 4), 0xF7]));
  msgs.push(Uint8Array.from([...H, 0x7C, 0x00, ...nibbles(0x731, 6), ...nibbles(img.length, 8), ...nibbles(crc32mpeg(img), 8), 0xF7]));
  for (let i = 32; i < pad.length; i += 32) msgs.push(Uint8Array.from([...H, 0x72, ...packBlock(pad.subarray(i, i + 32)), 0xF7]));
  msgs.push(Uint8Array.from([...H, 0x73, ...packBlock(pad.subarray(0, 32)), 0xF7]));
  return msgs;
}
function applyPatch(src, ops) {
  let n = 0; for (const o of ops) n += o[0] === 0 ? o[2] : atob(o[1]).length;
  const out = new Uint8Array(n); let p = 0;
  for (const o of ops) {
    if (o[0] === 0) { if (o[1] + o[2] > src.length) throw Error(t("parche fuera de rango", "patch out of range")); out.set(src.subarray(o[1], o[1] + o[2]), p); p += o[2]; }
    else { const s = atob(o[1]); for (let i = 0; i < s.length; i++) out[p++] = s.charCodeAt(i); }
  }
  return out;
}
async function sha256(buf) { const h = await crypto.subtle.digest("SHA-256", buf); return hex(new Uint8Array(h)).replace(/ /g, ""); }
function concat(msgs) { let n = 0; for (const m of msgs) n += m.length; const u = new Uint8Array(n); let p = 0; for (const m of msgs) { u.set(m, p); p += m.length; } return u; }

// ---------- the official file and the version
$("file").onchange = async () => {
  stockImg = stockSyx = null; packets = null; updateSend();
  const f = $("file").files[0]; if (!f) return;
  const buf = await f.arrayBuffer(); const h = await sha256(buf);
  let html = `${esc(f.name)} · ${buf.byteLength} bytes<br>SHA-256 ${h}<br>`;
  try {
    if (h === STOCK_SYX) { const d = decodeSyx(buf); stockImg = d.img; stockSyx = d.msgs; }
    else if (h === STOCK_IMG) { stockImg = new Uint8Array(buf); stockSyx = encodeSyx(stockImg); }
    else if (new Uint8Array(buf)[0] === 0xF0) { const d = decodeSyx(buf); if (await sha256(d.img) === STOCK_IMG) { stockImg = d.img; stockSyx = d.msgs; } }
    if (!stockImg) { $("fileInfo").innerHTML = html + `<span class="bad">${t("No es el firmware oficial Circuit Rhythm 2.0.1 (build 5706). Descárgalo con el enlace de arriba.", "This is not the official Circuit Rhythm 2.0.1 (build 5706) firmware. Download it with the link above.")}</span>`; return; }
    $("fileInfo").innerHTML = html + `<span class="ok">✔ ${t("firmware oficial Circuit Rhythm 2.0.1 (build 5706), imagen", "official Circuit Rhythm 2.0.1 (build 5706) firmware, image")} ${stockImg.length} bytes</span>`;
    log(t("Firmware oficial verificado", "Official firmware verified")); await prepare();
  } catch (e) { $("fileInfo").innerHTML = html + `<span class="bad">${t("Archivo inválido", "Invalid file")}: ${esc(e.message)}</span>`; }
};
$("ver").onchange = () => { updateAck(true); prepare(); updateSend(); };
async function prepare() {
  packets = null; updateSend(); if (!stockImg) { $("verInfo").textContent = t("Primero elige el firmware oficial.", "Pick the official firmware first."); return; }
  const v = $("ver").value;
  try {
    if (v === "Oficial") { packets = stockSyx; $("verInfo").innerHTML = `<span class="ok">✔ ${t("firmware oficial sin cambios", "official firmware unchanged")} · ${packets.length} ${t("mensajes", "messages")}</span>`; updateSend(); return; }
    const P = PATCHES[v]; const img = applyPatch(stockImg, P.ops);
    const hi = await sha256(img); if (hi !== P.image_sha256) throw Error(t("la imagen parcheada no coincide con la publicada (", "the patched image does not match the published one (") + hi.slice(0, 16) + "…)");
    const msgs = encodeSyx(img); const hs = await sha256(concat(msgs)); if (hs !== P.syx_sha256) throw Error(t("el .syx no coincide con el publicado (", "the .syx does not match the published one (") + hs.slice(0, 16) + "…)");
    packets = msgs;
    $("verInfo").innerHTML = `<span class="ok">✔ ${v}: ${t("imagen", "image")} ${img.length} bytes, SHA-256 ${hs} ${t("idéntico al publicado", "identical to the published one")} · ${msgs.length} ${t("mensajes", "messages")}</span>`;
    log(`${v} ${t("preparado y verificado", "prepared and verified")} (${hs.slice(0, 16)}…)`, "ok");
  } catch (e) { $("verInfo").innerHTML = `<span class="bad">${esc(e.message)}</span>`; }
  updateSend();
}
$("verInfo").textContent = t("Primero elige el firmware oficial.", "Pick the official firmware first.");

// ---------- MIDI (as tools/rh_uploader.html)
function closePort(p) {
  if (!p) return;
  try { if (p.type === "input") p.onmidimessage = null; } catch (e) {}
  if (p.state === "disconnected") return;
  try { if (p.type === "output" && p.clear) p.clear(); } catch (e) {}
  try { if (p.connection !== "closed") Promise.resolve(p.close()).catch(() => {}); } catch (e) {}
}
function openPorts(inp, out, ms = 6000) {
  return Promise.race([Promise.all([inp.open(), out.open()]),
    new Promise((_, rej) => setTimeout(() => rej(new Error(t("el puerto no responde (¿se está reiniciando el aparato?)", "the port does not respond (is the device restarting?)"))), ms))]);
}
function dropMidi(es, en) { releaseAll(); midi = null; for (const id of ["outSel", "inSel"]) $(id).innerHTML = "";
  $("btnId").disabled = true; setMidiState(es, en, "warn"); $("btnMidi").disabled = false; updateSend(); }
function releaseAll() {
  if (idPending) { clearTimeout(idPending.t); idPending.inp.removeEventListener("midimessage", idPending.h); idPending = null; }
  if (xfer) { clearTimeout(xfer.timer); xfer.inp.removeEventListener("midimessage", onMsg); xfer = null; }
  if (!midi) return; midi.onstatechange = null;
  for (const p of midi.inputs.values()) closePort(p); for (const p of midi.outputs.values()) closePort(p);
}
window.addEventListener("pagehide", () => { try { releaseAll(); } catch (e) {} midi = null; });
window.addEventListener("beforeunload", e => { if (xfer) { e.preventDefault(); e.returnValue = ""; return; } releaseAll(); });
$("btnMidi").onclick = async () => {
  if (midi) releaseAll();
  try { midi = await navigator.requestMIDIAccess({ sysex: true }); }
  catch (e) { setMidiState("acceso denegado: " + e.message, "access denied: " + e.message, "bad"); return; }
  setMidiState("acceso concedido", "access granted", "ok");
  midi.onstatechange = onState; fillPorts(); $("btnId").disabled = false; updateSend();
};
let portsTimer = null;
function onState(ev) {
  const p = ev.port; log(`MIDI: ${p.type} «${p.name}» ${p.state} / ${p.connection}`);
  if (p.state === "disconnected") {
    if (xfer && (p === xfer.out || p === xfer.inp)) { finish(t("el puerto del Circuit Rhythm ha desaparecido (¿se ha reiniciado o desconectado?)", "the Circuit Rhythm port has gone (restarted or disconnected?)"), "warn"); dropMidi("el aparato se está reiniciando: espera a que arranque y pulsa «Permitir acceso MIDI»", "the device is restarting: wait until it starts and press “Allow MIDI access”"); return; }
    if (idPending && (p === idPending.out || p === idPending.inp)) idDone(t("dispositivo desconectado", "device disconnected"), "bad");
    closePort(p);
    if (/circuit rhythm/i.test(p.name || "")) { dropMidi("el Circuit Rhythm se ha desconectado o reiniciado: cuando esté listo, pulsa «Permitir acceso MIDI»", "the Circuit Rhythm was disconnected or restarted: when it is ready, press “Allow MIDI access”"); return; }
  }
  clearTimeout(portsTimer); portsTimer = setTimeout(() => { if (midi) fillPorts(); }, 400);
}
function score(name) { if (!/circuit rhythm/i.test(name)) return -1; if (/midi ?[23]|midiin2|midiout2|midiin3|midiout3|din|daw/i.test(name)) return 0; return 2; }
function fillPorts() {
  if (!midi) return;
  for (const [sel, map] of [[$("outSel"), midi.outputs], [$("inSel"), midi.inputs]]) {
    const prev = sel.value; sel.innerHTML = "";
    const ports = [...map.values()].sort((a, b) => score(b.name) - score(a.name));
    for (const p of ports) { const o = document.createElement("option"); o.value = p.id; o.textContent = p.name + (score(p.name) === 2 ? t("  ← recomendado", "  ← recommended") : ""); sel.appendChild(o); }
    if ([...sel.options].some(o => o.value === prev)) sel.value = prev;
  }
  updateSend();
}
const outPort = () => midi && midi.outputs.get($("outSel").value);
const inPort = () => midi && midi.inputs.get($("inSel").value);
function idDone(msg, cls) { if (!idPending) return; const { t, inp, out, h } = idPending; idPending = null;
  clearTimeout(t); inp.removeEventListener("midimessage", h); closePort(inp); closePort(out); if (msg) { $("idState").textContent = msg; $("idState").className = cls; } }
$("btnId").onclick = () => {
  const out = outPort(), inp = inPort(); if (!out || !inp || idPending || xfer) return;
  $("idState").textContent = t("esperando respuesta…", "waiting for an answer…"); $("idState").className = "";
  function h(ev) { const d = ev.data;
    if (d.length === 17 && d[0] === 0xF0 && d[1] === 0x7E && d[3] === 0x06 && d[4] === 0x02) {
      const mode = d[9] === 1 ? "firmware" : d[9] === 17 ? "bootloader" : t("modo ", "mode ") + d[9]; const build = d[14] * 128 + d[15];
      idDone(`Circuit Rhythm · ${mode} · build ${build}`, "ok"); } }
  idPending = { inp, out, h, t: setTimeout(() => idDone(t("sin respuesta", "no answer"), "bad"), 2000) };
  inp.addEventListener("midimessage", h);
  openPorts(inp, out).then(() => { if (idPending && idPending.h === h) out.send([0xF0, 0x7E, 0x7F, 0x06, 0x01, 0xF7]); }).catch(e => idDone(t("no se pudo abrir el puerto: ", "could not open the port: ") + e.message, "bad"));
};
// ---------- the versions that write to the SD card (every one but the safer "…S" builds and the official firmware) ask for a tick first
const needsAck = v => v !== "Oficial" && !/S$/.test(v);
function updateAck(reset) { const need = needsAck($("ver").value); $("ackRow").style.display = need ? "flex" : "none"; if (reset || !need) $("ack").checked = false; }
$("ack").onchange = () => updateSend();
function updateSend() { updateAck(false); $("ack").disabled = !!xfer;
  $("btnSend").disabled = !(packets && outPort() && inPort() && !xfer && !idPending && (!needsAck($("ver").value) || $("ack").checked)); }

// ---------- transfer (pull protocol, as Components does)
const STATUS = { 0: ["inicio de actualización", "update started"], 1: ["esperando confirmación: PULSA PLAY en el Circuit Rhythm", "waiting for confirmation: PRESS PLAY on the Circuit Rhythm"],
  16: ["cancelado en el dispositivo", "cancelled on the device"], 17: ["se agotó el tiempo de confirmación", "the confirmation timed out"], 124: ["FALLO (composición no viable)", "FAILED (composition not viable)"],
  125: ["recibido (composición no viable)", "received (composition not viable)"], 126: ["FALLO (CRC)", "FAILED (CRC)"], 127: ["ÉXITO", "SUCCESS"] };
$("btnSend").onclick = () => {
  const name = $("outSel").selectedOptions[0].textContent;
  if (!confirm(t(`Se enviará ${$("ver").value} al puerto: ${name}\n\n¿Has hecho la copia de seguridad de la SD? No desconectes el Circuit Rhythm hasta que termine. ¿Continuar?`,
    `${$("ver").value === "Oficial" ? "The official firmware" : $("ver").value} will be sent to the port: ${name}\n\nHave you backed up the SD card? Do not disconnect the Circuit Rhythm until it ends. Continue?`))) return;
  start();
};
$("btnAbort").onclick = () => finish(t("cancelado por el usuario (el dispositivo descartará la actualización incompleta)", "cancelled by the user (the device will discard the incomplete update)"), "warn");
function start() {
  const out = outPort(), inp = inPort(); if (!out || !inp || xfer) return;
  if (idPending) idDone("", "");
  xfer = { out, inp, next: 0, last: -1, timer: null };
  $("btnSend").disabled = true; $("btnAbort").disabled = false; $("file").disabled = $("ver").disabled = true;
  inp.addEventListener("midimessage", onMsg);
  const me = xfer;
  openPorts(inp, out).then(() => { if (xfer !== me) return;
    log(`${t("Inicio", "Start")}: ${packets.length} ${t("mensajes", "messages")} → ${out.name}`); sendNext(); if (packets[xfer.next] && packets[xfer.next][5] === 0x7C) sendNext(); arm(25000);
  }).catch(e => finish(t("no se pudo abrir el puerto: ", "could not open the port: ") + e.message, "bad"));
}
function arm(ms) { clearTimeout(xfer.timer); xfer.timer = setTimeout(() => finish(t("tiempo de espera agotado; no se envió nada más", "timed out; nothing more was sent"), "bad"), ms); }
function sendNext() {
  const p = packets[xfer.next++]; xfer.out.send(p);
  $("prog").value = Math.round(100 * xfer.next / packets.length);
  if (xfer.next === packets.length) { $("phase").textContent = t("Transferido; esperando el informe del dispositivo…", "Transferred; waiting for the device’s report…"); arm(30000); }
}
function onMsg(ev) {
  const d = ev.data; if (!xfer || d[0] !== 0xF0) return;
  for (let k = 0; k < 5; k++) if (d[k] !== NOV[k]) return;
  if (d[5] === 0x72) {
    let n = null;
    if (d.length === 10) n = d[6] + (d[7] << 7) + (d[8] << 14);
    else if (d.length === 15) { const s = d.slice(6, 14); n = s[7] + (s[6] << 4) + (s[5] << 8); }
    if (n === null) return;
    if ((n > xfer.last || n === 0) && xfer.next < packets.length) { xfer.last = n; $("phase").textContent = t("Transfiriendo…", "Transferring…"); sendNext(); if (xfer.next < packets.length) arm(10000); }
  } else if (d[5] === 0x73 && d.length === 10) {
    const c = d[6]; log(`← ${t("estado", "status")} ${c}: ${STATUS[c] ? t(...STATUS[c]) : "?"}`, c === 127 ? "ok" : (c >= 124 || c === 16 || c === 17) ? "bad" : "");
    if (c === 1) { $("phase").textContent = t("PULSA PLAY en el Circuit Rhythm para confirmar", "PRESS PLAY on the Circuit Rhythm to confirm"); arm(25000); }
    else if (c === 0) arm(25000);
    else if (c === 127) { finish(t("Actualización recibida correctamente. El Circuit Rhythm se reiniciará e instalará el firmware: espera a que arranque.", "Update received correctly. The Circuit Rhythm restarts and installs the firmware: wait until it starts."), "ok"); dropMidi("el aparato se reinicia: cuando haya arrancado, pulsa «Permitir acceso MIDI»", "the device restarts: once it has started, press “Allow MIDI access”"); }
    else if (c === 125) arm(30000);
    else if (c === 16 || c === 17 || c === 124 || c === 126) finish(t("El dispositivo rechazó la actualización; el firmware actual no se modifica.", "The device refused the update; the current firmware is left unchanged."), "bad");
  }
}
function finish(msg, cls) {
  if (!xfer) return; const { inp, out } = xfer;
  clearTimeout(xfer.timer); inp.removeEventListener("midimessage", onMsg); xfer = null; closePort(inp); closePort(out);
  $("phase").textContent = msg; $("phase").className = cls; log(msg, cls);
  $("btnAbort").disabled = true; $("file").disabled = $("ver").disabled = false; updateSend();
}
$("outSel").onchange = $("inSel").onchange = updateSend;
setMidiState("sin acceso", "no access", "warn");
if (!navigator.requestMIDIAccess) setMidiState("este navegador no soporta Web MIDI: usa Chrome o Edge", "this browser does not support Web MIDI: use Chrome or Edge", "bad");
setLang(LANG); updateSend();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main(sys.argv[1:] or DEFAULT)
