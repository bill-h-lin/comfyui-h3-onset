# ComfyUI H3 Onset: two nodes for controlling MiniMax H3's audio

H3 gives you no handle on **when** it makes a sound, and it silently copies the head of your
reference voice into the render. These two nodes fix the second problem and turn the same
underlying mechanism into a control surface for the first.

Everything below was measured on one box: RTX PRO 6000, ComfyUI v0.32.0,
`minimax_h3_ref2va_pruned_int8`, 8 steps, 124 frames, 1344x768, local. **`selftest.py` re-checks
every structural claim in this README on your machine in a few seconds.**

---

## Node 1: `H3 Zero Audio Prefix`

### The defect

**H3 copies the first ~200 ms of the bound reference voice into the generated audio.**

If your reference WAV opens on a breath, a lip-smack, or a recording click, that burst is
reproduced in the render as a phantom sound *before the first word*. The render is otherwise
perfect: correct length, correct dialogue, clean video. Nothing fails. You only notice if you
listen to the head of every clip. This is the widely-reported *"annoying tiny bits of dialogue at
the very first second."*

| | result |
|---|---|
| renders reproducing the reference's onset burst | **24 / 24** |
| Whisper transcribing a spurious word before the line | **16 / 24** |
| renders after zeroing the reference's leading 200 ms | **0 / 3** |
| head-200 ms peak, one real reference | `0.508` → `0.000` |

### The fix

Insert **H3 Zero Audio Prefix** between `LoadAudio` and the H3 reference-to-video node. It zeroes
the leading window and applies a short cosine ramp so the cut does not itself become a new click.
Everything after the window is **bit-identical** to the source.

### Why a node and not a trimmed file

A pre-trimmed `.wav` on disk looks exactly like an untrimmed one. The guard becomes invisible to
anyone who opens your workflow, and invisible to you six weeks later. In the graph it is
self-documenting, and the `report` output states the measured before/after head peak, so the node
shows its own evidence rather than asking to be trusted.

### Inputs

| | |
|---|---|
| `audio` | AUDIO |
| `ms` | leading window to silence. **200 ms** is the measured default |
| `ramp_ms` | cosine fade-in after the window. 10 ms default; `0` reproduces a hard trim exactly |

### Caveat

The 200 ms figure is measured for H3's audio conditioning on this stack. **Check your own reference
files.** Burst magnitude varies a lot per file (head-200 ms peaks of 0.508, 0.426 and 0.094 across
three voices here). `ms=0` is a guaranteed no-op if you want to A/B it.

---

## Node 2, `H3 Place Transient`: telling H3 *when* to make a sound

**The copy is not confined to the head.** At the head it is a defect and node 1 removes it. Off the
head it is a **control surface**.

Write short transients into the bound reference at the times you want events. H3 puts sound events
there. **Seven of them, in one 5.18 s shot:**

| commanded (ms) | 1000 | 1900 | 2548 | 3015 | 3350 | 3592 | 3766 |
|---|--:|--:|--:|--:|--:|--:|--:|
| **excess over an otherwise byte-identical carrier (dB)** | **+27.0** | **+18.2** | **+20.5** | **+22.0** | **+12.2** | **+14.1** | **+12.2** |
| **seven decoy times, nothing placed** | -0.3 | +0.1 | +0.2 | -0.4 | +0.6 | +1.0 | -1.4 |

**n = 3/3 seeds on every cell. 21 firing, 21 flat.** The null is the *same file* with only the
transient windows removed, so the comparison has one variable. **Gaps down to 174 ms still resolve.**
Landing is **slightly early by a constant**. See Scope for the size and the reason.

⭐ **This is not passthrough.** Several of those deltas **exceed the amplitude of the cue itself**
(+27.0 against a stimulus ceiling of +24.6; +22.0 against +14.4; +12.2 against +7.5). H3 generates
a fuller event than you wrote in. The audio in the render is the model's; the reference only says *when*.

**It transfers to new subjects.** The same train, two scenes it was never tuned on, 2 seeds each:

| subject | K - null at the seven commanded times (dB) | ≥ +10 dB | 6 decoy times |
|---|---|--:|---|
| chained trunk | +17.6 / +17.8 / +18.8 / +21.2 / +7.7 / +14.7 / +10.7 | 6 of 7 | -7.84 ... +0.72 |
| steel wall anchor | +26.3 / +17.2 / +20.4 / +22.1 / +12.8 / +14.3 / +9.4 | 6 of 7 | -3.12 ... +0.58 |

### The complement: **commanded silence**, and a listener confirmed it

Leave a region with no placed transient and it comes back quiet. Measured as the loudest 40 ms
window against that same clip's own 20th-percentile bed:

| arm | loudest moment over its own floor |
|---|--:|
| placed train | **21-22 dB** |
| null: same scene, same seeds, transients removed | **5.4-7.0 dB** |

Then a blind listening test, because a dB figure is not a perception. Six takes of a scene that
**visibly depicts a hammer striking a bronze bell**, anonymised and shuffled, key sealed to a file
and unopened until the verdict was recorded. Three placed, three not. Asked only what they heard:

> *"take 3 4 6 are just background strong wind sound? take 1 2 5 are clicking sound"*

**3/3 by arm. p = 1/C(6,3) = 0.050, one-tailed.** A bell is struck on screen and the track is wind,
unless you place the event.

### Inputs

| | |
|---|---|
| `audio` | carrier. **Use room tone, not speech.** See scope |
| `times_ms` | comma-separated times. Irregular spacing is fine |
| `width_ms` | transient length. The measured stimulus was two ticks of 9 and 12 ms |
| `gain` | peak amplitude of the first transient |
| `decay` | multiplier per successive transient (`1.0` = all equal) |
| `transient` *(optional)* | use this AUDIO as the transient shape. **Harvesting one from an accepted H3 take** keeps the cue in-domain. ⚠️ Not A/B'd against a synthetic click |

Returns the modified `AUDIO` and a `report` naming exactly what it placed and what it skipped.

---

## ⚠️ Scope: a capability, not a clock

- 🔴 **We do NOT command *what*.** In the bronze test above the placed event was heard as a
  *click*, not a bell. The scene depicts a struck bell. The node places an event and makes it
  bigger than the cue; it does **not** re-timbre it into the depicted object's voice. A click is
  right for a knock and wrong for a tower clock.
- 🔴 **We do NOT claim the picture follows.** We pre-registered that test and it **failed**: 16
  held-out takes, a tracked visible rebound within ±60 ms of a commanded time, per-clip null at a
  random phase over 4000 draws. Placed hits 5,4,4,3,2,1,1 (median 3.0) v null 2,1,1,1,1,0,0 (median
  1.0). Median higher, **but the arms overlap**, and no-overlap was the pre-declared bar. **Not
  established.** Treat picture-sound agreement as something you *select* for across takes: about
  57 % here, roughly two takes per keeper.
- **Use a speech-free carrier.** A carrier containing speech reproduces transients *before* its own
  voice onset and **goes deaf after it** (+39/+43/+39 dB, then -5.2/+0.4/+0.7/+0.6). **It also
  imports the spoken line into your render, 6 of 6.**
- **Per-arm spread widens from 2.52 to ~30 dB at production geometry.** It reproduces; it does not
  reproduce *uniformly*. Budget re-rolls.
- ⚠️ An earlier draft of ours said the landing error was -15 ms. **It was not.** 5 ms of that was
  *the detector's own offset*, found only by running the same detector on the reference wav. If you
  measure this yourself, run that control first.
- ⭐ **The lead is a fixed offset, not a fraction of the commanded time. So your carrier does not
  have to be the same length as your render.** Our carrier is 5.184 s against a 5.1667 s render
  (0.334 % longer). If H3 mapped one duration onto the other, events would land early *in proportion
  to t*: mean 9.2 ms, almost exactly the "~10 ms" an average would report. Tested: the **unscaled**
  carrier cross-correlates **~2x better** than one resampled to the render's length, on **4 of 4**
  takes, at a **constant +5 ms lag**. Write your events at the times you want, in a carrier of
  whatever length is convenient.
- **One prompt family, one carrier, one box.** We cannot tell you it generalises past that.

### ⛔ Two routes that do NOT work: measured, so you can skip them

**The head.** +4.97 dB with per-arm spread 9.87 / 10.83 dB. Noise. H3 fills the head with the line,
so a transient there has no room. Same fact node 1 exploits, seen from the other side.

**A timecode in the prompt.** The prompt format cannot express intra-shot pacing at all. Timecodes
read as shot markers. Five prompt-side levers for pacing, five nulls.

---

## 🔴 The prompt trap that will cost you a scene

Independent of both nodes: there are **two** ways to make H3 generate impact sounds you never
asked for. Both are in the prompt, and one of them is in the *picture* line, which nobody expects.

### 🔴 (a) The picture line must not describe the impact REPEATING

Same subject, same room, same three seeds, clean carrier, nothing placed, and a **bed-only
soundscape byte-identical in every arm**. Only the picture line's verb clause changes:

| picture line's verb clause | per seed | ACCEPT |
|---|--:|--:|
| *"shudder and **chatter** ... **again and again, faster and faster**"* | 6.4 · 22.9 · 22.9 | 1/3 |
| *"shudder and **jolt** ... **again and again, faster and faster**"* | 6.2 · 25.7 · 26.3 | 1/3 |
| ⭐ *"**shudder** as something strikes the trunk from within"* | 7.0 · 7.3 · 6.0 | **3/3** |
| *"taut and motionless"* (floor control) | 7.6 · 5.5 · 7.2 | 3/3 |

⭐ **The repetition is what matters, not the sound-word or the depicted impact.** `chatter` and
`jolt` score identically. The third row depicts an impact and still sits on the floor. Deleting
five words moved two seeds from 22.9 and 25.7 dB down to 7.3 and 6.0.

**This costs you nothing**, because the repetition belongs in the placed carrier, which is where the
rhythm actually comes from.

### 🔴 (b) The soundscape line must not name the impacts

**Naming impacts in `overall_soundscape` makes H3 generate them on its own, loudly, at times you did
not choose.** Same object, same room, same seeds, clean carrier, nothing placed. The *picture*
line is **byte-identical** between the first two rows:

| `overall_soundscape` says | unbidden sound over floor |
|---|--:|
| *"the dull heavy **knock** of something striking the inside of the wooden lid ... **again and again**"* | **19.9 dB** |
| *"the **contact of wood and chain**"* | **10.6 dB** (7.0 / 14.2 by seed) |
| *"the quiet still air of a large empty hall and nothing else"* | **6.8 dB** |

So **depict the impacts in the picture; never name them in the soundscape.** The picture may show all
the violence you like. A separate scene depicting repeated strikes with a restrained soundscape
measured **5.7 dB**, silent.

⚠️ Row 2 is an improvement, not a fix, and it is a **per-seed lottery**. And it is not universal: a
macro of hard metal on concrete whose soundscape *does* name contact sat at 6.7 dB. **Measure it per
scene.** If you place events, screen your null takes.

---

## Install

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/bill-h-lin/comfyui-h3-onset
# no dependencies beyond what ComfyUI already has (torch)
```

Restart ComfyUI. Both nodes appear under **audio/h3**.

## Verify the claims yourself

```bash
python selftest.py
```

It builds carriers in memory and checks the structural claims this README makes about both nodes:
that the prefix guard zeroes exactly the window it says and leaves the tail bit-identical, that the
transient placer writes only inside its windows, that its null is byte-identical outside them, that
out-of-range times are reported rather than silently dropped, and that a 174 ms gap survives. It
does **not** re-run the GPU measurements; those numbers came from the renders cited above.

`example_workflow.json` is a minimal graph with both nodes wired in.

MIT.
