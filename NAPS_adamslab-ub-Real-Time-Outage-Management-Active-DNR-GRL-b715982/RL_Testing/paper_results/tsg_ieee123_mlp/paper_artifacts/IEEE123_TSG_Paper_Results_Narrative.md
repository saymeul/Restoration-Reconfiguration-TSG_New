# IEEE 123 TSG Vulnerability Assessment Results Narrative

Generated: 2026-06-18T16:38:47

## Evidence Boundary

This IEEE 123 package uses the completed IEEE 123 evidence only. It does not use IEEE 34 results as simulation data, and it does not claim IEEE 8500 behavior.

The completed IEEE 123 observation studies include baseline five attack families, exhaustive action-mask criticality, exhaustive voltage single-observation criticality, exhaustive branchflow single-observation criticality over applicable cases, coordinated branchflow top-k ablation, defense-stress summarization.

## Which Attacks Are Most Damaging?

`branchflow_hiding` is the most damaging baseline attack family with mean degradation 54.449 kWh, total degradation 1633.483 kWh, maximum degradation 829.460 kWh, and 2 damaging cases out of 30.
The largest single baseline case is `B0006_branchflow_hiding_seed1262161534` under `branchflow_hiding`, with 829.460 kWh physical degradation.

## Which Observations Are Most Critical?

Among completed action-mask targets, `action_mask.swsec11` is the most critical with mean degradation 54.449 kWh and maximum degradation 829.460 kWh.
Among completed voltage targets, `bus_voltage.48` is the most critical with mean degradation 51.841 kWh and maximum degradation 829.460 kWh.
Among completed branchflow single-observation targets, `branchflow.Line.l13` is the most critical with mean degradation 41.473 kWh and maximum degradation 829.460 kWh.
The coordinated branchflow subset ablation tests whether branchflow vulnerability is driven by groups of observations rather than one individual sensor.
At k=3, coordinated branchflow hiding reproduces 100.0% of the baseline branchflow degradation.
At k=10, coordinated branchflow hiding reproduces 100.0% of the baseline branchflow degradation.
The full selected branchflow subset reaches 100.0% reproduction with total degradation 1633.483 kWh.

## How Much Restored Energy Is Lost?

Use physical degradation in kWh as the primary damage metric. It measures positive restored-energy loss relative to the clean restoration outcome and avoids overstating cases where an attack accidentally improves restoration.
Across the completed defense-stress groups, mitigation left 0.000 kWh residual degradation after detected damaging attacks.

## Detection and Mitigation

The completed IEEE 123 defense-stress evidence found zero high-impact detection bypass cases and zero residual restored-energy degradation after mitigation among the damaging completed cases.

## Recommended Manuscript Use

Use Table 1 for attack-family ranking, Table 2 for worst baseline cases, Tables 3-5 for exhaustive critical observations, and Table 10 for the evidence audit. Tables 6-9 should be used only when their source studies are present in the manifest.

## Evidence Audit

The artifact manifest records 17 input/provenance rows.
