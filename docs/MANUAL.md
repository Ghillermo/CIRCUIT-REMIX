# Circuit Remix Alpha 0.06 — manual

[English](MANUAL_EN.md) · [versión ilustrada](manual/index.html)

> ⚠️ **Alpha 0.06 es experimental:** lo nuevo (la envolvente, la entrada desde los retornos de FX y casi todo lo de Alpha 0.04 / 0.05) se ha comprobado sobre todo en emulación. Para tocar en serio, Alpha 0.03. **Haz una copia de tu tarjeta SD.**

Circuit Remix en el Circuit Rhythm (firmware 2.0.1, build 5706), vista por vista.

## Índice

**0. Introducción**

- [0.1 Cómo leer este manual](#leer)
- [0.2 El código de colores](#colores)
- [0.3 Instalar y volver al original](#instalar)

**1. En cualquier vista**

- [1.1 Transporte, metrónomo y cuantizar](#transporte)

**2. Vistas de pista**

- [2.1 El botón de pista](#pista)
- [2.2 El menú de pista](#menu)
- [2.3 Página Stock+](#stockplus)
- [2.4 Página Granular](#granular)
- [2.5 Página Sinte](#sinte)
- [2.6 Página Envolvente](#envolvente)
- [2.7 Entrada de línea y enlace estéreo](#entrada)
- [2.8 Vista Note](#note)

**3. Pasos y patrón**

- [3.1 Velocity y Micro Step](#velocity)
- [3.2 Pattern Settings y probabilidad](#patternsettings)
- [3.3 Patterns: cadenas](#patterns)

**4. Samples**

- [4.1 Sample mode](#samplemode)
- [4.2 Sample Rec](#samplerec)

**5. Mezcla y efectos**

- [5.1 Mixer](#mixer)
- [5.2 FX y Sidechain](#fx)

**6. Proyectos y ajustes**

- [6.1 Projects y Packs](#projects)
- [6.2 Setup y Advanced Setup](#setup)

**A. Apéndice**

- [A.1 Qué se guarda y dónde](#guardado)
- [A.2 MIDI](#midi)

- [Glosario de funciones](#glosario)

## 0. Introducción

<a id="leer"></a>
### 0.1 Cómo leer este manual

Cada capítulo es una vista del aparato: cómo se llega, qué hacen sus pads, knobs y botones con Circuit Remix. Todo lo demás funciona como en el firmware original de Novation (consulta su manual); los gestos nuevos son combinaciones que en el original no hacían nada o repetían el gesto sin modificador.

- **Pads 1-32** de izquierda a derecha y de arriba abajo: fila 1 = 1-8, fila 2 = 9-16, fila 3 = 17-24, fila 4 = 25-32.
- **K1-K8** = los 8 knobs. **▲ / ▼** = los botones de flecha.
- **Mantener** un botón = pulsarlo y no soltarlo; **A + B** = B con A mantenido.
- **★** = exclusiva de Circuit Remix (no está en CIRCUIT-HACKS).
- **(desde Alpha 0.0x)** = la versión que trajo la función. Lo marcado *(Alpha 0.06)* es nuevo o cambia en esta versión.
- Al final, el **[glosario](#glosario)**: una entrada por función, con su vista y su gesto.

<a id="colores"></a>
### 0.2 El código de colores

Desde Alpha 0.05 todo lo nuevo sigue unas reglas fijas *(desde Alpha 0.05)*:

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
| Envolvente | rosa |

<a id="instalar"></a>
### 0.3 Instalar y volver al original

1. Descarga `rm_uploader.zip`, descomprímelo y abre `rm_uploader.html` en Chrome o Edge.
2. Aporta el firmware oficial 2.0.1 (build 5706) del Circuit Rhythm: el instalador comprueba su SHA-256 y lo parchea en tu ordenador.
3. Elige la versión y envíala al aparato por USB.

**Versiones S** (A0.06S): sin las funciones que crean, cambian o borran ficheros de la tarjeta por su cuenta (copiar proyectos, borrar packs, copiar samples). La más segura para tu SD.

**Volver al firmware oficial:** mantén **Sample Rec + Samples + Note** al encender (modo bootloader de Novation) y envía el oficial con el instalador («Oficial») o con Novation Components. Haz siempre una copia de tu tarjeta SD.

## 1. En cualquier vista

<a id="transporte"></a>
### 1.1 Transporte, metrónomo y cuantizar

*Cómo se llega:* en cualquier vista

| Gesto | Qué hace |
|---|---|
| **Shift + Clear** | metrónomo en cuatro estados; con Shift, el LED de Clear: rojo = sin metrónomo, verde = metrónomo, magenta = solo cuenta atrás, cian = las dos *(desde Alpha 0.0)* |
| **Record armado + Play** (parado, con cuenta atrás) | un compás de clics al tempo y arranca grabando (Record parpadea); Play durante la cuenta la cancela |
| **Shift + Play** (parado) | el del original: sigue desde donde se paró; con cuenta atrás, la cuenta y luego sigue |
| **Shift + Play** (sonando) | cuantiza el patrón de la pista elegida: los micropasos 2-3 al comienzo de su paso, 4-6 al del siguiente; los redobles se quedan. LED de Play con Shift: amarillo; verde tras cuantizar; rojo = nada que cuantizar *(desde Alpha 0.0)* |

La cuenta atrás no se guarda: al encender vuelve a «sin cuenta atrás».

**Arreglos del original** (desde Alpha 0.04): la reproducción empieza antes (≈ 10 ms de Play al primer sonido; el original ≈ 18 ms), las notas de un mismo paso suenan juntas, no se pierden notas con muchas pistas en el mismo paso y el reloj no tropieza al guardar un sample.

## 2. Vistas de pista

<a id="pista"></a>
### 2.1 El botón de pista

*Cómo se llega:* las vistas de pista (Samples, Note, Velocity, Gate, Pattern Settings…)

| Gesto | Qué hace |
|---|---|
| **Clear + botón de la pista** | ★ sus knobs por defecto y su automatización borrada; el resto (nivel, panorama, envíos, sidechain, sample) como al cargar el proyecto *(desde Alpha 0.0)* |
| **Duplicate + pista A, luego pista B** | ★ B recibe los parámetros y el sample de A; con Duplicate mantenido, más pistas *(desde Alpha 0.0)* |
| **Mantener el botón de la pista** (¼ s) | abre el [menú de pista](#menu) en los pads *(desde Alpha 0.04)* |
| **Pads de sample mantenidos** (arpegiador encendido) | ★ arpegio de los samples mantenidos (también uno solo): cada golpe cambia el sample, con la velocity de su pad; con Record y Play se graba *(desde Alpha 0.0)* |

Pulsar el botón sin mantenerlo elige la pista, como en el original. Desde el Mixer, Clear + pista hace lo del original. El arpegiador se enciende en [Pattern Settings](#patternsettings) (Shift + pad 25).

<a id="menu"></a>
### 2.2 El menú de pista

*Cómo se llega:* toca el botón de la pista elegida (el menú se queda abierto hasta que eliges algo o lo vuelves a tocar), o mantén el botón de cualquier pista (el menú solo mientras lo mantienes)

Los pads se convierten en el menú de esa pista *(Alpha 0.06)*:

| Pad | Qué hace |
|---|---|
| **1** | página **stock** de los knobs (la del original) |
| **2** | página **[Stock+](#stockplus)** (con un sample) |
| **3** | página **[Granular](#granular)** (con el granular) |
| **4** | página **[Sinte](#sinte)** (con el sinte) |
| **5** | página **[Envolvente](#envolvente)** (con el sinte o el granular) *(Alpha 0.06)* |
| **9** | ★ **[enlace estéreo](#entrada)** con la pista siguiente, sí / no |
| **11** | el **granular** de la pista, sí / no (hasta 4 pistas); encendido, su página |
| **12** | ★ el **sinte** de la pista, sí / no (hasta 4 pistas); encendido, su página |
| **13** | ★ la **[entrada de línea](#entrada)** como sonido de la pista, sí / no |
| **14** | el gate de la entrada: tenue = siempre suena, brillante = solo con sus notas, por el VCA y el filtro de la pista (oscuro si la pista no es de entrada) |
| **15** | la fuente de la entrada: las entradas (ámbar) → el retorno de reverb (crema) → el de delay (melocotón) *(Alpha 0.06)* |

- **Abrirlo:** un toque en el botón de la pista que ya está elegida lo deja abierto; se cierra al soltar un pad del menú, al tocar otra vez el botón o al pulsar cualquier otro botón. Mantener el botón de una pista (¼ s) lo abre solo mientras lo mantienes, como los botones de vista del original.
- Fila 1, las **páginas** de la pista: solo las de su sonido (sample: stock y Stock+; granular: stock, Granular y Envolvente; sinte: stock, Sinte y Envolvente; entrada: stock); las demás, oscuras. Brillante = la que se ve. **Mantener** un pad de página (½ s o más) la muestra solo hasta que lo sueltas y vuelve la anterior.
- Fila 2, debajo, los **conmutadores**: brillante = encendido, tenue = apagado. **El sonido de la pista solo cambia aquí:** sample, granular, sinte o entrada, uno por pista; poner uno quita los otros.
- Con el granular o el sinte, la página stock deja los knobs del original (filtro, envolvente, tono, nivel…) actuando sobre ellos.

En Alpha 0.04 el menú era: 1-3 páginas, 4 granular, 5 / 6 entrada y gate, 7 enlace.

<a id="stockplus"></a>
### 2.3 Página Stock+

*Cómo se llega:* menú de pista, pad 2, en una pista con un sample (el botón de la pista parpadea en azul cielo)

La página Stock+ es por pista y se queda hasta apagar *(desde Alpha 0.01; K5-K8 desde Alpha 0.02)*. Actúa sobre el sample de la pista.

| Knob | Solo | Con Shift |
|---|---|---|
| K1 | ★ envolvente de tono: centro = nada; derecha = cada golpe empieza más agudo, izquierda más grave (hasta ±24 semitonos) | ajuste fino |
| K2 | ★ lo que tarda en volver a la nota (5 ms - 4 s) | ajuste fino |
| K3 | ★ velocidad del LFO de tono: centro = apagado; derecha = libre (0,05-30 Hz); izquierda = a tempo, de 8 compases junto al centro a 1/16T en el extremo *(desde Alpha 0.05)* | ajuste fino |
| K4 | ★ profundidad del LFO de tono (0-24 semitonos) | ajuste fino |
| K5 | ★ cantidad del ring mod | ★ su frecuencia (20 Hz-5 kHz) |
| K6 | ★ pitch follow: el corte del paso bajo sigue a la nota | ★ tipo de filtro sobre los knobs de filtro del original: **stock** (blanco), **24 dB** (naranja), **comb** (lavanda) |
| K7 | ★ **stretch**: más lento (izquierda, hasta 0,25×) o más rápido (derecha, hasta 4×) sin cambiar el tono; centro = el original | ★ bitcrush |
| K8 | ★ velocidad del scan (mueve el inicio de cada nota; en un loop, el inicio del loop en cada vuelta): centro = quieto; derecha = libre (0,05-20 Hz); izquierda = a tempo, más rápido hacia el extremo *(desde Alpha 0.05)* | ★ su profundidad |

- **LEDs:** azul cielo con el brillo según el valor (K1, K3, K7 y K8: la distancia al centro); K6 en el color de su tipo de filtro. Con Shift, K5-K8 enseñan su segunda capa.
- **Clear + knob:** su valor por defecto (en K5-K8, las dos capas).
- **Se guarda con el proyecto.** En proyectos de Alpha 0.04, la mitad a tempo de K3 y K8 va ahora al revés.
- **El stretch** reparte el sample en granos de unos 43 ms que se mantienen en fase (WSOLA): a 0,5× suena muy bien; a 0,25× la batería puede sonar con clics.

<a id="granular"></a>
### 2.4 Página Granular

*Cómo se llega:* menú de pista, pad 11 (pone el granular y su página) o pad 3 (su página) (el botón de la pista parpadea en lila)

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
| K8 | ventana (rectángulo → triángulo → percusiva) | gate, encendido / apagado: tenue = siempre suena (drone), brillante = lo abren las notas *(desde Alpha 0.05)* |

Lila con el brillo según el valor (K4, K5 y Shift + K5: la distancia al centro). Clear + knob = por defecto. Se guarda con el proyecto.

<a id="sinte"></a>
### 2.5 Página Sinte

*Cómo se llega:* menú de pista, pad 12 (pone el sinte y su página) o pad 4 (su página) (el botón de la pista parpadea en menta)

★ Un sinte monofónico de dos osciladores en el DSP del master, como sonido de cualquier pista *(desde Alpha 0.05)*. **Hasta 4 pistas con sinte.** Las notas le llegan como a un sample (pads, vista Note, secuencia, MIDI).

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

<a id="envolvente"></a>
### 2.6 Página Envolvente

*Cómo se llega:* menú de pista, pad 5, en una pista con el sinte o el granular (el botón de la pista parpadea en rosa)

★ La envolvente del sinte y del granular, según el **modo de reproducción** de la pista (Sample mode, pads 25 / 26 / 27) *(Alpha 0.06)*:

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

<a id="entrada"></a>
### 2.7 Entrada de línea y enlace estéreo

*Cómo se llega:* menú de pista, pads 13 / 14 / 15 y 9

**Entrada de línea** (pad 13; desde Alpha 0.04): la entrada de audio suena como el sonido de la pista, con su nivel, panorama, envíos, filtro y envolvente.
- Una pista de entrada: L + R. Dos: la de número menor es L, la mayor R. En una tercera, sale la primera puesta.
- **Pad 14, el gate:** tenue = siempre suena; brillante = solo mientras suenan sus notas, por el VCA y el filtro de la pista (paso bajo, paso alto, resonancia; el filtro desde Alpha 0.06).
- **Pad 15, la fuente** (Alpha 0.06): las entradas (ámbar) → el **retorno de reverb** (crema) → el **de delay** (melocotón), por turnos; cada pista de entrada la suya. El retorno llega un bloque tarde (0,67 ms). Ojo: mandar esa pista a su propia reverb o delay realimenta.

**Enlace estéreo** (pad 9; desde Alpha 0.04): la pista (izquierda, su sample) y la siguiente (derecha, el sample siguiente) suenan juntas con los parámetros y las notas de la primera. Pad 9 en cualquiera de las dos = deshacer. En la pista 8 sola, oscuro. Sin enlazar quedan el LFO y el scan libres de Stock+ y el WSOLA del stretch.

Las dos se guardan con el proyecto.

<a id="note"></a>
### 2.8 Vista Note

*Cómo se llega:* botón Note

| Gesto | Qué hace |
|---|---|
| **Teclas mantenidas** (arpegiador encendido) | ★ arpegio de las notas mantenidas sobre el sample de la pista; con Record y Play se graba *(desde Alpha 0.0)* |
| **Shift mantenido** | ★ editor de la **escala propia de la pista** *(desde Alpha 0.0)* |

**El editor:** los 32 pads son dos octavas de piano desde la tónica (fila 4 = las blancas de la octava de abajo, el pad 25 = la tónica; fila 3 = sus negras; filas 2 / 1 = la octava de arriba). Cada tecla enciende o apaga su grado (7 como máximo); la más alta es el **periodo**: la tónica de la siguiente iteración (la octava u otra, hasta 24 semitonos). Tónica blanca, grados verdes, periodo azul.

Al soltar Shift, el teclado toca la escala: una iteración por fila (dos si tiene 4 notas o menos); ▲ / ▼ mueven una fila. Sin teclas, vuelve el piano del original. Se guarda con el proyecto.

## 3. Pasos y patrón

<a id="velocity"></a>
### 3.1 Velocity y Micro Step

*Cómo se llega:* botón Velocity; Micro Step = Shift + Gate

| Vista | Gesto | Qué hace |
|---|---|---|
| Velocity | **Shift + paso** | marca el paso: al sonar, la automatización no suena ahí y los parámetros automatizados vuelven a la posición de su knob. Con Shift, los pasos marcados en rojo; los demás, como los dibuja la vista *(desde Alpha 0.05)* *(desde Alpha 0.04)* |
| Micro Step | **pad 31** | longitud fija: apagada → el selector en los pads 17-32 (1-16 pasos; elegir una la enciende); encendida → apagada (naranja brillante / tenue) *(desde Alpha 0.04)* |
| Micro Step | **pad 32** | gate por pulsación: el golpe dura lo que mantienes el pad del paso; mantener un paso vacío 300 ms o más también lo crea (verde brillante / tenue) *(desde Alpha 0.04)* |

Encender uno de los dos de Micro Step apaga el otro. Con cualquiera, un golpe introducido a mano en los pasos toma esa longitud.

<a id="patternsettings"></a>
### 3.2 Pattern Settings y probabilidad

*Cómo se llega:* botón Pattern Settings (dos veces: la vista de probabilidad, modo 1)

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

<a id="patterns"></a>
### 3.3 Patterns: cadenas

*Cómo se llega:* botón Patterns

| Gesto | Qué hace |
|---|---|
| **Shift + botón de página de arriba** | modo cadena (verde) *(desde Alpha 0.0)* |
| En el modo: **un patrón** (A), **otra vez** (n + 1 pasadas), **otro** (B), **otro más** (C) | regla «n veces A, luego B; la vez siguiente, C» (AAB AAC …) |
| **Clear + patrón** | sin regla |
| **Shift + botón de página de abajo** | fuera del modo: la cadena del original |

Cada escena recuerda el modo con que se guardó. Las reglas se guardan con el proyecto.

## 4. Samples

<a id="samplemode"></a>
### 4.1 Sample mode

*Cómo se llega:* botón Samples dos veces

| Gesto | Qué hace |
|---|---|
| **Pads 1 / 2** (del original) | ajustan el sample al patrón cambiando el tono; desde Alpha 0.04 apagan antes el stretch |
| **Pads 9 / 10** | ★ lo mismo con el **stretch** (K7 de Stock+), sin cambiar el tono: la longitud siguiente / la anterior *(desde Alpha 0.04)* |
| **Pad 19** | ★ de-clicker del loop de la pista elegida (crossfade de 256 muestras), encendido / apagado (azul brillante / tenue); encendido por defecto, se guarda con el proyecto *(desde Alpha 0.04)* |

El pad 19 está sobre el 27 (loop). Los loops muy cortos suenan a su longitud (en el original se repetían cada ~128 muestras).

<a id="samplerec"></a>
### 4.2 Sample Rec

*Cómo se llega:* botón Sample Rec

| Gesto | Qué hace |
|---|---|
| **Pad 23** | ★ de-clicker de los loops de todas las pistas, encendido / apagado (encendido al arrancar) *(desde Alpha 0.04)* |
| **Pad 24** | ★ **grabación estéreo**: L en el hueco elegido, R en el siguiente (que debe estar vacío; si no, solo el primero, en mono); apagada al arrancar *(desde Alpha 0.04)* |
| **Duplicate + hueco A, Duplicate + hueco B** | ★ copia el sample A en B, también desde otro pack (no en las versiones S) *(desde Alpha 0.01)* |
| **Fixed Recording** (pads 17-21, del original) | con reloj MIDI externo, usa el tempo del reloj que llega *(desde Alpha 0.02)* |

**Copiar un sample** (transporte parado): Duplicate + hueco con sample (parpadea en amarillo); Duplicate + hueco B (de este pack o, tras cargar otro, de ese): verde ~1,5 s y B suena al momento. Si B tiene sample, parpadea en blanco y Duplicate + B otra vez antes de ~5 s lo sobrescribe. Rojo = no se ha podido (memoria llena, aparato ocupado o pack interno).

## 5. Mezcla y efectos

<a id="mixer"></a>
### 5.1 Mixer

*Cómo se llega:* botón Mixer

| Gesto | Qué hace |
|---|---|
| **Shift + pad de pista** (fila 1) | mute de esa pista en el compás siguiente (el pad parpadea; otra vez = cancelar; parado, al momento) *(desde Alpha 0.0)* |
| **Shift + knob** (página de niveles) | derecha = nivel 100; izquierda = 0 (grabando, queda como automatización) *(desde Alpha 0.0)* |
| **Shift + pads 9-16** | la escena actual se repite 1-8 veces; sonando, con Shift, la vuelta que suena en blanco *(desde Alpha 0.0)* |
| **Página de panoramas, Shift + knob** a la derecha / izquierda | ★ **modo cue** sí / no (botón 19 en rosa): la mezcla por la salida izquierda, el cue por la derecha *(desde Alpha 0.04)* |
| **Modo cue, knob** | el envío al cue de su pista (knobs en rosa, brillo = envío); una pista silenciada con envío suena solo en el cue; Clear + knob = 0 |

El pad 9 sin Shift sigue siendo el Mute Recall del original. El modo cue no se guarda.

<a id="fx"></a>
### 5.2 FX y Sidechain

*Cómo se llega:* botón FX; Sidechain = Shift + FX

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

## 6. Proyectos y ajustes

<a id="projects"></a>
### 6.1 Projects y Packs

*Cómo se llega:* botón Projects (dos veces: Packs)

**Copiar un proyecto** (no en las versiones S; desde Alpha 0.0), con el transporte parado:
1. **Duplicate + pad con proyecto (A)**: parpadea en amarillo.
2. **Duplicate + pad vacío (B)**: copia A en B (verde ~1,5 s). B puede estar en otro pack: elige A, carga otro pack y Duplicate + un pad vacío.
3. **Duplicate + un pad con proyecto**: parpadea en blanco (pregunta); **Duplicate + el mismo pad** antes de ~5 s lo sobrescribe.

Copia el proyecto **tal como está guardado** y no toca el cargado. (Save + pad, del original, guarda el cargado con sus cambios.)

**Borrar un pack** (vista Packs; no en las versiones S; desde Alpha 0.01): **Clear + pad del pack** = pregunta (parpadea en rojo ~5 s); **Clear + el mismo pad** = lo borra de la tarjeta (verde ~1,5 s). Nunca el cargado, el interno ni un hueco vacío.

El mod nunca escribe en el pack de la memoria interna (rojo + LED de Save rojo).

<a id="setup"></a>
### 6.2 Setup y Advanced Setup

*Cómo se llega:* Shift + Save (Setup); Advanced Setup como en el original

| Vista | Gesto | Qué hace |
|---|---|---|
| Advanced | **Duplicate** | la toma Thru: **Thru** (verde) → **Out 2** (rojo tenue) → **Merge** (amarillo: MIDI In + el MIDI del aparato) → **Filter** (azul: MIDI In menos los canales del aparato) *(desde Alpha 0.0)* |
| Setup | **Pad 29 / 30** (la primera vez) | canal de escucha / de salida de **Program Change** en los pads 1-16; el pad otra vez = PGM Rx / Tx sí / no *(desde Alpha 0.0)* |
| Setup | **Pad 22** | ★ **modo General MIDI** del proyecto (verde brillante / tenue): las pistas salen por el canal 10 con su nota GM; las notas GM del canal 10 tocan su pista *(desde Alpha 0.04)* |
| Setup | **K1-K8**, con el modo GM | la nota GM de cada pista (35-81, dos clics por nota; cada nota nueva suena una vez). De fábrica: 36, 38, 42, 46, 39, 37, 45, 49 |
| Advanced | **Pad 22** | ★ teclado externo al arpegiador: las notas que entran por el canal de una pista con el arpegiador encendido se arpegian (verde brillante / tenue) *(desde Alpha 0.04)* |
| Advanced | **Pad 23** | ★ fusión USB: lo que entra por el DIN In sale también por USB (verde brillante / tenue) *(desde Alpha 0.04)* |

Todo se guarda en los ajustes del aparato, salvo el modo GM, que va con el proyecto. Si los dos canales de Program Change son distintos, el recibido se reenvía por el de salida.

## A. Apéndice

<a id="guardado"></a>
### A.1 Qué se guarda y dónde

| Dónde | Qué |
|---|---|
| **Con el proyecto** | Stock+, Granular, Sinte (ajustes y pistas), Envolvente, la fuente de la entrada, entrada de línea, enlace estéreo, de-clicker por pista, escala propia, reglas de cadena, dinámicas / mutación / frecuencia por paso, marcas de Velocity, Micro Step, modo GM, reverb / delay / sidechain |
| **Ajustes del aparato** | canales de Program Change, modo del Thru, teclado al arpegiador, fusión USB, resonancia del filtro master, compresor |
| **Hasta apagar** | la página de knobs de cada pista, el modo cue, el metrónomo / cuenta atrás, Sample Rec pads 23 / 24 |

Lo propio del mod va en una zona del fichero de proyecto que el original no usa. Un proyecto de una versión anterior carga sin lo que esa versión no tenía. **Guarda copias de tus proyectos.**

<a id="midi"></a>
### A.2 MIDI

Los knobs nuevos mueven parámetros del original con su MIDI de siempre (guía del programador del Circuit Rhythm): sidechain NRPN 1:1-1:4 (canal de la pista); reverb NRPN 1:18-1:20; delay NRPN 1:6-1:11; resonancia master CC 71; compresor NRPN 1:22-1:26. Las páginas Stock+, Granular y Sinte aún no tienen MIDI.

<a id="glosario"></a>
## Glosario de funciones

| Función | Qué es / gesto | Capítulo | Desde |
|---|---|---|---|
| **Arpegiador de notas** | arpegia las teclas mantenidas en la vista Note | [2.8 Vista Note](#note) | Alpha 0.0 |
| **Arpegiador de samples** | arpegia los pads de sample mantenidos; Shift + pad 25 de Pattern Settings lo enciende | [2.1 El botón de pista](#pista) | Alpha 0.0 |
| **Bitcrush** | Stock+, Shift + K7 | [2.3 Página Stock+](#stockplus) | Alpha 0.02 |
| **Borrar un pack** | Clear + pack dos veces en Packs | [6.1 Projects y Packs](#projects) | Alpha 0.01 |
| **Cadenas con reglas** | patrones que se encadenan «n veces A, luego B» | [3.3 Patterns: cadenas](#patterns) | Alpha 0.0 |
| **Compresor master** | umbral, soft clip, ataque y release en la vista Sidechain | [5.2 FX y Sidechain](#fx) | Alpha 0.0 |
| **Copiar parámetros de pista** | Duplicate + pista A, pista B | [2.1 El botón de pista](#pista) | Alpha 0.0 |
| **Copiar proyectos** | Duplicate + A, Duplicate + B en Projects, también a otro pack | [6.1 Projects y Packs](#projects) | Alpha 0.0 |
| **Copiar samples** | Duplicate + A, Duplicate + B en Sample Rec | [4.2 Sample Rec](#samplerec) | Alpha 0.01 |
| **Cuantizar** | Shift + Play sonando | [1.1 Transporte, metrónomo y cuantizar](#transporte) | Alpha 0.0 |
| **Cuenta atrás** | un compás antes de grabar; Shift + Clear | [1.1 Transporte, metrónomo y cuantizar](#transporte) | Alpha 0.0 |
| **De-clicker de loops** | crossfade en el punto de loop; pad 19 de Sample mode, pad 23 de Sample Rec | [4.1 Sample mode](#samplemode) | Alpha 0.04 |
| **Dinámicas por paso** | velocity y retraso al azar dentro del paso; fila 3 de la probabilidad | [3.2 Pattern Settings y probabilidad](#patternsettings) | Alpha 0.0 |
| **Enlace estéreo** | una pista y la siguiente como un sonido estéreo; menú, pad 9 | [2.7 Entrada de línea y enlace estéreo](#entrada) | Alpha 0.04 |
| **Entrada de línea** | la entrada de audio como sonido de una pista; menú, pads 13 / 14 | [2.7 Entrada de línea y enlace estéreo](#entrada) | Alpha 0.04 |
| **Envolvente de tono** | Stock+, K1 / K2 | [2.3 Página Stock+](#stockplus) | Alpha 0.01 |
| **Envolvente por modo** | inicio, longitud, pendiente y → filtro del sinte y el granular; menú, pad 5 | [2.6 Página Envolvente](#envolvente) | Alpha 0.06 |
| **Envíos de FX en los knobs** | ▼ / ▲ en la vista FX | [5.2 FX y Sidechain](#fx) | Alpha 0.0 |
| **Escala propia** | una escala por pista; Shift en la vista Note | [2.8 Vista Note](#note) | Alpha 0.0 |
| **Fixed Recording con reloj externo** | la duración al tempo del reloj MIDI que llega | [4.2 Sample Rec](#samplerec) | Alpha 0.02 |
| **Frecuencia por paso** | el paso suena una de cada n pasadas | [3.2 Pattern Settings y probabilidad](#patternsettings) | Alpha 0.0 |
| **Fusión USB** | el DIN In también por USB; Advanced Setup, pad 23 | [6.2 Setup y Advanced Setup](#setup) | Alpha 0.04 |
| **Gate por pulsación** | el golpe dura lo que mantienes el pad; Micro Step, pad 32 | [3.1 Velocity y Micro Step](#velocity) | Alpha 0.04 |
| **General MIDI** | las pistas por el canal 10 con su nota GM; Setup, pad 22 | [6.2 Setup y Advanced Setup](#setup) | Alpha 0.04 |
| **Grabación estéreo** | L y R en dos huecos; Sample Rec, pad 24 | [4.2 Sample Rec](#samplerec) | Alpha 0.04 |
| **Granular** | el motor granular en hasta 4 pistas; menú, pads 11 / 3 | [2.4 Página Granular](#granular) | Alpha 0.04 |
| **LFO de tono** | Stock+, K3 / K4; libre o a tempo | [2.3 Página Stock+](#stockplus) | Alpha 0.01 |
| **Longitud fija** | los golpes a mano con una longitud; Micro Step, pad 31 | [3.1 Velocity y Micro Step](#velocity) | Alpha 0.04 |
| **Marcas de Velocity** | en el paso marcado la automatización vuelve al knob; Shift + paso | [3.1 Velocity y Micro Step](#velocity) | Alpha 0.04 |
| **Menú de pista** | tocar el botón de la pista elegida (se queda abierto) o mantener el de una pista | [2.2 El menú de pista](#menu) | Alpha 0.04 |
| **Metrónomo** | cuatro estados con Shift + Clear | [1.1 Transporte, metrónomo y cuantizar](#transporte) | Alpha 0.0 |
| **Modo cue** | mezcla a la izquierda, cue a la derecha; Mixer, panoramas, Shift + knob | [5.1 Mixer](#mixer) | Alpha 0.04 |
| **Mutación del sample** | a veces suena el vecino; fila 4 de la probabilidad | [3.2 Pattern Settings y probabilidad](#patternsettings) | Alpha 0.0 |
| **Mute al compás** | Shift + pad de pista en el Mixer | [5.1 Mixer](#mixer) | Alpha 0.0 |
| **Nivel a 100 / 0** | Shift + knob en los niveles del Mixer | [5.1 Mixer](#mixer) | Alpha 0.0 |
| **Nudge** | el primer paso pasa a ser el 1; pad 26 de Pattern Settings | [3.2 Pattern Settings y probabilidad](#patternsettings) | Alpha 0.0 |
| **Órdenes fractal / deconstruido** | pads 27 / 28 de Pattern Settings | [3.2 Pattern Settings y probabilidad](#patternsettings) | Alpha 0.0 |
| **Página Stock+** | ocho knobs más por pista; menú, pad 2 | [2.3 Página Stock+](#stockplus) | Alpha 0.01 |
| **Program Change** | canales de escucha y salida; Setup, pads 29 / 30 | [6.2 Setup y Advanced Setup](#setup) | Alpha 0.0 |
| **Repetir la escena** | la escena actual 1-8 veces; Mixer, Shift + pads 9-16 | [5.1 Mixer](#mixer) | Alpha 0.0 |
| **Reset de knobs de pista** | Clear + botón de la pista | [2.1 El botón de pista](#pista) | Alpha 0.0 |
| **Resonancia master** | Shift + ▲ / ▼ en la vista FX | [5.2 FX y Sidechain](#fx) | Alpha 0.0 |
| **Retornos de FX como fuente** | la reverb o el delay como sonido de una pista de entrada; menú, pad 15 | [2.7 Entrada de línea y enlace estéreo](#entrada) | Alpha 0.06 |
| **Ring mod** | Stock+, K5 (Shift: la frecuencia) | [2.3 Página Stock+](#stockplus) | Alpha 0.02 |
| **Scan** | mueve el inicio de cada nota o del loop; Stock+, K8 | [2.3 Página Stock+](#stockplus) | Alpha 0.02 |
| **Sidechain por knobs** | K1-K4 de la vista Sidechain | [5.2 FX y Sidechain](#fx) | Alpha 0.0 |
| **Sinte** | dos osciladores con FM en hasta 4 pistas; menú, pads 12 / 4 | [2.5 Página Sinte](#sinte) | Alpha 0.05 |
| **Stretch** | más lento o rápido sin cambiar el tono; Stock+ K7, Sample mode pads 9 / 10 | [2.3 Página Stock+](#stockplus) | Alpha 0.02 |
| **Teclado externo al arpegiador** | Advanced Setup, pad 22 | [6.2 Setup y Advanced Setup](#setup) | Alpha 0.04 |
| **Thru: Out 2 / Merge / Filter** | Duplicate en Advanced Setup | [6.2 Setup y Advanced Setup](#setup) | Alpha 0.0 |
| **Tipo de filtro (24 dB, comb)** | Stock+, Shift + K6 | [2.3 Página Stock+](#stockplus) | Alpha 0.02 |
| **Umbral del compresor** | K5 de la vista Sidechain | [5.2 FX y Sidechain](#fx) | Alpha 0.01 |
