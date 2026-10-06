# Table 3. IEEE 34 Critical Observations

| evidence_family | attack_definition | target_observation_id | target_component_name | case_count | attack_applied_count | mean_degradation_kwh | max_degradation_kwh | damaging_cases | detection_rate_pct | action_changed_rate_pct | mitigation_recovery_pct | paper_note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| load-control action mask | false unavailable dispatch-load action | action_mask.Load_s890 | Load.s890 | 30 | 30 | 3038.190 | 8832.380 | 16 | 100.000 | 100.000 | 93.750 | Direct current-GRL load-status/control observation. |
| load-control action mask | false unavailable dispatch-load action | action_mask.Load_s844 | Load.s844 | 30 | 30 | 1627.701 | 8663.260 | 16 | 100.000 | 100.000 | 100.000 | Direct current-GRL load-status/control observation. |
| line status/topology | false closed hidden-outage adjacency | topology_edge.Line.l30 | Line.l30 | 1 | 1 | 169.566 | 169.566 | 1 | 100.000 | 100.000 | 0.000 | Direct topology/status observation; executable cases are sparse. |
| line status/topology | false closed hidden-outage adjacency | topology_edge.Line.l28 | Line.l28 | 2 | 2 | 131.945 | 192.747 | 2 | 100.000 | 100.000 | 100.000 | Direct topology/status observation; executable cases are sparse. |
| load-control action mask | false unavailable dispatch-load action | action_mask.Load_d818_820sa | Load.d818_820sa | 30 | 30 | 99.597 | 377.610 | 9 | 100.000 | 36.667 | 100.000 | Direct current-GRL load-status/control observation. |
| line status/topology | false closed hidden-outage adjacency | topology_edge.Line.l18 | Line.l18 | 2 | 2 | 96.374 | 192.747 | 1 | 100.000 | 50.000 | 100.000 | Direct topology/status observation; executable cases are sparse. |
| switch action mask | false unavailable switch action | action_mask.swtie4 | swtie4 | 30 | 30 | 67.253 | 296.908 | 9 | 100.000 | 76.667 | 100.000 | Direct current-GRL switch-status/action availability observation. |
| bus voltage | false low voltage measurement | bus_voltage.816 | 816 | 20 | 20 | 64.222 | 419.903 | 4 | 100.000 | 30.000 | 75.000 | Direct measurement observation. |
| line status/topology | false open line-status adjacency | topology_edge.Line.l8 | Line.l8 | 27 | 27 | 44.559 | 419.903 | 3 | 100.000 | 40.741 | 100.000 | Direct topology/status observation. |
| line status/topology | false open line-status adjacency | topology_edge.Line.824848 | Line.824848 | 30 | 30 | 39.277 | 419.903 | 7 | 100.000 | 50.000 | 85.714 | Direct topology/status observation. |
| bus voltage | false low voltage measurement | bus_voltage.852 | 852 | 11 | 11 | 33.107 | 364.175 | 1 | 100.000 | 18.182 | 100.000 | Direct measurement observation. |
| load-control action mask | false unavailable dispatch-load action | action_mask.Load_d808_810sb | Load.d808_810sb | 30 | 30 | 32.730 | 172.397 | 6 | 100.000 | 36.667 | 100.000 | Direct current-GRL load-status/control observation. |
| bus voltage | false low voltage measurement | bus_voltage.814 | 814 | 23 | 23 | 31.319 | 351.149 | 4 | 100.000 | 60.870 | 100.000 | Direct measurement observation. |
| bus voltage | false low voltage measurement | bus_voltage.800 | 800 | 28 | 28 | 31.250 | 419.903 | 4 | 100.000 | 60.714 | 75.000 | Direct measurement observation. |
| line status/topology | false closed hidden-outage adjacency | topology_edge.Line.l12 | Line.l12 | 3 | 3 | 23.006 | 69.017 | 1 | 100.000 | 33.333 | 100.000 | Direct topology/status observation; executable cases are sparse. |
| switch action mask | false unavailable switch action | action_mask.swtie1 | swtie1 | 30 | 30 | 21.491 | 304.635 | 8 | 100.000 | 100.000 | 50.000 | Direct current-GRL switch-status/action availability observation. |
| line status/topology | false closed hidden-outage adjacency | topology_edge.Line.l15 | Line.l15 | 7 | 7 | 19.722 | 69.040 | 2 | 100.000 | 42.857 | 100.000 | Direct topology/status observation; executable cases are sparse. |
| bus voltage | false low voltage measurement | bus_voltage.824 | 824 | 19 | 19 | 17.011 | 192.747 | 4 | 100.000 | 63.158 | 50.000 | Direct measurement observation. |
| load-control action mask | false unavailable dispatch-load action | action_mask.Load_d816_824sb | Load.d816_824sb | 30 | 30 | 15.531 | 120.577 | 19 | 100.000 | 100.000 | 100.000 | Direct current-GRL load-status/control observation. |
| bus voltage | false low voltage measurement | bus_voltage.828 | 828 | 17 | 17 | 14.259 | 69.040 | 6 | 100.000 | 70.588 | 66.667 | Direct measurement observation. |
| load-control action mask | false unavailable dispatch-load action | action_mask.Load_d828_830sa | Load.d828_830sa | 30 | 30 | 12.670 | 80.573 | 6 | 100.000 | 43.333 | 100.000 | Direct current-GRL load-status/control observation. |
| line status/topology | false closed hidden-outage adjacency | topology_edge.Line.l14 | Line.l14 | 2 | 2 | 9.086 | 18.172 | 1 | 100.000 | 100.000 | 100.000 | Direct topology/status observation; executable cases are sparse. |
| switch action mask | false unavailable switch action | action_mask.swsec1 | swsec1 | 30 | 30 | 9.075 | 179.903 | 9 | 100.000 | 73.333 | 77.778 | Direct current-GRL switch-status/action availability observation. |
| bus voltage | false low voltage measurement | bus_voltage.812 | 812 | 25 | 25 | 8.969 | 69.040 | 4 | 100.000 | 36.000 | 75.000 | Direct measurement observation. |
| bus voltage | false low voltage measurement | bus_voltage.850 | 850 | 22 | 22 | 6.275 | 69.040 | 2 | 100.000 | 40.909 | 100.000 | Direct measurement observation. |
| bus voltage | false low voltage measurement | bus_voltage.806 | 806 | 26 | 26 | 5.970 | 69.040 | 3 | 100.000 | 53.846 | 66.667 | Direct measurement observation. |
| bus voltage | false low voltage measurement | bus_voltage.sourcebus | sourcebus | 30 | 30 | 5.953 | 166.607 | 4 | 100.000 | 46.667 | 25.000 | Direct measurement observation. |
| line status/topology | false open line-status adjacency | topology_edge.Line.l12 | Line.l12 | 27 | 27 | 5.786 | 69.040 | 3 | 100.000 | 29.630 | 100.000 | Direct topology/status observation. |
| line status/topology | false open line-status adjacency | topology_edge.Line.828832 | Line.828832 | 30 | 30 | 3.719 | 69.017 | 3 | 100.000 | 33.333 | 66.667 | Direct topology/status observation. |
| line status/topology | false closed hidden-outage adjacency | topology_edge.Line.l6 | Line.l6 | 3 | 3 | 1.977 | 5.930 | 1 | 100.000 | 66.667 | 0.000 | Direct topology/status observation; executable cases are sparse. |

Markdown preview shows first 30 of 59 rows.
