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

| | |
|---|---|
| the reference's opening burst | **0.36×** speech RMS, **15.2×** above the gap that follows |
| renders that reproduced it | **24 of 24** (median 15.3×, all above 3×) |
| Whisper transcribing a spurious word before the line | **16 of 24** |
| zeroing the first 200 ms of the reference | burst drops to **0.2×** — **3 of 3** |

The duration is preserved — the window is silenced, not cut — so the audio clock cannot shift.
A short cosine ramp follows the silenced window so the cut does not itself become a new click.

The node returns a `report` string with the measured head peak before and after, so it states its
own evidence in the UI rather than asking you to trust it.

### Scope, honestly

- This addresses **one** of several things that can go wrong at the head of an H3 render. It is
  the *reference-copy* defect specifically. Do not assume it explains every head artefact you hear.
- **A source separator is not a substitute.** Music-bed removal (e.g. htdemucs) is a different
  axis and it is not sample-exact: run on an already-zeroed file it bled ~0.002 back into a window
  that had been exactly 0.000000. If you clean *and* trim, trim **after** cleaning, then verify the
  head is still exactly zero.
- Numbers above were measured on one box (RTX PRO 6000, ComfyUI v0.32.0, H3 ref2va int8).

---

## Two more things worth knowing, found while building this

### 1. Native references + keyframes are silently incompatible in every released ComfyUI

Bind native reference images **and** keyframes on the same generation and **the keyframes are
dropped — not rejected.** No error, no warning; you get a render that ignored them and you assume
the model is weak at control.

`comfy/model_base.py` writes `cond_video_latents` and then **overwrites it a few lines later.**
Verified present in **v0.32.0** and in **v0.33.3**, the newest release at the time of writing.

**The fix exists and is not mine:** PR **#15439** changes the overwrite to an append — credit to
**drozbay**. It is merged to `master` and is **in no release**, so upgrading does not get it. Patch
the file or run a worktree. The contribution here is the *failure mode and its silence*: this is
exactly the combination a reference-heavy workflow pushes you toward.

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
