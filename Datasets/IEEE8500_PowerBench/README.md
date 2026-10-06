# IEEE 8500 PowerBench Staging Package

This folder stages the IEEE 8500 material imported from PowerBench for extending the IEEE 34-bus and IEEE 123-bus FDIA/restoration workflow to the IEEE 8500-node feeder.

Source repository: https://github.com/RoshniAnna/PowerBench  
Imported branch: `main`  
Imported commit: `f1db8d8c151f6685767087e57e12b46a3253048b`

## Contents

- `source/PowerBench/Datasets/State Estimation/8500 Node/`
  - Recommended clean base IEEE 8500 OpenDSS feeder source.
  - Contains `Master.dss`, feeder component `.dss` files, sensor pickles, `GraphBuild.py`, `DSSCircuit_Interface.py`, and `DataGeneration.py`.
- `source/PowerBench/Datasets/Line Failure Detection/8500-bus/`
  - IEEE 8500 line-outage scenario generation source.
  - Useful for adapting outage-case construction and line-failure sampling.
- `source/PowerBench/Datasets/Cyber Attack Detection/Sensor Attacks/8500-Node/`
  - IEEE 8500 voltage-sensor attack generation source with SLURM-array support.
- `source/PowerBench/Datasets/Cyber Attack Detection/PV Attacks/8500-Node/`
  - IEEE 8500 PV attack source and PV/loadshape inputs.
- `source/PowerBench/Datasets/Cyber Attack Detection/EVCS Attacks/8500-bus/`
  - IEEE 8500 EV charging station attack source and charger input data.
- `powerbench_ieee8500_import_manifest.csv`
  - Per-file source path, raw source URL, local path, byte size, and commit SHA.

## Recommended Starting Point

Use the clean base feeder first:

`source/PowerBench/Datasets/State Estimation/8500 Node/Master.dss`

That master file defines `Circuit.IEEE8500` and redirects the main feeder files:

- `LineCodes2.dss`
- `Triplex_Linecodes.dss`
- `Lines.dss`
- `Transformers.dss`
- `LoadXfmrs.dss`
- `Triplex_Lines.dss`
- `Loads.dss`
- `Capacitors.dss`
- `CapControls.dss`
- `Regulators.dss`
- `Buscoords.dss`

## Before HPC Simulation

The imported PowerBench files provide the IEEE 8500 feeder model and related data-generation examples. To reproduce the IEEE 34/123 study pattern on IEEE 8500, the next integration steps are:

1. Compile the IEEE 8500 `Master.dss` locally with `opendssdirect.py`.
2. Build the IEEE 8500 observation registry: bus voltages, branch flows, line/switch/topology status, loads/energy, and action masks.
3. Define the restoration action space for IEEE 8500 switches, controllable loads, and any DER/EV/PV controls included in scope.
4. Create small smoke-test outage cases before launching full batches.
5. Port the existing IEEE 34/123 FDIA families and mitigation variants to the IEEE 8500 observation/action registry.
6. Split target scans into HPC array jobs and write outputs under a new paper-results namespace, for example `paper_results/tsg_ieee8500/`.

Keep GRL as the main controller evidence first. MLP and BPSO can be added as companion packages after the IEEE 8500 base environment, outage cases, action mask, and result manifests are stable.
