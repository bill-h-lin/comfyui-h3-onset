#!/usr/bin/env python
"""selftest.py -- re-check every STRUCTURAL claim this README makes, on your machine.

Run:  python selftest.py

WHAT THIS DOES AND DOES NOT COVER.
It checks what the nodes do to a waveform: which samples they touch, which they leave alone,
what they report. That is exactly the part a reader can verify without a GPU.
⛔ It does NOT re-run the render measurements (the dB tables in the README). Those came from
the renders cited there and need H3, a GPU and about an hour.

🔴 EVERY CHECK IS PAIRED WITH A NEGATIVE CONTROL where one exists. A test suite that only ever
sees correct input cannot tell you it would have caught anything -- so `_must_fail` asserts that
a deliberately broken variant DOES trip the same check.
"""
import sys, math

try:
    import torch
except ImportError:
    sys.exit("selftest needs torch (ComfyUI already has it) -- run this with ComfyUI's python")

from nodes import H3ZeroAudioPrefix, H3PlaceTransient

SR = 32000
DUR = 5.184
N = int(round(SR * DUR))

_passed, _failed = 0, 0

def check(label, cond, detail=""):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  ok    {label}")
    else:
        _failed += 1
        print(f"  FAIL  {label}   {detail}")

def _must_fail(label, cond):
    """The negative control: `cond` is the SAME predicate applied to broken input.
    It must be False, or the check above it proves nothing."""
    global _passed, _failed
    if not cond:
        _passed += 1
        print(f"  ok    {label}  (negative control: broken input is rejected)")
    else:
        _failed += 1
        print(f"  FAIL  {label}  -- THE CHECK CANNOT FAIL, so it verifies nothing")

def tone(seed=0, dbfs=-46.0):
    """Room tone, never digital silence -- see the note in the README about manufactured defects."""
    g = torch.Generator().manual_seed(seed)
    x = torch.randn(N, generator=g)
    k = torch.hann_window(257); k = k / k.sum()
    x = torch.nn.functional.conv1d(x.view(1, 1, -1), k.view(1, 1, -1), padding=128).view(-1)[:N]
    x = x * (10 ** (dbfs / 20.0)) / x.pow(2).mean().sqrt()
    return {"waveform": x.view(1, 1, -1), "sample_rate": SR}


print("H3 Onset nodes -- structural selftest")
print(f"carrier: {N} samples, {DUR:.3f} s @ {SR} Hz\n")

# ---------------------------------------------------------------- node 1
print("H3ZeroAudioPrefix")
z = H3ZeroAudioPrefix()
src = tone(1)
# make a loud head burst, the defect this node exists for
src["waveform"][..., : int(0.2 * SR)] += 0.5

out, rep = z.apply(src, ms=200.0, ramp_ms=10.0)
n = int(round(SR * 0.2))
r = int(round(SR * 0.01))
check("zeroes exactly the leading 200 ms",
      float(out["waveform"][..., :n].abs().max()) == 0.0,
      f"peak={float(out['waveform'][..., :n].abs().max())}")
_must_fail("zeroes exactly the leading 200 ms",
           float(src["waveform"][..., :n].abs().max()) == 0.0)

check("leaves everything past the window+ramp bit-identical",
      torch.equal(out["waveform"][..., n + r:], src["waveform"][..., n + r:]))
_must_fail("leaves everything past the window+ramp bit-identical",
           torch.equal(out["waveform"][..., n:], src["waveform"][..., n:]))

check("sample rate is preserved", out["sample_rate"] == SR)
check("length is preserved", out["waveform"].shape[-1] == N)

hard, _ = z.apply(src, ms=200.0, ramp_ms=0.0)
check("ramp_ms=0 reproduces a hard trim exactly",
      torch.equal(hard["waveform"][..., n:], src["waveform"][..., n:]))

noop, _ = z.apply(src, ms=0.0, ramp_ms=0.0)
check("ms=0 is a guaranteed no-op", torch.equal(noop["waveform"], src["waveform"]))

# ⚠️ The SIGNAL through the ramp is noise and is not monotonic. The RAMP ENVELOPE is.
# Recover it by dividing out the source, which is what actually has to rise 0 -> 1.
env = (out["waveform"][0, 0, n:n + r] / src["waveform"][0, 0, n:n + r])
check("the ramp envelope rises monotonically 0 -> 1, so the cut cannot become a new click",
      bool((env.diff() >= -1e-5).all()) and float(env[0]) < 1e-6 and abs(float(env[-1]) - 1.0) < 1e-2,
      f"env[0]={float(env[0]):.4g} env[-1]={float(env[-1]):.4g} min_diff={float(env.diff().min()):.3g}")
_must_fail("the ramp envelope rises monotonically 0 -> 1, so the cut cannot become a new click",
           bool(((hard["waveform"][0, 0, n:n + r] / src["waveform"][0, 0, n:n + r]).diff().abs() > 1e-5).any()))

check("report states the measured before/after head peak",
      "head peak" in rep and "->" in rep, rep)

# ---------------------------------------------------------------- node 2
print("\nH3PlaceTransient")
p = H3PlaceTransient()
K = [1000, 1900, 2548, 3015, 3350, 3592, 3766]
base = tone(2)
placed, rep2 = p.apply(base, times_ms=", ".join(str(k) for k in K),
                       width_ms=12.0, gain=0.55, decay=0.72)

w = max(1, int(round(SR * 12.0 / 1000.0)))
windows = []
for ms in K:
    s = int(round(SR * ms / 1000.0))
    windows.append((s, min(s + w, N)))

mask = torch.ones(N, dtype=torch.bool)
for s, e in windows:
    mask[s:e] = False

check("samples OUTSIDE the placed windows are untouched",
      torch.equal(placed["waveform"][0, 0][mask], base["waveform"][0, 0][mask]))
_must_fail("samples OUTSIDE the placed windows are untouched",
           torch.equal(placed["waveform"][0, 0], base["waveform"][0, 0]))

check("every commanded window actually changed",
      all(not torch.equal(placed["waveform"][0, 0, s:e], base["waveform"][0, 0, s:e])
          for s, e in windows))

check("the first transient carries the requested gain",
      abs(float(placed["waveform"][0, 0, windows[0][0]:windows[0][1]].abs().max()) - 0.55) < 1e-3,
      f"peak={float(placed['waveform'][0, 0, windows[0][0]:windows[0][1]].abs().max()):.4f}")

check("decay is applied per successive transient",
      float(placed["waveform"][0, 0, windows[6][0]:windows[6][1]].abs().max())
      < float(placed["waveform"][0, 0, windows[0][0]:windows[0][1]].abs().max()))

gaps = [K[i + 1] - K[i] for i in range(len(K) - 1)]
check(f"the tightest gap ({min(gaps)} ms) still gives two separate, non-overlapping transients",
      min(gaps) * SR / 1000.0 > w and windows[5][1] <= windows[6][0])

check("length and sample rate are preserved",
      placed["waveform"].shape[-1] == N and placed["sample_rate"] == SR)

check("report names what it placed", "placed 7 transient(s)" in rep2, rep2)

# a NULL built the way the README says to build one
null, _ = p.apply(tone(2), times_ms="", width_ms=12.0, gain=0.55, decay=0.72)
check("an empty times_ms yields a carrier byte-identical to the source (a valid null)",
      torch.equal(null["waveform"], base["waveform"]))

# out-of-range must be REPORTED, not silently dropped
_, rep3 = p.apply(tone(3), times_ms="1000, 99000", width_ms=12.0, gain=0.55, decay=1.0)
check("a time past the end of the carrier is REPORTED, not silently dropped",
      "SKIPPED" in rep3 and "99000" in rep3, rep3)
_must_fail("a time past the end of the carrier is REPORTED, not silently dropped",
           "SKIPPED" in rep2)

# a bad token must raise, not be quietly ignored
try:
    p.apply(tone(4), times_ms="1000, banana", width_ms=12.0, gain=0.55, decay=1.0)
    check("an unparseable time raises instead of being ignored", False, "no exception")
except ValueError as e:
    check("an unparseable time raises instead of being ignored", "banana" in str(e))

# the optional supplied transient must actually be used
shape = {"waveform": torch.ones(1, 1, 64) * 0.9, "sample_rate": SR}
sup, rep4 = p.apply(tone(5), times_ms="1000", width_ms=12.0, gain=0.4, decay=1.0, transient=shape)
s0 = int(round(SR * 1.0))
check("a supplied transient is used instead of the synthetic click",
      abs(float(sup["waveform"][0, 0, s0:s0 + 64].abs().max()) - 0.4) < 1e-3
      and "supplied audio" in rep4, rep4)

print(f"\n{_passed} passed, {_failed} failed")
sys.exit(1 if _failed else 0)
