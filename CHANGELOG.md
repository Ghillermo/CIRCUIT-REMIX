# CHANGELOG

## Alpha 0.01 (2026-10-21)

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
