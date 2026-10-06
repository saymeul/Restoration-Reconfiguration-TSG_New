"""
FDIA mitigation helpers for cyber-resilient GCAPS restoration tests.

The mitigation layer repairs only the observation channels that the residual
detector flags as suspicious. In these offline experiments the trusted
reference is the OpenDSS/state-estimator observation used by the detector.
"""

from FDIA_Attacks import clone_observation


CHANNEL_TO_OBSERVATION_KEYS = {
    "voltage": ("NodeFeat(BusVoltage)",),
    "branchflow": ("EdgeFeat(Branchflow)",),
    "energy": ("EnergySupp",),
    "topology": ("Adjacency",),
    "action_mask": ("ActionMasking",),
}


def _channel_from_metric(metric_name):
    if metric_name.startswith("voltage_"):
        return "voltage"
    if metric_name.startswith("branchflow_"):
        return "branchflow"
    if metric_name.startswith("energy_"):
        return "energy"
    if metric_name.startswith("topology_"):
        return "topology"
    if metric_name.startswith("action_mask_"):
        return "action_mask"
    return None


def mitigated_keys_from_detection(detection):
    """Map detector residual names to observation keys that should be repaired."""
    detected_channels = detection.get("detected_channels", [])
    channels = []
    keys = []
    for metric_name in detected_channels:
        channel = _channel_from_metric(metric_name)
        if channel is None or channel in channels:
            continue
        channels.append(channel)
        keys.extend(CHANNEL_TO_OBSERVATION_KEYS[channel])
    return channels, keys


def mitigate_observation(reference_obs, received_obs, detection):
    """
    Return a corrected observation and serializable mitigation metadata.

    Only detected channels are replaced. If no FDIA is detected, the received
    observation is passed through unchanged.
    """
    mitigated = clone_observation(received_obs)
    channels, keys = mitigated_keys_from_detection(detection)

    for key in keys:
        if key in reference_obs and key in mitigated:
            mitigated[key] = reference_obs[key].copy()

    metadata = {
        "strategy": "replace_detected_channels_with_reference",
        "mitigation_applied": bool(keys),
        "mitigated_channels": channels,
        "mitigated_keys": keys,
        "reference_source": "OpenDSS/state-estimator observation",
    }
    return mitigated, metadata
