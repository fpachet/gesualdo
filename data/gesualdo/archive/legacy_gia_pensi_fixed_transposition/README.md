# Legacy Gia Pensi Fixed-Transposition Files

These files are older single-piece experiments for Gesualdo VI/22, "Gia piansi
nel dolore".

They are kept here to avoid confusing them with the current Kunst der Fuge
batch reductions under `data/gesualdo/kdf_*`.

The archived standalone MIDI duplicate:

```text
gesualdo_vi_libro_madrigali_22.mid
```

is the same source material as:

```text
data/gesualdo/kdf_madrigals/gesualdo_vi_libro_madrigali_22_(c)icking-archive.mid
```

The legacy quartet MusicXML files were generated with the older fixed
transposition workflow, using `SEMITONES = -9`. The current KdF quartet batch
uses adaptive target-aware transposition; for VI/22 it reports
`chosen_semitones = 0` in:

```text
data/gesualdo/kdf_reductions_report.tsv
```
