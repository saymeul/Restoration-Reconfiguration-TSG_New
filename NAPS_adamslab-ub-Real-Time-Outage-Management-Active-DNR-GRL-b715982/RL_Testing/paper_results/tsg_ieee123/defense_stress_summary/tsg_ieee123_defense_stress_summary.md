# IEEE 123 Defense Stress Summary

This summary combines completed IEEE 123 case-level evidence only.

## Top Residual-Risk Groups

| Source | Group | Cases | Damaging | Detection | Total degradation kWh | Residual kWh | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline_attack_family | branchflow_hiding | 30 | 6 | 0.800 | 3121.162 | 5.196 | 0.998 |
| branchflow_coordinated_subset_ablation | branchflow_subset_kfull | 6 | 6 | 1.000 | 3121.162 | 5.196 | 0.998 |
| baseline_attack_family | topology_drop | 30 | 3 | 1.000 | 1686.653 | 3.695 | 0.998 |
| branchflow_coordinated_subset_ablation | branchflow_subset_k10 | 6 | 6 | 1.000 | 3130.509 | 0.003 | 1.000 |
| branchflow_coordinated_subset_ablation | branchflow_subset_k5 | 6 | 5 | 1.000 | 2332.344 | 0.003 | 1.000 |
| action_mask_single_criticality_partial | action_mask.swsec6 | 30 | 11 | 0.967 | 337.636 | 0.002 | 1.000 |
| branchflow_coordinated_subset_ablation | branchflow_subset_k3 | 6 | 4 | 1.000 | 2332.341 | 0.000 | 1.000 |
| baseline_attack_family | voltage_masking | 30 | 1 | 0.867 | 786.306 | 0.000 | 1.000 |
| baseline_attack_family | energy_inflation | 30 | 1 | 1.000 | 322.342 | 0.000 | 1.000 |
| action_mask_single_criticality_partial | action_mask.swsec7 | 30 | 14 | 1.000 | 272.418 | 0.000 | 1.000 |
| baseline_attack_family | action_mask_false_unavailable | 30 | 9 | 1.000 | 227.576 | 0.000 | 1.000 |
| branchflow_single_criticality_partial | branchflow.Line.l115 | 30 | 1 | 0.767 | 0.022 | 0.000 | 1.000 |

## Bypass Cases

High-impact bypass cases found: `0`.

## Detected But Low-Recovery Cases

| Source | Group | Case | Degradation kWh | Residual kWh | Recovery |
|---|---|---|---:|---:|---:|
| baseline_attack_family | branchflow_hiding | B0015_branchflow_hiding_seed630833044 | 5.193 | 5.193 | 0.000 |
| branchflow_coordinated_subset_ablation | branchflow_subset_kfull | BFAB_C0003_Kfull_seed630833044 | 5.193 | 5.193 | 0.000 |
| baseline_attack_family | topology_drop | B0003_topology_drop_seed175394891 | 3.695 | 3.695 | 0.000 |
| baseline_attack_family | branchflow_hiding | B0011_branchflow_hiding_seed830125963 | 0.003 | 0.003 | 0.000 |
| branchflow_coordinated_subset_ablation | branchflow_subset_k5 | BFAB_C0005_K5_seed830125963 | 0.003 | 0.003 | 0.000 |
| branchflow_coordinated_subset_ablation | branchflow_subset_k10 | BFAB_C0005_K10_seed830125963 | 0.003 | 0.003 | 0.000 |
| branchflow_coordinated_subset_ablation | branchflow_subset_kfull | BFAB_C0005_Kfull_seed830125963 | 0.003 | 0.003 | 0.000 |
| action_mask_single_criticality_partial | action_mask.swsec6 | AM0015_T0005_action_mask_swsec6_seed630833044 | 0.002 | 0.002 | 0.000 |

## Worst Residual Cases

| Source | Group | Case | Detected | Degradation kWh | Residual kWh |
|---|---|---|---:|---:|---:|
| baseline_attack_family | branchflow_hiding | B0015_branchflow_hiding_seed630833044 | 1 | 5.193 | 5.193 |
| branchflow_coordinated_subset_ablation | branchflow_subset_kfull | BFAB_C0003_Kfull_seed630833044 | 1 | 5.193 | 5.193 |
| baseline_attack_family | topology_drop | B0003_topology_drop_seed175394891 | 1 | 3.695 | 3.695 |
| baseline_attack_family | branchflow_hiding | B0011_branchflow_hiding_seed830125963 | 1 | 0.003 | 0.003 |
| branchflow_coordinated_subset_ablation | branchflow_subset_k5 | BFAB_C0005_K5_seed830125963 | 1 | 0.003 | 0.003 |
| branchflow_coordinated_subset_ablation | branchflow_subset_k10 | BFAB_C0005_K10_seed830125963 | 1 | 0.003 | 0.003 |
| branchflow_coordinated_subset_ablation | branchflow_subset_kfull | BFAB_C0005_Kfull_seed830125963 | 1 | 0.003 | 0.003 |
| action_mask_single_criticality_partial | action_mask.swsec6 | AM0015_T0005_action_mask_swsec6_seed630833044 | 1 | 0.002 | 0.002 |
| baseline_attack_family | topology_drop | B0021_topology_drop_seed1568965551 | 1 | 0.000 | 0.000 |
| baseline_attack_family | branchflow_hiding | B0014_branchflow_hiding_seed611696197 | 1 | 1559.847 | 0.000 |
| branchflow_coordinated_subset_ablation | branchflow_subset_kfull | BFAB_C0000_Kfull_seed611696197 | 1 | 1559.847 | 0.000 |
| baseline_attack_family | topology_drop | B0002_topology_drop_seed1519571662 | 1 | 884.793 | 0.000 |
| baseline_attack_family | branchflow_hiding | B0002_branchflow_hiding_seed1519571662 | 1 | 884.428 | 0.000 |
| branchflow_coordinated_subset_ablation | branchflow_subset_k3 | BFAB_C0001_K3_seed1519571662 | 1 | 884.428 | 0.000 |
| branchflow_coordinated_subset_ablation | branchflow_subset_k5 | BFAB_C0001_K5_seed1519571662 | 1 | 884.428 | 0.000 |

