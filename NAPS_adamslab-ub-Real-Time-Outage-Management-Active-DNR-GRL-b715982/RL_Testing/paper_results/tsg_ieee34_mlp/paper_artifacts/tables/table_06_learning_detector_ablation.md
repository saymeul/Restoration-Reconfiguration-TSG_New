# Table 6. IEEE 34 Learning Detector Ablation

| attack_id | detector_profile | mitigation_mode | base_detection_rate_pct | learning_detection_rate_pct | detection_delta_pct | base_bypass_rate_pct | learning_bypass_rate_pct | bypass_delta_pct | base_residual_degradation_kwh | learning_residual_degradation_kwh | residual_delta_kwh | base_recovery_pct | learning_recovery_pct | recovery_delta_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| highimpact_dispatch_s890_line_l8_voltage_816 | relaxed_status_tolerance | always_reference_screening | 66.667 | 96.667 | 30.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| highimpact_dispatch_s890_line_l8_voltage_816 | relaxed_status_tolerance | gated_candidate_screening | 66.667 | 96.667 | 30.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| highimpact_dispatch_s890_line_l8_voltage_816 | current_residual | always_reference_screening | 100.000 | 100.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| highimpact_dispatch_s890_line_l8_voltage_816 | current_residual | gated_candidate_screening | 100.000 | 100.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| highimpact_dispatch_s890_line_l8_voltage_816 | strict_integrity | always_reference_screening | 100.000 | 100.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| highimpact_dispatch_s890_line_l8_voltage_816 | strict_integrity | gated_candidate_screening | 100.000 | 100.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| highimpact_dispatch_s890_switch_swtie4 | current_residual | always_reference_screening | 100.000 | 100.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| highimpact_dispatch_s890_switch_swtie4 | current_residual | gated_candidate_screening | 100.000 | 100.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| highimpact_dispatch_s890_switch_swtie4 | relaxed_status_tolerance | always_reference_screening | 100.000 | 100.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| highimpact_dispatch_s890_switch_swtie4 | relaxed_status_tolerance | gated_candidate_screening | 100.000 | 100.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| highimpact_dispatch_s890_switch_swtie4 | strict_integrity | always_reference_screening | 100.000 | 100.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| highimpact_dispatch_s890_switch_swtie4 | strict_integrity | gated_candidate_screening | 100.000 | 100.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| highimpact_dispatch_s890_voltage_816 | current_residual | always_reference_screening | 100.000 | 100.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| highimpact_dispatch_s890_voltage_816 | current_residual | gated_candidate_screening | 100.000 | 100.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| highimpact_dispatch_s890_voltage_816 | relaxed_status_tolerance | always_reference_screening | 66.667 | 66.667 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| highimpact_dispatch_s890_voltage_816 | relaxed_status_tolerance | gated_candidate_screening | 66.667 | 66.667 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| highimpact_dispatch_s890_voltage_816 | strict_integrity | always_reference_screening | 100.000 | 100.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| highimpact_dispatch_s890_voltage_816 | strict_integrity | gated_candidate_screening | 100.000 | 100.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| stealth_branchflow_l8_small_only | current_residual | always_reference_screening | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| stealth_branchflow_l8_small_only | current_residual | gated_candidate_screening | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| stealth_branchflow_l8_small_only | relaxed_status_tolerance | always_reference_screening | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| stealth_branchflow_l8_small_only | relaxed_status_tolerance | gated_candidate_screening | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| stealth_branchflow_l8_small_only | strict_integrity | always_reference_screening | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| stealth_branchflow_l8_small_only | strict_integrity | gated_candidate_screening | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| stealth_load_s890_branchflow_l8_small | current_residual | always_reference_screening | 100.000 | 100.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| stealth_load_s890_branchflow_l8_small | current_residual | gated_candidate_screening | 100.000 | 100.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| stealth_load_s890_branchflow_l8_small | relaxed_status_tolerance | always_reference_screening | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| stealth_load_s890_branchflow_l8_small | relaxed_status_tolerance | gated_candidate_screening | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| stealth_load_s890_branchflow_l8_small | strict_integrity | always_reference_screening | 100.000 | 100.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| stealth_load_s890_branchflow_l8_small | strict_integrity | gated_candidate_screening | 100.000 | 100.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

Markdown preview shows first 30 of 48 rows.
