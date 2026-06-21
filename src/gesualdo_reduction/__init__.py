"""Madrigal-to-string-ensemble reduction experiments built on MusES."""

from gesualdo_reduction.analysis import analyze_midi, dense_chords, transposition_plan, voice_ranges

_REDUCTION_EXPORTS = {
    "AssignmentPolicy",
    "DEFAULT_TRANSPOSITION_CANDIDATES",
    "EnsembleProfile",
    "PIANO_REDUCTION",
    "QUARTET_PLUS_VIOLE",
    "ReductionBuilder",
    "ReductionConfig",
    "RegisterAssignmentPolicy",
    "STRING_QUARTET",
    "SweetSpotAssignmentPolicy",
    "Take6QuartetCompressionPolicy",
    "TargetPart",
    "TranspositionChoice",
    "VoiceOrderAssignmentPolicy",
    "add_editorial_dynamics",
    "build_ensemble_score",
    "build_piano_score",
    "build_quartet_plus_viole_sweetspot_score",
    "build_quartet_plus_viole_score",
    "build_quartet_score",
    "build_take6_quartet_score",
    "choose_global_transposition",
    "key_signature_transposition_burden",
    "lower_take6_high_cello_register",
    "normalize_musescore_grid_rhythm",
    "normalize_musescore_rhythm_artifacts",
    "reduce_to_ensemble",
    "reduce_to_piano",
    "reduce_to_quartet_plus_viole_sweetspot",
    "reduce_to_quartet",
    "reduce_to_quartet_plus_viole",
    "reduce_take6_to_quartet",
    "score_global_transposition",
}


def __getattr__(name: str):
    if name in _REDUCTION_EXPORTS:
        from importlib import import_module

        return getattr(import_module("gesualdo_reduction.reduction"), name)
    if name in {"cleanup_musicxml", "cleanup_score"}:
        from importlib import import_module

        return getattr(import_module("gesualdo_reduction.notation_cleanup"), name)
    if name in {"strip_time_modifications"}:
        from importlib import import_module

        return getattr(import_module("gesualdo_reduction.musicxml_compat"), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AssignmentPolicy",
    "DEFAULT_TRANSPOSITION_CANDIDATES",
    "EnsembleProfile",
    "PIANO_REDUCTION",
    "QUARTET_PLUS_VIOLE",
    "ReductionBuilder",
    "ReductionConfig",
    "RegisterAssignmentPolicy",
    "STRING_QUARTET",
    "SweetSpotAssignmentPolicy",
    "Take6QuartetCompressionPolicy",
    "TargetPart",
    "TranspositionChoice",
    "VoiceOrderAssignmentPolicy",
    "add_editorial_dynamics",
    "analyze_midi",
    "build_ensemble_score",
    "build_piano_score",
    "build_quartet_plus_viole_sweetspot_score",
    "build_quartet_plus_viole_score",
    "build_quartet_score",
    "build_take6_quartet_score",
    "choose_global_transposition",
    "cleanup_musicxml",
    "cleanup_score",
    "dense_chords",
    "key_signature_transposition_burden",
    "lower_take6_high_cello_register",
    "normalize_musescore_grid_rhythm",
    "normalize_musescore_rhythm_artifacts",
    "reduce_to_ensemble",
    "reduce_to_piano",
    "reduce_to_quartet_plus_viole_sweetspot",
    "reduce_to_quartet",
    "reduce_to_quartet_plus_viole",
    "reduce_take6_to_quartet",
    "score_global_transposition",
    "strip_time_modifications",
    "transposition_plan",
    "voice_ranges",
]
