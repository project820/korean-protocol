"""Render raw structural-trial outputs using the frozen safe text renderer.

Column labels and links are explicit so profile-only matched results cannot be
silently substituted for the older, full-dictionary historical reference.
This module renders presentation only; run.py verifies frozen trial evidence.
"""

from html import escape
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
from urllib.parse import quote, urlsplit


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RENDER_SHA256 = "2aa3d31e77da3bfaadff94235735782c33077c9a39930cbabf54dc934b4f6ea5"
BASELINE_LABEL = "KP 0.7 · 프로필만 재실행"
CANDIDATE_LABEL = "압축 후보 · 프로필만"
HISTORICAL_LABEL = "이전 KP 0.7 · 전체 사전 포함 · 다른 입력 범위"
COLUMN_LABELS = {"baseline-profile": BASELINE_LABEL, "candidate-profile": CANDIDATE_LABEL,
                 "kp": HISTORICAL_LABEL}


def _load_safe_renderer(path):
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != RENDER_SHA256:
        raise ValueError("Frozen renderer hash mismatch")
    spec = importlib.util.spec_from_file_location("frozen_readme_renderer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


safe = _load_safe_renderer(HERE.parent / "readme-model-comparison-20261015/render.py")


def _validate_column(directory, suffix, label, prefix, cases, document_directory):
    if not isinstance(suffix, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", suffix):
        raise ValueError("Output suffix must be a simple filename suffix")
    if suffix not in COLUMN_LABELS or label != COLUMN_LABELS[suffix]:
        raise ValueError("Column scope label does not match its recorded arm")
    if (not isinstance(prefix, str) or not prefix.strip() or urlsplit(prefix).scheme
            or prefix.startswith(("//", "/")) or "\r" in prefix or "\n" in prefix):
        raise ValueError("Output links require a repository-relative prefix")
    directory = Path(directory)
    expected_prefix = os.path.relpath(directory.resolve(), Path(document_directory).resolve()).replace(os.sep, "/")
    if prefix.rstrip("/") != expected_prefix:
        raise ValueError("Output link prefix does not point to its selected directory")
    expected = {f"{case['id']}-{suffix}.txt" for case in cases}
    actual = {path.name for path in directory.glob(f"*-{suffix}.txt")}
    if actual != expected:
        raise ValueError(f"Expected six {suffix} outputs; missing={sorted(expected-actual)}, "
                         f"unexpected={sorted(actual-expected)}")
    return directory


def _output_cell(directory, case, suffix, prefix):
    name = f"{case['id']}-{suffix}"
    filename = name + ".txt"
    raw_bytes = (directory / filename).read_bytes()
    record = json.loads((directory.parent / "records" / (name + ".json")).read_bytes())
    if (record.get("id") != name or record.get("source_id") != case["id"]
            or record.get("condition") != suffix
            or record.get("source_sha256") != hashlib.sha256(case["source"].encode("utf-8")).hexdigest()):
        raise ValueError(f"Response record source or arm mismatch: {filename}")
    status = record.get("http_status")
    if (record.get("status") != "completed"
            or record.get("response_status", record.get("status")) != "completed"
            or type(status) is not int or not 200 <= status < 300):
        raise ValueError(f"Response transport did not complete successfully: {filename}")
    if hashlib.sha256(raw_bytes).hexdigest() != record.get("output_sha256"):
        raise ValueError(f"Output hash mismatch: {filename}")
    raw = raw_bytes.decode("utf-8")
    if not raw.strip():
        raise ValueError(f"Empty model output: {filename}")
    href = prefix.rstrip("/") + "/" + quote(filename)
    notes = []
    if record.get("token_budget_pass") is False:
        notes.append("입력 토큰 기준 미충족 · 출력 원문 유지")
    if record.get("quality_gate_pass") is False or record.get("quality_pass") is False:
        notes.append("품질 기준 미충족 · 출력 원문 유지")
    annotation = "".join("<br><strong>" + escape(note) + "</strong>" for note in notes)
    return ('<td valign="top">' + safe.render_text(raw)
            + '<br><br><a href="' + escape(href, quote=True)
            + '">모델 출력 원문</a>' + annotation + '</td>')


def render_table(cases, baseline_directory, baseline_suffix, candidate_directory,
                 candidate_suffix, baseline_label, candidate_label,
                 baseline_link_prefix, candidate_link_prefix, *, document_directory=ROOT):
    """Render six exact sources, one selected baseline arm, and one candidate arm.

    Raw outputs must match their sibling records' hashes, source, arm, and
    successful transport. Quality/token failure flags remain separate annotations.
    Labels must equal the exported scope constants. Link prefixes must point to
    the selected directories relative to document_directory (repository default).
    Case anchors are preserved; callers composing two tables should supply unique
    anchor prefixes in the second table's case metadata to avoid duplicate IDs.
    """
    safe._validate_cases(cases)
    if baseline_suffix not in ("baseline-profile", "kp") or candidate_suffix != "candidate-profile":
        raise ValueError("Expected a baseline/historical arm and a compact candidate arm")
    baseline_directory = _validate_column(baseline_directory, baseline_suffix,
                                          baseline_label, baseline_link_prefix, cases, document_directory)
    candidate_directory = _validate_column(candidate_directory, candidate_suffix,
                                           candidate_label, candidate_link_prefix, cases, document_directory)
    for case in cases:
        if (baseline_directory / f"{case['id']}-{baseline_suffix}.txt").samefile(
                candidate_directory / f"{case['id']}-{candidate_suffix}.txt"):
            raise ValueError("Baseline and candidate refer to the same output file")
    labels = ("원문 · 사실과 조건의 기준", baseline_label, candidate_label)
    rows = ["<table>", "<thead>", "<tr>" + "".join(
        '<th width="33%" scope="col" nowrap>' + escape(label) + "</th>" for label in labels
    ) + "</tr>", "</thead>", "<tbody>"]
    for case in cases:
        rows.extend([
            '<tr><th colspan="3" align="left"><a id="' + escape(case["anchor"], quote=True)
            + '"></a>' + str(int(case["id"])) + ". " + escape(case["title"]) + "</th></tr>",
            "<tr>",
            '<td valign="top">' + safe.render_text(case["source"], markdown=False) + "</td>",
            _output_cell(baseline_directory, case, baseline_suffix, baseline_link_prefix),
            _output_cell(candidate_directory, case, candidate_suffix, candidate_link_prefix),
            "</tr>",
        ])
    rows.extend(["</tbody>", "</table>"])
    return "\n".join(rows)


def verify_table(table, *args, **kwargs):
    """Reject changes to a deterministic table generated from the selected files."""
    if table != render_table(*args, **kwargs):
        raise ValueError("Table differs from the six sources and selected raw output files")
