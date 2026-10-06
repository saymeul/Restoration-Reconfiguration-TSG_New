# IEEE 123 TSG Vulnerability Assessment Results Narrative

Generated: 2026-06-20T23:51:29

## Evidence Boundary

This IEEE 123 package uses the completed IEEE 123 evidence only. It does not use IEEE 34 results as simulation data, and it does not claim IEEE 8500 behavior.

Completed IEEE 123 BPSO p2/i2 evidence only: the 30-case baseline attack-family study, the 41-target action-mask/status criticality study, defense-stress summary, and advanced mitigation ablation are complete. Voltage, branchflow, topology, and energy false-data channels are not claimed as direct BPSO decision vulnerabilities because this BPSO objective uses ActionMasking as the decision-relevant observation constraint.

The completed IEEE 123 observation studies include baseline five attack families, exhaustive action-mask criticality, defense-stress summarization, advanced mitigation ablation.

## Which Attacks Are Most Damaging?

`action_mask_false_unavailable` is the most damaging baseline attack family with mean degradation 678.300 kWh, total degradation 20349.010 kWh, maximum degradation 4439.399 kWh, and 15 damaging cases out of 30.
The largest single baseline case is `B0016_action_mask_false_unavailable_seed1706330019` under `action_mask_false_unavailable`, with 4439.399 kWh physical degradation.

## Which Observations Are Most Critical?

Among completed action-mask targets, `action_mask.Load_s48` is the most critical with mean degradation 989.312 kWh and maximum degradation 4539.177 kWh.
A coordinated branchflow subset ablation is not available in this artifact package, so coordinated branchflow conclusions should not be claimed from this package alone.

## How Much Restored Energy Is Lost?

Use physical degradation in kWh as the primary damage metric. It measures positive restored-energy loss relative to the clean restoration outcome and avoids overstating cases where an attack accidentally improves restoration.
The largest residual-risk defense group is `action_mask.Load_s48` from `action_mask_single_criticality`, with total degradation 29679.353 kWh and residual degradation 8258.732 kWh after mitigation.

## Detection and Mitigation

The completed IEEE 123 defense-stress evidence found zero high-impact detection bypass cases among the damaging completed cases. The remaining weakness is residual mitigation loss after detection.
On the 60 detected low-recovery cases, the current one-step FDIA-aware selector left 58610.708 kWh residual degradation, while `detector_mitigated_only` reduced residual degradation to 0.000 kWh and recovered 58610.708 kWh.
The best-case mitigation table shows the largest individual recovery for `AM0022_T0014_action_mask_swtie2_seed996050191`, reducing residual loss by 5490.851 kWh.

## Recommended Manuscript Use

Use Table 1 for attack-family ranking, Table 2 for worst baseline cases, Tables 3-5 for completed critical-observation studies, and Table 10 for the evidence audit. Tables 6-9 should be used only when their source studies are present in the manifest.

## Evidence Audit

The artifact manifest records 17 input/provenance rows.
