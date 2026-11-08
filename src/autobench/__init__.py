"""AutoBenchmark scaffold.

A minimal, dependency-free implementation of the deterministic machinery
in the AutoBenchmark recipe (Li et al., arXiv:2610.38882, Section 1 and
Appendix A): task package schema, grounding provenance, the three
submission gates, benchmark review verdicts, and the checkpoint loop.

Model-calling roles (proposer, solvers, judges) are interfaces here. The
quickstart wires in deterministic stubs so the whole loop runs offline.
"""

from . import gates, integrity, loop, manifest, review, schema, spec

__all__ = ["gates", "integrity", "loop", "manifest", "review", "schema", "spec"]
__version__ = "0.1.0"
