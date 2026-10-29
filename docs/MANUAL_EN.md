# Circuit Remix Alpha 0.09 — manual

[Español](MANUAL.md) · [illustrated version](manual/en.html)

> ⚠️ **Alpha 0.09 is experimental:** what's new (the automation, the modes in Sample mode, an FX into an input, the stereo link's offsets, the synth's morph and unison) and most things since Alpha 0.04 have mostly been checked in emulation. For serious playing, Alpha 0.03. **Back up your SD card.**

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
- [2.5 Synth page](#sinte)
- [2.6 Envelope page](#envolvente)
- [2.7 Line input and stereo link](#entrada)
- [2.8 Note view](#note)

**3. Steps and pattern**

- [3.1 Velocity and Micro Step](#velocity)
- [3.2 Pattern Settings and probability](#patternsettings)
- [3.3 Patterns: chains](#patterns)

**4. Samples**

- [4.1 Sample mode](#samplemode)
- [4.2 Sample Rec](#samplerec)

**5. Mix and effects**

- [5.1 Mixer](#mixer)
- [5.2 FX and Sidechain](#fx)

**6. Projects and settings**

- [6.1 Projects and Packs](#projects)
- [6.2 Setup and Advanced Setup](#setup)

**A. Appendix**

- [A.1 What is saved and where](#guardado)
- [A.2 MIDI](#midi)

- [Glossary of functions](#glosario)

## 0. Introduction

<a id="leer"></a>
### 0.1 How to read this manual

Each chapter is a view of the device: how you get there, and what its pads, knobs and buttons do with Circuit Remix. Everything else works as in Novation's original firmware (see its manual); the new gestures are combinations that did nothing in the original or repeated the plain gesture.

- **Pads 1-32** left to right, top to bottom: row 1 = 1-8, row 2 = 9-16, row 3 = 17-24, row 4 = 25-32.
- **K1-K8** = the 8 knobs. **▲ / ▼** = the arrow buttons.
- **Hold** a button = press it and keep it down; **A + B** = B with A held.
- **★** = exclusive to Circuit Remix (not in CIRCUIT-HACKS).
- **(since Alpha 0.0x)** = the release that brought the function. Marked *(Alpha 0.09)*: new or changed in this release.
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

1. Download `rm_uploader.zip`, unzip it and open `rm_uploader.html` in Chrome or Edge.
2. Provide the official Circuit Rhythm firmware 2.0.1 (build 5706): the installer checks its SHA-256 and patches it on your computer.
3. Pick the version and send it to the device over USB.

**S versions** (A0.09S): without the functions that create, change or delete files on the card by themselves (project copy, pack delete, sample copy). The safest for your SD.

**Back to the official firmware:** hold **Sample Rec + Samples + Note** while powering on (Novation's bootloader mode) and send the official one with the installer ("Official") or with Novation Components. Always back up your SD card.

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
| **Sample pads held** (arpeggiator on) | ★ arpeggio of the held samples (one also works): each hit changes the sample, with its pad's velocity; recorded with Record and Play *(since Alpha 0.0)* |

Pressing the button without holding selects the track, as in the original. From the Mixer, Clear + track does the original's. The arpeggiator is switched on in [Pattern Settings](#patternsettings) (Shift + pad 25).

<a id="menu"></a>
### 2.2 The track menu

*How to get there:* tap the selected track's button (the menu stays open until you pick something or tap again), or hold any track's button (the menu only while held)

The pads become that track's menu *(Alpha 0.06)*:

| Pad | What it does |
|---|---|
| **1** | the **stock** knob page (the original's) |
| **2** | the **[Stock+](#stockplus)** page (with a sample; with the granular or the synth *(Alpha 0.07)*) |
| **3** | the **[Granular](#granular)** page (with the granular) |
| **4** | the **[Synth](#sinte)** page (with the synth) |
| **5** | the **[Envelope](#envolvente)** page (with the synth or the granular) *(Alpha 0.06)* |
| **8** | ★ the track's voice back to **Project init** (red): K1-K8 and the rest of the voice as the project was last loaded or saved; level, pan, sends and sidechain are left alone *(Alpha 0.09)* |

**The track's sound, the stereo link and the line input** moved to [Sample mode](#samplemode) *(Alpha 0.09)*: its pads 5-8, 14, 15 and 16.

- **Opening it:** a tap on the button of the track already selected leaves it open; it closes when you let go of a menu pad, tap the button again or press any other button. Holding a track's button (¼ s) opens it only while held, like the original's view buttons.
- Row 1, the track's **pages**: only those of its sound (sample: stock and Stock+; granular: stock, Stock+, Granular and Envelope; synth: stock, Stock+, Synth and Envelope; input: stock); the others dark. Bright = the one shown. **Holding** a page pad (½ s or more) shows it only until you let go, then the previous one returns.
- **The track's sound** (sample, granular, synth or input, one per track) is picked in [Sample mode](#samplemode), pads 5-8 *(Alpha 0.09)*. Up to Alpha 0.08 it was on row 2 of this menu (pads 11-14), with the link on 9 and the input's source on 15.
- With the granular or the synth, the stock page leaves the original's knobs (filter, envelope, pitch, level…) acting on them; the **distortion** too, with the same curve as on a sample *(Alpha 0.07)*.

In Alpha 0.04 the menu was: 1-3 pages, 4 granular, 5 / 6 input and gate, 7 link.

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
### 2.5 Synth page

*How to get there:* Sample mode, pad 7 (puts the synth on, with its page), or track menu, pad 4 (its page)

★ A monophonic two-oscillator synth on the master DSP, as any track's sound *(since Alpha 0.05)*. **Up to 4 synth tracks.** It gets its notes like a sample does (pads, Note view, sequence, MIDI).

| Knob | Alone | With Shift |
|---|---|---|
| K1 | OSC 1 waveform: saw (red), pulse (yellow), triangle (green), sine (white) | noise |
| K2 | OSC 2 waveform (the same colours) | sync, on / off (right half = on) |
| K3 | OSC 2 pitch (±24 semitones) | glide (5 ms - 2 s) |
| K4 | OSC 2 fine tune (±50 cents) | octave (−3 … +3) |
| K5 | mix OSC 1 ↔ OSC 2 | velocity → FM |
| K6 | SUB (an octave below) | release (2 ms - 4 s) |
| K7 | FM (OSC 2 modulates OSC 1) | envelope → low-pass (from the centre) |
| K8 | pulse width (50 % → 2 %) | — |

- **The original's knobs** of the track still act on the synth (on the stock page): pitch, envelope (left of centre decay, centre sustain, right slow attack), low-pass, high-pass, resonance, distortion *(Alpha 0.07)*, level, pan, sends, sidechain and mute.
- **The original's start and length** *(Alpha 0.09)* (stock page, K2 / K3): **start = morph**: from K1 / K2's waveform, each oscillator moves smoothly to the next one (saw → pulse → triangle → sine → saw), up to 3 shapes fully up; **length = unison**: below fully up, each oscillator plays twice, detuned by up to a quarter semitone (length at 0). At the defaults (start 0, length fully up) it sounds as before. Morph and unison use more DSP: four synths like that plus the granular at once may not fit.
- **Note-off:** a synth track gets the note-off even in one-shot mode, so the release sounds.
- **LEDs:** mint with the value as brightness (K3, K4, Shift + K4, Shift + K7: the distance from the centre); K1 / K2 in their waveform's colour.
- Clear + knob = default. **Saved with the project.**

<a id="envolvente"></a>
### 2.6 Envelope page

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

<a id="entrada"></a>
### 2.7 Line input and stereo link

*How to get there:* Sample mode, pads 8 / 15 / 16 and 14

The pads are [Sample mode](#samplemode)'s *(Alpha 0.09)*; up to Alpha 0.08 they were on the track menu (input 13, gate 14, source 15, link 9).

**Line input** (pad 8; since Alpha 0.04): the audio input plays as the track's sound, with its level, pan, sends, filter and envelope.
- One input track: L + R. Two: the lower-numbered one is L, the higher R. Setting a third removes the first one set.
- **Pad 16, the gate:** dim = always sounds; bright = only while its notes play, through the track's VCA and filter (low-pass, high-pass, resonance; the filter since Alpha 0.06).
- **Pad 15, the source** (Alpha 0.06): the inputs (dim amber, no FX; up to Alpha 0.07, amber) → the **reverb return** (cream) → the **delay return** (peach), in turn; each input track its own. The return arrives a block late (0.67 ms).
- **An FX into an input** *(Alpha 0.09)*: the return an input track takes no longer goes to the master; it only sounds through the track. That track's send into its own effect is halved (the full knob = half a send), so the feedback stays contained; its send into the other effect is whole. Up to Alpha 0.08 the return also sounded through the master and the send into its own effect fed back.

**Stereo link** (pad 14; since Alpha 0.04): the track (left) and the next one (right) play together with the first one's notes. Pad 14 on either = undo. Dark on track 8 alone. Not linked: Stock+'s free LFO and scan, and the stretch's WSOLA.
- **The second track, as offsets** *(Alpha 0.09)*: its K1-K8 (stock page) are offsets from the first one's: centre = the same, right adds, left subtracts. Its LEDs steel blue, dark at the centre. Clear + knob = the centre.
- **Its sample** = the first one's + the gap between their pads: by default the next one; picking another pad on the second changes the gap, and moving the first one's moves both *(Alpha 0.09)*.
- **Its own steps play too** *(Alpha 0.09)*: the second plays the first one's notes and its own as well.
- Linking puts the second's knobs at the centre (it sounds the same); unlinking leaves them where they sounded. An Alpha 0.04-0.08 project with a link loads as it sounded.

Both are saved with the project.

<a id="note"></a>
### 2.8 Note view

*How to get there:* the Note button

| Gesture | What it does |
|---|---|
| **Keys held** (arpeggiator on) | ★ arpeggio of the held notes on the track's sample; recorded with Record and Play *(since Alpha 0.0)* |
| **Shift held** | ★ the track's **own scale** editor *(since Alpha 0.0)* |

**The editor:** the 32 pads are two piano octaves from the tonic (row 4 = the white keys of the lower octave, pad 25 = the tonic; row 3 = its black keys; rows 2 / 1 = the upper octave). Each key switches its degree on or off (7 at most); the highest is the **period**: the next iteration's tonic (the octave or another, up to 24 semitones). Tonic white, degrees green, period blue.

When you let go of Shift, the keyboard plays the scale: one iteration per row (two if it has 4 notes or fewer); ▲ / ▼ move a row. With no keys, the original piano returns. Saved with the project.

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
| **Pad 26** (blue) | Nudge: the pattern is rewritten so its first step is 1 (it sounds the same) *(since Alpha 0.0)* |
| **Pad 27 / 28** | **fractal** (1 · 1 2 · 1 2 3 …) and **deconstructed** (1 6 11 16 · 2 7 12 13 …) orders; a direction pad goes back to the original *(since Alpha 0.0)* |
| **Pad 25** (grey) | probability view, mode 2: pick a step; **row 3 = dynamics** (velocity and delay within the step; with Record, each step with dynamics is written as it played), **row 4 (25-28) = sample mutation** (sometimes its neighbour plays) *(since Alpha 0.0)* |
| **Pattern Settings twice** | probability view, mode 1: **row 4 = frequency** of the step (it plays one pass in n) *(since Alpha 0.0)* |
| **Clear + pad 25** | clears the pattern's dynamics and mutation (frequency stays) *(since Alpha 0.04)* |
| **Shift + pad 25** | ★ the track's arpeggiator on / off (green bright / dim) *(since Alpha 0.0)* |
| **Shift + pads 27-32** | arpeggio order: fractal, deconstructed, up, down, ping-pong, random |
| **Shift + pads 17-24** | arpeggio resolution (1/4 … 1/32T); the same one again = the track's sync rate |

The arpeggiator's rows with Shift: the chosen option bright green, the others dim green (since Alpha 0.05). Per-step values travel with the hit when quantizing, nudging, copying a step and with the original's Mutate.

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

## 4. Samples

<a id="samplemode"></a>
### 4.1 Sample mode

*How to get there:* the Samples button twice

| Gesture | What it does |
|---|---|
| **Pads 1 / 2** (the original's) | fit the sample to the pattern by changing pitch; since Alpha 0.04 they switch the stretch off first |
| **Pads 9 / 10** | ★ the same with the **stretch** (Stock+ K7), without changing pitch: the next / previous length *(since Alpha 0.04)* |
| **Pad 19** | ★ the selected track's loop de-clicker (256-sample crossfade), on / off (blue bright / dim); on by default, saved with the project *(since Alpha 0.04)* |
| **Pads 5-8** | ★ the **track's sound**, one lit, the others dim: **5** sample (white), **6** [granular](#granular) (lilac), **7** [synth](#sinte) (mint), **8** [line input](#entrada) (amber). Pad 5 removes the granular, the synth or the input; 6 / 7 leave the track's knobs on their page; the pad of the sound already playing does nothing *(Alpha 0.09)* |
| **Pad 14** | ★ [stereo link](#entrada) with the next track (steel blue) *(Alpha 0.09)* |
| **Pad 15** | ★ the [input](#entrada)'s source: the inputs (dim amber), the reverb return (cream), the delay return (peach); only on an input track *(Alpha 0.09)* |
| **Pad 16** | ★ the [input](#entrada)'s gate (amber bright / dim); only on an input track *(Alpha 0.09)* |

Shift + these pads, as in the original. Pad 19 sits above pad 27 (loop). Very short loops play at their own length (the original repeated them every ~128 samples).

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

Everything is saved in the device's settings, except GM mode, which goes with the project. If the two Program Change channels differ, the received one is forwarded on the send channel.

## A. Appendix

<a id="guardado"></a>
### A.1 What is saved and where

| Where | What |
|---|---|
| **With the project** | Stock+, Granular, Synth (settings and tracks), Envelope, the input's source, line input, stereo link (with the second track's offsets), per-track de-clicker, own scale, chain rules, per-step dynamics / mutation / frequency, Velocity marks, Micro Step, GM mode, reverb / delay / sidechain |
| **Device settings** | Program Change channels, Thru mode, keyboard into the arpeggiator, USB merge, master filter resonance, compressor |
| **Until power-off** | each track's knob page, Project init (what was loaded or saved), cue mode, metronome / count-in, Sample Rec pads 23 / 24 |

The mod's own data goes in a part of the project file the original doesn't use. A project from an earlier version loads without what that version lacked. **Keep copies of your projects.**

<a id="midi"></a>
### A.2 MIDI

The new knobs move the original's parameters with their usual MIDI (Circuit Rhythm programmer's guide): sidechain NRPN 1:1-1:4 (the track's channel); reverb NRPN 1:18-1:20; delay NRPN 1:6-1:11; master resonance CC 71; compressor NRPN 1:22-1:26. The Stock+, Granular and Synth pages have no MIDI yet.

<a id="glosario"></a>
## Glossary of functions

| Function | What it is / gesture | Chapter | Since |
|---|---|---|---|
| **Automation view** | steps with knob automation in yellow, and listening to them; Velocity + Shift, or Velocity again (latched) | [3.1 Velocity and Micro Step](#velocity) | Alpha 0.09 |
| **Bitcrush** | Stock+, Shift + K7 | [2.3 Stock+ page](#stockplus) | Alpha 0.02 |
| **Clear a step's automation** | Clear + step in Velocity | [3.1 Velocity and Micro Step](#velocity) | Alpha 0.09 |
| **Compressor threshold** | Sidechain view K5 | [5.2 FX and Sidechain](#fx) | Alpha 0.01 |
| **Copy projects** | Duplicate + A, Duplicate + B in Projects, also to another pack | [6.1 Projects and Packs](#projects) | Alpha 0.0 |
| **Copy samples** | Duplicate + A, Duplicate + B in Sample Rec | [4.2 Sample Rec](#samplerec) | Alpha 0.01 |
| **Copy track parameters** | Duplicate + track A, track B | [2.1 The track button](#pista) | Alpha 0.0 |
| **Count-in** | a bar before recording; Shift + Clear; since 0.08 on the music's clock, also as a slave | [1.1 Transport, metronome and quantize](#transporte) | Alpha 0.0 |
| **Cue mode** | mix on the left, cue on the right; Mixer, pan, Shift + knob | [5.1 Mixer](#mixer) | Alpha 0.04 |
| **Delete a pack** | Clear + pack twice in Packs | [6.1 Projects and Packs](#projects) | Alpha 0.01 |
| **Distortion on granular and synth** | the original's distortion knob on them too | [2.2 The track menu](#menu) | Alpha 0.07 |
| **Envelope by play mode** | start, length, slope and → filter of the synth and the granular; menu, pad 5 | [2.6 Envelope page](#envolvente) | Alpha 0.06 |
| **External keyboard into the arpeggiator** | Advanced Setup, pad 22 | [6.2 Setup and Advanced Setup](#setup) | Alpha 0.04 |
| **Filter type (24 dB, comb)** | Stock+, Shift + K6 | [2.3 Stock+ page](#stockplus) | Alpha 0.02 |
| **Fixed length** | hand-entered hits with a set length; Micro Step, pad 31 | [3.1 Velocity and Micro Step](#velocity) | Alpha 0.04 |
| **Fixed Recording with external clock** | the length at the incoming MIDI clock's tempo | [4.2 Sample Rec](#samplerec) | Alpha 0.02 |
| **Fractal / deconstructed orders** | Pattern Settings pads 27 / 28 | [3.2 Pattern Settings and probability](#patternsettings) | Alpha 0.0 |
| **FX into an input** | a return taken by an input track leaves the master; its feedback, halved | [2.7 Line input and stereo link](#entrada) | Alpha 0.09 |
| **FX returns as a source** | the reverb or the delay as an input track's sound; Sample mode, pad 15 | [2.7 Line input and stereo link](#entrada) | Alpha 0.06 |
| **FX sends on the knobs** | ▼ / ▲ in the FX view | [5.2 FX and Sidechain](#fx) | Alpha 0.0 |
| **Gate by press** | the hit lasts as long as the pad is held; Micro Step, pad 32 | [3.1 Velocity and Micro Step](#velocity) | Alpha 0.04 |
| **General MIDI** | the tracks on channel 10 with their GM note; Setup, pad 22 | [6.2 Setup and Advanced Setup](#setup) | Alpha 0.04 |
| **Granular** | the granular engine on up to 4 tracks; Sample mode pad 6, menu pad 3 | [2.4 Granular page](#granular) | Alpha 0.04 |
| **Level to 100 / 0** | Shift + knob on the Mixer's levels | [5.1 Mixer](#mixer) | Alpha 0.0 |
| **Line input** | the audio input as a track's sound; Sample mode, pads 8 / 16 | [2.7 Line input and stereo link](#entrada) | Alpha 0.04 |
| **Loop de-clicker** | a crossfade at the loop point; Sample mode pad 19, Sample Rec pad 23 | [4.1 Sample mode](#samplemode) | Alpha 0.04 |
| **Master compressor** | threshold, soft clip, attack and release in the Sidechain view | [5.2 FX and Sidechain](#fx) | Alpha 0.0 |
| **Master resonance** | Shift + ▲ / ▼ in the FX view | [5.2 FX and Sidechain](#fx) | Alpha 0.0 |
| **Metronome** | four states with Shift + Clear | [1.1 Transport, metronome and quantize](#transporte) | Alpha 0.0 |
| **Mute at the bar** | Shift + track pad in the Mixer | [5.1 Mixer](#mixer) | Alpha 0.0 |
| **Note arpeggiator** | arpeggiates the keys held in the Note view | [2.8 Note view](#note) | Alpha 0.0 |
| **Nudge** | the first step becomes step 1; Pattern Settings pad 26 | [3.2 Pattern Settings and probability](#patternsettings) | Alpha 0.0 |
| **Own scale** | a scale per track; Shift in the Note view | [2.8 Note view](#note) | Alpha 0.0 |
| **Per-step dynamics** | random velocity and delay within the step; probability row 3 | [3.2 Pattern Settings and probability](#patternsettings) | Alpha 0.0 |
| **Per-step frequency** | the step plays one pass in n | [3.2 Pattern Settings and probability](#patternsettings) | Alpha 0.0 |
| **Pitch envelope** | Stock+, K1 / K2 | [2.3 Stock+ page](#stockplus) | Alpha 0.01 |
| **Pitch LFO** | Stock+, K3 / K4; free or synced | [2.3 Stock+ page](#stockplus) | Alpha 0.01 |
| **Program Change** | listen and send channels; Setup, pads 29 / 30 | [6.2 Setup and Advanced Setup](#setup) | Alpha 0.0 |
| **Project init** | the track's voice as loaded or saved; menu, pad 8 (red) | [2.2 The track menu](#menu) | Alpha 0.09 |
| **Quantize** | Shift + Play while playing | [1.1 Transport, metronome and quantize](#transporte) | Alpha 0.0 |
| **Repeat the scene** | the current scene 1-8 times; Mixer, Shift + pads 9-16 | [5.1 Mixer](#mixer) | Alpha 0.0 |
| **Ring mod** | Stock+, K5 (Shift: the frequency) | [2.3 Stock+ page](#stockplus) | Alpha 0.02 |
| **Rule chains** | patterns chained "n times A, then B" | [3.3 Patterns: chains](#patterns) | Alpha 0.0 |
| **Sample arpeggiator** | arpeggiates the held sample pads; Shift + Pattern Settings pad 25 switches it on | [2.1 The track button](#pista) | Alpha 0.0 |
| **Sample mutation** | sometimes the neighbour plays; probability row 4 | [3.2 Pattern Settings and probability](#patternsettings) | Alpha 0.0 |
| **Scan** | moves each note's or the loop's start; Stock+, K8 | [2.3 Stock+ page](#stockplus) | Alpha 0.02 |
| **Sidechain on the knobs** | Sidechain view K1-K4 | [5.2 FX and Sidechain](#fx) | Alpha 0.0 |
| **Snapshot** | the moved knobs into a step; Record held + step | [3.1 Velocity and Micro Step](#velocity) | Alpha 0.09 |
| **Start and length on the granular** | the original's start adds to the position, the length narrows the zone | [2.4 Granular page](#granular) | Alpha 0.09 |
| **Stereo link** | a track and the next as one stereo sound; Sample mode, pad 14; since 0.09 the second as offsets | [2.7 Line input and stereo link](#entrada) | Alpha 0.04 |
| **Stereo recording** | L and R into two slots; Sample Rec, pad 24 | [4.2 Sample Rec](#samplerec) | Alpha 0.04 |
| **Stock+ page** | eight more knobs per track; menu, pad 2; since 0.07 on the granular and the synth too | [2.3 Stock+ page](#stockplus) | Alpha 0.01 |
| **Stretch** | slower or faster without changing pitch; Stock+ K7, Sample mode pads 9 / 10 | [2.3 Stock+ page](#stockplus) | Alpha 0.02 |
| **Synth** | two oscillators with FM on up to 4 tracks; Sample mode pad 7, menu pad 4 | [2.5 Synth page](#sinte) | Alpha 0.05 |
| **Synth morph and unison** | the original's start and length on the synth | [2.5 Synth page](#sinte) | Alpha 0.09 |
| **Thru: Out 2 / Merge / Filter** | Duplicate in Advanced Setup | [6.2 Setup and Advanced Setup](#setup) | Alpha 0.0 |
| **Track knobs reset** | Clear + the track's button | [2.1 The track button](#pista) | Alpha 0.0 |
| **Track menu** | tap the selected track's button (stays open) or hold a track's button | [2.2 The track menu](#menu) | Alpha 0.04 |
| **USB merge** | DIN In also over USB; Advanced Setup, pad 23 | [6.2 Setup and Advanced Setup](#setup) | Alpha 0.04 |
| **Velocity marks** | on a marked step the parameters go back to Project init (up to 0.08, to the knob); Shift + step | [3.1 Velocity and Micro Step](#velocity) | Alpha 0.04 |
| **Visual metronome** | Clear flashes orange on each click with the click's level at 0 (Tempo / Swing K5) | [1.1 Transport, metronome and quantize](#transporte) | Alpha 0.08 |
| **Waveshaper** | soft, hard, fold or bitcrush on the granular and the synth; Stock+, K7 (Shift: the type) | [2.3 Stock+ page](#stockplus) | Alpha 0.07 |
