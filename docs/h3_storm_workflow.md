# `h3_storm_workflow.json` — the graph that actually rendered THE STORM

**This is the API graph ComfyUI executed**, dumped from the driver and submitted through the Comfy
MCP. It is 15 nodes. Every one of the six shipped shots ran **this** graph and differed only in
`prompt` and `noise_seed`.

> ⚠️ **Read this before you compare it with `h3_fuse_workflow.json`.** That other file is the
> **commanded-transient** graph — it is 17 nodes and adds `LoadAudio` → `H3ZeroAudioPrefix` to bind a
> carrier wav. **THE STORM does not use it.** The two files are different experiments and both are
> published on purpose: one is the film, the other is the technique.

## The part that surprises people: there is no reference bound at all

`MiniMaxH3ReferenceToVideo` is the node's name, not a claim about the inputs. In this graph its
`ref_image` and `ref_audio` sockets are **left unconnected**:

```
inputs: clip, vae, audio_vae, prompt, width=1344, height=768, length=124, ref_image_size=match
        (no ref_image, no ref_audio)
```

⇒ THE STORM is **text → picture + audio in one H3 pass**, with nothing conditioning the sound.
That is exactly why the film's impacts are the model's own timing and not commanded ones.
🔴 **`--ref-image` / `--ref-audio` left unset do NOT mean "no reference" in every driver — some bind a
default.** Pass the explicit negative (`--no-ref-image --no-ref-audio`) or check the dumped graph.

## Settings that are not defaults, and why

| node / field | value | why |
|---|---|---|
| `BasicScheduler.scheduler` | `simple` | measured on this box; **it contradicts this model's own official template** |
| `BasicScheduler.steps` | `8` | the ref2va lane's measured production point |
| `KSamplerSelect.sampler_name` | `res_multistep` | |
| `MiniMaxH3ReferenceToVideo` w×h | `1344×768` | the 1152×640 detail floor survives v0.32.0 (19 v 4, p = 0.0026) |
| `…length` | `124` | 124 frames @ 24 fps ≈ 5.17 s — **the same 124 f the ≤3.02 s position bound was measured at** |
| `UNETLoader.unet_name` | `minimax_h3_ref2va_pruned_int8_convrot` | int8 ref2va |
| `CLIPLoader.clip_name` | `qwen3vl_32b_minimax_h3_bf16`, `type: minimax` | |
| two `VAELoader`s | video fp16 + audio fp32 | H3 decodes picture and sound separately — `VAEDecode` and `VAEDecodeAudio` both run |
| `PathchSageAttentionKJ` | `auto`, `allow_compile: false` | |
| `CreateVideo.fps` | `24.0` | |

## Reproducing a shot
Load this graph, replace `prompt` with one of the six in the repo, set `noise_seed`, submit. The
prompt text is the full `integrated_multimodal_description:` / `overall_soundscape:` block — H3 reads
the soundscape line, which is how a shot gets "quiet still air and nothing else" instead of music.
