# IEEE 34 Master Evidence and Observation Audit

Generated: 2026-06-16 12:21:30 local time

This file summarizes completed deterministic IEEE 34 evidence and audits which
observation families are true current GRL inputs. It is intended to prevent
paper claims from drifting beyond what the controller actually observes.

## Output Files

- master_evidence: `paper_results\tsg_ieee34\master_evidence_audit\ieee34_master_evidence_table.csv`
- study_summary: `paper_results\tsg_ieee34\master_evidence_audit\ieee34_study_summary.csv`
- observation_family_audit: `paper_results\tsg_ieee34\master_evidence_audit\ieee34_observation_family_audit.csv`
- attack_surface_audit: `paper_results\tsg_ieee34\master_evidence_audit\ieee34_attack_surface_audit.csv`
- markdown_summary: `paper_results\tsg_ieee34\master_evidence_audit\IEEE34_Master_Evidence_Audit.md`
- manifest: `paper_results\tsg_ieee34\master_evidence_audit\ieee34_master_evidence_manifest.json`

## Top Evidence Rows

| global_damage_rank | study_id | attack_or_corruption | entity_id | mean_physical_degradation_kwh | max_physical_degradation_kwh | damaging_case_count | detection_rate | bypass_high_impact_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | coordinated_attack_study | dispatch_s890_branchflow_l8_voltage_816 | action_mask.Load_s890;branchflow.Line.l8;bus_voltage.816 | 3080.849 | 9115.475 | 17 | 1.000 | 0.000 |
| 2 | coordinated_attack_study | dispatch_s890_voltage_816 | action_mask.Load_s890;bus_voltage.816 | 3080.849 | 9115.475 | 17 | 1.000 | 0.000 |
| 3 | advanced_defense_stealth_stress | highimpact_dispatch_s890_voltage_816: relaxed_status_tolerance:gated_candidate_screening | action_mask.Load_s890;bus_voltage.816 | 3080.849 | 9115.475 | 17 | 0.667 | 0.000 |
| 4 | advanced_defense_stealth_stress | highimpact_dispatch_s890_voltage_816: current_residual:always_reference_screening | action_mask.Load_s890;bus_voltage.816 | 3080.849 | 9115.475 | 17 | 1.000 | 0.000 |
| 5 | advanced_defense_stealth_stress | highimpact_dispatch_s890_voltage_816: current_residual:gated_candidate_screening | action_mask.Load_s890;bus_voltage.816 | 3080.849 | 9115.475 | 17 | 1.000 | 0.000 |
| 6 | advanced_defense_stealth_stress | highimpact_dispatch_s890_voltage_816: relaxed_status_tolerance:always_reference_screening | action_mask.Load_s890;bus_voltage.816 | 3080.849 | 9115.475 | 17 | 0.667 | 0.000 |
| 7 | advanced_defense_stealth_stress | highimpact_dispatch_s890_voltage_816: strict_integrity:always_reference_screening | action_mask.Load_s890;bus_voltage.816 | 3080.849 | 9115.475 | 17 | 1.000 | 0.000 |
| 8 | advanced_defense_stealth_stress | highimpact_dispatch_s890_voltage_816: strict_integrity:gated_candidate_screening | action_mask.Load_s890;bus_voltage.816 | 3080.849 | 9115.475 | 17 | 1.000 | 0.000 |
| 9 | advanced_defense_learning_stealth_stress | highimpact_dispatch_s890_voltage_816: relaxed_status_tolerance:gated_candidate_screening | action_mask.Load_s890;bus_voltage.816 | 3080.849 | 9115.475 | 17 | 0.667 | 0.000 |
| 10 | advanced_defense_learning_stealth_stress | highimpact_dispatch_s890_voltage_816: current_residual:always_reference_screening | action_mask.Load_s890;bus_voltage.816 | 3080.849 | 9115.475 | 17 | 1.000 | 0.000 |
| 11 | advanced_defense_learning_stealth_stress | highimpact_dispatch_s890_voltage_816: current_residual:gated_candidate_screening | action_mask.Load_s890;bus_voltage.816 | 3080.849 | 9115.475 | 17 | 1.000 | 0.000 |
| 12 | advanced_defense_learning_stealth_stress | highimpact_dispatch_s890_voltage_816: relaxed_status_tolerance:always_reference_screening | action_mask.Load_s890;bus_voltage.816 | 3080.849 | 9115.475 | 17 | 0.667 | 0.000 |

## Observation Family Audit

| family | total_registry_count | attackable_current_grl_input_count | direct_current_grl_attack_surface | audit_note |
| --- | --- | --- | --- | --- |
| action_mask | 19 | 19 | yes | Direct current policy input; valid for switch and dispatch-load action-availability attacks. |
| branchflow | 40 | 40 | yes | Direct current GRL measurement input; branchflow FDIA is valid. |
| der | 4 | 0 | no | DER metadata exists for generator buses, but DER availability/capacity is not a current direct GRL observation. A DER-specific FDIA study needs a controller-input extension or a clearly separate physical-contingency study. |
| global | 3 | 3 | yes | Direct scalar GRL inputs for energy supply, voltage violation, and convergence violation. |
| load | 68 | 0 | no | Load demand metadata exists, but load demand is not a current direct GRL observation. Load-control availability is attackable through ActionMasking dispatch_load entries. |
| topology | 40 | 40 | yes | Direct current GRL input through Adjacency; valid for line-status/topology attacks. |
| voltage | 37 | 37 | yes | Direct current GRL measurement input; voltage FDIA is valid. |

## Professor Requirement Audit

| professor_requirement_area | direct_current_grl_input | valid_current_attack | recommended_next_step |
| --- | --- | --- | --- |
| topology/status FDIA | yes | yes | Use the completed coordinated results to select high-impact cases for advanced detector/mitigation stress tests. |
| switch/breaker/line status corruption | yes | yes | Stress-test high-impact switch/load/line combinations under stronger detector and stealth settings. |
| load attack | partial | yes for load-control status via ActionMasking; no for pure load-demand observation FDIA | Use high-impact dispatch-load targets in coordinated attacks; treat load-demand bias as a future controller-input extension unless the model is changed. |
| DER attack | no | not as current observation FDIA | Do not fake DER observation FDIA. Either extend controller observation/model or define a separate physical DER-contingency study. |
| fault-status attack | no | not as named fault-status observation FDIA | Do not claim explicit fault-status FDIA unless a formal fault-status observation channel is added. |
| voltage measurement attack | yes | yes | Use voltage false-low targets in advanced stealth and detector-threshold sensitivity tests. |
| branchflow measurement attack | yes | yes | Treat branchflow as a coordinated/stealth channel unless a separate action-targeted branchflow perturbation is added. |
| coordinated and stealthy attacks | yes | yes | Use the high-impact relaxed-detector bypass cases to motivate strict status-integrity detection, robust mitigation, and cross-system replication on IEEE 123. |

## Main Next Implementation Recommendation

Next convert the IEEE 34 evidence into paper-ready figures/tables
and then replicate the same audited workflow on IEEE 123. The IEEE
34 advanced stress study shows that strict status-integrity
detection is essential for Load_s890-centered attacks: relaxed
status thresholds create high-impact bypass cases under gated
mitigation. Do not claim load-demand, DER-availability, or
fault-status observation FDIA unless the controller observation is
extended or the attack is explicitly defined as a separate
physical-contingency study.

