# ComfyUI H3 Onset Guard

A one-node fix for MiniMax H3's **phantom onset** — the *"annoying tiny bits of dialogue at the
very first second"* that people keep reporting on reference-to-video renders.

**H3 copies the opening milliseconds of your reference voice into the render.** If the reference
opens on a breath, a lip-smack or a recording click, that burst is reproduced before the first
word. It is not a sampler artefact and it is not random.

```
custom_nodes/  →  git clone https://github.com/bill-h-lin/comfyui-h3-onset
```
No dependencies beyond torch. Restart ComfyUI; the node appears as **H3 Zero Audio Prefix**
under `audio/h3`. Drop it between your `LoadAudio` and the reference-audio input.

---

## The measurement

The claim is not "the head is loud." It is that **the render copies the first ~320 ms of the
specific wav you bound**, and the control is what makes that readable:

| each render's first 320 ms, cross-correlated against… | Pearson r |
|---|---:|
| **its own bound reference wav** | **0.76 – 0.92** |
| the *other* character's wav | **0.013 – 0.024** |

That separation is the whole result. The correlation is to that file, not to speech in general.

Two shots with **byte-identical prompts**, differing only in the bound wav, made it visible: their
reference heads sit **39.2 dB vs 3.8 dB** above floor, and the render heads follow almost exactly.
The two wavs are **bit-identical from 0.32 s onward** — one is simply the other with its first
199.7 ms zeroed.

**On the amplitude endpoint** (measured earlier, separately): the reference opens at **0.36×**
speech RMS, **15.2×** above the gap that follows; **24 of 24** renders reproduced it above 3×;
Whisper transcribed a spurious word before the line in **16 of 24**. Zeroing the leading 200 ms
dropped it to 0.2×, **3 of 3**.

### Two things that took us a while, and will save you the same time

**1. It is seed-dependent — 2 of 6 seeds skipped the copy entirely** (r = 0.115 and 0.080 against
their own wav). Those two looked like the *best* result in a before/after comparison, with the
largest apparent reduction of the set — **their heads were quiet because they skipped the copy, not
because anything fixed it.** A reduction number alone mis-attributes in both directions. Check the
mechanism, not the delta.

**2. The copy is not the defect — a loud reference head is.** One shot correlates at r = 0.83 and
is completely inaudible, because its reference head is only 3.8 dB above floor: there is nothing
loud to copy. This is *why* zeroing the head is the right fix rather than trying to suppress the
copy — you remove what there is to copy.

The duration is preserved — the window is silenced, not cut — so the audio clock cannot shift. A
short cosine ramp follows so the cut does not itself become a new click. The node returns a
`report` string with the measured head peak before and after, so it states its own evidence in the
UI rather than asking you to trust it.

### Scope, honestly

- This addresses **one** of several things that can go wrong at the head of an H3 render, and we
  have separated three. A prompt-caused burst from `<d></d>` dialogue tags (~24 dB, 20/20) is a
  *different* defect with a different fix, and a ~19.6 ms silence-then-step at t=0 is a third whose
  cause is still unresolved. **Do not merge them** — we did, for two sessions, and it cost us.
- **A source separator is not a substitute.** Music-bed removal (e.g. htdemucs) is a different axis
  and it is not sample-exact: run on an already-zeroed file it bled ~0.002 back into a window that
  had been exactly 0.000000. If you clean *and* trim, trim **after** cleaning, then verify the head
  is still exactly zero.
- Measured on one box: RTX PRO 6000, ComfyUI v0.32.0, H3 ref2va int8.

---

## Two more things worth knowing, found while building this

### 1. Native references + keyframes are silently incompatible in ComfyUI up to and including v0.33.3

Bind native reference images **and** keyframes on the same generation and **the keyframes are
dropped — not rejected.** No error, no warning; you get a render that ignored them and you assume
the model is weak at control.

In `comfy/model_base.py`, `class MiniMaxH3`'s `extra_conds` has **two independent `if` blocks, not
an `if`/`else`**: the keyframe branch assigns `cond_video_latents`, and the reference branch then
**unconditionally reassigns it.** Verified present on **v0.32.0** and **v0.33.3**.

**The fix exists, it is not mine, and it has shipped:** PR **#15439** changes the overwrite to an
append — credit to **drozbay**. Merged 2026-08-13 and **released in ComfyUI v0.34.0 on 2026-08-26.**
⇒ **On v0.34.0 or newer you do not have this bug; on v0.33.3 or older you still do**, and nothing in
the UI will tell you. The contribution here is the *failure mode and its silence*: this is exactly
the combination a reference-heavy workflow pushes you toward.

### 2. The official H3 template's scheduler advice degrades this stack

The official MiniMax H3 R2V template carries embedded guidance recommending `beta` or `normal`
over `simple` for reference-heavy prompts. Tested with same seed / prompt / references / canvas /
steps, scheduler the only variable:

| scheduler | identity (SFace cosine) | face height | picture |
|---|---:|---:|---|
| **`simple`** (used here) | **0.531** | 39.6 % | clean |
| `normal` | **0.208** | 38.3 % | clean, slightly better water texture |
| `beta` | — | — | **red grid artefacts over every frame, washed-out colour** |

`beta` produces gross visible corruption — not a taste judgement. `normal` renders cleanly and
**destroys identity transfer**; framing is matched to within 1.3 pp, which accounts for only ~0.035
of the 0.32 gap, so this is an identity result and not a framing artefact.

⚠️ **One seed** — quoted as a direction, not a closed number. Both effects sit far outside
run-to-run noise (the identity noise floor here is ~0.0004). A careful implementer following the
official note would switch schedulers and silently degrade every render.

---

## The workflow

`workflow/h3_r2v_workflow.json` — frontend format, drag it onto the ComfyUI canvas.

It is the **API prompt our driver actually submits**, exported to frontend format through
ComfyUI's own `app.loadApiJson` → `graph.serialize()`, then verified by round-tripping back
through `graphToPrompt()` and diffing against the driver's `--dump-workflow` output:
**0 input-level differences, node ids preserved.** Nothing in it was hand-authored.

🔴 **A trap worth repeating, because it cost us a bad file:** the round-trip diff is **blind to a
nonexistent input file.** A `LoadImage` pointing at a filename that does not exist round-trips with
0 diffs — the frontend faithfully preserves a path it cannot resolve. Only the *judge path*
(`loadGraphData`, i.e. dragging the file onto the canvas) reports `missing: ['LoadImage']`. **A
clean diff is not evidence the graph will run.**

### Non-default parameters, and the measurement behind each

| setting | value | why it is not the default |
|---|---|---|
| steps | **8** | the ref2va lane's measured floor on this box; 20 is the text-to-video lane and a different question |
| resolution | **1344×768** | the 1152×640 detail floor survives on v0.32.0 (19 v 4, p = 0.0026). Do not enlarge the canvas for 2K |
| scheduler | **`simple`** | measured — and it contradicts this model's own official template. See above |
| precision | **int8 DiT + bf16 encoder** | the bf16 twin fits at 3 references (90.8 GiB, +27 % s/it) and was rejected on a blind listening test, not on cost |
| reference count | **≤ 3** | identity gain plateaus at 3. VRAM does not rise monotonically with count — 90.7 / 93.3 / 90.8 GiB at 1 / 2 / 3 |
| attention | Sage via the **node**, never the launch flag | the global `--use-sage-attention` flag swaps module-level attention for everything, and the audio VAE calls it |

**Dependency note:** the graph includes `PathchSageAttentionKJ` from
[KJNodes](https://github.com/kijai/ComfyUI-KJNodes) — this is the sanctioned route to Sage
attention, as opposed to the global `--use-sage-attention` launch flag, which swaps module-level
attention for everything including the audio VAE. Bypass the node if you do not have KJNodes
installed and the graph runs on stock ComfyUI. ⚠️ **Every render in this entry was made with it
active, and I have not measured whether bypassing it changes the output** — attention kernels are
not numerically identical, so treat a bypassed run as a different configuration, not as a
reproduction.

### The rule that is not visible in the graph

**References must follow who is in shot.** A bound character reference puts that character in
frame even when the prompt never mentions them — measured on 2 of 2 shots, and in one case the
character rendered *back-to-camera and faceless*, which a face detector scores as absent. Deleting
the description is **not** sufficient; drop the reference image.

A set reference must contain **no one**, and a full-frame plate pins the camera — an empty plate
fixed the body count but cost the eyeline 8/8 → 0/8.

---

## Licence

MIT. The keyframe fix (PR #15439) is drozbay's work, not mine.
