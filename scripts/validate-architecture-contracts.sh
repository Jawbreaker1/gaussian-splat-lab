#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 - <<'PY' "${repo_root}"
import json
import sys
from pathlib import Path

repo_root = Path(sys.argv[1])
frameworks_path = repo_root / "data/manifests/framework-evaluation.json"
gates_path = repo_root / "data/manifests/pipeline-gates.json"

frameworks = json.loads(frameworks_path.read_text(encoding="utf-8"))
gates = json.loads(gates_path.read_text(encoding="utf-8"))

allowed_decisions = {"preferred", "accepted", "conditional", "deferred", "blocked"}
allowed_commercial_statuses = set(frameworks.get("commercialUsePolicy", {}).get("allowedStatuses", []))
if not allowed_commercial_statuses:
    raise SystemExit("missing commercialUsePolicy.allowedStatuses")
blocked_license_markers = ["non-commercial", "research", "agpl", "gpl", "unknown"]
blocked_commercial_statuses = {"blocked", "blocked_by_policy"}

seen_ids = set()
for item in frameworks.get("frameworks", []):
    item_id = item.get("id")
    if not item_id or item_id in seen_ids:
        raise SystemExit(f"invalid or duplicate framework id: {item_id!r}")
    seen_ids.add(item_id)

    decision = item.get("decision")
    if decision not in allowed_decisions:
        raise SystemExit(f"invalid decision for {item_id}: {decision!r}")

    if decision in {"preferred", "accepted", "conditional"} and not item.get("officialSources"):
        raise SystemExit(f"missing official sources for {item_id}")

    license_text = str(item.get("license", "")).lower()
    if decision in {"preferred", "accepted"}:
        for marker in blocked_license_markers:
            if marker in license_text:
                raise SystemExit(
                    f"framework {item_id} has blocked-looking license {item.get('license')!r} but decision {decision!r}"
                )

    commercial_use = item.get("commercialUse")
    if commercial_use not in allowed_commercial_statuses:
        raise SystemExit(f"framework {item_id} has invalid commercialUse: {commercial_use!r}")

    commercial_conditions = item.get("commercialConditions")
    if not isinstance(commercial_conditions, list) or not commercial_conditions:
        raise SystemExit(f"framework {item_id} missing commercialConditions")

    if item.get("distributionRisk") not in {"low", "medium", "high"}:
        raise SystemExit(f"framework {item_id} missing valid distributionRisk")

    if decision == "conditional" and not item.get("condition"):
        raise SystemExit(f"conditional framework missing condition: {item_id}")

    if decision in {"preferred", "accepted"} and commercial_use in blocked_commercial_statuses:
        raise SystemExit(f"framework {item_id} is accepted but commercially blocked")

    if decision == "blocked" and commercial_use not in blocked_commercial_statuses:
        raise SystemExit(f"framework {item_id} is blocked but commercialUse is {commercial_use!r}")

if "graphdeco-inria-gaussian-splatting" not in seen_ids:
    raise SystemExit("original gaussian-splatting framework decision is missing")

blocked_original = next(
    item for item in frameworks["frameworks"] if item["id"] == "graphdeco-inria-gaussian-splatting"
)
if blocked_original.get("decision") != "blocked" or blocked_original.get("commercialUse") != "blocked":
    raise SystemExit("original graphdeco/inria gaussian-splatting must remain blocked")

opensplat = next((item for item in frameworks["frameworks"] if item["id"] == "opensplat"), None)
if opensplat is None or opensplat.get("commercialUse") != "blocked_by_policy":
    raise SystemExit("OpenSplat must remain blocked by policy unless AGPL is explicitly accepted")

expected_gate_ids = [
    "framework_license",
    "environment",
    "intake",
    "frame_sampling",
    "sfm",
    "splat_training",
    "packaging",
    "viewer",
    "quality_report",
]
actual_gate_ids = [gate.get("id") for gate in gates.get("gates", [])]
if actual_gate_ids != expected_gate_ids:
    raise SystemExit(f"pipeline gates out of order: {actual_gate_ids}")

expected_status_values = [
    "pass",
    "warning",
    "setup_gap",
    "fail",
    "blocked_license",
    "blocked_workload",
]
if gates.get("statusValues") != expected_status_values:
    raise SystemExit(f"pipeline status values out of sync: {gates.get('statusValues')}")

for gate in gates.get("gates", []):
    for key in ["inputContract", "outputContract", "validation"]:
        if not gate.get(key):
            raise SystemExit(f"gate {gate.get('id')} missing {key}")

print("architecture_contract_validation=passed")
PY
