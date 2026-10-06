# IEEE 123 Advanced Mitigation Ablation

This ablation reruns the detected hard residual IEEE 123 FDIA cases and compares mitigation variants.

## Variant Summary

| Variant | Cases | Residual kWh | Recovered kWh | Recovery | Improved vs current | Worse vs current |
|---|---:|---:|---:|---:|---:|---:|
| all_channel_reference_only | 60 | 0.000000 | 58610.707867 | 1.000000 | 60 | 0 |
| detector_mitigated_only | 60 | 0.000000 | 58610.707867 | 1.000000 | 60 | 0 |
| horizon_screen_raw_mitigated | 60 | 0.000000 | 58610.707867 | 1.000000 | 60 | 0 |
| horizon_screen_raw_mitigated_reference | 60 | 0.000000 | 58610.707867 | 1.000000 | 60 | 0 |
| attacked_no_defense | 60 | 58610.707867 | 0.000000 | 0.000000 | 0 | 0 |
| current_one_step_fdia_aware | 60 | 58610.707867 | 0.000000 | 0.000000 | 0 | 0 |

## Best Variant By Case

| Source case | Group | Best variant | Current residual kWh | Best residual kWh | Reduction kWh |
|---|---|---|---:|---:|---:|
| AM0022_T0014_action_mask_swtie2_seed996050191 | action_mask.swtie2 | detector_mitigated_only | 5490.850684 | 0.000000 | 5490.850684 |
| AM0022_T0026_action_mask_Load_s69a_seed996050191 | action_mask.Load_s69a | detector_mitigated_only | 5490.431247 | 0.000000 | 5490.431247 |
| AM0005_T0007_action_mask_swsec8_seed623645698 | action_mask.swsec8 | detector_mitigated_only | 4497.154117 | 0.000000 | 4497.154117 |
| AM0025_T0031_action_mask_Load_s48_seed1869647486 | action_mask.Load_s48 | detector_mitigated_only | 4184.222371 | 0.000000 | 4184.222371 |
| AM0028_T0031_action_mask_Load_s48_seed1097882150 | action_mask.Load_s48 | detector_mitigated_only | 4074.509254 | 0.000000 | 4074.509254 |
| AM0025_T0006_action_mask_swsec7_seed1869647486 | action_mask.swsec7 | detector_mitigated_only | 3967.441880 | 0.000000 | 3967.441880 |
| AM0000_T0033_action_mask_Load_s64b_seed380655884 | action_mask.Load_s64b | detector_mitigated_only | 1493.325329 | 0.000000 | 1493.325329 |
| AM0011_T0033_action_mask_Load_s64b_seed830125963 | action_mask.Load_s64b | detector_mitigated_only | 1492.325014 | 0.000000 | 1492.325014 |
| AM0007_T0033_action_mask_Load_s64b_seed858031802 | action_mask.Load_s64b | detector_mitigated_only | 1487.047365 | 0.000000 | 1487.047365 |
| AM0020_T0033_action_mask_Load_s64b_seed1904300917 | action_mask.Load_s64b | detector_mitigated_only | 1481.536027 | 0.000000 | 1481.536027 |
| AM0000_T0034_action_mask_Load_s66c_seed380655884 | action_mask.Load_s66c | detector_mitigated_only | 1464.413858 | 0.000000 | 1464.413858 |
| AM0025_T0034_action_mask_Load_s66c_seed1869647486 | action_mask.Load_s66c | detector_mitigated_only | 1459.398557 | 0.000000 | 1459.398557 |
| AM0027_T0034_action_mask_Load_s66c_seed1868073150 | action_mask.Load_s66c | detector_mitigated_only | 1190.661691 | 0.000000 | 1190.661691 |
| AM0007_T0029_action_mask_Load_s109a_seed858031802 | action_mask.Load_s109a | detector_mitigated_only | 932.058875 | 0.000000 | 932.058875 |
| AM0025_T0027_action_mask_Load_s100c_seed1869647486 | action_mask.Load_s100c | detector_mitigated_only | 839.277975 | 0.000000 | 839.277975 |
| AM0007_T0032_action_mask_Load_s49a_seed858031802 | action_mask.Load_s49a | detector_mitigated_only | 832.581454 | 0.000000 | 832.581454 |
| AM0014_T0030_action_mask_Load_s113a_seed611696197 | action_mask.Load_s113a | detector_mitigated_only | 826.318632 | 0.000000 | 826.318632 |
| AM0007_T0040_action_mask_Load_s22b_seed858031802 | action_mask.Load_s22b | detector_mitigated_only | 796.364818 | 0.000000 | 796.364818 |
| AM0000_T0039_action_mask_Load_s30c_seed380655884 | action_mask.Load_s30c | detector_mitigated_only | 793.376382 | 0.000000 | 793.376382 |
| AM0011_T0029_action_mask_Load_s109a_seed830125963 | action_mask.Load_s109a | detector_mitigated_only | 790.867887 | 0.000000 | 790.867887 |
| AM0011_T0025_action_mask_Load_s88a_seed830125963 | action_mask.Load_s88a | detector_mitigated_only | 790.739004 | 0.000000 | 790.739004 |
| AM0011_T0022_action_mask_Load_s82a_seed830125963 | action_mask.Load_s82a | detector_mitigated_only | 789.469081 | 0.000000 | 789.469081 |
| AM0025_T0024_action_mask_Load_s92c_seed1869647486 | action_mask.Load_s92c | detector_mitigated_only | 788.857790 | 0.000000 | 788.857790 |
| AM0003_T0040_action_mask_Load_s22b_seed175394891 | action_mask.Load_s22b | detector_mitigated_only | 788.742704 | 0.000000 | 788.742704 |
| AM0024_T0040_action_mask_Load_s22b_seed1448425263 | action_mask.Load_s22b | detector_mitigated_only | 785.900183 | 0.000000 | 785.900183 |
| AM0024_T0039_action_mask_Load_s30c_seed1448425263 | action_mask.Load_s30c | detector_mitigated_only | 785.664844 | 0.000000 | 785.664844 |
| AM0014_T0026_action_mask_Load_s69a_seed611696197 | action_mask.Load_s69a | detector_mitigated_only | 785.010404 | 0.000000 | 785.010404 |
| AM0007_T0028_action_mask_Load_s107b_seed858031802 | action_mask.Load_s107b | detector_mitigated_only | 784.477619 | 0.000000 | 784.477619 |
| AM0010_T0029_action_mask_Load_s109a_seed1391317448 | action_mask.Load_s109a | detector_mitigated_only | 781.594301 | 0.000000 | 781.594301 |
| AM0000_T0035_action_mask_Load_s53a_seed380655884 | action_mask.Load_s53a | detector_mitigated_only | 780.801528 | 0.000000 | 780.801528 |
| AM0014_T0029_action_mask_Load_s109a_seed611696197 | action_mask.Load_s109a | detector_mitigated_only | 780.427576 | 0.000000 | 780.427576 |
| AM0003_T0022_action_mask_Load_s82a_seed175394891 | action_mask.Load_s82a | detector_mitigated_only | 776.619603 | 0.000000 | 776.619603 |
| AM0006_T0028_action_mask_Load_s107b_seed1262161534 | action_mask.Load_s107b | detector_mitigated_only | 774.142851 | 0.000000 | 774.142851 |
| AM0015_T0035_action_mask_Load_s53a_seed630833044 | action_mask.Load_s53a | detector_mitigated_only | 770.085060 | 0.000000 | 770.085060 |
| AM0015_T0040_action_mask_Load_s22b_seed630833044 | action_mask.Load_s22b | detector_mitigated_only | 761.847461 | 0.000000 | 761.847461 |
| AM0011_T0032_action_mask_Load_s49a_seed830125963 | action_mask.Load_s49a | detector_mitigated_only | 686.740685 | 0.000000 | 686.740685 |
| AM0025_T0023_action_mask_Load_s84c_seed1869647486 | action_mask.Load_s84c | detector_mitigated_only | 386.384915 | 0.000000 | 386.384915 |
| AM0010_T0023_action_mask_Load_s84c_seed1391317448 | action_mask.Load_s84c | detector_mitigated_only | 375.708106 | 0.000000 | 375.708106 |
| AM0026_T0002_action_mask_swsec3_seed1985582968 | action_mask.swsec3 | detector_mitigated_only | 209.383074 | 0.000000 | 209.383074 |
| AM0026_T0007_action_mask_swsec8_seed1985582968 | action_mask.swsec8 | detector_mitigated_only | 209.383074 | 0.000000 | 209.383074 |
| AM0026_T0014_action_mask_swtie2_seed1985582968 | action_mask.swtie2 | detector_mitigated_only | 209.383074 | 0.000000 | 209.383074 |
| AM0026_T0017_action_mask_swtie5_seed1985582968 | action_mask.swtie5 | detector_mitigated_only | 209.383074 | 0.000000 | 209.383074 |
| AM0004_T0016_action_mask_swtie4_seed891296660 | action_mask.swtie4 | detector_mitigated_only | 161.001652 | 0.000000 | 161.001652 |
| AM0018_T0009_action_mask_swsec10_seed1675750130 | action_mask.swsec10 | detector_mitigated_only | 112.142490 | 0.000000 | 112.142490 |
| AM0018_T0010_action_mask_swsec11_seed1675750130 | action_mask.swsec11 | detector_mitigated_only | 112.142490 | 0.000000 | 112.142490 |
| AM0005_T0005_action_mask_swsec6_seed623645698 | action_mask.swsec6 | detector_mitigated_only | 103.287122 | 0.000000 | 103.287122 |
| AM0005_T0009_action_mask_swsec10_seed623645698 | action_mask.swsec10 | detector_mitigated_only | 103.287122 | 0.000000 | 103.287122 |
| AM0005_T0010_action_mask_swsec11_seed623645698 | action_mask.swsec11 | detector_mitigated_only | 103.287122 | 0.000000 | 103.287122 |
| AM0007_T0014_action_mask_swtie2_seed858031802 | action_mask.swtie2 | detector_mitigated_only | 94.468706 | 0.000000 | 94.468706 |
| AM0022_T0027_action_mask_Load_s100c_seed996050191 | action_mask.Load_s100c | detector_mitigated_only | 72.118536 | 0.000000 | 72.118536 |
| AM0008_T0003_action_mask_swsec4_seed795118727 | action_mask.swsec4 | detector_mitigated_only | 33.730833 | 0.000000 | 33.730833 |
| B0026_action_mask_false_unavailable_seed1985582968 | action_mask_false_unavailable | detector_mitigated_only | 33.071162 | 0.000000 | 33.071162 |
| B0018_action_mask_false_unavailable_seed1675750130 | action_mask_false_unavailable | detector_mitigated_only | 23.461195 | 0.000000 | 23.461195 |
| AM0023_T0030_action_mask_Load_s113a_seed894593567 | action_mask.Load_s113a | detector_mitigated_only | 22.498039 | 0.000000 | 22.498039 |
| AM0017_T0016_action_mask_swtie4_seed1340119489 | action_mask.swtie4 | detector_mitigated_only | 20.104291 | 0.000000 | 20.104291 |
| AM0004_T0028_action_mask_Load_s107b_seed891296660 | action_mask.Load_s107b | detector_mitigated_only | 11.410109 | 0.000000 | 11.410109 |
| AM0004_T0012_action_mask_swsec13_seed891296660 | action_mask.swsec13 | detector_mitigated_only | 6.190458 | 0.000000 | 6.190458 |
| AM0028_T0025_action_mask_Load_s88a_seed1097882150 | action_mask.Load_s88a | detector_mitigated_only | 1.898426 | 0.000000 | 1.898426 |
| AM0028_T0026_action_mask_Load_s69a_seed1097882150 | action_mask.Load_s69a | detector_mitigated_only | 1.242348 | 0.000000 | 1.242348 |
| AM0029_T0006_action_mask_swsec7_seed1710510346 | action_mask.swsec7 | detector_mitigated_only | 0.456338 | 0.000000 | 0.456338 |

