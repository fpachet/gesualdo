"""Animate optimal-transport search with real one-bar score engravings.

Render with:

    manim -pqm animations/actual_score_transport.py ActualScoreTransport

The left-hand six-part source bar remains fixed.  The quartet bar on the right
morphs as the search tries, rejects, and backtracks from alternative reductions.
The SVG notation is engraved from MusicXML by ``generate_actual_score_assets.py``.
"""

from __future__ import annotations

from pathlib import Path

from manim import *


BG = "#0B0F14"
CARD = "#111821"
INK = "#F2F4F8"
MUTED = "#98A2B3"
FAINT = "#344054"
BLUE = "#58C4DD"
GOLD = "#F4D35E"
GREEN = "#83C167"
RED = "#FF5A5F"
ORANGE = "#FF9F1C"

ASSETS = Path(__file__).resolve().parent / "assets" / "actual_score"


def engraved_score(name: str, height: float, center: np.ndarray) -> ImageMobject:
    score = ImageMobject(str(ASSETS / f"{name}.png"))
    score.set_opacity(0.96)
    score.scale_to_fit_height(height)
    score.move_to(center)
    return score


def pill(text: str, color: str, center: np.ndarray, width: float = 2.35) -> VGroup:
    box = RoundedRectangle(
        width=width,
        height=0.46,
        corner_radius=0.12,
        color=color,
        stroke_width=1.6,
    ).set_fill(BG, opacity=0.96)
    box.move_to(center)
    label = Text(
        text,
        font="Avenir Next",
        font_size=18,
        color=color,
    ).move_to(box)
    return VGroup(box, label)


class ActualScoreTransport(Scene):
    """One fixed source bar and one quartet bar that changes under search."""

    def construct(self):
        self.camera.background_color = BG

        title = Text(
            "Optimal transport explores score reductions",
            font="Avenir Next",
            weight=MEDIUM,
            font_size=40,
            color=INK,
        ).to_edge(UP, buff=0.24)
        title_rule = Line(LEFT * 5.9, RIGHT * 5.9, color=FAINT, stroke_width=1)
        title_rule.next_to(title, DOWN, buff=0.14)

        left_card = RoundedRectangle(
            width=6.25,
            height=5.55,
            corner_radius=0.18,
            color=BLUE,
            stroke_width=1.4,
        ).set_fill(CARD, opacity=0.72)
        left_card.move_to([-3.38, -0.03, 0])

        right_card = RoundedRectangle(
            width=6.25,
            height=5.55,
            corner_radius=0.18,
            color=FAINT,
            stroke_width=1.4,
        ).set_fill(CARD, opacity=0.72)
        right_card.move_to([3.38, -0.03, 0])

        left_header = Text(
            "FIXED SOURCE  ·  ONE BAR  ·  SIX VOICES",
            font="Avenir Next",
            font_size=17,
            color=BLUE,
        ).move_to([-3.38, 2.39, 0])
        right_header = Text(
            "WORKING REDUCTION  ·  STRING QUARTET",
            font="Avenir Next",
            font_size=17,
            color=MUTED,
        ).move_to([3.38, 2.39, 0])

        lock_box = RoundedRectangle(
            width=0.62,
            height=0.34,
            corner_radius=0.08,
            color=BLUE,
            stroke_width=1.1,
        ).set_fill(BG, opacity=0.9)
        lock_box.move_to(left_card.get_corner(UL) + [0.48, -0.38, 0])
        lock_text = Text(
            "FIXED", font="Avenir Next", font_size=12, color=BLUE
        ).move_to(lock_box)
        lock = VGroup(lock_box, lock_text)

        source_score = engraved_score(
            "source", 4.42, np.array([-3.38, -0.03, 0])
        )
        crossing_target = engraved_score(
            "crossing", 3.72, np.array([3.38, -0.03, 0])
        )
        loss_target = engraved_score(
            "harmonic_loss", 3.72, np.array([3.38, -0.03, 0])
        )
        accepted_target = engraved_score(
            "accepted", 3.72, np.array([3.38, -0.03, 0])
        )

        def image_point(
            image: ImageMobject, x_ratio: float, y_ratio: float
        ) -> np.ndarray:
            """Address an engraved notehead by normalized image coordinates."""

            return np.array(
                [
                    image.get_left()[0] + x_ratio * image.width,
                    image.get_top()[1] - y_ratio * image.height,
                    0,
                ]
            )

        # First-beat noteheads in the rasterized engravings.  The source points
        # never move; every candidate supplies a new set of target assignments.
        source_note_points = [
            image_point(source_score, 0.565, ratio)
            for ratio in (0.055, 0.235, 0.420, 0.610, 0.795, 0.940)
        ]
        target_note_points = [
            image_point(crossing_target, 0.700, ratio)
            for ratio in (0.105, 0.350, 0.600, 0.850)
        ]

        def mapping_overlay(
            assignments: list[tuple[int, int]], colors: list[str]
        ) -> VGroup:
            arrows = VGroup()
            rings = VGroup()
            for (source_index, target_index), color in zip(assignments, colors):
                start = source_note_points[source_index]
                end = target_note_points[target_index]
                arrows.add(
                    Arrow(
                        start,
                        end,
                        buff=0.09,
                        color=color,
                        stroke_width=2.7,
                        max_tip_length_to_length_ratio=0.035,
                    ).set_opacity(0.88)
                )
                rings.add(
                    Circle(radius=0.105, color=color, stroke_width=2.0).move_to(start),
                    Circle(radius=0.105, color=color, stroke_width=2.0).move_to(end),
                )
            return VGroup(arrows, rings).set_z_index(5)

        crossing_mapping = mapping_overlay(
            [(1, 0), (0, 1), (2, 2), (5, 3)],
            [GOLD, BLUE, ORANGE, GREEN],
        )
        loss_mapping = mapping_overlay(
            [(0, 0), (1, 1), (3, 2), (5, 3)],
            [BLUE, GOLD, GOLD, GREEN],
        )
        accepted_mapping = mapping_overlay(
            [(0, 0), (1, 1), (2, 2), (5, 3)],
            [BLUE, GOLD, ORANGE, GREEN],
        )
        mapping_label = pill(
            "BEAT 1  ·  NOTE PROVENANCE",
            MUTED,
            np.array([0, 2.86, 0]),
            width=2.45,
        )

        question = Text(
            "?",
            font="Avenir Next",
            font_size=92,
            color=FAINT,
        ).move_to([3.38, 0.10, 0])
        source_caption = Text(
            "The source bar never changes",
            font="Avenir Next",
            font_size=18,
            color=MUTED,
        ).move_to([-3.38, -2.52, 0])

        combinations = MathTex(
            r"\binom{6}{4}4!=360\ \text{assignments per onset}",
            font_size=30,
            color=INK,
        ).to_edge(DOWN, buff=0.16)
        combinations.set_color_by_tex(r"360", GOLD)

        self.play(Write(title), Create(title_rule), run_time=0.9)
        self.play(
            FadeIn(left_card, shift=0.10 * RIGHT),
            FadeIn(right_card, shift=0.10 * LEFT),
            FadeIn(left_header),
            FadeIn(right_header),
            run_time=0.75,
        )
        self.play(
            FadeIn(source_score, shift=0.18 * RIGHT),
            FadeIn(lock, scale=0.9),
            FadeIn(source_caption),
            FadeIn(question, scale=0.8),
            FadeIn(combinations, shift=0.10 * UP),
            run_time=1.15,
        )
        self.wait(0.7)

        # First branch: the engraved quartet is real notation, but its upper
        # parts are assigned in reverse order and therefore cross.
        candidate_badge = pill(
            "TRY 137 / 360", BLUE, np.array([3.38, -2.42, 0])
        )
        current_score = crossing_target.copy()
        crossing_zone = RoundedRectangle(
            width=5.35,
            height=1.22,
            corner_radius=0.10,
            color=RED,
            stroke_width=2.2,
        ).set_fill(RED, opacity=0.035)
        crossing_zone.move_to([3.38, 1.03, 0])
        crossing_status = pill(
            "VOICE CROSSING  ·  +8.4",
            RED,
            np.array([3.38, -1.84, 0]),
            width=2.75,
        )

        self.play(
            FadeOut(question, scale=0.7),
            FadeIn(current_score, shift=0.24 * LEFT),
            FadeIn(candidate_badge, shift=0.08 * UP),
            FadeIn(mapping_label, shift=0.06 * DOWN),
            run_time=1.0,
        )
        self.play(
            LaggedStart(
                *[GrowArrow(arrow) for arrow in crossing_mapping[0]],
                lag_ratio=0.09,
            ),
            FadeIn(crossing_mapping[1]),
            run_time=0.85,
        )
        self.play(
            Create(crossing_zone),
            FadeIn(crossing_status, shift=0.08 * UP),
            right_card.animate.set_stroke(RED, width=1.8),
            run_time=0.55,
        )
        self.wait(0.65)

        backtrack_1 = Text(
            "REJECT  ↶  BACKTRACK",
            font="Avenir Next",
            font_size=17,
            color=RED,
        ).move_to(candidate_badge[1])
        self.play(
            Transform(candidate_badge[1], backtrack_1),
            current_score.animate.shift(0.20 * LEFT).set_opacity(0.30),
            LaggedStart(
                *[Uncreate(arrow) for arrow in reversed(crossing_mapping[0])],
                lag_ratio=0.07,
            ),
            FadeOut(crossing_mapping[1]),
            FadeOut(crossing_zone),
            FadeOut(crossing_status),
            run_time=0.65,
        )

        # Second branch: the notation visibly moves into a new realization.
        # It is orderly, but the viola now doubles the tenor G and loses the
        # distinctive Alto-II chromatic line.
        try_221 = pill("TRY 221 / 360", GOLD, candidate_badge.get_center())
        loss_zone = RoundedRectangle(
            width=5.35,
            height=0.78,
            corner_radius=0.10,
            color=RED,
            stroke_width=2.2,
        ).set_fill(RED, opacity=0.035)
        loss_zone.move_to([3.38, -0.48, 0])
        loss_status = pill(
            "UNIQUE INNER LINE LOST  ·  +5.1",
            RED,
            np.array([3.38, -1.84, 0]),
            width=3.38,
        )

        loss_score = loss_target.copy()
        self.play(
            Transform(candidate_badge[0], try_221[0]),
            Transform(candidate_badge[1], try_221[1]),
            FadeOut(current_score, shift=0.22 * LEFT),
            FadeIn(loss_score, shift=0.22 * RIGHT),
            LaggedStart(
                *[GrowArrow(arrow) for arrow in loss_mapping[0]],
                lag_ratio=0.08,
            ),
            FadeIn(loss_mapping[1]),
            right_card.animate.set_stroke(GOLD, width=1.8),
            run_time=1.25,
            rate_func=smooth,
        )
        current_score = loss_score
        self.play(
            Create(loss_zone),
            FadeIn(loss_status, shift=0.08 * UP),
            run_time=0.55,
        )
        self.wait(0.65)

        backtrack_2 = Text(
            "REJECT  ↶  BACKTRACK",
            font="Avenir Next",
            font_size=17,
            color=RED,
        ).move_to(candidate_badge[1])
        self.play(
            Transform(candidate_badge[1], backtrack_2),
            current_score.animate.shift(0.20 * LEFT).set_opacity(0.30),
            LaggedStart(
                *[Uncreate(arrow) for arrow in reversed(loss_mapping[0])],
                lag_ratio=0.07,
            ),
            FadeOut(loss_mapping[1]),
            FadeOut(loss_zone),
            FadeOut(loss_status),
            run_time=0.65,
        )

        # Third branch: the four-staff score moves once more, retaining the
        # outer parts and the unique chromatic inner voice.
        try_284 = pill("TRY 284 / 360", GREEN, candidate_badge.get_center())
        accepted_score = accepted_target.copy()
        self.play(
            Transform(candidate_badge[0], try_284[0]),
            Transform(candidate_badge[1], try_284[1]),
            FadeOut(current_score, shift=0.22 * LEFT),
            FadeIn(accepted_score, shift=0.22 * RIGHT),
            LaggedStart(
                *[GrowArrow(arrow) for arrow in accepted_mapping[0]],
                lag_ratio=0.08,
            ),
            FadeIn(accepted_mapping[1]),
            right_card.animate.set_stroke(GREEN, width=2.0),
            run_time=1.25,
            rate_func=smooth,
        )
        current_score = accepted_score

        accepted_status = pill(
            "BEST COST 4.2  ✓",
            GREEN,
            np.array([3.38, -1.84, 0]),
            width=2.35,
        )
        final_rule = Text(
            "outer voices fixed  •  chromatic line retained  •  no crossing",
            font="Avenir Next",
            font_size=23,
            color=INK,
            t2c={
                "outer voices": BLUE,
                "chromatic line": GOLD,
                "no crossing": GREEN,
            },
        ).to_edge(DOWN, buff=0.18)

        self.play(
            FadeIn(accepted_status, shift=0.08 * UP),
            FadeOut(combinations, shift=0.06 * DOWN),
            FadeIn(final_rule, shift=0.06 * UP),
            mapping_label[0].animate.set_stroke(GREEN, width=1.4),
            run_time=0.75,
        )
        self.play(
            Circumscribe(source_score, color=BLUE, fade_out=True, time_width=0.7),
            Circumscribe(current_score, color=GREEN, fade_out=True, time_width=0.7),
            run_time=1.25,
        )
        self.wait(0.8)

        # Final section: make the meaning of "optimal" explicit.  The musical
        # score is judged by a declared rule set R; each rule contributes a
        # weighted penalty, and the selected plan has the smallest total.
        summary_title = Text(
            "Why this reduction is optimal",
            font="Avenir Next",
            weight=MEDIUM,
            font_size=40,
            color=INK,
        ).move_to(title)
        solution_header = Text(
            "SELECTED SOLUTION  ·  PLAN 284",
            font="Avenir Next",
            font_size=17,
            color=GREEN,
        ).move_to([-3.38, 2.39, 0])

        rules_card = RoundedRectangle(
            width=6.25,
            height=5.55,
            corner_radius=0.18,
            color=GOLD,
            stroke_width=1.6,
        ).set_fill(CARD, opacity=0.76)
        rules_card.move_to([3.38, -0.03, 0])
        rules_header = Text(
            "DECLARED RULE SET  R",
            font="Avenir Next",
            font_size=18,
            color=GOLD,
        ).move_to([3.38, 2.39, 0])
        cost_formula = MathTex(
            r"C(\pi)=\sum_{r\in\mathcal R}w_r\,p_r(\pi)",
            font_size=31,
            color=INK,
        ).move_to([3.38, 1.86, 0])
        cost_formula.set_color_by_tex(r"\mathcal R", GOLD)

        rule_specs = [
            ("outer voices preserved", "0.0", GREEN),
            ("voice crossing", "0.0", GREEN),
            ("harmonic loss", "0.6", GOLD),
            ("register displacement", "1.1", BLUE),
            ("melodic discontinuity", "1.3", ORANGE),
            ("omit covered duplicates", "1.2", MUTED),
        ]
        rule_rows = VGroup()
        for index, (rule, value, color) in enumerate(rule_specs):
            y = 1.30 - 0.43 * index
            marker = Dot(radius=0.045, color=color).move_to([0.78, y, 0])
            rule_text = Text(
                rule,
                font="Avenir Next",
                font_size=18,
                color=INK,
            ).move_to([3.03, y, 0], aligned_edge=LEFT)
            rule_text.align_to([1.02, y, 0], LEFT)
            value_text = Text(
                value,
                font="Avenir Next",
                font_size=19,
                color=color,
            ).move_to([5.63, y, 0], aligned_edge=RIGHT)
            rule_rows.add(VGroup(marker, rule_text, value_text))

        total_rule = Line(
            [0.80, -1.17, 0], [5.75, -1.17, 0], color=FAINT, stroke_width=1.2
        )
        total_label = Text(
            "TOTAL COST",
            font="Avenir Next",
            font_size=20,
            color=INK,
        ).move_to([1.02, -1.48, 0], aligned_edge=LEFT)
        total_value = Text(
            "4.2",
            font="Avenir Next",
            font_size=27,
            color=GREEN,
            weight=BOLD,
        ).move_to([5.63, -1.48, 0], aligned_edge=RIGHT)
        optimum_formula = MathTex(
            r"\pi^*=\arg\min_{\pi\in\mathrm{feasible}}C(\pi)",
            r"\quad C(\pi^*)=4.2",
            font_size=27,
            color=INK,
        ).move_to([3.38, -2.06, 0])
        optimum_formula.set_color_by_tex(r"\pi^*", GREEN)
        optimum_formula.set_color_by_tex(r"4.2", GREEN)

        searched_caption = Text(
            "all 360 assignments evaluated or pruned",
            font="Avenir Next",
            font_size=17,
            color=MUTED,
        ).move_to([-3.38, -1.86, 0])
        solution_badge = pill(
            "MINIMUM TOTAL COST  ·  4.2",
            GREEN,
            np.array([-3.38, -2.38, 0]),
            width=3.55,
        )
        precise_claim = Text(
            "OPTIMAL under the declared rules R and weights w",
            font="Avenir Next",
            font_size=25,
            color=INK,
            t2c={"OPTIMAL": GREEN, "rules R": GOLD, "weights w": BLUE},
        ).to_edge(DOWN, buff=0.17)

        self.play(
            Transform(title, summary_title),
            FadeOut(left_card),
            FadeOut(left_header),
            FadeOut(lock),
            FadeOut(source_score, shift=0.16 * LEFT),
            FadeOut(source_caption),
            FadeOut(accepted_mapping[0]),
            FadeOut(accepted_mapping[1]),
            FadeOut(mapping_label),
            FadeOut(candidate_badge),
            FadeOut(accepted_status),
            FadeOut(final_rule),
            Transform(right_header, solution_header),
            right_card.animate.move_to([-3.38, -0.03, 0]).set_stroke(GREEN, width=1.8),
            current_score.animate.scale(0.92).move_to([-3.38, 0.24, 0]),
            FadeIn(rules_card, shift=0.18 * LEFT),
            FadeIn(rules_header),
            run_time=1.35,
        )
        self.play(
            FadeIn(cost_formula, shift=0.08 * DOWN),
            LaggedStart(
                *[FadeIn(row, shift=0.10 * RIGHT) for row in rule_rows],
                lag_ratio=0.10,
            ),
            run_time=1.35,
        )
        self.play(
            Create(total_rule),
            FadeIn(total_label),
            FadeIn(total_value, scale=1.15),
            FadeIn(searched_caption),
            FadeIn(solution_badge, shift=0.08 * UP),
            run_time=0.8,
        )
        self.play(
            Write(optimum_formula),
            FadeIn(precise_claim, shift=0.08 * UP),
            run_time=1.0,
        )
        self.play(
            Indicate(total_value, color=GREEN, scale_factor=1.22),
            Indicate(solution_badge, color=GREEN, scale_factor=1.05),
            run_time=1.0,
        )
        self.wait(2.0)
