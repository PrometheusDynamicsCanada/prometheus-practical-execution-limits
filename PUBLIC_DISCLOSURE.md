# Public Disclosure & Reproducibility Scope

## 1. Verifiable Empirical Artifacts Included in This Repository

This repository provides complete, standalone empirical provenance for the **Prometheus Practical Execution Limits Campaign (Phase 5)** across **24 live cloud QPU jobs** (`20` IBM Quantum Heron `SamplerV2` jobs on `156Q` `ibm_marrakesh` and `ibm_fez` + `4` IQM Resonance jobs on `54Q` `IQM Emerald`), comprising **`1,648` physical circuit executions (`PUBs`)** and **`1,687,552` physical measurement shots** (`1,024` shots per execution) across **`129` unique logical workload instances** (`206` stage-level 4-arm x 2-wave workload evaluations):

- **Verifiable Hardware Identifiers:** All `20` IBM Quantum Job IDs (`dbt8ti9vvpic738mm8ng` through `dbu6elae8crs738b4rig`) and all `4` IQM Resonance Job UUIDs (`01a1e32d-7c08-76d6-9e3a-aa1f1613cedf` through `01a1e32f-f4bf-73e3-a312-d6414619dd8f`), with zero overlap against any other repository in the Prometheus quantum portfolio (`verified via prometheus-quantum-overview/scripts/verify_portfolio_accounting.py`).
- **Frozen Pre-Execution Manifests:** Sanitized pre-submission manifests (`data/manifests/*.json`) preserving SHA-256 commitments of compiled payloads, calibration timestamps / `calibration_set_id`s, structural native two-qubit gate counts, and compiled circuit depths.
- **Unrouted Logical Benchmark Circuits & Certified Reference Oracles:** All `129` unique logical benchmark circuits in portable OpenQASM 2.0 (`data/logical_workloads/qasm/*.qasm`) paired with `data/logical_workloads/logical_references_129_workloads.json` (certified `HiGHS MILP` weighted MaxCut optima, deterministic hidden target bitstrings, and exact noiseless probability references).
- **Raw Hardware Measurement Histograms:** Unmodified returned shot histograms (`1,648` PUB histograms totaling `1,687,552` physical shots in `data/raw_counts/*.json`) and the zero-placeholder `1,648`-row master CSV (`data/ALL_1648_EXECUTIONS_MASTER_LEDGER.csv`).
- **Complete Outcome Reporting (Including Unresolved & Negative Regimes):** All `28` coarse frontier points (`Stage 5.1`), `16Q-17Q` marginal/unresolved boundary points, `ibm_fez` inter-wave degradation results (`Stage 5.3A`), and `IQM Emerald` `14Q-16Q` failed points (`Stage 5.5`) are published alongside the confirmed dense pass-vs-fail separations.
- **Standalone Offline Verifier (`numpy` only):** `scripts/verify_practical_limits_campaign.py` recomputes all `1,648` PUB primary metrics, universal distribution observables (`F_B`, `F_H`, `TVD`, `HOP`, `XEB`, `Shannon Entropy`), and strict two-wave `MECE` classifications directly from the raw measurement histograms without requiring Qiskit, `pytket`, or proprietary compiler code.

## 2. Intellectual Property & Account-Privacy Boundary

To protect Prometheus Dynamics proprietary compiler and selector intellectual property and account security while preserving 100% empirical verifiability of the measured hardware outcomes:

- **Withheld Proprietary Implementation:** Proprietary hardware-aware optimization, compilation heuristics, multi-objective scoring parameters, synthesis routines, and physical qubit coordinate mappings are withheld from this public repository.
- **Sanitized Host & Account Metadata:** Local host file paths, API credentials, internal provider CRNs, and multi-account reserve-pool balances have been removed from public JSON manifests (`original_private_manifest_sha256` and `original_private_settled_ledger_sha256` preserve cryptographic continuity references per portfolio Verification Tier 4).
- **Clean Single-Commit Release:** This repository is published as a freshly initialized single-commit sanitized release (`0` historical pre-sanitization blobs in `.git` object storage).
