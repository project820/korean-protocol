"""Check frozen input and count integrity; this does not automate semantic judgment."""
from pathlib import Path
import argparse
import collections
import hashlib
import json


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-only", action="store_true")
    parser.add_argument("--source-root", type=Path,
                        help="Verify this checkout instead of the historical source path.")
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    read = lambda name: json.loads((here / name).read_text())
    freeze = read("freeze.json")
    contexts = read("contexts.json")
    matches = read("matches.json")
    extraction = read("extraction.json")
    assert sha(here / "contexts.json") == freeze["contexts_sha256"]
    assert sha(here / "plan.md") == freeze["plan_sha256"]
    assert matches["contexts_sha256"] == freeze["contexts_sha256"]
    assert contexts["fixed_denominator"] == freeze["fixed_denominator"] == 40
    assert len(contexts["contexts"]) == len(matches["matches"]) == 40
    context_by_id = {c["id"]: c for c in contexts["contexts"]}
    assert len(context_by_id) == 40
    assert {m["context_id"] for m in matches["matches"]} == set(context_by_id)
    assert len({m["context_id"] for m in matches["matches"]}) == 40
    entry_by_id = {e["id"]: e for e in extraction["entries"]}
    assert len(entry_by_id) == len(extraction["entries"]) == 177
    assert matches["sources"] == extraction["sources"]
    if not args.snapshot_only:
        root = args.source_root if args.source_root is not None else Path(matches["source_root"])
        for source in matches["sources"]:
            assert sha(root / source["path"]) == source["sha256"], source["path"]
        for e in extraction["entries"]:
            source = json.loads((root / e["source_path"]).read_text())
            original = source["entries"][int(e["json_pointer"].split("/")[-1])]
            assert source["version"] == e["dataset_version"]
            assert all(original[k] == v for k, v in e.items()
                       if k not in {"source_path", "json_pointer", "dataset_version"})
    for m in matches["matches"]:
        c = context_by_id[m["context_id"]]
        assert all(m[k] == c[k] for k in ("domain", "target_concept", "intended_meaning"))
        assert m["result"] in {"matched", "unmatched", "ambiguous"}
        assert all(e == entry_by_id[e["id"]] for e in m["candidates"])
        if m["result"] == "matched":
            e = entry_by_id[m["matched_entry_id"]]
            assert e in m["candidates"]
            assert m["matched_sense_id"] == e["sense_id"]
            assert m["matched_editorial_status"] == e["status"]
        else:
            assert m["matched_entry_id"] is None
            assert m["matched_sense_id"] is None
            assert m["matched_editorial_status"] is None
    counts = dict(collections.Counter(m["result"] for m in matches["matches"]))
    domains = {d: dict(collections.Counter(m["result"] for m in matches["matches"]
                                         if m["domain"] == d))
               for d in contexts["domains"]}
    assert collections.Counter(c["domain"] for c in contexts["contexts"]) == contexts["domains"]
    statuses = dict(collections.Counter(m["matched_editorial_status"]
                                       for m in matches["matches"] if m["result"] == "matched"))
    summary = matches["summary"]
    assert summary["denominator"] == 40
    assert summary["counts"] == counts
    assert summary["by_domain"] == domains
    assert summary["matched_editorial_statuses"] == statuses
    assert summary["matched_fraction"] == f'{counts["matched"]}/40'
    assert summary["matched_percent"] == counts["matched"] / 40 * 100
    print(json.dumps({"verification": "passed", "source_mode":
                      "preserved_snapshot_only" if args.snapshot_only else "current_sources_match",
                      "contexts_sha256": freeze["contexts_sha256"], **summary},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
