# Table 7. IEEE 123 Advanced Mitigation Ablation

| variant | variant_family | case_count | total_attacked_degradation_kwh | total_residual_kwh | max_residual_kwh | total_recovered_kwh | total_recovery_pct | cases_improved_vs_current | cases_worse_vs_current | total_residual_reduction_vs_current_kwh |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_channel_reference_only | advanced_candidate | 58 | 2617.432 | 0.000 | 0.000 | 2617.432 | 100.000 | 58 | 0 | 2617.432 |
| detector_mitigated_only | advanced_candidate | 58 | 2617.432 | 0.000 | 0.000 | 2617.432 | 100.000 | 58 | 0 | 2617.432 |
| horizon_screen_raw_mitigated | advanced_horizon_screening | 58 | 2617.432 | 0.000 | 0.000 | 2617.432 | 100.000 | 58 | 0 | 2617.432 |
| horizon_screen_raw_mitigated_reference | advanced_horizon_screening | 58 | 2617.432 | 0.000 | 0.000 | 2617.432 | 100.000 | 58 | 0 | 2617.432 |
| attacked_no_defense | baseline | 58 | 2617.432 | 2617.432 | 849.639 | 0.000 | 0.000 | 0 | 0 | 0.000 |
| current_one_step_fdia_aware | current_mitigation | 58 | 2617.432 | 2617.432 | 849.639 | 0.000 | 0.000 | 0 | 0 | 0.000 |
