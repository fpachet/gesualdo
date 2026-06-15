# Explainable Music AI Without Training Data

## AI-Assisted Construction of a Constraint-Based System for Reducing Gesualdo Madrigals

### Abstract

Carlo Gesualdo's late madrigals occupy a singular place in the history of
Western polyphony: they are famous for their chromatic intensity, harmonic
audacity, and expressive extremity, yet they remain rarely performed outside
specialized vocal contexts. This paper presents an ongoing project that
revisits these madrigals through automatic reduction for modern instrumental
ensembles, with string quartet as the primary target. The task appears at first
to be an assignment problem: source musical events must be transported from a
five-voice vocal texture into four instrumental parts. In practice, however,
the problem quickly exceeds a pure optimal-transport formulation. Every
assignment is entangled with musical constraints: preserving source
provenance, maintaining harmonic coverage, avoiding misleading doublings,
respecting instrumental sweet spots, preserving contrapuntal continuity,
deciding when sparse texture is preferable to artificial fullness, and
occasionally adding editorial material such as octave reinforcement or a
missing third.

The project also falls between two established AI paradigms. It is not a
machine-learning problem, because no paired corpus of Gesualdo madrigals and
expert quartet reductions exists from which to learn the transformation. But it
is not a classical expert system in the style of hand-authored rule bases
either. Although the final system can be described by an explicit set of
musical rules, those rules were not available in advance as a clean declarative
specification. They emerged through AI-assisted coding: a human expert listened
to and inspected concrete outputs, identified musically salient failures, and
used a coding assistant to operationalize successive refinements as algorithms,
parameters, tests, validation checks, and repair passes.

We describe the resulting deterministic symbolic reduction system, the musical
constraints it negotiates, and the retrospective rule set that now explains its
behavior. We argue that this mode of development constitutes a form of
emergent rule engineering: a way to build explainable, specialized music AI
systems when training data is absent and expert knowledge resists complete
pre-formalization. We also propose a reverse reconstruction experiment in which
the final textual rule description is given to a coding assistant to test
whether the working system can be recovered from its explicit explanation
alone. Such an experiment would measure the gap between post-hoc explanation
and procedural musical knowledge.

## 1. Introduction

Gesualdo's madrigals are among the most striking musical artifacts of the late
Renaissance. Their reputation rests not only on chromaticism in the abstract,
but on the way harmonic shocks, contrapuntal lines, and text-driven expression
combine into a volatile musical language. The madrigals are admired, analyzed,
and cited as landmarks of harmonic imagination. Yet they are not part of the
ordinary performance ecology of modern chamber music. They require trained
vocal ensembles, familiarity with late Renaissance text setting, and a
performing tradition that is distant from many instrumental contexts.

This project begins from a practical and musical question: can Gesualdo's
madrigals be revisited as playable instrumental music, specifically as string
quartets, without flattening the musical qualities that make them worth
revisiting? The goal is not to produce literal transcriptions, nor to compose
free fantasies on Gesualdo. It is to construct reductions that preserve as much
source material as possible while producing idiomatic, inspectable, playable
quartet scores.

The problem is deceptively hard. A typical source texture contains five vocal
voices; the target quartet has four instruments. The reduction must therefore
omit, merge, reassign, or occasionally supplement material. It must preserve
the outer lines where they carry structural identity, but it must also maintain
the harmonic evidence that makes Gesualdo's language recognizable. It must
avoid overfilling sparse textures, yet it must not allow important sonorities
to collapse into empty octaves or misleading fifths. It must respect the range
of the instruments, but also their preferred registers and characteristic
colors. It must avoid isolated fragments that arise from local coverage
choices, but it must sometimes borrow an idle target instrument to preserve a
continuing line. It must be faithful to the source, but source fidelity alone
does not define a good reduction.

At first sight, this looks like an optimization or optimal-transport problem.
Source notes must be assigned to target instruments, perhaps with costs for
register displacement, omitted pitch classes, voice crossing, and melodic
discontinuity. This view is useful, but incomplete. A note is not merely a unit
of mass to be transported. It may function as a suspension, a third, a doubled
fifth, a passing tone, an anchor, or the trace of an independent voice. Likewise
an empty target part is not simply unused capacity: it may be musically
appropriate restraint, or it may be a missed opportunity to restore a lost
strand. The reduction problem is therefore not only computational assignment,
but musical negotiation among conflicting obligations.

This paper presents a system built to negotiate those obligations. The system
is deterministic and symbolic. It parses source madrigals into note events,
chooses a global transposition for the target ensemble, preserves source-event
provenance, assigns outer and inner voices through cost-based heuristics,
optionally enriches texture with source-traceable restorations, and can add
explicitly marked editorial harmony such as missing thirds. It emits MusicXML
string-quartet reductions and validates the measured output to ensure that
parts contain no gaps, overlaps, overfull measures, or untraceable notes. The
current corpus contains 37 reductions from Gesualdo's fourth and sixth books of
madrigals, with rendered audio and a static review interface.

The technical contribution is not only the reducer. The project also exposes a
methodological point about AI-assisted construction of symbolic music systems.
The system is explainable in the sense that its decisions can be inspected,
tested, and described by an explicit rule set. But it was not built as a
classical expert system, where expert knowledge is first elicited as a compact
body of rules and then encoded. Instead, the rules emerged retrospectively from
an interactive development process. The human expert noticed concrete musical
failures; the coding assistant helped turn those judgments into code,
parameters, tests, and validation. The resulting system is therefore an
explainable procedural expert system whose knowledge is distributed across
implementation choices rather than centralized in a declarative rule base.

The paper makes three claims:

1. Gesualdo-to-quartet reduction is a low-data musical transformation problem
   that cannot be naturally addressed by supervised machine learning.
2. The task also resists a classical expert-system formulation because the
   relevant musical knowledge is conditional, conflicting, contextual, and only
   partly articulable in advance.
3. AI-assisted coding enables emergent formalization: expert musical judgment
   can be progressively operationalized through interaction with working
   outputs, producing a deterministic and explainable system after the fact.

## 2. Why This Is Not a Standard Machine-Learning Problem

Many recent music AI systems are built around data: paired examples,
self-supervised corpora, or large-scale generative models. The present task has
a different structure. There is no dataset of Gesualdo madrigals paired with
expert string-quartet reductions. Indeed, such a dataset is unlikely to exist
at useful scale. Even if a few hand reductions were created, they would encode
the taste of particular arrangers rather than a stable training distribution.

The lack of data is not incidental. It is part of the musical situation. The
system is meant to explore a rare transformation of a specific historical
repertoire into a modern instrumental medium. The target output is too
specialized for generic score-generation models and too underrepresented for
supervised learning. A model trained on ordinary quartet writing would not know
which Gesualdo source events must be preserved; a model trained on Renaissance
polyphony would not know how to make the result idiomatic for strings. A
large-scale model might produce plausible musical surface, but it would not
provide the provenance guarantees that are central to this project.

Provenance is crucial. For most emitted notes, the system must be able to say:
this note comes from this source event, at this offset, with this duration and
pitch class. Generated material, when allowed, must be explicitly marked as
editorial. This requirement is not merely technical. It is an ethical and
musicological constraint on the reduction: the output should remain
inspectably connected to Gesualdo's text, not merely inspired by it.

The no-data condition therefore motivates symbolic construction. But symbolic
construction does not automatically imply a traditional expert system.

## 3. Why This Is Not a Classical Expert System

There is a tempting analogy between this reducer and classical rule-based
music systems such as Ebcioglu's work on chorale harmonization. Both concern
musical expertise, symbolic representation, and explicit constraints. But the
analogy quickly breaks down.

In a harmonization system, the task can often be framed as generating voices
from a given melody under a style grammar: chord choices, voice-leading rules,
doubling conventions, cadence formulas, and constraints on forbidden parallels.
The rule set may be large and sophisticated, but the task has a relatively
stable formal identity.

Madrigal reduction is different. It is a lossy transformation of an existing
polyphonic object. The system must decide what to preserve, what to omit, what
to reassign, what to compress, when to leave a target part silent, and when to
add editorial support. These decisions do not follow from a single grammar of
correctness. They depend on the local source texture, the target instrument,
the continuation of lines, the harmonic function of omitted notes, and the
perceptual result.

Several constraints are identifiable:

- source provenance: output notes should usually derive from real source
  events;
- pitch-class coverage: important active source pitch classes should not be
  lost unnecessarily;
- outer-voice preservation: the highest and lowest source lines often carry
  structural identity;
- active-voice preservation: where the source has rich texture, the reduction
  should not collapse it without reason;
- range feasibility: target instruments must be able to play the notes;
- sweet-spot preference: feasible notes are not equally idiomatic or
  expressive in all registers;
- continuity: target parts should behave as lines, not as collections of
  isolated chord fillers;
- voice-order stability: similar source material should not bounce
  arbitrarily between instruments;
- anti-crossing pressure: instrumental lines should avoid avoidable crossing
  and registral confusion;
- anti-doubling pressure: duplicate pitch classes, doubled thirds, and bare
  fifths may be undesirable depending on context;
- editorial restraint: generated harmony should be distinguishable and should
  not merely fill the page;
- textural freedom: redundant octaves or invented thirds may sometimes be
  musically preferable to source-literal thinness.

The difficulty is that these are not simple hard rules. "Avoid doubled thirds"
is not always correct. "Preserve all source voices" is impossible with four
instruments and often musically undesirable. "Do not invent notes" is a strong
default, but optional editorial thirds can sometimes produce a more plausible
quartet sonority than another doubled fifth. "Prefer source material" must
coexist with "make the result playable." Each constraint is a pressure whose
priority changes with musical context.

The resulting knowledge does not naturally fit a clean rule base. Some of it
is expressed as hard validation. Some is expressed as local cost terms. Some is
encoded by the ordering of passes. Some lives in thresholds, weights,
candidate-generation strategies, pruning rules, and tests. Some was discovered
only by listening to failures.

This distribution of knowledge is one reason AI-assisted coding matters.

## 4. The Reduction Problem as Musical Negotiation

The transport view remains useful. At a given source onset, active source
events compete for limited target capacity. A candidate assignment can be
scored by costs: pitch displacement, range violation, register preference,
melodic distance from a previous target note, crossing penalty, and pitch-class
coverage. The system can search candidate transpositions and assignments, then
choose low-cost options.

But the transport metaphor must be expanded. In ordinary optimal transport,
mass is conserved or transformed according to a formal cost. In musical
reduction, the objects being transported have functions that are not fully
represented by pitch and duration. A source note may be important because it is
the first attack after a suspension, because it supplies a third in an
otherwise empty sonority, because it belongs to a line that has been audible
for several measures, or because omitting it changes the perceived harmonic
shock. Conversely, a note may be safely omitted if it merely duplicates an
already represented pitch class in a texture where doubling would weaken the
quartet writing.

We therefore describe the task as constrained musical negotiation. The system
negotiates among:

- conservation and compression: preserving source material while reducing
  five voices to four;
- source fidelity and instrumental idiom: retaining pitch classes, rhythms,
  and lines while fitting string ranges and colors;
- harmonic evidence and contrapuntal identity: preserving sonorities without
  turning lines into static chords;
- restraint and enrichment: leaving space when the source is sparse, but
  restoring or adding material when the target texture becomes misleading;
- local and longer-range coherence: making good choices at a given onset
  without producing unmusical discontinuities in the following measures.

This framing explains why a single formalism is insufficient. Pure optimal
transport captures assignment but not musical semantics. Classical rules
capture some expert constraints but not their many exceptions and trade-offs.
Machine learning would require data that does not exist and would weaken
source-traceable control. The system combines elements of all three without
being reducible to any one of them.

## 5. System Overview

The current system reduces Gesualdo madrigal MIDI files into MusicXML for
string quartet and related ensembles. Its main reduction mode is conservative:
most output notes are copied from real source events and retain provenance.
Generated material is optional and explicitly marked as editorial.

The pipeline contains the following stages.

### 5.1 Source Event Extraction

The input score is parsed into exact source events: note starts, durations,
pitch classes, source voice identifiers, ties, bar boundaries, time signatures,
key signatures, and voice ranges. The reduction operates on these events rather
than on an unstructured note stream. This representation allows the system to
validate later that emitted notes remain traceable to the source.

### 5.2 Global Transposition

The system chooses a global transposition unless one is forced. Candidate
transpositions are scored against the target ensemble. The score favors
playable ranges, preferred instrumental registers, small octave displacement,
and limited global movement away from the source pitch level. Long notes are
weighted more strongly than short notes, because sustained structural tones
expose register problems more clearly than passing tones.

### 5.3 Outer-Voice Preservation

For quartet reduction, the highest source voice by median pitch is assigned to
Violin I and the lowest source voice to Cello. This preserves the outer
contours that often define the contrapuntal and registral frame of the
madrigal. These assignments are not merely mechanical: later passes may borrow
idle outer instruments when doing so improves coverage and continuity.

### 5.4 Middle-Voice Selection

The remaining source voices are selectively reduced into Violin II and Viola.
At each source onset, the system prefers source events that add pitch classes
not already covered by the outer voices or previously selected inner notes. It
favors fresh attacks over tied continuations, prefers tones that clarify or
widen the sonority, and avoids unnecessary pitch-class duplication.

Selected candidates are assigned to target instruments by minimizing a musical
cost combining register fit, melodic continuity, pitch displacement, and
voice-order stability.

### 5.5 Borrowing and Continuity Repair

When an outer instrument is idle, it may temporarily borrow uncovered inner
source material. This increases capacity, but only under continuity pressure:
borrowed notes should behave like a line rather than as stray chord fillers.
Isolated borrowed events can be pruned if they lack nearby support in the same
source voice.

This rule illustrates the difficulty of the task. Borrowing is not simply a
capacity expansion; it is musically acceptable only when it produces a
plausible instrumental gesture.

### 5.6 Source-Traceable Enrichment

An optional enrichment mode attempts to preserve the number of active source
voices when the plain quartet reduction has collapsed a richer texture. This
mode still copies real source events; it does not invent harmony. It prioritizes
unrepresented source voices and permits duplicate pitch classes only when
there is enough musical context.

### 5.7 Editorial Harmony and Missing Thirds

A more interventionist optional mode can add editorial support tones to idle
strings. These notes are generated and marked as such. The system requires a
minimum duration, a genuinely free target instrument, and a source sonority
rich enough to justify support.

A narrower submode detects bare fifth shells and may add a missing third. When
possible, it chooses the third that appears later in the source; otherwise it
uses a pragmatic default. The invented third is fitted to the target string's
range and preferred register.

This feature is musically revealing. From a source-literal perspective,
inventing a third is suspicious. From a quartet-writing perspective, however,
the alternative may be a weak doubled fifth or octave. The system therefore
marks such material as editorial rather than pretending it is source-derived.

### 5.8 Dynamics and Validation

An optional editorial dynamics layer estimates a coarse bar-level energy
contour from active part count, attack density, register, and registral span.
It adds visible MusicXML dynamics and local hairpins. This layer does not alter
note choice.

Finally, the measured output is validated. Each part must have the expected bar
count, no gaps or overlaps, no overfull measures, and no untraceable notes.
Validation is part of the musical argument: the system is not only generative,
but inspectable and accountable.

## 6. AI-Assisted Coding as Emergent Rule Engineering

The final system can be described as a set of rules. A textual rule document
now exists and explains the main principles: preserve the madrigal before
improving the quartet texture, choose global transposition by target fit,
preserve outer voices, prefer uncovered pitch classes, prune isolated borrowed
events, distinguish source-traceable enrichment from editorial harmony, and so
on.

However, this document is retrospective. It was not the original specification.
The development process proceeded differently. A musical problem appeared in a
concrete output: a texture sounded thin, a viola line contained an isolated
pickup, an octave doubling felt less convincing than a generated third, or a
technically playable note sat outside an instrument's expressive sweet spot.
The human expert described the problem in musical language. The coding
assistant proposed implementation strategies, modified code, added tests, and
helped regenerate outputs. Through this loop, informal musical judgments became
procedural constraints.

This is not the usual workflow of expert systems. In a classical expert-system
approach, one attempts to elicit domain knowledge first and then encode it as a
rule base. That approach assumes that the expert can state the relevant rules
in advance. In this project, many rules became visible only after hearing or
seeing the system fail.

Examples include:

- borrowing an idle outer string is useful, but only when the borrowed material
  forms a continuing line;
- duplicate pitch classes are sometimes legitimate source preservation, but
  not when they merely inflate a unison texture;
- editorial thirds are dangerous in principle, yet sometimes preferable to a
  hollow quartet sonority;
- a note may be in range but still outside an instrument's persuasive register;
- a local coverage improvement may create an implausible instrumental gesture;
- generated support should merge across internal segmentation so the score does
  not display artificial repeated notes.

These constraints are too situated to be cleanly prescribed before
implementation. But they can be discovered and stabilized through interaction.
We call this process emergent rule engineering. The rule set emerges from the
joint activity of musical judgment, coding assistance, test construction,
output inspection, and listening.

The resulting system is explainable, but its explanation is not equivalent to
its specification. Nor is the explanation simply the source code. The musical
knowledge is distributed across:

- explicit conditionals and algorithms;
- cost functions and weights;
- ordering of passes;
- pruning and repair procedures;
- validation checks;
- tests encoding previously observed failures;
- example outputs and listening decisions;
- retrospective prose documentation.

This distributed structure is central to the paper's claim. AI-assisted coding
does not merely accelerate implementation. It changes what can be implemented:
it allows a specialized symbolic system to grow around musical failures that
would be difficult to enumerate preemptively.

## 7. Development Episodes

The methodological claim becomes clearer when viewed through concrete
development episodes. In each case, the starting point was not a pre-existing
formal rule, but an observed musical inadequacy. The final implementation then
left several traces: code, parameters, tests, and eventually prose rules.

### 7.1 Borrowing an Idle Outer String

An early version of the quartet reduction preserved the highest and lowest
source voices as Violin I and Cello, then compressed the remaining voices into
Violin II and Viola. This was musically conservative, but it created a problem:
when an outer source voice rested, the corresponding quartet instrument also
rested, even if an important middle line was being omitted because the two
inner instruments were already occupied.

The first obvious repair was to use the idle outer string as extra capacity.
But this naive rule produced unconvincing results. If an idle Violin I or Cello
grabbed a single uncovered note merely to improve harmonic coverage at one
onset, the result sounded like a stray chord filler rather than an instrumental
line. The musical judgment was therefore more subtle: borrowing is acceptable
when the borrowed material forms a continuous gesture, not when it produces an
isolated event.

This became a procedural rule. The system can borrow idle outer targets for
uncovered source material, but borrowed events are later pruned unless they
have nearby borrowed neighbors in the same source voice. The rule is not a
simple declarative constraint such as "outer parts may borrow." It combines
candidate generation, target-capacity reasoning, source-voice identity, local
continuity, and a repair pass. Its current textual form is clear, but that
clarity came after the implementation stabilized the musical distinction.

### 7.2 Preserving Active Voices Without Inflating Unisons

Another episode concerned source density. A plain four-part reduction can
collapse a rich five-voice source texture into too few active quartet parts.
The intuitive musical request was to preserve more of the active source voices.
This led to the `preserve_active_voice_count` option, which restores omitted
source events when the source has more active voices than the reduction
currently represents.

The first version of this idea risks a common failure: preserving active voice
count can become mere page filling. If the source sonority contains only one
pitch class, adding another octave or unison duplicate may technically preserve
another source voice, but it does not necessarily improve the quartet. It can
make a sparse pickup sound artificially swollen or harmonically misleading.

The resulting constraint is contextual. Duplicate pitch classes can be
preserved when they represent an independent source line in a richer sonority,
but a bare unison or octave does not justify adding another target part merely
to increase density. In addition, duplicate-pitch restorations may be shortened
at the next real source change so they do not obscure later chromatic events.

This episode illustrates why the problem resists a flat rule list. "Preserve
active voices" and "avoid duplicate pitch classes" are both musically
reasonable, but neither is correct by itself. The system encodes the compromise
as a set of interacting conditions rather than as a single principle.

### 7.3 Inventing a Third, but Marking It as Editorial

The most delicate episode involved missing thirds. The conservative system
prefers real source notes and avoids inventing harmony. Yet some quartet
textures produced bare fifth shells or hollow doublings that sounded less
convincing than a modest editorial completion. From the standpoint of source
fidelity, adding a third is suspect. From the standpoint of instrumental
reduction, refusing to add one can produce a sonority that misrepresents the
musical effect.

The implemented compromise is intentionally narrow. Editorial thirds are only
considered as part of the editorial harmony layer. The system detects a bare
root-fifth shell, checks that no third is already present, and then prefers the
minor or major third that appears later in the source if such evidence exists.
If the source gives no immediate clue, it uses a pragmatic default. The
generated note is placed in a playable register and marked internally as
generated, not as source-derived.

This is a good example of post-hoc explainability. The final prose rule can say
"detect bare fifth shells and add a missing third when justified." But the
actual musical knowledge is distributed across shell detection, future-source
lookahead, range fitting, target availability, generated-note provenance, and
the user's judgment that this kind of intervention is acceptable only when it
remains explicit.

### 7.4 Sweet Spots Rather Than Mere Ranges

A further episode concerned instrumental register. A simple reduction system
can treat range as a hard feasibility constraint: a note is either playable or
not. But string writing depends on more than feasibility. A pitch may be
playable by a violin, viola, or cello while still sitting in a register that
sounds awkward, weak, or unlike the intended instrumental role.

This led to a target-aware sweet-spot model. Candidate transpositions and
assignments are scored not only by range validity but by preferred registers,
duration-weighted exposure, octave displacement, and continuity from previous
notes. In the five-part quartet-plus-viole variant, a specialized assignment
policy can remap inner voices while preserving outer voices, choosing the
mapping that best fits instrumental sweet spots and avoids unstable order
changes.

Again, the rule is easy to state after the fact: prefer idiomatic registers.
But the working version is procedural. It asks where the note can be placed,
how exposed it is, how much octave displacement is required, how the assignment
affects neighboring material, and whether preserving source order is worth a
less idiomatic register.

These episodes support the larger argument. The final system is explainable,
but its explanation emerged from accumulated encounters with musical failures.
Each failure forced a local formalization; each formalization interacted with
others; and the coding assistant made it feasible to keep iterating at the
level where musical judgment remained active.

## 8. Results

The current corpus contains 37 Gesualdo madrigals from books IV and VI. For
each source, the system generates a four-part string-quartet MusicXML reduction
and a rendered audio file. The retained batch completed successfully according
to its report: all outputs have four reduced parts, consistent measure counts
across parts, and no validation errors.

The system also provides comparison variants for selected pieces:

- a plain conservative quartet reduction;
- a source-enriched reduction preserving additional active source voices;
- a source-plus-harmony variant with generated editorial support;
- a source-plus-thirds variant that can add missing thirds to bare fifth
  shells.

These variants are important because they expose the musical trade-offs. A
plain reduction maximizes provenance and restraint, but may sound thin. A
source-enriched version restores omitted source material, but can introduce
doublings. Editorial harmony improves quartet texture, but moves away from
strict source derivation. Editorial thirds can make a sonority more convincing
for strings, but must be marked as generated.

The result is not a single "correct" reduction. It is a controllable family of
reductions organized by different attitudes toward source fidelity and
instrumental idiom.

## 9. Evaluation Plan

The project currently has generated outputs, validation, tests, and a review
interface. A full paper should add systematic evaluation. We propose three
levels.

### 9.1 Technical Validity

The first level measures whether outputs are structurally valid:

- successful generation rate over the 37-piece corpus;
- absence of gaps, overlaps, and overfull measures;
- measure-count consistency across parts;
- proportion of source-traceable versus editorial notes;
- range and preferred-register statistics;
- number of unresolved validation errors.

This level establishes that the system produces usable symbolic artifacts.

### 9.2 Musical Constraint Metrics

The second level evaluates musical pressures:

- pitch-class coverage relative to active source sonorities;
- rate and location of omitted active voices;
- duplicate pitch-class frequency;
- doubled-third and bare-fifth frequency;
- voice-crossing events;
- melodic discontinuity in each target part;
- isolated singleton notes before and after pruning;
- use of idle target capacity;
- density differences among plain, source-enriched, and editorial variants.

These metrics do not replace musical judgment, but they make the trade-offs
visible.

### 9.3 Expert Review

The third level uses expert listeners or performers. Conductors, quartet
players, or musicologists can rate reductions along dimensions such as:

- playability;
- preservation of source identity;
- harmonic intelligibility;
- contrapuntal continuity;
- quartet idiom;
- musical coherence;
- acceptability of editorial additions.

Blind comparisons between variants would be especially useful. The question is
not whether one variant is universally best, but whether different constraint
settings produce musically interpretable differences.

## 10. Reverse Reconstruction Experiment

The existence of a retrospective rule document invites a further experiment.
If the final textual rule description is given to a coding assistant, can the
assistant reconstruct a system that performs as well as the current one?

This experiment directly tests the gap between explicit explanation and
procedural knowledge. We propose four reconstruction conditions:

1. rules only: the assistant receives the textual rule document and input/output
   format requirements, but not the implementation;
2. rules plus tests: the assistant receives the rule document and the unit
   tests;
3. rules plus examples: the assistant receives the rule document and a small
   number of input/output pairs;
4. iterative reconstruction: the assistant can inspect failures on the corpus
   and revise the implementation over several rounds.

The reconstructed systems would be compared against the original along the
technical and musical metrics above. We expect the rules-only system to capture
the broad architecture but fail on many musically salient edge cases. The
difference would quantify how much expertise resides outside the textual rule
set: in ordering, weights, corner cases, tests, and accumulated listening
decisions.

This experiment would sharpen the paper's methodological claim. The final rule
set is useful and explanatory, but it is not the same thing as the working
system. AI-assisted construction does not merely translate a specification into
code; it helps discover the specification through code.

## 11. Discussion

The project suggests a middle path for music AI. Many musically valuable tasks
do not have enough data for machine learning. Many also resist classical
expert-system engineering because the relevant knowledge is tacit,
conflicting, and context-dependent. AI-assisted coding offers a practical
alternative: build a deterministic symbolic system iteratively, using concrete
musical failures as knowledge-elicitation events.

This does not eliminate the need for expertise. On the contrary, the system
depends on expert judgment at every stage. The coding assistant supplies
implementation leverage, not musical authority. It makes it feasible to turn
small, situated judgments into functioning code quickly enough for the expert
to remain in the loop.

The result is an unusual kind of explainable AI system. It is not explainable
because it was specified as a rule base from the beginning. It is explainable
because its behavior is inspectable after construction: source events are
traceable, generated notes are marked, validation checks are explicit, and the
procedures can be read and modified. Explanation is post-hoc, but not merely
rationalizing an opaque model. It is a retrospective account of a transparent
procedural artifact.

This distinction matters for creative AI research. In many discussions,
explainability and machine learning are opposed: learned models are powerful
but opaque, while symbolic systems are interpretable but laborious and brittle.
The present project suggests another axis. AI-assisted coding can reduce the
labor of symbolic construction while preserving inspectability. It can make
small, specialized, low-data creative systems viable again.

## 12. Limitations

The current system remains local in important ways. It does not solve one
global optimization over an entire madrigal. Some decisions are made at source
onsets with limited lookahead, then adjusted by pruning and repair passes.
Although this has produced musically convincing results, longer-range planning
could improve continuity and large-scale texture.

The editorial harmony rules are intentionally conservative but still debatable.
Inventing a third, even when marked, changes the source. Future versions should
make editorial interventions more configurable and more clearly visible in the
score.

Evaluation is not yet complete. The system has corpus-scale generation,
validation, tests, and listening examples, but a publishable version should
include systematic ablations and expert review.

Finally, the development process itself needs stronger documentary evidence.
The episodes above should eventually be backed by concrete before-and-after
outputs, commit history, test names, or score excerpts showing how a musical
failure led to a new constraint, parameter, or repair pass.

## 13. Conclusion

Gesualdo reduction for string quartet is a small but revealing music AI
problem. It has no training data, resists clean declarative formalization, and
cannot be reduced to pure optimal transport. It requires source-traceable
assignment under conflicting musical constraints, with occasional editorial
freedom and constant attention to instrumental idiom.

The system described here shows that AI-assisted coding can make such problems
tractable. Through iterative interaction, tacit musical judgments become
operational constraints. The resulting system is explainable, deterministic,
and inspectable, but its rule set emerges after the fact rather than preceding
the implementation.

The broader claim is that low-data creative AI need not choose between opaque
machine learning and brittle classical expert systems. There is a third path:
AI-assisted construction of specialized symbolic systems, where code becomes
the medium through which expert knowledge is discovered, tested, and
stabilized.

## Possible Titles

- Explainable Music AI Without Training Data: AI-Assisted Construction of a
  Constraint-Based Gesualdo Reduction System
- After Expert Systems, Before Training Data: AI-Assisted Symbolic Music
  Reduction
- Reduction Without Training Data: Emergent Rule Engineering for Gesualdo
  Madrigals
- Constrained Musical Negotiation: Reducing Gesualdo Madrigals for String
  Quartet
- From Tacit Judgment to Procedural Rules: AI-Assisted Coding of a Symbolic
  Music Reduction System

## Venue Framing Notes

For ICCC, foreground computational creativity without training data,
AI-assisted symbolic system building, and emergent rule engineering.

For ISMIR or TISMIR, foreground formal task definition, symbolic music
processing, corpus-scale evaluation, ablations, and expert ratings.

For MCM or Journal of Mathematics and Music, foreground multi-objective
constraint negotiation, transport-like assignment, and the limits of formal
optimization in musical reduction.

For DLfM, foreground the corpus, MusicXML artifacts, source provenance,
reproducibility, and the review interface.

## Citation Placeholders

- Carlo Gesualdo, madrigals, books IV and VI.
- Ebcioglu's expert-system work on chorale harmonization.
- Literature on algorithmic arrangement and reduction.
- Literature on symbolic music AI and constraint-based composition.
- Literature on explainable AI and human-in-the-loop creative systems.
- Literature on optimal transport or assignment formulations in music, if a
  directly relevant source is identified.
