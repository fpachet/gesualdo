# Optimal transport animation

`optimal_transport_6_to_4.py` is a compact Manim Community scene explaining
six-voice-to-string-quartet reduction as **partial optimal transport**: four
source notes are assigned to four instrumental slots, while two harmonically
redundant notes pay an explicit omission cost.

The visual reflects the reducer's real musical priorities:

- preserve the highest and lowest active source voices;
- prefer target registers with small melodic motion;
- avoid voice crossings;
- retain distinct pitch classes rather than doublings.

It also exposes the combinatorial search: one chord has
`binomial(6, 4) * 4! = 360` labelled assignments. The animation tries and
backtracks from a crossing solution and a harmonically lossy solution before
accepting the lowest-cost partial matching. Eight independent chord slices
would already create about `2.8e20` naive assignment sequences, motivating
local pruning and continuity-aware search.

The notation view is deliberately persistent: the six source mini-staves stay
fixed on the left, while copied notes enter the four-part working score on the
right for every candidate. Rejected notes travel back to their source staves;
the accepted four-note score remains in place.

## Render

Install Manim Community, then run from the repository root:

```bash
# Fast preview
manim -pql animations/optimal_transport_6_to_4.py OptimalTransportScoreReduction

# 1080p final
manim -pqh animations/optimal_transport_6_to_4.py OptimalTransportScoreReduction

# Lightweight GIF
manim --format=gif -ql animations/optimal_transport_6_to_4.py OptimalTransportScoreReduction
```

The scene uses only Manim primitives and `MathTex`; it has no external image or
music-font assets.

## Actual one-bar notation version

`actual_score_transport.py` uses engraved SVG notation generated from real
MusicXML. The complete six-voice bar stays fixed on the left while the
four-staff reduction on the right morphs through two rejected candidates and
the accepted solution. Colored first-beat arrows retain note-level provenance:
they connect exact source noteheads to their destination noteheads, disappear
during backtracking, and are redrawn for the next candidate.

The concluding section defines the total cost as a weighted sum over a declared
rule set (outer-voice preservation, crossing, harmony, register, continuity,
and omission), shows the winning penalties summing to `4.2`, and states the
precise claim: the result is optimal under those rules and weights.

```bash
uv run --with pillow python animations/generate_actual_score_assets.py
manim -pqm animations/actual_score_transport.py ActualScoreTransport
```

The generated MusicXML and SVG files live in `animations/assets/actual_score/`;
the transparent PNG renderings are stored beside them. Verovio, Pillow, and
macOS Quick Look are needed only when regenerating the assets.
