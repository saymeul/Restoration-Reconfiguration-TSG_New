# IEEE 34 Case Study Freeze

Freeze date: 2026-06-16

Status: IEEE 34 is frozen as the first completed TSG vulnerability-assessment
case study.

This folder is the retained IEEE 34 evidence package:

```text
RL_Testing/paper_results/tsg_ieee34/
```

Final paper artifact package:

```text
RL_Testing/paper_results/tsg_ieee34/paper_artifacts/
```

Final manifest:

```text
RL_Testing/paper_results/tsg_ieee34/paper_artifacts/ieee34_paper_artifacts_manifest.json
```

Final master audit:

```text
RL_Testing/paper_results/tsg_ieee34/master_evidence_audit/ieee34_master_evidence_manifest.json
```

Frozen evidence counts:

```text
completed IEEE 34 studies: 11
master evidence rows: 299
missing input files: 0
repeat ranking diff count: 0 for every included study
paper table bundles: 9
paper figures: 6
learning-detector ablation rows: 48
```

Freeze rule:

```text
Do not overwrite, delete, or reinterpret IEEE 34 result files while implementing
IEEE 123 or IEEE 8500. New system studies must use separate output folders,
for example:

RL_Testing/paper_results/tsg_ieee123/
RL_Testing/paper_results/tsg_ieee8500/
```

Permitted future IEEE 34 changes:

```text
1. Manuscript wording or figure/table selection notes.
2. A clearly labeled post-freeze addendum, if a reviewer or advisor requests
   a new IEEE 34 run.
3. A regenerated artifact package only if it is explicitly labeled as a new
   version and the previous frozen package is retained.
```

Scientific boundary:

```text
The frozen IEEE 34 evidence supports direct current-GRL observation attacks on
action/status, topology/status, voltage, branchflow, and global scalar
observations. It does not claim direct load-demand, DER-availability, or
explicit fault-status FDIA unless the controller observation model is extended.
```
