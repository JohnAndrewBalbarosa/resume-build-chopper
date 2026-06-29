from resume_builder.extraction.models import CleanedSource, DEFAULT_CAP_CHARS


def test_cleaned_source_defaults():
    cs = CleanedSource(source_id="owner/repo:README.md", kind="github_readme")
    assert cs.text == ""
    assert cs.section_hints == []
    assert cs.truncated is False and cs.degraded is False


def test_cap_chars_constant():
    assert DEFAULT_CAP_CHARS == 12000
