# Obvious Key-Signature Transposition Updates

This folder documents the in-place cleaner-key update applied to the checked-in
MusicXML and MP3 reduction corpus.

Selection rule:
- source audit row status: `attention`
- cleaner-key candidate exists
- `tessitura_delta <= 0.02`

Generated set:
- 90 updated reductions
- 42 CPDL five-voice quartet-plus-viole reductions
- 30 CPDL five-voice string-quartet reductions
- 9 CPDL six-voice string-quartet reductions
- 9 KdF string-quartet reductions

Layout:
- `*/original/`: MusicXML snapshots before the in-place update
- `*/updated/`: MusicXML snapshots after the in-place update
- `*/original_mp3/`: MP3 snapshots before rerendering
- `*/updated_mp3/`: MP3 snapshots after rerendering
- `manifest.tsv`: one row per updated score, linking source, updated data path,
  MP3 path, snapshots, old/new transpositions, key-burden scores, and
  tessitura scores

The active corpus under `data/` now points at the updated MusicXML and MP3
versions. The snapshots here preserve side-by-side comparison material.
