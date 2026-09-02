# The commanded-transient carriers, and how to rebuild them

> 🔴 **NEITHER FILM ON THIS SITE USES THESE CARRIERS.**
> The current entry, **[THE LAST HEAT](../)**, binds *voice* references (through `H3ZeroAudioPrefix`)
> in 10 of its 18 graphs and binds **no carrier wav and no placed transient in any of them**. Every
> impact, the furnace and the ring are H3's own timing. The earlier film,
> **[THE STORM](../storm.html)**, binds no reference at all: `ref_image` and `ref_audio` are
> unconnected in its graph.
> These wavs belong to a **separate, earlier experiment** (working title *THE FUSE*). Keeping this
> page honest matters more than keeping it tidy, so the three are labelled rather than merged.

**What these files are for.** A sound event written into a **reference wav** before any picture
exists comes back in the render at the time you wrote it: H3 reproduces a transient in the bound
reference at its authored position, so the rhythm can be authored first and the model performs it.
That is the technique these wavs demonstrate, and it is measured. ⚠️ **It holds only within the first
~3.02 s of a 124-frame render** (beats at or after ~3.35 s do not reproduce). ⛔ The picture does
**not** follow the score: a pre-registered test of that failed.

## What is here
| file | what |
|---|---|
| `build_score.py` | writes one carrier wav per shot, plus a **seed-matched null** for each |
| `plan_score.py` | turns a global beat grid (timeline seconds) into per-shot carrier times |
| `tick_idx.npy` / `tick_vals.npy` | the **measured** 672-sample transient, harvested by diffing a recording against its own null |
| `score.json` | the film's per-shot beat times |
| `*.wav` | the carriers actually bound at render time, and their nulls |

## The bed
`c9_tone_clean.wav`: room tone at -46 dBFS from t=0. ⛔ **Never digital silence:** a carrier that
contains a silent run makes a defect the model will happily reproduce.

## The two rules that cost me shots
1. **Never name the impacts in `overall_soundscape`.** Naming them makes H3 generate them itself,
   loudly, at times you did not choose. Use a restrained line.
2. **And name no SPACE in it either.** My "restrained" line said *"the quiet still air of a dark
   studio"* while the picture line asked for a *white* studio field. The model followed the
   soundscape and blacked out the set.

## Reproducing the carriers inside ComfyUI
`H3PlaceTransient` (in the node pack) reproduces these files to within one 16-bit LSB: 16 of
165 888 samples, 85 dB below peak, with `gain = 0.548736572`, `decay = 0.848528137` and the
measured cue supplied as the `transient` input. **The film was rendered from the wavs in this
directory**, built by `build_score.py`; the node is the in-graph equivalent.


## Every file in this directory, downloadable

GitHub Pages has no directory listing, so here they are explicitly.

| script | |
|---|---|
| [`build_score.py`](build_score.py) | builds every wav below, plus a seed-matched null for each |

| carrier wav | size |
|---|--:|
| [`f1_pane.wav`](f1_pane.wav) | 331,820 B |
| [`f1_pane_null.wav`](f1_pane_null.wav) | 331,820 B |
| [`f2_ceramic.wav`](f2_ceramic.wav) | 331,820 B |
| [`f2_ceramic_null.wav`](f2_ceramic_null.wav) | 331,820 B |
| [`f3_fruit.wav`](f3_fruit.wav) | 331,820 B |
| [`f3_fruit_null.wav`](f3_fruit_null.wav) | 331,820 B |
| [`f4_paint.wav`](f4_paint.wav) | 331,820 B |
| [`f4_paint_null.wav`](f4_paint_null.wav) | 331,820 B |
| [`f5_proof.wav`](f5_proof.wav) | 331,820 B |
| [`f5_proof_null.wav`](f5_proof_null.wav) | 331,820 B |
| [`f5b_proof.wav`](f5b_proof.wav) | 331,820 B |
| [`f5b_proof_null.wav`](f5b_proof_null.wav) | 331,820 B |
| [`f5c_bounce.wav`](f5c_bounce.wav) | 331,820 B |
| [`f5c_bounce_null.wav`](f5c_bounce_null.wav) | 331,820 B |
| [`f6_water.wav`](f6_water.wav) | 331,820 B |
| [`f6_water_null.wav`](f6_water_null.wav) | 331,820 B |
| [`f7_hold.wav`](f7_hold.wav) | 331,820 B |
| [`f7_hold_null.wav`](f7_hold_null.wav) | 331,820 B |
| [`f8_silent.wav`](f8_silent.wav) | 331,820 B |
| [`f8_silent_null.wav`](f8_silent_null.wav) | 331,820 B |
| [`f9_tick.wav`](f9_tick.wav) | 331,820 B |
| [`f9_tick_null.wav`](f9_tick_null.wav) | 331,820 B |
