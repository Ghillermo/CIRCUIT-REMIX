"""The user manual of Circuit Remix, by views, with a glossary of every function (MIT; the user, 2026-10-28: «Make a manual (circuit-hacks
style manual, group chapters per view when possible and add a glossary per function)»).  One source, two languages, two outputs each:

    python tools/make_guide.py      -> docs/MANUAL.md, docs/MANUAL_EN.md (text), docs/manual/index.html, docs/manual/en.html (illustrated:
                                       the pads and knobs in colour); in the development tree under public/

Every chapter: (id, part, {es, en: title, how to get there, detail in a small markdown: ### | tables | - lists, 1. lists, **bold**, `code`},
figures).  The glossary: one entry per function, linked to its chapter.  The colours follow docs/INTERFAZ.md (RH52 / Alpha 0.05).
"""
from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "Alpha 0.05"
OUT = ROOT / "public" / "docs" if (ROOT / "public").is_dir() else ROOT / "docs"     # (the development tree / the public one)

# ---------------------------------------------------------------------------------------------------- colours (the LEDs' RGB, docs/INTERFAZ.md)
C = dict(white="#ffffff", grey="#5a5a5a", sky="#14a5fe", lilac="#ffa2ff", mint="#8affd0", amber="#ffaf2f", steel="#5e84cc", red="#ff2020",
         yellow="#ffff19", green="#22ee44", orange="#fc9108", peach="#ff8682", cream="#e7ff9e", pink="#ff74be", magenta="#c63ac6",
         cyan="#44ddff", blue="#2f7bff", track="#ff4e13")
DIM = 0.32


def fig(es, en, pads=None, knobs=None, buttons=None):
    """pads: {n (1..32): (colour, label es, label en[, dim])}; knobs: {k (1..8): (label es, label en[, colour])}; buttons: [names held / pressed]"""
    return dict(es=es, en=en, pads=pads or {}, knobs=knobs or {}, buttons=buttons or [])


def svg(f, lang):
    """The 8 knobs and the 4 x 8 pads; the buttons the gesture uses as chips under them."""
    PW, PG, X0 = 58, 66, 20
    W = X0 * 2 + 7 * PG + PW
    kh = 96
    bh = 34 if f["buttons"] else 0
    H = kh + 4 * PG + 14 + bh
    li = 1 if lang == "es" else 2
    cap = f[lang]
    out = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{html.escape(cap)}">',
           f'<rect x="0" y="0" width="{W}" height="{H}" rx="18" fill="#17181b"/>']
    for k in range(1, 9):
        x = X0 + (k - 1) * PG + PW / 2
        y = 46
        spec = f["knobs"].get(k)
        ring = C.get(spec[3], spec[3]) if spec and len(spec) > 3 else ("#00c2a8" if spec else "#3a3d42")
        out.append(f'<circle cx="{x}" cy="{y}" r="21" fill="#26282c" stroke="{ring}" stroke-width="{4 if spec else 2}"/>')
        out.append(f'<text x="{x}" y="{y + 4}" font-size="11" fill="#cfd3d8" text-anchor="middle">K{k}</text>')
        if spec:
            out.append(f'<text x="{x}" y="{y + 36}" font-size="10" fill="{ring}" text-anchor="middle">{html.escape(spec[li])}</text>')
    for n in range(1, 33):
        r, c = (n - 1) // 8, (n - 1) % 8
        x, y = X0 + c * PG, kh + r * PG
        spec = f["pads"].get(n)
        if spec:
            col = C.get(spec[0], spec[0])
            dim = len(spec) > 3 and spec[3]
            out.append(f'<rect x="{x}" y="{y}" width="{PW}" height="{PW}" rx="7" fill="{col}" fill-opacity="{DIM if dim else 0.95}" stroke="#000"/>')
            lines = spec[li].split("\n") if spec[li] else []
            tc = "#eee" if dim else "#111"
            for i, ln in enumerate(lines[:3]):
                out.append(f'<text x="{x + PW / 2}" y="{y + 28 + 12 * i - 6 * (len(lines[:3]) - 1)}" font-size="9.5" fill="{tc}" '
                           f'text-anchor="middle" font-weight="bold">{html.escape(ln)}</text>')
        else:
            out.append(f'<rect x="{x}" y="{y}" width="{PW}" height="{PW}" rx="7" fill="#2b2d31" stroke="#111"/>')
        out.append(f'<text x="{x + 4}" y="{y + 54}" font-size="8" fill="#7d838a">{n}</text>')
    if f["buttons"]:
        bx, by = X0, kh + 4 * PG + 8
        for b_ in f["buttons"]:
            b_ = b_[li - 1] if isinstance(b_, tuple) else b_
            w = 14 + 7 * len(b_)
            out.append(f'<rect x="{bx}" y="{by}" width="{w}" height="22" rx="5" fill="#ff6a13"/>')
            out.append(f'<text x="{bx + w / 2}" y="{by + 15}" font-size="11" fill="#111" text-anchor="middle" font-weight="bold">{html.escape(b_)}</text>')
            bx += w + 8
    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------------------------------------------- the chapters
PARTS = [("0", "Introducción", "Introduction"), ("1", "En cualquier vista", "In any view"), ("2", "Vistas de pista", "Track views"),
         ("3", "Pasos y patrón", "Steps and pattern"), ("4", "Samples", "Samples"), ("5", "Mezcla y efectos", "Mix and effects"),
         ("6", "Proyectos y ajustes", "Projects and settings"), ("A", "Apéndice", "Appendix")]
V = []


def view(vid, part, es, en, figs=()):
    """es / en: (title, how to get there, detail[, figures])"""
    if len(es) > 3:
        es, figs = es[:3], es[3]
    V.append(dict(id=vid, part=part, es=es, en=en, figs=list(figs)))


A = "*(Alpha 0.05)*"
A_EN = "*(Alpha 0.05)*"

# ===== 0
view("leer", "0", ("Cómo leer este manual", "—", """
Cada capítulo es una vista del aparato: cómo se llega, qué hacen sus pads, knobs y botones con Circuit Remix. Todo lo demás funciona como en el firmware original de Novation (consulta su manual); los gestos nuevos son combinaciones que en el original no hacían nada o repetían el gesto sin modificador.

- **Pads 1-32** de izquierda a derecha y de arriba abajo: fila 1 = 1-8, fila 2 = 9-16, fila 3 = 17-24, fila 4 = 25-32.
- **K1-K8** = los 8 knobs. **▲ / ▼** = los botones de flecha.
- **Mantener** un botón = pulsarlo y no soltarlo; **A + B** = B con A mantenido.
- **★** = exclusiva de Circuit Remix (no está en CIRCUIT-HACKS).
- **(desde Alpha 0.0x)** = la versión que trajo la función. Lo marcado {A} es nuevo o cambia en esta versión.
- Al final, el **[glosario](#glosario)**: una entrada por función, con su vista y su gesto.
"""), ("How to read this manual", "—", """
Each chapter is a view of the device: how you get there, and what its pads, knobs and buttons do with Circuit Remix. Everything else works as in Novation's original firmware (see its manual); the new gestures are combinations that did nothing in the original or repeated the plain gesture.

- **Pads 1-32** left to right, top to bottom: row 1 = 1-8, row 2 = 9-16, row 3 = 17-24, row 4 = 25-32.
- **K1-K8** = the 8 knobs. **▲ / ▼** = the arrow buttons.
- **Hold** a button = press it and keep it down; **A + B** = B with A held.
- **★** = exclusive to Circuit Remix (not in CIRCUIT-HACKS).
- **(since Alpha 0.0x)** = the release that brought the function. Marked {A}: new or changed in this release.
- At the end, the **[glossary](#glosario)**: one entry per function, with its view and its gesture.
"""))

view("colores", "0", ("El código de colores", "—", f"""
Desde Alpha 0.05 todo lo nuevo sigue unas reglas fijas {A}:

| Regla | Qué ves |
|---|---|
| El brillo es el valor | en una página de knobs, todos los knobs del mismo color; cuanto más brillo, más valor |
| Knobs con centro | el centro (el cero) oscuro; más brillo hacia los dos extremos |
| Frecuencias (LFO, scan) | centro = parado; a la derecha libre, más rápido hacia el extremo; a la izquierda a tempo, divisiones más rápidas hacia el extremo |
| Adelante / atrás (scan del granular) | centro = parado; a la derecha hacia delante, a la izquierda hacia atrás, más rápido hacia los extremos |
| Encendido / apagado | el mismo color, brillante / tenue |
| Modos | un color por modo (las formas de onda del sinte, el tipo de filtro de Stock+, el metrónomo) |
| Opciones que se eligen entre sí | en la misma fila; la elegida brillante, las demás tenues |
| Abrir un menú o una página | un toque lo deja abierto; mantenerlo lo muestra hasta soltar |

Cada página de knobs de una pista tiene su color, el mismo en sus knobs, en el botón de la pista (que parpadea) y en su pad del menú:

| Página | Color |
|---|---|
| stock (la del firmware original) | blanco en el menú; los knobs, los del original |
| Stock+ | azul cielo |
| Granular | lila |
| Sinte | menta |
""", [fig("Las páginas de knobs en el menú de pista: brillante = la que se ve.", "The knob pages in the track menu: bright = the one shown.",
          pads={1: ("white", "stock", "stock"), 2: ("sky", "Stock+", "Stock+", True), 3: ("lilac", "Granular", "Granular", True),
                4: ("mint", "Sinte", "Synth", True)})]), ("The colour code", "—", f"""
Since Alpha 0.05 everything new follows fixed rules {A_EN}:

| Rule | What you see |
|---|---|
| Brightness is the value | on a knob page every knob has the same colour; the brighter, the higher |
| Knobs with a centre | the centre (zero) dark; brighter towards both ends |
| Frequencies (LFO, scan) | centre = stopped; right = free running, faster towards the end; left = synced to the tempo, faster divisions towards the end |
| Forward / backward (the granular scan) | centre = stopped; right forward, left backward, faster towards the ends |
| On / off | the same colour, bright / dim |
| Modes | a colour per mode (the synth's waveforms, Stock+'s filter type, the metronome) |
| Options you pick one of | on the same row; the chosen one bright, the others dim |
| Opening a menu or a page | a tap keeps it open; holding shows it until you let go |

Each knob page of a track has its own colour, the same on its knobs, on the track's (blinking) button and on its pad in the menu:

| Page | Colour |
|---|---|
| stock (the original firmware's) | white in the menu; the knobs, the original's |
| Stock+ | sky blue |
| Granular | lilac |
| Synth | mint |
"""))

view("instalar", "0", ("Instalar y volver al original", "—", """
1. Descarga `rm_uploader.zip`, descomprímelo y abre `rm_uploader.html` en Chrome o Edge.
2. Aporta el firmware oficial 2.0.1 (build 5706) del Circuit Rhythm: el instalador comprueba su SHA-256 y lo parchea en tu ordenador.
3. Elige la versión y envíala al aparato por USB.

**Versiones S** (A0.05S): sin las funciones que crean, cambian o borran ficheros de la tarjeta por su cuenta (copiar proyectos, borrar packs, copiar samples). La más segura para tu SD.

**Volver al firmware oficial:** mantén **Sample Rec + Samples + Note** al encender (modo bootloader de Novation) y envía el oficial con el instalador («Oficial») o con Novation Components. Haz siempre una copia de tu tarjeta SD.
"""), ("Install and go back to the original", "—", """
1. Download `rm_uploader.zip`, unzip it and open `rm_uploader.html` in Chrome or Edge.
2. Provide the official Circuit Rhythm firmware 2.0.1 (build 5706): the installer checks its SHA-256 and patches it on your computer.
3. Pick the version and send it to the device over USB.

**S versions** (A0.05S): without the functions that create, change or delete files on the card by themselves (project copy, pack delete, sample copy). The safest for your SD.

**Back to the official firmware:** hold **Sample Rec + Samples + Note** while powering on (Novation's bootloader mode) and send the official one with the installer ("Official") or with Novation Components. Always back up your SD card.
"""))

# ===== 1
view("transporte", "1", ("Transporte, metrónomo y cuantizar", "en cualquier vista", """
| Gesto | Qué hace |
|---|---|
| **Shift + Clear** | metrónomo en cuatro estados; con Shift, el LED de Clear: rojo = sin metrónomo, verde = metrónomo, magenta = solo cuenta atrás, cian = las dos *(desde Alpha 0.0)* |
| **Record armado + Play** (parado, con cuenta atrás) | un compás de clics al tempo y arranca grabando (Record parpadea); Play durante la cuenta la cancela |
| **Shift + Play** (parado) | el del original: sigue desde donde se paró; con cuenta atrás, la cuenta y luego sigue |
| **Shift + Play** (sonando) | cuantiza el patrón de la pista elegida: los micropasos 2-3 al comienzo de su paso, 4-6 al del siguiente; los redobles se quedan. LED de Play con Shift: amarillo; verde tras cuantizar; rojo = nada que cuantizar *(desde Alpha 0.0)* |

La cuenta atrás no se guarda: al encender vuelve a «sin cuenta atrás».

**Arreglos del original** (desde Alpha 0.04): la reproducción empieza antes (≈ 10 ms de Play al primer sonido; el original ≈ 18 ms), las notas de un mismo paso suenan juntas, no se pierden notas con muchas pistas en el mismo paso y el reloj no tropieza al guardar un sample.
""", [fig("Shift + Clear: el LED de Clear da el estado del metrónomo.", "Shift + Clear: the Clear LED shows the metronome's state.",
          buttons=["Shift", "Clear"])]), ("Transport, metronome and quantize", "in any view", """
| Gesture | What it does |
|---|---|
| **Shift + Clear** | metronome in four states; with Shift, the Clear LED: red = no metronome, green = metronome, magenta = count-in only, cyan = both *(since Alpha 0.0)* |
| **Record armed + Play** (stopped, with count-in) | one bar of clicks at the tempo, then recording starts (Record blinks); Play during the count cancels it |
| **Shift + Play** (stopped) | the original's: carry on from where it stopped; with count-in, the count and then carry on |
| **Shift + Play** (playing) | quantizes the selected track's pattern: micro steps 2-3 to the start of their step, 4-6 to the next one; rolls stay. Play LED with Shift: yellow; green after quantizing; red = nothing to quantize *(since Alpha 0.0)* |

The count-in isn't saved: at power-on it goes back to "no count-in".

**Fixes to the original** (since Alpha 0.04): playback starts sooner (≈ 10 ms from Play to the first sound; the original ≈ 18 ms), the notes of one step sound together, no notes get lost with many tracks on the same step, and the clock no longer stumbles while a sample is saved.
"""))

# ===== 2
view("pista", "2", ("El botón de pista", "las vistas de pista (Samples, Note, Velocity, Gate, Pattern Settings…)", """
| Gesto | Qué hace |
|---|---|
| **Clear + botón de la pista** | ★ sus knobs por defecto y su automatización borrada; el resto (nivel, panorama, envíos, sidechain, sample) como al cargar el proyecto *(desde Alpha 0.0)* |
| **Duplicate + pista A, luego pista B** | ★ B recibe los parámetros y el sample de A; con Duplicate mantenido, más pistas *(desde Alpha 0.0)* |
| **Mantener el botón de la pista** (¼ s) | abre el [menú de pista](#menu) en los pads *(desde Alpha 0.04)* |
| **Pads de sample mantenidos** (arpegiador encendido) | ★ arpegio de los samples mantenidos (también uno solo): cada golpe cambia el sample, con la velocity de su pad; con Record y Play se graba *(desde Alpha 0.0)* |

Pulsar el botón sin mantenerlo elige la pista, como en el original. Desde el Mixer, Clear + pista hace lo del original. El arpegiador se enciende en [Pattern Settings](#patternsettings) (Shift + pad 25).
"""), ("The track button", "the track views (Samples, Note, Velocity, Gate, Pattern Settings…)", """
| Gesture | What it does |
|---|---|
| **Clear + the track's button** | ★ its knobs to their defaults and their automation cleared; the rest (level, pan, sends, sidechain, sample) as when the project was loaded *(since Alpha 0.0)* |
| **Duplicate + track A, then track B** | ★ B gets A's parameters and sample; with Duplicate held, more tracks *(since Alpha 0.0)* |
| **Hold the track's button** (¼ s) | opens the [track menu](#menu) on the pads *(since Alpha 0.04)* |
| **Sample pads held** (arpeggiator on) | ★ arpeggio of the held samples (one also works): each hit changes the sample, with its pad's velocity; recorded with Record and Play *(since Alpha 0.0)* |

Pressing the button without holding selects the track, as in the original. From the Mixer, Clear + track does the original's. The arpeggiator is switched on in [Pattern Settings](#patternsettings) (Shift + pad 25).
"""))

MENU_FIG = dict(pads={1: ("white", "stock", "stock"), 2: ("sky", "Stock+", "Stock+", True), 3: ("lilac", "Granular", "Granular", True),
                      4: ("mint", "Sinte", "Synth", True), 9: ("steel", "enlace", "link", True), 11: ("lilac", "gran.\non/off", "gran.\non/off", True),
                      12: ("mint", "sinte\non/off", "synth\non/off", True), 13: ("amber", "entrada", "line in", True), 14: ("amber", "gate", "gate", True)})
view("menu", "2", ("El menú de pista", "toca el botón de la pista elegida (el menú se queda abierto hasta que eliges algo o lo vuelves a tocar), o mantén el botón de cualquier pista (el menú solo mientras lo mantienes)", f"""
Los pads se convierten en el menú de esa pista {A}:

| Pad | Qué hace |
|---|---|
| **1** | página **stock** de los knobs (la del original) |
| **2** | página **[Stock+](#stockplus)** (con un sample) |
| **3** | página **[Granular](#granular)** (con el granular) |
| **4** | página **[Sinte](#sinte)** (con el sinte) |
| **9** | ★ **[enlace estéreo](#entrada)** con la pista siguiente, sí / no |
| **11** | el **granular** de la pista, sí / no (hasta 4 pistas); encendido, su página |
| **12** | ★ el **sinte** de la pista, sí / no (hasta 4 pistas); encendido, su página |
| **13** | ★ la **[entrada de línea](#entrada)** como sonido de la pista, sí / no |
| **14** | el gate de la entrada: tenue = siempre suena, brillante = solo con sus notas (oscuro si la pista no es de entrada) |

- **Abrirlo:** un toque en el botón de la pista que ya está elegida lo deja abierto; se cierra al soltar un pad del menú, al tocar otra vez el botón o al pulsar cualquier otro botón. Mantener el botón de una pista (¼ s) lo abre solo mientras lo mantienes, como los botones de vista del original.
- Fila 1, las **páginas** de la pista: solo las de su sonido (sample: stock y Stock+; granular: stock y Granular; sinte: stock y Sinte; entrada: stock); las demás, oscuras. Brillante = la que se ve. **Mantener** un pad de página (½ s o más) la muestra solo hasta que lo sueltas y vuelve la anterior.
- Fila 2, debajo, los **conmutadores**: brillante = encendido, tenue = apagado. **El sonido de la pista solo cambia aquí:** sample, granular, sinte o entrada, uno por pista; poner uno quita los otros.
- Con el granular o el sinte, la página stock deja los knobs del original (filtro, envolvente, tono, nivel…) actuando sobre ellos.

En Alpha 0.04 el menú era: 1-3 páginas, 4 granular, 5 / 6 entrada y gate, 7 enlace.
""", [fig("El menú de una pista con un sample, en la página stock.", "The menu of a track with a sample, on the stock page.",
          buttons=[("Pista elegida (toque)", "Selected track (tap)")],
          pads={1: ("white", "stock", "stock"), 2: ("sky", "Stock+", "Stock+", True), 9: ("steel", "enlace", "link", True),
                11: ("lilac", "granular", "granular", True), 12: ("mint", "sinte", "synth", True), 13: ("amber", "entrada", "line in", True)}),
      fig("El menú de una pista con el sinte, en su página.", "The menu of a synth track, on its page.",
          pads={1: ("white", "stock", "stock", True), 4: ("mint", "Sinte", "Synth"), 9: ("steel", "enlace", "link", True),
                11: ("lilac", "granular", "granular", True), 12: ("mint", "sinte", "synth"), 13: ("amber", "entrada", "line in", True)})]),
     ("The track menu", "tap the selected track's button (the menu stays open until you pick something or tap again), or hold any track's button (the menu only while held)", f"""
The pads become that track's menu {A_EN}:

| Pad | What it does |
|---|---|
| **1** | the **stock** knob page (the original's) |
| **2** | the **[Stock+](#stockplus)** page (with a sample) |
| **3** | the **[Granular](#granular)** page (with the granular) |
| **4** | the **[Synth](#sinte)** page (with the synth) |
| **9** | ★ **[stereo link](#entrada)** with the next track, on / off |
| **11** | the track's **granular**, on / off (up to 4 tracks); switched on, its page |
| **12** | ★ the track's **synth**, on / off (up to 4 tracks); switched on, its page |
| **13** | ★ the **[line input](#entrada)** as the track's sound, on / off |
| **14** | the input's gate: dim = always sounds, bright = only with its notes (dark if the track isn't an input track) |

- **Opening it:** a tap on the button of the track already selected leaves it open; it closes when you let go of a menu pad, tap the button again or press any other button. Holding a track's button (¼ s) opens it only while held, like the original's view buttons.
- Row 1, the track's **pages**: only those of its sound (sample: stock and Stock+; granular: stock and Granular; synth: stock and Synth; input: stock); the others dark. Bright = the one shown. **Holding** a page pad (½ s or more) shows it only until you let go, then the previous one returns.
- Row 2, below, the **toggles**: bright = on, dim = off. **The track's sound only changes here:** sample, granular, synth or input, one per track; setting one removes the others.
- With the granular or the synth, the stock page leaves the original's knobs (filter, envelope, pitch, level…) acting on them.

In Alpha 0.04 the menu was: 1-3 pages, 4 granular, 5 / 6 input and gate, 7 link.
"""))

view("stockplus", "2", ("Página Stock+", "menú de pista, pad 2, en una pista con un sample (el botón de la pista parpadea en azul cielo)", f"""
La página Stock+ es por pista y se queda hasta apagar *(desde Alpha 0.01; K5-K8 desde Alpha 0.02)*. Actúa sobre el sample de la pista.

| Knob | Solo | Con Shift |
|---|---|---|
| K1 | ★ envolvente de tono: centro = nada; derecha = cada golpe empieza más agudo, izquierda más grave (hasta ±24 semitonos) | ajuste fino |
| K2 | ★ lo que tarda en volver a la nota (5 ms - 4 s) | ajuste fino |
| K3 | ★ velocidad del LFO de tono: centro = apagado; derecha = libre (0,05-30 Hz); izquierda = a tempo, de 8 compases junto al centro a 1/16T en el extremo {A} | ajuste fino |
| K4 | ★ profundidad del LFO de tono (0-24 semitonos) | ajuste fino |
| K5 | ★ cantidad del ring mod | ★ su frecuencia (20 Hz-5 kHz) |
| K6 | ★ pitch follow: el corte del paso bajo sigue a la nota | ★ tipo de filtro sobre los knobs de filtro del original: **stock** (blanco), **24 dB** (naranja), **comb** (lavanda) |
| K7 | ★ **stretch**: más lento (izquierda, hasta 0,25×) o más rápido (derecha, hasta 4×) sin cambiar el tono; centro = el original | ★ bitcrush |
| K8 | ★ velocidad del scan (mueve el inicio de cada nota; en un loop, el inicio del loop en cada vuelta): centro = quieto; derecha = libre (0,05-20 Hz); izquierda = a tempo, más rápido hacia el extremo {A} | ★ su profundidad |

- **LEDs:** azul cielo con el brillo según el valor (K1, K3, K7 y K8: la distancia al centro); K6 en el color de su tipo de filtro. Con Shift, K5-K8 enseñan su segunda capa.
- **Clear + knob:** su valor por defecto (en K5-K8, las dos capas).
- **Se guarda con el proyecto.** En proyectos de Alpha 0.04, la mitad a tempo de K3 y K8 va ahora al revés.
- **El stretch** reparte el sample en granos de unos 43 ms que se mantienen en fase (WSOLA): a 0,5× suena muy bien; a 0,25× la batería puede sonar con clics.
""", [fig("Página Stock+: knobs en azul cielo; K6 en el color de su tipo de filtro.", "Stock+ page: knobs in sky blue; K6 in its filter type's colour.",
          knobs={1: ("env. tono", "pitch env.", "", "sky"), 2: ("caída", "decay", "", "sky"), 3: ("LFO vel.", "LFO rate", "", "sky"),
                 4: ("LFO prof.", "LFO depth", "", "sky"), 5: ("ring", "ring", "", "sky"), 6: ("follow", "follow", "", "white"),
                 7: ("stretch", "stretch", "", "sky"), 8: ("scan", "scan", "", "sky")})]), ("Stock+ page", "track menu, pad 2, on a track with a sample (the track's button blinks sky blue)", f"""
The Stock+ page is per track and stays until power-off *(since Alpha 0.01; K5-K8 since Alpha 0.02)*. It acts on the track's sample.

| Knob | Alone | With Shift |
|---|---|---|
| K1 | ★ pitch envelope: centre = none; right = each hit starts higher, left lower (up to ±24 semitones) | fine |
| K2 | ★ how long it takes to return to the note (5 ms - 4 s) | fine |
| K3 | ★ pitch LFO rate: centre = off; right = free (0.05-30 Hz); left = synced, from 8 bars by the centre to 1/16T at the end {A_EN} | fine |
| K4 | ★ pitch LFO depth (0-24 semitones) | fine |
| K5 | ★ ring mod amount | ★ its frequency (20 Hz-5 kHz) |
| K6 | ★ pitch follow: the low-pass cutoff follows the note | ★ filter type over the original's filter knobs: **stock** (white), **24 dB** (orange), **comb** (lavender) |
| K7 | ★ **stretch**: slower (left, down to 0.25×) or faster (right, up to 4×) without changing pitch; centre = the original | ★ bitcrush |
| K8 | ★ scan rate (moves each note's start; on a loop, the loop's start on every pass): centre = still; right = free (0.05-20 Hz); left = synced, faster towards the end {A_EN} | ★ its depth |

- **LEDs:** sky blue with the value as brightness (K1, K3, K7 and K8: the distance from the centre); K6 in its filter type's colour. With Shift, K5-K8 show their second layer.
- **Clear + knob:** its default (on K5-K8, both layers).
- **Saved with the project.** In Alpha 0.04 projects, the synced half of K3 and K8 now runs the other way.
- **The stretch** splits the sample into ~43 ms grains kept in phase (WSOLA): at 0.5× it sounds very good; at 0.25× drums may click.
"""))

view("granular", "2", ("Página Granular", "menú de pista, pad 11 (pone el granular y su página) o pad 3 (su página) (el botón de la pista parpadea en lila)", f"""
El motor granular de CIRCUIT-HACKS sobre el sample de la pista, en el DSP del master *(desde Alpha 0.04)*. Sigue la nota (vista Note, teclado y MIDI). Los knobs de filtro (paso alto, paso bajo, resonancia) y la envolvente de la pista actúan sobre él. **Hasta 4 pistas granulares**, cada una con sus ajustes; los 16 granos se reparten (16 con una pista, 7 por pista con dos, 4 con tres, 2 con cuatro).

| Knob | Solo | Con Shift |
|---|---|---|
| K1 | tamaño del grano (5-500 ms) | fino |
| K2 | densidad (1-16 granos) | ★ apertura estéreo (0 = mono) |
| K3 | posición en el sample | fina |
| K4 | scan: centro = quieto; derecha hacia delante, izquierda hacia atrás | fino |
| K5 | altura (centro = la nota; ±24 semitonos) | altura fina |
| K6 | dispersión de la posición | zona (qué parte del sample) |
| K7 | dispersión de la altura | probabilidad de reverso |
| K8 | ventana (rectángulo → triángulo → percusiva) | gate, encendido / apagado: tenue = siempre suena (drone), brillante = lo abren las notas {A} |

Lila con el brillo según el valor (K4, K5 y Shift + K5: la distancia al centro). Clear + knob = por defecto. Se guarda con el proyecto.
""", [fig("Página Granular: knobs en lila.", "Granular page: knobs in lilac.",
          knobs={1: ("tamaño", "size", "", "lilac"), 2: ("densidad", "density", "", "lilac"), 3: ("posición", "position", "", "lilac"),
                 4: ("scan", "scan", "", "lilac"), 5: ("altura", "pitch", "", "lilac"), 6: ("disp. pos.", "pos. spray", "", "lilac"),
                 7: ("disp. alt.", "pitch spray", "", "lilac"), 8: ("ventana", "window", "", "lilac")})]), ("Granular page", "track menu, pad 11 (puts the granular on, with its page) or pad 3 (its page) (the track's button blinks lilac)", f"""
The CIRCUIT-HACKS granular engine on the track's sample, on the master DSP *(since Alpha 0.04)*. It follows the note (Note view, keyboard and MIDI). The track's filter knobs (high-pass, low-pass, resonance) and envelope act on it. **Up to 4 granular tracks**, each with its own settings; the 16 grains are shared (16 with one track, 7 each with two, 4 with three, 2 with four).

| Knob | Alone | With Shift |
|---|---|---|
| K1 | grain size (5-500 ms) | fine |
| K2 | density (1-16 grains) | ★ stereo spread (0 = mono) |
| K3 | position in the sample | fine |
| K4 | scan: centre = still; right forward, left backward | fine |
| K5 | pitch (centre = the note; ±24 semitones) | fine pitch |
| K6 | position spray | zone (which part of the sample) |
| K7 | pitch spray | reverse chance |
| K8 | window (rectangle → triangle → percussive) | gate, on / off: dim = always sounds (drone), bright = opened by the notes {A_EN} |

Lilac with the value as brightness (K4, K5 and Shift + K5: the distance from the centre). Clear + knob = default. Saved with the project.
"""))

view("sinte", "2", ("Página Sinte", "menú de pista, pad 12 (pone el sinte y su página) o pad 4 (su página) (el botón de la pista parpadea en menta)", f"""
★ Un sinte monofónico de dos osciladores en el DSP del master, como sonido de cualquier pista {A}. **Hasta 4 pistas con sinte.** Las notas le llegan como a un sample (pads, vista Note, secuencia, MIDI).

| Knob | Solo | Con Shift |
|---|---|---|
| K1 | forma de onda de OSC 1: sierra (rojo), pulso (amarillo), triángulo (verde), seno (blanco) | ruido |
| K2 | forma de onda de OSC 2 (los mismos colores) | sync, encendido / apagado (mitad derecha = encendido) |
| K3 | altura de OSC 2 (±24 semitonos) | glide (5 ms - 2 s) |
| K4 | afinación fina de OSC 2 (±50 cents) | octava (−3 … +3) |
| K5 | mezcla OSC 1 ↔ OSC 2 | velocity → FM |
| K6 | SUB (una octava por debajo) | release (2 ms - 4 s) |
| K7 | FM (OSC 2 modula a OSC 1) | envolvente → paso bajo (desde el centro) |
| K8 | ancho del pulso (50 % → 2 %) | — |

- **Los knobs del original** de la pista siguen actuando sobre el sinte (en la página stock): tono, envolvente (a la izquierda del centro caída, en el centro sostiene, a la derecha ataque lento), paso bajo, paso alto, resonancia, nivel, panorama, envíos, sidechain y mute.
- **Note-off:** una pista con sinte recibe el note-off aunque esté en one-shot, para que suene el release.
- **LEDs:** menta con el brillo según el valor (K3, K4, Shift + K4, Shift + K7: la distancia al centro); K1 / K2 en el color de su forma de onda.
- Clear + knob = por defecto. **Se guarda con el proyecto.**
""", [fig("Página Sinte: K1 / K2 en el color de la forma de onda, el resto en menta.", "Synth page: K1 / K2 in the waveform's colour, the rest in mint.",
          knobs={1: ("OSC 1", "OSC 1", "", "red"), 2: ("OSC 2", "OSC 2", "", "red"), 3: ("altura 2", "pitch 2", "", "mint"),
                 4: ("fino 2", "fine 2", "", "mint"), 5: ("mezcla", "mix", "", "mint"), 6: ("SUB", "SUB", "", "mint"),
                 7: ("FM", "FM", "", "mint"), 8: ("pulso", "pulse", "", "mint")})]), ("Synth page", "track menu, pad 12 (puts the synth on, with its page) or pad 4 (its page) (the track's button blinks mint)", f"""
★ A monophonic two-oscillator synth on the master DSP, as any track's sound {A_EN}. **Up to 4 synth tracks.** It gets its notes like a sample does (pads, Note view, sequence, MIDI).

| Knob | Alone | With Shift |
|---|---|---|
| K1 | OSC 1 waveform: saw (red), pulse (yellow), triangle (green), sine (white) | noise |
| K2 | OSC 2 waveform (the same colours) | sync, on / off (right half = on) |
| K3 | OSC 2 pitch (±24 semitones) | glide (5 ms - 2 s) |
| K4 | OSC 2 fine tune (±50 cents) | octave (−3 … +3) |
| K5 | mix OSC 1 ↔ OSC 2 | velocity → FM |
| K6 | SUB (an octave below) | release (2 ms - 4 s) |
| K7 | FM (OSC 2 modulates OSC 1) | envelope → low-pass (from the centre) |
| K8 | pulse width (50 % → 2 %) | — |

- **The original's knobs** of the track still act on the synth (on the stock page): pitch, envelope (left of centre decay, centre sustain, right slow attack), low-pass, high-pass, resonance, level, pan, sends, sidechain and mute.
- **Note-off:** a synth track gets the note-off even in one-shot mode, so the release sounds.
- **LEDs:** mint with the value as brightness (K3, K4, Shift + K4, Shift + K7: the distance from the centre); K1 / K2 in their waveform's colour.
- Clear + knob = default. **Saved with the project.**
"""))

view("entrada", "2", ("Entrada de línea y enlace estéreo", "menú de pista, pads 13 / 14 y 9", """
**Entrada de línea** (pad 13; desde Alpha 0.04): la entrada de audio suena como el sonido de la pista, con su nivel, panorama, envíos, filtro y envolvente.
- Una pista de entrada: L + R. Dos: la de número menor es L, la mayor R. En una tercera, sale la primera puesta.
- **Pad 14, el gate:** tenue = siempre suena; brillante = solo mientras suenan sus notas.

**Enlace estéreo** (pad 9; desde Alpha 0.04): la pista (izquierda, su sample) y la siguiente (derecha, el sample siguiente) suenan juntas con los parámetros y las notas de la primera. Pad 9 en cualquiera de las dos = deshacer. En la pista 8 sola, oscuro. Sin enlazar quedan el LFO y el scan libres de Stock+ y el WSOLA del stretch.

Las dos se guardan con el proyecto.
"""), ("Line input and stereo link", "track menu, pads 13 / 14 and 9", """
**Line input** (pad 13; since Alpha 0.04): the audio input plays as the track's sound, with its level, pan, sends, filter and envelope.
- One input track: L + R. Two: the lower-numbered one is L, the higher R. Setting a third removes the first one set.
- **Pad 14, the gate:** dim = always sounds; bright = only while its notes play.

**Stereo link** (pad 9; since Alpha 0.04): the track (left, its sample) and the next one (right, the next sample) play together with the first one's parameters and notes. Pad 9 on either = undo. Dark on track 8 alone. Not linked: Stock+'s free LFO and scan, and the stretch's WSOLA.

Both are saved with the project.
"""))

view("note", "2", ("Vista Note", "botón Note", """
| Gesto | Qué hace |
|---|---|
| **Teclas mantenidas** (arpegiador encendido) | ★ arpegio de las notas mantenidas sobre el sample de la pista; con Record y Play se graba *(desde Alpha 0.0)* |
| **Shift mantenido** | ★ editor de la **escala propia de la pista** *(desde Alpha 0.0)* |

**El editor:** los 32 pads son dos octavas de piano desde la tónica (fila 4 = las blancas de la octava de abajo, el pad 25 = la tónica; fila 3 = sus negras; filas 2 / 1 = la octava de arriba). Cada tecla enciende o apaga su grado (7 como máximo); la más alta es el **periodo**: la tónica de la siguiente iteración (la octava u otra, hasta 24 semitonos). Tónica blanca, grados verdes, periodo azul.

Al soltar Shift, el teclado toca la escala: una iteración por fila (dos si tiene 4 notas o menos); ▲ / ▼ mueven una fila. Sin teclas, vuelve el piano del original. Se guarda con el proyecto.
"""), ("Note view", "the Note button", """
| Gesture | What it does |
|---|---|
| **Keys held** (arpeggiator on) | ★ arpeggio of the held notes on the track's sample; recorded with Record and Play *(since Alpha 0.0)* |
| **Shift held** | ★ the track's **own scale** editor *(since Alpha 0.0)* |

**The editor:** the 32 pads are two piano octaves from the tonic (row 4 = the white keys of the lower octave, pad 25 = the tonic; row 3 = its black keys; rows 2 / 1 = the upper octave). Each key switches its degree on or off (7 at most); the highest is the **period**: the next iteration's tonic (the octave or another, up to 24 semitones). Tonic white, degrees green, period blue.

When you let go of Shift, the keyboard plays the scale: one iteration per row (two if it has 4 notes or fewer); ▲ / ▼ move a row. With no keys, the original piano returns. Saved with the project.
"""))

# ===== 3
view("velocity", "3", ("Velocity y Micro Step", "botón Velocity; Micro Step = Shift + Gate", f"""
| Vista | Gesto | Qué hace |
|---|---|---|
| Velocity | **Shift + paso** | marca el paso: al sonar, la automatización no suena ahí y los parámetros automatizados vuelven a la posición de su knob. Con Shift, los pasos marcados en rojo; los demás, como los dibuja la vista {A} *(desde Alpha 0.04)* |
| Micro Step | **pad 31** | longitud fija: apagada → el selector en los pads 17-32 (1-16 pasos; elegir una la enciende); encendida → apagada (naranja brillante / tenue) *(desde Alpha 0.04)* |
| Micro Step | **pad 32** | gate por pulsación: el golpe dura lo que mantienes el pad del paso; mantener un paso vacío 300 ms o más también lo crea (verde brillante / tenue) *(desde Alpha 0.04)* |

Encender uno de los dos de Micro Step apaga el otro. Con cualquiera, un golpe introducido a mano en los pasos toma esa longitud.
""", [fig("Micro Step: pad 31 longitud fija, pad 32 gate por pulsación (apagados: tenues).", "Micro Step: pad 31 fixed length, pad 32 gate by press (off: dim).",
          pads={31: ("orange", "longitud", "length", True), 32: ("green", "gate", "gate", True)}, buttons=["Shift", "Gate"])]),
     ("Velocity and Micro Step", "the Velocity button; Micro Step = Shift + Gate", f"""
| View | Gesture | What it does |
|---|---|---|
| Velocity | **Shift + step** | marks the step: when it plays, automation is silent there and automated parameters go back to their knob's position. With Shift, the marked steps in red; the others as the view draws them {A_EN} *(since Alpha 0.04)* |
| Micro Step | **pad 31** | fixed length: off → the selector on pads 17-32 (1-16 steps; picking one switches it on); on → off (orange bright / dim) *(since Alpha 0.04)* |
| Micro Step | **pad 32** | gate by press: the hit lasts as long as you hold the step's pad; holding an empty step 300 ms or more also creates it (green bright / dim) *(since Alpha 0.04)* |

Switching one of the two Micro Step options on switches the other off. With either, a hit entered by hand on the steps takes that length.
"""))

view("patternsettings", "3", ("Pattern Settings y probabilidad", "botón Pattern Settings (dos veces: la vista de probabilidad, modo 1)", """
| Gesto | Qué hace |
|---|---|
| **Pad 26** (azul) | Nudge: el patrón se reescribe para que su primer paso sea el 1 (suena igual) *(desde Alpha 0.0)* |
| **Pad 27 / 28** | órdenes **fractal** (1 · 1 2 · 1 2 3 …) y **deconstruido** (1 6 11 16 · 2 7 12 13 …); un pad de dirección vuelve al original *(desde Alpha 0.0)* |
| **Pad 25** (gris) | vista de probabilidad, modo 2: elige un paso; **fila 3 = dinámicas** (velocity y retraso dentro del paso; con Record, cada paso con dinámicas queda escrito como sonó), **fila 4 (25-28) = mutación del sample** (a veces suena el vecino) *(desde Alpha 0.0)* |
| **Pattern Settings dos veces** | vista de probabilidad, modo 1: **fila 4 = frecuencia** del paso (suena una de cada n pasadas) *(desde Alpha 0.0)* |
| **Clear + pad 25** | borra las dinámicas y la mutación del patrón (la frecuencia se queda) *(desde Alpha 0.04)* |
| **Shift + pad 25** | ★ arpegiador de la pista encendido / apagado (verde brillante / tenue) *(desde Alpha 0.0)* |
| **Shift + pads 27-32** | orden del arpegio: fractal, deconstruido, arriba, abajo, ping-pong, aleatorio |
| **Shift + pads 17-24** | resolución del arpegio (1/4 … 1/32T); otra vez la misma = el sync rate de la pista |

Las filas del arpegiador con Shift: la opción elegida verde brillante, las demás verde tenue (desde Alpha 0.05). Los valores por paso viajan con el golpe al cuantizar, al hacer Nudge, al copiar un paso y con el Mutate del original.
""", [fig("Pattern Settings con Shift: el arpegiador.", "Pattern Settings with Shift: the arpeggiator.",
          pads={**{17 + i: ("green", ("1/4" if i == 0 else ""), ("1/4" if i == 0 else ""), i != 2) for i in range(8)},
                25: ("green", "arp", "arp"), **{27 + i: ("green", n, n, i != 2) for i, n in enumerate(["fract.", "decon.", "↑", "↓", "↕", "?"])}},
          buttons=["Shift"])]), ("Pattern Settings and probability", "the Pattern Settings button (twice: the probability view, mode 1)", """
| Gesture | What it does |
|---|---|
| **Pad 26** (blue) | Nudge: the pattern is rewritten so its first step is 1 (it sounds the same) *(since Alpha 0.0)* |
| **Pad 27 / 28** | **fractal** (1 · 1 2 · 1 2 3 …) and **deconstructed** (1 6 11 16 · 2 7 12 13 …) orders; a direction pad goes back to the original *(since Alpha 0.0)* |
| **Pad 25** (grey) | probability view, mode 2: pick a step; **row 3 = dynamics** (velocity and delay within the step; with Record, each step with dynamics is written as it played), **row 4 (25-28) = sample mutation** (sometimes its neighbour plays) *(since Alpha 0.0)* |
| **Pattern Settings twice** | probability view, mode 1: **row 4 = frequency** of the step (it plays one pass in n) *(since Alpha 0.0)* |
| **Clear + pad 25** | clears the pattern's dynamics and mutation (frequency stays) *(since Alpha 0.04)* |
| **Shift + pad 25** | ★ the track's arpeggiator on / off (green bright / dim) *(since Alpha 0.0)* |
| **Shift + pads 27-32** | arpeggio order: fractal, deconstructed, up, down, ping-pong, random |
| **Shift + pads 17-24** | arpeggio resolution (1/4 … 1/32T); the same one again = the track's sync rate |

The arpeggiator's rows with Shift: the chosen option bright green, the others dim green (since Alpha 0.05). Per-step values travel with the hit when quantizing, nudging, copying a step and with the original's Mutate.
"""))

view("patterns", "3", ("Patterns: cadenas", "botón Patterns", """
| Gesto | Qué hace |
|---|---|
| **Shift + botón de página de arriba** | modo cadena (verde) *(desde Alpha 0.0)* |
| En el modo: **un patrón** (A), **otra vez** (n + 1 pasadas), **otro** (B), **otro más** (C) | regla «n veces A, luego B; la vez siguiente, C» (AAB AAC …) |
| **Clear + patrón** | sin regla |
| **Shift + botón de página de abajo** | fuera del modo: la cadena del original |

Cada escena recuerda el modo con que se guardó. Las reglas se guardan con el proyecto.
"""), ("Patterns: chains", "the Patterns button", """
| Gesture | What it does |
|---|---|
| **Shift + the upper page button** | chain mode (green) *(since Alpha 0.0)* |
| In the mode: **a pattern** (A), **again** (n + 1 passes), **another** (B), **one more** (C) | rule "n times A, then B; the next time, C" (AAB AAC …) |
| **Clear + pattern** | no rule |
| **Shift + the lower page button** | out of the mode: the original's chain |

Each scene remembers the mode it was saved with. The rules are saved with the project.
"""))

# ===== 4
view("samplemode", "4", ("Sample mode", "botón Samples dos veces", """
| Gesto | Qué hace |
|---|---|
| **Pads 1 / 2** (del original) | ajustan el sample al patrón cambiando el tono; desde Alpha 0.04 apagan antes el stretch |
| **Pads 9 / 10** | ★ lo mismo con el **stretch** (K7 de Stock+), sin cambiar el tono: la longitud siguiente / la anterior *(desde Alpha 0.04)* |
| **Pad 19** | ★ de-clicker del loop de la pista elegida (crossfade de 256 muestras), encendido / apagado (azul brillante / tenue); encendido por defecto, se guarda con el proyecto *(desde Alpha 0.04)* |

El pad 19 está sobre el 27 (loop). Los loops muy cortos suenan a su longitud (en el original se repetían cada ~128 muestras).
""", [fig("Sample mode: pads 9 / 10 bajo los 1 / 2; pad 19 sobre el loop.", "Sample mode: pads 9 / 10 under 1 / 2; pad 19 above loop.",
          pads={1: ("cyan", "tono +", "pitch +"), 2: ("cyan", "tono −", "pitch −"), 9: ("cyan", "stretch +", "stretch +"),
                10: ("cyan", "stretch −", "stretch −"), 19: ("cyan", "de-click", "de-click"), 27: ("cyan", "loop", "loop", True)})]),
     ("Sample mode", "the Samples button twice", """
| Gesture | What it does |
|---|---|
| **Pads 1 / 2** (the original's) | fit the sample to the pattern by changing pitch; since Alpha 0.04 they switch the stretch off first |
| **Pads 9 / 10** | ★ the same with the **stretch** (Stock+ K7), without changing pitch: the next / previous length *(since Alpha 0.04)* |
| **Pad 19** | ★ the selected track's loop de-clicker (256-sample crossfade), on / off (blue bright / dim); on by default, saved with the project *(since Alpha 0.04)* |

Pad 19 sits above pad 27 (loop). Very short loops play at their own length (the original repeated them every ~128 samples).
"""))

view("samplerec", "4", ("Sample Rec", "botón Sample Rec", """
| Gesto | Qué hace |
|---|---|
| **Pad 23** | ★ de-clicker de los loops de todas las pistas, encendido / apagado (encendido al arrancar) *(desde Alpha 0.04)* |
| **Pad 24** | ★ **grabación estéreo**: L en el hueco elegido, R en el siguiente (que debe estar vacío; si no, solo el primero, en mono); apagada al arrancar *(desde Alpha 0.04)* |
| **Duplicate + hueco A, Duplicate + hueco B** | ★ copia el sample A en B, también desde otro pack (no en las versiones S) *(desde Alpha 0.01)* |
| **Fixed Recording** (pads 17-21, del original) | con reloj MIDI externo, usa el tempo del reloj que llega *(desde Alpha 0.02)* |

**Copiar un sample** (transporte parado): Duplicate + hueco con sample (parpadea en amarillo); Duplicate + hueco B (de este pack o, tras cargar otro, de ese): verde ~1,5 s y B suena al momento. Si B tiene sample, parpadea en blanco y Duplicate + B otra vez antes de ~5 s lo sobrescribe. Rojo = no se ha podido (memoria llena, aparato ocupado o pack interno).
"""), ("Sample Rec", "the Sample Rec button", """
| Gesture | What it does |
|---|---|
| **Pad 23** | ★ every track's loop de-clicker, on / off (on at power-up) *(since Alpha 0.04)* |
| **Pad 24** | ★ **stereo recording**: L into the chosen slot, R into the next one (which must be empty; otherwise only the first, in mono); off at power-up *(since Alpha 0.04)* |
| **Duplicate + slot A, Duplicate + slot B** | ★ copies sample A into B, also from another pack (not in the S versions) *(since Alpha 0.01)* |
| **Fixed Recording** (pads 17-21, the original's) | with an external MIDI clock, it uses the incoming clock's tempo *(since Alpha 0.02)* |

**Copying a sample** (transport stopped): Duplicate + a slot with a sample (blinks yellow); Duplicate + slot B (in this pack or, after loading another, in that one): green ~1.5 s and B plays at once. If B has a sample, it blinks white and Duplicate + B again within ~5 s overwrites it. Red = it couldn't (memory full, device busy or the internal pack).
"""))

# ===== 5
view("mixer", "5", ("Mixer", "botón Mixer", f"""
| Gesto | Qué hace |
|---|---|
| **Shift + pad de pista** (fila 1) | mute de esa pista en el compás siguiente (el pad parpadea; otra vez = cancelar; parado, al momento) *(desde Alpha 0.0)* |
| **Shift + knob** (página de niveles) | derecha = nivel 100; izquierda = 0 (grabando, queda como automatización) *(desde Alpha 0.0)* |
| **Shift + pads 9-16** | la escena actual se repite 1-8 veces; sonando, con Shift, la vuelta que suena en blanco *(desde Alpha 0.0)* |
| **Página de panoramas, Shift + knob** a la derecha / izquierda | ★ **modo cue** sí / no (botón 19 en rosa): la mezcla por la salida izquierda, el cue por la derecha *(desde Alpha 0.04)* |
| **Modo cue, knob** | el envío al cue de su pista (knobs en rosa, brillo = envío); una pista silenciada con envío suena solo en el cue; Clear + knob = 0 |

El pad 9 sin Shift sigue siendo el Mute Recall del original. El modo cue no se guarda.
"""), ("Mixer", "the Mixer button", f"""
| Gesture | What it does |
|---|---|
| **Shift + track pad** (row 1) | mutes that track at the next bar (the pad blinks; again = cancel; stopped, at once) *(since Alpha 0.0)* |
| **Shift + knob** (levels page) | right = level 100; left = 0 (while recording, it stays as automation) *(since Alpha 0.0)* |
| **Shift + pads 9-16** | the current scene repeats 1-8 times; playing, with Shift, the pass now playing in white *(since Alpha 0.0)* |
| **Pan page, Shift + knob** right / left | ★ **cue mode** on / off (button 19 pink): the mix on the left output, the cue on the right *(since Alpha 0.04)* |
| **Cue mode, knob** | its track's cue send (knobs pink, brightness = send); a muted track with a send plays only in the cue; Clear + knob = 0 |

Pad 9 without Shift is still the original's Mute Recall. Cue mode isn't saved.
"""))

view("fx", "5", ("FX y Sidechain", "botón FX; Sidechain = Shift + FX", """
| Vista | Gesto | Qué hace |
|---|---|---|
| FX | **▼ / ▲** | los knobs pasan a los envíos de **reverb** (▼, crema) / **delay** (▲, melocotón) de las 8 pistas *(desde Alpha 0.0)* |
| FX | **Shift + knob** | delay: K1 time, K2 sync, K3 feedback, K4 width, K5 ratio, K6 slew; reverb: K1 tipo, K2 decay, K3 damping |
| FX | **Shift + ▲ / ▼** | resonancia del filtro master ±16 (global, del aparato) |
| FX | **Duplicate** | reset: envíos a 0, filtro master al centro |
| FX | **Clear + knob** | el envío de esa pista a 0 |
| Sidechain | **K1-K4** | ataque, hold, decay y profundidad del sidechain de la pista elegida *(desde Alpha 0.0)* |
| Sidechain | **K5** | umbral del compresor master (a tope = el del original) *(desde Alpha 0.01)* |
| Sidechain | **K6 / K7 / K8** | soft clip / ataque / release del compresor master |
| Sidechain | **Clear + knob** | K1-K4: el valor de su preset; K6-K8: el de fábrica; K5: el umbral del original |

Con Shift, el brillo de cada knob muestra su valor. Reverb, delay y sidechain se guardan con el proyecto; la resonancia y el compresor son del aparato. El compresor solo se oye si está encendido (Advanced Setup).
"""), ("FX and Sidechain", "the FX button; Sidechain = Shift + FX", """
| View | Gesture | What it does |
|---|---|---|
| FX | **▼ / ▲** | the knobs become the 8 tracks' **reverb** (▼, cream) / **delay** (▲, peach) sends *(since Alpha 0.0)* |
| FX | **Shift + knob** | delay: K1 time, K2 sync, K3 feedback, K4 width, K5 ratio, K6 slew; reverb: K1 type, K2 decay, K3 damping |
| FX | **Shift + ▲ / ▼** | master filter resonance ±16 (global, the device's) |
| FX | **Duplicate** | reset: sends to 0, master filter to the centre |
| FX | **Clear + knob** | that track's send to 0 |
| Sidechain | **K1-K4** | the selected track's sidechain attack, hold, decay and depth *(since Alpha 0.0)* |
| Sidechain | **K5** | master compressor threshold (fully up = the original's) *(since Alpha 0.01)* |
| Sidechain | **K6 / K7 / K8** | master compressor soft clip / attack / release |
| Sidechain | **Clear + knob** | K1-K4: its preset's value; K6-K8: the factory one; K5: the original threshold |

With Shift, each knob's brightness shows its value. Reverb, delay and sidechain are saved with the project; resonance and the compressor belong to the device. The compressor is only heard when switched on (Advanced Setup).
"""))

# ===== 6
view("projects", "6", ("Projects y Packs", "botón Projects (dos veces: Packs)", """
**Copiar un proyecto** (no en las versiones S; desde Alpha 0.0), con el transporte parado:
1. **Duplicate + pad con proyecto (A)**: parpadea en amarillo.
2. **Duplicate + pad vacío (B)**: copia A en B (verde ~1,5 s). B puede estar en otro pack: elige A, carga otro pack y Duplicate + un pad vacío.
3. **Duplicate + un pad con proyecto**: parpadea en blanco (pregunta); **Duplicate + el mismo pad** antes de ~5 s lo sobrescribe.

Copia el proyecto **tal como está guardado** y no toca el cargado. (Save + pad, del original, guarda el cargado con sus cambios.)

**Borrar un pack** (vista Packs; no en las versiones S; desde Alpha 0.01): **Clear + pad del pack** = pregunta (parpadea en rojo ~5 s); **Clear + el mismo pad** = lo borra de la tarjeta (verde ~1,5 s). Nunca el cargado, el interno ni un hueco vacío.

El mod nunca escribe en el pack de la memoria interna (rojo + LED de Save rojo).
"""), ("Projects and Packs", "the Projects button (twice: Packs)", """
**Copying a project** (not in the S versions; since Alpha 0.0), transport stopped:
1. **Duplicate + a pad with a project (A)**: blinks yellow.
2. **Duplicate + an empty pad (B)**: copies A into B (green ~1.5 s). B can be in another pack: pick A, load another pack and Duplicate + an empty pad.
3. **Duplicate + a pad with a project**: blinks white (asking); **Duplicate + the same pad** within ~5 s overwrites it.

It copies the project **as saved** and never touches the loaded one. (Save + pad, the original's, saves the loaded one with its changes.)

**Deleting a pack** (Packs view; not in the S versions; since Alpha 0.01): **Clear + the pack's pad** = asks (blinks red ~5 s); **Clear + the same pad** = deletes it from the card (green ~1.5 s). Never the loaded one, the internal one or an empty slot.

The mod never writes to the internal memory's pack (red + Save LED red).
"""))

view("setup", "6", ("Setup y Advanced Setup", "Shift + Save (Setup); Advanced Setup como en el original", f"""
| Vista | Gesto | Qué hace |
|---|---|---|
| Advanced | **Duplicate** | la toma Thru: **Thru** (verde) → **Out 2** (rojo tenue) → **Merge** (amarillo: MIDI In + el MIDI del aparato) → **Filter** (azul: MIDI In menos los canales del aparato) *(desde Alpha 0.0)* |
| Setup | **Pad 29 / 30** (la primera vez) | canal de escucha / de salida de **Program Change** en los pads 1-16; el pad otra vez = PGM Rx / Tx sí / no *(desde Alpha 0.0)* |
| Setup | **Pad 22** | ★ **modo General MIDI** del proyecto (verde brillante / tenue): las pistas salen por el canal 10 con su nota GM; las notas GM del canal 10 tocan su pista *(desde Alpha 0.04)* |
| Setup | **K1-K8**, con el modo GM | la nota GM de cada pista (35-81, dos clics por nota; cada nota nueva suena una vez). De fábrica: 36, 38, 42, 46, 39, 37, 45, 49 |
| Advanced | **Pad 22** | ★ teclado externo al arpegiador: las notas que entran por el canal de una pista con el arpegiador encendido se arpegian (verde brillante / tenue) *(desde Alpha 0.04)* |
| Advanced | **Pad 23** | ★ fusión USB: lo que entra por el DIN In sale también por USB (verde brillante / tenue) *(desde Alpha 0.04)* |

Todo se guarda en los ajustes del aparato, salvo el modo GM, que va con el proyecto. Si los dos canales de Program Change son distintos, el recibido se reenvía por el de salida.
"""), ("Setup and Advanced Setup", "Shift + Save (Setup); Advanced Setup as in the original", f"""
| View | Gesture | What it does |
|---|---|---|
| Advanced | **Duplicate** | the Thru socket: **Thru** (green) → **Out 2** (dim red) → **Merge** (yellow: MIDI In + the device's MIDI) → **Filter** (blue: MIDI In minus the device's channels) *(since Alpha 0.0)* |
| Setup | **Pad 29 / 30** (the first time) | **Program Change** listen / send channel on pads 1-16; the pad again = PGM Rx / Tx on / off *(since Alpha 0.0)* |
| Setup | **Pad 22** | ★ the project's **General MIDI mode** (green bright / dim): the tracks play out on channel 10 with their GM note; GM notes on channel 10 play their track *(since Alpha 0.04)* |
| Setup | **K1-K8**, with GM mode | each track's GM note (35-81, two clicks a note; each new note plays once). Factory: 36, 38, 42, 46, 39, 37, 45, 49 |
| Advanced | **Pad 22** | ★ external keyboard into the arpeggiator: notes coming in on the channel of a track with its arpeggiator on are arpeggiated (green bright / dim) *(since Alpha 0.04)* |
| Advanced | **Pad 23** | ★ USB merge: what comes in on DIN In also goes out over USB (green bright / dim) *(since Alpha 0.04)* |

Everything is saved in the device's settings, except GM mode, which goes with the project. If the two Program Change channels differ, the received one is forwarded on the send channel.
"""))

# ===== A
view("guardado", "A", ("Qué se guarda y dónde", "—", """
| Dónde | Qué |
|---|---|
| **Con el proyecto** | Stock+, Granular, Sinte (ajustes y pistas), entrada de línea, enlace estéreo, de-clicker por pista, escala propia, reglas de cadena, dinámicas / mutación / frecuencia por paso, marcas de Velocity, Micro Step, modo GM, reverb / delay / sidechain |
| **Ajustes del aparato** | canales de Program Change, modo del Thru, teclado al arpegiador, fusión USB, resonancia del filtro master, compresor |
| **Hasta apagar** | la página de knobs de cada pista, el modo cue, el metrónomo / cuenta atrás, Sample Rec pads 23 / 24 |

Lo propio del mod va en una zona del fichero de proyecto que el original no usa. Un proyecto de una versión anterior carga sin lo que esa versión no tenía. **Guarda copias de tus proyectos.**
"""), ("What is saved and where", "—", """
| Where | What |
|---|---|
| **With the project** | Stock+, Granular, Synth (settings and tracks), line input, stereo link, per-track de-clicker, own scale, chain rules, per-step dynamics / mutation / frequency, Velocity marks, Micro Step, GM mode, reverb / delay / sidechain |
| **Device settings** | Program Change channels, Thru mode, keyboard into the arpeggiator, USB merge, master filter resonance, compressor |
| **Until power-off** | each track's knob page, cue mode, metronome / count-in, Sample Rec pads 23 / 24 |

The mod's own data goes in a part of the project file the original doesn't use. A project from an earlier version loads without what that version lacked. **Keep copies of your projects.**
"""))

view("midi", "A", ("MIDI", "—", """
Los knobs nuevos mueven parámetros del original con su MIDI de siempre (guía del programador del Circuit Rhythm): sidechain NRPN 1:1-1:4 (canal de la pista); reverb NRPN 1:18-1:20; delay NRPN 1:6-1:11; resonancia master CC 71; compresor NRPN 1:22-1:26. Las páginas Stock+, Granular y Sinte aún no tienen MIDI.
"""), ("MIDI", "—", """
The new knobs move the original's parameters with their usual MIDI (Circuit Rhythm programmer's guide): sidechain NRPN 1:1-1:4 (the track's channel); reverb NRPN 1:18-1:20; delay NRPN 1:6-1:11; master resonance CC 71; compressor NRPN 1:22-1:26. The Stock+, Granular and Synth pages have no MIDI yet.
"""))

# ---------------------------------------------------------------------------------------------------- the glossary: one entry per function
# (name es, name en, what es, what en, chapter, since)
GLOSSARY = [
    ("Arpegiador de notas", "Note arpeggiator", "arpegia las teclas mantenidas en la vista Note", "arpeggiates the keys held in the Note view", "note", "0.0"),
    ("Arpegiador de samples", "Sample arpeggiator", "arpegia los pads de sample mantenidos; Shift + pad 25 de Pattern Settings lo enciende", "arpeggiates the held sample pads; Shift + Pattern Settings pad 25 switches it on", "pista", "0.0"),
    ("Bitcrush", "Bitcrush", "Stock+, Shift + K7", "Stock+, Shift + K7", "stockplus", "0.02"),
    ("Cadenas con reglas", "Rule chains", "patrones que se encadenan «n veces A, luego B»", "patterns chained \"n times A, then B\"", "patterns", "0.0"),
    ("Copiar parámetros de pista", "Copy track parameters", "Duplicate + pista A, pista B", "Duplicate + track A, track B", "pista", "0.0"),
    ("Copiar proyectos", "Copy projects", "Duplicate + A, Duplicate + B en Projects, también a otro pack", "Duplicate + A, Duplicate + B in Projects, also to another pack", "projects", "0.0"),
    ("Copiar samples", "Copy samples", "Duplicate + A, Duplicate + B en Sample Rec", "Duplicate + A, Duplicate + B in Sample Rec", "samplerec", "0.01"),
    ("Borrar un pack", "Delete a pack", "Clear + pack dos veces en Packs", "Clear + pack twice in Packs", "projects", "0.01"),
    ("Compresor master", "Master compressor", "umbral, soft clip, ataque y release en la vista Sidechain", "threshold, soft clip, attack and release in the Sidechain view", "fx", "0.0"),
    ("Cuantizar", "Quantize", "Shift + Play sonando", "Shift + Play while playing", "transporte", "0.0"),
    ("Cuenta atrás", "Count-in", "un compás antes de grabar; Shift + Clear", "a bar before recording; Shift + Clear", "transporte", "0.0"),
    ("De-clicker de loops", "Loop de-clicker", "crossfade en el punto de loop; pad 19 de Sample mode, pad 23 de Sample Rec", "a crossfade at the loop point; Sample mode pad 19, Sample Rec pad 23", "samplemode", "0.04"),
    ("Dinámicas por paso", "Per-step dynamics", "velocity y retraso al azar dentro del paso; fila 3 de la probabilidad", "random velocity and delay within the step; probability row 3", "patternsettings", "0.0"),
    ("Enlace estéreo", "Stereo link", "una pista y la siguiente como un sonido estéreo; menú, pad 9", "a track and the next as one stereo sound; menu, pad 9", "entrada", "0.04"),
    ("Entrada de línea", "Line input", "la entrada de audio como sonido de una pista; menú, pads 13 / 14", "the audio input as a track's sound; menu, pads 13 / 14", "entrada", "0.04"),
    ("Envolvente de tono", "Pitch envelope", "Stock+, K1 / K2", "Stock+, K1 / K2", "stockplus", "0.01"),
    ("Escala propia", "Own scale", "una escala por pista; Shift en la vista Note", "a scale per track; Shift in the Note view", "note", "0.0"),
    ("Fixed Recording con reloj externo", "Fixed Recording with external clock", "la duración al tempo del reloj MIDI que llega", "the length at the incoming MIDI clock's tempo", "samplerec", "0.02"),
    ("Frecuencia por paso", "Per-step frequency", "el paso suena una de cada n pasadas", "the step plays one pass in n", "patternsettings", "0.0"),
    ("Fusión USB", "USB merge", "el DIN In también por USB; Advanced Setup, pad 23", "DIN In also over USB; Advanced Setup, pad 23", "setup", "0.04"),
    ("Gate por pulsación", "Gate by press", "el golpe dura lo que mantienes el pad; Micro Step, pad 32", "the hit lasts as long as the pad is held; Micro Step, pad 32", "velocity", "0.04"),
    ("General MIDI", "General MIDI", "las pistas por el canal 10 con su nota GM; Setup, pad 22", "the tracks on channel 10 with their GM note; Setup, pad 22", "setup", "0.04"),
    ("Grabación estéreo", "Stereo recording", "L y R en dos huecos; Sample Rec, pad 24", "L and R into two slots; Sample Rec, pad 24", "samplerec", "0.04"),
    ("Granular", "Granular", "el motor granular en hasta 4 pistas; menú, pads 11 / 3", "the granular engine on up to 4 tracks; menu, pads 11 / 3", "granular", "0.04"),
    ("Longitud fija", "Fixed length", "los golpes a mano con una longitud; Micro Step, pad 31", "hand-entered hits with a set length; Micro Step, pad 31", "velocity", "0.04"),
    ("LFO de tono", "Pitch LFO", "Stock+, K3 / K4; libre o a tempo", "Stock+, K3 / K4; free or synced", "stockplus", "0.01"),
    ("Marcas de Velocity", "Velocity marks", "en el paso marcado la automatización vuelve al knob; Shift + paso", "on a marked step automation returns to the knob; Shift + step", "velocity", "0.04"),
    ("Menú de pista", "Track menu", "tocar el botón de la pista elegida (se queda abierto) o mantener el de una pista", "tap the selected track's button (stays open) or hold a track's button", "menu", "0.04"),
    ("Metrónomo", "Metronome", "cuatro estados con Shift + Clear", "four states with Shift + Clear", "transporte", "0.0"),
    ("Modo cue", "Cue mode", "mezcla a la izquierda, cue a la derecha; Mixer, panoramas, Shift + knob", "mix on the left, cue on the right; Mixer, pan, Shift + knob", "mixer", "0.04"),
    ("Mute al compás", "Mute at the bar", "Shift + pad de pista en el Mixer", "Shift + track pad in the Mixer", "mixer", "0.0"),
    ("Mutación del sample", "Sample mutation", "a veces suena el vecino; fila 4 de la probabilidad", "sometimes the neighbour plays; probability row 4", "patternsettings", "0.0"),
    ("Nivel a 100 / 0", "Level to 100 / 0", "Shift + knob en los niveles del Mixer", "Shift + knob on the Mixer's levels", "mixer", "0.0"),
    ("Nudge", "Nudge", "el primer paso pasa a ser el 1; pad 26 de Pattern Settings", "the first step becomes step 1; Pattern Settings pad 26", "patternsettings", "0.0"),
    ("Órdenes fractal / deconstruido", "Fractal / deconstructed orders", "pads 27 / 28 de Pattern Settings", "Pattern Settings pads 27 / 28", "patternsettings", "0.0"),
    ("Página Stock+", "Stock+ page", "ocho knobs más por pista; menú, pad 2", "eight more knobs per track; menu, pad 2", "stockplus", "0.01"),
    ("Program Change", "Program Change", "canales de escucha y salida; Setup, pads 29 / 30", "listen and send channels; Setup, pads 29 / 30", "setup", "0.0"),
    ("Repetir la escena", "Repeat the scene", "la escena actual 1-8 veces; Mixer, Shift + pads 9-16", "the current scene 1-8 times; Mixer, Shift + pads 9-16", "mixer", "0.0"),
    ("Reset de knobs de pista", "Track knobs reset", "Clear + botón de la pista", "Clear + the track's button", "pista", "0.0"),
    ("Resonancia master", "Master resonance", "Shift + ▲ / ▼ en la vista FX", "Shift + ▲ / ▼ in the FX view", "fx", "0.0"),
    ("Ring mod", "Ring mod", "Stock+, K5 (Shift: la frecuencia)", "Stock+, K5 (Shift: the frequency)", "stockplus", "0.02"),
    ("Scan", "Scan", "mueve el inicio de cada nota o del loop; Stock+, K8", "moves each note's or the loop's start; Stock+, K8", "stockplus", "0.02"),
    ("Sidechain por knobs", "Sidechain on the knobs", "K1-K4 de la vista Sidechain", "Sidechain view K1-K4", "fx", "0.0"),
    ("Sinte", "Synth", "dos osciladores con FM en hasta 4 pistas; menú, pads 12 / 4", "two oscillators with FM on up to 4 tracks; menu, pads 12 / 4", "sinte", "0.05"),
    ("Stretch", "Stretch", "más lento o rápido sin cambiar el tono; Stock+ K7, Sample mode pads 9 / 10", "slower or faster without changing pitch; Stock+ K7, Sample mode pads 9 / 10", "stockplus", "0.02"),
    ("Teclado externo al arpegiador", "External keyboard into the arpeggiator", "Advanced Setup, pad 22", "Advanced Setup, pad 22", "setup", "0.04"),
    ("Thru: Out 2 / Merge / Filter", "Thru: Out 2 / Merge / Filter", "Duplicate en Advanced Setup", "Duplicate in Advanced Setup", "setup", "0.0"),
    ("Tipo de filtro (24 dB, comb)", "Filter type (24 dB, comb)", "Stock+, Shift + K6", "Stock+, Shift + K6", "stockplus", "0.02"),
    ("Umbral del compresor", "Compressor threshold", "K5 de la vista Sidechain", "Sidechain view K5", "fx", "0.01"),
    ("Envíos de FX en los knobs", "FX sends on the knobs", "▼ / ▲ en la vista FX", "▼ / ▲ in the FX view", "fx", "0.0"),
]

UI = dict(es=dict(title=f"Circuit Remix {VERSION} — manual", how="Cómo se llega:", toc="Índice", glossary="Glosario de funciones",
                  gl_cols=("Función", "Qué es / gesto", "Capítulo", "Desde"), other='[English](MANUAL_EN.md) · [versión ilustrada](manual/index.html)',
                  other_html='<p class="lang"><a href="en.html">English</a> · <a href="../MANUAL.md">texto</a></p>',
                  cover="Manual por vistas", warn="> ⚠️ **Alpha 0.05 es experimental:** lo nuevo (el sinte y la interfaz de Alpha 0.05, y casi todo lo de Alpha 0.04) se ha comprobado sobre todo en emulación. Para tocar en serio, Alpha 0.03. **Haz una copia de tu tarjeta SD.**",
                  intro="Circuit Remix en el Circuit Rhythm (firmware 2.0.1, build 5706), vista por vista.", md="MANUAL.md", html="index.html", lang="es",
                  footer="Circuit Remix — MIT. Sin código de Novation."),
          en=dict(title=f"Circuit Remix {VERSION} — manual", how="How to get there:", toc="Contents", glossary="Glossary of functions",
                  gl_cols=("Function", "What it is / gesture", "Chapter", "Since"), other='[Español](MANUAL.md) · [illustrated version](manual/en.html)',
                  other_html='<p class="lang"><a href="index.html">Español</a> · <a href="../MANUAL_EN.md">text</a></p>',
                  cover="Manual by views", warn="> ⚠️ **Alpha 0.05 is experimental:** what's new (the synth and Alpha 0.05's interface, and most of Alpha 0.04) has mostly been checked in emulation. For serious playing, Alpha 0.03. **Back up your SD card.**",
                  intro="Circuit Remix on the Circuit Rhythm (firmware 2.0.1, build 5706), view by view.", md="MANUAL_EN.md", html="en.html", lang="en",
                  footer="Circuit Remix — MIT. No Novation code."))


def numbered(lang):
    out = []
    for p, *_ in PARTS:
        n = 0
        for v in V:
            if v["part"] == p:
                n += 1
                out.append((f"{p}.{n}", v))
    return out


def part_name(p, lang): return next(x for x in PARTS if x[0] == p)[1 if lang == "es" else 2]


def texts(v, lang):
    t = v[lang]
    return t[0], t[1], t[2].strip("\n").replace("{A}", A if lang == "es" else A_EN)


def glossary_md(lang, link):
    """link(chapter id) -> its href"""
    U = UI[lang]
    rows = ["| " + " | ".join(U["gl_cols"]) + " |", "|---|---|---|---|"]
    num = {v["id"]: (code, v) for code, v in numbered(lang)}
    key = 0 if lang == "es" else 1
    for g in sorted(GLOSSARY, key=lambda g_: g_[key].lower().replace("ó", "o").replace("á", "a").replace("é", "e")):
        code, v = num[g[4]]
        rows.append(f"| **{g[key]}** | {g[2 + key]} | [{code} {texts(v, lang)[0]}]({link(g[4])}) | Alpha {g[5]} |")
    return "\n".join(rows)


# ---------------------------------------------------------------------------------------------------- output
def inline(t):
    t = html.escape(t)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return t


def md2html(text):
    out, lines, i = [], text.split("\n"), 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("### "):
            out.append(f"<h4>{inline(ln[4:])}</h4>"); i += 1
        elif ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in rows[0]) + "</tr></thead><tbody>")
            for r in rows[2:]:
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            out.append("</tbody></table>")
        elif ln.startswith("- "):
            out.append("<ul>")
            while i < len(lines) and lines[i].startswith("- "):
                out.append(f"<li>{inline(lines[i][2:])}</li>"); i += 1
            out.append("</ul>")
        elif re.match(r"\d+\. ", ln):
            out.append("<ol>")
            while i < len(lines) and re.match(r"\d+\. ", lines[i]):
                out.append(f"<li>{inline(re.sub(r'^[0-9]+[.] ', '', lines[i]))}</li>"); i += 1
            out.append("</ol>")
        elif ln.startswith("> "):
            out.append(f'<p class="warn">{inline(ln[2:])}</p>'); i += 1
        elif ln.strip() == "":
            i += 1
        else:
            out.append(f"<p>{inline(ln)}</p>"); i += 1
    return "\n".join(out)


CSS = """
:root { --bg:#f6f4ef; --fg:#1d1d1f; --muted:#5b5f66; --card:#ffffff; --accent:#ff6a13; --line:#e1ddd3; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#121315; --fg:#ececec; --muted:#a3a8ae; --card:#1c1d20; --line:#2c2e33; } }
:root[data-theme="dark"] { --bg:#121315; --fg:#ececec; --muted:#a3a8ae; --card:#1c1d20; --line:#2c2e33; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:16px/1.55 "Helvetica Neue", Arial, sans-serif; overflow-x:hidden; }
header.cover { background:#17181b; color:#fff; padding:56px 24px 40px; text-align:center; }
header.cover h1 { font-size:40px; margin:0 0 8px; letter-spacing:.5px; } header.cover p { color:#c9cdd2; margin:4px 0; }
header.cover .bar { height:6px; width:180px; margin:18px auto 0; background:linear-gradient(90deg,#ffffff,#14a5fe,#ffa2ff,#8affd0,#ffaf2f,#5e84cc); border-radius:3px; }
main { max-width:980px; margin:0 auto; padding:24px 16px 64px; }
nav.toc { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px 22px; }
nav.toc h2 { margin-top:0; } nav.toc ol { padding-left:20px; } nav.toc a { color:var(--fg); }
h2.group { margin-top:48px; padding-bottom:6px; border-bottom:3px solid var(--accent); }
section.feat { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:20px 24px; margin:22px 0; }
section.feat h3 { margin-top:0; } section.feat .code { color:var(--accent); font-weight:bold; margin-right:6px; }
.summary { color:var(--muted); border-left:4px solid var(--accent); padding-left:12px; }
figure { margin:16px 0; } figure svg { width:100%; max-width:600px; height:auto; border-radius:14px; display:block; margin:0 auto; }
figcaption { color:var(--muted); font-size:14px; margin-top:6px; text-align:center; }
table { border-collapse:collapse; width:100%; margin:12px 0; font-size:14.5px; display:block; overflow-x:auto; }
th, td { border:1px solid var(--line); padding:6px 8px; text-align:left; vertical-align:top; }
th { background:rgba(255,106,19,.10); } code { background:rgba(127,127,127,.15); padding:1px 4px; border-radius:4px; }
footer { color:var(--muted); text-align:center; font-size:13px; padding:24px; }
p.lang { text-align:right; margin:0 0 8px; } p.lang a, section.feat a { color:var(--accent); font-weight:bold; }
p.warn { background:rgba(255,106,19,.12); border-radius:8px; padding:10px 14px; }
"""


def write(lang):
    U = UI[lang]
    num = numbered(lang)
    # the text manual
    out = [f"# {U['title']}", "", U["other"], "", U["warn"], "", U["intro"], "", f"## {U['toc']}", ""]
    for p, *_ in PARTS:
        out.append(f"**{p}. {part_name(p, lang)}**")
        out.append("")
        for code, v in num:
            if v["part"] == p:
                out.append(f"- [{code} {texts(v, lang)[0]}](#{v['id']})")
        out.append("")
    out.append(f"- [{U['glossary']}](#glosario)")
    out.append("")
    for p, *_ in PARTS:
        out += [f"## {p}. {part_name(p, lang)}", ""]
        for code, v in num:
            if v["part"] != p:
                continue
            title, how, detail = texts(v, lang)
            out += [f'<a id="{v["id"]}"></a>', f"### {code} {title}", ""]
            if how != "—":
                out += [f"*{U['how']}* {how}", ""]
            out += [detail, ""]
    out += ['<a id="glosario"></a>', f"## {U['glossary']}", "", glossary_md(lang, lambda c: f"#{c}"), ""]
    (OUT / U["md"]).write_text("\n".join(out), encoding="utf-8", newline="\n")
    # the illustrated one
    h = [f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
         f'<title>{html.escape(U["title"])}</title><style>{CSS}</style></head><body>',
         f'<header class="cover"><h1>Circuit Remix</h1><p>{U["cover"]}</p><p>{VERSION}</p><div class="bar"></div></header><main>',
         U["other_html"], md2html(U["warn"]), f"<p>{inline(U['intro'])}</p>", f'<nav class="toc"><h2>{U["toc"]}</h2>']
    for p, *_ in PARTS:
        h.append(f"<h3>{p}. {html.escape(part_name(p, lang))}</h3><ol>")
        for code, v in num:
            if v["part"] == p:
                h.append(f'<li><a href="#{v["id"]}">{code} {html.escape(texts(v, lang)[0])}</a></li>')
        h.append("</ol>")
    h.append(f'<h3><a href="#glosario">{html.escape(U["glossary"])}</a></h3></nav>')
    for p, *_ in PARTS:
        h.append(f'<h2 class="group">{p}. {html.escape(part_name(p, lang))}</h2>')
        for code, v in num:
            if v["part"] != p:
                continue
            title, how, detail = texts(v, lang)
            h.append(f'<section class="feat" id="{v["id"]}"><h3><span class="code">{code}</span>{html.escape(title)}</h3>')
            if how != "—":
                h.append(f'<div class="summary"><p><strong>{html.escape(U["how"])}</strong> {inline(how)}</p></div>')
            for f in v["figs"]:
                h.append(f"<figure>{svg(f, lang)}<figcaption>{html.escape(f[lang])}</figcaption></figure>")
            h.append(md2html(detail.replace("](#", "](#")))
            h.append("</section>")
    h.append(f'<h2 class="group" id="glosario">{html.escape(U["glossary"])}</h2><section class="feat">{md2html(glossary_md(lang, lambda c: "#" + c))}</section>')
    h.append(f"<footer>{U['footer']}</footer></main></body></html>")
    d = OUT / "manual"
    d.mkdir(parents=True, exist_ok=True)
    (d / U["html"]).write_text("\n".join(h), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    ids = [v["id"] for v in V]
    assert len(ids) == len(set(ids)) and all(g[4] in ids for g in GLOSSARY)
    for lang in ("es", "en"):
        write(lang)
    d = OUT.relative_to(ROOT).as_posix()
    print(f"{len(V)} chapters, {len(GLOSSARY)} glossary entries: {d}/MANUAL.md, MANUAL_EN.md, manual/index.html, manual/en.html")
