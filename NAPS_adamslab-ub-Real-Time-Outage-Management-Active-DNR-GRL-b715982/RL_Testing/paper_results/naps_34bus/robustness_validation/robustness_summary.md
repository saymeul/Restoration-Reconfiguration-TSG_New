# FDIA Robustness Validation Summary

## Trial Statistics by System and Attack

| System | Attack | Trials | Harmful Cases | Harmful Rate (95% CI) | Mean Impact (95% CI) | Max Impact |
|---|---|---:|---:|---:|---:|---:|
| 34bus | branchflow_hiding | 186 | 0 | 0.000000 [0.000000, 0.020236] | 0.000000 [0.000000, 0.000000] | 0.000000 |
| 34bus | energy_inflation | 201 | 1 | 0.004975 [0.000879, 0.027639] | 0.000096 [0.000000, 0.000283] | 0.019230 |
| 34bus | topology_drop | 168 | 13 | 0.077381 [0.045777, 0.127881] | 0.002318 [0.000000, 0.005065] | 0.192946 |
| 34bus | voltage_masking | 195 | 17 | 0.087179 [0.055142, 0.135169] | 0.009512 [0.000000, 0.019551] | 0.703583 |

## Top Recovery Cases

| System | Seed | Scenario | Attack | Attacked Impact | Mitigated Impact | Impact Reduction |
|---|---:|---|---|---:|---:|---:|
| 34bus | 2030 | R0014_seed867880546 | voltage_masking | 0.703583 | 0.000000 | 1.000000 |
| 34bus | 2029 | R0143_seed573070527 | voltage_masking | 0.659342 | 0.000000 | 1.000000 |
| 34bus | 2029 | R0025_seed74242697 | voltage_masking | 0.211433 | 0.000000 | 1.000000 |
| 34bus | 2027 | R0012_seed104905785 | topology_drop | 0.192946 | 0.000000 | 1.000000 |
| 34bus | 2027 | R0081_seed1347394171 | voltage_masking | 0.172379 | 0.000000 | 1.000000 |
| 34bus | 2026 | R0143_seed808199744 | topology_drop | 0.132032 | 0.000000 | 1.000000 |
| 34bus | 2028 | R0147_seed387786182 | voltage_masking | 0.075033 | 0.000000 | 1.000000 |
| 34bus | 2026 | R0023_seed550207905 | topology_drop | 0.025476 | 0.000000 | 1.000000 |
| 34bus | 2027 | R0018_seed1864714207 | topology_drop | 0.025222 | 0.000000 | 1.000000 |
| 34bus | 2026 | R0066_seed346752128 | energy_inflation | 0.019230 | 0.000000 | 1.000000 |

## RL Detector and Recovery Summary

| System | Samples | Correct | Accuracy (95% CI) | Harmful Recovery Samples | Mean Impact Reduction |
|---|---:|---:|---:|---:|---:|
| 34bus | 40 | 40 | 1.000000 [0.912375, 1.000000] | 30 | 1.000000 |
