# THE FUSE — the carriers, and how to rebuild them

Every sound event in this film was written into a **reference wav** before any picture existed.
H3 reproduces a transient written into the bound reference at the time you put it, so the rhythm is
authored first and the model performs it.

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
