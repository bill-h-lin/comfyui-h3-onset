# THE LAST HEAT — the 18 graphs that rendered it

These are the **executed API graphs** for all 18 shots of *THE LAST HEAT* — one file per shot,
dumped from the driver that rendered them and submitted through the Comfy MCP. They are not a
representative sample and not a hand-cleaned canvas export: each file is the prompt ComfyUI actually ran.

## The graphs are NOT identical to one another
This matters, because a one-file "here is the workflow" would be a lie about this film. The shots
differ in **which references they bind**, and that changes the node count:

| | shots |
|---|--:|
| bind **at least one reference image** | **11 of 18** |
| bind **a reference voice** | **10 of 18** |
| bind **both** | **7 of 18** |
| bind **neither** — text → picture + audio in one pass | **4 of 18** |
| bind **two** reference images, addressed as `<Picture 1>` / `<Picture 2>` | **4 of 18** |
| carry a spoken line (`[English]` in the prompt) | **10 of 18** |
| route the reference voice through **`H3ZeroAudioPrefix`** (this repo's node) | **10 of 18** |

Node counts run **15 to 19**. The 15-node shots are the ones with no reference at all; each bound
image adds a `LoadImage`, and a bound voice adds `LoadAudio` → `H3ZeroAudioPrefix`.

⭐ **The two-reference shots are the interesting ones.** `MiniMaxH3ReferenceToVideo` takes a list of
reference images (`ref_images.ref_image_0`, `ref_image_1`), and the prompt addresses them positionally
as `<Picture 1>` and `<Picture 2>`. That is how both characters appear in the same frame with
consistent identity.

⭐ **`H3ZeroAudioPrefix` is in 10 of these 18 graphs**, between `LoadAudio` and the H3 node.
It is the node in this repo, doing the job it was written for: H3 copies the first ~200 ms of the bound
reference voice into the render, and without the guard that burst arrives as a phantom sound before the
first word.

## Constant across all 18 shots — asserted, not asserted-by-eye
`width` 1344 · `height` 768 · `length` 124 frames @ 24 fps · `steps` 8 · `scheduler` `simple` ·
`sampler_name` `res_multistep` · UNet `minimax_h3_ref2va_pruned_int8_convrot` ·
CLIP `qwen3vl_32b_minimax_h3_bf16` (`type: minimax`) · video VAE fp16 + audio VAE fp32 ·
`PathchSageAttentionKJ` (`auto`, `allow_compile: false`) · `VAEDecode` **and** `VAEDecodeAudio` off the
same `SamplerCustomAdvanced` output.

## Per shot, in cut order

| # | graph | frames | cut dur (s) | nodes | seed | ref images | ref voice | spoken line | ZeroAudioPrefix |
|--:|---|--:|--:|--:|---|---|---|---|---|
| 1 | `s01_shopwide.json` | 124 | 5.17 | 17 | `20265911` | — | `c5_calm_voice.wav` | yes | yes |
| 2 | `s03c_master_look.json` | 121 | 5.04 | 18 | `20265953` | `lh_master_crop.png` | `c5_calm_voice.wav` | yes | yes |
| 3 | `s04_appr_a.json` | 119 | 4.96 | 18 | `20265911` | `lh_appr_full_crop.png` | `c5_noa_voice.wav` | yes | yes |
| 4 | `s05_gather.json` | 121 | 5.04 | 17 | `20265913` | — | `c5_calm_voice.wav` | yes | yes |
| 5 | `s05b_handoff.json` | 96 | 4.00 | 17 | `20265911` | `lh_master_crop.png`, `lh_appr_full_crop.png` | — | — | — |
| 6 | `s07_breath.json` | 84 | 3.50 | 15 | `20265911` | — | — | — | — |
| 7 | `s09_master_b.json` | 118 | 4.92 | 18 | `20265911` | `lh_master_crop.png` | `c5_calm_voice.wav` | yes | yes |
| 8 | `s09b_eyeline.json` | 101 | 4.21 | 17 | `20265931` | `lh_master_crop.png`, `lh_appr_full_crop.png` | — | — | — |
| 9 | `s10b_steady.json` | 124 | 5.17 | 17 | `20265943` | `lh_master_crop.png`, `lh_appr_full_crop.png` | — | — | — |
| 10 | `s11_thin.json` | 122 | 5.08 | 17 | `20265913` | — | `c5_calm_voice.wav` | yes | yes |
| 11 | `s12_appr_b.json` | 101 | 4.21 | 18 | `20265912` | `lh_appr_full_crop.png` | `c5_noa_voice.wav` | yes | yes |
| 12 | `s13c_reflect.json` | 124 | 5.17 | 15 | `20265961` | — | — | — | — |
| 13 | `s13b_hesays.json` | 121 | 5.04 | 18 | `20265913` | `lh_master_crop.png` | `c5_calm_voice.wav` | yes | yes |
| 14 | `s14_appr_c.json` | 124 | 5.17 | 18 | `20265911` | `lh_appr_full_crop.png` | `c5_noa_voice.wav` | yes | yes |
| 15 | `s15c_ring.json` | 124 | 5.17 | 15 | `20265922` | — | — | — | — |
| 16 | `s16_place.json` | 84 | 3.50 | 16 | `20265941` | `lh_appr_full_crop.png` | — | — | — |
| 17 | `s18b_tight.json` | 124 | 5.17 | 19 | `20265973` | `lh_master_crop.png`, `lh_appr_full_crop.png` | `c5_calm_voice.wav` | yes | yes |
| 18 | `s17_dawn.json` | 124 | 5.17 | 15 | `20265942` | — | — | — | — |

## What is NOT in this directory, and why
The bound reference files themselves (`lh_master_crop.png`, `lh_appr_full_crop.png`,
`c5_calm_voice.wav`, `c5_noa_voice.wav`) are **not redistributed here**. The two images are crops of
frames from **text-only H3 renders** made on this box — no photograph of any real person exists
anywhere in the chain. Load the graph, point `LoadImage`/`LoadAudio` at your own reference, and change
the `prompt`.

## Dependencies
- **ComfyUI v0.32.0** with the MiniMax H3 nodes (`MiniMaxH3ReferenceToVideo`, `VAEDecodeAudio`).
- **`H3ZeroAudioPrefix`** — [this repo](https://github.com/bill-h-lin/comfyui-h3-onset). Needed for
  10 of the 18 graphs; the other 8 run without it.
- **`PathchSageAttentionKJ`** — ComfyUI-KJNodes. It is a speed patch; drop the node and rewire
  `UNETLoader` → `BasicScheduler`/`BasicGuider` if you do not have it.
- Models: `minimax_h3_ref2va_pruned_int8_convrot.safetensors`, `qwen3vl_32b_minimax_h3_bf16.safetensors`,
  `minimax_h3_video_vae_fp16.safetensors`, `minimax_h3_audio_vae_fp32.safetensors`.

## Format
**API format** (`/prompt` payload), not canvas format — that is what ComfyUI executed and what the
`/history` audit compares against, so it is what is published. Load with *Workflow → Open* in a recent
ComfyUI, or POST to `/prompt` directly. An API graph carries no `Note` nodes, which is why the
annotation is this file rather than boxes on a canvas.

---
`h3_lastheat_workflows.zip` in this directory contains all 18 JSON files plus this README.
