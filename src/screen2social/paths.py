import re
import unicodedata
from pathlib import Path

from screen2social.errors import OutputExistsError


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return slug or "recording"


def create_package_dir(source: Path, ready_root: Path) -> Path:
    ready_root = ready_root.expanduser().resolve()
    ready_root.mkdir(parents=True, exist_ok=True)
    package_dir = ready_root / slugify(source.stem)
    try:
        package_dir.mkdir()
    except FileExistsError as exc:
        raise OutputExistsError(f"Output package already exists: {package_dir}") from exc
    return package_dir
