# Table 4. IEEE 34 Coordinated Attack Ranking

| damage_rank | attack_id | target_observation_id | case_count | mean_degradation_kwh | max_degradation_kwh | damaging_cases | detection_rate_pct | bypass_rate_pct | mitigation_recovery_pct | mean_load_changes | mean_switch_changes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | dispatch_s890_branchflow_l8_voltage_816 | action_mask.Load_s890;branchflow.Line.l8;bus_voltage.816 | 30 | 3080.849 | 9115.475 | 17 | 100.000 | 0.000 | 94.118 | 1.300 | 0.033 |
| 2 | dispatch_s890_voltage_816 | action_mask.Load_s890;bus_voltage.816 | 30 | 3080.849 | 9115.475 | 17 | 100.000 | 0.000 | 94.118 | 1.300 | 0.033 |
| 3 | hidden_l28_voltage_816_dispatch_s890 | topology_edge.Line.l28;bus_voltage.816;action_mask.Load_s890 | 30 | 3080.849 | 9115.475 | 17 | 100.000 | 0.000 | 94.118 | 1.367 | 0.000 |
| 4 | dispatch_s890_line_l8_voltage_816 | action_mask.Load_s890;topology_edge.Line.l8;bus_voltage.816 | 30 | 3065.622 | 9124.530 | 17 | 100.000 | 0.000 | 94.118 | 1.433 | 0.133 |
| 5 | dispatch_s890_switch_swtie4 | action_mask.Load_s890;action_mask.swtie4 | 30 | 3009.214 | 8808.308 | 14 | 100.000 | 0.000 | 100.000 | 1.000 | 0.767 |
| 6 | dispatch_s844_switch_swtie1 | action_mask.Load_s844;action_mask.swtie1 | 30 | 1641.454 | 8667.718 | 12 | 100.000 | 0.000 | 100.000 | 1.000 | 1.000 |
| 7 | dispatch_s844_voltage_852 | action_mask.Load_s844;bus_voltage.852 | 30 | 1639.677 | 8663.260 | 17 | 100.000 | 0.000 | 100.000 | 1.067 | 0.000 |
| 8 | switch_swtie4_line_l8_voltage_816 | action_mask.swtie4;topology_edge.Line.l8;bus_voltage.816 | 30 | 83.651 | 419.903 | 9 | 100.000 | 0.000 | 100.000 | 0.433 | 0.900 |
| 9 | hidden_l30_switch_swtie4 | topology_edge.Line.l30;action_mask.swtie4 | 30 | 72.474 | 434.266 | 9 | 100.000 | 0.000 | 100.000 | 0.100 | 0.800 |
| 10 | line_l8_line_824848_voltage_816 | topology_edge.Line.l8;topology_edge.Line.824848;bus_voltage.816 | 30 | 49.150 | 419.903 | 5 | 100.000 | 0.000 | 100.000 | 0.567 | 0.233 |
