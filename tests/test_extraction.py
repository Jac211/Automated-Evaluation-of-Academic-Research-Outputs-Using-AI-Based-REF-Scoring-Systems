from ref_evaluator.extraction import count_words, segment_text, strip_references


def test_segment_preserves_original_text():
    text = "Hello, world (e.g. this).\nNext   line here."
    segments = segment_text(text, 3)
    assert segments == ["Hello, world (e.g.", "this).\nNext   line", "here."]


def test_segment_covers_all_words():
    text = " ".join(f"w{i}" for i in range(10))
    segments = segment_text(text, 4)
    assert [count_words(s) for s in segments] == [4, 4, 2]


def test_segment_empty():
    assert segment_text("   ", 5) == []


def test_strip_references_removes_trailing_list():
    body = "Intro text. " * 50
    text = f"{body}\nReferences\n[1] Smith 2020.\n[2] Jones 2021."
    assert strip_references(text) == f"{body}\n"


def test_strip_references_ignores_early_heading():
    text = "Contents\nReferences\n" + "Body text. " * 50
    assert strip_references(text) == text


def test_strip_references_numbered_heading():
    body = "Body. " * 50
    assert strip_references(f"{body}\n7. Bibliography\nA. Author.") == f"{body}\n"
