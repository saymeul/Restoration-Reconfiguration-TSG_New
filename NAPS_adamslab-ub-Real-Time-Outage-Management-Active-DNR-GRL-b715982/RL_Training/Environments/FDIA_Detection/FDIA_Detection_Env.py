"""
Gym environment for an RL-based FDIA detector.

The detector observes compact residual features between a trusted OpenDSS
reference state and the received cyber observation. Its action is the detected
attack class/channel. This keeps the detection agent separate from the GCAPS
restoration agent while allowing both to be connected in testing.
"""

import random
import sys
from pathlib import Path

import gym
import numpy as np
from gym import spaces


THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[3]
RL_TESTING_DIR = REPO_ROOT / "RL_Testing"
if str(RL_TESTING_DIR) not in sys.path:
    sys.path.insert(0, str(RL_TESTING_DIR))

from FDIA_Common import ATTACK_NAMES, apply_attack, detect_fdia, random_attack_kwargs
from FDIA_Features import BDD_RESIDUAL_FEATURE_KEYS, residuals_to_feature_vector
from FDIA_ExperimentCore import ATTACK_TO_RL_LABEL, RestorationExperiment


class FDIADetectionEnv(gym.Env):
    """
    RL detector environment.

    Action labels:
        0 clean
        1 voltage_masking
        2 branchflow_hiding
        3 energy_inflation
        4 topology_drop
    """

    metadata = {"render.modes": ["human"]}

    def __init__(
        self,
        system="13bus",
        scenarios=None,
        attacks=None,
        samples_per_reset=1,
        seed=None,
        false_alarm_penalty=0.50,
        missed_attack_penalty=1.25,
        wrong_attack_penalty=0.75,
        physical_impact_weight=0.50,
    ):
        super(FDIADetectionEnv, self).__init__()
        self.system = system
        self.scenarios = scenarios or ["SC1", "SC2", "random"]
        self.attacks = attacks or list(ATTACK_NAMES)
        self.samples_per_reset = samples_per_reset
        self.false_alarm_penalty = float(false_alarm_penalty)
        self.missed_attack_penalty = float(missed_attack_penalty)
        self.wrong_attack_penalty = float(wrong_attack_penalty)
        self.physical_impact_weight = float(physical_impact_weight)
        self.rng = np.random.default_rng(seed)
        if seed is not None:
            random.seed(seed)

        # The detector training env only needs OpenDSS observations, not the
        # restoration model, so keep GCAPS unloaded for faster detector training.
        self.experiment = RestorationExperiment(system=system, load_model=False)
        self.action_space = spaces.Discrete(len(ATTACK_NAMES))
        self.observation_space = spaces.Box(
            low=-1.0e6,
            high=1.0e6,
            shape=(len(BDD_RESIDUAL_FEATURE_KEYS),),
            dtype=np.float32,
        )
        self.current_attack = "clean"
        self.current_true_label = ATTACK_TO_RL_LABEL["clean"]
        self.current_features = np.zeros(len(BDD_RESIDUAL_FEATURE_KEYS), dtype=np.float32)
        self.current_report = {}
        self.current_metadata = {}

    def seed(self, seed=None):
        self.rng = np.random.default_rng(seed)
        random.seed(seed)
        return [seed]

    def _sample_case(self):
        scenario_name = str(self.rng.choice(self.scenarios))
        attack_name = str(self.rng.choice(self.attacks))
        true_obs = self.experiment.get_observation(scenario_name)
        attack_kwargs = random_attack_kwargs(attack_name, self.rng)
        received_obs, metadata = apply_attack(true_obs, attack_name, **attack_kwargs)
        report = detect_fdia(true_obs, received_obs)
        features = residuals_to_feature_vector(report["residuals"], BDD_RESIDUAL_FEATURE_KEYS)
        return scenario_name, attack_name, features.astype(np.float32), report, metadata

    def reset(self):
        scenario_name, attack_name, features, report, metadata = self._sample_case()
        self.current_scenario = scenario_name
        self.current_attack = attack_name
        self.current_true_label = ATTACK_TO_RL_LABEL[attack_name]
        self.current_features = features
        self.current_report = report
        self.current_metadata = metadata
        return self.current_features

    def _physical_consequence_proxy(self):
        residuals = self.current_report.get("residuals", {})
        return (
            float(residuals.get("energy_abs", 0.0))
            + float(residuals.get("voltage_max_abs", 0.0))
            + float(residuals.get("branchflow_relative_mae", 0.0))
            + float(residuals.get("topology_changed_edge_fraction", 0.0))
        )

    def step(self, action):
        action = int(np.asarray(action).reshape(-1)[0])
        true_label = int(self.current_true_label)
        attack_present = self.current_attack != "clean"
        detected_attack = ATTACK_NAMES[action] != "clean"
        consequence = self._physical_consequence_proxy()

        if action == true_label:
            reward = 1.0
        elif not attack_present and detected_attack:
            reward = -self.false_alarm_penalty
        elif attack_present and not detected_attack:
            reward = -self.missed_attack_penalty - self.physical_impact_weight * consequence
        else:
            reward = -self.wrong_attack_penalty

        info = {
            "system": self.system,
            "scenario": self.current_scenario,
            "attack": self.current_attack,
            "true_label": true_label,
            "predicted_label": action,
            "predicted_attack": ATTACK_NAMES[action],
            "correct": int(action == true_label),
            "attack_present": int(attack_present),
            "physical_consequence_proxy": consequence,
            "residuals": self.current_report.get("residuals", {}),
            "attack_metadata": self.current_metadata,
        }

        done = True
        terminal_obs = np.array(self.current_features, copy=True)
        return terminal_obs, float(reward), done, info

    def render(self, mode="human"):
        print(
            "system={} scenario={} true_attack={}".format(
                self.system,
                getattr(self, "current_scenario", "unknown"),
                self.current_attack,
            )
        )
