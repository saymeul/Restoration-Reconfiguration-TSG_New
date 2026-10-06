# IEEE 123 Advanced Mitigation Ablation

This ablation reruns the detected hard residual IEEE 123 FDIA cases and compares mitigation variants.

## Variant Summary

| Variant | Cases | Residual kWh | Recovered kWh | Recovery | Improved vs current | Worse vs current |
|---|---:|---:|---:|---:|---:|---:|
| all_channel_reference_only | 8 | 0.000000 | 14.095640 | 1.000000 | 8 | 0 |
| detector_mitigated_only | 8 | 0.000000 | 14.095640 | 1.000000 | 8 | 0 |
| horizon_screen_raw_mitigated | 8 | 0.000000 | 14.095640 | 1.000000 | 8 | 0 |
| horizon_screen_raw_mitigated_reference | 8 | 0.000000 | 14.095640 | 1.000000 | 8 | 0 |
| attacked_no_defense | 8 | 14.095640 | 0.000000 | 0.000000 | 0 | 0 |
| current_one_step_fdia_aware | 8 | 14.095640 | 0.000000 | 0.000000 | 0 | 0 |

## Best Variant By Case

| Source case | Group | Best variant | Current residual kWh | Best residual kWh | Reduction kWh |
|---|---|---|---:|---:|---:|
| B0015_branchflow_hiding_seed630833044 | branchflow_hiding | detector_mitigated_only | 5.193085 | 0.000000 | 5.193085 |
| BFAB_C0003_Kfull_seed630833044 | branchflow_subset_kfull | detector_mitigated_only | 5.193085 | 0.000000 | 5.193085 |
| B0003_topology_drop_seed175394891 | topology_drop | detector_mitigated_only | 3.694644 | 0.000000 | 3.694644 |
| B0011_branchflow_hiding_seed830125963 | branchflow_hiding | detector_mitigated_only | 0.003205 | 0.000000 | 0.003205 |
| BFAB_C0005_K10_seed830125963 | branchflow_subset_k10 | detector_mitigated_only | 0.003205 | 0.000000 | 0.003205 |
| BFAB_C0005_K5_seed830125963 | branchflow_subset_k5 | detector_mitigated_only | 0.003205 | 0.000000 | 0.003205 |
| BFAB_C0005_Kfull_seed830125963 | branchflow_subset_kfull | detector_mitigated_only | 0.003205 | 0.000000 | 0.003205 |
| AM0015_T0005_action_mask_swsec6_seed630833044 | action_mask.swsec6 | detector_mitigated_only | 0.002007 | 0.000000 | 0.002007 |

