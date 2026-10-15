"""Test README presentation fidelity separately from model semantic quality."""

import importlib.util
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "readme_comparison", ROOT / "evaluation/readme-model-comparison-20261015/render.py"
)
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)


class RenderedTextTests(unittest.TestCase):
    def test_preserves_whitespace_delimiters_and_ambiguous_operators(self):
        for raw in ("2 ** 3 ** 2 = 512", "값 ** 주의 **", "** leading**", "**trailing **",
                    "word**!**word"):
            with self.subTest(raw=raw):
                self.assertEqual(raw, renderer.projected_text(raw))
                self.assertNotIn("<strong>", renderer.render_text(raw))

    def test_fence_requires_a_whitespace_only_closer(self):
        for raw in ("```\n```python\n# 주석\n```",
                    "~~~~\n~~~\n# 주석\n~~~~code\n# 다른 주석\n~~~~",
                    "```\n~~~\n# 주석\n``` \t"):
            with self.subTest(raw=raw):
                self.assertEqual(raw, renderer.projected_text(raw))
                self.assertNotIn("<strong>", renderer.render_text(raw))

    def test_backtick_info_cannot_contain_backticks(self):
        raw = "```x``` 설명\n```python\n# 주석\n```\n# 제목"
        expected = "```x``` 설명\n```python\n# 주석\n```\n제목"
        self.assertEqual(expected, renderer.projected_text(raw))
        self.assertIn("# 주석", renderer.render_text(raw))
        self.assertTrue(renderer.render_text(raw).endswith("<strong>제목</strong>"))

    def test_formats_headings_and_bold_but_keeps_conditions_and_numbering(self):
        raw = "## 제출 조건\n\n01) **4시간 안에** 응답해야 한다.\n7. 근무시간 밖 제출 건은 다음 영업일 12:00까지.\n1. 예외\n1. 반복\n"
        html = renderer.render_text(raw)
        self.assertIn("<strong>제출 조건</strong><br><br>01)", html)
        self.assertIn("7. 근무시간 밖", html)
        self.assertEqual(2, html.count("1. "))
        self.assertTrue(html.endswith("<br>"))
        renderer.verify_rendered_text(raw, html)

    def test_falls_back_without_dropping_unsupported_syntax(self):
        raw = "```md\n# **literal**\n```\n> **quote**\n[**link**](javascript:alert(1))\n| **cell** |\n    **code**\n**unclosed\n***unsupported***\n"
        html = renderer.render_text(raw)
        renderer.verify_rendered_text(raw, html)
        self.assertEqual(raw, renderer.projected_text(raw))
        self.assertNotIn("<strong>", html)

    def test_escapes_html_and_ampersands_without_losing_characters(self):
        raw = '<script>alert("조건 < 4 & 7 > 1")</script>\n**<img src=x onerror=alert(1)>**'
        html = renderer.render_text(raw)
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img", html)
        self.assertIn("&lt;script&gt;", html)
        renderer.verify_rendered_text(raw, html)

    def test_plain_source_does_not_interpret_markdown(self):
        raw = "# 원문 **그대로**\r\n\r\n2) 조건"
        html = renderer.render_text(raw, markdown=False)
        self.assertNotIn("<strong>", html)
        renderer.verify_rendered_text(raw, html, markdown=False)

    def test_verifier_rejects_changed_scope_and_injected_markup(self):
        raw = "**재검토 전에는** 배포할 수 없다."
        html = renderer.render_text(raw)
        for changed in (html.replace("없다", "있다"), html + "추가 조건", html + "<!--hidden-->",
                        '<a href="javascript:alert(1)">' + html + "</a>", "<strong>" + html):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                renderer.verify_rendered_text(raw, changed)

    def test_does_not_apply_language_specific_edits(self):
        raw = "- 담당자는 미확인.\n- do not deploy before review.\n- 日本語の条件を保つ。\n"
        renderer.verify_rendered_text(raw, renderer.render_text(raw))
        self.assertEqual(raw, renderer.projected_text(raw))


class TableTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.cases = [dict(id=f"{n:02}", title="사례", anchor=f"case-{n}",
                           source=f"원문 {n}: **원문 표식**과 조건을 유지한다.") for n in range(1, 7)]
        for case in self.cases:
            for kind in ("kp", "ste"):
                (self.directory / f"{case['id']}-{kind}.txt").write_bytes(
                    f"## 출력 {kind}\r\n\r\n7. **{case['id']}** 조건 유지\r\n".encode("utf-8"))

    def test_renders_six_sources_twelve_outputs_and_keeps_raw_bytes(self):
        before = {path.name: path.read_bytes() for path in self.directory.glob("*.txt")}
        table = renderer.render_table(self.cases, self.directory, "evaluation/run/outputs")
        renderer.verify_table(table, self.cases, self.directory, "evaluation/run/outputs")
        self.assertEqual(18, table.count('<td valign="top">'))
        self.assertEqual(6, table.count('colspan="3"'))
        self.assertEqual(3, table.count('width="33%" scope="col" nowrap'))
        self.assertEqual(12, table.count(">모델 출력 원문</a>"))
        for number in range(1, 7):
            self.assertIn(f'id="case-{number}"></a>{number}. 사례</th>', table)
        self.assertIn('href="evaluation/run/outputs/01-kp.txt"', table)
        self.assertIn("**원문 표식**", table)
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.directory.glob("*.txt")})
        with self.assertRaises(ValueError):
            renderer.verify_table(table.replace("조건 유지", "조건 삭제", 1), self.cases,
                                  self.directory, "evaluation/run/outputs")

    def test_rejects_incomplete_extra_and_empty_outputs(self):
        missing = self.directory / "01-kp.txt"
        original = missing.read_bytes()
        missing.unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            renderer.render_table(self.cases, self.directory, "outputs")
        missing.write_bytes(original)
        extra = self.directory / "unexpected.txt"
        extra.write_text("extra", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unexpected"):
            renderer.render_table(self.cases, self.directory, "outputs")
        extra.unlink()
        missing.write_text("\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Empty model output"):
            renderer.render_table(self.cases, self.directory, "outputs")

    def test_rejects_duplicate_or_incomplete_cases(self):
        for cases in (self.cases[:5], self.cases + self.cases[:1],
                      [self.cases[0]] * 6, [dict(case, source="") for case in self.cases]):
            with self.subTest(cases=cases), self.assertRaises(ValueError):
                renderer.render_table(cases, self.directory, "outputs")

    def test_rejects_newlines_in_row_metadata(self):
        for key in ("title", "anchor"):
            for separator in ("\n", "\r", "\r\n"):
                with self.subTest(key=key, separator=separator):
                    cases = [dict(case) for case in self.cases]
                    cases[0][key] = "사례" + separator + separator + "요약"
                    with self.assertRaisesRegex(ValueError, "single line"):
                        renderer.render_table(cases, self.directory, "outputs")

    def test_escapes_metadata_and_rejects_executable_link_prefix(self):
        self.cases[0]["anchor"] = 'id" onmouseover="alert(1)'
        self.cases[0]["title"] = "<script>title</script>"
        table = renderer.render_table(self.cases, self.directory, "outputs?x=\"&y")
        self.assertNotIn("<script>", table)
        self.assertIn("&quot; onmouseover=&quot;", table)
        self.assertNotIn('id="id" onmouseover=', table)
        with self.assertRaises(ValueError):
            renderer.render_table(self.cases, self.directory, "javascript:alert(1)")


class FrozenExperimentTests(unittest.TestCase):
    """Check shipped evidence, rather than claiming a synthetic model result."""

    directory = ROOT / "evaluation/readme-model-comparison-20261015"
    link_prefix = "evaluation/readme-model-comparison-20261015/outputs"

    def assert_public_evidence_matches_frozen_plan(self, directory):
        # Public hashes/labels bind the displayed sources and arms to the frozen
        # plan; they do not independently establish the saved private wire bytes.
        plan = json.loads((directory / "plan.json").read_text(encoding="utf-8"))
        cases_raw = (directory / "cases.json").read_bytes()
        self.assertEqual(plan["cases_sha256"], hashlib.sha256(cases_raw).hexdigest())
        cases = json.loads(cases_raw)
        self.assertEqual(["kp", "ste"], plan["conditions"])
        expected = {f"{case['id']}-{kind}": (case, kind)
                    for case in cases for kind in plan["conditions"]}
        records = {path.stem: json.loads(path.read_text(encoding="utf-8"))
                   for path in (directory / "records").glob("*.json")}
        self.assertEqual(12, len(expected))
        self.assertEqual(set(expected), set(records))
        self.assertEqual(set(expected), {path.stem for path in (directory / "outputs").glob("*.txt")})
        for name, record in records.items():
            case, kind = expected[name]
            raw = (directory / "outputs" / (name + ".txt")).read_bytes()
            self.assertEqual(name, record["id"])
            self.assertEqual(case["id"], record["source_id"])
            self.assertEqual(kind, record["condition"])
            self.assertEqual(hashlib.sha256(case["source"].encode("utf-8")).hexdigest(),
                             record["source_sha256"])
            self.assertEqual(plan["model_requested"], record["requested_model"])
            self.assertEqual(plan["model_requested"], record["returned_model"])
            self.assertEqual(plan["effort"], record["effort"])
            self.assertEqual("completed", record["status"])
            self.assertEqual(0, record["retry_count"])
            self.assertEqual([], record["tools"])
            self.assertFalse(record["previous_response_id_sent"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), record["output_sha256"])
            self.assertEqual(len(raw.decode("utf-8")), record["characters"])

    def test_all_twelve_output_bytes_and_labels_match_frozen_plan(self):
        self.assert_public_evidence_matches_frozen_plan(self.directory)

    def test_frozen_evidence_checks_reject_changed_source_or_mislabeled_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary)
            for name in ("records", "outputs"):
                shutil.copytree(self.directory / name, fixture / name)
            cases_raw = (self.directory / "cases.json").read_bytes()
            plan_raw = (self.directory / "plan.json").read_bytes()
            (fixture / "cases.json").write_bytes(cases_raw)
            (fixture / "plan.json").write_bytes(plan_raw)
            record_path = fixture / "records/01-kp.json"
            record_raw = record_path.read_bytes()
            self.assert_public_evidence_matches_frozen_plan(fixture)
            for field, value in (("source_sha256", "0" * 64), ("condition", "ste"),
                                 ("source_id", "02"), ("requested_model", "other-model"),
                                 ("returned_model", "other-model"), ("effort", "low")):
                with self.subTest(field=field):
                    changed = json.loads(record_raw)
                    changed[field] = value
                    record_path.write_text(json.dumps(changed), encoding="utf-8")
                    with self.assertRaises(AssertionError):
                        self.assert_public_evidence_matches_frozen_plan(fixture)
                    record_path.write_bytes(record_raw)
            changed_cases = json.loads(cases_raw)
            changed_cases[0]["source"] += " 추가 조건"
            changed_raw = json.dumps(changed_cases, ensure_ascii=False).encode("utf-8")
            (fixture / "cases.json").write_bytes(changed_raw)
            with self.assertRaises(AssertionError):
                self.assert_public_evidence_matches_frozen_plan(fixture)
            # Even a matching cases checksum cannot hide a mismatch against the
            # per-response source hashes that were recorded at generation time.
            changed_plan = json.loads(plan_raw)
            changed_plan["cases_sha256"] = hashlib.sha256(changed_raw).hexdigest()
            (fixture / "plan.json").write_text(json.dumps(changed_plan), encoding="utf-8")
            with self.assertRaises(AssertionError):
                self.assert_public_evidence_matches_frozen_plan(fixture)

    def test_readme_table_matches_six_sources_and_twelve_actual_outputs(self):
        cases = json.loads((self.directory / "cases.json").read_text(encoding="utf-8"))
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        start = readme.index("<table>")
        end = readme.index("</table>", start) + len("</table>")
        renderer.verify_table(readme[start:end], cases, self.directory / "outputs", self.link_prefix)


if __name__ == "__main__":
    unittest.main()
