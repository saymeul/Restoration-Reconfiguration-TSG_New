import logging
import math
import os
import random
from random import sample

import gym
import networkx as nx
import numpy as np
from gym import spaces
from gym.utils import seeding

try:
    from .DSS_Initialize import *
    from .state_action_reward import get_reward, get_state, take_action
except ImportError:
    from DSS_Initialize import *
    from state_action_reward import get_reward, get_state, take_action


logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", level=logging.WARNING)


class DSS_OutCtrl_Env(gym.Env):
    metadata = {"render.modes": ["human"]}

    def __init__(self):
        print("Initializing IEEE 8500 env from PowerBench OpenDSS data")
        self.DSSCktObj, graph, conv_flag = initialize()
        self.outedges = []
        self.G = graph.copy()
        self.max_reset_radius = int(os.environ.get("TSG_IEEE8500_RESET_RADIUS", "4"))
        self.max_reset_outage_edges = int(os.environ.get("TSG_IEEE8500_RESET_MAX_OUTAGE_EDGES", "25"))
        self.action_space = spaces.MultiBinary(n_actions)
        self.observation_space = spaces.Dict(
            {
                "EnergySupp": spaces.Box(low=0, high=2, shape=(1,)),
                "NodeFeat(BusVoltage)": spaces.Box(low=0, high=2, shape=(len(G_init.nodes()), 3)),
                "EdgeFeat(Branchflow)": spaces.Box(low=0, high=np.inf, shape=(len(G_init.edges()),)),
                "Adjacency": spaces.Box(low=0, high=1, shape=(len(G_init.nodes()), len(G_init.nodes()))),
                "VoltageViolation": spaces.Box(low=0, high=1000, shape=(1,)),
                "ConvergenceViolation": spaces.Box(low=0, high=10, shape=(1,)),
                "ActionMasking": spaces.Box(low=0, high=1, shape=(n_actions,)),
            }
        )
        print(
            "IEEE 8500 env initialized: nodes={} edges={} switches={} dispatch_loads={}".format(
                len(G_init.nodes()),
                len(G_init.edges()),
                len(AllSwitches),
                len(dispatch_loads),
            )
        )

    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        random.seed(seed)
        np.random.seed(seed % (2**32 - 1))
        return [seed]

    def step(self, action):
        try:
            self.DSSCktObj, self.G = take_action(action, self.outedges)
            obs_post_action = get_state(self.DSSCktObj, self.G, self.outedges)
            reward = get_reward(obs_post_action)
        except Exception as exc:
            logging.warning("IEEE 8500 step failed: %s", exc)
            obs_post_action = get_state(self.DSSCktObj, self.G, self.outedges)
            reward = np.asarray([0.0])
        done = True
        info = {"is_success": done, "episode": {"r": reward, "l": 1}}
        return obs_post_action, float(np.asarray(reward).reshape(-1)[0]), done, info

    def _sample_outage_edges(self):
        nodes = [node for node in G_init.nodes() if G_init.degree(node) > 0]
        if not nodes:
            return []
        root = random.choice(nodes)
        radius = max(1, random.randint(1, max(1, self.max_reset_radius)))
        subgraph = nx.ego_graph(G_base, root, radius=radius, undirected=False)
        sub_edges = list(subgraph.edges())
        if not sub_edges:
            return []
        outage_fraction = random.uniform(0.0, 0.50)
        outage_count = max(1, int(math.ceil(len(sub_edges) * outage_fraction)))
        if self.max_reset_outage_edges > 0:
            outage_count = min(outage_count, self.max_reset_outage_edges)
        outage_count = min(outage_count, len(sub_edges))
        return sample(sub_edges, k=outage_count)

    def reset(self):
        logging.info("resetting IEEE 8500 environment")
        self.DSSCktObj, graph, conv_flag = initialize()
        self.G = graph.copy()
        out_edges = self._sample_outage_edges()
        for outage_edge in out_edges:
            try:
                branch_name = graph.edges[outage_edge]["label"][0]
                self.DSSCktObj.dss.Text.Command("Open {} term=1".format(branch_name))
                self.DSSCktObj.dss.Solution.Solve()
            except Exception:
                continue
        self.G.remove_edges_from(out_edges)
        self.outedges = out_edges
        obs = get_state(self.DSSCktObj, self.G, self.outedges)
        if np.isnan(obs["EdgeFeat(Branchflow)"]).sum() > 0 or obs["NodeFeat(BusVoltage)"].max() > 100000:
            return self.reset()
        return obs

    def test_func1(self):
        return self.reset()

    def test_func2(self):
        return self.reset()

    def render(self, mode="human", close=False):
        pass
