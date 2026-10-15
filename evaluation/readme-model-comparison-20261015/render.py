"""Render the six README cases without editing model wording.

The presentation contract removes only an ATX heading's prefix (up to three
spaces, 1-6 hashes, and following horizontal whitespace), and balanced
``**text**`` markers bounded by whitespace or line boundaries, with no leading
or trailing whitespace or internal asterisks. Ambiguous emphasis stays literal.
Newlines (including a final newline) become ``<br>``.
Bullet and ordered-list markers remain literal, so 01), 7., and repeated 1.
cannot be silently renumbered. Blank lines supply paragraph spacing. Code,
quotes, tables, links, and other unsupported syntax remain escaped text.
CRLF/CR are normalized to LF for presentation only; raw files are never written.

``verify_rendered_text`` checks exact text after this formatting projection;
``verify_table`` checks the complete deterministic table against all 12 files.
These checks establish presentation fidelity, not semantic correctness of the
model's response to the source. Raw byte hashes and semantic review live in the
run's separate evidence files.
"""

import argparse
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import quote, urlsplit


HEADING = re.compile(r"^ {0,3}#{1,6}[ \t]+")
BOLD = re.compile(r"(?<!\S)\*\*([^\s*](?:[^*\n]*[^\s*])?)\*\*(?!\S)")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def _normalized(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _lines(text):
    """Yield text and supported-format status, preserving every input line."""
    fence = None
    for line in _normalized(text).split("\n"):
        match = FENCE.match(line)
        if fence is not None:
            yield line, False
            if (match and match[1][0] == fence[0] and len(match[1]) >= len(fence)
                    and not line[match.end():].strip(" \t")):
                fence = None
        elif match:
            # Backtick info strings cannot themselves contain a backtick.
            if match[1][0] != "`" or "`" not in line[match.end():]:
                fence = match[1]
            yield line, False
        else:
            # Unsupported constructs fall back as a whole line, not partial HTML.
            supported = not (
                line.startswith(("    ", "\t"))
                or line.lstrip().startswith((">", "|"))
                or "`" in line
                or re.search(r"!?\[[^\n]*\]", line)
            )
            yield line, supported


def projected_text(text):
    """Return exact visible text under the documented formatting contract."""
    result = []
    for line, supported in _lines(text):
        if supported:
            line = HEADING.sub("", line, count=1)
            line = BOLD.sub(lambda match: match[1], line)
        result.append(line)
    return "\n".join(result)


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        if attrs or tag not in {"strong", "br"}:
            raise ValueError("Rendered text contains an unsupported HTML tag or attribute")
        if tag == "br":
            self.parts.append("\n")
        else:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag:
            raise ValueError("Rendered text contains unbalanced HTML")

    def handle_data(self, data):
        self.parts.append(data)

    def handle_comment(self, data):
        raise ValueError("Rendered text contains an HTML comment")

    def handle_decl(self, decl):
        raise ValueError("Rendered text contains an HTML declaration")

    def handle_pi(self, data):
        raise ValueError("Rendered text contains a processing instruction")


def verify_rendered_text(source, rendered, *, markdown=True):
    """Raise ValueError if rendering changes text beyond the narrow contract."""
    parser = _VisibleText()
    parser.feed(rendered)
    parser.close()
    if parser.stack:
        raise ValueError("Rendered text contains unclosed HTML")
    expected = projected_text(source) if markdown else _normalized(source)
    if "".join(parser.parts) != expected:
        raise ValueError("Rendered text differs from the source formatting projection")


def render_text(text, *, markdown=True):
    rendered_lines = []
    for line, supported in _lines(text):
        heading = markdown and supported and HEADING.match(line)
        if heading:
            line = line[heading.end():]
        if markdown and supported:
            pieces = []
            cursor = 0
            for match in BOLD.finditer(line):
                pieces.extend((escape(line[cursor:match.start()]),
                               "<strong>" + escape(match[1]) + "</strong>"))
                cursor = match.end()
            pieces.append(escape(line[cursor:]))
            rendered_line = "".join(pieces)
        else:
            rendered_line = escape(line)
        if heading:
            rendered_line = "<strong>" + rendered_line + "</strong>"
        rendered_lines.append(rendered_line)
    rendered = "<br>".join(rendered_lines)
    verify_rendered_text(text, rendered, markdown=markdown)
    return rendered


def _validate_cases(cases):
    if not isinstance(cases, list) or len(cases) != 6:
        raise ValueError("Exactly six source cases are required")
    for case in cases:
        if not isinstance(case, dict) or any(
            not isinstance(case.get(key), str) or not case[key].strip()
            for key in ("id", "title", "anchor", "source")
        ):
            raise ValueError("Each case needs nonempty string id, title, anchor, and source")
        if not re.fullmatch(r"[0-9]{2}", case["id"]):
            raise ValueError("Case ids must be two ASCII digits")
        if any("\n" in case[key] or "\r" in case[key] for key in ("title", "anchor")):
            raise ValueError("Case title and anchor must each use a single line")
    if len({case["id"] for case in cases}) != 6:
        raise ValueError("Case ids must be unique")
    if len({case["anchor"] for case in cases}) != 6:
        raise ValueError("Case anchors must be unique")


def render_table(cases, outputs_directory, link_prefix):
    """Read six sources/twelve raw outputs and return the README HTML table."""
    _validate_cases(cases)
    directory = Path(outputs_directory)
    expected = {f"{case['id']}-{kind}.txt" for case in cases for kind in ("kp", "ste")}
    actual = {path.name for path in directory.glob("*.txt")}
    if actual != expected:
        raise ValueError(f"Expected exactly twelve outputs; missing={sorted(expected-actual)}, "
                         f"unexpected={sorted(actual-expected)}")
    if not isinstance(link_prefix, str) or urlsplit(link_prefix).scheme or link_prefix.startswith("//"):
        raise ValueError("Raw output links require a repository-relative prefix")
    rows = [
        "<table>", "<thead>",
        '<tr><th width="33%" scope="col" nowrap>원문 · 사실과 조건의 기준</th>'
        '<th width="33%" scope="col" nowrap>Korean Protocol 0.7</th>'
        '<th width="33%" scope="col" nowrap>STE 원칙 적용 · 한국어 참고</th></tr>',
        "</thead>", "<tbody>",
    ]
    for case in cases:
        rows.extend([
            '<tr><th colspan="3" align="left"><a id="' + escape(case["anchor"], quote=True)
            + '"></a>' + str(int(case["id"])) + ". " + escape(case["title"]) + "</th></tr>",
            "<tr>",
            '<td valign="top">' + render_text(case["source"], markdown=False) + "</td>",
        ])
        for kind in ("kp", "ste"):
            filename = f"{case['id']}-{kind}.txt"
            # newline='' leaves the raw newline sequence available to render_text.
            with (directory / filename).open(encoding="utf-8", newline="") as handle:
                raw = handle.read()
            if not raw.strip():
                raise ValueError(f"Empty model output: {filename}")
            href = link_prefix.rstrip("/") + "/" + quote(filename)
            rows.append('<td valign="top">' + render_text(raw)
                        + '<br><br><a href="' + escape(href, quote=True)
                        + '">모델 출력 원문</a></td>')
        rows.extend(["</tr>"])
    rows.extend(["</tbody>", "</table>"])
    return "\n".join(rows)


def verify_table(table, cases, outputs_directory, link_prefix):
    """Reject any divergence from the deterministic raw-file presentation."""
    if table != render_table(cases, outputs_directory, link_prefix):
        raise ValueError("Table differs from the six sources and twelve raw output files")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", type=Path)
    parser.add_argument("outputs_directory", type=Path)
    parser.add_argument("--link-prefix", required=True)
    parser.add_argument("--check", type=Path, help="Check a file containing only the rendered table")
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    if args.check:
        verify_table(args.check.read_text(encoding="utf-8").removesuffix("\n"),
                     cases, args.outputs_directory, args.link_prefix)
    else:
        print(render_table(cases, args.outputs_directory, args.link_prefix))


if __name__ == "__main__":
    main()
