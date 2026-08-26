"""H3 Onset Guard — zero the leading N ms of a reference voice before H3 sees it.

WHY THIS NODE EXISTS (measured, not assumed).
MiniMax H3 reproduces the FIRST ~200 ms of a bound reference voice inside the render.
If the reference opens on a breath, lip-smack or recording click, that burst is copied
into the generated audio as a phantom sound BEFORE the first word — 24 of 24 renders on
our box. Zeroing the leading 200 ms of the reference removes it, 3 of 3.

The fix is trivial and the failure is silent, which is exactly why it belongs in the
graph rather than in a shell script: a pre-trimmed .wav on disk looks identical to an
untrimmed one, so the guard is invisible to anyone who opens your workflow.

`report` returns the measured head level before and after, so the node states its own
evidence in the UI instead of asking you to trust it.
"""
import torch

class H3ZeroAudioPrefix:
    CATEGORY = "audio/h3"
    FUNCTION = "apply"
    RETURN_TYPES = ("AUDIO", "STRING")
    RETURN_NAMES = ("audio", "report")
    DESCRIPTION = ("Zero the leading N ms of a reference voice. H3 copies that window into "
                   "the render as a phantom onset; this removes it at the source.")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "audio": ("AUDIO",),
            "ms": ("FLOAT", {"default": 200.0, "min": 0.0, "max": 2000.0, "step": 10.0,
                             "tooltip": "Leading window to silence. 200 ms is the measured default."}),
            "ramp_ms": ("FLOAT", {"default": 10.0, "min": 0.0, "max": 200.0, "step": 1.0,
                                  "tooltip": "Cosine fade-in after the silenced window, so the "
                                             "cut itself does not become a new click."}),
        }}

    def apply(self, audio, ms, ramp_ms):
        wf = audio["waveform"]
        sr = int(audio["sample_rate"])
        out = wf.clone()
        n = int(round(sr * ms / 1000.0))
        n = max(0, min(n, out.shape[-1]))
        head_before = float(out[..., :n].abs().max()) if n else 0.0
        if n:
            out[..., :n] = 0.0
        r = int(round(sr * ramp_ms / 1000.0))
        r = max(0, min(r, out.shape[-1] - n))
        if r:
            ramp = 0.5 * (1.0 - torch.cos(torch.linspace(0, 3.141592653589793, r,
                                                         device=out.device, dtype=out.dtype)))
            out[..., n:n + r] *= ramp
        head_after = float(out[..., :n].abs().max()) if n else 0.0
        report = (f"zeroed {n} samples ({ms:.0f} ms) at {sr} Hz, {ramp_ms:.0f} ms cosine ramp | "
                  f"head peak {head_before:.6f} -> {head_after:.6f} | "
                  f"tail untouched ({out.shape[-1] - n - r} samples)")
        return ({"waveform": out, "sample_rate": sr}, report)


NODE_CLASS_MAPPINGS = {"H3ZeroAudioPrefix": H3ZeroAudioPrefix}
NODE_DISPLAY_NAME_MAPPINGS = {"H3ZeroAudioPrefix": "H3 Zero Audio Prefix"}
