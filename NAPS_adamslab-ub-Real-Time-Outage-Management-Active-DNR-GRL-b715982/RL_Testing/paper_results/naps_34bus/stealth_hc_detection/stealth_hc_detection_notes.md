# IEEE 34-Bus Stealth a=Hc FDIA Detection Notes

This folder is a detection-focused experiment and is separate from the
topology/status FDIA restoration-impact comparison.

## Threat Model

The attack is a measurement-space stealth FDIA:

```text
a = Hc
```

Because this repository does not include a full AC WLS state estimator for the
IEEE 34-bus feeder, `H` is implemented as a PCA measurement-subspace proxy
fitted from clean OpenDSS observations. The attack vector is injected in the
range of this fitted measurement subspace. Therefore, the projection-residual
BDD using the same `H` should not receive a new residual alarm from the attack.

This is not the same attack as the topology/status FDIA used for the main
restoration-impact comparison.

## Final Validation

Read-only validation of the final CSVs:

```text
case rows: 400
summary rows: 9
restoration probe rows: 15
held-out stealth attacks: 80
max attack-induced projection-residual delta: 4.728661906483467e-12
projection-BDD attack-induced alarms: 0
restoration probe action-changed rows: 1
max restoration probe physical impact: 0.0015526192016945412
```

## Main Detection Interpretation

The key result is:

```text
state_estimator_projection_bdd_attack_induced = 0.0
```

This means the stealth `a = Hc` attack did not create new alarms in the
projection-residual BDD. This is the intended classical stealth-FDIA behavior.

The legacy direct-channel residual check detects many of these attacks because
it compares the clean observation directly against the received attacked
observation. That is useful for project traceability, but it is not the
classical state-estimation BDD setting.

## Learning Detector Interpretation

The raw-measurement learning detectors are reported on a held-out test set.
Their performance is weak in this run, so the honest conclusion is not that
learning detection solved the stealth attack. The honest conclusion is:

```text
The implemented a=Hc measurement-subspace attack bypasses the projection BDD,
and the current static raw-measurement learning detectors do not reliably
detect it.
```

This supports a careful discussion: stronger learning detection would likely
need richer temporal, graph-structured, or physics-informed features.

## Files

- `stealth_hc_detection_cases_34bus.csv`: train/test clean and stealth samples,
  BDD residuals, direct residual checks, attack magnitudes, and learning
  predictions.
- `table_stealth_hc_detection_summary_34bus.csv`: detector metrics for
  projection BDD, direct residual check, and raw-measurement learning models.
- `stealth_hc_learning_model_summary_34bus.csv`: held-out performance of each
  raw-measurement learning model.
- `stealth_hc_restoration_probe_34bus.csv`: small single-step restoration probe
  showing whether the detection-focused stealth attack changed GRL/MLP/BPSO
  actions.
- `stealth_hc_measurement_subspace_34bus.npz`: fitted measurement-subspace
  parameters.
- `stealth_hc_detection_manifest.json`: machine-readable experiment manifest.
