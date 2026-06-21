# Tier 1 Key-Signature Transposition Comparison

This folder contains the first-tier recomputation from the global-transposition
key-signature audit.

Selection rule:
- source row status: `attention`
- cleaner-key candidate exists
- `tessitura_delta <= 0.01`

Generated set:
- 52 comparison pairs
- 20 CPDL five-voice string-quartet reductions
- 20 CPDL five-voice quartet-plus-viole reductions
- 7 CPDL six-voice string-quartet reductions
- 5 KdF string-quartet reductions

Layout:
- `*/original/`: snapshot copy of the current MusicXML reduction
- `*/alternative/`: recomputed MusicXML using the cleaner-key transposition
- `manifest.tsv`: one row per comparison pair, linking source, current output,
  original snapshot, alternative output, transpositions, key-burden scores, and
  tessitura scores

The source reductions under `data/` were not overwritten.
