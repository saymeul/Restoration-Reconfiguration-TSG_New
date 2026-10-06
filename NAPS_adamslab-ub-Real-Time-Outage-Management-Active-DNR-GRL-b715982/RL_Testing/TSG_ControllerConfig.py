"""Controller selection helpers for TSG vulnerability studies.

The original TSG runners default to the GCAPS/GRL controller.  This module
keeps alternate controller selection explicit so comparison runs can use the
same attack/evaluation logic while writing to separate result namespaces.
"""

from pathlib import Path
from time import perf_counter

import numpy as np

from FDIA_Common import restoration_action_quality
from FDIA_ExperimentCore import BASE_DIR, RestorationExperiment, resolve_path


DEFAULT_CONTROLLER = "GRL"
CONTROLLER_CHOICES = ("GRL", "MLP", "BPSO")

_MODEL_PATHS = {
    "GRL": {
        "34bus": BASE_DIR / "34bus" / "TrainedModels" / "GCAPS_34.zip",
        "123bus": BASE_DIR / "123bus" / "TrainedModels" / "GCAPS_123.zip",
        "8500bus": BASE_DIR / "8500bus" / "TrainedModels" / "GCAPS_8500.zip",
    },
    "MLP": {
        "34bus": BASE_DIR / "34bus" / "TrainedModels" / "MLP_34.zip",
        "123bus": BASE_DIR / "123bus" / "TrainedModels" / "MLP_123.zip",
        "8500bus": BASE_DIR / "8500bus" / "TrainedModels" / "MLP_8500.zip",
    },
}

_OUTPUT_NAMESPACE = {
    ("34bus", "GRL"): "tsg_ieee34",
    ("34bus", "MLP"): "tsg_ieee34_mlp",
    ("34bus", "BPSO"): "tsg_ieee34_bpso",
    ("123bus", "GRL"): "tsg_ieee123",
    ("123bus", "MLP"): "tsg_ieee123_mlp",
    ("123bus", "BPSO"): "tsg_ieee123_bpso",
    ("8500bus", "GRL"): "tsg_ieee8500",
    ("8500bus", "MLP"): "tsg_ieee8500_mlp",
    ("8500bus", "BPSO"): "tsg_ieee8500_bpso",
}


def stable_seed(*parts):
    value = 2166136261
    for part in parts:
        for char in str(part):
            value ^= ord(char)
            value = (value * 16777619) % (2**32 - 1)
    return int(value or 1)


def canonical_edge(edge):
    u, v = edge
    return tuple(sorted((str(u), str(v))))


def resolve_graph_edge(graph, edge):
    u, v = canonical_edge(edge)
    if (u, v) in graph.edges:
        return u, v
    if (v, u) in graph.edges:
        return v, u
    raise KeyError("Outage edge {} is not present in the graph.".format((u, v)))


class BPSORestorationExperiment(RestorationExperiment):
    """Binary PSO controller with the same experiment/evaluation interface.

    BPSO is not a trained neural policy. It uses the received observation only
    for decision constraints such as ActionMasking, then scores candidate
    actions on the current deterministic OpenDSS outage scenario.
    """

    def __init__(
        self,
        system,
        particles=8,
        iterations=8,
        seed=5157,
        enforce_action_mask=True,
    ):
        super().__init__(system=system, load_model=False)
        self.controller_name = "BPSO"
        self.controller_model_path = ""
        self.bpso_particles = max(1, int(particles))
        self.bpso_iterations = max(1, int(iterations))
        self.bpso_seed = int(seed)
        self.bpso_enforce_action_mask = bool(enforce_action_mask)
        self._tsg_current_scenario = None

    def set_current_scenario(self, scenario):
        self._tsg_current_scenario = dict(scenario or {})

    def _apply_current_scenario(self):
        if not self._tsg_current_scenario:
            raise RuntimeError(
                "BPSO requires a current deterministic outage scenario before predict_action()."
            )
        DSSCktObj, G_init, _conv_flag = self.init_module.initialize()
        self.env.DSSCktObj = DSSCktObj
        self.env.G = G_init.copy()

        normalized_edges = [
            resolve_graph_edge(G_init, edge)
            for edge in self._tsg_current_scenario.get("outage_edges", [])
        ]
        for outage_edge in normalized_edges:
            branch_name = G_init.edges[outage_edge]["label"][0]
            self.env.DSSCktObj.dss.Text.Command("Open {} term=1".format(branch_name))
            self.env.DSSCktObj.dss.Solution.Solve()

        self.env.G.remove_edges_from(normalized_edges)
        self.env.outedges = normalized_edges

    def _evaluate_candidate_action(self, action):
        self._apply_current_scenario()
        action = np.asarray(action, dtype=int)
        obs_post_action, reward, done, _info = self.env.step(action)
        metrics = self.metrics_from_observation(obs_post_action, reward=reward, action=action)
        metrics["done"] = bool(done)
        return metrics

    def predict_action(self, obs):
        rng = np.random.default_rng(
            stable_seed(
                self.bpso_seed,
                self.system,
                self._tsg_current_scenario.get("scenario_seed", "no_scenario")
                if self._tsg_current_scenario
                else "no_scenario",
            )
        )
        n_actions = int(self.n_actions)
        action_mask = np.asarray(obs.get("ActionMasking", []), dtype=float).reshape(-1)
        if action_mask.size != n_actions:
            action_mask = np.zeros(n_actions, dtype=float)

        def repair(position):
            action = np.asarray(position, dtype=int).reshape(-1).copy()
            if action.size != n_actions:
                repaired = np.zeros(n_actions, dtype=int)
                repaired[: min(action.size, n_actions)] = action[: min(action.size, n_actions)]
                action = repaired
            action = np.where(action > 0, 1, 0).astype(int)
            if self.bpso_enforce_action_mask:
                action[action_mask > 0.5] = 0
            return action

        def score(position):
            action = repair(position)
            metrics = self._evaluate_candidate_action(action)
            return restoration_action_quality(metrics), metrics, action

        start = perf_counter()
        positions = rng.integers(0, 2, size=(self.bpso_particles, n_actions), dtype=int)
        positions = np.asarray([repair(item) for item in positions], dtype=int)
        velocities = rng.normal(0.0, 0.25, size=(self.bpso_particles, n_actions))
        personal_best_positions = positions.copy()
        personal_best_scores = np.full(self.bpso_particles, -np.inf, dtype=float)
        global_best_position = positions[0].copy()
        global_best_score = -np.inf
        global_best_metrics = None

        for _iteration in range(self.bpso_iterations):
            for particle_index in range(self.bpso_particles):
                value, metrics, action = score(positions[particle_index])
                if value > personal_best_scores[particle_index]:
                    personal_best_scores[particle_index] = value
                    personal_best_positions[particle_index] = action
                if value > global_best_score:
                    global_best_score = value
                    global_best_position = action
                    global_best_metrics = metrics

            inertia = 0.72
            cognitive = 1.49
            social = 1.49
            r1 = rng.random(size=(self.bpso_particles, n_actions))
            r2 = rng.random(size=(self.bpso_particles, n_actions))
            velocities = (
                inertia * velocities
                + cognitive * r1 * (personal_best_positions - positions)
                + social * r2 * (global_best_position - positions)
            )
            probabilities = 1.0 / (1.0 + np.exp(-np.clip(velocities, -20.0, 20.0)))
            positions = (rng.random(size=(self.bpso_particles, n_actions)) < probabilities).astype(int)
            positions = np.asarray([repair(item) for item in positions], dtype=int)

        elapsed_ms = (perf_counter() - start) * 1000.0
        self.last_bpso_metadata = {
            "bpso_particles": self.bpso_particles,
            "bpso_iterations": self.bpso_iterations,
            "bpso_candidate_evaluations": int(self.bpso_particles * self.bpso_iterations),
            "bpso_best_quality": float(global_best_score),
            "bpso_best_metrics": global_best_metrics or {},
            "bpso_enforced_action_mask": int(self.bpso_enforce_action_mask),
        }
        return repair(global_best_position), float(elapsed_ms)


def normalize_controller(controller):
    value = str(controller or DEFAULT_CONTROLLER).upper()
    if value not in CONTROLLER_CHOICES:
        raise ValueError(
            "Unknown controller '{}'. Available: {}".format(
                controller,
                ", ".join(CONTROLLER_CHOICES),
            )
        )
    return value


def add_controller_args(parser):
    parser.add_argument(
        "--controller",
        choices=CONTROLLER_CHOICES,
        default=DEFAULT_CONTROLLER,
        help="Restoration controller to evaluate without changing the physical feeder.",
    )
    parser.add_argument(
        "--model-path",
        default=None,
        help=(
            "Optional explicit restoration model path. If omitted, the selected "
            "controller's feeder-specific trained model is used."
        ),
    )
    parser.add_argument(
        "--bpso-particles",
        type=int,
        default=8,
        help="BPSO particle count when --controller BPSO is selected.",
    )
    parser.add_argument(
        "--bpso-iterations",
        type=int,
        default=8,
        help="BPSO iteration count when --controller BPSO is selected.",
    )
    parser.add_argument(
        "--bpso-seed",
        type=int,
        default=5157,
        help="Base deterministic seed for BPSO candidate search.",
    )
    parser.add_argument(
        "--bpso-allow-masked-actions",
        action="store_true",
        help="Allow BPSO to choose actions marked unavailable by ActionMasking.",
    )


def controller_model_path(system, controller=DEFAULT_CONTROLLER, model_path=None):
    selected = normalize_controller(controller)
    if selected == "BPSO":
        return Path(model_path) if model_path else Path("__BPSO_NO_TRAINED_MODEL__")
    if model_path:
        candidate = resolve_path(model_path)
    else:
        try:
            candidate = _MODEL_PATHS[selected][system]
        except KeyError as exc:
            raise ValueError(
                "No model path is registered for controller={} system={}.".format(
                    selected,
                    system,
                )
            ) from exc
    candidate = Path(candidate)
    if not candidate.exists():
        raise FileNotFoundError(
            "Missing restoration model for controller={} system={}: {}".format(
                selected,
                system,
                candidate,
            )
        )
    return candidate


def make_controller_experiment(system, args=None, load_model=True):
    controller = normalize_controller(getattr(args, "controller", DEFAULT_CONTROLLER))
    model_override = getattr(args, "model_path", None)
    if controller == "BPSO":
        experiment = BPSORestorationExperiment(
            system=system,
            particles=getattr(args, "bpso_particles", 8),
            iterations=getattr(args, "bpso_iterations", 8),
            seed=getattr(args, "bpso_seed", 5157),
            enforce_action_mask=not bool(getattr(args, "bpso_allow_masked_actions", False)),
        )
        return experiment
    model_path = controller_model_path(system, controller, model_override)
    experiment = RestorationExperiment(
        system=system,
        model_path=model_path,
        load_model=load_model,
    )
    experiment.controller_name = controller
    experiment.controller_model_path = str(model_path)
    return experiment


def controller_output_dir(output_dir, default_output_dir, system, controller=DEFAULT_CONTROLLER):
    selected = normalize_controller(controller)
    if str(output_dir) != str(default_output_dir):
        return output_dir
    current_namespace = _OUTPUT_NAMESPACE[(system, DEFAULT_CONTROLLER)]
    target_namespace = _OUTPUT_NAMESPACE[(system, selected)]
    parts = [
        target_namespace if part == current_namespace else part
        for part in Path(default_output_dir).parts
    ]
    return str(Path(*parts))


def controller_metadata(system, args):
    controller = normalize_controller(getattr(args, "controller", DEFAULT_CONTROLLER))
    model_path = controller_model_path(system, controller, getattr(args, "model_path", None))
    metadata = {
        "controller": controller,
        "controller_model_path": str(model_path),
        "controller_model_exists": bool(model_path.exists()) if str(model_path) else False,
        "controller_family": (
            "graph_rl"
            if controller == "GRL"
            else "mlp_policy"
            if controller == "MLP"
            else "binary_particle_swarm_optimizer"
        ),
        "controller_observation_contract": (
            "Same OpenDSS observation dictionary and MultiBinary restoration action "
            "contract used by the GRL vulnerability runners."
        ),
    }
    if controller == "BPSO":
        metadata.update(
            {
                "bpso_particles": int(getattr(args, "bpso_particles", 8)),
                "bpso_iterations": int(getattr(args, "bpso_iterations", 8)),
                "bpso_seed": int(getattr(args, "bpso_seed", 5157)),
                "bpso_enforce_action_mask": int(
                    not bool(getattr(args, "bpso_allow_masked_actions", False))
                ),
                "bpso_decision_model": (
                    "Binary PSO scores candidate restoration actions on the current "
                    "OpenDSS outage scenario and uses the received ActionMasking channel "
                    "as an availability constraint."
                ),
            }
        )
    return metadata


def experiment_controller_name(experiment):
    return getattr(experiment, "controller_name", DEFAULT_CONTROLLER)


def experiment_controller_model_path(experiment):
    return getattr(experiment, "controller_model_path", str(getattr(experiment, "model_path", "")))
