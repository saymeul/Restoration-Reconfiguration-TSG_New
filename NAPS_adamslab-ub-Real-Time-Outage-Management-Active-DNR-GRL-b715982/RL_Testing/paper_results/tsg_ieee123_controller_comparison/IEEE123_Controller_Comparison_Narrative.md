# IEEE 123 Controller Comparison Narrative

Generated: 2026-06-20T23:49:32

## Evidence Boundary

GRL and MLP rows come from frozen IEEE 123 case-study artifacts. BPSO now includes a frozen scoped p2/i2 evidence package: complete 30-case baseline, all 41 action-mask criticality targets, defense-stress summary, and advanced mitigation ablation.

## Baseline Attack-Family Comparison

- GRL: most damaging available attack is `branchflow_hiding` with mean degradation 104.039 kWh over 30 cases; evidence level `full_frozen_case_study`.
- MLP: most damaging available attack is `branchflow_hiding` with mean degradation 54.449 kWh over 30 cases; evidence level `full_frozen_case_study`.
- BPSO: most damaging available attack is `action_mask_false_unavailable` with mean degradation 678.300 kWh over 30 cases; evidence level `scoped_p2_i2_action_mask_frozen`.

## BPSO Interpretation

The current BPSO implementation uses the received `ActionMasking` channel as an optimizer constraint and scores candidates on the physical OpenDSS outage scenario. Therefore action-mask/status attacks are directly decision-relevant for this BPSO variant, while voltage, branchflow, topology, and energy false-data channels require a richer perceived-objective BPSO model before they should be claimed as fully comparable vulnerabilities.

## Completion Status

- GRL: full_frozen_case_study; baseline cases 150, action-mask rows 41, voltage rows 0, branchflow rows 138, defense rows 190.
- MLP: full_frozen_case_study; baseline cases 150, action-mask rows 41, voltage rows 130, branchflow rows 129, defense rows 181.
- BPSO: scoped_p2_i2_action_mask_frozen; baseline cases 150, action-mask rows 41, voltage rows 0, branchflow rows 0, defense rows 46.
