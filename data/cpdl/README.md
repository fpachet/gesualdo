# CPDL Gesualdo vocal works

Downloaded from the Carlo Gesualdo composer page on ChoralWiki/CPDL:

https://www.cpdl.org/wiki/index.php/Carlo_Gesualdo

The main CPDL hostname was behind a browser challenge during collection, so the
download script used the public `test.cpdl.org` mirror and raw MediaWiki pages
as a fallback for pages that rendered with HTTP 500.

Contents:

- `{4,5,6,7}-voices/sources/`: MusicXML/MIDI files linked from listed vocal
  work pages, split by source voice count.
- `5-voices/reductions/string_quartet/`: supported five-voice string quartet
  reductions.
- `5-voices/renders/string_quartet_mp3/`: MuseScore MP3 renders for those
  quartet reductions.
- `5-voices/reductions/string_quartet_plus_viole/`: restored five-voice
  string quartet plus viole d'amour reductions.
- `5-voices/renders/string_quartet_plus_viole_mp3/`: MuseScore MP3 renders for
  those five-instrument reductions.
- `6-voices/reductions/string_quartet/`: supported six-voice string quartet
  reductions using the separate `six_voice_quartet` reducer mode.
- `6-voices/renders/string_quartet_mp3/`: MuseScore MP3 renders for those
  quartet reductions.
- `manifest.tsv`: one row per downloaded file, including work title, section,
  CPDL work URL, local path, download URL, and original source filename.
- `errors.tsv`: work pages from the composer page that exposed no direct
  MusicXML/MIDI links at collection time.

Collection summary, 2026-06-07:

- 173 CPDL Gesualdo vocal work pages scanned.
- 397 score files downloaded and validated.
- 7 pages listed in `errors.tsv` had no direct MusicXML/MIDI links.
- 123 five-voice works reduced to string quartet.
- 123 five-voice string quartet MP3 renders.
- 122 five-voice works reduced to string quartet plus viole d'amour.
- 122 five-voice quartet plus viole d'amour MP3 renders.
- 34 six-voice works reduced to string quartet.
- 34 six-voice string quartet MP3 renders.
