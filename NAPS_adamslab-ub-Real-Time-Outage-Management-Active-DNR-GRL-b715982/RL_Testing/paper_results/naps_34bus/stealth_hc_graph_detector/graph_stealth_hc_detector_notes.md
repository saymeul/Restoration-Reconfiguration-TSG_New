# IEEE 34-Bus Graph-Learning Stealth FDIA Detector Notes

This folder contains a separate graph-learning detector for the stealth
measurement FDIA experiment. It does not reuse the GCAPS/GRL restoration policy
as a detector.

## Detector Concept

The restoration model and detector are separated:

```text
GCAPS/GRL restoration policy: outage restoration decision maker
Graph FDIA detector: clean vs stealth-FDIA classifier
```

The detector is a compact two-layer graph convolutional classifier. It uses the
fixed IEEE 34-bus feeder graph and bus-level features built from:

- phase A/B/C bus voltages,
- incident branch-flow sum/mean/max,
- energy supplied repeated at each node,
- active phase fraction,
- normalized node degree.

## Attack Model

The attack is the stealth measurement attack:

```text
a = Hc
```

Here `H` is the same PCA measurement-subspace proxy used in
`stealth_hc_detection`. This is a detection-focused experiment and is separate
from the topology/status FDIA restoration-impact study.

## Final Validation

Read-only validation of final outputs:

```text
case rows: 720
summary rows: 5
training-history rows: 9
held-out stealth attacks: 120
max attack-induced projection-residual delta: 2.892408534904689e-12
projection-BDD attack-induced alarms: 0
```

## Main Results

Projection-residual BDD:

```text
attack-induced detection rate: 0.0%
```

Graph-learning detector:

```text
accuracy: 93.33%
precision: 94.83%
recall/detection rate: 91.67%
false-positive rate: 5.00%
F1-score: 93.22%
```

## Paper-Safe Interpretation

The stealth `a = Hc` attack bypasses the projection-residual BDD because the
attack is constructed inside the fitted measurement subspace. A separate
graph-learning detector, using bus-voltage and incident branch-flow patterns on
the IEEE 34-bus graph, detects most held-out stealth attacks while keeping a low
false-positive rate.

Use careful wording: this is a graph-learning detector trained for stealth FDIA
detection. It is not the same as the GCAPS/GRL restoration policy.

## Files

- `graph_stealth_hc_detection_cases_34bus.csv`: train/test clean and stealth
  cases with BDD and graph-detector predictions.
- `table_graph_stealth_hc_detection_summary_34bus.csv`: projection-BDD,
  direct residual, and graph-learning detector metrics.
- `graph_stealth_hc_training_history_34bus.csv`: training/test loss history.
- `graph_stealth_hc_detector_34bus.pt`: trained graph-detector checkpoint.
- `graph_stealth_hc_detection_manifest.json`: machine-readable manifest.
