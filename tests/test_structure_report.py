"""Check table fidelity and frozen profile-only trial evidence without model calls."""

import hashlib
from html import escape
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "evaluation/readme-structure-r1-20261015"
OLD = ROOT / "evaluation/readme-model-comparison-20261015"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


report = load_module("structure_report", EXPERIMENT / "report.py")
runner = load_module("structure_runner", EXPERIMENT / "run.py")


class TableTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.document_directory = Path(self.temporary.name)
        self.directory = self.document_directory / "outputs"
        self.directory.mkdir()
        (self.document_directory / "records").mkdir()
        self.cases = [dict(id=f"{number:02}", title=f"사례 {number}", anchor=f"case-{number}",
                           source=f"원문 {number}: **조건**은 4시간 < 8시간이다.\n담당 미확인.")
                      for number in range(1, 7)]
        for case in self.cases:
            for suffix in ("baseline-profile", "candidate-profile", "kp"):
                raw = f"## {suffix}\r\n\r\n7. **조건** 유지\r\n<script>주입 금지</script>\r\n".encode("utf-8")
                name = f"{case['id']}-{suffix}"
                (self.directory / (name + ".txt")).write_bytes(raw)
                record = dict(id=name, source_id=case["id"], condition=suffix,
                              source_sha256=hashlib.sha256(case["source"].encode("utf-8")).hexdigest(),
                              output_sha256=hashlib.sha256(raw).hexdigest(), status="completed",
                              response_status="completed", http_status=200)
                (self.document_directory / "records" / (name + ".json")).write_text(
                    json.dumps(record), encoding="utf-8")
        self.arguments = (self.cases, self.directory, "baseline-profile", self.directory,
                          "candidate-profile", report.BASELINE_LABEL, report.CANDIDATE_LABEL,
                          "outputs", "outputs")

    def render(self, arguments=None):
        return report.render_table(*(self.arguments if arguments is None else arguments),
                                   document_directory=self.document_directory)

    def assert_cells_match_raw(self, table, baseline_directory, baseline_suffix, candidate_directory):
        cells = re.findall(r'<td valign="top">(.*?)</td>', table, re.S)
        self.assertEqual(18, len(cells))
        for index, case in enumerate(self.cases):
            report.safe.verify_rendered_text(case["source"], cells[3 * index], markdown=False)
            for column, directory, suffix in ((1, baseline_directory, baseline_suffix),
                                              (2, candidate_directory, "candidate-profile")):
                raw = (directory / f"{case['id']}-{suffix}.txt").read_bytes().decode("utf-8")
                rendered = cells[3 * index + column].rsplit('<br><br><a href="', 1)[0]
                report.safe.verify_rendered_text(raw, rendered)

    def test_matched_table_preserves_raw_bytes_content_numbering_and_links(self):
        original = {path.name: path.read_bytes() for path in self.directory.glob("*.txt")}
        table = self.render()
        report.verify_table(table, *self.arguments, document_directory=self.document_directory)
        self.assert_cells_match_raw(table, self.directory, "baseline-profile", self.directory)
        self.assertEqual(3, table.count('width="33%" scope="col" nowrap'))
        self.assertEqual(6, table.count('colspan="3"'))
        self.assertEqual(12, table.count(">모델 출력 원문</a>"))
        self.assertIn('id="case-1"></a>1. 사례 1</th>', table)
        self.assertIn('href="outputs/01-baseline-profile.txt"', table)
        self.assertIn('href="outputs/01-candidate-profile.txt"', table)
        self.assertIn("7. <strong>조건</strong> 유지", table)
        self.assertNotIn("<script>", table)
        self.assertEqual(original, {path.name: path.read_bytes() for path in self.directory.glob("*.txt")})
        with self.assertRaises(ValueError):
            report.verify_table(table.replace("조건", "삭제", 1), *self.arguments,
                                document_directory=self.document_directory)

    def test_historical_table_labels_the_different_scope_and_links_original_files(self):
        arguments = list(self.arguments)
        arguments[2] = "kp"
        arguments[5] = report.HISTORICAL_LABEL
        table = self.render(arguments)
        self.assertIn(escape(arguments[5]), table)
        self.assertIn('href="outputs/01-kp.txt"', table)
        self.assertNotIn("01-baseline-profile.txt", table)
        self.assert_cells_match_raw(table, self.directory, "kp", self.directory)

    def test_rejects_missing_empty_or_extra_selected_arm_outputs(self):
        path = self.directory / "01-candidate-profile.txt"
        original = path.read_bytes()
        path.unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            self.render()
        path.write_text("\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Output hash mismatch"):
            self.render()
        path.write_bytes(original)
        (self.directory / "07-candidate-profile.txt").write_text("extra", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unexpected"):
            self.render()

    def test_rejects_unsafe_labels_suffixes_and_link_prefixes(self):
        for index, value in ((2, "../kp"), (5, "label\n\nbreak"), (6, "label\rbreak"),
                             (7, "javascript:alert(1)"), (8, "//example.com")):
            with self.subTest(index=index):
                arguments = list(self.arguments)
                arguments[index] = value
                with self.assertRaises(ValueError):
                    self.render(arguments)

    def test_rejects_output_drift_after_capture(self):
        with (self.directory / "01-candidate-profile.txt").open("ab") as handle:
            handle.write(b" changed after capture")
        with self.assertRaisesRegex(ValueError, "Output hash mismatch"):
            self.render()

    def test_rejects_historical_output_labeled_as_profile_only(self):
        arguments = list(self.arguments)
        arguments[2] = "kp"
        with self.assertRaisesRegex(ValueError, "scope label"):
            self.render(arguments)

    def test_rejects_a_link_prefix_pointing_to_another_directory(self):
        arguments = list(self.arguments)
        arguments[7] = "evaluation/wrong/outputs"
        with self.assertRaisesRegex(ValueError, "link prefix"):
            self.render(arguments)

    def test_refuses_changed_renderer_before_importing_it(self):
        path = self.directory / "changed-renderer.py"
        path.write_text("raise AssertionError('must never execute')", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "renderer hash"):
            report._load_safe_renderer(path)

    def test_rejects_record_source_arm_or_transport_mismatch(self):
        path = self.document_directory / "records/01-candidate-profile.json"
        original = path.read_bytes()
        for field, value in (("source_id", "02"), ("condition", "baseline-profile"),
                             ("source_sha256", "0" * 64), ("id", "01-baseline-profile"),
                             ("status", "failed"), ("response_status", "incomplete"),
                             ("http_status", 503)):
            with self.subTest(field=field):
                record = json.loads(original)
                record[field] = value
                path.write_text(json.dumps(record), encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.render()
                path.write_bytes(original)

    def test_retains_raw_output_when_quality_or_token_gate_fails(self):
        path = self.document_directory / "records/01-candidate-profile.json"
        record = json.loads(path.read_bytes())
        record.update(token_budget_pass=False, quality_gate_pass=False)
        path.write_text(json.dumps(record), encoding="utf-8")
        table = self.render()
        self.assertIn("입력 토큰 기준 미충족", table)
        self.assertIn("품질 기준 미충족", table)
        self.assert_cells_match_raw(table, self.directory, "baseline-profile", self.directory)

    def test_rejects_identical_underlying_output_files(self):
        candidate = self.directory / "01-candidate-profile.txt"
        candidate.unlink()
        candidate.symlink_to(self.directory / "01-baseline-profile.txt")
        with self.assertRaisesRegex(ValueError, "same output file"):
            self.render()

    def test_supports_another_experiment_using_its_own_sibling_records(self):
        another = self.document_directory / "another-experiment"
        for name in ("outputs", "records"):
            shutil.copytree(self.document_directory / name, another / name)
        arguments = list(self.arguments)
        arguments[3] = another / "outputs"
        arguments[8] = "another-experiment/outputs"
        table = self.render(arguments)
        self.assertIn('href="another-experiment/outputs/01-candidate-profile.txt"', table)
        self.assert_cells_match_raw(table, self.directory, "baseline-profile", another / "outputs")
        path = another / "records/01-candidate-profile.json"
        record = json.loads(path.read_bytes())
        record["source_sha256"] = "0" * 64
        path.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "record source or arm mismatch"):
            self.render(arguments)


class ActualTrialTests(unittest.TestCase):
    def assert_saved_report_table(self, study, block, cases, baseline_directory,
                                  baseline_suffix, baseline_label, baseline_prefix):
        readme = (study / "README.md").read_bytes().decode("utf-8")
        start = f"<!-- {block}:start -->"
        end = f"<!-- {block}:end -->"
        self.assertEqual(1, readme.count(start))
        self.assertEqual(1, readme.count(end))
        section = readme.split(start, 1)[1].split(end, 1)[0]
        self.assertTrue(section.startswith("\n") and section.endswith("\n"))
        table = section[1:-1]
        expected = report.render_table(
            cases, baseline_directory, baseline_suffix, study / "outputs", "candidate-profile",
            baseline_label, report.CANDIDATE_LABEL, baseline_prefix, "outputs",
            document_directory=study,
        )
        self.assertEqual(expected, table)
        cells = re.findall(r'<td valign="top">(.*?)</td>', table, re.S)
        self.assertEqual(18, len(cells))
        for index, case in enumerate(cases):
            report.safe.verify_rendered_text(case["source"], cells[3 * index], markdown=False)
            for column, directory, suffix in ((1, baseline_directory, baseline_suffix),
                                              (2, study / "outputs", "candidate-profile")):
                raw = (directory / f"{case['id']}-{suffix}.txt").read_bytes().decode("utf-8")
                body = cells[3 * index + column].rsplit('<br><br><a href="', 1)[0]
                report.safe.verify_rendered_text(raw, body)

    def test_saved_r1_and_r2_matched_tables_equal_their_raw_evidence(self):
        for revision in ("r1", "r2"):
            with self.subTest(revision=revision):
                study = ROOT / f"evaluation/readme-structure-{revision}-20261015"
                cases = json.loads((study / "cases.json").read_bytes())
                self.assert_saved_report_table(study, "matched-comparison", cases,
                                               study / "outputs", "baseline-profile",
                                               report.BASELINE_LABEL, "outputs")

    def test_saved_r2_historical_table_uses_original_outputs_and_unique_anchor_prefix(self):
        study = ROOT / "evaluation/readme-structure-r2-20261015"
        cases = json.loads((study / "cases.json").read_bytes())
        historical_cases = [dict(case, anchor="historical-" + case["anchor"]) for case in cases]
        self.assert_saved_report_table(study, "historical-comparison", historical_cases,
                                       OLD / "outputs", "kp", report.HISTORICAL_LABEL,
                                       "../readme-model-comparison-20261015/outputs")

    def test_all_twelve_outputs_and_frozen_inputs_pass_runner_verification_offline(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("Tests must not call models")):
            cases, plan = runner.verify()
        self.assertEqual(6, len(cases))
        self.assertEqual(12, plan["planned_calls"])
        self.assertEqual(["baseline-profile", "candidate-profile"], plan["conditions"])
        self.assertEqual(6000, plan["candidate_input_token_ceiling"])

    def test_actual_candidate_full_request_usage_is_at_most_6000_input_tokens(self):
        cases = json.loads((EXPERIMENT / "cases.json").read_bytes())
        self.assertEqual(6, len(cases))
        for case in cases:
            name = case["id"] + "-candidate-profile"
            record = json.loads((EXPERIMENT / "records" / (name + ".json")).read_bytes())
            with self.subTest(output=name):
                self.assertEqual("completed", record["status"])
                self.assertIs(type(record["usage"]["input_tokens"]), int)
                self.assertGreaterEqual(record["usage"]["input_tokens"], 0)
                self.assertLessEqual(record["usage"]["input_tokens"], 6000)
                self.assertTrue(record["token_budget_pass"])
                self.assertEqual(6000, record["token_budget_ceiling"])

    def test_matched_and_historical_tables_match_every_actual_raw_output(self):
        cases = json.loads((EXPERIMENT / "cases.json").read_bytes())
        all_paths = list((EXPERIMENT / "outputs").glob("*.txt")) + list((OLD / "outputs").glob("*.txt"))
        hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in all_paths}
        for directory, suffix, label, prefix in (
            (EXPERIMENT / "outputs", "baseline-profile", report.BASELINE_LABEL, "outputs"),
            (OLD / "outputs", "kp", report.HISTORICAL_LABEL,
             "../readme-model-comparison-20261015/outputs"),
        ):
            with self.subTest(baseline=suffix):
                arguments = (cases, directory, suffix, EXPERIMENT / "outputs", "candidate-profile",
                             label, report.CANDIDATE_LABEL, prefix, "outputs")
                table = report.render_table(*arguments, document_directory=EXPERIMENT)
                report.verify_table(table, *arguments, document_directory=EXPERIMENT)
                cells = re.findall(r'<td valign="top">(.*?)</td>', table, re.S)
                self.assertEqual(18, len(cells))
                for index, case in enumerate(cases):
                    report.safe.verify_rendered_text(case["source"], cells[3 * index], markdown=False)
                    for column, folder, arm in ((1, directory, suffix),
                                                (2, EXPERIMENT / "outputs", "candidate-profile")):
                        raw = (folder / f"{case['id']}-{arm}.txt").read_bytes().decode("utf-8")
                        body = cells[3 * index + column].rsplit('<br><br><a href="', 1)[0]
                        report.safe.verify_rendered_text(raw, body)
        self.assertEqual(hashes, {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in all_paths})


if __name__ == "__main__":
    unittest.main()
