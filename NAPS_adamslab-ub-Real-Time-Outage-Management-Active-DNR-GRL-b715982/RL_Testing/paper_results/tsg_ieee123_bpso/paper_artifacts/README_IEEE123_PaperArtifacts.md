# IEEE 123 Paper Artifacts

This folder contains paper-facing outputs generated from completed IEEE 123 vulnerability simulations. The source simulations are not rerun by this artifact builder.

## Key Files

- Narrative: `paper_results\tsg_ieee123_bpso\paper_artifacts\IEEE123_TSG_Paper_Results_Narrative.md`
- Manifest: `paper_results\tsg_ieee123_bpso\paper_artifacts\ieee123_paper_artifacts_manifest.json`
- Freeze marker: `paper_results\tsg_ieee123_bpso\IEEE123_CASE_STUDY_FREEZE.md`

## Tables

- `paper_results\tsg_ieee123_bpso\paper_artifacts\tables\table_01_attack_family_ranking.csv`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\tables\table_01_attack_family_ranking.md`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\tables\table_02_worst_baseline_cases.csv`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\tables\table_02_worst_baseline_cases.md`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\tables\table_03_action_mask_criticality_exhaustive.csv`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\tables\table_03_action_mask_criticality_exhaustive.md`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\tables\table_04_voltage_single_criticality_exhaustive.csv`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\tables\table_04_voltage_single_criticality_exhaustive.md`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\tables\table_05_branchflow_single_criticality_exhaustive.csv`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\tables\table_05_branchflow_single_criticality_exhaustive.md`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\tables\table_06_branchflow_subset_ablation.csv`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\tables\table_06_branchflow_subset_ablation.md`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\tables\table_07_defense_stress_summary.csv`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\tables\table_07_defense_stress_summary.md`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\tables\table_08_advanced_mitigation_ablation.csv`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\tables\table_08_advanced_mitigation_ablation.md`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\tables\table_09_best_mitigation_by_case.csv`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\tables\table_09_best_mitigation_by_case.md`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\tables\table_10_evidence_audit.csv`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\tables\table_10_evidence_audit.md`

## Figures

- `paper_results\tsg_ieee123_bpso\paper_artifacts\figures\fig_01_attack_family_degradation.png`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\figures\fig_02_action_mask_criticality.png`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\figures\fig_06_defense_residual_risk.png`
- `paper_results\tsg_ieee123_bpso\paper_artifacts\figures\fig_07_advanced_mitigation_ablation.png`

## Claim Boundary

Completed IEEE 123 BPSO p2/i2 evidence only: the 30-case baseline attack-family study, the 41-target action-mask/status criticality study, defense-stress summary, and advanced mitigation ablation are complete. Voltage, branchflow, topology, and energy false-data channels are not claimed as direct BPSO decision vulnerabilities because this BPSO objective uses ActionMasking as the decision-relevant observation constraint.
