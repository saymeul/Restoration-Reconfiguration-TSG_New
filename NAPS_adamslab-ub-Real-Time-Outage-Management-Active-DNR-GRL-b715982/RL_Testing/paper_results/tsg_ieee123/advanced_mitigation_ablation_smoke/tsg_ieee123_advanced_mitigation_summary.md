# IEEE 123 Advanced Mitigation Ablation

This ablation reruns the detected hard residual IEEE 123 FDIA cases and compares mitigation variants.

## Variant Summary

| Variant | Cases | Residual kWh | Recovered kWh | Recovery | Improved vs current | Worse vs current |
|---|---:|---:|---:|---:|---:|---:|
| all_channel_reference_only | 1 | 0.000000 | 5.193085 | 1.000000 | 1 | 0 |
| detector_mitigated_only | 1 | 0.000000 | 5.193085 | 1.000000 | 1 | 0 |
| horizon_screen_raw_mitigated | 1 | 0.000000 | 5.193085 | 1.000000 | 1 | 0 |
| horizon_screen_raw_mitigated_reference | 1 | 0.000000 | 5.193085 | 1.000000 | 1 | 0 |
| attacked_no_defense | 1 | 5.193085 | 0.000000 | 0.000000 | 0 | 0 |
| current_one_step_fdia_aware | 1 | 5.193085 | 0.000000 | 0.000000 | 0 | 0 |

## Best Variant By Case

| Source case | Group | Best variant | Current residual kWh | Best residual kWh | Reduction kWh |
|---|---|---|---:|---:|---:|
| B0015_branchflow_hiding_seed630833044 | branchflow_hiding | detector_mitigated_only | 5.193085 | 0.000000 | 5.193085 |

