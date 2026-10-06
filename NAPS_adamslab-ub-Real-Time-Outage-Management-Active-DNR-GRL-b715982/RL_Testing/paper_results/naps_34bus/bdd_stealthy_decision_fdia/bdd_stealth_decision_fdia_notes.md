# IEEE 34-Bus BDD-Stealthy Decision-Aware FDIA Notes

This folder contains the coordinated FDIA experiment that combines:

```text
a = Hc measurement-subspace FDIA
false status/action-availability corruption
```

The goal is to test attacks that bypass projection-residual BDD while still
impacting restoration decisions for GCAPS/GRL, MLP, and BPSO.

## Threat Model

This is **not** a pure measurement-only `a = Hc` attack.

The attack has two explicit parts:

1. `a = Hc` measurement corruption in the fitted measurement subspace. This is
   used to bypass the projection-residual BDD.
2. False status/action-availability corruption before the restoration decision.
   This is what makes the outage-management decisions change for GRL, MLP, and
   BPSO.

No final restoration action is modified after the method decides.

## Final Validation

Read-only validation:

```text
search rows: 60
selected rows: 15
comparison rows: 720
invalid attacked comparison rows: 0
selected projection-BDD attack-induced alarms: 0
selected graph-detector detections: 13 / 15
selected raw-learning majority detections: 15 / 15
selected action-changed cases: 15 / 15
```

## Selected-Case Restoration Impact

Mean physical impact over 24 dynamic time steps:

```text
GCAPS/GRL: 0.7489
MLP:       0.6222
BPSO:      0.7052
```

Maximum physical impact:

```text
GCAPS/GRL: 1.0035
MLP:       1.0838
BPSO:      1.0661
```

Action changed rate:

```text
GCAPS/GRL: 100%
MLP:       100%
BPSO:      100%
```

## Detection Interpretation

Projection-residual BDD:

```text
attack-induced detection rate: 0%
```

Graph-learning detector on selected cases:

```text
GCAPS/GRL targeted cases: 80%
MLP targeted cases:       80%
BPSO targeted cases:      100%
overall:                  13/15 = 86.67%
```

Ordinary raw-measurement learning baselines:

```text
held-out detector benchmark: weak to moderate
selected high-impact cases: 15/15 majority detections
```

This means the paper should not claim that only the graph detector can detect
the selected coordinated attacks. The safer claim is:

```text
Projection-residual BDD is bypassed. The graph-learning detector provides
strong held-out stealth-detection performance and detects most selected
coordinated harmful attacks. Ordinary static raw-measurement learners are weak
on the held-out benchmark, but their majority vote also detects the selected
high-impact coordinated cases.
```

## Files

- `bdd_stealth_attack_search_34bus.csv`: all search candidates.
- `bdd_stealth_selected_cases_34bus.csv`: selected valid harmful cases.
- `bdd_stealth_method_comparison_34bus.csv`: 24-step clean/attacked comparison
  rows for selected cases.
- `table_bdd_stealth_method_summary_34bus.csv`: restoration-impact summary.
- `table_bdd_stealth_detection_summary_34bus.csv`: selected-case detection
  summary.
- `table_bdd_stealth_detector_training_summary_34bus.csv`: held-out detector
  benchmark for raw learners and graph learner.
- `bdd_stealth_graph_detector_34bus.pt`: trained graph detector checkpoint.
- `bdd_stealth_manifest.json`: machine-readable experiment manifest.
