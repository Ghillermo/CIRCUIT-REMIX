# Circuit Remix Alpha 0.14 — manual

[Español](MANUAL.md) · [illustrated version](manual/en.html)

> ⚠️ **Alpha 0.13 is experimental:** the FX sequencer and the looper have been tried on the device; most other things since Alpha 0.04 mostly in emulation. **Back up your SD card.**

Circuit Remix on the Circuit Rhythm (firmware 2.0.1, build 5706), view by view.

## Contents

**0. Introduction**

- [0.1 How to read this manual](#leer)
- [0.2 The colour code](#colores)
- [0.3 Install and go back to the original](#instalar)

**1. In any view**

- [1.1 Transport, metronome and quantize](#transporte)

**2. Track views**

- [2.1 The track button](#pista)
- [2.2 The track menu](#menu)
- [2.3 Stock+ page](#stockplus)
- [2.4 Granular page](#granular)
- [2.5 OSC 1 / OSC 2 pages (the VA)](#sinte)
- [2.6 Filter / VCA and Envelope + LFO pages](#filtro)
- [2.7 8-operator FM](#fm)
- [2.8 Voice: modes, polyphony and unison](#voces)
- [2.9 Envelope page](#envolvente)
- [2.10 Matrix, Sequenceable and Non-sequenceable](#matriz)
- [2.11 Line input and stereo link](#entrada)
- [2.12 Note view](#note)

**3. Steps and pattern**

- [3.1 Velocity and Micro Step](#velocity)
- [3.2 Pattern Settings and probability](#patternsettings)
- [3.3 Patterns: chains](#patterns)
- [3.4 Pattern Mutate](#mutate)

**4. Samples**

- [4.1 Sample mode](#samplemode)
- [4.2 Sample Rec](#samplerec)
- [4.3 Pack patches and starters](#patches)

**5. Mix and effects**

- [5.1 Mixer](#mixer)
- [5.2 FX and Sidechain](#fx)
- [5.3 Grid FX: the FX sequencer and the looper](#gridfx)

**6. Projects and settings**

- [6.1 Projects and Packs](#projects)
- [6.2 Setup and Advanced Setup](#setup)

**A. Appendix**

- [A.1 What is saved and where](#guardado)
- [A.2 MIDI](#midi)
- [A.3 Arrhythmia modules (proof of concept)](#modulos)

- [Glossary of functions](#glosario)

## 0. Introduction

<a id="leer"></a>
### 0.1 How to read this manual

Each chapter is a view of the device: how you get there, and what its pads, knobs and buttons do with Circuit Remix. Everything else works as in Novation's original firmware (see its manual); the new gestures are combinations that did nothing in the original or repeated the plain gesture.

- **Pads 1-32** left to right, top to bottom: row 1 = 1-8, row 2 = 9-16, row 3 = 17-24, row 4 = 25-32.
- **K1-K8** = the 8 knobs. **▲ / ▼** = the arrow buttons.
- **Hold** a button = press it and keep it down; **A + B** = B with A held.
- **★** = exclusive to Circuit Remix (not in CIRCUIT-HACKS).
- **(since Alpha 0.0x)** = the release that brought the function. Marked *(Alpha 0.14)* or *(Alpha 0.13)*: new or changed in these releases; *(Alpha 0.11)* = 0.10 + Arrhythmia's modules (0.11 only).
- At the end, the **[glossary](#glosario)**: one entry per function, with its view and its gesture.

<a id="colores"></a>
### 0.2 The colour code

Since Alpha 0.05 everything new follows fixed rules *(since Alpha 0.05)*:

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

Each knob page of a track has its own colour, the same on its knobs and on its pad in the menu (the track's button no longer blinks *(Alpha 0.09)*):

| Page | Colour |
|---|---|
| stock (the original firmware's) | white in the menu; the knobs, the original's |
| Stock+ | sky blue |
| Granular | lilac |
| Synth | mint |
| Envelope | rose |

<a id="instalar"></a>
### 0.3 Install and go back to the original

1. Download `rm_app.zip`, unzip it, open `rm_app.html` in Chrome or Edge and go to the **Firmware** tab (the same app manages the card and uploads the modules).
2. Provide the official Circuit Rhythm firmware 2.0.1 (build 5706): the installer checks its SHA-256 and patches it on your computer.
3. Pick the version and send it to the device over USB.

**S versions** (A0.11S, A0.10S): without the functions that create, change or delete files on the card by themselves (project copy, pack delete, sample copy). The safest for your SD.

**Alpha 0.10 / 0.10S** = Alpha 0.11 / 0.11S without the [Arrhythmia modules](#modulos).

**Back to the official firmware:** hold **Sample Rec + Samples + Note** while powering on (Novation's bootloader mode) and send the official one with the app's Firmware tab ("Official") or with Novation Components. Always back up your SD card.

## 1. In any view

<a id="transporte"></a>
### 1.1 Transport, metronome and quantize

*How to get there:* in any view

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

## 2. Track views

<a id="pista"></a>
### 2.1 The track button

*How to get there:* the track views (Samples, Note, Velocity, Gate, Pattern Settings…)

| Gesture | What it does |
|---|---|
| **Clear + the track's button** | ★ its knobs to their defaults and their automation cleared; the rest (level, pan, sends, sidechain, sample) as when the project was loaded *(since Alpha 0.0)* |
| **Duplicate + track A, then track B** | ★ B gets A's parameters and sample; with Duplicate held, more tracks *(since Alpha 0.0)* |
| **Hold the track's button** (¼ s) | opens the [track menu](#menu) on the pads *(since Alpha 0.04)* |
| **Shift held** (in any view) | ★ each track's button flashes white for 100 ms each time it plays *(Alpha 0.10)* |
| **Sample pads held** (arpeggiator on) | ★ arpeggio of the held samples (one also works): each hit changes the sample, with its pad's velocity; recorded with Record and Play *(since Alpha 0.0)* |

Pressing the button without holding selects the track, as in the original. From the Mixer, Clear + track does the original's. The arpeggiator is switched on in [Pattern Settings](#patternsettings) (Shift + pad 25).

<a id="menu"></a>
### 2.2 The track menu

*How to get there:* tap the selected track's button (the menu stays open until you pick something or tap again), or hold any track's button (the menu only while held)

The pads become that track's menu. Since *(Alpha 0.12)* it is **CIRCUIT-HACKS' row 1**, views only: the track's engine and voice are picked in [Sample mode](#samplemode).

| Pad | What it opens |
|---|---|
| **1** | ★ **[Sequenceable](#matriz)**; **Shift + 1**: ★ **[Non-sequenceable](#matriz)** |
| **2** | the **sound's** page: sample or input → the stock page; granular → **[Granular](#granular)**; VA → **[OSC 1](#sinte)**; FM → its **[operators](#fm)** |
| **3** | VA → **[OSC 2](#sinte)**; FM → its **[pitch envelope](#fm)**; dark with the other sounds |
| **4** | ★ **[Filter / VCA](#filtro)** (lime) |
| **5** | ★ **[Envelope + LFO](#filtro)** (rose) |
| **6** | ★ **[Matrix](#matriz)** |
| **9** | the **stock** page (the original's) |
| **10** | **[Stock+](#stockplus)** |
| **16** | ★ **Project init** (red): the track's voice back to how the project was last loaded or saved (K1-K8 and the rest of the voice; level, pan, sends and sidechain are left alone); Stock+, Granular, Synth and Envelope back to factory values |

The other pads dark. Bright = the page shown.

- **Opening it:** a tap on the button of the track already selected leaves it open; it closes when you let go of a menu pad, tap the button again or press any other button. Holding a track's button (¼ s) opens it only while held, like the original's view buttons.
- **Holding** a page pad (½ s or more) shows it only until you let go.
- Up to Alpha 0.11 the menu was: 1 stock, 2 Stock+, 3 Granular, 4 Synth, 5 Envelope, 6 Matrix, 7 Sequenceable, 8 Project init, 16 Non-sequenceable.

*(Alpha 0.13)*: with the FM, the menu's **row 3** = operators 1-8. The sticky menu no longer closes when you pick a page, nor with Shift, Clear or Duplicate.

<a id="stockplus"></a>
### 2.3 Stock+ page

*How to get there:* track menu, pad 2, on a track with a sample, the granular or the synth

The Stock+ page is per track and stays until power-off *(since Alpha 0.01; K5-K8 since Alpha 0.02)*. It acts on the track's sample; with the granular or the synth, on them *(Alpha 0.07)*.

| Knob | Alone | With Shift |
|---|---|---|
| K1 | ★ pitch envelope: centre = none; right = each hit starts higher, left lower (up to ±24 semitones) | fine |
| K2 | ★ how long it takes to return to the note (5 ms - 4 s) | fine |
| K3 | ★ pitch LFO rate: centre = off; right = free (0.05-30 Hz); left = synced, from 8 bars by the centre to 1/16T at the end *(since Alpha 0.05)* | fine |
| K4 | ★ pitch LFO depth (0-24 semitones) | fine |
| K5 | ★ ring mod amount | ★ its frequency (20 Hz-5 kHz) |
| K6 | ★ pitch follow: the low-pass cutoff follows the note | ★ filter type over the original's filter knobs: **stock** (white), **24 dB** (orange), **comb** (lavender) |
| K7 | ★ **stretch**: slower (left, down to 0.25×) or faster (right, up to 4×) without changing pitch; centre = the original | ★ bitcrush |
| K8 | ★ scan rate (moves each note's start; on a loop, the loop's start on every pass): centre = still; right = free (0.05-20 Hz); left = synced, faster towards the end *(since Alpha 0.05)* | ★ its depth |

- **LEDs:** sky blue with the value as brightness (K1, K3, K7 and K8: the distance from the centre); K6 in its filter type's colour. With Shift, K5-K8 show their second layer.
- **Clear + knob:** its default (on K5-K8, both layers).
- **Saved with the project.** In Alpha 0.04 projects, the synced half of K3 and K8 now runs the other way.
- **The stretch** splits the sample into ~43 ms grains kept in phase (WSOLA): at 0.5× it sounds very good; at 0.25× drums may click.

**With the granular or the synth** *(Alpha 0.07)*: the track's same values, on its sound.

| Knob | Granular | Synth |
|---|---|---|
| K1-K4 | the pitch envelope and LFO, on each new grain's pitch | the pitch envelope and LFO, on both oscillators |
| K5, K6 | ring, pitch follow and the filter type, on its filter | the same |
| K7 | ★ **waveshaper**: amount (0 = off; the gain from ×1 to ×16; for bitcrush, the bits). Shift: its **type**, **soft** (gold), **hard** (red-orange), **fold** (teal), **bitcrush** (lime) | the same |
| K8 | ★ an LFO on the grains' **position** (Shift: its depth) | ★ an LFO on the **FM amount** (Shift: its depth) |

- **Filter type** (Shift + K6): with **24 dB** its filter runs twice; with **comb** its filters open and a comb plays, tuned by the track's low-pass knob (plus the follow; on the synth, plus envelope → filter), with the resonance as feedback.
- K7's LED is in the type's colour, as bright as the amount; with Shift, fully. Clear + K7: off and soft.
- The waveshaper is saved with the project and goes along with Clear + the track's button and Duplicate.

<a id="granular"></a>
### 2.4 Granular page

*How to get there:* Sample mode, pad 6 (puts the granular on, with its page), or track menu, pad 3 (its page)

The CIRCUIT-HACKS granular engine on the track's sample, on the master DSP *(since Alpha 0.04)*. It follows the note (Note view, keyboard and MIDI). The track's filter knobs (high-pass, low-pass, resonance) and envelope act on it; the distortion too *(Alpha 0.07)*. **Up to 4 granular tracks**, each with its own settings; the 16 grains are shared (16 with one track, 7 each with two, 4 with three, 2 with four).

| Knob | Alone | With Shift |
|---|---|---|
| K1 | grain size (5-500 ms) | fine |
| K2 | density (1-16 grains) | ★ stereo spread (0 = mono) |
| K3 | position in the sample | fine |
| K4 | scan: centre = still; right forward, left backward | fine |
| K5 | pitch (centre = the note; ±24 semitones) | fine pitch |
| K6 | position spray | zone (which part of the sample) |
| K7 | pitch spray | reverse chance |
| K8 | window (rectangle → triangle → percussive) | gate, on / off: dim = always sounds (drone), bright = opened by the notes *(since Alpha 0.05)* |

Lilac with the value as brightness (K4, K5 and Shift + K5: the distance from the centre). Clear + knob = default. Saved with the project.

**The original's start and length** *(Alpha 0.09)* (stock page, K2 / K3): the start adds to the position (this page's K3), up to the sample's end; the length narrows the zone (fully up, its default, changes nothing).

<a id="sinte"></a>
### 2.5 OSC 1 / OSC 2 pages (the VA)

*How to get there:* Sample mode, selector (pad 8), pad 20 (puts the VA on); track menu, pads 2 / 3

★ CIRCUIT-HACKS' VA oscillators as any track's sound *(Alpha 0.12)*: two oscillators with a sine → triangle → saw → square morph, a shape per wave (fold, curve, 5-saw supersaw or pulse width), FM both ways, ring, sync and bitwise modes. Up to 4 synth slots (VA or [FM](#fm)) across all tracks, shared with the [polyphony](#voces). It gets its notes like a sample does (pads, Note view, sequence, MIDI).

**OSC 1** (menu, pad 2; a VA's Synth page):

| Knob | Alone | With Shift |
|---|---|---|
| K1 | tune (±24 semitones) | envelope → pitch |
| K2 | fine | glide |
| K3 | wave (morph; its LED in the nearest wave's colour: sine white, triangle green, saw red, square yellow) | octave |
| K4 | shape | envelope → shape |
| K5 | envelope → FM (from the centre) | — |
| K6 | envelope → ring (from the centre) | — |
| K7 | envelope → morph (from the centre) | — |
| K8 | envelope → mix (from the centre) | — |

**OSC 2** (menu, pad 3):

| Knob | What it does |
|---|---|
| K1 | OSC 2 tune (±24 semitones) |
| K2 | OSC 2 fine |
| K3 | OSC 2 wave |
| K4 | OSC 2 shape |
| K5 | FM: nothing in the centre; right OSC 2 → OSC 1, left OSC 1 → OSC 2 |
| K6 | ring |
| K7 | sync and bitwise modes, by zones: none, sync, xor, or, nor, and, nand (each zone in its colour) |
| K8 | mix OSC 1 ↔ OSC 2 |

- **The envelope** is the [Envelope](#envolvente) page's (its K2 = the release). Glide and octave also on the [voice dropdown](#voces).
- **The original's knobs** of the track still act: filter, envelope, pitch, distortion, level… (stock page or [Filter / VCA](#filtro)).
- **LEDs:** mint, brightness = the value; the bipolar ones dark in the centre and lighter to the left *(Alpha 0.12)*.
- Clear + knob = default. **Saved with the project**; OSC 1's tune and fine and the three envelope depths go to the card with the [project's sound](#guardado).
- Up to Alpha 0.11 the synth was another one (two classic oscillators with SUB and noise, one page).

*(Alpha 0.13)*: **OSC 2 follows OSC 1** as a harmonic ratio (OSC 2's K5: 0.25 … 31; its fine ±50 cents), as in CIRCUIT-HACKS. Fixed: K6 (FM) did nothing and RING also set the FM. **2× oversampling** (Sample mode, selector, pad 4 on a VA track): less aliasing in the high notes with FM and sync, when the DSP has room. Choke (pad 29) on a synth switches the voice mode's side; reverse flips the Envelope.

<a id="filtro"></a>
### 2.6 Filter / VCA and Envelope + LFO pages

*How to get there:* track menu, pads 4 and 5 (any track)

★ Two pages gathering knobs from others *(Alpha 0.12)*. Each knob moves the usual value (the original's, the Envelope's or Stock+'s), with its steps and its Clear, and the matrix's lanes record it the same way.

**Filter / VCA** (pad 4, lime):

| Knob | What it does |
|---|---|
| K1 | the track's **level** (the Mixer's) |
| K4 | the original's envelope |
| K5 | envelope → low-pass (granular and synth; from the centre) |
| K6 / K7 / K8 | the original's high-pass, low-pass and resonance |
| K2 / K3 | nothing (dark) |

**Envelope + LFO** (pad 5):

| Knob | What it does |
|---|---|
| K1-K4 | the [Envelope](#envolvente) page's: start, length, slope, → filter (granular and synth; rose) |
| K5 | [Stock+](#stockplus)'s LFO rate (from the centre: right free, left synced; sky blue) |
| K6 | Stock+'s LFO depth (sky blue) |
| K7 / K8 | nothing |

Both stay until you pick another page or change the track's engine.

<a id="fm"></a>
### 2.7 8-operator FM

*How to get there:* Sample mode, selector (pad 8), pad 24 (puts the FM on; one more tap: the FM page)

★ CIRCUIT-HACKS' 8-operator FM, with DX7 envelopes and 56 algorithms, as any track's sound *(Alpha 0.12)*. It shares the 4 synth slots with the [VA](#sinte).

**The FM page** (Sample mode, a tap on pad 24 of a track with FM; all 32 pads are its own):

| Pad | What it does |
|---|---|
| **9-16** | the operator 1-8 to edit (carriers green, modulators blue, the chosen one bright; those the algorithm does not use, off) |
| **3** | the pitch envelope (lavender) |
| **7 held** | the 56 algorithms on pads 9-32, in three pages with ▼ / ▲ (the 4-operator ones green, the 8-operator ones amber, the DX7's white); one pressed = that algorithm |
| **Clear + 7** | a playable voicing of the algorithm (every ratio 1) |
| **8 held** | the 24 starting instruments (in their family's colour); one pressed = loaded |
| **7 (tap)** | closes the page |

**The knobs** (on the FM page and on the Synth page of a track with FM: menu, pad 2 = the operator, pad 3 = the pitch envelope):

| Knob | Operator | With Shift |
|---|---|---|
| K1 | ratio | algorithm |
| K2 | fine | feedback |
| K3 | output level | rate scaling |
| K4 | velocity sensitivity | level scaling |
| K5-K8 | its envelope's R1-R4 | L1-L4 |

With the pitch envelope: K1 transpose, K3 noise, K4 its operator, K5-K8 R1-R4 (Shift: L1-L4). Lavender, brightness = the value. Clear + knob = the initial value.

- **Sample mode, pad 24 held:** the 24 instruments on rows 1, 2 and 4, without opening the page.
- **Polyphony and voice modes:** [Voice](#voces).
- **Saved with the project on the card** (the pack's patch bank) *(Alpha 0.12)*; not on the internal pack nor in the S builds.

<a id="voces"></a>
### 2.8 Voice: modes, polyphony and unison

*How to get there:* Sample mode, selector (pad 8), pad 16 (VA and FM)

★ CIRCUIT-HACKS' voice modes for the VA and the FM *(Alpha 0.12)*. There are **4 synth slots** across all tracks; polyphony and unison take the free ones.

- **A tap on pad 16:** polyphony on / off (back to the last mono mode). With little DSP left, a new note takes the oldest voice.
- **Pad 16 held:** the modes on pads 17-24 (the current one bright; pad 16 shows in the mode's colour), and the knobs:

| Pad | Mode |
|---|---|
| 17 (green) | **retrigger**: every note retriggers the envelope |
| 18 (yellow) | **legato**: a note overlapping the previous one only changes the pitch (no envelope or FM operator retrigger) |
| 19 (teal) | **glide**: like legato, and the pitch slides; a detached note starts at its own pitch |
| 20 (green) | **uni retrig**: all the track's voices on the same note, detuned with K2 |
| 21 (yellow) | **uni legato** |
| 22 (teal) | **uni glide** |
| 23 (violet) | **uni always-glide**: always slides, also after a release |
| 24 (magenta) | **poly**: up to 4 notes at once |

| Knob (pad 16 held) | What it does |
|---|---|
| K1 (teal) | glide |
| K2 (blue) | unison detune (up to ±50 cents on the outer voices) |

- With 3 or 4 voices in unison the level drops (0.82 / 0.71) so it does not clip.
- A track that never picked a mode sounds as up to Alpha 0.11.
- **Saved with the project on the card** *(Alpha 0.12)* (not in the S builds).

<a id="envolvente"></a>
### 2.9 Envelope page

*How to get there:* track menu, pad 5, on a synth or granular track

★ The synth's and the granular's envelope, by the track's **play mode** (Sample mode, pads 25 / 26 / 27) *(Alpha 0.06)*:

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

<a id="matriz"></a>
### 2.10 Matrix, Sequenceable and Non-sequenceable

*How to get there:* track menu, pads 6, 7 and 16 (any track)

★ Three pages to modulate and automate *(Alpha 0.10)*. A tap latches the page, holding lasts until you let go, and again removes it.

**Destinations (32 per track):** row 1 = the original's K1-K8; row 2 = Stock+'s K1-K8 (K7: stretch on a sample, the waveshaper on the granular and the synth); rows 3-4 = the sound's page (synth 16 values, granular 13, sample Stock+'s Shift + K5-K8). An input track only has the original's. When you pick one, the pads show where it is for 1.5 s, in its page's colour.

**Matrix (pad 6):** K1-K8 are the sources.

| Knob | Source | With Shift |
|---|---|---|
| K1 | velocity | |
| K2 | note | |
| K3 | random per note | |
| K4 | LFO 2 | 4 zones (triangle, saw, square, sample & hold), each with 32 rates: first half synced, second half free, dark at the centre |
| K5 | envelope 2 | attack (4, a colour each) and decay (32) |
| K6 | a track's hit | the track and the decay |
| K7 | position in the pattern | |
| K8 | random by steps | steps per value: 1, 2, 4, 8 |

The knob's position is destination + amount: off at the start, then 16 clicks per destination. Its LED takes the destination page's colour, with brightness = the amount. Clear + knob turns it off; Clear + Shift + knob resets the source's parameter.

**Sequenceable (pad 7):** K1-K8 are the 8 automation lanes. The knob moves its lane's destination and records into it. Shift + knob picks the destination (4 clicks each). Clear + knob erases the lane in all 8 patterns and gives it back to the original's K.

**Non-sequenceable (pad 16):** K1-K8 move their destination (Stock+ K1-K8 from the factory) and are never recorded, not even with Record. Shift + knob picks the destination; Clear + knob, the factory one.

**Automatic lanes:** with Record, a Stock+, Granular or Synth knob is recorded too: into that destination's lane or, if it has none, into the highest free lane, which adopts it. So the Sequenceable page fills itself.

**Extra lane:** a ninth automation per track, one value per step. The first destination that finds no lane takes it; with no lanes left, other destinations are not recorded. Clear + Shift + any Sequenceable knob erases it in all 8 patterns.

The menu's pad 8 also brings the matrix and the Non-sequenceable page back to factory values; lanes keep their destination and data.

*(Alpha 0.13)*: **every parameter** (but the FM's operators) is a destination, in the order of the track's views and only those its engine has: OSC 1's extras, the Envelope, the waveshaper type, Stock+'s Shift layer, level, pan and sends.

<a id="entrada"></a>
### 2.11 Line input and stereo link

*How to get there:* Sample mode, pads 8 / 15 / 16 and 14

Since Alpha 0.12 they are [Sample mode](#samplemode)'s engine selector (pad 8); in Alpha 0.09-0.11, Sample mode's pads 8 (input), 15 (source) and 16 (gate); up to Alpha 0.08, the track menu (input 13, gate 14, source 15, link 9).

**Line input** (selector, pads 18 / 19; since Alpha 0.04): the audio input plays as the track's sound, with its level, pan, sends, filter and envelope.
- One input track: L + R. Two: the lower-numbered one is L, the higher R. Setting a third removes the first one set.
- **The gate: pad 18 = no gate** (always sounds, straight to the mix); **pad 19 = gated**: only while its notes play, through the track's VCA and filter (low-pass, high-pass, resonance; the filter since Alpha 0.06).
- **The source** (Alpha 0.06; pad 2 with 18, pad 3 with 19): the inputs (dim amber, no FX; up to Alpha 0.07, amber) → the **reverb return** (cream) → the **delay return** (peach), in turn; each input track its own. The return arrives a block late (0.67 ms).
- **An FX into an input** *(Alpha 0.09)*: the return an input track takes no longer goes to the master; it only sounds through the track. That track's send into its own effect is at three quarters *(Alpha 0.10)* (the full knob = three quarters of a send; half in Alpha 0.09), so the feedback stays contained; its send into the other effect is whole. Up to Alpha 0.08 the return also sounded through the master and the send into its own effect fed back.

**Stereo link** (pad 14; since Alpha 0.04): the track (left) and the next one (right) play together with the first one's notes. Pad 14 on either = undo. Dark on track 8 alone. Not linked: Stock+'s free LFO and scan, and the stretch's WSOLA.
- **The second track, as offsets** *(Alpha 0.09)*: its K1-K8 (stock page) are offsets from the first one's: centre = the same, right adds, left subtracts. Its LEDs steel blue, dark at the centre. Clear + knob = the centre.
- **Its sample** = the first one's + the gap between their pads: by default the next one; picking another pad on the second changes the gap, and moving the first one's moves both *(Alpha 0.09)*.
- **Its own steps play too** *(Alpha 0.09)*: the second plays the first one's notes and its own as well.
- Linking puts the second's knobs at the centre (it sounds the same); unlinking leaves them where they sounded. An Alpha 0.04-0.08 project with a link loads as it sounded.

Both are saved with the project.

<a id="note"></a>
### 2.12 Note view

*How to get there:* the Note button

| Gesture | What it does |
|---|---|
| **Keys held** (arpeggiator on) | ★ arpeggio of the held notes on the track's sample; recorded with Record and Play *(since Alpha 0.0)* |
| **Shift + key** | ★ **latch** *(Alpha 0.12)*: the note goes into or out of the track's chord (up to 6; ice blue). Then every note you play or sequence sounds the chord moved to it (the root = the lowest note): a moving chord. With the arpeggio, the arpeggio plays the chord. A mono track plays the root; chords need [polyphony](#voces) |
| **Clear + Note** | ★ empties the latch's chord *(Alpha 0.12)* |
| **Shift + Note** in the expanded Note view (Note twice) | ★ the track's **own scale** editor (up to 0.11: Shift held in the Note view) *(since Alpha 0.0)* |

**The editor:** the 32 pads are two piano octaves from the tonic (row 4 = the white keys of the lower octave, pad 25 = the tonic; row 3 = its black keys; rows 2 / 1 = the upper octave). Each key switches its degree on or off (7 at most); the highest is the **period**: the next iteration's tonic (the octave or another, up to 24 semitones). Tonic white, degrees green, period blue.

When the editor closes, the keyboard plays the scale: one iteration per row (two if it has 4 notes or fewer); ▲ / ▼ move a row. With no keys, the original piano returns. Saved with the project.

## 3. Steps and pattern

<a id="velocity"></a>
### 3.1 Velocity and Micro Step

*How to get there:* the Velocity button; Micro Step = Shift + Gate

| View | Gesture | What it does |
|---|---|---|
| Velocity | **Shift held** | ★ the **automation view** *(Alpha 0.09)*: steps with knob automation in **yellow**, the marked ones in **red**, the others as the view draws them |
| Velocity | **Shift + a yellow step** | ★ **listen to it** *(Alpha 0.09)*: its values go to the knobs and the sound, those knobs yellow (brightness = the value); another yellow step sets its own; let go of Shift and everything goes back |
| Velocity | **Shift + another step** | marks the step *(since Alpha 0.04)*: when it plays, automation is silent there and automated parameters go back to **Project init** *(Alpha 0.09)* (up to Alpha 0.08, to their knob's position); a knob turned by hand stays where you left it. Again = unmark |
| Velocity | **Velocity again** | ★ the automation view **latched**, without holding Shift *(Alpha 0.09)*: a tap on a yellow step listens to it, on another marks it. Velocity again, or another view, removes it (what you were listening to goes back). Shift + Velocity is still the original's fixed velocity |
| Velocity | **Clear + step** (with or without Shift; Clear first) | ★ erases that step's knob automation; its notes, its mark and the Mixer's lanes stay *(Alpha 0.09)* |
| Velocity | **Yellow step held + another step** (automation view) | ★ **ramp** *(Alpha 0.10)*: each knob lane with a value at either end gets the straight line between them, micro step by micro step; an end without a value uses the current value |
| Track view (Samples) | **Record held + step** | ★ **snapshot** *(Alpha 0.09)*: each knob not at Project init goes into that step (its 6 micro steps); the step's pad yellow while you hold it; when you let go of Record, recording as it was |
| Micro Step | **pad 31** | fixed length: off → the selector on pads 17-32 (1-16 steps; picking one switches it on); on → off (orange bright / dim) *(since Alpha 0.04)* |
| Micro Step | **pad 32** | gate by press: the hit lasts as long as you hold the step's pad; holding an empty step 300 ms or more also creates it (green bright / dim) *(since Alpha 0.04)* |

Switching one of the two Micro Step options on switches the other off. With either, a hit entered by hand on the steps takes that length.

A track's **Project init** *(Alpha 0.09)*: its parameters as the project was last loaded or saved (taken again on every save). Pad 8 of the [track menu](#menu) (red) brings its voice back there.

<a id="patternsettings"></a>
### 3.2 Pattern Settings and probability

*How to get there:* the Pattern Settings button (twice: the probability view, mode 1)

| Gesture | What it does |
|---|---|
| **Pad 26** (blue) | Nudge: moves the chosen range one step back; with Shift, forward. Steps, lanes and per-step values go with it *(Alpha 0.10)* |
| **Pad 27 / 28** | **fractal** (1 · 1 2 · 1 2 3 …) and **deconstructed** (1 6 11 16 · 2 7 12 13 …) orders; a direction pad goes back to the original *(since Alpha 0.0)* |
| **Pad 25** (grey) | probability view, mode 2: pick a step; **row 3 = dynamics** (velocity and delay within the step; with Record, each step with dynamics is written as it played), **row 4 (25-28) = sample mutation** (sometimes its neighbour plays) *(since Alpha 0.0)* |
| **Pattern Settings twice** | probability view, mode 1: **row 4 = frequency** of the step: it plays on the last of every n passes *(Alpha 0.10)*; each pattern of a chain keeps its own count, and when it does not play, the previous note rings on *(since Alpha 0.0)* |
| **Clear + pad 25** | clears the pattern's dynamics and mutation (frequency stays) *(since Alpha 0.04)* |
| **Shift + pad 25** | ★ the track's arpeggiator on / off (green bright / dim) *(since Alpha 0.0)* |
| **Shift + pads 1-4** (arpeggiator on) | ★ octave spread: none, +1, +1 / −1, +2 / −1 *(Alpha 0.10)* |
| **Shift + pads 5-8** (arpeggiator on) | ★ when the octave changes: after a cycle, every note, every 3, every 4 *(Alpha 0.10)* |
| **Shift + pads 9-12** (arpeggiator on) | ★ groove: none, note / dotted note, swing, each note twice *(Alpha 0.10)* |
| **Shift + pads 13-16** (arpeggiator on) | ★ restart: none, after 1 / 3 / 5 notes of the second cycle *(Alpha 0.10)* |
| **Shift + pads 27-32** | arpeggio order: fractal, deconstructed, up, down, ping-pong, random |
| **Shift + pads 17-24** | arpeggio resolution (1/4 … 1/32T); the same one again = the track's sync rate |

The arpeggiator's rows with Shift: the chosen option bright green, the others dim green (since Alpha 0.05). The arpeggio modifiers come from CIRCUIT-HACKS and are saved per pattern; with the arpeggiator off, those pads do the original's. Per-step values travel with the hit when quantizing, nudging, copying a step and with the original's Mutate.

<a id="patterns"></a>
### 3.3 Patterns: chains

*How to get there:* the Patterns button

| Gesture | What it does |
|---|---|
| **Shift + the upper page button** | chain mode (green) *(since Alpha 0.0)* |
| In the mode: **a pattern** (A), **again** (n + 1 passes), **another** (B), **one more** (C) | rule "n times A, then B; the next time, C" (AAB AAC …) |
| **Clear + pattern** | no rule |
| **Shift + the lower page button** | out of the mode: the original's chain |

Each scene remembers the mode it was saved with. The rules are saved with the project.

<a id="mutate"></a>
### 3.4 Pattern Mutate

*How to get there:* Patterns or Mixer: Shift + Duplicate

Designed by **[mefisme](https://github.com/mefisme)** (Rhythm Plus, MIT), with our own code *(Alpha 0.13)*. Each chosen track plays a random list of patterns made from its chain, instead of the chain.

| Gesture | What it does |
|---|---|
| **Shift + Duplicate** (a tap, Patterns or Mixer) | a new seed: the chosen tracks play their list from their next pattern end |
| **Shift + Duplicate held** (Patterns) | the settings page (red-orange; chosen = bright) |
| On the page: **column 1 / 2** | the list's length 1-4 / 5-8 |
| **column 3** | length type: as the chain / exact / random up to the length |
| **columns 4-5** | how much changes: all, 7, 6, 5 / 4, 3, 2, 1 slots |
| **column 6** | repeats yes / no; **column 7**: keep the first slot |
| **Track buttons** | the tracks it mutates |
| **Clear + Duplicate** (any view) | ends every list; **a pattern pad** ends its track's |

A mutating track ends its chain on its list's last slot (so the next scene comes in on time).

## 4. Samples

<a id="samplemode"></a>
### 4.1 Sample mode

*How to get there:* the Samples button twice

| Gesture | What it does |
|---|---|
| **Pads 1 / 2** (the original's) | fit the sample to the pattern by changing its pitch; since Alpha 0.04 they switch the stretch off first |
| **Pads 9 / 10** | ★ the same with the **stretch** (Stock+'s K7), keeping the pitch: the next / the previous length *(since Alpha 0.04)* |
| **Pad 19** | ★ the selected track's loop de-clicker (a 256-sample crossfade) **and its retriggers'** in any mode, reverse too *(Alpha 0.12)*, on / off (blue bright / dim); on by default, saved with the project *(since Alpha 0.04)* |
| **Pad 14** | ★ [stereo link](#entrada) with the next track (steel blue) |
| **Pad 8** | ★ **the engine selector** *(Alpha 0.12)*: opens and closes the engine row (in the track's engine colour: open bright, closed dim) |

**With the selector open** (pad 8 again, or leaving Sample mode, closes it; picking an engine keeps it open). Rows 1-3 belong to the selector; the sample-only options (1 / 2, 9 / 10, 19, the slices 22-24 and 31 / 32) are hidden; 25-30 as always:

| Pad | What it does |
|---|---|
| **17** | **sample** (cyan) |
| **18** | **input only** (white): the [line input](#entrada) straight to the mix, without filter or VCA; its source on pad **2** |
| **19** | **input → VCA / VCF / FX** (amber): with the track's filter and envelope; its source on pad **3** |
| **20** | **VA** (mint): [OSC 1 / OSC 2](#sinte) |
| **21 / 22** | VA-drum and wavetable: dark, not on the Rhythm yet |
| **23** | **granular** (lilac): [Granular](#granular) |
| **24** | **FM** (lavender): [8-operator FM](#fm); with FM already on, a tap = the FM page, held = the 24 instruments on rows 1, 2 and 4 |
| **16** | the [voice](#voces) (VA and FM): tap = polyphony, held = the voice modes on 17-24 |
| **14** | the stereo link |
| **8** | closes |

The track's engine bright, the others dim. The input's source: the inputs (dim amber), the reverb return (cream), the delay return (peach).

Shift + these pads, as the original. Very short loops play at their own length (the original repeated them every ~128 samples). Up to Alpha 0.11 the sound was on pads 5-8, the input on 15 / 16 and VA / FM / poly on 11-13.

<a id="samplerec"></a>
### 4.2 Sample Rec

*How to get there:* the Sample Rec button

| Gesture | What it does |
|---|---|
| **Pad 23** | ★ every track's loop de-clicker, on / off (on at power-up) *(since Alpha 0.04)* |
| **Pad 24** | ★ **stereo recording**: L into the chosen slot, R into the next one (which must be empty; otherwise only the first, in mono); off at power-up *(since Alpha 0.04)* |
| **Duplicate + slot A, Duplicate + slot B** | ★ copies sample A into B, also from another pack (not in the S versions) *(since Alpha 0.01)* |
| **Fixed Recording** (pads 17-21, the original's) | with an external MIDI clock, it uses the incoming clock's tempo *(since Alpha 0.02)* |

**Copying a sample** (transport stopped): Duplicate + a slot with a sample (blinks yellow); Duplicate + slot B (in this pack or, after loading another, in that one): green ~1.5 s and B plays at once. If B has a sample, it blinks white and Duplicate + B again within ~5 s overwrites it. Red = it couldn't (memory full, device busy or the internal pack).

<a id="patches"></a>
### 4.3 Pack patches and starters

*How to get there:* Sample mode: hold an engine pad, or pad 8

Each pack has **64 synth and granular patches** in its patch bank on the card *(Alpha 0.13)*.

| Gesture | What it does |
|---|---|
| **Pad 8 held** (with the selector open or closed) | the pack's 64 patches on rows 1, 2 and 4; **▲ / ▼** = the page |
| In the list: **a tap** | loads the patch on the track (sets its engine) |
| **Clear + patch, twice** | saves the track's sound in that slot |
| **Duplicate + A, then B** | swaps A and B; **Duplicate + A, another pack, Duplicate + B** = copies A to B |
| **Engine pad held** (20 VA, 23 granular, 24 FM) | its **starters**: 8 VA, 8 granular or the 24 FM instruments; a tap loads |
| **Clear + track button** (track views) | the track goes back to the last patch or starter it loaded |
| **Clear + knob** (OSC 1 / OSC 2, Granular, FM) | that knob goes back to the loaded patch's value |

An empty slot of the pack first shows an example patch until you save over it. **Not in Alpha 0.13S or 0.14S** (they write to the card).

## 5. Mix and effects

<a id="mixer"></a>
### 5.1 Mixer

*How to get there:* the Mixer button

| Gesture | What it does |
|---|---|
| **Shift + track pad** (row 1) | mutes that track at the next bar (the pad blinks; again = cancel; stopped, at once) *(since Alpha 0.0)* |
| **Shift + knob** (levels page) | right = level 100; left = 0 (while recording, it stays as automation) *(since Alpha 0.0)* |
| **Shift + pads 9-16** | the current scene repeats 1-8 times; playing, with Shift, the pass now playing in white *(since Alpha 0.0)* |
| **Pan page, Shift + knob** right / left | ★ **cue mode** on / off (button 19 pink): the mix on the left output, the cue on the right *(since Alpha 0.04)* |
| **Cue mode, knob** | its track's cue send (knobs pink, brightness = send); a muted track with a send plays only in the cue; Clear + knob = 0 |

Pad 9 without Shift is still the original's Mute Recall. Cue mode isn't saved.

The Grid FX view (Shift + Mixer): see [Grid FX](#gridfx) *(Alpha 0.13)*. Slots latched with pad 16 show bright, as in the original.

<a id="fx"></a>
### 5.2 FX and Sidechain

*How to get there:* the FX button; Sidechain = Shift + FX

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

<a id="gridfx"></a>
### 5.3 Grid FX: the FX sequencer and the looper

*How to get there:* Shift + Mixer (the Grid FX view); Sample mode, selector, pad 21

**FX sequencer** *(Alpha 0.13)*: a track plays the Grid FX instead of samples.

| Gesture | What it does |
|---|---|
| **Sample mode, selector (pad 8), pad 21** | the chosen track is an **FX track** (blue; again = off) |
| In its view: **pads 17-32** | the 16 Grid FX slots, each dim in its effect's colour; bright = the one playing |
| **A step** | turns on its sample's slot (flip) for its note's length |
| **Hold a step** (rows 1-2) | turns its effect on until you let go |
| **Octave ▼ + step / Octave ▲ + step** | that step: a random effect / repeat the last one |
| The FX track's **K1-K8** | how much of each track goes through the Grid FX (all at first); automatable |
| **Grid FX view: slot held + K2** *(Alpha 0.14)* | the type while held, as in the original: Beat Repeat … **Auto-Filter**, **Digitiser** … Vinyl and, past Vinyl, the new **delay throw** (peach: every track's delay full) and **reverb throw** (cream); let go, the slot is back to its saved type. No more Shift + K1 |

**Looper / live sampler** *(Alpha 0.13)*, in the Grid FX view (Shift + Mixer):

| Pad | Tap | Hold | Shift + pad |
|---|---|---|---|
| **9** (records the line input) | N bars | while held | armed: starts at the next bar; stopped, when it starts |
| **10** (resamples the mix after the Grid FX, without the loops) | N bars | while held | the same |
| **11-14** (the 4 loops) | once from the start | loops until let go | loop at the tempo on / off |

- Records into the loop of the last pad 11-14 touched: **overdub** if that pad is held or its loop is looping; otherwise it replaces.
- **Shift + K8** = N: ½, 1, 2 or 4 bars (a quarter turn per step; K8 yellow, orange, red-orange or salmon). **Clear + pad 11-14** = empty.
- LEDs: 9 / 10 dim red, bright red recording, amber armed; 11-14 dark empty, dim amber with audio, medium the chosen one, bright playing.
- Up to ≈ 6.7 s per loop, stereo. Loops aren't saved.

## 6. Projects and settings

<a id="projects"></a>
### 6.1 Projects and Packs

*How to get there:* the Projects button (twice: Packs)

**Copying a project** (not in the S versions; since Alpha 0.0), transport stopped:
1. **Duplicate + a pad with a project (A)**: blinks yellow.
2. **Duplicate + an empty pad (B)**: copies A into B (green ~1.5 s). B can be in another pack: pick A, load another pack and Duplicate + an empty pad.
3. **Duplicate + a pad with a project**: blinks white (asking); **Duplicate + the same pad** within ~5 s overwrites it.

It copies the project **as saved** and never touches the loaded one. (Save + pad, the original's, saves the loaded one with its changes.)

**Deleting a pack** (Packs view; not in the S versions; since Alpha 0.01): **Clear + the pack's pad** = asks (blinks red ~5 s); **Clear + the same pad** = deletes it from the card (green ~1.5 s). Never the loaded one, the internal one or an empty slot.

The mod never writes to the internal memory's pack (red + Save LED red).

<a id="setup"></a>
### 6.2 Setup and Advanced Setup

*How to get there:* Shift + Save (Setup); Advanced Setup as in the original

| View | Gesture | What it does |
|---|---|---|
| Advanced | **Duplicate** | the Thru socket: **Thru** (green) → **Out 2** (dim red) → **Merge** (yellow: MIDI In + the device's MIDI) → **Filter** (blue: MIDI In minus the device's channels) *(since Alpha 0.0)* |
| Setup | **Pad 29 / 30** (the first time) | **Program Change** listen / send channel on pads 1-16; the pad again = PGM Rx / Tx on / off *(since Alpha 0.0)* |
| Setup | **Pad 22** | ★ the project's **General MIDI mode** (green bright / dim): the tracks play out on channel 10 with their GM note; GM notes on channel 10 play their track *(since Alpha 0.04)* |
| Setup | **K1-K8**, with GM mode | each track's GM note (35-81, two clicks a note; each new note plays once). Factory: 36, 38, 42, 46, 39, 37, 45, 49 |
| Advanced | **Pad 22** | ★ external keyboard into the arpeggiator: notes coming in on the channel of a track with its arpeggiator on are arpeggiated (green bright / dim) *(since Alpha 0.04)* |
| Advanced | **Pad 23** | ★ USB merge: what comes in on DIN In also goes out over USB (green bright / dim) *(since Alpha 0.04)* |
| Advanced | **Pad 24** | ★ **save on stop** (green bright / dim; off from the factory): while playing, Save waits for the stop and blinks yellow *(Alpha 0.10)* |
| Advanced | **K1** | ★ **velocity curve**: −8 .. +8, 2 clicks a step, centre = the original; to the right soft hits sound louder, to the left the opposite *(Alpha 0.10)* |

Everything is saved in the device's settings, except GM mode, which goes with the project. If the two Program Change channels differ, the received one is forwarded on the send channel.

*(Alpha 0.13)*: GM mode, the knobs show their note as brightness, and a new note plays on the track.

## A. Appendix

<a id="guardado"></a>
### A.1 What is saved and where

| Where | What |
|---|---|
| **With the project** | the matrix, the lanes and the Non-sequenceable page, the arpeggio modifiers, Stock+, Granular, Synth (settings and tracks), Envelope, the input's source, line input, stereo link (with the second track's offsets), per-track de-clicker, own scale, chain rules, per-step dynamics / mutation / frequency, Velocity marks, Micro Step, GM mode, reverb / delay / sidechain |
| **On the card, with the project** *(Alpha 0.12)* | the pack's patch bank (`Patches/NN_PATCHBANK.cpb`): each track's 8-operator FM, the voice modes, the unison detune, the VA's OSC 1 tune / fine and envelope depths. Not on the internal pack nor in the S builds |
| **Device settings** | Program Change channels, Thru mode, keyboard into the arpeggiator, USB merge, save on stop, velocity curve, master filter resonance, compressor |
| **Until power-off** | each track's knob page, Project init (what was loaded or saved), cue mode, metronome / count-in, Sample Rec pads 23 / 24 |

The mod's own data goes in a part of the project file the original doesn't use. A project from an earlier version loads without what that version lacked. **Keep copies of your projects.**

<a id="midi"></a>
### A.2 MIDI

The new knobs move the original's parameters with their usual MIDI (Circuit Rhythm programmer's guide): sidechain NRPN 1:1-1:4 (the track's channel); reverb NRPN 1:18-1:20; delay NRPN 1:6-1:11; master resonance CC 71; compressor NRPN 1:22-1:26. The Stock+, Granular and Synth pages have no MIDI yet.

<a id="modulos"></a>
### A.3 Arrhythmia modules (proof of concept)

*How to get there:* from the computer, over USB

★ *(Alpha 0.11)* **A proof of concept, only in Alpha 0.11 and 0.11S.** Not in Alpha 0.10 / 0.10S, the earlier ones or the official firmware: with those the app gets no answer. Circuit Remix runs **[Arrhythmia](https://github.com/llcoolkm/arrhythmia)'s modules** (by llcoolkm, MIT licence): small programs (`.mod`) that take over the lights, pads and buttons and can play notes, move parameters and send MIDI. The modules, their interface and its documentation are Arrhythmia's; Circuit Remix brings its own code for that interface, so the same file works on both firmwares. The modules are not in this repository: **download them from [Arrhythmia's releases](https://github.com/llcoolkm/arrhythmia/releases)** and see their controls in [its modules guide](https://github.com/llcoolkm/arrhythmia/blob/main/docs/user/modules.md).

- **Upload and start:** in the [Circuit Remix app](https://github.com/Ghillermo/CIRCUIT-REMIX#the-circuit-remix-app-toolsrm_apphtml) (`rm_app.html`), button **Modules (proof of concept)…**: pick the `.mod`, the app checks it (header and CRC), uploads it, reads it back and starts it.
- **While it runs:** a module with an input takes the pads and buttons; **Shift** and the knobs stay the original's, **Play** still drives the transport. **Shift + Sample Rec** stops it and gives everything back.
- **Lost at power-off** (it lives in the processor's fast RAM). It does not read the card: no Arrhythmia module picker.
- A module is code that runs on the device: **only use modules you trust.**

<a id="glosario"></a>
## Glossary of functions

| Function | What it is / gesture | Chapter | Since |
|---|---|---|---|
| **2× oversampling** | the VA with less aliasing; Sample mode, selector, pad 4 | [2.5 OSC 1 / OSC 2 pages (the VA)](#sinte) | Alpha 0.13 |
| **8-operator FM** | CIRCUIT-HACKS' FM; Sample mode, selector, pad 24 | [2.7 8-operator FM](#fm) | Alpha 0.12 |
| **Arpeggio modifiers** | octaves, groove and restart; Pattern Settings, Shift + pads 1-16 | [3.2 Pattern Settings and probability](#patternsettings) | Alpha 0.10 |
| **Arrhythmia modules** | proof of concept: its `.mod` files over USB from the card app; Shift + Sample Rec stops | [A.3 Arrhythmia modules (proof of concept)](#modulos) | Alpha 0.11 |
| **Automation view** | steps with knob automation in yellow, and listening to them; Velocity + Shift, or Velocity again (latched) | [3.1 Velocity and Micro Step](#velocity) | Alpha 0.09 |
| **Bitcrush** | Stock+, Shift + K7 | [2.3 Stock+ page](#stockplus) | Alpha 0.02 |
| **Clear a step's automation** | Clear + step in Velocity | [3.1 Velocity and Micro Step](#velocity) | Alpha 0.09 |
| **Compressor threshold** | Sidechain view K5 | [5.2 FX and Sidechain](#fx) | Alpha 0.01 |
| **Copy projects** | Duplicate + A, Duplicate + B in Projects, also to another pack | [6.1 Projects and Packs](#projects) | Alpha 0.0 |
| **Copy samples** | Duplicate + A, Duplicate + B in Sample Rec | [4.2 Sample Rec](#samplerec) | Alpha 0.01 |
| **Copy track parameters** | Duplicate + track A, track B | [2.1 The track button](#pista) | Alpha 0.0 |
| **Count-in** | a bar before recording; Shift + Clear; since 0.08 on the music's clock, also as a slave | [1.1 Transport, metronome and quantize](#transporte) | Alpha 0.0 |
| **Cue mode** | mix on the left, cue on the right; Mixer, pan, Shift + knob | [5.1 Mixer](#mixer) | Alpha 0.04 |
| **Delay / reverb throw** | new Grid FX types; slot held + K2 (since 0.14) | [5.3 Grid FX: the FX sequencer and the looper](#gridfx) | Alpha 0.13 |
| **Delete a pack** | Clear + pack twice in Packs | [6.1 Projects and Packs](#projects) | Alpha 0.01 |
| **Distortion on granular and synth** | the original's distortion knob on them too | [2.2 The track menu](#menu) | Alpha 0.07 |
| **Engine selector** | sample, input, VA, granular or FM on row 3; Sample mode, pad 8 | [4.1 Sample mode](#samplemode) | Alpha 0.12 |
| **Envelope + LFO** | the Envelope and Stock+'s LFO on one page; menu, pad 5 | [2.6 Filter / VCA and Envelope + LFO pages](#filtro) | Alpha 0.12 |
| **Envelope by play mode** | start, length, slope and → filter of the synth and the granular; menu, pad 5 | [2.9 Envelope page](#envolvente) | Alpha 0.06 |
| **External keyboard into the arpeggiator** | Advanced Setup, pad 22 | [6.2 Setup and Advanced Setup](#setup) | Alpha 0.04 |
| **Extra lane** | a ninth automation, one value per step | [2.10 Matrix, Sequenceable and Non-sequenceable](#matriz) | Alpha 0.10 |
| **Filter / VCA** | level, envelope and filter on one page; menu, pad 4 | [2.6 Filter / VCA and Envelope + LFO pages](#filtro) | Alpha 0.12 |
| **Filter type (24 dB, comb)** | Stock+, Shift + K6 | [2.3 Stock+ page](#stockplus) | Alpha 0.02 |
| **Fixed length** | hand-entered hits with a set length; Micro Step, pad 31 | [3.1 Velocity and Micro Step](#velocity) | Alpha 0.04 |
| **Fixed Recording with external clock** | the length at the incoming MIDI clock's tempo | [4.2 Sample Rec](#samplerec) | Alpha 0.02 |
| **Fractal / deconstructed orders** | Pattern Settings pads 27 / 28 | [3.2 Pattern Settings and probability](#patternsettings) | Alpha 0.0 |
| **FX into an input** | a return taken by an input track leaves the master; its feedback, halved | [2.11 Line input and stereo link](#entrada) | Alpha 0.09 |
| **FX returns as a source** | the reverb or the delay as an input track's sound; Sample mode, selector, pads 2 / 3 | [2.11 Line input and stereo link](#entrada) | Alpha 0.06 |
| **FX sends on the knobs** | ▼ / ▲ in the FX view | [5.2 FX and Sidechain](#fx) | Alpha 0.0 |
| **FX sequencer** | a track plays the Grid FX; Sample mode, selector, pad 21 | [5.3 Grid FX: the FX sequencer and the looper](#gridfx) | Alpha 0.13 |
| **Gate by press** | the hit lasts as long as the pad is held; Micro Step, pad 32 | [3.1 Velocity and Micro Step](#velocity) | Alpha 0.04 |
| **General MIDI** | the tracks on channel 10 with their GM note; Setup, pad 22 | [6.2 Setup and Advanced Setup](#setup) | Alpha 0.04 |
| **Granular** | the granular engine on up to 4 tracks; Sample mode, selector, pad 23; menu pad 2 | [2.4 Granular page](#granular) | Alpha 0.04 |
| **Grid FX sends** | how much of each track goes through the Grid FX; the FX track's K1-K8 | [5.3 Grid FX: the FX sequencer and the looper](#gridfx) | Alpha 0.13 |
| **Latch** | a chord that follows every note; Shift + key in the Note view | [2.12 Note view](#note) | Alpha 0.12 |
| **Level to 100 / 0** | Shift + knob on the Mixer's levels | [5.1 Mixer](#mixer) | Alpha 0.0 |
| **Line input** | the audio input as a track's sound; Sample mode, pads 8 / 16 | [2.11 Line input and stereo link](#entrada) | Alpha 0.04 |
| **Loop de-clicker** | a crossfade at the loop point; Sample mode pad 19, Sample Rec pad 23 | [4.1 Sample mode](#samplemode) | Alpha 0.04 |
| **Looper** | 4 loops recorded from the input or the mix; Grid FX view, pads 9-14 | [5.3 Grid FX: the FX sequencer and the looper](#gridfx) | Alpha 0.13 |
| **Master compressor** | threshold, soft clip, attack and release in the Sidechain view | [5.2 FX and Sidechain](#fx) | Alpha 0.0 |
| **Master resonance** | Shift + ▲ / ▼ in the FX view | [5.2 FX and Sidechain](#fx) | Alpha 0.0 |
| **Metronome** | four states with Shift + Clear | [1.1 Transport, metronome and quantize](#transporte) | Alpha 0.0 |
| **Modulation matrix** | 8 sources per track to 32 destinations; menu, pad 6 | [2.10 Matrix, Sequenceable and Non-sequenceable](#matriz) | Alpha 0.10 |
| **Mute at the bar** | Shift + track pad in the Mixer | [5.1 Mixer](#mixer) | Alpha 0.0 |
| **Non-sequenceable** | 8 knobs that are never recorded; menu, Shift + pad 1 | [2.10 Matrix, Sequenceable and Non-sequenceable](#matriz) | Alpha 0.10 |
| **Note arpeggiator** | arpeggiates the keys held in the Note view | [2.12 Note view](#note) | Alpha 0.0 |
| **Nudge** | moves the chosen range one step; Pattern Settings pad 26 | [3.2 Pattern Settings and probability](#patternsettings) | Alpha 0.0 |
| **Own scale** | a scale per track; Shift in the Note view | [2.12 Note view](#note) | Alpha 0.0 |
| **Pack patches** | 64 synth and granular patches per pack; Sample mode, pad 8 held | [4.3 Pack patches and starters](#patches) | Alpha 0.13 |
| **Pattern Mutate** | random pattern lists per track (mefisme's design); Shift + Duplicate | [3.4 Pattern Mutate](#mutate) | Alpha 0.13 |
| **Per-step dynamics** | random velocity and delay within the step; probability row 3 | [3.2 Pattern Settings and probability](#patternsettings) | Alpha 0.0 |
| **Per-step frequency** | the step plays on the last of every n passes | [3.2 Pattern Settings and probability](#patternsettings) | Alpha 0.0 |
| **Pitch envelope** | Stock+, K1 / K2 | [2.3 Stock+ page](#stockplus) | Alpha 0.01 |
| **Pitch LFO** | Stock+, K3 / K4; free or synced | [2.3 Stock+ page](#stockplus) | Alpha 0.01 |
| **Polyphony** | up to 4 synth voices (VA or FM); Sample mode, a tap on pad 16 | [2.8 Voice: modes, polyphony and unison](#voces) | Alpha 0.12 |
| **Program Change** | listen and send channels; Setup, pads 29 / 30 | [6.2 Setup and Advanced Setup](#setup) | Alpha 0.0 |
| **Project init** | the track's voice as loaded or saved; menu, pad 16 (red; up to 0.11, pad 8) | [2.2 The track menu](#menu) | Alpha 0.09 |
| **Project's sound on the card** | the FM, the voice modes and the VA's values with the project, in the patch bank | [A.1 What is saved and where](#guardado) | Alpha 0.12 |
| **Quantize** | Shift + Play while playing | [1.1 Transport, metronome and quantize](#transporte) | Alpha 0.0 |
| **Ramps** | yellow step held + another step, in the automation view | [3.1 Velocity and Micro Step](#velocity) | Alpha 0.10 |
| **Repeat the scene** | the current scene 1-8 times; Mixer, Shift + pads 9-16 | [5.1 Mixer](#mixer) | Alpha 0.0 |
| **Retrigger de-click** | no click when a sample retriggers; Sample mode, pad 19 | [4.1 Sample mode](#samplemode) | Alpha 0.12 |
| **Ring mod** | Stock+, K5 (Shift: the frequency) | [2.3 Stock+ page](#stockplus) | Alpha 0.02 |
| **Rule chains** | patterns chained "n times A, then B" | [3.3 Patterns: chains](#patterns) | Alpha 0.0 |
| **Sample arpeggiator** | arpeggiates the held sample pads; Shift + Pattern Settings pad 25 switches it on | [2.1 The track button](#pista) | Alpha 0.0 |
| **Sample mutation** | sometimes the neighbour plays; probability row 4 | [3.2 Pattern Settings and probability](#patternsettings) | Alpha 0.0 |
| **Save on stop** | Save waits for the stop; Advanced Setup, pad 24 | [6.2 Setup and Advanced Setup](#setup) | Alpha 0.10 |
| **Scan** | moves each note's or the loop's start; Stock+, K8 | [2.3 Stock+ page](#stockplus) | Alpha 0.02 |
| **Sequenceable** | the 8 automation lanes with their own destination; menu, pad 1 | [2.10 Matrix, Sequenceable and Non-sequenceable](#matriz) | Alpha 0.10 |
| **Sidechain on the knobs** | Sidechain view K1-K4 | [5.2 FX and Sidechain](#fx) | Alpha 0.0 |
| **Snapshot** | the moved knobs into a step; Record held + step | [3.1 Velocity and Micro Step](#velocity) | Alpha 0.09 |
| **Start and length on the granular** | the original's start adds to the position, the length narrows the zone | [2.4 Granular page](#granular) | Alpha 0.09 |
| **Starters** | starting sounds per engine; Sample mode, engine pad held | [4.3 Pack patches and starters](#patches) | Alpha 0.13 |
| **Stereo link** | a track and the next as one stereo sound; Sample mode, pad 14; since 0.09 the second as offsets | [2.11 Line input and stereo link](#entrada) | Alpha 0.04 |
| **Stereo recording** | L and R into two slots; Sample Rec, pad 24 | [4.2 Sample Rec](#samplerec) | Alpha 0.04 |
| **Stock+ page** | eight more knobs per track; menu, pad 10; since 0.07 on the granular and the synth too | [2.3 Stock+ page](#stockplus) | Alpha 0.01 |
| **Stretch** | slower or faster without changing pitch; Stock+ K7, Sample mode pads 9 / 10 | [2.3 Stock+ page](#stockplus) | Alpha 0.02 |
| **Synth** | since 0.12 CIRCUIT-HACKS' VA (OSC 1 / OSC 2); Sample mode, selector, pad 20; menu pads 2 / 3 | [2.5 OSC 1 / OSC 2 pages (the VA)](#sinte) | Alpha 0.05 |
| **Thru: Out 2 / Merge / Filter** | Duplicate in Advanced Setup | [6.2 Setup and Advanced Setup](#setup) | Alpha 0.0 |
| **Track flash** | with Shift, each track's button flashes white when it plays | [2.1 The track button](#pista) | Alpha 0.10 |
| **Track knobs reset** | Clear + the track's button | [2.1 The track button](#pista) | Alpha 0.0 |
| **Track menu** | tap the selected track's button (stays open) or hold a track's button | [2.2 The track menu](#menu) | Alpha 0.04 |
| **Unison** | a track's voices on the same note, detuned; pad 16 held, K2 | [2.8 Voice: modes, polyphony and unison](#voces) | Alpha 0.12 |
| **USB merge** | DIN In also over USB; Advanced Setup, pad 23 | [6.2 Setup and Advanced Setup](#setup) | Alpha 0.04 |
| **Velocity curve** | Advanced Setup, K1 | [6.2 Setup and Advanced Setup](#setup) | Alpha 0.10 |
| **Velocity marks** | on a marked step the parameters go back to Project init (up to 0.08, to the knob); Shift + step | [3.1 Velocity and Micro Step](#velocity) | Alpha 0.04 |
| **Visual metronome** | Clear flashes orange on each click with the click's level at 0 (Tempo / Swing K5) | [1.1 Transport, metronome and quantize](#transporte) | Alpha 0.08 |
| **Voice modes** | retrigger, legato, glide, unisons and poly; Sample mode, pad 16 held | [2.8 Voice: modes, polyphony and unison](#voces) | Alpha 0.12 |
| **Waveshaper** | soft, hard, fold or bitcrush on the granular and the synth; Stock+, K7 (Shift: the type) | [2.3 Stock+ page](#stockplus) | Alpha 0.07 |
