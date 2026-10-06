# IEEE 34-Bus GAE Detection and Mitigation

This extension does not overwrite the existing topology/status FDIA impact results.

Detector: graph autoencoder trained only on clean outage observations.
Anomaly score combines node-feature, adjacency, and action-mask reconstruction error.

Mitigation: if the GAE detects an attack, switching/load actions are recomputed by
OpenDSS-validated candidate screening. The saved clean action is not directly copied;
a trusted-state controller recomputation and local/random candidates are physically
evaluated and ranked by energy ratio minus voltage and convergence penalties.

Important caveat: this is a detection-guided recovery study. It assumes a trusted
reference/state-estimator channel is available for screening after attack detection.
