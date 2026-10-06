# IEEE 123 Advanced Mitigation Ablation

This ablation reruns the detected hard residual IEEE 123 FDIA cases and compares mitigation variants.

## Variant Summary

| Variant | Cases | Residual kWh | Recovered kWh | Recovery | Improved vs current | Worse vs current |
|---|---:|---:|---:|---:|---:|---:|
| all_channel_reference_only | 2 | 0.000000 | 56.532356 | 1.000000 | 2 | 0 |
| detector_mitigated_only | 2 | 0.000000 | 56.532356 | 1.000000 | 2 | 0 |
| horizon_screen_raw_mitigated | 2 | 0.000000 | 56.532356 | 1.000000 | 2 | 0 |
| horizon_screen_raw_mitigated_reference | 2 | 0.000000 | 56.532356 | 1.000000 | 2 | 0 |
| attacked_no_defense | 2 | 56.532356 | 0.000000 | 0.000000 | 0 | 0 |
| current_one_step_fdia_aware | 2 | 56.532356 | 0.000000 | 0.000000 | 0 | 0 |

## Best Variant By Case

| Source case | Group | Best variant | Current residual kWh | Best residual kWh | Reduction kWh |
|---|---|---|---:|---:|---:|
| B0026_action_mask_false_unavailable_seed1985582968 | action_mask_false_unavailable | detector_mitigated_only | 33.071162 | 0.000000 | 33.071162 |
| B0018_action_mask_false_unavailable_seed1675750130 | action_mask_false_unavailable | detector_mitigated_only | 23.461195 | 0.000000 | 23.461195 |

