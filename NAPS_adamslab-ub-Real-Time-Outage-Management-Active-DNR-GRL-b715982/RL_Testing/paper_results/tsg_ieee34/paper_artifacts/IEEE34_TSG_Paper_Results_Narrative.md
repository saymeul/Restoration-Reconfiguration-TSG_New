# IEEE 34 TSG Vulnerability Assessment Results Narrative

Generated: 2026-06-16T12:23:44

## Evidence Boundary

The IEEE 34 evidence base is now organized around direct observations available to the current GRL restoration controller: action-mask/status inputs, topology adjacency/status, bus-voltage measurements, branch-flow measurements, and global restoration scalars. Load-demand, DER-availability, and explicit fault-status FDIA should not be claimed as direct current-controller observation attacks unless the controller observation model is extended.

All reported degradation is physical restored-energy degradation, computed as positive loss relative to the clean baseline. Accidental improvements are kept separate so the paper does not overstate attack damage.

## Which Attacks Are Most Damaging?

At the attack-family level, the strongest direct family is `action_mask_false_unavailable` with mean degradation 46.603 kWh, maximum degradation 289.271 kWh, and 8 damaging cases out of 30.
The strongest coordinated IEEE 34 attack is `dispatch_s890_branchflow_l8_voltage_816` with mean degradation 3080.849 kWh and maximum degradation 9115.475 kWh. This result is dominated by the dispatch-load status/control observation `Load_s890`; branchflow and voltage components should be interpreted as coordinated context unless they are shown damaging as standalone attacks.
Across the master evidence table, the top ranked row is `dispatch_s890_branchflow_l8_voltage_816` from `coordinated_attack_study` with mean degradation 3080.849 kWh.

## Which Observations Are Most Critical?

The most critical individual observation is `action_mask.Load_s890` under `false unavailable dispatch-load action` with mean degradation 3038.190 kWh and maximum degradation 8832.380 kWh. This is a direct current-controller observation and is therefore suitable for the IEEE 34 paper claim.
The ranked criticality table separates dispatch-load action-mask observations, switch action-mask observations, line-status/topology observations, voltage measurements, and branchflow measurements. Standalone branchflow hiding is retained in the table even when it produces zero positive restored-energy degradation, because that negative result is scientifically useful.

## How Much Restored Energy Is Lost?

Use the manuscript tables to report both mean and maximum physical degradation. The main restored-energy-loss claim for IEEE 34 should emphasize `mean_physical_degradation_kwh`, `max_physical_degradation_kwh`, and `damaging_case_count`; `mean_restored_energy_loss_kwh` can be negative when some attack realizations accidentally improve restoration, so it is not the cleanest damage metric by itself.

## Detection and Mitigation

The relaxed status-tolerance detector exposes the clearest bypass story: `highimpact_dispatch_s890_voltage_816` with gated candidate screening has mean degradation 3080.849 kWh, detection rate 66.7%, bypass rate 0.0%, and residual degradation after mitigation 3050.395 kWh.
Always-reference screening is the strongest robust-mitigation benchmark in the current IEEE 34 evidence, reaching up to 100.0% mean degradation recovery in the selected stress rows. This should be described as a stronger trusted-reference screening mode, not as a free detector replacement.
Strict status-integrity checks remain central for high-impact action-mask/status attacks. Relaxing binary status assumptions can let damaging Load_s890-centered attacks pass the gate, while robust candidate screening can recover much of the lost performance when a trusted/reference candidate is considered.

## Learning Detector Ablation

A learning-detector ablation has been generated using the existing IEEE 34 trained detector artifacts. The largest detection-rate increase in the ablation table is for `highimpact_dispatch_s890_line_l8_voltage_816` / `relaxed_status_tolerance` / `gated_candidate_screening`, with a detection change of 30.0 percentage points.
The learning-model summary table should be used carefully: it reports held-out model metrics, while the ablation table reports downstream restoration-defense behavior.

## Recommended Manuscript Use

Use Table 1 for the global damage ranking, Table 2 for attack-family comparisons, Table 3 for critical observations, Table 4 for coordinated attacks, Table 5 for advanced detection/mitigation stress testing, and the learning-ablation/model-summary tables only if their generated outputs are included in the final evidence package.

For figures, use the top-master-degradation and observation-criticality plots in the vulnerability section, the coordinated-degradation plot in the attack-scenario section, and the advanced-residual plus detection-bypass plots in the defense section.
