# The AutoBenchmark Method, in Detail

Source: Section 1, Appendix A, and Appendix B of Li et al., *Aligning
Autoresearch: Co-Improvement between Agents and Humans*, arXiv:2610.38882.
Section references like [1.2] or [A.1] point at the paper.

## 0. What problem this solves

Benchmark creation by hand is slow: a designer decides what capability to
measure (the *construct*), finds grounding material to build tasks from,
writes tasks plus a reference solution plus grading criteria, runs solvers,
and iterates. AutoBenchmark hands this whole job to an autoresearch agent
and studies two things at once: the benchmarks the agent produces, and how
much human direction improves them. The target domain in the paper is
benchmarks that evaluate autoresearch agents themselves [1.1, 1.2].

The headline findings, stated up front because they shape the design:

- Unaided, the agent produces benchmarks that are close to saturated:
  solvers score above 80, and Claude Opus 5 scores 98.0 on the best
  checkpoint of the fully autonomous run [1.1, Table 1].
- Detailed human direction at the proposal stage roughly halves solver
  scores. A one-sentence statement of intent barely helps [1.1, 1.3].
- A low solver score alone proves nothing, because broken tasks,
  impossible requirements, mis-specified graders, and fabricated grounding
  all produce the same number. The benchmark itself must be reviewed,
  separately from solving [1.2, Stage 3].

## 1. The pipeline at a glance

The agent produces a benchmark as a Harbor-compatible evaluation package:
a container environment, task instructions, the evidence supplied to the
solver, a reference solution, and machine-checkable grading criteria [1.2].

Three stages repeat for a fixed number of iterations:

1. **Proposal.** The agent designs and writes the benchmark package.
2. **Solving.** Solver agents attempt the tasks. Their scores are the
   difficulty signal.
3. **Review.** Independent LLM judges grade the benchmark itself on five
   criteria. Their verdicts decide whether the iteration may be built on.

Three cross-cutting components:

- **Autodata loop.** Each iteration starts from the best accepted
  checkpoint so far, not necessarily the latest one. Feedback is exposed
  as file-system memory: frozen snapshots, trajectories, answers, rubric
  judgments, and verdicts are written to disk and the prompt names the
  paths [1.2, Component 1].
- **External solvers.** Solvers that never take part in the loop check
  whether the proposer is making tasks adversarially hard for the in-loop
  solvers instead of genuinely better. Cheap external solvers run after
  every iteration, an expensive one runs on the selected best checkpoint,
  and their results are never written into the proposer's feedback
  [1.2, Component 2].
- **Human involvement.** A human can supply *what* to measure, *how* to
  measure it, or both, before the run and optionally during it
  [1.2, Component 3]. The four settings are detailed in Section 6 below.

## 2. Stage 1: Benchmark proposal [A.1]

Goal: difficult yet high-quality tasks. The agent receives a task spec (a
file with the general rules of the task, plus human direction when the
setting provides it) and, optionally, grounding material. It first decides
what capability to measure, then how to measure it: it writes down the
construct, develops several materially different operationalizations,
collects and stores primary sources, and instantiates the chosen design as
runnable tasks. Because the package must execute, the agent also owns the
decisions a human benchmark designer normally owns: what the solver sees,
what evidence it gets, what an ideal answer contains, how partial credit
is assigned, and a reference solution proving the task can be solved [1.2].

### 2.1 Authoring session [A.1, Stage 1-A]

- One fresh research agent per iteration: an OpenHands agent with a
  terminal, a file editor, a task tracker, and a summarizing condenser,
  running in an isolated container.
- It writes only to its own iteration directory. It may read the brief,
  the operator-provided grounding, the pinned Harbor documentation, and
  earlier frozen submissions. Public unauthenticated web retrieval is
  available for grounding.
- It cannot call models, launch judges or solvers, start containers,
  submit scheduler jobs, or run its own benchmark. The structural
  validator (2.3) is the only executable check it may invoke.
- The session ends by writing a one-shot marker. The harness then freezes
  and hashes the directory tree.

### 2.2 Submission contract [A.1, Stage 1-B]

A submission must contain:

- A specification: construct, scientific value, scope, hypothesis,
  feasibility argument, and threats to validity.
- A comparison of at least three materially different designs.
- A grounding directory with the retained source bytes and a provenance
  manifest. Every manifest record carries an origin, a UTC retrieval
  time, a local path, a SHA-256 hash, and license terms. Self-generated
  data must additionally retain the executable generator, its parameters
  and seed, per-stage timestamps, and verified asset hashes.
- A record of the agent's research process.

Each task directory is a complete native Harbor task: instruction, task
configuration, assets uploaded into the solver's working directory, a
deterministic reference solution, and a verifier directory holding the
grading criteria, a judging context, and a private reference answer.

Grading criteria are native binary, Likert, or numeric items with positive
weights and stable identifiers. Regexes, required phrases, length targets,
and model-specific criteria are prohibited.

### 2.3 Gate 1: structural validation [A.1, Stage 1-C]

Tasks are scaffolded before the session from pinned `harbor task init`
output, with the Dockerfile removed and fixed Reward Kit files installed.
The first gate validates the frozen tree without executing it:

- Protected content must return byte-identical: the verifier launcher,
  the answer-judge prompt template, image digests, timeouts, resource and
  network settings, and the judge wiring that fixes the judge's inputs,
  the reference path, and the aggregation. The agent may edit only the
  task description, keywords, and scientific metadata.
- Each required task must appear exactly once. Every path must be a
  regular file: symlinks, hardlinks, device nodes, and sparse files are
  rejected. The executable bit is allowed only on the reference solution
  and the protected launcher.
- Package limits: at most 1,024 files, 2 GiB total, 256 MiB per file,
  240-byte paths.
- Criteria must satisfy the Reward Kit schema: unique identifiers,
  positive weights, at least two points for a Likert item, an explicit
  range for a numeric item. Manifest timestamps, hostnames, and hashes
  must match the retained bytes.
- Revision-specific checks: the reference solution is parsed in shell
  no-execute mode and its literal Python heredocs are compiled. Criterion
  identity is held fixed, so an identifier cannot be rebound to another
  name or a name to another identifier. An instruction change whose
  private grading and reference artifacts are byte-identical to the
  checkpoint is rejected as the signature of a partial write.

### 2.4 Gate 2: revision integrity [A.1, Stage 1-D]

From the second iteration onward, a dedicated judge runs before any
execution. It sees only the solver-visible projection of the checkpoint
and of the current submission (instructions, READMEs, public metadata,
assets), a trusted diff, the feedback the agent could read, and the
current grounding. Private references, criteria, solutions, and hidden
solver results are excluded.

It applies a counterfactual test to every material public change: with
all prior solver answers and scores removed, would an independent author
still make this change from the construct, the grounding, or a genuine
ambiguity? A change passes only if retained sources support it at an
exact locator. Making an observed solver error less likely is explicitly
not a justification.

A static detector flags numbers, causal edges, stratum identities, and
long n-grams that newly appear in public files and also appear in the
feedback. These flags are advisory input to the judge. The judge's
verdict is binding, and its provenance review covers the whole current
grounding, not only the records touched by the diff.

### 2.5 Gate 3: reference-solution admission [A.1, Stage 1-E]

The agent's own reference solution is executed in the real task container
through Harbor's Oracle agent and graded with the real verifier and
answer judge. A submission is admitted only with no verifier error and a
reward of at least 0.9. This establishes that the task is solvable under
the fixed contract, that the environment holds what the solution needs,
and that the grader awards the intended answer. The retained reward
artifacts are hashed into the validation report that the quality judges
later read.

### 2.6 Repair [A.1, Stage 1-F]

A failure at any of the three gates returns the iteration to a fresh
session of the same agent, which receives a repair report naming the
failing gate and the defect and is restricted to fixing it. At most ten
submission attempts per iteration.

## 3. Stage 2: Benchmark solving [A.2]

### 3.1 Solver runs [A.2, Stage 2-A]

- Each solver attempts every task once, which is treated as one
  observation per model and task. Runs use Harbor's agent in the task
  container under the fixed execution contract, with per-route token
  caps, five tasks at a time.
- A completed run retains the final answer, the trajectory in Harbor's
  ATIF format, and a result summary.
- Provider errors, container and scheduler failures, missing
  trajectories, and truncated collections are classified as
  infrastructure outcomes and retried, never recorded as incorrect
  answers. Only completed runs enter the difficulty signal, and the
  feedback states this, so the agent does not read a failed run as a
  solved task.
- External solvers use a separate lane. Their results go to an
  operator-private directory that no feedback index references, routed
  through a loopback proxy.

### 3.2 Answer judging [A.2, Stage 2-B]

Answers are graded in a separate verifier container by a judge that sees
the judging context, the answer, and the private reference, and scores
each criterion independently. Scores combine by a protected weighted mean
into a reward in [0, 1]. The judge prompt is a harness-owned template that
treats the task, the answer, and every quoted asset as untrusted
evidence, and the judge route is fixed so the agent cannot address the
grader. Published feedback carries per-criterion scores and anchors.

## 4. Stage 3: Benchmark review [A.3]

### 4.1 The five criteria [A.3, Stage 3-A]

One judge per criterion. The wording is canonical and is disclosed
verbatim to the research agent, so it knows what its submission is
reviewed against. In the paper's words:

1. **Construct validity.** "The benchmark measures the research-agent
   capability claimed in the brief and the specification, not an
   incidental proxy or an evaluator quirk."
2. **Correctness.** "Task artifacts, private references, rubric
   semantics, score calculation, and reproducibility are internally
   correct and free of leakage."
3. **Feasibility.** "A genuinely stronger research agent could solve the
   benchmark with the supplied evidence, resources, and rules; difficulty
   from missing evidence, impossible requirements, or circular evaluation
   is rejected."
4. **Usefulness.** "Progress would transfer to meaningful scientific work
   or provide valuable evidence about research-agent capability."
5. **Overall.** "The integrated contribution has no serious red flags and
   is a credible publication-quality benchmark design at the current
   scale."

### 4.2 Isolation and verdict format [A.3, Stage 3-B]

The five sessions run concurrently on physically isolated bundles
holding the brief, the specification, the grounding, the frozen
submission, a sanitized validation report (versions, image digests, judge
identifier and prompt hash, scoring wiring, reference-solution status and
reward), and the retained solver evidence. No judge sees another's
verdict.

Each judge writes a JSON verdict with: a pass or fail decision, a
responsibility field separating submission defects from harness faults,
at least three artifact citations, at least one strength and one
weakness, required fixes for a fail, a confidence level, and a rationale.

### 4.3 Evidence protocol [A.3, Stage 3-C]

A manifest entry is an untrusted assertion. Every material claim or
grading anchor must be verified against retained content at an exact
locator or by a reproducible derivation. Placeholder domains, invented
citations, dead locators, self-authored text presented as publisher
bytes, and unsupported license or version declarations are mandatory
failures. Judges may not browse the web to repair an evidentiary gap, so
a claim that cannot be checked inside the bundle counts against the
submission.

## 5. The overall loop [A.4]

### 5.1 AI feedback bundle [A.4, Component A]

One curated, secret-scanned bundle is published per iteration, containing
the validation report, per-task run status, sanitized trajectories and
answers for the in-loop solvers, per-criterion rubric judgments, and the
five verdicts. Only files named by the bundle index may be read. Hidden
external results stay in the private lane. Raw provider logs, exception
text, and judge reasoning are omitted, and all published evidence is
labeled untrusted, so an instruction embedded in an answer or a retrieved
document is not a directive to the next session.

### 5.2 Checkpoint selection [A.4, Component B]

Before iteration t, a history over iterations 1 to t-1 is built. An
iteration is eligible when all five verdicts passed and its solver
evaluation is complete. Among eligible iterations, the loop takes the
lowest mean reward on the solver designated as the selection objective,
breaking ties toward the later iteration. With nothing eligible, it falls
back to the latest fully evaluated iteration and labels the session a
repair. The selected checkpoint is copied atomically into the new
writable directory for in-place editing, and the prompt exposes every
prior snapshot and feedback index, so the agent can inspect iterations it
did not descend from. The end-of-run selection uses the same policy but
refuses any checkpoint that did not pass every judge, and is written
where the agent cannot see it.

### 5.3 Human feedback inside the loop [A.4, Component C]

In the operator-in-the-loop setting, the driver finishes the preceding
iteration, then pauses before the next session and writes a review packet
with per-task scores, action and tool counts, rubric misses, quality
outcomes, and paths to the full trajectories and answers. No model job
runs while it waits. The admitted response is validated and snapshotted
and exposed as one more read-only artifact alongside the checkpoint
history, after which the loop resumes.

## 6. Human feedback settings [1.2, Component 3]

Benchmark creation involves two decisions, *what* to measure and *how* to
measure it. The paper varies both, plus whether feedback is available
only before the run or also during it:

- **(i) No feedback.** Fully autonomous. The agent gets no human
  direction and no grounding, only the general rules of the task spec,
  and chooses the scientific domain, the construct, and the
  operationalization itself.
- **(ii) Coarse-grained feedback, proposal stage.** A human states the
  intent in a single sentence. This fixes *what* to measure and leaves
  the entire operationalization to the agent.
- **(iii) Fine-grained feedback, proposal stage.** A human writes a
  detailed task specification and curates the list of grounding material
  the agent may use. This fixes both *what* and much of *how*, matching
  what a human benchmark designer decides before work starts.
- **(iv) Fine-grained feedback, proposal and execution stages.** In
  addition to (iii), a human inspects the outcome of an iteration and
  writes what the agent should do next, so direction is also available
  during the loop.

## 7. Experimental configuration [1.3]

- **Models.** Muse Spark 1.1 is the proposing research agent. The
  in-loop solvers are Muse Spark 1.1 itself and Muse-Glimmer-30B, so the
  proposer must create problems that a considerably weaker model and the
  proposer itself cannot solve, yet that remain meaningful. Muse Spark
  1.1 also serves as the answer judge and as the five benchmark-quality
  judges. External solvers: NVIDIA-Nemotron-3.5-Lightning-30B-A3B after
  every iteration, and Claude-Opus-5 on the selected best checkpoint.
  Neither is integrated in the loop.
- **Scale.** Every run produces a benchmark with ten instances over ten
  iterations. Each solver attempts every task once per iteration, so an
  iteration's difficulty signal is the mean over ten independent task
  observations per model.
- **Execution contract.** Identical in every iteration so scores stay
  comparable: 4 CPUs, 16 GiB of memory, and a 24-hour agent budget per
  task, with a separate verifier container for grading.
- **Grounding hygiene.** In settings (iii) and (iv), the harness hashes
  every supplied source and snapshots it read-only before the session
  starts. The agent may additionally retrieve public web content during
  the grounding stage.
- **Admission before solving.** Before any solver runs, the harness
  executes the agent's reference solution against the real verifier and
  admits the submission only at a score of at least 0.9, returning it for
  repair otherwise, with at most ten submission attempts per iteration.
- **Scoring display.** Scores are shown on a 0 to 100 scale. Lower means
  a harder, better benchmark.

## 8. Headline results

Claude Opus 5 score on the selected best checkpoints (lower is harder)
[Table 1]:

| Setting | Opus 5 score |
| --- | --- |
| Autonomous run, no feedback | 98.0 |
| Rebuttal Bench, coarse-grained feedback | 83.1 |
| Rebuttal Bench, fine-grained feedback | 65.9 |
| Graveyard Bench, coarse-grained feedback | 90.7 |
| Graveyard Bench, fine-grained feedback | 84.4 |

Execution-stage feedback (setting iv) was tested on SilentTrain Bench:
iterations 1 to 5 ran with fine-grained proposal feedback only, then the
run forked at iteration 6. The continuation that received human guidance
on how to instantiate the benchmark opened a persistent gap over the
unaided continuation, reported in the blog post as 23.9, 31.4, and 35.0
points after 6, 8, and 10 iterations [1.3, Figure 3].

The paper's own summary of where humans matter most: forming the problem
(a detailed specification with curated grounding material) and supplying
the way to realize it (guidance on instantiation, which restarted a
stalled loop). The necessary agent-side ingredients were grounding
material worth iterating on, feedback drawn from solver trajectories and
judge verdicts together, and enough loop iterations [blog, Conclusion].

## 9. The three benchmarks built with the method [1.3, Appendix B]

### 9.1 Graveyard Bench (ideation)

Question: will an idea-generating model re-propose a research direction
that is already dead?

- **Seeds.** Each task is seeded from failed research: a null
  pre-registered clinical trial, a medical reversal, or a results-level
  retraction. Grounding sources include the medical-reversals supplement
  of Herrera-Perez et al. (2019), ClinicalTrials.gov registry records and
  their AACT aggregation, and the Reproducibility Project: Psychology.
- **Task format.** The solver receives only a neutral research goal plus
  background, never the refuted intervention, and must produce ten
  structured hypotheses, each with a confidence score and a
  `previously_refuted` or `not_previously_refuted` flag.
- **Scoring.** A task counts as a zombie (incorrect) if any hypothesis
  matches the hidden claim's intervention, effect direction, and scope
  without being flagged `previously_refuted`. The difficulty is that a
  refuted idea leaves no confirming paper behind, so it looks unexplored,
  and novelty-seeking pushes the solver straight toward it.

### 9.2 SilentTrain Bench (experimentation)

Question: can an AI assistant repair a training bug that never raises an
error?

- **Seeds.** Defects that leave a training run executable while lowering
  the metric it reports, sourced from the silent-error corpus released
  with TrainCheck and from commit histories of widely used training
  frameworks and libraries (PyTorch, TensorFlow, HuggingFace
  Transformers, Accelerate, DeepSpeed, PyTorch Lightning, torchvision,
  timm, Detectron2, vLLM, LitGPT, Mosaic Composer, OpenNMT-py, lmms-eval)
  and of self-contained research codebases (nanoGPT, ring-flash-attention,
  opinf, GrowNet, stable-continual-learning, Human-Path-Prediction,
  turboquant-pro, mrpro). The GH Archive event stream locates the
  relevant commits and issue threads, and training runs execute on
  Imagenette.
- **Task format.** Each task supplies a complete repository containing
  one silent correctness regression, for example a compiled optimizer
  reusing stale state after a gradient becomes None, an epoch that
  finishes without processing a batch, or a mixture-of-experts run that
  omits its auxiliary loss from the reported total. The solver must
  reproduce the defect, fix it in the supplied repository, and validate
  the fix by executing a command that exercises the affected behavior.
- **Scoring.** The only hybrid grader of the three: a programmatic
  criterion runs a hidden regression over the repaired repository, and
  judge criteria read the submitted patch and the retained execution log
  alongside the written answer, so an explanation without a working
  repair does not pass. Both the instruction and the grader come from the
  run that received execution feedback, and its three interventions are
  visible in them: work from the complete repository, submit an executed
  validation, and grade behavior rather than with a deterministic checker
  alone.

### 9.3 Rebuttal Bench (assessment)

Question: does an author response actually answer the reviewer?

- **Seeds.** Reviewer comments and author rebuttals from papers with
  transparent peer review. Grounding sources: DISAPERE, PRRCA, ICLR 2024
  review threads via OpenReview, Nature Communications transparent
  peer-review files, and eLife decision letters with point-by-point
  responses.
- **Task format.** The solver adjudicates every sub-concern as RESOLVED,
  PARTIALLY_RESOLVED, NOT_RESOLVED, or DEFLECTED, labels the type of
  evidence supplied, and, where one applies, the deflection tactic used.
- **Scoring traps.** The tasks are constructed so that fluency is not
  evidence: several rebuttals substitute a weaker assay for the one the
  reviewer requested, and several excerpts contain a second-round
  reviewer declaring satisfaction, which the instruction explicitly
  forbids treating as proof of resolution.

## 10. What the paper does not specify

The methodology is specified to an unusual level of detail, but four
pieces are described rather than reproduced, and any replication must
write them itself:

1. **The task spec's general rules.** Section 1.2 and [A.1] say what the
   file contains, and that in the autonomous setting it carries the rules
   alone, but the text of the rules is not given.
2. **The answer-judge prompt template.** Described as a harness-owned,
   byte-protected template [A.1 Stage 1-C, A.2 Stage 2-B]. Its content is
   not published.
3. **The revision-integrity judge's prompt.** The counterfactual test is
   specified in prose [A.1 Stage 1-D], the prompt itself is not.
4. **Per-route token caps.** Solver runs are described as running under
   per-route token caps [A.2 Stage 2-A]. The cap values are not given.

For comparison, the same paper publishes verbatim prompts for its other
chapters (Appendix D for HackBench, Appendix F for AutoInteract), so
these four gaps are specific to the AutoBenchmark chapter.

## 11. Minimal replication checklist

Distilled from Sections 1 to 10, in execution order:

1. Fix the task package format first: instruction, configuration,
   solver-visible assets, deterministic reference solution, private
   grading criteria with stable identifiers and positive weights, judging
   context, private reference answer. Freeze everything that grades as
   byte-protected harness property.
2. Write the task spec: general rules, and, for the fine-grained setting,
   a detailed specification plus a curated, hashed, read-only grounding
   snapshot with a provenance manifest.
3. Run the proposer in an isolated, single-writer session with no access
   to models, judges, solvers, or containers. Freeze and hash each
   submission.
4. Enforce the three gates in order: structural validation, revision
   integrity (from iteration 2), reference-solution admission at a reward
   of at least 0.9. Allow bounded repair attempts with a named-defect
   report.
5. Solve with at least two in-loop solvers, one attempt per task, under
   a fixed execution contract. Treat infrastructure failures as retries,
   never as wrong answers.
6. Review with five isolated judges, one per criterion, using the fixed
   verdict format and the evidence protocol. No cross-talk between
   judges.
7. Run at least one external solver per iteration whose results never
   enter the proposer's feedback, plus a strong external solver on the
   selected checkpoint.
8. Publish a curated, secret-scanned feedback bundle per iteration and
   select the next parent by the eligibility rule: all verdicts pass,
   then lowest selection-solver score.
9. Budget human time where the paper shows it pays: a detailed proposal
   specification and curated grounding before the run, and instantiation
   guidance mid-loop when progress stalls.
10. Expect unaided runs to saturate. Treat a high solver score as a
    signal about the benchmark, not about the solvers.
