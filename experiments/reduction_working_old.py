# gesualdo_quartet_reduce.py
# pip install music21

from music21 import converter, stream, instrument, clef, note, chord, metadata
import statistics

# ---------- Config ----------
SEMITONES = -9  # your transposition interval
OUT_PATH = '../../data/gesualdo/gesualdo_quartet.musicxml'
ENFORCE_RANGES = True  # octave-fit middle lines to instrument ranges
REGISTER_SPLIT = 60    # when only one middle pitch exists at a slice, >=60 -> Violin II, else Viola

# "hard" ranges (MIDI) for octave-fitting if needed
RANGES = {
    'vln1': (55, 100),  # G3..E7
    'vln2': (55, 88),   # G3..E6-ish
    'vla':  (48, 88),   # C3..E6
    'vc':   (36, 72),   # C2..C5
}

def part_median_pitch(p):
    pitches = []
    for el in p.flat.notes:
        if isinstance(el, chord.Chord):
            pitches.extend([pp.midi for pp in el.pitches])
        elif isinstance(el, note.Note):
            pitches.append(el.pitch.midi)
    return statistics.median(pitches) if pitches else float('nan')

def extract_intervals(part):
    """Return list of (start, end, midi or None) for notes/rests; chords use their top pitch."""
    ints = []
    for el in part.flat.notesAndRests:
        start = float(el.offset)
        end = start + float(el.quarterLength)
        if isinstance(el, chord.Chord):
            m = max(pp.midi for pp in el.pitches)  # pick top note if a chord
            ints.append((start, end, m))
        elif isinstance(el, note.Note):
            ints.append((start, end, el.pitch.midi))
        else:
            # Rest
            ints.append((start, end, None))
    return ints

def build_grid(parts):
    """Collect a sorted list of all unique change points (offsets) across parts."""
    pts = set()
    for p in parts:
        for el in p.flat.notesAndRests:
            s = float(el.offset)
            e = s + float(el.quarterLength)
            pts.add(s); pts.add(e)
    grid = sorted(pts)
    # remove duplicates very close due to float rounding
    cleaned = []
    eps = 1e-9
    for x in grid:
        if not cleaned or abs(cleaned[-1] - x) > eps:
            cleaned.append(x)
    return cleaned

def pitch_at(intervals, t):
    """Pitch sounding at time t (inclusive start, exclusive end)."""
    for s, e, m in intervals:
        if s <= t < e:
            return m
    return None

def add_note_or_extend(part_stream, last_pitch, new_pitch, dur):
    """Either extend last note if same pitch, or add a new note/rest."""
    if new_pitch is None:
        # Rest
        if len(part_stream) > 0 and isinstance(part_stream[-1], note.Rest):
            # extend existing rest
            part_stream[-1].quarterLength += dur
        else:
            r = note.Rest(quarterLength=dur)
            part_stream.append(r)
        return None
    else:
        if len(part_stream) > 0 and isinstance(part_stream[-1], note.Note) and last_pitch == new_pitch:
            # extend previous tied note
            part_stream[-1].quarterLength += dur
        else:
            n = note.Note(new_pitch, quarterLength=dur)
            part_stream.append(n)
        return new_pitch

def octave_fit(midi_pitch, low, high):
    if midi_pitch is None:
        return None
    p = int(midi_pitch)
    while p < low:
        p += 12
    while p > high:
        p -= 12
    return p

def reduce_to_quartet(midi_path, semitones=SEMITONES, out_path=OUT_PATH,
                      enforce_ranges=ENFORCE_RANGES, register_split=REGISTER_SPLIT):
    # Parse and transpose
    s_orig = converter.parse(midi_path)
    s = s_orig.transpose(semitones) if semitones != 0 else s_orig

    parts = list(s.parts) if s.parts else [s]  # if MIDI is a single track
    if len(parts) < 4:
        raise ValueError(f"Expected >= 4 parts; found {len(parts)}")

    # Identify top and bottom parts by median pitch
    medians = [(i, part_median_pitch(p)) for i, p in enumerate(parts)]
    # filter NaNs safely
    medians = [(i, m) for i, m in medians if m == m]
    if not medians:
        raise ValueError("Could not compute medians; are there any notes?")
    top_idx = max(medians, key=lambda x: x[1])[0]
    bot_idx = min(medians, key=lambda x: x[1])[0]

    top_part = parts[top_idx]
    bot_part = parts[bot_idx]
    middle_parts = [p for i, p in enumerate(parts) if i not in (top_idx, bot_idx)]
    if len(middle_parts) == 0:
        # already 2 parts; just duplicate logic into vln2/vla as rests
        middle_parts = []

    # Prepare intervals for middle merge
    middle_ints = [extract_intervals(p) for p in middle_parts]
    grid = build_grid(middle_parts if middle_parts else parts)

    # Build merged inner voices (Violin II = upper middle, Viola = lower middle)
    v2_stream = stream.Part()
    vla_stream = stream.Part()
    v2_stream.insert(0, instrument.Violin())
    v2_stream.insert(0, clef.TrebleClef())
    vla_stream.insert(0, instrument.Viola())
    vla_stream.insert(0, clef.AltoClef())

    last_v2 = None
    last_vla = None

    for i in range(len(grid) - 1):
        t0, t1 = grid[i], grid[i + 1]
        dur = t1 - t0
        if dur <= 0:
            continue

        # collect middle pitches sounding at t0
        mid_pitches = []
        for ints in middle_ints:
            p = pitch_at(ints, t0)
            if p is not None:
                mid_pitches.append(p)

        v2_pitch = None
        vla_pitch = None

        if len(mid_pitches) >= 2:
            v2_pitch = max(mid_pitches)
            vla_pitch = min(mid_pitches)
            # if equal (unison), prefer giving it to v2 and let viola rest/sustain
            if v2_pitch == vla_pitch:
                vla_pitch = None
        elif len(mid_pitches) == 1:
            only = mid_pitches[0]
            # if one line already active, try to keep continuity
            if last_v2 is None and last_vla is None:
                if only >= register_split:
                    v2_pitch = only
                    vla_pitch = None
                else:
                    v2_pitch = None
                    vla_pitch = only
            elif last_v2 is None:
                # give to v2 to avoid dropping a line entirely
                v2_pitch = only
                vla_pitch = None
            elif last_vla is None:
                v2_pitch = None
                vla_pitch = only
            else:
                # both active previously → choose closer by voice-leading
                if abs(only - last_v2) <= abs(only - last_vla):
                    v2_pitch = only
                else:
                    vla_pitch = only
        else:
            # No middle notes sounding -> sustain rests/previous notes will be extended by add_note_or_extend
            v2_pitch = None
            vla_pitch = None

        # Optional: octave-fit to instrument ranges
        if enforce_ranges:
            if v2_pitch is not None:
                v2_pitch = octave_fit(v2_pitch, *RANGES['vln2'])
            if vla_pitch is not None:
                vla_pitch = octave_fit(vla_pitch, *RANGES['vla'])

        last_v2 = add_note_or_extend(v2_stream, last_v2, v2_pitch, dur)
        last_vla = add_note_or_extend(vla_stream, last_vla, vla_pitch, dur)

    # Keep outer parts as-is (already transposed)
    v1 = top_part.flat
    v1.insert(0, instrument.Violin())
    v1.insert(0, clef.TrebleClef())

    vc = bot_part.flat
    vc.insert(0, instrument.Violoncello())
    vc.insert(0, clef.BassClef())

    # Optional octave-fit outer voices (usually not needed after transposition)
    if ENFORCE_RANGES:
        def octave_fit_part(p, low, high):
            for n in p.recurse().notes:
                n.pitch.midi = octave_fit(n.pitch.midi, low, high)
        octave_fit_part(v1, *RANGES['vln1'])
        octave_fit_part(vc, *RANGES['vc'])

    # Assemble score
    out = stream.Score()
    out.insert(0, metadata.Metadata())
    if s.metadata:
        out.metadata.title = (s.metadata.title or '') + ' – String Quartet Reduction'
        out.metadata.composer = s.metadata.composer

    v1.partName = "Violin I"
    v2_stream.partName = "Violin II"
    vla_stream.partName = "Viola"
    vc.partName = "Violoncello"

    out.append(v1)
    out.append(v2_stream)
    out.append(vla_stream)
    out.append(vc)

    out.write('musicxml', fp=out_path)
    print(f"Written: {out_path}")

if __name__ == "__main__":
    # >>> Set your MIDI path here:
    midi_path = "../../data/gesualdo/gesualdo_vi_libro_madrigali_22.mid"
    reduce_to_quartet(midi_path, semitones=SEMITONES, out_path=OUT_PATH)
