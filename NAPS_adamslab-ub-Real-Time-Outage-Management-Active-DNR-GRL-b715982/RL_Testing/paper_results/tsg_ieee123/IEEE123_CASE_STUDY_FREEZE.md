# IEEE 123 Case Study Freeze

Freeze date: 2026-06-17

Status: IEEE 123 is frozen as the second completed TSG vulnerability-assessment case study, with post-freeze exhaustive action-mask and branchflow criticality completed.

This folder is the retained IEEE 123 evidence package:

```text
RL_Testing/paper_results/tsg_ieee123/
```

Final paper artifact package:

```text
paper_results\tsg_ieee123\paper_artifacts
```

Final manifest:

```text
RL_Testing/paper_results/tsg_ieee123/paper_artifacts/ieee123_paper_artifacts_manifest.json
```

Frozen evidence counts:

```text
baseline attack-family rows: 5
baseline case rows: 150
action-mask criticality rows completed: 41 of 41
branchflow single-target rows completed: 138 of 138
branchflow subset ablation rows: 6
defense-stress groups: 190
advanced mitigation variant rows: 6
paper table bundles: 9
paper figures: 5
missing input files: 0
```

Freeze rule:

```text
Do not overwrite, delete, or reinterpret IEEE 123 result files while implementing IEEE 8500.
Any new IEEE 123 run after this exhaustive-criticality update should be clearly labeled as a later addendum or a new version.
```

Scientific boundary:

```text
The frozen IEEE 123 evidence supports completed direct current-GRL observation attacks on topology/status, action-mask/status, voltage, branchflow, and global scalar observations.
The action-mask and branchflow single-observation criticality studies are exhaustive over the current IEEE 123 target registries used by the batch manifest.
IEEE 8500 behavior is not claimed here and must be evaluated separately when the files are available.
```
