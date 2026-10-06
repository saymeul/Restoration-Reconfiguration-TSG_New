# IEEE 123 Case Study Freeze

Freeze date: 2026-06-20

Status: IEEE 123 BPSO is frozen as a scoped p2/i2 controller-comparison evidence package: the 30-case baseline, 41 action-mask targets, defense-stress summary, and advanced mitigation ablation are complete.

This folder is the retained IEEE 123 evidence package:

```text
paper_results\tsg_ieee123_bpso
```

Final paper artifact package:

```text
paper_results\tsg_ieee123_bpso\paper_artifacts
```

Final manifest:

```text
paper_results\tsg_ieee123_bpso\paper_artifacts\ieee123_paper_artifacts_manifest.json
```

Frozen evidence counts:

```text
baseline attack-family rows: 5
baseline case rows: 150
action-mask criticality rows completed: 41 of 41
voltage single-target rows completed: 0 of 130
branchflow single-target ranking rows recorded: 0 from the 138-target registry; no-op-only targets do not produce ranking rows
branchflow subset ablation rows: 0
defense-stress groups: 46
advanced mitigation variant rows: 6
paper table bundles: 10
paper figures: 4
missing input files: 0
```

Freeze rule:

```text
Do not overwrite, delete, or reinterpret IEEE 123 result files while implementing IEEE 8500.
Any new IEEE 123 run after this exhaustive-criticality update should be clearly labeled as a later addendum or a new version.
```

Scientific boundary:

```text
Completed IEEE 123 BPSO p2/i2 evidence only: the 30-case baseline attack-family study, the 41-target action-mask/status criticality study, defense-stress summary, and advanced mitigation ablation are complete. Voltage, branchflow, topology, and energy false-data channels are not claimed as direct BPSO decision vulnerabilities because this BPSO objective uses ActionMasking as the decision-relevant observation constraint.
IEEE 8500 behavior is not claimed here and must be evaluated separately when the files are available.
```
