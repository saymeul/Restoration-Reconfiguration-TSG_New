$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'C:\Users\ISLAS2\OneDrive - Idaho National Laboratory\Desktop\TSG_Real-Time-Outage-Management-Active-DNR-GRL-v.1.0\NAPS_adamslab-ub-Real-Time-Outage-Management-Active-DNR-GRL-b715982\RL_Testing'

# Run all IEEE 123 full criticality chunks.

# Command 1 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 0 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0000_0000

# Command 2 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 1 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0001_0001

# Command 3 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 2 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0002_0002

# Command 4 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 3 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0003_0003

# Command 5 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 4 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0004_0004

# Command 6 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 5 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0005_0005

# Command 7 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 6 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0006_0006

# Command 8 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 7 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0007_0007

# Command 9 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 8 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0008_0008

# Command 10 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 9 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0009_0009

# Command 11 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 10 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0010_0010

# Command 12 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 11 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0011_0011

# Command 13 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 12 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0012_0012

# Command 14 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 13 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0013_0013

# Command 15 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 14 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0014_0014

# Command 16 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 15 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0015_0015

# Command 17 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 16 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0016_0016

# Command 18 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 17 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0017_0017

# Command 19 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 18 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0018_0018

# Command 20 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 19 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0019_0019

# Command 21 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 20 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0020_0020

# Command 22 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 21 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0021_0021

# Command 23 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 22 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0022_0022

# Command 24 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 23 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0023_0023

# Command 25 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 24 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0024_0024

# Command 26 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 25 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0025_0025

# Command 27 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 26 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0026_0026

# Command 28 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 27 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0027_0027

# Command 29 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 28 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0028_0028

# Command 30 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 29 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0029_0029

# Command 31 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 30 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0030_0030

# Command 32 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 31 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0031_0031

# Command 33 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 32 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0032_0032

# Command 34 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 33 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0033_0033

# Command 35 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 34 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0034_0034

# Command 36 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 35 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0035_0035

# Command 37 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 36 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0036_0036

# Command 38 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 37 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0037_0037

# Command 39 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 38 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0038_0038

# Command 40 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 39 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0039_0039

# Command 41 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 40 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0040_0040

# Command 42 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 41 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0041_0041

# Command 43 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 42 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0042_0042

# Command 44 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 43 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0043_0043

# Command 45 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 44 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0044_0044

# Command 46 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 45 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0045_0045

# Command 47 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 46 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0046_0046

# Command 48 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 47 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0047_0047

# Command 49 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 48 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0048_0048

# Command 50 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 49 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0049_0049

# Command 51 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 50 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0050_0050

# Command 52 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 51 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0051_0051

# Command 53 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 52 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0052_0052

# Command 54 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 53 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0053_0053

# Command 55 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 54 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0054_0054

# Command 56 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 55 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0055_0055

# Command 57 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 56 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0056_0056

# Command 58 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 57 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0057_0057

# Command 59 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 58 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0058_0058

# Command 60 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 59 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0059_0059

# Command 61 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 60 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0060_0060

# Command 62 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 61 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0061_0061

# Command 63 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 62 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0062_0062

# Command 64 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 63 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0063_0063

# Command 65 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 64 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0064_0064

# Command 66 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 65 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0065_0065

# Command 67 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 66 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0066_0066

# Command 68 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 67 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0067_0067

# Command 69 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 68 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0068_0068

# Command 70 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 69 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0069_0069

# Command 71 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 70 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0070_0070

# Command 72 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 71 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0071_0071

# Command 73 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 72 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0072_0072

# Command 74 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 73 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0073_0073

# Command 75 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 74 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0074_0074

# Command 76 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 75 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0075_0075

# Command 77 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 76 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0076_0076

# Command 78 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 77 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0077_0077

# Command 79 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 78 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0078_0078

# Command 80 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 79 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0079_0079

# Command 81 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 80 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0080_0080

# Command 82 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 81 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0081_0081

# Command 83 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 82 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0082_0082

# Command 84 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 83 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0083_0083

# Command 85 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 84 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0084_0084

# Command 86 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 85 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0085_0085

# Command 87 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 86 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0086_0086

# Command 88 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 87 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0087_0087

# Command 89 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 88 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0088_0088

# Command 90 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 89 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0089_0089

# Command 91 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 90 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0090_0090

# Command 92 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 91 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0091_0091

# Command 93 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 92 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0092_0092

# Command 94 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 93 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0093_0093

# Command 95 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 94 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0094_0094

# Command 96 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 95 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0095_0095

# Command 97 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 96 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0096_0096

# Command 98 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 97 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0097_0097

# Command 99 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 98 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0098_0098

# Command 100 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 99 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0099_0099

# Command 101 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 100 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0100_0100

# Command 102 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 101 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0101_0101

# Command 103 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 102 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0102_0102

# Command 104 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 103 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0103_0103

# Command 105 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 104 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0104_0104

# Command 106 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 105 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0105_0105

# Command 107 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 106 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0106_0106

# Command 108 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 107 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0107_0107

# Command 109 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 108 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0108_0108

# Command 110 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 109 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0109_0109

# Command 111 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 110 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0110_0110

# Command 112 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 111 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0111_0111

# Command 113 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 112 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0112_0112

# Command 114 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 113 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0113_0113

# Command 115 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 114 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0114_0114

# Command 116 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 115 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0115_0115

# Command 117 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 116 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0116_0116

# Command 118 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 117 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0117_0117

# Command 119 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 118 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0118_0118

# Command 120 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 119 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0119_0119

# Command 121 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 120 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0120_0120

# Command 122 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 121 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0121_0121

# Command 123 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 122 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0122_0122

# Command 124 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 123 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0123_0123

# Command 125 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 124 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0124_0124

# Command 126 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 125 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0125_0125

# Command 127 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 126 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0126_0126

# Command 128 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 127 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0127_0127

# Command 129 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 128 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0128_0128

# Command 130 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 129 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0129_0129

# Command 131 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 130 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0130_0130

# Command 132 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 131 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0131_0131

# Command 133 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 132 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0132_0132

# Command 134 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 133 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0133_0133

# Command 135 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 134 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0134_0134

# Command 136 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 135 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0135_0135

# Command 137 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 136 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0136_0136

# Command 138 of 179
conda run -n grl123 python Run_TSG_IEEE123_MeasurementCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-family branchflow --target-start-index 137 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\branchflow\chunk_0137_0137

# Command 139 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 0 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0000_0000

# Command 140 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 1 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0001_0001

# Command 141 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 2 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0002_0002

# Command 142 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 3 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0003_0003

# Command 143 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 4 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0004_0004

# Command 144 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 5 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0005_0005

# Command 145 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 6 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0006_0006

# Command 146 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 7 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0007_0007

# Command 147 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 8 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0008_0008

# Command 148 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 9 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0009_0009

# Command 149 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 10 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0010_0010

# Command 150 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 11 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0011_0011

# Command 151 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 12 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0012_0012

# Command 152 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 13 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0013_0013

# Command 153 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 14 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0014_0014

# Command 154 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 15 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0015_0015

# Command 155 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 16 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0016_0016

# Command 156 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 17 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0017_0017

# Command 157 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 18 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0018_0018

# Command 158 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 19 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0019_0019

# Command 159 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 20 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0020_0020

# Command 160 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 21 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0021_0021

# Command 161 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 22 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0022_0022

# Command 162 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 23 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0023_0023

# Command 163 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 24 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0024_0024

# Command 164 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 25 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0025_0025

# Command 165 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 26 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0026_0026

# Command 166 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 27 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0027_0027

# Command 167 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 28 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0028_0028

# Command 168 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 29 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0029_0029

# Command 169 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 30 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0030_0030

# Command 170 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 31 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0031_0031

# Command 171 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 32 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0032_0032

# Command 172 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 33 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0033_0033

# Command 173 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 34 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0034_0034

# Command 174 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 35 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0035_0035

# Command 175 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 36 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0036_0036

# Command 176 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 37 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0037_0037

# Command 177 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 38 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0038_0038

# Command 178 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 39 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0039_0039

# Command 179 of 179
conda run -n grl123 python Run_TSG_IEEE123_ActionMaskCriticality.py --cases 30 --horizon 24 --seed 20260615 --seed-schedule baseline_attack --baseline-case-seed-draws 5 --target-scope switch_and_load --target-start-index 40 --target-count 1 --include-noop --output-dir paper_results\tsg_ieee123\full_criticality_batches\action_mask\chunk_0040_0040
