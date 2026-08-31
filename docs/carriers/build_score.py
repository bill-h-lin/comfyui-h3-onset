#!/home/bill/infra/venvs/earlane/bin/python
"""Build CONDUCTED's score: one carrier wav per shot, plus its seed-matched null.

🔴 THE STIMULUS IS NOT RE-DERIVED.  Every transient is the SAME 672-sample tick group measured in
comp/c9/PROBE_PLACED_TRAIN.md (7/7 placed, 7/7 decoys flat, holds to 174 ms gaps).  tick_idx.npy /
tick_vals.npy are copied from c12film, never rebuilt -- changing the stimulus would make every
measured row on this track incomparable.

⛔ NOT digital silence anywhere.  The bed is c9_tone_clean.wav (room tone, -46 dBFS, from t=0).
Each shot's NULL is that same bed, byte-identical to the carrier OUTSIDE the placed windows --
asserted here, not assumed.  That is what makes "the event fired" mean anything.

⭐ A WITHHELD beat is simply a time listed in `hold`: it is written into the SHOT LIST (so the cut
lands there) but NOT into the carrier.  🔴 Per RESULT_BEAT_COMPLETION.md the model COMPLETES a
withheld TERMINAL member of a learned accelerating train 8/10 -- so a hold is only legal on a shot
whose events are ISOLATED, and this tool REFUSES a hold on a shot that carries a train.
"""
import numpy as np, soundfile as sf, json, hashlib, os, sys

SR, DUR = 32000, 5.1840
N = int(round(SR * DUR))
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.expanduser("~/ComfyUI/input")

idx = np.load(f"{HERE}/tick_idx.npy")
vals = np.load(f"{HERE}/tick_vals.npy")
assert len(idx) == 672, f"tick geometry changed: {len(idx)}"
rel = idx - idx[0]

clean, sr = sf.read(f"{OUT}/c9_tone_clean.wav")
assert sr == SR and len(clean) == N, (sr, len(clean))
clean = clean.astype(np.float32)


def build(name, times, amps=None, hold=()):
    """Place the measured tick group at `times`.  `hold` times are NOT written (commanded silence)."""
    times = list(times)
    if hold:
        gaps = np.diff(sorted(times + list(hold)))
        if len(gaps) >= 3 and np.all(np.diff(gaps) < 0):
            sys.exit(f"🔴 REFUSED: {name} holds a beat inside an ACCELERATING train -- "
                     f"RESULT_BEAT_COMPLETION.md measured the model completing that 8/10.")
    if amps is None:
        amps = [0.72 ** (k * 0.5) for k in range(len(times))]
    out = clean.copy()
    windows = []
    for t, a in zip(times, amps):
        p = int(round(t * SR)) + rel
        # 🔴 WRITE ONLY WHERE THE HARVESTED CUE IS NON-ZERO.  tick_vals.npy is sparse -- it was
        # extracted by diffing a recording against its own null, so 8 of its 672 samples are
        # exactly 0.  Writing those stamps DIGITAL SILENCE into the room tone, which is the
        # manufactured-defect trap (§DN.11).  It is also what made this script disagree with the
        # shipped H3PlaceTransient node, whose sparse write is the correct behaviour.
        keep = (p < N) & (vals != 0)
        out[p[keep]] = (vals[keep] * a).astype(np.float32)
        windows.append((int(p[keep][0]), int(p[keep][-1])))
    # SINGLE-VARIABLE ASSERTION: identical to the bed everywhere outside the placed windows
    mask = np.ones(N, bool)
    for a, b in windows:
        mask[a:b + 1] = False
    assert np.array_equal(out[mask], clean[mask]), f"{name}: carrier differs from the bed OUTSIDE the ticks"
    cp, nu = f"{OUT}/{name}.wav", f"{OUT}/{name}_null.wav"
    sf.write(cp, out, SR); sf.write(nu, clean, SR)
    return {"name": name, "placed": [round(t, 4) for t in times], "hold": [round(t, 4) for t in hold],
            "carrier": cp, "null": nu,
            "md5": hashlib.md5(open(cp, "rb").read()).hexdigest()[:12]}


if __name__ == "__main__":
    spec = json.load(open(f"{HERE}/score.json"))
    man = [build(s["name"], s["at"], s.get("amps"), s.get("hold", ())) for s in spec["shots"]]
    json.dump(man, open(f"{HERE}/carriers_manifest.json", "w"), indent=1)
    for m in man:
        print(f"  {m['name']:14s} placed={m['placed']}  hold={m['hold']}  md5={m['md5']}")
    print(f"\n{len(man)} carrier(s) + {len(man)} null(s) -> {OUT}")
