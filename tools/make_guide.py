"""The user manual of Circuit Remix, by views, with a glossary of every function (MIT; the user, 2026-10-28: «Make a manual (circuit-hacks
style manual, group chapters per view when possible and add a glossary per function)»).  One source, two languages, two outputs each:

    python tools/make_guide.py      -> docs/MANUAL.md, docs/MANUAL_EN.md (text), docs/manual/index.html, docs/manual/en.html (illustrated:
                                       the pads and knobs in colour); in the development tree under public/

Every chapter: (id, part, {es, en: title, how to get there, detail in a small markdown: ### | tables | - lists, 1. lists, **bold**, `code`},
figures).  The glossary: one entry per function, linked to its chapter.  The colours follow docs/INTERFAZ.md (RH52-RH59 / Alpha 0.05-0.09).
"""
from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "Alpha 0.09"
OUT = ROOT / "public" / "docs" if (ROOT / "public").is_dir() else ROOT / "docs"     # (the development tree / the public one)

# ---------------------------------------------------------------------------------------------------- colours (the LEDs' RGB, docs/INTERFAZ.md)
C = dict(white="#ffffff", grey="#5a5a5a", sky="#14a5fe", lilac="#ffa2ff", mint="#8affd0", amber="#ffaf2f", steel="#5e84cc", red="#ff2020",
         yellow="#ffff19", green="#22ee44", orange="#fc9108", peach="#ff8682", cream="#e7ff9e", pink="#ff74be", magenta="#c63ac6",
         cyan="#44ddff", blue="#2f7bff", track="#ff4e13", rose="#ff4c7b", gold="#ffd966", redorange="#ff5008", teal="#00ffb5",
         lime="#c7ff66")
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


A = "*(Alpha 0.09)*"
A_EN = "*(Alpha 0.09)*"
A8 = "*(Alpha 0.08)*"
A8_EN = "*(Alpha 0.08)*"
A7 = "*(Alpha 0.07)*"
A7_EN = "*(Alpha 0.07)*"
A6 = "*(Alpha 0.06)*"
A6_EN = "*(Alpha 0.06)*"
A5 = "*(desde Alpha 0.05)*"
A5_EN = "*(since Alpha 0.05)*"

# ===== 0
view("leer", "0", ("Cómo leer este manual", "—", """
Cada capítulo es una vista del aparato: cómo se llega, qué hacen sus pads, knobs y botones con Circuit Remix. Todo lo demás funciona como en el firmware original de Novation (consulta su manual); los gestos nuevos son combinaciones que en el original no hacían nada o repetían el gesto sin modificador.

- **Pads 1-32** de izquierda a derecha y de arriba abajo: fila 1 = 1-8, fila 2 = 9-16, fila 3 = 17-24, fila 4 = 25-32.
- **K1-K8** = los 8 knobs. **▲ / ▼** = los botones de flecha.
- **Mantener** un botón = pulsarlo y no soltarlo; **A + B** = B con A mantenido.
- **★** = exclusiva de Circuit Remix (no está en CIRCUIT-HACKS).
- **(desde Alpha 0.0x)** = la versión que trajo la función. Lo marcado {A6} es nuevo o cambia en esta versión.
- Al final, el **[glosario](#glosario)**: una entrada por función, con su vista y su gesto.
"""), ("How to read this manual", "—", """
Each chapter is a view of the device: how you get there, and what its pads, knobs and buttons do with Circuit Remix. Everything else works as in Novation's original firmware (see its manual); the new gestures are combinations that did nothing in the original or repeated the plain gesture.

- **Pads 1-32** left to right, top to bottom: row 1 = 1-8, row 2 = 9-16, row 3 = 17-24, row 4 = 25-32.
- **K1-K8** = the 8 knobs. **▲ / ▼** = the arrow buttons.
- **Hold** a button = press it and keep it down; **A + B** = B with A held.
- **★** = exclusive to Circuit Remix (not in CIRCUIT-HACKS).
- **(since Alpha 0.0x)** = the release that brought the function. Marked {A6}: new or changed in this release.
- At the end, the **[glossary](#glosario)**: one entry per function, with its view and its gesture.
"""))

view("colores", "0", ("El código de colores", "—", f"""
Desde Alpha 0.05 todo lo nuevo sigue unas reglas fijas {A5}:

| Regla | Qué ves |
|---|---|
| El brillo es el valor | en una página de knobs, todos los knobs del mismo color; cuanto más brillo, más valor |
| Knobs con centro | el centro (el cero) oscuro; más brillo hacia los dos extremos |
| Frecuencias (LFO, scan) | centro = parado; a la derecha libre, más rápido hacia el extremo; a la izquierda a tempo, divisiones más rápidas hacia el extremo |
| Adelante / atrás (scan del granular) | centro = parado; a la derecha hacia delante, a la izquierda hacia atrás, más rápido hacia los extremos |
| Encendido / apagado | el mismo color, brillante / tenue |
| Modos | un color por modo (las formas de onda del sinte, el tipo de filtro y el de waveshaper de Stock+, el metrónomo) |
| Opciones que se eligen entre sí | en la misma fila; la elegida brillante, las demás tenues |
| Abrir un menú o una página | un toque lo deja abierto; mantenerlo lo muestra hasta soltar |

Cada página de knobs de una pista tiene su color, el mismo en sus knobs y en su pad del menú (el botón de la pista ya no parpadea {A}):

| Página | Color |
|---|---|
| stock (la del firmware original) | blanco en el menú; los knobs, los del original |
| Stock+ | azul cielo |
| Granular | lila |
| Sinte | menta |
| Envolvente | rosa |
""", [fig("Las páginas de knobs en el menú de pista: brillante = la que se ve.", "The knob pages in the track menu: bright = the one shown.",
          pads={1: ("white", "stock", "stock"), 2: ("sky", "Stock+", "Stock+", True), 3: ("lilac", "Granular", "Granular", True),
                4: ("mint", "Sinte", "Synth", True)})]), ("The colour code", "—", f"""
Since Alpha 0.05 everything new follows fixed rules {A5_EN}:

| Rule | What you see |
|---|---|
| Brightness is the value | on a knob page every knob has the same colour; the brighter, the higher |
| Knobs with a centre | the centre (zero) dark; brighter towards both ends |
| Frequencies (LFO, scan) | centre = stopped; right = free running, faster towards the end; left = synced to the tempo, faster divisions towards the end |
| Forward / backward (the granular scan) | centre = stopped; right forward, left backward, faster towards the ends |
| On / off | the same colour, bright / dim |
| Modes | a colour per mode (the synth's waveforms, Stock+'s filter and waveshaper types, the metronome) |
| Options you pick one of | on the same row; the chosen one bright, the others dim |
| Opening a menu or a page | a tap keeps it open; holding shows it until you let go |

Each knob page of a track has its own colour, the same on its knobs and on its pad in the menu (the track's button no longer blinks {A_EN}):

| Page | Colour |
|---|---|
| stock (the original firmware's) | white in the menu; the knobs, the original's |
| Stock+ | sky blue |
| Granular | lilac |
| Synth | mint |
| Envelope | rose |
"""))

view("instalar", "0", ("Instalar y volver al original", "—", """
1. Descarga `rm_uploader.zip`, descomprímelo y abre `rm_uploader.html` en Chrome o Edge.
2. Aporta el firmware oficial 2.0.1 (build 5706) del Circuit Rhythm: el instalador comprueba su SHA-256 y lo parchea en tu ordenador.
3. Elige la versión y envíala al aparato por USB.

**Versiones S** (A0.09S): sin las funciones que crean, cambian o borran ficheros de la tarjeta por su cuenta (copiar proyectos, borrar packs, copiar samples). La más segura para tu SD.

**Volver al firmware oficial:** mantén **Sample Rec + Samples + Note** al encender (modo bootloader de Novation) y envía el oficial con el instalador («Oficial») o con Novation Components. Haz siempre una copia de tu tarjeta SD.
"""), ("Install and go back to the original", "—", """
1. Download `rm_uploader.zip`, unzip it and open `rm_uploader.html` in Chrome or Edge.
2. Provide the official Circuit Rhythm firmware 2.0.1 (build 5706): the installer checks its SHA-256 and patches it on your computer.
3. Pick the version and send it to the device over USB.

**S versions** (A0.09S): without the functions that create, change or delete files on the card by themselves (project copy, pack delete, sample copy). The safest for your SD.

**Back to the official firmware:** hold **Sample Rec + Samples + Note** while powering on (Novation's bootloader mode) and send the official one with the installer ("Official") or with Novation Components. Always back up your SD card.
"""))

# ===== 1
view("transporte", "1", ("Transporte, metrónomo y cuantizar", "en cualquier vista", """
| Gesto | Qué hace |
|---|---|
| **Shift + Clear** | metrónomo en cuatro estados; con Shift, el LED de Clear: rojo = sin metrónomo, verde = metrónomo, magenta = solo cuenta atrás, cian = las dos *(desde Alpha 0.0)* |
| **Record armado + Play** (parado, con cuenta atrás) | un compás de clics al tempo y arranca grabando (Record parpadea); Play durante la cuenta la cancela |
| **Shift + Play** (parado) | el del original: sigue desde donde se paró; con cuenta atrás, la cuenta y luego sigue |
| **K5 de la vista Tempo / Swing a 0** (clic sin volumen) | metrónomo visual: Clear destella 100 ms en cada clic de la cuenta y, sonando con el metrónomo, en cada tiempo, en naranja (distinto de los colores del metrónomo que muestra Clear con Shift); no mientras se mantiene Shift o Clear *(Alpha 0.08)* |
| **Shift + Play** (sonando) | cuantiza el patrón de la pista elegida: los micropasos 2-3 al comienzo de su paso, 4-6 al del siguiente; los redobles se quedan. LED de Play con Shift: amarillo; verde tras cuantizar; rojo = nada que cuantizar *(desde Alpha 0.0)* |

La cuenta atrás no se guarda: al encender vuelve a «sin cuenta atrás».

**La cuenta con el reloj de la música** *(Alpha 0.08)* (contribución de mefisme):
- Los clics siguen el reloj de la música: el tempo del proyecto, o el reloj MIDI externo si el Rhythm es esclavo. Antes los contaba la tarea de los LEDs, de 0 a 10 ms tarde.
- Play entra al empezar la cuenta y el reloj espera hasta el 1: el trabajo de Play se hace durante la cuenta y el 1 llega a tiempo.
- Durante la cuenta no se graba nada, el LED de Play se ve parado y Record destella en rojo en cada clic.
- Como esclavo, el primer clic cae en el compás siguiente del maestro si el Rhythm conoce su posición (recibió su Start o Song Position); si no, en el primer pulso tras pulsar Play. Un Start del maestro durante la cuenta la para.
- Play carga los pasos más rápido (el mismo resultado con la cuarta parte de las llamadas).
- **Luz de error:** si Clear parpadea en rojo (¼ s encendido, ¼ s apagado) sin pulsar nada, estas funciones se han apagado porque el firmware no es el esperado. No debería verse nunca: si lo ves, avísanos en GitHub.

**Arreglos del original** (desde Alpha 0.04): la reproducción empieza antes (≈ 10 ms de Play al primer sonido; el original ≈ 18 ms), las notas de un mismo paso suenan juntas, no se pierden notas con muchas pistas en el mismo paso y el reloj no tropieza al guardar un sample.
""", [fig("Shift + Clear: el LED de Clear da el estado del metrónomo.", "Shift + Clear: the Clear LED shows the metronome's state.",
          buttons=["Shift", "Clear"])]), ("Transport, metronome and quantize", "in any view", """
| Gesture | What it does |
|---|---|
| **Shift + Clear** | metronome in four states; with Shift, the Clear LED: red = no metronome, green = metronome, magenta = count-in only, cyan = both *(since Alpha 0.0)* |
| **Record armed + Play** (stopped, with count-in) | one bar of clicks at the tempo, then recording starts (Record blinks); Play during the count cancels it |
| **Shift + Play** (stopped) | the original's: carry on from where it stopped; with count-in, the count and then carry on |
| **Tempo / Swing view K5 at 0** (click muted) | visual metronome: Clear flashes for 100 ms on each click of the count and, while playing with the metronome, on each beat, in orange (unlike the metronome colours Clear shows with Shift); not while Shift or Clear is held *(Alpha 0.08)* |
| **Shift + Play** (playing) | quantizes the selected track's pattern: micro steps 2-3 to the start of their step, 4-6 to the next one; rolls stay. Play LED with Shift: yellow; green after quantizing; red = nothing to quantize *(since Alpha 0.0)* |

The count-in isn't saved: at power-on it goes back to "no count-in".

**The count on the music's clock** *(Alpha 0.08)* (contributed by mefisme):
- The clicks follow the music's clock: the project's tempo, or the external MIDI clock when the Rhythm is a slave. Before, the LED task timed them, 0 to 10 ms late.
- Play goes through at the start of the count and the clock waits until the 1: Play's work runs during the count and the 1 is on time.
- During the count nothing records, the Play LED shows stopped and Record flashes red on each click.
- As a slave, the first click comes on the master's next bar if the Rhythm knows its position (it received its Start or Song Position); otherwise on the first pulse after Play. A Start from the master during the count stops it.
- Play loads the steps faster (the same result with a quarter of the calls).
- **Error light:** if Clear blinks red (¼ s on, ¼ s off) without you pressing anything, these features have switched themselves off because the firmware isn't the expected one. It should never show: if you see it, tell us on GitHub.

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
                      4: ("mint", "Sinte", "Synth", True), 5: ("rose", "Envolv.", "Envelope", True), 8: ("red", "Project\ninit", "Project\ninit")})
view("menu", "2", ("El menú de pista", "toca el botón de la pista elegida (el menú se queda abierto hasta que eliges algo o lo vuelves a tocar), o mantén el botón de cualquier pista (el menú solo mientras lo mantienes)", f"""
Los pads se convierten en el menú de esa pista {A6}:

| Pad | Qué hace |
|---|---|
| **1** | página **stock** de los knobs (la del original) |
| **2** | página **[Stock+](#stockplus)** (con un sample; con el granular o el sinte {A7}) |
| **3** | página **[Granular](#granular)** (con el granular) |
| **4** | página **[Sinte](#sinte)** (con el sinte) |
| **5** | página **[Envolvente](#envolvente)** (con el sinte o el granular) {A6} |
| **8** | ★ la voz de la pista vuelve a **Project init** (rojo): K1-K8 y el resto de la voz como se cargó o guardó el proyecto por última vez; el nivel, el panorama, los envíos y el sidechain no se tocan {A} |

**El sonido de la pista, el enlace estéreo y la entrada** pasaron a [Sample mode](#samplemode) {A}: sus pads 5-8, 14, 15 y 16.

- **Abrirlo:** un toque en el botón de la pista que ya está elegida lo deja abierto; se cierra al soltar un pad del menú, al tocar otra vez el botón o al pulsar cualquier otro botón. Mantener el botón de una pista (¼ s) lo abre solo mientras lo mantienes, como los botones de vista del original.
- Fila 1, las **páginas** de la pista: solo las de su sonido (sample: stock y Stock+; granular: stock, Stock+, Granular y Envolvente; sinte: stock, Stock+, Sinte y Envolvente; entrada: stock); las demás, oscuras. Brillante = la que se ve. **Mantener** un pad de página (½ s o más) la muestra solo hasta que lo sueltas y vuelve la anterior.
- **El sonido de la pista** (sample, granular, sinte o entrada, uno por pista) se elige en [Sample mode](#samplemode), pads 5-8 {A}. Hasta Alpha 0.08 estaba en la fila 2 de este menú (pads 11-14), con el enlace en el 9 y la fuente de la entrada en el 15.
- Con el granular o el sinte, la página stock deja los knobs del original (filtro, envolvente, tono, nivel…) actuando sobre ellos; también la **distorsión**, con la misma curva que en un sample {A7}.

En Alpha 0.04 el menú era: 1-3 páginas, 4 granular, 5 / 6 entrada y gate, 7 enlace.
""", [fig("El menú de una pista con un sample, en la página stock.", "The menu of a track with a sample, on the stock page.",
          buttons=[("Pista elegida (toque)", "Selected track (tap)")],
          pads={1: ("white", "stock", "stock"), 2: ("sky", "Stock+", "Stock+", True), 8: ("red", "Project\ninit", "Project\ninit")}),
      fig("El menú de una pista con el sinte, en su página.", "The menu of a synth track, on its page.",
          pads={1: ("white", "stock", "stock", True), 2: ("sky", "Stock+", "Stock+", True), 4: ("mint", "Sinte", "Synth"),
                5: ("rose", "Envolv.", "Envelope", True), 8: ("red", "Project\ninit", "Project\ninit")})]),
     ("The track menu", "tap the selected track's button (the menu stays open until you pick something or tap again), or hold any track's button (the menu only while held)", f"""
The pads become that track's menu {A6_EN}:

| Pad | What it does |
|---|---|
| **1** | the **stock** knob page (the original's) |
| **2** | the **[Stock+](#stockplus)** page (with a sample; with the granular or the synth {A7_EN}) |
| **3** | the **[Granular](#granular)** page (with the granular) |
| **4** | the **[Synth](#sinte)** page (with the synth) |
| **5** | the **[Envelope](#envolvente)** page (with the synth or the granular) {A6_EN} |
| **8** | ★ the track's voice back to **Project init** (red): K1-K8 and the rest of the voice as the project was last loaded or saved; level, pan, sends and sidechain are left alone {A_EN} |

**The track's sound, the stereo link and the line input** moved to [Sample mode](#samplemode) {A_EN}: its pads 5-8, 14, 15 and 16.

- **Opening it:** a tap on the button of the track already selected leaves it open; it closes when you let go of a menu pad, tap the button again or press any other button. Holding a track's button (¼ s) opens it only while held, like the original's view buttons.
- Row 1, the track's **pages**: only those of its sound (sample: stock and Stock+; granular: stock, Stock+, Granular and Envelope; synth: stock, Stock+, Synth and Envelope; input: stock); the others dark. Bright = the one shown. **Holding** a page pad (½ s or more) shows it only until you let go, then the previous one returns.
- **The track's sound** (sample, granular, synth or input, one per track) is picked in [Sample mode](#samplemode), pads 5-8 {A_EN}. Up to Alpha 0.08 it was on row 2 of this menu (pads 11-14), with the link on 9 and the input's source on 15.
- With the granular or the synth, the stock page leaves the original's knobs (filter, envelope, pitch, level…) acting on them; the **distortion** too, with the same curve as on a sample {A7_EN}.

In Alpha 0.04 the menu was: 1-3 pages, 4 granular, 5 / 6 input and gate, 7 link.
"""))

view("stockplus", "2", ("Página Stock+", "menú de pista, pad 2, en una pista con un sample, el granular o el sinte", f"""
La página Stock+ es por pista y se queda hasta apagar *(desde Alpha 0.01; K5-K8 desde Alpha 0.02)*. Actúa sobre el sample de la pista; con el granular o el sinte, sobre ellos {A7}.

| Knob | Solo | Con Shift |
|---|---|---|
| K1 | ★ envolvente de tono: centro = nada; derecha = cada golpe empieza más agudo, izquierda más grave (hasta ±24 semitonos) | ajuste fino |
| K2 | ★ lo que tarda en volver a la nota (5 ms - 4 s) | ajuste fino |
| K3 | ★ velocidad del LFO de tono: centro = apagado; derecha = libre (0,05-30 Hz); izquierda = a tempo, de 8 compases junto al centro a 1/16T en el extremo {A5} | ajuste fino |
| K4 | ★ profundidad del LFO de tono (0-24 semitonos) | ajuste fino |
| K5 | ★ cantidad del ring mod | ★ su frecuencia (20 Hz-5 kHz) |
| K6 | ★ pitch follow: el corte del paso bajo sigue a la nota | ★ tipo de filtro sobre los knobs de filtro del original: **stock** (blanco), **24 dB** (naranja), **comb** (lavanda) |
| K7 | ★ **stretch**: más lento (izquierda, hasta 0,25×) o más rápido (derecha, hasta 4×) sin cambiar el tono; centro = el original | ★ bitcrush |
| K8 | ★ velocidad del scan (mueve el inicio de cada nota; en un loop, el inicio del loop en cada vuelta): centro = quieto; derecha = libre (0,05-20 Hz); izquierda = a tempo, más rápido hacia el extremo {A5} | ★ su profundidad |

- **LEDs:** azul cielo con el brillo según el valor (K1, K3, K7 y K8: la distancia al centro); K6 en el color de su tipo de filtro. Con Shift, K5-K8 enseñan su segunda capa.
- **Clear + knob:** su valor por defecto (en K5-K8, las dos capas).
- **Se guarda con el proyecto.** En proyectos de Alpha 0.04, la mitad a tempo de K3 y K8 va ahora al revés.
- **El stretch** reparte el sample en granos de unos 43 ms que se mantienen en fase (WSOLA): a 0,5× suena muy bien; a 0,25× la batería puede sonar con clics.

**Con el granular o el sinte** {A7}: los mismos valores de la pista, sobre su sonido.

| Knob | Granular | Sinte |
|---|---|---|
| K1-K4 | la envolvente y el LFO de tono, en el tono de cada grano nuevo | la envolvente y el LFO de tono, en los dos osciladores |
| K5, K6 | ring, pitch follow y el tipo de filtro, sobre su filtro | lo mismo |
| K7 | ★ **waveshaper**: cantidad (0 = apagado; la ganancia de ×1 a ×16; en bitcrush, los bits). Shift: su **tipo**, **suave** (dorado), **duro** (rojo anaranjado), **plegado** (turquesa), **bitcrush** (lima) | lo mismo |
| K8 | ★ LFO de la **posición** de los granos (Shift: su profundidad) | ★ LFO de la **cantidad de FM** (Shift: su profundidad) |

- **Tipo de filtro** (Shift + K6): con **24 dB** su filtro pasa dos veces; con **comb**, sus filtros se abren y suena un comb afinado por el knob de paso bajo de la pista (más el follow; en el sinte, más la envolvente → filtro), con la resonancia como realimentación.
- El LED de K7 va en el color del tipo y brilla según la cantidad; con Shift, a tope. Clear + K7: apagado y suave.
- El waveshaper se guarda con el proyecto y lo llevan Clear + el botón de la pista y Duplicate.
""", [fig("Página Stock+: knobs en azul cielo; K6 en el color de su tipo de filtro.", "Stock+ page: knobs in sky blue; K6 in its filter type's colour.",
          knobs={1: ("env. tono", "pitch env.", "", "sky"), 2: ("caída", "decay", "", "sky"), 3: ("LFO vel.", "LFO rate", "", "sky"),
                 4: ("LFO prof.", "LFO depth", "", "sky"), 5: ("ring", "ring", "", "sky"), 6: ("follow", "follow", "", "white"),
                 7: ("stretch", "stretch", "", "sky"), 8: ("scan", "scan", "", "sky")}),
      fig("Página Stock+ de una pista con el sinte: K7, el waveshaper en el color de su tipo (suave, dorado); K8, el LFO de la FM.",
          "Stock+ page of a synth track: K7, the waveshaper in its type's colour (soft, gold); K8, the FM's LFO.",
          knobs={1: ("env. tono", "pitch env.", "", "sky"), 2: ("caída", "decay", "", "sky"), 3: ("LFO vel.", "LFO rate", "", "sky"),
                 4: ("LFO prof.", "LFO depth", "", "sky"), 5: ("ring", "ring", "", "sky"), 6: ("follow", "follow", "", "white"),
                 7: ("waveshaper", "waveshaper", "", "gold"), 8: ("FM", "FM", "", "sky")})]), ("Stock+ page", "track menu, pad 2, on a track with a sample, the granular or the synth", f"""
The Stock+ page is per track and stays until power-off *(since Alpha 0.01; K5-K8 since Alpha 0.02)*. It acts on the track's sample; with the granular or the synth, on them {A7_EN}.

| Knob | Alone | With Shift |
|---|---|---|
| K1 | ★ pitch envelope: centre = none; right = each hit starts higher, left lower (up to ±24 semitones) | fine |
| K2 | ★ how long it takes to return to the note (5 ms - 4 s) | fine |
| K3 | ★ pitch LFO rate: centre = off; right = free (0.05-30 Hz); left = synced, from 8 bars by the centre to 1/16T at the end {A5_EN} | fine |
| K4 | ★ pitch LFO depth (0-24 semitones) | fine |
| K5 | ★ ring mod amount | ★ its frequency (20 Hz-5 kHz) |
| K6 | ★ pitch follow: the low-pass cutoff follows the note | ★ filter type over the original's filter knobs: **stock** (white), **24 dB** (orange), **comb** (lavender) |
| K7 | ★ **stretch**: slower (left, down to 0.25×) or faster (right, up to 4×) without changing pitch; centre = the original | ★ bitcrush |
| K8 | ★ scan rate (moves each note's start; on a loop, the loop's start on every pass): centre = still; right = free (0.05-20 Hz); left = synced, faster towards the end {A5_EN} | ★ its depth |

- **LEDs:** sky blue with the value as brightness (K1, K3, K7 and K8: the distance from the centre); K6 in its filter type's colour. With Shift, K5-K8 show their second layer.
- **Clear + knob:** its default (on K5-K8, both layers).
- **Saved with the project.** In Alpha 0.04 projects, the synced half of K3 and K8 now runs the other way.
- **The stretch** splits the sample into ~43 ms grains kept in phase (WSOLA): at 0.5× it sounds very good; at 0.25× drums may click.

**With the granular or the synth** {A7_EN}: the track's same values, on its sound.

| Knob | Granular | Synth |
|---|---|---|
| K1-K4 | the pitch envelope and LFO, on each new grain's pitch | the pitch envelope and LFO, on both oscillators |
| K5, K6 | ring, pitch follow and the filter type, on its filter | the same |
| K7 | ★ **waveshaper**: amount (0 = off; the gain from ×1 to ×16; for bitcrush, the bits). Shift: its **type**, **soft** (gold), **hard** (red-orange), **fold** (teal), **bitcrush** (lime) | the same |
| K8 | ★ an LFO on the grains' **position** (Shift: its depth) | ★ an LFO on the **FM amount** (Shift: its depth) |

- **Filter type** (Shift + K6): with **24 dB** its filter runs twice; with **comb** its filters open and a comb plays, tuned by the track's low-pass knob (plus the follow; on the synth, plus envelope → filter), with the resonance as feedback.
- K7's LED is in the type's colour, as bright as the amount; with Shift, fully. Clear + K7: off and soft.
- The waveshaper is saved with the project and goes along with Clear + the track's button and Duplicate.
"""))

view("granular", "2", ("Página Granular", "Sample mode, pad 6 (pone el granular y su página), o menú de pista, pad 3 (su página)", f"""
El motor granular de CIRCUIT-HACKS sobre el sample de la pista, en el DSP del master *(desde Alpha 0.04)*. Sigue la nota (vista Note, teclado y MIDI). Los knobs de filtro (paso alto, paso bajo, resonancia) y la envolvente de la pista actúan sobre él; también la distorsión {A7}. **Hasta 4 pistas granulares**, cada una con sus ajustes; los 16 granos se reparten (16 con una pista, 7 por pista con dos, 4 con tres, 2 con cuatro).

| Knob | Solo | Con Shift |
|---|---|---|
| K1 | tamaño del grano (5-500 ms) | fino |
| K2 | densidad (1-16 granos) | ★ apertura estéreo (0 = mono) |
| K3 | posición en el sample | fina |
| K4 | scan: centro = quieto; derecha hacia delante, izquierda hacia atrás | fino |
| K5 | altura (centro = la nota; ±24 semitonos) | altura fina |
| K6 | dispersión de la posición | zona (qué parte del sample) |
| K7 | dispersión de la altura | probabilidad de reverso |
| K8 | ventana (rectángulo → triángulo → percusiva) | gate, encendido / apagado: tenue = siempre suena (drone), brillante = lo abren las notas {A5} |

Lila con el brillo según el valor (K4, K5 y Shift + K5: la distancia al centro). Clear + knob = por defecto. Se guarda con el proyecto.

**Inicio y longitud del original** {A} (página stock, K2 / K3): el inicio se suma a la posición (K3 de esta página), hasta el final del sample; la longitud estrecha la zona (a tope, su valor por defecto, no cambia nada).
""", [fig("Página Granular: knobs en lila.", "Granular page: knobs in lilac.",
          knobs={1: ("tamaño", "size", "", "lilac"), 2: ("densidad", "density", "", "lilac"), 3: ("posición", "position", "", "lilac"),
                 4: ("scan", "scan", "", "lilac"), 5: ("altura", "pitch", "", "lilac"), 6: ("disp. pos.", "pos. spray", "", "lilac"),
                 7: ("disp. alt.", "pitch spray", "", "lilac"), 8: ("ventana", "window", "", "lilac")})]), ("Granular page", "Sample mode, pad 6 (puts the granular on, with its page), or track menu, pad 3 (its page)", f"""
The CIRCUIT-HACKS granular engine on the track's sample, on the master DSP *(since Alpha 0.04)*. It follows the note (Note view, keyboard and MIDI). The track's filter knobs (high-pass, low-pass, resonance) and envelope act on it; the distortion too {A7_EN}. **Up to 4 granular tracks**, each with its own settings; the 16 grains are shared (16 with one track, 7 each with two, 4 with three, 2 with four).

| Knob | Alone | With Shift |
|---|---|---|
| K1 | grain size (5-500 ms) | fine |
| K2 | density (1-16 grains) | ★ stereo spread (0 = mono) |
| K3 | position in the sample | fine |
| K4 | scan: centre = still; right forward, left backward | fine |
| K5 | pitch (centre = the note; ±24 semitones) | fine pitch |
| K6 | position spray | zone (which part of the sample) |
| K7 | pitch spray | reverse chance |
| K8 | window (rectangle → triangle → percussive) | gate, on / off: dim = always sounds (drone), bright = opened by the notes {A5_EN} |

Lilac with the value as brightness (K4, K5 and Shift + K5: the distance from the centre). Clear + knob = default. Saved with the project.

**The original's start and length** {A_EN} (stock page, K2 / K3): the start adds to the position (this page's K3), up to the sample's end; the length narrows the zone (fully up, its default, changes nothing).
"""))

view("sinte", "2", ("Página Sinte", "Sample mode, pad 7 (pone el sinte y su página), o menú de pista, pad 4 (su página)", f"""
★ Un sinte monofónico de dos osciladores en el DSP del master, como sonido de cualquier pista {A5}. **Hasta 4 pistas con sinte.** Las notas le llegan como a un sample (pads, vista Note, secuencia, MIDI).

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

- **Los knobs del original** de la pista siguen actuando sobre el sinte (en la página stock): tono, envolvente (a la izquierda del centro caída, en el centro sostiene, a la derecha ataque lento), paso bajo, paso alto, resonancia, distorsión {A7}, nivel, panorama, envíos, sidechain y mute.
- **Inicio y longitud del original** {A} (página stock, K2 / K3): **el inicio = morph**: desde la forma de K1 / K2, cada oscilador pasa de forma continua a la siguiente (sierra → pulso → triángulo → seno → sierra), hasta 3 formas a tope; **la longitud = unísono**: por debajo del máximo, cada oscilador suena dos veces, desafinadas hasta un cuarto de semitono (con la longitud a 0). Con los valores por defecto (inicio 0, longitud a tope) suena como antes. Morph y unísono gastan más DSP: cuatro sintes así con el granular a la vez podrían no caber.
- **Note-off:** una pista con sinte recibe el note-off aunque esté en one-shot, para que suene el release.
- **LEDs:** menta con el brillo según el valor (K3, K4, Shift + K4, Shift + K7: la distancia al centro); K1 / K2 en el color de su forma de onda.
- Clear + knob = por defecto. **Se guarda con el proyecto.**
""", [fig("Página Sinte: K1 / K2 en el color de la forma de onda, el resto en menta.", "Synth page: K1 / K2 in the waveform's colour, the rest in mint.",
          knobs={1: ("OSC 1", "OSC 1", "", "red"), 2: ("OSC 2", "OSC 2", "", "red"), 3: ("altura 2", "pitch 2", "", "mint"),
                 4: ("fino 2", "fine 2", "", "mint"), 5: ("mezcla", "mix", "", "mint"), 6: ("SUB", "SUB", "", "mint"),
                 7: ("FM", "FM", "", "mint"), 8: ("pulso", "pulse", "", "mint")})]), ("Synth page", "Sample mode, pad 7 (puts the synth on, with its page), or track menu, pad 4 (its page)", f"""
★ A monophonic two-oscillator synth on the master DSP, as any track's sound {A5_EN}. **Up to 4 synth tracks.** It gets its notes like a sample does (pads, Note view, sequence, MIDI).

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

- **The original's knobs** of the track still act on the synth (on the stock page): pitch, envelope (left of centre decay, centre sustain, right slow attack), low-pass, high-pass, resonance, distortion {A7_EN}, level, pan, sends, sidechain and mute.
- **The original's start and length** {A_EN} (stock page, K2 / K3): **start = morph**: from K1 / K2's waveform, each oscillator moves smoothly to the next one (saw → pulse → triangle → sine → saw), up to 3 shapes fully up; **length = unison**: below fully up, each oscillator plays twice, detuned by up to a quarter semitone (length at 0). At the defaults (start 0, length fully up) it sounds as before. Morph and unison use more DSP: four synths like that plus the granular at once may not fit.
- **Note-off:** a synth track gets the note-off even in one-shot mode, so the release sounds.
- **LEDs:** mint with the value as brightness (K3, K4, Shift + K4, Shift + K7: the distance from the centre); K1 / K2 in their waveform's colour.
- Clear + knob = default. **Saved with the project.**
"""))

view("envolvente", "2", ("Página Envolvente", "menú de pista, pad 5, en una pista con el sinte o el granular", f"""
★ La envolvente del sinte y del granular, según el **modo de reproducción** de la pista (Sample mode, pads 25 / 26 / 27) {A6}:

| Knob | Qué hace |
|---|---|
| K1 | **inicio**: el ataque, de instantáneo a 2 s |
| K2 | **longitud**: en **one-shot**, la caída (percusiva; soltar la nota no cuenta); en **gated**, el release al soltar (arriba mientras dura la nota); en **loop**, cuánto se mantiene (lo que dure más, la nota o este tiempo; luego un release corto). De 5 ms a 8 s |
| K3 | **pendiente**, desde el centro: centro = lineal; derecha = exponencial (cae antes); izquierda = más redonda (aguanta) |
| K4 | **envolvente → paso bajo**, desde el centro |
| K5-K8 | nada (oscuros) |

- **El sinte:** K1, K2 y K4 son sus valores de siempre (K2 = el release de Shift + K6, K4 = Shift + K7 de su página).
- **El granular:** con su gate encendido (Shift + K8), las notas abren y cierran la envolvente, que es su VCA; los granos corren siempre. Con el gate apagado, suena siempre, como antes.
- Rosa con el brillo según el valor (K3 / K4: la distancia al centro). Clear + knob = por defecto. **Se guarda con el proyecto.**
""", [fig("Página Envolvente: K1-K4 en rosa, K5-K8 apagados.", "Envelope page: K1-K4 in rose, K5-K8 off.",
          knobs={1: ("inicio", "start", "", "rose"), 2: ("longitud", "length", "", "rose"), 3: ("pendiente", "slope", "", "rose"),
                 4: ("→ filtro", "→ filter", "", "rose")})]), ("Envelope page", "track menu, pad 5, on a synth or granular track", f"""
★ The synth's and the granular's envelope, by the track's **play mode** (Sample mode, pads 25 / 26 / 27) {A6_EN}:

| Knob | What it does |
|---|---|
| K1 | **start**: the attack, from instant to 2 s |
| K2 | **length**: in **one-shot**, the decay (percussive; letting go of the note doesn't count); in **gated**, the release when you let go (at the top while the note lasts); in **loop**, how long it holds (the note or this time, whichever is longer; then a short release). From 5 ms to 8 s |
| K3 | **slope**, from the centre: centre = linear; right = exponential (drops sooner); left = rounder (holds) |
| K4 | **envelope → low-pass**, from the centre |
| K5-K8 | nothing (dark) |

- **The synth:** K1, K2 and K4 are its usual values (K2 = the release on Shift + K6, K4 = Shift + K7 on its page).
- **The granular:** with its gate on (Shift + K8), the notes open and close the envelope, which is its VCA; the grains run all the time. With the gate off, it always sounds, as before.
- Rose with the value as brightness (K3 / K4: the distance from the centre). Clear + knob = default. **Saved with the project.**
"""))

view("entrada", "2", ("Entrada de línea y enlace estéreo", "Sample mode, pads 8 / 15 / 16 y 14", """
Los pads son los de [Sample mode](#samplemode) {A6}; hasta Alpha 0.08 estaban en el menú de pista (entrada 13, gate 14, fuente 15, enlace 9).

**Entrada de línea** (pad 8; desde Alpha 0.04): la entrada de audio suena como el sonido de la pista, con su nivel, panorama, envíos, filtro y envolvente.
- Una pista de entrada: L + R. Dos: la de número menor es L, la mayor R. En una tercera, sale la primera puesta.
- **Pad 16, el gate:** tenue = siempre suena; brillante = solo mientras suenan sus notas, por el VCA y el filtro de la pista (paso bajo, paso alto, resonancia; el filtro desde Alpha 0.06).
- **Pad 15, la fuente** (Alpha 0.06): las entradas (ámbar tenue, sin FX; hasta Alpha 0.07, ámbar) → el **retorno de reverb** (crema) → el **de delay** (melocotón), por turnos; cada pista de entrada la suya. El retorno llega un bloque tarde (0,67 ms).
- **El FX hacia una entrada** {A6}: el retorno que toma una pista de entrada ya no va al master; suena solo a través de la pista. El envío de esa pista a su propio efecto llega a la mitad (el knob entero = medio envío), así la realimentación se queda contenida; el envío al otro efecto va entero. Hasta Alpha 0.08, el retorno sonaba también por el master y el envío a su propio efecto realimentaba.

**Enlace estéreo** (pad 14; desde Alpha 0.04): la pista (izquierda) y la siguiente (derecha) suenan juntas con las notas de la primera. Pad 14 en cualquiera de las dos = deshacer. En la pista 8 sola, oscuro. Sin enlazar quedan el LFO y el scan libres de Stock+ y el WSOLA del stretch.
- **La segunda pista, en desviaciones** {A6}: sus K1-K8 (página stock) son desviaciones de los de la primera: centro = igual, a la derecha suma, a la izquierda resta. Sus LEDs en azul acero, oscuros en el centro. Clear + knob = el centro.
- **Su sample** = el de la primera + la distancia entre sus pads: por defecto, el siguiente; elegir otro pad en la segunda cambia la distancia, y mover el de la primera mueve los dos {A6}.
- **Sus propios pasos también suenan** {A6}: la segunda toca las notas de la primera y además las suyas.
- Enlazar pone los knobs de la segunda en el centro (suena igual); deshacer el enlace los deja donde sonaban. Un proyecto de Alpha 0.04-0.08 con un enlace carga como sonaba.

Las dos se guardan con el proyecto.
"""), ("Line input and stereo link", "Sample mode, pads 8 / 15 / 16 and 14", """
The pads are [Sample mode](#samplemode)'s {A6}; up to Alpha 0.08 they were on the track menu (input 13, gate 14, source 15, link 9).

**Line input** (pad 8; since Alpha 0.04): the audio input plays as the track's sound, with its level, pan, sends, filter and envelope.
- One input track: L + R. Two: the lower-numbered one is L, the higher R. Setting a third removes the first one set.
- **Pad 16, the gate:** dim = always sounds; bright = only while its notes play, through the track's VCA and filter (low-pass, high-pass, resonance; the filter since Alpha 0.06).
- **Pad 15, the source** (Alpha 0.06): the inputs (dim amber, no FX; up to Alpha 0.07, amber) → the **reverb return** (cream) → the **delay return** (peach), in turn; each input track its own. The return arrives a block late (0.67 ms).
- **An FX into an input** {A6}: the return an input track takes no longer goes to the master; it only sounds through the track. That track's send into its own effect is halved (the full knob = half a send), so the feedback stays contained; its send into the other effect is whole. Up to Alpha 0.08 the return also sounded through the master and the send into its own effect fed back.

**Stereo link** (pad 14; since Alpha 0.04): the track (left) and the next one (right) play together with the first one's notes. Pad 14 on either = undo. Dark on track 8 alone. Not linked: Stock+'s free LFO and scan, and the stretch's WSOLA.
- **The second track, as offsets** {A6}: its K1-K8 (stock page) are offsets from the first one's: centre = the same, right adds, left subtracts. Its LEDs steel blue, dark at the centre. Clear + knob = the centre.
- **Its sample** = the first one's + the gap between their pads: by default the next one; picking another pad on the second changes the gap, and moving the first one's moves both {A6}.
- **Its own steps play too** {A6}: the second plays the first one's notes and its own as well.
- Linking puts the second's knobs at the centre (it sounds the same); unlinking leaves them where they sounded. An Alpha 0.04-0.08 project with a link loads as it sounded.

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
| Velocity | **Shift mantenido** | ★ la **vista de automatización** {A}: los pasos con automatización de knobs en **amarillo**, los marcados en **rojo**, los demás como los dibuja la vista |
| Velocity | **Shift + paso amarillo** | ★ **escucharlo** {A}: sus valores van a los knobs y al sonido, esos knobs en amarillo (brillo = el valor); otro paso amarillo pone los suyos; al soltar Shift, todo vuelve como estaba |
| Velocity | **Shift + otro paso** | marca el paso *(desde Alpha 0.04)*: al sonar, la automatización no suena ahí y los parámetros automatizados vuelven a **Project init** {A} (hasta Alpha 0.08, a la posición de su knob); un knob girado a mano se queda donde lo dejaste. Otra vez = desmarcar |
| Velocity | **Velocity otra vez** | ★ la vista de automatización **fija**, sin mantener Shift {A}: un toque en un paso amarillo lo escucha, en otro lo marca. Velocity otra vez, u otra vista, la quita (lo que escuchabas vuelve). Shift + Velocity sigue siendo la velocity fija del original |
| Velocity | **Clear + paso** (con o sin Shift; Clear primero) | ★ borra la automatización de knobs de ese paso; sus notas, su marca y los carriles del Mixer se quedan {A} |
| Vista de pista (Samples) | **Record mantenido + paso** | ★ **snapshot** {A}: cada knob que no está en Project init queda en ese paso (sus 6 micropasos); el pad del paso en amarillo mientras lo mantienes; al soltar Record, la grabación como estaba |
| Micro Step | **pad 31** | longitud fija: apagada → el selector en los pads 17-32 (1-16 pasos; elegir una la enciende); encendida → apagada (naranja brillante / tenue) *(desde Alpha 0.04)* |
| Micro Step | **pad 32** | gate por pulsación: el golpe dura lo que mantienes el pad del paso; mantener un paso vacío 300 ms o más también lo crea (verde brillante / tenue) *(desde Alpha 0.04)* |

Encender uno de los dos de Micro Step apaga el otro. Con cualquiera, un golpe introducido a mano en los pasos toma esa longitud.

**Project init** de una pista {A}: sus parámetros como se cargó o se guardó el proyecto por última vez (se vuelve a tomar en cada guardado). El pad 8 del [menú de pista](#menu) (rojo) devuelve ahí su voz.
""", [fig("Micro Step: pad 31 longitud fija, pad 32 gate por pulsación (apagados: tenues).", "Micro Step: pad 31 fixed length, pad 32 gate by press (off: dim).",
          pads={31: ("orange", "longitud", "length", True), 32: ("green", "gate", "gate", True)}, buttons=["Shift", "Gate"])]),
     ("Velocity and Micro Step", "the Velocity button; Micro Step = Shift + Gate", f"""
| View | Gesture | What it does |
|---|---|---|
| Velocity | **Shift held** | ★ the **automation view** {A_EN}: steps with knob automation in **yellow**, the marked ones in **red**, the others as the view draws them |
| Velocity | **Shift + a yellow step** | ★ **listen to it** {A_EN}: its values go to the knobs and the sound, those knobs yellow (brightness = the value); another yellow step sets its own; let go of Shift and everything goes back |
| Velocity | **Shift + another step** | marks the step *(since Alpha 0.04)*: when it plays, automation is silent there and automated parameters go back to **Project init** {A_EN} (up to Alpha 0.08, to their knob's position); a knob turned by hand stays where you left it. Again = unmark |
| Velocity | **Velocity again** | ★ the automation view **latched**, without holding Shift {A_EN}: a tap on a yellow step listens to it, on another marks it. Velocity again, or another view, removes it (what you were listening to goes back). Shift + Velocity is still the original's fixed velocity |
| Velocity | **Clear + step** (with or without Shift; Clear first) | ★ erases that step's knob automation; its notes, its mark and the Mixer's lanes stay {A_EN} |
| Track view (Samples) | **Record held + step** | ★ **snapshot** {A_EN}: each knob not at Project init goes into that step (its 6 micro steps); the step's pad yellow while you hold it; when you let go of Record, recording as it was |
| Micro Step | **pad 31** | fixed length: off → the selector on pads 17-32 (1-16 steps; picking one switches it on); on → off (orange bright / dim) *(since Alpha 0.04)* |
| Micro Step | **pad 32** | gate by press: the hit lasts as long as you hold the step's pad; holding an empty step 300 ms or more also creates it (green bright / dim) *(since Alpha 0.04)* |

Switching one of the two Micro Step options on switches the other off. With either, a hit entered by hand on the steps takes that length.

A track's **Project init** {A_EN}: its parameters as the project was last loaded or saved (taken again on every save). Pad 8 of the [track menu](#menu) (red) brings its voice back there.
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
| **Pads 5-8** | ★ el **sonido de la pista**, uno encendido, los demás tenues: **5** sample (blanco), **6** [granular](#granular) (lila), **7** [sinte](#sinte) (menta), **8** [entrada de línea](#entrada) (ámbar). El 5 quita el granular, el sinte o la entrada; el 6 / 7 dejan los knobs de la pista en su página; el del sonido que ya suena no hace nada {A6} |
| **Pad 14** | ★ [enlace estéreo](#entrada) con la pista siguiente (azul acero) {A6} |
| **Pad 15** | ★ la fuente de la [entrada](#entrada): las entradas (ámbar tenue), el retorno de reverb (crema), el de delay (melocotón); solo en una pista de entrada {A6} |
| **Pad 16** | ★ el gate de la [entrada](#entrada) (ámbar brillante / tenue); solo en una pista de entrada {A6} |

Shift + estos pads, como el original. El pad 19 está sobre el 27 (loop). Los loops muy cortos suenan a su longitud (en el original se repetían cada ~128 muestras).
""", [fig("Sample mode: pads 9 / 10 bajo los 1 / 2; el sonido de la pista en 5-8 y el enlace en 14; pad 19 sobre el loop.", "Sample mode: pads 9 / 10 under 1 / 2; the track's sound on 5-8 and the link on 14; pad 19 above loop.",
          pads={1: ("cyan", "tono +", "pitch +"), 2: ("cyan", "tono −", "pitch −"), 5: ("white", "sample", "sample"),
                6: ("lilac", "granular", "granular", True), 7: ("mint", "sinte", "synth", True), 8: ("amber", "entrada", "line in", True),
                9: ("cyan", "stretch +", "stretch +"), 10: ("cyan", "stretch −", "stretch −"), 14: ("steel", "enlace", "link", True),
                19: ("cyan", "de-click", "de-click"), 27: ("cyan", "loop", "loop", True)})]),
     ("Sample mode", "the Samples button twice", """
| Gesture | What it does |
|---|---|
| **Pads 1 / 2** (the original's) | fit the sample to the pattern by changing pitch; since Alpha 0.04 they switch the stretch off first |
| **Pads 9 / 10** | ★ the same with the **stretch** (Stock+ K7), without changing pitch: the next / previous length *(since Alpha 0.04)* |
| **Pad 19** | ★ the selected track's loop de-clicker (256-sample crossfade), on / off (blue bright / dim); on by default, saved with the project *(since Alpha 0.04)* |
| **Pads 5-8** | ★ the **track's sound**, one lit, the others dim: **5** sample (white), **6** [granular](#granular) (lilac), **7** [synth](#sinte) (mint), **8** [line input](#entrada) (amber). Pad 5 removes the granular, the synth or the input; 6 / 7 leave the track's knobs on their page; the pad of the sound already playing does nothing {A6} |
| **Pad 14** | ★ [stereo link](#entrada) with the next track (steel blue) {A6} |
| **Pad 15** | ★ the [input](#entrada)'s source: the inputs (dim amber), the reverb return (cream), the delay return (peach); only on an input track {A6} |
| **Pad 16** | ★ the [input](#entrada)'s gate (amber bright / dim); only on an input track {A6} |

Shift + these pads, as in the original. Pad 19 sits above pad 27 (loop). Very short loops play at their own length (the original repeated them every ~128 samples).
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
| **Con el proyecto** | Stock+, Granular, Sinte (ajustes y pistas), Envolvente, la fuente de la entrada, entrada de línea, enlace estéreo (con las desviaciones de la segunda pista), de-clicker por pista, escala propia, reglas de cadena, dinámicas / mutación / frecuencia por paso, marcas de Velocity, Micro Step, modo GM, reverb / delay / sidechain |
| **Ajustes del aparato** | canales de Program Change, modo del Thru, teclado al arpegiador, fusión USB, resonancia del filtro master, compresor |
| **Hasta apagar** | la página de knobs de cada pista, Project init (lo cargado o guardado), el modo cue, el metrónomo / cuenta atrás, Sample Rec pads 23 / 24 |

Lo propio del mod va en una zona del fichero de proyecto que el original no usa. Un proyecto de una versión anterior carga sin lo que esa versión no tenía. **Guarda copias de tus proyectos.**
"""), ("What is saved and where", "—", """
| Where | What |
|---|---|
| **With the project** | Stock+, Granular, Synth (settings and tracks), Envelope, the input's source, line input, stereo link (with the second track's offsets), per-track de-clicker, own scale, chain rules, per-step dynamics / mutation / frequency, Velocity marks, Micro Step, GM mode, reverb / delay / sidechain |
| **Device settings** | Program Change channels, Thru mode, keyboard into the arpeggiator, USB merge, master filter resonance, compressor |
| **Until power-off** | each track's knob page, Project init (what was loaded or saved), cue mode, metronome / count-in, Sample Rec pads 23 / 24 |

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
    ("Cuenta atrás", "Count-in", "un compás antes de grabar; Shift + Clear; desde 0.08 con el reloj de la música, también como esclavo", "a bar before recording; Shift + Clear; since 0.08 on the music's clock, also as a slave", "transporte", "0.0"),
    ("Metrónomo visual", "Visual metronome", "Clear destella en naranja en cada clic con el nivel del clic a 0 (K5 de Tempo / Swing)", "Clear flashes orange on each click with the click's level at 0 (Tempo / Swing K5)", "transporte", "0.08"),
    ("De-clicker de loops", "Loop de-clicker", "crossfade en el punto de loop; pad 19 de Sample mode, pad 23 de Sample Rec", "a crossfade at the loop point; Sample mode pad 19, Sample Rec pad 23", "samplemode", "0.04"),
    ("Dinámicas por paso", "Per-step dynamics", "velocity y retraso al azar dentro del paso; fila 3 de la probabilidad", "random velocity and delay within the step; probability row 3", "patternsettings", "0.0"),
    ("Enlace estéreo", "Stereo link", "una pista y la siguiente como un sonido estéreo; Sample mode, pad 14; desde 0.09 la segunda en desviaciones", "a track and the next as one stereo sound; Sample mode, pad 14; since 0.09 the second as offsets", "entrada", "0.04"),
    ("Entrada de línea", "Line input", "la entrada de audio como sonido de una pista; Sample mode, pads 8 / 16", "the audio input as a track's sound; Sample mode, pads 8 / 16", "entrada", "0.04"),
    ("FX hacia una entrada", "FX into an input", "el retorno que toma una pista de entrada deja el master; su realimentación, a la mitad", "a return taken by an input track leaves the master; its feedback, halved", "entrada", "0.09"),
    ("Envolvente por modo", "Envelope by play mode", "inicio, longitud, pendiente y → filtro del sinte y el granular; menú, pad 5", "start, length, slope and → filter of the synth and the granular; menu, pad 5", "envolvente", "0.06"),
    ("Retornos de FX como fuente", "FX returns as a source", "la reverb o el delay como sonido de una pista de entrada; Sample mode, pad 15", "the reverb or the delay as an input track's sound; Sample mode, pad 15", "entrada", "0.06"),
    ("Envolvente de tono", "Pitch envelope", "Stock+, K1 / K2", "Stock+, K1 / K2", "stockplus", "0.01"),
    ("Escala propia", "Own scale", "una escala por pista; Shift en la vista Note", "a scale per track; Shift in the Note view", "note", "0.0"),
    ("Fixed Recording con reloj externo", "Fixed Recording with external clock", "la duración al tempo del reloj MIDI que llega", "the length at the incoming MIDI clock's tempo", "samplerec", "0.02"),
    ("Frecuencia por paso", "Per-step frequency", "el paso suena una de cada n pasadas", "the step plays one pass in n", "patternsettings", "0.0"),
    ("Fusión USB", "USB merge", "el DIN In también por USB; Advanced Setup, pad 23", "DIN In also over USB; Advanced Setup, pad 23", "setup", "0.04"),
    ("Gate por pulsación", "Gate by press", "el golpe dura lo que mantienes el pad; Micro Step, pad 32", "the hit lasts as long as the pad is held; Micro Step, pad 32", "velocity", "0.04"),
    ("General MIDI", "General MIDI", "las pistas por el canal 10 con su nota GM; Setup, pad 22", "the tracks on channel 10 with their GM note; Setup, pad 22", "setup", "0.04"),
    ("Grabación estéreo", "Stereo recording", "L y R en dos huecos; Sample Rec, pad 24", "L and R into two slots; Sample Rec, pad 24", "samplerec", "0.04"),
    ("Granular", "Granular", "el motor granular en hasta 4 pistas; Sample mode pad 6, menú pad 3", "the granular engine on up to 4 tracks; Sample mode pad 6, menu pad 3", "granular", "0.04"),
    ("Inicio y longitud en el granular", "Start and length on the granular", "el inicio del original se suma a la posición, la longitud estrecha la zona", "the original's start adds to the position, the length narrows the zone", "granular", "0.09"),
    ("Longitud fija", "Fixed length", "los golpes a mano con una longitud; Micro Step, pad 31", "hand-entered hits with a set length; Micro Step, pad 31", "velocity", "0.04"),
    ("LFO de tono", "Pitch LFO", "Stock+, K3 / K4; libre o a tempo", "Stock+, K3 / K4; free or synced", "stockplus", "0.01"),
    ("Marcas de Velocity", "Velocity marks", "en el paso marcado los parámetros vuelven a Project init (hasta 0.08, al knob); Shift + paso", "on a marked step the parameters go back to Project init (up to 0.08, to the knob); Shift + step", "velocity", "0.04"),
    ("Vista de automatización", "Automation view", "los pasos con automatización de knobs en amarillo, y escucharlos; Velocity + Shift, o Velocity otra vez (fija)", "steps with knob automation in yellow, and listening to them; Velocity + Shift, or Velocity again (latched)", "velocity", "0.09"),
    ("Borrar la automatización de un paso", "Clear a step's automation", "Clear + paso en Velocity", "Clear + step in Velocity", "velocity", "0.09"),
    ("Snapshot", "Snapshot", "los knobs movidos, a un paso; Record mantenido + paso", "the moved knobs into a step; Record held + step", "velocity", "0.09"),
    ("Project init", "Project init", "la voz de la pista como se cargó o guardó; menú, pad 8 (rojo)", "the track's voice as loaded or saved; menu, pad 8 (red)", "menu", "0.09"),
    ("Menú de pista", "Track menu", "tocar el botón de la pista elegida (se queda abierto) o mantener el de una pista", "tap the selected track's button (stays open) or hold a track's button", "menu", "0.04"),
    ("Metrónomo", "Metronome", "cuatro estados con Shift + Clear", "four states with Shift + Clear", "transporte", "0.0"),
    ("Modo cue", "Cue mode", "mezcla a la izquierda, cue a la derecha; Mixer, panoramas, Shift + knob", "mix on the left, cue on the right; Mixer, pan, Shift + knob", "mixer", "0.04"),
    ("Mute al compás", "Mute at the bar", "Shift + pad de pista en el Mixer", "Shift + track pad in the Mixer", "mixer", "0.0"),
    ("Mutación del sample", "Sample mutation", "a veces suena el vecino; fila 4 de la probabilidad", "sometimes the neighbour plays; probability row 4", "patternsettings", "0.0"),
    ("Nivel a 100 / 0", "Level to 100 / 0", "Shift + knob en los niveles del Mixer", "Shift + knob on the Mixer's levels", "mixer", "0.0"),
    ("Nudge", "Nudge", "el primer paso pasa a ser el 1; pad 26 de Pattern Settings", "the first step becomes step 1; Pattern Settings pad 26", "patternsettings", "0.0"),
    ("Órdenes fractal / deconstruido", "Fractal / deconstructed orders", "pads 27 / 28 de Pattern Settings", "Pattern Settings pads 27 / 28", "patternsettings", "0.0"),
    ("Página Stock+", "Stock+ page", "ocho knobs más por pista; menú, pad 2; desde 0.07 también en el granular y el sinte", "eight more knobs per track; menu, pad 2; since 0.07 on the granular and the synth too", "stockplus", "0.01"),
    ("Program Change", "Program Change", "canales de escucha y salida; Setup, pads 29 / 30", "listen and send channels; Setup, pads 29 / 30", "setup", "0.0"),
    ("Repetir la escena", "Repeat the scene", "la escena actual 1-8 veces; Mixer, Shift + pads 9-16", "the current scene 1-8 times; Mixer, Shift + pads 9-16", "mixer", "0.0"),
    ("Reset de knobs de pista", "Track knobs reset", "Clear + botón de la pista", "Clear + the track's button", "pista", "0.0"),
    ("Resonancia master", "Master resonance", "Shift + ▲ / ▼ en la vista FX", "Shift + ▲ / ▼ in the FX view", "fx", "0.0"),
    ("Ring mod", "Ring mod", "Stock+, K5 (Shift: la frecuencia)", "Stock+, K5 (Shift: the frequency)", "stockplus", "0.02"),
    ("Scan", "Scan", "mueve el inicio de cada nota o del loop; Stock+, K8", "moves each note's or the loop's start; Stock+, K8", "stockplus", "0.02"),
    ("Sidechain por knobs", "Sidechain on the knobs", "K1-K4 de la vista Sidechain", "Sidechain view K1-K4", "fx", "0.0"),
    ("Sinte", "Synth", "dos osciladores con FM en hasta 4 pistas; Sample mode pad 7, menú pad 4", "two oscillators with FM on up to 4 tracks; Sample mode pad 7, menu pad 4", "sinte", "0.05"),
    ("Morph y unísono del sinte", "Synth morph and unison", "el inicio y la longitud del original en el sinte", "the original's start and length on the synth", "sinte", "0.09"),
    ("Stretch", "Stretch", "más lento o rápido sin cambiar el tono; Stock+ K7, Sample mode pads 9 / 10", "slower or faster without changing pitch; Stock+ K7, Sample mode pads 9 / 10", "stockplus", "0.02"),
    ("Teclado externo al arpegiador", "External keyboard into the arpeggiator", "Advanced Setup, pad 22", "Advanced Setup, pad 22", "setup", "0.04"),
    ("Thru: Out 2 / Merge / Filter", "Thru: Out 2 / Merge / Filter", "Duplicate en Advanced Setup", "Duplicate in Advanced Setup", "setup", "0.0"),
    ("Tipo de filtro (24 dB, comb)", "Filter type (24 dB, comb)", "Stock+, Shift + K6", "Stock+, Shift + K6", "stockplus", "0.02"),
    ("Waveshaper", "Waveshaper", "suave, duro, plegado o bitcrush en el granular y el sinte; Stock+, K7 (Shift: el tipo)", "soft, hard, fold or bitcrush on the granular and the synth; Stock+, K7 (Shift: the type)", "stockplus", "0.07"),
    ("Distorsión en granular y sinte", "Distortion on granular and synth", "el knob de distorsión del original también en ellos", "the original's distortion knob on them too", "menu", "0.07"),
    ("Umbral del compresor", "Compressor threshold", "K5 de la vista Sidechain", "Sidechain view K5", "fx", "0.01"),
    ("Envíos de FX en los knobs", "FX sends on the knobs", "▼ / ▲ en la vista FX", "▼ / ▲ in the FX view", "fx", "0.0"),
]

UI = dict(es=dict(title=f"Circuit Remix {VERSION} — manual", how="Cómo se llega:", toc="Índice", glossary="Glosario de funciones",
                  gl_cols=("Función", "Qué es / gesto", "Capítulo", "Desde"), other='[English](MANUAL_EN.md) · [versión ilustrada](manual/index.html)',
                  other_html='<p class="lang"><a href="en.html">English</a> · <a href="../MANUAL.md">texto</a></p>',
                  cover="Manual por vistas", warn="> ⚠️ **Alpha 0.09 es experimental:** lo nuevo (la automatización, los modos en Sample mode, el FX hacia una entrada, las desviaciones del enlace estéreo, el morph y el unísono del sinte) y casi todo desde Alpha 0.04 se ha comprobado sobre todo en emulación. Para tocar en serio, Alpha 0.03. **Haz una copia de tu tarjeta SD.**",
                  intro="Circuit Remix en el Circuit Rhythm (firmware 2.0.1, build 5706), vista por vista.", md="MANUAL.md", html="index.html", lang="es",
                  footer="Circuit Remix — MIT. Sin código de Novation."),
          en=dict(title=f"Circuit Remix {VERSION} — manual", how="How to get there:", toc="Contents", glossary="Glossary of functions",
                  gl_cols=("Function", "What it is / gesture", "Chapter", "Since"), other='[Español](MANUAL.md) · [illustrated version](manual/en.html)',
                  other_html='<p class="lang"><a href="index.html">Español</a> · <a href="../MANUAL_EN.md">text</a></p>',
                  cover="Manual by views", warn="> ⚠️ **Alpha 0.09 is experimental:** what's new (the automation, the modes in Sample mode, an FX into an input, the stereo link's offsets, the synth's morph and unison) and most things since Alpha 0.04 have mostly been checked in emulation. For serious playing, Alpha 0.03. **Back up your SD card.**",
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
    return t[0], t[1], t[2].strip("\n").replace("{A6}", A if lang == "es" else A_EN)


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
