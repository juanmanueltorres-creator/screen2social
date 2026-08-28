from pathlib import Path

from screen2social.social import build_post_markdown, write_post


def test_build_post_markdown_uses_readable_source_stem_and_canonical_assets():
    content = build_post_markdown(Path("GeoPlatform demo Filo del Sol.mkv"))

    assert content == (
        "# GeoPlatform demo Filo del Sol\n"
        "\n"
        "## Post\n"
        "\n"
        "[Escribí acá el texto final del post]\n"
        "\n"
        "## Assets\n"
        "\n"
        "- Video: linkedin.mp4\n"
        "- Thumbnail: thumbnail.png\n"
        "\n"
        "## Checklist\n"
        "\n"
        "- [ ] Revisé el video\n"
        "- [ ] Elegí thumbnail\n"
        "- [ ] Revisé el texto\n"
        "- [ ] Publicado en LinkedIn\n"
    )


def test_build_post_markdown_trims_title_and_preserves_utf8():
    content = build_post_markdown(Path("  Qué está pasando  .mkv"))

    assert content.startswith("# Qué está pasando\n")
    assert "Escribí acá" in content
    assert content.endswith("\n")


def test_build_post_markdown_uses_recording_for_blank_stem():
    content = build_post_markdown(Path("   .mkv"))

    assert content.startswith("# Recording\n")


def test_write_post_writes_utf8_content(tmp_path):
    destination = tmp_path / "post.md"
    content = "# Córdoba\n\nPublicación territorial.\n"

    write_post(destination, content)

    assert destination.read_text(encoding="utf-8") == content
