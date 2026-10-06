# IEEE 123 Defense Stress Summary

This summary combines completed IEEE 123 case-level evidence only.

## Top Residual-Risk Groups

| Source | Group | Cases | Damaging | Detection | Total degradation kWh | Residual kWh | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| action_mask_single_criticality_partial | action_mask.Load_s82a | 30 | 19 | 1.000 | 13635.136 | 1290.263 | 0.905 |
| action_mask_single_criticality_partial | action_mask.Load_s88a | 30 | 13 | 1.000 | 9079.693 | 849.639 | 0.906 |
| action_mask_single_criticality_partial | action_mask.Load_s109a | 30 | 17 | 1.000 | 10249.179 | 232.796 | 0.977 |
| action_mask_single_criticality_partial | action_mask.Load_s107b | 30 | 22 | 1.000 | 13508.764 | 167.644 | 0.988 |
| action_mask_single_criticality_partial | action_mask.swsec13 | 30 | 10 | 1.000 | 22.635 | 21.875 | 0.034 |
| action_mask_single_criticality_partial | action_mask.swtie8 | 30 | 9 | 1.000 | 19.455 | 19.455 | 0.000 |
| action_mask_single_criticality_partial | action_mask.swtie6 | 30 | 6 | 1.000 | 95.832 | 10.024 | 0.895 |
| baseline_attack_family | branchflow_hiding | 30 | 6 | 0.800 | 3121.162 | 5.196 | 0.998 |
| branchflow_coordinated_subset_ablation | branchflow_subset_kfull | 6 | 6 | 1.000 | 3121.162 | 5.196 | 0.998 |
| action_mask_single_criticality_partial | action_mask.Load_s20a | 30 | 17 | 1.000 | 12819.458 | 4.510 | 1.000 |
| baseline_attack_family | topology_drop | 30 | 3 | 1.000 | 1686.653 | 3.695 | 0.998 |
| action_mask_single_criticality_partial | action_mask.swsec3 | 30 | 9 | 0.967 | 86.437 | 3.693 | 0.957 |

## Bypass Cases

High-impact bypass cases found: `0`.

## Detected But Low-Recovery Cases

| Source | Group | Case | Degradation kWh | Residual kWh | Recovery |
|---|---|---|---:|---:|---:|
| action_mask_single_criticality_partial | action_mask.Load_s88a | AM0002_T0025_action_mask_Load_s88a_seed1519571662 | 849.639 | 849.639 | 0.000 |
| action_mask_single_criticality_partial | action_mask.Load_s82a | AM0019_T0022_action_mask_Load_s82a_seed1755757406 | 674.986 | 674.986 | 0.000 |
| action_mask_single_criticality_partial | action_mask.Load_s82a | AM0023_T0022_action_mask_Load_s82a_seed894593567 | 615.277 | 615.277 | 0.000 |
| action_mask_single_criticality_partial | action_mask.Load_s109a | AM0026_T0029_action_mask_Load_s109a_seed1985582968 | 196.736 | 196.736 | 0.000 |
| action_mask_single_criticality_partial | action_mask.Load_s107b | AM0019_T0028_action_mask_Load_s107b_seed1755757406 | 97.023 | 97.023 | 0.000 |
| action_mask_single_criticality_partial | action_mask.Load_s109a | AM0019_T0029_action_mask_Load_s109a_seed1755757406 | 36.060 | 36.060 | 0.000 |
| action_mask_single_criticality_partial | action_mask.Load_s107b | AM0004_T0028_action_mask_Load_s107b_seed891296660 | 34.618 | 34.618 | 0.000 |
| action_mask_single_criticality_partial | action_mask.Load_s107b | AM0022_T0028_action_mask_Load_s107b_seed996050191 | 34.618 | 34.618 | 0.000 |
| action_mask_single_criticality_partial | action_mask.swtie8 | AM0011_T0020_action_mask_swtie8_seed830125963 | 8.522 | 8.522 | 0.000 |
| action_mask_single_criticality_partial | action_mask.swsec13 | AM0011_T0012_action_mask_swsec13_seed830125963 | 8.522 | 8.522 | 0.000 |
| baseline_attack_family | branchflow_hiding | B0015_branchflow_hiding_seed630833044 | 5.193 | 5.193 | 0.000 |
| branchflow_coordinated_subset_ablation | branchflow_subset_kfull | BFAB_C0003_Kfull_seed630833044 | 5.193 | 5.193 | 0.000 |
| action_mask_single_criticality_partial | action_mask.swtie8 | AM0000_T0020_action_mask_swtie8_seed380655884 | 4.722 | 4.722 | 0.000 |
| action_mask_single_criticality_partial | action_mask.swsec13 | AM0000_T0012_action_mask_swsec13_seed380655884 | 4.722 | 4.722 | 0.000 |
| action_mask_single_criticality_partial | action_mask.Load_s20a | AM0010_T0038_action_mask_Load_s20a_seed1391317448 | 4.510 | 4.510 | 0.000 |

## Worst Residual Cases

| Source | Group | Case | Detected | Degradation kWh | Residual kWh |
|---|---|---|---:|---:|---:|
| action_mask_single_criticality_partial | action_mask.Load_s88a | AM0002_T0025_action_mask_Load_s88a_seed1519571662 | 1 | 849.639 | 849.639 |
| action_mask_single_criticality_partial | action_mask.Load_s82a | AM0019_T0022_action_mask_Load_s82a_seed1755757406 | 1 | 674.986 | 674.986 |
| action_mask_single_criticality_partial | action_mask.Load_s82a | AM0023_T0022_action_mask_Load_s82a_seed894593567 | 1 | 615.277 | 615.277 |
| action_mask_single_criticality_partial | action_mask.Load_s109a | AM0026_T0029_action_mask_Load_s109a_seed1985582968 | 1 | 196.736 | 196.736 |
| action_mask_single_criticality_partial | action_mask.Load_s107b | AM0019_T0028_action_mask_Load_s107b_seed1755757406 | 1 | 97.023 | 97.023 |
| action_mask_single_criticality_partial | action_mask.Load_s109a | AM0019_T0029_action_mask_Load_s109a_seed1755757406 | 1 | 36.060 | 36.060 |
| action_mask_single_criticality_partial | action_mask.Load_s107b | AM0004_T0028_action_mask_Load_s107b_seed891296660 | 1 | 34.618 | 34.618 |
| action_mask_single_criticality_partial | action_mask.Load_s107b | AM0022_T0028_action_mask_Load_s107b_seed996050191 | 1 | 34.618 | 34.618 |
| action_mask_single_criticality_partial | action_mask.swtie8 | AM0011_T0020_action_mask_swtie8_seed830125963 | 1 | 8.522 | 8.522 |
| action_mask_single_criticality_partial | action_mask.swsec13 | AM0011_T0012_action_mask_swsec13_seed830125963 | 1 | 8.522 | 8.522 |
| baseline_attack_family | branchflow_hiding | B0015_branchflow_hiding_seed630833044 | 1 | 5.193 | 5.193 |
| branchflow_coordinated_subset_ablation | branchflow_subset_kfull | BFAB_C0003_Kfull_seed630833044 | 1 | 5.193 | 5.193 |
| action_mask_single_criticality_partial | action_mask.swtie8 | AM0000_T0020_action_mask_swtie8_seed380655884 | 1 | 4.722 | 4.722 |
| action_mask_single_criticality_partial | action_mask.swsec13 | AM0000_T0012_action_mask_swsec13_seed380655884 | 1 | 4.722 | 4.722 |
| action_mask_single_criticality_partial | action_mask.Load_s20a | AM0010_T0038_action_mask_Load_s20a_seed1391317448 | 1 | 4.510 | 4.510 |

