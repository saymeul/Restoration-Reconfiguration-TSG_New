# IEEE 123 BPSO Implementation Status

Status date: 2026-06-19

Current status: IEEE 123 BPSO is complete and frozen as a scoped p2/i2 controller-comparison evidence package. The completed scope is the 30-case baseline attack-family study, all 41 action-mask/status criticality targets, defense-stress summary, advanced mitigation ablation, paper artifacts, and GRL/MLP/BPSO comparison update.

## What Is Implemented

The shared controller configuration supports:

```text
--controller BPSO
--bpso-particles
--bpso-iterations
--bpso-seed
--bpso-allow-masked-actions
```

BPSO is implemented as a binary particle swarm optimizer over the same MultiBinary restoration action vector used by GRL and MLP. It scores candidate actions on the current deterministic OpenDSS outage scenario and uses the received `ActionMasking` channel as an availability constraint.

## Completed Evidence

```text
paper_results/tsg_ieee123_bpso/baseline_attack_full_deterministic_p2_i2
paper_results/tsg_ieee123_bpso/full_criticality_merged/action_mask
paper_results/tsg_ieee123_bpso/defense_stress_summary
paper_results/tsg_ieee123_bpso/advanced_mitigation_ablation_exhaustive_criticality
paper_results/tsg_ieee123_bpso/paper_artifacts
paper_results/tsg_ieee123_bpso/IEEE123_CASE_STUDY_FREEZE.md
paper_results/tsg_ieee123_controller_comparison
```

Completed BPSO run configuration:

```text
cases: 30
horizon: 24 hours
bpso_particles: 2
bpso_iterations: 2
attacks: topology_drop, action_mask_false_unavailable, voltage_masking, branchflow_hiding, energy_inflation
```

## Baseline Attack-Family Result

```text
action_mask_false_unavailable: mean physical degradation 678.300319 kWh, total degradation 20349.009583 kWh, max degradation 4439.398883 kWh, damaging cases 15/30, detection rate 100%, mean mitigation recovery 86.666667%.
topology_drop: 0.000000 kWh positive degradation in the completed p2/i2 BPSO baseline.
voltage_masking: 0.000000 kWh positive degradation in the completed p2/i2 BPSO baseline.
branchflow_hiding: 0.000000 kWh positive degradation in the completed p2/i2 BPSO baseline.
energy_inflation: 0.000000 kWh positive degradation in the completed p2/i2 BPSO baseline.
```

## Action-Mask Criticality Result

All 41 action-mask/status targets are complete.

```text
case rows: 1210
criticality rows: 41
most damaging target: action_mask.Load_s48
mean degradation for top target: 989.311752 kWh
max degradation for top target: 4539.177177 kWh
damaging cases for top target: 8
detection rate for top target: 100%
mean mitigation recovery for top target: 75%
```

## Detection and Mitigation Result

```text
defense-stress case rows: 1360
defense-stress groups: 46
high-impact detection bypass cases: 0
low-recovery cases: 60
baseline action-mask residual degradation after current mitigation: 56.532356 kWh total
advanced mitigation rows: 360
advanced mitigation variants: 6
best tested advanced mitigation residual: 0.000000 kWh
best tested advanced mitigation recovery: 100%
```

The advanced mitigation ablation shows that `detector_mitigated_only`, `all_channel_reference_only`, `horizon_screen_raw_mitigated`, and `horizon_screen_raw_mitigated_reference` recover all degradation over the 60 low-recovery BPSO cases tested.

## Scientific Boundary

This is a frozen scoped BPSO evidence package, not a full voltage/branchflow BPSO observation-vulnerability study.

The current BPSO decision model is directly sensitive to `ActionMasking`, because that channel constrains the optimizer action search. Voltage, branchflow, topology, and energy false-data channels do not directly enter the BPSO objective in this implementation except through the detector/mitigation pipeline. A stronger perceived-objective BPSO variant would be needed before claiming full decision vulnerability to those channels.

## Optional Future Work

No remaining work is required for the completed scoped IEEE 123 BPSO comparison package. Future addenda could include a higher BPSO search budget, such as 8x8, or a new BPSO perceived-objective model that explicitly uses voltage and branchflow measurements.
