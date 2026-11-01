import io
import json
import zipfile
from pathlib import Path

import pytest

from llm_judge import inputs
from llm_judge.inputs import InputError, html_to_text, load, normalize, quote_found, render_json


def test_plain_text_file(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("# Title\nBody text.")
    doc = load(tmp_path / "a.md")
    assert doc.text == "=== file: a.md (text) ===\n# Title\nBody text."
    assert doc.tokens == round(len(doc.text) / 3.5)
    assert len(doc.sha256) == 64


def test_json_renders_multiline_strings_as_blocks(tmp_path: Path) -> None:
    value = {"name": "n_root", "story": "line one\nline two", "tags": ["a", {"k": 1}], "x": None}
    (tmp_path / "t.json").write_text(json.dumps(value))
    part = load(tmp_path / "t.json").parts[0]
    assert part.how == "json"
    assert part.text == (
        "name: n_root\nstory: |\n  line one\n  line two\ntags:\n  - a\n  -\n    k: 1\nx: null"
    )


def test_render_json_empty_containers_and_scalars() -> None:
    assert render_json({"a": {}, "b": [], "c": True, "d": 1.5}) == "a: {}\nb: []\nc: true\nd: 1.5"
    assert render_json("plain") == "plain"


def test_invalid_json_falls_back_to_text(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text("{not json")
    assert load(tmp_path / "bad.json").parts[0].how == "text (invalid JSON)"


def test_jsonl_lines_are_numbered(tmp_path: Path) -> None:
    (tmp_path / "log.jsonl").write_text('{"kind": "a"}\n\nnot json\n')
    part = load(tmp_path / "log.jsonl").parts[0]
    assert part.text == "[line 1]\nkind: a\n[line 3]\nnot json"


def test_html_source_keeps_scripts_and_drops_styles() -> None:
    markup = """<html><head><style>.x{color:red}</style></head><body>
    <h2>Cast</h2><p>Alex   is the <b>CEO</b>.</p><ul><li>one</li><li>two</li></ul>
    <table><tr><th>A</th><td>B</td></tr></table>
    <span data-tip="tool:pay" title="Pays a bill">pay</span>
    <span data-note="a long note written as a sentence">n</span>
    <script>const DATA = {who: "Morgan"};</script></body></html>"""
    text = html_to_text(markup, keep_scripts=True)
    assert "color:red" not in text
    assert "## Cast" in text
    assert "Alex is the CEO." in text
    assert "- one\n- two" in text
    assert "| A | B" in text
    assert "[Pays a bill]" in text and "tool:pay" not in text
    assert "[a long note written as a sentence]" in text
    assert 'const DATA = {who: "Morgan"};' in text
    assert "Morgan" not in html_to_text(markup, keep_scripts=False)


def test_html_keeps_side_by_side_inline_words_apart() -> None:
    markup = '<p>and its renewal<span class="badge">benchmark</span>Tue, the <b>CEO</b>.</p>'
    assert html_to_text(markup, keep_scripts=False) == "and its renewal benchmark Tue, the CEO."


def test_html_auto_without_chrome_reads_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(inputs, "find_chrome", lambda: None)
    (tmp_path / "p.html").write_text("<p>Hi</p><script>var a = 'data';</script>")
    part = load(tmp_path / "p.html").parts[0]
    assert part.how == "html source (no Chrome found)"
    assert "var a = 'data';" in part.text
    assert load(tmp_path / "p.html", html="source").parts[0].how == "html source"
    with pytest.raises(InputError, match="needs Chrome"):
        load(tmp_path / "p.html", html="rendered")


def test_html_rendered_uses_the_dom(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(inputs, "find_chrome", lambda: "/fake/chrome")
    monkeypatch.setattr(
        inputs, "render_html", lambda path, chrome: "<p>Built by JS</p><script>x()</script>"
    )
    (tmp_path / "p.html").write_text("<script>document.write('Built by JS')</script>")
    part = load(tmp_path / "p.html").parts[0]
    assert (part.how, part.text) == ("html rendered", "Built by JS")


def test_render_html_reports_chrome_failure(tmp_path: Path) -> None:
    (tmp_path / "p.html").write_text("<p>x</p>")
    with pytest.raises(InputError, match="could not render"):
        inputs.render_html(tmp_path / "p.html", "/usr/bin/false")
    with pytest.raises(InputError, match="could not render"):
        inputs.render_html(tmp_path / "p.html", str(tmp_path / "no-such-chrome"))


def test_find_chrome_honours_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "chrome"
    fake.write_text("")
    monkeypatch.setenv("JUDGE_CHROME", str(fake))
    assert inputs.find_chrome() == str(fake)


def test_docx_paragraphs(tmp_path: Path) -> None:
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    xml = (
        f'<w:document xmlns:w="{w}"><w:body>'
        "<w:p><w:r><w:t>First </w:t></w:r><w:r><w:t>para</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Second</w:t></w:r></w:p></w:body></w:document>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", xml)
    (tmp_path / "d.docx").write_bytes(buffer.getvalue())
    assert load(tmp_path / "d.docx").parts[0].text == "First para\nSecond"
    (tmp_path / "bad.docx").write_text("not a zip")
    with pytest.raises(InputError, match="not a readable .docx"):
        load(tmp_path / "bad.docx")


def test_pdf_text(tmp_path: Path) -> None:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with (tmp_path / "blank.pdf").open("wb") as f:
        writer.write(f)
    # A blank or scanned page has no text, so the file is rejected rather than read as "".
    with pytest.raises(InputError, match="no extractable text"):
        load(tmp_path / "blank.pdf")
    (tmp_path / "bad.pdf").write_text("not a pdf")
    with pytest.raises(InputError, match="not a readable PDF"):
        load(tmp_path / "bad.pdf")


def test_binary_and_empty_and_missing_files(tmp_path: Path) -> None:
    (tmp_path / "x.bin").write_bytes(b"\x00\x01\x02")
    (tmp_path / "latin.txt").write_bytes("caf\xe9".encode("latin-1"))
    (tmp_path / "empty.txt").write_text("  \n")
    with pytest.raises(InputError, match="binary"):
        load(tmp_path / "x.bin")
    with pytest.raises(InputError, match="not UTF-8"):
        load(tmp_path / "latin.txt")
    with pytest.raises(InputError, match="no text"):
        load(tmp_path / "empty.txt")
    with pytest.raises(InputError, match="does not exist"):
        load(tmp_path / "nope.txt")


def test_directory_reads_in_order_and_skips(tmp_path: Path) -> None:
    (tmp_path / "b.md").write_text("bee")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "a.txt").write_text("ay")
    (tmp_path / "img.png").write_bytes(b"\x89PNG\x00\x00")
    (tmp_path / ".hidden").mkdir()
    (tmp_path / ".hidden" / "c.txt").write_text("secret")
    doc = load(tmp_path)
    assert [p.path for p in doc.parts] == ["b.md", "sub/a.txt"]
    assert doc.skipped[0].startswith("img.png:")
    assert "=== file: sub/a.txt (text) ===\nay" in doc.text
    only = load(tmp_path, include=["sub/*"])
    assert [p.path for p in only.parts] == ["sub/a.txt"]
    with pytest.raises(InputError, match="no readable files"):
        load(tmp_path, include=["*.none"])


def test_quote_matching() -> None:
    text = normalize("Contoso  prepaid its first\nannual contract — by wire — in “December” 2020.")
    assert quote_found("contoso prepaid its first annual contract", text)
    assert quote_found('Contoso prepaid ... in "December" 2020', text)
    assert quote_found("Contoso prepaid … by wire", text)
    assert not quote_found("Contoso paid monthly", text)
    assert not quote_found("in December ... Contoso", text)  # fragments must be in order
    assert quote_found("Contoso prepaid its firstannual contract", text)  # glued by extraction
    assert quote_found("", text)


def test_quotes_ignore_markup_and_punctuation() -> None:
    text = normalize(
        '**Meridian Data, Inc.** ("Meridian"), a YC-backed startup.\n'
        "Opening balances on **2021-01-01**:\n- **Mercury Checking X0666: $2,295,363.20**\n"
        "- **Mercury Treasury: $2,000,000.00**\n| Atlas | `n_atlas` |"
    )
    assert quote_found('Meridian Data, Inc. ("Meridian"), a YC-backed startup', text)
    assert quote_found("Opening balances on 2021-01-01: Mercury Checking X0666: $2,295,363", text)
    assert quote_found("X0666: $2,295,363.20; Mercury Treasury: $2,000,000.00", text)
    assert quote_found("Atlas n_atlas", text)
    assert not quote_found("Mercury Checking X0666 has $2,295,363.20", text)  # an added word
    assert not quote_found("Mercury Checking X0666: $2,295,363.21", text)  # a changed number
