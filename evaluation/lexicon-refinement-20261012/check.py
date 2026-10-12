"""Verify reused-input development evidence; do not automate semantic judgments."""
from pathlib import Path
import argparse
import collections
import hashlib
import json


def sha(data):
    return hashlib.sha256(data).hexdigest()


def object_sha(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":")).encode())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--snapshot-only", action="store_true")
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    read = lambda path: json.loads(path.read_text())
    manifest = read(here / "manifest.json")
    data = read(here / "matches.json")
    records = read(here / "consulted-records.json")
    baseline = here / manifest["baseline_directory"]
    for item in manifest["original_artifacts"]:
        assert sha((baseline / item["path"]).read_bytes()) == item["sha256"], item["path"]
    contexts = read(baseline / "contexts.json")
    old = read(baseline / "matches.json")
    assert sha((baseline / "contexts.json").read_bytes()) == manifest["frozen_contexts_sha256"]
    assert manifest["baseline_inventory"] == 177
    assert manifest["expanded_inventory"] == 193
    assert manifest["added_entries"] == 16
    assert manifest["fixed_denominator"] == contexts["fixed_denominator"] == 40
    assert manifest["original_results"] == old["summary"]
    role = "reused_input_development_coverage_after_targeted_dictionary_expansion"
    assert manifest["evaluation_role"] == data["evaluation_role"] == records["evaluation_role"] == role
    preserved = {e["id"]: e for e in manifest["unchanged_objects"]}
    assert len(preserved) == len(manifest["unchanged_objects"]) == 177
    assert all(e["baseline_object_sha256"] == e["current_object_sha256"]
               for e in preserved.values())
    consulted = {e["record"]["id"]: e for e in records["records"]}
    assert len(consulted) == len(records["records"]) == 35
    revision = manifest["revision"]
    superseded = manifest["superseded_revision"]
    assert revision["number"] == data["revision"] == 2 and superseded["number"] == 1
    snapshot = here / superseded["directory"]
    for item in superseded["files"]:
        assert sha((snapshot / item["path"]).read_bytes()) == item["sha256"], item["path"]
    prior_records = {e["record"]["id"]: e for e in read(snapshot / "consulted-records.json")["records"]}
    prior_data = read(snapshot / "matches.json")
    assert set(prior_records) == set(consulted)
    assert prior_data["summary"]["development_counts"] == superseded["development_counts"]
    changed = {k for k, e in consulted.items()
               if e["full_object_sha256"] != prior_records[k]["full_object_sha256"]}
    assert changed == set(revision["changed_entry_ids"])
    assert all(consulted[k] == prior_records[k] for k in set(consulted) - changed)
    if not args.snapshot_only:
        root = args.source_root if args.source_root is not None else Path(manifest["source_root"])
        for item in manifest["sources"]:
            assert sha((root / item["path"]).read_bytes()) == item["sha256"], item["path"]
        all_entries = {}
        baseline_prefix = "evaluation/baselines/20261012-before-rule-and-lexicon-refinement"
        for path in ["lexicon/core.json", "lexicon/domains/software.json"]:
            before_path = f"{baseline_prefix}/{path}"
            before = read(root / before_path)
            after = read(root / path)
            assert sha((root / before_path).read_bytes()) == next(
                e["sha256"] for e in old["sources"] if e["path"] == path)
            assert after["entries"][:len(before["entries"])] == before["entries"]
            for e in before["entries"]:
                assert object_sha(e) == preserved[e["id"]]["baseline_object_sha256"]
            for i, e in enumerate(after["entries"]):
                all_entries[e["id"]] = e
                if e["id"] in consulted:
                    captured = consulted[e["id"]]
                    assert captured["source_path"] == path
                    assert captured["json_pointer"] == f"/entries/{i}"
                    assert captured["dataset_version"] == after["version"]
                    assert captured["full_object_sha256"] == object_sha(e)
                    assert captured["record"] == {
                        k: v for k, v in e.items() if k not in {"examples", "provenance"}}
        assert len(all_entries) == 193
        assert len(set(all_entries) - set(preserved)) == 16
    by_context = {e["id"]: e for e in contexts["contexts"]}
    old_by_id = {e["context_id"]: e for e in old["matches"]}
    rows = data["matches"]
    assert len(rows) == len({r["context_id"] for r in rows}) == 40
    assert {r["context_id"] for r in rows} == set(by_context)
    new_ids = set()
    for row in rows:
        context = by_context[row["context_id"]]
        previous = old_by_id[row["context_id"]]
        assert row["evaluation_role"] == role
        assert all(row[k] == context[k] for k in ("domain", "target_concept", "intended_meaning"))
        assert row["baseline_result"] == previous["result"]
        assert row["result"] in {"matched", "unmatched", "ambiguous"}
        assert all(k in consulted for k in row["candidate_entry_ids"])
        if row["origin"] == "new_entry_development_rematch":
            assert len(row["candidate_entry_ids"]) == 1
            new_ids.update(row["candidate_entry_ids"])
            assert not set(row["candidate_entry_ids"]) & set(preserved)
        else:
            assert row["origin"] == "carried_after_full_original_object_preservation_check"
            assert row["result"] == previous["result"]
            assert row["matched_entry_id"] == previous["matched_entry_id"]
            if row["matched_entry_id"]:
                assert row["matched_entry_id"] in preserved
        if row["result"] == "matched":
            assert row["matched_entry_id"] in row["candidate_entry_ids"]
            entry = consulted[row["matched_entry_id"]]["record"]
            assert row["matched_sense_id"] == entry["sense_id"]
            assert row["editorial_status"] == entry["status"]
        else:
            assert row["matched_entry_id"] is row["matched_sense_id"] is row["editorial_status"] is None
    assert len(new_ids) == 16
    prior_rows = {r["context_id"]: r for r in prior_data["matches"]}
    rechecked = {r["context_id"]: r for r in rows if set(r["candidate_entry_ids"]) & changed}
    assert set(rechecked) == {e["context_id"] for e in data["revision_recheck"]}
    for row in rows:
        if row["context_id"] not in rechecked:
            assert row == prior_rows[row["context_id"]]
    for e in data["revision_recheck"]:
        row, prior = rechecked[e["context_id"]], prior_rows[e["context_id"]]
        assert e["entry_id"] in row["candidate_entry_ids"]
        assert (e["previous_result"], e["previous_matched_sense_id"]) == (
            prior["result"], prior["matched_sense_id"])
        assert (e["result"], e["matched_sense_id"]) == (row["result"], row["matched_sense_id"])
    counts = dict(collections.Counter(row["result"] for row in rows))
    domains = {d: {k: sum(r["domain"] == d and r["result"] == k for r in rows)
                   for k in ("matched", "unmatched", "ambiguous")}
               for d in contexts["domains"]}
    statuses = dict(collections.Counter(row["editorial_status"] for row in rows
                                       if row["result"] == "matched"))
    summary = data["summary"]
    assert summary["evaluation_role"] == role
    assert summary["denominator"] == 40
    assert summary["baseline_counts"] == old["summary"]["counts"]
    assert summary["development_counts"] == counts
    assert summary["by_domain"] == domains
    assert summary["matched_editorial_status"] == statuses
    assert summary["development_matched_percent"] == counts["matched"] / 40 * 100
    assert summary["new_entry_matches"] == sum(r["origin"] == "new_entry_development_rematch"
                                               and r["result"] == "matched" for r in rows)
    assert summary["baseline_matches_retained"] == sum(r["origin"] != "new_entry_development_rematch"
                                                      and r["result"] == "matched" for r in rows)
    print(json.dumps({"verification": "passed", "source_mode":
                      "preserved_snapshot_only" if args.snapshot_only else "current_sources_match",
                      "revision": 2,
                      "superseded_revision_files_byte_identical": len(superseded["files"]),
                      "changed_entries_rechecked": sorted(changed),
                      "superseded_development_counts": superseded["development_counts"],
                      "original_artifacts_byte_identical": len(manifest["original_artifacts"]),
                      "original_objects_unchanged": 177,
                      "frozen_contexts_sha256": manifest["frozen_contexts_sha256"],
                      **summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
