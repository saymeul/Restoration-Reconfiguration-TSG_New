"""
Train the RL-based FDIA detector agent.

This agent is separate from the GCAPS restoration controller. It learns to map
FDIA residual features to a detection/channel action, then the testing pipeline
uses that action to trigger mitigation before GCAPS restoration.
"""

import argparse
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Train RL FDIA detector")
    parser.add_argument("--system", default="13bus", choices=["13bus", "34bus", "123bus"])
    parser.add_argument("--scenarios", nargs="+", default=["SC1", "SC2", "random"], choices=["SC1", "SC2", "random"])
    parser.add_argument(
        "--attacks",
        nargs="+",
        default=["clean", "voltage_masking", "branchflow_hiding", "energy_inflation", "topology_drop"],
        choices=["clean", "voltage_masking", "branchflow_hiding", "energy_inflation", "topology_drop"],
    )
    parser.add_argument("--total-steps", type=int, default=100000)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--n-steps", type=int, default=2048)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--gamma", type=float, default=0.95)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--save-dir", default="Trained_Models/FDIA_Detectors")
    parser.add_argument("--save-freq", type=int, default=25000)
    parser.add_argument("--disable-tensorboard", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import CheckpointCallback

    from Environments.FDIA_Detection.FDIA_Detection_Env import FDIADetectionEnv

    save_dir = Path(args.save_dir).resolve()
    save_dir.mkdir(parents=True, exist_ok=True)

    env = FDIADetectionEnv(
        system=args.system,
        scenarios=args.scenarios,
        attacks=args.attacks,
        seed=args.seed,
    )

    tensorboard_log = None if args.disable_tensorboard else str(Path("Tensorboard_logger") / "FDIA_Detector")
    checkpoint_callback = CheckpointCallback(
        save_freq=args.save_freq,
        save_path=str(save_dir),
        name_prefix="RLFDIA_{}".format(args.system),
    )

    model = PPO(
        policy="MlpPolicy",
        env=env,
        verbose=1,
        learning_rate=args.learning_rate,
        n_steps=args.n_steps,
        batch_size=args.batch_size,
        gamma=args.gamma,
        tensorboard_log=tensorboard_log,
        seed=args.seed,
    )
    model.learn(total_timesteps=args.total_steps, callback=checkpoint_callback)

    final_path = save_dir / "RLFDIA_{}_final".format(args.system)
    model.save(str(final_path))
    print("Saved RL FDIA detector: {}.zip".format(final_path))


if __name__ == "__main__":
    main()
