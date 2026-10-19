# Circuit Remix Alpha 0.0 — manual

[English](MANUAL_EN.md)

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

Parado, Shift + Play sin cuenta atrás es el del original (reproducir desde donde se paró). La cuenta atrás no se guarda: al encender vuelve a «sin cuenta atrás».

## 2. Mixer
| Gesto | Qué hace |
|---|---|
| **Shift + pad de pista** (fila 1) | mute de esa pista en el compás siguiente (el pad parpadea; otra vez = cancelar; parado, al momento) |
| **Shift + knob** (página de niveles) | a la derecha = nivel 100; a la izquierda = 0. Grabando, queda como automatización |
| **Shift + pads 9-16** | la escena actual se repite 1-8 veces (con Shift la fila 2 en amarillo, el elegido en verde; las escenas con reglas de cadena, melocotón) |

El pad 9 sin Shift sigue siendo el Mute Recall del original.

## 3. Vista de pista (samples)
| Gesto | Qué hace |
|---|---|
| **Clear + botón de la pista** (en su vista) | ★ sus knobs a su valor por defecto y su automatización borrada; el resto de parámetros (nivel, panorama, envíos, sidechain) y el sample elegido vuelven a como estaban al cargar el proyecto |
| **Duplicate + pista A, luego pista B** | ★ B recibe los parámetros de A (knobs, nivel, panorama, envíos, sidechain) y su sample elegido; con Duplicate mantenido, más pistas reciben la copia |
| **Pads de sample mantenidos** (arpegiador encendido) | ★ arpegio de los samples mantenidos (también uno solo): cada golpe cambia el sample como un sample flip, con la velocity de su pad. En marcha, a la rejilla; parado, al tempo. Con Record y Play, se graba en el patrón |

Con un paso mantenido, el pad de sample es el sample flip del original. Desde el Mixer, Clear + pista hace lo del original.

## 4. Vista Note
| Gesto | Qué hace |
|---|---|
| **Teclas mantenidas** (arpegiador encendido) | ★ arpegio de las notas mantenidas sobre el sample de la pista; con Record y Play, se graba |
| **Shift mantenido** | ★ editor de la **escala propia de la pista**: los 32 pads son dos octavas de piano desde la tónica (fila 4 = teclas blancas de la octava de abajo, el pad 25 = la tónica; fila 3 = sus negras; filas 2 / 1 = la octava de arriba). Cada tecla enciende o apaga su grado (7 como máximo); la más alta es el **periodo**: la tónica de la siguiente iteración (la octava o cualquier otra, hasta 24 semitonos). LEDs: tónica blanca, grados verdes, periodo azul |

Al soltar Shift, el teclado toca la escala: **una iteración por fila** (dos si tiene 4 notas o menos); ▲ / ▼ mueven una fila. Una escala por pista; sin teclas, vuelve el piano del original. Se guarda con el proyecto.

## 5. Pattern Settings
| Gesto | Qué hace |
|---|---|
| **Pad 26** (naranja) | Nudge: el patrón se reescribe para que su primer paso sea el 1 (pasos y automatización rotan; suena igual) |
| **Pad 27 / 28** | órdenes de reproducción **fractal** (1 · 1 2 · 1 2 3 …) y **deconstruido** (1 6 11 16 · 2 7 12 13 · …); un pad de dirección vuelve al original |
| **Pad 25** (melocotón) | vista de probabilidad, modo 2: elige un paso; **fila 3 = dinámicas** (velocity y retraso dentro del paso), **fila 4, pads 25-28 = mutación del sample** (a veces suena el vecino de su fila o el de la otra fila de su página) |
| **Pattern Settings dos veces** | vista de probabilidad, modo 1: **fila 4 = frecuencia** del paso (suena una de cada n pasadas) |
| **Shift + pad 25** | arpegiador de la pista y patrón encendido / apagado (verde / gris con Shift) |
| **Shift + pads 27-32** | orden del arpegio: fractal, deconstruido, arriba, abajo, ping-pong, aleatorio |
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
| K6 | soft clip del compresor master (derecha = encendido) |
| K7 / K8 | ataque / release del compresor master |

Un pad de preset devuelve la pista a ese preset. **Clear + K1-K4** = los valores de su preset; **Clear + K6-K8** = el compresor de fábrica. El brillo muestra el valor. Se guarda con el proyecto. El compresor solo se oye si está encendido (Advanced Setup).

## 9. Vista Projects: copiar proyectos (solo Alpha 0.0)
Con el transporte parado:
1. **Duplicate + pad con proyecto (A)**: parpadea en amarillo.
2. **Duplicate + pad vacío (B)**: copia A en B (verde ~1,5 s y luego el color de A). B puede estar en este pack o en otro: elige A, carga otro pack y Duplicate + un pad vacío.
3. **Duplicate + un pad con proyecto**: parpadea en blanco (pregunta); **Duplicate + el mismo pad** antes de ~5 s lo sobrescribe.

Nunca sobrescribe el proyecto cargado ni escribe en el pack de la memoria interna (rojo + LED de Save rojo). Alpha 0.0S no tiene esta función.

## 10. Setup (Shift + Save)
| Gesto | Qué hace |
|---|---|
| **Advanced Setup, Duplicate** | la toma Thru recorre **Thru** (verde) → **Out 2** (rojo tenue) → **Merge** (amarillo: MIDI In + el MIDI del aparato) → **Filter** (azul: MIDI In menos los canales en los que escucha el aparato) |
| **Pad 29** (la primera vez) | los pads 1-16 muestran el **canal de escucha de Program Change** (16 de fábrica); un pad lo cambia; el pad 29 otra vez = PGM Rx encendido / apagado |
| **Pad 30** (la primera vez) | lo mismo con el **canal de salida** de Program Change |

Si los dos canales son distintos, el Program Change recibido se reenvía por el de salida (con PGM Tx encendido). Todo se guarda en los ajustes del aparato.

## 11. Seguridad y recuperación
- El mod nunca escribe en el **pack de la memoria interna**: sus escrituras lo rechazan con el LED de Save en rojo 1,5 s. Lo que guarda el firmware original sigue igual.
- Lo propio del mod que va con el proyecto se guarda en el fichero de proyecto, en una zona que el original no usa. Todavía no se ha comprobado cómo carga el firmware original un proyecto guardado con Circuit Remix: guarda copias de tus proyectos.
- **Recuperación:** mantén **Sample Rec + Samples + Note** al encender (modo bootloader de Novation) y envía el firmware oficial con el instalador («Oficial») o con Novation Components.
