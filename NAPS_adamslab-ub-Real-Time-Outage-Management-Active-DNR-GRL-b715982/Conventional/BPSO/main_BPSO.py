"""
In this file the functions to create particle, swarm, 
and the main BPSO algorithm is defined

"""
import time
import argparse
import csv
import json
from pathlib import Path
from model_functions import*

No_switches = n_actions


#----- BPSO parameters
N_particles = 80
itermax = 400
# Particle parameters
particle_dims=No_switches #dimension of a particle
NUM_SWITCHES = len(sectional_swt) + len(tie_swt)
ATTACKS = ["clean", "voltage_masking", "branchflow_hiding", "energy_inflation", "topology_drop"]
SCENARIOS = {
    "SC1": [('13','18'), ('51','151'), ('65', '66')],
    "SC2": [('151','300'), ('57','60'), ('56','92'), ('67','72'), ('67','97')],
}
BPSO_DETECTOR_THRESHOLDS = {
    "energy_abs": 0.05,
    "topology_changed_edge_fraction": 0.01,
}
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "RL_Testing" / "123bus" / "paper_results" / "bpso_fdia_123_results.csv"
DEFAULT_DEFENDED_OUTPUT = REPO_ROOT / "RL_Testing" / "123bus" / "paper_results" / "bpso_fdia_123_defended_results.csv"
DEFENSE_MODES = ["unmitigated", "mitigated"]


class Particle:
    def __init__(self): 
        self.position = []  # particle position
        self.velocity = []  # particle velocity 
        self.fitness = -1*float("inf")  #This is for maximization
        self.pbest_position = []  # best position of the particle
        self.pbest_fitness= -1*float("inf") #This is for maximization
        
        # Initiate
        self.position  = np.random.randint(2, size = particle_dims)
        self.velocity  = np.random.randint(2, size = particle_dims)


    # Evaluate fitness and estimate personal best of the particle so far
    def evaluate_fitness(self, objective_func):
        self.fitness = objective_func(self.position)
        if self.fitness > self.pbest_fitness: # This is for maximization
            self.pbest_fitness = self.fitness
            self.pbest_position = self.position         
            
            
    def update_position(self, gbest_position): # To update position 
        c = 2
        r1 = np.random.rand()
        r2 = np.random.rand()
        vmax = 6
        
        # Compute velocity for each dimension and then update each dimension of the particle
        for indx, vel in enumerate(self.velocity):
            # Update velocity for the dimension of particle
              

            vel = vel + c * r1 * (self.pbest_position[indx] - self.position[indx]) + c * r2 * (gbest_position[indx] - self.position[indx]) 
            if abs(vel) > vmax and abs(vel) is vel: # greater than upper limit
               vel = vmax
            elif abs(vel) > vmax: # lesser than minimum limit
                vel = -vmax  
            vel = self.sigmoid(vel)
            # Update the position for the dimension of particle
            if np.random.rand(1) < vel:
               self.position[indx] = 1
            else:
                self.position[indx] = 0
                
            self.velocity[indx] = vel
            
            
    def sigmoid(self, x): # sigmoid transformation
        return 1.0/(1.0 + np.exp(-(x)))


def BPSO(objective_func, N_particles, itermax):
    swarm_particles = []
    gbest_position = []
    gbest_fitness= -1 * float("inf") #This is for maximization
    for i in range(N_particles): # Creating a swarm of particles
        swarm_particles.append(Particle()) 
    optimal_position=[]
    optimal_fitness=[]
    
    for iter in range(itermax): 
        for i in range(N_particles):
            swarm_particles[i].evaluate_fitness(objective_func)

            if swarm_particles[i].fitness > gbest_fitness: # This is for maximization
               gbest_fitness = float(swarm_particles[i].fitness)
               gbest_position = list(swarm_particles[i].position)
            print(f"Iteration:{iter}, particle:{i}, best_fitness:{gbest_fitness:.6f}")

        for i in range(N_particles):
            swarm_particles[i].update_position(gbest_position) #update velocity and position

        optimal_position.append(gbest_position)
        optimal_fitness.append(gbest_fitness)
    return optimal_position, optimal_fitness


def resolve_output_path(path):
    output_path = Path(path)
    if output_path.is_absolute():
        return output_path
    return (Path.cwd() / output_path).resolve()


def split_action(action):
    switch_vector = [int(value) for value in action[:NUM_SWITCHES]]
    load_values = [int(value) for value in action[NUM_SWITCHES:]]
    load_status = {load: int(load_values[index]) for index, load in enumerate(dispatch_loads)}
    return switch_vector, load_status


def build_attack_context(attack_name, scenario_edges, seed):
    if attack_name == "clean":
        return {}, {"target": "none", "optimizer_input_changed": False}
    if attack_name == "topology_drop":
        rng = np.random.default_rng(seed)
        scenario_set = set(tuple(edge) for edge in scenario_edges)
        candidates = [tuple(edge) for edge in list(G_init.edges()) if tuple(edge) not in scenario_set]
        drop_count = max(1, int(np.ceil(0.05 * len(candidates))))
        selected_idx = rng.choice(len(candidates), size=min(drop_count, len(candidates)), replace=False)
        dropped_edges = [candidates[int(idx)] for idx in selected_idx]
        metadata = {
            "target": "optimizer_topology",
            "optimizer_input_changed": True,
            "dropped_edges": [list(edge) for edge in dropped_edges],
            "note": "BPSO optimizes on a perceived topology with these additional missing edges; final action is evaluated on the true topology.",
        }
        return {"extra_out_edges": dropped_edges}, metadata
    if attack_name == "energy_inflation":
        rng = np.random.default_rng(seed)
        target_fraction = 0.25
        count = max(1, int(np.ceil(target_fraction * len(dispatch_loads))))
        selected = sorted(rng.choice(dispatch_loads, size=count, replace=False).tolist())
        bias = 0.25
        load_weights = {load: 1.0 + bias for load in selected}
        load_weights.update({load.lower(): 1.0 + bias for load in selected})
        metadata = {
            "target": "optimizer_load_weights",
            "optimizer_input_changed": True,
            "bias": bias,
            "weighted_loads": selected,
            "note": "BPSO optimizes with inflated perceived importance for selected dispatchable loads; final action is evaluated on true loads.",
        }
        return {"load_weights": load_weights}, metadata
    if attack_name == "voltage_masking":
        return {}, {
            "target": "NodeFeat(BusVoltage)",
            "optimizer_input_changed": False,
            "note": "BPSO does not use voltage measurements as optimization input in this implementation; use this case for FDIA detectability only.",
        }
    if attack_name == "branchflow_hiding":
        return {}, {
            "target": "EdgeFeat(Branchflow)",
            "optimizer_input_changed": False,
            "note": "BPSO does not use branch-flow measurements as optimization input in this implementation; use this case for FDIA detectability only.",
        }
    raise ValueError(f"Unknown attack '{attack_name}'")


def detect_bpso_input_attack(attack_name, attack_metadata):
    residuals = {
        "energy_abs": 0.0,
        "topology_changed_edge_fraction": 0.0,
        "measurement_detector_not_run": 0.0,
    }
    if attack_name == "energy_inflation":
        residuals["energy_abs"] = float(attack_metadata.get("bias", 0.0))
    elif attack_name == "topology_drop":
        edge_count = max(len(G_init.edges()), 1)
        residuals["topology_changed_edge_fraction"] = float(len(attack_metadata.get("dropped_edges", [])) / edge_count)
    elif attack_name in ("voltage_masking", "branchflow_hiding"):
        residuals["measurement_detector_not_run"] = 1.0

    detected_channels = []
    scores = []
    for metric, threshold in BPSO_DETECTOR_THRESHOLDS.items():
        value = residuals.get(metric, 0.0)
        if value > threshold:
            detected_channels.append(metric)
        scores.append(value / threshold if threshold > 0 else 0.0)

    return {
        "detected": bool(detected_channels),
        "score": float(max(scores)) if scores else 0.0,
        "detected_channels": detected_channels,
        "residuals": residuals,
    }


def mitigate_bpso_attack_context(attack_name, attack_context, attack_metadata, detection):
    """Correct attacked BPSO optimizer inputs when the detector flags them."""
    if not detection["detected"]:
        return attack_context, {
            "strategy": "none",
            "mitigation_applied": False,
            "mitigated_channels": [],
            "mitigated_keys": [],
            "note": "No optimizer-input FDIA was detected.",
        }

    mitigated_channels = []
    mitigated_keys = []
    corrected_context = dict(attack_context)

    if attack_name == "energy_inflation" and "energy_abs" in detection["detected_channels"]:
        corrected_context.pop("load_weights", None)
        mitigated_channels.append("energy")
        mitigated_keys.append("load_weights")

    if attack_name == "topology_drop" and "topology_changed_edge_fraction" in detection["detected_channels"]:
        corrected_context.pop("extra_out_edges", None)
        mitigated_channels.append("topology")
        mitigated_keys.append("extra_out_edges")

    return corrected_context, {
        "strategy": "remove_detected_optimizer_input_corruption",
        "mitigation_applied": bool(mitigated_keys),
        "mitigated_channels": mitigated_channels,
        "mitigated_keys": mitigated_keys,
        "note": "BPSO optimization uses corrected inputs; final action is still evaluated on the true physical topology.",
    }


def run_case(scenario_name, attack_name, particles, iterations, seed, clean_action=None, defense_mode="unmitigated"):
    scenario_edges = SCENARIOS[scenario_name]
    attack_context, attack_metadata = build_attack_context(attack_name, scenario_edges, seed)
    detection = detect_bpso_input_attack(attack_name, attack_metadata)
    optimizer_context = attack_context
    mitigation_metadata = {
        "strategy": "none",
        "mitigation_applied": False,
        "mitigated_channels": [],
        "mitigated_keys": [],
        "note": "Mitigation disabled for this run.",
    }
    post_mitigation_detection = detection

    if defense_mode == "mitigated" and attack_name != "clean":
        optimizer_context, mitigation_metadata = mitigate_bpso_attack_context(
            attack_name, attack_context, attack_metadata, detection
        )
        if mitigation_metadata["mitigation_applied"]:
            post_mitigation_detection = detect_bpso_input_attack("clean", {"target": "none"})

    np.random.seed(seed)

    def attacked_objective(position):
        return objective_func(position, scenario_edges=scenario_edges, attack_context=optimizer_context, verbose=False)

    start = time.perf_counter()
    optimal_position, optimal_fitness = BPSO(attacked_objective, particles, iterations)
    runtime_sec = time.perf_counter() - start

    best_action = np.array(optimal_position[-1], dtype=int)
    final_metrics = simulate_action(best_action, scenario_edges=scenario_edges, attack_context=None, verbose=False)
    switch_vector, load_status = split_action(best_action)

    if clean_action is None:
        action_changed = 0
        switch_changes = 0
        load_changes = 0
    else:
        clean_action = np.array(clean_action, dtype=int)
        action_changed = int(np.any(best_action != clean_action))
        switch_changes = int(np.sum(best_action[:NUM_SWITCHES] != clean_action[:NUM_SWITCHES]))
        load_changes = int(np.sum(best_action[NUM_SWITCHES:] != clean_action[NUM_SWITCHES:]))

    row = {
        "method": "BPSO",
        "scenario": scenario_name,
        "case": attack_name,
        "defense_mode": "clean" if attack_name == "clean" else defense_mode,
        "energy_kw": final_metrics["energy_kw"],
        "total_demand_kw": final_metrics["total_demand_kw"],
        "energy_ratio": final_metrics["energy_ratio"],
        "voltage_violation": final_metrics["voltage_violation"],
        "convergence_violation": final_metrics["convergence_violation"],
        "reward": final_metrics["fitness"],
        "fitness": final_metrics["fitness"],
        "optimizer_best_fitness": float(optimal_fitness[-1]) if optimal_fitness else 0.0,
        "policy_time_ms": runtime_sec * 1000.0,
        "runtime_sec": runtime_sec,
        "loads_served": final_metrics["loads_served"],
        "loads_shed": final_metrics["loads_shed"],
        "closed_switches": int(np.sum(best_action[:NUM_SWITCHES])),
        "open_switches": NUM_SWITCHES - int(np.sum(best_action[:NUM_SWITCHES])),
        "action_changed": action_changed,
        "switch_changes_vs_clean": switch_changes,
        "load_changes_vs_clean": load_changes,
        "switch_vector": switch_vector,
        "load_status": load_status,
        "attack_metadata": attack_metadata,
        "mitigation_metadata": mitigation_metadata,
        "mitigation_applied": int(mitigation_metadata["mitigation_applied"]),
        "mitigated_channels": mitigation_metadata["mitigated_channels"],
        "mitigated_keys": mitigation_metadata["mitigated_keys"],
        "fdia_detected": int(detection["detected"]),
        "detector_score": detection["score"],
        "detected_channels": detection["detected_channels"],
        "detector_residuals": detection["residuals"],
        "post_mitigation_fdia_detected": int(post_mitigation_detection["detected"]),
        "post_mitigation_detector_score": post_mitigation_detection["score"],
        "post_mitigation_detected_channels": post_mitigation_detection["detected_channels"],
        "post_mitigation_detector_residuals": post_mitigation_detection["residuals"],
        "particles": particles,
        "iterations": iterations,
        "best_iteration": int(np.argmax(optimal_fitness)) if optimal_fitness else -1,
        "action_array": best_action.tolist(),
    }
    return row


def write_csv(rows, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "method",
        "scenario",
        "case",
        "defense_mode",
        "energy_kw",
        "total_demand_kw",
        "energy_ratio",
        "voltage_violation",
        "convergence_violation",
        "reward",
        "fitness",
        "optimizer_best_fitness",
        "policy_time_ms",
        "runtime_sec",
        "loads_served",
        "loads_shed",
        "closed_switches",
        "open_switches",
        "action_changed",
        "switch_changes_vs_clean",
        "load_changes_vs_clean",
        "switch_vector",
        "load_status",
        "attack_metadata",
        "mitigation_metadata",
        "mitigation_applied",
        "mitigated_channels",
        "mitigated_keys",
        "fdia_detected",
        "detector_score",
        "detected_channels",
        "detector_residuals",
        "post_mitigation_fdia_detected",
        "post_mitigation_detector_score",
        "post_mitigation_detected_channels",
        "post_mitigation_detector_residuals",
        "particles",
        "iterations",
        "best_iteration",
    ]
    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            csv_row = {field: row[field] for field in fields}
            csv_row["switch_vector"] = json.dumps(csv_row["switch_vector"])
            csv_row["load_status"] = json.dumps(csv_row["load_status"])
            csv_row["attack_metadata"] = json.dumps(csv_row["attack_metadata"])
            csv_row["mitigation_metadata"] = json.dumps(csv_row["mitigation_metadata"])
            csv_row["mitigated_channels"] = json.dumps(csv_row["mitigated_channels"])
            csv_row["mitigated_keys"] = json.dumps(csv_row["mitigated_keys"])
            csv_row["detected_channels"] = json.dumps(csv_row["detected_channels"])
            csv_row["detector_residuals"] = json.dumps(csv_row["detector_residuals"])
            csv_row["post_mitigation_detected_channels"] = json.dumps(csv_row["post_mitigation_detected_channels"])
            csv_row["post_mitigation_detector_residuals"] = json.dumps(csv_row["post_mitigation_detector_residuals"])
            writer.writerow(csv_row)


def parse_args():
    parser = argparse.ArgumentParser(description="Run BPSO IEEE 123-bus clean/FDIA comparison cases")
    parser.add_argument("--scenarios", nargs="+", default=["SC2"], choices=sorted(SCENARIOS))
    parser.add_argument("--attacks", nargs="+", default=["clean"], choices=ATTACKS)
    parser.add_argument("--particles", type=int, default=N_particles)
    parser.add_argument("--iterations", type=int, default=itermax)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--output", default=str(DEFAULT_DEFENDED_OUTPUT))
    parser.add_argument("--defense-modes", nargs="+", default=DEFENSE_MODES, choices=DEFENSE_MODES)
    return parser.parse_args()


def main():
    args = parse_args()
    rows = []
    for scenario_name in args.scenarios:
        clean_row = run_case(scenario_name, "clean", args.particles, args.iterations, args.seed)
        rows.append(clean_row)
        clean_action = clean_row["action_array"]
        print(
            f"BPSO {scenario_name} clean | energy_ratio={clean_row['energy_ratio']:.6f} | "
            f"fitness={clean_row['fitness']:.6f} | runtime_sec={clean_row['runtime_sec']:.2f}"
        )
        for attack_name in args.attacks:
            if attack_name == "clean":
                continue
            for defense_mode in args.defense_modes:
                row = run_case(
                    scenario_name,
                    attack_name,
                    args.particles,
                    args.iterations,
                    args.seed,
                    clean_action,
                    defense_mode=defense_mode,
                )
                rows.append(row)
                print(
                    f"BPSO {scenario_name} {attack_name} {defense_mode} | "
                    f"energy_ratio={row['energy_ratio']:.6f} | "
                    f"fitness={row['fitness']:.6f} | action_changed={row['action_changed']} | "
                    f"mitigated={row['mitigation_applied']} | runtime_sec={row['runtime_sec']:.2f}"
                )

    output_path = resolve_output_path(args.output)
    write_csv(rows, output_path)
    print(f"Saved BPSO paper CSV: {output_path}")


if __name__ == "__main__":
    main()
