"""
Shared cyber-physical FDIA experiment utilities.

This module keeps the new FDIA impact/dynamics workflow outside the original
GCAPS restoration code. OpenDSS remains the physical ground truth; attacks only
corrupt the cyber observation sent to a controller or detector.
"""

import csv
import importlib
import json
import sys
from pathlib import Path
from time import perf_counter

import numpy as np

from FDIA_Common import (
    ATTACK_NAMES,
    apply_attack,
    detect_fdia,
    mitigate_observation,
    select_fdia_aware_grl_action,
)
from FDIA_Features import BDD_RESIDUAL_FEATURE_KEYS, residuals_to_feature_vector


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent

SYSTEM_CONFIG = {
    "13bus": {
        "folder": BASE_DIR / "13bus",
        "model": BASE_DIR / "13bus" / "TrainedModels" / "GCAPS_13.zip",
        "fixed_scenarios": {"SC1": "test_func1", "SC2": "test_func2"},
    },
    "34bus": {
        "folder": BASE_DIR / "34bus",
        "model": BASE_DIR / "34bus" / "TrainedModels" / "GCAPS_34.zip",
        "fixed_scenarios": {"SC1": "test_func1", "SC2": "test_func2"},
    },
    "123bus": {
        "folder": BASE_DIR / "123bus",
        "model": BASE_DIR / "123bus" / "TrainedModels" / "GCAPS_123.zip",
        "fixed_scenarios": {"SC1": "test_func1", "SC2": "test_func2"},
    },

    "8500bus": {
        "folder": BASE_DIR / "8500bus",
        "model": BASE_DIR / "8500bus" / "TrainedModels" / "GCAPS_8500.zip",
        "fixed_scenarios": {"SC1": "test_func1", "SC2": "test_func2"},
    },
}

ATTACK_TO_RL_LABEL = {name: index for index, name in enumerate(ATTACK_NAMES)}
RL_LABEL_TO_ATTACK = {index: name for name, index in ATTACK_TO_RL_LABEL.items()}

ATTACK_TO_DETECTION_METRIC = {
    "voltage_masking": "voltage_rl_detector_vote",
    "branchflow_hiding": "branchflow_rl_detector_vote",
    "energy_inflation": "energy_rl_detector_vote",
    "topology_drop": "topology_rl_detector_vote",
}

BUS_LOCAL_MODULES = [
    "DSS_CircuitSetup",
    "DSS_Initialize",
    "DSS_OutCtrl_Env",
    "state_action_reward",
]


def resolve_system_config(system):
    if system not in SYSTEM_CONFIG:
        raise ValueError("Unknown system '{}'. Available: {}".format(system, sorted(SYSTEM_CONFIG)))
    return SYSTEM_CONFIG[system]


def resolve_path(path, base_dir=BASE_DIR):
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return base_dir / candidate


def _clear_bus_modules():
    for module_name in BUS_LOCAL_MODULES:
        sys.modules.pop(module_name, None)
    for module_name in list(sys.modules):
        if module_name == "Policies" or module_name.startswith("Policies."):
            sys.modules.pop(module_name, None)


def prepare_bus_imports(system):
    config = resolve_system_config(system)
    bus_dir = config["folder"]
    if not bus_dir.exists():
        raise FileNotFoundError("Missing bus testing folder: {}".format(bus_dir))
    _clear_bus_modules()
    bus_path = str(bus_dir)
    if bus_path in sys.path:
        sys.path.remove(bus_path)
    sys.path.insert(0, bus_path)
    return bus_dir


def scenario_method(system, scenario_name):
    config = resolve_system_config(system)
    if scenario_name == "random":
        return "reset"
    try:
        return config["fixed_scenarios"][scenario_name]
    except KeyError as exc:
        choices = sorted(list(config["fixed_scenarios"]) + ["random"])
        raise ValueError("Unknown scenario '{}'. Available: {}".format(scenario_name, choices)) from exc


def observation_to_tensor(obs, device):
    import torch

    return {
        key: torch.as_tensor(np.expand_dims(np.asarray(value), axis=0), dtype=torch.float32, device=device)
        for key, value in obs.items()
    }


def safe_json(value):
    def _convert(item):
        if isinstance(item, np.ndarray):
            return item.tolist()
        if isinstance(item, (np.integer, np.floating)):
            return item.item()
        if isinstance(item, dict):
            return {str(key): _convert(val) for key, val in item.items()}
        if isinstance(item, (list, tuple)):
            return [_convert(val) for val in item]
        return item

    return json.dumps(_convert(value), sort_keys=True)


def write_csv(rows, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return

    fieldnames = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: safe_json(value) if isinstance(value, (dict, list, tuple, np.ndarray)) else value
                    for key, value in row.items()
                }
            )


def physical_impact(clean_metrics, attacked_metrics):
    energy_delta = attacked_metrics["energy_ratio"] - clean_metrics["energy_ratio"]
    voltage_delta = attacked_metrics["voltage_violation"] - clean_metrics["voltage_violation"]
    reward_delta = attacked_metrics["reward"] - clean_metrics["reward"]
    convergence_delta = attacked_metrics["convergence_violation"] - clean_metrics["convergence_violation"]
    impact_score = (
        max(0.0, -energy_delta)
        + max(0.0, voltage_delta)
        + max(0.0, -reward_delta)
        + max(0.0, convergence_delta)
    )
    return {
        "energy_ratio_delta_vs_clean": energy_delta,
        "energy_kw_delta_vs_clean": attacked_metrics["energy_kw"] - clean_metrics["energy_kw"],
        "voltage_violation_delta_vs_clean": voltage_delta,
        "reward_delta_vs_clean": reward_delta,
        "convergence_delta_vs_clean": convergence_delta,
        "loads_served_delta_vs_clean": attacked_metrics["loads_served"] - clean_metrics["loads_served"],
        "physical_impact_score": impact_score,
    }


def action_delta(clean_action, other_action, num_switches):
    clean_action = np.asarray(clean_action, dtype=int)
    other_action = np.asarray(other_action, dtype=int)
    return {
        "action_changed": int(np.any(clean_action != other_action)),
        "switch_changes_vs_clean": int(np.sum(clean_action[:num_switches] != other_action[:num_switches])),
        "load_changes_vs_clean": int(np.sum(clean_action[num_switches:] != other_action[num_switches:])),
    }


def detector_observation_from_reports(true_obs, received_obs):
    report = detect_fdia(true_obs, received_obs)
    features = residuals_to_feature_vector(report["residuals"], BDD_RESIDUAL_FEATURE_KEYS)
    return features.astype(np.float32), report


def rl_detection_from_label(label, residual_report=None):
    attack_name = RL_LABEL_TO_ATTACK.get(int(label), "clean")
    detected = attack_name != "clean"
    detected_channels = []
    if detected:
        detected_channels.append(ATTACK_TO_DETECTION_METRIC.get(attack_name, "learning_attack_vote"))
    return {
        "detected": detected,
        "score": 1.0 if detected else 0.0,
        "detected_channels": detected_channels,
        "thresholds": {},
        "residuals": dict((residual_report or {}).get("residuals", {})),
        "rl_detector_label": int(label),
        "rl_detector_attack": attack_name,
        "bdd_report": residual_report or {},
        "learning_reports": [],
        "learning_detected": detected,
        "learning_vote_fraction": 1.0 if detected else 0.0,
        "learning_vote_threshold": 0.0,
        "learning_any_detected": detected,
        "learning_detected_count": 1 if detected else 0,
        "learning_detector_count": 1,
        "learning_predicted_attacks": [attack_name] if detected else [],
        "learning_detected_channels": detected_channels,
        "learning_raw_detected_channels": detected_channels,
    }


class RestorationExperiment:
    """Loads one feeder test environment and its trained GCAPS restoration model."""

    def __init__(self, system="13bus", model_path=None, load_model=True):
        self.system = system
        self.config = resolve_system_config(system)
        if model_path:
            candidate_model = Path(model_path)
            self.model_path = candidate_model if candidate_model.is_absolute() else REPO_ROOT / candidate_model
        else:
            self.model_path = self.config["model"]
        self.bus_dir = prepare_bus_imports(system)
        self.env_module = importlib.import_module("DSS_OutCtrl_Env")
        self.init_module = importlib.import_module("DSS_Initialize")
        self.state_module = importlib.import_module("state_action_reward")
        self.env = self.env_module.DSS_OutCtrl_Env()
        self.dispatch_loads = list(self.init_module.dispatch_loads)
        self.n_actions = int(self.init_module.n_actions)
        self.num_switches = self.n_actions - len(self.dispatch_loads)
        self.model = None
        if load_model:
            self.load_restoration_model(self.model_path)

    def load_restoration_model(self, model_path):
        from stable_baselines3 import PPO

        self.model_path = Path(model_path)
        self.model = PPO.load(str(self.model_path), env=self.env)
        return self.model

    def get_observation(self, scenario_name):
        method_name = scenario_method(self.system, scenario_name)
        return getattr(self.env, method_name)()

    def predict_action(self, obs):
        if self.model is None:
            raise RuntimeError("No restoration model is loaded.")
        obs_tensor = observation_to_tensor(obs, self.model.device)
        start = perf_counter()
        import torch

        with torch.no_grad():
            action, _values, _log_probs = self.model.policy.forward(obs_tensor, deterministic=True)
        elapsed_ms = (perf_counter() - start) * 1000.0
        return action[0, :].detach().cpu().numpy().astype(int), elapsed_ms

    def split_action(self, action):
        action = np.asarray(action, dtype=int)
        switch_vector = [int(value) for value in action[: self.num_switches]]
        load_values = [int(value) for value in action[self.num_switches :]]
        load_status = {
            load: int(load_values[index])
            for index, load in enumerate(self.dispatch_loads)
            if index < len(load_values)
        }
        return switch_vector, load_status

    def calculate_energy_kw(self):
        energy_supplied = 0.0
        total_demand = 0.0
        for load_name in list(self.env.DSSCktObj.dss.Loads.AllNames()):
            self.env.DSSCktObj.dss.Circuit.SetActiveElement("Load.{}".format(load_name))
            powers = np.array(self.env.DSSCktObj.dss.CktElement.Powers())
            active_indices = 2 * np.array(range(0, min(int(powers.size / 2), 3)))
            active_power = np.nan_to_num(powers[active_indices], nan=0.0, posinf=0.0, neginf=0.0)
            energy_supplied += float(np.sum(active_power))
            total_demand += float(self.env.DSSCktObj.dss.Properties.Value("kW"))
        energy_ratio = energy_supplied / total_demand if total_demand else 0.0
        return energy_supplied, total_demand, energy_ratio

    def metrics_from_observation(self, obs, reward=None, action=None):
        energy_kw, total_demand_kw, measured_energy_ratio = self.calculate_energy_kw()
        energy_ratio = float(np.asarray(obs["EnergySupp"]).reshape(-1)[0])
        if not np.isfinite(energy_ratio):
            energy_ratio = measured_energy_ratio
        voltage_violation = float(np.asarray(obs["VoltageViolation"]).reshape(-1)[0])
        convergence_violation = float(np.asarray(obs["ConvergenceViolation"]).reshape(-1)[0])
        branchflows = np.nan_to_num(
            np.asarray(obs["EdgeFeat(Branchflow)"], dtype=float),
            nan=0.0,
            posinf=1.0e6,
            neginf=-1.0e6,
        )
        branchflows = np.clip(branchflows, -1.0e6, 1.0e6)
        voltages = np.nan_to_num(
            np.asarray(obs["NodeFeat(BusVoltage)"], dtype=float),
            nan=0.0,
            posinf=1.0e6,
            neginf=-1.0e6,
        )
        voltages = np.clip(voltages, -1.0e6, 1.0e6)
        active_voltages = voltages[np.isfinite(voltages) & (voltages > 0.01)]
        if reward is None:
            reward = 0.0 if convergence_violation > 0 else energy_ratio - voltage_violation
        loads_served = int(np.sum(np.asarray(action, dtype=int)[self.num_switches :])) if action is not None else 0
        return {
            "reward": float(reward),
            "energy_kw": float(energy_kw),
            "total_demand_kw": float(total_demand_kw),
            "energy_ratio": float(energy_ratio),
            "measured_energy_ratio": float(measured_energy_ratio),
            "voltage_violation": float(voltage_violation),
            "convergence_violation": float(convergence_violation),
            "branchflow_mean": float(np.mean(branchflows)) if branchflows.size else 0.0,
            "branchflow_max": float(np.max(branchflows)) if branchflows.size else 0.0,
            "voltage_min": float(np.min(active_voltages)) if active_voltages.size else 0.0,
            "voltage_max": float(np.max(active_voltages)) if active_voltages.size else 0.0,
            "loads_served": loads_served,
            "loads_shed": len(self.dispatch_loads) - loads_served if action is not None else 0,
        }

    def evaluate_action(self, scenario_name, action):
        self.get_observation(scenario_name)
        action = np.asarray(action, dtype=int)
        obs_post_action, reward, done, _info = self.env.step(action)
        metrics = self.metrics_from_observation(obs_post_action, reward=reward, action=action)
        metrics["done"] = bool(done)
        return metrics, obs_post_action

    def current_observation(self):
        return self.state_module.get_state(self.env.DSSCktObj, self.env.G, self.env.outedges)

    def _configure_daily_mode(self, step_hours):
        command = "Set mode=daily number=1 stepsize={}h".format(step_hours)
        self.env.DSSCktObj.dss.Text.Command(command)

    def _advance_time(self, hour):
        self.env.DSSCktObj.dss.Text.Command("Set hour={}".format(int(hour)))
        self.env.DSSCktObj.dss.Solution.Solve()

    def trajectory_after_action(self, scenario_name, action, horizon=24, step_hours=1, start_hour=0):
        action = np.asarray(action, dtype=int)
        first_metrics, first_obs = self.evaluate_action(scenario_name, action)
        trajectory = []
        try:
            self._configure_daily_mode(step_hours)
        except Exception as exc:
            first_metrics["time_command_warning"] = str(exc)

        for step in range(int(horizon)):
            hour = int(start_hour + step * step_hours)
            solve_warning = ""
            try:
                self._advance_time(hour)
            except Exception as exc:
                solve_warning = str(exc)
            obs = self.current_observation()
            metrics = self.metrics_from_observation(obs, action=action)
            if step == 0:
                metrics.update(
                    {
                        "initial_reward": first_metrics["reward"],
                        "initial_energy_ratio": first_metrics["energy_ratio"],
                        "initial_voltage_violation": first_metrics["voltage_violation"],
                    }
                )
            metrics.update({"time_step": step, "hour": hour, "solve_warning": solve_warning})
            trajectory.append(metrics)
        if not trajectory:
            first_metrics.update({"time_step": 0, "hour": start_hour, "solve_warning": ""})
            trajectory.append(first_metrics)
        return trajectory, first_obs


def run_one_step_physical_impact(experiment, scenario_name, attack_name):
    true_obs = experiment.get_observation(scenario_name)
    clean_action, clean_policy_ms = experiment.predict_action(true_obs)
    clean_metrics, _clean_post_obs = experiment.evaluate_action(scenario_name, clean_action)

    policy_obs, attack_metadata = apply_attack(true_obs, attack_name)
    attacked_action, attacked_policy_ms = experiment.predict_action(policy_obs)
    attacked_metrics, _attacked_post_obs = experiment.evaluate_action(scenario_name, attacked_action)
    detector_features, bdd_report = detector_observation_from_reports(true_obs, policy_obs)

    switches, load_status = experiment.split_action(attacked_action)
    row = {
        "system": experiment.system,
        "scenario": scenario_name,
        "attack": attack_name,
        "mode": "attacked_unmitigated",
        "clean_policy_time_ms": clean_policy_ms,
        "policy_time_ms": attacked_policy_ms,
        "clean_action": clean_action.tolist(),
        "action": attacked_action.tolist(),
        "switch_vector": switches,
        "load_status": load_status,
        "attack_metadata": attack_metadata,
        "bdd_detected": int(bdd_report["detected"]),
        "bdd_score": bdd_report["score"],
        "bdd_detected_channels": bdd_report["detected_channels"],
        "detector_feature_vector": detector_features.tolist(),
    }
    row.update(attacked_metrics)
    row.update(physical_impact(clean_metrics, attacked_metrics))
    row.update(action_delta(clean_action, attacked_action, experiment.num_switches))
    return row, {
        "true_obs": true_obs,
        "policy_obs": policy_obs,
        "clean_action": clean_action,
        "attacked_action": attacked_action,
        "clean_metrics": clean_metrics,
        "attacked_metrics": attacked_metrics,
        "bdd_report": bdd_report,
    }


def run_dynamic_physical_impact(experiment, scenario_name, attack_name, horizon=24, step_hours=1, start_hour=0):
    true_obs = experiment.get_observation(scenario_name)
    clean_action, clean_policy_ms = experiment.predict_action(true_obs)
    policy_obs, attack_metadata = apply_attack(true_obs, attack_name)
    attacked_action, attacked_policy_ms = experiment.predict_action(policy_obs)
    detector_features, bdd_report = detector_observation_from_reports(true_obs, policy_obs)

    clean_trajectory, _ = experiment.trajectory_after_action(
        scenario_name, clean_action, horizon=horizon, step_hours=step_hours, start_hour=start_hour
    )
    attacked_trajectory, _ = experiment.trajectory_after_action(
        scenario_name, attacked_action, horizon=horizon, step_hours=step_hours, start_hour=start_hour
    )

    rows = []
    for clean_metrics, attacked_metrics in zip(clean_trajectory, attacked_trajectory):
        switches, load_status = experiment.split_action(attacked_action)
        row = {
            "system": experiment.system,
            "scenario": scenario_name,
            "attack": attack_name,
            "mode": "attacked_unmitigated_dynamic",
            "time_step": attacked_metrics["time_step"],
            "hour": attacked_metrics["hour"],
            "clean_policy_time_ms": clean_policy_ms,
            "policy_time_ms": attacked_policy_ms,
            "clean_action": clean_action.tolist(),
            "action": attacked_action.tolist(),
            "switch_vector": switches,
            "load_status": load_status,
            "attack_metadata": attack_metadata,
            "bdd_detected": int(bdd_report["detected"]),
            "bdd_score": bdd_report["score"],
            "bdd_detected_channels": bdd_report["detected_channels"],
            "detector_feature_vector": detector_features.tolist(),
        }
        row.update(attacked_metrics)
        row.update(physical_impact(clean_metrics, attacked_metrics))
        row.update(action_delta(clean_action, attacked_action, experiment.num_switches))
        rows.append(row)
    return rows


def run_rl_mitigated_case(experiment, scenario_name, attack_name, rl_detector_model):
    true_obs = experiment.get_observation(scenario_name)
    clean_action, clean_policy_ms = experiment.predict_action(true_obs)
    clean_metrics, _ = experiment.evaluate_action(scenario_name, clean_action)

    policy_obs, attack_metadata = apply_attack(true_obs, attack_name)
    detector_features, bdd_report = detector_observation_from_reports(true_obs, policy_obs)
    detector_start = perf_counter()
    detector_action, _state = rl_detector_model.predict(detector_features, deterministic=True)
    detector_time_ms = (perf_counter() - detector_start) * 1000.0
    detection = rl_detection_from_label(int(np.asarray(detector_action).reshape(-1)[0]), bdd_report)
    mitigated_obs, mitigation_metadata = mitigate_observation(true_obs, policy_obs, detection)

    mitigated_action, policy_time_ms = experiment.predict_action(mitigated_obs)
    mitigated_metrics, _ = experiment.evaluate_action(scenario_name, mitigated_action)
    switches, load_status = experiment.split_action(mitigated_action)

    row = {
        "system": experiment.system,
        "scenario": scenario_name,
        "attack": attack_name,
        "mode": "rl_detector_mitigated",
        "clean_policy_time_ms": clean_policy_ms,
        "policy_time_ms": policy_time_ms,
        "detector_time_ms": detector_time_ms,
        "clean_action": clean_action.tolist(),
        "action": mitigated_action.tolist(),
        "switch_vector": switches,
        "load_status": load_status,
        "attack_metadata": attack_metadata,
        "rl_detector_label": detection["rl_detector_label"],
        "rl_detector_attack": detection["rl_detector_attack"],
        "rl_detector_detected": int(detection["detected"]),
        "rl_detected_channels": detection["detected_channels"],
        "mitigation_metadata": mitigation_metadata,
        "mitigation_applied": int(mitigation_metadata["mitigation_applied"]),
        "detector_feature_vector": detector_features.tolist(),
    }
    row.update(mitigated_metrics)
    row.update(physical_impact(clean_metrics, mitigated_metrics))
    row.update(action_delta(clean_action, mitigated_action, experiment.num_switches))
    return row


def run_dynamic_rl_mitigated_case(
    experiment,
    scenario_name,
    attack_name,
    rl_detector_model,
    horizon=24,
    step_hours=1,
    start_hour=0,
):
    true_obs = experiment.get_observation(scenario_name)
    clean_action, clean_policy_ms = experiment.predict_action(true_obs)
    policy_obs, attack_metadata = apply_attack(true_obs, attack_name)
    detector_features, bdd_report = detector_observation_from_reports(true_obs, policy_obs)

    detector_start = perf_counter()
    detector_action, _state = rl_detector_model.predict(detector_features, deterministic=True)
    detector_time_ms = (perf_counter() - detector_start) * 1000.0
    detection = rl_detection_from_label(int(np.asarray(detector_action).reshape(-1)[0]), bdd_report)
    mitigated_obs, mitigation_metadata = mitigate_observation(true_obs, policy_obs, detection)
    mitigated_action, policy_time_ms = experiment.predict_action(mitigated_obs)

    clean_trajectory, _ = experiment.trajectory_after_action(
        scenario_name, clean_action, horizon=horizon, step_hours=step_hours, start_hour=start_hour
    )
    mitigated_trajectory, _ = experiment.trajectory_after_action(
        scenario_name, mitigated_action, horizon=horizon, step_hours=step_hours, start_hour=start_hour
    )

    rows = []
    for clean_metrics, mitigated_metrics in zip(clean_trajectory, mitigated_trajectory):
        switches, load_status = experiment.split_action(mitigated_action)
        row = {
            "system": experiment.system,
            "scenario": scenario_name,
            "attack": attack_name,
            "mode": "rl_detector_mitigated_dynamic",
            "time_step": mitigated_metrics["time_step"],
            "hour": mitigated_metrics["hour"],
            "clean_policy_time_ms": clean_policy_ms,
            "policy_time_ms": policy_time_ms,
            "detector_time_ms": detector_time_ms,
            "clean_action": clean_action.tolist(),
            "action": mitigated_action.tolist(),
            "switch_vector": switches,
            "load_status": load_status,
            "attack_metadata": attack_metadata,
            "rl_detector_label": detection["rl_detector_label"],
            "rl_detector_attack": detection["rl_detector_attack"],
            "rl_detector_detected": int(detection["detected"]),
            "rl_detected_channels": detection["detected_channels"],
            "mitigation_metadata": mitigation_metadata,
            "mitigation_applied": int(mitigation_metadata["mitigation_applied"]),
            "detector_feature_vector": detector_features.tolist(),
        }
        row.update(mitigated_metrics)
        row.update(physical_impact(clean_metrics, mitigated_metrics))
        row.update(action_delta(clean_action, mitigated_action, experiment.num_switches))
        rows.append(row)
    return rows


def run_fdia_aware_screened_case(experiment, scenario_name, attack_name, detection):
    true_obs = experiment.get_observation(scenario_name)
    clean_action, clean_policy_ms = experiment.predict_action(true_obs)
    clean_metrics, _ = experiment.evaluate_action(scenario_name, clean_action)
    policy_obs, attack_metadata = apply_attack(true_obs, attack_name)
    mitigated_obs, mitigation_metadata = mitigate_observation(true_obs, policy_obs, detection)

    decision = select_fdia_aware_grl_action(
        lambda obs: experiment.predict_action(obs),
        lambda action: experiment.evaluate_action(scenario_name, action)[0],
        policy_obs,
        mitigated_obs,
        detection,
        experiment.num_switches,
    )
    action = np.asarray(decision["action"], dtype=int)
    switches, load_status = experiment.split_action(action)
    row = {
        "system": experiment.system,
        "scenario": scenario_name,
        "attack": attack_name,
        "mode": "rl_detector_fdia_aware_screened",
        "clean_policy_time_ms": clean_policy_ms,
        "policy_time_ms": decision["policy_time_ms"],
        "decision_time_ms": decision["decision_time_ms"],
        "screening_time_ms": decision["screening_time_ms"],
        "clean_action": clean_action.tolist(),
        "action": action.tolist(),
        "switch_vector": switches,
        "load_status": load_status,
        "attack_metadata": attack_metadata,
        "mitigation_metadata": mitigation_metadata,
        "selected_candidate": decision["selected_candidate"],
        "candidate_actions": decision["candidate_actions"],
        "fdia_aware_metadata": decision["fdia_aware_metadata"],
    }
    row.update(decision["metrics"])
    row.update(physical_impact(clean_metrics, decision["metrics"]))
    row.update(action_delta(clean_action, action, experiment.num_switches))
    return row
