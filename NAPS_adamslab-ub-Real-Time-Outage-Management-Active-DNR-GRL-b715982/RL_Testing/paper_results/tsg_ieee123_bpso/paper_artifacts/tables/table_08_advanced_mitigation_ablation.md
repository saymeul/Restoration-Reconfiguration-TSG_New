# Table 8. IEEE 123 Advanced Mitigation Ablation

| variant | variant_family | case_count | total_attacked_degradation_kwh | total_residual_kwh | max_residual_kwh | total_recovered_kwh | total_recovery_pct | cases_improved_vs_current | cases_worse_vs_current | total_residual_reduction_vs_current_kwh |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_channel_reference_only | advanced_candidate | 60 | 58610.708 | 0.000 | 0.000 | 58610.708 | 100.000 | 60 | 0 | 58610.708 |
| detector_mitigated_only | advanced_candidate | 60 | 58610.708 | 0.000 | 0.000 | 58610.708 | 100.000 | 60 | 0 | 58610.708 |
| horizon_screen_raw_mitigated | advanced_horizon_screening | 60 | 58610.708 | 0.000 | 0.000 | 58610.708 | 100.000 | 60 | 0 | 58610.708 |
| horizon_screen_raw_mitigated_reference | advanced_horizon_screening | 60 | 58610.708 | 0.000 | 0.000 | 58610.708 | 100.000 | 60 | 0 | 58610.708 |
| attacked_no_defense | baseline | 60 | 58610.708 | 58610.708 | 5490.851 | 0.000 | 0.000 | 0 | 0 | 0.000 |
| current_one_step_fdia_aware | current_mitigation | 60 | 58610.708 | 58610.708 | 5490.851 | 0.000 | 0.000 | 0 | 0 | 0.000 |
