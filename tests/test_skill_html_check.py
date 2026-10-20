"""Portable checks of diagnostics; no browser or third-party runtime is required."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/korean-protocol/scripts/check_html.py'


def page(body='', script='', head=''):
    return ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            '<title>입력 조건을 확인한다</title>' + head + '</head><body>' + body
            + ('<script>' + script + '</script>' if script else '') + '</body></html>')


class SkillHtmlCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SCRIPT.exists():
            cls.tool = None
            return
        spec = importlib.util.spec_from_file_location('kp_check_html', SCRIPT)
        cls.tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.tool)

    def check(self, html, **kwargs):
        self.assertIsNotNone(self.tool, 'bundled check_html.py is not implemented')
        return self.tool.check_html(html, **kwargs)

    def codes(self, result):
        return [item['code'] for item in result['diagnostics']]

    def test_run05_initial_heading_regression_is_diagnosed(self):
        # Exact failed h1 from run-05/runs/development-D07-m0-high-r0-candidate/output.md:107.
        # The original run remains immutable; this reduced specimen is not a corrected output.
        old = '<h1>毎週の積立額ではなく、毎週 더하는 금액과 기간에 따른 적립 모형</h1>'
        result = self.check(page(old))
        self.assertEqual(result['status'], 'issues_found')
        diagnostic = next(d for d in result['diagnostics'] if d['code'] == 'ui-language-kana')
        self.assertEqual(diagnostic['context'], 'h1')
        self.assertGreater(diagnostic['line'], 0)
        self.assertIn('毎週', diagnostic['snippet'])

    def test_clean_template_has_no_diagnostic_findings(self):
        result = self.check((ROOT / 'skills/korean-protocol/assets/interactive-explainer.html').read_text())
        self.assertEqual(result['status'], 'no_findings', result)
        self.assertIn('browser', ' '.join(result['limitations']).lower())

    def test_initial_text_and_accessible_attributes_are_checked(self):
        for body in ['<h1>テスト</h1>', '<button aria-label="テスト">실행한다</button>',
                     '<input type="button" value="テスト">', '<p title="テスト">설명한다</p>']:
            with self.subTest(body=body):
                self.assertIn('ui-language-kana', self.codes(self.check(page(body))))

    def test_hidden_error_text_is_checked_without_claiming_initial_visibility(self):
        result = self.check(page('<p hidden id="error">テスト</p>'))
        diagnostic = next(d for d in result['diagnostics'] if d['code'] == 'ui-language-kana')
        self.assertEqual(diagnostic['initial_visibility'], 'hidden')

    def test_javascript_strings_are_review_not_proven_displayed(self):
        result = self.check(page('<p id="status"></p>', 'status.textContent = "テスト";'))
        self.assertEqual(result['status'], 'review_required')
        self.assertIn('javascript-string-kana', self.codes(result))

    def test_run05_pure_han_dynamic_state_requires_review(self):
        # Exact failing statement from run-05/runs/development-D07-m0-xhigh-r1-candidate/output.md.
        result = self.check(page(script='totalOutput.textContent = "計算保留";'))
        self.assertEqual(result['status'], 'review_required')
        self.assertIn('javascript-string-cjk', self.codes(result))

    def test_mixed_korean_han_text_requires_review_without_asserting_error(self):
        result = self.check(page('<p>韓國 설명을 확인한다</p>'))
        self.assertEqual(result['status'], 'review_required')
        self.assertTrue(all(item['severity'] == 'review' for item in result['diagnostics']))

    def test_protected_han_source_stays_preserved_and_reviewable(self):
        result = self.check(page('<q>計算保留</q>'), protected_text=['計算保留'])
        self.assertNotIn('ui-language-cjk', self.codes(result))
        self.assertIn('protected-foreign-text', self.codes(result))
        self.assertEqual(result['status'], 'review_required')

    def test_escaped_javascript_strings_are_checked(self):
        result = self.check(page(script=r'status.textContent = "\u30c6\u30b9\u30c8";'))
        self.assertIn('javascript-string-kana', self.codes(result))

    def test_surrogate_pair_in_javascript_diagnostic_keeps_json_output(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'example.html'
            file.write_text(page(script=r'status.textContent="\uD83D\uDE00 テスト";'))
            original = file.read_bytes()
            result = subprocess.run([sys.executable, str(SCRIPT), str(file)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            diagnostic = json.loads(result.stdout)
            self.assertEqual(diagnostic['status'], 'review_required')
            self.assertIn('😀', diagnostic['diagnostics'][0]['snippet'])
            json.dumps(diagnostic, ensure_ascii=False).encode('utf-8')
            self.assertEqual(file.read_bytes(), original)
            self.assertNotIn('Traceback', result.stderr)

    def test_unpaired_javascript_surrogate_does_not_break_json_output(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'example.html'
            file.write_text(page(script=r'status.textContent="\uD83D テスト";'))
            original = file.read_bytes()
            result = subprocess.run([sys.executable, str(SCRIPT), str(file)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            diagnostic = json.loads(result.stdout)
            self.assertEqual(diagnostic['status'], 'review_required')
            self.assertIn('\\ud83d', diagnostic['diagnostics'][0]['snippet'])
            json.dumps(diagnostic, ensure_ascii=False).encode('utf-8')
            self.assertEqual(file.read_bytes(), original)
            self.assertNotIn('Traceback', result.stderr)

    def test_comments_and_lookup_identifiers_are_not_ui_diagnostics(self):
        html = page('<p id="テスト">조건을 확인한다</p>',
                    '// テスト\nconst el = document.getElementById("テスト"); /* テスト */')
        result = self.check(html)
        self.assertEqual(result['status'], 'no_findings')
        self.assertEqual(result['exclusions'][0]['context'], 'javascript-lookup-identifier')

    def test_code_examples_are_not_asserted_to_be_authored_ui(self):
        result = self.check(page('<pre><code>const テスト = 1;</code></pre>'))
        self.assertNotIn('ui-language-kana', self.codes(result))
        self.assertGreater(result['coverage']['code_text_segments_excluded'], 0)

    def test_exact_protected_source_is_preserved_and_still_requires_review(self):
        result = self.check(page('<q>テスト</q>'), protected_text=['テスト'])
        self.assertEqual(result['status'], 'review_required')
        self.assertNotIn('ui-language-kana', self.codes(result))
        diagnostic = next(d for d in result['diagnostics'] if d['code'] == 'protected-foreign-text')
        self.assertTrue(diagnostic['protected_exact_match'])

    def test_protected_substring_cannot_suppress_authored_heading(self):
        result = self.check(page('<h1>テスト 결과를 확인한다</h1>'), protected_text=['テスト'])
        self.assertEqual(result['status'], 'issues_found')
        self.assertIn('ui-language-kana', self.codes(result))

    def test_protecting_entire_heading_does_not_create_pass(self):
        result = self.check(page('<h1>テスト</h1>'), protected_text=['テスト'])
        self.assertEqual(result['status'], 'review_required')

    def test_external_resource_and_network_call_are_diagnosed(self):
        for html in [page(head='<script src="https://example.test/code.js"></script>'),
                     page('<img src="plot.png" alt="도표를 표시한다">'),
                     page(head='<style>@import "theme.css";</style>'),
                     page(head='<style>body {background:url(https://example.test/a.png)}</style>'),
                     page(script='fetch("https://example.test/data");')]:
            with self.subTest(html=html):
                self.assertEqual(self.check(html)['status'], 'issues_found')

    def test_embedded_assets_and_citation_links_are_not_dependencies(self):
        html = page('<a href="https://example.test/source">근거를 확인한다</a>',
                    head='<link rel="icon" href="data:,"><style>p {background:url(data:image/png;base64,AA)}</style>')
        self.assertNotIn('external-resource', self.codes(self.check(html)))

    def test_image_input_external_source_is_diagnosed(self):
        result = self.check(page('<input type="image" src="https://example.test/button.png" alt="제출한다">'))
        self.assertIn('external-resource', self.codes(result))
        self.assertEqual(result['status'], 'issues_found')

    def test_embedded_image_input_is_not_external_dependency(self):
        result = self.check(page('<input type="image" src="data:image/png;base64,AA" alt="제출한다">'))
        self.assertNotIn('external-resource', self.codes(result))

    def test_remote_dynamic_import_is_diagnosed(self):
        result = self.check(page(script='import("https://example.test/code.js");'))
        self.assertIn('external-resource', self.codes(result))
        self.assertEqual(result['status'], 'issues_found')

    def test_embedded_dynamic_import_is_not_external_dependency(self):
        result = self.check(page(script='import("data:text/javascript,export default 1");'))
        self.assertNotIn('external-resource', self.codes(result))

    def test_label_and_aria_targets_must_exist(self):
        result = self.check(page('<label for="missing">값을 입력한다</label>'
                                 '<input id="value" aria-describedby="absent">'))
        self.assertIn('label-target-missing', self.codes(result))
        self.assertIn('control-label-missing', self.codes(result))
        self.assertIn('aria-target-missing', self.codes(result))

    def test_wrapped_and_aria_labels_are_accepted(self):
        html = page('<label>값을 입력한다<input type="number"></label>'
                    '<input aria-label="기간을 입력한다"><span id="name">수량을 입력한다</span>'
                    '<input aria-labelledby="name">')
        self.assertEqual(self.check(html)['status'], 'no_findings')

    def test_duplicate_ids_are_diagnosed(self):
        self.assertIn('duplicate-id', self.codes(self.check(page('<p id="x"></p><p id="x"></p>'))))

    def test_reset_shadowing_regression_is_diagnosed(self):
        html = page('<form><button id="reset" type="button">초기화한다</button></form>', 'form.reset();')
        self.assertIn('form-member-shadow', self.codes(self.check(html)))

    def test_robust_reset_example_has_no_reset_findings(self):
        html = page('<form id="calculator"><button id="reset-calculator" type="button">초기화한다</button></form>',
                    'HTMLFormElement.prototype.reset.call(form);')
        self.assertEqual(self.check(html)['status'], 'no_findings')

    def test_input_is_not_modified_and_json_is_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'example.html'
            original = page('<h1>테스트 결과를 확인한다</h1>').encode()
            file.write_bytes(original)
            command = [sys.executable, str(SCRIPT), str(file), '--language', 'ko']
            first = subprocess.run(command, capture_output=True, text=True)
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout, second.stdout)
            self.assertEqual(json.loads(first.stdout)['status'], 'no_findings')
            self.assertEqual(file.read_bytes(), original)

    def test_bad_protection_input_is_json_error_not_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'example.html'
            file.write_text(page('<h1>테스트 결과를 확인한다</h1>'))
            protected = Path(directory) / 'protected.json'
            protected.write_text('{"allow_substrings": ["anything"]}')
            result = subprocess.run([sys.executable, str(SCRIPT), str(file), '--protected-text', str(protected)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['status'], 'invalid_input')
            self.assertNotIn('Traceback', result.stderr)

    def test_cli_errors_and_review_both_return_one(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'example.html'
            for html, status in [(page('<h1>テスト</h1>'), 'issues_found'),
                                 (page(script='result.textContent = "計算保留";'), 'review_required')]:
                with self.subTest(status=status):
                    file.write_text(html)
                    result = subprocess.run([sys.executable, str(SCRIPT), str(file)], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(json.loads(result.stdout)['status'], status)


if __name__ == '__main__':
    unittest.main()
