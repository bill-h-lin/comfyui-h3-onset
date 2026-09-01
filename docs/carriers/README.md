# The commanded-transient carriers, and how to rebuild them

> 🔴 **THESE CARRIERS ARE NOT USED BY `THE STORM`, THE FILM ON THE ENTRY PAGE.**
> They belong to a **separate, earlier experiment** (working title *THE FUSE*). THE STORM binds no
> reference audio at all — `ref_image` and `ref_audio` are unconnected in its graph — so every impact
> you hear in that film is H3's own timing, not a written one. Keeping this page honest matters more
> than keeping it tidy, so the two are labelled rather than merged.

**What these files are for.** A sound event written into a **reference wav** before any picture
exists comes back in the render at the time you wrote it: H3 reproduces a transient in the bound
reference at its authored position, so the rhythm can be authored first and the model performs it.
That is the technique these wavs demonstrate, and it is measured — but ⚠️ **only within the first
~3.02 s of a 124-frame render** (beats at or after ~3.35 s do not reproduce), and ⛔ the picture does
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
`c9_tone_clean.wav` — room tone at −46 dBFS from t=0. ⛔ **Never digital silence:** a carrier that
contains a silent run makes a defect the model will happily reproduce.

## The two rules that cost me shots
1. **Never name the impacts in `overall_soundscape`.** Naming them makes H3 generate them itself,
   loudly, at times you did not choose. Use a restrained line.
2. **And name no SPACE in it either.** My "restrained" line said *"the quiet still air of a dark
   studio"* while the picture line asked for a *white* studio field — the model followed the
   soundscape and blacked out the set.

## Reproducing the carriers inside ComfyUI
`H3PlaceTransient` (in the node pack) reproduces these files to within one 16-bit LSB — 16 of
165 888 samples, 85 dB below peak — with `gain = 0.548736572`, `decay = 0.848528137`, and the
measured cue supplied as the `transient` input. **The film was rendered from the wavs in this
directory**, built by `build_score.py`; the node is the in-graph equivalent.
