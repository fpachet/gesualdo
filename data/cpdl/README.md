# CPDL Gesualdo vocal works

Downloaded from the Carlo Gesualdo composer page on ChoralWiki/CPDL:

https://www.cpdl.org/wiki/index.php/Carlo_Gesualdo

The main CPDL hostname was behind a browser challenge during collection, so the
download script used the public `test.cpdl.org` mirror and raw MediaWiki pages
as a fallback for pages that rendered with HTTP 500.

Contents:

- `*.mxl`, `*.mid`, `*.midi`: MusicXML/MIDI files linked from listed vocal work
  pages.
- `manifest.tsv`: one row per downloaded file, including work title, section,
  CPDL work URL, local path, download URL, and original source filename.
- `errors.tsv`: work pages from the composer page that exposed no direct
  MusicXML/MIDI links at collection time.

Collection summary, 2026-06-07:

- 173 CPDL Gesualdo vocal work pages scanned.
- 397 score files downloaded and validated.
- 7 pages listed in `errors.tsv` had no direct MusicXML/MIDI links.
