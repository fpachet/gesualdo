# Quartet Part-Coherence Audit

This audit flags likely awkward reading spots in generated MusicXML reductions. It is intentionally observational: it does not rewrite the music.

Checks:
- `register_jump`: melodic movement of at least the configured interval between successive written events in the same part.
- `sparse_fragment`: a short island of notes after or before a long silence.
- `sparse_window`: very low participation density over a multi-bar window.
- `dangling_tie`, `dangling_slur`, `accidental_on_tie_continuation`: conservative notation-structure flags.

## Issue Counts

| Kind | Count |
| --- | ---: |
| accidental_on_tie_continuation | 1954 |
| dangling_tie | 2451 |
| register_jump | 8392 |
| sparse_fragment | 119 |
| sparse_window | 55 |

## Parse Issues

| Batch | Work | Title | Status | Note |
| --- | --- | --- | --- | --- |
| cpdl_5_voice_string_quartet | 59 | Ahi, dispietata e cruda | source_status_error | data/cpdl/059_ahi_dispietata_e_cruda__01_gesualdo_ahi_dispietata_e_cruda.mxl: reduction failed: Violin I has overlapping source events near measure 6: p0:e9 |
| cpdl_5_voice_string_quartet | 85 | Crudelissima doglia | source_status_error | data/cpdl/085_crudelissima_doglia__01_gesualdo_crudelissima_doglia.mxl: reduction failed: Violoncello has overlapping source events near measure 11: p4:e20 |
| cpdl_5_voice_string_quartet | 89 | Deh, se già fu crudele | source_status_error | data/cpdl/089_deh_se_gia_fu_crudele__01_gesualdo_deh_se_gia_fu_crudele.mxl: reduction failed: Violin I has overlapping source events near measure 18: p0:e45 |
| cpdl_5_voice_string_quartet | 108 | Languisce e moro, ahi, cruda | source_status_error | data/cpdl/108_languisce_e_moro_ahi_cruda__01_gesualdo_languisce_e_moro_ahi_cruda.mxl: reduction failed: Violin I has overlapping source events near measure 17: p0:e17 |
| cpdl_5_voice_string_quartet | 126 | Non t'amo, o voce ingrata | source_status_error | data/cpdl/126_non_t_amo_o_voce_ingrata__01_gesualdo_non_t_amo_o_voce_ingrata.mxl: reduction failed: Violin I has overlapping source events near measure 6: p0:e7 |
| cpdl_5_voice_string_quartet | 157 | Se vi miro pietosa | source_status_error | data/cpdl/157_se_vi_miro_pietosa__01_gesualdo_se_vi_miro_pietosa.mxl: reduction failed: Violin I has overlapping source events near measure 21: p0:e51 |
| cpdl_5_voice_string_quartet | 169 | Veggio sì, dal mio sole | source_status_error | data/cpdl/169_veggio_si_dal_mio_sole__01_gesualdo_veggio_si_dal_mio_sole.mxl: reduction failed: Violoncello has overlapping source events near measure 18: p4:e42 |
| cpdl_5_voice_quartet_plus_viole | 13 | O vos omnes (1603) | source_status_error | data/cpdl/5-voices/sources/013_o_vos_omnes_1603__04_o_vos_omnes_gesualdo.mxl: expected 5 parts, found 7; data/cpdl/5-voices/sources/013_o_vos_omnes_1603__06_ws_gesu_vos.mxl: expected 5 parts, found 7; data/cpdl/5-voices/sources/013_o_vos_omnes_1603__01_gesualdo_ovosomnes.mid: expected 5 parts, found 11; data/cpdl/5-voices/sources/013_o_vos_omnes_1603__03_o_vos_omnes_gesualdo.mid: expected 5 parts, found 6; data/cpdl/5-voices/sources/013_o_vos_omnes_1603__05_ws_gesu_vos.mid: expected 5 parts, found 1; data/cpdl/5-voices/sources/013_o_vos_omnes_1603__02_gesualdo_ovosomnes.mxl: reduction failed: Violin I has overlapping source events near measure 11: p0:e20 |
| cpdl_5_voice_quartet_plus_viole | 59 | Ahi, dispietata e cruda | source_status_error | data/cpdl/5-voices/sources/059_ahi_dispietata_e_cruda__01_gesualdo_ahi_dispietata_e_cruda.mxl: reduction failed: Violin I has overlapping source events near measure 6: p0:e9 |
| cpdl_5_voice_quartet_plus_viole | 85 | Crudelissima doglia | source_status_error | data/cpdl/5-voices/sources/085_crudelissima_doglia__01_gesualdo_crudelissima_doglia.mxl: reduction failed: Violin II has overlapping source events near measure 13: p1:e36 |
| cpdl_5_voice_quartet_plus_viole | 89 | Deh, se già fu crudele | source_status_error | data/cpdl/5-voices/sources/089_deh_se_gia_fu_crudele__01_gesualdo_deh_se_gia_fu_crudele.mxl: reduction failed: Violin I has overlapping source events near measure 18: p0:e45 |
| cpdl_5_voice_quartet_plus_viole | 108 | Languisce e moro, ahi, cruda | source_status_error | data/cpdl/5-voices/sources/108_languisce_e_moro_ahi_cruda__01_gesualdo_languisce_e_moro_ahi_cruda.mxl: reduction failed: Violin I has overlapping source events near measure 17: p0:e17 |
| cpdl_5_voice_quartet_plus_viole | 126 | Non t'amo, o voce ingrata | source_status_error | data/cpdl/5-voices/sources/126_non_t_amo_o_voce_ingrata__01_gesualdo_non_t_amo_o_voce_ingrata.mxl: reduction failed: Violin I has overlapping source events near measure 6: p0:e7 |
| cpdl_5_voice_quartet_plus_viole | 157 | Se vi miro pietosa | source_status_error | data/cpdl/5-voices/sources/157_se_vi_miro_pietosa__01_gesualdo_se_vi_miro_pietosa.mxl: reduction failed: Violin I has overlapping source events near measure 21: p0:e51 |
| cpdl_5_voice_quartet_plus_viole | 169 | Veggio sì, dal mio sole | source_status_error | data/cpdl/5-voices/sources/169_veggio_si_dal_mio_sole__01_gesualdo_veggio_si_dal_mio_sole.mxl: reduction failed: Violin II has overlapping source events near measure 22: p1:e55 |

## Counts By Batch

| Batch | Kind | Count |
| --- | --- | ---: |
| cpdl_5_voice_quartet_plus_viole | accidental_on_tie_continuation | 257 |
| cpdl_5_voice_quartet_plus_viole | dangling_tie | 191 |
| cpdl_5_voice_quartet_plus_viole | register_jump | 1091 |
| cpdl_5_voice_quartet_plus_viole | sparse_fragment | 109 |
| cpdl_5_voice_quartet_plus_viole | sparse_window | 34 |
| cpdl_5_voice_string_quartet | accidental_on_tie_continuation | 862 |
| cpdl_5_voice_string_quartet | dangling_tie | 1184 |
| cpdl_5_voice_string_quartet | register_jump | 3898 |
| cpdl_5_voice_string_quartet | sparse_fragment | 9 |
| cpdl_5_voice_string_quartet | sparse_window | 21 |
| cpdl_6_voice_string_quartet | accidental_on_tie_continuation | 316 |
| cpdl_6_voice_string_quartet | dangling_tie | 551 |
| cpdl_6_voice_string_quartet | register_jump | 1706 |
| kdf_string_quartet | accidental_on_tie_continuation | 297 |
| kdf_string_quartet | dangling_tie | 402 |
| kdf_string_quartet | register_jump | 1339 |
| take6_string_quartet_double_stops | accidental_on_tie_continuation | 222 |
| take6_string_quartet_double_stops | dangling_tie | 123 |
| take6_string_quartet_double_stops | register_jump | 358 |
| take6_string_quartet_double_stops | sparse_fragment | 1 |

## Counts By Part

| Part | Kind | Count |
| --- | --- | ---: |
| Viola | accidental_on_tie_continuation | 629 |
| Viola | dangling_tie | 938 |
| Viola | register_jump | 1667 |
| Viola | sparse_fragment | 17 |
| Viola | sparse_window | 11 |
| Viole d'amour | accidental_on_tie_continuation | 49 |
| Viole d'amour | dangling_tie | 46 |
| Viole d'amour | register_jump | 239 |
| Viole d'amour | sparse_fragment | 10 |
| Viole d'amour | sparse_window | 3 |
| Violin I | accidental_on_tie_continuation | 321 |
| Violin I | dangling_tie | 259 |
| Violin I | register_jump | 2049 |
| Violin I | sparse_fragment | 25 |
| Violin I | sparse_window | 6 |
| Violin II | accidental_on_tie_continuation | 692 |
| Violin II | dangling_tie | 987 |
| Violin II | register_jump | 1430 |
| Violin II | sparse_fragment | 17 |
| Violin II | sparse_window | 10 |
| Violoncello | accidental_on_tie_continuation | 263 |
| Violoncello | dangling_tie | 221 |
| Violoncello | register_jump | 3007 |
| Violoncello | sparse_fragment | 50 |
| Violoncello | sparse_window | 25 |

## Highest Priority Examples (Top 60)

| Severity | Kind | Batch | Work | Title | Part | Measure | Detail |
| --- | --- | --- | --- | --- | --- | --- | --- |
| high | sparse_window | cpdl_5_voice_quartet_plus_viole | 116 | Mentre, mia stella, miri | Viola | 57 | 1 attacks, 0.1875 ql in 4-bar window |
| high | sparse_window | cpdl_5_voice_quartet_plus_viole | 116 | Mentre, mia stella, miri | Violoncello | 57 | 1 attacks, 0.25 ql in 4-bar window |
| high | sparse_window | cpdl_5_voice_quartet_plus_viole | 150 | Se da sì nobil mano | Viola | 45 | 1 attacks, 0.25 ql in 4-bar window |
| high | sparse_window | cpdl_5_voice_quartet_plus_viole | 150 | Se da sì nobil mano | Viole d'amour | 45 | 1 attacks, 0.25 ql in 4-bar window |
| high | sparse_window | cpdl_5_voice_quartet_plus_viole | 150 | Se da sì nobil mano | Violoncello | 24 | 1 attacks, 0.75 ql in 4-bar window |
| high | sparse_window | cpdl_5_voice_quartet_plus_viole | 150 | Se da sì nobil mano | Violoncello | 45 | 1 attacks, 0.25 ql in 4-bar window |
| high | sparse_window | cpdl_5_voice_quartet_plus_viole | 162 | Sì gioioso mi fanno i dolor miei | Violoncello | 65 | 2 attacks, 0.3125 ql in 4-bar window |
| high | sparse_window | cpdl_5_voice_quartet_plus_viole | 62 | All'apparir di quelle luci ardenti | Violin II | 57 | 1 attacks, 0.125 ql in 4-bar window |
| high | sparse_window | cpdl_5_voice_quartet_plus_viole | 72 | Baci soavi e cari | Violin II | 86 | 2 attacks, 0.625 ql in 4-bar window |
| high | sparse_window | cpdl_5_voice_quartet_plus_viole | 77 | Caro amoroso neo | Violin I | 45 | 1 attacks, 0.125 ql in 4-bar window |
| high | sparse_window | cpdl_5_voice_quartet_plus_viole | 77 | Caro amoroso neo | Violoncello | 89 | 1 attacks, 0.25 ql in 4-bar window |
| high | sparse_window | cpdl_5_voice_quartet_plus_viole | 90 | Del bel de bei vostri occhi | Viole d'amour | 69 | 1 attacks, 0.125 ql in 4-bar window |
| high | sparse_window | cpdl_5_voice_quartet_plus_viole | 90 | Del bel de bei vostri occhi | Violin II | 69 | 1 attacks, 0.125 ql in 4-bar window |
| high | sparse_window | cpdl_5_voice_quartet_plus_viole | 90 | Del bel de bei vostri occhi | Violoncello | 65 | 1 attacks, 0.1875 ql in 4-bar window |
| high | sparse_window | cpdl_5_voice_quartet_plus_viole | 93 | Dolcissimo sospiro | Violin I | 69 | 1 attacks, 0.0625 ql in 4-bar window |
| high | sparse_window | cpdl_5_voice_quartet_plus_viole | 96 | Felice primavera | Violoncello | 85 | 1 attacks, 0.125 ql in 4-bar window |
| high | sparse_fragment | cpdl_5_voice_quartet_plus_viole | 97 | Felicissimo sonno | Violoncello | 21 | 1 attacks, 4 ql after/before long silence |
| high | register_jump | cpdl_5_voice_string_quartet | 10 | Laboravi in gemitu meo | Violin I | 35 | 25 semitones from MIDI 61 to 86 |
| high | register_jump | cpdl_5_voice_string_quartet | 10 | Laboravi in gemitu meo | Violin I | 44 | 19 semitones from MIDI 83 to 64 |
| high | register_jump | cpdl_5_voice_string_quartet | 10 | Laboravi in gemitu meo | Violoncello | 7 | 19 semitones from MIDI 43 to 62 |
| high | register_jump | cpdl_5_voice_string_quartet | 10 | Laboravi in gemitu meo | Violoncello | 14 | 19 semitones from MIDI 48 to 67 |
| high | register_jump | cpdl_5_voice_string_quartet | 100 | Già piansi nel dolore | Viola | 31 | 19 semitones from MIDI 48 to 67 |
| high | register_jump | cpdl_5_voice_string_quartet | 100 | Già piansi nel dolore | Violin I | 34 | 22 semitones from MIDI 59 to 81 |
| high | register_jump | cpdl_5_voice_string_quartet | 100 | Già piansi nel dolore | Violoncello | 46 | 29 semitones from MIDI 43 to 72 |
| high | register_jump | cpdl_5_voice_string_quartet | 100 | Già piansi nel dolore | Violoncello | 46 | 29 semitones from MIDI 72 to 43 |
| high | register_jump | cpdl_5_voice_string_quartet | 100 | Già piansi nel dolore | Violoncello | 50 | 21 semitones from MIDI 43 to 64 |
| high | register_jump | cpdl_5_voice_string_quartet | 101 | Hai rotto e sciolto e spento | Violin I | 17 | 19 semitones from MIDI 59 to 78 |
| high | register_jump | cpdl_5_voice_string_quartet | 101 | Hai rotto e sciolto e spento | Violoncello | 14 | 21 semitones from MIDI 66 to 45 |
| high | register_jump | cpdl_5_voice_string_quartet | 101 | Hai rotto e sciolto e spento | Violoncello | 20 | 19 semitones from MIDI 64 to 45 |
| high | register_jump | cpdl_5_voice_string_quartet | 102 | In più leggiadro velo | Violin I | 46 | 22 semitones from MIDI 82 to 60 |
| high | register_jump | cpdl_5_voice_string_quartet | 102 | In più leggiadro velo | Violin I | 46 | 21 semitones from MIDI 81 to 60 |
| high | register_jump | cpdl_5_voice_string_quartet | 102 | In più leggiadro velo | Violoncello | 8 | 22 semitones from MIDI 67 to 45 |
| high | register_jump | cpdl_5_voice_string_quartet | 102 | In più leggiadro velo | Violoncello | 26 | 20 semitones from MIDI 50 to 70 |
| high | register_jump | cpdl_5_voice_string_quartet | 103 | Io parto, e non più dissi | Violin I | 56 | 19 semitones from MIDI 57 to 76 |
| high | register_jump | cpdl_5_voice_string_quartet | 103 | Io parto, e non più dissi | Violoncello | 42 | 31 semitones from MIDI 40 to 71 |
| high | register_jump | cpdl_5_voice_string_quartet | 103 | Io parto, e non più dissi | Violoncello | 42 | 19 semitones from MIDI 71 to 52 |
| high | register_jump | cpdl_5_voice_string_quartet | 104 | Io pur respiro in così gran dolore | Violin I | 9 | 19 semitones from MIDI 83 to 64 |
| high | register_jump | cpdl_5_voice_string_quartet | 104 | Io pur respiro in così gran dolore | Violin I | 10 | 24 semitones from MIDI 62 to 86 |
| high | register_jump | cpdl_5_voice_string_quartet | 104 | Io pur respiro in così gran dolore | Violoncello | 3 | 19 semitones from MIDI 71 to 52 |
| high | register_jump | cpdl_5_voice_string_quartet | 105 | Io tacerò | Violin I | 7 | 20 semitones from MIDI 84 to 64 |
| high | register_jump | cpdl_5_voice_string_quartet | 105 | Io tacerò | Violoncello | 33 | 19 semitones from MIDI 48 to 67 |
| high | register_jump | cpdl_5_voice_string_quartet | 106 | Itene o miei sospiri | Violin II | 41 | 19 semitones from MIDI 58 to 77 |
| high | register_jump | cpdl_5_voice_string_quartet | 106 | Itene o miei sospiri | Violoncello | 5 | 24 semitones from MIDI 67 to 43 |
| high | register_jump | cpdl_5_voice_string_quartet | 106 | Itene o miei sospiri | Violoncello | 40 | 19 semitones from MIDI 46 to 65 |
| high | register_jump | cpdl_5_voice_string_quartet | 107 | Languisce al fin chi da la vita parte | Violin II | 31 | 24 semitones from MIDI 55 to 79 |
| high | register_jump | cpdl_5_voice_string_quartet | 109 | Luci serene e chiare | Violoncello | 12 | 28 semitones from MIDI 44 to 72 |
| high | register_jump | cpdl_5_voice_string_quartet | 11 | Maria, mater gratiae | Violin I | 21 | 20 semitones from MIDI 56 to 76 |
| high | register_jump | cpdl_5_voice_string_quartet | 11 | Maria, mater gratiae | Violin I | 45 | 20 semitones from MIDI 57 to 77 |
| high | register_jump | cpdl_5_voice_string_quartet | 11 | Maria, mater gratiae | Violoncello | 4 | 20 semitones from MIDI 47 to 67 |
| high | register_jump | cpdl_5_voice_string_quartet | 11 | Maria, mater gratiae | Violoncello | 11 | 26 semitones from MIDI 45 to 71 |
| high | register_jump | cpdl_5_voice_string_quartet | 11 | Maria, mater gratiae | Violoncello | 11 | 20 semitones from MIDI 71 to 51 |
| high | register_jump | cpdl_5_voice_string_quartet | 11 | Maria, mater gratiae | Violoncello | 11 | 21 semitones from MIDI 64 to 43 |
| high | register_jump | cpdl_5_voice_string_quartet | 11 | Maria, mater gratiae | Violoncello | 29 | 20 semitones from MIDI 67 to 47 |
| high | register_jump | cpdl_5_voice_string_quartet | 110 | Ma se avverrà ch'io moia | Violin I | 9 | 20 semitones from MIDI 84 to 64 |
| high | register_jump | cpdl_5_voice_string_quartet | 110 | Ma se avverrà ch'io moia | Violin II | 11 | 24 semitones from MIDI 79 to 55 |
| high | register_jump | cpdl_5_voice_string_quartet | 110 | Ma se avverrà ch'io moia | Violoncello | 16 | 20 semitones from MIDI 40 to 60 |
| high | register_jump | cpdl_5_voice_string_quartet | 110 | Ma se avverrà ch'io moia | Violoncello | 20 | 19 semitones from MIDI 69 to 50 |
| high | register_jump | cpdl_5_voice_string_quartet | 110 | Ma se avverrà ch'io moia | Violoncello | 21 | 19 semitones from MIDI 64 to 45 |
| high | register_jump | cpdl_5_voice_string_quartet | 110 | Ma se avverrà ch'io moia | Violoncello | 32 | 19 semitones from MIDI 69 to 50 |
| high | register_jump | cpdl_5_voice_string_quartet | 110 | Ma se avverrà ch'io moia | Violoncello | 33 | 19 semitones from MIDI 64 to 45 |

Full issue rows are in `part_coherence_audit.tsv`.
