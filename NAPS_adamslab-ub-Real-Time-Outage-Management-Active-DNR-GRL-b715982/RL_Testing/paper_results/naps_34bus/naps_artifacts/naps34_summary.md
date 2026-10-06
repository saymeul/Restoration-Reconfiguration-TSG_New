# NAPS 2026 IEEE 34-Bus FDIA Artifact Summary

## Experiment Focus

This artifact set focuses only on the IEEE 34-bus feeder. FDIA is applied to the cyber observation received by the graph RL restoration controller; the selected action is then evaluated on the true OpenDSS feeder. The main attacks emphasized for the NAPS paper are voltage masking and topology drop because they produced the strongest 34-bus degradation.

## Strongest One-Step Physical Degradation

| Scenario | Attack | Clean Energy | Attacked Energy | Energy Loss | Impact |
|---|---|---|---|---|---|
| R0342_seed1422974726 | voltage_masking | 0.925506 | 0.639668 | 0.285838 | 0.723845 |
| R0589_seed1723426319 | topology_drop | 0.911079 | 0.648903 | 0.262176 | 0.635494 |
| R0554_seed935905211 | voltage_masking | 0.917992 | 0.834763 | 0.083229 | 0.274566 |
| R0316_seed2000543456 | voltage_masking | 0.918065 | 0.853765 | 0.064300 | 0.182654 |
| R0232_seed1518043003 | voltage_masking | 0.916123 | 0.910341 | 0.005781 | 0.119671 |
| R0228_seed1438619800 | voltage_masking | 0.714810 | 0.709622 | 0.005189 | 0.118485 |
| R0021_seed3870524 | topology_drop | 0.934125 | 0.933492 | 0.000632 | 0.109373 |
| R0068_seed1480421712 | topology_drop | 0.933009 | 0.932510 | 0.000499 | 0.109105 |
| R0193_seed1568283881 | voltage_masking | 0.546536 | 0.521532 | 0.025003 | 0.104101 |
| R0439_seed2021310379 | voltage_masking | 0.735117 | 0.715177 | 0.019940 | 0.075033 |

## RL Detection and Mitigation Recovery

| Scenario | Attack | Attacked Energy | Mitigated Energy | Impact Reduction | Detector |
|---|---|---|---|---|---|
| R0342_seed1422974726 | voltage_masking | 0.639668 | 0.925506 | 1.000000 | voltage_masking |
| R0589_seed1723426319 | topology_drop | 0.648903 | 0.911079 | 1.000000 | topology_drop |
| R0554_seed935905211 | voltage_masking | 0.834763 | 0.917992 | 1.000000 | voltage_masking |
| R0316_seed2000543456 | voltage_masking | 0.853765 | 0.918065 | 1.000000 | voltage_masking |
| R0232_seed1518043003 | voltage_masking | 0.910341 | 0.916123 | 1.000000 | voltage_masking |
| R0228_seed1438619800 | voltage_masking | 0.709622 | 0.714810 | 1.000000 | voltage_masking |
| R0021_seed3870524 | topology_drop | 0.933492 | 0.934125 | 1.000000 | topology_drop |
| R0068_seed1480421712 | topology_drop | 0.932510 | 0.933009 | 1.000000 | topology_drop |
| R0193_seed1568283881 | voltage_masking | 0.521532 | 0.546536 | 1.000000 | voltage_masking |
| R0439_seed2021310379 | voltage_masking | 0.715177 | 0.735117 | 1.000000 | voltage_masking |

## Dynamic Loadshape Validation

| Scenario | Attack | Steps | Excluded | Max Attacked Impact | Max Mitigated Impact |
|---|---|---|---|---|---|
| R0503_seed1566321930 | topology_drop | 24 | 0 | 0.024056 | 0.000000 |
| R0104_seed1497792390 | topology_drop | 24 | 0 | 0.024035 | 0.000000 |
| R0228_seed1438619800 | voltage_masking | 24 | 0 | 0.009486 | 0.000000 |
| R0232_seed1518043003 | voltage_masking | 24 | 0 | 0.009085 | 0.000000 |
| R0193_seed1568283881 | voltage_masking | 24 | 0 | 0.000477 | 0.020620 |
| R0342_seed1422974726 | voltage_masking | 24 | 0 | 0.000001 | 0.000000 |
| R0021_seed3870524 | topology_drop | 24 | 0 | 0.000000 | 0.000000 |
| R0068_seed1480421712 | topology_drop | 24 | 0 | 0.000000 | 0.000000 |
| R0316_seed2000543456 | voltage_masking | 24 | 0 | 0.000000 | 0.000000 |
| R0439_seed2021310379 | voltage_masking | 24 | 0 | 0.000000 | 0.009382 |

## Filtered Robustness Statistics

| Attack | Trials | Harmful | Rate | CI Low | CI High | Max Impact |
|---|---|---|---|---|---|---|
| branchflow_hiding | 150 | 0 | 0.000000 | 0.000000 | 0.024971 | 0.000000 |
| energy_inflation | 163 | 1 | 0.006135 | 0.001084 | 0.033929 | 0.019230 |
| topology_drop | 137 | 12 | 0.087591 | 0.050815 | 0.146865 | 0.192946 |
| voltage_masking | 155 | 15 | 0.096774 | 0.059525 | 0.153527 | 0.703583 |

## RL Detector Summary

| Samples | Correct | Accuracy | CI Low | CI High | Harmful Recovery Samples | Mean Impact Reduction |
|---|---|---|---|---|---|---|
| 40 | 40 | 1.000000 | 0.912375 | 1.000000 | 28 | 1.000000 |

## Filter Accounting

| Item | Count | Details |
|---|---|---|
| raw_trials | 750 | All Monte Carlo trials before paper-ready filtering |
| filtered_trials | 605 | convergence_violation <= 0.0, physical_impact_score <= 5.0, abs(energy_ratio) <= 2.0 |
| excluded_clean_nonconverged | 1 | Excluded from filtered statistics; retained in raw CSV |
| excluded_energy_ratio_outlier | 4 | Excluded from filtered statistics; retained in raw CSV |
| excluded_nonconverged | 140 | Excluded from filtered statistics; retained in raw CSV |

## Paper-Safe Interpretation

The 34-bus feeder shows attack-dependent vulnerability. Voltage masking produced the strongest paper-valid one-step physical degradation in the focused search, and topology drop also produced harmful cases. The RL detector correctly classified the selected recovery cases, and reference-assisted channel mitigation restored the top one-step cases to the clean physical outcome. Dynamic loadshape replay shows that some high-impact one-step cases do not persist dynamically, while selected voltage-masking and topology-drop cases still show time-varying degradation that is reduced or removed by mitigation.

The mitigation remains reference/state-estimator-assisted, and the dynamic validation is quasi-static OpenDSS loadshape simulation rather than transient stability analysis.
