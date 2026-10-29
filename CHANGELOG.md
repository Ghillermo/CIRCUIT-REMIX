# CHANGELOG

## Alpha 0.09 (2026-10-29) — experimental

> ⚠️ **Experimental: necesita pulirse.** Todo lo nuevo se ha comprobado solo en emulación (el código del aparato ejecutado sobre un volcado de su memoria). Puede haber fallos, ruidos o cuelgues: para tocar en serio, sigue con **Alpha 0.03** (sigue en el instalador). **Haz una copia de la tarjeta SD.**

**Español.** Dos versiones nuevas: **Alpha 0.09** (marca `A0.09`) y **Alpha 0.09S** (marca `A0.09S`: sin la copia de proyectos, el borrado de packs ni la copia de samples). Todo en el [manual](docs/MANUAL.md) ([ilustrado](docs/manual/index.html)).

Novedades:
- **Automatización (la de CIRCUIT-HACKS):**
  - **Velocity + Shift:** los pasos con automatización de knobs en amarillo, los marcados en rojo.
  - **Shift + paso amarillo = escucharlo:** sus valores a los knobs y al sonido (los knobs en amarillo); al soltar Shift, todo vuelve.
  - **Velocity otra vez** = esa vista fija, sin mantener Shift (un toque escucha un paso amarillo o marca otro); otra vez, o salir de la vista, la quita.
  - **Clear + paso** en Velocity borra la automatización de knobs de ese paso (las notas se quedan).
  - **Un paso marcado** devuelve los parámetros a **Project init** (como se cargó o guardó el proyecto), no a donde estaba el knob.
  - **Snapshot:** en la vista de pista, Record mantenido + un paso guarda ahí los knobs movidos; el pad se ve amarillo mientras lo mantienes.
  - **Menú de pista, pad 8 (rojo):** la voz de la pista vuelve a Project init.
- **Los modos de la pista, en Sample mode** (Samples dos veces): pads 5-8 = sample / granular / sinte / entrada de línea, 14 = enlace estéreo, 15 / 16 = la fuente y el gate de la entrada. El menú de pista se queda con las páginas.
- **El FX hacia una entrada:** una pista de entrada que toma el retorno de la reverb o del delay lo saca del master (suena solo por la pista), y su envío a ese mismo efecto llega a la mitad: la realimentación se queda contenida. El envío al otro efecto, entero.
- **Enlace estéreo con desviaciones:** los K1-K8 de la segunda pista suman o restan a los de la primera (centro = igual; azul acero); su sample mantiene la distancia con el de la primera (por defecto, el siguiente); sus propios pasos también suenan. Los proyectos con enlace de Alpha 0.04-0.08 cargan como sonaban.
- **Inicio y longitud del original** (página stock, K2 / K3) en el granular (el inicio mueve la posición, la longitud estrecha la zona) y en el sinte (**morph** continuo entre formas de onda y **unísono** de dos voces por oscilador).
- **Sin parpadeos:** el botón de la pista ya no parpadea en las páginas Stock+, Granular, Sinte y Envolvente (encendía también el botón Samples).

**English.** Two new builds: **Alpha 0.09** (marker `A0.09`) and **Alpha 0.09S** (marker `A0.09S`: no project copy, pack delete or sample copy). Everything is in the [manual](docs/MANUAL_EN.md) ([illustrated](docs/manual/en.html)).

> ⚠️ **Experimental: needs refinement.** Everything new has only been checked in emulation (the device's code run on a dump of its memory). Expect bugs, noises or hangs: for serious playing, stay on **Alpha 0.03** (still in the installer). **Back up the SD card.**

What's new:
- **Automation (CIRCUIT-HACKS'):**
  - **Velocity + Shift:** steps with knob automation in yellow, the marked ones in red.
  - **Shift + a yellow step = listen to it:** its values to the knobs and the sound (the knobs in yellow); let go of Shift and everything goes back.
  - **Velocity again** = that view latched, without holding Shift (a tap listens to a yellow step or marks another); again, or leaving the view, removes it.
  - **Clear + step** in Velocity erases that step's knob automation (the notes stay).
  - **A marked step** brings the parameters back to **Project init** (as the project was loaded or saved), not to where the knob was.
  - **Snapshot:** in the track view, Record held + a step stores the moved knobs there; the pad shows yellow while you hold it.
  - **Track menu, pad 8 (red):** the track's voice back to Project init.
- **The track's modes, in Sample mode** (Samples twice): pads 5-8 = sample / granular / synth / line input, 14 = stereo link, 15 / 16 = the input's source and gate. The track menu keeps the pages.
- **An FX into an input:** an input track that takes the reverb or delay return takes it off the master (it only sounds through the track), and its send into that same effect is halved: the feedback stays contained. The send into the other effect, whole.
- **Stereo link with offsets:** the second track's K1-K8 add to or subtract from the first one's (centre = the same; steel blue); its sample keeps its distance from the first one's (by default, the next); its own steps play too. Linked projects from Alpha 0.04-0.08 load as they sounded.
- **The original's start and length** (stock page, K2 / K3) on the granular (the start moves the position, the length narrows the zone) and on the synth (a smooth **morph** between waveforms and a two-voice **unison** per oscillator).
- **No more blinking:** the track's button no longer blinks on the Stock+, Granular, Synth and Envelope pages (it also lit the Samples button).

## Alpha 0.08 (2026-10-29) — experimental

> ⚠️ **Experimental: necesita pulirse.** La cuenta atrás con el reloj se probó en el aparato sobre Alpha 0.04 (A0.04F, de mefisme); sobre lo de ahora solo se ha comprobado en emulación, como casi todo lo de Alpha 0.04-0.07. Puede haber fallos, ruidos o cuelgues: para tocar en serio, sigue con **Alpha 0.03** (sigue en el instalador). **Haz una copia de la tarjeta SD.**

**Español.** Dos versiones nuevas: **Alpha 0.08** (marca `A0.08`) y **Alpha 0.08S** (marca `A0.08S`: sin la copia de proyectos, el borrado de packs ni la copia de samples). Lo nuevo es la contribución de **mefisme** (pull request 7, sus A0.04F / A04FS), llevada a lo de ahora. Todo en el [manual](docs/MANUAL.md#transporte) ([ilustrado](docs/manual/index.html)).

Novedades:
- **La cuenta atrás sigue el reloj de la música:** el tempo del proyecto, o el reloj MIDI externo como esclavo. Antes la contaba la tarea de los LEDs: clics de 0 a 10 ms tarde.
- **El 1 a tiempo:** Play entra al empezar la cuenta y el arranque del reloj espera hasta el 1, así el trabajo de Play se hace durante la cuenta.
- **Durante la cuenta** no se graba nada y el LED de Play se ve parado; Record destella en rojo en cada clic.
- **Esclavo:** el primer clic cae en el compás siguiente del maestro si se conoce su posición (Start o Song Position).
- **Metrónomo visual:** con el nivel del clic a 0 (K5 de Tempo / Swing), Clear destella en naranja en cada clic y en cada tiempo.
- **Carga de pasos más rápida al pulsar Play** (el mismo resultado con la cuarta parte de las llamadas).
- **Luz de error:** Clear parpadea en rojo si estas funciones no pueden funcionar con el firmware que encuentran (no debería verse nunca).
- Shift + Play (la cuenta y seguir) y Play durante la cuenta (la cancela) siguen igual.
- **Entrada de línea:** en el menú de pista, el pad 15 con las entradas como fuente (sin FX) se ve ámbar tenue; los retornos de reverb y delay, como antes.

**English.** Two new builds: **Alpha 0.08** (marker `A0.08`) and **Alpha 0.08S** (marker `A0.08S`: no project copy, pack delete or sample copy). What's new is **mefisme**'s contribution (pull request 7, their A0.04F / A04FS), brought onto the current line. Everything is in the [manual](docs/MANUAL_EN.md#transporte) ([illustrated](docs/manual/en.html)).

> ⚠️ **Experimental: needs refinement.** The count-in on the clock was tested on the device on Alpha 0.04 (mefisme's A0.04F); on the current line it has only been checked in emulation, like most of Alpha 0.04-0.07. Expect bugs, noises or hangs: for serious playing, stay on **Alpha 0.03** (still in the installer). **Back up the SD card.**

What's new:
- **The count-in follows the music's clock:** the project's tempo, or the external MIDI clock as a slave. Before, the LED task timed it: clicks 0 to 10 ms late.
- **The 1 on time:** Play goes through at the start of the count and the clock's start waits until the 1, so Play's work runs during the count.
- **During the count** nothing records and the Play LED shows stopped; Record flashes red on each click.
- **Slave:** the first click comes on the master's next bar when its position is known (Start or Song Position).
- **Visual metronome:** with the click's level at 0 (Tempo / Swing K5), Clear flashes orange on each click and each beat.
- **Faster step load on Play** (the same result with a quarter of the calls).
- **Error light:** Clear blinks red if these features cannot run on the firmware they find (it should never show).
- Shift + Play (the count, then carry on) and Play during the count (cancels it) work as before.
- **Line input:** on the track menu, pad 15 with the inputs as the source (no FX) shows dim amber; the reverb and delay returns as before.

## Alpha 0.07 (2026-10-28) — experimental

> ⚠️ **Experimental: necesita pulirse.** Stock+ en el granular y el sinte solo se ha comprobado en emulación, como casi todo lo de Alpha 0.04-0.06. Puede haber fallos, ruidos o cuelgues: para tocar en serio, sigue con **Alpha 0.03** (sigue en el instalador). **Haz una copia de la tarjeta SD.**

**Español.** Dos versiones nuevas: **Alpha 0.07** (marca `A0.07`) y **Alpha 0.07S** (marca `A0.07S`: sin la copia de proyectos, el borrado de packs ni la copia de samples). Todo en el [manual](docs/MANUAL.md) ([ilustrado](docs/manual/index.html)).

Novedades:
- **Stock+ para todos los sonidos:** la página Stock+ (menú de pista, pad 2) también en una pista **granular** o con **sinte**:
  - envolvente y LFO de tono sobre el tono de cada grano nuevo / de los osciladores del sinte;
  - ring mod, pitch follow y el tipo de filtro (24 dB, comb) sobre su sonido;
  - **K7 = waveshaper:** cantidad (ganancia ×1-×16; en bitcrush, los bits); **Shift + K7 = su tipo:** suave (dorado), duro (rojo anaranjado), plegado (turquesa), bitcrush (lima);
  - **K8 = LFO** de la posición de los granos (granular) o de la cantidad de FM (sinte); Shift + K8, su profundidad;
  - el waveshaper se guarda con el proyecto y lo llevan Clear + botón de pista y Duplicate.
- **El knob de distorsión de la pista** (página stock) ahora también suena en el granular y el sinte, con la misma curva que en un sample.
- En una pista granular o con sinte la voz de sample, que no suena, ya no gasta Stock+.

**English.** Two new builds: **Alpha 0.07** (marker `A0.07`) and **Alpha 0.07S** (marker `A0.07S`: no project copy, pack delete or sample copy). Everything is in the [manual](docs/MANUAL_EN.md) ([illustrated](docs/manual/en.html)).

> ⚠️ **Experimental: needs refinement.** Stock+ on the granular and the synth has only been checked in emulation, like most of Alpha 0.04-0.06. Expect bugs, noises or hangs: for serious playing, stay on **Alpha 0.03** (still in the installer). **Back up the SD card.**

What's new:
- **Stock+ for every sound:** the Stock+ page (track menu, pad 2) on **granular** and **synth** tracks too:
  - the pitch envelope and LFO on each new grain's pitch / the synth's oscillators;
  - ring mod, pitch follow and the filter type (24 dB, comb) on their sound;
  - **K7 = waveshaper:** amount (gain x1-x16; for bitcrush, the bits); **Shift + K7 = its type:** soft (gold), hard (red-orange), fold (teal), bitcrush (lime);
  - **K8 = an LFO** on the grains' position (granular) or the FM amount (synth); Shift + K8, its depth;
  - the waveshaper is saved with the project and goes along with Clear + track button and Duplicate.
- **The track's distortion knob** (stock page) now also works on the granular and the synth, with the same curve as on a sample.
- On a granular or synth track the unheard sample voice no longer spends Stock+.

## Alpha 0.06 (2026-10-28) — experimental

> ⚠️ **Experimental: necesita pulirse.** La envolvente y la entrada desde los retornos de FX solo se han comprobado en emulación, como casi todo lo de Alpha 0.04 / 0.05. Puede haber fallos, ruidos o cuelgues: para tocar en serio, sigue con **Alpha 0.03** (sigue en el instalador). **Haz una copia de la tarjeta SD.**

**Español.** Dos versiones nuevas: **Alpha 0.06** (marca `A0.06`) y **Alpha 0.06S** (marca `A0.06S`: sin la copia de proyectos, el borrado de packs ni la copia de samples). Todo en el [manual](docs/MANUAL.md) ([ilustrado](docs/manual/index.html)).

Novedades:
- **Envolvente por modo de reproducción** para el sinte y el granular, en una **página Envolvente** nueva (menú de pista, pad 5, rosa):
  - K1 inicio (el ataque), K2 longitud, K3 pendiente (desde el centro), K4 envolvente → paso bajo;
  - la longitud según el modo de la pista: **one-shot** = caída percusiva; **gated** = sostiene y suelta; **loop** = sostiene ese tiempo aunque la nota sea corta;
  - en el granular, con su gate encendido, la envolvente es el VCA;
  - se guarda con el proyecto.
- **Entrada de línea desde los retornos de FX:**
  - pad 15 del menú: las entradas (ámbar) → el retorno de reverb (crema) → el de delay (melocotón);
  - el gate (pad 14) ahora pasa además por el **filtro** de la pista (VCA y VCF).
- La foto que usa Clear + botón de pista vive ahora en la RAM: deja sitio en el proyecto para la envolvente.

**English.** Two new builds: **Alpha 0.06** (marker `A0.06`) and **Alpha 0.06S** (marker `A0.06S`: no project copy, pack delete or sample copy). Everything is in the [manual](docs/MANUAL_EN.md) ([illustrated](docs/manual/en.html)).

> ⚠️ **Experimental: needs refinement.** The envelope and the line input from the FX returns have only been checked in emulation, like most of Alpha 0.04 / 0.05. Expect bugs, noises or hangs: for serious playing, stay on **Alpha 0.03** (still in the installer). **Back up the SD card.**

What's new:
- **Envelope by play mode** for the synth and the granular, on a new **Envelope page** (track menu, pad 5, rose):
  - K1 start (the attack), K2 length, K3 slope (from the centre), K4 envelope → low-pass;
  - the length by the track's play mode: **one-shot** = a percussive decay; **gated** = holds and releases; **loop** = holds for that time even after a short note;
  - on the granular, with its gate on, the envelope is the VCA;
  - saved with the project.
- **Line input from the FX returns:**
  - menu pad 15: the inputs (amber) → the reverb return (cream) → the delay return (peach);
  - the gate (pad 14) now also goes through the track's **filter** (VCA and VCF).
- The snapshot Clear + track button uses now lives in RAM: it frees project space for the envelope.

## Alpha 0.05 (2026-10-28) — experimental

> ⚠️ **Experimental: necesita pulirse.** El sinte y la interfaz nueva solo se han comprobado en emulación, como casi todo lo de Alpha 0.04. Puede haber fallos, ruidos o cuelgues: para tocar en serio, sigue con **Alpha 0.03** (sigue en el instalador). **Haz una copia de la tarjeta SD.**

**Español.** Dos versiones nuevas: **Alpha 0.05** (marca `A0.05`) y **Alpha 0.05S** (marca `A0.05S`: sin la copia de proyectos, el borrado de packs ni la copia de samples). **Manual nuevo**, vista por vista, con un glosario de funciones: [texto](docs/MANUAL.md) o [ilustrado](docs/manual/index.html).

Novedades:
- **Sinte** (en el DSP del master), como sonido de cualquier pista, hasta 4 pistas:
  - dos osciladores (sierra, pulso, triángulo, seno) con sync, FM, SUB, ruido, glide y octava;
  - su página de knobs (menú de pista, pad 4);
  - los knobs del original de la pista (tono, envolvente, filtros, nivel, envíos…) actúan sobre él;
  - se guarda con el proyecto.
- **Interfaz nueva**, con reglas fijas (el manual: «El código de colores»):
  - cada página de knobs tiene su color: Stock+ azul cielo, Granular lila, Sinte menta, en sus knobs, en el botón de la pista y en su pad del menú;
  - **menú de pista:** las páginas en los pads 1-4 (stock, Stock+, Granular, Sinte), solo las del sonido de la pista; debajo, los conmutadores: 9 enlace estéreo, 11 granular, 12 sinte, 13 entrada de línea, 14 su gate. El sonido solo cambia con los conmutadores. **Cambia de sitio todo menos los pads 1-3**;
  - **un toque en el botón de la pista elegida deja el menú abierto** hasta que eliges algo o lo tocas otra vez; mantenerlo, solo mientras lo mantienes. Mantener un pad de página la muestra hasta soltar, como los botones de vista del original;
  - Stock+ K3 / K8, la mitad a tempo: ahora **más rápido hacia el extremo izquierdo** (8 compases junto al centro, 1/16T en el extremo). En proyectos de Alpha 0.04 suenan distinto;
  - apagado = el mismo color, tenue (Micro Step, Setup, Advanced Setup, el arpegiador); en Velocity con Shift, solo los pasos marcados en rojo y los demás como los dibuja la vista;
  - Sinte K1 / K2 en el color de su forma de onda; Stock+ K6 en colores propios por tipo de filtro; el gate del granular (Shift + K8) y el sync del sinte (Shift + K2) como conmutadores.

**English.** Two new builds: **Alpha 0.05** (marker `A0.05`) and **Alpha 0.05S** (marker `A0.05S`: no project copy, pack delete or sample copy). **A new manual**, view by view, with a glossary of functions: [text](docs/MANUAL_EN.md) or [illustrated](docs/manual/en.html).

> ⚠️ **Experimental: needs refinement.** The synth and the new interface have only been checked in emulation, like most of Alpha 0.04. Expect bugs, noises or hangs: for serious playing, stay on **Alpha 0.03** (still in the installer). **Back up the SD card.**

What's new:
- **Synth** (on the master DSP), as any track's sound, up to 4 tracks:
  - two oscillators (saw, pulse, triangle, sine) with sync, FM, SUB, noise, glide and octave;
  - its knob page (track menu, pad 4);
  - the track's original knobs (pitch, envelope, filters, level, sends…) act on it;
  - saved with the project.
- **New interface**, with fixed rules (the manual: "The colour code"):
  - each knob page has its colour: Stock+ sky blue, Granular lilac, Synth mint, on its knobs, the track's button and its menu pad;
  - **track menu:** the pages on pads 1-4 (stock, Stock+, Granular, Synth), only those of the track's sound; below, the toggles: 9 stereo link, 11 granular, 12 synth, 13 line input, 14 its gate. The sound only changes with the toggles. **Everything but pads 1-3 moves**;
  - **a tap on the selected track's button leaves the menu open** until you pick something or tap again; holding it, only while held. Holding a page pad shows it until you let go, like the original's view buttons;
  - Stock+ K3 / K8, the synced half: now **faster towards the left end** (8 bars by the centre, 1/16T at the end). Alpha 0.04 projects sound different;
  - off = the same colour, dim (Micro Step, Setup, Advanced Setup, the arpeggiator); in Velocity with Shift, only the marked steps in red and the others as the view draws them;
  - Synth K1 / K2 in their waveform's colour; Stock+ K6 in its own colours per filter type; the granular's gate (Shift + K8) and the synth's sync (Shift + K2) as toggles.

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
