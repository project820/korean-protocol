import unittest

try:
    from evaluation.output_formats import media
except ImportError:
    media = None


class OutputMediaTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(media, 'Media validation capability is not implemented.')

    def test_missing_reusable_asset_fails_before_implementation(self):
        from pathlib import Path
        self.assertTrue((Path(__file__).resolve().parents[1] / 'skills/korean-protocol/assets/interactive-explainer.html').is_file())

    def test_html_keeps_complete_original_code(self):
        source = '<!doctype html><html lang="ko"><body><p>A &amp; B</p></body></html>'
        self.assertEqual(media.extract_html('설명\n```html\n' + source + '\n```'), source)

    def test_multiple_html_documents_are_ambiguous(self):
        with self.assertRaises(ValueError):
            media.extract_html('```html\n<html></html>\n```\n```html\n<html></html>\n```')

    def test_external_dependencies_and_network_code_fail(self):
        source = '<html lang="ko"><head><script src="https://cdn.example/a.js"></script></head><body><script>fetch("https://example.com")</script></body></html>'
        findings = media.inspect_html(source)
        self.assertTrue(any('external' in f for f in findings))
        self.assertTrue(any('network' in f for f in findings))

    def test_semantic_html_and_inline_code_pass_static_checks(self):
        source = '<!doctype html><html lang="ko"><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><main><h1>수량</h1><label for="q">수량</label><input id="q" type="number" value="3"><output id="result">3개</output><button type="button">초기화</button><script>document.getElementById("result").textContent="3개";</script></main></body></html>'
        self.assertEqual(media.inspect_html(source), [])

    def test_duplicate_ids_and_unlabelled_controls_fail(self):
        findings = media.inspect_html('<html lang="ko"><body><input id="x"><input id="x"></body></html>')
        self.assertTrue(any('duplicate' in f for f in findings))
        self.assertTrue(any('label' in f for f in findings))

    def test_form_controls_must_not_shadow_native_methods(self):
        findings = media.inspect_html('<html lang="ko"><body><form><button id="reset">초기화</button></form><script>form.reset();</script></body></html>')
        self.assertTrue(any('shadows' in f for f in findings))

    def test_prototype_reset_is_not_rejected_for_control_name(self):
        findings = media.inspect_html('<html lang="ko"><head><meta name="viewport" content="width=device-width"></head><body><form><button id="reset">초기화</button></form><script>HTMLFormElement.prototype.reset.call(form);</script></body></html>')
        self.assertEqual(findings, [])

    def test_python_is_parsed_without_execution(self):
        code = 'from manim import *\nclass Demo(Scene):\n    def construct(self):\n        raise RuntimeError("not executed")\n'
        self.assertEqual(media.inspect_manim(code), [])

    def test_python_requires_scene_and_rejects_syntax_error(self):
        self.assertTrue(media.inspect_manim('print("not a scene")'))
        self.assertTrue(media.inspect_manim('class Broken('))

    def test_artifact_report_never_claims_runtime_verification(self):
        report = media.inspect_output('L4', '```python\nfrom manim import *\nclass Demo(Scene):\n    def construct(self):\n        pass\n```\n장면 1: 시작한다.')
        self.assertEqual(report['runtime_status'], 'not_verified')
        self.assertEqual(report['semantic_status'], 'not_verified')
        self.assertEqual(report['status'], 'static_checks_only')


if __name__ == '__main__':
    unittest.main()
