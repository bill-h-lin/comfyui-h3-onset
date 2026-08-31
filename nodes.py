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


class H3PlaceTransient:
    """Write short transients into a reference wav at chosen times, so H3 puts sound events there.

    WHY THIS NODE EXISTS (measured, and scoped honestly).
    H3 gives you no handle on WHEN it makes a sound. A timecode in the prompt does not work --
    the prompt format cannot express intra-shot pacing; timecodes read as shot markers. What
    does work is the reference audio: H3 reproduces a transient written into the bound wav at
    the time you put it.

    MEASURED ON THIS BOX (r2v, 8 steps, 124 f, 1344x768, room-tone carrier):
      seven transients placed at 1000/1900/2548/3015/3350/3592/3766 ms came back at
      +27.0 / +18.2 / +20.5 / +22.0 / +12.2 / +14.1 / +12.2 dB over an otherwise byte-identical
      carrier -- n = 3/3 seeds on every one. Seven DECOY times with nothing placed read
      -0.3 to +1.4 dB, also 3/3. Gaps down to 174 ms still resolve.
      Landing is EARLY BY A FIXED OFFSET, not by a fraction of the commanded time.  Tested
      2026-08-31: our carrier is 5.184 s against a 5.1667 s render (0.334% longer), and a
      linear time-scale would put events early in proportion to t -- mean 9.2 ms, which is
      almost exactly the "~10 ms" figure an average would give.  It is NOT that: the
      UNSCALED carrier cross-correlates ~2x better than one resampled to the render's
      length, on 4 of 4 takes, at a constant +5 ms lag.
      => H3 places a transient at its ABSOLUTE time in the carrier, so THE CARRIER DOES NOT
      HAVE TO BE THE SAME LENGTH AS THE RENDER.  Write events where you want them in a
      carrier of convenient length.

    IT IS NOT PASSTHROUGH. Several of those deltas EXCEED the amplitude of the cue itself, so
    H3 generates a fuller event than you wrote in. The audio in the render is the model's; the
    reference only says *when*.

    WHAT IS NOT ESTABLISHED. Whether the PICTURE lands on the same instant. Treat picture-sound
    agreement as something you SELECT for across takes, not something this node commands.

    SCOPE. One prompt, one carrier, one box. A carrier containing SPEECH behaves differently:
    it reproduces transients before its own voice onset and goes deaf after it, and it imports
    the spoken line into your render (6/6 here). Use a speech-free carrier.
    """
    CATEGORY = "audio/h3"
    FUNCTION = "apply"
    RETURN_TYPES = ("AUDIO", "STRING")
    RETURN_NAMES = ("audio", "report")
    DESCRIPTION = ("Write transients into a reference wav at chosen times. H3 reproduces them, "
                   "so this is a handle on WHEN the model makes a sound.")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "audio": ("AUDIO", {"tooltip": "Carrier. Use room tone, NOT speech -- a speech "
                                           "carrier imports its line into your render."}),
            "times_ms": ("STRING", {"default": "1000, 1900, 2548, 3015",
                                    "tooltip": "Comma-separated times in ms. Irregular spacing "
                                               "is fine; 174 ms gaps still resolved here."}),
            "width_ms": ("FLOAT", {"default": 12.0, "min": 1.0, "max": 200.0, "step": 1.0,
                                   "tooltip": "Transient length. The measured stimulus was two "
                                              "ticks of 9 and 12 ms."}),
            # 🔴 step/round matter for REPRODUCIBILITY, not for taste. The ComfyUI frontend
            # SNAPS a widget value to its step on export, so a coarse step silently rewrites a
            # carrier: 0.5487370491027832 -> 0.55 turned a graph into "not the graph we rendered
            # with", and h3-workflow-export.py refused to write it.
            "gain": ("FLOAT", {"default": 0.55, "min": 0.0, "max": 1.0, "step": 0.0001,
                               "round": False,
                               "tooltip": "Peak amplitude of the first transient."}),
            "decay": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 1.0, "step": 0.0001,
                                "round": False,
                                "tooltip": "Multiplier applied per successive transient. 1.0 = "
                                           "all equal; <1 models something settling."}),
        }, "optional": {
            "transient": ("AUDIO", {"tooltip": "Optional: use THIS audio as the transient shape "
                                               "instead of a synthetic click. Harvesting one from "
                                               "an accepted H3 take keeps the cue in-domain."}),
        }}

    def apply(self, audio, times_ms, width_ms, gain, decay, transient=None):
        wf = audio["waveform"]
        sr = int(audio["sample_rate"])
        out = wf.clone()
        n_total = out.shape[-1]

        times = []
        for tok in str(times_ms).replace(";", ",").split(","):
            tok = tok.strip()
            if not tok:
                continue
            try:
                times.append(float(tok))
            except ValueError:
                raise ValueError(f"times_ms: could not read {tok!r} as a number")
        times.sort()

        if transient is not None:
            shape = transient["waveform"].clone()
            while shape.dim() > 1:
                shape = shape[0]
            shape = shape / (shape.abs().max() + 1e-9)
        else:
            w = max(1, int(round(sr * width_ms / 1000.0)))
            t = torch.linspace(0.0, 1.0, w)
            # a click with a fast attack and an exponential tail, band-limited enough not to alias
            shape = torch.sin(2 * 3.141592653589793 * 2000.0 * t * (w / sr)) * torch.exp(-6.0 * t)
            shape = shape / (shape.abs().max() + 1e-9)

        placed, skipped = [], []
        # 🔴 A HARVESTED CUE IS SPARSE. It is extracted by diffing a recording against its own
        # null, so it is exact zero everywhere except the event samples -- our measured stimulus
        # is 672 non-zero samples inside a 43 ms span, in two clusters with a gap between them.
        # Overwriting the WHOLE span would stamp digital silence into that gap, which is the
        # manufactured-defect trap: the carrier must never contain digital silence. So for a
        # supplied cue we write only where it is non-zero and leave the carrier's room tone
        # standing everywhere else. A synthetic click is a continuous waveform whose zero
        # crossings are part of its shape, so it is written across the whole span.
        sparse = transient is not None
        nz = (shape != 0) if sparse else None
        amp = float(gain)
        for i, ms in enumerate(times):
            start = int(round(sr * ms / 1000.0))
            end = min(start + shape.shape[-1], n_total)
            if start < 0 or start >= n_total:
                skipped.append(ms)
                continue
            seg = (shape[: end - start] * amp).to(out.device, out.dtype)
            if sparse:
                m = nz[: end - start].to(out.device)
                out[..., start:end] = torch.where(m, seg, out[..., start:end])
            else:
                out[..., start:end] = seg
            placed.append(ms)
            amp *= float(decay)

        dur_ms = 1000.0 * n_total / sr
        report = (f"placed {len(placed)} transient(s) at {[round(x) for x in placed]} ms "
                  f"in a {dur_ms:.0f} ms carrier @ {sr} Hz; "
                  f"shape={'supplied audio' if transient is not None else f'{width_ms:.0f} ms synthetic click'}, "
                  f"gain {gain:.2f}, decay {decay:.2f}"
                  + (f" | SKIPPED (outside the file): {[round(x) for x in skipped]} ms" if skipped else "")
                  + " | samples outside the transient windows are untouched")
        return ({"waveform": out, "sample_rate": sr}, report)


NODE_CLASS_MAPPINGS = {
    "H3ZeroAudioPrefix": H3ZeroAudioPrefix,
    "H3PlaceTransient": H3PlaceTransient,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "H3ZeroAudioPrefix": "H3 Zero Audio Prefix",
    "H3PlaceTransient": "H3 Place Transient",
}
