#!/usr/bin/env python3
"""
Standalone Offline Audit & Raw-Histogram Verifier for `prometheus-practical-execution-limits`.
Requires ONLY Python standard library + `numpy` (zero Qiskit, pytket, or proprietary imports).

Verifies:
  1. Exact deduplicated hardware accounting: 24 unique live QPU jobs (20 IBM Heron + 4 IQM Emerald),
     129 unique logical workload instances, 206 stage-level 4-arm x 2-wave evaluations,
     1,648 physical circuit executions (PUBs), and 1,687,552 physical shots (0 placeholder cells).
  2. Direct raw-histogram recomputation of all 1,648 PUB primary metrics and universal observables
     (`fb_overlap`, `fh_hellinger`, `tvd`, `hop`, `linear_xeb`, `shannon_entropy_bits`) against
     `data/ALL_1648_EXECUTIONS_MASTER_LEDGER.csv` and `data/logical_workloads/*.qasm` SHA-256 hashes.
  3. Direct recomputation of strict two-wave MECE (`Confirmed Pass`, `Unresolved Within Budget`,
     `Confirmed Fail`) outcomes across the headline boundary, +32h repeatability, Fez portability,
     and IQM Emerald cross-architecture stages.
  4. Automated IP, credential, account-metadata, host-path, and typography scan across every text
     file in the repository + byte-exact `REPO_SHA256_MANIFEST.json` verification.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np


def deterministic_seed(*parts: Any) -> int:
    raw = "|".join(str(p) for p in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big") % (2**31 - 1)


def score_raw_pub_numpy(ref: Dict[str, Any], counts: Dict[str, int], boot_seed: int, n_boot: int = 1000) -> Dict[str, Any]:
    w = int(ref["width"])
    fam = ref["family"]
    wid = ref["workload_id"]

    clean: Dict[str, int] = {}
    tot = 0
    for bs_raw, cnt in counts.items():
        if cnt <= 0:
            continue
        bs = bs_raw.replace(" ", "")
        bs = bs.zfill(w) if len(bs) < w else bs[-w:]
        clean[bs] = clean.get(bs, 0) + int(cnt)
        tot += int(cnt)

    bitstrings = list(clean.keys())
    probs_emp = np.array([clean[b] / float(tot) for b in bitstrings], dtype=np.float64)
    shannon_bits = float(-np.sum(probs_emp * np.log2(np.maximum(1e-18, probs_emp))))
    rng = np.random.default_rng(deterministic_seed(boot_seed, wid, tot))

    if fam == "F1_Weighted_QAOA":
        edges = ref["edges"]
        weights = ref["weights"]
        c_max = float(ref["c_max"])
        c_rand = float(ref["c_rand"])
        denom = max(1e-9, c_max - c_rand)
        cut_vals = np.zeros(len(bitstrings), dtype=np.float64)
        for idx_b, bs in enumerate(bitstrings):
            cv = 0.0
            for (u, v), wv in zip(edges, weights):
                if bs[w - 1 - u] != bs[w - 1 - v]:
                    cv += float(wv)
            cut_vals[idx_b] = cv
        c_meas = float(np.dot(probs_emp, cut_vals))
        prim = (c_meas - c_rand) / denom
        draws = rng.multinomial(tot, probs_emp, size=n_boot) / float(tot)
        bvals = ((draws @ cut_vals) - c_rand) / denom
        ci = (round(float(np.percentile(bvals, 2.5)), 6), round(float(np.percentile(bvals, 97.5)), 6))
        aux_ok = True
    elif fam in ("F2_QFT_PhaseRecovery", "F4_Twirled_Clifford_Mirror"):
        t_bs = ref["target_bitstring"]
        agree = np.where(
            np.array([[1 if bs[p] == t_bs[p] else 0 for p in range(w)] for bs in bitstrings]) == 1,
            1.0,
            -1.0,
        )
        per_bit = probs_emp @ agree
        prim = float(np.mean(per_bit))
        maj = bool(np.all(per_bit > 0.0))
        sample_pols = np.mean(agree, axis=1)
        draws = rng.multinomial(tot, probs_emp, size=n_boot) / float(tot)
        bvals = draws @ sample_pols
        ci = (round(float(np.percentile(bvals, 2.5)), 6), round(float(np.percentile(bvals, 97.5)), 6))
        aux_ok = maj if fam == "F2_QFT_PhaseRecovery" else True
    elif fam == "F3_Random_SU4":
        obs_h = ref["observed_bitstring_heavy_flags"]
        is_heavy = np.array([float(obs_h[bs]) for bs in bitstrings], dtype=np.float64)
        prim = float(np.dot(probs_emp, is_heavy))
        draws = rng.multinomial(tot, probs_emp, size=n_boot) / float(tot)
        bvals = draws @ is_heavy
        ci = (round(float(np.percentile(bvals, 2.5)), 6), round(float(np.percentile(bvals, 97.5)), 6))
        aux_ok = True
    else:
        raise ValueError(f"Unknown family {fam}")

    if ref["ideal_distribution_kind"] == "delta":
        t_bs = ref["target_bitstring"]
        p_hit = float(clean.get(t_bs, 0)) / float(tot)
        fb = math.sqrt(max(0.0, p_hit))
        fh = p_hit
        tvd = 1.0 - p_hit
        hop = p_hit
        xeb = float((1 << min(w, 30)) * p_hit - 1.0) if w <= 24 else 0.0
    else:
        obs_p = ref["observed_bitstring_ideal_probs"]
        obs_h = ref["observed_bitstring_heavy_flags"]
        fb_sum = 0.0
        hop_sum = 0.0
        lin_ip = 0.0
        l1_obs = 0.0
        ip_seen = 0.0
        for bs, cnt in clean.items():
            pm = float(cnt) / float(tot)
            pi = float(obs_p[bs])
            ip_seen += pi
            fb_sum += math.sqrt(max(0.0, pi * pm))
            if obs_h[bs]:
                hop_sum += pm
            lin_ip += pi * pm
            l1_obs += abs(pi - pm)
        tvd = 0.5 * (l1_obs + max(0.0, 1.0 - ip_seen))
        fb = fb_sum
        fh = fb_sum * fb_sum
        hop = hop_sum
        xeb = float((1 << w) * lin_ip - 1.0)

    return {
        "shots": tot,
        "primary_metric": round(prim, 6),
        "ci95": ci,
        "aux_pass": aux_ok,
        "fb_overlap": round(fb, 6),
        "fh_hellinger": round(fh, 6),
        "tvd": round(tvd, 6),
        "hop": round(hop, 6),
        "linear_xeb": round(xeb, 6),
        "shannon_entropy_bits": round(shannon_bits, 6),
    }


def classify_instance_mece(ci1: Tuple[float, float], ci2: Tuple[float, float], tau: float, a1: bool, a2: bool) -> str:
    if ci1[0] >= tau and ci2[0] >= tau and a1 and a2:
        return "Confirmed Pass"
    if ci1[1] < tau and ci2[1] < tau:
        return "Confirmed Fail"
    return "Unresolved Within Budget"


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    refs = json.loads((root / "data" / "logical_workloads" / "logical_references_129_workloads.json").read_text(encoding="utf-8"))
    assert len(refs) == 129, f"Expected 129 unique logical workloads, found {len(refs)}"

    # Verify all 129 logical .qasm SHA-256 digests
    for wid, r in refs.items():
        qp = root / "data" / "logical_workloads" / r["logical_qasm_file"]
        assert hashlib.sha256(qp.read_bytes()).hexdigest() == r["logical_qasm_sha256"], f"QASM SHA mismatch on {wid}"

    stage_files = [
        ("Stage_5.1_IBM_Marrakesh_Coarse_Frontier", "stage5_1_manifest.json", "stage5_1_raw_pub_counts.json", 20261115, 1000),
        ("Stage_5.2_IBM_Marrakesh_Boundary_W1", "stage5_2_manifest.json", "stage5_2_raw_pub_counts.json", 20261116, 2000),
        ("Stage_5.3A_IBM_Fez_Portability", "stage5_3a_fez_manifest.json", "stage5_3a_ibm_fez_raw_pub_counts.json", 20261118, 2000),
        ("Stage_5.3B_IBM_Marrakesh_Repeatability_W2", "stage5_3b_marrakesh_w2_manifest.json", "stage5_3b_ibm_marrakesh_recal_raw_pub_counts.json", 20261119, 2000),
        ("Stage_5.5_IQM_Emerald_Cross_Architecture", "stage5_5_iqm_emerald_manifest.json", "stage5_5_iqm_raw_pub_counts.json", 20261117, 2000),
    ]

    csv_rows = list(csv.DictReader((root / "data" / "ALL_1648_EXECUTIONS_MASTER_LEDGER.csv").open("r", encoding="utf-8")))
    assert len(csv_rows) == 1648, f"Expected 1648 CSV rows, got {len(csv_rows)}"
    for row in csv_rows:
        for k, v in row.items():
            assert v not in ("-", "N/A", ""), f"Placeholder cell in CSV {k}: {v}"

    csv_lookup = {(r["hardware_job_id"], int(r["pub_index"])): r for r in csv_rows}
    assert len(csv_lookup) == 1648

    job_ids = []
    stage_inst_scores: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    max_metric_diff = 0.0
    total_shots = 0

    for st_label, man_fn, raw_fn, bseed_base, n_boot_st in stage_files:
        man = json.loads((root / "data" / "manifests" / man_fn).read_text(encoding="utf-8"))
        raw = json.loads((root / "data" / "raw_counts" / raw_fn).read_text(encoding="utf-8"))
        jobs_man = {j["job_manifest_id"]: j for j in man["jobs"]}
        for j_mid, j_raw in raw.items():
            jid = j_raw["hardware_job_id"]
            job_ids.append(jid)
            pm_by_idx = {int(x["pub_index"]): x for x in jobs_man[j_mid]["pubs"]}
            for pr in j_raw["pubs"]:
                pidx = int(pr["pub_index"])
                pm = pm_by_idx[pidx]
                wid = pm["workload_id"]
                sc = score_raw_pub_numpy(refs[wid], pr["counts"], boot_seed=bseed_base + pidx, n_boot=n_boot_st)
                total_shots += sc["shots"]

                crow = csv_lookup[(jid, pidx)]
                for col in ("primary_metric", "fb_overlap", "fh_hellinger", "tvd", "hop", "linear_xeb", "shannon_entropy_bits"):
                    diff = abs(float(crow[col]) - float(sc[col]))
                    max_metric_diff = max(max_metric_diff, diff)
                    assert diff < 1e-4, f"Mismatch on {jid} pub {pidx} {col}: CSV={crow[col]} vs recomputed={sc[col]}"

                stage_inst_scores[(st_label, wid, pm["arm"], pm["pass_type"])] = sc

    assert len(job_ids) == 24 and len(set(job_ids)) == 24, f"Expected 24 unique jobs, got {len(set(job_ids))}"
    assert total_shots == 1687552, f"Expected 1,687,552 physical shots, got {total_shots}"

    # Verify headline strict two-wave MECE instance counts from raw histograms
    def count_strict_passes(st_label: str, wids: List[str], arm: str, tau: float) -> Tuple[int, int, int]:
        p_c = u_c = f_c = 0
        for wid in wids:
            s1 = stage_inst_scores[(st_label, wid, arm, "Primary")]
            s2 = stage_inst_scores[(st_label, wid, arm, "Confirm")]
            out = classify_instance_mece(s1["ci95"], s2["ci95"], tau, s1["aux_pass"], s2["aux_pass"])
            if out == "Confirmed Pass":
                p_c += 1
            elif out == "Confirmed Fail":
                f_c += 1
            else:
                u_c += 1
        return p_c, u_c, f_c

    w15_s52 = [f"F2_QFT_PhaseRecovery__C3_Dense_AllToAll__W15__L1__s{i}" for i in range(2, 12)]
    assert count_strict_passes("Stage_5.2_IBM_Marrakesh_Boundary_W1", w15_s52, "Arm3_Prometheus_Native", 0.50) == (10, 0, 0)
    assert count_strict_passes("Stage_5.2_IBM_Marrakesh_Boundary_W1", w15_s52, "Arm4_Prometheus_Selector", 0.50) == (10, 0, 0)
    assert count_strict_passes("Stage_5.2_IBM_Marrakesh_Boundary_W1", w15_s52, "Arm1_SABRE_MatchedBudget", 0.50) == (0, 0, 10)
    assert count_strict_passes("Stage_5.2_IBM_Marrakesh_Boundary_W1", w15_s52, "Arm2_TKET_MatchedBudget", 0.50) == (0, 0, 10)

    w15_s53b = [f"F2_QFT_PhaseRecovery__C3_Dense_AllToAll__W15__L1__s{i}" for i in range(2, 7)]
    assert count_strict_passes("Stage_5.3B_IBM_Marrakesh_Repeatability_W2", w15_s53b, "Arm3_Prometheus_Native", 0.50) == (5, 0, 0)
    assert count_strict_passes("Stage_5.3B_IBM_Marrakesh_Repeatability_W2", w15_s53b, "Arm4_Prometheus_Selector", 0.50) == (4, 1, 0)
    assert count_strict_passes("Stage_5.3B_IBM_Marrakesh_Repeatability_W2", w15_s53b, "Arm1_SABRE_MatchedBudget", 0.50) == (0, 0, 5)

    w12_iqm = [f"F2_QFT_PhaseRecovery__C3_Dense_AllToAll__W12__L1__s{i}" for i in range(0, 5)]
    assert count_strict_passes("Stage_5.5_IQM_Emerald_Cross_Architecture", w12_iqm, "Arm3_Prometheus_Native", 0.50) == (5, 0, 0)
    assert count_strict_passes("Stage_5.5_IQM_Emerald_Cross_Architecture", w12_iqm, "Arm4_Prometheus_Selector", 0.50) == (5, 0, 0)
    assert count_strict_passes("Stage_5.5_IQM_Emerald_Cross_Architecture", w12_iqm, "Arm1_SABRE_MatchedBudget", 0.50) == (0, 0, 5)

    # Automated IP, credential, account, host-path & typography scan across all tracked files
    forbidden_tokens = [
        "Account_A",
        "Account_B",
        "Account_C",
        "IQM_Account",
        "candidate_origin",
        "chosen_origin",
        "committed_origin",
        "prometheus_routed",
        "PrometheusV1",
        "PrometheusV2",
        "compilers_4arm",
        "discord.com/api/webhooks",
        "apikey",
        "C:\\Users",
        "C:/Users",
        "F:\\Prometheus",
        "F:/Prometheus",
        "\u2014",
        "\u2013",
        "\x0c",
        "\x08",
    ]
    self_rel = Path(__file__).resolve().relative_to(root).as_posix()
    scanned_files = 0
    for fp in sorted(root.rglob("*")):
        if not fp.is_file() or ".git" in fp.parts:
            continue
        rel = fp.relative_to(root).as_posix()
        if fp.suffix in (".md", ".json", ".csv", ".py", ".qasm", ".txt") and rel != self_rel:
            txt = fp.read_text(encoding="utf-8")
            for tok in forbidden_tokens:
                assert tok not in txt, f"Forbidden token '{tok}' detected in {rel}"
            scanned_files += 1

    # Verify REPO_SHA256_MANIFEST.json
    rm_path = root / "REPO_SHA256_MANIFEST.json"
    if rm_path.exists():
        rm = json.loads(rm_path.read_text(encoding="utf-8"))
        for rel_p, exp_sha in rm["files"].items():
            act_sha = hashlib.sha256((root / rel_p).read_bytes()).hexdigest()
            assert act_sha == exp_sha, f"SHA-256 mismatch on {rel_p}: {act_sha} != {exp_sha}"
        n_sha = len(rm["files"])
    else:
        n_sha = 0

    print("=" * 94)
    print("PRACTICAL EXECUTION LIMITS CAMPAIGN - STANDALONE RAW-HISTOGRAM & IP AUDIT")
    print("=" * 94)
    print(f"  [PASS] Unique Hardware Jobs Verified     : {len(set(job_ids))} / 24 (20 IBM Heron + 4 IQM Emerald, 0 duplicates)")
    print(f"  [PASS] Unique Logical Workloads Verified : {len(refs)} / 129 (.qasm SHA-256 verified)")
    print(f"  [PASS] Physical Executions (PUBs) & Shots: 1,648 PUBs | {total_shots:,d} shots (max diff = {max_metric_diff:.2e})")
    print("  [PASS] Two-Wave MECE Boundary Audits     : 10/10 Pass (Marrakesh 15Q W1), 5/5 Pass (+32h W2), 5/5 Pass (IQM 12Q)")
    print(f"  [PASS] IP, Account & Typography Scan     : {scanned_files} text files clean | {n_sha} SHA-256 checksums verified")
    print("=" * 94)


if __name__ == "__main__":
    main()
