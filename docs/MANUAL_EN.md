# Circuit Remix Alpha 0.0 — manual

[Español](MANUAL.md)

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

Stopped, Shift + Play without count-in is the original's (play from where it stopped). The count-in is not saved: at power-on it is back to "no count-in".

## 2. Mixer
| Gesture | What it does |
|---|---|
| **Shift + track pad** (row 1) | that track's mute on the next bar (the pad blinks; again = cancel; stopped, at once) |
| **Shift + knob** (levels page) | right = level 100; left = 0. While recording, it is recorded as automation |
| **Shift + pads 9-16** | the current scene repeats 1-8 times (with Shift row 2 yellow, the chosen one green; scenes with chain rules peach) |

Pad 9 without Shift is still the original's Mute Recall.

## 3. Track view (samples)
| Gesture | What it does |
|---|---|
| **Clear + the track's button** (in its view) | ★ its knobs to their defaults and its automation cleared; the other parameters (level, pan, sends, sidechain) and the selected sample back to how they were when the project was loaded |
| **Duplicate + track A, then track B** | ★ B gets A's parameters (knobs, level, pan, sends, sidechain) and its selected sample; with Duplicate held, more tracks get the copy |
| **Held sample pads** (arpeggiator on) | ★ arpeggio of the held samples (a single one too): each hit changes the sample like a sample flip, with its pad's velocity. Playing, on the grid; stopped, at the tempo. With Record and Play, it is recorded into the pattern |

With a step held, a sample pad is the original's sample flip. From the Mixer, Clear + track does what the original does.

## 4. Note view
| Gesture | What it does |
|---|---|
| **Held keys** (arpeggiator on) | ★ arpeggio of the held notes on the track's sample; recorded with Record and Play |
| **Shift held** | ★ editor of the **track's custom scale**: the 32 pads are two piano octaves from the root (row 4 = the lower octave's white keys, pad 25 = the root; row 3 = its black keys; rows 2 / 1 = the upper octave). Each key turns its degree on or off (7 at most); the highest is the **period**: the root of the next iteration (the octave or any other, up to 24 semitones). LEDs: root white, degrees green, period blue |

When Shift is released, the keyboard plays the scale: **one iteration per row** (two with 4 notes or fewer); ▲ / ▼ move one row. One scale per track; with no keys, the original piano is back. Saved with the project.

## 5. Pattern Settings
| Gesture | What it does |
|---|---|
| **Pad 26** (orange) | Nudge: the pattern is rewritten so that its first step is step 1 (steps and automation rotate; it sounds the same) |
| **Pad 27 / 28** | **fractal** (1 · 1 2 · 1 2 3 …) and **deconstructed** (1 6 11 16 · 2 7 12 13 · …) play orders; a direction pad goes back to the original |
| **Pad 25** (peach) | probability view, mode 2: pick a step; **row 3 = dynamics** (velocity and delay within the step), **row 4, pads 25-28 = sample mutation** (sometimes its row neighbour or the sample of the other row of its page plays) |
| **Pattern Settings twice** | probability view, mode 1: **row 4 = the step's frequency** (it plays one pass in n) |
| **Shift + pad 25** | the track and pattern's arpeggiator on / off (green / grey with Shift) |
| **Shift + pads 27-32** | arpeggio order: fractal, deconstructed, up, down, ping-pong, random |
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
| K6 | master compressor soft clip (right = on) |
| K7 / K8 | master compressor attack / release |

A preset pad brings the track back to that preset. **Clear + K1-K4** = its preset's values; **Clear + K6-K8** = the factory compressor. The brightness shows the value. Saved with the project. The compressor is only heard when it is on (Advanced Setup).

## 9. Projects view: copy projects (Alpha 0.0 only)
With the transport stopped:
1. **Duplicate + a pad with a project (A)**: it blinks yellow.
2. **Duplicate + an empty pad (B)**: copies A into B (green for ~1.5 s, then A's colour). B can be in this pack or another: pick A, load another pack and Duplicate + an empty pad.
3. **Duplicate + a pad with a project**: it blinks white (asking); **Duplicate + the same pad** within ~5 s overwrites it.

It never overwrites the loaded project nor writes to the internal memory pack (red + Save LED red). Alpha 0.0S does not have this feature.

## 10. Setup (Shift + Save)
| Gesture | What it does |
|---|---|
| **Advanced Setup, Duplicate** | the Thru jack cycles **Thru** (green) → **Out 2** (dim red) → **Merge** (yellow: MIDI In + the device's MIDI) → **Filter** (blue: MIDI In minus the channels the device listens on) |
| **Pad 29** (the first time) | pads 1-16 show the **Program Change listen channel** (16 by default); a pad changes it; pad 29 again = PGM Rx on / off |
| **Pad 30** (the first time) | the same with the Program Change **output channel** |

If the two channels differ, a received Program Change is forwarded on the output channel (with PGM Tx on). Everything is saved in the device settings.

## 11. Safety and recovery
- The mod never writes to the **internal memory pack**: its writes refuse it with the Save LED red for 1.5 s. Saving from the original firmware is unchanged.
- The mod's own data that travels with the project is saved in the project file, in an area the original does not use. How the original firmware loads a project saved with Circuit Remix has not been checked yet: keep copies of your projects.
- **Recovery:** hold **Sample Rec + Samples + Note** at power-on (Novation's bootloader mode) and send the official firmware with the installer ("Official") or with Novation Components.
