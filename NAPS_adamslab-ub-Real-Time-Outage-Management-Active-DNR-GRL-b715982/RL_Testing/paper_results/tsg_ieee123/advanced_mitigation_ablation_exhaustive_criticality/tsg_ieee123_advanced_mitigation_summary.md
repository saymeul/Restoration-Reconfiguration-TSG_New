# IEEE 123 Advanced Mitigation Ablation

This ablation reruns the detected hard residual IEEE 123 FDIA cases and compares mitigation variants.

## Variant Summary

| Variant | Cases | Residual kWh | Recovered kWh | Recovery | Improved vs current | Worse vs current |
|---|---:|---:|---:|---:|---:|---:|
| all_channel_reference_only | 58 | 0.000000 | 2617.431791 | 1.000000 | 58 | 0 |
| detector_mitigated_only | 58 | 0.000000 | 2617.431791 | 1.000000 | 58 | 0 |
| horizon_screen_raw_mitigated | 58 | 0.000000 | 2617.431791 | 1.000000 | 58 | 0 |
| horizon_screen_raw_mitigated_reference | 58 | 0.000000 | 2617.431791 | 1.000000 | 58 | 0 |
| attacked_no_defense | 58 | 2617.431791 | 0.000000 | 0.000000 | 0 | 0 |
| current_one_step_fdia_aware | 58 | 2617.431791 | 0.000000 | 0.000000 | 0 | 0 |

## Best Variant By Case

| Source case | Group | Best variant | Current residual kWh | Best residual kWh | Reduction kWh |
|---|---|---|---:|---:|---:|
| AM0002_T0025_action_mask_Load_s88a_seed1519571662 | action_mask.Load_s88a | detector_mitigated_only | 849.639182 | 0.000000 | 849.639182 |
| AM0019_T0022_action_mask_Load_s82a_seed1755757406 | action_mask.Load_s82a | detector_mitigated_only | 674.986481 | 0.000000 | 674.986481 |
| AM0023_T0022_action_mask_Load_s82a_seed894593567 | action_mask.Load_s82a | detector_mitigated_only | 615.276608 | 0.000000 | 615.276608 |
| AM0026_T0029_action_mask_Load_s109a_seed1985582968 | action_mask.Load_s109a | detector_mitigated_only | 196.736416 | 0.000000 | 196.736416 |
| AM0019_T0028_action_mask_Load_s107b_seed1755757406 | action_mask.Load_s107b | detector_mitigated_only | 97.022832 | 0.000000 | 97.022832 |
| AM0019_T0029_action_mask_Load_s109a_seed1755757406 | action_mask.Load_s109a | detector_mitigated_only | 36.059504 | 0.000000 | 36.059504 |
| AM0004_T0028_action_mask_Load_s107b_seed891296660 | action_mask.Load_s107b | detector_mitigated_only | 34.618273 | 0.000000 | 34.618273 |
| AM0022_T0028_action_mask_Load_s107b_seed996050191 | action_mask.Load_s107b | detector_mitigated_only | 34.618271 | 0.000000 | 34.618271 |
| AM0011_T0020_action_mask_swtie8_seed830125963 | action_mask.swtie8 | detector_mitigated_only | 8.522492 | 0.000000 | 8.522492 |
| AM0011_T0012_action_mask_swsec13_seed830125963 | action_mask.swsec13 | detector_mitigated_only | 8.522492 | 0.000000 | 8.522492 |
| B0015_branchflow_hiding_seed630833044 | branchflow_hiding | detector_mitigated_only | 5.193085 | 0.000000 | 5.193085 |
| BFAB_C0003_Kfull_seed630833044 | branchflow_subset_kfull | detector_mitigated_only | 5.193085 | 0.000000 | 5.193085 |
| AM0000_T0020_action_mask_swtie8_seed380655884 | action_mask.swtie8 | detector_mitigated_only | 4.721781 | 0.000000 | 4.721781 |
| AM0000_T0012_action_mask_swsec13_seed380655884 | action_mask.swsec13 | detector_mitigated_only | 4.721781 | 0.000000 | 4.721781 |
| AM0010_T0038_action_mask_Load_s20a_seed1391317448 | action_mask.Load_s20a | detector_mitigated_only | 4.510001 | 0.000000 | 4.510001 |
| AM0003_T0012_action_mask_swsec13_seed175394891 | action_mask.swsec13 | detector_mitigated_only | 4.353604 | 0.000000 | 4.353604 |
| AM0007_T0012_action_mask_swsec13_seed858031802 | action_mask.swsec13 | detector_mitigated_only | 3.718774 | 0.000000 | 3.718774 |
| AM0007_T0018_action_mask_swtie6_seed858031802 | action_mask.swtie6 | detector_mitigated_only | 3.717393 | 0.000000 | 3.717393 |
| AM0003_T0018_action_mask_swtie6_seed175394891 | action_mask.swtie6 | detector_mitigated_only | 3.694644 | 0.000000 | 3.694644 |
| B0003_topology_drop_seed175394891 | topology_drop | detector_mitigated_only | 3.694644 | 0.000000 | 3.694644 |
| AM0024_T0020_action_mask_swtie8_seed1448425263 | action_mask.swtie8 | detector_mitigated_only | 2.610386 | 0.000000 | 2.610386 |
| AM0024_T0002_action_mask_swsec3_seed1448425263 | action_mask.swsec3 | detector_mitigated_only | 2.610386 | 0.000000 | 2.610386 |
| AM0024_T0018_action_mask_swtie6_seed1448425263 | action_mask.swtie6 | detector_mitigated_only | 2.610386 | 0.000000 | 2.610386 |
| AM0006_T0020_action_mask_swtie8_seed1262161534 | action_mask.swtie8 | detector_mitigated_only | 2.510994 | 0.000000 | 2.510994 |
| AM0005_T0028_action_mask_Load_s107b_seed623645698 | action_mask.Load_s107b | detector_mitigated_only | 0.943077 | 0.000000 | 0.943077 |
| AM0029_T0012_action_mask_swsec13_seed1710510346 | action_mask.swsec13 | detector_mitigated_only | 0.550545 | 0.000000 | 0.550545 |
| AM0003_T0002_action_mask_swsec3_seed175394891 | action_mask.swsec3 | detector_mitigated_only | 0.542071 | 0.000000 | 0.542071 |
| AM0003_T0020_action_mask_swtie8_seed175394891 | action_mask.swtie8 | detector_mitigated_only | 0.542071 | 0.000000 | 0.542071 |
| AM0003_T0008_action_mask_swsec9_seed175394891 | action_mask.swsec9 | detector_mitigated_only | 0.542071 | 0.000000 | 0.542071 |
| AM0003_T0017_action_mask_swtie5_seed175394891 | action_mask.swtie5 | detector_mitigated_only | 0.542071 | 0.000000 | 0.542071 |
| AM0007_T0011_action_mask_swsec12_seed858031802 | action_mask.swsec12 | detector_mitigated_only | 0.540551 | 0.000000 | 0.540551 |
| AM0007_T0002_action_mask_swsec3_seed858031802 | action_mask.swsec3 | detector_mitigated_only | 0.540550 | 0.000000 | 0.540550 |
| AM0007_T0008_action_mask_swsec9_seed858031802 | action_mask.swsec9 | detector_mitigated_only | 0.540550 | 0.000000 | 0.540550 |
| AM0007_T0020_action_mask_swtie8_seed858031802 | action_mask.swtie8 | detector_mitigated_only | 0.540550 | 0.000000 | 0.540550 |
| AM0007_T0017_action_mask_swtie5_seed858031802 | action_mask.swtie5 | detector_mitigated_only | 0.540550 | 0.000000 | 0.540550 |
| AM0003_T0011_action_mask_swsec12_seed175394891 | action_mask.swsec12 | detector_mitigated_only | 0.538575 | 0.000000 | 0.538575 |
| AM0026_T0028_action_mask_Load_s107b_seed1985582968 | action_mask.Load_s107b | detector_mitigated_only | 0.441985 | 0.000000 | 0.441985 |
| AM0027_T0037_action_mask_Load_s16c_seed1868073150 | action_mask.Load_s16c | detector_mitigated_only | 0.123825 | 0.000000 | 0.123825 |
| AM0005_T0024_action_mask_Load_s92c_seed623645698 | action_mask.Load_s92c | detector_mitigated_only | 0.025508 | 0.000000 | 0.025508 |
| AM0018_T0037_action_mask_Load_s16c_seed1675750130 | action_mask.Load_s16c | detector_mitigated_only | 0.020344 | 0.000000 | 0.020344 |
| AM0026_T0037_action_mask_Load_s16c_seed1985582968 | action_mask.Load_s16c | detector_mitigated_only | 0.015795 | 0.000000 | 0.015795 |
| AM0025_T0020_action_mask_swtie8_seed1869647486 | action_mask.swtie8 | detector_mitigated_only | 0.005809 | 0.000000 | 0.005809 |
| AM0025_T0012_action_mask_swsec13_seed1869647486 | action_mask.swsec13 | detector_mitigated_only | 0.005809 | 0.000000 | 0.005809 |
| AM0005_T0037_action_mask_Load_s16c_seed623645698 | action_mask.Load_s16c | detector_mitigated_only | 0.005217 | 0.000000 | 0.005217 |
| B0011_branchflow_hiding_seed830125963 | branchflow_hiding | detector_mitigated_only | 0.003205 | 0.000000 | 0.003205 |
| BFAB_C0005_K10_seed830125963 | branchflow_subset_k10 | detector_mitigated_only | 0.003205 | 0.000000 | 0.003205 |
| BFAB_C0005_K5_seed830125963 | branchflow_subset_k5 | detector_mitigated_only | 0.003205 | 0.000000 | 0.003205 |
| BFAB_C0005_Kfull_seed830125963 | branchflow_subset_kfull | detector_mitigated_only | 0.003205 | 0.000000 | 0.003205 |
| AM0015_T0005_action_mask_swsec6_seed630833044 | action_mask.swsec6 | detector_mitigated_only | 0.002007 | 0.000000 | 0.002007 |
| AM0001_T0020_action_mask_swtie8_seed1491317288 | action_mask.swtie8 | detector_mitigated_only | 0.001381 | 0.000000 | 0.001381 |
| AM0001_T0012_action_mask_swsec13_seed1491317288 | action_mask.swsec13 | detector_mitigated_only | 0.001381 | 0.000000 | 0.001381 |
| AM0015_T0018_action_mask_swtie6_seed630833044 | action_mask.swtie6 | detector_mitigated_only | 0.001145 | 0.000000 | 0.001145 |
| AM0015_T0012_action_mask_swsec13_seed630833044 | action_mask.swsec13 | detector_mitigated_only | 0.000993 | 0.000000 | 0.000993 |
| AM0015_T0021_action_mask_swtie9_seed630833044 | action_mask.swtie9 | detector_mitigated_only | 0.000993 | 0.000000 | 0.000993 |
| AM0023_T0037_action_mask_Load_s16c_seed894593567 | action_mask.Load_s16c | detector_mitigated_only | 0.000019 | 0.000000 | 0.000019 |
| AM0023_T0039_action_mask_Load_s30c_seed894593567 | action_mask.Load_s30c | detector_mitigated_only | 0.000016 | 0.000000 | 0.000016 |
| AM0012_T0020_action_mask_swtie8_seed1472279763 | action_mask.swtie8 | detector_mitigated_only | 0.000009 | 0.000000 | 0.000009 |
| AM0012_T0012_action_mask_swsec13_seed1472279763 | action_mask.swsec13 | detector_mitigated_only | 0.000009 | 0.000000 | 0.000009 |

