# Data Dictionary: `prometheus-practical-execution-limits`

## 1. Accounting Distinction: Unique Logical Workloads vs. Physical Circuit Executions (`PUBs`)

To prevent confusion between unique problem instances and repeated multi-arm, two-wave, cross-processor, or multi-window hardware executions:

| Accounting Level | Exact Count | Definition |
| :--- | :---: | :--- |
| **Completed Live QPU Jobs** | **`24`** | `20` IBM Quantum `SamplerV2` batch jobs (`16` on `ibm_marrakesh`, `4` on `ibm_fez`) + `4` IQM Resonance batch jobs (`IQM Emerald`). |
| **Unique Logical Workload Instances** | **`129`** | Distinct `(family, regime, width, rounds, instance_idx)` circuits across the entire campaign (`56` in Stage 5.1 `s0..s1`, `60` fresh in Stage 5.2 `s2..s11`, and `13` additional Emerald-specific instances in Stage 5.5 `s0..s4`; Stages 5.3A and 5.3B re-evaluate the `30` paired core instances `s2..s6` from Stage 5.2 across processor and time). |
| **Stage-Level Workload Evaluations** | **`206`** | `56` (Stage 5.1) + `60` (Stage 5.2) + `30` (Stage 5.3A `ibm_fez`) + `30` (Stage 5.3B `ibm_marrakesh` `+32h`) + `30` (Stage 5.5 `IQM Emerald`). |
| **Compiled Physical Circuits** | **`824`** | `206` stage-level workload evaluations x `4` matched-budget execution strategies (`Arm 1: SABRE O3`, `Arm 2: TKET`, `Arm 3: Prometheus Native`, `Arm 4: Prometheus Selector`). |
| **Physical Circuit Executions (`PUBs`)** | **`1,648`** | `824` compiled physical circuits x `2` independent measurement waves (`Wave 1: Primary` + `Wave 2: Confirm`). |
| **Physical Measurement Shots** | **`1,687,552`** | `1,648` physical circuit executions x `1,024` physical shots per execution. |

---

## 2. Schema of `data/ALL_1648_EXECUTIONS_MASTER_LEDGER.csv` (`1,648` Rows, Zero Placeholders)

| Column Name | Type | Direction / Units | Description |
| :--- | :---: | :---: | :--- |
| `stage` | `string` | Categorical | Campaign stage identifier (`Stage_5.1_...` through `Stage_5.5_...`). |
| `job_manifest_id` | `string` | Identifier | Pre-execution batch manifest identifier (`Primary` or `Confirm` wave). |
| `hardware_job_id` | `string` | Provider ID | Verifiable IBM Quantum Job ID or IQM Resonance Job UUID. |
| `backend` | `string` | Processor | Physical QPU (`ibm_marrakesh`, `ibm_fez`, or `emerald`). |
| `pass_type` | `string` | Wave | `Primary` (Wave 1) or `Confirm` (Wave 2 independent confirmation measurement). |
| `pub_index` | `int` | `0`-indexed | Position of the PUB inside the submitted hardware batch job. |
| `point_id` | `string` | Identifier | Difficulty-point code (`B1-B6`, `E1-E6`, or Stage 5.1 grid point). |
| `workload_id` | `string` | Identifier | Canonical logical workload key `Family__Regime__Wxx__Ly__sz`. |
| `family` | `string` | Categorical | `F1_Weighted_QAOA`, `F2_QFT_PhaseRecovery`, `F3_Random_SU4`, or `F4_Twirled_Clifford_Mirror` *(primary scores are never averaged across families)*. |
| `regime` | `string` | Categorical | `C0_HardwareLocal_Path`, `C1_Sparse_NonLocal`, `C2_Intermediate_NonLocal`, or `C3_Dense_AllToAll`. |
| `width` | `int` | Qubits | Logical circuit width $W \in [9, 28]$. |
| `rounds` | `int` | Layers $L$ | Logical interaction rounds / layers $L$. |
| `instance_idx` | `int` | Seed index | Deterministic instance index (`s0..s11`). |
| `arm` | `string` | Strategy | `Arm1_SABRE_MatchedBudget` (`1.0x`), `Arm2_TKET_MatchedBudget` (`1.0x`), `Arm3_Prometheus_Native` (`1.0x`), or `Arm4_Prometheus_Selector` (`3.0x` search across Arms 1-3). |
| `shots` | `int` | Shots | Physical measurement shots (`1024` for every PUB). |
| `native_2q` | `int` | `(↓)` Gates | Native two-qubit entangling gate count (`CZ`). |
| `depth_total` | `int` | `(↓)` Layers | Total compiled native circuit depth. |
| `primary_metric_name` | `string` | Metric | Family-specific viability metric (`r_approx_gain`, `bit_polarization`, `hop`, `mirror_polarization`). |
| `viability_threshold` | `float` | Threshold $\tau$ | Predefined viability threshold (`0.35` for `F1`, `0.50` for `F2`, `0.58` for `F3`, `0.50` for `F4`). |
| `primary_metric` | `float` | `(↑)` | Measured family-specific primary metric on this `1,024`-shot PUB. |
| `aux_pass` | `int` (`0/1`) | Boolean | Auxiliary requirement (`1` iff per-bit majority vote recovers exact target string $z^*$ on `F2`; `1` on `F1, F3, F4`). |
| `fb_overlap` | `float` | `(↑)` `[0,1]` | Classical Bhattacharyya Distribution Overlap $F_B = \sum_x \sqrt{P_{\text{ideal}}(x) P_{\text{meas}}(x)}$ *(labeled `"State Fidelity"` in Studio UIs)*. |
| `fh_hellinger` | `float` | `(↑)` `[0,1]` | Squared Hellinger Fidelity $F_H = F_B^2$ *(equals exact complete-answer probability $P_{\text{meas}}(z^*)$ on single-target `F2` & `F4`)*. |
| `tvd` | `float` | `(↓)` `[0,1]` | Total Variation Distance $\frac{1}{2}\sum_x |P_{\text{ideal}}(x) - P_{\text{meas}}(x)|$. |
| `hop` | `float` | `(↑)` `[0,1]` | Heavy-Output Probability (probability mass above median of $P_{\text{ideal}}$). |
| `linear_xeb` | `float` | `(↑)` | Linear Cross-Entropy Benchmarking score $2^W \sum_x P_{\text{ideal}}(x) P_{\text{meas}}(x) - 1$. |
| `shannon_entropy_bits` | `float` | Bits | Empirical output Shannon entropy $-\sum_x P_{\text{meas}}(x) \log_2 P_{\text{meas}}(x)$. |
