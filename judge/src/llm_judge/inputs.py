"""Turn an output in any format into text the judge can read.

An output is a file or a directory. A directory is read file by file, in path order, and each
file's text is headed by its path. Files are read by kind:

- JSON and JSON Lines are rendered as indented `key: value` lines, so multi-line strings (a
  story, a prompt) read as text instead of one escaped line.
- HTML is either rendered in headless Chrome and its visible text taken (`rendered`), or read
  from source with its scripts kept (`source`), since a JavaScript-built page keeps its content in
  its scripts. `auto` renders when a Chrome or Chromium binary is found.
- PDF pages are extracted with pypdf, and Word .docx paragraphs from the document XML.
- Anything else that decodes as UTF-8 is read as plain text. Other binary files are rejected.

Nothing is truncated. The caller decides what to do with a long input.
"""

import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
import zipfile
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Literal
from xml.etree import ElementTree

HtmlMode = Literal["auto", "rendered", "source"]

CHARS_PER_TOKEN = 3.5
"""A rough English-text ratio, used only to warn about size before a model call."""


class InputError(Exception):
    """An input can't be read: missing, empty, or in a format the judge can't turn into text."""


@dataclass(frozen=True)
class Part:
    path: str
    """The file's path, relative to the input's directory (or its name, for a single file)."""
    text: str
    how: str
    """How the file was read, such as "text", "json" or "html rendered"."""


@dataclass(frozen=True)
class Document:
    label: str
    """The path as the user gave it."""
    parts: tuple[Part, ...]
    skipped: tuple[str, ...] = field(default=())
    """Files in a directory that were left out because they couldn't be read as text."""

    @property
    def text(self) -> str:
        return "\n\n".join(f"=== file: {p.path} ({p.how}) ===\n{p.text}" for p in self.parts)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.text.encode()).hexdigest()

    @property
    def tokens(self) -> int:
        return estimate_tokens(self.text)


def estimate_tokens(text: str) -> int:
    return round(len(text) / CHARS_PER_TOKEN)


def load(path: Path, html: HtmlMode = "auto", include: list[str] | None = None) -> Document:
    """Read a file or a directory. `include` (glob patterns) filters a directory's files."""
    if not path.exists():
        raise InputError(f"{path} does not exist")
    if path.is_file():
        return Document(label=str(path), parts=(read_file(path, path.name, html),))
    parts: list[Part] = []
    skipped: list[str] = []
    for file in sorted(p for p in path.rglob("*") if p.is_file()):
        rel = file.relative_to(path).as_posix()
        if any(piece.startswith(".") for piece in Path(rel).parts):
            continue
        if include and not any(fnmatch.fnmatch(rel, pattern) for pattern in include):
            continue
        try:
            parts.append(read_file(file, rel, html))
        except InputError as error:
            skipped.append(f"{rel}: {error}")
    if not parts:
        raise InputError(f"{path} holds no readable files")
    return Document(label=str(path), parts=tuple(parts), skipped=tuple(skipped))


def read_file(path: Path, display: str, html: HtmlMode = "auto") -> Part:
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            value = json.loads(_decode(path))
        except json.JSONDecodeError:
            return _nonempty(Part(display, _decode(path), "text (invalid JSON)"))
        return _nonempty(Part(display, render_json(value), "json"))
    if suffix in (".jsonl", ".ndjson"):
        return _nonempty(Part(display, _read_jsonl(path), "json lines"))
    if suffix in (".html", ".htm", ".xhtml"):
        return _nonempty(_read_html(path, display, html))
    if suffix == ".pdf":
        return _nonempty(Part(display, _read_pdf(path), "pdf"))
    if suffix == ".docx":
        return _nonempty(Part(display, _read_docx(path), "docx"))
    return _nonempty(Part(display, _decode(path), "text"))


def _nonempty(part: Part) -> Part:
    if not part.text.strip():
        raise InputError(f"{part.path} has no text ({part.how})")
    return part


def _decode(path: Path) -> str:
    data = path.read_bytes()
    if b"\x00" in data[:8192]:
        raise InputError(f"{path.name} is a binary file the judge can't read")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise InputError(f"{path.name} is not UTF-8 text") from error


# JSON -------------------------------------------------------------------------------------------


def render_json(value: Any) -> str:
    """Indented `key: value` lines. Multi-line strings become indented blocks after `|`."""
    out: list[str] = []
    _render(value, "", "", out)
    return "\n".join(out)


def _render(value: Any, pad: str, lead: str, out: list[str]) -> None:
    if isinstance(value, dict | list) and value:
        if lead:
            out.append(f"{pad}{lead.rstrip()}")
            pad += "  "
        if isinstance(value, dict):
            for key, item in value.items():
                _render(item, pad, f"{key}: ", out)
        else:
            for item in value:
                _render(item, pad, "- ", out)
    elif isinstance(value, str) and "\n" in value:
        out.append(f"{pad}{lead}|")
        out.extend(f"{pad}  {line}" for line in value.splitlines())
    else:
        out.append(f"{pad}{lead}{_scalar(value)}")


def _scalar(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _read_jsonl(path: Path) -> str:
    blocks = []
    for number, line in enumerate(_decode(path).splitlines(), start=1):
        if not line.strip():
            continue
        try:
            body = render_json(json.loads(line))
        except json.JSONDecodeError:
            body = line
        blocks.append(f"[line {number}]\n{body}")
    return "\n".join(blocks)


# HTML -------------------------------------------------------------------------------------------

_BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "br", "dd", "details", "div", "dl", "dt",
    "fieldset", "figcaption", "figure", "footer", "form", "header", "hr", "li", "main", "nav",
    "ol", "p", "pre", "section", "summary", "table", "tbody", "thead", "tfoot", "tr", "ul",
    "h1", "h2", "h3", "h4", "h5", "h6",
}  # fmt: skip
_TEXT_ATTRS = ("title", "alt", "aria-label")


class _HtmlText(HTMLParser):
    """Text of an HTML document, with line breaks at block elements and table cells split by |.

    Scripts are kept only when `keep_scripts` is set. Styles are always dropped. Tooltip-like
    attributes (title, alt, aria-label, and data-* values that read as prose) are kept in
    brackets after their element's opening tag.
    """

    def __init__(self, keep_scripts: bool):
        super().__init__(convert_charrefs=True)
        self.keep_scripts = keep_scripts
        self.chunks: list[str] = []
        self._skip_depth = 0
        self._raw_depth = 0
        self._inline_boundary = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("style", "template") or (tag == "script" and not self.keep_scripts):
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in ("script", "pre"):
            self._raw_depth += 1
            self._newline()
        elif tag in _BLOCK_TAGS:
            self._newline()
            if tag[0] == "h" and tag[1:].isdigit():
                self.chunks.append("\n" + "#" * int(tag[1:]) + " ")
            elif tag == "li":
                self.chunks.append("- ")
        elif tag in ("td", "th"):
            self.chunks.append("| " if self._at_line_start() else " | ")
        else:
            self._inline_boundary = True
        notes = [
            value.strip()
            for name, value in attrs
            if value
            and (
                name in _TEXT_ATTRS
                or (name.startswith("data-") and len(value) >= 20 and " " in value)
            )
        ]
        if notes:
            lead = "" if self._at_line_start() else " "
            self.chunks.append(lead + "[" + " / ".join(notes) + "] ")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("style", "template") or (tag == "script" and not self.keep_scripts):
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag in ("script", "pre"):
            self._raw_depth = max(0, self._raw_depth - 1)
            self._newline()
        elif tag in _BLOCK_TAGS:
            self._newline()
        else:
            self._inline_boundary = True

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._raw_depth:
            self.chunks.append(data)
            return
        text = re.sub(r"\s+", " ", data)
        if self._at_line_start():
            text = text.lstrip()
        elif self._inline_boundary and self.chunks[-1][-1:].isalnum() and text[:1].isalnum():
            # Two inline elements side by side, like a word and a badge: a browser often
            # separates them with margins, so keep the words apart here too.
            text = " " + text
        self._inline_boundary = False
        if text:
            self.chunks.append(text)

    def _at_line_start(self) -> bool:
        return not self.chunks or self.chunks[-1].endswith("\n")

    def _newline(self) -> None:
        if not self._at_line_start():
            self.chunks.append("\n")

    def text(self) -> str:
        lines = (line.rstrip() for line in "".join(self.chunks).splitlines())
        joined = "\n".join(line for line in lines)
        return re.sub(r"\n{3,}", "\n\n", joined).strip()


def html_to_text(markup: str, keep_scripts: bool) -> str:
    parser = _HtmlText(keep_scripts)
    parser.feed(markup)
    parser.close()
    return parser.text()


def find_chrome() -> str | None:
    """A Chrome or Chromium binary: $JUDGE_CHROME, the macOS app bundles, then $PATH."""
    candidates = [
        os.environ.get("JUDGE_CHROME"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        *(shutil.which(name) for name in ("google-chrome", "chromium", "chromium-browser")),
    ]
    return next((c for c in candidates if c and Path(c).exists()), None)


def render_html(path: Path, chrome: str) -> str:
    """The page's DOM after its scripts run, from headless Chrome."""
    with tempfile.TemporaryDirectory() as profile:
        try:
            done = subprocess.run(
                [
                    chrome,
                    "--headless=new",
                    "--disable-gpu",
                    "--no-first-run",
                    "--no-default-browser-check",
                    f"--user-data-dir={profile}",
                    "--virtual-time-budget=10000",
                    "--dump-dom",
                    path.resolve().as_uri(),
                ],
                capture_output=True,
                text=True,
                timeout=180,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise InputError(f"Chrome could not render {path.name}: {error}") from error
    if done.returncode != 0 or not done.stdout.strip():
        raise InputError(f"Chrome could not render {path.name}: {done.stderr.strip()[:300]}")
    return done.stdout


def _read_html(path: Path, display: str, mode: HtmlMode) -> Part:
    chrome = find_chrome() if mode in ("auto", "rendered") else None
    if mode == "rendered" and chrome is None:
        raise InputError("--html rendered needs Chrome or Chromium; set JUDGE_CHROME to its path")
    if chrome is not None:
        return Part(display, html_to_text(render_html(path, chrome), False), "html rendered")
    how = "html source" if mode == "source" else "html source (no Chrome found)"
    return Part(display, html_to_text(_decode(path), True), how)


# PDF and Word -----------------------------------------------------------------------------------


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(path)
        pages = [page.extract_text() or "" for page in reader.pages]
    except (PdfReadError, OSError, ValueError) as error:
        raise InputError(f"{path.name} is not a readable PDF: {error}") from error
    if not any(text.strip() for text in pages):
        raise InputError(f"{path.name} has no extractable text (a scanned PDF needs OCR first)")
    return "\n\n".join(f"[page {n}]\n{text.strip()}" for n, text in enumerate(pages, start=1))


_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _read_docx(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            root = ElementTree.fromstring(archive.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as error:
        raise InputError(f"{path.name} is not a readable .docx: {error}") from error
    paragraphs = ("".join(t.text or "" for t in p.iter(f"{_W}t")) for p in root.iter(f"{_W}p"))
    return "\n".join(paragraphs)


# Quotes -----------------------------------------------------------------------------------------

_ELLIPSIS = re.compile(r"\.\.\.|…|\[\.\.\.\]")
_NON_WORD = re.compile(r"[\W_]+")


def normalize(text: str) -> str:
    """Only the letters and digits, lowercased, with nothing between them: for matching quotes.

    Punctuation, markup and spacing are dropped, so a quote still matches when the judge leaves
    out Markdown emphasis, list bullets or table bars, changes a dash or a quote mark, or when
    text extraction glued or split words (HTML badges, PDF lines). The quote must still have the
    same letters and digits in the same order.
    """
    return _NON_WORD.sub("", unicodedata.normalize("NFKC", text).lower())


def quote_found(quote: str, normalized_text: str) -> bool:
    """Whether a quote appears in the (normalized) text. "..." in a quote skips words."""
    start = 0
    for fragment in (normalize(f) for f in _ELLIPSIS.split(quote)):
        if not fragment:
            continue
        found = normalized_text.find(fragment, start)
        if found < 0:
            return False
        start = found + len(fragment)
    return True
