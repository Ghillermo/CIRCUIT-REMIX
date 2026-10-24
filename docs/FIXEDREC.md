# Fixed Recording al tempo del reloj MIDI externo

Circuit Rhythm 2.0.1 (build 5706). Versiones: **A0.01F** (Alpha 0.01 + este arreglo) y **A01FS** (Alpha 0.01S + este arreglo).

> **English:** [`FIXEDREC_EN.md`](FIXEDREC_EN.md).

## Qué hace

Con un reloj MIDI externo (por ejemplo, un Circuit Tracks como maestro y el Rhythm como esclavo), **Fixed Recording** en la vista Sample Rec usa el tempo del reloj que llega. Sin reloj externo, usa el tempo del proyecto, como el firmware original.

Pads de Fixed Recording, vista Sample Rec, fila 3:

| Pad | Función |
|---|---|
| 17 | Fixed Recording sí / no |
| 18 | ½ compás |
| 19 | 1 compás |
| 20 | 2 compases |
| 21 | 4 compases |

Funciona con el umbral de grabación activado o no. La duración se fija al empezar la grabación. Un cambio de tempo durante la grabación no la cambia.

Duración de la grabación en 4/4:

| Duración | Muestras (48 kHz) | Tiempo |
|---|---|---|
| ½ compás | 720000 × 8 / BPM | 120000 / BPM ms |
| 1 compás | 720000 × 16 / BPM | 240000 / BPM ms |
| 2 compases | 720000 × 32 / BPM | 480000 / BPM ms |
| 4 compases | 720000 × 64 / BPM | 960000 / BPM ms |

Ejemplo: reloj externo a 110 BPM, 1 compás = 104727 muestras = 2,18 s.

El sample guardado puede ser hasta 255 muestras (unos 5 ms) más corto que la tabla. El firmware original recorta la grabación en bloques de 256 muestras.

## Límites

**Solo BPM enteros.** El firmware guarda todos los tempos como un número entero, de un byte. El tick del reloj mide el reloj externo y lo redondea al BPM entero más cercano (`0x08032430`: `round(periodo × 0x9C4 / 2^32)`), y la duración de Fixed Recording se calcula con ese número. El firmware original tiene el mismo límite: su propio tempo solo se puede poner en BPM enteros.

- Un maestro con un tempo entero da la duración exacta. El Circuit Tracks solo tiene tempos enteros.
- Un maestro con un tempo decimal (por ejemplo un DAW a 97,5 BPM) da la duración del tempo redondeado (98 BPM). El error es de hasta 0,5 BPM:

| Tempo del maestro | Usado | 1 compás | 4 compases |
|---|---|---|---|
| 97,5 | 98 | 12,6 ms menos | 50 ms menos |
| 120,4 | 120 | 6,6 ms más | 27 ms más |
| 120,5 | 121 | 8,2 ms menos | 33 ms menos |
| 40,5 | 41 | 72 ms menos | 289 ms menos |

El error es mayor con tempos lentos y grabaciones largas. Un arreglo para tempos decimales calcularía la duración con el periodo medido del reloj en lugar del BPM redondeado; no está hecho.

**Cambios de tempo.** El BPM medido se actualiza más o menos una vez por pulso. Una grabación que empieza justo después de un cambio de tempo puede usar el tempo del pulso anterior.

## Instalar

1. Haz una copia de la tarjeta SD. A0.01F tiene las funciones de Alpha 0.01 que escriben en la tarjeta. A01FS no tiene ninguna.
2. Abre `firmware/a0.01f/a001f_uploader.html` en Chrome o Edge.
3. Elige el firmware oficial `circuitrhythm-firmware-5706.syx` y la versión **A0.01F** o **A01FS**.
4. Permite el acceso MIDI, elige **Circuit Rhythm** como entrada y salida, y después **Identify** y **Send**. Pulsa **Play** en el aparato cuando lo pida.

Con Python: `python tools/patch_official.py RUTA/AL/circuitrhythm-firmware-5706.syx --version A0.01F` (o `--version A01FS`).

Para volver: **Sample Rec + Samples + Note** al encender, y después envía “Oficial” o usa Novation Components.

## Cómo funciona

El almacén de tempo del objeto reloj (RAM `0x200126E8`, vtable `0x08068EFC`, almacén de tempo en `+0x14`) tiene dos palabras de 32 bits:

- palabra 0: el tempo puesto en el aparato (el tempo del proyecto);
- palabra 1: el tempo medido del reloj externo, que escribe el tick del reloj (`0x08032430`) más o menos una vez por pulso, solo con reloj externo.

El firmware original lee la palabra 0 en dos sitios, cada uno `ldr r0, [r4, #0x10]; movs r1, #0; bl 0x0803FC58`:

| Llamada | Función | Calcula |
|---|---|---|
| `0x0803CEA0` | `0x0803CE98` | la duración objetivo en muestras y el temporizador de parada (15000 × n / BPM + 50 ms), cuando el estado del sampler pasa a 3 (grabando) |
| `0x08058FE0` | `0x08058F9C` | la duración en ms (32000 ms con Fixed Recording desactivado) |

`tools/fixedrec.py` cambia estos dos `bl` por llamadas a su propia función (72 bytes tras la imagen original). La función devuelve la palabra 1 cuando se cumple todo esto:

- el objeto reloj tiene su vtable `0x08068EFC`;
- el almacén es el almacén de tempo del reloj;
- la palabra 0 del almacén de reloj externo del reloj (`+0x48`) no es 0;
- la palabra 1 está entre 40 y 240 BPM.

Si no, devuelve la palabra 0, como el firmware original.

## Cambios frente a Alpha 0.01

Bytes de la imagen que difieren de la Alpha 0.01 publicada:

| Dirección | Cambio |
|---|---|
| `0x080101ED` | byte de la marca (`A0.01` → `A0.01F`) |
| `0x0803CEA0`–`0x0803CEA3` | `bl 0x0803FC58` → `bl` al arreglo |
| `0x08058FE0`–`0x08058FE3` | `bl 0x0803FC58` → `bl` al arreglo |
| final de la imagen | 88 bytes añadidos (el arreglo y su alineación) |

A01FS tiene los mismos cambios frente a Alpha 0.01S, con la marca `A01FS`. La marca de 6 bytes no tiene sitio para `A0.01FS`.

## Ficheros

| Fichero | Uso |
|---|---|
| `tools/fixedrec.py` | el módulo del arreglo |
| `tools/build_a001f.py` | construye A0.01F |
| `tools/build_a01fs.py` | construye A01FS |
| `tools/emu_fixedrec.py` | prueba en emulación del arreglo |
| `tools/make_a001f_uploader.py` | crea `firmware/a0.01f/a001f_uploader.html` |
| `tools/verify_builds.py` | vuelve a construir todas las versiones, también A0.01F y A01FS, y las compara con sus manifiestos |
| `firmware/a0.01f/manifest.json`, `firmware/a01fs/manifest.json` | SHA-256 e informes de build |

`tools/rm_uploader.html` no incluye A0.01F ni A01FS.

## Pruebas

### Emulación

```bash
python -m pip install unicorn capstone==5.0.7 keystone-engine
python tools/emu_fixedrec.py stock/circuitrhythm-firmware-5706-STOCK.bin firmware/a0.01f/circuitrhythm-5706-A0.01F.bin
```

La prueba ejecuta `0x0803CE98` y `0x08058F9C` de la imagen original y de la imagen construida en Unicorn, con almacenes de prueba y un objeto reloj de prueba. 17 casos: tempo del proyecto sin reloj externo, reloj externo, BPM fuera de 40–240 y en los límites, los dos búferes del almacén, otro almacén, vtable incorrecta, las cuatro duraciones, Fixed Recording desactivado, y registros conservados según la convención de llamada. Resultado: 17/17 correctos en A0.01F, A01FS y FRD1.

### En el aparato (FRD1)

FRD1 fue una build de prueba privada (original + el arreglo + el diagnóstico remoto por USB). No se publica: las versiones públicas no llevan diagnóstico remoto.

Circuit Tracks como maestro del reloj, Circuit Rhythm como esclavo, tempo del proyecto 90 BPM:

- El objeto reloj, su vtable, el almacén de tempo (`0x20012788`) y el almacén de reloj externo (`0x20012868`) estaban en las direcciones esperadas.
- El BPM medido (palabra 1) siguió al Tracks: 100, 120 y 110.
- El código del arreglo en la flash era idéntico a la build.
- Ocho grabaciones (pads 9–16) a 110 y 120 BPM, con cambios de tempo entre ellas: todas las duraciones correspondían al tempo del reloj, no al del proyecto. Cada WAV tenía la duración objetivo o hasta 93 muestras (1,9 ms) menos (el recorte de 256 muestras del firmware original).

### En el aparato (versión publicada)

A0.01F y A01FS tienen el mismo código del arreglo que FRD1. Con la versión publicada (sin diagnóstico): reloj externo a 100 BPM, tempo del proyecto 90 BPM, 1 compás en el pad 9 → 115200 muestras = 2,400 s, la duración del tempo del reloj.
