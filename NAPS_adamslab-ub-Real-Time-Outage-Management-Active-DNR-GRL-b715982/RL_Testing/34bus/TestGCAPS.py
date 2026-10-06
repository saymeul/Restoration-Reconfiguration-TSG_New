
"""
In this file the testing for the GCAPs for 34 bus network is performed
GCAPS results can be reproduced here.
"""

import numpy as np
import gym
from stable_baselines3 import PPO
import torch
from stable_baselines3 import A2C, PPO
from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback

from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
import pickle
from stable_baselines3.common.utils import set_random_seed

from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
from DSS_Initialize import *
from DSS_OutCtrl_Env import DSS_OutCtrl_Env
from Policies.bus_34.Feature_Extractor import CustomGNN
from Policies.bus_34.CustomPolicies import ActorCriticGCAPSPolicy
# if __name__ == '__main__':


env = DSS_OutCtrl_Env()
model = PPO.load(r"TrainedModels/GCAPS_34.zip", env=env)

#----Test Scenario 1---------------------------------------------
obs1 = env.test_func1()
obs1 = {key: torch.as_tensor([_obs]) for (key, _obs) in obs1.items()}

action1, values1, log_probs1 = model.policy.forward(obs1)
new_obs1 = env.step(action1[0,:])

Num_Switches = 9
decisions1 = action1[0,:].tolist()
switching1 = [int(_a) for _a in decisions1[:Num_Switches]]
loadctrl1 =  [int(_a) for _a in decisions1[Num_Switches:]]

loadstatus1 = {}
for d in dispatch_loads:
    indx = dispatch_loads.index(d)
    loadstatus1[d] = loadctrl1[indx]

print('Switching for scenario 1:')
print(switching1)
print('Load status:')
print(loadstatus1)
#--------------------------------------------------------

# #-----Test Scenario 2---------------------------------------------
# obs2 = env.test_func2()
# obs2 = {key: torch.as_tensor([_obs]) for (key, _obs) in obs2.items()}

# action2, values2, log_probs2 = model.policy.forward(obs2)
# new_obs2 = env.step(action2[0,:])

# Num_Switches = 9
# decisions2 = action2[0,:].tolist()
# switching2 = [int(_a) for _a in decisions2[:Num_Switches]]
# loadctrl2 =  [int(_a) for _a in decisions2[Num_Switches:]]

# loadstatus2 = {}
# for d in dispatch_loads:
#     indx = dispatch_loads.index(d)
#     loadstatus2[d] = loadctrl2[indx]
# print('Switching for scenario 2:')
# print(switching2)
# print('Load status:')
# print(loadstatus2)
#------------------------------------------------------------------------






