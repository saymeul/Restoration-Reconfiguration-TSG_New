# Real-Time Outage Management in Active Distribution Networks Using Reinforcement Learning over Graphs

## Contents

- [Overview](#overview)
- [Reinforcement Learning Training](#repo-contents)
- [Testing](#system-requirements)
- [Demo](#demo)


# Overview

Self-healing "smart grids" are characterized by fast-acting, intelligent control mechanisms that minimize power disruptions during outages. The corrective actions adopted during outages in power distribution networks include reconfiguration through switching control and emergency load shedding. The conventional decision-making models for outage mitigation are, however, not suitable for "smart grids" due to their slow response and computational inefficiency. Here, we present a new reinforcement learning (RL) model for outage management in the distribution network to enhance its resilience. The distinctive characteristic of our approach is that it explicitly accounts for the underlying network topology and its variations with switching control, while also capturing the complex interdependencies between state variables (along nodes and edges) by modeling the task as a graph learning problem. Our model learns the  optimal control policy for power restoration using a Capsule-based graph neural network. We validate our model on two test networks, namely the 13, 34 and 123-bus modified IEEE networks where it is shown to achieve near-optimal, real-time performance. 


# Reinforcement Learning Training

## System Requirements

### Hardware Requirements
Intel Xeon Gold 6330 CPU (28 cores) with 512GB RAM and an NVIDIA A100 GPU

### Software Requirements
The training has been performed on Linux, with Python 3.9.12. The required python packages were installed using Anaconda. The required packages can be found in the file requirements.txt.

#### OS Requirements

CentOS Linux release 7.9.2009
Linux kernel version: 3.10.0-1160.66.1.el7.x86_64

#### Installing Anaconda on Linux

```# Download Anaconda (replace <version> with the desired version)
curl -O https://repo.anaconda.com/archive/Anaconda3-<version>-Linux-x86_64.sh

# Run the installer (replace <version> with the downloaded version)
bash Anaconda3-<version>-Linux-x86_64.sh

# Activate Anaconda (you may need to restart your terminal or run source ~/.bashrc)
source ~/.bashrc

# Verify installation
conda --version
```

#### Installing the required packages
All the python packages along with their versions can be found in the file requirements.txt. These packages can be installed using the following command:
```pip install -r requirements.txt```

This should be installed in about 5 minutes.


# Testing
## System Requirements

### Hardware 
Intel Core i7-1365U, 1800 Mhz with 16GB RAM.


### Software Requirements
The testing has been performed on Windows, with Python 3.9.12. The required python packages (in file requirements.txt) were installed using Anaconda. 

#### OS Requirements
Microsoft Windows Version 22H2 (OS Build 22621.2715)


# Demo

## RL Training

The RL training is performed by running the train.py (```python train.py```) file. First thing to do is to set the network size (13, 34, or 123), inside the main function in train.py. The policy network, and other hyperparameters for training can be set inside the training_config.py file (inside the Configs directory).
The approximate time to train a 13 bus network for 2 million steps is around 36 hours, however could vary.

The trained models can be accessed from the directory "Trained_Models". The logs for training can be found in the generated directory "Tensorboard_logger".

The policies corresponding to the three networks (13, 34, and 123) can be found in the directory "Policies" inside "RL_Training".

## RL Testing

For testing the trained RL model on different networks go to the specific network folder and run the ```TestGCAPS.py```(for GCAPS) and ```TestMLP.py```(for MLP) files.
A separate README file is present in each network folder for instruction in addition to the trained RL models and the test environments.
The ```EvaluateCircuit.py``` file can be used to evaluate the RL solution on the network and assess the impact on energy supplied, voltage, etc.

The test scenarios and the solutions reported in the manuscript have been provided in these files already. For varying the selection (method or scenario) simply comment out the rest and uncomment the specific scenario and method.

The TestGCAPS and TestMLP files will provide the switching and load statuses and EvaluateCircuit file will use this solution on the network to evaluate the energy supplied and voltage violation.

Run time for these files are in the order of seconds.