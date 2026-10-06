"""
Run multi-seed robustness/statistical validation for FDIA resilience.

This script samples random outage scenarios and randomized FDIA strengths across
multiple seeds, records physical degradation statistics, and evaluates RL
detector + mitigation on the most harmful cases from each seed.
"""

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from FDIA_Common import ATTACK_NAMES
from FDIA_ExperimentCore import REPO_ROOT, RestorationExperiment, resolve_path, write_csv
from Run_FDIA_AttackSearch import (
    resilience_rows_for_case,
    run_search_case,
    strong_attack_kwargs,
)


DEFAULT_ATTACKS = ["voltage_masking", "branchflow_hiding", "energy_inflation", "topology_drop"]


def parse_args():
    parser = argparse.ArgumentParser(description="FDIA robustness/statistical validation")
    parser.add_argument("--systems", nargs="+", default=["13bus", "34bus", "123bus"], choices=["13bus", "34bus", "123bus"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[2026, 2027, 2028])
    parser.add_argument("--trials-per-seed", type=int, default=100)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--attacks", nargs="+", default=DEFAULT_ATTACKS, choices=ATTACK_NAMES)
    parser.add_argument(
        "--detector-template",
        default="RL_Training/Trained_Models/FDIA_Detectors/RLFDIA_{system}_final.zip",
        help="Path template for trained RL FDIA detector models",
    )
    parser.add_argument("--output-dir", default="paper_results/robustness_validation")
    parser.add_argument("--harmful-threshold", type=float, default=1.0e-6)
    parser.add_argument(
        "--filtered-max-impact",
        type=float,
        default=5.0,
        help="Maximum physical impact retained in filtered paper-ready statistics",
    )
    parser.add_argument(
        "--filtered-max-abs-energy-ratio",
        type=float,
        default=2.0,
        help="Maximum absolute energy ratio retained in filtered paper-ready statistics",
    )
    parser.add_argument(
        "--filtered-max-convergence-violation",
        type=float,
        default=0.0,
        help="Maximum convergence violation retained in filtered paper-ready statistics",
    )
    return parser.parse_args()


def as_float(row, key, default=0.0):
    try:
        value = row.get(key, "")
        if value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(row, key, default=0):
    try:
        value = row.get(key, "")
        if value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def fmt(value, digits=6):
    if value == "":
        return ""
    if not math.isfinite(float(value)):
        return ""
    return f"{float(value):.{digits}f}"


def resolve_detector_path(template, system):
    path_text = template.format(system=system)
    candidate = Path(path_text)
    if candidate.is_absolute():
        return candidate
    return REPO_ROOT / candidate


def std(values):
    if len(values) < 2:
        return 0.0
    return float(np.std(np.asarray(values, dtype=float), ddof=1))


def mean_ci(values, z=1.96):
    if not values:
        return 0.0, 0.0
    mean = float(np.mean(values))
    if len(values) < 2:
        return mean, mean
    margin = z * std(values) / math.sqrt(len(values))
    return max(0.0, mean - margin), mean + margin


def wilson_ci(successes, samples, z=1.96):
    if samples <= 0:
        return 0.0, 0.0
    p_hat = successes / samples
    z2 = z * z
    denom = 1.0 + z2 / samples
    center = (p_hat + z2 / (2.0 * samples)) / denom
    margin = z * math.sqrt((p_hat * (1.0 - p_hat) + z2 / (4.0 * samples)) / samples) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def filtered_exclusion_reason(row, args):
    convergence = as_float(row, "convergence_violation", 0.0)
    if not math.isfinite(convergence) or convergence > args.filtered_max_convergence_violation:
        return "nonconverged"
    clean_convergence = convergence - as_float(row, "convergence_delta_vs_clean", 0.0)
    if not math.isfinite(clean_convergence) or clean_convergence > args.filtered_max_convergence_violation:
        return "clean_nonconverged"

    impact = as_float(row, "physical_impact_score", math.nan)
    if not math.isfinite(impact):
        return "nonfinite_impact"
    if impact < 0.0 or impact > args.filtered_max_impact:
        return "impact_outlier"

    energy_ratio = as_float(row, "energy_ratio", math.nan)
    if not math.isfinite(energy_ratio) or abs(energy_ratio) > args.filtered_max_abs_energy_ratio:
        return "energy_ratio_outlier"
    clean_energy_ratio = energy_ratio - as_float(row, "energy_ratio_delta_vs_clean", 0.0)
    if not math.isfinite(clean_energy_ratio) or abs(clean_energy_ratio) > args.filtered_max_abs_energy_ratio:
        return "clean_energy_ratio_outlier"

    return ""


def split_filtered_rows(rows, args):
    kept = []
    excluded = defaultdict(int)
    for row in rows:
        reason = filtered_exclusion_reason(row, args)
        if reason:
            excluded[reason] += 1
        else:
            kept.append(row)
    return kept, excluded


def filter_report_rows(total_rows, kept_rows, excluded, args):
    rows = [
        {
            "item": "raw_trials",
            "count": total_rows,
            "details": "All Monte Carlo trials before paper-ready filtering",
        },
        {
            "item": "filtered_trials",
            "count": kept_rows,
            "details": (
                "convergence_violation <= {conv}, physical_impact_score <= {impact}, "
                "abs(energy_ratio) <= {energy}"
            ).format(
                conv=args.filtered_max_convergence_violation,
                impact=args.filtered_max_impact,
                energy=args.filtered_max_abs_energy_ratio,
            ),
        },
    ]
    for reason, count in sorted(excluded.items()):
        rows.append(
            {
                "item": "excluded_{}".format(reason),
                "count": count,
                "details": "Excluded from filtered statistics; retained in raw CSV",
            }
        )
    return rows


def summarize_trials(rows, harmful_threshold):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["system"], row["attack"])].append(row)

    summary = []
    for (system, attack), items in sorted(grouped.items()):
        impacts = [as_float(row, "physical_impact_score") for row in items]
        energy_losses = [max(0.0, -as_float(row, "energy_ratio_delta_vs_clean")) for row in items]
        reward_losses = [max(0.0, -as_float(row, "reward_delta_vs_clean")) for row in items]
        harmful = [impact for impact in impacts if impact > harmful_threshold]
        action_changed = sum(as_int(row, "action_changed") for row in items)
        harmful_ci_low, harmful_ci_high = wilson_ci(len(harmful), len(items))
        mean_impact_ci_low, mean_impact_ci_high = mean_ci(impacts)
        summary.append(
            {
                "system": system,
                "attack": attack,
                "trials": len(items),
                "harmful_cases": len(harmful),
                "harmful_rate": fmt(len(harmful) / len(items) if items else 0.0),
                "harmful_rate_ci_low": fmt(harmful_ci_low),
                "harmful_rate_ci_high": fmt(harmful_ci_high),
                "action_change_rate": fmt(action_changed / len(items) if items else 0.0),
                "mean_impact": fmt(float(np.mean(impacts)) if impacts else 0.0),
                "mean_impact_ci_low": fmt(mean_impact_ci_low),
                "mean_impact_ci_high": fmt(mean_impact_ci_high),
                "std_impact": fmt(std(impacts)),
                "max_impact": fmt(max(impacts) if impacts else 0.0),
                "mean_energy_loss": fmt(float(np.mean(energy_losses)) if energy_losses else 0.0),
                "max_energy_loss": fmt(max(energy_losses) if energy_losses else 0.0),
                "mean_reward_loss": fmt(float(np.mean(reward_losses)) if reward_losses else 0.0),
                "max_reward_loss": fmt(max(reward_losses) if reward_losses else 0.0),
            }
        )
    return summary


def group_resilience(rows):
    grouped = defaultdict(dict)
    for row in rows:
        key = (
            row.get("system", ""),
            row.get("validation_seed", ""),
            row.get("scenario", ""),
            row.get("attack", ""),
        )
        grouped[key][row.get("mode", "")] = row
    return grouped


def summarize_resilience(rows, harmful_threshold):
    grouped = group_resilience(rows)
    summary = []
    detector_counts = defaultdict(lambda: {"samples": 0, "correct": 0})
    recovery_by_system = defaultdict(list)

    for (system, validation_seed, scenario, attack), modes in sorted(grouped.items()):
        attacked = modes.get("attacked_unmitigated")
        mitigated = modes.get("rl_detector_mitigated")
        screened = modes.get("rl_detector_fdia_aware_screened")
        if not attacked:
            continue

        attacked_impact = as_float(attacked, "physical_impact_score")
        mitigated_impact = as_float(mitigated, "physical_impact_score") if mitigated else ""
        screened_impact = as_float(screened, "physical_impact_score") if screened else ""
        attacked_energy = as_float(attacked, "energy_ratio")
        clean_energy = attacked_energy - as_float(attacked, "energy_ratio_delta_vs_clean")
        mitigated_energy = as_float(mitigated, "energy_ratio") if mitigated else ""
        screened_energy = as_float(screened, "energy_ratio") if screened else ""
        denom = clean_energy - attacked_energy
        energy_recovery = ""
        if mitigated and abs(denom) > 1.0e-12:
            energy_recovery = (mitigated_energy - attacked_energy) / denom

        impact_reduction = ""
        if mitigated and attacked_impact > 1.0e-12:
            impact_reduction = (attacked_impact - mitigated_impact) / attacked_impact

        predicted = mitigated.get("rl_detector_attack", "") if mitigated else ""
        detector_counts[system]["samples"] += 1
        if predicted == attack:
            detector_counts[system]["correct"] += 1
        if attacked_impact > harmful_threshold and mitigated:
            recovery_by_system[system].append(float(impact_reduction))

        summary.append(
            {
                "system": system,
                "validation_seed": validation_seed,
                "scenario": scenario,
                "attack": attack,
                "clean_energy_ratio": fmt(clean_energy),
                "attacked_energy_ratio": fmt(attacked_energy),
                "mitigated_energy_ratio": fmt(mitigated_energy),
                "screened_energy_ratio": fmt(screened_energy),
                "attacked_impact_score": fmt(attacked_impact),
                "mitigated_impact_score": fmt(mitigated_impact),
                "screened_impact_score": fmt(screened_impact),
                "energy_recovery_fraction": fmt(energy_recovery),
                "impact_reduction_fraction": fmt(impact_reduction),
                "detector_expected": attack,
                "detector_predicted": predicted,
                "detector_correct": int(predicted == attack),
                "mitigation_applied": as_int(mitigated, "mitigation_applied") if mitigated else "",
                "screened_selected_candidate": screened.get("selected_candidate", "") if screened else "",
            }
        )

    detector_summary = []
    for system, counts in sorted(detector_counts.items()):
        samples = counts["samples"]
        correct = counts["correct"]
        recovery = recovery_by_system.get(system, [])
        accuracy_ci_low, accuracy_ci_high = wilson_ci(correct, samples)
        detector_summary.append(
            {
                "system": system,
                "samples": samples,
                "correct": correct,
                "accuracy": fmt(correct / samples if samples else 0.0),
                "accuracy_ci_low": fmt(accuracy_ci_low),
                "accuracy_ci_high": fmt(accuracy_ci_high),
                "harmful_recovery_samples": len(recovery),
                "mean_impact_reduction": fmt(float(np.mean(recovery)) if recovery else 0.0),
                "min_impact_reduction": fmt(min(recovery) if recovery else 0.0),
            }
        )
    return summary, detector_summary


def write_plain_csv(path, rows, fieldnames):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def plot_impact_distribution(rows, output_dir, filename="fig_robustness_impact_distribution.png", title="Robustness Validation: Impact Distribution"):
    if not rows:
        return
    systems = sorted({row["system"] for row in rows})
    data = [
        [as_float(row, "physical_impact_score") for row in rows if row["system"] == system]
        for system in systems
    ]
    fig, ax = plt.subplots(figsize=(7.0, 4.8))
    try:
        ax.boxplot(data, tick_labels=systems, showfliers=True)
    except TypeError:
        ax.boxplot(data, labels=systems, showfliers=True)
    ax.set_ylabel("Physical impact score")
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / filename, dpi=220)
    plt.close(fig)


def plot_harmful_rate(summary_rows, output_dir, filename="fig_robustness_harmful_rate.png", title="Harmful FDIA Rate Across Random Scenarios"):
    if not summary_rows:
        return
    systems = sorted({row["system"] for row in summary_rows})
    attacks = sorted({row["attack"] for row in summary_rows})
    x = np.arange(len(attacks))
    width = 0.8 / max(len(systems), 1)

    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    for index, system in enumerate(systems):
        values = []
        for attack in attacks:
            row = next((item for item in summary_rows if item["system"] == system and item["attack"] == attack), None)
            values.append(float(row["harmful_rate"]) if row else 0.0)
        ax.bar(x + index * width, values, width=width, label=system)
    ax.set_xticks(x + width * (len(systems) - 1) / 2)
    ax.set_xticklabels(attacks, rotation=25, ha="right")
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Harmful-case rate")
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_dir / filename, dpi=220)
    plt.close(fig)


def plot_recovery_summary(resilience_summary, output_dir, filename="fig_robustness_recovery.png", title="Robustness Validation: Mitigation Recovery on Top Cases"):
    harmful = [row for row in resilience_summary if float(row["attacked_impact_score"] or 0.0) > 1.0e-6]
    harmful = sorted(harmful, key=lambda row: float(row["attacked_impact_score"]), reverse=True)[:20]
    if not harmful:
        return

    labels = [f"{row['system']}\n{row['attack']}" for row in harmful]
    attacked = [float(row["attacked_impact_score"]) for row in harmful]
    mitigated = [float(row["mitigated_impact_score"]) for row in harmful]
    x = np.arange(len(harmful))
    width = 0.36

    fig, ax = plt.subplots(figsize=(12.0, 5.5))
    ax.bar(x - width / 2, attacked, width=width, label="Attacked", color="#c44e52")
    ax.bar(x + width / 2, mitigated, width=width, label="Mitigated", color="#55a868")
    ax.set_ylabel("Physical impact score")
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_dir / filename, dpi=220)
    plt.close(fig)


def write_markdown(
    output_dir,
    trial_summary,
    resilience_summary,
    detector_summary,
    filename="robustness_summary.md",
    title="FDIA Robustness Validation Summary",
    filter_report=None,
):
    top_cases = sorted(resilience_summary, key=lambda row: float(row["attacked_impact_score"] or 0.0), reverse=True)[:10]
    lines = [
        "# {}".format(title),
        "",
        "## Trial Statistics by System and Attack",
        "",
        "| System | Attack | Trials | Harmful Cases | Harmful Rate (95% CI) | Mean Impact (95% CI) | Max Impact |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in trial_summary:
        lines.append(
            "| {system} | {attack} | {trials} | {harmful_cases} | {harmful_rate} [{harmful_rate_ci_low}, {harmful_rate_ci_high}] | {mean_impact} [{mean_impact_ci_low}, {mean_impact_ci_high}] | {max_impact} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Top Recovery Cases",
            "",
            "| System | Seed | Scenario | Attack | Attacked Impact | Mitigated Impact | Impact Reduction |",
            "|---|---:|---|---|---:|---:|---:|",
        ]
    )
    for row in top_cases:
        lines.append(
            "| {system} | {validation_seed} | {scenario} | {attack} | {attacked_impact_score} | {mitigated_impact_score} | {impact_reduction_fraction} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## RL Detector and Recovery Summary",
            "",
            "| System | Samples | Correct | Accuracy (95% CI) | Harmful Recovery Samples | Mean Impact Reduction |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in detector_summary:
        lines.append(
            "| {system} | {samples} | {correct} | {accuracy} [{accuracy_ci_low}, {accuracy_ci_high}] | {harmful_recovery_samples} | {mean_impact_reduction} |".format(
                **row
            )
        )

    if filter_report:
        lines.extend(
            [
                "",
                "## Filter Accounting",
                "",
                "| Item | Count | Details |",
                "|---|---:|---|",
            ]
        )
        for row in filter_report:
            lines.append("| {item} | {count} | {details} |".format(**row))

    (output_dir / filename).write_text("\n".join(lines) + "\n")


def main():
    args = parse_args()
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_rows = []
    top_rows = []
    resilience_rows = []
    filtered_top_rows = []
    filtered_resilience_rows = []

    print("FDIA robustness/statistical validation")
    print("Systems: {} | seeds={} | trials_per_seed={} | top_k={}".format(
        args.systems,
        args.seeds,
        args.trials_per_seed,
        args.top_k,
    ))

    for system in args.systems:
        detector_path = resolve_detector_path(args.detector_template, system)
        if not detector_path.exists():
            raise FileNotFoundError("Missing detector model for {}: {}".format(system, detector_path))

        from stable_baselines3 import PPO

        experiment = RestorationExperiment(system)
        detector = PPO.load(str(detector_path))
        print("\nSystem {} | detector {}".format(system, detector_path))

        for validation_seed in args.seeds:
            rng = np.random.default_rng(validation_seed)
            seed_rows = []
            seed_contexts = {}
            print("  seed {}...".format(validation_seed))
            for trial_index in range(args.trials_per_seed):
                attack_name = str(rng.choice(args.attacks))
                scenario_seed = int(rng.integers(0, 2**31 - 1))
                attack_kwargs = strong_attack_kwargs(attack_name, rng)
                row, context = run_search_case(
                    experiment,
                    trial_index,
                    scenario_seed,
                    attack_name,
                    attack_kwargs,
                )
                row["validation_seed"] = validation_seed
                row["trial_index"] = trial_index
                row["search_system"] = system
                seed_rows.append(row)
                seed_contexts[row["scenario"]] = context

            ranked = sorted(seed_rows, key=lambda item: float(item["physical_impact_score"]), reverse=True)
            selected = ranked[: args.top_k]
            for rank, row in enumerate(selected, start=1):
                ranked_row = dict(row)
                ranked_row["top_rank"] = rank
                recovery_rows = resilience_rows_for_case(experiment, ranked_row, seed_contexts[row["scenario"]], detector)
                for recovery_row in recovery_rows:
                    recovery_row["validation_seed"] = validation_seed
                    recovery_row["top_rank"] = rank
                    resilience_rows.append(recovery_row)
                top_rows.append(ranked_row)

            ranked_filtered = [
                row for row in ranked
                if not filtered_exclusion_reason(row, args)
            ]
            selected_filtered = ranked_filtered[: args.top_k]
            for rank, row in enumerate(selected_filtered, start=1):
                ranked_row = dict(row)
                ranked_row["filtered_top_rank"] = rank
                recovery_rows = resilience_rows_for_case(experiment, ranked_row, seed_contexts[row["scenario"]], detector)
                for recovery_row in recovery_rows:
                    recovery_row["validation_seed"] = validation_seed
                    recovery_row["filtered_top_rank"] = rank
                    filtered_resilience_rows.append(recovery_row)
                filtered_top_rows.append(ranked_row)

            all_rows.extend(seed_rows)
            best = float(ranked[0]["physical_impact_score"]) if ranked else 0.0
            filtered_best = float(selected_filtered[0]["physical_impact_score"]) if selected_filtered else 0.0
            print("    trials={} best_impact={:.6f} filtered_best={:.6f}".format(len(seed_rows), best, filtered_best))

    trial_summary = summarize_trials(all_rows, args.harmful_threshold)
    resilience_summary, detector_summary = summarize_resilience(resilience_rows, args.harmful_threshold)
    filtered_trial_rows, excluded_counts = split_filtered_rows(all_rows, args)
    filtered_trial_summary = summarize_trials(filtered_trial_rows, args.harmful_threshold)
    filtered_resilience_summary, filtered_detector_summary = summarize_resilience(filtered_resilience_rows, args.harmful_threshold)
    filter_report = filter_report_rows(len(all_rows), len(filtered_trial_rows), excluded_counts, args)

    write_csv(all_rows, output_dir / "robustness_all_trials.csv")
    write_csv(top_rows, output_dir / "robustness_top_cases.csv")
    write_csv(resilience_rows, output_dir / "robustness_resilience_cases.csv")
    write_csv(filtered_top_rows, output_dir / "robustness_top_cases_filtered.csv")
    write_csv(filtered_resilience_rows, output_dir / "robustness_resilience_cases_filtered.csv")

    write_plain_csv(
        output_dir / "robustness_trial_summary.csv",
        trial_summary,
        [
            "system",
            "attack",
            "trials",
            "harmful_cases",
            "harmful_rate",
            "harmful_rate_ci_low",
            "harmful_rate_ci_high",
            "action_change_rate",
            "mean_impact",
            "mean_impact_ci_low",
            "mean_impact_ci_high",
            "std_impact",
            "max_impact",
            "mean_energy_loss",
            "max_energy_loss",
            "mean_reward_loss",
            "max_reward_loss",
        ],
    )
    write_plain_csv(
        output_dir / "robustness_trial_summary_filtered.csv",
        filtered_trial_summary,
        [
            "system",
            "attack",
            "trials",
            "harmful_cases",
            "harmful_rate",
            "harmful_rate_ci_low",
            "harmful_rate_ci_high",
            "action_change_rate",
            "mean_impact",
            "mean_impact_ci_low",
            "mean_impact_ci_high",
            "std_impact",
            "max_impact",
            "mean_energy_loss",
            "max_energy_loss",
            "mean_reward_loss",
            "max_reward_loss",
        ],
    )
    write_plain_csv(
        output_dir / "robustness_resilience_summary.csv",
        resilience_summary,
        [
            "system",
            "validation_seed",
            "scenario",
            "attack",
            "clean_energy_ratio",
            "attacked_energy_ratio",
            "mitigated_energy_ratio",
            "screened_energy_ratio",
            "attacked_impact_score",
            "mitigated_impact_score",
            "screened_impact_score",
            "energy_recovery_fraction",
            "impact_reduction_fraction",
            "detector_expected",
            "detector_predicted",
            "detector_correct",
            "mitigation_applied",
            "screened_selected_candidate",
        ],
    )
    write_plain_csv(
        output_dir / "robustness_resilience_summary_filtered.csv",
        filtered_resilience_summary,
        [
            "system",
            "validation_seed",
            "scenario",
            "attack",
            "clean_energy_ratio",
            "attacked_energy_ratio",
            "mitigated_energy_ratio",
            "screened_energy_ratio",
            "attacked_impact_score",
            "mitigated_impact_score",
            "screened_impact_score",
            "energy_recovery_fraction",
            "impact_reduction_fraction",
            "detector_expected",
            "detector_predicted",
            "detector_correct",
            "mitigation_applied",
            "screened_selected_candidate",
        ],
    )
    write_plain_csv(
        output_dir / "robustness_detector_summary.csv",
        detector_summary,
        [
            "system",
            "samples",
            "correct",
            "accuracy",
            "accuracy_ci_low",
            "accuracy_ci_high",
            "harmful_recovery_samples",
            "mean_impact_reduction",
            "min_impact_reduction",
        ],
    )
    write_plain_csv(
        output_dir / "robustness_detector_summary_filtered.csv",
        filtered_detector_summary,
        [
            "system",
            "samples",
            "correct",
            "accuracy",
            "accuracy_ci_low",
            "accuracy_ci_high",
            "harmful_recovery_samples",
            "mean_impact_reduction",
            "min_impact_reduction",
        ],
    )
    write_plain_csv(
        output_dir / "robustness_filter_report.csv",
        filter_report,
        ["item", "count", "details"],
    )

    plot_impact_distribution(all_rows, output_dir)
    plot_harmful_rate(trial_summary, output_dir)
    plot_recovery_summary(resilience_summary, output_dir)
    write_markdown(output_dir, trial_summary, resilience_summary, detector_summary)
    plot_impact_distribution(
        filtered_trial_rows,
        output_dir,
        filename="fig_robustness_impact_distribution_filtered.png",
        title="Filtered Robustness Validation: Impact Distribution",
    )
    plot_harmful_rate(
        filtered_trial_summary,
        output_dir,
        filename="fig_robustness_harmful_rate_filtered.png",
        title="Filtered Harmful FDIA Rate Across Random Scenarios",
    )
    plot_recovery_summary(
        filtered_resilience_summary,
        output_dir,
        filename="fig_robustness_recovery_filtered.png",
        title="Filtered Robustness Validation: Mitigation Recovery on Top Cases",
    )
    write_markdown(
        output_dir,
        filtered_trial_summary,
        filtered_resilience_summary,
        filtered_detector_summary,
        filename="robustness_summary_filtered.md",
        title="FDIA Robustness Validation Summary - Filtered Paper-Ready Set",
        filter_report=filter_report,
    )

    print("\nSaved robustness outputs in: {}".format(output_dir))
    print("Trials: {}".format(len(all_rows)))
    print("Filtered trials: {}".format(len(filtered_trial_rows)))
    print("Top cases: {}".format(len(top_rows)))
    print("Filtered top cases: {}".format(len(filtered_top_rows)))
    print("Resilience rows: {}".format(len(resilience_rows)))
    print("Filtered resilience rows: {}".format(len(filtered_resilience_rows)))


if __name__ == "__main__":
    main()
