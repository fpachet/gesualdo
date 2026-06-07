#!/usr/bin/env python3
"""Download CPDL MusicXML/MIDI files for Gesualdo works listed on ChoralWiki."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path


BASE_URL = "https://test.cpdl.org"
COMPOSER_PATH = "/wiki/index.php/Carlo_Gesualdo"
COMPOSER_URL = urllib.parse.urljoin(BASE_URL, COMPOSER_PATH)
DOWNLOAD_EXTENSIONS = {".mxl", ".xml", ".musicxml", ".mid", ".midi"}
USER_AGENT = "gesualdo-cpdl-collector/1.0 (+https://cpdl.org/)"


class ComposerPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.current_heading: str | None = None
        self._in_headline = False
        self._headline_text: list[str] = []
        self._anchor: dict[str, str] | None = None
        self._anchor_text: list[str] = []
        self.works: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "span" and attrs_dict.get("class") == "mw-headline":
            self._in_headline = True
            self._headline_text = []
            return
        if tag != "a":
            return

        href = attrs_dict.get("href") or ""
        title = attrs_dict.get("title") or ""
        classes = set((attrs_dict.get("class") or "").split())
        if (
            self._is_work_section()
            and "new" not in classes
            and href.startswith("/wiki/index.php/")
            and "(Carlo_Gesualdo)" in href
            and "redlink=1" not in href
        ):
            self._anchor = {
                "section": self.current_heading or "",
                "href": href,
                "title": title,
            }
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        if self._in_headline:
            self._headline_text.append(data)
        if self._anchor is not None:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "span" and self._in_headline:
            heading = " ".join("".join(self._headline_text).split())
            self.current_heading = heading
            self._in_headline = False
            self._headline_text = []
            return
        if tag == "a" and self._anchor is not None:
            title = " ".join("".join(self._anchor_text).split())
            if title:
                self.works.append({**self._anchor, "title": title})
            self._anchor = None
            self._anchor_text = []

    def _is_work_section(self) -> bool:
        if not self.current_heading:
            return False
        return self.current_heading.startswith(("Sacred works for ", "Secular works for "))


class DownloadLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict[str, str]] = []
        self._pending: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "a":
            href = html.unescape(attrs_dict.get("href") or "")
            path = urllib.parse.urlparse(href).path
            ext = Path(path).suffix.lower()
            if ext in DOWNLOAD_EXTENSIONS:
                self._pending = {"href": href, "title": attrs_dict.get("title") or ""}
                return
        if tag == "img" and self._pending is not None:
            self._pending["icon"] = attrs_dict.get("alt") or attrs_dict.get("src") or ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._pending is not None:
            self.links.append(self._pending)
            self._pending = None


def fetch(url: str, *, retries: int = 3) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def parse_works(page_html: str) -> list[dict[str, str]]:
    parser = ComposerPageParser()
    parser.feed(page_html)
    seen: set[str] = set()
    works: list[dict[str, str]] = []
    for work in parser.works:
        key = urllib.parse.urljoin(BASE_URL, work["href"])
        if key in seen:
            continue
        seen.add(key)
        works.append({**work, "url": key})
    return works


def parse_downloads(page_html: str, work_url: str) -> list[dict[str, str]]:
    music_files = page_html.split('id="General_Information"', 1)[0]
    parser = DownloadLinkParser()
    parser.feed(music_files)
    downloads: list[dict[str, str]] = []
    seen: set[str] = set()
    for link in parser.links:
        url = urllib.parse.urljoin(work_url, link["href"])
        if url in seen:
            continue
        seen.add(url)
        path = urllib.parse.urlparse(url).path
        downloads.append(
            {
                "url": url,
                "source_filename": urllib.parse.unquote(Path(path).name),
                "extension": Path(path).suffix.lower().lstrip("."),
                "title": link.get("title", ""),
                "icon": link.get("icon", ""),
            }
        )
    return downloads


def image_url_from_media_filename(filename: str) -> str:
    filename = filename.replace(" ", "_")
    if filename:
        filename = filename[0].upper() + filename[1:]
    digest = hashlib.md5(filename.encode("utf-8")).hexdigest()
    quoted_filename = urllib.parse.quote(filename)
    return f"{BASE_URL}/wiki/images/{digest[0]}/{digest[:2]}/{quoted_filename}"


def parse_raw_downloads(raw_wikitext: str) -> list[dict[str, str]]:
    downloads: list[dict[str, str]] = []
    seen: set[str] = set()
    music_files = raw_wikitext.split("==General Information==", 1)[0]
    for match in re.finditer(r"\[\[\s*Media:([^|\]\n]+)", music_files):
        filename = html.unescape(match.group(1)).strip().replace(" ", "_")
        if filename:
            filename = filename[0].upper() + filename[1:]
        ext = Path(filename).suffix.lower()
        if ext not in DOWNLOAD_EXTENSIONS:
            continue
        if filename in seen:
            continue
        seen.add(filename)
        downloads.append(
            {
                "url": image_url_from_media_filename(filename),
                "source_filename": filename,
                "extension": ext.lstrip("."),
                "title": filename,
                "icon": "",
            }
        )
    return downloads


def raw_url_for_work(work_url: str) -> str:
    parsed = urllib.parse.urlparse(work_url)
    title = urllib.parse.unquote(Path(parsed.path).name)
    query = urllib.parse.urlencode({"title": title, "action": "raw"})
    return f"{BASE_URL}/wiki/index.php?{query}"


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "_", ascii_text).strip("_").lower()
    return slug or "untitled"


def numbered_filename(
    work_index: int,
    work_title: str,
    download_index: int,
    source_filename: str,
    extension: str,
) -> str:
    source_stem = slugify(Path(source_filename).stem)
    work_slug = slugify(work_title)
    return f"{work_index:03d}_{work_slug}__{download_index:02d}_{source_stem}.{extension}"


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "work_index",
        "section",
        "work_title",
        "work_url",
        "download_index",
        "format",
        "local_path",
        "download_url",
        "source_filename",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def read_manifest(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_errors(path: Path, rows: list[dict[str, str]]) -> None:
    fields = ["work_index", "work_title", "work_url", "download_url", "error"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def process_work(
    output_dir: Path,
    total_works: int,
    work_index: int,
    work: dict[str, str],
) -> tuple[list[dict[str, str]], list[dict[str, str]], str]:
    title = work["title"]
    work_url = work["url"]
    manifest_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []
    try:
        work_html = fetch(work_url).decode("utf-8", errors="replace")
        downloads = parse_downloads(work_html, work_url)
    except Exception as exc:
        try:
            raw_wikitext = fetch(raw_url_for_work(work_url)).decode("utf-8", errors="replace")
            downloads = parse_raw_downloads(raw_wikitext)
        except Exception as raw_exc:
            error_rows.append(
                {
                    "work_index": str(work_index),
                    "work_title": title,
                    "work_url": work_url,
                    "download_url": "",
                    "error": f"{exc}; raw fallback failed: {raw_exc}",
                }
            )
            return manifest_rows, error_rows, f"[{work_index:03d}/{total_works:03d}] {title} - page error"

    if not downloads:
        error_rows.append(
            {
                "work_index": str(work_index),
                "work_title": title,
                "work_url": work_url,
                "download_url": "",
                "error": "no MusicXML or MIDI links found",
            }
        )
        return manifest_rows, error_rows, f"[{work_index:03d}/{total_works:03d}] {title} - no files"

    for download_index, download in enumerate(downloads, start=1):
        local_name = numbered_filename(
            work_index,
            title,
            download_index,
            download["source_filename"],
            download["extension"],
        )
        local_path = output_dir / local_name
        try:
            if not local_path.exists():
                local_path.write_bytes(fetch(download["url"]))
        except Exception as exc:
            error_rows.append(
                {
                    "work_index": str(work_index),
                    "work_title": title,
                    "work_url": work_url,
                    "download_url": download["url"],
                    "error": str(exc),
                }
            )
            continue
        manifest_rows.append(
            {
                "work_index": str(work_index),
                "section": work["section"],
                "work_title": title,
                "work_url": work_url,
                "download_index": str(download_index),
                "format": download["extension"],
                "local_path": str(local_path),
                "download_url": download["url"],
                "source_filename": download["source_filename"],
            }
        )

    return (
        manifest_rows,
        error_rows,
        f"[{work_index:03d}/{total_works:03d}] {title} - {len(manifest_rows)} files",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("data/cpdl"))
    parser.add_argument("--limit", type=int, default=0, help="Limit works for testing.")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent page/file fetches.")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    composer_html = fetch(COMPOSER_URL).decode("utf-8", errors="replace")
    works = parse_works(composer_html)
    if args.limit:
        works = works[: args.limit]

    manifest_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []
    previous_manifest_rows = read_manifest(args.output_dir / "manifest.tsv")

    print(f"Found {len(works)} CPDL Gesualdo vocal work pages.")
    with ThreadPoolExecutor(max_workers=max(args.workers, 1)) as executor:
        futures = [
            executor.submit(process_work, args.output_dir, len(works), work_index, work)
            for work_index, work in enumerate(works, start=1)
        ]
        for future in as_completed(futures):
            work_manifest_rows, work_error_rows, status = future.result()
            print(status, flush=True)
            manifest_rows.extend(work_manifest_rows)
            error_rows.extend(work_error_rows)

    merged_by_path = {row["local_path"]: row for row in previous_manifest_rows}
    merged_by_path.update({row["local_path"]: row for row in manifest_rows})
    manifest_rows = list(merged_by_path.values())
    manifest_rows.sort(key=lambda row: (int(row["work_index"]), int(row["download_index"])))
    error_rows.sort(
        key=lambda row: (
            int(row["work_index"]),
            row["download_url"],
            row["error"],
        )
            )

    write_manifest(args.output_dir / "manifest.tsv", manifest_rows)
    write_errors(args.output_dir / "errors.tsv", error_rows)
    print(
        f"Downloaded {len(manifest_rows)} files. "
        f"Logged {len(error_rows)} work/download issues."
    )
    return 0 if not error_rows else 1


if __name__ == "__main__":
    sys.exit(main())
