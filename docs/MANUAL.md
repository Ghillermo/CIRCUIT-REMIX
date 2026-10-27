# Circuit Remix Alpha 0.04 — manual

[English](MANUAL_EN.md)

> ⚠️ **Alpha 0.04 es experimental y necesita pulirse:** lo marcado «(Alpha 0.04)» se ha comprobado sobre todo en emulación. Para tocar en serio, Alpha 0.03.

Funciones de Circuit Remix en el Circuit Rhythm (firmware 2.0.1, build 5706), vista por vista. Todo lo demás funciona como en el firmware original de Novation; los gestos nuevos son combinaciones que en el original no hacían nada o repetían el gesto sin modificador.

**Convenciones.** Pads 1-32 de izquierda a derecha y de arriba abajo: fila 1 = pads 1-8, fila 2 = 9-16, fila 3 = 17-24, fila 4 = 25-32. Knobs K1-K8. ▲ / ▼ = los botones de flecha.

**Exclusivas** de Circuit Remix (no están en CIRCUIT-HACKS): marcadas con ★.

## 1. Transporte, metrónomo y cuantizar
| Gesto | Qué hace |
|---|---|
| **Shift + Clear** | recorre cuatro estados; con Shift mantenido, el LED de Clear: rojo = sin metrónomo, verde = metrónomo, magenta = solo cuenta atrás, cian = las dos |
| **Record armado + Play** (parado, con cuenta atrás) | un compás de clics al tempo del proyecto (Record parpadea) y arranca grabando; Play durante la cuenta la cancela |
| **Shift + Play** (parado, con cuenta atrás) | la cuenta y luego sigue desde donde se paró (el Shift + Play del original) |
| **Shift + Play** (sonando) | cuantiza a sus pasos el patrón de la pista elegida: los golpes de los micropasos 2-3 van al comienzo de su paso, los de 4-6 al del paso siguiente; los redobles se quedan. LED de Play con Shift: amarillo; verde tras cuantizar; rojo = no se ha tocado nada |

Desde Alpha 0.04 la reproducción empieza antes (≈ 10 ms de Play al primer sonido; el original ≈ 18 ms), las notas de un mismo paso suenan juntas y el reloj no tropieza al guardar un sample.

Parado, Shift + Play sin cuenta atrás es el del original (reproducir desde donde se paró). La cuenta atrás no se guarda: al encender vuelve a «sin cuenta atrás».

### A0.04F / A04FS: la cuenta atrás con el reloj de la música
En las versiones A0.04F y A04FS, la cuenta atrás y el metrónomo de arriba funcionan con estos cambios:

| | A0.04F / A04FS |
|---|---|
| **Tiempo** | los clics siguen el reloj que sigue la música: el tempo del proyecto, o el reloj MIDI externo como esclavo. Play entra al empezar la cuenta y el arranque del reloj queda en espera; la música arranca en el propio pulso del reloj tras el 4.º clic, así que el 1 cae a tiempo |
| **Durante la cuenta** | no se graba nada y el LED de Play sigue como parado hasta el 1. Record parpadea en rojo en cada clic |
| **Esclavo** | el primer clic llega en el siguiente compás del maestro cuando el Rhythm conoce su posición (recibió su Start o Song Position); si no, en el primer pulso de reloj tras la pulsación. Un Start del maestro durante la cuenta la para |
| **Metrónomo visual** | con el nivel del clic a 0 (K5 de la vista Tempo / Swing), Clear destella 100 ms en cada clic de la cuenta, y en cada tiempo mientras suena con el metrónomo o la cuenta atrás activos, en el color del estado (verde, magenta, cian). No mientras se mantiene Shift o Clear |
| **Luz de error** | Clear parpadea en rojo (250 ms encendido, 250 ms apagado) si alguna de estas funciones no puede funcionar con el firmware que encuentra |

Shift + Play (la cuenta y luego la reproducción desde donde se paró) y Play durante la cuenta (la cancela) funcionan como arriba. Play además carga los pasos más rápido (el mismo resultado con la cuarta parte de las llamadas).

## 2. Mixer
| Gesto | Qué hace |
|---|---|
| **Shift + pad de pista** (fila 1) | mute de esa pista en el compás siguiente (el pad parpadea; otra vez = cancelar; parado, al momento) |
| **Shift + knob** (página de niveles) | a la derecha = nivel 100; a la izquierda = 0. Grabando, queda como automatización |
| **Shift + pads 9-16** | la escena actual se repite 1-8 veces (con Shift la fila 2 en amarillo, el elegido en verde; las escenas con reglas de cadena, melocotón). Sonando, con Shift, la vuelta que suena se ve en blanco; en la última, el pad verde parpadea |
| **Página de panoramas** (botón 19), **Shift + knob** a la derecha / izquierda (Alpha 0.04) | ★ **modo cue** encendido / apagado (botón 19 en rosa): la mezcla sale por la salida izquierda y el cue por la derecha (para escuchar con un cable en Y) |
| **Página de panoramas en el modo cue, knob** (Alpha 0.04) | el envío al cue de su pista (knobs en rosa, brillo = envío); una pista silenciada con envío suena solo en el cue; Clear + knob = 0 |

El pad 9 sin Shift sigue siendo el Mute Recall del original. El modo cue no se guarda.

## 3. Vista de pista (samples)
| Gesto | Qué hace |
|---|---|
| **Clear + botón de la pista** (en su vista) | ★ sus knobs a su valor por defecto y su automatización borrada; el resto de parámetros (nivel, panorama, envíos, sidechain) y el sample elegido vuelven a como estaban al cargar el proyecto |
| **Duplicate + pista A, luego pista B** | ★ B recibe los parámetros de A (knobs, nivel, panorama, envíos, sidechain) y su sample elegido; con Duplicate mantenido, más pistas reciben la copia |
| **Pads de sample mantenidos** (arpegiador encendido) | ★ arpegio de los samples mantenidos (también uno solo): cada golpe cambia el sample como un sample flip, con la velocity de su pad. En marcha, a la rejilla; parado, al tempo. Con Record y Play, se graba en el patrón |

Con un paso mantenido, el pad de sample es el sample flip del original. Desde el Mixer, Clear + pista hace lo del original.

### Menú de pista (Alpha 0.04)
**Mantén el botón de una pista** (en las vistas de pista) un momento: los pads 1-7 son un menú para esa pista; al soltar el botón, se cierra.

| Pad | Qué hace |
|---|---|
| 1 / 2 / 3 | página de knobs **stock** / **Stock+** / **Granular**. El pad 3 pone además el granular en la pista (hasta 4 pistas; con 4 ya puestas, nada) |
| 4 | el granular de la pista encendido / apagado (las demás pistas granulares siguen) |
| 5 | ★ la **entrada de línea** como sonido de la pista (hasta dos pistas: una sola = L + R; dos = la de número menor L, la mayor R; en una tercera sale la primera puesta). Le quita el granular |
| 6 | el gate de la pista de entrada: tenue = siempre suena, encendido = solo con sus notas (oscuro si la pista no es de entrada) |
| 7 | ★ **enlace estéreo**: la pista (izquierda, su sample) y la siguiente (derecha, el sample siguiente) suenan juntas con los parámetros de la primera; pad 7 en cualquiera de las dos = deshacer (en la pista 8, nada) |

Elegir la página stock o Stock+ deja el granular sonando. Pulsar el botón de la pista sin mantenerlo la elige, como en el original.

### Página Stock+ de los knobs (desde Alpha 0.01; K5-K8 desde Alpha 0.02)
**Menú de pista, pad 2** (hasta Alpha 0.03: pulsar otra vez el botón de la pista elegida): sus 8 knobs pasan a la página Stock+; pad 1, vuelven a la de stock. Mientras está en Stock+, el botón de la pista parpadea en blanco. La página es por pista y se queda hasta apagar.

| Knob | En la página Stock+ | Con Shift |
|---|---|---|
| K1 | ★ cantidad de la envolvente de tono: centro = nada; a la derecha cada golpe empieza más agudo, a la izquierda más grave (hasta ±24 semitonos), y vuelve a su nota | ajuste fino |
| K2 | ★ lo que tarda en volver a la nota (de 5 ms a 4 s) | ajuste fino |
| K3 | ★ velocidad del LFO de tono desde el centro (Alpha 0.04): centro = apagado, derecha = libre (0,05 a 30 Hz), izquierda = a tempo (16 divisiones, de 1/16T a 8 compases; el ciclo empieza en el primer tiempo) | ajuste fino |
| K4 | ★ profundidad del LFO de tono (de 0 a 24 semitonos) | ajuste fino |
| K5 | ★ cantidad del ring mod | ★ su frecuencia (20 Hz-5 kHz) |
| K6 | ★ pitch follow: el corte del paso bajo del stock sube y baja con la nota | ★ tipo de filtro, sobre los knobs de filtro del stock: **stock** (sin cambios), **24 dB** (el paso bajo y el paso alto del stock, más pronunciados) o **comb** (el corte da su tono y la resonancia su realimentación) |
| K7 | ★ **stretch**: la pista suena más lenta (izquierda, hasta 0,25×) o más rápida (derecha, hasta 4×) sin cambiar de tono; el centro = como el stock | ★ bitcrush |
| K8 | ★ velocidad del scan, un LFO que mueve el punto de inicio de cada nota; desde Alpha 0.04 desde el centro: centro = quieto, derecha = libre (0,05 a 20 Hz), izquierda = a tempo (16 divisiones). En un loop mueve el inicio del loop en cada vuelta | ★ su profundidad |

- **Shift:** en K1-K4 es el ajuste fino, como en los knobs de stock; en K5-K8 es la segunda función, y mientras lo mantienes sus LEDs enseñan esa segunda capa.
- **Clear + knob:** su valor por defecto. En K5-K8 vuelven las dos capas (con y sin Shift).
- **LEDs:** los knobs en blanco con el brillo según su valor (K1 y K7: la distancia al centro). K6 va del color de su tipo de filtro: stock blanco, 24 dB el color del delay de la vista FX, comb el de la reverb.
- **Proyecto:** se guarda con él; un proyecto sin estos valores suena sin modulación (los de Alpha 0.01 cargan como estaban). Clear + botón de la pista los deja por defecto y Duplicate + pista A, pista B los copia.
- **El stretch** reparte el sample en granos de unos 43 ms que se solapan y se mantienen en fase (WSOLA). A 0,5× suena muy bien; a 0,25× la batería puede sonar con clics, porque cada golpe se repite. Probado con todo encendido en las 8 pistas a la vez, más reverb y delay.
- El tono de cada voz se recalcula unas 190 veces por segundo y al empezar cada golpe: con una caída muy corta (K2 a la izquierda del todo) o un LFO muy rápido puede notarse escalonado.
- En proyectos de Alpha 0.02 / 0.03, K3 o K8 movidos pueden sonar distinto (ahora van desde el centro).

### Página Granular (Alpha 0.04)
El motor granular de CIRCUIT-HACKS sobre el sample de la pista (menú, pad 3). Sigue la nota (vista Note, teclado y MIDI); los knobs de filtro (paso alto, paso bajo, resonancia) y la envolvente de la pista actúan sobre él. Hasta **4 pistas granulares a la vez**, cada una con sus ajustes; los granos se reparten (16 con una pista, 7 por pista con dos, 4 con tres, 2 con cuatro).

| Knob | Solo | Con Shift |
|---|---|---|
| K1 | tamaño del grano (5-500 ms) | fino |
| K2 | densidad (1-16 granos) | ★ apertura estéreo (0 = mono) |
| K3 | posición en el sample | fina |
| K4 | scan: el cabezal avanza o retrocede (centro = quieto) | fino |
| K5 | altura (centro = la nota; ±24 semitonos) | altura fina |
| K6 | dispersión de la posición | zona (qué parte del sample) |
| K7 | dispersión de la altura | probabilidad de reverso |
| K8 | ventana (rectángulo → triángulo → percusiva) | gate: a la izquierda = siempre suena (drone); si no, lo abren las notas de la pista |

Clear + knob = su valor por defecto. Se guarda con el proyecto (los proyectos de Alpha 0.03 no tienen granular).


## 4. Vista Note
| Gesto | Qué hace |
|---|---|
| **Teclas mantenidas** (arpegiador encendido) | ★ arpegio de las notas mantenidas sobre el sample de la pista; con Record y Play, se graba |
| **Shift mantenido** | ★ editor de la **escala propia de la pista**: los 32 pads son dos octavas de piano desde la tónica (fila 4 = teclas blancas de la octava de abajo, el pad 25 = la tónica; fila 3 = sus negras; filas 2 / 1 = la octava de arriba). Cada tecla enciende o apaga su grado (7 como máximo); la más alta es el **periodo**: la tónica de la siguiente iteración (la octava o cualquier otra, hasta 24 semitonos). LEDs: tónica blanca, grados verdes, periodo azul |

Al soltar Shift, el teclado toca la escala: **una iteración por fila** (dos si tiene 4 notas o menos); ▲ / ▼ mueven una fila. Una escala por pista; sin teclas, vuelve el piano del original. Se guarda con el proyecto.

## 5. Pattern Settings
| Gesto | Qué hace |
|---|---|
| **Pad 26** (azul) | Nudge: el patrón se reescribe para que su primer paso sea el 1 (pasos y automatización rotan; suena igual) |
| **Pad 27 / 28** | órdenes de reproducción **fractal** (1 · 1 2 · 1 2 3 …) y **deconstruido** (1 6 11 16 · 2 7 12 13 · …); un pad de dirección vuelve al original |
| **Pad 25** (gris) | vista de probabilidad, modo 2: elige un paso; **fila 3 = dinámicas** (velocity y retraso dentro del paso; **con Record, cada paso con dinámicas que suena queda escrito** con la velocity y el micropaso con que sonó, y pierde sus dinámicas), **fila 4, pads 25-28 = mutación del sample** (a veces suena el vecino de su fila o el de la otra fila de su página) |
| **Pattern Settings dos veces** | vista de probabilidad, modo 1: **fila 4 = frecuencia** del paso (suena una de cada n pasadas) |
| **Shift + pad 25** | arpegiador de la pista y patrón encendido / apagado (verde / gris con Shift) |
| **Shift + pads 27-32** | orden del arpegio: fractal, deconstruido, arriba, abajo, ping-pong, aleatorio |
| **Clear + pad 25** (Alpha 0.04) | borra las dinámicas y la mutación del patrón (la frecuencia se queda) |
| **Shift + pads 17-24** | resolución del arpegio (1/4 … 1/32T); otra vez la misma = el sync rate de la pista |

Los valores por paso viajan con el golpe al cuantizar, al hacer Nudge, al copiar un paso (Duplicate + paso A + paso B) y con el Mutate del original (Shift + Duplicate).

## 6. Vista Patterns: cadenas
| Gesto | Qué hace |
|---|---|
| **Shift + botón de página de arriba** | modo cadena (verde) |
| En el modo: **un patrón** (A), **otra vez** (n + 1 pasadas), **otro** (B), **otro más** (C) | regla «n veces A, luego B; la vez siguiente, C» (AAB AAC …) |
| **Clear + patrón** | sin regla |
| **Shift + botón de página de abajo** | fuera del modo: la cadena del original |

Cada escena recuerda el modo con que se guardó. Las reglas se guardan con el proyecto.

## 7. Vista FX
| Gesto | Qué hace |
|---|---|
| **▼ / ▲** | los knobs pasan a los envíos de **reverb** / **delay** de las 8 pistas sin cambiar el preset (▼ crema, ▲ melocotón; la página en pantalla, fuerte) |
| **Shift + knob**, página de delay | K1 time, K2 sync, K3 feedback, K4 width, K5 ratio, K6 slew |
| **Shift + knob**, página de reverb | K1 tipo (6), K2 decay, K3 damping |
| **Shift + ▲ / ▼** | resonancia del filtro master ±16 (amarillos con Shift) |
| **Duplicate** (azul claro) | reset: envíos de reverb y delay a 0, filtro master al centro |
| **Clear + knob** | el envío de esa pista en la página visible a 0 |

Con Shift, el brillo de cada knob muestra el valor de su parámetro. Los parámetros de reverb y delay se guardan con el proyecto; la resonancia es global (del aparato).

## 8. Vista Sidechain (Shift + FX)
| Knob | Qué mueve |
|---|---|
| K1-K4 | ataque, hold, decay y profundidad del sidechain de la pista elegida (la del último pad de preset tocado) |
| K5 | umbral del compresor master (a tope = el del stock; a la izquierda comprime desde más abajo) |
| K6 | soft clip del compresor master (derecha = encendido) |
| K7 / K8 | ataque / release del compresor master |

Un pad de preset devuelve la pista a ese preset. **Clear + K1-K4** = los valores de su preset; **Clear + K6-K8** = el compresor de fábrica; **Clear + K5** = el umbral del stock. Cada Clear + knob afecta solo a ese knob. El brillo muestra el valor. Se guarda con el proyecto. El compresor solo se oye si está encendido (Advanced Setup).

## 9. Vista Projects: copiar proyectos (no en Alpha 0.01S)
Con el transporte parado:
1. **Duplicate + pad con proyecto (A)**: parpadea en amarillo.
2. **Duplicate + pad vacío (B)**: copia A en B (verde ~1,5 s y luego el color de A). B puede estar en este pack o en otro: elige A, carga otro pack y Duplicate + un pad vacío.
3. **Duplicate + un pad con proyecto**: parpadea en blanco (pregunta); **Duplicate + el mismo pad** antes de ~5 s lo sobrescribe.

Nunca sobrescribe el proyecto cargado ni escribe en el pack de la memoria interna (rojo + LED de Save rojo). Alpha 0.01S no tiene esta función.

**Diferencias con Save + pad** (el guardado del stock, que guarda en cualquier pad):
| | Duplicate + A, Duplicate + B | Save + pad |
|---|---|---|
| Qué copia | el proyecto A **tal como está guardado** en la tarjeta | el proyecto **cargado, tal como está en memoria** (con los cambios sin guardar) |
| Hay que cargar A | no: lo que tienes cargado (y sus cambios sin guardar) se queda | sí: solo guarda el proyecto cargado |
| Desde otro pack | sí: eliges A, cargas otro pack y lo copias ahí | — (lo que guarda es lo cargado) |
| Si B tiene proyecto | pregunta (parpadeo blanco) y nunca toca el proyecto cargado | como el stock |
| Transporte | solo parado | como el stock |

### Packs (Projects dos veces): borrar un pack (no en Alpha 0.01S)
Con el transporte parado: **Clear + el pad de un pack** = pregunta (parpadea en rojo ~5 s); **Clear + el mismo pad** antes de ~5 s = borra el pack de la tarjeta (verde ~1,5 s). Nunca el pack cargado, ni el de la memoria interna, ni un hueco vacío.

### Sample Rec: copiar un sample (no en Alpha 0.01S)
Con el transporte parado:
1. **Duplicate + hueco con sample (A)**: parpadea en amarillo (Duplicate + A otra vez = olvidarlo).
2. **Duplicate + hueco B** (de este pack o, tras cargar otro pack, de ese): copia el sample de A en B y B suena al momento (verde ~1,5 s). Si B tiene sample, parpadea en blanco y **Duplicate + B** otra vez antes de ~5 s lo sobrescribe.

Rojo = no se ha podido (memoria de samples llena, el aparato ocupado o el pack interno).

## 10. Setup (Shift + Save)
| Gesto | Qué hace |
|---|---|
| **Advanced Setup, Duplicate** | la toma Thru recorre **Thru** (verde) → **Out 2** (rojo tenue) → **Merge** (amarillo: MIDI In + el MIDI del aparato) → **Filter** (azul: MIDI In menos los canales en los que escucha el aparato) |
| **Pad 29** (la primera vez) | los pads 1-16 muestran el **canal de escucha de Program Change** (16 de fábrica); un pad lo cambia; el pad 29 otra vez = PGM Rx encendido / apagado |
| **Pad 30** (la primera vez) | lo mismo con el **canal de salida** de Program Change |
| **Pad 22** (Alpha 0.04) | **modo General MIDI** del proyecto (verde = encendido): las pistas salen por el canal 10 con su nota GM; las notas GM que entran por el canal 10 tocan su pista |
| **K1-K8, con el modo GM** (Alpha 0.04) | la nota GM de cada pista (35-81, dos clics por nota; cada nota nueva suena una vez por el canal 10). De fábrica: 36, 38, 42, 46, 39, 37, 45, 49 |
| **Advanced Setup, pad 22** (Alpha 0.04) | teclado externo al arpegiador: las notas que entran por el canal de una pista con el arpegiador encendido se arpegian (verde = encendido) |
| **Advanced Setup, pad 23** (Alpha 0.04) | fusión USB: lo que entra por el DIN In sale también por USB (sin el reloj si Clock Tx está encendido) |

Si los dos canales son distintos, el Program Change recibido se reenvía por el de salida (con PGM Tx encendido). Todo se guarda en los ajustes del aparato (desde Alpha 0.04 también los canales de Program Change y el modo del Thru, que el original no guardaba si no cambiaba otro ajuste).

## 11. Sample mode y Sample Rec (Alpha 0.04)
| Vista | Gesto | Qué hace |
|---|---|---|
| Sample mode (Samples) | **pads 1 / 2** (originales) | ajustan el sample al patrón cambiando el tono; ahora apagan antes el stretch de la pista |
| Sample mode | **pads 9 / 10** | ★ lo mismo con el **stretch** (K7 de Stock+), sin cambiar el tono: la longitud siguiente / la anterior |
| Sample mode | **pad 19** | ★ de-clicker del loop de la pista elegida (crossfade de 256 muestras) encendido / apagado; encendido por defecto, se guarda con el proyecto |
| Sample Rec | **pad 23** | ★ de-clicker de los loops de todas las pistas (encendido al arrancar) |
| Sample Rec | **pad 24** | ★ **grabación estéreo**: L en el hueco elegido, R en el siguiente (que debe estar vacío; si no, solo el primero, en mono). Apagada al arrancar |

Los loops muy cortos suenan ahora a su longitud (en el original se repetían cada ~128 muestras y leían más allá de su final).

## 12. Velocity y Micro Step (Alpha 0.04)
| Vista | Gesto | Qué hace |
|---|---|---|
| Velocity (botón 10) | **Shift + paso** | marca el paso: al sonar, ningún carril de automatización suena ahí y los parámetros automatizados vuelven a la posición de su knob (con Shift, pasos en amarillo, los marcados en rojo) |
| Micro Step (Shift + Gate) | **pad 31** | longitud fija: apagada → el selector en los pads 17-32 (1-16 pasos; elegir una la enciende); encendida → apagada (naranja = encendida) |
| Micro Step | **pad 32** | gate por pulsación: el golpe dura lo que mantienes el pad del paso; mantener un paso vacío 300 ms o más también crea el golpe (verde = encendido) |

Con la longitud fija o el gate por pulsación, un golpe introducido a mano en los pasos toma esa longitud.

## 13. Seguridad y recuperación
- El mod nunca escribe en el **pack de la memoria interna**: sus escrituras lo rechazan con el LED de Save en rojo 1,5 s. Lo que guarda el firmware original sigue igual.
- Lo propio del mod que va con el proyecto se guarda en el fichero de proyecto, en una zona que el original no usa. Todavía no se ha comprobado cómo carga el firmware original un proyecto guardado con Circuit Remix: guarda copias de tus proyectos.
- **Recuperación:** mantén **Sample Rec + Samples + Note** al encender (modo bootloader de Novation) y envía el firmware oficial con el instalador («Oficial») o con Novation Components.
