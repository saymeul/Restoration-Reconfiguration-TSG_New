# Integrity Audit: Integrated-Profile Targeted IEEE 34-Bus FDIA Results

This folder contains the rerun with voltage and energy profile logging integrated
into the same selected-case clean/attacked trajectory generation used for the
impact rows.

## Main Result Folder

`targeted_dynamic_no_mitigation_profile_logged`

## Clean/Usable Outputs

The following files are internally consistent and can be used together:

- `targeted_attack_search_34bus.csv`
- `targeted_selected_cases_34bus.csv`
- `targeted_method_comparison_34bus.csv`
- `table_targeted_method_summary_34bus.csv`
- `table_targeted_detection_summary_34bus.csv`
- `profile_voltage_bus_phase_34bus.csv`
- `profile_energy_served_34bus.csv`
- `table_voltage_profile_summary_34bus.csv`
- `table_energy_served_by_method_34bus.csv`
- `fig_energy_served_kwh_attacked_34bus.png`

## Audit Checks Passed

- Selected-case mean impacts match the replayed comparison rows.
- `targeted_method_comparison_34bus.csv` has no non-finite values, negative
  energy, out-of-bound energy ratios, excessive impact scores, or convergence
  violations in the selected replay rows.
- `profile_voltage_bus_phase_34bus.csv` is generated from the same observations
  used to create the selected replay metrics.
- Voltage profile min/max values match `targeted_method_comparison_34bus.csv`
  exactly for all selected case/mode/time-step combinations.
- `profile_energy_served_34bus.csv` energy values match
  `targeted_method_comparison_34bus.csv` exactly.

## Search-Stage Invalid Rows

Some random search trials produced invalid OpenDSS/numerical behavior,
especially in BPSO candidate cases. These were filtered out by the paper-valid
selection criteria and are not part of the selected comparison or summary
tables.

## Methodology Condition

This is a targeted topology/status FDIA experiment. It is not the earlier strict
measurement-only FDIA experiment.

Selected cases use:

- base `topology_drop` observation corruption, and
- false topology/status projection into the decision feasibility/action
  availability channel.

This is recorded as:

- `attack_surface = observation_plus_decision_channel`
- `decision_channel_projection = false_topology_status_to_action_mask`

## MLP Condition

MLP impact is caused by corrupted DMS feasibility/status filtering. The raw MLP
policy action does not change under the targeted selected cases:

- raw policy action changed rate: `0`
- final dispatched action changed rate: `1`

The paper must state this clearly.

## BPSO Condition

BPSO impact is caused by corrupted perceived decision/optimization inputs,
especially topology/status/action availability information. This is a different
threat model from strict observation-only BPSO evaluation.

