# Circuit Remix Alpha 0.04 — manual

[Español](MANUAL.md)

> ⚠️ **Alpha 0.04 is experimental and needs refinement:** what is marked "(Alpha 0.04)" has mostly been checked in emulation only. For serious playing, Alpha 0.03.

The Circuit Remix features on the Circuit Rhythm (firmware 2.0.1, build 5706), view by view. Everything else works as in Novation's original firmware; the new gestures are combinations that did nothing in the original or repeated the gesture without the modifier.

**Conventions.** Pads 1-32 left to right, top to bottom: row 1 = pads 1-8, row 2 = 9-16, row 3 = 17-24, row 4 = 25-32. Knobs K1-K8. ▲ / ▼ = the arrow buttons.

**Exclusive** to Circuit Remix (not in CIRCUIT-HACKS): marked ★.

## 1. Transport, metronome and quantize
| Gesture | What it does |
|---|---|
| **Shift + Clear** | cycles four states; with Shift held, the Clear LED: red = no metronome, green = metronome, magenta = count-in only, cyan = both |
| **Record armed + Play** (stopped, count-in on) | one bar of clicks at the project tempo (Record blinks), then starts recording; Play during the count cancels it |
| **Shift + Play** (stopped, count-in on) | the count, then playback continues from where it stopped (the original Shift + Play) |
| **Shift + Play** (playing) | quantizes the selected track's pattern to its steps: hits on micro steps 2-3 move to the start of their step, those on 4-6 to the next step; rolls stay. Play LED with Shift: yellow; green after quantizing; red = nothing was touched |

Since Alpha 0.04 playback starts sooner (≈ 10 ms from Play to the first sound; the original ≈ 18 ms), the notes of one step sound together and the clock does not stumble while a sample is saved.

Stopped, Shift + Play without count-in is the original's (play from where it stopped). The count-in is not saved: at power-on it is back to "no count-in".

## 2. Mixer
| Gesture | What it does |
|---|---|
| **Shift + track pad** (row 1) | that track's mute on the next bar (the pad blinks; again = cancel; stopped, at once) |
| **Shift + knob** (levels page) | right = level 100; left = 0. While recording, it is recorded as automation |
| **Shift + pads 9-16** | the current scene repeats 1-8 times (with Shift row 2 yellow, the chosen one green; scenes with chain rules peach). While playing, with Shift, the repeat that is playing shows white; on the last one the green pad blinks |
| **Pan page** (button 19), **Shift + knob** right / left (Alpha 0.04) | ★ **cue mode** on / off (button 19 pink): the mix goes to the left output and the cue to the right (for listening with a Y cable) |
| **Pan page in cue mode, knob** (Alpha 0.04) | its track's cue send (knobs pink, brightness = send); a muted track with a send plays only in the cue; Clear + knob = 0 |

Pad 9 without Shift is still the original's Mute Recall. The cue mode is not saved.

## 3. Track view (samples)
| Gesture | What it does |
|---|---|
| **Clear + the track's button** (in its view) | ★ its knobs to their defaults and its automation cleared; the other parameters (level, pan, sends, sidechain) and the selected sample back to how they were when the project was loaded |
| **Duplicate + track A, then track B** | ★ B gets A's parameters (knobs, level, pan, sends, sidechain) and its selected sample; with Duplicate held, more tracks get the copy |
| **Held sample pads** (arpeggiator on) | ★ arpeggio of the held samples (a single one too): each hit changes the sample like a sample flip, with its pad's velocity. Playing, on the grid; stopped, at the tempo. With Record and Play, it is recorded into the pattern |

With a step held, a sample pad is the original's sample flip. From the Mixer, Clear + track does what the original does.

### Track menu (Alpha 0.04)
**Hold a track's button** (in the track views) for a moment: pads 1-7 become a menu for that track; releasing the button closes it.

| Pad | What it does |
|---|---|
| 1 / 2 / 3 | **stock** / **Stock+** / **Granular** knob page. Pad 3 also puts the granular on the track (up to 4 tracks; with 4 already set, nothing) |
| 4 | the track's granular on / off (the other granular tracks keep playing) |
| 5 | ★ the **line input** as the track's sound (up to two tracks: one alone = L + R; two = the lower-numbered L, the higher R; a third one replaces the first set). It takes the granular off |
| 6 | the line track's gate: dim = always on, lit = only with its notes (dark if the track is not a line track) |
| 7 | ★ **stereo link**: the track (left, its sample) and the next one (right, the next sample) play together with the first one's parameters; pad 7 on either = undo (on track 8, nothing) |

Choosing the stock or Stock+ page leaves the granular playing. Pressing the track's button without holding it selects it, as in the original.

### The Stock+ knob page (since Alpha 0.01; K5-K8 since Alpha 0.02)
**Track menu, pad 2** (up to Alpha 0.03: press the selected track's button again): its 8 knobs go to the Stock+ page; pad 1 goes back to the stock page. While a track is on the Stock+ page, its button blinks white. The page is per track and stays until power-off.

| Knob | On the Stock+ page | With Shift |
|---|---|---|
| K1 | ★ pitch envelope amount: centre = none; to the right each hit starts higher, to the left lower (up to ±24 semitones), then returns to its note | fine control |
| K2 | ★ how long it takes to return to the note (5 ms to 4 s) | fine control |
| K3 | ★ pitch LFO rate from the centre (Alpha 0.04): centre = off, right = free (0.05 to 30 Hz), left = synced to the tempo (16 divisions, 1/16T to 8 bars; the cycle starts on the first beat) | fine control |
| K4 | ★ pitch LFO depth (0 to 24 semitones) | fine control |
| K5 | ★ ring mod amount | ★ its frequency (20 Hz-5 kHz) |
| K6 | ★ pitch follow: the stock low-pass cutoff follows the note | ★ filter type, on the stock filter knobs: **stock** (unchanged), **24 dB** (the stock low-pass and high-pass, steeper) or **comb** (the cutoff sets its pitch, the resonance its feedback) |
| K7 | ★ **stretch**: the track plays slower (left, down to 0.25×) or faster (right, up to 4×) without changing pitch; centre = as stock | ★ bitcrush |
| K8 | ★ scan speed, an LFO that moves each note's start point; since Alpha 0.04 from the centre: centre = still, right = free (0.05 to 20 Hz), left = synced to the tempo (16 divisions). On a loop it moves the loop's start on every pass | ★ its depth |

- **Shift:** on K1-K4 it is fine control, as on the stock knobs; on K5-K8 it is the second function, and while you hold it their LEDs show that second layer.
- **Clear + knob:** its default. On K5-K8 both layers go back (with and without Shift).
- **LEDs:** the knobs are white, their brightness following their value (K1 and K7: the distance from the centre). K6 takes its filter type's colour: stock white, 24 dB the FX view's delay colour, comb its reverb colour.
- **Project:** saved with it; a project without these values plays without modulation (Alpha 0.01 projects load as they were). Clear + the track's button resets them and Duplicate + track A, track B copies them.
- **The stretch** splits the sample into overlapping grains of about 43 ms that are kept in phase (WSOLA). 0.5× sounds very good; at 0.25× drums may click, because each hit repeats. Tested with everything on all 8 tracks at once, plus reverb and delay.
- Each voice's pitch is recalculated about 190 times a second and at the start of every hit: a very short return (K2 fully left) or a very fast LFO may sound stepped.
- In projects from Alpha 0.02 / 0.03, a moved K3 or K8 may sound different (they now work from the centre).

### The Granular page (Alpha 0.04)
The CIRCUIT-HACKS granular engine on the track's sample (menu, pad 3). It follows the note (Note view, keyboard and MIDI); the track's filter knobs (high-pass, low-pass, resonance) and its envelope act on it. Up to **4 granular tracks at once**, each with its own settings; the grains are shared (16 with one track, 7 each with two, 4 with three, 2 with four).

| Knob | Alone | With Shift |
|---|---|---|
| K1 | grain size (5-500 ms) | fine |
| K2 | density (1-16 grains) | ★ stereo spread (0 = mono) |
| K3 | position in the sample | fine |
| K4 | scan: the playhead moves forward or back (centre = still) | fine |
| K5 | pitch (centre = the note; ±24 semitones) | fine pitch |
| K6 | position spray | zone (which part of the sample) |
| K7 | pitch spray | reverse chance |
| K8 | window (rectangle → triangle → percussive) | gate: fully left = always on (drone); otherwise the track's notes open it |

Clear + knob = its default. Saved with the project (Alpha 0.03 projects have no granular).


## 4. Note view
| Gesture | What it does |
|---|---|
| **Held keys** (arpeggiator on) | ★ arpeggio of the held notes on the track's sample; recorded with Record and Play |
| **Shift held** | ★ editor of the **track's custom scale**: the 32 pads are two piano octaves from the root (row 4 = the lower octave's white keys, pad 25 = the root; row 3 = its black keys; rows 2 / 1 = the upper octave). Each key turns its degree on or off (7 at most); the highest is the **period**: the root of the next iteration (the octave or any other, up to 24 semitones). LEDs: root white, degrees green, period blue |

When Shift is released, the keyboard plays the scale: **one iteration per row** (two with 4 notes or fewer); ▲ / ▼ move one row. One scale per track; with no keys, the original piano is back. Saved with the project.

## 5. Pattern Settings
| Gesture | What it does |
|---|---|
| **Pad 26** (blue) | Nudge: the pattern is rewritten so that its first step is step 1 (steps and automation rotate; it sounds the same) |
| **Pad 27 / 28** | **fractal** (1 · 1 2 · 1 2 3 …) and **deconstructed** (1 6 11 16 · 2 7 12 13 · …) play orders; a direction pad goes back to the original |
| **Pad 25** (grey) | probability view, mode 2: pick a step; **row 3 = dynamics** (velocity and delay within the step; **with Record, each step with dynamics that plays is written** with the velocity and micro step it played with, and loses its dynamics), **row 4, pads 25-28 = sample mutation** (sometimes its row neighbour or the sample of the other row of its page plays) |
| **Pattern Settings twice** | probability view, mode 1: **row 4 = the step's frequency** (it plays one pass in n) |
| **Shift + pad 25** | the track and pattern's arpeggiator on / off (green / grey with Shift) |
| **Shift + pads 27-32** | arpeggio order: fractal, deconstructed, up, down, ping-pong, random |
| **Clear + pad 25** (Alpha 0.04) | clears the pattern's dynamics and mutation (the frequency stays) |
| **Shift + pads 17-24** | arpeggio rate (1/4 … 1/32T); the same one again = the track's sync rate |

The per-step values travel with the hit when quantizing, with Nudge, when copying a step (Duplicate + step A + step B) and with the original's Mutate (Shift + Duplicate).

## 6. Patterns view: chains
| Gesture | What it does |
|---|---|
| **Shift + upper page button** | chain mode (green) |
| In the mode: **a pattern** (A), **again** (n + 1 passes), **another** (B), **one more** (C) | rule "n times A, then B; the next time, C" (AAB AAC …) |
| **Clear + pattern** | no rule |
| **Shift + lower page button** | out of the mode: the original chain |

Each scene remembers the mode it was saved with. The rules are saved with the project.

## 7. FX view
| Gesture | What it does |
|---|---|
| **▼ / ▲** | the knobs switch to the **reverb** / **delay** sends of the 8 tracks without changing the preset (▼ cream, ▲ peach; the page shown bright) |
| **Shift + knob**, delay page | K1 time, K2 sync, K3 feedback, K4 width, K5 ratio, K6 slew |
| **Shift + knob**, reverb page | K1 type (6), K2 decay, K3 damping |
| **Shift + ▲ / ▼** | master filter resonance ±16 (yellow with Shift) |
| **Duplicate** (light blue) | reset: reverb and delay sends to 0, master filter centred |
| **Clear + knob** | that track's send on the page shown to 0 |

With Shift, each knob's brightness shows its parameter's value. The reverb and delay parameters are saved with the project; the resonance is global (the device's).

## 8. Sidechain view (Shift + FX)
| Knob | What it moves |
|---|---|
| K1-K4 | attack, hold, decay and depth of the selected track's sidechain (the one of the last preset pad touched) |
| K5 | master compressor threshold (fully right = the stock's; further left it compresses from lower levels) |
| K6 | master compressor soft clip (right = on) |
| K7 / K8 | master compressor attack / release |

A preset pad brings the track back to that preset. **Clear + K1-K4** = its preset's values; **Clear + K6-K8** = the factory compressor; **Clear + K5** = the stock's threshold. Each Clear + knob affects only that knob. The brightness shows the value. Saved with the project. The compressor is only heard when it is on (Advanced Setup).

## 9. Projects view: copy projects (not in Alpha 0.01S)
With the transport stopped:
1. **Duplicate + a pad with a project (A)**: it blinks yellow.
2. **Duplicate + an empty pad (B)**: copies A into B (green for ~1.5 s, then A's colour). B can be in this pack or another: pick A, load another pack and Duplicate + an empty pad.
3. **Duplicate + a pad with a project**: it blinks white (asking); **Duplicate + the same pad** within ~5 s overwrites it.

It never overwrites the loaded project nor writes to the internal memory pack (red + Save LED red). Alpha 0.01S does not have this feature.

**How it differs from Save + pad** (the stock save, which saves to any pad):
| | Duplicate + A, Duplicate + B | Save + pad |
|---|---|---|
| What it copies | project A **as saved** on the card | the **loaded** project **as it is in memory** (unsaved changes included) |
| A must be loaded | no: what you have loaded (and its unsaved changes) stays | yes: it only saves the loaded project |
| From another pack | yes: pick A, load another pack and copy it there | — (it saves what is loaded) |
| If B holds a project | asks first (blinks white) and never touches the loaded project | as the stock |
| Transport | stopped only | as the stock |

### Packs (Projects twice): delete a pack (not in Alpha 0.01S)
With the transport stopped: **Clear + a pack's pad** = asks (blinks red for ~5 s); **Clear + the same pad** within ~5 s = deletes the pack from the card (green for ~1.5 s). Never the loaded pack, the internal memory pack or an empty slot.

### Sample Rec: copy a sample (not in Alpha 0.01S)
With the transport stopped:
1. **Duplicate + a slot with a sample (A)**: it blinks yellow (Duplicate + A again = forget it).
2. **Duplicate + slot B** (in this pack or, after loading another pack, in that one): copies A's sample into B, and B plays at once (green for ~1.5 s). If B holds a sample it blinks white, and **Duplicate + B** again within ~5 s overwrites it.

Red = it could not be done (sample memory full, the device busy, or the internal pack).

## 10. Setup (Shift + Save)
| Gesture | What it does |
|---|---|
| **Advanced Setup, Duplicate** | the Thru jack cycles **Thru** (green) → **Out 2** (dim red) → **Merge** (yellow: MIDI In + the device's MIDI) → **Filter** (blue: MIDI In minus the channels the device listens on) |
| **Pad 29** (the first time) | pads 1-16 show the **Program Change listen channel** (16 by default); a pad changes it; pad 29 again = PGM Rx on / off |
| **Pad 30** (the first time) | the same with the Program Change **output channel** |
| **Pad 22** (Alpha 0.04) | the project's **General MIDI mode** (green = on): the tracks go out on channel 10 with their GM note; GM notes coming in on channel 10 play their track |
| **K1-K8, in GM mode** (Alpha 0.04) | each track's GM note (35-81, two clicks a note; each new note plays once on channel 10). Factory: 36, 38, 42, 46, 39, 37, 45, 49 |
| **Advanced Setup, pad 22** (Alpha 0.04) | external keyboard into the arpeggiator: notes coming in on the channel of a track with its arpeggiator on are arpeggiated (green = on) |
| **Advanced Setup, pad 23** (Alpha 0.04) | USB merge: what comes into DIN In also goes out over USB (without the clock if Clock Tx is on) |

If the two channels differ, a received Program Change is forwarded on the output channel (with PGM Tx on). Everything is saved in the device settings (since Alpha 0.04 also the Program Change channels and the Thru mode, which the original did not save unless another setting changed).

## 11. Sample mode and Sample Rec (Alpha 0.04)
| View | Gesture | What it does |
|---|---|---|
| Sample mode (Samples) | **pads 1 / 2** (original) | fit the sample to the pattern by changing its pitch; they now switch the track's stretch off first |
| Sample mode | **pads 9 / 10** | ★ the same with **stretch** (Stock+ K7), without changing pitch: the next longer / shorter length |
| Sample mode | **pad 19** | ★ the selected track's loop de-clicker (a 256-sample crossfade) on / off; on by default, saved with the project |
| Sample Rec | **pad 23** | ★ the loop de-clicker of all tracks (on at power-on) |
| Sample Rec | **pad 24** | ★ **stereo recording**: L into the chosen slot, R into the next one (which must be empty; otherwise only the first, in mono). Off at power-on |

Very short loops now play at their own length (the original repeated them every ~128 samples and read past their end).

## 12. Velocity and Micro Step (Alpha 0.04)
| View | Gesture | What it does |
|---|---|---|
| Velocity (button 10) | **Shift + step** | marks the step: when it plays, no automation lane plays there and automated parameters go back to their knob's position (with Shift, steps yellow, marked ones red) |
| Micro Step (Shift + Gate) | **pad 31** | fixed length: off → the selector on pads 17-32 (1-16 steps; picking one switches it on); on → off (orange = on) |
| Micro Step | **pad 32** | gate by press: the hit lasts as long as you hold the step's pad; holding an empty step for 300 ms or more also creates the hit (green = on) |

With fixed length or gate by press on, a hit entered by hand on the steps takes that length.

## 13. Safety and recovery
- The mod never writes to the **internal memory pack**: its writes refuse it with the Save LED red for 1.5 s. Saving from the original firmware is unchanged.
- The mod's own data that travels with the project is saved in the project file, in an area the original does not use. How the original firmware loads a project saved with Circuit Remix has not been checked yet: keep copies of your projects.
- **Recovery:** hold **Sample Rec + Samples + Note** at power-on (Novation's bootloader mode) and send the official firmware with the installer ("Official") or with Novation Components.
