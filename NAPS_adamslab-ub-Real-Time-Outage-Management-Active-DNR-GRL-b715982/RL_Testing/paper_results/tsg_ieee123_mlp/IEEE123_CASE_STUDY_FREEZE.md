# IEEE 123 Case Study Freeze

Freeze date: 2026-06-18

Status: IEEE 123 is frozen as the second completed TSG vulnerability-assessment case study, with post-freeze exhaustive action-mask and branchflow criticality completed.

This folder is the retained IEEE 123 evidence package:

```text
paper_results\tsg_ieee123_mlp
```

Final paper artifact package:

```text
paper_results\tsg_ieee123_mlp\paper_artifacts
```

Final manifest:

```text
paper_results\tsg_ieee123_mlp\paper_artifacts\ieee123_paper_artifacts_manifest.json
```

Frozen evidence counts:

```text
baseline attack-family rows: 5
baseline case rows: 150
action-mask criticality rows completed: 41 of 41
voltage single-target rows completed: 130 of 130
branchflow single-target ranking rows recorded: 129 from the 138-target registry; no-op-only targets do not produce ranking rows
branchflow subset ablation rows: 6
defense-stress groups: 181
advanced mitigation variant rows: 0
paper table bundles: 10
paper figures: 6
missing input files: 0
```

Freeze rule:

```text
Do not overwrite, delete, or reinterpret IEEE 123 result files while implementing IEEE 8500.
Any new IEEE 123 run after this exhaustive-criticality update should be clearly labeled as a later addendum or a new version.
```

Scientific boundary:

```text
The frozen IEEE 123 evidence supports completed direct controller-observation attacks on topology/status, action-mask/status, voltage, branchflow, and global scalar observations.
The action-mask, voltage, and branchflow single-observation criticality studies are exhaustive over the current IEEE 123 target registries used by the batch manifest.
IEEE 8500 behavior is not claimed here and must be evaluated separately when the files are available.
```
