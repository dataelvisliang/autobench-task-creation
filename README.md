# AutoBenchmark: A Detailed Guide to Agent-Driven Benchmark Creation

This repository is a detailed, section-by-section write-up of the AutoBenchmark
methodology: how an autoresearch agent creates an evaluation benchmark end to end,
how the resulting tasks are checked, and what role humans play in the loop.

It is compiled from Section 1, Appendix A, and Appendix B of:

> Tianjian Li, Chuanyang Jin, Seungone Kim, Tong Chen, John Hoffman, Yoram Bachrach,
> Pedro Rodriguez, Ping Yu, Eryk Helenowski, Swarnadeep Saha, Jack Lanchantin,
> Weizhe Yuan, Ilia Kulikov, Jason Weston.
> *Aligning Autoresearch: Co-Improvement between Agents and Humans.*
> arXiv:2610.38882, submitted 28 October 2026.
> Paper: https://arxiv.org/abs/2610.38882
> Project blog post: https://facebookresearch.github.io/RAM/blogs/autobench/

## Contents

- [METHOD.md](METHOD.md): the full methodology, organized for replication.
  Pipeline stages, submission contract, validation gates, review criteria,
  loop mechanics, human feedback settings, experimental configuration,
  the three benchmarks built with the method, headline results, and a list
  of details the paper does not specify.

## Status of the original artifacts (checked 2026-11-08)

- No official code repository for AutoBenchmark has been released.
- The three generated benchmarks (Graveyard Bench, SilentTrain Bench,
  Rebuttal Bench) have no public download as of this writing.
- The complete method is described in prose in Section 1 and Appendix A
  of the paper, which is what this guide organizes.

## Code scaffold

The `src/autobench/` package implements the deterministic machinery of the
recipe in pure Python (standard library only). Model roles (proposer,
solvers, judges) are interfaces; the quickstart wires in deterministic
stubs and one real grader so the loop runs offline with no API keys.

- `schema.py`: task package and grading criteria, including the recipe's
  prohibitions (no regexes, required phrases, length targets, or
  model-specific criteria)
- `manifest.py`: grounding provenance records and hash-freezing of a
  source tree, with tamper verification
- `gates.py`: Gate 1 structural validation (protected files byte-identical,
  package limits) and Gate 3 reference-solution admission (reward >= 0.9),
  plus a scaffold-only NOP check: an empty submission graded by the real
  grader must score 0, or the task fails for leaking points. The paper
  does not use a NOP check; see METHOD.md Section 10.
- `integrity.py`: Gate 2 static leak detector, flagging numbers and long
  n-grams that move from feedback into solver-visible files
- `review.py`: the five review criteria and the fixed verdict format
- `loop.py`: checkpoint selection and secret-scanned feedback bundles
- `spec.py`: the task spec and the four human feedback settings

Run it:

```bash
PYTHONPATH=src python examples/quickstart.py
PYTHONPATH=src python -m pytest   # 31 tests
```

`examples/example_task/` is a tiny complete task package (sum the integers
in a file) whose reference solution is really executed by the grader.

## A note on text reuse

The methodology below is paraphrased and restructured for clarity, with short
verbatim quotations where the paper's exact wording matters (for example the
five review criteria). Every part is anchored to its source section so the
original text is one click away in the arXiv HTML version. Full verbatim
reproduction of the paper is intentionally left to the paper itself.

## Who this is for

Anyone who needs to create evaluation tasks with an agent in the loop and
wants a concrete, battle-tested recipe: what the creating agent may see,
what a valid task package must contain, which gates a task must pass before
it counts, and where human input has the most leverage.
