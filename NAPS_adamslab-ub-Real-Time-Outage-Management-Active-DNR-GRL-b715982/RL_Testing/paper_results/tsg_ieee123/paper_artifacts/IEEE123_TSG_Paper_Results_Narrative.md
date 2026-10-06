# IEEE 123 TSG Vulnerability Assessment Results Narrative

Generated: 2026-06-17T14:06:52

## Evidence Boundary

This IEEE 123 package uses the completed IEEE 123 evidence only. It does not use IEEE 34 results as simulation data, and it does not claim IEEE 8500 behavior.

The completed IEEE 123 observation studies include the baseline five attack families, exhaustive action-mask criticality, exhaustive branchflow single-observation criticality, coordinated branchflow top-k ablation, defense-stress summarization, and advanced mitigation ablation.

## Which Attacks Are Most Damaging?

`branchflow_hiding` is the most damaging baseline attack family with mean degradation 104.039 kWh, total degradation 3121.162 kWh, maximum degradation 1559.847 kWh, and 6 damaging cases out of 30.
The largest single baseline case is `B0014_branchflow_hiding_seed611696197` under `branchflow_hiding`, with 1559.847 kWh physical degradation.

## Which Observations Are Most Critical?

Among completed action-mask targets, `action_mask.Load_s48` is the most critical with mean degradation 2317.398 kWh and maximum degradation 4178.924 kWh.
Single branchflow observation attacks are weak in the completed IEEE 123 evidence. The strongest tested single branchflow target, `branchflow.Line.l115`, has mean degradation 0.000897 kWh.
The coordinated branchflow subset ablation is therefore important: it shows that the branchflow vulnerability is coordinated rather than driven by one individual sensor.
At k=3, coordinated branchflow hiding reproduces 74.7% of the baseline branchflow degradation.
At k=10, coordinated branchflow hiding reproduces 100.3% of the baseline branchflow degradation.
The full selected branchflow subset reaches 100.0% reproduction with total degradation 3121.162 kWh.

## How Much Restored Energy Is Lost?

Use physical degradation in kWh as the primary damage metric. It measures positive restored-energy loss relative to the clean restoration outcome and avoids overstating cases where an attack accidentally improves restoration.
The largest residual-risk defense group is `action_mask.Load_s82a` from `action_mask_single_criticality_partial`, with total degradation 13635.136 kWh and residual degradation 1290.263 kWh after mitigation.

## Detection and Mitigation

The completed IEEE 123 defense-stress evidence found zero high-impact detection bypass cases among the damaging completed cases. The main remaining weakness was mitigation selection after detection.
On the eight detected low-recovery cases, the current one-step FDIA-aware selector left 2617.432 kWh residual degradation, while `detector_mitigated_only` reduced residual degradation to 0.000 kWh and recovered 2617.432 kWh.
The best-case mitigation table shows the largest individual recovery for `AM0002_T0025_action_mask_Load_s88a_seed1519571662`, reducing residual loss by 849.639 kWh.

## Recommended Manuscript Use

Use Table 1 for attack-family ranking, Table 2 for worst baseline cases, Tables 3 and 4 for exhaustive critical observations, Table 5 for coordinated branchflow sensitivity, Table 6 for detection/mitigation residual risk, and Tables 7-8 for the advanced mitigation story.

## Evidence Audit

The artifact manifest records 15 input/provenance rows.
