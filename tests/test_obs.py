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

from types import SimpleNamespace

import simpleobsws
import screen2social.obs as obs_module
from screen2social.errors import ObsAuthError, ObsConnectionError, ObsRequestError


class FakeResponse:
    def __init__(self, *, ok=True, code=100, comment=None, data=None):
        self.requestStatus = SimpleNamespace(code=code, comment=comment)
        self.responseData = data
        self._ok = ok

    def ok(self):
        return self._ok


class FakeClient:
    def __init__(
        self,
        *,
        identified=True,
        close_code=None,
        connect_error=None,
        identify_error=None,
        call_error=None,
        response=None,
    ):
        self.identified = identified
        self.ws = SimpleNamespace(close_code=close_code)
        self.connect_error = connect_error
        self.identify_error = identify_error
        self.call_error = call_error
        self.response = response or FakeResponse(data={})
        self.connect_calls = 0
        self.identify_calls = []
        self.call_requests = []
        self.disconnect_calls = 0

    async def connect(self):
        self.connect_calls += 1
        if self.connect_error:
            raise self.connect_error
        return True

    async def wait_until_identified(self, timeout):
        self.identify_calls.append(timeout)
        if self.identify_error:
            raise self.identify_error
        return self.identified

    async def call(self, request, timeout):
        self.call_requests.append((request.requestType, timeout))
        if self.call_error:
            raise self.call_error
        return self.response

    async def disconnect(self):
        self.disconnect_calls += 1
        return True


def _config():
    return ObsConfig("localhost", 4455, "secret", 5.0)


def test_call_obs_request_connects_identifies_calls_and_disconnects(monkeypatch):
    client = FakeClient(response=FakeResponse(data={"ok": True}))
    monkeypatch.setattr(obs_module, "_make_client", lambda config: client)

    response = obs_module._call_obs_request(_config(), "GetRecordStatus")

    assert response.responseData == {"ok": True}
    assert client.connect_calls == 1
    assert client.identify_calls == [5.0]
    assert client.call_requests == [("GetRecordStatus", 5.0)]
    assert client.disconnect_calls == 1


def test_connection_failure_maps_to_stable_error_and_disconnects(monkeypatch):
    client = FakeClient(connect_error=OSError("connection refused"))
    monkeypatch.setattr(obs_module, "_make_client", lambda config: client)

    with pytest.raises(ObsConnectionError) as exc:
        obs_module._call_obs_request(_config(), "GetRecordStatus")

    assert exc.value.code == "OBS_CONNECTION_FAILED"
    assert client.disconnect_calls == 1


def test_identify_timeout_maps_to_connection_failed(monkeypatch):
    client = FakeClient(identified=False)
    monkeypatch.setattr(obs_module, "_make_client", lambda config: client)

    with pytest.raises(ObsConnectionError):
        obs_module._call_obs_request(_config(), "GetRecordStatus")

    assert client.disconnect_calls == 1


def test_auth_close_code_4009_maps_to_auth_failed(monkeypatch):
    client = FakeClient(identified=False, close_code=4009)
    monkeypatch.setattr(obs_module, "_make_client", lambda config: client)

    with pytest.raises(ObsAuthError) as exc:
        obs_module._call_obs_request(_config(), "GetRecordStatus")

    assert exc.value.code == "OBS_AUTH_FAILED"
    assert client.disconnect_calls == 1


def test_request_timeout_maps_to_request_failed(monkeypatch):
    client = FakeClient(call_error=simpleobsws.MessageTimeout("timeout"))
    monkeypatch.setattr(obs_module, "_make_client", lambda config: client)

    with pytest.raises(ObsRequestError) as exc:
        obs_module._call_obs_request(_config(), "GetRecordStatus")

    assert exc.value.code == "OBS_REQUEST_FAILED"
    assert client.disconnect_calls == 1

from screen2social.obs import ObsRecordStatus, get_record_status


def test_get_record_status_normalizes_active_response(monkeypatch):
    response = FakeResponse(
        data={
            "outputActive": True,
            "outputPaused": False,
            "outputTimecode": "00:01:23.456",
            "outputDuration": 83456,
            "outputBytes": 1234567,
        }
    )
    client = FakeClient(response=response)
    monkeypatch.setattr(obs_module, "_make_client", lambda config: client)

    status = get_record_status(_config())

    assert status == ObsRecordStatus(
        active=True,
        paused=False,
        timecode="00:01:23.456",
        duration_ms=83456,
        bytes_written=1234567,
    )


def test_get_record_status_normalizes_stopped_response(monkeypatch):
    response = FakeResponse(
        data={
            "outputActive": False,
            "outputPaused": False,
            "outputTimecode": "00:00:00.000",
            "outputDuration": 0,
            "outputBytes": 0,
        }
    )
    monkeypatch.setattr(obs_module, "_make_client", lambda config: FakeClient(response=response))

    assert get_record_status(_config()).active is False


def test_get_record_status_normalizes_paused_response(monkeypatch):
    response = FakeResponse(
        data={
            "outputActive": True,
            "outputPaused": True,
            "outputTimecode": "00:00:10.000",
            "outputDuration": 10000,
            "outputBytes": 2048,
        }
    )
    monkeypatch.setattr(obs_module, "_make_client", lambda config: FakeClient(response=response))

    status = get_record_status(_config())

    assert status.active is True
    assert status.paused is True


@pytest.mark.parametrize(
    "data",
    [
        None,
        {},
        {"outputActive": 1, "outputPaused": False, "outputTimecode": "x", "outputDuration": 0, "outputBytes": 0},
        {"outputActive": True, "outputPaused": False, "outputTimecode": 123, "outputDuration": 0, "outputBytes": 0},
        {"outputActive": True, "outputPaused": False, "outputTimecode": "x", "outputDuration": -1, "outputBytes": 0},
        {"outputActive": True, "outputPaused": False, "outputTimecode": "x", "outputDuration": 0, "outputBytes": -1},
    ],
)
def test_get_record_status_rejects_malformed_data(monkeypatch, data):
    monkeypatch.setattr(
        obs_module,
        "_make_client",
        lambda config: FakeClient(response=FakeResponse(data=data)),
    )

    with pytest.raises(ObsRequestError) as exc:
        get_record_status(_config())

    assert exc.value.code == "OBS_REQUEST_FAILED"


def test_get_record_status_rejects_failed_obs_response(monkeypatch):
    response = FakeResponse(ok=False, code=500, comment="generic failure")
    monkeypatch.setattr(obs_module, "_make_client", lambda config: FakeClient(response=response))

    with pytest.raises(ObsRequestError):
        get_record_status(_config())
