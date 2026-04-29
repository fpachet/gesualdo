"""Madrigal-to-string-ensemble reduction experiments built on MusES."""

from gesualdo_reduction.analysis import analyze_midi, dense_chords, transposition_plan, voice_ranges

_REDUCTION_EXPORTS = {
    "AssignmentPolicy",
    "EnsembleProfile",
    "QUARTET_PLUS_VIOLE",
    "ReductionBuilder",
    "ReductionConfig",
    "RegisterAssignmentPolicy",
    "STRING_QUARTET",
    "SweetSpotAssignmentPolicy",
    "TargetPart",
    "VoiceOrderAssignmentPolicy",
    "build_ensemble_score",
    "build_quartet_plus_viole_sweetspot_score",
    "build_quartet_plus_viole_score",
    "build_quartet_score",
    "reduce_to_ensemble",
    "reduce_to_quartet_plus_viole_sweetspot",
    "reduce_to_quartet",
    "reduce_to_quartet_plus_viole",
}


def __getattr__(name: str):
    if name in _REDUCTION_EXPORTS:
        from importlib import import_module

        return getattr(import_module("gesualdo_reduction.reduction"), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AssignmentPolicy",
    "EnsembleProfile",
    "QUARTET_PLUS_VIOLE",
    "ReductionBuilder",
    "ReductionConfig",
    "RegisterAssignmentPolicy",
    "STRING_QUARTET",
    "SweetSpotAssignmentPolicy",
    "TargetPart",
    "VoiceOrderAssignmentPolicy",
    "analyze_midi",
    "build_ensemble_score",
    "build_quartet_plus_viole_sweetspot_score",
    "build_quartet_plus_viole_score",
    "build_quartet_score",
    "dense_chords",
    "reduce_to_ensemble",
    "reduce_to_quartet_plus_viole_sweetspot",
    "reduce_to_quartet",
    "reduce_to_quartet_plus_viole",
    "transposition_plan",
    "voice_ranges",
]
