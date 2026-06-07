const RAW_BASE = "https://raw.githubusercontent.com/fpachet/gesualdo/main/";
const ASSET_VERSION = "2026-06-07-source-selectors";
const STORAGE_KEY = "gesualdo-quartet-review-v1";
const VEROVIO_SCRIPT_URL = "https://www.verovio.org/javascript/latest/verovio-toolkit-wasm.js";
const SCORE_RENDER_OPTIONS = {
  inputFrom: "xml",
  breaks: "auto",
  scale: 32,
  pageWidth: 1700,
  pageHeight: 2200,
  adjustPageHeight: true,
  footer: "none",
  svgViewBox: true,
};

const SOURCE_LABELS = {
  kdf: "Kunst der Fuge",
  cpdl: "CPDL",
};
const TARGET_LABELS = {
  string_quartet: "String quartet",
  string_quartet_plus_viole: "Quartet + viole",
};
const DATASETS = [
  {
    source: "kdf",
    voiceCount: 5,
    target: "string_quartet",
    report: "data/kdf/reductions/string_quartet_report.tsv",
    hasAudio: true,
  },
  {
    source: "cpdl",
    voiceCount: 5,
    target: "string_quartet",
    report: "data/cpdl/5-voices/reductions/string_quartet/report.tsv",
  },
  {
    source: "cpdl",
    voiceCount: 5,
    target: "string_quartet_plus_viole",
    report: "data/cpdl/5-voices/reductions/string_quartet_plus_viole/report.tsv",
  },
  {
    source: "cpdl",
    voiceCount: 6,
    target: "string_quartet",
    report: "data/cpdl/6-voices/reductions/string_quartet/report.tsv",
  },
];

let CATALOG = [];

const elements = {
  audio: document.getElementById("player"),
  search: document.getElementById("search"),
  sourceSelect: document.getElementById("sourceSelect"),
  voiceSelect: document.getElementById("voiceSelect"),
  targetSelect: document.getElementById("targetSelect"),
  groupSelect: document.getElementById("groupSelect"),
  sort: document.getElementById("sort"),
  pieceList: document.getElementById("pieceList"),
  visibleCount: document.getElementById("visibleCount"),
  audioCount: document.getElementById("audioCount"),
  partCount: document.getElementById("partCount"),
  selectedBook: document.getElementById("selectedBook"),
  selectedTitle: document.getElementById("selectedTitle"),
  selectedMeasures: document.getElementById("selectedMeasures"),
  selectedSemitones: document.getElementById("selectedSemitones"),
  selectedScore: document.getElementById("selectedScore"),
  selectedDuration: document.getElementById("selectedDuration"),
  scoreLink: document.getElementById("scoreLink"),
  mp3Link: document.getElementById("mp3Link"),
  midiLink: document.getElementById("midiLink"),
  scoreStatus: document.getElementById("scoreStatus"),
  scoreViewer: document.getElementById("scoreViewer"),
  scoreCaption: document.getElementById("scoreCaption"),
  scorePrev: document.getElementById("scorePrev"),
  scoreNext: document.getElementById("scoreNext"),
  scorePage: document.getElementById("scorePage"),
  scorePageSelect: document.getElementById("scorePageSelect"),
  shortlist: document.getElementById("shortlist"),
  notes: document.getElementById("notes"),
  saveState: document.getElementById("saveState"),
  exportCsv: document.getElementById("exportCsv"),
};

const state = {
  source: "kdf",
  voiceCount: "5",
  target: "string_quartet",
  group: "all",
  currentId: decodeURIComponent(window.location.hash.slice(1)) || "",
  scorePage: 1,
  reviews: loadReviews(),
};

const scoreRenderer = {
  toolkit: null,
  readyPromise: null,
  currentPieceId: "",
  pageCount: 0,
  requestToken: 0,
};

function loadReviews() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
  } catch {
    return {};
  }
}

function saveReviews() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.reviews));
  elements.saveState.textContent = "Saved locally";
}

function emptyReview() {
  return {
    readiness: 0,
    playability: 0,
    balance: 0,
    clarity: 0,
    shortlisted: false,
    notes: "",
  };
}

function reviewFor(id) {
  if (!state.reviews[id]) {
    state.reviews[id] = emptyReview();
  }
  return state.reviews[id];
}

function assetUrl(path) {
  const cleanPath = path.replace(/^\.\//, "");
  const suffix = `?v=${ASSET_VERSION}`;
  if (window.location.hostname.endsWith("github.io")) {
    return RAW_BASE + cleanPath + suffix;
  }
  return "../" + cleanPath + suffix;
}

function encodedAssetUrl(path) {
  return encodeURI(assetUrl(path));
}

function parseTsv(text) {
  const lines = text.trim().split(/\r?\n/);
  if (!lines.length) {
    return [];
  }
  const headers = lines[0].split("\t");
  return lines.slice(1).filter(Boolean).map((line) => {
    const values = line.split("\t");
    return Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]));
  });
}

function basename(path) {
  return String(path || "").split("/").pop() || "";
}

function numericValue(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function sourceLabel(source) {
  return SOURCE_LABELS[source] || source.toUpperCase();
}

function targetLabel(target) {
  return TARGET_LABELS[target] || target.replace(/_/g, " ");
}

function cpdlGroupLabel(section) {
  if (section.startsWith("Sacred")) {
    return "Sacred";
  }
  if (section.startsWith("Secular")) {
    return "Secular";
  }
  return section || "CPDL";
}

function pieceId(piece) {
  return [
    piece.sourceKey,
    piece.voiceCount,
    piece.target,
    piece.musicxml.replace(/[^A-Za-z0-9]+/g, "_").replace(/^_+|_+$/g, ""),
  ].join(":");
}

function kdfMp3Path(musicxmlPath) {
  return musicxmlPath
    .replace("/reductions/string_quartet/", "/renders/string_quartet_mp3/")
    .replace(/\.musicxml$/, ".mp3");
}

function normalizeKdfRow(row, dataset, order) {
  const musicxml = row.output;
  const piece = {
    sourceKey: dataset.source,
    sourceLabel: sourceLabel(dataset.source),
    voiceCount: dataset.voiceCount,
    target: dataset.target,
    targetLabel: targetLabel(dataset.target),
    group: row.book,
    groupLabel: `Book ${row.book}`,
    title: row.title,
    filename: basename(row.filename),
    source: row.filename,
    sourceFormat: "mid",
    durationQuarters: numericValue(row.duration_quarters),
    semitones: numericValue(row.chosen_semitones),
    score: numericValue(row.transposition_score),
    musicxml,
    mp3: dataset.hasAudio ? kdfMp3Path(musicxml) : "",
    measures: row.measures_per_part || "",
    reducedParts: numericValue(row.reduced_parts) || 4,
    order,
  };
  piece.id = pieceId(piece);
  return piece;
}

function normalizeCpdlRow(row, dataset, order) {
  const piece = {
    sourceKey: dataset.source,
    sourceLabel: sourceLabel(dataset.source),
    voiceCount: dataset.voiceCount,
    target: dataset.target,
    targetLabel: targetLabel(dataset.target),
    group: cpdlGroupLabel(row.section),
    groupLabel: cpdlGroupLabel(row.section),
    title: `${row.work_index}. ${row.work_title}`,
    filename: basename(row.source_path),
    source: row.source_path,
    sourceFormat: row.source_format,
    durationQuarters: null,
    semitones: numericValue(row.global_transposition),
    score: null,
    musicxml: row.output_path,
    mp3: "",
    measures: "",
    reducedParts: dataset.target === "string_quartet_plus_viole" ? 5 : 4,
    order,
  };
  piece.id = pieceId(piece);
  return piece;
}

async function loadDataset(dataset, startOrder) {
  const response = await fetch(encodedAssetUrl(dataset.report));
  if (!response.ok) {
    throw new Error(`Could not load ${dataset.report} (${response.status}).`);
  }
  const rows = parseTsv(await response.text()).filter((row) => row.status === "ok");
  return rows.map((row, index) => (
    dataset.source === "kdf"
      ? normalizeKdfRow(row, dataset, startOrder + index)
      : normalizeCpdlRow(row, dataset, startOrder + index)
  ));
}

async function loadCatalog() {
  const pieces = [];
  for (const dataset of DATASETS) {
    pieces.push(...await loadDataset(dataset, pieces.length));
  }
  CATALOG = pieces;
}

function sourceMidiPath(piece) {
  return piece.source;
}

function displayMeasures(piece) {
  if (!piece.measures) {
    return "--";
  }
  return piece.measures.split(",")[0];
}

function formatSemitones(value) {
  if (!Number.isFinite(value)) {
    return "--";
  }
  if (value === 0) {
    return "0";
  }
  return value > 0 ? `+${value}` : String(value);
}

function formatDuration(seconds) {
  if (!Number.isFinite(seconds)) {
    return "--:--";
  }
  const rounded = Math.round(seconds);
  const minutes = Math.floor(rounded / 60);
  const remainder = String(rounded % 60).padStart(2, "0");
  return `${minutes}:${remainder}`;
}

function scoreFileName(piece) {
  return piece.musicxml.split("/").pop();
}

function svgLength(value) {
  const match = String(value || "").match(/^([\d.]+)/);
  return match ? Number(match[1]) : 0;
}

function fitScoreSvg(svg) {
  const document = new DOMParser().parseFromString(svg, "image/svg+xml");
  const svgElement = document.documentElement;
  if (svgElement.nodeName.toLowerCase() !== "svg") {
    return svg;
  }

  const width = svgLength(svgElement.getAttribute("width"));
  const height = svgLength(svgElement.getAttribute("height"));
  if (!svgElement.getAttribute("viewBox") && width > 0 && height > 0) {
    svgElement.setAttribute("viewBox", `0 0 ${width} ${height}`);
  }

  svgElement.removeAttribute("width");
  svgElement.removeAttribute("height");
  svgElement.setAttribute("preserveAspectRatio", "xMinYMin meet");
  svgElement.classList.add("rendered-score");

  return new XMLSerializer().serializeToString(svgElement);
}

function loadVerovioScript() {
  if (window.verovio?.toolkit) {
    return Promise.resolve();
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = VEROVIO_SCRIPT_URL;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Could not load the Verovio renderer."));
    document.head.append(script);
  });
}

function waitForVerovioRuntime() {
  return new Promise((resolve, reject) => {
    const module = window.verovio?.module;
    if (!module || !window.verovio?.toolkit) {
      reject(new Error("Verovio did not initialize."));
      return;
    }

    if (module.calledRun) {
      resolve();
      return;
    }

    const previousHandler = module.onRuntimeInitialized;
    const timeout = window.setTimeout(() => {
      reject(new Error("Verovio took too long to initialize."));
    }, 20000);

    module.onRuntimeInitialized = () => {
      window.clearTimeout(timeout);
      if (typeof previousHandler === "function") {
        previousHandler();
      }
      resolve();
    };
  });
}

function initializeScoreRenderer() {
  if (!scoreRenderer.readyPromise) {
    scoreRenderer.readyPromise = loadVerovioScript()
      .then(waitForVerovioRuntime)
      .then(() => {
        scoreRenderer.toolkit = new window.verovio.toolkit();
        return scoreRenderer.toolkit;
      })
      .catch((error) => {
        scoreRenderer.readyPromise = null;
        throw error;
      });
  }
  return scoreRenderer.readyPromise;
}

function setScoreLoading(piece, label) {
  elements.scoreStatus.textContent = label;
  elements.scoreCaption.textContent = `${piece.title} | ${piece.groupLabel}`;
  elements.scoreViewer.replaceChildren();
  const message = document.createElement("p");
  message.className = "score-message";
  message.textContent = label;
  elements.scoreViewer.append(message);
}

function updateScoreControls() {
  const hasPages = scoreRenderer.pageCount > 0;
  elements.scorePage.textContent = hasPages ? `/ ${scoreRenderer.pageCount}` : "-- / --";
  elements.scorePageSelect.disabled = !hasPages;
  if (!hasPages) {
    elements.scorePageSelect.replaceChildren();
  } else if (elements.scorePageSelect.options.length !== scoreRenderer.pageCount) {
    elements.scorePageSelect.replaceChildren(
      ...Array.from({ length: scoreRenderer.pageCount }, (_, index) => {
        const option = document.createElement("option");
        option.value = String(index + 1);
        option.textContent = `Page ${index + 1}`;
        return option;
      }),
    );
  }
  if (hasPages) {
    elements.scorePageSelect.value = String(state.scorePage);
  }
  elements.scorePrev.disabled = !hasPages || state.scorePage <= 1;
  elements.scoreNext.disabled = !hasPages || state.scorePage >= scoreRenderer.pageCount;
}

function renderScorePage(piece = currentPiece()) {
  if (!scoreRenderer.toolkit || scoreRenderer.pageCount < 1) {
    updateScoreControls();
    return;
  }

  state.scorePage = Math.min(Math.max(state.scorePage, 1), scoreRenderer.pageCount);
  const svg = scoreRenderer.toolkit.renderToSVG(state.scorePage, false);
  if (!svg) {
    throw new Error("The selected page could not be rendered.");
  }

  elements.scoreViewer.innerHTML = fitScoreSvg(svg);
  elements.scoreStatus.textContent = piece.title;
  elements.scoreCaption.textContent = `${piece.title} | ${piece.groupLabel}`;
  updateScoreControls();
}

function showScoreError(piece, error) {
  scoreRenderer.pageCount = 0;
  elements.scoreStatus.textContent = "Score preview unavailable";
  elements.scoreCaption.textContent = `${piece.title} | ${piece.groupLabel}`;
  elements.scoreViewer.replaceChildren();

  const message = document.createElement("p");
  message.className = "score-message";
  message.textContent = error.message || "The score preview could not be loaded.";

  const link = document.createElement("a");
  link.href = encodedAssetUrl(piece.musicxml);
  link.target = "_blank";
  link.rel = "noopener";
  link.download = scoreFileName(piece);
  link.textContent = "Open MusicXML";

  elements.scoreViewer.append(message, link);
  updateScoreControls();
}

async function loadScorePreview(piece) {
  const token = ++scoreRenderer.requestToken;
  state.scorePage = 1;
  scoreRenderer.currentPieceId = piece.id;
  scoreRenderer.pageCount = 0;
  updateScoreControls();
  setScoreLoading(piece, "Loading score");

  try {
    const toolkit = await initializeScoreRenderer();
    if (token !== scoreRenderer.requestToken) {
      return;
    }

    setScoreLoading(piece, "Loading MusicXML");
    const response = await fetch(encodedAssetUrl(piece.musicxml));
    if (!response.ok) {
      throw new Error(`MusicXML request failed with ${response.status}.`);
    }

    const musicxml = await response.text();
    if (token !== scoreRenderer.requestToken) {
      return;
    }

    toolkit.setOptions(SCORE_RENDER_OPTIONS);
    if (!toolkit.loadData(musicxml)) {
      throw new Error("MusicXML could not be loaded by Verovio.");
    }

    scoreRenderer.pageCount = Math.max(1, toolkit.getPageCount());
    renderScorePage(piece);
  } catch (error) {
    if (token === scoreRenderer.requestToken) {
      showScoreError(piece, error);
    }
  }
}

function changeScorePage(delta) {
  if (!scoreRenderer.pageCount) {
    return;
  }
  const nextPage = Math.min(Math.max(state.scorePage + delta, 1), scoreRenderer.pageCount);
  if (nextPage === state.scorePage) {
    return;
  }
  state.scorePage = nextPage;
  renderScorePage(currentPiece());
}

function selectScorePage(value) {
  if (!scoreRenderer.pageCount) {
    return;
  }
  const nextPage = Math.min(Math.max(Number(value), 1), scoreRenderer.pageCount);
  if (!Number.isFinite(nextPage) || nextPage === state.scorePage) {
    return;
  }
  state.scorePage = nextPage;
  renderScorePage(currentPiece());
}

function handleScoreKeydown(event) {
  if (["INPUT", "SELECT", "TEXTAREA"].includes(event.target.tagName)) {
    return;
  }
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    changeScorePage(-1);
  }
  if (event.key === "ArrowRight") {
    event.preventDefault();
    changeScorePage(1);
  }
}

function currentPiece() {
  return CATALOG.find((piece) => piece.id === state.currentId) || filteredPieces()[0] || CATALOG[0] || null;
}

function currentFilterPieces({ includeQuery = false } = {}) {
  const query = includeQuery ? elements.search.value.trim().toLowerCase() : "";
  return CATALOG.filter((piece) => {
    const matchesSource = piece.sourceKey === state.source;
    const matchesVoice = String(piece.voiceCount) === String(state.voiceCount);
    const matchesTarget = piece.target === state.target;
    const matchesGroup = state.group === "all" || piece.group === state.group;
    const haystack = [
      piece.sourceLabel,
      piece.voiceCount,
      piece.targetLabel,
      piece.groupLabel,
      piece.title,
      piece.filename,
    ].join(" ").toLowerCase();
    return matchesSource && matchesVoice && matchesTarget && matchesGroup && (!query || haystack.includes(query));
  });
}

function uniqueSorted(values, numeric = false) {
  const unique = [...new Set(values)];
  return unique.sort((left, right) => {
    if (numeric) {
      return Number(left) - Number(right);
    }
    return String(left).localeCompare(String(right));
  });
}

function setSelectOptions(select, options, value) {
  select.replaceChildren(
    ...options.map((optionData) => {
      const option = document.createElement("option");
      option.value = optionData.value;
      option.textContent = optionData.label;
      return option;
    }),
  );
  select.value = value;
}

function availableVoices(source) {
  return uniqueSorted(
    CATALOG.filter((piece) => piece.sourceKey === source).map((piece) => String(piece.voiceCount)),
    true,
  );
}

function availableTargets(source, voiceCount) {
  return uniqueSorted(
    CATALOG
      .filter((piece) => piece.sourceKey === source && String(piece.voiceCount) === String(voiceCount))
      .map((piece) => piece.target),
  );
}

function availableGroups(source, voiceCount, target) {
  const groups = CATALOG
    .filter((piece) => (
      piece.sourceKey === source
      && String(piece.voiceCount) === String(voiceCount)
      && piece.target === target
    ))
    .map((piece) => piece.group);
  return uniqueSorted(groups).map((group) => {
    const piece = CATALOG.find((candidate) => (
      candidate.sourceKey === source
      && String(candidate.voiceCount) === String(voiceCount)
      && candidate.target === target
      && candidate.group === group
    ));
    return { value: group, label: piece?.groupLabel || group };
  });
}

function normalizeFilters() {
  const sources = uniqueSorted(CATALOG.map((piece) => piece.sourceKey));
  if (!sources.includes(state.source)) {
    state.source = sources[0] || "";
  }

  const voices = availableVoices(state.source);
  if (!voices.includes(String(state.voiceCount))) {
    state.voiceCount = voices[0] || "";
  }

  const targets = availableTargets(state.source, state.voiceCount);
  if (!targets.includes(state.target)) {
    state.target = targets.includes("string_quartet") ? "string_quartet" : targets[0] || "";
  }

  const groups = availableGroups(state.source, state.voiceCount, state.target).map((option) => option.value);
  if (state.group !== "all" && !groups.includes(state.group)) {
    state.group = "all";
  }
}

function renderFilterControls() {
  normalizeFilters();
  const sourceOptions = uniqueSorted(CATALOG.map((piece) => piece.sourceKey)).map((source) => ({
    value: source,
    label: sourceLabel(source),
  }));
  const voiceOptions = availableVoices(state.source).map((voiceCount) => ({
    value: voiceCount,
    label: `${voiceCount} voices`,
  }));
  const targetOptions = availableTargets(state.source, state.voiceCount).map((target) => ({
    value: target,
    label: targetLabel(target),
  }));
  const groupOptions = [
    { value: "all", label: "All groups" },
    ...availableGroups(state.source, state.voiceCount, state.target),
  ];

  setSelectOptions(elements.sourceSelect, sourceOptions, state.source);
  setSelectOptions(elements.voiceSelect, voiceOptions, String(state.voiceCount));
  setSelectOptions(elements.targetSelect, targetOptions, state.target);
  setSelectOptions(elements.groupSelect, groupOptions, state.group);
}

function selectFirstForCurrentFilters() {
  const first = currentFilterPieces()[0];
  if (first) {
    state.currentId = first.id;
  }
}

function handleFilterChange(changed) {
  if (changed === "source") {
    state.source = elements.sourceSelect.value;
    state.voiceCount = "";
    state.target = "string_quartet";
    state.group = "all";
  } else if (changed === "voice") {
    state.voiceCount = elements.voiceSelect.value;
    state.target = "string_quartet";
    state.group = "all";
  } else if (changed === "target") {
    state.target = elements.targetSelect.value;
    state.group = "all";
  } else if (changed === "group") {
    state.group = elements.groupSelect.value;
  }
  renderFilterControls();
  selectFirstForCurrentFilters();
  renderSelected();
  renderList();
}

function filteredPieces() {
  const pieces = currentFilterPieces({ includeQuery: true });

  const sortValue = elements.sort.value;
  pieces.sort((left, right) => {
    if (sortValue === "duration-desc") {
      return (right.durationQuarters ?? -1) - (left.durationQuarters ?? -1) || left.order - right.order;
    }
    if (sortValue === "duration-asc") {
      return (left.durationQuarters ?? Number.MAX_SAFE_INTEGER) - (right.durationQuarters ?? Number.MAX_SAFE_INTEGER)
        || left.order - right.order;
    }
    if (sortValue === "transposition") {
      return (left.semitones ?? 0) - (right.semitones ?? 0) || left.order - right.order;
    }
    if (sortValue === "readiness") {
      return reviewFor(right.id).readiness - reviewFor(left.id).readiness || left.order - right.order;
    }
    return left.order - right.order;
  });
  return pieces;
}

function renderList() {
  const pieces = filteredPieces();
  elements.visibleCount.textContent = String(pieces.length);
  elements.audioCount.textContent = String(pieces.filter((piece) => piece.mp3).length);
  elements.partCount.textContent = pieces.length ? String(Math.max(...pieces.map((piece) => piece.reducedParts || 4))) : "4";
  elements.pieceList.replaceChildren();

  if (!pieces.length) {
    const message = document.createElement("p");
    message.className = "empty-list-message";
    message.textContent = "No works match the current filters.";
    elements.pieceList.append(message);
    return;
  }

  for (const piece of pieces) {
    const review = reviewFor(piece.id);
    const row = document.createElement("button");
    row.type = "button";
    row.className = `piece-row${piece.id === state.currentId ? " is-selected" : ""}`;
    row.dataset.id = piece.id;

    const body = document.createElement("span");
    const title = document.createElement("span");
    title.className = "piece-title";
    title.textContent = piece.title;

    const meta = document.createElement("span");
    meta.className = "piece-meta";
    meta.textContent = [
      piece.sourceLabel,
      `${piece.voiceCount} voices`,
      piece.groupLabel,
      `${formatSemitones(piece.semitones)} semitones`,
    ].join(" | ");

    const rating = document.createElement("span");
    rating.className = `piece-review${review.readiness ? " is-rated" : ""}`;
    rating.textContent = review.readiness ? `${review.readiness}/5` : "--";

    body.append(title, meta);
    row.append(body, rating);
    row.addEventListener("click", () => selectPiece(piece.id));
    elements.pieceList.append(row);
  }
}

function selectPiece(id) {
  state.currentId = id;
  const piece = currentPiece();
  window.history.replaceState(null, "", `#${encodeURIComponent(piece.id)}`);
  renderSelected();
  renderList();
}

function renderSelected() {
  const piece = currentPiece();
  if (!piece) {
    return;
  }
  const review = reviewFor(piece.id);
  const mp3Url = piece.mp3 ? encodedAssetUrl(piece.mp3) : "";

  elements.selectedBook.textContent = `${piece.sourceLabel} | ${piece.voiceCount} voices | ${piece.targetLabel} | ${piece.groupLabel}`;
  elements.selectedTitle.textContent = piece.title;
  elements.selectedMeasures.textContent = displayMeasures(piece);
  elements.selectedSemitones.textContent = formatSemitones(piece.semitones);
  elements.selectedScore.textContent = Number.isFinite(piece.score) ? piece.score.toFixed(6) : "--";
  elements.selectedDuration.textContent = piece.mp3 ? "--:--" : "No audio";

  if (piece.mp3 && elements.audio.getAttribute("src") !== mp3Url) {
    elements.audio.setAttribute("src", mp3Url);
  }
  if (!piece.mp3) {
    elements.audio.removeAttribute("src");
    elements.audio.load();
  }

  setAssetLink(elements.scoreLink, piece.musicxml, piece.musicxml.split("/").pop(), "MusicXML");
  setOptionalAssetLink(elements.mp3Link, piece.mp3, piece.mp3 ? piece.mp3.split("/").pop() : "No MP3", "MP3");
  setAssetLink(elements.midiLink, sourceMidiPath(piece), piece.filename, "Source");

  elements.shortlist.classList.toggle("is-active", review.shortlisted);
  elements.shortlist.textContent = review.shortlisted ? "Shortlisted" : "Shortlist";
  elements.notes.value = review.notes || "";
  renderRatingControls(review);
  loadScorePreview(piece);
}

function setAssetLink(link, path, fileName, label) {
  link.href = encodedAssetUrl(path);
  link.download = fileName;
  link.target = "_blank";
  link.rel = "noopener";
  if (label) {
    link.textContent = label;
  }
  link.removeAttribute("aria-disabled");
  link.classList.remove("is-disabled");
}

function setOptionalAssetLink(link, path, fileName, label) {
  if (!path) {
    link.removeAttribute("href");
    link.removeAttribute("download");
    link.textContent = fileName;
    link.setAttribute("aria-disabled", "true");
    link.classList.add("is-disabled");
    return;
  }
  setAssetLink(link, path, fileName, label);
}

function initRatingControls() {
  document.querySelectorAll(".rating-row").forEach((row) => {
    const criterion = row.dataset.criterion;
    const buttonGroup = row.querySelector(".rating-buttons");
    for (let value = 1; value <= 5; value += 1) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = String(value);
      button.dataset.criterion = criterion;
      button.dataset.value = String(value);
      button.setAttribute("aria-pressed", "false");
      button.addEventListener("click", () => {
        const review = reviewFor(currentPiece().id);
        review[criterion] = review[criterion] === value ? 0 : value;
        saveReviews();
        renderRatingControls(review);
        renderList();
      });
      buttonGroup.append(button);
    }
  });
}

function renderRatingControls(review) {
  document.querySelectorAll(".rating-buttons button").forEach((button) => {
    const criterion = button.dataset.criterion;
    const active = Number(button.dataset.value) === review[criterion];
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
  });
}

function updateNotes() {
  const review = reviewFor(currentPiece().id);
  review.notes = elements.notes.value;
  saveReviews();
}

function toggleShortlist() {
  const review = reviewFor(currentPiece().id);
  review.shortlisted = !review.shortlisted;
  saveReviews();
  renderSelected();
  renderList();
}

function exportCsv() {
  const header = [
    "source",
    "voices",
    "target",
    "group",
    "title",
    "readiness",
    "playability",
    "balance",
    "clarity",
    "shortlisted",
    "notes",
    "musicxml",
    "mp3",
  ];
  const rows = CATALOG.map((piece) => {
    const review = reviewFor(piece.id);
    return [
      piece.sourceLabel,
      piece.voiceCount,
      piece.targetLabel,
      piece.groupLabel,
      piece.title,
      review.readiness,
      review.playability,
      review.balance,
      review.clarity,
      review.shortlisted ? "yes" : "no",
      review.notes,
      piece.musicxml,
      piece.mp3,
    ];
  });

  const csv = [header, ...rows]
    .map((row) => row.map(csvCell).join(","))
    .join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "gesualdo-quartet-review.csv";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function csvCell(value) {
  const text = String(value ?? "");
  if (/[",\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function attachEvents() {
  elements.sourceSelect.addEventListener("change", () => handleFilterChange("source"));
  elements.voiceSelect.addEventListener("change", () => handleFilterChange("voice"));
  elements.targetSelect.addEventListener("change", () => handleFilterChange("target"));
  elements.groupSelect.addEventListener("change", () => handleFilterChange("group"));
  elements.search.addEventListener("input", renderList);
  elements.sort.addEventListener("change", renderList);
  elements.shortlist.addEventListener("click", toggleShortlist);
  elements.notes.addEventListener("input", updateNotes);
  elements.exportCsv.addEventListener("click", exportCsv);
  elements.scorePrev.addEventListener("click", () => changeScorePage(-1));
  elements.scoreNext.addEventListener("click", () => changeScorePage(1));
  elements.scorePageSelect.addEventListener("change", () => selectScorePage(elements.scorePageSelect.value));
  document.addEventListener("keydown", handleScoreKeydown);
  elements.audio.addEventListener("loadedmetadata", () => {
    elements.selectedDuration.textContent = formatDuration(elements.audio.duration);
  });
}

function defaultPieceId() {
  const preferred = CATALOG.find((piece) => piece.musicxml.includes("book6_22_gia_piansi_nel_dolore"));
  return preferred?.id || CATALOG[0]?.id || "";
}

function applyCurrentPieceFilters(piece) {
  if (!piece) {
    return;
  }
  state.source = piece.sourceKey;
  state.voiceCount = String(piece.voiceCount);
  state.target = piece.target;
  state.group = "all";
}

function showCatalogLoadError(error) {
  elements.pieceList.replaceChildren();
  const message = document.createElement("p");
  message.className = "empty-list-message";
  message.textContent = error.message || "The catalog could not be loaded.";
  elements.pieceList.append(message);
  elements.visibleCount.textContent = "0";
  elements.audioCount.textContent = "0";
}

async function init() {
  initRatingControls();
  attachEvents();
  try {
    await loadCatalog();
    state.currentId = state.currentId || defaultPieceId();
    applyCurrentPieceFilters(currentPiece());
    renderFilterControls();
    selectPiece(currentPiece().id);
  } catch (error) {
    showCatalogLoadError(error);
  }
}

init();
