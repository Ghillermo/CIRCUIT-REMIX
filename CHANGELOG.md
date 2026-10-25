# CHANGELOG

## Alpha 0.03 (2026-10-25)

**Español.** Dos versiones nuevas (las anteriores siguen en el instalador):
- **Alpha 0.03** (marca `A0.03`): Alpha 0.02 con el arreglo de abajo; las mismas funciones del [manual](docs/MANUAL.md).
- **Alpha 0.03S** (marca `A0.03S`): Alpha 0.03 sin la copia de proyectos, el borrado de packs ni la copia de samples; nada del mod crea, modifica ni borra ficheros en la tarjeta.

Arreglo:
- **La página Stock+ funciona desde el encendido.** En Alpha 0.01 / 0.02, recién encendido el aparato (no tras instalar), Stock+ podía no hacer nada durante unos minutos. La causa está en el firmware original: el DSP de las voces no inicializa al arrancar su palabra de configuración del puerto con el procesador principal, y con algunos valores de la memoria al encender ese puerto pasa a palabras de 16 bits mientras el procesador manda de 24; todo lo que Stock+ escribía se perdía hasta que el puerto se recolocaba por casualidad. Ahora el arranque del DSP la borra antes de configurar el puerto (2 palabras de código propio).
- **Probado en el aparato** con la build de desarrollo equivalente (RH36): Stock+ funciona en los primeros segundos tras encender en frío. **Haz una copia de la tarjeta SD.**

**English.** Two new builds (the earlier ones stay in the installer):
- **Alpha 0.03** (marker `A0.03`): Alpha 0.02 with the fix below; the same features as in the [manual](docs/MANUAL_EN.md).
- **Alpha 0.03S** (marker `A0.03S`): Alpha 0.03 without project copy, pack delete or sample copy; nothing of the mod creates, changes or deletes files on the card.

Fix:
- **The Stock+ page works from power-on.** In Alpha 0.01 / 0.02, right after switching the device on (not after installing), Stock+ could do nothing for a few minutes. The cause is in the original firmware: the voices' DSP does not initialise, at start-up, the configuration word of its link to the main processor, and with some power-on memory contents that link switches to 16-bit words while the processor sends 24; everything Stock+ wrote was lost until the link happened to fall back into step. Now the DSP's start-up clears that word before it sets up the link (2 words of our own code).
- **Tested on the device** with the equivalent development build (RH36): Stock+ works in the first seconds after a cold start. **Back up the SD card.**

## Alpha 0.02 (2026-10-25)

**Español.** Dos versiones nuevas (las anteriores siguen en el instalador):
- **Alpha 0.02** (marca `A0.02`): todas las funciones del [manual](docs/MANUAL.md).
- **Alpha 0.02S** (marca `A0.02S`): Alpha 0.02 sin la copia de proyectos, el borrado de packs ni la copia de samples; nada del mod crea, modifica ni borra ficheros en la tarjeta.

Novedades:
- **La página Stock+ completa** (el botón de la pista elegida otra vez):
  - K5 ring mod (Shift: su frecuencia);
  - K6 pitch follow (Shift: tipo de filtro stock / 24 dB / comb sobre los knobs de filtro del stock; el LED, del color del tipo);
  - K7 **stretch** 0,25×-4× sin cambiar el tono (Shift: bitcrush);
  - K8 scan del punto de inicio (Shift: su profundidad).

  Clear + K5-K8 devuelve las dos capas al valor por defecto. Se guarda con el proyecto; los proyectos de Alpha 0.01 cargan como estaban.
- **Fixed Recording al tempo del reloj MIDI externo** (el arreglo de mefisme, antes en A0.01F / A01FS).
- **Arreglo:** las palabras de la página Stock+ ya no comparten memoria del DSP con el sample de la pista 8 (en Alpha 0.01 podía notarse en la pista 8 con la envolvente o el LFO de tono).
- **Probado en el aparato** con builds de desarrollo: el DSP con todo encendido en las 8 pistas, más reverb y delay, 2 minutos sin cortes; la página, sus knobs y el guardado. **Haz una copia de la tarjeta SD.**

**English.** Two new builds (the earlier ones stay in the installer):
- **Alpha 0.02** (marker `A0.02`): every feature in the [manual](docs/MANUAL_EN.md).
- **Alpha 0.02S** (marker `A0.02S`): Alpha 0.02 without project copy, pack delete or sample copy; nothing of the mod creates, changes or deletes files on the card.

What's new:
- **The full Stock+ page** (press the selected track's button again):
  - K5 ring mod (Shift: its frequency);
  - K6 pitch follow (Shift: filter type stock / 24 dB / comb on the stock filter knobs; its LED in the type's colour);
  - K7 **stretch** 0.25×-4× without changing pitch (Shift: bitcrush);
  - K8 start-point scan (Shift: its depth).

  Clear + K5-K8 resets both layers. Saved with the project; Alpha 0.01 projects load as they were.
- **Fixed Recording at the external MIDI clock's tempo** (mefisme's fix, previously in A0.01F / A01FS).
- **Fix:** the Stock+ page's words no longer share DSP memory with track 8's sample (in Alpha 0.01 it could be heard on track 8 with the pitch envelope or LFO).
- **Tested on the device** with development builds: the DSP with everything on all 8 tracks plus reverb and delay, 2 minutes without dropouts; the page, its knobs and saving. **Back up the SD card.**

## Alpha 0.01F / A01FS (2026-10-24)

> ⚠️ **Fallo conocido de Alpha 0.01, 0.01S, A0.01F y A01FS: pista 8.** Los valores de la página Stock+ (envolvente y LFO de tono) estaban en la memoria del DSP donde la pista 8 lee su sample mientras suena, y se escriben siempre, aunque no uses la página. Con algo sonando en la pista 8 puede oírse chirridos, clics o siseo, y el tono puede irse. **Arreglado en Alpha 0.02: actualiza.** Alpha 0.0 / 0.0S no lo tienen.
>
> ⚠️ **Known bug in Alpha 0.01, 0.01S, A0.01F and A01FS: track 8.** The Stock+ page's values (pitch envelope and LFO) sat in the DSP memory where track 8 reads its sample while it plays, and they are written all the time, even if you never use the page. With something playing on track 8 you may hear chirps, clicks or hiss, and its pitch may drift. **Fixed in Alpha 0.02: please update.** Alpha 0.0 / 0.0S are not affected.

**Español.** Dos versiones con un arreglo de Fixed Recording ([detalles](docs/FIXEDREC.md)):
- **Alpha 0.01F** (marca `A0.01F`): Alpha 0.01 + el arreglo.
- **A01FS** (marca `A01FS`): Alpha 0.01S + el arreglo.

Con un reloj MIDI externo, Fixed Recording usa el tempo del reloj, no el del proyecto. Sin reloj externo, usa el tempo del proyecto, como el original. Instalador: `firmware/a0.01f/a001f_uploader.html`.

Comprobado en emulación (17 casos) y en el aparato con la build de prueba FRD1 (el arreglo + el diagnóstico remoto de solo lectura). **Haz una copia de la tarjeta SD.**

**English.** Two builds with a Fixed Recording fix ([details](docs/FIXEDREC_EN.md)):
- **Alpha 0.01F** (marker `A0.01F`): Alpha 0.01 + the fix.
- **A01FS** (marker `A01FS`): Alpha 0.01S + the fix.

With an external MIDI clock, Fixed Recording uses the clock's tempo, not the project tempo. Without an external clock, it uses the project tempo, as the original. Installer: `firmware/a0.01f/a001f_uploader.html`.

Checked in emulation (17 cases) and on the device with the FRD1 test build (the fix + read-only remote diagnostics). **Back up the SD card.**

## Alpha 0.01 (2026-10-21)

> ⚠️ **Fallo conocido de Alpha 0.01, 0.01S, A0.01F y A01FS: pista 8.** Los valores de la página Stock+ (envolvente y LFO de tono) estaban en la memoria del DSP donde la pista 8 lee su sample mientras suena, y se escriben siempre, aunque no uses la página. Con algo sonando en la pista 8 puede oírse chirridos, clics o siseo, y el tono puede irse. **Arreglado en Alpha 0.02: actualiza.** Alpha 0.0 / 0.0S no lo tienen.
>
> ⚠️ **Known bug in Alpha 0.01, 0.01S, A0.01F and A01FS: track 8.** The Stock+ page's values (pitch envelope and LFO) sat in the DSP memory where track 8 reads its sample while it plays, and they are written all the time, even if you never use the page. With something playing on track 8 you may hear chirps, clicks or hiss, and its pitch may drift. **Fixed in Alpha 0.02: please update.** Alpha 0.0 / 0.0S are not affected.

**Español.** Dos versiones nuevas (las anteriores siguen en el instalador):
- **Alpha 0.01** (marca `A0.01`): todas las funciones del [manual](docs/MANUAL.md).
- **Alpha 0.01S** (marca `A0.01S`): Alpha 0.01 sin la copia de proyectos, el borrado de packs ni la copia de samples; nada del mod crea, modifica ni borra ficheros en la tarjeta.

Novedades:
- **Página Stock+ de los knobs de pista:** pulsa otra vez el botón de la pista elegida. K1 / K2 = envolvente de tono (cantidad ±24 semitonos, caída de 5 ms a 4 s), K3 / K4 = LFO de tono (0,05-30 Hz, hasta 24 semitonos); Shift = ajuste fino, como en los knobs del original; se guarda con el proyecto. Es la primera función con código propio en el DSP de las voces (el DSP probado en el aparato con una build de diagnóstico; la página con sus knobs, de momento solo en emulación).
- **Borrar un pack** desde el aparato (Packs: Clear + pack, Clear + el mismo pack) y **copiar un sample** a otro hueco, también desde otro pack (Sample Rec: Duplicate + A, Duplicate + B).
- **Umbral del compresor master** en K5 de la vista Sidechain; Clear + knob de Sidechain, uno a uno.
- **Repetición de escena:** en el Mixer con Shift, la vuelta que suena en blanco.
- **Las dinámicas se graban** en el paso con Record (la velocity y el micropaso con que sonó).
- Arreglos: la cuenta atrás va al tempo del proyecto; los LEDs de los envíos tras Duplicate / Clear en la vista FX; la fila de dinámicas de la vista de probabilidad.

Comprobado en emulación (cada función con su prueba; 121 gestos y acciones de uso normal iguales al original salvo lo añadido). **Haz una copia de la tarjeta SD.**

**English.** Two new builds (the earlier ones stay in the installer):
- **Alpha 0.01** (marker `A0.01`): every feature of the [manual](docs/MANUAL_EN.md).
- **Alpha 0.01S** (marker `A0.01S`): Alpha 0.01 without the project copy, the pack delete and the sample copy; nothing of the mod creates, changes or deletes files on the card.

New:
- **The Stock+ track knob page:** press the selected track's button again. K1 / K2 = pitch envelope (amount ±24 semitones, decay 5 ms to 4 s), K3 / K4 = pitch LFO (0.05-30 Hz, up to 24 semitones); Shift = fine control, as on the original knobs; saved with the project. The first feature with its own code in the voices' DSP (the DSP tested on the device with a diagnostic build; the page and its knobs so far in emulation only).
- **Delete a pack** on the device (Packs: Clear + pack, Clear + the same pack) and **copy a sample** to another slot, also from another pack (Sample Rec: Duplicate + A, Duplicate + B).
- **Master compressor threshold** on K5 of the Sidechain view; Clear + a Sidechain knob, one at a time.
- **Scene repeat:** in the Mixer with Shift, the repeat that is playing shows white.
- **Dynamics are recorded** into the step with Record (the velocity and micro step it played with).
- Fixes: the count-in follows the project's tempo; the send LEDs after Duplicate / Clear in the FX view; the dynamics row of the probability view.

Checked in emulation (each feature with its test; 121 gestures and ordinary actions identical to the original except what is added). **Back up the SD card.**

## Alpha 0.0 (2026-10-19)

**Español.** Primera versión pública de Circuit Remix: un port de las funciones de CIRCUIT-HACKS (Circuit Tracks) al Circuit Rhythm 2.0.1 (build 5706), con características exclusivas. Dos versiones:
- **Alpha 0.0** (marca `A0.0`): todas las funciones del [manual](docs/MANUAL.md).
- **Alpha 0.0S** (marca `A0.0S`): Alpha 0.0 sin la copia de proyectos; nada del mod crea, modifica ni borra ficheros en la tarjeta.

Comprobado en emulación (el código del aparato sobre un volcado de su memoria): cada función con su prueba, y que no se pierde nada del firmware original (115 gestos y acciones de uso normal iguales al original salvo lo añadido). Sin el diagnóstico remoto por SysEx de las versiones de desarrollo. En el aparato se han probado las primeras funciones y que los datos propios se guardan y se cargan con el proyecto; el resto está pendiente: **haz una copia de la tarjeta SD**.

**English.** First public release of Circuit Remix: a port of the CIRCUIT-HACKS (Circuit Tracks) features to the Circuit Rhythm 2.0.1 (build 5706), with exclusive features. Two builds:
- **Alpha 0.0** (marker `A0.0`): every feature of the [manual](docs/MANUAL_EN.md).
- **Alpha 0.0S** (marker `A0.0S`): Alpha 0.0 without the project copy; nothing of the mod creates, changes or deletes files on the card.

Checked in emulation (the device's code run on a dump of its memory): each feature with its test, and that nothing of the original firmware is lost (115 gestures and ordinary actions identical to the original except what is added). Without the remote SysEx diagnostics of the development builds. On the device, the first features and the saving / loading of the mod's own data with the project have been tested; the rest is pending: **back up the SD card**.
