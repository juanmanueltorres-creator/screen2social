from pathlib import Path


def build_post_markdown(source: Path) -> str:
    title = source.stem.strip() or "Recording"
    return (
        f"# {title}\n"
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


def write_post(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
