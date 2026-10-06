import gym
import torch
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor


class CustomGNN(BaseFeaturesExtractor):
    """GCAPS-style feature extractor with dimensions inferred from the feeder."""

    def __init__(
        self,
        observation_space: gym.spaces.Box,
        features_dim: int = 256,
        n_layers=2,
        n_dim=256,
        n_p=3,
        node_dim=3,
        n_K=2,
    ):
        super(CustomGNN, self).__init__(observation_space, features_dim)
        node_count = int(observation_space["NodeFeat(BusVoltage)"].shape[0])
        edge_count = int(observation_space["EdgeFeat(Branchflow)"].shape[0])
        context_dim = 2 + edge_count

        self.n_layers = n_layers
        self.n_dim = n_dim
        self.n_p = n_p
        self.n_K = n_K
        self.node_dim = node_dim
        self.init_embed = torch.nn.Linear(node_dim, n_dim * n_p)
        self.W_L_1_G1 = torch.nn.Linear(n_dim * (n_K + 1) * n_p, n_dim)
        self.W_L_1_G2 = torch.nn.Linear(n_dim * (n_K + 1) * n_p, n_dim)
        self.W_L_1_G3 = torch.nn.Linear(n_dim * (n_K + 1) * n_p, n_dim)
        self.W_F = torch.nn.Linear(n_dim * n_p, features_dim)
        self.full_context_nn = torch.nn.Sequential(
            torch.nn.Linear(context_dim, 2 * features_dim),
            torch.nn.LeakyReLU(),
            torch.nn.Linear(2 * features_dim, features_dim),
        )
        self.switch_encoder = torch.nn.Sequential(
            torch.nn.Linear(node_count, 2 * features_dim),
            torch.nn.LeakyReLU(),
            torch.nn.Linear(2 * features_dim, features_dim),
        )
        self.final_encoder = torch.nn.Sequential(
            torch.nn.Linear(2 * features_dim, 4 * features_dim),
            torch.nn.LeakyReLU(),
            torch.nn.Linear(4 * features_dim, features_dim),
        )

    def forward(self, data):
        x = data["NodeFeat(BusVoltage)"]
        num_samples, num_locations, _unused = x.size()
        adjacency = data["Adjacency"]
        eye = torch.eye(num_locations, device=adjacency.device).expand(
            (num_samples, num_locations, num_locations)
        )
        degree = torch.mul(
            eye,
            adjacency.sum(-1)[:, None].expand((num_samples, num_locations, num_locations)),
        )
        laplacian = degree - adjacency
        laplacian_squared = torch.matmul(laplacian, laplacian)

        f0 = self.init_embed(x)
        filter_input = torch.cat(
            (
                f0,
                torch.matmul(laplacian, f0),
                torch.matmul(laplacian_squared, f0),
            ),
            -1,
        )
        f1 = torch.cat(
            (
                self.W_L_1_G1(filter_input),
                self.W_L_1_G2(filter_input),
                self.W_L_1_G3(filter_input),
            ),
            -1,
        )
        node_embeddings = self.W_F(f1)
        switch_embeddings = self.switch_encoder(node_embeddings.permute(0, 2, 1))
        context = self.full_context_nn(
            torch.cat(
                (
                    data["EnergySupp"],
                    data["VoltageViolation"],
                    data["EdgeFeat(Branchflow)"],
                ),
                -1,
            )
        )
        return self.final_encoder(torch.cat((switch_embeddings.mean(dim=1), context), dim=-1))
