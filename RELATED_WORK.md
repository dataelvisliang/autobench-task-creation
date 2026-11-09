# Related Work: Automatic Task and Benchmark Creation

This file maps the papers closest to AutoBenchmark, the method documented
in METHOD.md. It answers one question: who else creates benchmarks or
tasks automatically, and what can be borrowed from each of them.

Source paper for the comparison: Tianjian Li and others, *Aligning
Autoresearch: Co-Improvement between Agents and Humans*,
arXiv:2610.38882, Section 1 and Appendix A. AutoBenchmark is Chapter 1
of that paper.

Checked 2026-11-08. Code and data availability is stated as verified on
that date. Anything not stated here was not verified.

## The short version

Only AutoBenchmark builds executable task packages with a solver
feedback loop and a review stage. The closest prior work on the same
problem is AutoBencher. The two generation methods most directly
borrowable for a tax agent eval are SWE-smith, which creates tasks by
breaking good code, and TaskCraft, which executes a tool first and then
writes the question from the answer.

## 1. The same problem: automatic benchmark creation

### AutoBencher (2024, arXiv:2407.08351, ICLR 2025)

The closest prior work to AutoBenchmark. It starts from a stated set of
wanted properties, such as salience, difficulty, and novelty, then has
GPT-4 rewrite a dataset description in rounds and generate questions
from it in bulk. It produced 4,000 questions across math, multilingual
tasks, knowledge, and safety.

Difference from AutoBenchmark: it has no solver feedback loop and no
review stage, and its output is question answering items, not
executable task packages. Code is public:
https://github.com/XiangLi1999/AutoBencher

### Autodata (2026, arXiv:2606.25996)

The inspiration for the AutoBenchmark loop. One agent acts as a data
scientist. A challenger proposes items, a weak solver and a strong
solver attempt them, and a verifier keeps only the items the strong
solver passes and the weak solver fails. The proposing agent itself can
then be optimized for another round.

Difference from AutoBenchmark: it mainly creates training data, and
benchmark creation is only one stated use. Its official code and data
were not confirmed as released on the check date.

## 2. Directly borrowable: verifiable programming and agent tasks

### SWE-smith (2025, arXiv:2504.21798)

Creates tasks by breaking good code. It rewrites functions, edits
syntax trees, and reverts pull requests, and it keeps only the changes
that break an existing test. The surviving test becomes a ready made
grader. It built 50,000 tasks from 128 repositories. Code, tasks,
trajectories, and models are public:
https://github.com/SWE-bench/SWE-smith

Borrow this when the task has code and tests. Breaking a correct
solution is a cheap way to get a task with a known failing test.

### TaskCraft (2025, arXiv:2506.10055)

The most directly relevant paper for agent tasks. It starts with
atomic single tool tasks: execute a tool for real, get an answer, then
have a model write the question from that answer. It then composes
these atoms into deeper multi step tasks and wider tasks that combine
several subtasks, and it filters with rejection sampling and
incremental verification. It built about 36,000 verifiable tasks.
Code and dataset are public:
https://github.com/OPPO-PersonalAI/TaskCraft

Borrow this when the task has tools. Executing first and writing the
question second guarantees the task has a true answer.

### R2E-Gym (2025, arXiv:2504.07164)

Builds runnable environments from GitHub commits in a programmatic
way. It produced more than 8,100 runnable environments. Tests are
generated automatically, and the task text is translated back from
execution results instead of being written from human issues and pull
requests. Code, data, and models are public.

Borrow this when the task needs a real execution environment. The
commit history is the raw material, and the environment is the grader.

## 3. Adjacent work: grading strictness and contamination

### EvalPlus (2023, arXiv:2305.01210)

It does not create tasks. It creates tests. For existing programming
tasks it generates extra test cases, using LLM generation and mutation,
and it expanded the HumanEval test set to about 80 times its original
size. It covers the grading strictness end of the problem, the same
line as the NOP empty submission check in this repo. Code is public.

### LiveCodeBench and LiveBench (2024)

These solve the same pain, tasks expire and get contaminated, but by a
different route: they do not generate tasks, they keep collecting new
human made ones. LiveCodeBench pulls programming tasks from new
LeetCode, AtCoder, and Codeforces contests and labels them by date, so
it only tests models on tasks published after their training cutoff.
LiveBench refreshes monthly from new papers, contests, and news, and
it uses objective answers for grading with no LLM judge. Code and data
are public.

Borrow this route when fresh human tasks exist and generation is not
needed. Collection is simpler than generation when the supply of new
tasks never stops.

## 4. Older lineage: synthetic data, with reusable techniques

These papers create training data, not benchmarks. Their techniques
can still be reused for task creation.

### Self-Instruct (2023)

Bootstraps new instructions from 175 seed tasks. The seed set is small,
and the model generates new tasks in the same shape.

### Evol-Instruct (2023)

Takes instructions and makes them harder in rounds: add constraints,
deepen the task, make it more specific.

### Magpie (2024)

Needs no seeds at all. It prompts an aligned model with an empty
template and lets the model produce instructions on its own. It
generated 4 million instructions and kept 300,000 after filtering.

### Persona Hub (2024)

Extracts 1 billion personas from web text. Changing the persona
changes the angle of the generated task, which addresses diversity.

### AgentInstruct (2024)

Uses a chain of specialist agents to produce 25 million instruction
pairs from source documents, and it released 1 million of those pairs.
The framework code was not confirmed as released on the check date.

## What to borrow for a tax agent eval

Three ideas transfer most directly.

1. From SWE-smith: break a correct solution to create a task. In tax
   terms, take a correct filing and introduce one controlled error, then
   the deterministic tax engine is the grader.
2. From TaskCraft: execute first, then write the question. Run the tax
   engine on real material first, then write the task from the computed
   answer, so every task has a true reference solution.
3. From EvalPlus and the NOP check in this repo: test the grader, not
   only the task. An empty submission must score zero, or the grader
   leaks points.

AutoBencher is the only same problem competitor with public code, and
it is worth reading for its bulk generation loop. Autodata is worth
reading for the challenger solver verifier loop that AutoBenchmark
adopted.
