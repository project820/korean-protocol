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

    def test_html_mutations_are_diagnosed_with_source_locations(self):
        for expression in ['node.innerHTML = value;', 'node.outerHTML += value;',
                           'node.insertAdjacentHTML("beforeend", value);']:
            with self.subTest(expression=expression):
                result = self.check(page(script='\n' + expression))
                diagnostic = next(d for d in result['diagnostics']
                                  if d['code'] == 'innerhtml-assignment')
                self.assertEqual(result['status'], 'issues_found')
                self.assertEqual(diagnostic['line'], 2)
                self.assertEqual(diagnostic['context'], 'javascript')
                self.assertIn('HTML', diagnostic['snippet'])

    def test_html_reads_comments_and_string_examples_are_not_mutations(self):
        script = ('const markup = node.innerHTML;\n'
                  'node.innerHTML === value; node.outerHTML != value;\n'
                  'node.textContent = "node.innerHTML = value";\n'
                  '// node.outerHTML = value;\n'
                  '/* node.insertAdjacentHTML("beforeend", value); */')
        self.assertNotIn('innerhtml-assignment', self.codes(self.check(page(script=script))))

    def test_regex_literal_contents_are_not_html_mutations(self):
        for script in [r'const pattern = /node.innerHTML = value/;',
                       r'const pattern = /node\.innerHTML = [a/]+/g;',
                       r'const pattern = (/node.outerHTML += value/);',
                       r'function pattern() { return /node.innerHTML = value/; }',
                       r'const pattern = true && /node.innerHTML = value/;',
                       r'const pattern = /node["innerHTML"] = value/;']:
            with self.subTest(script=script):
                self.assertNotIn('innerhtml-assignment', self.codes(self.check(page(script=script))))

    def test_static_bracket_html_assignments_are_diagnosed(self):
        for expression in ['node["innerHTML"] = source;', "node['outerHTML'] = source;",
                           'node[ /* property */ "innerHTML" ] += source;']:
            with self.subTest(expression=expression):
                result = self.check(page(script='\n' + expression))
                diagnostic = next(d for d in result['diagnostics']
                                  if d['code'] == 'innerhtml-assignment')
                self.assertEqual(diagnostic['line'], 2)
                self.assertIn('HTML', diagnostic['snippet'])

    def test_template_interpolation_html_assignments_are_diagnosed(self):
        for script in ['const view = `${node.innerHTML = source}`;',
                       'const view = `결과: ${node["outerHTML"] = source}`;',
                       'const view = `${({ value: node.innerHTML = source }).value}`;',
                       'const view = `${`결과: ${node.innerHTML = source}`}`;']:
            with self.subTest(script=script):
                self.assertIn('innerhtml-assignment', self.codes(self.check(page(script=script))))

    def test_html_mutation_scanner_keeps_division_and_template_text_distinct(self):
        for script in ['const value = total / count; node.innerHTML = source;',
                       'const value = total / node.innerHTML / count; node.outerHTML = source;']:
            with self.subTest(script=script):
                self.assertIn('innerhtml-assignment', self.codes(self.check(page(script=script))))
        for script in ['const view = `node.innerHTML = source`;',
                       r'const view = `\${node.innerHTML = source}`;',
                       'const view = `${"node.innerHTML = source"}`;',
                       'const view = `${/node.innerHTML = source/}`;',
                       'const value = node["innerHTML"];',
                       'node["outerHTML"] === source;']:
            with self.subTest(script=script):
                self.assertNotIn('innerhtml-assignment', self.codes(self.check(page(script=script))))

    def test_result_after_first_input_is_diagnosed(self):
        for control in ['<input aria-label="값">', '<select aria-label="값"></select>',
                        '<textarea aria-label="값"></textarea>']:
            for result_area in ['<output>96kWh</output>', '<div aria-live="polite">96kWh</div>']:
                with self.subTest(control=control, result_area=result_area):
                    result = self.check(page(control + '\n' + result_area))
                    diagnostic = next(d for d in result['diagnostics']
                                      if d['code'] == 'result-after-input')
                    self.assertEqual(result['status'], 'issues_found')
                    self.assertEqual(diagnostic['line'], 2)
                    self.assertIn(diagnostic['context'], ('output', 'div'))
                    self.assertIn(result_area.split('>')[0] + '>', diagnostic['snippet'])

    def test_result_order_uses_first_result_and_ignores_hidden_inputs(self):
        for body in ['<input type="hidden"><output>96kWh</output><input aria-label="값">',
                     '<div aria-live="polite">96kWh<input aria-label="값"></div>',
                     '<output>96kWh</output><input aria-label="값"><output>150kWh</output>',
                     '<input aria-label="값">', '<output>96kWh</output>',
                     '<input type="HIDDEN"><output>96kWh</output>', '']:
            with self.subTest(body=body):
                self.assertNotIn('result-after-input', self.codes(self.check(page(body))))

    def test_result_order_prioritizes_visible_output_over_status_or_inert_regions(self):
        for prefix in ['<div aria-live="polite">저장 상태</div>',
                       '<div aria-live="off">저장 상태</div>',
                       '<output hidden>이전 결과</output>',
                       '<template><output>결과 서식</output></template>',
                       '<output aria-hidden="true">이전 결과</output>',
                       '<div hidden><output>이전 결과</output></div>',
                       '<div aria-hidden="true"><output>이전 결과</output></div>',
                       '<output aria-live="off">이전 결과</output>']:
            with self.subTest(prefix=prefix):
                result = self.check(page(prefix + '<input aria-label="입력">\n<output>결과</output>'))
                diagnostic = next(d for d in result['diagnostics']
                                  if d['code'] == 'result-after-input')
                self.assertEqual(diagnostic['line'], 2)
                self.assertEqual(diagnostic['context'], 'output')

    def test_result_order_ignores_inactive_result_regions(self):
        for result_area in ['<output hidden>결과</output>',
                            '<output aria-hidden="true">결과</output>',
                            '<template><output>결과</output></template>',
                            '<div aria-live="off">결과</div>',
                            '<div aria-live="polite" hidden>결과</div>']:
            with self.subTest(result_area=result_area):
                result = self.check(page('<input aria-label="입력">' + result_area))
                self.assertNotIn('result-after-input', self.codes(result))

    def test_dark_theme_css_is_diagnosed_with_source_locations(self):
        for css in ['@media (prefers-color-scheme: dark) { body { color: white; } }',
                    ':root { color-scheme: dark; }', ':root { COLOR-SCHEME: only DARK; }']:
            with self.subTest(css=css):
                result = self.check(page(head='<style>\n' + css + '</style>'))
                diagnostic = next(d for d in result['diagnostics']
                                  if d['code'] == 'dark-default-theme')
                self.assertEqual(result['status'], 'issues_found')
                self.assertEqual(diagnostic['line'], 2)
                self.assertEqual(diagnostic['context'], 'css')
                self.assertIn('dark', diagnostic['snippet'].lower())

    def test_light_theme_and_commented_dark_css_are_not_diagnosed(self):
        css = (':root { color-scheme: light; }\n'
               '@media (prefers-color-scheme: light) { body { color: black; } }\n'
               '/* @media (prefers-color-scheme: dark) {} color-scheme: dark; */')
        result = self.check(page(head='<style>' + css + '</style>'))
        self.assertNotIn('dark-default-theme', self.codes(result))

    def test_css_string_contents_are_not_dark_theme_declarations(self):
        for css in ['p::before { content: "color-scheme: dark"; }',
                    "p::before { content: '@media (prefers-color-scheme: dark) {}'; }",
                    r'p::before { content: "\"color-scheme: dark"; }',
                    'p::before { content: "/*"; } :root { color-scheme: light; }']:
            with self.subTest(css=css):
                self.assertNotIn('dark-default-theme', self.codes(
                    self.check(page(head='<style>' + css + '</style>'))))

    def test_dark_only_color_scheme_meta_is_diagnosed(self):
        for content in ['dark', 'only dark', 'DARK']:
            with self.subTest(content=content):
                result = self.check(page(head='\n<meta name="color-scheme" content="' + content + '">'))
                diagnostic = next(d for d in result['diagnostics']
                                  if d['code'] == 'dark-default-theme')
                self.assertEqual(diagnostic['line'], 2)
                self.assertEqual(diagnostic['context'], 'meta@content')

    def test_light_and_dark_color_schemes_are_not_dark_only(self):
        for value in ['light', 'light dark', 'DARK light', 'normal']:
            with self.subTest(value=value):
                for head in ['<meta name="color-scheme" content="' + value + '">',
                             '<style>:root { color-scheme: ' + value + '; }</style>']:
                    self.assertNotIn('dark-default-theme', self.codes(self.check(page(head=head))))

    def test_dark_theme_declaration_after_css_string_keeps_source_location(self):
        css = 'p::before { content: "/* not a comment */"; }\n:root { color-scheme: dark; }'
        result = self.check(page(head='<style>' + css + '</style>'))
        diagnostic = next(d for d in result['diagnostics'] if d['code'] == 'dark-default-theme')
        self.assertEqual(diagnostic['line'], 2)
        self.assertEqual(diagnostic['column'], 9)

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
