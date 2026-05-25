const RAW_BASE = "https://raw.githubusercontent.com/fpachet/gesualdo/main/";
const STORAGE_KEY = "gesualdo-quartet-review-v1";

const CATALOG = [
  { book: "IV", title: "1. Luci serena e chiare", filename: "gesualdo_iv_libro_madrigali_1_(c)icking-archive.mid", durationQuarters: 344.0, semitones: -1, score: 0.362301, musicxml: "data/gesualdo/kdf_reductions/gesualdo_iv_libro_madrigali_1_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_iv_libro_madrigali_1_(c)icking-archive_quartet_rhythm_first.mp3", measures: "86,86,86,86" },
  { book: "IV", title: "2. Tallor sano desio", filename: "gesualdo_iv_libro_madrigali_2_(c)icking-archive.mid", durationQuarters: 292.0, semitones: -1, score: 0.362074, musicxml: "data/gesualdo/kdf_reductions/gesualdo_iv_libro_madrigali_2_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_iv_libro_madrigali_2_(c)icking-archive_quartet_rhythm_first.mp3", measures: "73,73,73,73" },
  { book: "IV", title: "3-4. Io Tacerò", filename: "gesualdo_iv_libro_madrigali_3-4_(c)icking-archive.mid", durationQuarters: 552.0, semitones: 1, score: 0.492314, musicxml: "data/gesualdo/kdf_reductions/gesualdo_iv_libro_madrigali_3-4_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_iv_libro_madrigali_3-4_(c)icking-archive_quartet_rhythm_first.mp3", measures: "138,138,138,138" },
  { book: "IV", title: "5. Che fai meco", filename: "gesualdo_iv_libro_madrigali_5_(c)icking-archive.mid", durationQuarters: 220.0, semitones: 1, score: 0.418197, musicxml: "data/gesualdo/kdf_reductions/gesualdo_iv_libro_madrigali_5_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_iv_libro_madrigali_5_(c)icking-archive_quartet_rhythm_first.mp3", measures: "55,55,55,55" },
  { book: "IV", title: "6. Questa crudele et pia", filename: "gesualdo_iv_libro_madrigali_6_(c)icking-archive.mid", durationQuarters: 308.0, semitones: 1, score: 0.321606, musicxml: "data/gesualdo/kdf_reductions/gesualdo_iv_libro_madrigali_6_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_iv_libro_madrigali_6_(c)icking-archive_quartet_rhythm_first.mp3", measures: "77,77,77,77" },
  { book: "IV", title: "7-8. Or che in gioia", filename: "gesualdo_iv_libro_madrigali_7-8_(c)icking-archive.mid", durationQuarters: 334.0, semitones: -1, score: 0.357012, musicxml: "data/gesualdo/kdf_reductions/gesualdo_iv_libro_madrigali_7-8_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_iv_libro_madrigali_7-8_(c)icking-archive_quartet_rhythm_first.mp3", measures: "85,85,85,85" },
  { book: "IV", title: "9-10. Cor mio, deh, non piangete", filename: "gesualdo_iv_libro_madrigali_9-10_(c)icking-archive.mid", durationQuarters: 404.0, semitones: 1, score: 0.442808, musicxml: "data/gesualdo/kdf_reductions/gesualdo_iv_libro_madrigali_9-10_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_iv_libro_madrigali_9-10_(c)icking-archive_quartet_rhythm_first.mp3", measures: "101,101,101,101" },
  { book: "IV", title: "11. Sparge la morte", filename: "gesualdo_iv_libro_madrigali_11_(c)icking-archive.mid", durationQuarters: 460.0, semitones: 3, score: 0.348933, musicxml: "data/gesualdo/kdf_reductions/gesualdo_iv_libro_madrigali_11_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_iv_libro_madrigali_11_(c)icking-archive_quartet_rhythm_first.mp3", measures: "115,115,115,115" },
  { book: "IV", title: "12-13. Moro, e mentre sospiro", filename: "gesualdo_iv_libro_madrigali_12-13_(c)icking-archive.mid", durationQuarters: 308.0, semitones: 2, score: 0.493598, musicxml: "data/gesualdo/kdf_reductions/gesualdo_iv_libro_madrigali_12-13_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_iv_libro_madrigali_12-13_(c)icking-archive_quartet_rhythm_first.mp3", measures: "77,77,77,77" },
  { book: "IV", title: "14. Mentre gira costei", filename: "gesualdo_iv_libro_madrigali_14_(c)icking-archive.mid", durationQuarters: 228.0, semitones: 0, score: 0.354195, musicxml: "data/gesualdo/kdf_reductions/gesualdo_iv_libro_madrigali_14_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_iv_libro_madrigali_14_(c)icking-archive_quartet_rhythm_first.mp3", measures: "57,57,57,57" },
  { book: "IV", title: "15. A voi, mentre il mio core", filename: "gesualdo_iv_libro_madrigali_15_(c)icking-archive.mid", durationQuarters: 236.0, semitones: -1, score: 0.338248, musicxml: "data/gesualdo/kdf_reductions/gesualdo_iv_libro_madrigali_15_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_iv_libro_madrigali_15_(c)icking-archive_quartet_rhythm_first.mp3", measures: "59,59,59,59" },
  { book: "IV", title: "16-17. Ecco, morirò dunque", filename: "gesualdo_iv_libro_madrigali_16-17_(c)icking-archive.mid", durationQuarters: 320.0, semitones: 0, score: 0.341776, musicxml: "data/gesualdo/kdf_reductions/gesualdo_iv_libro_madrigali_16-17_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_iv_libro_madrigali_16-17_(c)icking-archive_quartet_rhythm_first.mp3", measures: "80,80,80,80" },
  { book: "IV", title: "18. Arde il mio cor", filename: "gesualdo_iv_libro_madrigali_18_(c)icking-archive.mid", durationQuarters: 224.0, semitones: 0, score: 0.270176, musicxml: "data/gesualdo/kdf_reductions/gesualdo_iv_libro_madrigali_18_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_iv_libro_madrigali_18_(c)icking-archive_quartet_rhythm_first.mp3", measures: "56,56,56,56" },
  { book: "IV", title: "19. Se chiudete nel core", filename: "gesualdo_iv_libro_madrigali_19_(c)icking-archive.mid", durationQuarters: 212.0, semitones: 0, score: 0.306730, musicxml: "data/gesualdo/kdf_reductions/gesualdo_iv_libro_madrigali_19_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_iv_libro_madrigali_19_(c)icking-archive_quartet_rhythm_first.mp3", measures: "53,53,53,53" },
  { book: "VI", title: "1. Se la mia morte brami", filename: "gesualdo_vi_libro_madrigali_1_(c)icking-archive.mid", durationQuarters: 392.0, semitones: 0, score: 0.326959, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_1_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_1_(c)icking-archive_quartet_rhythm_first.mp3", measures: "98,98,98,98" },
  { book: "VI", title: "2. Beltà poi che tassenti", filename: "gesualdo_vi_libro_madrigali_2_(c)icking-archive.mid", durationQuarters: 328.0, semitones: 0, score: 0.411626, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_2_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_2_(c)icking-archive_quartet_rhythm_first.mp3", measures: "82,82,82,82" },
  { book: "VI", title: "3. Tu piangi, o filli mia", filename: "gesualdo_vi_libro_madrigali_3_(c)icking-archive.mid", durationQuarters: 320.0, semitones: 1, score: 0.371635, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_3_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_3_(c)icking-archive_quartet_rhythm_first.mp3", measures: "80,80,80,80" },
  { book: "VI", title: "4. Resta di darmi noia", filename: "gesualdo_vi_libro_madrigali_4_(c)icking-archive.mid", durationQuarters: 296.0, semitones: 1, score: 0.473277, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_4_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_4_(c)icking-archive_quartet_rhythm_first.mp3", measures: "74,74,74,74" },
  { book: "VI", title: "5. Chiaro risplender suole", filename: "gesualdo_vi_libro_madrigali_5_(c)icking-archive.mid", durationQuarters: 384.0, semitones: 0, score: 0.329151, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_5_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_5_(c)icking-archive_quartet_rhythm_first.mp3", measures: "96,96,96,96" },
  { book: "VI", title: "6. Io parto e non più dissi", filename: "gesualdo_vi_libro_madrigali_6_(c)icking-archive.mid", durationQuarters: 296.0, semitones: 0, score: 0.405896, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_6_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_6_(c)icking-archive_quartet_rhythm_first.mp3", measures: "74,74,74,74" },
  { book: "VI", title: "7. Mille volte il di", filename: "gesualdo_vi_libro_madrigali_7_(c)icking-archive.mid", durationQuarters: 328.0, semitones: 2, score: 0.378196, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_7_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_7_(c)icking-archive_quartet_rhythm_first.mp3", measures: "82,82,82,82" },
  { book: "VI", title: "8. O Dolce mio tesoro", filename: "gesualdo_vi_libro_madrigali_8_(c)icking-archive.mid", durationQuarters: 280.0, semitones: 0, score: 0.342774, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_8_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_8_(c)icking-archive_quartet_rhythm_first.mp3", measures: "70,70,70,70" },
  { book: "VI", title: "9. Deh, come invan sospiro", filename: "gesualdo_vi_libro_madrigali_9_(c)icking-archive.mid", durationQuarters: 292.0, semitones: 0, score: 0.306834, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_9_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_9_(c)icking-archive_quartet_rhythm_first.mp3", measures: "73,73,73,73" },
  { book: "VI", title: "10. Io pur respiro in così gran dolore", filename: "gesualdo_vi_libro_madrigali_10_(c)icking-archive.mid", durationQuarters: 264.0, semitones: 0, score: 0.280893, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_10_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_10_(c)icking-archive_quartet_rhythm_first.mp3", measures: "66,66,66,66" },
  { book: "VI", title: "11. Alme dAmor rubelle", filename: "gesualdo_vi_libro_madrigali_11_(c)icking-archive.mid", durationQuarters: 196.0, semitones: -1, score: 0.382057, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_11_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_11_(c)icking-archive_quartet_rhythm_first.mp3", measures: "49,49,49,49" },
  { book: "VI", title: "12. Càndido e verde fiore", filename: "gesualdo_vi_libro_madrigali_12_(c)icking-archive.mid", durationQuarters: 200.0, semitones: -1, score: 0.391196, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_12_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_12_(c)icking-archive_quartet_rhythm_first.mp3", measures: "50,50,50,50" },
  { book: "VI", title: "13. Ardita Zanzaretta", filename: "gesualdo_vi_libro_madrigali_13_(c)icking-archive.mid", durationQuarters: 300.0, semitones: 1, score: 0.326902, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_13_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_13_(c)icking-archive_quartet_rhythm_first.mp3", measures: "75,75,75,75" },
  { book: "VI", title: "14. Ardo per te, mio bene", filename: "gesualdo_vi_libro_madrigali_14_(c)icking-archive.mid", durationQuarters: 328.0, semitones: 2, score: 0.406867, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_14_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_14_(c)icking-archive_quartet_rhythm_first.mp3", measures: "82,82,82,82" },
  { book: "VI", title: "15. Ancide sol la morte", filename: "gesualdo_vi_libro_madrigali_15_(c)icking-archive.mid", durationQuarters: 240.0, semitones: 0, score: 0.377753, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_15_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_15_(c)icking-archive_quartet_rhythm_first.mp3", measures: "60,60,60,60" },
  { book: "VI", title: "16. Quel no crudel que la mia speme ancise", filename: "gesualdo_vi_libro_madrigali_16_(c)icking-archive.mid", durationQuarters: 244.0, semitones: 0, score: 0.394022, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_16_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_16_(c)icking-archive_quartet_rhythm_first.mp3", measures: "61,61,61,61" },
  { book: "VI", title: "17. Moro, lasso, al mio duolo", filename: "gesualdo_vi_libro_madrigali_17_(c)icking-archive.mid", durationQuarters: 344.0, semitones: 0, score: 0.295460, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_17_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_17_(c)icking-archive_quartet_rhythm_first.mp3", measures: "86,86,86,86" },
  { book: "VI", title: "18. Volan quasi farfalle", filename: "gesualdo_vi_libro_madrigali_18_(c)icking-archive.mid", durationQuarters: 288.0, semitones: -1, score: 0.384345, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_18_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_18_(c)icking-archive_quartet_rhythm_first.mp3", measures: "72,72,72,72" },
  { book: "VI", title: "19. Al mio gioir il ciel si fa sereno", filename: "gesualdo_vi_libro_madrigali_19_(c)icking-archive.mid", durationQuarters: 249.0, semitones: -1, score: 0.367686, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_19_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_19_(c)icking-archive_quartet_rhythm_first.mp3", measures: "63,63,63,63" },
  { book: "VI", title: "20. Tu segui, o bella Clori", filename: "gesualdo_vi_libro_madrigali_20_(c)icking-archive.mid", durationQuarters: 236.0, semitones: 0, score: 0.431175, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_20_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_20_(c)icking-archive_quartet_rhythm_first.mp3", measures: "59,59,59,59" },
  { book: "VI", title: "21. Ancor che per amarti", filename: "gesualdo_vi_libro_madrigali_21_(c)icking-archive.mid", durationQuarters: 336.0, semitones: 0, score: 0.297434, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_21_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_21_(c)icking-archive_quartet_rhythm_first.mp3", measures: "84,84,84,84" },
  { book: "VI", title: "22. Già piansi nel dolore", filename: "gesualdo_vi_libro_madrigali_22_(c)icking-archive.mid", durationQuarters: 230.0, semitones: 0, score: 0.331850, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_22_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_22_(c)icking-archive_quartet_rhythm_first.mp3", measures: "58,58,58,58" },
  { book: "VI", title: "23. Quando ridente e bella", filename: "gesualdo_vi_libro_madrigali_23_(c)icking-archive.mid", durationQuarters: 253.0, semitones: -1, score: 0.359785, musicxml: "data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_23_(c)icking-archive_quartet_rhythm_first.musicxml", mp3: "data/gesualdo/kdf_reductions_mp3/gesualdo_vi_libro_madrigali_23_(c)icking-archive_quartet_rhythm_first.mp3", measures: "64,64,64,64" },
].map((piece, index) => ({
  ...piece,
  index,
  id: piece.filename.replace(/\.mid$/, ""),
}));

const elements = {
  audio: document.getElementById("player"),
  search: document.getElementById("search"),
  sort: document.getElementById("sort"),
  pieceList: document.getElementById("pieceList"),
  visibleCount: document.getElementById("visibleCount"),
  selectedBook: document.getElementById("selectedBook"),
  selectedTitle: document.getElementById("selectedTitle"),
  selectedMeasures: document.getElementById("selectedMeasures"),
  selectedSemitones: document.getElementById("selectedSemitones"),
  selectedScore: document.getElementById("selectedScore"),
  selectedDuration: document.getElementById("selectedDuration"),
  scoreLink: document.getElementById("scoreLink"),
  mp3Link: document.getElementById("mp3Link"),
  midiLink: document.getElementById("midiLink"),
  shortlist: document.getElementById("shortlist"),
  notes: document.getElementById("notes"),
  saveState: document.getElementById("saveState"),
  exportCsv: document.getElementById("exportCsv"),
};

const state = {
  book: "all",
  currentId: decodeURIComponent(window.location.hash.slice(1)) || "gesualdo_vi_libro_madrigali_22_(c)icking-archive",
  reviews: loadReviews(),
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
  if (window.location.hostname.endsWith("github.io")) {
    return RAW_BASE + cleanPath;
  }
  return "../" + cleanPath;
}

function encodedAssetUrl(path) {
  return encodeURI(assetUrl(path));
}

function sourceMidiPath(piece) {
  return `data/gesualdo/kdf_madrigals/${piece.filename}`;
}

function displayMeasures(piece) {
  return piece.measures.split(",")[0];
}

function formatSemitones(value) {
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

function currentPiece() {
  return CATALOG.find((piece) => piece.id === state.currentId) || CATALOG[0];
}

function filteredPieces() {
  const query = elements.search.value.trim().toLowerCase();
  const pieces = CATALOG.filter((piece) => {
    const matchesBook = state.book === "all" || piece.book === state.book;
    const haystack = `${piece.book} ${piece.title} ${piece.filename}`.toLowerCase();
    return matchesBook && (!query || haystack.includes(query));
  });

  const sortValue = elements.sort.value;
  pieces.sort((left, right) => {
    if (sortValue === "duration-desc") {
      return right.durationQuarters - left.durationQuarters || left.index - right.index;
    }
    if (sortValue === "duration-asc") {
      return left.durationQuarters - right.durationQuarters || left.index - right.index;
    }
    if (sortValue === "transposition") {
      return left.semitones - right.semitones || left.index - right.index;
    }
    if (sortValue === "readiness") {
      return reviewFor(right.id).readiness - reviewFor(left.id).readiness || left.index - right.index;
    }
    return left.index - right.index;
  });
  return pieces;
}

function renderList() {
  const pieces = filteredPieces();
  elements.visibleCount.textContent = String(pieces.length);
  elements.pieceList.replaceChildren();

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
    meta.textContent = `Book ${piece.book} | ${displayMeasures(piece)} measures | ${formatSemitones(piece.semitones)} semitones`;

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
  const review = reviewFor(piece.id);
  const mp3Url = encodedAssetUrl(piece.mp3);

  elements.selectedBook.textContent = `Book ${piece.book}`;
  elements.selectedTitle.textContent = piece.title;
  elements.selectedMeasures.textContent = displayMeasures(piece);
  elements.selectedSemitones.textContent = formatSemitones(piece.semitones);
  elements.selectedScore.textContent = piece.score.toFixed(6);
  elements.selectedDuration.textContent = "--:--";

  if (elements.audio.getAttribute("src") !== mp3Url) {
    elements.audio.setAttribute("src", mp3Url);
  }

  setAssetLink(elements.scoreLink, piece.musicxml, piece.musicxml.split("/").pop());
  setAssetLink(elements.mp3Link, piece.mp3, piece.mp3.split("/").pop());
  setAssetLink(elements.midiLink, sourceMidiPath(piece), piece.filename);

  elements.shortlist.classList.toggle("is-active", review.shortlisted);
  elements.shortlist.textContent = review.shortlisted ? "Shortlisted" : "Shortlist";
  elements.notes.value = review.notes || "";
  renderRatingControls(review);
}

function setAssetLink(link, path, fileName) {
  link.href = encodedAssetUrl(path);
  link.download = fileName;
  link.target = "_blank";
  link.rel = "noopener";
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
    "book",
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
      piece.book,
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
  document.querySelectorAll("[data-book]").forEach((button) => {
    button.addEventListener("click", () => {
      state.book = button.dataset.book;
      document.querySelectorAll("[data-book]").forEach((other) => {
        other.classList.toggle("is-active", other === button);
      });
      renderList();
    });
  });

  elements.search.addEventListener("input", renderList);
  elements.sort.addEventListener("change", renderList);
  elements.shortlist.addEventListener("click", toggleShortlist);
  elements.notes.addEventListener("input", updateNotes);
  elements.exportCsv.addEventListener("click", exportCsv);
  elements.audio.addEventListener("loadedmetadata", () => {
    elements.selectedDuration.textContent = formatDuration(elements.audio.duration);
  });
}

initRatingControls();
attachEvents();
selectPiece(currentPiece().id);
