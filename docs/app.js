const RAW_BASE = "https://raw.githubusercontent.com/fpachet/gesualdo/main/";
const ASSET_VERSION = "2026-06-07-kdf-book-layout";
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

const CATALOG = [
  { book: "IV", title: "1. Luci serena e chiare", filename: "book4_01_luci_serena_e_chiare.mid", source: "data/kdf/book4/sources/book4_01_luci_serena_e_chiare.mid", durationQuarters: 344.0, semitones: -1, score: 0.362301, musicxml: "data/kdf/book4/reductions/string_quartet/book4_01_luci_serena_e_chiare.musicxml", mp3: "data/kdf/book4/renders/string_quartet_mp3/book4_01_luci_serena_e_chiare.mp3", measures: "86,86,86,86" },
  { book: "IV", title: "2. Tallor sano desio", filename: "book4_02_tallor_sano_desio.mid", source: "data/kdf/book4/sources/book4_02_tallor_sano_desio.mid", durationQuarters: 292.0, semitones: -1, score: 0.362074, musicxml: "data/kdf/book4/reductions/string_quartet/book4_02_tallor_sano_desio.musicxml", mp3: "data/kdf/book4/renders/string_quartet_mp3/book4_02_tallor_sano_desio.mp3", measures: "73,73,73,73" },
  { book: "IV", title: "3-4. Io Tacerò", filename: "book4_03-04_io_tacero.mid", source: "data/kdf/book4/sources/book4_03-04_io_tacero.mid", durationQuarters: 552.0, semitones: 1, score: 0.492314, musicxml: "data/kdf/book4/reductions/string_quartet/book4_03-04_io_tacero.musicxml", mp3: "data/kdf/book4/renders/string_quartet_mp3/book4_03-04_io_tacero.mp3", measures: "138,138,138,138" },
  { book: "IV", title: "5. Che fai meco", filename: "book4_05_che_fai_meco.mid", source: "data/kdf/book4/sources/book4_05_che_fai_meco.mid", durationQuarters: 220.0, semitones: 1, score: 0.418197, musicxml: "data/kdf/book4/reductions/string_quartet/book4_05_che_fai_meco.musicxml", mp3: "data/kdf/book4/renders/string_quartet_mp3/book4_05_che_fai_meco.mp3", measures: "55,55,55,55" },
  { book: "IV", title: "6. Questa crudele et pia", filename: "book4_06_questa_crudele_et_pia.mid", source: "data/kdf/book4/sources/book4_06_questa_crudele_et_pia.mid", durationQuarters: 308.0, semitones: 1, score: 0.321606, musicxml: "data/kdf/book4/reductions/string_quartet/book4_06_questa_crudele_et_pia.musicxml", mp3: "data/kdf/book4/renders/string_quartet_mp3/book4_06_questa_crudele_et_pia.mp3", measures: "77,77,77,77" },
  { book: "IV", title: "7-8. Or che in gioia", filename: "book4_07-08_or_che_in_gioia.mid", source: "data/kdf/book4/sources/book4_07-08_or_che_in_gioia.mid", durationQuarters: 334.0, semitones: -1, score: 0.357012, musicxml: "data/kdf/book4/reductions/string_quartet/book4_07-08_or_che_in_gioia.musicxml", mp3: "data/kdf/book4/renders/string_quartet_mp3/book4_07-08_or_che_in_gioia.mp3", measures: "85,85,85,85" },
  { book: "IV", title: "9-10. Cor mio, deh, non piangete", filename: "book4_09-10_cor_mio_deh_non_piangete.mid", source: "data/kdf/book4/sources/book4_09-10_cor_mio_deh_non_piangete.mid", durationQuarters: 404.0, semitones: 1, score: 0.442808, musicxml: "data/kdf/book4/reductions/string_quartet/book4_09-10_cor_mio_deh_non_piangete.musicxml", mp3: "data/kdf/book4/renders/string_quartet_mp3/book4_09-10_cor_mio_deh_non_piangete.mp3", measures: "101,101,101,101" },
  { book: "IV", title: "11. Sparge la morte", filename: "book4_11_sparge_la_morte.mid", source: "data/kdf/book4/sources/book4_11_sparge_la_morte.mid", durationQuarters: 460.0, semitones: 3, score: 0.348933, musicxml: "data/kdf/book4/reductions/string_quartet/book4_11_sparge_la_morte.musicxml", mp3: "data/kdf/book4/renders/string_quartet_mp3/book4_11_sparge_la_morte.mp3", measures: "115,115,115,115" },
  { book: "IV", title: "12-13. Moro, e mentre sospiro", filename: "book4_12-13_moro_e_mentre_sospiro.mid", source: "data/kdf/book4/sources/book4_12-13_moro_e_mentre_sospiro.mid", durationQuarters: 308.0, semitones: 2, score: 0.493598, musicxml: "data/kdf/book4/reductions/string_quartet/book4_12-13_moro_e_mentre_sospiro.musicxml", mp3: "data/kdf/book4/renders/string_quartet_mp3/book4_12-13_moro_e_mentre_sospiro.mp3", measures: "77,77,77,77" },
  { book: "IV", title: "14. Mentre gira costei", filename: "book4_14_mentre_gira_costei.mid", source: "data/kdf/book4/sources/book4_14_mentre_gira_costei.mid", durationQuarters: 228.0, semitones: 0, score: 0.354195, musicxml: "data/kdf/book4/reductions/string_quartet/book4_14_mentre_gira_costei.musicxml", mp3: "data/kdf/book4/renders/string_quartet_mp3/book4_14_mentre_gira_costei.mp3", measures: "57,57,57,57" },
  { book: "IV", title: "15. A voi, mentre il mio core", filename: "book4_15_a_voi_mentre_il_mio_core.mid", source: "data/kdf/book4/sources/book4_15_a_voi_mentre_il_mio_core.mid", durationQuarters: 236.0, semitones: -1, score: 0.338248, musicxml: "data/kdf/book4/reductions/string_quartet/book4_15_a_voi_mentre_il_mio_core.musicxml", mp3: "data/kdf/book4/renders/string_quartet_mp3/book4_15_a_voi_mentre_il_mio_core.mp3", measures: "59,59,59,59" },
  { book: "IV", title: "16-17. Ecco, morirò dunque", filename: "book4_16-17_ecco_moriro_dunque.mid", source: "data/kdf/book4/sources/book4_16-17_ecco_moriro_dunque.mid", durationQuarters: 320.0, semitones: 0, score: 0.341776, musicxml: "data/kdf/book4/reductions/string_quartet/book4_16-17_ecco_moriro_dunque.musicxml", mp3: "data/kdf/book4/renders/string_quartet_mp3/book4_16-17_ecco_moriro_dunque.mp3", measures: "80,80,80,80" },
  { book: "IV", title: "18. Arde il mio cor", filename: "book4_18_arde_il_mio_cor.mid", source: "data/kdf/book4/sources/book4_18_arde_il_mio_cor.mid", durationQuarters: 224.0, semitones: 0, score: 0.270176, musicxml: "data/kdf/book4/reductions/string_quartet/book4_18_arde_il_mio_cor.musicxml", mp3: "data/kdf/book4/renders/string_quartet_mp3/book4_18_arde_il_mio_cor.mp3", measures: "56,56,56,56" },
  { book: "IV", title: "19. Se chiudete nel core", filename: "book4_19_se_chiudete_nel_core.mid", source: "data/kdf/book4/sources/book4_19_se_chiudete_nel_core.mid", durationQuarters: 212.0, semitones: 0, score: 0.306730, musicxml: "data/kdf/book4/reductions/string_quartet/book4_19_se_chiudete_nel_core.musicxml", mp3: "data/kdf/book4/renders/string_quartet_mp3/book4_19_se_chiudete_nel_core.mp3", measures: "53,53,53,53" },
  { book: "VI", title: "1. Se la mia morte brami", filename: "book6_01_se_la_mia_morte_brami.mid", source: "data/kdf/book6/sources/book6_01_se_la_mia_morte_brami.mid", durationQuarters: 392.0, semitones: 0, score: 0.326959, musicxml: "data/kdf/book6/reductions/string_quartet/book6_01_se_la_mia_morte_brami.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_01_se_la_mia_morte_brami.mp3", measures: "98,98,98,98" },
  { book: "VI", title: "2. Beltà poi che tassenti", filename: "book6_02_belta_poi_che_tassenti.mid", source: "data/kdf/book6/sources/book6_02_belta_poi_che_tassenti.mid", durationQuarters: 328.0, semitones: 0, score: 0.411626, musicxml: "data/kdf/book6/reductions/string_quartet/book6_02_belta_poi_che_tassenti.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_02_belta_poi_che_tassenti.mp3", measures: "82,82,82,82" },
  { book: "VI", title: "3. Tu piangi, o filli mia", filename: "book6_03_tu_piangi_o_filli_mia.mid", source: "data/kdf/book6/sources/book6_03_tu_piangi_o_filli_mia.mid", durationQuarters: 320.0, semitones: 1, score: 0.371635, musicxml: "data/kdf/book6/reductions/string_quartet/book6_03_tu_piangi_o_filli_mia.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_03_tu_piangi_o_filli_mia.mp3", measures: "80,80,80,80" },
  { book: "VI", title: "4. Resta di darmi noia", filename: "book6_04_resta_di_darmi_noia.mid", source: "data/kdf/book6/sources/book6_04_resta_di_darmi_noia.mid", durationQuarters: 296.0, semitones: 1, score: 0.473277, musicxml: "data/kdf/book6/reductions/string_quartet/book6_04_resta_di_darmi_noia.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_04_resta_di_darmi_noia.mp3", measures: "74,74,74,74" },
  { book: "VI", title: "5. Chiaro risplender suole", filename: "book6_05_chiaro_risplender_suole.mid", source: "data/kdf/book6/sources/book6_05_chiaro_risplender_suole.mid", durationQuarters: 384.0, semitones: 0, score: 0.329151, musicxml: "data/kdf/book6/reductions/string_quartet/book6_05_chiaro_risplender_suole.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_05_chiaro_risplender_suole.mp3", measures: "96,96,96,96" },
  { book: "VI", title: "6. Io parto e non più dissi", filename: "book6_06_io_parto_e_non_piu_dissi.mid", source: "data/kdf/book6/sources/book6_06_io_parto_e_non_piu_dissi.mid", durationQuarters: 296.0, semitones: 0, score: 0.405896, musicxml: "data/kdf/book6/reductions/string_quartet/book6_06_io_parto_e_non_piu_dissi.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_06_io_parto_e_non_piu_dissi.mp3", measures: "74,74,74,74" },
  { book: "VI", title: "7. Mille volte il di", filename: "book6_07_mille_volte_il_di.mid", source: "data/kdf/book6/sources/book6_07_mille_volte_il_di.mid", durationQuarters: 328.0, semitones: 2, score: 0.378196, musicxml: "data/kdf/book6/reductions/string_quartet/book6_07_mille_volte_il_di.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_07_mille_volte_il_di.mp3", measures: "82,82,82,82" },
  { book: "VI", title: "8. O Dolce mio tesoro", filename: "book6_08_o_dolce_mio_tesoro.mid", source: "data/kdf/book6/sources/book6_08_o_dolce_mio_tesoro.mid", durationQuarters: 280.0, semitones: 0, score: 0.342774, musicxml: "data/kdf/book6/reductions/string_quartet/book6_08_o_dolce_mio_tesoro.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_08_o_dolce_mio_tesoro.mp3", measures: "70,70,70,70" },
  { book: "VI", title: "9. Deh, come invan sospiro", filename: "book6_09_deh_come_invan_sospiro.mid", source: "data/kdf/book6/sources/book6_09_deh_come_invan_sospiro.mid", durationQuarters: 292.0, semitones: 0, score: 0.306834, musicxml: "data/kdf/book6/reductions/string_quartet/book6_09_deh_come_invan_sospiro.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_09_deh_come_invan_sospiro.mp3", measures: "73,73,73,73" },
  { book: "VI", title: "10. Io pur respiro in così gran dolore", filename: "book6_10_io_pur_respiro_in_cosi_gran_dolore.mid", source: "data/kdf/book6/sources/book6_10_io_pur_respiro_in_cosi_gran_dolore.mid", durationQuarters: 264.0, semitones: 0, score: 0.280893, musicxml: "data/kdf/book6/reductions/string_quartet/book6_10_io_pur_respiro_in_cosi_gran_dolore.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_10_io_pur_respiro_in_cosi_gran_dolore.mp3", measures: "66,66,66,66" },
  { book: "VI", title: "11. Alme dAmor rubelle", filename: "book6_11_alme_damor_rubelle.mid", source: "data/kdf/book6/sources/book6_11_alme_damor_rubelle.mid", durationQuarters: 196.0, semitones: -1, score: 0.382057, musicxml: "data/kdf/book6/reductions/string_quartet/book6_11_alme_damor_rubelle.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_11_alme_damor_rubelle.mp3", measures: "49,49,49,49" },
  { book: "VI", title: "12. Càndido e verde fiore", filename: "book6_12_candido_e_verde_fiore.mid", source: "data/kdf/book6/sources/book6_12_candido_e_verde_fiore.mid", durationQuarters: 200.0, semitones: -1, score: 0.391196, musicxml: "data/kdf/book6/reductions/string_quartet/book6_12_candido_e_verde_fiore.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_12_candido_e_verde_fiore.mp3", measures: "50,50,50,50" },
  { book: "VI", title: "13. Ardita Zanzaretta", filename: "book6_13_ardita_zanzaretta.mid", source: "data/kdf/book6/sources/book6_13_ardita_zanzaretta.mid", durationQuarters: 300.0, semitones: 1, score: 0.326902, musicxml: "data/kdf/book6/reductions/string_quartet/book6_13_ardita_zanzaretta.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_13_ardita_zanzaretta.mp3", measures: "75,75,75,75" },
  { book: "VI", title: "14. Ardo per te, mio bene", filename: "book6_14_ardo_per_te_mio_bene.mid", source: "data/kdf/book6/sources/book6_14_ardo_per_te_mio_bene.mid", durationQuarters: 328.0, semitones: 2, score: 0.406867, musicxml: "data/kdf/book6/reductions/string_quartet/book6_14_ardo_per_te_mio_bene.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_14_ardo_per_te_mio_bene.mp3", measures: "82,82,82,82" },
  { book: "VI", title: "15. Ancide sol la morte", filename: "book6_15_ancide_sol_la_morte.mid", source: "data/kdf/book6/sources/book6_15_ancide_sol_la_morte.mid", durationQuarters: 240.0, semitones: 0, score: 0.377753, musicxml: "data/kdf/book6/reductions/string_quartet/book6_15_ancide_sol_la_morte.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_15_ancide_sol_la_morte.mp3", measures: "60,60,60,60" },
  { book: "VI", title: "16. Quel no crudel que la mia speme ancise", filename: "book6_16_quel_no_crudel_que_la_mia_speme_ancise.mid", source: "data/kdf/book6/sources/book6_16_quel_no_crudel_que_la_mia_speme_ancise.mid", durationQuarters: 244.0, semitones: 0, score: 0.394022, musicxml: "data/kdf/book6/reductions/string_quartet/book6_16_quel_no_crudel_que_la_mia_speme_ancise.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_16_quel_no_crudel_que_la_mia_speme_ancise.mp3", measures: "61,61,61,61" },
  { book: "VI", title: "17. Moro, lasso, al mio duolo", filename: "book6_17_moro_lasso_al_mio_duolo.mid", source: "data/kdf/book6/sources/book6_17_moro_lasso_al_mio_duolo.mid", durationQuarters: 344.0, semitones: 0, score: 0.295460, musicxml: "data/kdf/book6/reductions/string_quartet/book6_17_moro_lasso_al_mio_duolo.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_17_moro_lasso_al_mio_duolo.mp3", measures: "86,86,86,86" },
  { book: "VI", title: "18. Volan quasi farfalle", filename: "book6_18_volan_quasi_farfalle.mid", source: "data/kdf/book6/sources/book6_18_volan_quasi_farfalle.mid", durationQuarters: 288.0, semitones: -1, score: 0.384345, musicxml: "data/kdf/book6/reductions/string_quartet/book6_18_volan_quasi_farfalle.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_18_volan_quasi_farfalle.mp3", measures: "72,72,72,72" },
  { book: "VI", title: "19. Al mio gioir il ciel si fa sereno", filename: "book6_19_al_mio_gioir_il_ciel_si_fa_sereno.mid", source: "data/kdf/book6/sources/book6_19_al_mio_gioir_il_ciel_si_fa_sereno.mid", durationQuarters: 249.0, semitones: -1, score: 0.367686, musicxml: "data/kdf/book6/reductions/string_quartet/book6_19_al_mio_gioir_il_ciel_si_fa_sereno.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_19_al_mio_gioir_il_ciel_si_fa_sereno.mp3", measures: "63,63,63,63" },
  { book: "VI", title: "20. Tu segui, o bella Clori", filename: "book6_20_tu_segui_o_bella_clori.mid", source: "data/kdf/book6/sources/book6_20_tu_segui_o_bella_clori.mid", durationQuarters: 236.0, semitones: 0, score: 0.431175, musicxml: "data/kdf/book6/reductions/string_quartet/book6_20_tu_segui_o_bella_clori.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_20_tu_segui_o_bella_clori.mp3", measures: "59,59,59,59" },
  { book: "VI", title: "21. Ancor che per amarti", filename: "book6_21_ancor_che_per_amarti.mid", source: "data/kdf/book6/sources/book6_21_ancor_che_per_amarti.mid", durationQuarters: 336.0, semitones: 0, score: 0.297434, musicxml: "data/kdf/book6/reductions/string_quartet/book6_21_ancor_che_per_amarti.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_21_ancor_che_per_amarti.mp3", measures: "84,84,84,84" },
  { book: "VI", title: "22. Già piansi nel dolore", filename: "book6_22_gia_piansi_nel_dolore.mid", source: "data/kdf/book6/sources/book6_22_gia_piansi_nel_dolore.mid", durationQuarters: 230.0, semitones: 0, score: 0.331850, musicxml: "data/kdf/book6/reductions/string_quartet/book6_22_gia_piansi_nel_dolore.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_22_gia_piansi_nel_dolore.mp3", measures: "58,58,58,58" },
  { book: "VI", title: "23. Quando ridente e bella", filename: "book6_23_quando_ridente_e_bella.mid", source: "data/kdf/book6/sources/book6_23_quando_ridente_e_bella.mid", durationQuarters: 253.0, semitones: -1, score: 0.359785, musicxml: "data/kdf/book6/reductions/string_quartet/book6_23_quando_ridente_e_bella.musicxml", mp3: "data/kdf/book6/renders/string_quartet_mp3/book6_23_quando_ridente_e_bella.mp3", measures: "64,64,64,64" },
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
  book: "all",
  currentId: decodeURIComponent(window.location.hash.slice(1)) || "gesualdo_vi_libro_madrigali_22_(c)icking-archive",
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

function sourceMidiPath(piece) {
  return piece.source;
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
  elements.scoreCaption.textContent = `${piece.title} | Book ${piece.book}`;
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
  elements.scoreCaption.textContent = `${piece.title} | Book ${piece.book}`;
  updateScoreControls();
}

function showScoreError(piece, error) {
  scoreRenderer.pageCount = 0;
  elements.scoreStatus.textContent = "Score preview unavailable";
  elements.scoreCaption.textContent = `${piece.title} | Book ${piece.book}`;
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
  loadScorePreview(piece);
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
  elements.scorePrev.addEventListener("click", () => changeScorePage(-1));
  elements.scoreNext.addEventListener("click", () => changeScorePage(1));
  elements.scorePageSelect.addEventListener("change", () => selectScorePage(elements.scorePageSelect.value));
  document.addEventListener("keydown", handleScoreKeydown);
  elements.audio.addEventListener("loadedmetadata", () => {
    elements.selectedDuration.textContent = formatDuration(elements.audio.duration);
  });
}

initRatingControls();
attachEvents();
selectPiece(currentPiece().id);
