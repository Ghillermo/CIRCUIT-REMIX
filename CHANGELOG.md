# CHANGELOG

## Alpha 0.04 (2026-10-27) — experimental

> ⚠️ **Experimental: necesita pulirse.** Casi todo lo nuevo se ha comprobado solo en emulación. En el aparato se han probado el granular de una pista, el de-clicker y los loops cortos, la grabación estéreo, el arranque de la reproducción y el reloj al guardar un sample. Puede haber fallos, ruidos o cuelgues: para tocar en serio, sigue con **Alpha 0.03** (sigue en el instalador). **Haz una copia de la tarjeta SD.**

**Español.** Dos versiones nuevas: **Alpha 0.04** (marca `A0.04`) y **Alpha 0.04S** (marca `A0.04S`: sin la copia de proyectos, el borrado de packs ni la copia de samples). Todo en el [manual](docs/MANUAL.md).

Novedades:
- **Menú de pista:** mantén el botón de una pista y los pads 1-7 son un menú: página stock / Stock+ / Granular, el granular encendido / apagado, la entrada de línea y su gate, el enlace estéreo. Sustituye a pulsar otra vez el botón de la pista.
- **Granular** (el motor de CIRCUIT-HACKS, en el DSP del master):
  - página Granular en los knobs (tamaño, densidad, posición, scan, altura, dispersiones, ventana; con Shift: ajuste fino, apertura estéreo, zona, reverso, gate);
  - sigue la nota (vista Note, teclado, MIDI);
  - el filtro y la envolvente de la pista actúan sobre él;
  - **hasta 4 pistas granulares a la vez**, cada una con sus ajustes; se guarda con el proyecto.
- **Entrada de línea como sonido de una pista** (una pista: L + R; dos pistas: L y R), con gate por notas.
- **Enlace estéreo:** una pista y la siguiente suenan como un solo sonido estéreo (su sample a la izquierda, el siguiente a la derecha).
- **Sample Rec estéreo** (pad 24): L en el hueco elegido, R en el siguiente.
- **Loops:**
  - de-clicker por crossfade (pad 19 de Sample mode por pista; pad 23 de Sample Rec para todas; encendido por defecto);
  - los loops cortos suenan a su longitud (en el original se repetían cada ~128 muestras);
  - el scan (K8 de Stock+) mueve el inicio del loop en cada vuelta.
- **Stock+:** K3 (LFO de tono) y K8 (scan) desde el centro: centro = quieto, derecha = libre, izquierda = a tempo. En proyectos de Alpha 0.02 / 0.03 pueden sonar distinto.
- **Sample mode, pads 9 / 10:** ajustar el sample al patrón con stretch, sin cambiar el tono.
- **Mixer, modo cue** (página de panoramas, Shift + knob): la mezcla por la salida izquierda, el cue por la derecha.
- **Micro Step:** longitud fija (pad 31) y gate por pulsación (pad 32) al introducir pasos.
- **Vista Velocity, Shift + paso:** en ese paso, los parámetros automatizados vuelven a su knob.
- **Pattern Settings, Clear + pad 25:** borra las dinámicas y la mutación del patrón.
- **Setup:** modo General MIDI (pad 22, la nota de cada pista en K1-K8); Advanced Setup: teclado externo al arpegiador (pad 22) y fusión USB del DIN In (pad 23).

Arreglos del firmware original:
- La reproducción empieza antes (≈ 10 ms de Play al primer sonido; el original ≈ 18 ms) y las notas de un mismo paso suenan juntas.
- El reloj ya no tropieza al guardar un sample.
- Notas perdidas con muchas pistas en el mismo paso (la cola de disparos al DSP se llenaba).
- Los canales de Program Change y el modo del Thru (Merge / Filter) se guardan al apagar (sin comprobar en el aparato).

**English.** Two new builds: **Alpha 0.04** (marker `A0.04`) and **Alpha 0.04S** (marker `A0.04S`: no project copy, pack delete or sample copy). Everything is in the [manual](docs/MANUAL_EN.md).

> ⚠️ **Experimental: needs refinement.** Almost everything new has only been checked in emulation. On the device we tested the single-track granular, the de-clicker and short loops, stereo recording, the playback start and the clock while a sample is saved. Expect bugs, noises or hangs: for serious playing, stay on **Alpha 0.03** (still in the installer). **Back up the SD card.**

What's new:
- **Track menu:** hold a track's button and pads 1-7 become a menu: stock / Stock+ / Granular page, granular on / off, line input and its gate, stereo link. It replaces pressing the track's button again.
- **Granular** (the CIRCUIT-HACKS engine, on the master DSP):
  - a Granular knob page (size, density, position, scan, pitch, sprays, window; with Shift: fine control, stereo spread, zone, reverse, gate);
  - it follows the note (Note view, keyboard, MIDI);
  - the track's filter and envelope act on it;
  - **up to 4 granular tracks at once**, each with its own settings; saved with the project.
- **Line input as a track's sound** (one track: L + R; two tracks: L and R), with a note gate.
- **Stereo link:** a track and the next one play as one stereo sound (its sample on the left, the next one on the right).
- **Stereo Sample Rec** (pad 24): L into the chosen slot, R into the next one.
- **Loops:**
  - crossfade de-clicker (Sample mode pad 19 per track; Sample Rec pad 23 for all; on by default);
  - short loops play at their own length (the original repeated them every ~128 samples);
  - the scan (Stock+ K8) moves the loop's start on every pass.
- **Stock+:** K3 (pitch LFO) and K8 (scan) from the centre: centre = still, right = free, left = synced to the tempo. Projects from Alpha 0.02 / 0.03 may sound different.
- **Sample mode, pads 9 / 10:** fit the sample to the pattern with stretch, without changing pitch.
- **Mixer cue mode** (pan page, Shift + knob): the mix on the left output, the cue on the right.
- **Micro Step:** fixed length (pad 31) and gate by press (pad 32) when entering steps.
- **Velocity view, Shift + step:** on that step, automated parameters go back to their knob.
- **Pattern Settings, Clear + pad 25:** clears the pattern's dynamics and mutation.
- **Setup:** General MIDI mode (pad 22, each track's note on K1-K8); Advanced Setup: external keyboard into the arpeggiator (pad 22) and USB merge of DIN In (pad 23).

Fixes to the original firmware:
- Playback starts sooner (≈ 10 ms from Play to the first sound; the original ≈ 18 ms) and the notes of one step sound together.
- The clock no longer stumbles while a sample is saved.
- Lost notes with many tracks on the same step (the trigger queue to the DSP overflowed).
- The Program Change channels and the Thru mode (Merge / Filter) are kept after power-off (not yet checked on the device).

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
