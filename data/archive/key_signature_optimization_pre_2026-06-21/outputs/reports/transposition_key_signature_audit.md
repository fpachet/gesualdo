# Global Transposition Key-Signature Audit

This audit checks whether a nearby global transposition would materially reduce the printed key-signature burden while preserving the current instrumental tessitura fit.

Method:
- Candidate window: current transposition +/- 5 semitones.
- Key-signature burden: duration-weighted average of `abs(sharps)` after transposition; lower is easier.
- Tessitura guard: reuse the reducer's existing `score_global_transposition` range/register score.
- A candidate is allowed when its tessitura score is no worse than the current score by max(0.05, 0.1 relative).
- A piece is flagged when the allowed candidate improves key burden by at least 2 and 40%.

## Status Counts

| Status | Count |
| --- | --- |
| attention | 75 |
| no_key_signature_data | 7 |
| ok | 234 |
| source_status_error | 15 |

## Counts By Batch

| Batch | Attention | OK | Other |
| --- | ---: | ---: | ---: |
| cpdl_5_voice_quartet_plus_viole | 43 | 79 | 8 |
| cpdl_5_voice_string_quartet | 18 | 105 | 7 |
| cpdl_6_voice_string_quartet | 6 | 21 | 7 |
| kdf_string_quartet | 8 | 29 | 0 |

## Largest Attention Cases (Top 40)

| Batch | Work | Title | Current | Current burden | Candidate | Candidate burden | Delta | Tessitura delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kdf_string_quartet | VI 3. Tu piangi, o filli mia | 3. Tu piangi, o filli mia | 1 | 6 | 0 | 1 | 5 | 0.0230712 |
| kdf_string_quartet | VI 11. Alme dAmor rubelle | 11. Alme dAmor rubelle | -1 | 5 | 0 | 0 | 5 | 0.033702 |
| kdf_string_quartet | VI 13. Ardita Zanzaretta | 13. Ardita Zanzaretta | 1 | 5 | 0 | 0 | 5 | 0.0433668 |
| cpdl_5_voice_string_quartet | 63 | Alme d'Amor rubelle | -1 | 5 | 0 | 0 | 5 | 0.033702 |
| cpdl_5_voice_string_quartet | 64 | Amor pace non chero | -1 | 5 | 0 | 0 | 5 | 0.0250491 |
| cpdl_5_voice_string_quartet | 69 | Ardita zanzaretta | 1 | 5 | 0 | 0 | 5 | 0.0433668 |
| cpdl_5_voice_string_quartet | 71 | Asciugate i begli occhi | 1 | 6 | 0 | 1 | 5 | 0.0280921 |
| cpdl_5_voice_string_quartet | 105 | Io tacerò | 1 | 6 | 2 | 1 | 5 | 0.0447791 |
| cpdl_5_voice_string_quartet | 132 | O mal nati messagi | -1 | 5 | 0 | 0 | 5 | 0.0430596 |
| cpdl_5_voice_quartet_plus_viole | 6 | Domine ne despicias | 6 | 6 | 7 | 1 | 5 | 0.0378557 |
| cpdl_5_voice_quartet_plus_viole | 7 | Exaudi Deus | 6 | 6 | 5 | 1 | 5 | 0.0433873 |
| cpdl_5_voice_quartet_plus_viole | 12 | O Crux benedicta | 1 | 5 | 0 | 0 | 5 | 0.0240724 |
| cpdl_5_voice_quartet_plus_viole | 14 | Peccantem me quotidie | 6 | 5 | 7 | 0 | 5 | 0.0312112 |
| cpdl_5_voice_quartet_plus_viole | 16 | Reminiscere | 6 | 5 | 7 | 0 | 5 | 0.0392101 |
| cpdl_5_voice_quartet_plus_viole | 18 | Tribularer si nescirem | 1 | 5 | 0 | 0 | 5 | 0.0339521 |
| cpdl_5_voice_quartet_plus_viole | 20 | Venit lumen tuum | 4 | 6 | 3 | 1 | 5 | 0.0222873 |
| cpdl_5_voice_quartet_plus_viole | 60 | Al mio gioir il ciel si fa sereno | 1 | 6 | 0 | 1 | 5 | 0.0207791 |
| cpdl_5_voice_quartet_plus_viole | 68 | Arde il mio cor | 1 | 5 | 0 | 0 | 5 | 0.0211759 |
| cpdl_5_voice_quartet_plus_viole | 75 | Candida man qual neve | 1 | 5 | 0 | 0 | 5 | 0.0245591 |
| cpdl_5_voice_quartet_plus_viole | 76 | Candido e verde fiore | 1 | 5 | 0 | 0 | 5 | 0.0485013 |
| cpdl_5_voice_quartet_plus_viole | 87 | Deh coprite il bel seno | 1 | 5 | 0 | 0 | 5 | 0.0305395 |
| cpdl_5_voice_quartet_plus_viole | 98 | Gelo ha madonna il seno | 6 | 5 | 7 | 0 | 5 | 0.0486276 |
| cpdl_5_voice_quartet_plus_viole | 102 | In più leggiadro velo | 1 | 6 | 0 | 1 | 5 | 0.0202586 |
| cpdl_5_voice_quartet_plus_viole | 107 | Languisce al fin chi da la vita parte | 1 | 5 | 0 | 0 | 5 | 0.0215408 |
| cpdl_5_voice_quartet_plus_viole | 115 | Mentre madonna il lasso fianco posa | 1 | 5 | 0 | 0 | 5 | 0.0498608 |
| cpdl_5_voice_quartet_plus_viole | 121 | Moro, lasso, al mio duolo | 1 | 5 | 0 | 0 | 5 | 0.0263397 |
| cpdl_5_voice_quartet_plus_viole | 143 | Quel 'no' crudel che la mia speme ancise | 1 | 5 | 0 | 0 | 5 | 0.0207676 |
| cpdl_5_voice_quartet_plus_viole | 149 | Se così dolce è il duolo | 6 | 5 | 7 | 0 | 5 | 0.0209797 |
| cpdl_5_voice_quartet_plus_viole | 158 | Sento che nel partire | 6 | 6 | 5 | 1 | 5 | 0.0271295 |
| cpdl_5_voice_quartet_plus_viole | 163 | T'amo, mia vita | 1 | 6 | 2 | 1 | 5 | 0.0227022 |
| cpdl_5_voice_quartet_plus_viole | 171 | Volan quasi farfalle | 1 | 6 | 0 | 1 | 5 | 0.0274933 |
| kdf_string_quartet | IV 1. Luci serena e chiare | 1. Luci serena e chiare | -1 | 4 | 0 | 1 | 3 | 0.0363202 |
| kdf_string_quartet | IV 2. Tallor sano desio | 2. Tallor sano desio | -1 | 4 | 0 | 1 | 3 | 0.0421938 |
| kdf_string_quartet | VI 18. Volan quasi farfalle | 18. Volan quasi farfalle | -1 | 4 | 0 | 1 | 3 | 0.040696 |
| cpdl_5_voice_string_quartet | 77 | Caro amoroso neo | -1 | 4 | 0 | 1 | 3 | 0.0260181 |
| cpdl_5_voice_string_quartet | 111 | Ma se tale ha costei | -1 | 4 | 0 | 1 | 3 | 0.0370602 |
| cpdl_5_voice_string_quartet | 124 | Non mi toglia il ben mio | -1 | 4 | 0 | 1 | 3 | 0.0466474 |
| cpdl_5_voice_string_quartet | 136 | Occhi del mio cor vita | 1 | 5 | 2 | 2 | 3 | 0.0233044 |
| cpdl_5_voice_string_quartet | 141 | Quando ridente e bella | -1 | 4 | 0 | 1 | 3 | 0.0448604 |
| cpdl_5_voice_string_quartet | 164 | Tall'or sano desio | -1 | 4 | 0 | 1 | 3 | 0.0421938 |

Full per-piece results are in `transposition_key_signature_audit.tsv`; all candidate scores are in `transposition_key_signature_candidates.tsv`.
