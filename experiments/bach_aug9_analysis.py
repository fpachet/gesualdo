from music21 import converter, chord, note, interval, pitch
import os

def is_augmented_ninth_chord(ch):
    """
    Detect if chord contains a dominant 7♯9 structure upward from some root:
    major 3rd (4), perfect 5th (7), minor 7th (10), augmented 9th (15)
    """
    # print(ch)
    if len(ch.pitches) < 4:
        return False

    for root in ch.pitches:
        upward_semitones = []

        for p in ch.pitches:
            if p == root:
                continue
            iv = interval.Interval(noteStart=root, noteEnd=p)
            if iv.semitones > 0:  # only upward intervals
                upward_semitones.append(iv.semitones)

        semis_mod12 = {s % 12 for s in upward_semitones}
        semis_raw = set(upward_semitones)

        # semitone checks
        if {4, 7, 10}.issubset(semis_mod12) and (15 in semis_raw or 3 in semis_mod12):
            return True

    return False

def analyze_midi_file(filepath):
    try:
        print('analyse  '+filepath)
        score = converter.parse(filepath)
        chords = score.chordify()
        chords = chords.flatten()# reduce to one stream of vertical chords
        for ch in chords.recurse().getElementsByClass(chord.Chord):
            if len(ch.pitches) >= 4 and is_augmented_ninth_chord(ch):
                return ch
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
    return None

def scan_folder_for_aug9_chords_recursive(root_folder):
    matched_files = []
    for dirpath, _, filenames in os.walk(root_folder):
        for filename in filenames:
            if filename.lower().endswith((".mid", ".midi")):
                filepath = os.path.join(dirpath, filename)
                ch = analyze_midi_file(filepath)
                if ch:
                    print(f'found one: {ch} at {ch.offset} in {filepath}')
                    print(f"Chord at offset {ch.offset} → Measure {ch.measureNumber}, Beat {round(ch.beat, 2)}")
                    matched_files.append((ch, filepath))
    return matched_files

# Usage:
folder_path = "../../data/allbach"
matches = scan_folder_for_aug9_chords_recursive(folder_path)
print("Files with augmented 9th chords:", matches)
