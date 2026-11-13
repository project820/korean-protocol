#!/usr/bin/env python3
"""Read-only, bounded HTML diagnostics using only the Python standard library.

This checks observable source patterns, not browser behavior, Korean grammar,
meaning preservation, or formal STE/KP compliance. No JavaScript is executed.
"""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys


SCHEMA_VERSION = 1
KANA = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\uff66-\uff9d]')
HAN = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002fa1f]')
CJK_TEXT = re.compile(KANA.pattern + '|' + HAN.pattern)
VOID = frozenset('area base br col embed hr img input link meta param source track wbr'.split())
UI_ATTRIBUTES = frozenset(['title', 'placeholder', 'aria-label', 'aria-description', 'aria-valuetext', 'alt'])
FORM_MEMBERS = frozenset(['reset', 'submit', 'requestSubmit', 'checkValidity', 'reportValidity', 'addEventListener'])
CODE_TAGS = frozenset(['code', 'pre', 'kbd', 'samp'])
LIMITATIONS = [
    'No browser execution: layout, computed visibility, dynamic states, keyboard behavior and calculations are unverified.',
    'L3 mutation, result-order and dark-theme diagnostics are static checks; empty initial results and required calculation buttons are not judged without browser execution.',
    'Kana/Han detection is a diagnostic signal, not a language classifier; Han can be valid Korean source text and requires review.',
    'No semantic, source-preservation, accessibility-conformance or STE/KP certification is performed.',
    'JavaScript literals are scanned without data-flow analysis; a flagged literal is not proven to be displayed.',
    'Computed/concatenated/encoded-at-runtime text, CSS-generated text and external resource behavior require independent review.',
    'Code-example text and standard DOM lookup identifiers are excluded from UI-language claims.',
    'Protected exact matches still require source review; no substring allowlist grants a pass.',
]


def _position(text, start, origin):
    prefix = text[:start]
    lines = prefix.count('\n')
    return (origin[0] + lines,
            (len(prefix.rsplit('\n', 1)[-1]) if lines else origin[1] + start) + 1)


def _snippet(text):
    text = text.strip()
    match = CJK_TEXT.search(text)
    start = max(0, match.start() - 35) if match else 0
    return text[start:start + 180]


def _decode_js_string(text):
    """Decode only lexical escapes, never evaluate JavaScript or expressions."""
    escapes = {'n': '\n', 'r': '\r', 't': '\t', 'b': '\b', 'f': '\f', 'v': '\v'}
    def replace(match):
        value = match.group(1)
        try:
            if value.startswith('u{'):
                return chr(int(value[2:-1], 16))
            if value.startswith(('u', 'x')) and len(value) > 1:
                return chr(int(value[1:], 16))
        except (ValueError, OverflowError):
            return match.group(0)
        return escapes.get(value, value)
    decoded = re.sub(r'\\(u\{[0-9a-fA-F]+\}|u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|[^\r\n])', replace, text)
    decoded = re.sub(r'[\ud800-\udbff][\udc00-\udfff]',
                     lambda match: chr(0x10000 + ((ord(match.group()[0]) - 0xd800) << 10)
                                       + ord(match.group()[1]) - 0xdc00), decoded)
    # A JavaScript string may contain an unpaired UTF-16 code unit. Keep its
    # escaped spelling in diagnostics instead of emitting an invalid UTF-8 str.
    return re.sub(r'[\ud800-\udfff]', lambda match: '\\u%04x' % ord(match.group()), decoded)


def _javascript_literals(text):
    """Mask lexical text, retaining executable template interpolations and positions."""
    literals, masked = [], list(text)
    regex_keywords = frozenset('return throw case delete void typeof new in of instanceof yield await else do'.split())

    def mask(start, end):
        for index in range(start, end):
            if masked[index] not in ('\n', '\r'):
                masked[index] = ' '

    def literal(start, end, raw):
        prefix = text[max(0, start - 120):start]
        lookup = bool(re.search(
            r'\b(?:getElementById|getElementsByName|getElementsByClassName|querySelector|querySelectorAll|addEventListener)\s*\(\s*$', prefix))
        literals.append({'text': _decode_js_string(raw), 'start': start, 'end': end,
                         'lookup_identifier': lookup})

    def template(start):
        i, segment, parts = start + 1, start + 1, []
        while i < len(text):
            if text[i] == '\\':
                i = min(len(text), i + 2)
            elif text[i] == '`':
                parts.append(text[segment:i])
                mask(segment, i + 1)
                literal(start, i + 1, ''.join(parts))
                return i + 1
            elif text.startswith('${', i):
                parts.append(text[segment:i])
                mask(segment, i + 2)
                i = scan(i + 2, interpolation=True)
                segment = i
            else:
                i += 1
        parts.append(text[segment:i])
        mask(segment, i)
        literal(start, i, ''.join(parts))
        return i

    def scan(i, interpolation=False):
        # This is a bounded lexer, not a JS parser. An operator, opening delimiter
        # or expression-prefix keyword permits a regex; a value token permits division.
        regex_allowed, braces = True, 0
        while i < len(text):
            char = text[i]
            if char.isspace():
                i += 1
                continue
            if text.startswith('//', i):
                end = text.find('\n', i)
                end = len(text) if end < 0 else end
            elif text.startswith('/*', i):
                close = text.find('*/', i + 2)
                end = len(text) if close < 0 else close + 2
            elif char in ('"', "'"):
                end = i + 1
                while end < len(text):
                    if text[end] == '\\':
                        end = min(len(text), end + 2)
                    elif text[end] == char:
                        end += 1
                        break
                    else:
                        end += 1
                literal(i, end, text[i + 1:end - 1] if text[end - 1] == char else text[i + 1:end])
                regex_allowed = False
            elif char == '`':
                mask(i, i + 1)
                i = template(i)
                regex_allowed = False
                continue
            elif char == '/' and regex_allowed:
                end, in_class = i + 1, False
                while end < len(text) and text[end] not in ('\n', '\r'):
                    current = text[end]
                    if current == '\\':
                        end = min(len(text), end + 2)
                        continue
                    if current == '[':
                        in_class = True
                    elif current == ']':
                        in_class = False
                    elif current == '/' and not in_class:
                        end += 1
                        while end < len(text) and text[end].isalpha():
                            end += 1
                        break
                    end += 1
                regex_allowed = False
            else:
                token = re.match(r'[A-Za-z_$][\w$]*|\d[\w.]*', text[i:])
                if token:
                    regex_allowed = token.group() in regex_keywords
                    i += len(token.group())
                    continue
                if char == '{':
                    braces += 1
                elif char == '}':
                    if interpolation and not braces:
                        mask(i, i + 1)
                        return i + 1
                    braces -= 1
                if text[i:i + 2] in ('++', '--'):
                    i += 2
                    continue
                regex_allowed = char in '([{=,:;!?&|+*-/%^~<>'
                i += 1
                continue
            mask(i, end)
            i = end
        return i

    scan(0)
    return literals, ''.join(masked)


def _dark_only(value):
    schemes = set(re.findall(r'[\w-]+', value.lower()))
    return 'dark' in schemes and 'light' not in schemes


class _Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.nodes, self.texts, self.scripts, self.styles = [], [], [], [], []
        self.duplicate_attributes = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        line, column = self.getpos()
        node = {'tag': tag, 'attrs': attributes, 'line': line, 'column': column + 1,
                'parents': list(self.stack), 'text': '', 'source': self.get_starttag_text()}
        self.nodes.append(node)
        if len(attributes) != len(attrs):
            self.duplicate_attributes.append(node)
        for name, value in attributes.items():
            if name.startswith('on') and value:
                self.scripts.append((value, self.getpos()))
            if name == 'style' and value:
                self.styles.append((value, self.getpos()))
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]['tag'] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        for node in self.stack:
            node['text'] += data
        tags = [node['tag'] for node in self.stack]
        if tags and tags[-1] == 'script':
            kind = (self.stack[-1]['attrs'].get('type') or '').lower()
            if kind in ('', 'module', 'text/javascript', 'application/javascript'):
                self.scripts.append((data, self.getpos()))
        elif tags and tags[-1] == 'style':
            self.styles.append((data, self.getpos()))
        elif data.strip() and not any(tag in ('script', 'style', 'template') for tag in tags):
            self.texts.append({'text': data.strip(), 'origin': self.getpos(),
                               'context': tags[-1] if tags else 'document',
                               'code': any(tag in CODE_TAGS for tag in tags),
                               'hidden': any('hidden' in node['attrs'] or node['attrs'].get('aria-hidden') == 'true'
                                             for node in self.stack)})


def check_html(text, file='<memory>', language='ko', protected_text=None):
    """Return deterministic JSON-compatible diagnostics without changing any input."""
    if language != 'ko':
        raise ValueError('only --language ko is supported in this diagnostic version')
    if protected_text is None:
        protected_text = []
    if (not isinstance(protected_text, list) or
            any(not isinstance(value, str) or not value for value in protected_text)):
        raise ValueError('protected text must be a JSON list of nonempty exact strings')
    protected = set(protected_text)
    parser = _Document()
    parser.feed(text)
    parser.close()
    diagnostics, exclusions = [], []
    coverage = {'markup_text_segments': len(parser.texts), 'ui_attributes': 0,
                'javascript_literal_count': 0, 'code_text_segments_excluded': 0,
                'lookup_identifiers_excluded': 0, 'protected_exact_matches': 0}

    def add(code, severity, line, column, context, value, message, **extra):
        diagnostics.append({'code': code, 'severity': severity, 'line': line, 'column': column,
                            'context': context, 'snippet': _snippet(value), 'message': message, **extra})

    def language_check(value, line, column, context, javascript=False, hidden=False):
        kana, han = bool(KANA.search(value)), bool(HAN.search(value))
        if not (kana or han):
            return
        if value in protected:
            coverage['protected_exact_matches'] += 1
            add('protected-foreign-text', 'review', line, column, context, value,
                'Exact protected text is preserved; verify its source and presentation rather than translating it automatically.',
                protected_exact_match=True, initial_visibility='hidden' if hidden else 'not_computed')
        else:
            suffix = 'kana' if kana else 'cjk'
            message = ('Kana occurs in Korean UI markup; review authored text against original quoted/source content.'
                       if kana else 'Han text occurs in Korean UI markup; review whether it is authored UI or preserved source text.')
            if javascript:
                message = ('Kana' if kana else 'Han text') + ' occurs in a JavaScript literal; review whether this becomes UI text.'
            add(('javascript-string-' if javascript else 'ui-language-') + suffix,
                'error' if kana and not javascript else 'review', line, column, context, value,
                message,
                protected_exact_match=False,
                initial_visibility='not_computed' if javascript else ('hidden' if hidden else 'not_hidden_by_attribute'))

    for item in parser.texts:
        if item['code']:
            coverage['code_text_segments_excluded'] += 1
            exclusions.append({'severity': 'info', 'line': item['origin'][0], 'column': item['origin'][1] + 1,
                               'context': item['context'], 'snippet': _snippet(item['text']),
                               'reason': 'code-example-text-not-asserted-to-be-ui'})
            continue
        language_check(item['text'], item['origin'][0], item['origin'][1] + 1,
                       item['context'], hidden=item['hidden'])

    ids = {}
    for node in parser.nodes:
        attrs, tag = node['attrs'], node['tag']
        line, column = node['line'], node['column']
        if (tag == 'meta' and (attrs.get('name') or '').strip().lower() == 'color-scheme'
                and _dark_only(attrs.get('content') or '')):
            add('dark-default-theme', 'error', line, column, 'meta@content', node['source'],
                'The color-scheme meta tag supports only dark; include a light scheme.')
        if attrs.get('id'):
            if attrs['id'] in ids:
                add('duplicate-id', 'error', line, column, tag, attrs['id'], 'HTML id is duplicated.')
            else:
                ids[attrs['id']] = node
        for name in sorted(UI_ATTRIBUTES):
            if attrs.get(name):
                coverage['ui_attributes'] += 1
                language_check(attrs[name], line, column, tag + '@' + name)
        if tag == 'input' and attrs.get('type', '').lower() in ('button', 'submit', 'reset') and attrs.get('value'):
            coverage['ui_attributes'] += 1
            language_check(attrs['value'], line, column, 'input@value')
        resources = []
        if tag in ('script', 'img', 'iframe', 'audio', 'video', 'source', 'track', 'embed'):
            resources += [(name, attrs[name]) for name in ('src', 'poster', 'srcset') if attrs.get(name)]
        if tag == 'input' and (attrs.get('type') or '').lower() == 'image' and attrs.get('src'):
            resources.append(('src', attrs['src']))
        if tag == 'object' and attrs.get('data'):
            resources.append(('data', attrs['data']))
        if tag == 'link' and attrs.get('href') and set((attrs.get('rel') or '').lower().split()) & {
                'stylesheet', 'icon', 'preload', 'modulepreload', 'preconnect', 'dns-prefetch', 'manifest'}:
            resources.append(('href', attrs['href']))
        if tag == 'form' and attrs.get('action'):
            resources.append(('action', attrs['action']))
        for name, value in resources:
            if not value.strip().lower().startswith(('data:', '#')):
                add('external-resource', 'error', line, column, tag + '@' + name, value,
                    'Resource/action requires another file or connection; a single-file offline artifact must embed it or remove the dependency.')
    for node in parser.duplicate_attributes:
        add('duplicate-attribute', 'error', node['line'], node['column'], node['tag'], '',
            'Duplicate HTML attributes can change the parsed UI; review the source.')

    result_candidates = [(index, node) for index, node in enumerate(parser.nodes)
                         if (node['attrs'].get('aria-live') or '').strip().lower() != 'off'
                         and not any(ancestor['tag'] == 'template'
                                     or 'hidden' in ancestor['attrs']
                                     or (ancestor['attrs'].get('aria-hidden') or '').strip().lower() == 'true'
                                     for ancestor in node['parents'] + [node])]
    first_result = next((index for index, node in result_candidates if node['tag'] == 'output'), None)
    if first_result is None:
        first_result = next((index for index, node in result_candidates
                             if (node['attrs'].get('aria-live') or '').strip().lower()
                             in ('polite', 'assertive')), None)
    first_input = next((index for index, node in enumerate(parser.nodes)
                        if node['tag'] in ('input', 'select', 'textarea')
                        and not (node['tag'] == 'input'
                                 and (node['attrs'].get('type') or '').lower() == 'hidden')), None)
    if first_result is not None and first_input is not None and first_result > first_input:
        node = parser.nodes[first_result]
        add('result-after-input', 'error', node['line'], node['column'], node['tag'], node['source'],
            'The first result region follows the first form input in DOM order; put the result region first.')

    html_nodes = [node for node in parser.nodes if node['tag'] == 'html']
    if not html_nodes or (html_nodes[0]['attrs'].get('lang') or '').lower().split('-')[0] != language:
        add('document-language', 'error', 1, 1, 'html@lang', '', 'Set the document language to ko for this Korean UI check.')

    labels = [node for node in parser.nodes if node['tag'] == 'label']
    for node in labels:
        target = node['attrs'].get('for')
        if target and target not in ids:
            add('label-target-missing', 'error', node['line'], node['column'], 'label@for', target,
                'The label target id does not exist.')
    for node in parser.nodes:
        attrs, tag = node['attrs'], node['tag']
        for name in ('aria-labelledby', 'aria-describedby'):
            for target in (attrs.get(name) or '').split():
                if target not in ids:
                    add('aria-target-missing', 'error', node['line'], node['column'], tag + '@' + name, target,
                        'Referenced accessible text id does not exist.')
        if tag not in ('input', 'select', 'textarea', 'button'):
            continue
        kind = (attrs.get('type') or '').lower()
        if kind != 'hidden':
            labelled = bool((attrs.get('aria-label') or '').strip())
            labelled = labelled or any(ids.get(key, {}).get('text', '').strip()
                                      for key in (attrs.get('aria-labelledby') or '').split())
            labelled = labelled or any(parent['tag'] == 'label' and parent['text'].strip()
                                      for parent in node['parents'])
            labelled = labelled or any(label['attrs'].get('for') == attrs.get('id') and attrs.get('id')
                                      and label['text'].strip() for label in labels)
            labelled = labelled or (tag == 'button' and node['text'].strip())
            labelled = labelled or (tag == 'input' and kind in ('button', 'submit', 'reset') and (attrs.get('value') or '').strip())
            labelled = labelled or (tag == 'input' and kind == 'image' and (attrs.get('alt') or '').strip())
            if not labelled:
                add('control-label-missing', 'error', node['line'], node['column'], tag, attrs.get('id') or '',
                    'The control has no nonempty static explicit/wrapped/accessible label in this source.')
        in_form = any(parent['tag'] == 'form' for parent in node['parents'])
        in_form = in_form or ids.get(attrs.get('form'), {}).get('tag') == 'form'
        if in_form:
            for name in ('id', 'name'):
                if attrs.get(name) in FORM_MEMBERS:
                    add('form-member-shadow', 'error', node['line'], node['column'], tag + '@' + name, attrs[name],
                        'This form control shadows a native form member; rename the control and use HTMLFormElement.prototype.reset.call(form) for reset.')

    for style, origin in parser.styles:
        css = re.sub(r'/\*.*?\*/', lambda match: ' ' * len(match.group()), style, flags=re.S)
        # Mask strings and comments together so comment markers inside strings
        # cannot consume real declarations. Preserve offsets for source locations.
        theme_css = re.sub(r'/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
                           lambda match: re.sub(r'[^\r\n]', ' ', match.group()), style, flags=re.S)
        for match in re.finditer(
                r'@media\b[^{};]*\(\s*prefers-color-scheme\s*:\s*dark\s*\)'
                r'|(?<![\w-])color-scheme\s*:\s*([^;{}]*)', theme_css, re.I):
            if match.group(1) is not None and not _dark_only(match.group(1)):
                continue
            line, column = _position(style, match.start(), origin)
            add('dark-default-theme', 'error', line, column, 'css', match.group(),
                'Use one light theme; remove dark color-scheme declarations and dark preference media queries.')
        for match in re.finditer(r'@import\b|url\(\s*[\'"]?([^\)\'"\s]+)', css, re.I):
            value = match.group(1)
            if value and value.lower().startswith(('data:', '#')):
                continue
            line, column = _position(style, match.start(), origin)
            add('external-resource', 'error', line, column, 'css', match.group(),
                'CSS import/resource is not embedded in this single file.')

    for script, origin in parser.scripts:
        literals, code = _javascript_literals(script)
        assignment = r'(?:=(?!=|>)|[+\-*/%&|^]=|&&=|\|\|=|\?\?=)'
        for match in re.finditer(
                r'\.\s*(?:(?:innerHTML|outerHTML)\s*' + assignment
                + r'|insertAdjacentHTML\s*\()', code):
            line, column = _position(script, match.start(), origin)
            add('innerhtml-assignment', 'error', line, column, 'javascript',
                script[match.start():match.end()],
                'HTML mutation can interpret data as markup; use textContent for source strings.')
        for literal in literals:
            if script[literal['start']] not in ('"', "'") or literal['text'] not in ('innerHTML', 'outerHTML'):
                continue
            opening = re.search(r'\[\s*$', code[:literal['start']])
            closing = re.match(r'\s*\]\s*' + assignment, code[literal['end']:])
            if opening and closing:
                line, column = _position(script, opening.start(), origin)
                add('innerhtml-assignment', 'error', line, column, 'javascript',
                    script[opening.start():literal['end'] + closing.end()],
                    'HTML mutation can interpret data as markup; use textContent for source strings.')
        coverage['javascript_literal_count'] += len(literals)
        for literal in literals:
            if re.search(r'(?<![\w$.])import\s*\(\s*$', code[:literal['start']]):
                if not literal['text'].strip().lower().startswith(('data:', '#')):
                    line, column = _position(script, literal['start'], origin)
                    add('external-resource', 'error', line, column, 'javascript-import', literal['text'],
                        'Dynamic import references a module outside this single file.')
            if literal['lookup_identifier']:
                coverage['lookup_identifiers_excluded'] += 1
                if CJK_TEXT.search(literal['text']):
                    line, column = _position(script, literal['start'], origin)
                    exclusions.append({'severity': 'info', 'line': line, 'column': column,
                                       'context': 'javascript-lookup-identifier', 'snippet': _snippet(literal['text']),
                                       'reason': 'standard-dom-lookup-argument-not-asserted-to-be-ui'})
                continue
            line, column = _position(script, literal['start'], origin)
            language_check(literal['text'], line, column, 'javascript-string', javascript=True)
        for match in re.finditer(r'\b(?:fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon)\s*\(', code):
            line, column = _position(script, match.start(), origin)
            add('network-call', 'error', line, column, 'javascript', match.group(),
                'This source contains a network API call; review/remove it for offline single-file output.')

    diagnostics.sort(key=lambda item: (item['line'], item['column'], item['code'], item['context'], item['snippet']))
    status = ('issues_found' if any(item['severity'] == 'error' for item in diagnostics) else
              'review_required' if diagnostics else 'no_findings')
    return {'schema_version': SCHEMA_VERSION, 'file': str(file),
            'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(), 'language': language,
            'status': status, 'diagnostics': diagnostics, 'exclusions': exclusions, 'coverage': coverage,
            'limitations': list(LIMITATIONS)}


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({'schema_version': SCHEMA_VERSION, 'status': 'invalid_input', 'error': message},
                         ensure_ascii=False, sort_keys=True))
        raise SystemExit(2)


def main(argv=None):
    parser = _ArgumentParser(description=__doc__)
    parser.add_argument('html', type=Path)
    parser.add_argument('--language', choices=['ko'], default='ko')
    parser.add_argument('--protected-text', type=Path, help='JSON list of exact original text units; matches still require source review')
    args = parser.parse_args(argv)
    try:
        text = args.html.read_bytes().decode('utf-8')
        protected = json.loads(args.protected_text.read_bytes().decode('utf-8')) if args.protected_text else []
        result = check_html(text, file=str(args.html), language=args.language, protected_text=protected)
    except (OSError, UnicodeError, ValueError) as error:
        result = {'schema_version': SCHEMA_VERSION, 'status': 'invalid_input',
                  'file': str(args.html), 'error': type(error).__name__ + ': ' + str(error)}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result['status'] == 'no_findings' else 1


if __name__ == '__main__':
    sys.exit(main())
