import pytest

from screen2social.errors import OutputExistsError
from screen2social.paths import create_package_dir, slugify


def test_slugify_is_filesystem_safe_and_deterministic():
    assert slugify("GeoPlatform: Pulso Público 01!") == "geoplatform-pulso-publico-01"


def test_create_package_dir_uses_source_stem(tmp_path):
    source = tmp_path / "GeoPlatform Demo.mkv"
    source.touch()
    ready = tmp_path / "ready"

    package_dir = create_package_dir(source, ready)

    assert package_dir == ready / "geoplatform-demo"
    assert package_dir.is_dir()


def test_create_package_dir_never_overwrites_existing_package(tmp_path):
    source = tmp_path / "demo.mkv"
    source.touch()
    ready = tmp_path / "ready"
    (ready / "demo").mkdir(parents=True)

    with pytest.raises(OutputExistsError) as exc:
        create_package_dir(source, ready)

    assert exc.value.code == "OUTPUT_EXISTS"
