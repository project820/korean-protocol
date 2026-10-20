"""Inspect generated artifacts without executing code or claiming visual/semantic QA."""
import argparse
import ast
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path


def code_blocks(text, languages):
    return [m.group(2) for m in re.finditer(
        r'^```([\w+-]*)[^\n]*\n(.*?)\n```\s*$', text, re.M | re.S)
        if m.group(1).lower() in languages]


def extract_html(text):
    blocks = code_blocks(text, {'html', 'htm'})
    if len(blocks) == 1:
        return blocks[0]
    if len(blocks) > 1:
        raise ValueError('multiple HTML artifacts')
    stripped = text.strip()
    if re.match(r'(?is)(<!doctype\s+html[^>]*>\s*)?<html\b', stripped):
        return stripped
    raise ValueError('one complete HTML artifact required')


class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.labels = set()
        self.controls = []
        self.findings = []
        self.label_depth = 0
        self.form_depth = 0
        self.shadowed_methods = set()
        self.has_language = False
        self.has_viewport = False

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == 'form':
            self.form_depth += 1
        if tag in ('input', 'button', 'select', 'textarea') and self.form_depth:
            reserved = {'reset', 'submit', 'checkValidity', 'reportValidity', 'requestSubmit'}
            self.shadowed_methods.update({attrs.get('id'), attrs.get('name')} & reserved)
        if attrs.get('id'):
            self.ids.append(attrs['id'])
        if tag == 'html':
            self.has_language = attrs.get('lang', '').lower().startswith('ko')
        if tag == 'meta' and attrs.get('name', '').lower() == 'viewport':
            self.has_viewport = 'width=device-width' in attrs.get('content', '')
        if tag == 'label':
            self.label_depth += 1
            if attrs.get('for'):
                self.labels.add(attrs['for'])
        if tag in ('input', 'select', 'textarea') and attrs.get('type') not in ('hidden', 'submit', 'reset', 'button'):
            self.controls.append((attrs, self.label_depth > 0))
        resource = attrs.get('src') or (attrs.get('href') if tag == 'link' else None)
        if resource and not resource.startswith(('data:', '#')):
            self.findings.append('external resource: ' + resource)
        if tag in ('iframe', 'object', 'embed'):
            self.findings.append('external embedded content requires inspection')

    def handle_endtag(self, tag):
        if tag == 'form':
            self.form_depth = max(0, self.form_depth - 1)
        if tag == 'label':
            self.label_depth = max(0, self.label_depth - 1)


def inspect_html(source):
    document = Document()
    document.feed(source)
    findings = list(document.findings)
    for method in document.shadowed_methods:
        if re.search(r'\.\s*' + re.escape(method) + r'\s*\(', source):
            findings.append('form control shadows an invoked native form method: ' + method)
    if not document.has_language:
        findings.append('Korean document language missing')
    if not document.has_viewport:
        findings.append('responsive viewport missing')
    if len(document.ids) != len(set(document.ids)):
        findings.append('duplicate HTML id')
    for attrs, nested in document.controls:
        labelledby = attrs.get('aria-labelledby', '').split()
        labelled = bool(labelledby) and all(i in document.ids for i in labelledby)
        if not (nested or attrs.get('id') in document.labels or attrs.get('aria-label') or labelled):
            findings.append('control label missing: ' + attrs.get('id', '(no id)'))
    if re.search(r'\b(fetch\s*\(|XMLHttpRequest\b|WebSocket\s*\(|EventSource\s*\(|sendBeacon\s*\(|import\s*\()', source):
        findings.append('network-capable script requires removal or explicit inspection')
    if re.search(r'@import\b|url\(\s*[\'\"]?(?:https?:|//)', source, re.I):
        findings.append('external CSS resource')
    if not re.search(r'</html\s*>', source, re.I):
        findings.append('HTML closing element missing')
    return findings


def inspect_manim(source):
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return ['Python syntax error at line ' + str(exc.lineno)]
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    def scene_base(base):
        name = base.id if isinstance(base, ast.Name) else base.attr if isinstance(base, ast.Attribute) else ''
        return name.endswith('Scene')
    scenes = [c for c in classes if any(scene_base(b) for b in c.bases)]
    if not scenes:
        return ['Manim Scene subclass missing']
    if not any(any(isinstance(n, ast.FunctionDef) and n.name == 'construct' for n in c.body) for c in scenes):
        return ['Manim construct method missing']
    return []


def inspect_output(modality, text):
    result = {'modality': modality, 'output_sha256': hashlib.sha256(text.encode()).hexdigest(),
              'runtime_status': 'not_verified', 'semantic_status': 'not_verified', 'findings': []}
    try:
        if modality == 'L3':
            code = extract_html(text)
            result['artifact_sha256'] = hashlib.sha256(code.encode()).hexdigest()
            result['findings'] = inspect_html(code)
        elif modality == 'L4':
            blocks = code_blocks(text, {'python', 'py'})
            if len(blocks) != 1:
                raise ValueError('one Python artifact required for static inspection')
            result['artifact_sha256'] = hashlib.sha256(blocks[0].encode()).hexdigest()
            result['findings'] = inspect_manim(blocks[0])
        elif modality not in ('L1', 'L2'):
            raise ValueError('unknown modality')
    except ValueError as exc:
        result['findings'].append(str(exc))
    result['status'] = 'static_failed' if result['findings'] else 'static_checks_only'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modality', choices=['L1', 'L2', 'L3', 'L4'])
    parser.add_argument('path', type=Path)
    args = parser.parse_args()
    result = inspect_output(args.modality, args.path.read_text())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result['findings'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
