"""A short 3Blue1Brown-style explanation of six-to-four score reduction.

Render a quick preview:

    manim -pql animations/optimal_transport_6_to_4.py OptimalTransportScoreReduction

Render the final 1080p movie:

    manim -pqh animations/optimal_transport_6_to_4.py OptimalTransportScoreReduction

The scene deliberately calls the model *partial* optimal transport.  A normal
balanced transport problem conserves all mass; a four-part score cannot retain
six simultaneous monophonic source notes, so two redundant notes are allowed
to pay an explicit omission cost.
"""

from __future__ import annotations

from manim import *


# A restrained palette close to the visual language of 3Blue1Brown videos.
BG = "#0B0F14"
INK = "#F2F4F8"
MUTED = "#98A2B3"
FAINT = "#344054"
SOURCE_BLUE = "#58C4DD"
INNER_GOLD = "#F4D35E"
INNER_ORANGE = "#FF9F1C"
BASS_GREEN = "#83C167"
OMIT_GREY = "#667085"
FAIL_RED = "#FF5A5F"


class NoteToken(VGroup):
    """A tiny drawn note, avoiding dependence on a music-symbol font."""

    def __init__(self, color: ManimColor | str, scale: float = 1.0, **kwargs):
        super().__init__(**kwargs)
        self.head = (
            Ellipse(width=0.30, height=0.20)
            .rotate(-18 * DEGREES)
            .set_fill(color, opacity=1)
            .set_stroke(color, width=1)
        )
        self.stem = Line(
            self.head.get_right() + 0.01 * LEFT,
            self.head.get_right() + 0.54 * UP,
            color=color,
            stroke_width=3,
        )
        self.add(self.head, self.stem)
        self.scale(scale)


class SourceVoice(VGroup):
    def __init__(self, voice: str, pitch: str, color: ManimColor | str):
        super().__init__()
        self.voice_text = Text(voice, font="Avenir Next", font_size=24, color=MUTED)
        self.pitch_text = Text(pitch, font="Avenir Next", font_size=27, color=INK)
        self.note = NoteToken(color)
        self.voice_text.move_to(LEFT * 0.95)
        self.pitch_text.move_to(RIGHT * 0.28)
        self.note.move_to(RIGHT * 1.12)
        self.add(self.voice_text, self.pitch_text, self.note)


class TargetVoice(VGroup):
    def __init__(self, instrument: str):
        super().__init__()
        self.slot = Circle(radius=0.18, color=FAINT, stroke_width=2)
        self.instrument_text = Text(
            instrument, font="Avenir Next", font_size=24, color=MUTED
        )
        self.instrument_text.next_to(self.slot, RIGHT, buff=0.32)
        self.add(self.slot, self.instrument_text)


def transport_path(source: Mobject, target: Mobject) -> CubicBezier:
    """Smooth left-to-right path with a subtle register-dependent bow."""

    start = source.get_center() + 0.17 * RIGHT
    end = target.get_center() + 0.17 * LEFT
    bend = 0.15 * np.sign(end[1] - start[1])
    return CubicBezier(
        start,
        start + 1.25 * RIGHT + bend * UP,
        end + 1.25 * LEFT - bend * UP,
        end,
    )


def mini_staff(center_y: float, x_start: float, x_end: float) -> VGroup:
    """A compact five-line staff used as a readable score abstraction."""

    spacing = 0.065
    lines = VGroup(
        *[
            Line(
                [x_start, center_y + offset * spacing, 0],
                [x_end, center_y + offset * spacing, 0],
                color=FAINT,
                stroke_width=0.8,
            )
            for offset in (-2, -1, 0, 1, 2)
        ]
    )
    barline = Line(
        [x_end, center_y - 2 * spacing, 0],
        [x_end, center_y + 2 * spacing, 0],
        color=FAINT,
        stroke_width=1.1,
    )
    return VGroup(lines, barline).set_z_index(-3)


class OptimalTransportScoreReduction(Scene):
    """Explain a single 6-note-to-4-part assignment in about 25 seconds."""

    def construct(self):
        self.camera.background_color = BG

        title = Text(
            "Optimal transport for score reduction",
            font="Avenir Next",
            weight=MEDIUM,
            font_size=43,
            color=INK,
        ).to_edge(UP, buff=0.25)
        title_rule = Line(LEFT * 5.8, RIGHT * 5.8, color=FAINT, stroke_width=1)
        title_rule.next_to(title, DOWN, buff=0.15)

        source_header = Text(
            "FIXED SOURCE  ·  6 VOICES",
            font="Avenir Next",
            font_size=18,
            color=SOURCE_BLUE,
        ).move_to([-4.25, 2.72, 0])
        target_header = Text(
            "WORKING REDUCTION  ·  4 PARTS",
            font="Avenir Next",
            font_size=18,
            color=BASS_GREEN,
        ).move_to([3.75, 2.72, 0])

        source_specs = [
            ("Soprano", "G5", SOURCE_BLUE),
            ("Alto I", "E5", INNER_GOLD),
            ("Alto II", "C5", INNER_ORANGE),
            ("Tenor I", "G4", INNER_GOLD),
            ("Tenor II", "E4", INNER_ORANGE),
            ("Bass", "C3", BASS_GREEN),
        ]
        source_y = [2.05, 1.28, 0.51, -0.26, -1.03, -1.80]
        sources = VGroup(
            *[SourceVoice(voice, pitch, color) for voice, pitch, color in source_specs]
        )
        for row, y in zip(sources, source_y):
            row.move_to([-4.28, y, 0])

        target_specs = ["Violin I", "Violin II", "Viola", "Cello"]
        target_y = [1.82, 0.70, -0.42, -1.54]
        targets = VGroup(*[TargetVoice(name) for name in target_specs])
        for row, y in zip(targets, target_y):
            row.move_to([3.45, y, 0])

        source_staves = VGroup(
            *[mini_staff(y, -3.62, -2.68) for y in source_y]
        )
        target_staves = VGroup(
            *[mini_staff(y, 2.48, 3.38) for y in target_y]
        )

        divider = DashedLine(
            [0, 2.47, 0], [0, -2.35, 0], dash_length=0.08, color=FAINT
        ).set_stroke(opacity=0.65, width=1.2)

        opening_caption = Text(
            "One sonority: six candidates, four playable slots",
            font="Avenir Next",
            font_size=27,
            color=INK,
        ).to_edge(DOWN, buff=0.32)

        self.play(Write(title), Create(title_rule), run_time=1.0)
        self.play(
            FadeIn(source_header, shift=0.15 * DOWN),
            FadeIn(target_header, shift=0.15 * DOWN),
            FadeIn(source_staves),
            FadeIn(target_staves),
            Create(divider),
            run_time=0.7,
        )
        self.play(
            LaggedStart(*[FadeIn(row, shift=0.25 * RIGHT) for row in sources], lag_ratio=0.08),
            LaggedStart(*[FadeIn(row, shift=0.25 * LEFT) for row in targets], lag_ratio=0.11),
            FadeIn(opening_caption, shift=0.15 * UP),
            run_time=1.3,
        )
        self.wait(0.6)

        # Only locally plausible register assignments are shown; the algorithm
        # evaluates many more candidates, but drawing all 24 obscures the idea.
        plausible_pairs = [
            (0, 0),
            (0, 1),
            (1, 0),
            (1, 1),
            (1, 2),
            (2, 1),
            (2, 2),
            (3, 1),
            (3, 2),
            (4, 1),
            (4, 2),
            (4, 3),
            (5, 2),
            (5, 3),
        ]
        possible_edges = VGroup(
            *[
                transport_path(sources[i].note, targets[j].slot)
                .set_stroke(FAINT, width=1.3, opacity=0.42)
                .set_z_index(-2)
                for i, j in plausible_pairs
            ]
        )

        formula = MathTex(
            r"\min_{x,z}\;\sum_{i,j}x_{ij}C_{ij}+\lambda\sum_i z_i",
            color=INK,
            font_size=34,
        ).to_edge(DOWN, buff=0.26)
        formula.set_color_by_tex(r"C_{ij}", INNER_GOLD)
        formula.set_color_by_tex(r"\lambda", GREY_B)

        self.play(
            FadeOut(opening_caption, shift=0.1 * DOWN),
            LaggedStart(*[Create(edge) for edge in possible_edges], lag_ratio=0.025),
            FadeIn(formula, shift=0.1 * UP),
            run_time=1.5,
        )

        cost_label = Text(
            "COST = register + leap + crossing + harmonic loss",
            font="Avenir Next",
            font_size=20,
            color=MUTED,
            t2c={
                "register": SOURCE_BLUE,
                "leap": INNER_GOLD,
                "crossing": INNER_ORANGE,
                "harmonic loss": BASS_GREEN,
            },
        ).next_to(formula, UP, buff=0.13)
        self.play(FadeIn(cost_label), run_time=0.6)
        self.wait(0.5)

        # Make the combinatorics visible before revealing the winner.  Choosing
        # four of six notes and permuting them over four labelled instruments
        # already gives 360 assignments at a single onset.  A naive search over
        # eight onsets would therefore inspect roughly 2.8e20 sequences.
        objective_formula = formula.copy()
        objective_cost_label = cost_label.copy()
        search_formula = MathTex(
            r"\binom{6}{4}4! = 360"
            r"\qquad"
            r"360^8 \approx 2.8\times 10^{20}",
            font_size=34,
            color=INK,
        ).move_to(formula)
        search_formula[0][0:9].set_color(SOURCE_BLUE)
        search_formula[0][10:].set_color(INNER_GOLD)
        search_caption = Text(
            "plans for one chord                 naive plans over 8 chords",
            font="Avenir Next",
            font_size=19,
            color=MUTED,
        ).move_to(cost_label)

        self.play(
            Transform(formula, search_formula),
            Transform(cost_label, search_caption),
            possible_edges.animate.set_stroke(opacity=0.24),
            run_time=1.0,
        )
        self.wait(0.6)

        search_box = RoundedRectangle(
            width=2.18,
            height=0.48,
            corner_radius=0.12,
            color=SOURCE_BLUE,
            stroke_width=1.5,
        ).set_fill(BG, opacity=0.96)
        search_box.move_to([0, 2.18, 0])
        search_text = Text(
            "TRY 137 / 360",
            font="Avenir Next",
            font_size=19,
            color=SOURCE_BLUE,
        ).move_to(search_box)
        search_badge = VGroup(search_box, search_text)

        def candidate_paths(
            assignments: list[tuple[int, int]],
            colors: list[ManimColor | str],
        ) -> VGroup:
            return VGroup(
                *[
                    transport_path(sources[i].note, targets[j].slot)
                    .set_stroke(color, width=4.2, opacity=0.94)
                    .set_z_index(-1)
                    for (i, j), color in zip(assignments, colors)
                ]
            )

        def candidate_score_notes(
            assignments: list[tuple[int, int]],
            colors: list[ManimColor | str],
            pitches: list[str],
        ) -> tuple[VGroup, VGroup]:
            """Copies of fixed source notes that populate the working score."""

            notes = VGroup()
            labels = VGroup()
            for (source_index, target_index), color, pitch in zip(
                assignments, colors, pitches
            ):
                notes.add(sources[source_index].note.copy().set_z_index(5))
                labels.add(
                    Text(
                        pitch,
                        font="Avenir Next",
                        font_size=20,
                        color=color,
                    ).next_to(targets[target_index].slot, LEFT, buff=0.30)
                )
            return notes, labels

        def status_badge(text: str, color: ManimColor | str) -> VGroup:
            box = RoundedRectangle(
                width=3.10,
                height=0.48,
                corner_radius=0.10,
                color=color,
                stroke_width=1.4,
            ).set_fill(BG, opacity=0.96)
            box.move_to([0, -2.18, 0])
            label = Text(
                text,
                font="Avenir Next",
                font_size=18,
                color=color,
            ).move_to(box)
            return VGroup(box, label)

        # Candidate 137 swaps the two upper voices.  The red paths cross, so
        # branch-and-bound rejects the branch and visibly rewinds it.
        crossing_assignments = [(0, 1), (1, 0), (2, 2), (5, 3)]
        crossing_colors = [FAIL_RED, FAIL_RED, INNER_ORANGE, BASS_GREEN]
        crossing_edges = candidate_paths(crossing_assignments, crossing_colors)
        crossing_notes, crossing_pitch_labels = candidate_score_notes(
            crossing_assignments,
            crossing_colors,
            ["G5", "E5", "C5", "C3"],
        )
        crossing_mark = VGroup(
            Line(0.17 * UL, 0.17 * DR, color=FAIL_RED, stroke_width=4),
            Line(0.17 * DL, 0.17 * UR, color=FAIL_RED, stroke_width=4),
        ).move_to([-0.62, 1.51, 0])
        crossing_status = status_badge("COST 18.7  •  VOICE CROSSING", FAIL_RED)

        self.play(FadeIn(search_badge, scale=0.9), run_time=0.45)
        self.add(*crossing_notes)
        self.play(
            LaggedStart(
                *[
                    AnimationGroup(
                        Create(edge),
                        MoveAlongPath(note, edge),
                        FadeIn(pitch_label, shift=0.08 * RIGHT),
                    )
                    for edge, note, pitch_label in zip(
                        crossing_edges, crossing_notes, crossing_pitch_labels
                    )
                ],
                lag_ratio=0.08,
            ),
            run_time=0.85,
        )
        self.play(
            Create(crossing_mark),
            FadeIn(crossing_status, shift=0.08 * UP),
            run_time=0.45,
        )
        rejected_137 = Text(
            "REJECT  ↶  BACKTRACK",
            font="Avenir Next",
            font_size=18,
            color=FAIL_RED,
        ).move_to(search_badge[1])
        self.play(
            Transform(search_badge[1], rejected_137),
            LaggedStart(
                *[
                    AnimationGroup(
                        Uncreate(edge),
                        MoveAlongPath(note, edge.copy().reverse_direction()),
                        FadeOut(pitch_label),
                    )
                    for edge, note, pitch_label in zip(
                        reversed(crossing_edges),
                        reversed(crossing_notes),
                        reversed(crossing_pitch_labels),
                    )
                ],
                lag_ratio=0.08,
            ),
            FadeOut(crossing_mark),
            FadeOut(crossing_status),
            run_time=0.9,
        )
        self.remove(*crossing_notes)

        # Candidate 221 is orderly, but retains a doubled G while dropping the
        # only inner C.  It is cheaper geometrically and still worse musically.
        try_221 = Text(
            "TRY 221 / 360",
            font="Avenir Next",
            font_size=19,
            color=INNER_GOLD,
        ).move_to(search_badge[1])
        search_box_gold = search_box.copy().set_stroke(INNER_GOLD)
        duplicate_assignments = [(0, 0), (1, 1), (3, 2), (5, 3)]
        duplicate_colors = [SOURCE_BLUE, INNER_GOLD, INNER_GOLD, BASS_GREEN]
        duplicate_edges = candidate_paths(duplicate_assignments, duplicate_colors)
        duplicate_notes, duplicate_pitch_labels = candidate_score_notes(
            duplicate_assignments,
            duplicate_colors,
            ["G5", "E5", "G4", "C3"],
        )
        omitted_c_ring = Circle(
            radius=0.29, color=FAIL_RED, stroke_width=3
        ).move_to(sources[2].note)
        harmonic_status = status_badge("COST 11.3  •  UNIQUE C LOST", FAIL_RED)

        self.play(
            Transform(search_badge[0], search_box_gold),
            Transform(search_badge[1], try_221),
            run_time=0.42,
        )
        self.add(*duplicate_notes)
        self.play(
            LaggedStart(
                *[
                    AnimationGroup(
                        Create(edge),
                        MoveAlongPath(note, edge),
                        FadeIn(pitch_label, shift=0.08 * RIGHT),
                    )
                    for edge, note, pitch_label in zip(
                        duplicate_edges, duplicate_notes, duplicate_pitch_labels
                    )
                ],
                lag_ratio=0.08,
            ),
            run_time=0.85,
        )
        self.play(
            Create(omitted_c_ring),
            FadeIn(harmonic_status, shift=0.08 * UP),
            run_time=0.45,
        )
        rejected_221 = Text(
            "REJECT  ↶  BACKTRACK",
            font="Avenir Next",
            font_size=18,
            color=FAIL_RED,
        ).move_to(search_badge[1])
        self.play(
            Transform(search_badge[1], rejected_221),
            LaggedStart(
                *[
                    AnimationGroup(
                        Uncreate(edge),
                        MoveAlongPath(note, edge.copy().reverse_direction()),
                        FadeOut(pitch_label),
                    )
                    for edge, note, pitch_label in zip(
                        reversed(duplicate_edges),
                        reversed(duplicate_notes),
                        reversed(duplicate_pitch_labels),
                    )
                ],
                lag_ratio=0.08,
            ),
            FadeOut(omitted_c_ring),
            FadeOut(harmonic_status),
            run_time=0.9,
        )
        self.remove(*duplicate_notes)

        try_284 = Text(
            "TRY 284 / 360",
            font="Avenir Next",
            font_size=19,
            color=BASS_GREEN,
        ).move_to(search_badge[1])
        search_box_green = search_box.copy().set_stroke(BASS_GREEN)
        self.play(
            Transform(search_badge[0], search_box_green),
            Transform(search_badge[1], try_284),
            Transform(formula, objective_formula),
            Transform(cost_label, objective_cost_label),
            run_time=0.75,
        )

        # The optimal partial assignment: preserve the two outer anchors, then
        # keep the inner pitches that maximize coverage without voice crossing.
        chosen = [
            (0, 0, SOURCE_BLUE, "G5"),
            (1, 1, INNER_GOLD, "E5"),
            (2, 2, INNER_ORANGE, "C5"),
            (5, 3, BASS_GREEN, "C3"),
        ]
        chosen_edges = VGroup()
        target_pitch_labels = VGroup()
        final_score_notes: list[NoteToken] = []

        for source_index, target_index, color, pitch in chosen:
            path = transport_path(sources[source_index].note, targets[target_index].slot)
            path.set_stroke(color, width=5, opacity=0.95).set_z_index(-1)
            chosen_edges.add(path)

            moving_note = sources[source_index].note.copy().set_z_index(5)
            target_pitch = Text(
                pitch, font="Avenir Next", font_size=23, color=color
            ).next_to(targets[target_index].slot, LEFT, buff=0.32)
            target_pitch_labels.add(target_pitch)

            self.add(moving_note)
            self.play(
                Create(path),
                MoveAlongPath(moving_note, path),
                targets[target_index].slot.animate.set_fill(BG, opacity=0).set_stroke(
                    color, width=1.2, opacity=0.30
                ),
                FadeIn(target_pitch, shift=0.12 * RIGHT),
                run_time=0.72,
                rate_func=smooth,
            )
            final_score_notes.append(moving_note)

        best_text = Text(
            "BEST COST 4.2  ✓",
            font="Avenir Next",
            font_size=18,
            color=BASS_GREEN,
        ).move_to(search_badge[1])
        self.play(Transform(search_badge[1], best_text), run_time=0.45)

        # Two source notes repeat pitch classes already carried by the target.
        # In partial OT they go to a deletion/omission sink at penalty lambda.
        sink_box = RoundedRectangle(
            width=2.10,
            height=0.62,
            corner_radius=0.12,
            color=OMIT_GREY,
            stroke_width=1.5,
        ).set_fill(BG, opacity=0.94)
        sink_box.move_to([0, -2.24, 0])
        sink_text = Text(
            "omit duplicates  ·  cost λ",
            font="Avenir Next",
            font_size=19,
            color=MUTED,
        ).move_to(sink_box)
        sink = VGroup(sink_box, sink_text)

        omission_paths = VGroup()
        omission_motion_paths: list[CubicBezier] = []
        omitted_notes = VGroup()
        for source_index in (3, 4):
            start = sources[source_index].note.get_center() + 0.17 * RIGHT
            end = sink_box.get_left() + [0.06, 0.12 * (4 - source_index), 0]
            motion_path = CubicBezier(
                start,
                start + 0.75 * RIGHT,
                end + 0.65 * LEFT + 0.35 * UP,
                end,
            )
            visible_path = DashedVMobject(motion_path.copy(), num_dashes=18).set_stroke(
                OMIT_GREY, width=2, opacity=0.8
            )
            omission_motion_paths.append(motion_path)
            omission_paths.add(visible_path)
            omitted_notes.add(sources[source_index].note.copy().set_opacity(0.75))

        self.play(
            FadeOut(formula),
            FadeOut(cost_label),
            FadeOut(search_badge),
            FadeIn(sink),
            run_time=0.65,
        )
        for note, visible_path, motion_path in zip(
            omitted_notes, omission_paths, omission_motion_paths
        ):
            self.add(note)
            self.play(
                Create(visible_path),
                MoveAlongPath(note, motion_path),
                run_time=0.75,
            )
            self.play(FadeOut(note, scale=0.45), run_time=0.25)

        self.play(
            sources[3].animate.set_opacity(0.28),
            sources[4].animate.set_opacity(0.28),
            possible_edges.animate.set_opacity(0.10),
            run_time=0.7,
        )

        result = Text(
            "preserve the outer voices  •  cover the harmony  •  avoid crossings",
            font="Avenir Next",
            font_size=25,
            color=INK,
            t2c={
                "outer voices": SOURCE_BLUE,
                "harmony": INNER_GOLD,
                "avoid crossings": BASS_GREEN,
            },
        ).to_edge(DOWN, buff=0.30)
        self.play(FadeOut(sink), FadeIn(result, shift=0.12 * UP), run_time=0.8)

        quartet_brace = Brace(targets, RIGHT, color=BASS_GREEN, buff=0.22)
        quartet_label = Text(
            "minimum-cost\npartial matching",
            font="Avenir Next",
            font_size=18,
            color=BASS_GREEN,
            line_spacing=0.85,
        ).next_to(quartet_brace, RIGHT, buff=0.18)
        self.play(GrowFromCenter(quartet_brace), FadeIn(quartet_label), run_time=0.75)
        self.play(
            LaggedStart(
                *[
                    Indicate(note, color=color, scale_factor=1.22)
                    for note, (_, _, color, _) in zip(final_score_notes, chosen)
                ],
                lag_ratio=0.14,
            ),
            run_time=1.4,
        )
        self.wait(1.8)
