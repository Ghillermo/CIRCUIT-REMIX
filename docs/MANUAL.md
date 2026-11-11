# Circuit Remix Alpha 0.14 — manual

[English](MANUAL_EN.md) · [versión ilustrada](manual/index.html)

> ⚠️ **Alpha 0.13 es experimental:** el secuenciador de efectos y el looper se han probado en el aparato; casi todo lo demás desde Alpha 0.04, sobre todo en emulación. **Haz una copia de tu tarjeta SD.**

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
- [2.5 Páginas OSC 1 / OSC 2 (el VA)](#sinte)
- [2.6 Páginas Filtro / VCA y Envolvente + LFO](#filtro)
- [2.7 FM de 8 operadores](#fm)
- [2.8 Voz: modos, polifonía y unísono](#voces)
- [2.9 Página Envolvente](#envolvente)
- [2.10 Matriz, Secuenciables y No secuenciables](#matriz)
- [2.11 Entrada de línea y enlace estéreo](#entrada)
- [2.12 Vista Note](#note)

**3. Pasos y patrón**

- [3.1 Velocity y Micro Step](#velocity)
- [3.2 Pattern Settings y probabilidad](#patternsettings)
- [3.3 Patterns: cadenas](#patterns)
- [3.4 Pattern Mutate](#mutate)

**4. Samples**

- [4.1 Sample mode](#samplemode)
- [4.2 Sample Rec](#samplerec)
- [4.3 Patches del pack y starters](#patches)

**5. Mezcla y efectos**

- [5.1 Mixer](#mixer)
- [5.2 FX y Sidechain](#fx)
- [5.3 Grid FX: secuenciador de efectos y looper](#gridfx)

**6. Proyectos y ajustes**

- [6.1 Projects y Packs](#projects)
- [6.2 Setup y Advanced Setup](#setup)

**A. Apéndice**

- [A.1 Qué se guarda y dónde](#guardado)
- [A.2 MIDI](#midi)
- [A.3 Módulos de Arrhythmia (prueba de concepto)](#modulos)

- [Glosario de funciones](#glosario)

## 0. Introducción

<a id="leer"></a>
### 0.1 Cómo leer este manual

Cada capítulo es una vista del aparato: cómo se llega, qué hacen sus pads, knobs y botones con Circuit Remix. Todo lo demás funciona como en el firmware original de Novation (consulta su manual); los gestos nuevos son combinaciones que en el original no hacían nada o repetían el gesto sin modificador.

- **Pads 1-32** de izquierda a derecha y de arriba abajo: fila 1 = 1-8, fila 2 = 9-16, fila 3 = 17-24, fila 4 = 25-32.
- **K1-K8** = los 8 knobs. **▲ / ▼** = los botones de flecha.
- **Mantener** un botón = pulsarlo y no soltarlo; **A + B** = B con A mantenido.
- **★** = exclusiva de Circuit Remix (no está en CIRCUIT-HACKS).
- **(desde Alpha 0.0x)** = la versión que trajo la función. Lo marcado *(Alpha 0.14)* o *(Alpha 0.13)* es nuevo o cambia en estas versiones; *(Alpha 0.11)* = 0.10 + los módulos de Arrhythmia (solo en 0.11).
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
| Modos | un color por modo (las formas de onda del sinte, el tipo de filtro y el de waveshaper de Stock+, el metrónomo) |
| Opciones que se eligen entre sí | en la misma fila; la elegida brillante, las demás tenues |
| Abrir un menú o una página | un toque lo deja abierto; mantenerlo lo muestra hasta soltar |

Cada página de knobs de una pista tiene su color, el mismo en sus knobs y en su pad del menú (el botón de la pista ya no parpadea *(Alpha 0.09)*):

| Página | Color |
|---|---|
| stock (la del firmware original) | blanco en el menú; los knobs, los del original |
| Stock+ | azul cielo |
| Granular | lila |
| Sinte | menta |
| Envolvente | rosa |

<a id="instalar"></a>
### 0.3 Instalar y volver al original

1. Descarga `rm_app.zip`, descomprímelo, abre `rm_app.html` en Chrome o Edge y ve a la pestaña **Firmware** (la misma app ordena la tarjeta y sube los módulos).
2. Aporta el firmware oficial 2.0.1 (build 5706) del Circuit Rhythm: el instalador comprueba su SHA-256 y lo parchea en tu ordenador.
3. Elige la versión y envíala al aparato por USB.

**Versiones S** (A0.11S, A0.10S): sin las funciones que crean, cambian o borran ficheros de la tarjeta por su cuenta (copiar proyectos, borrar packs, copiar samples). La más segura para tu SD.

**Alpha 0.10 / 0.10S** = Alpha 0.11 / 0.11S sin los [módulos de Arrhythmia](#modulos).

**Volver al firmware oficial:** mantén **Sample Rec + Samples + Note** al encender (modo bootloader de Novation) y envía el oficial con la pestaña Firmware de la app («Oficial») o con Novation Components. Haz siempre una copia de tu tarjeta SD.

## 1. En cualquier vista

<a id="transporte"></a>
### 1.1 Transporte, metrónomo y cuantizar

*Cómo se llega:* en cualquier vista

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

## 2. Vistas de pista

<a id="pista"></a>
### 2.1 El botón de pista

*Cómo se llega:* las vistas de pista (Samples, Note, Velocity, Gate, Pattern Settings…)

| Gesto | Qué hace |
|---|---|
| **Clear + botón de la pista** | ★ sus knobs por defecto y su automatización borrada; el resto (nivel, panorama, envíos, sidechain, sample) como al cargar el proyecto *(desde Alpha 0.0)* |
| **Duplicate + pista A, luego pista B** | ★ B recibe los parámetros y el sample de A; con Duplicate mantenido, más pistas *(desde Alpha 0.0)* |
| **Mantener el botón de la pista** (¼ s) | abre el [menú de pista](#menu) en los pads *(desde Alpha 0.04)* |
| **Shift mantenido** (en cualquier vista) | ★ el botón de cada pista se enciende en blanco 100 ms cada vez que suena *(Alpha 0.10)* |
| **Pads de sample mantenidos** (arpegiador encendido) | ★ arpegio de los samples mantenidos (también uno solo): cada golpe cambia el sample, con la velocity de su pad; con Record y Play se graba *(desde Alpha 0.0)* |

Pulsar el botón sin mantenerlo elige la pista, como en el original. Desde el Mixer, Clear + pista hace lo del original. El arpegiador se enciende en [Pattern Settings](#patternsettings) (Shift + pad 25).

<a id="menu"></a>
### 2.2 El menú de pista

*Cómo se llega:* toca el botón de la pista elegida (el menú se queda abierto hasta que eliges algo o lo vuelves a tocar), o mantén el botón de cualquier pista (el menú solo mientras lo mantienes)

Los pads se convierten en el menú de esa pista. Desde *(Alpha 0.12)* es **la fila 1 de CIRCUIT-HACKS**, solo vistas: el motor y la voz de la pista se eligen en [Sample mode](#samplemode).

| Pad | Qué abre |
|---|---|
| **1** | ★ **[Secuenciables](#matriz)**; **Shift + 1**: ★ **[No secuenciables](#matriz)** |
| **2** | la página **del sonido**: sample o entrada → la stock; granular → **[Granular](#granular)**; VA → **[OSC 1](#sinte)**; FM → sus **[operadores](#fm)** |
| **3** | VA → **[OSC 2](#sinte)**; FM → su **[envolvente de pitch](#fm)**; oscuro con los demás sonidos |
| **4** | ★ **[Filtro / VCA](#filtro)** (lima) |
| **5** | ★ **[Envolvente + LFO](#filtro)** (rosa) |
| **6** | ★ **[Matriz](#matriz)** |
| **9** | la página **stock** (la del original) |
| **10** | **[Stock+](#stockplus)** |
| **16** | ★ **Project init** (rojo): la voz de la pista vuelve a como se cargó o guardó el proyecto (K1-K8 y el resto de la voz; nivel, panorama, envíos y sidechain no se tocan); Stock+, Granular, Sinte y Envolvente, a sus valores de fábrica |

Los demás pads, oscuros. Brillante = la página que se ve.

- **Abrirlo:** un toque en el botón de la pista que ya está elegida lo deja abierto; se cierra al soltar un pad del menú, al tocar otra vez el botón o al pulsar cualquier otro botón. Mantener el botón de una pista (¼ s) lo abre solo mientras lo mantienes, como los botones de vista del original.
- **Mantener** un pad de página (½ s o más) la muestra solo hasta que lo sueltas.
- Hasta Alpha 0.11 el menú era: 1 stock, 2 Stock+, 3 Granular, 4 Sinte, 5 Envolvente, 6 Matriz, 7 Secuenciables, 8 Project init, 16 No secuenciables.

*(Alpha 0.13)*: con el FM, la **fila 3** del menú = los operadores 1-8. El menú fijo ya no se cierra al elegir una página ni con Shift, Clear o Duplicate.

<a id="stockplus"></a>
### 2.3 Página Stock+

*Cómo se llega:* menú de pista, pad 10 (hasta 0.11, pad 2), en una pista con un sample, el granular o el sinte

La página Stock+ es por pista y se queda hasta apagar *(desde Alpha 0.01; K5-K8 desde Alpha 0.02)*. Actúa sobre el sample de la pista; con el granular o el sinte, sobre ellos *(Alpha 0.07)*.

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

**Con el granular o el sinte** *(Alpha 0.07)*: los mismos valores de la pista, sobre su sonido.

| Knob | Granular | Sinte |
|---|---|---|
| K1-K4 | la envolvente y el LFO de tono, en el tono de cada grano nuevo | la envolvente y el LFO de tono, en los dos osciladores |
| K5, K6 | ring, pitch follow y el tipo de filtro, sobre su filtro | lo mismo |
| K7 | ★ **waveshaper**: cantidad (0 = apagado; la ganancia de ×1 a ×16; en bitcrush, los bits). Shift: su **tipo**, **suave** (dorado), **duro** (rojo anaranjado), **plegado** (turquesa), **bitcrush** (lima) | lo mismo |
| K8 | ★ LFO de la **posición** de los granos (Shift: su profundidad) | ★ LFO de la **cantidad de FM** (Shift: su profundidad) |

- **Tipo de filtro** (Shift + K6): con **24 dB** su filtro pasa dos veces; con **comb**, sus filtros se abren y suena un comb afinado por el knob de paso bajo de la pista (más el follow; en el sinte, más la envolvente → filtro), con la resonancia como realimentación.
- El LED de K7 va en el color del tipo y brilla según la cantidad; con Shift, a tope. Clear + K7: apagado y suave.
- El waveshaper se guarda con el proyecto y lo llevan Clear + el botón de la pista y Duplicate.

<a id="granular"></a>
### 2.4 Página Granular

*Cómo se llega:* Sample mode, selector (pad 8), pad 23 (pone el granular y su página), o menú de pista, pad 2 (su página)

El motor granular de CIRCUIT-HACKS sobre el sample de la pista, en el DSP del master *(desde Alpha 0.04)*. Sigue la nota (vista Note, teclado y MIDI). Los knobs de filtro (paso alto, paso bajo, resonancia) y la envolvente de la pista actúan sobre él; también la distorsión *(Alpha 0.07)*. **Hasta 4 pistas granulares**, cada una con sus ajustes; los 16 granos se reparten (16 con una pista, 7 por pista con dos, 4 con tres, 2 con cuatro).

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

**Inicio y longitud del original** *(Alpha 0.09)* (página stock, K2 / K3): el inicio se suma a la posición (K3 de esta página), hasta el final del sample; la longitud estrecha la zona (a tope, su valor por defecto, no cambia nada).

<a id="sinte"></a>
### 2.5 Páginas OSC 1 / OSC 2 (el VA)

*Cómo se llega:* Sample mode, selector (pad 8), pad 20 (pone el VA); menú de pista, pads 2 / 3

★ Los osciladores VA de CIRCUIT-HACKS como sonido de cualquier pista *(Alpha 0.12)*: dos osciladores con morph seno → triángulo → sierra → cuadrada, una forma por onda (pliegue, curva, supersaw de 5 sierras o ancho del pulso), FM a los dos lados, ring, sync y modos bit a bit. Hasta 4 huecos de sinte (VA o [FM](#fm)) entre todas las pistas, compartidos con la [polifonía](#voces). Las notas le llegan como a un sample (pads, vista Note, secuencia, MIDI).

**OSC 1** (menú, pad 2; la página Sinte de un VA):

| Knob | Solo | Con Shift |
|---|---|---|
| K1 | afinación (±24 semitonos) | envolvente → tono |
| K2 | fino | glide |
| K3 | onda (morph; su LED en el color de la onda más cercana: seno blanco, triángulo verde, sierra roja, cuadrada amarilla) | octava |
| K4 | forma | envolvente → forma |
| K5 | envolvente → FM (desde el centro) | — |
| K6 | envolvente → ring (desde el centro) | — |
| K7 | envolvente → morph (desde el centro) | — |
| K8 | envolvente → mezcla (desde el centro) | — |

**OSC 2** (menú, pad 3):

| Knob | Qué hace |
|---|---|
| K1 | afinación de OSC 2 (±24 semitonos) |
| K2 | fino de OSC 2 |
| K3 | onda de OSC 2 |
| K4 | forma de OSC 2 |
| K5 | FM: en el centro nada; a la derecha OSC 2 → OSC 1, a la izquierda OSC 1 → OSC 2 |
| K6 | ring |
| K7 | sync y modos bit a bit, por zonas: nada, sync, xor, or, nor, and, nand (cada zona en su color) |
| K8 | mezcla OSC 1 ↔ OSC 2 |

- **La envolvente** es la de la página [Envolvente](#envolvente) (su K2 = el release). Glide y octava también en el [desplegable de voz](#voces).
- **Los knobs del original** de la pista siguen actuando: filtro, envolvente, tono, distorsión, nivel… (página stock o [Filtro / VCA](#filtro)).
- **LEDs:** menta, brillo = el valor; los bipolares, oscuros en el centro y más claros a la izquierda *(Alpha 0.12)*.
- Clear + knob = por defecto. **Se guarda con el proyecto**; la afinación y el fino de OSC 1 y las tres profundidades de envolvente, en la tarjeta con el [sonido del proyecto](#guardado).
- Hasta Alpha 0.11 el sinte era otro (dos osciladores clásicos con SUB y ruido, una sola página).

*(Alpha 0.13)*: **OSC 2 sigue a OSC 1** como relación armónica (K5 de OSC 2: 0,25 … 31; su fino ±50 cents), como en CIRCUIT-HACKS. Arreglado: K6 (FM) no hacía nada y RING ponía también el FM. **Sobremuestreo 2×** (Sample mode, selector, pad 4 en una pista VA): menos aliasing en agudos con FM y sync, si el DSP tiene sitio. Choke (pad 29) en un sinte cambia de lado el modo de voz; reverse invierte la Envolvente.

<a id="filtro"></a>
### 2.6 Páginas Filtro / VCA y Envolvente + LFO

*Cómo se llega:* menú de pista, pads 4 y 5 (cualquier pista)

★ Dos páginas que reúnen knobs de otras *(Alpha 0.12)*. Cada knob mueve el valor de siempre (el del original, la Envolvente o Stock+), con sus pasos y su Clear, y los carriles de la matriz lo graban igual.

**Filtro / VCA** (pad 4, lima):

| Knob | Qué hace |
|---|---|
| K1 | el **nivel** de la pista (el del Mixer) |
| K4 | la envolvente del original |
| K5 | envolvente → paso bajo (granular y sinte; desde el centro) |
| K6 / K7 / K8 | paso alto, paso bajo y resonancia del original |
| K2 / K3 | nada (oscuros) |

**Envolvente + LFO** (pad 5):

| Knob | Qué hace |
|---|---|
| K1-K4 | los de la página [Envolvente](#envolvente): inicio, longitud, pendiente, → filtro (granular y sinte; rosa) |
| K5 | velocidad del LFO de [Stock+](#stockplus) (desde el centro: derecha libre, izquierda a tempo; azul cielo) |
| K6 | profundidad del LFO de Stock+ (azul cielo) |
| K7 / K8 | nada |

Las dos se quedan hasta elegir otra página o cambiar el motor de la pista.

<a id="fm"></a>
### 2.7 FM de 8 operadores

*Cómo se llega:* Sample mode, selector (pad 8), pad 24 (pone el FM; un toque más: la página FM)

★ El FM de 8 operadores de CIRCUIT-HACKS, con las envolventes del DX7 y 56 algoritmos, como sonido de cualquier pista *(Alpha 0.12)*. Comparte los 4 huecos de sinte con el [VA](#sinte).

**La página FM** (Sample mode, un toque al pad 24 de una pista con el FM; los 32 pads son suyos):

| Pad | Qué hace |
|---|---|
| **9-16** | el operador 1-8 a editar (portadores verde, moduladores azul, el elegido brillante; los que el algoritmo no usa, apagados) |
| **3** | la envolvente de pitch (lavanda) |
| **7 mantenido** | los 56 algoritmos en los pads 9-32, en tres páginas con ▼ / ▲ (los de 4 operadores verdes, los de 8 ámbar, los del DX7 blancos); uno pulsado = ese algoritmo |
| **Clear + 7** | una voz tocable del algoritmo (todos los ratios a 1) |
| **8 mantenido** | los 24 instrumentos de partida (en el color de su familia); uno pulsado = cargado |
| **7 (toque)** | cierra la página |

**Los knobs** (en la página FM y en la página Sinte de una pista con FM: menú, pad 2 = el operador, pad 3 = la envolvente de pitch):

| Knob | Operador | Con Shift |
|---|---|---|
| K1 | ratio | algoritmo |
| K2 | fino | feedback |
| K3 | nivel de salida | rate scaling |
| K4 | sensibilidad a la velocity | level scaling |
| K5-K8 | R1-R4 de su envolvente | L1-L4 |

Con la envolvente de pitch: K1 transposición, K3 ruido, K4 su operador, K5-K8 R1-R4 (Shift: L1-L4). Lavanda, brillo = el valor. Clear + knob = el valor inicial.

- **Sample mode, pad 24 mantenido:** los 24 instrumentos en las filas 1, 2 y 4, sin abrir la página.
- **Polifonía y modos de voz:** [Voz](#voces).
- **Se guarda con el proyecto en la tarjeta** (el banco de patches del pack) *(Alpha 0.12)*; no en el pack interno ni en las versiones S.

<a id="voces"></a>
### 2.8 Voz: modos, polifonía y unísono

*Cómo se llega:* Sample mode, selector (pad 8), pad 16 (VA y FM)

★ Los modos de voz de CIRCUIT-HACKS para el VA y el FM *(Alpha 0.12)*. Hay **4 huecos de sinte** entre todas las pistas; la polifonía y el unísono toman los libres.

- **Un toque al pad 16:** polifonía sí / no (vuelve al último modo mono). Con poco DSP libre, una nota nueva toma la voz más antigua.
- **Pad 16 mantenido:** los modos en los pads 17-24 (el actual brillante; el pad 16 se ve en el color del modo), y los knobs:

| Pad | Modo |
|---|---|
| 17 (verde) | **retrigger**: cada nota vuelve a disparar la envolvente |
| 18 (amarillo) | **legato**: una nota que pisa a la anterior solo cambia la altura (no vuelve a disparar la envolvente ni los operadores FM) |
| 19 (verde azulado) | **glide**: como legato, y la altura se desliza; una nota suelta empieza en su altura |
| 20 (verde) | **uni retrig**: todas las voces de la pista en la misma nota, desafinadas con K2 |
| 21 (amarillo) | **uni legato** |
| 22 (verde azulado) | **uni glide** |
| 23 (violeta) | **uni always-glide**: se desliza siempre, también tras soltar |
| 24 (magenta) | **poly**: hasta 4 notas a la vez |

| Knob (pad 16 mantenido) | Qué hace |
|---|---|
| K1 (verde azulado) | glide |
| K2 (azul) | desafinación del unísono (hasta ±50 cents en las voces de los extremos) |

- Con 3 o 4 voces en unísono el nivel baja (0,82 / 0,71) para no saturar.
- Una pista que nunca eligió modo suena como hasta Alpha 0.11.
- **Se guarda con el proyecto en la tarjeta** *(Alpha 0.12)* (no en las versiones S).

<a id="envolvente"></a>
### 2.9 Página Envolvente

*Cómo se llega:* menú de pista, pad 5 (desde 0.12, [Envolvente + LFO](#filtro): sus K1-K4), en una pista con el sinte o el granular

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

<a id="matriz"></a>
### 2.10 Matriz, Secuenciables y No secuenciables

*Cómo se llega:* menú de pista, pad 6, pad 1 y Shift + pad 1 (hasta 0.11: 6, 7 y 16; cualquier pista)

★ Tres páginas para modular y automatizar *(Alpha 0.10)*. Un toque fija la página, mantener dura hasta soltar y otra vez la quita.

**Destinos (32 por pista):** fila 1 = K1-K8 del original; fila 2 = K1-K8 de Stock+ (K7: stretch en un sample, el waveshaper en el granular y el sinte); filas 3-4 = la página del sonido (sinte 16 valores, granular 13, sample Shift + K5-K8 de Stock+). Una pista de entrada solo tiene los del original. Al elegir uno, los pads enseñan dónde está durante 1,5 s, con el color de su página.

**Matriz (pad 6):** K1-K8 son las fuentes.

| Knob | Fuente | Con Shift |
|---|---|---|
| K1 | velocity | |
| K2 | nota | |
| K3 | aleatorio por nota | |
| K4 | LFO 2 | 4 zonas (triángulo, sierra, cuadrada, sample & hold), cada una con 32 velocidades: primera mitad a tempo, segunda libre, oscuro en el centro |
| K5 | envolvente 2 | ataque (4, un color cada uno) y caída (32) |
| K6 | golpe de una pista | la pista y la caída |
| K7 | posición en el patrón | |
| K8 | aleatorio por pasos | pasos por valor: 1, 2, 4, 8 |

La posición del knob es destino + cantidad: al principio apagado, luego 16 clics por destino. Su LED lleva el color de la página del destino, con el brillo = la cantidad. Clear + knob lo apaga; Clear + Shift + knob devuelve el parámetro de la fuente.

**Secuenciables (pad 7):** K1-K8 son los 8 carriles de automatización. El knob mueve el destino de su carril y graba en él. Shift + knob elige el destino (4 clics cada uno). Clear + knob borra el carril en los 8 patrones y lo devuelve a su K del original.

**No secuenciables (pad 16):** K1-K8 mueven su destino (de fábrica, Stock+ K1-K8) y nunca se graban, ni con Record. Shift + knob elige el destino; Clear + knob, el de fábrica.

**Carriles automáticos:** con Record, un knob de Stock+, Granular o Sinte también se graba: en el carril de ese destino o, si no tiene, en el carril libre más alto, que lo adopta. Así la página Secuenciables se rellena sola.

**Carril extra:** una novena automatización por pista, con un valor por paso. La toma el primer destino que no encuentra carril; sin más carriles, los demás destinos no se graban. Clear + Shift + cualquier knob de Secuenciables lo borra en los 8 patrones.

El pad 8 del menú devuelve también la matriz y los No secuenciables a sus valores de fábrica; los carriles conservan su destino y sus datos.

*(Alpha 0.13)*: **todos los parámetros** (salvo los operadores del FM) son destinos, en el orden de las vistas de la pista y solo los que tiene su motor: los extras de OSC 1, la Envolvente, el tipo de waveshaper, la capa Shift de Stock+, nivel, panorama y envíos.

<a id="entrada"></a>
### 2.11 Entrada de línea y enlace estéreo

*Cómo se llega:* Sample mode, selector (pad 8): pads 18 / 19 y 2 / 3; enlace: pad 14 (hasta 0.11: pads 8 / 15 / 16 y 14)

Desde Alpha 0.12 son los del selector de motores de [Sample mode](#samplemode) (pad 8); en Alpha 0.09-0.11, los pads 8 (entrada), 15 (fuente) y 16 (gate) de Sample mode; hasta Alpha 0.08, el menú de pista (entrada 13, gate 14, fuente 15, enlace 9).

**Entrada de línea** (selector, pads 18 / 19; desde Alpha 0.04): la entrada de audio suena como el sonido de la pista, con su nivel, panorama, envíos, filtro y envolvente.
- Una pista de entrada: L + R. Dos: la de número menor es L, la mayor R. En una tercera, sale la primera puesta.
- **El gate: pad 18 = sin gate** (siempre suena, directo a la mezcla); **pad 19 = con gate**: solo mientras suenan sus notas, por el VCA y el filtro de la pista (paso bajo, paso alto, resonancia; el filtro desde Alpha 0.06).
- **La fuente** (Alpha 0.06; pad 2 con el 18, pad 3 con el 19): las entradas (ámbar tenue, sin FX; hasta Alpha 0.07, ámbar) → el **retorno de reverb** (crema) → el **de delay** (melocotón), por turnos; cada pista de entrada la suya. El retorno llega un bloque tarde (0,67 ms).
- **El FX hacia una entrada** *(Alpha 0.09)*: el retorno que toma una pista de entrada ya no va al master; suena solo a través de la pista. El envío de esa pista a su propio efecto llega a tres cuartos *(Alpha 0.10)* (el knob entero = tres cuartos de envío; en Alpha 0.09, la mitad), así la realimentación se queda contenida; el envío al otro efecto va entero. Hasta Alpha 0.08, el retorno sonaba también por el master y el envío a su propio efecto realimentaba.

**Enlace estéreo** (pad 14; desde Alpha 0.04): la pista (izquierda) y la siguiente (derecha) suenan juntas con las notas de la primera. Pad 14 en cualquiera de las dos = deshacer. En la pista 8 sola, oscuro. Sin enlazar quedan el LFO y el scan libres de Stock+ y el WSOLA del stretch.
- **La segunda pista, en desviaciones** *(Alpha 0.09)*: sus K1-K8 (página stock) son desviaciones de los de la primera: centro = igual, a la derecha suma, a la izquierda resta. Sus LEDs en azul acero, oscuros en el centro. Clear + knob = el centro.
- **Su sample** = el de la primera + la distancia entre sus pads: por defecto, el siguiente; elegir otro pad en la segunda cambia la distancia, y mover el de la primera mueve los dos *(Alpha 0.09)*.
- **Sus propios pasos también suenan** *(Alpha 0.09)*: la segunda toca las notas de la primera y además las suyas.
- Enlazar pone los knobs de la segunda en el centro (suena igual); deshacer el enlace los deja donde sonaban. Un proyecto de Alpha 0.04-0.08 con un enlace carga como sonaba.

Las dos se guardan con el proyecto.

<a id="note"></a>
### 2.12 Vista Note

*Cómo se llega:* botón Note

| Gesto | Qué hace |
|---|---|
| **Teclas mantenidas** (arpegiador encendido) | ★ arpegio de las notas mantenidas sobre el sample de la pista; con Record y Play se graba *(desde Alpha 0.0)* |
| **Shift + tecla** | ★ **latch** *(Alpha 0.12)*: la nota entra o sale del acorde de la pista (hasta 6; azul hielo). Luego cada nota que toques o secuencies hace sonar el acorde trasladado a ella (la raíz = la nota más grave): un acorde que se mueve. Con el arpegio, el arpegio toca el acorde. En una pista mono suena la raíz; los acordes, con la [polifonía](#voces) |
| **Clear + Note** | ★ vacía el acorde del latch *(Alpha 0.12)* |
| **Shift + Note** en la vista Note ampliada (Note dos veces) | ★ editor de la **escala propia de la pista** (hasta 0.11: Shift mantenido en la vista Note) *(desde Alpha 0.0)* |

**El editor:** los 32 pads son dos octavas de piano desde la tónica (fila 4 = las blancas de la octava de abajo, el pad 25 = la tónica; fila 3 = sus negras; filas 2 / 1 = la octava de arriba). Cada tecla enciende o apaga su grado (7 como máximo); la más alta es el **periodo**: la tónica de la siguiente iteración (la octava u otra, hasta 24 semitonos). Tónica blanca, grados verdes, periodo azul.

Al cerrar el editor, el teclado toca la escala: una iteración por fila (dos si tiene 4 notas o menos); ▲ / ▼ mueven una fila. Sin teclas, vuelve el piano del original. Se guarda con el proyecto.

## 3. Pasos y patrón

<a id="velocity"></a>
### 3.1 Velocity y Micro Step

*Cómo se llega:* botón Velocity; Micro Step = Shift + Gate

| Vista | Gesto | Qué hace |
|---|---|---|
| Velocity | **Shift mantenido** | ★ la **vista de automatización** *(Alpha 0.09)*: los pasos con automatización de knobs en **amarillo**, los marcados en **rojo**, los demás como los dibuja la vista |
| Velocity | **Shift + paso amarillo** | ★ **escucharlo** *(Alpha 0.09)*: sus valores van a los knobs y al sonido, esos knobs en amarillo (brillo = el valor); otro paso amarillo pone los suyos; al soltar Shift, todo vuelve como estaba |
| Velocity | **Shift + otro paso** | marca el paso *(desde Alpha 0.04)*: al sonar, la automatización no suena ahí y los parámetros automatizados vuelven a **Project init** *(Alpha 0.09)* (hasta Alpha 0.08, a la posición de su knob); un knob girado a mano se queda donde lo dejaste. Otra vez = desmarcar |
| Velocity | **Velocity otra vez** | ★ la vista de automatización **fija**, sin mantener Shift *(Alpha 0.09)*: un toque en un paso amarillo lo escucha, en otro lo marca. Velocity otra vez, u otra vista, la quita (lo que escuchabas vuelve). Shift + Velocity sigue siendo la velocity fija del original |
| Velocity | **Clear + paso** (con o sin Shift; Clear primero) | ★ borra la automatización de knobs de ese paso; sus notas, su marca y los carriles del Mixer se quedan *(Alpha 0.09)* |
| Velocity | **Paso amarillo mantenido + otro paso** (vista de automatización) | ★ **rampa** *(Alpha 0.10)*: cada carril de knob con valor en alguno de los dos extremos recibe la línea recta entre ellos, micropaso a micropaso; un extremo sin valor usa el valor actual |
| Vista de pista (Samples) | **Record mantenido + paso** | ★ **snapshot** *(Alpha 0.09)*: cada knob que no está en Project init queda en ese paso (sus 6 micropasos); el pad del paso en amarillo mientras lo mantienes; al soltar Record, la grabación como estaba |
| Micro Step | **pad 31** | longitud fija: apagada → el selector en los pads 17-32 (1-16 pasos; elegir una la enciende); encendida → apagada (naranja brillante / tenue) *(desde Alpha 0.04)* |
| Micro Step | **pad 32** | gate por pulsación: el golpe dura lo que mantienes el pad del paso; mantener un paso vacío 300 ms o más también lo crea (verde brillante / tenue) *(desde Alpha 0.04)* |

Encender uno de los dos de Micro Step apaga el otro. Con cualquiera, un golpe introducido a mano en los pasos toma esa longitud.

**Project init** de una pista *(Alpha 0.09)*: sus parámetros como se cargó o se guardó el proyecto por última vez (se vuelve a tomar en cada guardado). El pad 8 del [menú de pista](#menu) (rojo) devuelve ahí su voz.

<a id="patternsettings"></a>
### 3.2 Pattern Settings y probabilidad

*Cómo se llega:* botón Pattern Settings (dos veces: la vista de probabilidad, modo 1)

| Gesto | Qué hace |
|---|---|
| **Pad 26** (azul) | Nudge: mueve el tramo elegido un paso atrás; con Shift, adelante. Pasos, carriles y valores por paso van con él *(Alpha 0.10)* |
| **Pad 27 / 28** | órdenes **fractal** (1 · 1 2 · 1 2 3 …) y **deconstruido** (1 6 11 16 · 2 7 12 13 …); un pad de dirección vuelve al original *(desde Alpha 0.0)* |
| **Pad 25** (gris) | vista de probabilidad, modo 2: elige un paso; **fila 3 = dinámicas** (velocity y retraso dentro del paso; con Record, cada paso con dinámicas queda escrito como sonó), **fila 4 (25-28) = mutación del sample** (a veces suena el vecino) *(desde Alpha 0.0)* |
| **Pattern Settings dos veces** | vista de probabilidad, modo 1: **fila 4 = frecuencia** del paso: suena en la última de cada n pasadas *(Alpha 0.10)*; cada patrón de una cadena lleva su cuenta, y cuando no suena, la nota anterior sigue entera *(desde Alpha 0.0)* |
| **Clear + pad 25** | borra las dinámicas y la mutación del patrón (la frecuencia se queda) *(desde Alpha 0.04)* |
| **Shift + pad 25** | ★ arpegiador de la pista encendido / apagado (verde brillante / tenue) *(desde Alpha 0.0)* |
| **Shift + pads 1-4** (arpegiador encendido) | ★ apertura de octavas: nada, +1, +1 / −1, +2 / −1 *(Alpha 0.10)* |
| **Shift + pads 5-8** (arpegiador encendido) | ★ cuándo cambia la octava: tras una vuelta, en cada nota, cada 3, cada 4 *(Alpha 0.10)* |
| **Shift + pads 9-12** (arpegiador encendido) | ★ groove: nada, nota / nota con puntillo, swing, cada nota dos veces *(Alpha 0.10)* |
| **Shift + pads 13-16** (arpegiador encendido) | ★ reinicio: nada, tras 1 / 3 / 5 notas de la segunda vuelta *(Alpha 0.10)* |
| **Shift + pads 27-32** | orden del arpegio: fractal, deconstruido, arriba, abajo, ping-pong, aleatorio |
| **Shift + pads 17-24** | resolución del arpegio (1/4 … 1/32T); otra vez la misma = el sync rate de la pista |

Las filas del arpegiador con Shift: la opción elegida verde brillante, las demás verde tenue (desde Alpha 0.05). Los modificadores del arpegio vienen de CIRCUIT-HACKS y se guardan por patrón; con el arpegiador apagado, esos pads hacen lo del original. Los valores por paso viajan con el golpe al cuantizar, al hacer Nudge, al copiar un paso y con el Mutate del original.

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

<a id="mutate"></a>
### 3.4 Pattern Mutate

*Cómo se llega:* Patterns o Mixer: Shift + Duplicate

Diseño de **[mefisme](https://github.com/mefisme)** (Rhythm Plus, MIT), con código propio *(Alpha 0.13)*. Cada pista elegida toca una lista de patrones al azar, hecha de su cadena, en lugar de la cadena.

| Gesto | Qué hace |
|---|---|
| **Shift + Duplicate** (toque, Patterns o Mixer) | semilla nueva: las pistas elegidas tocan su lista desde su siguiente fin de patrón |
| **Shift + Duplicate mantenido** (Patterns) | la página de ajustes (naranja rojizo; elegido = fuerte) |
| En la página: **columna 1 / 2** | longitud de la lista 1-4 / 5-8 |
| **columna 3** | tipo de longitud: como la cadena / exacta / al azar hasta la longitud |
| **columnas 4-5** | cuánto cambia: todo, 7, 6, 5 / 4, 3, 2, 1 huecos |
| **columna 6** | repeticiones sí / no; **columna 7**: conservar el primer hueco |
| **Botones de pista** | las pistas que muta |
| **Clear + Duplicate** (cualquier vista) | fin de todas las listas; **un pad de patrón** termina la de su pista |

Una pista que muta acaba su cadena en el último hueco de su lista (para que la escena siguiente entre a tiempo).

## 4. Samples

<a id="samplemode"></a>
### 4.1 Sample mode

*Cómo se llega:* botón Samples dos veces

| Gesto | Qué hace |
|---|---|
| **Pads 1 / 2** (del original) | ajustan el sample al patrón cambiando el tono; desde Alpha 0.04 apagan antes el stretch |
| **Pads 9 / 10** | ★ lo mismo con el **stretch** (K7 de Stock+), sin cambiar el tono: la longitud siguiente / la anterior *(desde Alpha 0.04)* |
| **Pad 19** | ★ de-clicker del loop de la pista elegida (crossfade de 256 muestras) **y de sus redisparos** en cualquier modo, también en reverse *(Alpha 0.12)*, encendido / apagado (azul brillante / tenue); encendido por defecto, se guarda con el proyecto *(desde Alpha 0.04)* |
| **Pad 14** | ★ [enlace estéreo](#entrada) con la pista siguiente (azul acero) |
| **Pad 8** | ★ **el selector de motores** *(Alpha 0.12)*: abre y cierra la fila de motores (en el color del motor de la pista: abierto brillante, cerrado tenue) |

**Con el selector abierto** (otro toque al pad 8, o salir de Sample mode, lo cierra; elegir un motor lo deja abierto). Las filas 1-3 son del selector; las opciones solo de sample (1 / 2, 9 / 10, 19, los slices 22-24 y 31 / 32) se ocultan; 25-30, como siempre:

| Pad | Qué hace |
|---|---|
| **17** | **sample** (cian) |
| **18** | **solo entrada** (blanco): la [entrada de línea](#entrada) directa a la mezcla, sin filtro ni VCA; su fuente en el pad **2** |
| **19** | **entrada → VCA / VCF / FX** (ámbar): con el filtro y la envolvente de la pista; su fuente en el pad **3** |
| **20** | **VA** (menta): [OSC 1 / OSC 2](#sinte) |
| **21 / 22** | VA-drum y wavetable: oscuros, aún no existen en el Rhythm |
| **23** | **granular** (lila): [Granular](#granular) |
| **24** | **FM** (lavanda): [FM de 8 operadores](#fm); con el FM ya puesto, un toque = la página FM, mantenido = los 24 instrumentos en las filas 1, 2 y 4 |
| **16** | la [voz](#voces) (VA y FM): toque = polifonía, mantenido = los modos de voz en 17-24 |
| **14** | el enlace estéreo |
| **8** | cierra |

El del motor de la pista, brillante; los demás, tenues. La fuente de la entrada: las entradas (ámbar tenue), el retorno de reverb (crema), el de delay (melocotón).

Shift + estos pads, como el original. Los loops muy cortos suenan a su longitud (en el original se repetían cada ~128 muestras). Hasta Alpha 0.11 el sonido estaba en los pads 5-8, la entrada en 15 / 16 y el VA / FM / poly en 11-13.

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

<a id="patches"></a>
### 4.3 Patches del pack y starters

*Cómo se llega:* Sample mode: mantener un pad de motor, o el pad 8

Cada pack tiene **64 patches** de sinte y granular en su banco de patches de la tarjeta *(Alpha 0.13)*.

| Gesto | Qué hace |
|---|---|
| **Pad 8 mantenido** (con el selector abierto o cerrado) | los 64 patches del pack en las filas 1, 2 y 4; **▲ / ▼** = la página |
| En la lista: **toque** | carga el patch en la pista (pone su motor) |
| **Clear + patch, dos veces** | guarda el sonido de la pista en ese hueco |
| **Duplicate + A, luego B** | intercambia A y B; **Duplicate + A, otro pack, Duplicate + B** = copia A en B |
| **Pad de motor mantenido** (20 VA, 23 granular, 24 FM) | sus **starters**: 8 VA, 8 granulares o los 24 instrumentos FM; un toque carga |
| **Clear + botón de pista** (vistas de pista) | la pista vuelve al último patch o starter que cargó |
| **Clear + knob** (OSC 1 / OSC 2, Granular, FM) | ese knob vuelve al valor del patch cargado |

Un hueco vacío del pack enseña primero un patch de ejemplo hasta que guardas encima. **No están en Alpha 0.13S ni 0.14S** (escriben en la tarjeta).

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

La vista Grid FX (Shift + Mixer): ver [Grid FX](#gridfx) *(Alpha 0.13)*. Los huecos fijados con el pad 16 se ven en fuerte, como en el original.

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

<a id="gridfx"></a>
### 5.3 Grid FX: secuenciador de efectos y looper

*Cómo se llega:* Shift + Mixer (la vista Grid FX); Sample mode, selector, pad 21

**Secuenciador de efectos** *(Alpha 0.13)*: una pista hace sonar los Grid FX en lugar de samples.

| Gesto | Qué hace |
|---|---|
| **Sample mode, selector (pad 8), pad 21** | la pista elegida es una **pista de efectos** (azul; otra vez = no) |
| En su vista: **pads 17-32** | los 16 huecos del Grid FX, cada uno tenue en el color de su efecto; en fuerte el que suena |
| **Un paso** | enciende el hueco de su sample (flip) mientras dura su nota |
| **Mantener un paso** (filas 1-2) | enciende su efecto hasta soltarlo |
| **Octave ▼ + paso / Octave ▲ + paso** | ese paso: un efecto al azar / repetir el último |
| **K1-K8** de la pista de efectos | cuánto de cada pista pasa por el Grid FX (todo al empezar); se automatizan |
| **Vista Grid FX: hueco mantenido + K2** *(Alpha 0.14)* | el tipo mientras se mantiene, como en el original: Beat Repeat … **Auto-Filter**, **Digitiser** … Vinyl y, tras Vinyl, los nuevos **delay throw** (melocotón: el delay de todas las pistas a tope) y **reverb throw** (crema); al soltar, el hueco vuelve a su tipo guardado. Ya no hay Shift + K1 |

**Looper / sampler en vivo** *(Alpha 0.13)*, en la vista Grid FX (Shift + Mixer):

| Pad | Toque | Mantener | Shift + pad |
|---|---|---|---|
| **9** (graba la entrada de línea) | N compases | mientras se mantiene | armado: empieza en el compás siguiente; parado, al arrancar |
| **10** (remuestrea la mezcla tras el Grid FX, sin los loops) | N compases | mientras se mantiene | igual |
| **11-14** (los 4 loops) | una vez desde el principio | en bucle hasta soltar | bucle a tempo sí / no |

- Graba en el loop del último pad 11-14 tocado: **overdub** si ese pad está mantenido o su loop suena en bucle; si no, sustituye.
- **Shift + K8** = N: ½, 1, 2 o 4 compases (un cuarto de vuelta por paso; K8 en amarillo, naranja, rojo anaranjado o salmón). **Clear + pad 11-14** = vaciar.
- LEDs: 9 / 10 rojo tenue, rojo fuerte grabando, ámbar armado; 11-14 oscuro vacío, ámbar tenue con audio, medio el elegido, fuerte sonando.
- Hasta ≈ 6,7 s por loop, estéreo. Los loops no se guardan.

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
| Advanced | **Pad 24** | ★ **guardar al parar** (verde brillante / tenue; apagado de fábrica): con la marcha en curso, Save espera a parar y parpadea en amarillo *(Alpha 0.10)* |
| Advanced | **K1** | ★ **curva de velocity**: −8 .. +8, 2 clics por paso, centro = el original; a la derecha los golpes flojos suenan más fuerte, a la izquierda al revés *(Alpha 0.10)* |

Todo se guarda en los ajustes del aparato, salvo el modo GM, que va con el proyecto. Si los dos canales de Program Change son distintos, el recibido se reenvía por el de salida.

*(Alpha 0.13)*: modo GM, los knobs muestran su nota con el brillo, y una nota nueva suena en la pista.

## A. Apéndice

<a id="guardado"></a>
### A.1 Qué se guarda y dónde

| Dónde | Qué |
|---|---|
| **Con el proyecto** | la matriz, los carriles y los No secuenciables, los modificadores del arpegio, Stock+, Granular, Sinte (ajustes y pistas), Envolvente, la fuente de la entrada, entrada de línea, enlace estéreo (con las desviaciones de la segunda pista), de-clicker por pista, escala propia, reglas de cadena, dinámicas / mutación / frecuencia por paso, marcas de Velocity, Micro Step, modo GM, reverb / delay / sidechain |
| **En la tarjeta, con el proyecto** *(Alpha 0.12)* | el banco de patches del pack (`Patches/NN_PATCHBANK.cpb`): el FM de 8 operadores de cada pista, los modos de voz, la desafinación del unísono, la afinación / el fino de OSC 1 y las profundidades de envolvente del VA. No en el pack interno ni en las versiones S |
| **Ajustes del aparato** | canales de Program Change, modo del Thru, teclado al arpegiador, fusión USB, guardar al parar, curva de velocity, resonancia del filtro master, compresor |
| **Hasta apagar** | la página de knobs de cada pista, Project init (lo cargado o guardado), el modo cue, el metrónomo / cuenta atrás, Sample Rec pads 23 / 24 |

Lo propio del mod va en una zona del fichero de proyecto que el original no usa. Un proyecto de una versión anterior carga sin lo que esa versión no tenía. **Guarda copias de tus proyectos.**

<a id="midi"></a>
### A.2 MIDI

Los knobs nuevos mueven parámetros del original con su MIDI de siempre (guía del programador del Circuit Rhythm): sidechain NRPN 1:1-1:4 (canal de la pista); reverb NRPN 1:18-1:20; delay NRPN 1:6-1:11; resonancia master CC 71; compresor NRPN 1:22-1:26. Las páginas Stock+, Granular y Sinte aún no tienen MIDI.

<a id="modulos"></a>
### A.3 Módulos de Arrhythmia (prueba de concepto)

*Cómo se llega:* desde el ordenador, por USB

★ *(Alpha 0.11)* **Una prueba de concepto, solo en Alpha 0.11 y 0.11S.** No está en Alpha 0.10 / 0.10S, ni en las anteriores, ni en el firmware oficial: con ellas la app no recibe respuesta. Circuit Remix ejecuta los **módulos de [Arrhythmia](https://github.com/llcoolkm/arrhythmia)** (de llcoolkm, licencia MIT): pequeños programas (`.mod`) que toman las luces, los pads y los botones y pueden tocar notas, mover parámetros y mandar MIDI. Los módulos, su interfaz y su documentación son de Arrhythmia; Circuit Remix trae su propio código para esa interfaz, así que el mismo fichero sirve en los dos firmwares. Los módulos no están en este repositorio: **descárgalos de las [releases de Arrhythmia](https://github.com/llcoolkm/arrhythmia/releases)** y mira sus controles en [su guía de módulos](https://github.com/llcoolkm/arrhythmia/blob/main/docs/user/modules.md).

- **Subir y arrancar:** en la [app de Circuit Remix](https://github.com/Ghillermo/CIRCUIT-REMIX#la-app-de-circuit-remix-toolsrm_apphtml) (`rm_app.html`), botón **Módulos (prueba de concepto)…**: elige el `.mod`, la app lo comprueba (cabecera y CRC), lo sube, lo lee de vuelta y lo arranca.
- **Mientras corre:** un módulo con entrada se queda con los pads y los botones; **Shift** y los knobs siguen siendo del original, **Play** sigue moviendo el transporte. **Shift + Sample Rec** lo para y devuelve todo como estaba.
- **Se pierde al apagar** (vive en la RAM rápida del procesador). No lee la tarjeta: sin el selector de módulos de Arrhythmia.
- Un módulo es código que corre en el aparato: **usa solo módulos en los que confíes.**

<a id="glosario"></a>
## Glosario de funciones

| Función | Qué es / gesto | Capítulo | Desde |
|---|---|---|---|
| **Arpegiador de notas** | arpegia las teclas mantenidas en la vista Note | [2.12 Vista Note](#note) | Alpha 0.0 |
| **Arpegiador de samples** | arpegia los pads de sample mantenidos; Shift + pad 25 de Pattern Settings lo enciende | [2.1 El botón de pista](#pista) | Alpha 0.0 |
| **Bitcrush** | Stock+, Shift + K7 | [2.3 Página Stock+](#stockplus) | Alpha 0.02 |
| **Borrar la automatización de un paso** | Clear + paso en Velocity | [3.1 Velocity y Micro Step](#velocity) | Alpha 0.09 |
| **Borrar un pack** | Clear + pack dos veces en Packs | [6.1 Projects y Packs](#projects) | Alpha 0.01 |
| **Cadenas con reglas** | patrones que se encadenan «n veces A, luego B» | [3.3 Patterns: cadenas](#patterns) | Alpha 0.0 |
| **Carril extra** | una novena automatización, un valor por paso | [2.10 Matriz, Secuenciables y No secuenciables](#matriz) | Alpha 0.10 |
| **Compresor master** | umbral, soft clip, ataque y release en la vista Sidechain | [5.2 FX y Sidechain](#fx) | Alpha 0.0 |
| **Copiar parámetros de pista** | Duplicate + pista A, pista B | [2.1 El botón de pista](#pista) | Alpha 0.0 |
| **Copiar proyectos** | Duplicate + A, Duplicate + B en Projects, también a otro pack | [6.1 Projects y Packs](#projects) | Alpha 0.0 |
| **Copiar samples** | Duplicate + A, Duplicate + B en Sample Rec | [4.2 Sample Rec](#samplerec) | Alpha 0.01 |
| **Cuantizar** | Shift + Play sonando | [1.1 Transporte, metrónomo y cuantizar](#transporte) | Alpha 0.0 |
| **Cuenta atrás** | un compás antes de grabar; Shift + Clear; desde 0.08 con el reloj de la música, también como esclavo | [1.1 Transporte, metrónomo y cuantizar](#transporte) | Alpha 0.0 |
| **Curva de velocity** | Advanced Setup, K1 | [6.2 Setup y Advanced Setup](#setup) | Alpha 0.10 |
| **De-click de redisparos** | sin clic al volver a disparar un sample; Sample mode, pad 19 | [4.1 Sample mode](#samplemode) | Alpha 0.12 |
| **De-clicker de loops** | crossfade en el punto de loop; pad 19 de Sample mode, pad 23 de Sample Rec | [4.1 Sample mode](#samplemode) | Alpha 0.04 |
| **Delay / reverb throw** | tipos nuevos de Grid FX; hueco mantenido + K2 (desde 0.14) | [5.3 Grid FX: secuenciador de efectos y looper](#gridfx) | Alpha 0.13 |
| **Destello de las pistas** | con Shift, el botón de cada pista en blanco al sonar | [2.1 El botón de pista](#pista) | Alpha 0.10 |
| **Dinámicas por paso** | velocity y retraso al azar dentro del paso; fila 3 de la probabilidad | [3.2 Pattern Settings y probabilidad](#patternsettings) | Alpha 0.0 |
| **Distorsión en granular y sinte** | el knob de distorsión del original también en ellos | [2.2 El menú de pista](#menu) | Alpha 0.07 |
| **Enlace estéreo** | una pista y la siguiente como un sonido estéreo; Sample mode, pad 14; desde 0.09 la segunda en desviaciones | [2.11 Entrada de línea y enlace estéreo](#entrada) | Alpha 0.04 |
| **Entrada de línea** | la entrada de audio como sonido de una pista; Sample mode, pads 8 / 16 | [2.11 Entrada de línea y enlace estéreo](#entrada) | Alpha 0.04 |
| **Envolvente + LFO** | la Envolvente y el LFO de Stock+ en una página; menú, pad 5 | [2.6 Páginas Filtro / VCA y Envolvente + LFO](#filtro) | Alpha 0.12 |
| **Envolvente de tono** | Stock+, K1 / K2 | [2.3 Página Stock+](#stockplus) | Alpha 0.01 |
| **Envolvente por modo** | inicio, longitud, pendiente y → filtro del sinte y el granular; menú, pad 5 | [2.9 Página Envolvente](#envolvente) | Alpha 0.06 |
| **Envíos al Grid FX** | cuánto de cada pista pasa por el Grid FX; K1-K8 de la pista de efectos | [5.3 Grid FX: secuenciador de efectos y looper](#gridfx) | Alpha 0.13 |
| **Envíos de FX en los knobs** | ▼ / ▲ en la vista FX | [5.2 FX y Sidechain](#fx) | Alpha 0.0 |
| **Escala propia** | una escala por pista; Shift en la vista Note | [2.12 Vista Note](#note) | Alpha 0.0 |
| **Filtro / VCA** | nivel, envolvente y filtro en una página; menú, pad 4 | [2.6 Páginas Filtro / VCA y Envolvente + LFO](#filtro) | Alpha 0.12 |
| **Fixed Recording con reloj externo** | la duración al tempo del reloj MIDI que llega | [4.2 Sample Rec](#samplerec) | Alpha 0.02 |
| **FM de 8 operadores** | el FM de CIRCUIT-HACKS; Sample mode, selector, pad 24 | [2.7 FM de 8 operadores](#fm) | Alpha 0.12 |
| **Frecuencia por paso** | el paso suena en la última de cada n pasadas | [3.2 Pattern Settings y probabilidad](#patternsettings) | Alpha 0.0 |
| **Fusión USB** | el DIN In también por USB; Advanced Setup, pad 23 | [6.2 Setup y Advanced Setup](#setup) | Alpha 0.04 |
| **FX hacia una entrada** | el retorno que toma una pista de entrada deja el master; su realimentación, a tres cuartos | [2.11 Entrada de línea y enlace estéreo](#entrada) | Alpha 0.09 |
| **Gate por pulsación** | el golpe dura lo que mantienes el pad; Micro Step, pad 32 | [3.1 Velocity y Micro Step](#velocity) | Alpha 0.04 |
| **General MIDI** | las pistas por el canal 10 con su nota GM; Setup, pad 22 | [6.2 Setup y Advanced Setup](#setup) | Alpha 0.04 |
| **Grabación estéreo** | L y R en dos huecos; Sample Rec, pad 24 | [4.2 Sample Rec](#samplerec) | Alpha 0.04 |
| **Granular** | el motor granular en hasta 4 pistas; Sample mode, selector, pad 23; menú pad 2 | [2.4 Página Granular](#granular) | Alpha 0.04 |
| **Guardar al parar** | Save espera a parar; Advanced Setup, pad 24 | [6.2 Setup y Advanced Setup](#setup) | Alpha 0.10 |
| **Inicio y longitud en el granular** | el inicio del original se suma a la posición, la longitud estrecha la zona | [2.4 Página Granular](#granular) | Alpha 0.09 |
| **Latch** | un acorde que sigue a cada nota; Shift + tecla en la vista Note | [2.12 Vista Note](#note) | Alpha 0.12 |
| **LFO de tono** | Stock+, K3 / K4; libre o a tempo | [2.3 Página Stock+](#stockplus) | Alpha 0.01 |
| **Longitud fija** | los golpes a mano con una longitud; Micro Step, pad 31 | [3.1 Velocity y Micro Step](#velocity) | Alpha 0.04 |
| **Looper** | 4 loops grabados de la entrada o la mezcla; vista Grid FX, pads 9-14 | [5.3 Grid FX: secuenciador de efectos y looper](#gridfx) | Alpha 0.13 |
| **Marcas de Velocity** | en el paso marcado los parámetros vuelven a Project init (hasta 0.08, al knob); Shift + paso | [3.1 Velocity y Micro Step](#velocity) | Alpha 0.04 |
| **Matriz de modulación** | 8 fuentes por pista hacia 32 destinos; menú, pad 6 | [2.10 Matriz, Secuenciables y No secuenciables](#matriz) | Alpha 0.10 |
| **Menú de pista** | tocar el botón de la pista elegida (se queda abierto) o mantener el de una pista | [2.2 El menú de pista](#menu) | Alpha 0.04 |
| **Metrónomo** | cuatro estados con Shift + Clear | [1.1 Transporte, metrónomo y cuantizar](#transporte) | Alpha 0.0 |
| **Metrónomo visual** | Clear destella en naranja en cada clic con el nivel del clic a 0 (K5 de Tempo / Swing) | [1.1 Transporte, metrónomo y cuantizar](#transporte) | Alpha 0.08 |
| **Modificadores del arpegio** | octavas, groove y reinicio; Pattern Settings, Shift + pads 1-16 | [3.2 Pattern Settings y probabilidad](#patternsettings) | Alpha 0.10 |
| **Modo cue** | mezcla a la izquierda, cue a la derecha; Mixer, panoramas, Shift + knob | [5.1 Mixer](#mixer) | Alpha 0.04 |
| **Modos de voz** | retrigger, legato, glide, unísonos y poly; Sample mode, pad 16 mantenido | [2.8 Voz: modos, polifonía y unísono](#voces) | Alpha 0.12 |
| **Módulos de Arrhythmia** | prueba de concepto: sus `.mod` por USB desde la app de la tarjeta; Shift + Sample Rec para | [A.3 Módulos de Arrhythmia (prueba de concepto)](#modulos) | Alpha 0.11 |
| **Mutación del sample** | a veces suena el vecino; fila 4 de la probabilidad | [3.2 Pattern Settings y probabilidad](#patternsettings) | Alpha 0.0 |
| **Mute al compás** | Shift + pad de pista en el Mixer | [5.1 Mixer](#mixer) | Alpha 0.0 |
| **Nivel a 100 / 0** | Shift + knob en los niveles del Mixer | [5.1 Mixer](#mixer) | Alpha 0.0 |
| **No secuenciables** | 8 knobs que nunca se graban; menú, Shift + pad 1 | [2.10 Matriz, Secuenciables y No secuenciables](#matriz) | Alpha 0.10 |
| **Nudge** | mueve el tramo elegido un paso; pad 26 de Pattern Settings | [3.2 Pattern Settings y probabilidad](#patternsettings) | Alpha 0.0 |
| **Órdenes fractal / deconstruido** | pads 27 / 28 de Pattern Settings | [3.2 Pattern Settings y probabilidad](#patternsettings) | Alpha 0.0 |
| **Página Stock+** | ocho knobs más por pista; menú, pad 10; desde 0.07 también en el granular y el sinte | [2.3 Página Stock+](#stockplus) | Alpha 0.01 |
| **Patches del pack** | 64 patches de sinte y granular por pack; Sample mode, pad 8 mantenido | [4.3 Patches del pack y starters](#patches) | Alpha 0.13 |
| **Pattern Mutate** | listas de patrones al azar por pista (diseño de mefisme); Shift + Duplicate | [3.4 Pattern Mutate](#mutate) | Alpha 0.13 |
| **Polifonía** | hasta 4 voces de sinte (VA o FM); Sample mode, un toque al pad 16 | [2.8 Voz: modos, polifonía y unísono](#voces) | Alpha 0.12 |
| **Program Change** | canales de escucha y salida; Setup, pads 29 / 30 | [6.2 Setup y Advanced Setup](#setup) | Alpha 0.0 |
| **Project init** | la voz de la pista como se cargó o guardó; menú, pad 16 (rojo; hasta 0.11, pad 8) | [2.2 El menú de pista](#menu) | Alpha 0.09 |
| **Rampas** | paso amarillo mantenido + otro paso, en la vista de automatización | [3.1 Velocity y Micro Step](#velocity) | Alpha 0.10 |
| **Repetir la escena** | la escena actual 1-8 veces; Mixer, Shift + pads 9-16 | [5.1 Mixer](#mixer) | Alpha 0.0 |
| **Reset de knobs de pista** | Clear + botón de la pista | [2.1 El botón de pista](#pista) | Alpha 0.0 |
| **Resonancia master** | Shift + ▲ / ▼ en la vista FX | [5.2 FX y Sidechain](#fx) | Alpha 0.0 |
| **Retornos de FX como fuente** | la reverb o el delay como sonido de una pista de entrada; Sample mode, selector, pads 2 / 3 | [2.11 Entrada de línea y enlace estéreo](#entrada) | Alpha 0.06 |
| **Ring mod** | Stock+, K5 (Shift: la frecuencia) | [2.3 Página Stock+](#stockplus) | Alpha 0.02 |
| **Scan** | mueve el inicio de cada nota o del loop; Stock+, K8 | [2.3 Página Stock+](#stockplus) | Alpha 0.02 |
| **Secuenciables** | los 8 carriles de automatización con destino propio; menú, pad 1 | [2.10 Matriz, Secuenciables y No secuenciables](#matriz) | Alpha 0.10 |
| **Secuenciador de efectos** | una pista toca los Grid FX; Sample mode, selector, pad 21 | [5.3 Grid FX: secuenciador de efectos y looper](#gridfx) | Alpha 0.13 |
| **Selector de motores** | sample, entrada, VA, granular o FM en la fila 3; Sample mode, pad 8 | [4.1 Sample mode](#samplemode) | Alpha 0.12 |
| **Sidechain por knobs** | K1-K4 de la vista Sidechain | [5.2 FX y Sidechain](#fx) | Alpha 0.0 |
| **Sinte** | desde 0.12 el VA de CIRCUIT-HACKS (OSC 1 / OSC 2); Sample mode, selector, pad 20; menú pads 2 / 3 | [2.5 Páginas OSC 1 / OSC 2 (el VA)](#sinte) | Alpha 0.05 |
| **Snapshot** | los knobs movidos, a un paso; Record mantenido + paso | [3.1 Velocity y Micro Step](#velocity) | Alpha 0.09 |
| **Sobremuestreo 2×** | el VA con menos aliasing; Sample mode, selector, pad 4 | [2.5 Páginas OSC 1 / OSC 2 (el VA)](#sinte) | Alpha 0.13 |
| **Sonido del proyecto en la tarjeta** | el FM, los modos de voz y los valores del VA con el proyecto, en el banco de patches | [A.1 Qué se guarda y dónde](#guardado) | Alpha 0.12 |
| **Starters** | sonidos de partida por motor; Sample mode, pad de motor mantenido | [4.3 Patches del pack y starters](#patches) | Alpha 0.13 |
| **Stretch** | más lento o rápido sin cambiar el tono; Stock+ K7, Sample mode pads 9 / 10 | [2.3 Página Stock+](#stockplus) | Alpha 0.02 |
| **Teclado externo al arpegiador** | Advanced Setup, pad 22 | [6.2 Setup y Advanced Setup](#setup) | Alpha 0.04 |
| **Thru: Out 2 / Merge / Filter** | Duplicate en Advanced Setup | [6.2 Setup y Advanced Setup](#setup) | Alpha 0.0 |
| **Tipo de filtro (24 dB, comb)** | Stock+, Shift + K6 | [2.3 Página Stock+](#stockplus) | Alpha 0.02 |
| **Umbral del compresor** | K5 de la vista Sidechain | [5.2 FX y Sidechain](#fx) | Alpha 0.01 |
| **Unísono** | las voces de una pista en la misma nota, desafinadas; pad 16 mantenido, K2 | [2.8 Voz: modos, polifonía y unísono](#voces) | Alpha 0.12 |
| **Vista de automatización** | los pasos con automatización de knobs en amarillo, y escucharlos; Velocity + Shift, o Velocity otra vez (fija) | [3.1 Velocity y Micro Step](#velocity) | Alpha 0.09 |
| **Waveshaper** | suave, duro, plegado o bitcrush en el granular y el sinte; Stock+, K7 (Shift: el tipo) | [2.3 Página Stock+](#stockplus) | Alpha 0.07 |
