# Table 1. IEEE 34 Master Evidence Ranking

| rank | study_id | attack_or_corruption | target_observation_id | case_count | mean_degradation_kwh | max_degradation_kwh | damaging_cases | detection_rate_pct | bypass_rate_pct | mitigation_recovery_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | coordinated_attack_study | dispatch_s890_branchflow_l8_voltage_816 | action_mask.Load_s890;branchflow.Line.l8;bus_voltage.816 | 30 | 3080.849 | 9115.475 | 17 | 100.000 | 0.000 | 94.118 |
| 2 | coordinated_attack_study | dispatch_s890_voltage_816 | action_mask.Load_s890;bus_voltage.816 | 30 | 3080.849 | 9115.475 | 17 | 100.000 | 0.000 | 94.118 |
| 3 | advanced_defense_stealth_stress | highimpact_dispatch_s890_voltage_816: relaxed_status_tolerance:gated_candidate_screening | action_mask.Load_s890;bus_voltage.816 | 30 | 3080.849 | 9115.475 | 17 | 66.667 | 0.000 | 7.771 |
| 4 | advanced_defense_stealth_stress | highimpact_dispatch_s890_voltage_816: current_residual:always_reference_screening | action_mask.Load_s890;bus_voltage.816 | 30 | 3080.849 | 9115.475 | 17 | 100.000 | 0.000 | 94.118 |
| 5 | advanced_defense_stealth_stress | highimpact_dispatch_s890_voltage_816: current_residual:gated_candidate_screening | action_mask.Load_s890;bus_voltage.816 | 30 | 3080.849 | 9115.475 | 17 | 100.000 | 0.000 | 94.118 |
| 6 | advanced_defense_stealth_stress | highimpact_dispatch_s890_voltage_816: relaxed_status_tolerance:always_reference_screening | action_mask.Load_s890;bus_voltage.816 | 30 | 3080.849 | 9115.475 | 17 | 66.667 | 0.000 | 94.118 |
| 7 | advanced_defense_stealth_stress | highimpact_dispatch_s890_voltage_816: strict_integrity:always_reference_screening | action_mask.Load_s890;bus_voltage.816 | 30 | 3080.849 | 9115.475 | 17 | 100.000 | 0.000 | 94.118 |
| 8 | advanced_defense_stealth_stress | highimpact_dispatch_s890_voltage_816: strict_integrity:gated_candidate_screening | action_mask.Load_s890;bus_voltage.816 | 30 | 3080.849 | 9115.475 | 17 | 100.000 | 0.000 | 94.118 |
| 9 | advanced_defense_learning_stealth_stress | highimpact_dispatch_s890_voltage_816: relaxed_status_tolerance:gated_candidate_screening | action_mask.Load_s890;bus_voltage.816 | 30 | 3080.849 | 9115.475 | 17 | 66.667 | 0.000 | 7.771 |
| 10 | advanced_defense_learning_stealth_stress | highimpact_dispatch_s890_voltage_816: current_residual:always_reference_screening | action_mask.Load_s890;bus_voltage.816 | 30 | 3080.849 | 9115.475 | 17 | 100.000 | 0.000 | 94.118 |
| 11 | advanced_defense_learning_stealth_stress | highimpact_dispatch_s890_voltage_816: current_residual:gated_candidate_screening | action_mask.Load_s890;bus_voltage.816 | 30 | 3080.849 | 9115.475 | 17 | 100.000 | 0.000 | 94.118 |
| 12 | advanced_defense_learning_stealth_stress | highimpact_dispatch_s890_voltage_816: relaxed_status_tolerance:always_reference_screening | action_mask.Load_s890;bus_voltage.816 | 30 | 3080.849 | 9115.475 | 17 | 66.667 | 0.000 | 94.118 |
| 13 | advanced_defense_learning_stealth_stress | highimpact_dispatch_s890_voltage_816: strict_integrity:always_reference_screening | action_mask.Load_s890;bus_voltage.816 | 30 | 3080.849 | 9115.475 | 17 | 100.000 | 0.000 | 94.118 |
| 14 | advanced_defense_learning_stealth_stress | highimpact_dispatch_s890_voltage_816: strict_integrity:gated_candidate_screening | action_mask.Load_s890;bus_voltage.816 | 30 | 3080.849 | 9115.475 | 17 | 100.000 | 0.000 | 94.118 |
| 15 | coordinated_attack_study | hidden_l28_voltage_816_dispatch_s890 | topology_edge.Line.l28;bus_voltage.816;action_mask.Load_s890 | 30 | 3080.849 | 9115.475 | 17 | 100.000 | 0.000 | 94.118 |
| 16 | coordinated_attack_study | dispatch_s890_line_l8_voltage_816 | action_mask.Load_s890;topology_edge.Line.l8;bus_voltage.816 | 30 | 3065.622 | 9124.530 | 17 | 100.000 | 0.000 | 94.118 |
| 17 | advanced_defense_stealth_stress | highimpact_dispatch_s890_line_l8_voltage_816: relaxed_status_tolerance:gated_candidate_screening | action_mask.Load_s890;topology_edge.Line.l8;bus_voltage.816 | 30 | 3065.622 | 9124.530 | 17 | 66.667 | 0.000 | 0.000 |
| 18 | advanced_defense_stealth_stress | highimpact_dispatch_s890_line_l8_voltage_816: current_residual:always_reference_screening | action_mask.Load_s890;topology_edge.Line.l8;bus_voltage.816 | 30 | 3065.622 | 9124.530 | 17 | 100.000 | 0.000 | 94.118 |
| 19 | advanced_defense_stealth_stress | highimpact_dispatch_s890_line_l8_voltage_816: current_residual:gated_candidate_screening | action_mask.Load_s890;topology_edge.Line.l8;bus_voltage.816 | 30 | 3065.622 | 9124.530 | 17 | 100.000 | 0.000 | 94.118 |
| 20 | advanced_defense_stealth_stress | highimpact_dispatch_s890_line_l8_voltage_816: relaxed_status_tolerance:always_reference_screening | action_mask.Load_s890;topology_edge.Line.l8;bus_voltage.816 | 30 | 3065.622 | 9124.530 | 17 | 66.667 | 0.000 | 94.118 |

Markdown preview shows first 20 of 30 rows.
