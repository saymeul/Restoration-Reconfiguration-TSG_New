from typing import Any, Dict, List, Optional, Tuple, Type, Union

import gym
import torch as th
from gym import spaces
from stable_baselines3.common.distributions import (
    BernoulliDistribution,
    CategoricalDistribution,
    DiagGaussianDistribution,
    Distribution,
    MultiCategoricalDistribution,
    StateDependentNoiseDistribution,
)
from stable_baselines3.common.policies import BasePolicy
from stable_baselines3.common.preprocessing import get_action_dim
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor, FlattenExtractor, MlpExtractor
from stable_baselines3.common.type_aliases import Schedule

from Policies.bus_8500.Feature_Extractor import CustomGNN


class ActorCriticGCAPSPolicy(BasePolicy):
    def __init__(
        self,
        observation_space: gym.spaces.Space,
        action_space: gym.spaces.Space,
        lr_schedule: Schedule,
        net_arch: Optional[List[Union[int, Dict[str, List[int]]]]] = None,
        activation_fn: Type[th.nn.Module] = th.nn.Tanh,
        ortho_init: bool = True,
        use_sde: bool = False,
        log_std_init: float = 0.0,
        full_std: bool = True,
        sde_net_arch: Optional[List[int]] = None,
        use_expln: bool = False,
        squash_output: bool = False,
        features_extractor_class: Type[BaseFeaturesExtractor] = FlattenExtractor,
        features_extractor_kwargs: Optional[Dict[str, Any]] = None,
        optimizer_class: Type[th.optim.Optimizer] = th.optim.Adam,
        optimizer_kwargs: Optional[Dict[str, Any]] = None,
        device: Union[th.device, str] = "cpu",
    ):
        super(ActorCriticGCAPSPolicy, self).__init__(
            observation_space,
            action_space,
            features_extractor_class,
            features_extractor_kwargs,
            optimizer_class=optimizer_class,
            optimizer_kwargs=optimizer_kwargs,
            squash_output=squash_output,
        )
        features_extractor_kwargs = features_extractor_kwargs or {}
        features_dim = features_extractor_kwargs["features_dim"]
        node_dim = features_extractor_kwargs["node_dim"]
        self.node_dim = node_dim
        self.value_net = th.nn.Sequential(
            th.nn.Linear(features_dim, 2 * features_dim, bias=True),
            th.nn.Linear(2 * features_dim, 2 * features_dim, bias=True),
            th.nn.Linear(2 * features_dim, 1, bias=True),
        ).to(device=device)
        self.features_extractor = CustomGNN(
            node_dim=node_dim,
            features_dim=features_dim,
            observation_space=observation_space,
        )
        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)
        self.action_dist = make_proba_distribution(action_space, use_sde=use_sde)
        self.net_arch = net_arch
        self.activation_fn = activation_fn
        self.action_net = self.action_dist.proba_distribution_net(latent_dim=features_dim)
        self.mlp_extractor = MlpExtractor(
            features_dim,
            net_arch=self.net_arch,
            activation_fn=self.activation_fn,
            device=self.device,
        )

    def forward(self, obs: th.Tensor, deterministic: bool = True) -> Tuple[th.Tensor, th.Tensor, th.Tensor]:
        features = self.extract_features(obs)
        latent_pi, latent_vf = self.mlp_extractor(features)
        values = self.value_net(latent_vf)
        distribution = self._get_action_dist_from_latent(latent_pi, obs)
        actions = distribution.get_actions(deterministic=True)
        log_prob = distribution.log_prob(actions)
        actions = actions.reshape((-1,) + self.action_space.shape)
        return actions, values, log_prob

    def evaluate_actions(self, obs: th.Tensor, actions: th.Tensor) -> Tuple[th.Tensor, th.Tensor, th.Tensor]:
        features = self.extract_features(obs)
        latent_pi, latent_vf = self.mlp_extractor(features)
        distribution = self._get_action_dist_from_latent(latent_pi, obs)
        log_prob = distribution.log_prob(actions)
        values = self.value_net(latent_vf)
        return values, log_prob, distribution.entropy()

    def _predict(self, observation: th.Tensor, deterministic: bool = True) -> th.Tensor:
        actions, _values, _log_prob = self.forward(observation, deterministic=deterministic)
        return th.tensor([actions])

    def predict_values(self, obs: th.Tensor) -> th.Tensor:
        features = self.extract_features(obs)
        latent_vf = self.mlp_extractor.forward_critic(features)
        return self.value_net(latent_vf)

    def _get_action_dist_from_latent(self, latent_pi: th.Tensor, obs) -> Distribution:
        mean_actions = self.action_net(latent_pi)
        action_mask = obs["ActionMasking"].to(th.bool)
        mean_actions[action_mask] += -1000000 * mean_actions[action_mask].abs()
        if isinstance(self.action_dist, DiagGaussianDistribution):
            return self.action_dist.proba_distribution(mean_actions, self.log_std)
        if isinstance(self.action_dist, CategoricalDistribution):
            return self.action_dist.proba_distribution(action_logits=mean_actions)
        if isinstance(self.action_dist, MultiCategoricalDistribution):
            return self.action_dist.proba_distribution(action_logits=mean_actions)
        if isinstance(self.action_dist, BernoulliDistribution):
            return self.action_dist.proba_distribution(action_logits=mean_actions)
        if isinstance(self.action_dist, StateDependentNoiseDistribution):
            return self.action_dist.proba_distribution(mean_actions, self.log_std)
        raise ValueError("Invalid action distribution")


def make_proba_distribution(
    action_space: gym.spaces.Space,
    use_sde: bool = False,
    dist_kwargs: Optional[Dict[str, Any]] = None,
) -> Distribution:
    dist_kwargs = dist_kwargs or {}
    if isinstance(action_space, spaces.Box):
        cls = StateDependentNoiseDistribution if use_sde else DiagGaussianDistribution
        return cls(get_action_dim(action_space), **dist_kwargs)
    if isinstance(action_space, spaces.Discrete):
        return CategoricalDistribution(action_space.n, **dist_kwargs)
    if isinstance(action_space, spaces.MultiDiscrete):
        return MultiCategoricalDistribution(action_space.nvec, **dist_kwargs)
    if isinstance(action_space, spaces.MultiBinary):
        return BernoulliDistribution(action_space.n, **dist_kwargs)
    raise NotImplementedError("Unsupported action space type {}".format(type(action_space)))
