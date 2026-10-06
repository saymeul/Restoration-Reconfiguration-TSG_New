# Observation-Level False-Data Attacks on Graph Reinforcement Learning Distribution Restoration

Working draft for IEEE Transactions on Smart Grid submission.

Draft date: 2026-06-25

Evidence scope: frozen IEEE 34-bus and IEEE 123-bus case-study artifacts. IEEE 8500-bus results are not claimed in this version and should be added only after the HPC-scale study is approved, executed, audited, and frozen as a separate evidence package.

## Candidate Titles

1. Observation-Level False-Data Injection Attacks on Graph Reinforcement Learning for Distribution System Restoration
2. Vulnerability and Mitigation of Graph Reinforcement Learning Restoration Under Cyber-Physical Observation Attacks
3. Auditable False-Data Attack Assessment for Learning-Based Distribution Network Restoration

Preferred working title: Observation-Level False-Data Injection Attacks on Graph Reinforcement Learning for Distribution System Restoration

## Abstract

Learning-based distribution system restoration controllers are increasingly attractive for fast post-outage decision making, but their cyber-physical security properties remain insufficiently characterized. This paper presents an auditable false-data injection attack assessment for graph reinforcement learning (GRL)-based active distribution network restoration. We study direct controller-observation attacks on action/status masks, topology/status inputs, voltage measurements, branch-flow measurements, and global restoration scalars. Attacks corrupt only the cyber observation provided to the restoration policy, while clean, attacked, and mitigated actions are evaluated on the same physical OpenDSS outage scenarios. The framework is evaluated on frozen IEEE 34-bus and IEEE 123-bus evidence packages using deterministic outage-edge replay and restored-energy degradation as the primary impact metric. On IEEE 34, action/status observation attacks dominate: false-unavailable dispatch-load attacks centered on `Load_s890` create multi-MWh restored-energy degradation, and coordinated attacks reach mean physical degradation above 3 MWh. On IEEE 123, the vulnerability structure changes: baseline branch-flow hiding is the strongest family, but exhaustive action-mask criticality identifies individual load-control observations that are much more damaging than the baseline aggregate attack. We further evaluate residual/status-integrity detection, learning-detector augmentation, and candidate-screening mitigation. Results show that strict status-integrity checks and trusted-reference or horizon-screened mitigation substantially reduce residual degradation, while relaxed detection assumptions can leave high-impact attacks unresolved. The study provides a reproducible evidence structure for scaling the assessment to larger feeders such as IEEE 8500.

## Keywords

Distribution system restoration; false-data injection attack; graph reinforcement learning; cyber-physical security; active distribution networks; OpenDSS; detection and mitigation.

## Manuscript Thesis

The paper should argue that learning-based restoration vulnerability is not captured by a generic "FDIA hurts RL" statement. The attack surface depends strongly on which controller observation family is corrupted, which feeder is studied, and whether the defense uses strict status-integrity checks plus robust candidate screening. IEEE 34 and IEEE 123 show different dominant vulnerabilities, so the journal contribution is the audited assessment workflow and the cross-feeder comparison, not a single feeder-specific anecdote.

## Main Contributions

1. An auditable observation-level FDIA workflow for learning-based distribution restoration, where attacks modify only controller observations and all restoration outcomes are evaluated on the true OpenDSS feeder.

2. A direct-observation attack taxonomy covering action/status masks, topology/status inputs, voltage measurements, branch-flow measurements, and global restoration scalars, with explicit claim boundaries for observations not available to the current controller.

3. Frozen IEEE 34-bus and IEEE 123-bus case studies using deterministic outage-edge replay, restored-energy degradation, damaging-case counts, detection rates, bypass rates, and mitigation residuals.

4. Evidence that IEEE 34 and IEEE 123 have different dominant vulnerability modes: IEEE 34 is driven by dispatch-load action/status observations, while IEEE 123 exposes stronger branch-flow family effects and high-impact action-mask criticality at individual load-control observations.

5. A defense evaluation showing that residual/status-integrity detection and trusted-reference or horizon-screened candidate mitigation can recover most or all detected degradation, while relaxed status assumptions and weak screening can leave large residual losses.

6. Companion controller evidence for MLP and scoped BPSO studies, used as secondary support rather than the main GRL claim.

## Claim Boundary

Use this boundary consistently:

- The main paper claims direct attacks on observations available to the current restoration controller: action/status masks, topology/status inputs, voltage measurements, branch-flow measurements, and global scalar observations.
- Do not claim direct load-demand FDIA, DER-availability FDIA, or explicit fault-status FDIA unless the controller observation model is extended.
- IEEE 34 and IEEE 123 are completed and frozen.
- IEEE 8500 is future work until HPC approval and a separately audited run are complete.
- MLP and BPSO results are companion/controller-comparison evidence. The main frozen GRL results should remain the core journal story unless the manuscript is later expanded into a full controller-comparison paper.

## Paper Structure

### I. Introduction

Distribution automation increasingly relies on fast restoration controllers that can choose switching and load-pickup actions after faults or outages. Graph reinforcement learning is appealing because feeder topology, switch status, and load connectivity are naturally graph structured. However, this same observation-rich structure exposes the controller to cyber-physical false-data injection attacks. A small perturbation in the controller observation can alter the selected restoration action even though the physical feeder state has not changed.

Most existing restoration studies emphasize performance under nominal or uncertain physical conditions. For learning-based controllers, an equally important question is whether the policy remains trustworthy when its cyber observation is manipulated. This paper studies that question under a strict cyber-physical evaluation rule: the attacker may corrupt only the observation received by the controller, and every clean, attacked, and mitigated action is evaluated on the same true OpenDSS feeder state.

The results show that vulnerability is highly observation dependent. In the IEEE 34-bus case, dispatch-load action/status observations dominate physical degradation. In the IEEE 123-bus case, baseline branch-flow hiding is the strongest aggregate attack family, but exhaustive action-mask criticality reveals that individual dispatch-load observations can be far more damaging than the baseline family average. These differences motivate an auditable, feeder-aware vulnerability assessment instead of one-off attack demonstrations.

### II. Related Work

This section needs citations and should be filled after reference collection.

Suggested subsections:

- Distribution system service restoration and active distribution networks.
- Reinforcement learning and graph neural network policies for restoration.
- False-data injection attacks and bad-data detection in power systems.
- Cyber-physical attacks against learning-enabled control.
- Mitigation through residual detection, trusted-reference screening, robust action selection, and moving-target or secure measurement strategies.

Citation placeholders:

- [R1] Distribution restoration survey.
- [R2] RL for distribution restoration.
- [R3] GNN/GRL restoration controller paper or baseline method.
- [R4] FDIA in power system state estimation.
- [R5] Cybersecurity of distribution automation.
- [R6] Robust or secure RL in power systems.

### III. System and Threat Model

#### A. Restoration Environment

The restoration controller observes a graph-structured distribution feeder state and selects a MultiBinary action vector representing restoration decisions such as switch operations and controllable load actions. The physical evaluation is performed in OpenDSS. For each deterministic outage-edge scenario, the clean controller action, attacked controller action, and mitigated action are all evaluated against the same true feeder state and loadshape horizon.

The primary performance metric is restored-energy degradation:

`physical_degradation_kwh = max(0, clean_restored_energy_kwh - attacked_restored_energy_kwh)`

This metric counts only positive physical loss relative to the clean baseline. Accidental improvements are tracked separately and should not be counted as attack damage.

#### B. Observation-Level FDIA

The attacker is modeled as corrupting the cyber observation received by the controller. The physical feeder model used for evaluation is not altered by the attacker. The studied direct observation families are:

- action/status mask attacks, including false-unavailable switch or load actions;
- topology/status attacks, including false-open or false-closed line-status adjacency observations;
- bus-voltage measurement attacks, including false-low voltage masking;
- branch-flow measurement attacks, including branchflow hiding;
- global scalar observation attacks, including energy-related scalar manipulation.

#### C. Defense Model

The defense has two layers:

1. Detection: residual and status-integrity checks identify suspicious observations. Detector profiles include `current_residual`, `strict_integrity`, and `relaxed_status_tolerance`. The relaxed profile is included to stress-test bypass and stealth behavior.

2. Mitigation: if the detector flags an attack, candidate restoration actions are screened before physical evaluation. Mitigation modes include `gated_candidate_screening` and `always_reference_screening`. IEEE 123 also includes advanced mitigation ablations such as `detector_mitigated_only`, `all_channel_reference_only`, `horizon_screen_raw_mitigated`, and `horizon_screen_raw_mitigated_reference`.

### IV. Experimental Workflow

#### A. Deterministic Case Generation

Both IEEE 34 and IEEE 123 studies use deterministic outage-edge replay with a fixed seed schedule. Each attack family is evaluated over the same clean outage cases, allowing clean, attacked, and mitigated results to be compared without scenario drift.

#### B. Evidence Packages

IEEE 34 frozen package:

- location: `paper_results/tsg_ieee34`
- freeze date: 2026-06-16
- completed studies: 11
- master evidence rows: 299
- missing inputs: 0
- paper tables: 9
- paper figures: 6
- learning-detector ablation rows: 48

IEEE 123 frozen package:

- location: `paper_results/tsg_ieee123`
- freeze date: 2026-06-17
- baseline attack-family rows: 5
- baseline case rows: 150
- action-mask criticality rows: 41 of 41
- branchflow single-target rows: 138 of 138 target registry, with ranking rows for applicable targets
- branchflow subset ablation rows: 6
- defense-stress groups: 190
- advanced mitigation variants: 6
- missing inputs: 0

#### C. Paper-Facing Metrics

Report the following metrics consistently:

- mean physical degradation in kWh;
- maximum physical degradation in kWh;
- total physical degradation in kWh where applicable;
- damaging-case count and rate;
- detection rate and detection rate on damaging cases;
- high-impact bypass count or rate;
- residual degradation after mitigation;
- mitigation recovery ratio.

### V. IEEE 34-Bus Results

#### A. Baseline Attack-Family Ranking

The IEEE 34 baseline results identify action/status observation attacks as the strongest direct attack family. The baseline `action_mask_false_unavailable` attack produces mean physical degradation of 46.603 kWh, maximum degradation of 289.271 kWh, and 8 damaging cases out of 30. Voltage masking has near-zero mean degradation but includes one damaging case. Branchflow hiding, energy inflation, and topology drop do not create positive physical degradation in the baseline family study.

#### B. Exhaustive Observation Criticality

The strongest IEEE 34 individual vulnerability is the dispatch-load action/status observation for `Load_s890`. The false-unavailable attack on `action_mask.Load_s890` produces mean physical degradation of 3038.190 kWh, maximum degradation of 8832.380 kWh, and 16 damaging cases out of 30. The attack is detected in all cases, changes the selected action in all cases, and mitigation recovers 93.75% of degradation.

The second most important dispatch-load observation is `Load_s844`, with mean degradation of 1627.701 kWh, maximum degradation of 8663.260 kWh, and 16 damaging cases. These results show that the largest IEEE 34 vulnerability is not generic measurement noise; it is targeted corruption of action/status observations that constrain controllable load restoration decisions.

#### C. Coordinated Attack Results

The strongest coordinated IEEE 34 attack is `dispatch_s890_branchflow_l8_voltage_816`, with mean physical degradation of 3080.849 kWh, maximum degradation of 9115.475 kWh, and 17 damaging cases out of 30. This coordinated attack is dominated by the `Load_s890` action/status component. Branchflow and voltage components should be described as coordinated context unless a standalone damage result is shown.

#### D. Detection and Mitigation

IEEE 34 demonstrates that detector and mitigation assumptions matter. Under relaxed status tolerance with gated candidate screening, `highimpact_dispatch_s890_voltage_816` leaves mean residual degradation of 3050.395 kWh and recovers only 7.771% of degradation, despite a detection rate of 66.667%. By contrast, current residual or strict status-integrity detection with reference-aware screening reduces residual degradation to approximately 44.770 kWh and recovers about 94.118% of degradation.

The learning-detector ablation improves detection for one relaxed-tolerance high-impact case by 30 percentage points, but the downstream recovery does not improve when the mitigation mode remains limiting. This distinction is important: higher detection accuracy does not automatically imply better restoration unless the mitigation action is also robust.

### VI. IEEE 123-Bus Results

#### A. Baseline Attack-Family Ranking

The IEEE 123 baseline results differ substantially from IEEE 34. The strongest baseline family is `branchflow_hiding`, with mean degradation of 104.039 kWh, total degradation of 3121.162 kWh, maximum degradation of 1559.847 kWh, and 6 damaging cases out of 30. `topology_drop` ranks second, with mean degradation of 56.222 kWh and total degradation of 1686.653 kWh. `action_mask_false_unavailable` has smaller baseline mean degradation, 7.586 kWh, but affects 9 damaging cases.

This difference is one of the central cross-feeder findings: the dominant vulnerability family is feeder and controller-context dependent.

#### B. Exhaustive Action-Mask Criticality

Although the baseline IEEE 123 action-mask family has modest mean impact, exhaustive single-target action-mask criticality reveals much larger individual vulnerabilities. The strongest target is `action_mask.Load_s48`, with mean degradation of 2317.398 kWh, maximum degradation of 4178.924 kWh, and 17 damaging cases. Other high-impact targets include `Load_s64b`, `Load_s16c`, `Load_s82a`, and `Load_s107b`.

This result supports a key journal claim: baseline family averages can understate the risk of individual controller-observation targets. Exhaustive or registry-driven criticality analysis is needed to identify the actual high-impact cyber observations.

#### C. Branchflow Criticality and Coordination

IEEE 123 branchflow vulnerability is primarily coordinated rather than single-sensor. The strongest single branchflow target, `branchflow.Line.l115`, has mean degradation near zero and maximum degradation of only 0.022 kWh in the single-target study. However, coordinated branchflow hiding recovers the baseline damage as more selected branchflow observations are included.

The branchflow subset ablation shows:

- k = 1 and k = 2 reproduce essentially none of the baseline branchflow damage;
- k = 3 reproduces 74.727% of baseline branchflow degradation;
- k = 5 remains near 74.727%;
- k = 10 reproduces approximately 100.299%;
- the full selected subset reproduces the baseline branchflow degradation.

This supports the interpretation that IEEE 123 branchflow vulnerability emerges from coordinated observation manipulation, not from one isolated branchflow sensor.

#### D. Defense Stress and Advanced Mitigation

The IEEE 123 defense-stress study finds zero high-impact detection bypass cases in the completed evidence. The main remaining weakness is mitigation selection after detection. In the hardest 58 detected low-recovery cases, the current one-step FDIA-aware mitigation leaves total residual degradation of 2617.432 kWh and recovers 0% in that subset.

Advanced mitigation variants remove this residual:

- `detector_mitigated_only`: total residual 0 kWh, recovery 100%, improved 58 of 58 cases;
- `all_channel_reference_only`: total residual 0 kWh, recovery 100%, improved 58 of 58 cases;
- `horizon_screen_raw_mitigated`: total residual 0 kWh, recovery 100%, improved 58 of 58 cases;
- `horizon_screen_raw_mitigated_reference`: total residual 0 kWh, recovery 100%, improved 58 of 58 cases.

These variants are defense ablations, not retrained GRL policies. The paper should present them as evidence that robust candidate selection after detection can remove residual restoration loss in hard cases.

### VII. Companion Controller Evidence

The main manuscript should remain centered on frozen GRL evidence, but companion evidence can support generality.

#### A. MLP Companion Evidence

IEEE 34 MLP evidence exists under `paper_results/tsg_ieee34_mlp`. It uses `MLP_34.zip` and the same OpenDSS observation and MultiBinary action contract. The result is a null-damage robustness finding: all paper-facing physical degradation rows are 0 kWh.

IEEE 123 MLP evidence exists under `paper_results/tsg_ieee123_mlp`. It uses `MLP_123.zip`. The MLP IEEE 123 case shows limited damage: `branchflow_hiding` has mean degradation of 54.449 kWh, total degradation of 1633.483 kWh, and 2 damaging cases; `action_mask_false_unavailable` has mean degradation of 26.801 kWh and 1 damaging case. Mitigation recovers the damaging cases, and the advanced mitigation table has zero hard cases.

#### B. BPSO Companion Evidence

IEEE 123 BPSO evidence exists as a scoped p2/i2 controller-comparison package under `paper_results/tsg_ieee123_bpso`. It is complete for its scoped action-mask-focused evidence package, but voltage, branchflow, topology, and energy channels should not be claimed as direct BPSO decision vulnerabilities in the same way unless the BPSO perceived-objective model is extended.

IEEE 34 BPSO evidence exists as older method-comparison artifacts under `paper_results/naps_34bus`, not as a full frozen `tsg_ieee34_bpso` package. Treat it as method-comparison/addendum evidence rather than equal-status main TSG evidence.

### VIII. Discussion

The two completed feeders give a strong journal story even before IEEE 8500. IEEE 34 shows that targeted action/status attacks can dominate restoration loss. IEEE 123 shows that the dominant baseline attack family can shift to branchflow hiding, while individual action-mask targets remain highly damaging under exhaustive criticality. Together, the results argue for observation-registry-based vulnerability assessment instead of generic attack families alone.

The defense results also show a practical lesson. Detection alone is insufficient if the mitigated candidate action is still selected through a weak or attacked action set. Robust candidate screening, trusted-reference candidates, and horizon-aware screening can substantially reduce or eliminate residual loss after detection.

### IX. Limitations and Future Work

This version does not claim IEEE 8500 behavior. The IEEE 8500 feeder should be treated as a future HPC-scale validation study. Once HPC access is approved, the same workflow should be repeated with a separately frozen evidence package, including baseline attack-family results, exhaustive or chunked observation criticality, coordinated attack ablation, defense stress, advanced mitigation, and controller-comparison addenda if feasible.

Other limitations:

- The direct attack claims are limited to observations available to the current controller.
- Load-demand, DER-availability, and explicit fault-status attacks require controller-observation extensions.
- The current learning-detector evidence should be separated from restoration-policy evidence.
- Some companion controller evidence is scoped and should not be overstated as full cross-controller equivalence.

### X. Conclusion

This paper presents an auditable observation-level FDIA assessment for GRL-based distribution restoration. Across frozen IEEE 34-bus and IEEE 123-bus evidence packages, the study shows that high-impact vulnerabilities are strongly observation- and feeder-dependent. IEEE 34 is dominated by dispatch-load action/status attacks, while IEEE 123 combines branchflow-family vulnerability with high-impact individual action-mask targets. Residual/status-integrity detection and robust candidate screening substantially reduce attack impact, and advanced mitigation ablations remove residual degradation in hard IEEE 123 cases. The resulting workflow provides a reproducible foundation for future HPC-scale validation on IEEE 8500.

## Initial Table Plan

| Manuscript table | Source artifact | Purpose |
| --- | --- | --- |
| Table I | IEEE34 and IEEE123 freeze markers/manifests | Evidence package summary and claim boundary |
| Table II | IEEE34 table 02, IEEE123 table 01 | Baseline attack-family comparison |
| Table III | IEEE34 table 03, IEEE123 table 03 | Most critical action/status observations |
| Table IV | IEEE34 table 04, IEEE123 table 05 | Coordinated attack and branchflow subset results |
| Table V | IEEE34 table 05, IEEE123 table 06-07 | Detection and mitigation comparison |
| Table VI | MLP/BPSO companion artifacts | Controller-comparison addendum, if included |

## Initial Figure Plan

| Manuscript figure | Source artifact | Message |
| --- | --- | --- |
| Fig. 1 | Conceptual diagram to create | Observation-only FDIA and true-physics evaluation loop |
| Fig. 2 | IEEE34 top degradation / observation criticality figures | IEEE34 action/status vulnerability |
| Fig. 3 | IEEE123 attack-family and action-mask criticality figures | IEEE123 cross-family vulnerability |
| Fig. 4 | IEEE123 branchflow subset ablation | Coordinated branchflow vulnerability |
| Fig. 5 | IEEE34 and IEEE123 defense residual plots | Detection and mitigation effectiveness |

## Action Items Before LaTeX Conversion

1. Finalize whether the first submission includes companion MLP/BPSO evidence in the main paper, appendix, or future controller-comparison paper.
2. Collect and format related-work citations.
3. Convert the evidence tables into publication-sized IEEE tables.
4. Create one clean conceptual system/threat-model figure.
5. Decide whether to keep IEEE 8500 as future work or wait for HPC results before submission.
6. Verify all numerical claims against frozen CSV/manifest sources before LaTeX submission.
