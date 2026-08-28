import pytest

from screen2social.errors import ObsConfigError
from screen2social.obs import ObsConfig, load_obs_config


def test_load_obs_config_uses_local_defaults_and_hides_password():
    config = load_obs_config({"SCREEN2SOCIAL_OBS_PASSWORD": "super-secret"})

    assert config.host == "localhost"
    assert config.port == 4455
    assert config.timeout_seconds == 5.0
    assert config.password == "super-secret"
    assert "super-secret" not in repr(config)


def test_load_obs_config_trims_host_and_password():
    config = load_obs_config(
        {
            "SCREEN2SOCIAL_OBS_HOST": " 127.0.0.1 ",
            "SCREEN2SOCIAL_OBS_PASSWORD": " secret ",
        }
    )

    assert config.host == "127.0.0.1"
    assert config.password == "secret"


@pytest.mark.parametrize(
    "environ",
    [
        {},
        {"SCREEN2SOCIAL_OBS_PASSWORD": "   "},
        {"SCREEN2SOCIAL_OBS_PASSWORD": "secret", "SCREEN2SOCIAL_OBS_HOST": "   "},
        {"SCREEN2SOCIAL_OBS_PASSWORD": "secret", "SCREEN2SOCIAL_OBS_PORT": "0"},
        {"SCREEN2SOCIAL_OBS_PASSWORD": "secret", "SCREEN2SOCIAL_OBS_PORT": "65536"},
        {"SCREEN2SOCIAL_OBS_PASSWORD": "secret", "SCREEN2SOCIAL_OBS_PORT": "abc"},
        {"SCREEN2SOCIAL_OBS_PASSWORD": "secret", "SCREEN2SOCIAL_OBS_TIMEOUT_SECONDS": "0"},
        {"SCREEN2SOCIAL_OBS_PASSWORD": "secret", "SCREEN2SOCIAL_OBS_TIMEOUT_SECONDS": "-1"},
        {"SCREEN2SOCIAL_OBS_PASSWORD": "secret", "SCREEN2SOCIAL_OBS_TIMEOUT_SECONDS": "nan"},
        {"SCREEN2SOCIAL_OBS_PASSWORD": "secret", "SCREEN2SOCIAL_OBS_TIMEOUT_SECONDS": "inf"},
    ],
)
def test_load_obs_config_rejects_invalid_values(environ):
    with pytest.raises(ObsConfigError) as exc:
        load_obs_config(environ)

    assert exc.value.code == "OBS_CONFIG_ERROR"
    assert "secret" not in str(exc.value)
