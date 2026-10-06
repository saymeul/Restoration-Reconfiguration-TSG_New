# Table 10. IEEE 123 Evidence Audit

| input_id | path | exists | row_count | paper_role | status_note |
| --- | --- | --- | --- | --- | --- |
| baseline_attack_ranking | paper_results\tsg_ieee123_bpso\baseline_attack_full_deterministic_p2_i2\tsg_ieee123_attack_ranking.csv | 1 | 5 | Which attack families are most damaging? | available |
| baseline_cases | paper_results\tsg_ieee123_bpso\baseline_attack_full_deterministic_p2_i2\tsg_ieee123_case_summary.csv | 1 | 150 | Worst individual attack cases and restored-energy loss. | available |
| baseline_manifest | paper_results\tsg_ieee123_bpso\baseline_attack_full_deterministic_p2_i2\tsg_ieee123_manifest.json | 1 | 1 | Manifest/provenance. | available |
| action_mask_ranking | paper_results\tsg_ieee123_bpso\full_criticality_merged\action_mask\tsg_ieee123_action_mask_criticality_ranking.csv | 1 | 41 | Critical switch/load status observations completed so far. | available |
| action_mask_manifest | paper_results\tsg_ieee123_bpso\full_criticality_merged\action_mask\tsg_ieee123_action_mask_criticality_manifest.json | 1 | 1 | Manifest/provenance. | available |
| voltage_single_ranking | paper_results\tsg_ieee123_bpso\full_criticality_merged\voltage\tsg_ieee123_measurement_criticality_ranking.csv | 0 | 0 | Critical bus-voltage observations completed so far. | missing |
| voltage_single_manifest | paper_results\tsg_ieee123_bpso\full_criticality_merged\voltage\tsg_ieee123_measurement_criticality_manifest.json | 0 | 0 | Manifest/provenance. | missing |
| branchflow_single_ranking | paper_results\tsg_ieee123_bpso\full_criticality_merged\branchflow\tsg_ieee123_measurement_criticality_ranking.csv | 0 | 0 | Critical single branchflow observations completed so far. | missing |
| branchflow_single_manifest | paper_results\tsg_ieee123_bpso\full_criticality_merged\branchflow\tsg_ieee123_measurement_criticality_manifest.json | 0 | 0 | Manifest/provenance. | missing |
| branchflow_subset_summary | paper_results\tsg_ieee123_bpso\branchflow_subset_ablation\tsg_ieee123_branchflow_subset_ablation_k_summary.csv | 0 | 0 | Coordinated branchflow sensitivity/ablation. | missing |
| branchflow_subset_manifest | paper_results\tsg_ieee123_bpso\branchflow_subset_ablation\tsg_ieee123_branchflow_subset_ablation_manifest.json | 0 | 0 | Manifest/provenance. | missing |
| defense_stress_group_summary | paper_results\tsg_ieee123_bpso\defense_stress_summary\tsg_ieee123_defense_stress_group_summary.csv | 1 | 46 | Detection, bypass, residual-risk summary. | available |
| defense_stress_low_recovery | paper_results\tsg_ieee123_bpso\defense_stress_summary\tsg_ieee123_defense_stress_low_recovery_cases.csv | 1 | 60 | Hard cases for advanced mitigation. | available |
| defense_stress_manifest | paper_results\tsg_ieee123_bpso\defense_stress_summary\tsg_ieee123_defense_stress_manifest.json | 1 | 1 | Manifest/provenance. | available |
| advanced_mitigation_summary | paper_results\tsg_ieee123_bpso\advanced_mitigation_ablation_exhaustive_criticality\tsg_ieee123_advanced_mitigation_variant_summary.csv | 1 | 6 | Advanced mitigation variant comparison. | available |
| advanced_mitigation_best_by_case | paper_results\tsg_ieee123_bpso\advanced_mitigation_ablation_exhaustive_criticality\tsg_ieee123_advanced_mitigation_best_by_case.csv | 1 | 60 | Best mitigation strategy per residual case. | available |
| advanced_mitigation_manifest | paper_results\tsg_ieee123_bpso\advanced_mitigation_ablation_exhaustive_criticality\tsg_ieee123_advanced_mitigation_manifest.json | 1 | 1 | Manifest/provenance. | available |
