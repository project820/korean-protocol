#!/usr/bin/env python3
"""Validate this independent suite and create or verify its immutable freeze record."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FAMILIES = {
    "particles_and_argument_roles",
    "omission_and_referents",
    "relative_and_modifier_attachment",
    "negation_and_quantifier_scope",
    "aspect_and_modality",
    "passive_and_causative",
    "honorifics_and_speech_act",
    "conditions_and_simultaneity",
}
CASE_FIELDS = {
    "id", "family", "case_type", "explicit_context", "source", "candidate",
    "expected_decision", "acceptable_output", "rejected_output", "rationale",
    "preserved_facts", "prohibited_changes",
}
DECISIONS = {"normal": "accept", "failure": "reject", "keep": "keep"}

def require(condition, message):
    if not condition:
        raise SystemExit(message)

def digest(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()

def validate():
    data = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))
    require(data.get("schema_version") == "1.0", "Wrong schema version")
    require(data.get("suite_id") == "korean-independent-v1", "Wrong suite ID")
    require(isinstance(data.get("provenance"), dict), "Missing provenance")
    require(isinstance(data.get("decision_contract"), dict), "Missing decision contract")
    cases = data.get("cases")
    require(isinstance(cases, list) and len(cases) == 24, "Exactly 24 cases required")
    ids = [case.get("id") for case in cases]
    require(len(set(ids)) == 24, "Case IDs must be unique")
    groups = Counter()
    for case in cases:
        require(set(case) == CASE_FIELDS, f"Wrong fields: {case.get('id')}")
        cid = case["id"]
        require(case["family"] in FAMILIES, f"Unknown family: {cid}")
        require(case["case_type"] in DECISIONS, f"Unknown case type: {cid}")
        require(case["expected_decision"] == DECISIONS[case["case_type"]], f"Wrong decision: {cid}")
        for field in CASE_FIELDS - {"preserved_facts", "prohibited_changes"}:
            require(isinstance(case[field], str) and bool(case[field].strip()), f"Empty or non-string {field}: {cid}")
        for field in ("preserved_facts", "prohibited_changes"):
            require(isinstance(case[field], list) and len(case[field]) > 0, f"Empty or non-list {field}: {cid}")
            require(all(isinstance(x, str) and x.strip() for x in case[field]), f"Invalid {field}: {cid}")
        kind = case["case_type"]
        if kind == "keep":
            require(case["source"] == case["candidate"] == case["acceptable_output"], f"Keep must retain source: {cid}")
        else:
            require(case["source"] != case["candidate"], f"Revision must differ: {cid}")
        if kind == "normal":
            require(case["candidate"] == case["acceptable_output"], f"Normal candidate must be acceptable: {cid}")
        if kind == "failure":
            require(case["candidate"] == case["rejected_output"], f"Failure must specify rejected candidate: {cid}")
        require(case["acceptable_output"] != case["rejected_output"], f"Outputs must differ: {cid}")
        groups[(case["family"], kind)] += 1
    require(set(groups) == {(family, kind) for family in FAMILIES for kind in DECISIONS}, "Missing family/type combination")
    require(all(count == 1 for count in groups.values()), "One case required per family/type")
    return {
        "schema_valid": True,
        "case_count": 24,
        "family_count": 8,
        "case_type_counts": dict(sorted(Counter(c["case_type"] for c in cases).items())),
        "expected_decision_counts": dict(sorted(Counter(c["expected_decision"] for c in cases).items())),
        "family_counts": dict(sorted(Counter(c["family"] for c in cases).items())),
        "one_case_per_family_and_type": True,
        "sha256": {name: digest(name) for name in ("cases.json", "plan.md", "validate.py")},
        "scope": "Structural verification and frozen file identity only; semantic correctness and integrated rule behavior require independent review.",
    }

parser = argparse.ArgumentParser(description=__doc__)
mode = parser.add_mutually_exclusive_group(required=True)
mode.add_argument("--freeze", action="store_true")
mode.add_argument("--verify", action="store_true")
args = parser.parse_args()
record = validate()
check = ROOT / "check.json"
if args.freeze:
    require(not check.exists(), "Freeze record already exists; refusing replacement")
    record["freeze_status"] = "frozen_before_rule_mapping"
    with check.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"result": "frozen", "case_count": 24, "sha256": record["sha256"]}, ensure_ascii=False))
else:
    require(check.exists(), "Missing freeze record")
    frozen = json.loads(check.read_text(encoding="utf-8"))
    for field, value in record.items():
        require(frozen.get(field) == value, f"Frozen record mismatch: {field}")
    require(frozen.get("freeze_status") == "frozen_before_rule_mapping", "Invalid freeze status")
    print(json.dumps({"result": "verified", "case_count": 24, "sha256": record["sha256"]}, ensure_ascii=False))
