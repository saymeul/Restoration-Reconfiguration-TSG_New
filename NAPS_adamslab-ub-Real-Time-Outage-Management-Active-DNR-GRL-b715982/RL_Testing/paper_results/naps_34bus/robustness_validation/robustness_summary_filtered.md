# FDIA Robustness Validation Summary - Filtered Paper-Ready Set

## Trial Statistics by System and Attack

| System | Attack | Trials | Harmful Cases | Harmful Rate (95% CI) | Mean Impact (95% CI) | Max Impact |
|---|---|---:|---:|---:|---:|---:|
| 34bus | branchflow_hiding | 150 | 0 | 0.000000 [0.000000, 0.024971] | 0.000000 [0.000000, 0.000000] | 0.000000 |
| 34bus | energy_inflation | 163 | 1 | 0.006135 [0.001084, 0.033929] | 0.000118 [0.000000, 0.000349] | 0.019230 |
| 34bus | topology_drop | 137 | 12 | 0.087591 [0.050815, 0.146865] | 0.002842 [0.000000, 0.006207] | 0.192946 |
| 34bus | voltage_masking | 155 | 15 | 0.096774 [0.059525, 0.153527] | 0.007710 [0.000000, 0.017255] | 0.703583 |

## Top Recovery Cases

| System | Seed | Scenario | Attack | Attacked Impact | Mitigated Impact | Impact Reduction |
|---|---:|---|---|---:|---:|---:|
| 34bus | 2030 | R0014_seed867880546 | voltage_masking | 0.703583 | 0.000000 | 1.000000 |
| 34bus | 2029 | R0025_seed74242697 | voltage_masking | 0.211433 | 0.000000 | 1.000000 |
| 34bus | 2027 | R0012_seed104905785 | topology_drop | 0.192946 | 0.000000 | 1.000000 |
| 34bus | 2027 | R0081_seed1347394171 | voltage_masking | 0.172379 | 0.000000 | 1.000000 |
| 34bus | 2026 | R0143_seed808199744 | topology_drop | 0.132032 | 0.000000 | 1.000000 |
| 34bus | 2028 | R0147_seed387786182 | voltage_masking | 0.075033 | 0.000000 | 1.000000 |
| 34bus | 2026 | R0023_seed550207905 | topology_drop | 0.025476 | 0.000000 | 1.000000 |
| 34bus | 2027 | R0018_seed1864714207 | topology_drop | 0.025222 | 0.000000 | 1.000000 |
| 34bus | 2026 | R0066_seed346752128 | energy_inflation | 0.019230 | 0.000000 | 1.000000 |
| 34bus | 2029 | R0140_seed2025955993 | voltage_masking | 0.009138 | 0.000000 | 1.000000 |

## RL Detector and Recovery Summary

| System | Samples | Correct | Accuracy (95% CI) | Harmful Recovery Samples | Mean Impact Reduction |
|---|---:|---:|---:|---:|---:|
| 34bus | 40 | 40 | 1.000000 [0.912375, 1.000000] | 28 | 1.000000 |

## Filter Accounting

| Item | Count | Details |
|---|---:|---|
| raw_trials | 750 | All Monte Carlo trials before paper-ready filtering |
| filtered_trials | 605 | convergence_violation <= 0.0, physical_impact_score <= 5.0, abs(energy_ratio) <= 2.0 |
| excluded_clean_nonconverged | 1 | Excluded from filtered statistics; retained in raw CSV |
| excluded_energy_ratio_outlier | 4 | Excluded from filtered statistics; retained in raw CSV |
| excluded_nonconverged | 140 | Excluded from filtered statistics; retained in raw CSV |
